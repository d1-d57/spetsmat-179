"""The one place this project speaks to a vision model, and the only place it speaks HTTP.

``core/`` decides what to send and what an answer means; this file gets the bytes there
and back.  That split is the same rule that keeps sqlite3 and the Telegram library out of
``core/`` -- and here it has a second edge: everything that can go wrong with an external
model goes wrong in this file, so there is exactly one place to look.

THE SETTINGS MATTER MORE THAN ALL THE PREPROCESSING (§5)
--------------------------------------------------------

``temperature=0``, image detail ``high``, and the counterintuitive one:
``thinking_level=minimum``.  At minimal reasoning the results are **up to 75% better**,
because high reasoning makes the model talk itself out of what it saw.  A grid of ticks
is a perception task, not a reasoning task, and reasoning about it is a way to be wrong
at length.

THE SCHEMA (§5)
---------------

``raw_text`` is FIRST and REQUIRED.  Required fields are emitted in schema order, so
putting the verbatim transcription first makes the model transcribe before it formats --
and the main quality loss under a schema comes precisely from the instruction to format,
cured by transcribing first and formatting second.  It also gives §6 a second,
INDEPENDENT channel to check the structured answer against.

🔴 **The enum is SPLIT ACROSS TWO FIELDS.**  Gemini's practical ceiling is about 120 enum
values; 56 students plus 45 tasks is 101, which is on the edge of it.  Two fields of 56
and 45 are comfortably inside.  The task label is validated in code as well, because a
schema is a request and not a guarantee.

🔴 **The closed list is CODES, never names.**  The model is handed `u17`, so it physically
cannot invent a child who does not exist, and the image it is looking at carries nothing
personal either.  See §4 of the brief and ``core/services/raspoznavanie``.

🔴 **A CELL HAS THREE STATES, NOT TWO, AND THE SCHEMA IS WHERE THE THIRD ONE WAS LOST.**
The form prints its own legend -- «Сдал — крестик в клетке. Снято — прочерк. Пусто — не
сдавал.» -- and the journal has counted all three for a year (735 ``retract`` events last
year).  The schema offered ``solved`` and nothing else, and the prompt asked for a row
with any МЕТКА; a dash is a метка, so «снято» came back as a hand-in.  That failure is
worse than an empty answer: an empty answer is a refusal a teacher SEES, and a plausible
wrong value is one they confirm without looking.  ``retracted`` is a third array over the
SAME 45 labels, and the ~120-value ceiling above is per FIELD rather than per schema --
``alternatives`` has been carrying a fourth copy of the 56 codes since P7, on the live key,
which is measurement rather than reassurance.

FAILURES THAT PRETEND TO BE SOMETHING ELSE (§7)
-----------------------------------------------

* **A model refusal and a content filter arrive as HTTP 200.**  The stop reason is
  checked BEFORE the JSON is touched, because a refusal has a perfectly well-formed
  envelope and an empty or apologetic body, and a parser reaching for ``rows`` first
  reports «модель вернула пустую таблицу» -- which reads as «на бланке ничего нет».
* **Spend-limit exhaustion arrives as 429 WITHOUT ``retry-after``.**  A standard retry
  hammers it forever.  The two 429s are distinguished by the presence of the header and
  by the error text, and only the transient one is retried.  Eternal retry is forbidden.
* **Google's SDK has no timeout and no retries by default** -- its documentation
  describes what you must switch on -- and its ``timeout`` is in **milliseconds**.  This
  module talks to an OpenAI-compatible endpoint over ``urllib`` where the timeout is in
  seconds, and the number is stated once, in ``DEFAULT_TIMEOUT_S``, so that a future
  Google adapter converts it explicitly instead of passing 45 and waiting 45 ms.
* **Timeout 30-60 s, never 600.**  A handler hanging ten minutes is a dead bot to a
  teacher standing in front of eighteen children.

🔴 **A MODEL WRAPS ITS JSON IN A MARKDOWN FENCE EVEN UNDER A STRICT SCHEMA.**  Measured on
this project 2026-09-02 on a live key: ``minimax-m3`` returned a perfectly valid
``{"rows": []}`` inside a fence and the naive parser rejected it.  ``strip_fence`` runs
before every parse.  A bot that skips it drops valid answers and looks broken.
"""

from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from dataclasses import dataclass, field
from typing import Optional, Sequence

#: Seconds.  Not milliseconds -- and the unit is spelled into the name because the one
#: SDK most likely to replace this transport measures the same setting in the other unit,
#: and the mistake is invisible: 45 becomes 45 ms and every call times out instantly.
DEFAULT_TIMEOUT_S = 45

#: How many times a TRANSIENT failure is retried.  Three, and not «until it works»: a
#: teacher is standing in front of a room, and a bot that keeps trying is a bot that
#: never answers.
MAX_ATTEMPTS = 3

#: Seconds between attempts, indexed by attempt.  Short, because the whole budget is one
#: teacher's patience rather than a batch job's.
BACKOFF_S = (1.0, 3.0)

#: The longest ``retry-after`` worth honouring inside a handler.  Beyond it the honest
#: answer is «попробуйте через минуту», not a handler asleep on the event loop.
MAX_RETRY_AFTER_S = 10

#: Substrings that identify the 429 that means «the money ran out», as opposed to the 429
#: that means «too fast, wait a moment».  Matched case-insensitively against the body.
#: This list is the distinguishing rule §7 asks for; the header is the other half.
SPEND_LIMIT_MARKERS = (
    "insufficient",
    "quota",
    "credit",
    "billing",
    "exceeded your current",
    "spend limit",
    "payment required",
)

#: Finish reasons that mean «the model did not answer», with the envelope of one that
#: did.  Checked BEFORE the body is parsed.
REFUSAL_REASONS = ("content_filter", "refusal", "safety", "recitation", "blocked")

DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "minimax/minimax-m3:free"

_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$")

#: The three states of a cell, in the owner's own words, exactly as ``tools/blank.py``
#: prints them under every grid.  Quoted into the prompt rather than paraphrased: the
#: paper the teacher is holding and the instruction the model is reading then say the
#: same sentence, and ``tests/photo/test_snyato.py`` goes red if the two ever differ by
#: a character.  ``tools/blank.py`` is outside this position's zone, so the link is
#: carried by a test rather than by an import -- but it IS carried.
CELL_LEGEND = "Сдал — крестик в клетке. Снято — прочерк. Пусто — не сдавал."


# --------------------------------------------------------------------------- failures

class LlmError(Exception):
    """Anything that stopped an answer from arriving.  Every subclass is user-visible."""

    #: Whether trying the same call again could plausibly succeed.  Consulted by the
    #: caller AND by the retry loop, so «do not hammer» is one fact, not two.
    transient = False


class LlmTimeout(LlmError):
    transient = True


class LlmTransportError(LlmError):
    """A network failure or a 5xx.  Worth one more attempt, not worth forever."""

    transient = True


class RateLimited(LlmError):
    """429 WITH a ``retry-after``: the provider is asking us to slow down."""

    transient = True

    def __init__(self, message: str, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SpendLimitReached(LlmError):
    """429 WITHOUT ``retry-after``: the money ran out.

    NOT transient, and that is the whole point of separating it.  Retrying this is the
    failure §7 names -- a standard retry policy hammers a spend limit forever, because
    nothing about the response ever changes.
    """

    transient = False


class ModelRefused(LlmError):
    """HTTP 200, and the model did not answer: a refusal or a content filter.

    Detected from the stop reason BEFORE the body is parsed.  An envelope that says
    ``content_filter`` and carries an empty ``rows`` is not an empty sheet.
    """


class BadModelAnswer(LlmError):
    """HTTP 200, a real answer, and it does not fit the schema this code can use."""


# ------------------------------------------------------------------------ the schema

def build_schema(codes: Sequence[str], labels: Sequence[str],
                 sheets: Optional[Sequence[str]] = None) -> dict:
    """The strict JSON schema, with ``raw_text`` first and the closed list split in two.

    ``codes`` and ``labels`` are the ONLY vocabularies the model may answer in.  Handed a
    closed list it physically cannot invent a student who does not exist -- which is a
    stronger guarantee than any instruction in a prompt, and it is the reason this
    function takes the catalogue's contents rather than a count.
    """
    if not codes:
        raise ValueError("the closed list of student codes is empty; nothing to ask about")
    if not labels:
        raise ValueError("the closed list of task labels is empty; nothing to ask about")
    schema = {
        "type": "object",
        "additionalProperties": False,
        # ORDER IS LOAD-BEARING: required fields are emitted in schema order, so the
        # verbatim transcription is produced before any formatting decision is made.
        "required": ["raw_text", "rows"],
        "properties": {
            "raw_text": {
                "type": "string",
                "description": "Дословная расшифровка бланка, как есть, без нормализации.",
            },
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["student_code", "solved"],
                    "properties": {
                        # Field one of the split enum: 56 values.
                        "student_code": {"type": "string", "enum": list(codes)},
                        # Field two: 45 values.  Together 101, which is on the edge of
                        # the ~120 practical ceiling; apart, each is comfortably inside.
                        "solved": {
                            "type": "array",
                            "items": {"type": "string", "enum": list(labels)},
                        },
                        # 🔴 THE THIRD STATE OF A CELL, AND THE SCHEMA IS WHERE IT WAS
                        # LOST.  The form's own legend names three: «Сдал — крестик в
                        # клетке. Снято — прочерк. Пусто — не сдавал.»  With only
                        # ``solved`` on offer and a prompt asking for any МЕТКА, a dash is
                        # a метка and there is nowhere else to put it, so «снято» arrived
                        # as a hand-in -- a plausible WRONG value, which a teacher
                        # confirms without looking, rather than a visible refusal.
                        # Measured 2026-09-02 against a live model: u5 carried a dash on
                        # 1а°, ``raw_text`` read «u5  -» correctly, and ``solved`` came
                        # back ``[1а°]``.  The model was right and the schema had no
                        # word for what it saw.  The same closed list as ``solved``:
                        # it is the same vocabulary of task labels, only the verb differs.
                        "retracted": {
                            "type": "array",
                            "items": {"type": "string", "enum": list(labels)},
                        },
                        "alternatives": {
                            "type": "array",
                            "items": {"type": "string", "enum": list(codes)},
                        },
                    },
                },
            },
        },
    }
    if sheets:
        # WHICH SHEET IS ON THE PAPER.  A third field, and a small one -- 18 values -- so
        # neither of the two big enums grows and §5's ~120 ceiling is untouched.
        #
        # It exists because the pipeline used to ASSUME the newest sheet.  The §3 verifier
        # photographed листок 12 while 13 was current and got nine marks written onto
        # листок 13's problem ids -- adjacent sheets share 2 to 11 labels -- with the other
        # thirty-five labels dropped without a word.  ``tools/blank.py`` prints «Листок N»
        # at the top of every form; nothing was reading it back.
        schema["properties"]["sheet_number"] = {
            "type": "string",
            "enum": list(sheets),
            "description": "Номер листка, напечатанный сверху бланка.",
        }
        schema["required"] = ["raw_text", "sheet_number", "rows"]
    return schema


def build_prompt(codes: Sequence[str], labels: Sequence[str],
                 sheets: Optional[Sequence[str]] = None) -> str:
    """What the model is told.  Codes and task labels — nothing about any child.

    ``UNKNOWN`` has no place in the closed list of codes, so ambiguity is expressed by
    OMITTING the row and listing the candidates in ``alternatives``: a row the pipeline
    then shows to the teacher as two buttons.  Never make a model guess between two
    similar rows -- asked to choose, it will, and it will be confident.

    🔴 THE THREE STATES ARE QUOTED VERBATIM FROM THE FORM'S OWN LEGEND, and the quotation
    is the point rather than the phrasing.  ``tools/blank.py`` prints «Сдал — крестик в
    клетке. Снято — прочерк. Пусто — не сдавал.» under every grid, the owner wrote that
    sentence, and the journal has known the third state for a year (735 ``retract``
    events).  A paraphrase here would be a second source of truth for a rule the paper
    already states -- and the two would drift the first time either was edited.
    """
    head = (
        "На фотографии печатный бланк приёма задач. Слева в каждой строке — КОД "
        "(например u17). Столбцы — номера задач.\n\n"
    )
    if sheets:
        head += (
            "Сверху на бланке напечатано «Листок N». Верни этот номер в sheet_number, "
            "ровно как он напечатан. Возможные номера: %s\n\n" % ", ".join(sheets)
        )
    return head + (
        "Коды строк: %s\n\n"
        "Номера задач: %s\n\n"
        "Сначала запиши в raw_text дословно всё, что видишь на бланке, как есть.\n\n"
        "У клетки ТРИ состояния, и они напечатаны на самом бланке внизу: «%s»\n"
        "  • крестик, галочка, любая закраска — задача СДАНА: её номер в solved;\n"
        "  • прочерк — тире, минус, чёрточка — задача СНЯТА: её номер в retracted. "
        "Это НЕ сдача. Прочерк в solved не кладут никогда;\n"
        "  • пустая клетка — не сдавал: её номер не идёт никуда.\n\n"
        "Верни строку, если в её клетках есть хоть одна пометка — крестик или прочерк. "
        "В строке могут быть и крестики, и прочерки одновременно.\n"
        "Если код строки прочитать нельзя или подходят несколько — НЕ УГАДЫВАЙ: не "
        "включай эту строку в rows, а перечисли подходящие коды в alternatives. "
        "Если пометок нет нигде, верни пустой список rows."
    ) % (", ".join(codes), ", ".join(labels), CELL_LEGEND)


# ------------------------------------------------------------------------- the answer

@dataclass(frozen=True)
class LlmAnswer:
    """What came back, after the envelope was checked and the fence was taken off."""

    raw_text: str
    rows: tuple
    model: str
    latency_s: float
    attempts: int = 1
    #: The sheet number the model read off the top of the form, or ``""`` when the caller
    #: did not ask.  The caller compares it with the sheet it THINKS is current.
    sheet_number: str = ""
    #: Task labels the model returned that are not on the sheet.  Reported, never dropped:
    #: a label that is not on this sheet is evidence about WHICH sheet the paper is.
    unknown_labels: tuple = field(default_factory=tuple)
    #: Labels the model returned that are not in the closed list.  A schema is a request,
    #: not a guarantee, so the label is validated in code and the strays are reported
    #: rather than silently dropped.
    rejected_labels: tuple = field(default_factory=tuple)


def strip_fence(text: str) -> str:
    """Take a markdown fence off a JSON body.

    🔴 Measured on this project 2026-09-02 on a live key: ``minimax-m3`` returned a
    perfectly valid ``{"rows": []}`` inside ```` ```json ... ``` ```` UNDER A STRICT
    SCHEMA, and the naive parser rejected it.  Models do this; the schema does not stop
    them.  A bot that does not strip the fence drops valid answers and looks broken.
    """
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = _FENCE.sub("", clean).strip()
    return clean


def check_stop_reason(payload: dict) -> None:
    """Refuse a 200 that is not an answer — BEFORE anything reaches ``json.loads``.

    A refusal and a content filter both arrive with a normal envelope and a body that is
    empty or apologetic.  Parsed body-first, that becomes «модель вернула пустую
    таблицу», which a teacher reads as «на бланке ничего нет» and a developer reads as a
    working pipeline.  Two lines, in the right ORDER, close the whole class.
    """
    choices = payload.get("choices") or []
    if not choices:
        raise ModelRefused("модель не вернула ни одного варианта ответа")
    choice = choices[0]
    message = choice.get("message") or {}
    if message.get("refusal"):
        raise ModelRefused("модель отказалась отвечать: %s" % message["refusal"])
    for key in ("finish_reason", "native_finish_reason", "stop_reason"):
        reason = (choice.get(key) or "")
        if isinstance(reason, str) and reason.lower() in REFUSAL_REASONS:
            raise ModelRefused("модель не ответила, причина остановки: %s" % reason)
    if not (message.get("content") or "").strip():
        raise ModelRefused("модель вернула пустой ответ (HTTP 200 без содержимого)")


def parse_answer(payload: dict, labels: Sequence[str], *, model: str, latency_s: float,
                 attempts: int = 1) -> LlmAnswer:
    """Envelope -> ``LlmAnswer``.  Stop reason first, fence second, JSON third."""
    check_stop_reason(payload)
    body = strip_fence(payload["choices"][0]["message"]["content"])
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as error:
        raise BadModelAnswer("ответ не разобрался как JSON: %s" % error)
    if not isinstance(parsed, dict):
        raise BadModelAnswer("ответ — не объект, а %s" % type(parsed).__name__)

    allowed = set(labels)
    rows, rejected = [], []
    for row in parsed.get("rows") or []:
        if not isinstance(row, dict):
            continue
        # A schema is a request, not a guarantee: the label is validated here too.
        solved = [label for label in (row.get("solved") or []) if label in allowed]
        rejected.extend(
            label for label in (row.get("solved") or []) if label not in allowed
        )
        # «Снято» travels in its own list from here to the draft and is never folded into
        # ``solved``: the two are different facts about the world, they are counted
        # differently by the journal (``CellState.RETRACTED`` is not credited and is not a
        # debt either), and folding them is exactly the defect this field was added for.
        retracted = [label for label in (row.get("retracted") or []) if label in allowed]
        rejected.extend(
            label for label in (row.get("retracted") or []) if label not in allowed
        )
        rows.append(
            {
                "student_code": row.get("student_code"),
                "solved": solved,
                "retracted": retracted,
                "alternatives": list(row.get("alternatives") or []),
            }
        )
    return LlmAnswer(
        raw_text=str(parsed.get("raw_text") or ""),
        rows=tuple(rows),
        model=model,
        latency_s=latency_s,
        attempts=attempts,
        sheet_number=str(parsed.get("sheet_number") or ""),
        unknown_labels=tuple(dict.fromkeys(rejected)),
        rejected_labels=tuple(rejected),
    )


# ----------------------------------------------------------------------- the transport

class VisionModel:
    """One OpenAI-compatible vision endpoint, with §5's settings and §7's failure map.

    ``post`` is injectable so that the failure tests can produce a 200-refusal, a 429
    without ``retry-after`` and a timeout without a network -- the three classes §7 says
    pretend to be something else, and therefore the three that a test over a real
    endpoint could never produce on demand.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        post=None,
        sleep=time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("нет ключа модели: смотрите tools/kluch.sh")
        if not 5 <= timeout_s <= 60:
            # 600 is the number this bound exists to refuse: a handler hanging ten
            # minutes is a dead bot to a teacher, and «no timeout» is worse still.
            raise ValueError("таймаут %s с вне 5..60 — см. §7" % timeout_s)
        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout_s = timeout_s
        self._post = post or self._http_post
        self._sleep = sleep

    # ------------------------------------------------------------------ the request

    def _body(self, jpeg: bytes, codes: Sequence[str], labels: Sequence[str],
              sheets: Optional[Sequence[str]] = None) -> dict:
        encoded = base64.b64encode(jpeg).decode()
        return {
            "model": self._model,
            # §5: zero temperature, and minimal reasoning -- up to 75% better, because
            # high reasoning makes the model talk itself out of what it saw.
            "temperature": 0,
            "thinking_level": "minimum",
            "reasoning": {"effort": "minimal"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": build_prompt(codes, labels, sheets)},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64,%s" % encoded,
                                # §5: the models that accept a detail hint read a grid of
                                # ticks far better at ``high``; the ones that do not,
                                # ignore it.
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "blank",
                    "strict": True,
                    "schema": build_schema(codes, labels, sheets),
                },
            },
        }

    def _http_post(self, body: dict) -> dict:
        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer %s" % self._api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            # Seconds here.  A Google adapter would have to multiply by 1000; the unit is
            # in the constant's NAME so that the conversion is a decision and not a bug.
            #
            # ``HTTPError`` is deliberately NOT caught here: it is a subclass of
            # ``URLError`` and would be swallowed by the branch below, so it is let
            # through to ``read_sheet``, which owns the 429 fork.
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                return json.loads(response.read())
        except urllib.error.URLError as error:
            if isinstance(error, urllib.error.HTTPError):
                raise
            if isinstance(error.reason, TimeoutError) or "timed out" in str(error.reason).lower():
                raise LlmTimeout("модель не ответила за %d с" % self._timeout_s)
            raise LlmTransportError("сеть недоступна: %s" % error.reason)
        except TimeoutError:
            raise LlmTimeout("модель не ответила за %d с" % self._timeout_s)

    # -------------------------------------------------------------------- the call

    def read_sheet(self, jpeg: bytes, codes: Sequence[str], labels: Sequence[str],
                   sheets: Optional[Sequence[str]] = None) -> LlmAnswer:
        """Send one prepared image and return the answer, or raise one of §7's failures.

        The retry loop retries TRANSIENT failures only, at most ``MAX_ATTEMPTS`` times.
        ``SpendLimitReached`` and ``ModelRefused`` are not transient and leave on the
        first attempt: retrying a spend limit is the eternal-retry failure §7 forbids,
        and retrying a refusal asks the same model the same question and gets the same
        no, three times, while a teacher waits.
        """
        body = self._body(jpeg, codes, labels, sheets)
        last: Optional[LlmError] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            started = time.perf_counter()
            try:
                payload = self._post(body)
            except (LlmError, urllib.error.HTTPError) as raised:
                # An ``HTTPError`` is classified HERE and not in the socket wrapper,
                # because the 429 fork is a property of the CALL rather than of the
                # transport that carried it: a future Google or Anthropic adapter raises
                # the same exception type and must land in the same fork, and a test that
                # hands over a 429 must reach the same code production does.
                error = raised if isinstance(raised, LlmError) else _classify_http_error(raised)
                last = error
                if not error.transient or attempt == MAX_ATTEMPTS:
                    raise error
                self._sleep(self._pause_before_next(error, attempt))
                continue
            return parse_answer(
                payload,
                labels,
                model=self._model,
                latency_s=time.perf_counter() - started,
                attempts=attempt,
            )
        raise last  # pragma: no cover -- the loop above always returns or raises

    def _pause_before_next(self, error: LlmError, attempt: int) -> float:
        """How long to wait, honouring a ``retry-after`` we are willing to sit through."""
        asked = getattr(error, "retry_after", None)
        if asked is not None and 0 < asked <= MAX_RETRY_AFTER_S:
            return float(asked)
        return BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)]


def _parse_retry_after(raw) -> Optional[float]:
    """``retry-after`` is EITHER a number of seconds OR an HTTP-date.  Both are legal.

    Reading only the number and treating a failure to parse as «no header» sends an
    ordinary rate limit down the spend-limit branch, and the teacher is then told the
    money ran out and stops using photo marking for the term over something that would
    have cleared in a minute.  Found by the §3 verifier on
    ``Wed, 02 Sep 2026 10:00:00 GMT``.
    """
    if not raw:
        return None
    text = str(raw).strip()
    try:
        return float(text)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def _classify_http_error(error) -> LlmError:
    """Turn an ``HTTPError`` into the failure it actually is.

    THE 429 FORK IS THE WHOLE FUNCTION.  With a ``retry-after`` it is «slow down» and one
    more attempt is right.  Without one it is a spend limit, nothing about the response
    will ever change, and a standard retry policy hammers it forever -- which is the
    failure §7 names.  The header is the first test and the error text is the second,
    because not every provider sends the header even when it means «slow down».
    """
    try:
        text = error.read().decode("utf-8", "replace")
    except Exception:  # pragma: no cover -- a body that cannot be read is still an error
        text = ""
    headers = getattr(error, "headers", None)
    retry_after = None
    if headers is not None:
        retry_after = _parse_retry_after(headers.get("retry-after") or headers.get("Retry-After"))

    if error.code == 429:
        lowered = text.lower()
        if retry_after is None or any(m in lowered for m in SPEND_LIMIT_MARKERS):
            return SpendLimitReached(
                "429 без retry-after — похоже, кончился лимит трат: %s" % text[:200]
            )
        return RateLimited("429, просят подождать %s с" % retry_after, retry_after)
    if error.code in (401, 403):
        return LlmError("модель отказала в доступе (%d): %s" % (error.code, text[:200]))
    if 500 <= error.code < 600:
        return LlmTransportError("модель ответила %d: %s" % (error.code, text[:200]))
    return LlmError("модель ответила %d: %s" % (error.code, text[:200]))
