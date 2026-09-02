"""§5 and §7: the settings that matter, and the failures that pretend to be something else.

Every failure here is produced WITHOUT a network.  That is not a convenience: a refusal
that arrives as HTTP 200, a 429 with the money gone and a timeout are precisely the three
things a test against a live endpoint cannot ask for on demand, which is why they survive
into production in the first place.  ``VisionModel`` takes its ``post`` as an argument so
that each of them can be handed over deliberately.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from infra.llm import (
    BadModelAnswer,
    DEFAULT_TIMEOUT_S,
    LlmTimeout,
    LlmTransportError,
    MAX_ATTEMPTS,
    ModelRefused,
    RateLimited,
    SpendLimitReached,
    VisionModel,
    build_prompt,
    build_schema,
    check_stop_reason,
    parse_answer,
    strip_fence,
)

CODES = ["u%d" % n for n in range(1, 57)]
LABELS = ["1", "2", "3а", "3б", "4", "5", "6", "7а", "7б", "8", "9", "10*", "11*"]


def envelope(content, **choice_extra):
    choice = {"message": {"content": content}, "finish_reason": "stop"}
    choice.update(choice_extra)
    return {"choices": [choice]}


def http_error(code, body, headers=None):
    return urllib.error.HTTPError(
        "https://example/api", code, "err", headers or {}, io.BytesIO(body.encode())
    )


def model(post, **kwargs):
    return VisionModel(api_key="k", post=post, sleep=lambda _s: None, **kwargs)


# ------------------------------------------------------------------ §5, the schema

def test_raw_text_is_first_and_required():
    """Required fields are emitted in schema ORDER, so the transcription comes first.

    The main quality loss under a schema comes from the instruction to format; it is
    cured by transcribing first and formatting second.  Order is the cure, so order is
    what the test pins.
    """
    schema = build_schema(CODES, LABELS)

    assert schema["required"][0] == "raw_text"
    assert list(schema["properties"])[0] == "raw_text"
    # And it survives serialisation -- the wire is where the order has to hold.
    assert json.dumps(schema).index('"raw_text"') < json.dumps(schema).index('"rows"')


def test_the_closed_list_is_split_across_two_fields_and_carries_codes_only():
    """Gemini's practical ceiling is ~120 values; 56 + 45 = 101 is on the edge of it.

    Two fields of 56 and 45 are comfortably inside, and neither of them names a child:
    handed a closed list of codes the model physically cannot invent a student who does
    not exist.
    """
    row = build_schema(CODES, LABELS)["properties"]["rows"]["items"]["properties"]

    students = row["student_code"]["enum"]
    tasks = row["solved"]["items"]["enum"]
    assert students == CODES and tasks == LABELS
    assert max(len(students), len(tasks)) < 120
    for value in students:
        assert value.startswith("u") and value[1:].isdigit()

    prompt = build_prompt(CODES, LABELS)
    assert "u17" in prompt
    assert "UNKNOWN" not in prompt  # ambiguity goes to `alternatives`, not to a magic word


def test_an_empty_closed_list_is_refused_rather_than_sent():
    """A schema with an empty enum asks the model for a value it cannot produce."""
    with pytest.raises(ValueError):
        build_schema([], LABELS)
    with pytest.raises(ValueError):
        build_schema(CODES, [])


def test_the_call_carries_zero_temperature_minimum_thinking_and_high_detail():
    """§5: at minimal reasoning the results are up to 75% better.

    High reasoning makes the model talk itself out of what it saw.  A grid of ticks is a
    perception task, and reasoning about it is a way to be wrong at length.
    """
    seen = {}

    def post(body):
        seen.update(body)
        return envelope(json.dumps({"raw_text": "x", "rows": []}))

    model(post).read_sheet(b"jpeg", CODES, LABELS)

    assert seen["temperature"] == 0
    assert seen["thinking_level"] == "minimum"
    assert seen["messages"][0]["content"][1]["image_url"]["detail"] == "high"
    assert seen["response_format"]["json_schema"]["strict"] is True


def test_the_timeout_is_seconds_and_the_ten_minute_shape_is_refused():
    """Google's SDK measures this in MILLISECONDS and has no timeout by default.

    The unit lives in the constant's name so a future adapter converts deliberately.  The
    bound refuses 600 outright: a handler hanging ten minutes is a dead bot to a teacher.
    """
    assert 30 <= DEFAULT_TIMEOUT_S <= 60
    with pytest.raises(ValueError):
        model(lambda body: envelope("{}"), timeout_s=600)


# --------------------------------------------------------- §7, class 1: HTTP 200 refusal

def test_a_refusal_is_http_200_and_is_caught_before_the_json_is_touched():
    """A refusal has a perfectly well-formed envelope and an empty body.

    Parsed body-first it becomes «модель вернула пустую таблицу», which a teacher reads
    as «на бланке ничего нет» and a developer reads as a working pipeline.  The stop
    reason is therefore checked BEFORE ``json.loads``.
    """
    with pytest.raises(ModelRefused):
        check_stop_reason(envelope("", finish_reason="content_filter"))
    with pytest.raises(ModelRefused):
        check_stop_reason({"choices": [{"message": {"refusal": "не могу"}}]})
    with pytest.raises(ModelRefused):
        check_stop_reason(envelope("   "))
    with pytest.raises(ModelRefused):
        check_stop_reason({"choices": []})


def test_the_refusal_test_can_go_red_if_the_code_takes_200_for_success():
    """The negative control the criterion asks for, in the shape it asks for.

    A pipeline that accepts HTTP 200 without looking at the stop reason would read a
    filtered response as an empty sheet.  This asserts on exactly that difference: a
    content-filtered envelope whose body IS valid JSON, which a body-first parser accepts
    happily.
    """
    filtered = envelope(json.dumps({"raw_text": "", "rows": []}), finish_reason="content_filter")

    # Body-first: valid, empty, and wrong.
    assert json.loads(filtered["choices"][0]["message"]["content"])["rows"] == []
    # Reason-first: refused.
    with pytest.raises(ModelRefused):
        parse_answer(filtered, LABELS, model="m", latency_s=0.0)


def test_a_refusal_is_not_retried():
    """Asking the same model the same question gets the same no, three times over."""
    calls = []

    def post(body):
        calls.append(1)
        return envelope("", finish_reason="content_filter")

    with pytest.raises(ModelRefused):
        model(post).read_sheet(b"jpeg", CODES, LABELS)
    assert len(calls) == 1


# ------------------------------------------- §7, class 2: 429 WITHOUT retry-after

def test_429_without_retry_after_is_a_spend_limit_and_is_never_retried():
    """A standard retry policy hammers a spend limit forever: nothing ever changes."""
    calls = []

    def post(body):
        calls.append(1)
        raise http_error(429, '{"error":"rate limit"}', headers={})

    with pytest.raises(SpendLimitReached):
        model(post).read_sheet(b"jpeg", CODES, LABELS)
    assert len(calls) == 1, "a spend limit was retried %d times" % len(calls)


def test_429_with_retry_after_is_a_different_failure_and_is_retried():
    """The fork §7 asks for: the header is the first test, the error text the second."""
    calls = []

    def post(body):
        calls.append(1)
        if len(calls) == 1:
            raise http_error(429, "slow down", headers={"retry-after": "1"})
        return envelope(json.dumps({"raw_text": "x", "rows": []}))

    answer = model(post).read_sheet(b"jpeg", CODES, LABELS)
    assert calls == [1, 1]
    assert answer.attempts == 2
    assert RateLimited("x", 1).transient and not SpendLimitReached("x").transient


def test_a_429_that_names_the_money_is_a_spend_limit_even_with_a_header():
    """Not every provider omits the header when it means «you are out of credit»."""
    def post(body):
        raise http_error(
            429, '{"error":"You exceeded your current quota"}', headers={"retry-after": "2"}
        )

    with pytest.raises(SpendLimitReached):
        model(post).read_sheet(b"jpeg", CODES, LABELS)


# --------------------------------------------------------------- §7, class 3: timeout

def test_a_timeout_is_retried_a_bounded_number_of_times_and_then_reported():
    """Bounded, and the bound is a teacher's patience, not a batch job's."""
    calls = []

    def post(body):
        calls.append(1)
        raise LlmTimeout("не ответила")

    with pytest.raises(LlmTimeout):
        model(post).read_sheet(b"jpeg", CODES, LABELS)
    assert len(calls) == MAX_ATTEMPTS == 3


def test_a_transient_transport_failure_recovers_on_the_second_attempt():
    calls = []

    def post(body):
        calls.append(1)
        if len(calls) == 1:
            raise LlmTransportError("500")
        return envelope(json.dumps({"raw_text": "ok", "rows": []}))

    assert model(post).read_sheet(b"jpeg", CODES, LABELS).attempts == 2


# ------------------------------------------------------ the markdown fence (§5, named)

def test_json_inside_a_markdown_fence_is_parsed_and_not_rejected():
    """🔴 NAMED TEST.  Measured on this project 2026-09-02 on a live key.

    ``minimax-m3`` returned a perfectly valid ``{"rows": []}`` inside ```` ```json ```` --
    UNDER A STRICT SCHEMA -- and the naive parser rejected it.  A bot that does not strip
    the fence drops valid answers and looks broken.
    """
    payload = {"raw_text": "u1 x x", "rows": [{"student_code": "u1", "solved": ["1", "2"]}]}

    fenced = "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False)
    answer = parse_answer(envelope(fenced), LABELS, model="m", latency_s=0.0)
    assert answer.rows[0]["solved"] == ["1", "2"]

    # The bare fence, the language-tagged fence and the unfenced body all parse.
    for body in ("```\n{}\n```", "```json\n{}\n```", "{}", "  ```JSON\n{}\n```  "):
        assert strip_fence(body) == "{}", body


def test_the_fence_test_can_go_red():
    """The negative control: a naive parser really does reject the measured answer."""
    fenced = '```json\n{"raw_text":"x","rows":[]}\n```'
    with pytest.raises(json.JSONDecodeError):
        json.loads(fenced)
    assert json.loads(strip_fence(fenced))["rows"] == []


# ------------------------------------------------------------- the label validation

def test_a_label_outside_the_closed_list_is_rejected_in_code_and_reported():
    """A schema is a request, not a guarantee — §5 says validate the label in code.

    Reported rather than silently dropped: a model inventing task «99» is a fact the
    teacher's confirmation table should be able to say out loud.
    """
    payload = {"raw_text": "x", "rows": [{"student_code": "u1", "solved": ["1", "99"]}]}
    answer = parse_answer(envelope(json.dumps(payload)), LABELS, model="m", latency_s=0.0)

    assert answer.rows[0]["solved"] == ["1"]
    assert answer.rejected_labels == ("99",)


def test_a_body_that_is_not_an_object_is_a_bad_answer_and_not_a_traceback():
    with pytest.raises(BadModelAnswer):
        parse_answer(envelope("[1, 2, 3]"), LABELS, model="m", latency_s=0.0)
    with pytest.raises(BadModelAnswer):
        parse_answer(envelope("not json at all"), LABELS, model="m", latency_s=0.0)
