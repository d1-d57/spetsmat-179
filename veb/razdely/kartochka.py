#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — served by `veb/server.py` on `/kartochka/<id>`.
"""The pupil's card: everything the system knows about ONE pupil, on one page.

WHY THIS PAGE EXISTS. Владелец 09.09, after search had led him somewhere odd for
a pupil: «может быть, надо сделать так, чтобы поиск по школьнику выдавал его
полную карточку... карточка должна выдаваться, если ты авторизован... если ты
не авторизован, то поиск должен выдавать только верхнюю часть карточки». This
is that card — the future personal page a pupil will see once they can log in
themselves (`paroli-shkolnikov`, out of this заход's scope by its own STOP
clause); today it differentiates guest from signed-in (organiser or teacher)
instead, which is the same distinction the rest of the site already draws.

🔴 NO SECOND WRITE PATH INTO THE MARK JOURNAL. Ticking a problem posts to the
ALREADY-EXISTING `/api/priyom` (`veb/priyom.py::otmetka`, `MarkingService`
under it) — the same door `veb/priyom.py`'s own grid uses, gated the same way
(any signed-in viewer, per that file). `core/services/progress.py` exposes
reads only (`states_for`/`states_for_many`/`debts`/`grid`/`graveyard`); giving
it a write method would land in `core/services/`, outside this заход's zone
(`veb/razdely/`, `veb/server.py`, `veb/obshchee/`, `tests/veb/`). Calling the
already-public HTTP door from a new page is well inside it.

DESIGN IS INHERITED, NOT INVENTED (`doc/DIZAJN-ZAKREPLENO.md` §0). This is a
standalone page in the shape of `veb/razdely/list_odin.py` — its own
`<!doctype html>`, the site's own stylesheet pulled through
`_obshchij_stil()` — rather than a sixth tab in the shell: a pupil card is not
one of the site's sections and needs none of their radio-tab machinery.
"""
from __future__ import annotations

from veb.obshchee.karkas import e
from core.istochnik import put_bazy
from veb.razdely.list_odin import _obshchij_stil

SVOI_STILI = """
.kartochka{max-width:38em;padding:1.3em 2.4em 2.4em;position:relative}
.kartochka h1{font-family:var(--sans);font-size:1.4em;margin:0 .1em 1.1em 0}
.kartochka .zakryt{position:absolute;top:1.3em;right:1.6em;font-size:1.3em;
  line-height:1;color:var(--muted);text-decoration:none}
.kartochka .zakryt:hover{color:var(--text)}
.kartochka .stroki{display:flex;flex-direction:column;gap:.4em;margin:0 0 1.8em}
.kartochka .stroki .r{display:flex;gap:.7em;line-height:1.4}
.kartochka .stroki .l{color:var(--muted);font-family:var(--sans);font-size:.86em;
  min-width:8.5em;flex:none}
.kartochka .net{color:var(--muted)}
.kond-lich{border-collapse:collapse;width:100%}
.kond-lich td{padding:.3em .6em .3em 0;vertical-align:top}
.kond-lich .nom{font-family:var(--sans);color:var(--faint);white-space:nowrap}
.kond-lich .fishki{line-height:2.1}
.kl{display:inline-block;margin:0 .3em .3em 0;padding:.15em .6em;
  border:1px solid var(--rule);border-radius:6px;font-family:var(--sans);font-size:.92em}
.kl.solved{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.kl.retracted{color:var(--muted);text-decoration:line-through}
button.kl{cursor:pointer;background:var(--panel);font:inherit}
button.kl:disabled{opacity:.5;cursor:wait}
@media(max-width:760px){.kartochka{padding-left:1.1rem;padding-right:1.1rem}}
"""


def _verh(row: dict) -> str:
    """Класс, группа, кабинет, принимающий — то же самое гостю и вошедшему."""
    stroki = [
        ("Класс", e(row["class"]) if row.get("class") else None),
        ("Группа", e(row["gruppa"]) if row.get("gruppa") else None),
        ("Кабинет", e(row["room"]) if row.get("room") else None),
        ("Принимает", e(row["teacher_name"]) if row.get("teacher_name") else None),
    ]

    def stroka(l, v):
        znachenie = v if v else '<span class="net">не назначен</span>'
        return f'<div class="r"><span class="l">{l}</span><span class="v">{znachenie}</span></div>'

    return '<div class="stroki">' + "".join(stroka(l, v) for l, v in stroki) + "</div>"


def _galochki(c, student_id: int, *, mozhno_stavit: bool) -> str:
    """Его задачи: одна строка на листок этого учебного года, ячейка на задачу.

    Читает через `ProgressService` — ровно так же, как уже читают
    `veb/razdely/konduit.py` и `veb/priyom.py`; второго мнения о том, что
    значит клетка, здесь нет.
    """
    from core.services.progress import ProgressService
    from infra.repositories import SqliteCatalogue, SqliteMarkJournal
    from veb.priyom import ZNAK, _listki_goda

    catalogue = SqliteCatalogue(c)
    progress = ProgressService(SqliteMarkJournal(c), catalogue)
    listki = _listki_goda(catalogue.sheets())
    zadachi = {sh.id: catalogue.problems_of_sheet(sh.id) for sh in listki}
    vse_zadachi = [p.id for zad in zadachi.values() for p in zad]
    if not vse_zadachi:
        return '<p class="net">листков этого года ещё нет</p>'
    sostoyaniya = progress.states_for(student_id, vse_zadachi)

    stroki = []
    for sh in listki:
        zad = zadachi[sh.id]
        if not zad:
            continue
        yacheyki = []
        for p in zad:
            sost = sostoyaniya[p.id]
            znak = ZNAK[sost]
            if mozhno_stavit:
                nadpis = f"{e(p.label)} {znak}" if znak else e(p.label)
                yacheyki.append(
                    f'<button class="kl {sost.value}" type="button" '
                    f'data-u="{student_id}" data-z="{p.id}">{nadpis}</button>')
            elif znak:
                yacheyki.append(f'<span class="kl {sost.value}">{e(p.label)} {znak}</span>')
        if not mozhno_stavit and not yacheyki:
            continue
        soderzhimoe = "".join(yacheyki) or '<span class="net">ничего не отмечено</span>'
        stroki.append(f'<tr><td class="nom">{e(sh.number)}</td>'
                      f'<td class="fishki">{soderzhimoe}</td></tr>')
    if not stroki:
        return '<p class="net">ничего не отмечено</p>'
    return f'<table class="kond-lich"><tbody>{"".join(stroki)}</tbody></table>'


#: Тап по клетке — СУЩЕСТВУЮЩАЯ дверь `/api/priyom` (`MarkingService` под ней),
#: тот же контракт `{student, problem, target}`, что и у собственного скрипта
#: `veb/priyom.py`. Второго журнала здесь нет и не будет.
_SKRIPT = r"""<script>
(function(){
  var DALEE = {"empty":"solved","solved":"empty","retracted":"solved"};
  var ZNAK = {"empty":"","solved":"✓","retracted":"x"};
  function podpis(k){ return k.textContent.replace(/\s*[✓x]?\s*$/, ""); }
  function narisovat(k, s){
    k.className = "kl " + s;
    var znak = ZNAK[s];
    k.textContent = podpis(k) + (znak ? " " + znak : "");
  }
  document.addEventListener("click", function(sob){
    var k = sob.target.closest("button.kl[data-u]");
    if(!k) return;
    var bylo = (k.className.match(/\bkl\s+(\S+)/) || [null, "empty"])[1];
    var target = DALEE[bylo] || "solved";
    k.disabled = true;
    fetch("/api/priyom", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({student: +k.dataset.u, problem: +k.dataset.z, target: target})
    }).then(function(r){ return r.json(); }).then(function(otvet){
      k.disabled = false;
      if(otvet && otvet.sostoyanie){ narisovat(k, otvet.sostoyanie); }
      else { k.title = (otvet && otvet.error) || "не записалось"; }
    }).catch(function(oshibka){ k.disabled = false; k.title = "не записалось: " + oshibka; });
  });
})();
</script>"""


def stranica(c, row: dict, *, vhodivshij: bool) -> str:
    """The whole card. `vhodivshij` = signed in (organiser or teacher) — the
    same "who may tick" test `/api/priyom` itself already applies."""
    imya = f'{row["surname"]} {row["name"]}'
    telo = [_verh(row)]
    skript = ""
    if vhodivshij:
        telo.append('<p class="zag2">Задачи</p>')
        telo.append(_galochki(c, row["student_id"], mozhno_stavit=True))
        skript = _SKRIPT
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(imya)} — Ключики</title>
<style>{_obshchij_stil(put_bazy(c))}{SVOI_STILI}</style></head>
<body>
<main class="kartochka">
  <a class="zakryt" href="/raspredelenie" title="закрыть" aria-label="закрыть">&#10005;</a>
  <h1>{e(row["surname"])} {e(row["name"])}</h1>
  {"".join(telo)}
</main>
{skript}
</body></html>"""
