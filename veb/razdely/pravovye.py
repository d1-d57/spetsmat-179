#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the routes below are declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI` names this
# module, one line in `veb/server.py`).
"""Privacy policy and terms of use — two static pages, no database, no cookies of their own.

WHY THIS EXISTS.  The owner set up Google authorisation for the nightly database backup
to Drive (`ops/vygruzka_bazy.py`), and the Google Cloud console asked for privacy-policy
and terms-of-use addresses before it would let him proceed — the same two addresses Google
shows a human on the consent screen at the exact moment they decide whether to grant Drive
access.  `http://math-kluychiki.ru/privacy` and `/terms` did not exist; this module is what
answers them.

EVERY SENTENCE ON THESE TWO PAGES IS CHECKED AGAINST THE CODE, NOT COPIED FROM A TEMPLATE.
In particular: the login cookie set by `veb/server.py::_post_vhod` carries a thirty-day
`Max-Age` (`vhod.COOKIE_MAX_AGE_SECONDS`), so it is described here as a thirty-day login
cookie, not as a "session" cookie in the strict sense.

🔴 THE GOOGLE-DRIVE PARAGRAPH WAS REWRITTEN ONCE ALREADY, MID-заход, BECAUSE THE CODE IT
DESCRIBES CHANGED UNDERNEATH IT.  The first draft described `ops/vygruzka_bazy.py`'s then-
current service account (`SCOPES = [".../auth/drive"]`, the full scope).  While this заход
was still running, the sibling заход `bekap-avtorizacia` (zone `ops/`, not this one's)
merged into `main` and replaced that mechanism outright: `ops/vygruzka_bazy.py` now reads
`Credentials.from_authorized_user_file` — the owner's OWN Google account, consented once
through `ops/avtorizacia_drive.py`, not a service account at all — and that заход's own
accepted `## ОТЧЁТ` (`zhurnal/2026-09-02_spetsmat-bot/kod_bekap-avtorizacia.md`, item C)
records the scope it actually runs on: the NARROW `drive.file` ("The заход runs on the
narrow scope. The wide `drive` was never taken, and the owner never had to consent
twice."). The paragraph below was updated to match — service account language and "the
scope is formally wide" language both removed, because both are now false about `main`.
`ops/` stays outside this position's zone; only the PROSE here, which is squarely this
zone's job to keep true, was touched.

WHY A SEPARATE MODULE, AND WHY THIS EXTENSION POINT.  `veb/server.py` already declares
"a section owns its own routes" (see `RAZDELY_S_MARSHRUTAMI` there) for exactly this
situation — a new page that needs no edit to the request-dispatch logic itself, only one
line registering the module.  `veb/vhod.py` is followed here for FORM only (a
self-contained module, `marshruty()`, a handler with no database, no external resource)
— not for its own separate cream-coloured stylesheet, which was a deliberate one-off for
the login form.  The look here instead reuses the SAME CSS custom properties already
defined in `veb/obshchee/karkas.py`'s `:root` block (and mirrored in
`veb/static/priyom.css`), because these two pages are what most visitors and Google's own
reviewer will see coming from the main site or a search result, and "looks like part of
the site" means matching THAT look, not the login form's.

ZERO EXTERNAL SUBREQUESTS, ON PURPOSE.  No `<link>`, no `@font-face`, no image, no script
tag pointing outside this page.  The font names in the stylesheet below (`"Source Sans 3"`,
`"Source Serif 4"`) are the same bare fallback stack `karkas.py` already uses elsewhere in
the codebase — nothing loads them from a network, confirmed by grep before writing this.
"""
from __future__ import annotations

import html


def marshruty():
    """Пути этих двух страниц: {путь: обработчик}. Зовётся сборкой сервера.

    A handler takes the live request handler and returns True when it has answered —
    the contract `veb/server.py` declares above `RAZDELY_S_MARSHRUTAMI`.
    """
    return {"/privacy": stranica_privacy, "/terms": stranica_terms}


# --------------------------------------------------------------------------- обработчики

def stranica_privacy(h) -> bool:
    h._send_html(200, _obolochka("Политика конфиденциальности — Спецмат", _TELO_PRIVACY))
    return True


def stranica_terms(h) -> bool:
    h._send_html(200, _obolochka("Условия использования — Спецмат", _TELO_TERMS))
    return True


# --------------------------------------------------------------------------- содержимое

def e(s: str) -> str:
    return html.escape(s)


_TELO_PRIVACY = f"""
<h1>Политика конфиденциальности</h1>
<p class="podzag">Спецмат — сайт одного математического класса школы №179.</p>

<p>На сайте преподаватели смотрят расписание и отмечают, кто из школьников сдал какие
задачи. Больше он ничего не делает.</p>

<h2>Какие данные мы храним</h2>
<p>Имена и фамилии школьников, кто у кого занимается, номера кабинетов и отметки о
сданных задачах. Больше ничего: ни домашних адресов, ни телефонов, ни платёжных
данных мы не собираем и никогда не собирали.</p>

<h2>Чего на сайте нет</h2>
<p>Рекламы, счётчиков посещаемости и стороннего кода на сайте нет. Эта страница не
обращается ни к одному стороннему адресу — ни за шрифтом, ни за картинкой, ни за
скриптом.</p>

<h2>Куки</h2>
<p>Сайт ставит одну куку — она подтверждает, что человек вошёл как преподаватель или
организатор, и держится тридцать дней, чтобы не вводить пароль заново при каждом заходе на
сайт. Куки, которая бы следила за посетителем, на сайте нет.</p>

<h2>Google Диск</h2>
<p>Раз в сутки сайт делает резервную копию своей базы данных и кладёт её в отдельную
папку на Google Диске владельца — на случай, если сервер выйдет из строя.</p>
<p>Доступ владелец даёт лично, войдя в свой собственный Google-аккаунт, а не через
безликого робота. Разрешение при этом узкое: программа видит только те файлы,
которые сама туда положила, — она не может прочитать даже список остального
содержимого этой папки, не говоря о других файлах на Диске. Раз в сутки она также
удаляет из папки самые старые свои архивы, оставляя примерно две последние недели.</p>

<h2>Кто имеет доступ к данным</h2>
<p>Доступ к данным есть у преподавателей класса — они входят по паролю — и у
владельца сайта, у которого есть доступ к серверу.</p>

<h2>Как связаться</h2>
<p>Вопросы о сайте или о данных — пишите на
<a href="mailto:matfak57@gmail.com">matfak57@gmail.com</a>.</p>
"""

_TELO_TERMS = f"""
<h1>Условия использования</h1>
<p class="podzag">Спецмат — внутренний инструмент одного класса, а не публичный сервис.</p>

<p>Сайтом бесплатно пользуются преподаватели и организаторы одного математического
класса школы №179. Регистрации через сторонние сервисы, оплаты и подписок на нём нет
и не будет.</p>

<h2>Доступность и сохранность данных</h2>
<p>Мы стараемся, чтобы сайт работал без перебоев, но гарантий доступности дать не
можем: сервер может отказать, интернет — пропасть, а данные — потеряться при
поломке. Резервная копия базы данных вне сервера — в закрытой папке на Google
Диске владельца — появилась только сегодня и не защищает от всего; подробнее о
ней — в <a href="/privacy">политике конфиденциальности</a>.</p>

<h2>Кто пользуется сайтом</h2>
<p>Входят по паролю только преподаватели и организаторы класса; посторонним доступа
на сайт нет.</p>

<h2>Данные и третьи лица</h2>
<p>Мы не передаём и не продаём данные школьников никаким третьим лицам — сайт
существует только для внутреннего учёта одного класса.</p>

<h2>Если что-то сломалось</h2>
<p>Сайт перестал работать, показывает не то или потерял данные — напишите
владельцу, разберёмся, что можно восстановить.</p>

<h2>Как связаться</h2>
<p>Вопросы, жалобы, находки — пишите на
<a href="mailto:matfak57@gmail.com">matfak57@gmail.com</a>.</p>
"""


def _obolochka(zagolovok: str, telo: str) -> bytes:
    """Общая рамка обеих страниц: свой стиль, цвета и шрифты — те же переменные, что
    в `veb/obshchee/karkas.py`, никакой внешней загрузки.
    """
    return f"""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(zagolovok)}</title>
<style>
:root{{--bg:#fbfaf6;--panel:#fffdf8;--text:#211f1b;--muted:#726c60;--rule:#e7e2d6;
  --accent:#2f6e8e;--accent-soft:#e8f0f4;
  --sans:"Source Sans 3",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1b1e22;--panel:#23272c;
  --text:#dcd8d0;--muted:#9a948a;--rule:#343a41;--accent:#7fb6d2;--accent-soft:#22333d}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--serif);font-size:19px}}
.menu{{padding:.9rem 3rem;background:var(--panel);border-bottom:1px solid var(--rule);
  font-family:var(--sans)}}
.menu a{{color:var(--muted);text-decoration:none;font-weight:600}}
.menu a:hover{{color:var(--accent)}}
.holst{{padding:1.6rem 3rem 3rem;max-width:44em}}
h1{{font-family:var(--sans);font-size:2rem;font-weight:600;letter-spacing:-.02em;margin:0 0 .3rem}}
h2{{font-family:var(--sans);font-size:1.15rem;font-weight:700;margin:1.9rem 0 .5rem}}
.podzag{{color:var(--muted);font-family:var(--sans);font-size:1.05rem;margin:0 0 1.5rem}}
p{{line-height:1.6;font-size:1.08rem;margin:0 0 1rem}}
a{{color:var(--accent)}}
</style>
<div class="menu"><a href="/">← Спецмат</a></div>
<div class="holst">
{telo}
</div>
</html>""".encode("utf-8")
