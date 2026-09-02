"""THE SECOND CLASS: the template and the code must name the same variable.

``infra/asr.py:260`` read ``SPETSMAT_ASR_KEY``.  ``bot.env.example`` offered
``ASR_API_KEY``.  Nothing crashed and nothing went red: ``build_transcriber`` found
neither name, installed ``FakeTranscriber``, and every dictation came back as the same
canned line.  An owner who filled the template in *correctly* would have had a bot that
looked as if it worked and recognised nothing.

Why this is a test and not a `grep` in the criterion: the criterion's own `diff` compares
every ASR-ish IDENTIFIER in ``infra/asr.py`` against the template, and three of them are
not environment variables at all (``ASR_KEY_ENV`` and ``ASR_FOLDER_ENV`` hold names,
``ASR_TIMEOUT_SECONDS`` is a plain constant).  It can only be made green by writing three
variables nothing reads into the template.  This gate instead derives the names from the
READ -- ``environ.get(X)``, with ``X`` resolved through the module's own constants -- so it
is right about what an environment variable is.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dependency_scan as scanner  # noqa: E402

#: The seams whose configuration the owner is expected to fill in from the template.  Both
#: were dark in battle on 02.09, and for two different reasons at the same time.
CONFIGURED_SEAMS = ("infra/asr.py", "bot/app.py")

#: Every module in this repository that reads the environment at all.  Used for the
#: OTHER direction: a line in the template that nobody reads is a line the owner fills in
#: for nothing -- which is precisely what ``ASR_PROVIDER`` and ``ASR_API_KEY`` were.
EVERY_READER = CONFIGURED_SEAMS + ("config.py", "ops/opoveshchenie.py")


def _read(paths) -> dict:
    found = {}
    for relative in paths:
        for name, line in scanner.env_names_read(scanner.REPO / relative).items():
            found.setdefault(name, "%s:%s" % (relative, line))
    return found


def test_the_template_offers_every_variable_the_recognition_seams_read(capsys):
    """A variable the code reads and the template omits cannot be configured at all."""
    read = _read(CONFIGURED_SEAMS)
    template = scanner.template_names(scanner.REPO / "bot.env.example")
    missing = sorted(set(read) - set(template))

    with capsys.disabled():
        print(
            "\n[имена] переменных читают %s: %d · строк в bot.env.example %d · "
            "нет в шаблоне %d"
            % (", ".join(CONFIGURED_SEAMS), len(read), len(template), len(missing))
        )

    assert read, "ни одного чтения окружения не найдено — гейт ничего не проверил"
    assert not missing, (
        "код читает %d переменн(ую/ых), которых нет в bot.env.example — владелец не может "
        "их настроить:\n%s"
        % (len(missing), "\n".join("  %s — %s" % (name, read[name]) for name in missing))
    )


def test_every_line_of_the_template_is_read_by_something(capsys):
    """A template line nobody reads is the ``ASR_API_KEY`` bug in its pure form."""
    read = _read(EVERY_READER)
    template = scanner.template_names(scanner.REPO / "bot.env.example")
    orphans = sorted(set(template) - set(read))

    with capsys.disabled():
        print(
            "[имена] строк шаблона %d · читающих модулей %d · строк, которых не читает "
            "никто, %d"
            % (len(template), len(EVERY_READER), len(orphans))
        )

    assert template, "шаблон пуст — гейт ничего не проверил"
    assert not orphans, (
        "%d строк(и) bot.env.example не читает ни один из %s — владелец заполнит их "
        "впустую, и голос молча уйдёт в заглушку:\n%s"
        % (
            len(orphans),
            ", ".join(EVERY_READER),
            "\n".join(
                "  %s — bot.env.example:%s" % (name, template[name]) for name in orphans
            ),
        )
    )
