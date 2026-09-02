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
