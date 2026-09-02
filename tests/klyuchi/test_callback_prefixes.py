"""ГОТОВЫЙ СТОРОЖ, применить после влития P18 → tests/klyuchi/test_callback_prefixes.py

Почему он нужен, хотя дефект найден и починен: гейт классов P20 ЗНАЛ про
столкновение `vy` — печатал абзац «ИЗВЕСТНЫЙ ДЕФЕКТ callback:vy» — и давал
6 passed. Проверка, которая знает о поломке и не краснеет, это надежда.

Замер 02.09 18:5x на живом коде: классов CallbackData 30, столкновение 1
(`vy:1` ← VoiceConfirm, ViewYear). После починки обязано стать 0, а тест —
краснеть, если кто-нибудь снова возьмёт занятый префикс.
"""
import importlib
import inspect
import pathlib

from aiogram.filters.callback_data import CallbackData


def _vse_klassy() -> dict:
    найдено = {}
    for p in sorted(pathlib.Path("bot").rglob("*.py")):
        модуль = str(p.with_suffix("")).replace("/", ".")
        try:
            m = importlib.import_module(модуль)
        except Exception:
            continue
        for _, o in vars(m).items():
            if inspect.isclass(o) and issubclass(o, CallbackData) and o is not CallbackData:
                найдено[o.__module__ + "." + o.__name__] = o
    return найдено


def test_no_two_screens_pack_to_the_same_callback_string():
    """Две кнопки разных экранов не смеют упаковаться в одну строку.

    Порядком включения роутеров это НЕ лечится: кто включён раньше, тот и съедает
    нажатие, а второй экран умирает молча — именно так голосовой черновик не мог
    записать НИКТО (заявка 2026-09-02T1802).
    """
    классы = _vse_klassy()
    assert len(классы) >= 25, "классов найдено %d — сканер перестал их видеть" % len(классы)

    образцы = {}
    for полное, кл in классы.items():
        поля = {
            имя: (1 if "int" in str(поле.annotation) else "x")
            for имя, поле in getattr(кл, "model_fields", {}).items()
        }
        try:
            s = кл(**поля).pack()
        except Exception:
            continue
        образцы.setdefault(s, []).append(полное)

    столкновения = {s: v for s, v in образцы.items() if len(v) > 1}
    print("[callback] классов %d, различных упаковок %d, столкновений %d"
          % (len(классы), len(образцы), len(столкновения)))
    assert not столкновения, "две кнопки дают одну строку: " + "; ".join(
        "%r ← %s" % (s, ", ".join(v)) for s, v in столкновения.items()
    )
