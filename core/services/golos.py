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
from typing import Optional, Protocol, Sequence


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
