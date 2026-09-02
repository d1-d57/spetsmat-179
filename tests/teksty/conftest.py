"""Печать охвата сторожа текстов.

`print` внутри зелёного теста pytest проглатывает, а охват обязан быть виден
именно на зелёном: «нарушений 0» без числа проверенных строк неотличимо от
«проверено ноль строк».
"""
from __future__ import annotations


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    from test_teksty import OHVAT

    if not OHVAT:
        return
    terminalreporter.write_line(
        "строк проверено %d из %d, в %d файлах, нарушений %d"
        % (
            OHVAT["vsego"],
            OHVAT["vsego"],
            OHVAT["fajlov"],
            OHVAT["narushenij"],
        )
    )
