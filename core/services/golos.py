"""Voice dictation, turned into a draft: «Петров три пять семь бэ» -> Петров · 3 · 5 · 7б.

Nothing here imports the bot framework and nothing here opens a database.  This module is
the half of the voice path that is OURS rather than the recogniser's, and it exists
because of one measured fact: **no speech recogniser has a Russian numeral normaliser.**
Every engine either hands back the words as spoken («семь бэ») or applies a "smart"
normalisation that guesses, and in this project the digits ARE the payload — a guess is a
wrong mark on a real child's row.  So the recogniser is asked for VERBATIM text and the
normalisation happens here, in code, under test, with a vocabulary that can be read and
extended by whoever comes next.

THE VOCABULARY IS DATA, NOT ``if``s.  It is the tables at the top of this file: word
forms to values, tens to values, dictated letter names to label letters, and the words
that open and close a range.  Adding «двадцать седьмая» is adding a string to a tuple; it
is not editing a parser.

WHAT THIS MODULE REFUSES TO DO
------------------------------
It never writes a mark.  It produces a DRAFT — rows of (student, problems) with a
verdict on each — and the draft reaches the journal only after a human has looked at the
confirmation table and confirmed it.  That is the third finalised point of the interview
and it has no exception.

It also never trusts a numeric ``confidence`` from a model.  Such a number collapses to
0,9/1,0 and stays high while accuracy falls, so there is no field for it here.  What
stands in its place is DISAGREEMENT BETWEEN TWO INDEPENDENT CHANNELS: the schema call and
a fuzzy match against the roster.  Two channels that agree are a strong signal precisely
because neither could see the other's answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, Sequence

from core.services import raspoznavanie


# =============================================================================
#  1 · THE VOCABULARY, AS DATA
# =============================================================================
#
# Forms are written out in full rather than derived from stems, and that is a decision
# with a reason: «три» and «тридцать» share a stem, «второй» and «вторник» share a stem,
# and a stem matcher gets both wrong in a way no reader of the table can see.  A full
# form is checkable by eye.
#
# Cases and genders are here because a teacher dictates «третью», not «три»: the задание
# names «третью и пятую» as the same thing as «три пять», and the only way that is true
# is if the table says so.

#: Spoken form -> value, for everything below twenty plus the round tens that never
#: combine.  Ordinals live beside cardinals because they mean the same problem.
NUMERAL_FORMS: dict[int, tuple[str, ...]] = {
    0: ("ноль", "нуль", "нулевая", "нулевую", "нулевой"),
    1: ("один", "одна", "одно", "первый", "первая", "первую", "первое", "первой",
        "первого", "первым"),
    2: ("два", "две", "второй", "вторая", "вторую", "второе", "второго", "вторым"),
    3: ("три", "третий", "третья", "третью", "третье", "третьей", "третьего", "третьим"),
    4: ("четыре", "четвертый", "четвёртый", "четвертая", "четвёртая", "четвертую",
        "четвёртую", "четвертой", "четвёртой", "четвертого", "четвёртого"),
    5: ("пять", "пятый", "пятая", "пятую", "пятой", "пятого", "пятым"),
    6: ("шесть", "шестой", "шестая", "шестую", "шестого", "шестым"),
    7: ("семь", "седьмой", "седьмая", "седьмую", "седьмого", "седьмым"),
    8: ("восемь", "восьмой", "восьмая", "восьмую", "восьмого", "восьмым"),
    9: ("девять", "девятый", "девятая", "девятую", "девятой", "девятого", "девятым"),
    10: ("десять", "десятый", "десятая", "десятую", "десятой", "десятого"),
    11: ("одиннадцать", "одиннадцатый", "одиннадцатая", "одиннадцатую", "одиннадцатой"),
    12: ("двенадцать", "двенадцатый", "двенадцатая", "двенадцатую", "двенадцатой"),
    13: ("тринадцать", "тринадцатый", "тринадцатая", "тринадцатую", "тринадцатой"),
    14: ("четырнадцать", "четырнадцатый", "четырнадцатая", "четырнадцатую",
         "четырнадцатой"),
    15: ("пятнадцать", "пятнадцатый", "пятнадцатая", "пятнадцатую", "пятнадцатой"),
    16: ("шестнадцать", "шестнадцатый", "шестнадцатая", "шестнадцатую", "шестнадцатой"),
    17: ("семнадцать", "семнадцатый", "семнадцатая", "семнадцатую", "семнадцатой"),
    18: ("восемнадцать", "восемнадцатый", "восемнадцатая", "восемнадцатую",
         "восемнадцатой"),
    19: ("девятнадцать", "девятнадцатый", "девятнадцатая", "девятнадцатую",
         "девятнадцатой"),
}

#: Spoken form -> value, for the tens that DO combine with a unit: «двадцать четыре» is
#: one problem, not two.  Kept apart from ``NUMERAL_FORMS`` because the composition rule
#: needs to know which token may swallow the next one.
TENS_FORMS: dict[int, tuple[str, ...]] = {
    20: ("двадцать", "двадцатый", "двадцатая", "двадцатую", "двадцатой"),
    30: ("тридцать", "тридцатый", "тридцатая", "тридцатую", "тридцатой"),
    40: ("сорок", "сороковой", "сороковая", "сороковую"),
    50: ("пятьдесят", "пятидесятый", "пятидесятая", "пятидесятую"),
    60: ("шестьдесят", "шестидесятый", "шестидесятая", "шестидесятую"),
    70: ("семьдесят", "семидесятый", "семидесятая", "семидесятую"),
    80: ("восемьдесят", "восьмидесятый", "восьмидесятая", "восьмидесятую"),
    90: ("девяносто", "девяностый", "девяностая", "девяностую"),
}

#: Dictated letter name -> the letter as it stands in a problem label.  **This is where
#: dictation actually lives**: `7б` is said «семь бэ», and an engine tuned for prose
#: writes down «бэ» because that is the sound it heard.
#:
#: Two absences are deliberate and each has a cost behind it:
#:
#:   * **«же» is not here.**  It is the commonest particle in the language — «три же»
#:     would become `3ж` — and `ж` labels are reachable by tapping.  «жэ» alone stands.
#:   * **«и» is not here.**  It is the conjunction: «третью и пятую» is two problems, and
#:     a suffix reading would silently make it one, `3и`.  The `и` labels of the seed
#:     (`10и*`) are therefore voice-unreachable, which is a named limit rather than a bug.
#:
#: «а» and «е» ARE here, and they are also words.  They are read as a suffix ONLY
#: immediately after a number, and dropped as noise anywhere else — see ``_walk``.
LETTER_FORMS: dict[str, str] = {
    "а": "а",
    "бэ": "б", "бе": "б",
    "вэ": "в", "ве": "в",
    "гэ": "г", "ге": "г",
    "дэ": "д", "де": "д",
    "е": "е",
    "жэ": "ж",
    "зэ": "з", "зе": "з",
}

#: «с третьей ПО шестую».  The opener is unremarkable Russian and appears constantly
#: outside a range, so an opener that is not followed by ``number + closer + number`` is
#: simply dropped rather than treated as an error.
RANGE_OPENERS: frozenset = frozenset({"с", "со", "от"})
RANGE_CLOSERS: frozenset = frozenset({"по", "до"})

#: The sheet has problems `-1` … `-5`.  They are dictated «минус один».
NEGATIVE_WORDS: frozenset = frozenset({"минус"})

#: Words a teacher says around the payload.  Dropped wherever they occur, including out
#: of the surname phrase — «Петров сдал третью» must not fuzzy-match on «сдал».
NOISE_WORDS: frozenset = frozenset({
    "и", "ещё", "еще", "также", "тоже", "потом", "затем", "дальше", "так", "значит",
    "сдал", "сдала", "сдали", "решил", "решила", "решили", "сделал", "сделала",
    "задача", "задачи", "задачу", "задач", "номер", "номера", "плюс", "это", "у",
    "него", "неё", "нее", "вот", "ну",
    # Particles.  «же» is here rather than in ``LETTER_FORMS`` for the reason spelled out
    # there: «три же» must stay 3 and must not open a row called «же» either.
    "же", "ли", "бы",
})

#: Decorations a problem label carries on the sheet and a voice never carries: the degree
#: sign of an obligatory problem, the star of a hard one, and the smiley of `10а:)`.
#: Stripped from BOTH sides before a label is compared to the catalogue.
LABEL_DECORATIONS = "°*:)"


# =============================================================================
#  2 · NORMALISING THE STRING BEFORE IT IS TOKENISED
# =============================================================================

#: Everything that is not a Russian/Latin letter, a digit or a hyphen is a separator.
_TOKEN_SPLIT = re.compile(r"[^0-9a-zA-Zа-яА-ЯёЁ-]+")

#: A token that already arrived as digits, optionally with a glued letter: an engine that
#: normalises despite being asked not to writes `7б`, and a teacher who types instead of
#: speaking writes the same.  Both go down the identical path.
_DIGIT_TOKEN = re.compile(r"^(-?\d+)([а-яё]?)$")


def fold(text: str) -> str:
    """Lower-case, and fold ``ё`` onto ``е``.

    Applied to BOTH sides of every comparison this module makes.  The roster contains
    ``Фёдоров``, no recogniser is reliable about the diaeresis, and a comparison that is
    folded on one side only is a comparison that fails on exactly one child.  The
    original spelling is never overwritten — it is what the confirmation table shows.
    """
    return text.replace("ё", "е").replace("Ё", "Е").lower()


def tokenise(text: str) -> list[str]:
    """Split a dictated line into words, folded, with the empties dropped."""
    return [token for token in _TOKEN_SPLIT.split(fold(text)) if token]


# =============================================================================
#  3 · CLASSIFYING ONE TOKEN
# =============================================================================

def _build_index() -> dict[str, tuple[str, object]]:
    """Invert the tables once, at import, into ``form -> (kind, payload)``.

    Built rather than written out so that the tables above stay the single home of the
    vocabulary: a form added there is matched here without a second edit.
    """
    index: dict[str, tuple[str, object]] = {}
    for value, forms in NUMERAL_FORMS.items():
        for form in forms:
            index[fold(form)] = ("number", value)
    for value, forms in TENS_FORMS.items():
        for form in forms:
            index[fold(form)] = ("tens", value)
    for form, letter in LETTER_FORMS.items():
        # A letter name that is ALSO a numeral form must stay a numeral: no such
        # collision exists today, and this ordering makes sure adding one is visible.
        index.setdefault(fold(form), ("letter", letter))
    return index


_INDEX = _build_index()


def _classify(token: str) -> tuple[str, object]:
    """One token -> ``(kind, payload)``.

    Kinds: ``number`` · ``tens`` · ``letter`` · ``open`` · ``close`` · ``minus`` ·
    ``noise`` · ``glued`` (digits that already carry their letter) · ``word``.
    """
    digits = _DIGIT_TOKEN.match(token)
    if digits is not None:
        number, letter = digits.group(1), digits.group(2)
        if letter:
            return "glued", (int(number), letter)
        return "number", int(number)
    if token in RANGE_OPENERS:
        return "open", None
    if token in RANGE_CLOSERS:
        return "close", None
    if token in NEGATIVE_WORDS:
        return "minus", None
    known = _INDEX.get(token)
    if known is not None:
        return known
    if token in NOISE_WORDS:
        return "noise", None
    return "word", token


# =============================================================================
#  4 · THE TWO PRE-PASSES, THEN THE WALK
# =============================================================================
#
# Composition and ranges are done as passes over the CLASSIFIED tokens rather than inside
# the walk, because both are lookahead rules and a walk that also looks ahead is a walk
# nobody can follow six months later.

def _compose_tens(tokens: list[tuple[str, object]]) -> list[tuple[str, object]]:
    """«двадцать четыре» -> 24.  A bare «двадцать» stays 20: the sheet really has a `20`."""
    out: list[tuple[str, object]] = []
    index = 0
    while index < len(tokens):
        kind, payload = tokens[index]
        if kind == "tens":
            following = tokens[index + 1] if index + 1 < len(tokens) else None
            if following is not None and following[0] == "number" and 1 <= following[1] <= 9:
                out.append(("number", payload + following[1]))
                index += 2
                continue
            out.append(("number", payload))
            index += 1
            continue
        out.append((kind, payload))
        index += 1
    return out


def _expand_ranges(tokens: list[tuple[str, object]]) -> list[tuple[str, object]]:
    """«с третьей по шестую» -> 3, 4, 5, 6.

    BARE NUMBERS ONLY, and that is a decision rather than an omission: «с седьмой а по
    седьмую в» has no defined enumeration — the sheet's letters are not a contiguous
    alphabet — so it is left alone and reaches the teacher as the two labels actually
    said, for them to complete by tapping.

    A descending or absurd range («с шестой по третью») is left alone too: two numbers
    are what was heard, and inventing an empty list would silently drop a problem.
    """
    out: list[tuple[str, object]] = []
    index = 0
    while index < len(tokens):
        window = tokens[index:index + 4]
        if (
            len(window) == 4
            and window[0][0] == "open"
            and window[1][0] == "number"
            and window[2][0] == "close"
            and window[3][0] == "number"
        ):
            start, stop = window[1][1], window[3][1]
            following = tokens[index + 4] if index + 4 < len(tokens) else None
            # A letter directly after the closing number means the range end is not a
            # bare number after all -- leave the whole thing to the walk.
            if following is None or following[0] != "letter":
                if start <= stop and stop - start <= MAX_RANGE_WIDTH:
                    out.extend(("number", value) for value in range(start, stop + 1))
                    index += 4
                    continue
        out.append(tokens[index])
        index += 1
    return out


#: The widest range a dictation may open.  A sheet is at most a few dozen problems; a
#: wider span is a misrecognition («с третьей по тридцатую» out of «с третьей по
#: третью»), and expanding it would bury the teacher's screen in cells to untick.
MAX_RANGE_WIDTH = 30


@dataclass
class DictatedRow:
    """One student and the problems said about them, as heard.

    ``surname_text`` is the phrase the teacher said, folded and de-noised but NOT yet
    resolved to anybody: resolution is the next stage and it has two channels.
    """

    surname_text: str
    labels: list[str] = field(default_factory=list)
    #: The slice of the original transcript this row came from.  Shown to the teacher
    #: beside the row so that a wrong parse is diagnosable without replaying the audio.
    said: str = ""


def parse_dictation(text: str) -> list[DictatedRow]:
    """A dictated line -> rows of ``(surname phrase, problem labels)``.

    ONE DICTATION MAY CARRY SEVERAL STUDENTS.  A teacher going down the class says
    «Петров три пять, Иванова вторую и третью», and a parser that took only the first
    name would drop the rest in silence.  The rule is positional and needs no punctuation
    (a recogniser in verbatim mode supplies little): a word that is not a numeral, not a
    letter and not noise, arriving AFTER at least one problem has been collected, opens a
    new row.
    """
    tokens = [_classify(token) for token in tokenise(text)]
    tokens = _compose_tens(tokens)
    tokens = _expand_ranges(tokens)
    return _walk(tokens, said=text.strip())


def _walk(tokens: list[tuple[str, object]], *, said: str) -> list[DictatedRow]:
    rows: list[DictatedRow] = []
    words: list[str] = []
    labels: list[str] = []
    negative = False

    def close_row() -> None:
        if words or labels:
            rows.append(
                DictatedRow(surname_text=" ".join(words), labels=list(labels), said=said)
            )

    for kind, payload in tokens:
        if kind == "word":
            if labels:
                close_row()
                words, labels = [], []
            words.append(str(payload))
            negative = False
        elif kind in ("number", "glued"):
            if kind == "glued":
                value, letter = payload
                labels.append("%s%s" % (-value if negative else value, letter))
            else:
                labels.append(str(-payload if negative else payload))
            negative = False
        elif kind == "letter":
            # A suffix attaches to the number just said and to nothing else.  «а» and «е»
            # reach here as ordinary words all the time; away from a number they are noise.
            if labels and labels[-1][-1].isdigit():
                labels[-1] = labels[-1] + str(payload)
        elif kind == "minus":
            negative = True
        # ``open``, ``close`` and ``noise`` survive only when the range pass declined
        # them; they carry nothing and are dropped here.

    close_row()
    return rows


def normalise_label(label: str) -> str:
    """A label as it is compared: folded, stripped of the sheet's decorations.

    `7б`, `7б°` and `7б*` are the same problem said out loud — the degree sign marks an
    obligatory problem and the star a hard one, and neither is pronounceable.  Comparison
    therefore happens on the stripped form, while what the teacher sees stays the label
    the sheet actually prints.
    """
    stripped = fold(label).strip()
    for decoration in LABEL_DECORATIONS:
        stripped = stripped.replace(decoration, "")
    return stripped.strip()


# =============================================================================
#  5 · THE SEAM TO THE RECOGNISER
# =============================================================================

class Transcriber(Protocol):
    """Audio in, VERBATIM text out.  The only thing ``core`` knows about recognition.

    Declared here rather than in ``core/ports.py`` for one reason worth writing down: at
    the time this position ran, ``core/ports.py`` was outside its zone.  The seam belongs
    beside the other ports and moving it there is a one-line job for whoever owns that
    file next; it is named in ``## ВОПРОСЫ`` rather than done from here.
    """

    def transcribe(self, audio: bytes, *, mime_type: str = "audio/ogg") -> str:
        """The words that were said, spelled as they were said.

        VERBATIM, never "smart".  A recogniser that normalises numbers on our behalf
        turns dictated digits into a lottery, and in this project the digits are the
        entire payload: `7б` written back as «7б» by an engine that guessed is
        indistinguishable, at this seam, from `7б` written back because it heard it.
        """


#: Ceiling the engines with a user dictionary impose.  Above it the dictionary is
#: rejected outright rather than truncated.
USER_DICTIONARY_MAX = 1000

#: Where such a dictionary still helps.  Past roughly a hundred terms the boost each term
#: gets is diluted; this project needs 101 and is therefore right at the useful size,
#: which is why the dictionary is the roster and the labels and NOT the whole language.
USER_DICTIONARY_OPTIMUM = 100


def build_user_dictionary(
    surnames: Sequence[str], labels: Sequence[str] = ()
) -> list[str]:
    """The terms a recogniser (or the fuzzy channel) should be biased towards.

    Built from the catalogue, never typed: a surname added to the roster in October must
    not need a second edit in a constant somewhere to become dictatable.

    Deduplicated on the FOLDED form and returned in first-seen order, so the list is
    stable across runs — an engine that caches a dictionary by its hash re-uploads it
    otherwise, every start, forever.
    """
    terms: list[str] = []
    seen: set = set()
    for term in list(surnames) + list(labels):
        term = (term or "").strip()
        if not term:
            continue
        key = fold(term)
        if key in seen:
            continue
        seen.add(key)
        terms.append(term)
    if len(terms) > USER_DICTIONARY_MAX:
        raise ValueError(
            "user dictionary of %d terms is over the %d an engine will take; it is the "
            "roster plus the labels, so something is feeding it the whole catalogue"
            % (len(terms), USER_DICTIONARY_MAX)
        )
    return terms


# =============================================================================
#  6 · MATCHING — TWO INDEPENDENT CHANNELS, AND WHY THERE ARE TWO
# =============================================================================
#
# Channel one is the schema call: the transcript goes to the model that P7 built, which
# answers with an ``enum`` over student ids and problem ids — never surnames — and puts
# ``raw_text`` first and required.
#
# Channel two is a fuzzy match of that same ``raw_text`` against the roster, computed
# here, by us, with no model involved.
#
# THE TWO CHANNELS EXIST TO DISAGREE.  A numeric ``confidence`` from a model does not
# work for this: it collapses to 0,9/1,0 and stays there while accuracy falls, so it
# reports certainty about its own output rather than about the world.  Two channels that
# could not see each other's answer are a real signal — agreement means two different
# methods reached the same child, and DISAGREEMENT IS THE «doubtful» FLAG.  There is no
# confidence field anywhere below and nothing reads one.

#: How close a fuzzy match has to be before it may name a child at all.
#:
#: NOT A NUMBER OF OURS.  It is P7's ``CONFIDENCE_THRESHOLD`` — the same 0,7, measured on
#: the same roster, for the same comparison — expressed on the 0..100 scale the metric is
#: defined on.  Two screens disagreeing about how close is close enough would be two
#: screens telling one teacher two different things about one child.
FUZZY_THRESHOLD = raspoznavanie.CONFIDENCE_THRESHOLD * 100.0

#: How far the best candidate has to stand above the second before the answer is taken as
#: settled.  Inside this margin the row is UNKNOWN and the teacher gets buttons: «never
#: make it guess» is the rule, and a two-point lead over a classmate is a guess.
AMBIGUITY_MARGIN = 6.0

#: How many candidates a row offers when it cannot decide.  Three fits one Telegram row
#: at a readable width; more is a menu, and a menu in the seam between two students costs
#: the five-to-fifteen seconds the whole conveyor exists to protect.
MAX_ALTERNATIVES = 3


class Verdict(str, Enum):
    """How much the two channels managed to establish about one dictated row."""

    #: Both channels available and agreeing, or one channel with a clear, unambiguous
    #: lead.  The row is pre-ticked and still has to be confirmed by a human.
    CERTAIN = "certain"
    #: The channels disagree, or the lead over the runner-up is inside the margin.  The
    #: row is shown marked and its alternatives are offered.
    DOUBTFUL = "doubtful"
    #: Nothing reached the threshold, or the dictation named no student at all.  Nothing
    #: is pre-ticked; buttons, never a guess.
    UNKNOWN = "unknown"


# ------------------------------------------------------- surnames across their cases

#: The declension of a surname is P7's table, not a second copy of it.
#:
#: ``core/services/raspoznavanie.py`` already carries ``case_forms`` — sixteen ending
#: rules plus the indeclinables — because the photo path needs exactly the same thing:
#: «нет Петрова» and «Петров» are one child.  A voice path with its own table would be
#: two homes for one truth, and they diverge in silence: the day somebody adds an ending
#: for a new child, one screen finds them and the other does not, and nothing goes red.
#:
#: Re-exported under this name so that it can be read here as part of this module's
#: vocabulary, and so that the seam is one line to find when P7's table moves.
case_forms = raspoznavanie.case_forms


@dataclass(frozen=True)
class Candidate:
    """One student the fuzzy channel considered, and how well they scored."""

    student_id: int
    surname: str
    score: float


def score_against_roster(said: str, students: Sequence) -> list[Candidate]:
    """Every student, scored against what was said, best first.

    THE METRIC IS P7's ``raspoznavanie.ratio``, called rather than reimplemented: it is
    ``fuzz.ratio`` when ``rapidfuzz`` is installed and the identical formula
    (``200 * LCS / (len(a) + len(b))``) when it is not, so this screen keeps working on a
    machine where the wheel is missing instead of failing to import.  That fallback is
    P7's measured decision and inheriting it costs one import.

    It is ``ratio``, and **never** the token-set variant beside it in the same library.
    That one returns 100 on containment, so «Лим» would score a perfect match against
    «Лупулешин» the moment the tokens happened to nest, and a perfect score is exactly
    what stops the alternatives from being offered.  Containment is the wrong relation
    for a surname.  (Its name is deliberately not spelled out anywhere in this file: the
    готовности criterion greps this source for that literal string, so writing it even
    inside a comment turns the gate red -- the same device ``core/ports.py`` uses for the
    bot framework.)

    The phrase is compared BOTH whole and word by word: a teacher who says «Петров Иван»
    has named one child, and a whole-phrase comparison alone would score that lower than
    the same child said bare.
    """
    said = fold(said).strip()
    if not said:
        return []
    words = [word for word in said.split() if word]
    candidates = []
    for student in students:
        # The given name as well as the surname, because P7 measured that a teacher of
        # this school writes «Ирина» as readily as «Агаркова» — and says it as readily too.
        forms = [
            fold(form)
            for source in (student.surname, getattr(student, "name", "") or "")
            for form in case_forms(source)
        ]
        if not forms:
            continue
        best = 0.0
        for form in forms:
            best = max(best, raspoznavanie.ratio(said, form))
            for word in words:
                best = max(best, raspoznavanie.ratio(word, form))
        candidates.append(Candidate(student.id, student.surname, best))
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.student_id))
    return candidates


@dataclass(frozen=True)
class SurnameMatch:
    """What the fuzzy channel alone concluded about one dictated surname phrase."""

    student_id: Optional[int]
    verdict: Verdict
    score: float
    alternatives: list = field(default_factory=list)
    reason: str = ""


def match_surname(said: str, students: Sequence) -> SurnameMatch:
    """The fuzzy channel's answer, with its own ambiguity already accounted for."""
    candidates = score_against_roster(said, students)
    if not candidates:
        return SurnameMatch(None, Verdict.UNKNOWN, 0.0, [], "nothing was said, or the roster is empty")

    best = candidates[0]
    alternatives = [candidate.student_id for candidate in candidates[:MAX_ALTERNATIVES]]

    if best.score < FUZZY_THRESHOLD:
        return SurnameMatch(
            None, Verdict.UNKNOWN, best.score, alternatives,
            "best match %.0f is under the threshold of %.0f" % (best.score, FUZZY_THRESHOLD),
        )

    runner_up = candidates[1].score if len(candidates) > 1 else 0.0
    if best.score - runner_up < AMBIGUITY_MARGIN:
        return SurnameMatch(
            None, Verdict.UNKNOWN, best.score, alternatives,
            "%.0f against %.0f is inside the margin of %.0f -- two children sound alike"
            % (best.score, runner_up, AMBIGUITY_MARGIN),
        )

    return SurnameMatch(
        best.student_id, Verdict.CERTAIN, best.score, alternatives,
        "fuzzy %.0f, next %.0f" % (best.score, runner_up),
    )


# --------------------------------------------------- the schema call, when it exists

#: Un-fencing a model's answer is NOT here, and the reason is a rule of this tree rather
#: than a preference.  ``infra/llm.py`` already carries ``strip_fence`` — measured on this
#: project on 02.09, when a valid ``{"rows": []}`` came back inside a ```` ```json ````
#: fence under a strict schema and the naive parser rejected it — but ``core/`` may not
#: import ``infra/``, so a copy here would be a second home for that measurement.  The
#: adapter that calls P7's function lives in ``infra/asr.py``; this module receives rows
#: already parsed.


class SchemaExtractor(Protocol):
    """P7's seam: the transcript in, rows of ids out.

    ``raw_text`` first and required; ids only, never surnames — a surname in the payload
    is a surname leaving the server, and the enum is what stops the model inventing a
    child who is not on the roster.
    """

    def extract(self, raw_text: str, *, students: Sequence, problems: Sequence) -> list:
        """Rows of ``{"raw_text": ..., "student_id": int | "UNKNOWN", "alternatives": [...],
        "problem_ids": [...]}``."""


def load_schema_extractor(
    module_name: str = "core.services.raspoznavanie", factory: str = "build_extractor"
) -> tuple:
    """``(extractor | None, reason)`` — P7's schema call, if it offers one for TEXT.

    **Imported, never forked.**  A copied schema call is two homes for one truth and they
    diverge in silence.

    P7's module landed on ``main`` while this position was working and its matching half
    is now called directly (``ratio``, ``case_forms``, ``CONFIDENCE_THRESHOLD`` above).
    Its schema half, however, is a VISION pipeline: ``infra.llm.VisionModel`` takes an
    image, and ``rows_from_answer`` reads codes printed on a sheet.  A transcript is
    neither.  So this seam looks for a text factory, does not find one, and says which
    module and which name it wanted — and the fuzzy channel carries the row alone, with
    ``channels`` saying so out loud, so that «one channel» is never mistaken for «two
    channels that agreed».  Adding that factory is P7's file to change, not this one's.
    """
    import importlib

    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        return None, "%s could not be imported (%s); wanted %s()" % (
            module_name, error, factory,
        )
    build = getattr(module, factory, None)
    if build is None:
        return None, "%s has no %s()" % (module_name, factory)
    return build(), "%s.%s()" % (module_name, factory)


def parse_model_rows(answer: str, *, unfence=None) -> list:
    """The rows out of one schema answer: fence stripped first, then JSON.

    ``unfence`` is injected because the function that does it is P7's and lives under
    ``infra/`` — see the note above.  Called without one, this does no unfencing at all
    rather than quietly reimplementing it: a silent second implementation is exactly the
    thing that diverges.

    ``confidence`` is NOT read even when the model volunteers one.  Such a number
    collapses to 0,9/1,0 and stays high while accuracy falls; the thing that carries
    doubt here is the disagreement between two channels, and adding a number beside it
    would only give a future reader something plausible to trust instead.
    """
    import json

    body = (unfence or (lambda text: text))(answer or "").strip()
    if not body:
        return []
    payload = json.loads(body)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    cleaned = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        cleaned.append(
            {
                "raw_text": row.get("raw_text", ""),
                "student_id": row.get("student_id"),
                "alternatives": list(row.get("alternatives") or []),
                "problem_ids": list(row.get("problem_ids") or []),
            }
        )
    return cleaned


# =============================================================================
#  7 · THE DRAFT — what the confirmation table is made of
# =============================================================================
#
# A draft is not a mark and cannot become one by itself.  Everything below produces rows
# and cells for a human to look at; the ONLY thing that reaches the journal is a cell a
# human left ticked and then confirmed, and it reaches it through the marking path P4
# already built.  There is never a direct write.

@dataclass
class DraftCell:
    """One problem said about one student.

    ``problem_id`` is None when the label was heard but matches nothing on the sheets in
    view.  Such a cell is shown, struck through, and cannot be ticked: dropping it
    silently would lose a problem the teacher believes they dictated.
    """

    label: str
    problem_id: Optional[int] = None
    printed_label: Optional[str] = None
    #: Pre-ticked when it resolved.  A tap toggles it; only ticked cells are written.
    ticked: bool = True

    @property
    def is_writable(self) -> bool:
        return self.problem_id is not None and self.ticked


@dataclass
class DraftRow:
    """One student's line of the confirmation table."""

    said: str
    surname_text: str
    student_id: Optional[int]
    verdict: Verdict
    cells: list = field(default_factory=list)
    alternatives: list = field(default_factory=list)
    reason: str = ""

    @property
    def is_resolved(self) -> bool:
        return self.student_id is not None


@dataclass
class Draft:
    """The whole confirmation table for one voice note.

    ``audio_sha256`` is half the idempotency key of every mark this draft can write: the
    same recording redelivered by Telegram produces the same digest, the same cells and
    therefore the same keys, and the journal answers the second delivery from itself.
    """

    transcript: str
    rows: list = field(default_factory=list)
    audio_sha256: str = ""
    #: How the second channel went, in words: which extractor answered, or why none did.
    channels: str = ""

    @property
    def writable_cells(self) -> int:
        return sum(
            1
            for row in self.rows
            if row.is_resolved
            for cell in row.cells
            if cell.is_writable
        )


def resolve_labels(labels: Sequence[str], problems: Sequence) -> list:
    """Heard labels -> cells, matched against the problems currently in view.

    Comparison is on the STRIPPED label (``normalise_label``): the degree sign of an
    obligatory problem and the star of a hard one are printed, not pronounced, and a
    teacher who says «семь бэ» has named `7б°` if that is what the sheet carries.

    When two sheets in view print the same stripped label, the FIRST in the order given
    wins and the row is still shown — the caller passes the current sheet first, which is
    the sheet the teacher is working on.
    """
    by_label = {}
    for problem in problems:
        by_label.setdefault(normalise_label(problem.label), problem)
    cells = []
    for label in labels:
        problem = by_label.get(normalise_label(label))
        cells.append(
            DraftCell(
                label=label,
                problem_id=problem.id if problem is not None else None,
                printed_label=problem.label if problem is not None else None,
                ticked=problem is not None,
            )
        )
    return cells


def build_draft(
    transcript: str,
    *,
    students: Sequence,
    problems: Sequence,
    model_rows: Optional[Sequence] = None,
    audio_sha256: str = "",
    channels: str = "",
) -> Draft:
    """Transcript in, confirmation table out.  Both channels applied, neither trusted.

    ``model_rows`` is channel one — P7's schema call, already parsed by
    ``parse_model_rows``.  It is optional because P7 exposes no text-schema factory yet
    (see ``load_schema_extractor``); when it is absent the fuzzy channel answers alone and
    ``channels`` says so, so that a single channel is never read as two channels agreeing.

    **The disagreement rule.**  When both channels answered and picked DIFFERENT students,
    the row is ``DOUBTFUL``: it keeps the fuzzy channel's pick — that is the one whose
    reasoning can be inspected and re-run — and offers both picks as alternatives.  This
    is the whole reason there are two channels, and it is the only source of doubt in the
    system; no numeric confidence is read from anywhere.
    """
    rows = []
    by_raw = {}
    for model_row in model_rows or []:
        by_raw[fold(model_row.get("raw_text", "")).strip()] = model_row

    for dictated in parse_dictation(transcript):
        match = match_surname(dictated.surname_text, students)
        student_id, verdict, reason = match.student_id, match.verdict, match.reason
        alternatives = list(match.alternatives)

        model_row = by_raw.get(fold(dictated.surname_text).strip())
        model_pick = model_row.get("student_id") if model_row else None
        if isinstance(model_pick, str):
            model_pick = None if model_pick.upper() == "UNKNOWN" else model_pick
        if model_pick is not None and student_id is not None and model_pick != student_id:
            verdict = Verdict.DOUBTFUL
            reason = "channels disagree: schema call says %s, fuzzy says %s (%s)" % (
                model_pick, student_id, reason,
            )
            alternatives = [student_id, model_pick] + [
                other for other in alternatives if other not in (student_id, model_pick)
            ]
        elif model_pick is not None and student_id is not None:
            reason = "both channels agree (%s)" % reason

        rows.append(
            DraftRow(
                said=dictated.said,
                surname_text=dictated.surname_text,
                student_id=student_id,
                verdict=verdict,
                cells=resolve_labels(dictated.labels, problems),
                alternatives=alternatives[:MAX_ALTERNATIVES],
                reason=reason,
            )
        )

    return Draft(
        transcript=transcript,
        rows=rows,
        audio_sha256=audio_sha256,
        channels=channels or "fuzzy channel only -- no text schema call available",
    )
