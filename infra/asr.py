"""The adapter to a speech recogniser.  One Protocol, one fake, one real client.

WHY THIS FILE IS SHAPED LIKE THIS — three traps, all measured before a line was written.

**1 · The audio does not go into a multimodal model in one call.**  On twenty-to-thirty
second dictations a quarter of such calls ANSWER the audio instead of transcribing it —
they hear «Петров три пять семь бэ» and reply about Петров.  Worse, and aimed straight at
this design: putting fifty-six surnames into the prompt of an audio model measurably
biases it towards the text and away from what it actually heard, which is the one thing
we needed it to report.  So recognition is a TRANSCRIPTION call and nothing else, and the
roster is applied afterwards, by ``core.services.golos``, where it can be argued with.

**2 · Whisper's ``initial_prompt`` is not a vocabulary mechanism.**  It is the context of
the previous fragment, capped at 224 tokens, and it has documented looping
hallucinations.  Feeding the roster through it would look like a user dictionary and
behave like a prompt injection into the decoder.

**3 · OpenAI does not accept ogg/opus.**  Telegram sends nothing else for a voice note,
so that route costs an ffmpeg dependency before it costs anything else.  Known in
advance, and the reason the client below speaks to an engine that takes the container as
it arrives.

WHAT IS ACTUALLY WIRED, AND WHAT IS HONESTLY NOT
------------------------------------------------
``YandexSpeechKitTranscriber`` is real and its request is asserted by tests that need no
key and no network: verbatim mode on, ``oggopus`` as the format, and NO sample rate in
the request at all.  What it does NOT carry is the user dictionary: on this project's own
reading, the phrase list lives on the v3 STREAMING api, which is gRPC and would cost a
dependency this repository does not have.  ``build_user_dictionary`` therefore exists,
is built from the catalogue and IS used — by the fuzzy channel in
``core.services.golos``, which is the same compensation applied one layer later and under
test.  The gap is named in the report rather than papered over.

⚠ A local alternative worth naming: **GigaAM-v3** measures 7,19 % WER on Russian against
Whisper large-v3's 15,44 %, and runs on four cores in five to eight seconds where Whisper
takes minutes.  It is not wired here because it is a model download rather than a key,
and this position had neither; it fits this Protocol without changing one line of it.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional, Sequence


class TranscriptionUnavailable(RuntimeError):
    """No recogniser could be reached, and the caller must say so rather than guess.

    A voice note that produced no transcript is a screen that says «не расслышал,
    повторите» — never an empty draft, which is indistinguishable from a dictation the
    teacher meant to be empty.
    """


# --------------------------------------------------------------------------- limits

#: Telegram's ``getFile`` ceiling.  Never a constraint for a voice note — a minute of
#: opus is tens of kilobytes — but it is the same door the photo path goes through, and a
#: forwarded audio FILE can reach it.
TELEGRAM_GETFILE_MAX_BYTES = 20 * 1024 * 1024

#: The synchronous recognition endpoint takes a short utterance and no more: one megabyte
#: and thirty seconds.  A longer dictation belongs on the streaming api, and the refusal
#: has to say which of the two limits it hit — a teacher who reads «слишком длинно» after
#: a twelve-second note learns nothing.
SHORT_AUDIO_MAX_BYTES = 1024 * 1024
SHORT_AUDIO_MAX_SECONDS = 30

#: How long we wait for the engine before telling the teacher to tap instead.  A voice
#: note that takes longer than this has already cost more than the buttons it replaces.
ASR_TIMEOUT_SECONDS = 20


# ------------------------------------------------------------------------- the fake

class FakeTranscriber:
    """A recogniser made of a dictionary, for tests and for a machine with no key.

    It is not a mock in the "assert it was called" sense: it is the same seam with a
    scripted engine behind it, so every test above this line exercises the real parsing,
    matching and confirmation path.  ``build_transcriber`` returns one of these when no
    key is configured, and SAYS SO — a silent fake in production would turn every
    dictation into the same canned line.
    """

    def __init__(
        self,
        script: Optional[dict] = None,
        *,
        default: Optional[str] = None,
        reason: str = "scripted",
    ) -> None:
        #: sha256-free: keyed by the raw bytes, because a test writes ``b"petrov"`` and
        #: wants ``"Петров три пять семь бэ"`` back without computing a digest first.
        #:
        #: HELD BY REFERENCE, not copied.  A fixture builds the fake once and the test
        #: that uses it adds its line afterwards; a defensive copy here would leave every
        #: such test talking to an engine that had already made up its mind, and the
        #: failure reads as «the recogniser heard nothing» rather than «the fake was
        #: snapshotted».
        self.script = script if script is not None else {}
        self.default = default
        self.reason = reason
        self.calls: list = []

    def transcribe(self, audio: bytes, *, mime_type: str = "audio/ogg") -> str:
        self.calls.append((audio, mime_type))
        if audio in self.script:
            return self.script[audio]
        if self.default is not None:
            return self.default
        raise TranscriptionUnavailable(
            "no transcript scripted for %d bytes of %s (fake reason: %s)"
            % (len(audio), mime_type, self.reason)
        )


# -------------------------------------------------------------------- the real client

class YandexSpeechKitTranscriber:
    """Synchronous recognition of one short utterance, over plain HTTP.

    ``urllib`` rather than a client library on purpose: the whole call is one POST of the
    audio bytes with the parameters in the query string, and a dependency for that would
    be a dependency to keep current forever.

    THE THREE THINGS THE REQUEST MUST GET RIGHT, each with a test:

    * ``raw_results=true`` — the engine writes numbers AS WORDS and leaves them alone.
      This is the verbatim mode the interview finalised.  With it off the engine returns
      digits it decided on, and «семь бэ» comes back as whatever its normaliser preferred;
      our own normaliser then has nothing to normalise and no way to tell that it was
      overruled.
    * ``format=oggopus`` and **NO sample rate at all.**  Android moved voice notes from
      16 to 48 kHz in March 2024 and older cached messages still exist in the wild, so a
      hardcoded rate is wrong for a message whose age nobody controls.  An ogg container
      carries its own rate; the parameter only exists for raw PCM, and sending it is how
      a project acquires a rate it then has to keep right.
    * The key travels in the ``Authorization`` header, never in the query string, which is
      what proxies and access logs record.
    """

    ENDPOINT = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        *,
        language: str = "ru-RU",
        phrases: Sequence[str] = (),
        endpoint: Optional[str] = None,
        timeout: int = ASR_TIMEOUT_SECONDS,
    ) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._language = language
        #: Kept, not sent.  See the module docstring: this endpoint has no phrase list,
        #: and holding the terms here is what lets the seam stay unchanged when the
        #: streaming client that CAN send them replaces this one.
        self.phrases = list(phrases)
        self._endpoint = endpoint or self.ENDPOINT
        self._timeout = timeout

    # ------------------------------------------------------------------ the request

    def build_request(self, audio: bytes, *, mime_type: str = "audio/ogg") -> tuple:
        """``(url, headers, body)``, computed and returned rather than sent.

        Split out so that the three properties above are assertable without a key, a
        network or a recorded cassette.  A test that can only check them by making the
        call checks them on a machine that has credentials, which is not this one.
        """
        if not audio:
            raise TranscriptionUnavailable("empty audio: nothing was recorded")
        if len(audio) > SHORT_AUDIO_MAX_BYTES:
            raise TranscriptionUnavailable(
                "%d bytes is over the %d this endpoint accepts (about %d seconds); a "
                "longer dictation needs the streaming api"
                % (len(audio), SHORT_AUDIO_MAX_BYTES, SHORT_AUDIO_MAX_SECONDS)
            )
        query = "&".join(
            [
                "topic=general",
                "lang=%s" % self._language,
                "folderId=%s" % self._folder_id,
                # The container carries its own sample rate.  Deliberately no
                # ``sampleRateHertz``: see the class docstring.
                "format=oggopus",
                # VERBATIM.  Numbers stay words and our own normaliser does the work.
                "raw_results=true",
            ]
        )
        headers = {
            "Authorization": "Api-Key %s" % self._api_key,
            "Content-Type": mime_type,
        }
        return "%s?%s" % (self._endpoint, query), headers, audio

    # -------------------------------------------------------------------- the call

    def transcribe(self, audio: bytes, *, mime_type: str = "audio/ogg") -> str:
        url, headers, body = self.build_request(audio, mime_type=mime_type)
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:  # pragma: no cover -- needs a key
            raise TranscriptionUnavailable(
                "recogniser answered %s: %s" % (error.code, error.reason)
            ) from error
        except (urllib.error.URLError, OSError, ValueError) as error:  # pragma: no cover
            raise TranscriptionUnavailable("recogniser unreachable: %s" % error) from error
        return self.read_result(payload)

    @staticmethod
    def read_result(payload: dict) -> str:
        """The transcript out of one answer, or a refusal naming what came back instead.

        An engine that answers 200 with ``{"error_code": ...}`` is the shape that turns
        into an empty draft if the body is trusted, and an empty draft is
        indistinguishable from a dictation the teacher meant to be empty.
        """
        if not isinstance(payload, dict):
            raise TranscriptionUnavailable("recogniser answered %r" % (payload,))
        if "result" not in payload:
            raise TranscriptionUnavailable(
                "recogniser answered without a result: %s"
                % json.dumps(payload, ensure_ascii=False)[:200]
            )
        text = (payload.get("result") or "").strip()
        if not text:
            raise TranscriptionUnavailable("recogniser heard nothing in this recording")
        return text


# ------------------------------------------------------------------------- the door

#: The two environment variables that decide whether recognition is real.  Named here
#: because they are the whole configuration of this adapter; they are NOT in ``config.py``
#: because they are secrets and that file is in git.
ASR_KEY_ENV = "SPETSMAT_ASR_KEY"
ASR_FOLDER_ENV = "SPETSMAT_ASR_FOLDER"


def build_transcriber(
    *, phrases: Sequence[str] = (), environ: Optional[dict] = None
) -> tuple:
    """``(transcriber, how)`` — the recogniser this machine can actually offer.

    Returns the fake, loudly, when no key is configured, and the second element of the
    tuple is the sentence the caller logs and the report quotes.  A fake that installed
    itself silently would answer every dictation with the same canned line and look
    exactly like a working bot.
    """
    environ = os.environ if environ is None else environ
    key = (environ.get(ASR_KEY_ENV) or "").strip()
    folder = (environ.get(ASR_FOLDER_ENV) or "").strip()
    if key and folder:
        return (
            YandexSpeechKitTranscriber(key, folder, phrases=phrases),
            # THE LINE A TEACHER READS ON A LESSON.  It says what happens, not what was
            # intended: «held» was literally true and read as «the dictionary works»,
            # which is how this gap survived unnoticed.  Pinned by
            # ``test_the_start_line_says_the_dictionary_never_leaves_this_process``.
            "speechkit, verbatim mode; NO DICTIONARY IN THE REQUEST: %d terms built, "
            "this engine takes no phrase list, recognition runs with no hint"
            % len(phrases),
        )
    missing = [
        name
        for name, value in ((ASR_KEY_ENV, key), (ASR_FOLDER_ENV, folder))
        if not value
    ]
    return (
        FakeTranscriber(reason="unset: %s" % ", ".join(missing)),
        "NO RECOGNISER: %s unset — voice notes will be refused, not guessed"
        % ", ".join(missing),
    )


# =============================================================================
#  THE SECOND CHANNEL'S ENVELOPE — P7's, opened here because ``core`` may not
# =============================================================================

def unfence(text: str) -> str:
    """Take the markdown fence off a model's JSON.  **P7's function, called.**

    It lives in ``infra/llm.py`` and it carries a measurement: on 02.09, on a live key, a
    model returned a perfectly valid ``{"rows": []}`` inside a ```` ```json ```` fence
    UNDER A STRICT SCHEMA, and the naive parser rejected it.  A bot that does not strip
    the fence drops valid answers and looks broken.

    The one-line wrapper exists because ``core/services/golos.py`` cannot reach
    ``infra/`` and therefore takes this as an argument.  Rewriting the three lines there
    would have been quicker and would have made a second home for that measurement: the
    next model that fences differently gets fixed in one of them.
    """
    from infra.llm import strip_fence

    return strip_fence(text)


def rows_from_schema_answer(answer: str) -> list:
    """A schema answer, whatever envelope it arrived in, as rows this screen can use."""
    from core.services.golos import parse_model_rows

    return parse_model_rows(answer, unfence=unfence)
