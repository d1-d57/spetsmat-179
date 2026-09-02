"""ОБРЕЗКА РЕЖЕТ КОДЫ И ПОДПИСИ — the band outside the detected quadrilateral.

``_sheet_quad`` looks for the SHEET.  It finds the largest four-sided thing in the frame,
and that is the sheet only while the edge of the paper is in the shot.  Photograph the
form close enough to read it — which is what anyone does who wants it legible — and the
largest quadrilateral is the RULED GRID.  The crop then follows the grid's own lines, and
the column of codes ``u1…u18`` and the row of task labels are printed OUTSIDE those
lines, so both leave with the crop.

🔴 WHAT THAT LOOKS LIKE FROM THE CLASSROOM.  The model is handed a bare grid.  It sees
every tick, it cannot say whose they are, and it refuses honestly — ``rows`` empty and
``raw_text`` saying «в последней ВИДИМОЙ строке, в последнем ВИДИМОМ столбце».  Measured
by the оркестратор on 2026-09-02: the same form with the paper edge in shot came back
with correct rows, and the same form filling the frame came back empty.

WHAT GOES RED IF THE FIX IS REVERTED — measured on 2026-09-02 by actually setting
``SHEET_MARGIN = 0.0`` and running the file, not estimated: 4 failed, 3 passed.  The four
are the containment test, the frame-versus-rectangle test, the step-log test and the
warping-branch test.  None of them asserts that a field is present; they all assert about
pixels of a form built by the real ``tools/blank.py``.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest

import config
from core.services.raspoznavanie import (
    SHEET_MARGIN,
    TARGET_LONG_SIDE,
    _crop_to_sheet,
    _downscale,
    _ordered,
    _sheet_quad,
    prepare,
)

pytest.importorskip("PIL")
cv2 = pytest.importorskip("cv2")
numpy = pytest.importorskip("numpy")

#: Anything darker than this is ink.  Generous on purpose: the anti-aliased edge of a
#: 22 px label is nowhere near black, and a strict threshold would quietly stop seeing
#: the very text this file is about.
INK = 128


# ------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def form_bytes():
    """A REAL form from ``tools/blank.py``, filling the frame, no paper edge in shot.

    Not a synthetic rectangle on a dark ground: the defect lives precisely in the
    difference between the two.  A drawn rectangle HAS an outer edge for the detector to
    find, which is why the synthetic fixture in ``test_preprocessing.py`` never showed
    this and 18 gates out of 18 stayed green.
    """
    from tools.blank import ROWS_PER_FORM, draw_form, labels_of_sheet, roster_from_seed

    roster = roster_from_seed(config.SEED_DIR)[:ROWS_PER_FORM]
    labels = labels_of_sheet(config.SEED_DIR, "1")
    if not roster or not labels:
        pytest.skip("seed/ is the oracle of this file and it is empty")

    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "blank.png"
        draw_form([code for code, _ in roster], labels, "1", "302", path)
        return path.read_bytes()


def _frame(raw):
    """The frame exactly as ``prepare`` has it when the geometry step is reached."""
    import io

    from PIL import Image, ImageOps

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    frame, _ = _downscale(numpy.asarray(image)[:, :, ::-1])
    return frame


def _ink_box(frame):
    """``(x0, y0, x1, y1)`` covering every dark pixel, ends inclusive."""
    ink = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) < INK
    columns = numpy.where(ink.any(axis=0))[0]
    rows = numpy.where(ink.any(axis=1))[0]
    assert columns.size and rows.size, "the form came out blank"
    return int(columns.min()), int(rows.min()), int(columns.max()), int(rows.max())


def _found_rect(frame):
    """``(x, y, w, h)`` of the quadrilateral the detector calls «the sheet»."""
    quad = _sheet_quad(frame)
    assert quad is not None, "no quadrilateral found on a printed form"
    return tuple(int(v) for v in cv2.boundingRect(_ordered(quad).astype("int32")))


def _margin_of(steps):
    """The band this run ASKED FOR, read out of the step log.

    Named for the request and not for the result, because those are two different numbers
    whenever a side runs into the frame -- see ``_kept_of``.  The first version of this
    helper called the request «the band actually kept», and the docstring was the whole
    of the evidence for it.
    """
    for step in steps:
        if "margin=" in step:
            return int(step.split("margin=", 1)[1].split("px", 1)[0])
    raise AssertionError("no step names a margin: %r" % (list(steps),))


def _kept_of(steps):
    """The band the step log says it KEPT: ``{"l": .., "t": .., "r": .., "b": ..}``.

    The warping branch keeps one number for all four sides -- it clamps nothing and
    shrinks everything together -- so it is spread across the four keys here, and a
    caller comparing sides sees «equal», which is true of that branch.
    """
    for step in steps:
        if "kept=" in step:
            body = step.split("kept=", 1)[1].rstrip(")")
            if body.endswith("px"):
                value = int(body[:-2])
                return {side: value for side in "ltrb"}
            return {part[0]: int(part[1:]) for part in body.split(",")}
    raise AssertionError("no step names the band it kept: %r" % (list(steps),))


# ------------------------------------------------------------------- the premise

def test_the_detector_finds_the_grid_and_the_codes_stand_outside_it(form_bytes):
    """🔴 THE PREMISE OF THE WHOLE FILE, ASSERTED RATHER THAN ASSUMED.

    If this one ever goes red the defect has changed shape and the rest of the file is
    reasoning about something that no longer happens — which is worth knowing loudly.
    """
    frame = _frame(form_bytes)
    x, y, w, h = _found_rect(frame)
    ink_x0, ink_y0, _, ink_y1 = _ink_box(frame)

    assert ink_x0 < x, (
        "the codes were expected OUTSIDE the found rectangle; ink starts at x=%d and the "
        "rectangle at x=%d — the detector may now be finding the sheet" % (ink_x0, x)
    )
    assert ink_y0 < y, "the task labels stand above the grid: ink y=%d, rect y=%d" % (
        ink_y0, y
    )
    assert ink_y1 > y + h, "the legend stands below the grid: ink y=%d, rect ends %d" % (
        ink_y1, y + h,
    )


# ------------------------------------------------------------------------ the fix

def test_the_crop_keeps_every_mark_that_was_in_the_frame(form_bytes):
    """NOTHING PRINTED IS THROWN AWAY — the codes, the labels and the legend all survive.

    Stated as containment of ink rather than as a size, because a size can be satisfied
    by cropping the wrong 1086 pixels.  Ink is what the model reads.
    """
    frame = _frame(form_bytes)
    ink_x0, ink_y0, ink_x1, ink_y1 = _ink_box(frame)

    cropped, steps = _crop_to_sheet(frame)
    x, y, w, h = _found_rect(frame)
    margin = _margin_of(steps)
    kept_x0, kept_y0 = max(0, x - margin), max(0, y - margin)
    kept_x1 = min(frame.shape[1], x + w + margin) - 1
    kept_y1 = min(frame.shape[0], y + h + margin) - 1

    assert kept_x0 <= ink_x0, (
        "the code column is cut: ink starts at x=%d, the crop at x=%d (margin %d px)"
        % (ink_x0, kept_x0, margin)
    )
    assert kept_y0 <= ink_y0, "the task labels are cut: ink y=%d, crop y=%d" % (
        ink_y0, kept_y0,
    )
    assert kept_x1 >= ink_x1 and kept_y1 >= ink_y1, (
        "ink runs to (%d, %d) and the crop ends at (%d, %d)"
        % (ink_x1, ink_y1, kept_x1, kept_y1)
    )
    assert cropped.shape[1] >= w and cropped.shape[0] >= h


def test_the_band_is_measured_against_the_frame_and_not_against_the_found_rectangle(
    form_bytes,
):
    """🔴 THE DECISION THE MEASUREMENT FORCED, PINNED SO IT CANNOT BE «TIDIED» BACK.

    Eight per cent sounds like eight per cent either way.  It is not: on this form the
    codes need 102 px, which is 6,5 % of the frame's long side and 10,7 % of the found
    rectangle.  A fraction of the rectangle fails, and it fails WORSE on a shorter sheet,
    because the rectangle shrinks with the label count while the printed column does not.
    """
    frame = _frame(form_bytes)
    x, _, w, _ = _found_rect(frame)
    ink_x0 = _ink_box(frame)[0]
    needed = x - ink_x0

    _, steps = _crop_to_sheet(frame)
    margin = _margin_of(steps)

    assert margin == round(SHEET_MARGIN * max(frame.shape[:2]))
    assert margin >= needed, "%d px of band against %d px of codes" % (margin, needed)
    assert round(SHEET_MARGIN * w) < needed, (
        "the same %.0f %% of the FOUND RECTANGLE is %d px and would lose the codes — "
        "if that has stopped being true, re-measure before simplifying this"
        % (SHEET_MARGIN * 100, round(SHEET_MARGIN * w))
    )


def test_a_side_that_hits_the_frame_edge_does_not_shrink_the_other_three(form_bytes):
    """🔴 THE MISTAKE THIS TEST WAS WRITTEN OUT OF, AND IT WAS MEASURED, NOT IMAGINED.

    The first version reduced ONE margin until all four sides fitted inside the frame —
    which reads as careful and is wrong here.  On this very form the grid reaches 5 px
    from the right edge of the frame, so the shared clamp cut the band to 4 px on ALL
    FOUR sides and the codes stayed outside exactly as before: ``crop:bounding-rect
    (964x568,margin=4px)``.  Each side is clamped on its own.
    """
    frame = _frame(form_bytes)
    x, y, w, h = _found_rect(frame)
    height, width = frame.shape[:2]
    assert width - (x + w) < 0.08 * max(frame.shape[:2]), (
        "this form no longer has a side against the frame edge, so this test proves "
        "nothing; rebuild it from one that does"
    )

    cropped, steps = _crop_to_sheet(frame)
    margin = _margin_of(steps)

    # ±2 px: the offset runs along the quadrilateral's own edges, and the grid is a
    # degree or so off square, so the bounding box of the grown corners is not the found
    # box plus exactly ``margin``.  The claim under test is «the left side kept its full
    # band while the right side hit the wall», and two pixels do not touch it.
    assert cropped.shape[1] >= min(width, x + w + margin) - max(0, x - margin) - 2, (
        "the width collapsed to %d where the per-side clamp gives %d — a shared clamp is "
        "back" % (cropped.shape[1], min(width, x + w + margin) - max(0, x - margin))
    )
    assert cropped.shape[0] >= min(height, y + h + margin) - max(0, y - margin) - 2


def test_the_step_log_names_the_band_as_honestly_as_it_names_the_crop(form_bytes):
    """A crop that silently keeps a band and one that silently does not look identical.

    ``Prepared.steps`` is the audit channel of this pipeline — the place where «nothing
    was enlarged» is a checkable claim rather than a docstring — and a step that did
    something unnamed is the one shape it must never take.
    """
    prepared = prepare(form_bytes)
    geometry = [s for s in prepared.steps if s.startswith(("crop:", "perspective:"))]

    assert geometry, prepared.steps
    assert any("margin=" in step for step in geometry), geometry
    assert _margin_of(geometry) > 0


def test_the_step_log_names_the_band_it_KEPT_and_not_the_one_it_asked_for(form_bytes):
    """🔴 THE REQUEST AND THE RESULT ARE DIFFERENT NUMBERS, AND ONLY ONE OF THEM IS TRUE.

    ``margin`` is what the crop ASKS for; the slice grants it per side, and a band that
    runs off the frame stops at the frame.  On this very form the grid stands 8 px from
    the right edge, so the right band is 8 px while ``margin`` says 187 -- and 8 px is
    exactly the number at which the codes stay outside, which is the shared-clamp defect
    this file already tests for.  A log printing only the request reads identically in
    both cases, so the ONE job of that line -- telling a crop that kept its band from one
    that did not -- is not done by it.  Found by the §3 verifier, not by this file.

    The assertion is against PIXELS, not against a second copy of the formula: the four
    numbers must add up to the picture that came out.
    """
    frame = _frame(form_bytes)
    x, y, w, h = _found_rect(frame)
    height, width = frame.shape[:2]

    assert width - (x + w) < 0.08 * max(frame.shape[:2]), (
        "this form no longer has a side against the frame edge, so this test proves "
        "nothing; rebuild it from one that does"
    )

    cropped, steps = _crop_to_sheet(frame)
    asked, kept = _margin_of(steps), _kept_of(steps)

    assert kept["r"] < asked, (
        "the right side ran into the frame edge, yet the log reports the full band "
        "%d px on it (kept=%r) -- the request is being printed as the result" % (asked, kept)
    )
    assert kept["l"] == asked, (
        "the left side had room for the whole band and must show it: %r" % (kept,)
    )

    # ±2 px: the offset runs along the quadrilateral's own edges and the grid is a degree
    # or so off square, so the grown bounding box is not the found box plus exactly the
    # band.  The claim under test is «these four numbers describe THIS picture».
    assert abs(cropped.shape[1] - (w + kept["l"] + kept["r"])) <= 2, (
        "log says l%d r%d around a %d px rectangle, which is %d px, but the picture is "
        "%d px wide" % (kept["l"], kept["r"], w, w + kept["l"] + kept["r"], cropped.shape[1])
    )
    assert abs(cropped.shape[0] - (h + kept["t"] + kept["b"])) <= 2, (
        "log says t%d b%d around a %d px rectangle, but the picture is %d px tall"
        % (kept["t"], kept["b"], h, cropped.shape[0])
    )


# -------------------------------------------------------- the branch a real photo takes

def _skewed(raw):
    """The same form seen from an angle: the branch a hand-held photograph reaches.

    The lean is 10 % with a 4 % drop, and those two numbers are not free — they were
    chosen by measurement.  At 16 % the detector loses the quadrilateral altogether and
    the run falls into ``crop:skipped-sheet-not-found``, which is a branch that proves
    nothing about a margin.
    """
    frame = _frame(raw)
    height, width = frame.shape[:2]
    source = numpy.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype="float32",
    )
    lean = width * 0.10
    target = numpy.array(
        [[lean, 0], [width - 1, height * 0.04],
         [width - 1 - lean, height - 1], [0, height * 0.96]],
        dtype="float32",
    )
    return cv2.warpPerspective(
        frame, cv2.getPerspectiveTransform(source, target), (width, height),
        borderValue=(255, 255, 255),
    )


def _ink_count(frame):
    return int((cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) < 160).sum())


def test_the_warping_branch_keeps_the_band_too(form_bytes, monkeypatch):
    """🔴 ONE DEFECT, TWO BRANCHES, AND THE WARPING ONE IS WHAT A REAL PHOTOGRAPH TAKES.

    Fixing only the rectangular branch would leave the classroom case — a phone held in a
    hand — cutting the codes exactly as before, while every test on a flat scan stayed
    green.  So this asserts on INK RECOVERED rather than on a size: the same skewed frame
    is cropped twice, once with the band and once without, and the difference is the
    codes, the task labels and the legend.
    """
    import core.services.raspoznavanie as module

    frame = _skewed(form_bytes)
    whole = _ink_count(frame)

    monkeypatch.setattr(module, "SHEET_MARGIN", 0.0)
    without, steps_without = _crop_to_sheet(frame)
    monkeypatch.setattr(module, "SHEET_MARGIN", SHEET_MARGIN)
    withband, steps_with = _crop_to_sheet(frame)

    assert [s for s in steps_with if s.startswith("perspective:corrected")], steps_with
    assert _margin_of(steps_with) > 0 and _margin_of(steps_without) == 0
    assert _ink_count(without) < 0.25 * whole, (
        "the no-margin crop was expected to lose most of the print (%d of %d) — if it "
        "does not, this test is no longer about anything"
        % (_ink_count(without), whole)
    )
    assert _ink_count(withband) > 0.7 * whole, (
        "the band recovered only %d of the frame's %d ink pixels"
        % (_ink_count(withband), whole)
    )


def test_the_warping_branch_reports_the_band_the_shrink_guard_left_it(form_bytes):
    """🔴 THE WARP CLAMPS NOTHING AND STILL DOES NOT GET THE BAND IT ASKED FOR.

    The guard above the warp forbids any dimension from growing, and a grown quadrilateral
    on a tilted sheet routinely trips it: the whole target is scaled down, and the band is
    scaled down with it.  Nothing is lost -- the picture is smaller, not cropped -- but the
    number of pixels of band in the OUTPUT is no longer the number that was requested, and
    the step log is the only place a reader could learn that.

    Measured here rather than recomputed: 125 px asked, 113 px in the picture.  The
    assertion is the INEQUALITY plus «the guard actually fired», so it stays true if the
    lean of the fixture is ever retuned.
    """
    frame = _skewed(form_bytes)
    _, steps = _crop_to_sheet(frame)

    step = [s for s in steps if s.startswith("perspective:corrected")]
    assert step, steps

    asked, kept = _margin_of(steps), _kept_of(steps)
    width = int(step[0].split(",")[1].split("x")[0])

    assert width == frame.shape[1], (
        "the shrink guard did not fire on this fixture (%d wide against a %d frame), so "
        "there is nothing here to report and this test proves nothing"
        % (width, frame.shape[1])
    )
    assert 0 < kept["l"] < asked, (
        "the guard shrank the target but the log still reports the full %d px band "
        "(kept=%r)" % (asked, kept)
    )


def test_the_band_never_turns_the_crop_into_an_enlargement(form_bytes):
    """The prohibition that outranks this whole fix: no dimension may grow.

    A band is added to a crop, never to the frame — and the warping branch computes its
    target from the GROWN corners, so this is the guard that says the growth did not
    sneak past ``scale``.  Enlargement is 34 pp at worst, the most damaging operation in
    the benchmark, and it would arrive here wearing the costume of a helpful margin.
    """
    for frame in (_frame(form_bytes), _skewed(form_bytes)):
        cropped, steps = _crop_to_sheet(frame)
        assert cropped.shape[0] <= frame.shape[0], steps
        assert cropped.shape[1] <= frame.shape[1], steps

    prepared = prepare(form_bytes)
    assert prepared.long_side <= TARGET_LONG_SIDE, prepared.steps
