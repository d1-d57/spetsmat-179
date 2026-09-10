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


@pytest.fixture
def koren_vozvrashchayetsya():
    """Снять корневой логгер и ВЕРНУТЬ его как был.

    🔴 ЦЕНА ОТСУТСТВИЯ ВОЗВРАТА, оплачено 02.09 19:0x, 115 ошибок в общем прогоне:
    первая редакция этого файла чистила приёмники корня и не возвращала их. На
    корне висит протоколирование САМОГО pytest, и все последующие тесты, трогающие
    журнал, падали с ошибкой — по отдельности зелёные, вместе красные. Ровно тот
    класс, что уже стоил волне ночи: `conftest` с общим именем модуля (урок 13).
    Тест, портящий глобальное состояние, ломает не себя, а СОСЕДЕЙ.
    """
    koren = logging.getLogger()
    byli, uroven = list(koren.handlers), koren.level
    for h in byli:
        koren.removeHandler(h)
    koren.setLevel(logging.WARNING)
    # 🔴 И ЦИКЛ СОБЫТИЙ ТОЖЕ ВОЗВРАЩАЕМ. `asyncio.run()` закрывает созданный им цикл
    # и НЕ оставляет текущего в потоке; соседние фикстуры (`tests/photo/`) зовут
    # `get_event_loop()` и падают с «There is no current event loop in thread
    # MainThread» — 22 ошибки при 102 пройденных, все в ЧУЖИХ файлах. Замер
    # 02.09 19:0x. Тест, портящий глобальное состояние, ломает не себя, а соседей;
    # первый раз это стоило волне ночи на общем имени модуля `conftest` (урок 13).
    try:
        byl_cikl = asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        byl_cikl = None
    try:
        yield koren
    finally:
        asyncio.set_event_loop(byl_cikl if byl_cikl and not byl_cikl.is_closed()
                               else asyncio.new_event_loop())
        for h in list(koren.handlers):
            koren.removeHandler(h)
        for h in byli:
            koren.addHandler(h)
        koren.setLevel(uroven)


def test_the_entry_point_gives_the_logger_a_home_before_build_speaks(
    monkeypatch, tmp_path, koren_vozvrashchayetsya
):
    import bot.__main__ as tochka_vhoda

    # 🔴 ИСТОЧНИК НАЗЫВАЕТСЯ ДО ЗАПУСКА, ПОТОМУ ЧТО ТАК ТЕПЕРЬ ЗАПУСКАЕТСЯ И БОТ.
    # `_main` передаёт `config.DB_PATH` аргументом в `build`, а аргументы вычисляются
    # ДО вызова — значит без названного источника падает не подменённый `build`, а
    # сам разбор аргументов, и проверка проверяла бы не то. Файла по этому пути нет и
    # не нужно: до открытия базы дело не доходит, `build` подменён на взрыв.
    monkeypatch.setenv("SPETSMAT_BAZA", str(tmp_path / "spetsmat.db"))

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
