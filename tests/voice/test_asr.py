"""The seam to the recogniser: the request it builds and the answers it refuses.

Every test here runs without a key, without a network and without a recorded cassette.
That is the point of ``build_request`` being a separate, pure method: the three
properties the request has to get right are the ones a machine with credentials would
otherwise be the only place to check, and this machine has none.
"""

from __future__ import annotations

import json

import pytest

from core.services.golos import (
    USER_DICTIONARY_MAX,
    build_user_dictionary,
    fold,
)
from infra.asr import (
    SHORT_AUDIO_MAX_BYTES,
    FakeTranscriber,
    TranscriptionUnavailable,
    YandexSpeechKitTranscriber,
    build_transcriber,
)


@pytest.fixture
def client():
    return YandexSpeechKitTranscriber("secret-key", "folder-1", phrases=["Петров"])


# ------------------------------------------------------- the three request properties

def test_the_request_asks_for_verbatim_mode(client):
    """«Smart» normalisation turns dictated digits into a lottery, and the digits are the
    whole payload.  ``rawResults=true`` is the switch that leaves them as words.

    THIS TEST WAS GREEN FOR THE WHOLE TIME THE SWITCH WAS OFF, and that is worth a
    sentence, because it is how the defect survived: it asserted the same misspelling
    the code made — ``raw_results``, the protobuf field name — so it compared the file
    to itself and never to the endpoint.  A test that copies its expectation out of the
    implementation cannot fail on a wrong implementation.  What settled it was a live
    call, not a green suite; the measurement is in
    ``test_the_verbatim_flag_is_spelled_the_way_the_http_endpoint_reads_it``.
    """
    url, _headers, _body = client.build_request(b"ogg-bytes")
    assert "rawResults=true" in url


def test_the_request_names_the_container_and_no_sample_rate(client):
    """Android moved voice notes from 16 to 48 kHz in March 2024 and older cached
    messages still exist in the wild.  The ogg container carries its own rate; a
    hardcoded one is wrong for a message whose age nobody controls."""
    url, _headers, _body = client.build_request(b"ogg-bytes")

    assert "format=oggopus" in url
    assert "samplerate" not in fold(url), "a sample rate reached the request: %s" % url
    assert "16000" not in url and "48000" not in url


def test_the_key_travels_in_the_header_and_never_in_the_query(client):
    """A query string is what proxies and access logs record."""
    url, headers, _body = client.build_request(b"ogg-bytes")

    assert headers["Authorization"] == "Api-Key secret-key"
    assert "secret-key" not in url


def test_the_audio_is_the_body_unchanged(client):
    """No transcoding, no re-containering: the bytes Telegram gave us are the bytes the
    engine hears.  Anything else is an ffmpeg dependency wearing a disguise."""
    _url, headers, body = client.build_request(b"ogg-bytes", mime_type="audio/ogg")

    assert body == b"ogg-bytes"
    assert headers["Content-Type"] == "audio/ogg"


# ------------------------------------------------------------------ the two refusals

def test_an_empty_recording_is_refused_rather_than_sent(client):
    with pytest.raises(TranscriptionUnavailable) as refusal:
        client.build_request(b"")
    assert "empty" in str(refusal.value)


def test_an_over_long_recording_says_which_limit_it_hit(client):
    """«слишком длинно» after a twelve-second note teaches a teacher nothing."""
    with pytest.raises(TranscriptionUnavailable) as refusal:
        client.build_request(b"x" * (SHORT_AUDIO_MAX_BYTES + 1))

    message = str(refusal.value)
    assert "streaming" in message
    assert str(SHORT_AUDIO_MAX_BYTES) in message


# ------------------------------------------------------------- reading the answer back

def test_a_transcript_is_read_out_of_a_normal_answer():
    assert YandexSpeechKitTranscriber.read_result(
        {"result": "Петров три пять семь бэ"}
    ) == "Петров три пять семь бэ"


@pytest.mark.parametrize(
    "payload",
    [
        {"error_code": "BAD_REQUEST", "error_message": "no folder"},
        {"result": ""},
        {"result": "   "},
        [],
    ],
)
def test_an_answer_with_no_words_in_it_is_a_refusal_and_not_an_empty_draft(payload):
    """An empty draft is indistinguishable from a dictation the teacher meant to be
    empty, so «heard nothing» must arrive as a refusal the screen can say out loud."""
    with pytest.raises(TranscriptionUnavailable):
        YandexSpeechKitTranscriber.read_result(payload)


def test_the_refusal_quotes_what_actually_came_back():
    """A 200 with an error body is the shape that becomes a silent empty draft."""
    with pytest.raises(TranscriptionUnavailable) as refusal:
        YandexSpeechKitTranscriber.read_result({"error_code": "BAD_FOLDER"})
    assert "BAD_FOLDER" in str(refusal.value)


# --------------------------------------------------------------------- the door

def test_with_no_key_the_door_hands_back_a_fake_and_says_so():
    """A fake that installed itself silently would answer every dictation with the same
    canned line and look exactly like a working bot."""
    transcriber, how = build_transcriber(environ={})

    assert isinstance(transcriber, FakeTranscriber)
    assert "NO RECOGNISER" in how
    assert "SPETSMAT_ASR_KEY" in how


def test_half_a_configuration_is_no_configuration():
    """A key without a folder cannot make a call; falling through to the real client
    would fail at the network instead of at the door."""
    transcriber, how = build_transcriber(environ={"SPETSMAT_ASR_KEY": "k"})

    assert isinstance(transcriber, FakeTranscriber)
    assert "SPETSMAT_ASR_FOLDER" in how


def test_with_a_key_the_door_hands_back_the_real_client_carrying_the_terms():
    transcriber, how = build_transcriber(
        phrases=["Петров", "Кахиани"],
        environ={"SPETSMAT_ASR_KEY": "k", "SPETSMAT_ASR_FOLDER": "f"},
    )

    assert isinstance(transcriber, YandexSpeechKitTranscriber)
    assert transcriber.phrases == ["Петров", "Кахиани"]
    assert "verbatim" in how


#: Wordings a teacher reads on a lesson as «the dictionary works».  The first of them
#: is the line this file shipped with: «held» is literally true — the terms ARE held, in
#: an attribute nobody reads — and false by implication, which is the class ``P18`` was
#: written for.  The owner read it as «словарь работает» and was wrong.
READS_AS_A_WORKING_DICTIONARY = (
    "terms held for the phrase list",
    "held for the phrase list",
    "with the phrase list",
    "dictionary sent",
)


def test_the_start_line_says_the_dictionary_never_leaves_this_process():
    """The fact and the sentence about the fact, asserted together in one test.

    Apart they rot apart: a line that describes a request is only honest while the
    request stays what it describes, and the request is one edit away at all times.
    """
    transcriber, how = build_transcriber(
        phrases=["Петров", "Кахиани", "7б"],
        environ={"SPETSMAT_ASR_KEY": "k", "SPETSMAT_ASR_FOLDER": "f"},
    )
    url, headers, body = transcriber.build_request(b"ogg-bytes")

    # THE FACT.  Nowhere in the request — not the query, not a header, not the body.
    carried = [
        term
        for term in transcriber.phrases
        if term in url or any(term in value for value in headers.values())
    ]
    assert carried == [], "terms reached the request after all: %s" % carried
    assert transcriber.phrases and b"".join(t.encode() for t in transcriber.phrases) not in body

    # THE SENTENCE.  It has to carry the fact, and it must not read as its opposite.
    assert "NO DICTIONARY IN THE REQUEST" in how, how
    for misleading in READS_AS_A_WORKING_DICTIONARY:
        assert misleading not in how, "the start line reads as a working dictionary: %s" % how
    assert str(len(transcriber.phrases)) in how, "the line does not say how many terms: %s" % how


def test_an_unreachable_engine_becomes_a_refusal_the_screen_can_say_out_loud():
    """The fallback the задача makes unconditional: a lesson outlives a recogniser.

    Port 1 on the loopback is closed on every machine, so this needs no network and no
    key.  What it pins is that the failure arrives as ``TranscriptionUnavailable`` —
    the one exception ``bot/routers/voice.py`` knows how to turn into «не расслышал,
    повторите» — and never as a raw ``URLError`` that reaches the teacher as a crash.
    """
    client = YandexSpeechKitTranscriber(
        "k", "f", endpoint="http://127.0.0.1:1/speech/v1/stt:recognize", timeout=2
    )

    with pytest.raises(TranscriptionUnavailable) as refusal:
        client.transcribe(b"ogg-bytes")
    assert "unreachable" in str(refusal.value)


def test_the_verbatim_flag_is_spelled_the_way_the_http_endpoint_reads_it():
    """The one word that decides whether «минус один» becomes -1 or 1.

    ``raw_results`` is the PROTOBUF field name — it is real, it is field 9 of v2's
    ``RecognitionSpec``, and it is why this spelling looks right.  The v1 HTTP endpoint
    this file talks to takes ``rawResults``, and an unknown query parameter is IGNORED,
    not refused: the wrong spelling returns 200 with a normalised transcript and no
    complaint anywhere.  Measured live on 02.09 with the owner's key, same audio,
    three calls differing only here:

        raw_results=true  -> «Санин с 3 по 6 - 1 петров 7 б 10 а»
        rawResults=true   -> «санин с третьей по шестую минус один петров семь б десять а»
        no parameter      -> «Санин с 3 по 6 - 1 петров 7 б 10 а»

    The first and the third are the same string: the flag was doing nothing.  The cost
    is a wrong mark — the sheet has problems -1..-5, dictated «минус один», and
    engine-side normalisation writes them «- 1» with a space, which
    ``core.services.golos.tokenise`` splits into an unrecognised «-» and the number 1.
    The teacher says problem -1 and the draft offers problem 1.
    """
    client = YandexSpeechKitTranscriber("k", "f")
    url, _, _ = client.build_request(b"ogg-bytes")

    assert "rawResults=true" in url, url
    # The protobuf spelling must not come back: it is silently ignored, so nothing
    # else in this suite would ever notice its return.
    assert "raw_results" not in url, "the ignored protobuf spelling is back: %s" % url


def test_the_fake_refuses_an_unscripted_recording_instead_of_inventing_one():
    fake = FakeTranscriber({b"a": "Петров три"})

    assert fake.transcribe(b"a") == "Петров три"
    with pytest.raises(TranscriptionUnavailable):
        fake.transcribe(b"b")


# ------------------------------------------------------------------ the dictionary

def test_the_dictionary_is_the_roster_plus_the_labels_and_is_built_from_the_seed():
    """101 terms is what this conduit needs: 56 surnames and the task labels.  Built from
    the catalogue so that a surname added in October needs no second edit anywhere."""
    terms = build_user_dictionary(["Петров", "Кахиани"], ["3", "7б"])
    assert terms == ["Петров", "Кахиани", "3", "7б"]


def test_the_dictionary_is_deduplicated_on_the_folded_form_and_keeps_its_order():
    """An engine that caches a dictionary by its hash re-uploads it on every start
    otherwise, forever."""
    assert build_user_dictionary(["Фёдоров", "Федоров", "", "  "]) == ["Фёдоров"]


def test_a_dictionary_over_the_engine_ceiling_is_refused_rather_than_truncated():
    """Silent truncation loses whichever surnames sorted last."""
    with pytest.raises(ValueError) as refusal:
        build_user_dictionary(["term-%d" % index for index in range(USER_DICTIONARY_MAX + 1)])
    assert str(USER_DICTIONARY_MAX) in str(refusal.value)
