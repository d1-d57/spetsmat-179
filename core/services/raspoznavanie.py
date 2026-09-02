"""Photo -> draft -> confirmation table -> journal.  There is never a direct write.

This module is the middle of that sentence.  It owns three things and deliberately not a
fourth:

  * **the CODE** a student is called by on paper and in flight (§4) -- `u17`, never a
    surname;
  * **the PREPROCESSING** (§2, §3) -- what happens to the bytes before they leave, and,
    louder, what must NOT happen to them;
  * **the CONFIDENCE** (§6) -- computed here, from the model's own verbatim
    transcription, because the number a model reports about itself does not exist.

The fourth thing -- the call itself -- lives in ``infra/llm.py``: it is the only part
that speaks HTTP, and keeping it out of ``core/`` is the same rule that keeps sqlite3 and
the Telegram library out of this tree.

THE LEGAL BOUNDARY, AND WHY IT IS A BOUNDARY AND NOT A PREFERENCE (§4).  Sending the
surname of a child to a model hosted abroad is a cross-border transfer of personal data,
and the lawful procedure for a private person running a school bot is unworkable.  The
answer is not to promise deletion afterwards.  It is that **if the image and the request
carry no personal data, there is no object of regulation at all**: the form is printed
with codes, the surname column does not exist on it, and the matching from code to child
happens on this machine, against a catalogue that never leaves it.  That is data
minimisation in its purest form rather than a loophole, and it is why
``tests/photo/test_privacy.py`` greps the outgoing payload instead of trusting this
paragraph.
"""

from __future__ import annotations

import re
from typing import Optional

#: The prefix a student's code carries on the printed form and in every payload that
#: leaves this machine.  One letter, so that a code stays short enough to be read off a
#: printed grid at arm's length, and so that the closed list handed to the model stays
#: well inside the ~120 values §5 calls Gemini's practical ceiling.
CODE_PREFIX = "u"

#: What a code is allowed to look like.  Anchored at both ends: a model that echoes
#: «u17.» or «строка u17» must fail to match rather than be silently trimmed into a
#: student id, because a silent trim is how a mark lands on the wrong child.
CODE_PATTERN = re.compile(r"^%s([1-9][0-9]*)$" % CODE_PREFIX)


def code_for_student(student_id: int) -> str:
    """The one place a student id becomes the string that appears on paper.

    The form generator and the bot both call this, so the two cannot drift: a form
    printed by one convention and read by another puts every mark on the wrong row, and
    the failure is silent -- every row is a real student, so nothing looks wrong.
    """
    if not isinstance(student_id, int) or isinstance(student_id, bool) or student_id < 1:
        raise ValueError("a student id is a positive integer, got %r" % (student_id,))
    return "%s%d" % (CODE_PREFIX, student_id)


def student_id_from_code(code: str) -> Optional[int]:
    """The inverse, and ``None`` for anything that is not exactly a code.

    ``None`` rather than an exception: the caller is holding a value a MODEL produced,
    and a model producing rubbish is an expected input on this path, not a bug in the
    program.  It becomes a doubtful row in the confirmation table, which is a thing the
    teacher can see and fix in one tap.
    """
    if not isinstance(code, str):
        return None
    match = CODE_PATTERN.match(code.strip())
    return int(match.group(1)) if match else None


# =============================================================================== §2, §3
#
# INTAKE, AND THE PREPROCESSING THAT MOSTLY CONSISTS OF NOT DOING THINGS
#
# The classic OCR advice actively harms a vision language model.  VLM-RobustBench, March
# 2026, 133 configurations over 9-11 models, accuracy loss in percentage points:
#
#     autocontrast            0,0
#     greyscale               3,2
#     histogram equalisation  3,5
#     inversion              10,1
#     UPSCALING              up to 34 -- the worst operation in the entire benchmark
#
# So the prohibitions below are not caution.  They are the largest single lever in this
# file, larger than anything the pipeline actively does, and they are written as a
# CARRIER -- ``FORBIDDEN_OPERATIONS`` and the guard over the step log -- rather than as
# an absence, because an absence is indistinguishable from a forgetting.
#
# WHAT IS DONE, in this order and for these reasons:
#
#   1. EXIF orientation.  The cheapest and largest single win, up to 14% on closed
#      models.  A phone stores the sensor's raw frame plus a rotation tag; a reader that
#      ignores the tag hands the model a sideways table.
#   2. Downscale to ~1568 on the long side with ``INTER_AREA``, and NEVER up.
#   3. Crop to the sheet, and correct perspective ONLY when the quadrilateral is visibly
#      not rectangular.  Geometry AFTER the resize: ten times cheaper on a small image.
#   4. JPEG quality 90.
#
# Tone is not touched at all.  The only tone operation the benchmark clears is
# autocontrast, at 0,0 -- harmless, not helpful -- and this pipeline does not spend a
# millisecond on an operation whose measured gain is zero.
#
# 🔴 NO PER-ROW SLICING.  The only direct measurement on handwritten tabular records:
# CER 64 with per-row slicing against 1,21 on the whole scan.  A strip without context
# invents, and it costs triple the tokens.  The whole sheet goes in one image.

import hashlib  # noqa: E402  -- kept beside the section that uses it
from dataclasses import dataclass  # noqa: E402
from typing import Sequence, Tuple  # noqa: E402

#: ``getFile`` gives at most 20 MB.  The asymmetry is Telegram's and it surprises
#: everyone once: the bot may SEND 50 MB and may DOWNLOAD only 20.  A file over this is
#: refused with a sentence, not with a traceback out of an HTTP layer.
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024

#: The long side the image is reduced to.  Chosen to sit at the tile boundary the closed
#: models bill and reason over; going higher costs tokens and buys nothing, going lower
#: loses the tick inside a box.
TARGET_LONG_SIDE = 1568

#: JPEG quality of the outgoing image.  Above this the file grows without the model
#: seeing more; below it, the thin pen stroke of a tick starts to dissolve into the
#: printed rule of the box it sits in.
JPEG_QUALITY = 90

#: How far from a rectangle the detected sheet has to be before it is worth warping.
#: Perspective correction on an already-rectangular crop is a resample for nothing --
#: pure loss, no gain -- so it is gated rather than always applied.
SKEW_TOLERANCE = 0.06

#: Every operation the benchmark measured a loss on, with that loss, so the number is
#: visible at the point where somebody would be tempted to add the operation back.
#: ``prepare`` records what it did, and the guard refuses a step log naming any of these.
FORBIDDEN_OPERATIONS = {
    "upscale": "up to 34 pp -- the worst operation in the entire benchmark",
    "greyscale": "3,2 pp",
    "binarise": "destroys the pen stroke the tick is made of",
    "equalise": "3,5 pp",
    "invert": "10,1 pp",
    "denoise": "blur is the worst measured degradation, and 3,4 s on top",
    "slice_rows": "CER 64 with per-row slicing against 1,21 on the whole scan",
}


class IntakeRefused(Exception):
    """The photo cannot be taken in at all, and the teacher is told why in one sentence."""


class PreprocessingViolation(Exception):
    """The pipeline recorded an operation the benchmark forbids.

    Raised rather than logged: an image that has been upscaled is worth up to 34 points
    of accuracy less than the same image untouched, and shipping it would mean asking a
    teacher to correct rows that a correct pipeline would never have got wrong.
    """


@dataclass(frozen=True)
class Prepared:
    """The image as it will leave this machine, and an account of what was done to it.

    ``sha256`` is over the DOWNLOADED bytes, never over ``jpeg``: it is the idempotency
    key of the whole flow (§8), and it has to identify the photograph the teacher sent
    rather than the output of whatever this pipeline happened to do to it this time.  A
    change to ``TARGET_LONG_SIDE`` must not make yesterday's photo a new photo.
    """

    jpeg: bytes
    sha256: str
    width: int
    height: int
    #: What was actually done, in order.  Auditable from outside: the test asserts on
    #: this list rather than on pixels, so «we did not upscale» is a checkable claim.
    steps: Tuple[str, ...]

    @property
    def long_side(self) -> int:
        return max(self.width, self.height)


def sha256_of(data: bytes) -> str:
    """The idempotency key of a photo: SHA-256 of its BYTES.

    NOT ``file_unique_id``.  Telegram's guarantee for that field is worded «is supposed
    to be the same», which is a hope rather than a contract, and the failure it permits
    is the expensive one: the same sheet recorded twice, silently, into an append-only
    journal.  A hash of the bytes is the only key that survives both a process restart
    and a re-delivered update, because it depends on nothing the process remembers.
    """
    return hashlib.sha256(data).hexdigest()


def choose_photo_size(sizes: Sequence, *, limit: int = MAX_DOWNLOAD_BYTES):
    """The largest of Telegram's offered sizes that ``getFile`` can actually fetch.

    A photo arrives as an ARRAY of sizes, not as a file.  The ceiling is 2560 px on the
    long side when the sender had the HD toggle on and 1280 otherwise; compression is
    always client-side, so the original does not exist anywhere and asking for it is not
    an option.  Largest-that-fits, and ``None`` when even the smallest is over the limit.
    """
    fitting = [
        size for size in sizes
        if (getattr(size, "file_size", None) or 0) <= limit
    ]
    if not fitting:
        return None
    return max(fitting, key=lambda size: (getattr(size, "width", 0) or 0) * (getattr(size, "height", 0) or 0))


def refuse_if_too_large(size_bytes: int) -> None:
    """The 20 MB gate, stated once so that both the photo path and the document path use
    the same number and the same sentence."""
    if size_bytes > MAX_DOWNLOAD_BYTES:
        raise IntakeRefused(
            "файл %.1f МБ — Telegram отдаёт боту не больше %d МБ; "
            "пришлите фото, а не файл, или снимите ближе"
            % (size_bytes / 1024 / 1024, MAX_DOWNLOAD_BYTES // 1024 // 1024)
        )


def _guard(steps) -> Tuple[str, ...]:
    """Refuse a step log that names a forbidden operation.

    The guard exists because the prohibitions are the largest lever in this file and an
    absence cannot be tested.  A future edit that adds ``cv2.cvtColor(..., GRAY)`` and
    records it honestly goes red here; one that adds it and records nothing is caught by
    the test that asserts on the exact expected step list.
    """
    for step in steps:
        head = step.split(":", 1)[0]
        if head in FORBIDDEN_OPERATIONS:
            raise PreprocessingViolation(
                "preprocessing recorded %r, which the benchmark measures at %s"
                % (step, FORBIDDEN_OPERATIONS[head])
            )
    return tuple(steps)


def prepare(raw: bytes) -> Prepared:
    """Bytes in, the JPEG that leaves this machine out.  ~230-250 ms for the whole thing.

    Every step is recorded in ``Prepared.steps`` including the ones that decided NOT to
    act -- ``resize:skipped-already-small`` and ``perspective:skipped-rectangular`` are
    the two decisions this pipeline most needs to be able to prove it made.
    """
    import io

    import numpy
    from PIL import Image, ImageOps

    refuse_if_too_large(len(raw))
    digest = sha256_of(raw)
    steps = []

    try:
        image = Image.open(io.BytesIO(raw))
    except Exception as error:  # a corrupt upload is an expected input, not a crash
        raise IntakeRefused("не смог открыть изображение: %s" % error)

    # 1. EXIF.  First, and it is the biggest single win in the whole pipeline: the phone
    #    stored a sideways frame plus a tag, and a reader that ignores the tag hands the
    #    model a table rotated ninety degrees.
    before = image.size
    image = ImageOps.exif_transpose(image)
    steps.append("exif:%s" % ("rotated" if image.size != before else "already-upright"))

    image = image.convert("RGB")  # a colour space, not a greyscale conversion
    frame = numpy.asarray(image)[:, :, ::-1]  # PIL is RGB, OpenCV is BGR

    # 2. Downscale, and NEVER up.  ``INTER_AREA`` is the correct kernel for shrinking --
    #    it averages the source pixels a destination pixel covers, which is exactly what
    #    keeps a one-pixel pen stroke visible instead of aliasing it away.
    frame, resize_step = _downscale(frame)
    steps.append(resize_step)

    # 3. Geometry AFTER the resize: ten times cheaper on a small image, and the crop is
    #    the same crop.  Perspective is corrected only when the sheet is visibly not
    #    rectangular; on an already-square crop a warp is a resample for nothing.
    frame, geometry_steps = _crop_to_sheet(frame)
    steps.extend(geometry_steps)

    # 4. Out.  Quality 90, and no tone operation at all: the only one the benchmark
    #    clears is autocontrast at 0,0, which is permission rather than a reason.
    height, width = frame.shape[:2]
    jpeg = _encode(frame)
    steps.append("jpeg:q%d" % JPEG_QUALITY)

    return Prepared(
        jpeg=jpeg,
        sha256=digest,
        width=width,
        height=height,
        steps=_guard(steps),
    )


def _cv2():
    """OpenCV, imported at the moment of use.

    A module-level import would make ``pytest`` fail to COLLECT the whole suite on a
    machine without OpenCV, turning a missing optional dependency into «every test in the
    project is broken».
    """
    try:
        import cv2
    except ImportError as error:  # pragma: no cover -- installed on every machine here
        raise IntakeRefused(
            "для разбора фото нужен OpenCV: python3 -m pip install --user opencv-python-headless (%s)"
            % error
        )
    return cv2


def _downscale(frame):
    """Reduce the long side to ``TARGET_LONG_SIDE``.  Returns ``(frame, step)``.

    The branch that does nothing is the important one.  An image already smaller than the
    target is LEFT ALONE: enlarging it to hit a round number is the single worst thing
    this pipeline could do, and it is exactly the thing that feels like an improvement.
    """
    cv2 = _cv2()
    height, width = frame.shape[:2]
    long_side = max(height, width)
    if long_side <= TARGET_LONG_SIDE:
        return frame, "resize:skipped-already-small(%dx%d)" % (width, height)
    scale = TARGET_LONG_SIDE / float(long_side)
    resized = cv2.resize(
        frame,
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )
    return resized, "resize:INTER_AREA(%dx%d->%dx%d)" % (
        width, height, resized.shape[1], resized.shape[0],
    )


def _sheet_quad(frame):
    """The four corners of the sheet in the frame, or ``None`` when it is not found.

    Edges rather than thresholds: a white sheet on a white desk has no threshold that
    separates them, but it always has a boundary.  ``None`` is a perfectly good answer --
    the frame is then used whole, which is what the model would have seen anyway.
    """
    cv2 = _cv2()
    import numpy

    # A single-channel edge map is not a greyscale CONVERSION of the outgoing image: the
    # picture that leaves this machine stays colour.  This is a measurement made on the
    # way to a crop rectangle and thrown away.
    edges = cv2.Canny(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 60, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    frame_area = frame.shape[0] * frame.shape[1]
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 0.25 * frame_area:
        return None  # too small to be the sheet; cropping to it would throw away rows
    approximated = cv2.approxPolyDP(largest, 0.02 * cv2.arcLength(largest, True), True)
    if len(approximated) != 4:
        return None
    return numpy.array([point[0] for point in approximated], dtype="float32")


def _ordered(quad):
    """Corners as top-left, top-right, bottom-right, bottom-left."""
    import numpy

    total = quad.sum(axis=1)
    diff = numpy.diff(quad, axis=1).ravel()
    return numpy.array(
        [quad[numpy.argmin(total)], quad[numpy.argmin(diff)],
         quad[numpy.argmax(total)], quad[numpy.argmax(diff)]],
        dtype="float32",
    )


def _skew_of(quad) -> float:
    """How far from a rectangle, as a fraction: opposite sides that disagree in length.

    A photograph taken from straight above gives a quadrilateral whose opposite sides are
    equal; tilt makes the near edge longer than the far one, and this is that difference
    normalised by the larger of the two.
    """
    import numpy

    corners = _ordered(quad)
    def side(a, b):
        return float(numpy.linalg.norm(corners[a] - corners[b]))
    pairs = ((side(0, 1), side(3, 2)), (side(0, 3), side(1, 2)))
    return max(
        abs(first - second) / max(first, second, 1.0) for first, second in pairs
    )


def _crop_to_sheet(frame):
    """Crop to the detected sheet, warping only when it is visibly not rectangular."""
    cv2 = _cv2()
    import numpy

    quad = _sheet_quad(frame)
    if quad is None:
        return frame, ["crop:skipped-sheet-not-found"]

    corners = _ordered(quad)
    skew = _skew_of(quad)
    if skew <= SKEW_TOLERANCE:
        x, y, w, h = cv2.boundingRect(corners.astype("int32"))
        cropped = frame[max(0, y):y + h, max(0, x):x + w]
        if cropped.size == 0:
            return frame, ["crop:skipped-empty-rect"]
        return cropped, [
            "crop:bounding-rect(%dx%d)" % (cropped.shape[1], cropped.shape[0]),
            "perspective:skipped-rectangular(skew=%.3f)" % skew,
        ]

    width = int(max(
        numpy.linalg.norm(corners[0] - corners[1]), numpy.linalg.norm(corners[3] - corners[2])
    ))
    height = int(max(
        numpy.linalg.norm(corners[0] - corners[3]), numpy.linalg.norm(corners[1] - corners[2])
    ))
    if width < 2 or height < 2:
        return frame, ["crop:skipped-degenerate-quad"]

    # 🔴 The warp is never allowed to enlarge.  A steeply tilted sheet has a far edge much
    # shorter than the near one, and squaring it up to the LONGER edge is an upscale
    # wearing a geometry costume -- the worst operation in the benchmark, arriving by a
    # door the resize guard does not watch.
    source_long = max(frame.shape[0], frame.shape[1])
    if max(width, height) > source_long:
        scale = source_long / float(max(width, height))
        width, height = max(2, int(width * scale)), max(2, int(height * scale))

    target = numpy.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32"
    )
    warped = cv2.warpPerspective(
        frame, cv2.getPerspectiveTransform(corners, target), (width, height),
        flags=cv2.INTER_AREA,
    )
    return warped, ["perspective:corrected(skew=%.3f,%dx%d)" % (skew, width, height)]


def _encode(frame) -> bytes:
    cv2 = _cv2()
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not ok:  # pragma: no cover -- imencode fails only on a malformed array
        raise IntakeRefused("не смог закодировать изображение в JPEG")
    return buffer.tobytes()
