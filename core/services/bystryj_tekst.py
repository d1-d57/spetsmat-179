"""The fourth way in: a teacher TYPES the sheet the way they write it on paper.

    Лёня Санин 7, 9а, 11б, 12, 13, 15а, 15в, 2б, 4, 6
    Катя Долкирева 2а, 2б, 4, 5в, 8, 10а
    Аня Бочарова [3д] 5, 12
    Влад Быков —

Buttons (P4), photo (P7), voice (P8) and text are EQUAL ways to reach the same journal --
the second thing the interview finalised -- and «equal» here is literal: this module owns
no matching metric, no confirmation table and no write path of its own.  It owns exactly
one thing nobody else does: **the grammar of the written block**, which is not the grammar
of a dictation and breaks the dictation parser in two measured ways (see PART 2).

WHAT THIS MODULE DELIBERATELY DOES NOT CONTAIN
----------------------------------------------
* **The similarity metric.**  ``raspoznavanie.ratio`` (P7), reached through
  ``core/services/golos.py``.  It is ``fuzz.ratio`` when ``rapidfuzz`` is installed and
  the identical formula when it is not.  It is never the token-set variant beside it in
  the same library: that one returns 100 on containment, so a short surname nested inside
  a long one would score a perfect match and the alternatives would stop being offered --
  which is the one thing this path may never do.  (The name of that variant is not spelled
  out anywhere in this file on purpose: the готовности criterion greps this source for the
  literal string, the same device ``core/services/golos.py`` and ``core/ports.py`` use.)
* **The declension of a name.**  ``raspoznavanie.case_forms`` (P7), sixteen ending rules
  plus the indeclinables, re-exported by P8 and used from there.
* **The threshold and the ambiguity margin.**  P8's ``FUZZY_THRESHOLD`` and
  ``AMBIGUITY_MARGIN``, which are themselves P7's ``CONFIDENCE_THRESHOLD``.  Four screens
  disagreeing about how close is close enough would be four screens telling one teacher
  four different things about one child.
* **The confirmation table.**  ``golos.Draft`` / ``DraftRow`` / ``DraftCell`` -- the same
  dataclasses the voice screen builds and the same stored dict the photo screen builds, so
  that ``bot.routers.photo.checked_cells`` stays ONE function that decides what a
  «Записать» would write.
* **The write.**  P4's ``MarkingService``.  Nothing here touches the journal, and nothing
  reaches the journal until a human has looked at the whole table and pressed a button.
  That is the third finalised point of the interview and it has no exception.

If this file were deleted the journal would lose an input, not a capability.

THE ONE ERROR THIS PATH MAY NOT MAKE.  A plus put on the WRONG child is invisible: it is
noticed only by the child it went missing from, weeks later.  So every decision here is
biased towards asking: below the threshold, or inside the margin, the row resolves to
nobody and the teacher gets buttons.  A guess that happens to be right and a guess that
happens to be wrong are the same act, and only one of them is ever discovered.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

import config
from core.services import golos
from core.services.golos import Verdict, fold

# =============================================================================
#  PART 1 · УМЕНЬШИТЕЛЬНЫЕ — A DICTIONARY, NOT A FUZZINESS
# =============================================================================
#
# «Лёня» and «Леонид» are four characters apart out of six; «Катя» and «Екатерина» are
# further still.  No similarity metric reaches either, and no threshold can be lowered far
# enough to catch them without catching half the class as well -- that is precisely the
# lowering that puts a plus on the wrong child.  A hypocorism is a FACT ABOUT THE LANGUAGE,
# it is finite, and it belongs in a table.
#
# THE TABLE IS DATA, NOT ``if``s.  Adding «Ксюша» is adding a string to a tuple; it is not
# editing a parser.  It is inverted once, at import, into diminutive -> full names.
#
# A diminutive that names SEVERAL full names (Слава is Владислав, Вячеслав and Ярослав;
# Ася is Анастасия and Анна) is kept as several: the expansion tries all of them and the
# surname settles it.  When the surname cannot settle it, the row goes to buttons, which
# is the correct outcome and not a failure of the table.
#
# ⚠ Four names of this catalogue are deliberately ABSENT -- Арон, Дэвин, Нино, Эльдар.
# Their hypocorisms are not something this position knows, and an invented one is worse
# than a missing one: a missing form costs a tap, an invented form can match the wrong
# child.  The отчёт reports the coverage as a number rather than claiming completeness.

#: ``full name -> the short names a teacher of this school actually writes``.
DIMINUTIVES = {
    "Александр": ("Саша", "Саня", "Шура", "Алекс", "Сашка"),
    "Алексей": ("Лёша", "Алёша", "Лёха", "Лёшка"),
    "Анастасия": ("Настя", "Ася", "Стася", "Настюша"),
    "Андрей": ("Андрюша", "Дюша", "Андрюха"),
    "Анна": ("Аня", "Анюта", "Нюта", "Ася", "Анька"),
    "Василий": ("Вася", "Васёк", "Васька"),
    "Вера": ("Верочка", "Веруня"),
    "Виктор": ("Витя", "Витёк", "Витька"),
    "Владислав": ("Влад", "Владик", "Слава"),
    "Всеволод": ("Сева", "Севка"),
    "Вячеслав": ("Слава", "Славик", "Славка"),
    "Георгий": ("Гоша", "Жора", "Гера", "Гошка"),
    "Даниил": ("Даня", "Данила", "Данил", "Данька"),
    "Дарья": ("Даша", "Дашуня", "Дашка"),
    "Дмитрий": ("Дима", "Митя", "Димон", "Димка"),
    "Евгений": ("Женя", "Жека", "Женька"),
    "Екатерина": ("Катя", "Катюша", "Катька"),
    "Елизавета": ("Лиза", "Лизавета", "Лизка"),
    "Иван": ("Ваня", "Ванька", "Иванка"),
    "Ирина": ("Ира", "Ириша", "Ирка"),
    "Константин": ("Костя", "Котя", "Костик"),
    "Леонид": ("Лёня", "Лёнька", "Лёка"),
    "Максим": ("Макс", "Максик", "Максимка"),
    "Марк": ("Маркуша", "Марик"),
    "Матвей": ("Мотя", "Матвейка"),
    "Михаил": ("Миша", "Мишаня", "Мишка"),
    "Никита": ("Никитка", "Ника"),
    "Полина": ("Поля", "Полинка", "Полька"),
    "Роман": ("Рома", "Ромка", "Ромчик"),
    "Софья": ("Соня", "Софа", "София", "Сонька"),
    "Тимофей": ("Тима", "Тимоша", "Тимка"),
    "Фёдор": ("Федя", "Федька", "Федюня"),
    "Ярослав": ("Ярик", "Слава", "Яр"),
}


def _build_diminutive_index() -> dict:
    """``folded short name -> (full name, ...)``, built once from the table above.

    Built rather than written out so that the table stays the single home of the
    vocabulary: a form added there is matched here without a second edit.  The full name
    is also indexed onto itself, so that a phrase which already carries it goes down the
    identical path instead of a special case.
    """
    index: dict = {}
    for full, shorts in DIMINUTIVES.items():
        for form in (full,) + tuple(shorts):
            key = fold(form)
            if full not in index.setdefault(key, ()):
                index[key] = index[key] + (full,)
    return index


_DIMINUTIVE_INDEX = _build_diminutive_index()


def full_names_for(word: str) -> tuple:
    """Every full given name the written word may be a short form of.  Empty when none."""
    return _DIMINUTIVE_INDEX.get(fold(word or "").strip(), ())


def covered_names(students: Sequence) -> tuple:
    """``(covered, total)`` over a roster -- how many students the table reaches.

    Reported as a NUMBER in the отчёт rather than described as «покрыты все»: the four
    names the table deliberately omits are exactly the ones a claim of completeness would
    hide, and a coverage figure that cannot fall is not a measurement.
    """
    names = [getattr(student, "name", "") or "" for student in students]
    return sum(1 for name in names if full_names_for(name)), len(names)


def expand_diminutives(phrase: str) -> list:
    """The phrase, plus one variant per way its short names could be spelled out in full.

    «Лёня Санин» -> «Леонид Санин».  «Слава Быков» -> «Владислав Быков», «Вячеслав Быков»,
    «Ярослав Быков» -- three variants, all tried, and if two of them land on two different
    children within the margin the row goes to buttons.

    THE EXPANSION HAPPENS ON THE INPUT, NOT ON THE ROSTER, and that is the whole reason
    this module adds no second matching channel.  A short name resolved to its full form
    is then compared by exactly the metric, exactly the declension table and exactly the
    threshold every other screen uses.  A second fuzzy channel here would be a second
    opinion about the same child, and two opinions is how one screen finds a student the
    other cannot.

    The original phrase is always first: a name that is already full must not be made
    worse by a table that does not know it.
    """
    words = [word for word in re.split(r"\s+", (phrase or "").strip()) if word]
    if not words:
        return []
    variants = [" ".join(words)]
    for index, word in enumerate(words):
        for full in full_names_for(word):
            if fold(full) == fold(word):
                continue
            variant = list(words)
            variant[index] = full
            candidate = " ".join(variant)
            if candidate not in variants:
                variants.append(candidate)
    return variants


# -------------------------------------------------------- BOTH tokens, added up
#
# THE WRITTEN CHANNEL KNOWS SOMETHING THE SPOKEN ONE DOES NOT: the owner types a given
# name AND a surname, every time.  P8's ``score_against_roster`` compares each written word
# against every form of both fields and keeps the MAXIMUM, which is right for a dictation
# where a teacher may say a surname alone.  Here it throws away the second half of the
# evidence, and the задание asks for the other rule in as many words: «сравнивай КАЖДЫЙ
# токен записи с фамилией И с именем, **и складывай**».
#
# MEASURED, WHICH IS WHY THIS EXISTS.  Ten surnames of people who are not in this school,
# run through the maximum rule against the real 56-child roster: THREE were accepted as
# real children with no doubt shown -- «Чебышёв» became Чапышев at 71, «Лобачевский» became
# Николаева at 82, «Манин» became Исанин at 73.  Each of those is a plus landing on a child
# who did not earn it, and the child it went missing from is the only person who would ever
# notice.  Adding the two halves instead of maximising them refuses all three, because a
# stranger matches one field by accident and never both.
#
# The THRESHOLD and the MARGIN are still P8's constants, imported and not re-chosen: what
# changes is the score handed to them, not how close is close enough.


def _surname_score(token: str, student) -> float:
    """How well one written word matches this child's SURNAME, across its cases."""
    folded = fold(token)
    return max(
        (
            golos.raspoznavanie.ratio(folded, fold(form))
            for form in golos.case_forms(student.surname or "")
        ),
        default=0.0,
    )


def _name_score(token: str, student) -> float:
    """How well one written word matches this child's GIVEN NAME, across its cases.

    The dictionary enters HERE and as a fact, not as a similarity: when the written word is
    a known short form of this child's given name, the answer is 100 and no metric is
    consulted.  «Лёня» IS «Леонид» in the way that «Лёнид» merely resembles it, and a
    fuzziness that reached the first would reach half the class along with it.
    """
    if any(fold(full) == fold(student.name or "") for full in full_names_for(token)):
        return 100.0
    folded = fold(token)
    return max(
        (
            golos.raspoznavanie.ratio(folded, fold(form))
            for form in golos.case_forms(student.name or "")
        ),
        default=0.0,
    )


def score_student(said: str, student) -> float:
    """One phrase against one child, 0..100, on P8's scale.

    Two words or more: the best assignment of one word to the surname and ANOTHER word to
    the given name, averaged.  BOTH ORDERS are tried -- «Аня Бочарова» and «Бочарова Анна»
    are the same child written by two people -- and any further words (a patronymic, a
    stray) are ignored rather than allowed to drag the average down.

    One word: P8's rule unchanged, the better of the two fields.  A teacher who writes only
    «Быков» has given one piece of evidence and must be judged on one.
    """
    words = [word for word in re.split(r"\s+", (said or "").strip()) if word]
    if not words:
        return 0.0
    if len(words) == 1:
        return max(_surname_score(words[0], student), _name_score(words[0], student))
    return max(
        (_surname_score(surname, student) + _name_score(given, student)) / 2.0
        for surname in words
        for given in words
        if surname is not given
    )


def match_student(said: str, students: Sequence):
    """Which child a written name means, or nobody -- a ``golos.SurnameMatch``.

    P8's decision rule, applied to this channel's score: below ``FUZZY_THRESHOLD`` nobody
    is named, and a lead over the runner-up smaller than ``AMBIGUITY_MARGIN`` names nobody
    either.  Both constants are imported so that four screens keep one answer to «how close
    is close enough»; only the number they judge is this module's.

    A refusal is not a failure.  It draws ``MAX_ALTERNATIVES`` buttons, and a tap costs the
    teacher one second — which is the price of never putting a plus on the wrong child.
    """
    if not (said or "").strip():
        return golos.SurnameMatch(None, Verdict.UNKNOWN, 0.0, [], "имя не написано")

    scored = sorted(
        (
            golos.Candidate(student.id, student.surname, score_student(said, student))
            for student in students
        ),
        key=lambda candidate: (-candidate.score, candidate.student_id),
    )
    if not scored:
        return golos.SurnameMatch(None, Verdict.UNKNOWN, 0.0, [], "каталог пуст")

    best = scored[0]
    alternatives = [candidate.student_id for candidate in scored[: golos.MAX_ALTERNATIVES]]

    if best.score < golos.FUZZY_THRESHOLD:
        return golos.SurnameMatch(
            None, Verdict.UNKNOWN, best.score, alternatives,
            "лучшее совпадение %.0f ниже порога %.0f"
            % (best.score, golos.FUZZY_THRESHOLD),
        )

    runner_up = scored[1].score if len(scored) > 1 else 0.0
    if best.score - runner_up < golos.AMBIGUITY_MARGIN:
        return golos.SurnameMatch(
            None, Verdict.UNKNOWN, best.score, alternatives,
            "%.0f против %.0f — внутри допуска %.0f, двое пишутся похоже"
            % (best.score, runner_up, golos.AMBIGUITY_MARGIN),
        )

    return golos.SurnameMatch(
        best.student_id, Verdict.CERTAIN, best.score, alternatives,
        "совпадение %.0f, следующее %.0f" % (best.score, runner_up),
    )


# =============================================================================
#  PART 2 · THE GRAMMAR OF A WRITTEN BLOCK
# =============================================================================
#
# WHY THE DICTATION PARSER IS NOT REUSED HERE, MEASURED RATHER THAN ASSUMED.
# ``golos.parse_dictation`` is a parser for SPEECH and it mis-reads this format twice:
#
#   * `Аня Бочарова [3д] 5, 12` -- its tokeniser treats `[` and `]` as separators, so `3д`
#     arrives as an ordinary glued digit token and becomes A PROBLEM LABEL.  The child
#     silently gains a problem `3д` she never handed in, and the sheet marker -- the one
#     thing the bracket exists to carry -- is gone.
#   * `Влад Быков —` -- the dash is classified as noise and dropped, so the block becomes
#     indistinguishable from a name typed with nothing after it.  Rule 4 needs the dash to
#     be a POSITIVE FACT: пришёл и не сдал ничего.
#
# Both are silent losses, which is why this grammar is written out rather than patched in.
#
# THE BLOCK, NOT THE LINE, IS THE UNIT.  A teacher writes about ten problems per child and
# the wrapping is whatever the phone did with the width of the screen.  A block ends where
# the NEXT NAME begins, and a name is the only thing that can begin one: every label of
# every sheet in this catalogue starts with a digit, and the прочерк and the bracket start
# with punctuation.  Reading end-of-line as end-of-block would drop the tail of every
# multi-line block -- silently, and on the children with the most to record.

#: Every dash a phone or a keyboard can produce for «пришёл, не сдал ничего».  The em dash
#: is what the owner types; the hyphen is what a laptop gives without a compose key; the
#: en dash is what an autocorrect turns either into.  All three mean the same fact.
DASHES = ("—", "-", "–", "―", "‒", "−")

#: A line that is nothing but three or more dashes or underscores is the horizontal rule
#: the paper sheet is divided by -- a separator, carrying no fact.  THREE, not one: one
#: dash alone on a line is the прочерк and means the opposite of nothing.
_RULE = re.compile(r"^[-—–―‒−_*=]{3,}$")

#: The sheet marker: `[3д]` after the name and before the labels.  Non-greedy, so that a
#: line carrying two brackets keeps them apart instead of swallowing everything between.
_SHEET_MARKER = re.compile(r"\[\s*([^\[\]]*?)\s*\]")

#: What a problem label looks like when it is written rather than spoken: a number, an
#: optional letter, and the decorations the printed sheet carries (`7б°`, `10а:)`).
#: Anchored at both ends -- a token that merely CONTAINS a number is not a label, and
#: trimming it into one is how a word becomes a mark.
_LABEL = re.compile(r"^\d+\s*[а-яёa-z]?[%s]*$" % re.escape(golos.LABEL_DECORATIONS))

#: Punctuation that separates labels and carries nothing: commas, semicolons, the trailing
#: full stop of a line.  Stripped from the ends of a token before it is classified.
_TRIM = " \t,;.·•"


@dataclass
class TextBlock:
    """One student's block, as WRITTEN -- pure syntax, resolved against nothing.

    Kept separate from the draft on purpose: the grammar above can be tested without a
    database, a catalogue or a roster, and every case in §1 of the задание is a string in,
    a ``TextBlock`` out.
    """

    #: The name exactly as typed, before any expansion or matching.
    name_text: str
    #: The problem labels, in the order written, decorations kept as typed.
    labels: list = field(default_factory=list)
    #: What stood in the brackets after the name, or None when there were none.
    sheet_marker: Optional[str] = None
    #: True iff the block carried a прочерк and no labels: пришёл и не сдал ничего.
    present_no_marks: bool = False
    #: The block's own text, shown beside the row so a wrong parse is diagnosable
    #: without asking the teacher to remember what they typed.
    said: str = ""


def _classify_token(token: str) -> str:
    """``name`` · ``label`` · ``dash`` · ``empty`` for one whitespace-separated token."""
    stripped = token.strip(_TRIM)
    if not stripped:
        return "empty"
    if stripped in DASHES:
        return "dash"
    if _LABEL.match(stripped):
        return "label"
    return "name"


def _opens_a_block(line: str) -> bool:
    """Does this line start a new student, or continue the one above it?

    The rule is positional and needs no punctuation: only a NAME can open a block.  Every
    label in this catalogue begins with a digit, the прочерк begins with a dash and the
    sheet marker with a bracket, so a line whose first token is a word is a new child and
    a line whose first token is anything else is the tail of the previous one.
    """
    tokens = line.split()
    return bool(tokens) and _classify_token(tokens[0]) == "name"


def split_blocks(text: str) -> list:
    """A typed message -> one ``TextBlock`` per student.  No catalogue, no database.

    Blank lines and horizontal rules separate but do not terminate: a rule between two
    children is the paper's own divider and carries nothing this parser needs.
    """
    chunks: list = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or _RULE.match(line):
            continue
        if _opens_a_block(line) or not chunks:
            chunks.append([line])
        else:
            chunks[-1].append(line)
    return [_parse_block(" ".join(chunk)) for chunk in chunks if chunk]


def _parse_block(text: str) -> TextBlock:
    """One block's text -> its name, its sheet marker, its labels and its прочерк."""
    said = text.strip()

    # The bracket first, and only the FIRST one: it belongs to the name that precedes it,
    # and a second bracket further along the line is not a second sheet for one child.
    marker = None
    match = _SHEET_MARKER.search(said)
    if match is not None:
        marker = match.group(1).strip() or None
        text = (said[: match.start()] + " " + said[match.end():]).strip()

    name_words: list = []
    labels: list = []
    dashes = 0
    for token in text.split():
        kind = _classify_token(token)
        if kind == "empty":
            continue
        if kind == "label":
            labels.append(token.strip(_TRIM))
        elif kind == "dash":
            dashes += 1
        elif not labels and dashes == 0:
            # A word BEFORE the first label is part of the name.  A word after it is not:
            # the block is over as far as this line is concerned, and the next name opens
            # its own block anyway -- so a stray word here is dropped rather than glued
            # onto a name it does not belong to.
            name_words.append(token.strip(_TRIM))

    return TextBlock(
        name_text=" ".join(name_words),
        labels=labels,
        sheet_marker=marker,
        # A dash counts ONLY when nothing was handed in.  «Петров — 3, 5» is a teacher
        # using the dash as a separator, not as a statement about attendance, and reading
        # it as «не сдал ничего» would contradict the three problems on the same line.
        present_no_marks=bool(dashes) and not labels,
        said=said,
    )


# =============================================================================
#  PART 3 · THE DRAFT — the SAME confirmation table, reached from a fourth door
# =============================================================================


@dataclass
class TextRow(golos.DraftRow):
    """P8's confirmation-table row, plus the two facts a written block carries.

    A subclass and not a new dataclass, so that every consumer of a ``golos.DraftRow`` --
    the renderer, the stored dict, ``checked_cells`` -- keeps working unchanged.  The
    table is one table; this row simply knows two more things about itself.
    """

    #: True iff the block was a прочерк.  Goes to ATTENDANCE, never to marks.
    present_no_marks: bool = False
    #: The sheet the bracket named, when it named one that exists.
    sheet_id: Optional[int] = None
    #: What the bracket said, kept even when it matched no sheet -- an unresolved marker is
    #: shown to the teacher rather than dropped, because dropping it silently moves the
    #: whole block onto the current sheet and the teacher never learns that it did.
    sheet_marker: Optional[str] = None


@dataclass
class TextCell(golos.DraftCell):
    """P8's cell, plus WHICH SHEET the label was found on.

    Measured on the owner's own four lines, and the reason this class exists: he wrote
    `Лёня Санин 7, 9а, 11б, 12, 13, 15а, 15в, 2б, 4, 6` for the current sheet, and nine of
    those ten labels are on it.  `9а` is not -- `4д` prints `9` -- so the label fell
    through to the first older sheet that happens to print `9а`, which is листок 1, issued
    a year ago.  Pre-ticked and drawn as plain «9а», that is a plus landing on a problem
    from last autumn with nothing on the screen to say so.
    """

    #: The sheet the matched problem actually belongs to.
    sheet_id: Optional[int] = None
    #: Its printed number (`4д`, `1`), so the screen can say where the label came from.
    sheet_number: Optional[str] = None
    #: False when the label resolved on some sheet OTHER than the block's own.
    on_lead_sheet: bool = True


def _annotate_cells(cells: Sequence, problems: Sequence, sheets: Sequence, lead_sheet_id):
    """``golos.DraftCell``s -> ``TextCell``s that know their sheet, off-sheet ones untied.

    The matching itself is NOT redone here: ``golos.resolve_labels`` has already decided
    which problem each label means, by the stripped-label rule that every screen shares.
    This is a pass over its answer that adds one fact and applies one rule:

        A label that resolved on a sheet OTHER than the block's own is shown, is named
        with its sheet, and is NOT pre-ticked.

    Shown, because a debt handed in today was set weeks ago and dropping the label would
    lose a real hand-in.  Not pre-ticked, because «при сомнении — кнопки, а не догадка»:
    the teacher who meant the debt taps it on in one move, and the teacher who mistyped a
    label off the current sheet never learns to distrust a screen that ticked it for them.
    """
    by_id = {problem.id: problem for problem in problems}
    number_of = {sheet.id: str(sheet.number) for sheet in sheets}

    annotated = []
    for cell in cells:
        problem = by_id.get(cell.problem_id) if cell.problem_id is not None else None
        sheet_id = problem.sheet_id if problem is not None else None
        on_lead = sheet_id is None or lead_sheet_id is None or sheet_id == lead_sheet_id
        annotated.append(
            TextCell(
                label=cell.label,
                problem_id=cell.problem_id,
                printed_label=cell.printed_label,
                ticked=bool(cell.ticked) and on_lead,
                sheet_id=sheet_id,
                sheet_number=number_of.get(sheet_id),
                on_lead_sheet=on_lead,
            )
        )
    return annotated


def _sheet_by_number(sheets: Sequence, marker: Optional[str]):
    """The sheet a bracket names, or None.  Compared folded: `3Д`, `3д` and ` 3д ` are one."""
    if not marker:
        return None
    wanted = fold(marker).strip()
    for sheet in sheets:
        if fold(str(sheet.number)).strip() == wanted:
            return sheet
    return None


def problems_for(catalogue, sheet=None) -> list:
    """The problems a block may name, THE BLOCK'S SHEET FIRST.

    ``golos.resolve_labels`` resolves a duplicated label to the first sheet in the order it
    is given, so the order IS the disambiguation rule.  With a bracket the block's own
    sheet leads; without one the current sheet leads, which is rule 2: «листок по
    умолчанию — текущий», the ordinary case rather than the exception.

    Older sheets stay reachable in both cases -- a debt handed in today was set weeks ago.
    """
    sheets = catalogue.sheets()
    if not sheets:
        return []
    lead = sheet or max(sheets, key=lambda item: item.ord)
    ordered = [lead] + [item for item in sheets if item.id != lead.id]
    return [
        problem for item in ordered for problem in catalogue.problems_of_sheet(item.id)
    ]


def digest_of(text: str) -> str:
    """The idempotency half of every key this path can write: SHA-256 of the typed text.

    The same message sent twice -- a teacher who taps send again because the network
    stalled -- produces the same digest, the same cells and therefore the same keys, and
    the journal answers the second confirmation out of itself instead of writing a second
    event.  Exactly P7's and P8's device, with the bytes of a message where they use the
    bytes of a file.
    """
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def build_draft(text: str, *, students: Sequence, catalogue) -> golos.Draft:
    """A typed message -> the confirmation table, with nothing written and nothing guessed.

    ``golos.Draft`` is returned rather than a shape of this module's own, so the screen
    that draws it and the function that decides what «Записать» would write are the ones
    that already exist.
    """
    sheets = catalogue.sheets()
    current = max(sheets, key=lambda item: item.ord) if sheets else None
    default_problems = problems_for(catalogue)

    rows: list = []
    for block in split_blocks(text):
        match = match_student(block.name_text, students)
        sheet = _sheet_by_number(sheets, block.sheet_marker)
        problems = default_problems if sheet is None else problems_for(catalogue, sheet)
        lead = sheet if sheet is not None else current

        rows.append(
            TextRow(
                said=block.said,
                surname_text=block.name_text,
                student_id=match.student_id,
                verdict=match.verdict,
                cells=_annotate_cells(
                    golos.resolve_labels(block.labels, problems),
                    problems,
                    sheets,
                    lead.id if lead is not None else None,
                ),
                alternatives=list(match.alternatives),
                reason=match.reason,
                present_no_marks=block.present_no_marks,
                sheet_id=sheet.id if sheet is not None else None,
                sheet_marker=block.sheet_marker,
            )
        )

    return golos.Draft(
        transcript=(text or "").strip(),
        rows=rows,
        # The field is named for the voice path that introduced it; what it holds is «the
        # digest of whatever arrived», and for this door that is the message itself.
        audio_sha256=digest_of(text),
        channels="нечёткое сопоставление + словарь уменьшительных; схемного разбора нет",
    )


# =============================================================================
#  PART 4 · THE ПРОЧЕРК GOES TO ATTENDANCE, AND NOWHERE ELSE
# =============================================================================
#
# Rule 4 of the задание, and it is a rule about MEANING rather than about parsing: `Влад
# Быков —` is a statement that the child WAS THERE and handed in nothing.  By pluses alone
# that is indistinguishable from truancy, and the difference is the difference between «его
# не спросили» and «его не было» -- which is the whole reason P6 exists.
#
# So a прочерк produces no cells and never touches ``MarkingService``.  It produces an
# attendance intent, written through ``core/services/sessions.py`` with status «был».  P6
# already derives the red line from ``(status, has_marks)`` in ``AttendanceView`` and
# already owns the test that the two states differ; this module feeds that derivation and
# does not restate it.

#: The attendance status a прочерк asserts.  Taken from ``config`` rather than typed, so
#: that the one home of the vocabulary stays the one home.
PRESENT = config.ATTENDANCE_STATUSES[0]

#: Where a mark made on this path came from.  ⚠ «текст» is the honest value and the schema
#: does not yet allow it: ``migrations/001_init.sql`` constrains ``source`` to the four
#: values of ``config.MARK_SOURCES``, and both files are outside this position's zone.  So
#: the fallback below stands in until somebody who owns those files adds the value, at
#: which point this constant starts being used with no edit here.  The provenance is not
#: lost in the meantime -- it is written into the mark's ``note``, which has no such
#: constraint.  Named in ``## ВОПРОСЫ`` with its дом rather than fixed out of zone.
SOURCE = "текст" if "текст" in config.MARK_SOURCES else config.MARK_SOURCES[0]

#: What the ``note`` of every mark from this path says, so that a mark made by typing is
#: still traceable to the typing a year later even while ``SOURCE`` has to borrow a value.
NOTE = "текстовый ввод"


def looks_like_a_record(text: str) -> bool:
    """Is this typed message a record of a lesson at all, or just a message?

    THE HANDLER THAT ANSWERS EVERY TEXT IS A HANDLER THAT STEALS EVERY TEXT.  A teacher
    types «спасибо», «а когда следующее занятие?» and «Петров 3, 5» into the same box, and
    only the third is for this screen.  Registration (P3), the attendance question (P14)
    and the owner's rename (P19) all take plain text too; they are FSM-gated and stand
    above this router, but a router that claimed everything left over would still swallow
    the ordinary sentence and answer it with a confirmation table.

    The test is the format's own: at least one block that carries a NAME and then either a
    problem label or a прочерк.  A sentence has words and no labels; a record has both.
    Deliberately strict rather than clever -- a false negative costs the teacher the
    buttons they already have, a false positive costs everyone the ability to talk to the
    bot at all.
    """
    for block in split_blocks(text):
        if block.name_text and (block.labels or block.present_no_marks):
            return True
    return False


def attendance_intents(draft) -> list:
    """``[student_id, ...]`` -- the children a прочерк says were present.

    A row whose student is unresolved contributes NOTHING, exactly as
    ``bot.routers.photo.checked_cells`` refuses to write a mark for «probably Petya»:
    attendance lands on a child or it does not land.  The teacher answers «кто это?» with
    a tap and the row is counted on the next pass.
    """
    return [
        row.student_id
        for row in getattr(draft, "rows", ())
        if getattr(row, "present_no_marks", False) and row.student_id is not None
    ]
