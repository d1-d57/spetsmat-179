"""§2 and §3: what the pipeline does to the bytes, and — louder — what it must not.

THE TESTS THAT MATTER HERE ARE THE ONES ABOUT NOT ACTING.  Upscaling costs up to 34
percentage points of accuracy, the worst operation in the whole benchmark, and it is
exactly the operation that feels like an improvement to whoever edits this next
(«the target is 1568, this image is 900, let us make it 1568»).  So the prohibition is
asserted twice: once on the step log of a real small image, and once on the guard
itself, fed an operation it must refuse.
"""

from __future__ import annotations

import io
import time

import pytest

from core.services.raspoznavanie import (
    FORBIDDEN_OPERATIONS,
    IntakeRefused,
    MAX_DOWNLOAD_BYTES,
    PreprocessingViolation,
    TARGET_LONG_SIDE,
    _guard,
    choose_photo_size,
    prepare,
    refuse_if_too_large,
    sha256_of,
)

PIL = pytest.importorskip("PIL")
pytest.importorskip("cv2")


# ------------------------------------------------------------------------- fixtures

def _photo(width, height, *, orientation=None, fmt="JPEG"):
    """A JPEG that looks enough like a photographed sheet to exercise the geometry.

    A flat colour would give the sheet detector no edges at all and would test the
    ``crop:skipped-sheet-not-found`` branch forever; this draws a bright rectangle on a
    dark ground, which is what a lit sheet on a desk actually is.
    """
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), (40, 40, 45))
    draw = ImageDraw.Draw(image)
    inset_x, inset_y = width // 12, height // 12
    draw.rectangle(
        [inset_x, inset_y, width - inset_x, height - inset_y], fill=(250, 250, 248)
    )
    for row in range(6):
        y = inset_y + (height - 2 * inset_y) * (row + 1) // 8
        draw.line([(inset_x, y), (width - inset_x, y)], fill=(120, 120, 120), width=2)

    buffer = io.BytesIO()
    if orientation is None:
        image.save(buffer, fmt, quality=95)
    else:
        exif = Image.Exif()
        exif[274] = orientation  # 274 = Orientation
        image.save(buffer, fmt, quality=95, exif=exif)
    return buffer.getvalue()


# --------------------------------------------------------- the prohibitions (§3)

def test_a_small_image_is_never_enlarged():
    """The single most expensive mistake available on this path, closed by a branch.

    900 px in, 900 px out.  Not 1568: an upscale to hit a round number is up to 34
    percentage points of accuracy, the worst operation in the entire benchmark.
    """
    prepared = prepare(_photo(900, 600))

    assert prepared.long_side <= 900
    assert any(step.startswith("resize:skipped-already-small") for step in prepared.steps), (
        prepared.steps
    )
    assert not any(step.startswith("resize:INTER_AREA") for step in prepared.steps)


def test_the_guard_refuses_every_operation_the_benchmark_forbids():
    """The negative control on the prohibition itself.

    Seven forbidden operations, seven refusals, and one honest step log that must pass.
    A guard that cannot go red is a comment with parentheses.
    """
    refused = 0
    for operation in FORBIDDEN_OPERATIONS:
        with pytest.raises(PreprocessingViolation) as raised:
            _guard(["exif:already-upright", "%s:whatever" % operation])
        assert operation in str(raised.value)
        refused += 1

    assert refused == len(FORBIDDEN_OPERATIONS) == 7, (
        "expected all seven forbidden operations to be refused, got %d" % refused
    )
    # And the log a correct run produces goes through untouched.
    assert _guard(["exif:rotated", "resize:INTER_AREA(3000x2000->1568x1045)", "jpeg:q90"])


def test_no_per_row_slicing_is_reachable():
    """CER 64 with per-row slicing against 1,21 on the whole scan.

    There is no code path that cuts rows, and ``slice_rows`` is in the forbidden set so
    that adding one and recording it honestly goes red rather than shipping.
    """
    assert "slice_rows" in FORBIDDEN_OPERATIONS
    prepared = prepare(_photo(2000, 1400))
    assert isinstance(prepared.jpeg, bytes)  # ONE image, not a list of strips


# --------------------------------------------------------------- what it does do (§3)

def test_a_large_image_is_downscaled_with_inter_area():
    prepared = prepare(_photo(3000, 2000))

    assert prepared.long_side <= TARGET_LONG_SIDE, prepared.steps
    assert any("INTER_AREA" in step for step in prepared.steps), prepared.steps


def test_exif_orientation_is_honoured():
    """The cheapest and largest single win: up to 14% on closed models.

    Orientation 6 means «rotate 90° clockwise to display».  A reader that ignores the tag
    hands the model a table lying on its side; the sides must come back swapped.
    """
    prepared = prepare(_photo(1200, 800, orientation=6))

    assert any(step == "exif:rotated" for step in prepared.steps), prepared.steps
    assert prepared.height > prepared.width, (prepared.width, prepared.height)


def test_perspective_is_corrected_only_when_the_sheet_is_visibly_skewed():
    """A straight-on shot must record the DECISION not to warp, not merely omit it."""
    prepared = prepare(_photo(1400, 1000))
    geometry = [s for s in prepared.steps if s.startswith(("crop:", "perspective:"))]
    assert geometry, prepared.steps
    assert not any(s.startswith("perspective:corrected") for s in geometry), geometry


def test_the_pipeline_stays_within_its_measured_budget():
    """230-250 ms is the claim; the ceiling here is loose on purpose.

    A tight assertion on wall-clock is a test that fails on somebody else's laptop for
    reasons that are not this project's.  What must not pass silently is an edit that
    puts ``fastNlMeansDenoisingColored`` (3,4 s on its own) back in.
    """
    raw = _photo(2560, 1440)
    started = time.perf_counter()
    prepare(raw)
    elapsed = time.perf_counter() - started
    print("[preprocessing] 2560x1440 -> %d ms (claim: 230-250 ms)" % (elapsed * 1000))
    assert elapsed < 2.0, "preprocessing took %.2f s" % elapsed


# ------------------------------------------------------------------------ intake (§2)

def test_the_hash_is_of_the_downloaded_bytes_and_not_of_the_jpeg_we_produced():
    """§8's idempotency key must identify the PHOTOGRAPH, not this pipeline's output.

    Otherwise a change to ``TARGET_LONG_SIDE`` turns yesterday's photo into a new photo
    and the whole sheet is recorded a second time.
    """
    raw = _photo(1800, 1200)
    prepared = prepare(raw)

    assert prepared.sha256 == sha256_of(raw)
    assert prepared.sha256 != sha256_of(prepared.jpeg)


def test_a_file_over_twenty_megabytes_is_refused_in_a_sentence():
    """``getFile`` gives at most 20 MB — the bot may SEND 50 and may DOWNLOAD 20."""
    refuse_if_too_large(MAX_DOWNLOAD_BYTES)  # exactly at the limit is fine
    with pytest.raises(IntakeRefused) as raised:
        refuse_if_too_large(MAX_DOWNLOAD_BYTES + 1)
    assert "20" in str(raised.value)


def test_choose_photo_size_takes_the_largest_that_getfile_can_fetch():
    class Size:
        def __init__(self, width, height, file_size):
            self.width, self.height, self.file_size = width, height, file_size

    sizes = [Size(320, 180, 20_000), Size(1280, 720, 300_000), Size(2560, 1440, 900_000)]
    assert choose_photo_size(sizes).width == 2560

    over = [Size(2560, 1440, MAX_DOWNLOAD_BYTES + 1), Size(1280, 720, 300_000)]
    assert choose_photo_size(over).width == 1280

    assert choose_photo_size([Size(2560, 1440, MAX_DOWNLOAD_BYTES + 1)]) is None
    assert choose_photo_size([]) is None


def test_a_corrupt_upload_is_an_expected_input_and_not_a_traceback():
    with pytest.raises(IntakeRefused):
        prepare(b"this is not an image")
