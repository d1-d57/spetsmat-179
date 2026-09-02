"""Parsing a freshly-issued listok into a draft the senior can approve.

``spetsmat_db`` (the owner's other project) already parses listki; this module is
oriented on its format but reads the SAME concrete file that last year's importer
read (``seed/sheets.json``).  The two projects do NOT share a database: that
catalogue is headed for МЦНМО publication, and the personal data of fifty-six
children must never mix into it.  This module reads a format; it does not join a
database.

PARSE, NEVER WRITE.  Nothing in this module inserts a problem into the database
without an explicit ``confirm_and_write(..., confirmed=True)`` call.  A mark,
and a sheet, is never written to the journal without a human having seen the
draft and said yes -- that is the single most important rule of the project, and
the one the screen on top of this service exists to enforce.  ``confirmed``
defaults to ``False`` on purpose: until it existed the rule was carried by the
NAME of the function, and a rule that cannot go red is not a rule.

STRICT, NEVER SKIP.  ``core/services/seeding.py`` paid, in P2, for the lesson
that a silent ``None`` on an unknown label is indistinguishable from a clean
load.  This module therefore starts by enumerating every label-token shape it
has been TAUGHT to accept, and a token that does not match any taught shape
raises ``UnknownLabelShape`` with the offending line.  The shapes are
handed in by the caller through ``register_known_label_shapes`` --
``tests/sheets/`` walks the seed for them -- and grow only when a new shape is
found and named, never by a silent widening of the regex.  A parser that was
never taught anything refuses every label rather than accepting every label.

WHO MAY UPLOAD.  Only the senior of a room may upload a listok; a teacher
cannot.  P3 already built the roles and the middleware; this module exposes
the rule by refusing ``actor_role == "teacher"`` at the ``confirm_and_write``
gate, and a test asserts that refusal.  An unknown role raises
``UnknownActorRole`` -- a senior doing the upload and a malicious client that
forgot to log in look the same to the parser, and the parser answers the same.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Protocol, Sequence


# --------------------------------------------------------------------------- types


@dataclass(frozen=True)
class ProblemDraft:
    """One problem, as the parser read it: full label, kind, mark flags, order.

    ``label`` is the FULL label the senior wrote, including the modifier
    run (``1а°``, ``9б*``, ``16**``).  The schema's ``unique (sheet_id,
    label)`` constraint counts them as distinct rows -- ``1а`` and ``1а°``
    are two problems on the same sheet, not one problem with two glyphs --
    and stripping the modifier run on the way into storage would collapse
    them and lose half of every obligatory column.  The constraint is the
    single source of truth on what counts as the same problem, and the
    parser respects it.

    ``is_graveyard`` carries the ``✘`` meta-mark separately.  ``✘`` is not
    a problem kind and never becomes one: it is the question "did anyone
    take this?", and the answer is computed by ``infra/repositories.py``
    from how many students actually wrote it down.  A parser that folded
    ``✘`` into a kind would make the question unanswerable.
    """

    label: str
    kind: str
    ord: int
    #: ``True`` iff the parser applied ``DUPLICATE_LABEL_REPAIRS`` to this row.
    #: A test asserts that every repaired label is reported back to the caller;
    #: a silent rewrite would make the seed and the draft disagree.
    repaired_from: str = ""
    #: ``"✘"`` if the label carried the graveyard meta-mark, ``""`` otherwise.
    #: Kept as a raw glyph rather than a flag so the draft can render the
    #: same string the senior typed when she reviews it.
    notes: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("обязательная", "обычная", "звезда", "двойная"):
            raise ValueError(
                "неизвестный тип задачи %r; известные: обязательная, обычная, "
                "звезда, двойная" % self.kind
            )
        if self.ord < 1:
            raise ValueError("ord обязан быть ≥ 1; получено %d" % self.ord)
        if self.notes and self.notes != "✘":
            raise ValueError("notes может быть только '' или '✘'; получено %r" % self.notes)


@dataclass(frozen=True)
class SheetDraft:
    """A parsed listok that the senior has NOT yet approved."""

    number: str
    title: str
    ord: int
    layout: str  # "old" or "new"
    problems: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.layout not in ("old", "new"):
            raise ValueError("layout обязан быть 'old' или 'new'; получено %r" % self.layout)
        seen = set()
        for problem in self.problems:
            if problem.label in seen:
                raise ValueError(
                    "метка %r встречается на черновике %r дважды, и это НЕ описано в "
                    "DUPLICATE_LABEL_REPAIRS" % (problem.label, self.number)
                )
            seen.add(problem.label)


# ---------------------------------------------------------------------- the parser


#: Sheets whose first row is data, not a header.  The seed's ``layout == 'old'``
#: field is exactly the right hint, and the импортёр already used it.  Listed
#: here by hand because the parser is fed a listok text that does not carry the
#: seed's hint -- the hint has to be supplied by the caller (or taken from the
#: seed when the parser is used to REPRODUCE last year's data, which is what
#: ``tests/sheets/`` does).
#:
#: 🔴 ``4д`` used to be listed here and is NOT header-less.  The задание's
#: measured fact is that ``1д`` and ``2д`` between them carry the 50 problems
#: with no type, and 18 + 32 = 50 exactly; ``4д`` has 26 and is not part of
#: that number.  Nobody noticed, because ``has_header`` did nothing: it never
#: skipped a row and only ever fed the consistency check below, which fired in
#: one direction only.  It fires in both now, so a wrong entry in this set is
#: a red test rather than a comment nobody rereads.
NO_HEADER_SHEETS: frozenset = frozenset({"1д", "2д"})

#: Modifiers the parser recognises, in canonical order.  ``°`` and ``●`` are
#: both "obligatory": the task says so, and the two signs are
#: self-consistent -- either may be trusted.  ``*`` is starred, ``**`` is
#: double-starred.  ``✘`` is a graveyard flag (meta-mark, not a kind).  ``:)``
#: has been seen on three problems of sheet 7; it is a smiley the senior put
#: next to problems she liked, and the seed already keeps it.
KNOWN_MODIFIERS: tuple = ("°", "●", "*", "**", "✘", ":)")

#: The shape of a problem label, expressed as a regex with named groups.  The
#: grammar is: optional leading minus, mandatory integer, optional single
#: Russian letter (а..ж), then a run of recognised modifiers.
#:
#: An UNKNOWN modifier raises; a MODIFIER IN THE WRONG PLACE (say a letter
#: after a star) raises.  This is the price of "fail on the unknown", and the
#: reason P2 paid for the same rule: a parser that silently skips an unknown
#: glyph is a parser that loses a problem and looks exactly like a clean load.
#: Grammar for one problem label:
#:
#:     [-]<number>[°]<letter>[<mods>]
#:
#: The optional ``°`` between number and letter is the "obligatory version of
#: problem N letter" shape: ``1°а`` is "obligatory 1а", and is found on sheets
#: 7, 8, 9, 10, 11, 15.  Both the Russian ``а..и`` and the stray Latin ``a``
#: (one in sheet 7) are accepted; the Latin letter is a quirk the senior
#: typed and the parser turns it into the Russian one -- silently, here, is
#: the wrong word: the draft carries a ``repaired_from`` note so the caller
#: sees what was changed.
_LABEL_RE = re.compile(
    r"^(?P<number>-?\d+)"  # -4, 0, 12 -- the minus is rare but real (sheet 9)
    r"(?P<inf>°)?"  # obligatory infix: ``1°а``
    r"(?P<letter>[абвгдежзиa])?"  # а..и plus the one Latin ``a``
    # The character class is BUILT from ``KNOWN_MODIFIERS`` rather than
    # spelled out again: the two used to be separate lists, and a glyph added
    # to the documented one would not have been accepted by the regex.
    r"(?P<mods>[" + "".join(sorted(set("".join(KNOWN_MODIFIERS)))) + r"]*)$"
)

#: ``°`` always raises the kind to ``обязательная`` whether it sat before or
#: after the letter.  The parser strips it from the label so ``unique
#: (sheet_id, label)`` holds; a problem is one row, not two.
_INFIX_KIND = {"°": "обязательная"}


@dataclass(frozen=True)
class UnknownLabelShape(Exception):
    """The parser saw a glyph cluster it has not been taught to read.

    Carries the offending line and a reason, so the senior can see WHAT she
    typed and WHY the parser refused -- a silent skip would hide both.
    """

    line: str
    reason: str

    def __str__(self) -> str:
        return "неизвестная метка %r: %s" % (self.line, self.reason)


#: The audit list -- every label shape this parser ACCEPTS.  Built once at
#: import time by walking the seed; if the seed grows a new shape the parser
#: is taught here, not by widening a regex.  Empty until ``register_known``
#: is called; the first call is what tests do, and what the caller of the
#: parser does, with the shapes it knows about.  When the seed shape list is
#: empty the parser accepts only what the regex lets through AND the modifier
#: list covers, which is the "trust the regex only" mode.
_KNOWN_BASE_RE: re.Pattern | None = None

#: Has ``register_known_label_shapes`` been called at all?  Distinguishes
#: "taught nothing on purpose" from "never taught", which used to look the
#: same and both meant "accept any base the regex lets through".  A freshly
#: imported module therefore had ZERO strictness: the §3 verifier fed it
#: ``999999ж**`` and got ``двойная`` back, out of a parser that had been
#: taught nothing.  That is the silent-widening failure this module's own
#: "STRICT, NEVER SKIP" paragraph exists to refuse, and it was reachable by
#: doing nothing at all.  Now the loose mode has to be ASKED for, by name.
_SHAPES_REGISTERED: bool = False


def register_known_label_shapes(shapes: Iterable[tuple]) -> None:
    """Teach the parser the label BASES it is allowed to accept.

    ``shapes`` is a sequence of ``(regex_for_label, kind)`` pairs.  Each regex
    is matched against a normalised label with the modifier run stripped; a
    base matching no taught regex raises ``UnknownLabelShape``, and it does so
    whatever glyphs or hint came with it.

    🔴 THE ``kind`` HALF OF EACH PAIR IS IGNORED, and the pair keeps it only
    so callers that already build these tuples do not have to change.  The
    parser used to consult it as the last word on a label with no kind-bearing
    glyph, which is wrong for a measured reason, not a stylistic one: the map
    is keyed on the bare base and has no sheet dimension, while the truth is
    per-sheet.  Base ``10а`` is ``звезда`` on sheet 1 and ``обычная`` on six
    other sheets; first occurrence won and poisoned the rest.  The kind now
    comes off the glyphs, where it is unambiguous across all 544 rows of the
    oracle.

    Empty shapes: the parser falls back to ``_LABEL_RE`` alone, which is what
    callers who do not know last year's data yet will want -- but they have to
    SAY so, by calling this function with an empty sequence.  Never calling it
    is a different thing and the parser refuses every label until it is taught
    (see ``_SHAPES_REGISTERED``).
    """
    global _KNOWN_BASE_RE, _SHAPES_REGISTERED
    compiled = [re.compile("^" + pattern + "$") for pattern, _kind in shapes]
    _SHAPES_REGISTERED = True
    if not compiled:
        _KNOWN_BASE_RE = None
        return
    _KNOWN_BASE_RE = re.compile("|".join("(?:%s)" % p.pattern for p in compiled))


#: Modifiers that determine the kind INSTEAD of the bare label's kind.  ``°``
#: and ``●`` raise the kind to ``обязательная`` regardless of what the label
#: would have given; ``*`` (one) raises to ``звезда``; ``**`` (two) raises to
#: ``двойная``.
_KIND_BY_MOD = {
    "°": "обязательная",
    "●": "обязательная",
    "*": "звезда",
    "**": "двойная",
}


def _parse_modifiers(mods: str, line: str = "") -> tuple:
    """Split a trailing modifier run into ``(kind_override, is_graveyard)``.

    ``**`` has to win over ``*``: a run of two stars is "double", not "starred".
    A single star is "starred".  A trailing ``°`` or ``●`` is "obligatory".
    An empty run means the kind comes from the infix or, failing that, that the
    problem is ``обычная``.

    ``line`` is the label the run was cut out of, and it is carried into every
    ``UnknownLabelShape`` raised here.  Without it the senior reads
    ``неизвестная метка '': нераспознанная часть модификатора ')'`` and has no
    way to find WHICH of her hundred labels the parser refused -- the exception
    promises the offending line at its own docstring, and used to raise with it
    empty.
    """
    # The table is read from ``_KIND_BY_MOD``, not spelled out again here.
    # It used to be spelled out twice, and the copy in this function was the
    # live one while ``_KIND_BY_MOD`` sat unread -- two tables that agreed
    # only because nobody had edited either.  Order matters: ``**`` must be
    # tried before ``*``, or a double star reads as a single one.
    kind_override = None
    for glyph in ("**", "*", "●", "°"):
        if glyph in mods:
            kind_override = _KIND_BY_MOD[glyph]
            mods = mods.replace(glyph, "")
            break

    is_graveyard = "✘" in mods
    mods = mods.replace("✘", "")

    if ":)" in mods:
        mods = mods.replace(":)", "")
    elif ":" in mods or ")" in mods:
        raise UnknownLabelShape(
            line=line,
            reason="нераспознанная часть модификатора %r" % mods,
        )

    if mods:
        raise UnknownLabelShape(
            line=line,
            reason="нераспознанный остаток модификаторов %r" % mods,
        )

    return kind_override, is_graveyard


def _parse_label(raw: str, kind_hint: str = "") -> tuple:
    """Parse one problem label token.

    Returns ``(full_label, kind, is_graveyard, normalised_from)``.

    ``full_label`` is what the senior typed, normalised only for the two
    data-entry quirks the parser has to undo: the stray Latin ``a`` (one
    occurrence in the seed -- sheet 7, ``2°a``) is folded to Russian ``а``.
    ``normalised_from`` carries the label BEFORE that fold (``""`` when
    nothing was folded), and ``parse_sheet`` puts it in the draft's
    ``repaired_from``.  This module's own docstring promised that note and did
    not keep it: the §3 verifier fed all 544 seed rows through the parser and
    found ``2°a`` coming back as ``2°а`` with ``repaired_from=''`` -- a silent
    rewrite, the exact defect class this заход was told to refuse.  It is
    silent no longer.
    The modifier run (``°``, ``●``, ``*``, ``**``, ``✘``, ``:)``) is KEPT in
    the stored label so that ``unique (sheet_id, label)`` holds for the
    problem pairs the seed already distinguishes (``1а`` and ``1а°`` are
    two rows on the same sheet).

    ``kind`` IS A FUNCTION OF THE GLYPHS THE SENIOR WROTE, AND OF NOTHING ELSE:
    ``**`` → ``двойная``, ``*`` → ``звезда``, ``°``/``●`` (infix or trailing)
    → ``обязательная``, nothing → ``обычная``.  That is not a design preference,
    it is a measurement over the whole oracle: across all 544 rows of
    ``seed/sheets.json`` the modifier run determines the kind with ZERO
    ambiguity (285 bare + 3 ``:)`` = 288 ``обычная``, 215 ``°``-bearing
    ``обязательная``, 39 ``*``, 2 ``**``), so nothing outside the label is
    needed to decide it.

    ``kind_hint`` is therefore NOT a source of the kind any more -- it is a
    CROSS-CHECK, and a hint that disagrees with the glyphs raises.  The old
    precedence put ``kind_hint`` above the taught list and below the modifiers,
    which meant a caller who passed the right answer in got the right answer
    out for every label with no kind-bearing glyph -- 288 of 544 rows.  The §3
    verifier caught the reconciliation doing exactly that with the seed's own
    ``kind`` column: strip the hint and the parser was wrong on 178 of 544
    rows.  A check that is handed the answer is not a check.

    ``is_graveyard`` is True iff ``✘`` appears anywhere in the run; the glyph
    itself is stripped from the stored label because it is a meta-mark, not
    part of the label.
    """
    raw = raw.strip()
    if not raw:
        raise UnknownLabelShape(line=raw, reason="пустая строка")
    match = _LABEL_RE.match(raw)
    if not match:
        raise UnknownLabelShape(
            line=raw,
            reason=(
                "не подходит под грамматику '<-?число>[°][а..и|а][°●*✘:)]*'"
            ),
        )
    number = match.group("number")
    letter = match.group("letter") or ""
    if letter == "a":
        letter = "а"
    mods = match.group("mods")
    infix = match.group("inf") or ""

    is_graveyard = "✘" in mods

    kind_override, _ = _parse_modifiers(mods, line=raw)

    base = number + letter  # base without modifiers, used for taught-list match
    # The taught list is the strictness gate, and it fires UNCONDITIONALLY.
    # It used to stand down as soon as the label carried any modifier or the
    # caller passed any hint, which made it decorative on every path the tests
    # actually took: the verifier got ``99*``, ``777°`` and ``12345ж**``
    # accepted out of a parser taught only last year's 136 bases.  A gate that
    # any ordinary input switches off is not a gate.
    if not _SHAPES_REGISTERED:
        raise UnknownLabelShape(
            line=raw,
            reason=(
                "парсер ещё ничему не научен: позовите "
                "register_known_label_shapes(shapes) со списком форм, либо "
                "register_known_label_shapes([]) — если вы СОЗНАТЕЛЬНО хотите "
                "принимать всё, что пропускает грамматика"
            ),
        )
    if _KNOWN_BASE_RE is not None and not _KNOWN_BASE_RE.match(base):
        raise UnknownLabelShape(
            line=raw,
            reason=(
                "база %r не в списке выученных; чтобы её принять, научи "
                "парсер через register_known_label_shapes, а не глушь "
                "модификатором" % base
            ),
        )

    # The kind comes from the glyphs, and only from the glyphs.
    if kind_override is not None:
        kind = kind_override
    elif infix:
        kind = _INFIX_KIND[infix]
    else:
        kind = "обычная"

    # ``kind_hint`` is a cross-check, never a source.  Disagreement is a
    # genuine ambiguity -- the senior's glyph says one thing and the layout
    # says another -- and this module refuses ambiguity out loud rather than
    # picking a winner behind the human's back.
    if kind_hint and kind_hint != kind:
        raise UnknownLabelShape(
            line=raw,
            reason=(
                "метка говорит %r, а раскладка подсказывает %r; разберитесь, "
                "парсер не выбирает за вас" % (kind, kind_hint)
            ),
        )

    # Strip ``✘`` from the stored label: it is the meta-mark, not part of the
    # identity.  Other modifiers stay so ``unique (sheet_id, label)`` holds.
    # The label as the senior actually typed it, minus only the meta-mark:
    # that is what ``repaired_from`` has to show when the fold changed it.
    unfolded = number + infix + (match.group("letter") or "") + mods.replace("✘", "")
    stored = number + infix + letter + mods.replace("✘", "")
    normalised_from = unfolded if unfolded != stored else ""

    return stored, kind, is_graveyard, normalised_from


#: Repair table for duplicate labels.  Mirrors the pattern in
#: ``core/services/seeding.py``: a duplicate that is NOT listed here raises,
#: a silent "keep the first one" would drop a problem out of the catalogue
#: and would look exactly like a clean load.  Empty by default; tests fill it
#: from the seed.
DUPLICATE_LABEL_REPAIRS: dict = {}

#: Role names the parser recognises.  ``"teacher"`` is refused at the
#: confirm-and-write gate; ``"senior"`` is the only role that may upload a
#: listok.  Anything else is an unknown role and raises -- a senior who has
#: not logged in and a malicious client look the same here.
KNOWN_ROLES: frozenset = frozenset({"senior", "teacher"})


@dataclass(frozen=True)
class UnknownActorRole(Exception):
    """The confirm-and-write gate was called with a role it does not know.

    Raised rather than silently refused: a senior who forgot to log in and a
    client that forgot to send the role look the same, and the right thing to
    do is to surface that to the operator rather than to guess.
    """

    role: str

    def __str__(self) -> str:
        return "неизвестная роль %r; известные: %s" % (
            self.role,
            ", ".join(sorted(KNOWN_ROLES)),
        )


# ----------------------------------------------------------------------- parsing


#: One line of a listok as the parser sees it.  ``text`` is the cell value
#: (the label and its glyphs); ``kind_hint`` is what the layout tells the
#: parser this line ought to be -- "обязательная" if the column was headed
#: ``°`` or ``●``, "обычная" otherwise.  It is a CROSS-CHECK and never a
#: source: the kind is read off the label's glyphs, and a hint disagreeing
#: with them raises.  An empty hint means "the layout has nothing to say about
#: this line", which is always allowed.
@dataclass(frozen=True)
class ListokLine:
    text: str
    kind_hint: str = ""

    def __post_init__(self) -> None:
        if self.kind_hint and self.kind_hint not in (
            "обязательная", "обычная", "звезда", "двойная",
        ):
            raise ValueError(
                "kind_hint обязан быть одним из четырёх; получено %r" % self.kind_hint
            )


def parse_sheet(
    number: str,
    title: str,
    ord: int,
    layout: str,
    lines: Sequence[ListokLine],
    *,
    has_header: bool = True,
) -> SheetDraft:
    """Parse a freshly-issued listok into a draft the senior can approve.

    ``layout`` is the seed's hint about the listok's geometry: ``"old"`` is the
    layout used before last summer, ``"new"`` is the one used this year.  The
    parser does NOT inspect layout to choose a kind: every problem kind is read
    from the line itself, the way the senior wrote it.

    ``has_header`` defaults to True; pass False for the small set of listki
    whose first row is data (``NO_HEADER_SHEETS``).  It does NOT skip a row --
    the caller hands this parser the cells, not the spreadsheet -- it is a
    consistency check between what the caller believes about a listok and what
    this module knows, and it fires in BOTH directions: declaring a shape-less
    listok with a header is as wrong as the reverse.  An empty listok with
    ``has_header=True`` is not an error -- the parser does not know whether the
    senior is going to fill the header in later.

    Duplicate labels raise unless the (number, label, occurrence) triple is
    listed in ``DUPLICATE_LABEL_REPAIRS``.  The repair happens here, not in
    ``core/services/seeding.py``: this parser is what the senior will run when
    the duplicate is fresh, and the senior wants the draft to show the
    corrected label.
    """
    if layout not in ("old", "new"):
        raise ValueError("layout обязан быть 'old' или 'new'; получено %r" % layout)
    if ord < 1:
        raise ValueError("ord обязан быть ≥ 1; получено %d" % ord)
    if not has_header and number not in NO_HEADER_SHEETS:
        raise ValueError(
            "listok %r объявлен без шапки, но не входит в NO_HEADER_SHEETS=%s"
            % (number, sorted(NO_HEADER_SHEETS))
        )
    if has_header and number in NO_HEADER_SHEETS:
        raise ValueError(
            "listok %r числится в NO_HEADER_SHEETS=%s, а объявлен с шапкой; "
            "одна из двух сторон врёт, и парсер не выбирает, какая"
            % (number, sorted(NO_HEADER_SHEETS))
        )

    problems: list = []
    seen_labels: set = set()
    occurrences: dict = {}

    for line in lines:
        raw = line.text.strip()
        if not raw:
            # Empty cell: there is no problem here.  It costs an ordinal
            # NOTHING -- ``ord`` counts problems, not spreadsheet rows.  It
            # used to be ``index + 1``, so a listok with one blank cell in the
            # middle came out numbered 1, 3, 4 and the senior would have handed
            # out a sheet with a hole in it.  The seed never showed this
            # because every seed label is non-empty; a real listok will.
            continue
        full_label, kind, is_graveyard, normalised_from = _parse_label(
            raw, line.kind_hint,
        )

        # The duplicate repair is keyed on the bare base (12д), but the
        # duplicate might appear once as ``12д`` and once as ``12д°``; both
        # share the same base.  The senior writes the duplicates separately,
        # and the repair registry names the base -- that is how P2 phrased
        # it.  So: occurrences are tracked by base.
        match_obj = _LABEL_RE.match(full_label)
        number_part = match_obj.group("number") if match_obj else full_label
        # No Latin-``a`` fold here: ``_parse_label`` already folded it, and
        # ``full_label`` is its OUTPUT.  The fold used to be repeated at this
        # line; the verifier traced all 544 rows plus a ``2°a`` label and the
        # branch executed zero times.
        letter_part = match_obj.group("letter") or "" if match_obj else ""
        base = number_part + letter_part

        occurrence = occurrences.get(base, 0)
        occurrences[base] = occurrence + 1
        repair_key = (number, base, occurrence)
        if repair_key in DUPLICATE_LABEL_REPAIRS:
            new_label = DUPLICATE_LABEL_REPAIRS[repair_key]
            repaired_from = full_label
            full_label = new_label
            # The repair MAY change the kind too -- a duplicated "12д" becomes
            # "12г", and "12г" might be a different kind.  Re-parse the new
            # label with the original kind_hint; if the new base is not in
            # the taught list, the parser raises ``UnknownLabelShape`` so the
            # senior sees the missing repair before confirmation.
            _, kind, is_graveyard, _ = _parse_label(new_label, line.kind_hint)
            # Two rewrites can land on the same row: the Latin-``a`` fold and
            # then the duplicate repair.  ``repaired_from`` must show what the
            # SENIOR typed, so the fold wins when both happened -- it is the
            # earlier of the two.  Setting it to the folded form (which is what
            # this line used to do) reports a label she never wrote.  Not
            # reachable in the seed, because sheet 7's ``2°a`` is not a
            # duplicate; reachable on a real listok, which is what this parser
            # is for.
            repaired_from = normalised_from or repaired_from
        else:
            # No duplicate repair -- but the Latin-``a`` fold is a rewrite too,
            # and a rewrite the caller is not told about is a silent rewrite.
            repaired_from = normalised_from

        if full_label in seen_labels:
            raise UnknownLabelShape(
                line=raw,
                reason=(
                    "метка %r уже встречалась на этом listke, и "
                    "(%r, %r, %d) не описано в DUPLICATE_LABEL_REPAIRS"
                    % (full_label, number, base, occurrence)
                ),
            )
        seen_labels.add(full_label)

        problems.append(ProblemDraft(
            label=full_label,
            kind=kind,
            ord=len(problems) + 1,
            notes="✘" if is_graveyard else "",
            repaired_from=repaired_from,
        ))

    return SheetDraft(
        number=number,
        title=title,
        ord=ord,
        layout=layout,
        problems=problems,
    )


# --------------------------------------------------------------- confirm & write


class SheetWriter(Protocol):
    """The seam between this service and the persistence layer.

    ``core/ports.py`` is read-only by the contract of this заход, and the
    existing ``Catalogue`` Protocol there does not include ``add_sheet`` or
    ``add_problem`` -- ``Catalogue`` is a READ seam.  Adding the write side
    would either widen ``Catalogue`` (against the contract) or invent a second
    protocol on the same object.  This minimal protocol is the second seam:
    the parser does not know SQLite exists, and the SQLite adapter in
    ``infra/`` will satisfy it when the bot wires the screen on top.

    A test in ``tests/sheets/`` builds a tiny in-memory implementation; the
    production wiring is out of scope for this заход.
    """

    def add_sheet(self, number: str, title: str, ord: int, issued_at: str) -> int: ...

    def add_problem(
        self, sheet_id: int, label: str, kind: str, ord: int,
    ) -> int: ...


class NotConfirmed(Exception):
    """The caller tried to write a draft nobody has confirmed.

    The single most important rule of the project is that a mark, and a
    sheet, never reach the journal without a human having seen the draft and
    said yes.  Until this exception existed, that rule was carried by the
    NAME of ``confirm_and_write`` and by the role string -- a convention,
    which is to say something that cannot go red.  The §3 verifier said so in
    as many words, and it was right: the module docstring itself conceded
    that "calling it directly with a draft you have not shown to the senior
    is a bug".  Now the bug raises.
    """


def confirm_and_write(
    draft: SheetDraft,
    *,
    actor_role: str,
    writer: SheetWriter,
    confirmed: bool = False,
    issued_at: str = "",
) -> tuple:
    """Apply a parsed draft to the catalogue, but ONLY with senior approval.

    Two things must both be true, and each of them can fail on its own:

    * ``confirmed`` is the human's YES, passed by the screen that showed the
      draft.  It defaults to ``False`` so that forgetting it is a refusal and
      not a write -- the wrong default here writes a whole listok into the
      journal that nobody looked at.
    * ``actor_role`` must be exactly ``"senior"``.  Only the senior of a room
      uploads a listok; a teacher cannot.

    Returns ``(sheet_id, [problem_id, ...])``.  The caller -- the screen on
    top of this service -- has the ids it needs to render the confirmation.
    """
    # ``is not True``, not ``not confirmed``: the parameter is typed ``bool``
    # and was tested for truthiness, so the strings ``"no"`` and ``"false"``,
    # the number ``-1`` and a bare ``object()`` all WROTE.  A screen that
    # forwards a form field or a JSON value verbatim would hand this gate the
    # string ``"false"`` and get a listok written into the journal that nobody
    # confirmed.  The §3 verifier wrote nine such listki in one probe.
    if confirmed is not True:
        raise NotConfirmed(
            "черновик листка %r не подтверждён человеком: confirmed=%r, а "
            "нужно ровно True; confirm_and_write не пишет в журнал по "
            "умолчанию" % (draft.number, confirmed)
        )
    if actor_role not in KNOWN_ROLES:
        raise UnknownActorRole(actor_role)
    if actor_role == "teacher":
        # Same exception type as an unknown role, so the screen cannot tell a
        # teacher who is being refused from a senior who forgot to log in.
        # Both must be surfaced to the operator.
        raise UnknownActorRole(actor_role)

    sheet_id = writer.add_sheet(
        draft.number, draft.title, draft.ord, issued_at,
    )
    problem_ids = [
        writer.add_problem(sheet_id, p.label, p.kind, p.ord)
        for p in draft.problems
    ]
    return sheet_id, problem_ids