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

import logging
import re
from typing import Optional

#: Куда уходит то, что человеку читать незачем: имя класса исключения Python и
#: отсутствие библиотеки на сервере.
log = logging.getLogger(__name__)

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
#     ENLARGEMENT            up to 34 -- the worst operation in the entire benchmark
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

#: 🔴 THE BAND KEPT OUTSIDE THE DETECTED QUADRILATERAL, AS A FRACTION OF THE FRAME'S LONG
#: SIDE.  The detector looks for the SHEET; when the edge of the paper is not in the shot
#: -- and it is not, for anyone who moves in close enough to be legible -- the largest
#: quadrilateral in the frame is the RULED GRID itself, and the crop follows its lines.
#: The column of codes ``u1…u18`` and the row of task labels ``1а°…10и*`` are printed
#: OUTSIDE those lines, so both leave with the crop and the model is handed a bare grid:
#: it sees every tick, cannot say whose they are, and honestly refuses -- ``rows`` empty,
#: ``raw_text`` saying «в последней ВИДИМОЙ строке».
#:
#: MEASURED ON A REAL FORM (``tools/blank.py``, 2026-09-02), frame 1109x1568 after step 2,
#: found rectangle 956x560 at (149, 77) — that rectangle IS the grid:
#:
#:     needed on the left (codes)   102 px = 10,7 % of the found rect · 6,5 % of the frame
#:     needed above (task labels)    45 px =  8,0 %                    · 2,9 %
#:     needed below (the legend)     52 px =  9,3 %                    · 3,3 %
#:
#: 🔴 THE FRACTION IS OF THE FRAME, NOT OF THE FOUND RECTANGLE, and the measurement is
#: what forces that rather than taste: 8 % of the found rectangle is 76 px and loses the
#: codes, 8 % of the frame is 125 px and keeps all three.  A fraction of the rectangle is
#: also fragile in the direction that matters -- the same code column beside a shorter
#: sheet needs a LARGER share, because the rectangle shrinks with the label count while
#: the printed code column does not.  A fraction of the frame does not move with it.
#:
#: Not free and not pretending to be: when the paper edge IS in the shot the band is
#: background rather than text.  That is the cheap side of the trade -- a strip of desk
#: costs the model nothing, and it was the missing codes that cost it the whole answer.
SHEET_MARGIN = 0.08

#: Every operation the benchmark measured a loss on, with that loss, so the number is
#: visible at the point where somebody would be tempted to add the operation back.
#: ``prepare`` records what it did, and the guard refuses a step log naming any of these.
FORBIDDEN_OPERATIONS = {
    "enlarge": "34 pp at worst -- the single most damaging operation in the benchmark",
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

    Raised rather than logged: an image that has been enlarged is worth 34 points of
    accuracy less than the same image untouched, and shipping it would mean asking a
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
    #: this list rather than on pixels, so «nothing was enlarged» is a checkable claim.
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

    # 1. EXIF.  First, and it is the biggest single win in the whole pipeline: the phone
    #    stored a sideways frame plus a tag, and a reader that ignores the tag hands the
    #    model a table rotated ninety degrees.
    #
    #    THE DECODE IS INSIDE THIS GUARD, not only the open.  ``Image.open`` parses the
    #    HEADER and returns; the pixels are read later, so a truncated upload -- the most
    #    ordinary failure a phone on school wifi produces -- opened cleanly and then threw
    #    a bare ``OSError: image file is truncated`` out of ``exif_transpose``, past every
    #    ``except IntakeRefused`` in the router.  Found by the §3 verifier at 60% truncation.
    try:
        image = Image.open(io.BytesIO(raw))
        before = image.size
        image = ImageOps.exif_transpose(image)
        # ``convert`` forces the decode: a colour space, not a greyscale conversion.
        image = image.convert("RGB")
    except Exception as error:  # a corrupt upload is an expected input, not a crash
        # 🔴 ЗДЕСЬ ПЕЧАТАЛОСЬ `type(error).__name__` — имя класса исключения
        # Python («UnidentifiedImageError»), и его читал преподаватель. Отказ
        # показывается ДОСЛОВНО (`answer(str(refusal))` в `bot/routers/photo.py`),
        # так что имя класса доезжало до человека целиком.
        log.warning("не удалось раскодировать снимок: %r", error)
        raise IntakeRefused(
            "не смог прочитать этот снимок — пришлите фото заново, "
            "обычной камерой и без обрезки"
        )
    steps.append("exif:%s" % ("rotated" if image.size != before else "already-upright"))
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
        # 🔴 ЗДЕСЬ ЧЕЛОВЕКУ ПОКАЗЫВАЛИ КОМАНДУ УСТАНОВКИ ПАКЕТА. Отказ читает
        # преподаватель на занятии; поставить библиотеку на сервер он не может,
        # а сделать сейчас может ровно одно — отметить кнопками.
        log.error("на сервере нет OpenCV, разбор фото невозможен: %s", error)
        raise IntakeRefused(
            "разбор фото на сервере сейчас не работает — отметьте кнопками: /setka"
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


def _margin_px(frame) -> int:
    """``SHEET_MARGIN`` of the frame's long side, in whole pixels.

    One place, so that the rectangular branch and the warping branch cannot drift apart:
    the text that stands outside the detected quadrilateral is the same text whichever
    branch the photograph happens to take.
    """
    return int(round(SHEET_MARGIN * max(frame.shape[:2])))


def _grown_corners(corners, margin):
    """The four corners pushed OUTWARD by ``margin`` px along both edges meeting at each.

    An offset of the quadrilateral, not a scaling about its centre: scaling moves a
    corner by an amount that depends on how far it happens to sit from the middle, and
    the text this band exists to recover stands at a FIXED distance outside the lines.

    🔴 NOTHING IS CLAMPED TO THE FRAME HERE, AND THAT IS DELIBERATE.  The two callers
    need opposite things.  The rectangular branch takes a bounding box and slices it, and
    a numpy slice clamps to the array by itself -- an offset that runs off the edge
    simply stops there, per side, which is exactly right.  The warping branch feeds these
    four points to ``getPerspectiveTransform``, where moving ONE corner back inside would
    change the homography and map the sheet onto a quadrilateral it does not have -- a
    distortion no step log would show.  It would rather sample past the edge and get a
    black band, which is honest and carries no ticks.
    """
    import numpy

    def unit(vector):
        length = float(numpy.linalg.norm(vector))
        return vector / length if length > 1e-6 else numpy.zeros(2, dtype="float32")

    # TL away from TR and BL, TR away from TL and BR, and so on around the ring.
    neighbours = ((1, 3), (0, 2), (3, 1), (2, 0))
    directions = numpy.array(
        [unit(corners[i] - corners[a]) + unit(corners[i] - corners[b])
         for i, (a, b) in enumerate(neighbours)],
        dtype="float32",
    )
    return (corners + directions * float(margin)).astype("float32")


def _crop_to_sheet(frame):
    """Crop to the detected sheet, warping only when it is visibly not rectangular.

    🔴 AND IT KEEPS A BAND OUTSIDE THE QUADRILATERAL IT FOUND, WHICH IS THE POINT.  What
    the detector returns is «the largest four-sided thing in the frame», and that is the
    sheet only when the edge of the paper is in the shot.  Photograph the form close
    enough to read it -- which is what a teacher does -- and the largest quadrilateral is
    the RULED GRID.  Cropping to it drops the code column and the task labels, because
    they are printed outside the lines, and the model is then asked whose ticks these are
    with nothing on screen that could answer.  See ``SHEET_MARGIN`` for the measurement.
    """
    cv2 = _cv2()
    import numpy

    quad = _sheet_quad(frame)
    if quad is None:
        return frame, ["crop:skipped-sheet-not-found"]

    corners = _ordered(quad)
    skew = _skew_of(quad)
    margin = _margin_px(frame)
    corners = _grown_corners(corners, margin)
    if skew <= SKEW_TOLERANCE:
        x, y, w, h = cv2.boundingRect(corners.astype("int32"))
        # The slice clamps by itself, per side: a band that runs off the top of the frame
        # stops at the top and leaves the other three at full width.  A shared clamp --
        # one number reduced until every side fits -- was written here first and measured
        # WRONG on the very form this заход is about: the grid reaches 5 px from the right
        # edge of the frame, so a shared clamp cut the margin to 4 px on ALL FOUR sides
        # and left the codes outside exactly as before.
        cropped = frame[max(0, y):y + h, max(0, x):x + w]
        if cropped.size == 0:
            return frame, ["crop:skipped-empty-rect"]
        return cropped, [
            # The band is named in the step log with the same honesty as the neighbours:
            # a crop that silently kept a margin and one that silently did not look
            # identical from outside, and this line is what tells them apart.
            "crop:bounding-rect(%dx%d,margin=%dpx)"
            % (cropped.shape[1], cropped.shape[0], margin),
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
    # shorter than the near one, and squaring the sheet to its LONGER edge is an
    # enlargement wearing a geometry costume -- the most damaging operation in the
    # benchmark, arriving through a door the shrink guard does not watch.
    #
    # PER AXIS, and that is the whole correction.  This clamp used to compare only
    # ``max(width, height)`` against ``max(frame.shape)``, which lets a target that is
    # shorter on the long side and TALLER on the short one through untouched: the §3
    # verifier drove 1568x1045 -- the shape a real phone photo has after step 2 -- to
    # 1532x1213, 1,134 times the pixels, and found 1,218 times over random quads.  A
    # single-number comparison cannot express «no dimension grows»; two do.
    source_height, source_width = frame.shape[:2]
    scale = min(1.0, source_width / float(width), source_height / float(height))
    if scale < 1.0:
        width, height = max(2, int(width * scale)), max(2, int(height * scale))

    target = numpy.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32"
    )
    # 🔴 ``BORDER_REPLICATE`` BECAUSE THE BAND CAN REACH PAST THE FRAME, and here it may
    # not be clamped: the rectangular branch clamps per side because a bounding box has
    # sides, but these four points ARE the homography, and pulling one of them back
    # inside would map the sheet onto a quadrilateral it does not have.  So the warp
    # samples past the edge instead, and the question is only what it finds there.
    # Replicate rather than the default black: the pixel at the frame edge of a photo of
    # a sheet is paper or desk, and a smear of it reads as «nothing here», which is true.
    # A black wedge reads as an object.  Neither invents a tick, and that is the property
    # that matters -- but one of them invents an EDGE, and edges are what §2 detects on.
    warped = cv2.warpPerspective(
        frame, cv2.getPerspectiveTransform(corners, target), (width, height),
        flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE,
    )
    return warped, [
        "perspective:corrected(skew=%.3f,%dx%d,margin=%dpx)"
        % (skew, width, height, margin)
    ]


def _encode(frame) -> bytes:
    cv2 = _cv2()
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not ok:  # pragma: no cover -- imencode fails only on a malformed array
        # Показывается человеку дословно, поэтому говорит про снимок, а не
        # про кодек: «JPEG» преподавателю на занятии ничего не даёт.
        log.error("imencode отказал: кадр %r", getattr(frame, "shape", None))
        raise IntakeRefused(
            "не смог подготовить этот снимок — пришлите фото заново"
        )
    return buffer.tobytes()


# ================================================================================== §6
#
# CONFIDENCE FROM THE MODEL DOES NOT EXIST, SO IT IS COMPUTED HERE
#
# A numeric ``confidence`` field collapses to 0,9 and 1,0 and stays high while accuracy
# falls -- it measures fluency, not correctness.  Logprobs are unavailable as a substitute
# across all three providers.  So the number this pipeline acts on is computed on this
# machine, from the model's OWN verbatim transcription, which is why ``raw_text`` is first
# and required in the schema: it is a second channel, independent of the structured
# answer, and **disagreement between the two IS the signal «doubtful»**.
#
# 🔴 ``ratio``, NEVER ``token_set_ratio``.  The latter returns 100 on containment --
# «Иванов И.» against «Иванов» scores a perfect match -- so it cannot separate a student
# from that student's own initial-bearing neighbour, which is the single comparison this
# whole section exists to make.  ``tests/photo/test_confidence.py`` pins that example.
#
# ON AMBIGUITY THE ANSWER IS ``UNKNOWN``, NEVER A GUESS.  Two Petyas is not a hard case
# for a model -- it will pick one, immediately and confidently.  The row comes back with
# no student and a list of candidates, and the bot draws two buttons.
#
# 🔴 A PREMISE OF §6 IS NO LONGER TRUE ON THIS PROJECT, AND IT IS WORTH SAYING WHERE THE
# CODE CAN BE READ RATHER THAN ONLY IN A REPORT.  §6 describes expanding the fifty-six
# names across cases and matching them against ``raw_text``.  That was written before §4
# took the names off the sheet: on a form printed by ``tools/blank.py`` the transcription
# contains CODES, and there is nothing personal in it to match.  Both channels are
# therefore built and both are used, for the two inputs that really occur:
#
#   * ``score_code_agreement`` -- the live channel on a printed form.  The structured
#     answer says ``u17``; the transcription either shows ``u17`` or it does not.
#   * ``match_person`` over ``case_forms`` -- the channel §6 specifies, over text that
#     WAS typed or written by a person: the teacher's own correction, and a legacy sheet
#     printed before this change and still in a folder somewhere.  It runs entirely on
#     this machine, against a catalogue that never leaves it, which is the whole reason
#     the names may be involved at all.

#: The score below which the pipeline stops believing a row and shows it as doubtful.
#: 0,7 on a 0..1 scale, i.e. 70 on the 0..100 scale the metric is defined on.
CONFIDENCE_THRESHOLD = 0.7

#: What a row with no student resolved is called.  Not a magic string in the schema --
#: the closed list contains only real codes, so the model expresses «I cannot tell» by
#: omitting the row and filling ``alternatives``, and this is what the pipeline calls the
#: result on its own side.
UNKNOWN = "UNKNOWN"

#: Russian case endings, by the shape of the nominative.  A morphological analyser would
#: be better and is not worth a dependency here: this is a similarity CHANNEL, not a
#: parser, and a form it fails to generate costs a few points of score on a row that the
#: other channel already agrees about.
_CASE_RULES = (
    # (nominative ending, [endings that replace it])
    ("ова", ["ова", "овой", "ову", "овою"]),
    ("ева", ["ева", "евой", "еву", "евою"]),
    ("ина", ["ина", "иной", "ину", "иною"]),
    ("ская", ["ская", "ской", "скую", "скою"]),
    ("цкая", ["цкая", "цкой", "цкую", "цкою"]),
    ("ов", ["ов", "ова", "ову", "овым", "ове"]),
    ("ев", ["ев", "ева", "еву", "евым", "еве"]),
    ("ёв", ["ёв", "ёва", "ёву", "ёвым", "ёве"]),
    ("ин", ["ин", "ина", "ину", "иным", "ине"]),
    ("ын", ["ын", "ына", "ыну", "ыным", "ыне"]),
    ("ский", ["ский", "ского", "скому", "ским", "ском"]),
    ("цкий", ["цкий", "цкого", "цкому", "цким", "цком"]),
    ("ий", ["ий", "его", "ему", "им", "ем"]),
    ("ый", ["ый", "ого", "ому", "ым", "ом"]),
    ("я", ["я", "и", "е", "ю", "ей"]),
    ("а", ["а", "ы", "е", "у", "ой"]),
)

#: Endings that do not decline at all in Russian.  Generating five identical forms for
#: «Черных» or «Живаго» would inflate the form count without adding a single comparison.
_INDECLINABLE = ("о", "е", "у", "ы", "и", "их", "ых", "аго", "ко", "енко")


def ratio(first: str, second: str) -> float:
    """Normalised indel similarity, 0..100.  ``rapidfuzz.fuzz.ratio``, and nothing else.

    🔴 NOT ``token_set_ratio``: it returns 100 on containment, so «Иванов И.» against
    «Иванов» is a perfect match and the two cannot be told apart -- which is precisely
    the comparison this function exists to make.

    ``rapidfuzz`` is used when it is installed.  When it is not, the same metric is
    computed here: ``200 * LCS / (len(a) + len(b))`` IS the definition of ``fuzz.ratio``,
    so the fallback is the same number rather than a near-enough substitute, and the test
    asserts the two agree wherever both are available.  A vision pipeline that cannot run
    because a fuzzy-matching wheel is missing is a worse outcome than a slower one.
    """
    left, right = (first or "").strip().lower(), (second or "").strip().lower()
    if not left and not right:
        return 100.0
    if not left or not right:
        return 0.0
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return 200.0 * _lcs_length(left, right) / (len(left) + len(right))
    return float(fuzz.ratio(left, right))


def _lcs_length(left: str, right: str) -> int:
    """Longest common SUBSEQUENCE, in the two-row form: the metric needs a number, not
    the alignment, and a full table over a page of transcription is wasteful."""
    previous = [0] * (len(right) + 1)
    for left_char in left:
        current = [0]
        for index, right_char in enumerate(right):
            if left_char == right_char:
                current.append(previous[index] + 1)
            else:
                current.append(max(current[index], previous[index + 1]))
        previous = current
    return previous[-1]


def case_forms(word: str) -> tuple:
    """One name, and the forms it takes in a Russian sentence.

    A teacher writing «нет Петрова» and a teacher writing «Петров» mean the same child.
    Matching on the nominative alone misses every oblique case, and the miss is silent:
    the row simply looks doubtful and costs the teacher a tap.
    """
    word = (word or "").strip()
    if not word:
        return ()
    lowered = word.lower()
    if lowered.endswith(_INDECLINABLE):
        return (word,)
    for ending, replacements in _CASE_RULES:
        if lowered.endswith(ending) and len(lowered) > len(ending):
            stem = word[: len(word) - len(ending)]
            return tuple(dict.fromkeys(stem + form for form in replacements))
    # A bare consonant stem: Петров-style declension without the -ов.
    return tuple(dict.fromkeys(word + form for form in ("", "а", "у", "ом", "е")))


def roster_forms(students) -> dict:
    """``{form -> student_id}`` over the whole roster, cases and initials included.

    THIS DICTIONARY NEVER LEAVES THIS MACHINE.  It is the local half of §4: the model is
    handed codes, the person is recognised here, and the two are joined by a table that
    exists only in this process.
    """
    forms = {}
    for student in students:
        for form in case_forms(student.surname):
            forms.setdefault(form.lower(), student.id)
        # The given name in its own cases as well.  In this school a teacher writes
        # «Ирина» as readily as «Агаркова», and a channel that only knows surnames marks
        # every first-name correction doubtful -- a tap each, every lesson, forever.
        for form in case_forms(student.name):
            forms.setdefault(form.lower(), student.id)
        initial = (student.name or "")[:1]
        if initial:
            forms.setdefault(("%s %s." % (student.surname, initial)).lower(), student.id)
            forms.setdefault(("%s. %s" % (initial, student.surname)).lower(), student.id)
    return forms


def match_person(text: str, forms: dict):
    """Best (student_id, score 0..1) for a piece of human-written text, or ``(None, 0)``.

    Whole-string similarity against every known form.  Ambiguity is NOT resolved here:
    two forms within a hair of each other come back as the better one plus a score the
    caller can see is not decisive, and the caller turns that into two buttons.
    """
    best_id, best_score = None, 0.0
    for form, student_id in forms.items():
        score = ratio(text, form) / 100.0
        if score > best_score:
            best_id, best_score = student_id, score
    return best_id, best_score


def score_code_agreement(code: str, raw_text: str) -> float:
    """0..1: does the model's own transcription contain the code its answer names?

    The live channel on a printed form.  ``raw_text`` is produced BEFORE the structured
    answer -- that is what putting it first in the schema buys -- so the two are as close
    to independent as anything obtainable from one call, and their disagreement is the
    only honest doubt signal available.
    """
    if not code:
        return 0.0
    tokens = re.findall(r"[A-Za-zА-Яа-я]+[0-9]+", raw_text or "")
    if not tokens:
        return 0.0
    return max(ratio(code, token) for token in tokens) / 100.0


@dataclass(frozen=True)
class DraftRow:
    """One row of the confirmation table, before a human has looked at it.

    ``state`` is the only thing the screen needs to decide how to draw the row, and it is
    computed here rather than in the router so that the rule has one home.
    """

    code: Optional[str]
    student_id: Optional[int]
    solved: tuple
    #: ``confident`` · ``doubtful`` · ``UNKNOWN``.
    state: str
    score: float = 0.0
    #: Student ids the model could not choose between.  The bot draws one button each.
    alternatives: tuple = ()
    #: 🔴 THE CELLS THE FORM SAYS WERE TAKEN BACK -- «Снято — прочерк» in the legend the
    #: owner printed.  A SEPARATE tuple, and never merged into ``solved``: a dash and a
    #: tick are different facts, the journal counts them differently
    #: (``CellState.RETRACTED`` is not credited and is not a debt), and merging them was
    #: the defect this field exists to close.  Empty on every answer that carries no
    #: dash, which is most of them.
    retracted: tuple = ()

    @property
    def needs_a_human(self) -> bool:
        return self.state != "confident"


def rows_from_answer(answer, known_student_ids) -> tuple:
    """The model's answer, turned into confirmation-table rows with OUR confidence.

    Four outcomes, and the last two are the point:

      * a code that resolves and agrees with the transcription -> ``confident``;
      * a code that resolves and does NOT agree -> ``doubtful``, the teacher checks it;
      * a code naming a student the catalogue does not have -> ``UNKNOWN``.  The closed
        list makes this nearly unreachable, and «nearly» is why it is handled;
      * a row the model would not commit to, carrying ``alternatives`` -> ``UNKNOWN``
        with the candidates, drawn as one button each.

    🔴 AND THE THIRD STATE OF A CELL TRAVELS BESIDE THE FIRST.  ``solved`` and
    ``retracted`` are two tuples on the same row and are never added together here: the
    form's legend names three states, the journal has counted three for a year, and the
    one place they were collapsed into two was the schema this function reads.

    Nothing here writes anything.  The whole table goes to a human first.
    """
    known = set(known_student_ids)
    rows = []
    for row in getattr(answer, "rows", ()) or ():
        code = row.get("student_code")
        student_id = student_id_from_code(code) if code else None
        alternatives = tuple(
            candidate
            for candidate in (
                student_id_from_code(value) for value in row.get("alternatives") or ()
            )
            if candidate in known
        )
        solved = tuple(row.get("solved") or ())
        # The dash rides in its own tuple the whole way.  Read with ``.get`` and defaulted
        # to empty rather than required, because every answer built before the schema grew
        # this field -- a stored draft, a fixture, an older test -- must still parse.
        retracted = tuple(row.get("retracted") or ())

        if student_id is None or student_id not in known:
            rows.append(
                DraftRow(code=code, student_id=None, solved=solved, state=UNKNOWN,
                         score=0.0, alternatives=alternatives, retracted=retracted)
            )
            continue

        score = score_code_agreement(code, getattr(answer, "raw_text", ""))
        if alternatives or score < CONFIDENCE_THRESHOLD:
            state = UNKNOWN if alternatives else "doubtful"
        else:
            state = "confident"
        rows.append(
            DraftRow(code=code, student_id=student_id, solved=solved, state=state,
                     score=score, alternatives=alternatives, retracted=retracted)
        )
    return tuple(rows)
