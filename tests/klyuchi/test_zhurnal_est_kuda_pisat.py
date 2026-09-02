"""Точка входа обязана дать логгеру дом ДО того, как кто-нибудь в него напишет.

🔴 ЦЕНА, найдено владельцем 02.09: `basicConfig` не вызывался нигде во всём боевом
коде, у корня уровень WARNING и ноль приёмников, и обе строки, которыми процесс
доказывает включённость распознавания, печатались в пустоту. Тот же класс, что
пустой `BOT_TOKEN` при 486 зелёных тестах: ДОКАЗАТЕЛЬСТВО ЕСТЬ, УВИДЕТЬ НЕЛЬЗЯ.

Тест проверяет не наличие строки в коде, а ПОРЯДОК: журнал настроен РАНЬШЕ, чем
позван `build()`. Поэтому `build` здесь подменяется взрывом — если настройка
стоит после него, до неё не дойдёт очередь, и тест краснеет.
"""
import asyncio
import logging

import pytest


def _obnulit_koren():
    koren = logging.getLogger()
    for h in list(koren.handlers):
        koren.removeHandler(h)
    koren.setLevel(logging.WARNING)


def test_the_entry_point_gives_the_logger_a_home_before_build_speaks(monkeypatch):
    import bot.__main__ as tochka_vhoda

    _obnulit_koren()
    assert not logging.getLogger("bot.app").isEnabledFor(logging.INFO), (
        "корень уже настроен кем-то до теста — проверка недействительна"
    )

    def vzryv(**_):
        raise RuntimeError("build позван — дальше не идём")

    monkeypatch.setattr(tochka_vhoda, "BOT_TOKEN", "123456:AAFakeTokenForTheTestOnly")
    monkeypatch.setattr(tochka_vhoda, "build", vzryv)

    with pytest.raises(RuntimeError):
        asyncio.run(tochka_vhoda._main())

    koren = logging.getLogger()
    assert koren.handlers, "у корневого логгера нет приёмника — записи уходят в пустоту"
    assert logging.getLogger("bot.app").isEnabledFor(logging.INFO), (
        "уровень корня %s: строки «vision on» и про распознаватель речи не напечатаются"
        % logging.getLevelName(koren.getEffectiveLevel())
    )
    print("[журнал] приёмников у корня %d, уровень %s, INFO проходит"
          % (len(koren.handlers), logging.getLevelName(koren.getEffectiveLevel())))
