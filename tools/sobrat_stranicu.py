#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — зовётся `veb/server.py::_peresobrat` после КАЖДОЙ
# успешной записи в базу, и руками при выкладке статики. Прежний контракт
# `called-by-hand` был верен ровно до появления сервера: снимок старел, пока база
# жила, и внешняя версия расходилась с внутренней.
"""Собирает САМОДОСТАТОЧНУЮ статику по ТЗ 07_TZ-SAJT.md.

Три страницы, меню из трёх пунктов строкой сверху (§1: «может быть, наверху, чтобы
ничего не выезжало»). Текст занимает весь экран.

Данные вмораживаются на момент сборки: Pages отдаёт статику, ей не нужен ни сервер,
ни база, и чтение переживает выключенный ноутбук — в этом смысл разделения (§7).
"""
# Мак владельца несёт Python 3.9, сервер — 3.12. `list | None` в аннотации на 3.9
# исполняется и падает; с этим импортом аннотации не вычисляются вовсе, и один и
# тот же файл работает в обоих местах. Проверено запуском на обоих.
from __future__ import annotations

import html
import pathlib
import sqlite3
import sys

KOREN = pathlib.Path(__file__).resolve().parent.parent
DATA = KOREN / "data" / "spetsmat.db"
VYHOD = KOREN / "docs" / "index.html"
# 🔴 ЛИСТКИ ИЩУТСЯ ТАМ, КУДА ВЕДУТ ССЫЛКИ. Было `KOREN.parent / "materials" /
# "spetsmat-2026"` — СОСЕДНИЙ репозиторий на маке владельца, которого на сервере
# нет вовсе (`ls /opt/materials` → No such file or directory). Ссылки при этом
# всегда были относительные, вида `href="listki/16A-derevya.pdf"`, то есть от
# `docs/`. Пока сборку звали руками с мака, расхождение не проявлялось; первая же
# пересборка на сервере вычистила бы обе таблицы листков молча — проверка
# существования файла не находила бы НИ ОДНОГО.
MAT = KOREN / "docs"

# 🔴 ДНИ ЗАНЯТИЙ БЕРУТСЯ ИЗ ОДНОГО ДОМА — `veb/sobrat_fajl.py`. Вписанные руками
# `DATA_NA` и `DATA_SLOVAMI` отсюда убраны: их никто не читал, а датой они
# повторяли ту самую строку, которая звала субботу четвергом.
sys.path.insert(0, str(KOREN))
from veb.sobrat_fajl import DNI_ZANYATIJ, blizhajshij_den  # noqa: E402


def e(s):
    return html.escape(str(s if s is not None else ""))


VHOD_SKRIPT = r"""
<div class="okno" id="okno-vhod" hidden>
  <div class="okno-fon" data-zakryt></div>
  <form class="okno-telo" id="forma-vhoda" method="post" action="/vhod">
    <h2>Вход</h2>
    <!-- 🔴 СКРЫТОЕ ИМЯ ПОЛЬЗОВАТЕЛЯ СТОИТ ЗДЕСЬ НЕ ДЛЯ СЕРВЕРА — ОН ЕГО НЕ ЧИТАЕТ.
         Менеджеры паролей сохраняют ПАРУ «логин + пароль» и форму без логина чаще
         всего пропускают молча. С этим полем браузер предлагает запомнить вход и
         подставляет его в следующий раз. Владелец 06.09: «нужно, чтобы после
         входа пароль запоминался автоматически». -->
    <input type="text" name="kto" value="организатор" autocomplete="username"
           readonly hidden aria-hidden="true" tabindex="-1">
    <label for="parol">Пароль организатора</label>
    <input type="password" id="parol" name="parol" required autocomplete="current-password">
    <p class="okno-oshibka" id="vhod-oshibka" hidden>Неверный пароль.</p>
    <div class="okno-knopki">
      <button type="button" class="vtoraya" data-zakryt>Отмена</button>
      <button type="submit" class="glavnaya">ОК</button>
    </div>
  </form>
</div>
<script>
/* ── ВХОД ВСПЛЫВАЮЩИМ ОКНОМ, А НЕ ОТДЕЛЬНОЙ СТРАНИЦЕЙ ───────────────────────────
   Владелец 06.09: «нажимаю Вход — появляется небольшое всплывающее окно для
   пароля, ввожу поверх всего, нажимаю ОК и остаюсь на той же странице».
   Отдельная страница /vhod осталась жива и работает — она нужна как запасной
   путь и как то, куда сервер отправляет неавторизованного; но обычный человек
   её больше не видит. */
(function(){
  const okno = document.getElementById('okno-vhod');
  const forma = document.getElementById('forma-vhoda');
  const pole = document.getElementById('parol');
  const oshibka = document.getElementById('vhod-oshibka');
  if(!okno) return;

  function otkryt(){ okno.hidden = false; oshibka.hidden = true; pole.value=''; pole.focus(); }
  function zakryt(){ okno.hidden = true; }

  document.addEventListener('click', function(ev){
    const knopka = ev.target.closest('[data-otkryt-vhod]');
    if(knopka){ ev.preventDefault(); otkryt(); return; }
    if(ev.target.closest('[data-zakryt]')) zakryt();
  });
  document.addEventListener('keydown', function(ev){
    if(ev.key === 'Escape' && !okno.hidden) zakryt();
  });

  /* 🔴 ФОРМА ОТПРАВЛЯЕТСЯ БРАУЗЕРОМ, А НЕ СКРИПТОМ, И ЭТО ГЛАВНОЕ ЗДЕСЬ.
     Раньше вход шёл через `fetch` с `preventDefault` — и менеджер паролей не
     видел входа вовсе, поэтому не предлагал пароль сохранить и не подставлял
     его потом. Владелец вводил пароль каждый раз заново.

     Обычная отправка это чинит: браузер понимает, что произошёл вход, сервер
     отвечает 302 на `/`, и человек оказывается ровно там же, где был, — то есть
     обещание «остаюсь на той же странице» выполняется и без скрипта. Неверный
     пароль возвращает на `/?vhod=ne-pustil`, и окно открывается снова с ошибкой.

     Скрипт здесь только один: показать окно и запомнить, что оно было открыто. */
  const adres = new URL(location.href);
  if(adres.searchParams.get('vhod') === 'ne-pustil'){
    otkryt();
    oshibka.textContent = 'Неверный пароль.';
    oshibka.hidden = false;
    adres.searchParams.delete('vhod');
    history.replaceState(null, '', adres.pathname + adres.search + adres.hash);
  }
})();
</script>"""


PRAVKA_SKRIPT = r"""
<div class="soob" id="soob"></div>
<script>
/* ── ПРАВКИ НАКАПЛИВАЮТСЯ, СОХРАНЯЕТ КНОПКА ────────────────────────────────────
   Владелец 06.09: «должна быть большая кнопка Сохранить; должна быть возможность
   откатить правки или сохранить; при попытке перезагрузить, если есть
   несохранённые правки, должно выдаваться предупреждение. Это стандартные
   правила». Так и сделано, и это ЗАМЕНА прежнего поведения: раньше каждое
   движение мыши уходило в базу немедленно, и отменить его было нечем.

   🔴 ЭКРАН НЕ ПЕРЕСЧИТЫВАЕТ СЛЕДСТВИЯ ПРАВКИ САМ, И ЭТО НАРОЧНО. Кто в какой
   группе, сколько у кого школьников, куда переехали дети — считает сервер, по
   правилам, которые живут в одном месте. Если бы это же считал и браузер, правил
   стало бы двое, и они разошлись бы — ровно та болезнь, от которой лечится вся
   эта страница. Поэтому правка помечается жёлтым «не сохранено», а после
   «Сохранить» страница перечитывается и показывает то, что в базе. */
(function(){
  const panel = document.getElementById('panel-pravok');
  const schyot = document.getElementById('skolko-pravok');
  const soob = document.getElementById('soob');
  if(!panel) return;

  const pravki = new Map();          // ключ → операция; последняя правка побеждает
  const KLYUCH_VYBORA = 'spetsmat-vybor';

  function slovo(n){
    const sto = n % 100, des = n % 10;
    if(sto > 10 && sto < 20) return 'правок';
    if(des === 1) return 'правка';
    if(des >= 2 && des <= 4) return 'правки';
    return 'правок';
  }
  function obnovit(){
    /* 🔴 КНОПКИ ВСЕГДА НА ВИДУ, В ВЕРХНЕЙ ПАНЕЛИ, И ПРОСТО ГАСНУТ. Кнопка,
       появляющаяся из ниоткуда, не сообщает, что сохранение вообще существует, —
       владелец её искал. А подпись, объясняющая кнопку словами, не нужна вовсе:
       число несохранённых правок стоит на самой кнопке, и этого достаточно. */
    const n = pravki.size;
    const est = n > 0;
    document.getElementById('sohranit').disabled = !est;
    document.getElementById('sbrosit').disabled = !est;
    panel.classList.toggle('est-pravki', est);
    schyot.textContent = est ? ' ' + n : '';
  }
  function pomenyalos(el, klyuch, operacia){
    pravki.set(klyuch, operacia);
    const ryad = el.closest('.para, tr, .shapka');
    if(ryad) ryad.classList.add('tronuto');
    obnovit();
  }

  /* Предупреждение при уходе со страницы — стандартное поведение браузера. */
  window.addEventListener('beforeunload', function(ev){
    if(pravki.size === 0) return;
    ev.preventDefault();
    ev.returnValue = '';
    return '';
  });

  function pomnit(){
    const s = {};
    document.querySelectorAll('input.rd').forEach(i => { if(i.checked) s[i.name] = i.id; });
    try{ sessionStorage.setItem(KLYUCH_VYBORA, JSON.stringify(s)); }catch(err){}
  }
  (function vernut(){
    let s;
    try{ s = JSON.parse(sessionStorage.getItem(KLYUCH_VYBORA) || '{}'); }catch(err){ return; }
    Object.keys(s).forEach(function(k){
      const el = document.getElementById(s[k]);
      if(el) el.checked = true;
    });
  })();

  document.addEventListener('change', function(ev){
    const el = ev.target;
    if(!el.classList || !el.classList.contains('org')) return;
    const sl = +el.dataset.slot;
    if(el.classList.contains('pr-sel')){
      const sid = +el.dataset.sid;
      if(el.value){
        pomenyalos(el, 'shk:' + sid + ':' + sl,
          {put:'/api/enrollment', telo:{student_id:sid, slot:sl, teacher_id:+el.value}});
      }else{
        const gr = el.parentElement.querySelector('.gr-sel');
        pomenyalos(el, 'shk:' + sid + ':' + sl,
          {put:'/api/enrollment', telo:{student_id:sid, slot:sl, teacher_id:null,
                                        gruppa: gr ? gr.value : ''}});
      }
    }else if(el.classList.contains('gr-sel')){
      const sid = +el.dataset.sid;
      const pr = el.parentElement.querySelector('.pr-sel');
      if(pr) pr.value = '';       /* группа сменилась — преподаватель снимается */
      pomenyalos(el, 'shk:' + sid + ':' + sl,
        {put:'/api/enrollment', telo:{student_id:sid, slot:sl, teacher_id:null,
                                      gruppa: el.value}});
    }else if(el.classList.contains('tgr-sel')){
      const tid = +el.dataset.tid;
      pomenyalos(el, 'prep:' + tid,
        {put:'/api/prepodavateli', telo:{deystvie:'gruppa', teacher_id:tid, gruppa:el.value}});
    }else if(el.classList.contains('kab-inp')){
      const k = el.value.trim();
      if(!k){ el.value = el.defaultValue; return; }
      pomenyalos(el, 'kab:' + el.dataset.gruppa + ':' + el.dataset.data,
        {put:'/api/kabinety', telo:{gruppa:el.dataset.gruppa, kabinet:k,
                                    data:el.dataset.data}});
    }
  });

  document.addEventListener('click', function(ev){
    const krest = ev.target.closest('.tabl[data-snyat]');
    if(krest){
      const sid = +krest.dataset.snyat, sl = +krest.dataset.slot;
      krest.classList.add('snyato');
      pomenyalos(krest, 'shk:' + sid + ':' + sl,
        {put:'/api/enrollment', telo:{student_id:sid, slot:sl, teacher_id:null,
                                      gruppa: krest.dataset.gruppa}});
      return;
    }
  });

  document.getElementById('sbrosit').addEventListener('click', function(){
    if(pravki.size === 0) return;
    if(!window.confirm('Отменить ' + pravki.size + ' ' + slovo(pravki.size)
        + ' и вернуть как было?')) return;
    pravki.clear();
    obnovit();
    pomnit();
    location.reload();
  });

  document.getElementById('sohranit').addEventListener('click', async function(){
    if(pravki.size === 0) return;
    const spisok = Array.from(pravki.entries());
    soob.className = 'soob idet';
    soob.textContent = 'сохраняю…';
    for(let i = 0; i < spisok.length; i++){
      const [klyuch, op] = spisok[i];
      soob.textContent = 'сохраняю ' + (i + 1) + ' из ' + spisok.length + '…';
      let otvet, dannye = {};
      try{
        otvet = await fetch(op.put, {method:'POST',
          headers:{'Content-Type':'application/json'}, body: JSON.stringify(op.telo)});
      }catch(err){
        soob.className = 'soob ploho';
        soob.textContent = 'НЕ СОХРАНЕНО: сервер недоступен (' + err + '). '
          + 'Сохранено до этого: ' + i + ' из ' + spisok.length + '.';
        return;
      }
      try{ dannye = await otvet.json(); }catch(err){}
      if(!otvet.ok){
        /* 🔴 ОСТАНАВЛИВАЕМСЯ НА ПЕРВОМ ОТКАЗЕ. Идти дальше значило бы оставить
           половину правок применённой, а человека — в уверенности, что применилось
           всё либо ничего. Сохранённое до отказа названо числом. */
        soob.className = 'soob ploho';
        soob.textContent = 'НЕ СОХРАНЕНО (' + otvet.status + '): '
          + (dannye.error || 'сервер отказал')
          + ' · применено до отказа: ' + i + ' из ' + spisok.length;
        return;
      }
      pravki.delete(klyuch);
    }
    obnovit();
    pomnit();
    location.reload();
  });

  obnovit();
})();
</script>"""


# ─────────────────────────────────────────────────────────────────────────────
# 🔴 УРОВНИ ДОСТУПА. ОДИН САЙТ, ОДИН КАРКАС, НАДСТРОЙКИ СВЕРХУ.
#
# Роль НЕ выбирает вёрстку. Роль выбирает НАБОР ВОЗМОЖНОСТЕЙ, а вёрстку рисует
# один и тот же код для всех. Разница между тем, что видит гость, и тем, что
# видит организатор, — это несколько ДОБАВЛЕННЫХ элементов, а не другая страница.
#
# Почему именно так, а не «страница для админа» отдельным файлом: две страницы
# одного и того же расходятся всегда. Не иногда, а всегда — потому что правку
# вносят в одну, а про вторую вспоминают через неделю. Здесь расходиться нечему.
#
# Как это проверяется машиной, а не вниманием человека: КАЖДЫЙ элемент, который
# существует только благодаря возможности, несёт атрибут `data-org`. Гейт
# `proverit_karkas()` снимает все такие элементы из версии с ролью и сравнивает
# остаток с гостевой ПОБАЙТОВО. Разошлось — значит каркас разъехался, и это
# ошибка сборки, а не вопрос вкуса.
#
# Как сюда добавляется НОВАЯ роль (преподаватель, школьник — они на очереди):
# одной строкой в этот словарь. Ни одна функция отрисовки при этом не меняется.
VOZMOZHNOSTI = {
    "gost": frozenset(),
    "organizator": frozenset({
        "pravit-raspredelenie",   # выпадающие списки вместо текста, крестики
        "pravit-kabinety",        # поля кабинета в шапке группы
        "videt-schyot",           # счётчики нагрузки и числа по группам
        "videt-klass",            # буква класса у школьника
        "pereklyuchat-dni",       # переключатель понедельник/четверг вместо даты
    }),
}


ALL_VOZMOZHNOSTI = frozenset().union(*VOZMOZHNOSTI.values())


def sobrat_html(rezhim: str = "gost", svodka: list | None = None) -> str:
    """Собирает страницу и ВОЗВРАЩАЕТ её. Один рендерер на все уровни доступа.

    🔴 ЗДЕСЬ ЖИВЁТ ГЛАВНОЕ РЕШЕНИЕ ЭТОГО ФАЙЛА: гость и организатор смотрят на
    страницу, порождённую ОДНИМ И ТЕМ ЖЕ кодом. Режим добавляет органы правки в
    те же места, где у гостя стоит текст, и НЕ трогает окружающую разметку.
    Пока рендерера было два — сайт и админка, — они разъезжались: расхождение
    видно было глазом на списке преподавателей, и «привести к похожему виду
    руками» лечило его ровно до следующей правки. Разъехаться нельзя, если код
    один; это и есть проверка «взять блок из гостевой и из админской и сверить».

    `rezhim`: `"gost"` — то, что лежит в `docs/index.html` и что видят все;
    `"admin"` — то же самое плюс выпадающие списки, счётчики и крестики.
    `svodka`: если передан список, в него дописываются строки отчёта сборки.
    """
    # `admin` — старое имя роли организатора, оставлено, чтобы не ломать вызовы.
    rol = "organizator" if rezhim == "admin" else rezhim
    if rol not in VOZMOZHNOSTI:
        raise ValueError("роль: " + " | ".join(sorted(VOZMOZHNOSTI)))
    mogu = VOZMOZHNOSTI[rol]

    def mozhno(vozmozhnost: str) -> bool:
        """Единственный способ спросить про права. Прямых сравнений с ролью нет.

        🔴 СПРАШИВАТЬ НАДО ПРО ВОЗМОЖНОСТЬ, А НЕ ПРО РОЛЬ. `if rol == "organizator"`
        разложенное по двадцати местам — это и есть та самая вторая версия сайта,
        только рассыпанная. Когда придёт роль преподавателя, её надо будет вписать
        в двадцать мест и в одном забыть. Здесь — в один словарь наверху.
        """
        assert vozmozhnost in ALL_VOZMOZHNOSTI, f"неизвестная возможность: {vozmozhnost}"
        return vozmozhnost in mogu

    ADMIN = mozhno("pravit-raspredelenie")   # короткое имя для самых частых мест
    c = sqlite3.connect(DATA)
    c.row_factory = sqlite3.Row

    # 🔴 РАСПРЕДЕЛЕНИЕ ЗАВИСИТ ОТ ДНЯ. Занятия по понедельникам и четвергам, и
    # кабинет у группы в эти дни может быть РАЗНЫЙ. Поэтому строим оба дня сразу,
    # а на странице переключатель; по умолчанию открывается ближайший.
    # 🔴 ДЕНЬ СЧИТАЕТСЯ, А НЕ ВПИСЫВАЕТСЯ. Вписанная руками дата протухает молча:
    # так `2026-09-05` уже звался здесь четвергом, будучи субботой. Ни один гейт
    # этого не видел — вписанная строка всегда согласна сама с собой. Проверяется
    # одной строкой:
    #   python3 -c "from datetime import date;print(date(2026,9,7).weekday())"
    # Оба дня сейчас ОДИНАКОВЫ по составу, и это по-прежнему так. Здесь чинится
    # ИМЯ дня, а не раскладка.
    # 🔴 ПОНЕДЕЛЬНИК И ЧЕТВЕРГ, И ЭТО ПРАВКА ПОДПИСЕЙ, А НЕ ДАННЫХ. В
    # `migrations/003_slot_vmesto_weekday.sql` записано weekday=1 → slot=1,
    # weekday=4 → slot=2, то есть слот 1 — понедельник, слот 2 — четверг, и так уже
    # давно. Отстали только имена дней: код до сих пор звал их четвергом и субботой.
    # `enrollment` не трогается ни строкой.
    # Имена и номера дней НЕ вписаны здесь, а взяты из `veb/sobrat_fajl.DNI_ZANYATIJ` —
    # того самого «одного дома», который этот файл и объявляет. Вписанная копия уже
    # однажды разошлась с домом и печатала на странице неверные дни.
    # 🔴 ВРЕМЯ ЗАНЯТИЙ ЖИВЁТ ЗДЕСЬ, ОДНОЙ СТРОКОЙ НА ДЕНЬ. Раньше оно стояло
    # прямо в разметке расписания, и второе место, где его надо показать (шапка
    # распределения), пришлось бы писать копией — то есть завести вторую правду
    # о том же. Продиктовано владельцем 06.09.
    VREMYA = {"pn": "14:15\u2009—\u200915:55", "cht": "13:10\u2009—\u200915:00"}
    MESYACY = ("января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря")

    def po_russki(iso):
        """`2026-09-07` → `7 сентября`. Дата на странице читается человеком."""
        god, mes, den = (int(x) for x in iso.split("-"))
        return f"{den} {MESYACY[mes - 1]}"

    _dni_po_poryadku = sorted(DNI_ZANYATIJ)          # пн, затем чт
    DNI = {("pn", "cht")[i]: (DNI_ZANYATIJ[w], i + 1, blizhajshij_den(w))
           for i, w in enumerate(_dni_po_poryadku)}
    # 🔴 КАБИНЕТ НА ДЕНЬ, А ЕСЛИ НА ЭТОТ ДЕНЬ ЕЩЁ НЕ НАЗНАЧЕН — ПОСЛЕДНИЙ
    # ИЗВЕСТНЫЙ, И ЭТО ВИДНО. Владелец ставит привязку накануне вечером, поэтому
    # «на послезавтра строки нет» — обычное состояние, а не потеря данных. Голый
    # `where data = ?` в этом состоянии печатал «кабинет не назначен» у всех трёх
    # групп разом, и переезд подписей дней (четверг+суббота → понедельник+четверг)
    # сделал бы это состоянием по умолчанию: строк на новые дни в базе просто нет.
    # Точное совпадение печатается как есть; последний известный несёт `title` с
    # датой, откуда он взят, — читатель обязан отличать одно от другого.
    kabinety_dnya = {}
    otkuda_kabinet = {}
    for kl, (_, _, dat) in DNI.items():
        tochno = {r["gruppa"]: r["kabinet"] for r in c.execute(
            "select gruppa, kabinet from kabinet_na_den where data = ?", (dat,))}
        proshloe = {}
        for r in c.execute("select data, gruppa, kabinet from kabinet_na_den "
                           "where data < ? order by data", (dat,)):
            proshloe[r["gruppa"]] = (r["kabinet"], r["data"])
        svedeno, istochnik = {}, {}
        for kod in ("В", "Д", "Н"):
            if kod in tochno:
                svedeno[kod] = tochno[kod]
            elif kod in proshloe:
                svedeno[kod], istochnik[kod] = proshloe[kod]
        kabinety_dnya[kl] = svedeno
        otkuda_kabinet[kl] = istochnik

    def kab_html(kl, kod):
        """Чип кабинета. Пусто — честное «не назначен», а не выдуманный номер."""
        k = kabinety_dnya[kl].get(kod)
        if not k:
            return '<span class="net">кабинет не назначен</span>'
        ot = otkuda_kabinet[kl].get(kod)
        podpis = (f' title="на этот день ещё не назначен; кабинет с {e(ot)}"'
                  if ot else "")
        klass = "kab staryj" if ot else "kab"
        return f'<span class="{klass}"{podpis}>{e(k)}</span>'

    kabinety = kabinety_dnya["pn"]
    gruppy = {r["kod"]: r["starshij"] for r in c.execute(
        "select kod, starshij from gruppy order by kod")}
    prep = {r["id"]: dict(r) for r in c.execute(
        "select id, name, gruppa from teachers where aktiven = 1")}

    def shkolniki(slot):
        return c.execute("""
            select s.id, s.surname, s.name, s.class, e.teacher_id
            from students s
            left join enrollment e
              on e.student_id = s.id and e.valid_to = '9999-12-31' and e.slot = ?
            where s.status is null or s.status <> 'left'
            order by s.surname, s.name
        """, (slot,)).fetchall()

    shk_dnya = {kl: shkolniki(sl) for kl, (_, sl, _) in DNI.items()}
    shk = shk_dnya["pn"]

    def gr_shk(r, pr=None):
        pr = pr or prep
        t_ = pr.get(r["teacher_id"])
        return t_["gruppa"] if t_ else None

    def kab_shk(r):
        return kabinety.get(gr_shk(r))

    def vybor_prepoda(r, sl, gostevoj_tekst):
        """Выпадающий список преподавателей — там же, где у гостя стоит его имя.

        🔴 `data-gost` НЕСЁТ ТО, ЧТО СТОЯЛО БЫ ЗДЕСЬ У ГОСТЯ. По нему гейт
        `proverit_karkas()` восстанавливает гостевой вид из админского и сверяет
        побайтово. Без этого атрибута «список вместо имени» был бы для машины
        просто расхождением, и проверку пришлось бы делать глазами — то есть
        не делать вовсе.
        """
        # Свои первыми: девять правок из десяти — внутри группы, и чужие не должны
        # попадаться раньше своих (находка из рабочего файла распределения).
        svoi, chuzhie = [], []
        moya = gr_shk(r)
        for x in sorted(prep.values(), key=lambda z: z["name"]):
            (svoi if x.get("gruppa") == moya else chuzhie).append(x)
        opts = ['<option value=""%s>— нет —</option>'
                % (" selected" if not r["teacher_id"] else "")]
        def opt(x):
            vybran = " selected" if x["id"] == r["teacher_id"] else ""
            return f'<option value="{x["id"]}"{vybran}>{e(x["name"])}</option>'
        if svoi:
            opts.append(f'<optgroup label="группа {e(moya or "—")}">'
                        + "".join(opt(x) for x in svoi) + "</optgroup>")
        po_gruppam = {}
        for x in chuzhie:
            po_gruppam.setdefault(x.get("gruppa") or "—", []).append(x)
        for kod in ("В", "Д", "Н"):
            if kod in po_gruppam:
                opts.append(f'<optgroup label="группа {kod}">'
                            + "".join(opt(x) for x in po_gruppam[kod]) + "</optgroup>")
        if "—" in po_gruppam:
            opts.append('<optgroup label="без группы">'
                        + "".join(opt(x) for x in po_gruppam["—"]) + "</optgroup>")
        return (f'<select class="org pr-sel" data-org="pravit-raspredelenie"'
                f' data-gost="{e(gostevoj_tekst)}" data-sid="{r["id"]}" data-slot="{sl}">'
                + "".join(opts) + '</select>')

    def vybor_gruppy(r, sl, tek):
        """Выпадающий список группы. «нигде» — это ВЫБОР, а не пустота."""
        opts = ['<option value=""%s>нигде</option>' % (" selected" if not tek else "")]
        for kod in ("В", "Д", "Н"):
            opts.append('<option value="%s"%s>%s</option>'
                        % (kod, " selected" if tek == kod else "", kod))
        return (f'<select class="org gr-sel" data-org="pravit-raspredelenie"'
                f' data-sid="{r["id"]}" data-slot="{sl}">'
                + "".join(opts) + '</select>')

    def para_shk(r, kl, pokazat_kab=True):
        """Строка «школьник → его преподаватель».

        Гостю — имя преподавателя и кабинет текстом. Организатору — В ТОМ ЖЕ
        МЕСТЕ два выпадающих списка: преподаватель и группа. Буква класса
        (К · И · Л) стоит только у организатора: ребёнку она не нужна, а тому,
        кто раскладывает людей по группам, нужна. Буквы группы у гостя нет —
        решение владельца 06.09: она дублирует кабинет и добавляет шум.
        """
        kab = kabinety_dnya[kl]
        sl = DNI[kl][1]
        t_ = prep.get(r["teacher_id"])
        g = gr_shk(r)
        klass = (f'<span class="kl" data-org="videt-klass"> {e(r["class"])}</span>'
                 if mozhno("videt-klass") and r["class"] else "")
        # 🔴 КАБИНЕТ — ГОСТЮ, НЕ АДМИНУ. Решение владельца 06.09: «на странице,
        # которую видят все, кабинет должен быть виден; на странице только для
        # администраторов номер кабинета не нужен». Тот, кто раскладывает людей,
        # смотрит на людей; кабинет он правит в шапке группы, и только там.
        imya_prepoda = e(t_["name"]) if t_ else "—"
        if ADMIN:
            hvost = (vybor_prepoda(r, sl, imya_prepoda) + vybor_gruppy(r, sl, g))
        else:
            hvost = imya_prepoda
            if pokazat_kab and g and kab.get(g):
                hvost += '<span data-tolko-gost> ' + kab_html(kl, g) + "</span>"
        return (f'<div class="para" data-i="{e((r["surname"] + " " + r["name"]).lower())}">'
                f'<span class="kto"><b>{e(r["surname"])}</b> {e(r["name"])}{klass}</span>'
                f'<span class="komu">{hvost}</span></div>')

    def vybor_gruppy_prepoda(x, sl):
        """Группа преподавателя. Смена — правило, а не побочный эффект.

        Владелец 06.09: преподаватель уходит в другую группу — все его дети
        ОТКРЕПЛЯЮТСЯ и остаются в своих группах, преподаватель приходит в новую
        группу без детей. Само правило исполняет `/api/prepodavateli`, здесь
        только орган.
        """
        pusto = " selected disabled" if not x["gruppa"] else " disabled"
        opts = [f'<option value=""{pusto}>—</option>']
        for kod in ("В", "Д", "Н"):
            opts.append('<option value="%s"%s>%s</option>'
                        % (kod, " selected" if x["gruppa"] == kod else "", kod))
        return (f'<select class="org tgr-sel" data-org="pravit-raspredelenie"'
                f' data-gost="{e(x["gruppa"] or "")}"'
                f' data-tid="{x["id"]}" data-slot="{sl}">'
                + "".join(opts) + '</select>')

    def deti_prepoda(x, ego, sl):
        """Список школьников преподавателя. Крестик = ОТКРЕПИТЬ, и только в админке.

        Ребёнок остаётся в СВОЕЙ группе — поэтому крестик несёт группу самого
        преподавателя, а не пустоту: снятый без группы ребёнок провалился бы в
        «нигде», а его никто никуда не переводил.
        """
        if not ego:
            return '<span class="net">—</span>'
        # \U0001f534 ОДНА И ТА ЖЕ РАЗМЕТКА В ОБОИХ РЕЖИМАХ, И РАЗЛИЧАЕТ ИХ РОВНО
        # ОРГАН ПРАВКИ. Фамилия — всегда `<span class="det">`; у организатора она
        # ЗАВЁРНУТА в кнопку с крестиком, и это единственная разница. Запятые в
        # таблице преподавателей рисует CSS, а не строка — иначе гостевой вариант
        # был бы одним текстовым узлом, админский двадцатью элементами, и «сверить
        # блок списка из гостевой и из админской» стало бы сравнением несравнимого.
        # ТАБЛЕТКИ, А НЕ СТРОКИ, И МЕЛКИМ ШРИФТОМ — приём из рабочего файла
        # распределения владельца. С пятью школьниками обычная строка не влезает
        # и переносится, оставляя дыру; уменьшенная фамилия влезает всегда.
        # Крестик занимает НОЛЬ ширины, пока на таблетку не навели мышь, — поэтому
        # у гостя и у организатора список одинаковой ширины, а не «почти такой же».
        if not ego:
            return '<span class="net">—</span>'
        kuski = []
        for r in ego:
            atr, krest = "", ""
            if ADMIN:
                atr = (f' role="button" tabindex="0"'
                       f' data-snyat="{r["id"]}" data-slot="{sl}"'
                       f' data-gruppa="{e(x["gruppa"] or "")}"')
                krest = ('<span class="x" data-org="pravit-raspredelenie"'
                         ' title="открепить">\u00d7</span>')
            kuski.append(f'<span class="tabl"{atr}>{e(r["surname"])}{krest}</span>')
        return "".join(kuski)

    def para_prep(x, kl, pokazat_gruppu=True):
        """Строка «преподаватель → его школьники».

        🔴 ТОЛЬКО ФАМИЛИИ школьников: с именами строка не влезает (замечание
        владельца 04.09). Группа и кабинет на вкладке ГРУППЫ не печатаются — там
        и так все из одной группы и одного кабинета, это шум.
        """
        kab = kabinety_dnya[kl]
        sl = DNI[kl][1]
        ego = sorted((r for r in shk_dnya[kl] if r["teacher_id"] == x["id"]),
                     key=lambda r: r["surname"])
        redko = ""
        metki = ""
        if pokazat_gruppu:
            if x["gruppa"]:
                metki += f' <span class="gr">{e(x["gruppa"])}</span>'
            if x["gruppa"] and kab.get(x["gruppa"]) and not ADMIN:
                metki += '<span data-tolko-gost> ' + kab_html(kl, x["gruppa"]) + "</span>"
        if mozhno("videt-schyot"):
            metki += '<span class="sch%s" data-org="videt-schyot"> %d</span>' % (
                "" if 3 <= len(ego) <= 4 else " ploho", len(ego))
        deti_html = deti_prepoda(x, ego, sl)
        return (f'<div class="para" data-i="{e(x["name"].lower())}">'
                f'<span class="kto"><b>{e(x["name"])}</b>{redko}{metki}</span>'
                f'<span class="komu deti">{deti_html}</span></div>')

    def vid_vse(kl):
        """Вкладка «школьникам»: ДВА столбца, каждому — его преподаватель.

        🔴 ДВА, А НЕ ТРИ, И ЭТО НЕ ВКУСОВЩИНА. Столько же, сколько в публичной
        версии, — потому что базовая вёрстка у гостя и у организатора обязана
        совпадать. Владелец 06.09, дословно: «если в разделе учеников для версии
        для читателей две колонки — то для версии для администраторов должно быть
        то же самое: те же самые две колонки». Три столбца тут стояли ровно один
        заход и были ошибкой исполнителя.

        Читается ПО СТОЛБЦАМ: фамилии идут сверху вниз внутри столбца, поэтому
        человека находишь по букве, а не просматривая каждую строку.
        """
        deti = shk_dnya[kl]
        pol = (len(deti) + 1) // 2
        return ('<div class="dva">'
                f'<div class="kol">{"".join(para_shk(r, kl) for r in deti[:pol])}</div>'
                f'<div class="kol">{"".join(para_shk(r, kl) for r in deti[pol:])}</div></div>')

    def vid_prepodavateli(kl):
        """Вкладка преподавателей ТАБЛИЦЕЙ: колонки обязаны стоять ровно.

        Порядок владельца: преподаватель · школьники · группа · кабинет —
        кабинет самое неважное и уходит вправо.
        """
        kab = kabinety_dnya[kl]
        sl = DNI[kl][1]
        ryady = []
        for x in sorted(prep.values(), key=lambda z: z["name"]):
            ego = sorted((r for r in shk_dnya[kl] if r["teacher_id"] == x["id"]),
                         key=lambda r: r["surname"])
            deti = deti_prepoda(x, ego, sl)
            k = kab.get(x["gruppa"])
            # 🔴 СЧЁТЧИК — ТОЛЬКО В АДМИНКЕ. Норма 3–4; красным 0, 1, 2 и 5+.
            # Гостю нагрузка преподавателя не нужна и является техническим числом
            # (ТЗ §2.5), а тому, кто раскладывает людей, она и есть главный сигнал.
            schet = ('<td class="tsch%s" data-org="videt-schyot">%d</td>'
                     % ("" if 3 <= len(ego) <= 4 else " ploho", len(ego))) \
                    if mozhno("videt-schyot") else ""
            gr = vybor_gruppy_prepoda(x, sl) if ADMIN else e(x["gruppa"] or "")
            # 🔴 ОБА ДНЯ ВИДНЫ СРАЗУ, У КАЖДОГО ПРЕПОДАВАТЕЛЯ. Владелец 06.09:
            # «„понедельник-четверг“ как текст не нужен, а кнопки нужны… рядом с
            # каждым преподавателем». Общий переключатель дня отвечает на вопрос
            # «что сегодня»; здесь нужен другой — «ходит ли он в этот день вообще».
            #
            # 🔴 ЭТО ПОКА ОТМЕТКА, А НЕ ВЫКЛЮЧАТЕЛЬ, И ВЫГЛЯДИТ ОНА ОТМЕТКОЙ.
            # Признака «преподаватель работает по понедельникам» в базе нет: есть
            # только его школьники по слотам, и отметка честно показывает именно
            # их — закрашена, если в этот день у него кто-то есть. Нарисовать
            # нажимаемую кнопку без своего поля в схеме значило бы поставить
            # выключатель, который ничего не выключает. Это предмет захода про
            # слой занятия, и там же появится настоящее «работает в этот день».
            dni_metki = "".join(
                '<span class="den-metka%s" title="%s">%s</span>' % (
                    "" if any(r["teacher_id"] == x["id"] for r in shk_dnya[k]) else " pusto",
                    e(DNI[k][0]), e(DNI[k][0][:2]))
                for k in DNI)
            ryady.append(
                f'<tr data-i="{e(x["name"].lower())}" data-tid="{x["id"]}">'
                f'<td class="tp"><b>{e(x["name"])}</b></td>'
                f'<td class="td-deti">{deti}</td>'
                + f'<td class="tdni">{dni_metki}</td>'
                + schet
                + f'<td class="tg">{gr}</td>'
                + (f'<td class="tk"><span data-tolko-gost>{kab_html(kl, x["gruppa"])}'
                   f'</span></td>' if k and not ADMIN else '<td class="tk"></td>')
                + '</tr>')
        return '<table class="prep-tab"><tbody>' + "".join(ryady) + '</tbody></table>'
    def vkladka_gruppy(kod, kl):
        """Группа: слева школьники, справа преподаватели, служебное — ВНИЗУ.

        🔴 ШАПКИ НАВЕРХУ БОЛЬШЕ НЕТ, И ЭТО РЕШЕНИЕ ВЛАДЕЛЬЦА 06.09. Там стояли
        имя старшего и числа «преподавателей 6 · школьников 20» — и то и другое
        он назвал лишним в самом заметном месте экрана: «и так понятно, кто
        руководитель… надо вынести». Верхняя строка отдана тому, ради чего сюда
        пришли, — спискам.

        Служебное переехало ПОД список преподавателей, в свою рамку: числа, а у
        организатора ещё и поля кабинета на оба дня. Оно нужно, но не первым.
        """
        star = gruppy[kod]
        kab = kabinety_dnya[kl].get(kod)
        deti = [r for r in shk_dnya[kl] if gr_shk(r) == kod]
        svoi = sorted((x for x in prep.values() if x["gruppa"] == kod),
                      key=lambda x: x["name"])
        sl = DNI[kl][1]

        if mozhno("pravit-kabinety"):
            # 🔴 КАБИНЕТЫ — ДВУМЯ ПОЛЯМИ, ПОНЕДЕЛЬНИК И ЧЕТВЕРГ, НА ОДНОМ ЭКРАНЕ.
            # Владелец: «у каждой аудитории должно быть два поля — понедельник и
            # четверг». Правят их вместе, накануне вечером; перещёлкивать день
            # ради второго поля — лишний ход. Это ЕДИНСТВЕННОЕ место, где кабинет
            # вводится: в списках распределения у организатора его нет вовсе.
            polya = "".join(
                f'<label class="kab-pole">{e(DNI[k][0])}'
                f'<input class="org kab-inp" data-gruppa="{e(kod)}"'
                f' data-data="{e(DNI[k][2])}"'
                f' value="{e(kabinety_dnya[k].get(kod) or "")}"'
                f' size="5" placeholder="—"></label>'
                for k in DNI)
            nizhnyaya = ('<div class="gruppa-niz" data-org="pravit-kabinety">'
                         f'<span class="gruppa-cifry">старший <b>{e(star)}</b>'
                         f' · преподавателей {len(svoi)} · школьников {len(deti)}</span>'
                         f'<span class="kab-polya">кабинет {polya}</span></div>')
        else:
            nizhnyaya = ('<div class="gruppa-niz" data-tolko-gost>'
                         f'<span class="gruppa-cifry">старший <b>{e(star)}</b></span>'
                         f'<span class="kab-polya">кабинет {kab_html(kl, kod)}</span></div>')

        return ('<div class="dva">'
                + f'<div class="kol">{"".join(para_shk(r, kl, pokazat_kab=False) for r in deti)}</div>'
                + '<div class="kol kol-pr"><div class="prep-ramka">'
                + "".join(para_prep(x, kl, pokazat_gruppu=False) for x in svoi)
                + "</div>" + nizhnyaya + "</div>"
                + "</div>")

    # ── ЛИСТКИ ────────────────────────────────────────────────────────────────
    # Номер и название по СМЫСЛУ, а не имя файла. Ведущие нули убраны, слово
    # «ДРАФТ» снято: это готовая версия, а не черновик (слова владельца 04.09).
    # Зачёт стоит ПОСЛЕ листка 10 — им заканчивалось первое полугодие.
    # Числа Фибоначчи не выдавались вовсе, поэтому их на странице нет.
    L8_PERVOE = [
        ("1",  "Постепенно, с первого шага",       "01_Постепенно, с первого шага.pdf"),
        ("2",  "Правило суммы и произведения",     "02_Правило суммы и произведения.pdf"),
        ("3",  "Пары и тройки",                    "03_Пары и тройки.pdf"),
        ("4",  "Ещё раз про сложение и умножение", "04_Еще раз про сложение и умножение.pdf"),
        ("5",  "Биекции",                          "05_Биекции.pdf"),
        ("6",  "Графы",                            "06_Графы.pdf"),
        ("7",  "Множества",                        "07_Множества.pdf"),
        ("8",  "Зоопарк теории графов",            "08_Зоопарк теории графов.pdf"),
        ("9",  "Индукция",                         "09_Индукция.pdf"),
        ("10", "Биномиальные коэффициенты",        "10_Биномиальные коэффициенты.pdf"),
        ("",   "Программа зачёта",                 "Программа зачета.pdf"),
        ("Д1", "Информация",                       "д01_Информация.pdf"),
        ("Д2", "Геометрическое суммирование",      "д02_Геометрическое суммирование.pdf"),
    ]
    L8_VTOROE = [
        ("11", "Соответствия",  "11_Соответствия.pdf"),
        ("12", "Делимость",     "12_Делимость.pdf"),
        ("13", "Остатки",       "13_Остатки.pdf"),
        ("14", "ОТА",           "14_ОТА.pdf"),
        ("15", "Бесконечность", "15_Бесконечность.pdf"),
        ("Д3", "Игры",          "д03_Игры.pdf"),
    ]
    # 9 класс: одна ТЕМА, три версии в одну строку слева направо — A · α · ℵ.
    L9 = [("16", "Деревья", [("A", "16A-derevya.pdf"),
                             ("α", "16α-derevya.pdf"),
                             ("ℵ", "16ℵ-derevya.pdf")])]

    def est(papka, fajl):
        return (MAT / papka).joinpath(fajl).is_file()

    def stroki_8(spisok, papka):
        out = []
        for nom, nazv, fajl in spisok:
            if not est(papka, fajl):
                continue
            out.append(f'<tr><td class="nom">{e(nom)}</td>'
                       f'<td><a href="{papka}/{e(fajl)}">{e(nazv)}</a></td></tr>')
        return "".join(out)

    def stroki_9():
        out = []
        for nom, tema, versii in L9:
            live = [(z, f) for z, f in versii if est("listki", f)]
            if not live:
                continue
            ssylki = " ".join(
                f'<a class="ver" href="listki/{e(f)}">{e(z)}</a>' for z, f in live)
            out.append(f'<tr><td class="nom">{e(nom)}</td>'
                       f'<td>{e(tema)}</td><td class="verstroka">{ssylki}</td></tr>')
        return "".join(out)

    l9 = [f for _, _, vs in L9 for _, f in vs if est("listki", f)]
    l8 = [f for _, _, f in L8_PERVOE + L8_VTOROE if est("listki-8kl", f)]

    zhdut = [r for r in shk if r["teacher_id"] not in prep]

    if svodka is not None:
        svodka.append(f"  режим {rezhim} · школьников {len(shk)} · преподавателей "
                      f"{len(prep)} · ждут назначения {len(zhdut)}")
        svodka.append("  группы: " + " · ".join(f"{k}→{kabinety.get(k,'—')}"
                                                for k in ("В", "Д", "Н")))
        svodka.append(f"  листки: 9кл {len(l9)} · 8кл {len(l8)}")

    # ── ЧТО СТОИТ НА ГЛАВНОЙ ────────────────────────────────────────────────
    # Кабинеты ближайшего занятия — по группам, одной строкой. Неизвестные не
    # выдумываются: их просто нет в строке.
    def _kab_skoro(k):
        est = [(kod, kabinety_dnya[k].get(kod)) for kod in ("В", "Д", "Н")]
        est = [(kod, v) for kod, v in est if v]
        return " · ".join(f'{kod}&nbsp;<b>{e(v)}</b>' for kod, v in est) if est \
            else '<span class="net">кабинеты уточняются</span>'

    # 🔴 ТЕКУЩИЙ ЛИСТОК — САМОЕ ПОЛЕЗНОЕ, ЧТО ЗДЕСЬ МОЖЕТ СТОЯТЬ. Школьник заходит
    # узнать, что решать; всё остальное на главной он уже знает. Берётся ПОСЛЕДНИЙ
    # листок девятого класса, у которого есть хоть один файл на диске, — то есть
    # тот, что выдан. Ни одного файла нет — блока нет вовсе, а не пустая рамка.
    def _tekushchij():
        for nom, tema, versii in reversed(L9):
            zhivye = [(z, f) for z, f in versii if est("listki", f)]
            if zhivye:
                ssylki = " ".join(
                    f'<a class="ver bolshoj" href="listki/{e(f)}">{e(z)}</a>'
                    for z, f in zhivye)
                return ('<div class="listok-blok"><div class="zag2">Сейчас решаем</div>'
                        f'<p class="listok-imya"><span class="listok-nom">{e(nom)}</span>'
                        f' {e(tema)}</p><p class="listok-ver">{ssylki}</p></div>')
        return ""

    kabinety_skoro = _kab_skoro(min(DNI, key=lambda k: DNI[k][2]))
    tekushchij_listok = _tekushchij()

    # ── ПРАВАЯ ЧАСТЬ СТРОКИ ВКЛАДОК ─────────────────────────────────────────
    # 🔴 ГОСТЮ — БЛИЖАЙШЕЕ ЗАНЯТИЕ, А НЕ ПЕРЕКЛЮЧАТЕЛЬ ДНЯ. Владелец 06.09: «для
    # распределения на общей странице не нужна вкладка понедельник и четверг —
    # имеется в виду распределение на ближайшее занятие… лучше написать „7 сентября“
    # и время сразу». Человек, зашедший посмотреть, куда идти, спрашивает «куда мне
    # СЕГОДНЯ», а не «покажи мне четверг».
    #
    # 🔴 ОРГАНИЗАТОРУ ПЕРЕКЛЮЧАТЕЛЬ ОСТАЁТСЯ: он правит оба дня и обязан видеть оба.
    # Это ровно то, что уровни доступа и означают: не другая страница, а другой
    # набор возможностей на том же месте.
    blizh = min(DNI, key=lambda k: DNI[k][2])
    if mozhno("pereklyuchat-dni"):
        zanyatie_verh = (
            '<span class="dni" data-org="pereklyuchat-dni">'
            + "".join(f'<label for="d-{k}">{e(DNI[k][0])}</label>' for k in DNI)
            + "</span>")
    else:
        zanyatie_verh = (
            f'<span class="skoro" data-tolko-gost>{e(po_russki(DNI[blizh][2]))}'
            f' · {e(DNI[blizh][0])} · {VREMYA[blizh]}</span>')

    # 🔴 КАБИНЕТ ГРУППЫ ПЕРЕЕХАЛ НАВЕРХ, В ТУ ЖЕ СТРОКУ. Он занимал отдельную
    # строку под вкладками — ради одного числа. Показывается только на вкладке
    # своей группы; какая вкладка открыта, знает CSS, а не скрипт.
    kabinety_verh = "".join(
        f'<span class="kab-verh kab-verh-{kod}" data-tolko-gost>'
        + kab_html(blizh, kod) + "</span>"
        for kod in ("В", "Д", "Н")) if not ADMIN else ""

    # ── ДАННЫЕ ДЛЯ СТРАНИЦЫ КЛАССА ──────────────────────────────────────────
    # Всё, что можно посчитать, считается из базы. Вписано руками только то, чего
    # в базе нет: кто какой предмет ведёт и кто классный руководитель — этого
    # система не знает и знать пока негде.
    klassy = {}
    for r in shk:
        if r["class"]:
            klassy[r["class"]] = klassy.get(r["class"], 0) + 1

    # 🔴 НЕ-ЛЮДИ ИЗ СПИСКА ВЫКИДЫВАЮТСЯ. В таблице преподавателей живут служебные
    # строки «отсутствует» и «НС» — это не люди, а способ сказать «никого». Дом у
    # этого знания один и он не здесь: `veb/sobrat_fajl.NE_LYUDI`.
    from veb.sobrat_fajl import NE_LYUDI
    vse_prepy = c.execute("select name, aktiven from teachers order by name").fetchall()
    seychas = sorted({r["name"] for r in vse_prepy
                      if r["name"] not in NE_LYUDI and r["aktiven"]},
                     key=lambda s: s.lower())
    ranshe = sorted({r["name"] for r in vse_prepy
                     if r["name"] not in NE_LYUDI and not r["aktiven"]},
                    key=lambda s: s.lower())
    spisok_prepodavatelej = "".join(f"<li>{e(n)}</li>" for n in seychas)
    byvshie_html = ('<div class="zag2 ranshe-zag">Вели раньше</div>'
                    '<ul class="prep-spisok ranshe">'
                    + "".join(f"<li>{e(n)}</li>" for n in ranshe) + "</ul>") if ranshe else ""

    # Кабинеты в подписи расписания: показываем те, что известны, и честно молчим,
    # когда их нет. Владелец назначает их накануне, и «уточняются» — нормальное
    # состояние, а не дефект.
    izvestnye = [f'{kod}&nbsp;{e(kabinety_dnya["pn"][kod])}'
                 for kod in ("В", "Д", "Н") if kabinety_dnya["pn"].get(kod)]
    kabinety_podpis = ("кабинеты: " + " · ".join(izvestnye)) if izvestnye \
        else '<span class="net">кабинеты уточняются</span>'

    # ── ЧЕМ РЕЖИМЫ ОТЛИЧАЮТСЯ, ЦЕЛИКОМ И В ОДНОМ МЕСТЕ ───────────────────────
    # Гость видит кнопку «Вход». Организатор — метку режима, кнопку «Выход» и
    # скрипт правки. Больше ничем: вся остальная разметка у них общая, потому
    # что порождена одним кодом.
    # 🔴 «Вход» ОТКРЫВАЕТ ОКНО, а не уводит на другую страницу. Ссылка на `/vhod`
    # оставлена в `href` нарочно: без JavaScript она по-прежнему работает и ведёт
    # на настоящую страницу входа. Окно — улучшение поверх работающего, а не
    # замена его на то, что ломается при первой же ошибке в скрипте.
    # 🔴 СОХРАНИТЬ И СБРОСИТЬ СТОЯТ РЯДОМ С ВЫХОДОМ, В ВЕРХНЕЙ ПАНЕЛИ. Нижняя
    # плашка убрана: она занимала низ экрана постоянно и объясняла сама себя
    # фразой, которой владелец не поверил ни секунды («правок нет — можно менять
    # распределение»). Кнопке не нужна подпись — ей нужно быть на виду и гаснуть,
    # когда нажимать нечего. Число несохранённых правок стоит на самой кнопке.
    verh_prava = ('<span class="verh-prava" id="panel-pravok">'
                  '<button type="button" id="sbrosit" class="vtoraya" disabled>Сбросить</button>'
                  '<button type="button" id="sohranit" class="glavnaya" disabled>'
                  'Сохранить<span class="schyot-pravok" id="skolko-pravok"></span></button>'
                  '<a class="vhod" href="/vyhod">Выход</a></span>' if ADMIN
                  else '<span class="verh-prava">'
                       '<a class="vhod" href="/vhod" data-otkryt-vhod>Вход</a></span>')
    # Окно входа лежит в странице ВСЕГДА, у обеих ролей: так каркас у них
    # совпадает буквально, и гейту нечего прощать.
    skripty = VHOD_SKRIPT + (PRAVKA_SKRIPT if ADMIN else "")

    return f"""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Спецмат · 9 класс</title>
<style>
:root{{--bg:#fbfaf6;--panel:#fffdf8;--text:#211f1b;--muted:#726c60;--rule:#e7e2d6;
  --accent:#2f6e8e;--accent-soft:#e8f0f4;--warm:#c9743a;--faint:#b7ae9c;--chip:#e7e0d2;
  --krasn:#b3402a;--krasn-fon:rgba(179,64,42,.08);
  --sans:"Source Sans 3",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1b1e22;--panel:#23272c;
  --text:#dcd8d0;--muted:#9a948a;--rule:#343a41;--accent:#7fb6d2;--accent-soft:#22333d;
  --warm:#e0946a;--faint:#6b6f75;--chip:#333a41;
  --krasn:#e8836a;--krasn-fon:rgba(232,131,106,.12)}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--serif);font-size:20px}}
/* Меню — строка сверху: три пункта помещаются, ничего выезжать не должно (§1). */
.menu{{position:sticky;top:0;z-index:40;display:flex;gap:.3rem;align-items:baseline;
  padding:.9rem 3rem;background:var(--panel);border-bottom:1px solid var(--rule);
  font-family:var(--sans);flex-wrap:wrap}}
.menu .im{{font-weight:600;font-size:1.05rem;margin-right:1.6rem;white-space:nowrap}}
.menu label{{cursor:pointer;font-weight:600;font-size:1.05rem;color:var(--muted);
  padding:.35em 1rem;border-radius:8px}}
.menu label:hover{{color:var(--text);background:var(--accent-soft)}}
.holst{{padding:1.3rem 3rem 2rem;max-width:none}}
h1{{font-family:var(--sans);font-size:2.1rem;font-weight:600;letter-spacing:-.02em;margin:0}}
.data{{color:var(--muted);font-family:var(--sans);font-size:1rem;margin:0 0 1.6rem}}
.oblozhka p{{font-size:1.3rem;line-height:1.5;max-width:52em;margin:0 0 .8em}}
.rasp-str{{font-size:1.15rem;padding:.15em 0}}
.raspisanie{{border:1px solid var(--rule);border-radius:10px;padding:1.1rem 1.4rem;
  margin:1.6rem 0 0;background:var(--panel);max-width:52em}}
.zag2{{font-family:var(--sans);font-size:.85rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);margin:0 0 .5em}}
.str,.vid{{display:none}}
#p-start:checked~#s-start,#p-list:checked~#s-list,#p-rasp:checked~#s-rasp{{display:block}}
#p-start:checked~.menu label[for=p-start],#p-list:checked~.menu label[for=p-list],
#p-rasp:checked~.menu label[for=p-rasp]{{color:var(--accent);background:var(--accent-soft)}}
input.rd{{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}}
.tabbar{{display:flex;gap:.25rem;border-bottom:2px solid var(--rule);margin:0 0 1rem;flex-wrap:wrap}}
.tabbar label{{cursor:pointer;font-family:var(--sans);font-weight:600;font-size:1.1rem;
  color:var(--muted);padding:.5rem 1.2rem;border:2px solid transparent;border-bottom:none;
  border-radius:10px 10px 0 0;margin-bottom:-2px}}
.tabbar label:hover{{color:var(--text)}}
{"".join(f"#t-{k}:checked~#v-{k}{{display:block}}#t-{k}:checked~.tabbar label[for=t-{k}]"
         "{color:var(--accent);background:var(--panel);border-color:var(--rule) var(--rule) var(--panel)}"
         for k in ("shk","prep","В","Д","Н"))}
{"".join(f"#l-{k}:checked~#w-{k}{{display:block}}#l-{k}:checked~.tabbar label[for=l-{k}]"
         "{color:var(--accent);background:var(--panel);border-color:var(--rule) var(--rule) var(--panel)}"
         for k in ("9","8"))}
table{{border-collapse:collapse;width:100%;font-size:1.05rem}}
th{{font-family:var(--sans);font-size:.8rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);text-align:left;padding:0 1.1rem .55rem 0;
  border-bottom:1px solid var(--rule)}}
td{{padding:.5rem 1.1rem .5rem 0;border-bottom:1px solid var(--rule);vertical-align:baseline}}
tr:hover td{{background:var(--accent-soft)}}
.kl{{color:var(--muted);font-family:var(--sans);font-size:.9rem}}
.kab.staryj{{background:none;border:1px dashed var(--rule);color:var(--muted)}}
.kab{{font-family:var(--sans);font-weight:600;background:var(--chip);border-radius:7px;
  padding:.1em .55em;white-space:nowrap}}
.gr{{font-family:var(--sans);font-weight:600;color:var(--accent)}}
.pr{{white-space:nowrap}}
.deti{{font-size:.95rem;color:var(--muted);line-height:1.45}}
.ch{{font-family:var(--sans);color:var(--muted);text-align:right;white-space:nowrap}}
.net{{color:var(--warm);font-family:var(--sans);font-size:.95rem}}
.redko{{font-family:var(--sans);font-size:.85rem;color:var(--warm)}}
.shapka{{font-family:var(--sans);font-size:1.15rem;color:var(--muted);margin:0 0 .8rem}}
.zhdut{{border:1px solid var(--warm);border-radius:10px;padding:1rem 1.3rem;margin:0 0 1.8rem}}
.zhdut .zag2{{color:var(--warm)}}
.poisk{{width:100%;max-width:640px;padding:.65em .9em;font:inherit;font-size:1.1rem;
  border:1px solid var(--rule);border-radius:9px;background:var(--panel);color:var(--text);margin:0 0 1.5rem}}
.poisk:focus{{outline:none;border-color:var(--accent)}}
.podskazki{{position:relative;max-width:640px}}
.podskazki.bolshoj{{max-width:none;margin-top:2.2rem}}
.poisk-big{{max-width:none;width:100%;font-size:1.6rem;padding:.85em 1.1em;border-radius:14px}}
.podskazki.bolshoj .spisok{{top:5.2rem;font-size:1.3rem}}
.podskazki.bolshoj .spisok div{{padding:.6em 1.1em}}
#nashli{{max-width:none;font-size:1.5rem;line-height:1.45;margin-top:1.6rem}}
.otvet{{width:100%;padding:1rem 1.2rem;border:1px solid var(--rule);border-radius:12px;
  background:var(--panel);color:var(--text)}}
.spisok{{position:absolute;left:0;right:0;top:3.1rem;z-index:20;background:var(--panel);
  border:1px solid var(--rule);border-radius:0 0 9px 9px;max-height:18rem;overflow:auto}}
.spisok div{{padding:.5em .9em;cursor:pointer}}
.spisok div:hover{{background:var(--accent-soft);color:var(--accent)}}
/* ТРИ КОЛОНКИ ВО ВЕСЬ ЭКРАН. Слева и посередине — школьник и его преподаватель,
   справа — преподаватель и его школьники. Разделены вертикальной линией.
   Списками, а не квадратиками: человек ищет свою фамилию по алфавиту. */
.dva{{display:grid;grid-template-columns:1fr 1fr;gap:0 2.5rem;align-items:start}}
.odin{{max-width:none}}
.kol{{padding-right:2rem;border-right:1px solid var(--rule);min-width:0}}
.kol:last-child{{border-right:none;padding-right:0}}
/* Крупнее и плотнее: пустой половины экрана быть не должно. */
.para{{display:flex;gap:.8rem;align-items:baseline;padding:.34rem 0;flex-wrap:wrap;
  border-bottom:1px solid var(--rule);font-size:1.15rem}}
/* На вкладках групп места больше — там строки крупнее. */
#v-В .para,#v-Д .para,#v-Н .para{{font-size:1.6rem;padding:.48rem 0}}
#v-В .komu,#v-Д .komu,#v-Н .komu{{font-size:1.5rem}}
/* На общей вкладке школьников, наоборот, чуть плотнее — там 54 строки. */
#v-shk .para{{font-size:1.08rem;padding:.26rem 0}}
#v-shk .komu{{font-size:1rem}}
.para .kto{{flex:0 0 auto;min-width:0}}
.para .komu{{margin-left:auto;text-align:right;color:var(--muted);font-family:var(--sans);
  font-size:1.05rem}}
.para .komu.deti{{white-space:normal;text-align:right}}
.para .komu.deti span{{display:inline-block;margin-left:.55rem}}
.kol-pr .para{{padding:.45rem 0}}
.kol-pr .para{{font-size:1.75rem}}
.kol-pr .komu.deti{{font-size:1.55rem}}
.kol-pr .komu.deti span{{margin-left:.7rem}}
/* Запятая между фамилиями рисуется CSS: у гостя и у организатора один и тот же
   элемент `.det`, и разметка обоих режимов отличается ровно кнопкой-органом. */
.zpt:not(:last-child)::after{{content:", "}}
.tabl .zpt:not(:last-child)::after{{content:none}}
/* Кнопка входа — справа в том же меню, тем же шрифтом, что и его пункты. */
.vhod{{margin-left:auto;font-family:var(--sans);font-weight:600;font-size:1.05rem;
  color:var(--accent);text-decoration:none;padding:.35em 1rem;border:1px solid var(--accent);
  border-radius:8px;white-space:nowrap}}
.vhod:hover{{background:var(--accent);color:var(--panel)}}
.rezhim{{font-family:var(--sans);font-weight:600;font-size:.95rem;color:var(--warm);
  margin-left:auto;margin-right:.8rem;white-space:nowrap}}
.rezhim+.vhod{{margin-left:0}}
/* ── ОРГАНЫ ПРАВКИ. Стоят там же, где у гостя текст, и больше нигде. ── */
.org{{font:inherit;font-family:var(--sans);font-size:.95rem;color:var(--text);
  background:var(--panel);border:1px solid var(--rule);border-radius:7px;
  padding:.12em .3em;margin-left:.4rem;max-width:11rem}}
.org:hover,.org:focus{{border-color:var(--accent);outline:none}}
.tsch{{font-family:var(--sans);font-weight:600;text-align:center;width:1%;
  white-space:nowrap;color:var(--muted)}}
.tsch.ploho,.sch.ploho{{color:#c0392b}}
.sch{{font-family:var(--sans);font-weight:600;font-size:.8em;color:var(--muted)}}
/* Крестик = открепить. Появляется по клику на фамилии преподавателя, не раньше:
   восемнадцать всегда видимых крестиков — это приглашение промахнуться. */
/* ── ТАБЛЕТКА ФАМИЛИИ. Приём взят из рабочего файла распределения владельца:
   мелкий шрифт и скруглённая пилюля, чтобы пять школьников влезали в строку
   преподавателя и не переносились, оставляя дыру. Крестик занимает НОЛЬ ширины,
   пока на таблетку не навели мышь, — поэтому у гостя и у организатора список
   ровно одинаковой ширины. Элемент один и тот же; правку добавляет data-org. */
/* Отметки дней у преподавателя: закрашена — в этот день у него есть школьники. */
.tdni{{white-space:nowrap;width:1%;padding-right:1.2rem}}
.den-metka{{display:inline-block;font-family:var(--sans);font-size:.66rem;font-weight:700;
  letter-spacing:.04em;text-transform:uppercase;padding:.1em .34em;border-radius:4px;
  margin-right:.22rem;background:var(--accent-soft);color:var(--accent);
  border:1px solid transparent}}
.den-metka.pusto{{background:none;color:var(--faint);border-color:var(--rule)}}
/* ── БЛИЖАЙШЕЕ ЗАНЯТИЕ И КАБИНЕТ — В СТРОКЕ ВКЛАДОК, а не отдельной полосой. ── */
.tabbar-rasp .zanyatie{{margin-left:auto;align-self:center;display:flex;align-items:center;gap:.3rem}}
.skoro{{font-family:var(--sans);font-size:1rem;color:var(--muted);white-space:nowrap}}
.kab-verh{{display:none;align-self:center;margin-left:.9rem}}
#t-В:checked~.tabbar .kab-verh-В,#t-Д:checked~.tabbar .kab-verh-Д,
#t-Н:checked~.tabbar .kab-verh-Н{{display:inline-block}}
/* ── ГРУППА: преподаватели в рамке, служебное — под ними. ── */
.prep-ramka{{border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);
  padding:.5rem 0}}
.gruppa-niz{{margin-top:1rem;border:1px solid var(--rule);border-radius:11px;
  padding:.7rem 1.1rem;background:var(--panel);display:flex;align-items:center;
  gap:1.2rem;flex-wrap:wrap;font-family:var(--sans);font-size:.98rem;color:var(--muted)}}
.gruppa-niz b{{color:var(--text)}}
.gruppa-cifry{{white-space:nowrap}}
/* Строки списков подсвечиваются под мышкой — видно, на чём стоишь. */
#s-rasp .para:hover{{background:var(--accent-soft);border-radius:6px}}
.prep-tab tr:hover td{{background:var(--accent-soft)}}
/* ── СТРАНИЦА КЛАССА. Ни одного повтора имени сайта: оно стоит наверху. ── */
.klass{{display:grid;grid-template-columns:minmax(0,1fr) 17rem;gap:0 3rem;align-items:start}}
@media(max-width:900px){{.klass{{grid-template-columns:1fr}}}}
/* Ближайшее занятие — самое крупное на странице: за этим и заходят. */
.skoro-blok{{margin:0 0 2.4rem}}
.skoro-den{{font-size:2.6rem;font-weight:600;letter-spacing:-.02em;margin:.1rem 0 0;
  line-height:1.1}}
.skoro-vremya{{font-family:var(--sans);font-size:1.9rem;color:var(--accent);margin:.1rem 0 0}}
.skoro-kab{{font-family:var(--sans);font-size:1.25rem;color:var(--muted);margin:.5rem 0 0}}
.skoro-kab b{{color:var(--text);font-weight:600}}
/* Текущий листок — второе по важности и тоже крупно. */
.listok-blok{{margin:0 0 2.4rem}}
.listok-imya{{font-size:2rem;font-weight:600;margin:.1rem 0 0;line-height:1.15}}
.listok-nom{{color:var(--faint);font-family:var(--sans);margin-right:.5rem}}
.listok-ver{{margin:.7rem 0 0}}
.ver.bolshoj{{font-size:1.2rem;padding:.25em 1em;margin:0 .4rem 0 0}}
.vedut-blok{{margin:0 0 1.5rem}}
.vedut{{width:100%;border-collapse:collapse;font-size:1.2rem;max-width:34rem}}
.vedut td{{border:none;padding:.3rem 0;vertical-align:baseline}}
.vedut .predmet{{color:var(--muted);font-family:var(--sans);font-size:1rem;width:13rem}}
/* Подпись: то, что важно знать, но не первым. */
.podpis{{font-family:var(--sans);font-size:.95rem;color:var(--faint);
  margin:2.5rem 0 0;padding-top:1rem;border-top:1px solid var(--rule)}}
.klass-sboku{{border-left:1px solid var(--rule);padding-left:2rem}}
@media(max-width:900px){{.klass-sboku{{border-left:none;padding-left:0;margin-top:1.5rem}}}}
.prep-spisok{{list-style:none;margin:.4rem 0 0;padding:0;font-size:1.05rem}}
.prep-spisok li{{padding:.2rem 0}}
.prep-spisok.ranshe{{color:var(--muted);font-size:.98rem}}
.ranshe-zag{{margin-top:1.4rem}}
/* ── ЛИСТКИ: восьмой класс двумя столбцами, чтобы не тянуться одной колонкой. ── */
.dva-listka{{display:grid;grid-template-columns:1fr 1fr;gap:0 3rem;align-items:start}}
@media(max-width:900px){{.dva-listka{{grid-template-columns:1fr}}}}
/* Переключатель дня стоит в той же строке, что и вкладки, а не отдельной полосой. */
.tabbar-rasp .dni{{margin-left:auto;display:flex;gap:.25rem;align-self:center}}
.tabbar-rasp .dni label{{font-size:.98rem;padding:.3em .9rem}}
/* ── СТРОКА НЕ ПЕРЕНОСИТСЯ. Перенос был не косметикой, а поломкой: список
   переставал читаться колонкой, и на месте переноса зияла дыра. Причина —
   раздутые выпадающие списки, съедавшие место у фамилии. Лечится тем же, чем
   в рабочем файле распределения: фамилии отдаётся всё оставшееся место, а поля
   получают фиксированную ширину и не растягиваются. */
#s-rasp .para{{flex-wrap:nowrap}}
#s-rasp .para .kto{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
#s-rasp .para .komu{{flex:0 0 auto;white-space:nowrap}}
#s-rasp .para .komu.deti{{flex:1 1 auto;white-space:normal}}
.org.pr-sel{{max-width:10.5rem;flex:0 0 auto}}
.org.gr-sel{{max-width:4.2rem;flex:0 0 auto}}
/* 🔴 НА ТЕЛЕФОНЕ ЗАПРЕТ ПЕРЕНОСА ПРЕВРАЩАЕТСЯ В ГОРИЗОНТАЛЬНУЮ ПРОКРУТКУ.
   Фамилия и два выпадающих списка в 375 пикселей не помещаются никак, и строка
   уезжает за край экрана — то есть лечение узкой колонки на большом экране
   ломает маленький. Поэтому ниже 760 пикселей перенос возвращается: там колонка
   всё равно одна, и разваливать ей нечего. Поймано прогоном в мобильном виде,
   а не рассуждением: `scrollWidth > clientWidth` было истиной. */
@media(max-width:760px){{
  #s-rasp .para{{flex-wrap:wrap}}
  #s-rasp .para .kto{{white-space:normal;overflow:visible;text-overflow:clip}}
  #s-rasp .para .komu{{white-space:normal}}
  .org.pr-sel{{max-width:100%}}
  .kab-polya{{margin-left:0}}
}}
.tabl{{display:inline-flex;align-items:center;gap:0;padding:.14em .55em;
  border:1px solid var(--rule);border-radius:999px;background:var(--panel);
  font-family:var(--sans);font-size:.85rem;line-height:1.25;color:var(--text);
  white-space:nowrap;margin:.12em .3em .12em 0}}
.tabl[data-snyat]{{cursor:pointer}}
.tabl[data-snyat]:hover,.tabl[data-snyat]:focus-visible{{border-color:var(--krasn);
  background:var(--krasn-fon);color:var(--krasn);outline:none}}
.tabl .x{{width:0;overflow:hidden;color:var(--krasn);font-size:1rem;line-height:1;
  transition:width .12s,margin-left .12s}}
.tabl[data-snyat]:hover .x,.tabl[data-snyat]:focus-visible .x{{width:.7em;margin-left:.3em}}
/* Поля кабинета: два дня рядом, оба на одном экране. */
.kab-polya{{margin-left:auto;display:inline-flex;gap:.9rem;align-items:center;flex-wrap:wrap}}
.kab-pole{{display:inline-flex;align-items:center;gap:.4rem;font-size:.95rem;
  color:var(--muted)}}
.kab-pole input{{width:5rem;text-align:center;font-weight:600;font-size:1.05rem}}
.shapka{{display:flex;align-items:baseline;gap:1.2rem;flex-wrap:wrap}}
/* ── ВСПЛЫВАЮЩЕЕ ОКНО ВХОДА ── */
.okno{{position:fixed;inset:0;z-index:100;display:flex;align-items:center;
  justify-content:center;padding:1rem}}
.okno[hidden]{{display:none}}
.okno-fon{{position:absolute;inset:0;background:rgba(0,0,0,.45)}}
.okno-telo{{position:relative;background:var(--panel);border:1px solid var(--rule);
  border-radius:14px;padding:1.6rem 1.8rem;min-width:min(22rem,92vw);
  box-shadow:0 18px 50px rgba(0,0,0,.3);font-family:var(--sans)}}
.okno-telo h2{{margin:0 0 1rem;font-size:1.35rem;font-weight:600}}
.okno-telo label{{display:block;font-size:.95rem;color:var(--muted);margin:0 0 .35rem}}
.okno-telo input{{width:100%;font:inherit;font-size:1.1rem;padding:.55em .7em;
  border:1px solid var(--rule);border-radius:9px;background:var(--bg);color:var(--text)}}
.okno-telo input:focus{{outline:none;border-color:var(--accent)}}
.okno-oshibka{{color:var(--krasn);font-size:.95rem;margin:.7rem 0 0}}
.okno-knopki{{display:flex;gap:.6rem;justify-content:flex-end;margin-top:1.3rem}}
button.glavnaya,button.vtoraya{{font:inherit;font-family:var(--sans);font-weight:600;
  padding:.5em 1.4em;border-radius:9px;cursor:pointer;border:1px solid var(--rule);
  background:var(--panel);color:var(--text)}}
button.glavnaya{{background:var(--accent);border-color:var(--accent);color:#fff}}
button.glavnaya:hover{{opacity:.88}}
button.vtoraya{{color:var(--muted)}}
button.vtoraya:hover{{color:var(--text)}}
/* ── ПАНЕЛЬ НЕСОХРАНЁННЫХ ПРАВОК ── */
/* ── ВЕРХНЯЯ ПАНЕЛЬ: имя, разделы, поиск, права. Одна строка на всё. ── */
.menu .im{{font-weight:600;font-size:1.05rem;margin-right:1.4rem;white-space:nowrap;
  color:var(--text);padding:0;background:none;cursor:default}}
.menu .im:hover{{background:none}}
.poisk-verh{{flex:1 1 18rem;max-width:34rem;margin:0 1.2rem;min-width:10rem}}
.poisk-verh .poisk{{margin:0;font-size:1rem;padding:.42em .8em;width:100%}}
.poisk-verh .spisok{{top:2.6rem}}
.poisk-verh #nashli{{position:absolute;left:0;right:0;top:2.6rem;z-index:19}}
.verh-prava{{display:flex;align-items:center;gap:.5rem;margin-left:auto;white-space:nowrap}}
.verh-prava button{{padding:.38em 1em;font-size:.98rem}}
.schyot-pravok{{font-variant-numeric:tabular-nums}}
.est-pravki .glavnaya{{box-shadow:0 0 0 3px var(--accent-soft)}}
button.glavnaya[disabled],button.vtoraya[disabled]{{opacity:.45;cursor:default}}
button.glavnaya[disabled]:hover{{opacity:.45}}
/* Панель занимает низ экрана — страница не должна прятать под ней последние строки. */
body{{padding-bottom:2rem}}
/* Тронутое, но не сохранённое — видно глазом и не спутаешь с сохранённым. */
.tronuto{{background:rgba(201,116,58,.10);outline:2px solid rgba(201,116,58,.35);
  outline-offset:2px;border-radius:6px}}
.tabl.snyato{{text-decoration:line-through;opacity:.55}}
/* Ответ сервера человеку. Отказ виден внизу экрана и не пропускается. */
.soob{{position:fixed;left:0;right:0;bottom:0;z-index:60;font-family:var(--sans);
  font-size:1.05rem;padding:.7rem 1.2rem;display:none}}
.soob.idet{{display:block;background:var(--accent-soft);color:var(--text)}}
.soob.ploho{{display:block;background:#c0392b;color:#fff;font-weight:600}}
/* Таблица преподавателей: колонки ровные, кабинет уходит вправо. */
.prep-tab{{width:100%;border-collapse:collapse}}
.prep-tab td{{padding:.55rem .8rem .55rem 0;border-bottom:1px solid var(--rule);
  vertical-align:baseline;font-size:1.75rem}}
.prep-tab .tp{{white-space:nowrap;width:1%;padding-right:2rem}}
.prep-tab .td-deti{{color:var(--muted);font-family:var(--sans);font-size:1.25rem;
  width:auto;padding-right:2rem}}
.prep-tab tr.skryt{{display:none}}
.prep-tab .tg{{font-family:var(--sans);font-weight:600;color:var(--accent);
  text-align:center;width:1%;white-space:nowrap}}
.prep-tab .tk{{text-align:right;width:1%;white-space:nowrap;padding-right:0}}
.para.skryt{{display:none}}
/* Переключатель дня — сверху справа, рядом с заголовком. */
.shapka-str{{display:flex;align-items:baseline;gap:1.5rem;flex-wrap:wrap;margin:0 0 .7rem}}
.dni{{display:flex;gap:.25rem;margin-left:auto}}
.dni label{{cursor:pointer;font-family:var(--sans);font-weight:600;font-size:1.05rem;
  color:var(--muted);padding:.35em 1.1rem;border:1px solid var(--rule);border-radius:9px}}
.dni label:hover{{color:var(--text)}}
#d-pn:checked~.holst .dni label[for=d-pn],
#d-cht:checked~.holst .dni label[for=d-cht],
#d-pn:checked~#s-rasp .dni label[for=d-pn],
#d-cht:checked~#s-rasp .dni label[for=d-cht]{{color:var(--accent);border-color:var(--accent);
  background:var(--accent-soft)}}
.den{{display:none}}
#d-pn:checked~#s-rasp .den-pn,#d-cht:checked~#s-rasp .den-cht{{display:block}}
.poisk-str{{margin:0;max-width:32rem;flex:1 1 18rem}}
@media(max-width:900px){{.dva{{grid-template-columns:1fr}}
  .kol{{border-right:none;padding-right:0}}}}
/* Карточки группы: всё на один экран, колонками — преподаватель и его дети. */
.karty{{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:1rem}}
.kart{{border:1px solid var(--rule);border-radius:10px;padding:.7rem .9rem;background:var(--panel)}}
.kart-z{{display:flex;align-items:baseline;gap:.4rem;font-family:var(--sans);font-size:1rem;
  padding-bottom:.4rem;margin-bottom:.4rem;border-bottom:1px solid var(--rule)}}
.kart-z .ch{{margin-left:auto;color:var(--muted)}}
.kart ul{{list-style:none;margin:0;padding:0}}
.kart li{{font-size:.95rem;padding:.12rem 0}}
.kart.zhd{{border-color:var(--warm)}}
.kart.zhd .kart-z b{{color:var(--warm)}}
/* Листки: номер · название · версии в одну строку. */
.listki{{max-width:46em}}
.listki td{{padding:.4rem 1rem .4rem 0}}
.listki .nom{{font-family:var(--sans);font-weight:600;color:var(--faint);
  width:3.5rem;white-space:nowrap}}
.listki a{{color:var(--accent);text-decoration:none;font-size:1.05rem}}
.listki a:hover{{text-decoration:underline}}
.verstroka{{white-space:nowrap;text-align:right}}
.ver{{display:inline-block;font-family:var(--sans);font-weight:600;background:var(--chip);
  border-radius:7px;padding:.12em .6em;margin-left:.35rem;color:var(--text)!important;
  text-decoration:none!important}}
.ver:hover{{background:var(--accent);color:var(--panel)!important}}
.polug{{font-family:var(--sans);font-size:.85rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);margin:1.8rem 0 .5rem}}
.polug:first-child{{margin-top:0}}
.menu label.im{{font-weight:600;font-size:1.05rem;margin-right:1.6rem;color:var(--text);
  padding-left:0}}
.fajly{{list-style:none;margin:0;padding:0;columns:2;column-gap:3rem}}
.fajly li{{padding:.4em 0;border-bottom:1px solid var(--rule);break-inside:avoid}}
.fajly a{{color:var(--accent);text-decoration:none;font-size:1.05rem}}
@media(max-width:760px){{.menu,.holst{{padding-left:1.1rem;padding-right:1.1rem}}.fajly{{columns:1}}}}
</style>

<input class="rd" type="radio" name="den" id="d-pn" checked>
<input class="rd" type="radio" name="den" id="d-cht">
<input class="rd" type="radio" name="str" id="p-start" checked>
<input class="rd" type="radio" name="str" id="p-list">
<input class="rd" type="radio" name="str" id="p-rasp">

<!-- ВЕРХНЯЯ ПАНЕЛЬ. Имя сайта стоит ОДИН раз и здесь; разделы больше не повторяют
     своё название заголовком внутри себя. Поиск живёт тут же и работает на всех
     разделах — искать надо там, где смотришь, а не там, где нашлось место. -->
<nav class="menu">
  <span class="im">Спецмат&nbsp;· 9&nbsp;класс</span>
  <label for="p-start">Класс</label>
  <label for="p-list">Листки</label>
  <label for="p-rasp">Распределение</label>
  <div class="podskazki poisk-verh">
    <input class="poisk" id="poisk" placeholder="Поиск — школьник, преподаватель, листок" autocomplete="off">
    <div class="spisok" id="spisok" hidden></div>
    <div id="nashli"></div>
  </div>
  {verh_prava}
</nav>

<section class="str holst" id="s-start">
  <!-- 🔴 СВЕРХУ — ТО, ЗА ЧЕМ СЮДА ЗАХОДЯТ, И КРУПНО. Владелец 06.09: «размер
       текста должен занимать большую часть места, и текст должен быть полезным…
       школьникам не важно, что их 53 и что это 179-я школа». Числа класса ушли
       в подпись внизу; наверху — когда занятие, где оно и что сейчас решаем. -->
  <div class="klass">
    <div class="klass-glavnoe">
      <div class="skoro-blok">
        <div class="zag2">Ближайшее занятие</div>
        <p class="skoro-den">{e(po_russki(DNI[blizh][2]))}, {e(DNI[blizh][0])}</p>
        <p class="skoro-vremya">{VREMYA[blizh]}</p>
        <p class="skoro-kab">{kabinety_skoro}</p>
      </div>

      {tekushchij_listok}

      <div class="vedut-blok">
        <div class="zag2">Кто ведёт</div>
        <table class="vedut"><tbody>
          <tr><td class="predmet">алгебра</td><td>Ольга Рыжая</td></tr>
          <tr><td class="predmet">геометрия</td><td>Наталия Стрелкова</td></tr>
          <tr><td class="predmet">спецмат</td><td>Даня Макаров, Ваня Яковлев</td></tr>
          <tr><td class="predmet">классные руководители</td><td>Дарья Аракелова, Радий Юрьевич Скребцов</td></tr>
        </tbody></table>
      </div>
    </div>

    <aside class="klass-sboku">
      <div class="zag2">Преподаватели спецмата</div>
      <ul class="prep-spisok">{spisok_prepodavatelej}</ul>
      {byvshie_html}
    </aside>
  </div>

  <p class="podpis">Школа №&nbsp;179 · математический класс · 9К и 9Л · {len(shk)} школьников</p>
</section>

<section class="str holst" id="s-list">
  <input class="rd" type="radio" name="lst" id="l-8" checked>
  <input class="rd" type="radio" name="lst" id="l-9">
  <div class="tabbar"><label for="l-8">8 класс</label><label for="l-9">9 класс</label></div>
  <section class="vid" id="w-8">
    <div class="dva-listka">
      <div>
        <p class="polug">первое полугодие</p>
        <table class="listki"><tbody>{stroki_8(L8_PERVOE, "listki-8kl")}</tbody></table>
      </div>
      <div>
        <p class="polug">второе полугодие</p>
        <table class="listki"><tbody>{stroki_8(L8_VTOROE, "listki-8kl")}</tbody></table>
      </div>
    </div>
  </section>
  <section class="vid" id="w-9">
    <table class="listki"><tbody>{stroki_9()}</tbody></table>
  </section>
</section>

<section class="str holst" id="s-rasp">
  <!-- Ни заголовка «Распределение», ни отдельной строки под поиск: название
       раздела уже стоит во вкладке наверху, повторять его нечем и незачем.
       Вкладки и переключатель дня — одной строкой. -->
  <input class="rd" type="radio" name="vk" id="t-shk" checked>
  <input class="rd" type="radio" name="vk" id="t-prep">
  <input class="rd" type="radio" name="vk" id="t-В">
  <input class="rd" type="radio" name="vk" id="t-Д">
  <input class="rd" type="radio" name="vk" id="t-Н">
  <div class="tabbar tabbar-rasp">
    <label for="t-shk">школьникам</label><label for="t-prep">преподавателям</label>
    <label for="t-В">В</label><label for="t-Д">Д</label><label for="t-Н">Н</label>
    <span class="zanyatie">{zanyatie_verh}</span>
    {kabinety_verh}
  </div>
  <section class="vid" id="v-shk">
    <div class="den den-pn">{vid_vse("pn")}</div>
    <div class="den den-cht">{vid_vse("cht")}</div>
  </section>
  <section class="vid" id="v-prep">
    <div class="den den-pn">{vid_prepodavateli("pn")}</div>
    <div class="den den-cht">{vid_prepodavateli("cht")}</div>
  </section>
  {"".join(f'<section class="vid" id="v-{k}">'
           f'<div class="den den-pn">{vkladka_gruppy(k, "pn")}</div>'
           f'<div class="den den-cht">{vkladka_gruppy(k, "cht")}</div></section>'
           for k in ("В", "Д", "Н"))}
</section>

<script>
// Поиск ищет и школьника, и преподавателя, подсказывает от двух букв: людей мало.
const IMENA = {[e(f'{r["surname"]} {r["name"]}') for r in shk] + [e(t["name"]) for t in prep.values()]
               + [e(f'{n} {tema}') for n, tema, _ in L9] + [e(f'{n} {nz}') for n, nz, _ in L8_PERVOE + L8_VTOROE if n]!r};
// Что показать по найденному. Для школьника — к кому и куда идти; для
// преподавателя — его группа, старший, кабинет и сколько у него школьников.
const KOMU = {{{",".join(
  [f'"{e(r["surname"])} {e(r["name"])}":"{e(prep[r["teacher_id"]]["name"]) if r["teacher_id"] in prep else "—"} · {e(gr_shk(r) or "—")} · {e(kab_shk(r) or "кабинет не назначен")}"' for r in shk]
+ [f'"{e(n)} {e(tema)}":"листок 9 класса · {" · ".join(z for z, f in vs if est("listki", f))}"' for n, tema, vs in L9]
+ [f'"{e(n)} {e(nz)}":"листок 8 класса"' for n, nz, fl in L8_PERVOE + L8_VTOROE if n and est("listki-8kl", fl)]
+ [f'"{e(t_["name"])}":"{e(", ".join(sorted(r["surname"] + " " + r["name"] for r in shk if r["teacher_id"] == t_["id"])) or "школьников нет")} · {e(t_["gruppa"] or "—")} · {e(kabinety.get(t_["gruppa"]) or "кабинет не назначен")}"' for t_ in prep.values()]
)}}};
const poisk=document.getElementById('poisk'),spisok=document.getElementById('spisok'),nashli=document.getElementById('nashli');
poisk.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase(); nashli.innerHTML='';
  if(q.length<2){{spisok.hidden=true;return;}}
  const r=IMENA.filter(n=>n.toLowerCase().includes(q)).slice(0,8);
  spisok.innerHTML=r.map(n=>'<div>'+n+'</div>').join(''); spisok.hidden=!r.length;
}});
spisok.addEventListener('click',e=>{{
  if(e.target.tagName!=='DIV')return;
  const n=e.target.textContent; poisk.value=n; spisok.hidden=true;
  nashli.innerHTML = KOMU[n] ? '<div class="otvet"><b>'+n+'</b> → '+KOMU[n]+'</div>' : '';
}});
document.addEventListener('click',e=>{{if(!e.target.closest('.podskazki'))spisok.hidden=true;}});

// Поиск на РАСПРЕДЕЛЕНИИ: прячет строки, не совпавшие с фамилией или именем.
// Работает разом во всех вкладках и в обоих днях — искать надо там, где смотришь.
// 🔴 ПО УМОЛЧАНИЮ — БЛИЖАЙШЕЕ ЗАНЯТИЕ. Занятия по понедельникам и четвергам:
// во вторник, среду и четверг ближайшее — четверг, в остальные дни — понедельник.
// Страница статическая, поэтому день выбирается при открытии, а не при сборке.
(function(){{
  const d=new Date().getDay();          // 0 вс · 1 пн · 4 чт
  if(d>=2&&d<=4) document.getElementById('d-cht').checked=true;
}})();

const pr=document.getElementById('poisk-r');
pr.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase();
  document.querySelectorAll('#s-rasp .para, #s-rasp tr[data-i]').forEach(d=>{{
    d.classList.toggle('skryt', !!q && !d.dataset.i.includes(q) &&
      !d.textContent.toLowerCase().includes(q));
  }});
}});
</script>
{skripty}
"""


# 🔴 ГВОЗДЬ. ГЕЙТ, КОТОРЫЙ НЕ ДАЁТ КАРКАСУ РАЗЪЕХАТЬСЯ.
#
# Требование владельца 06.09, дословно: «они должны быть склеены… это не должно
# различаться — мы не должны за этим следить, это должно быть прибито гвоздями».
# Следить и не надо: за этим следит машина, на каждой сборке.
#
# КАК ЭТО РАБОТАЕТ. Из страницы с ролью снимается всё, что добавлено
# ВОЗМОЖНОСТЬЮ, — и остаток обязан совпасть с гостевой страницей ПОБАЙТОВО.
# Снимается ровно три вещи, и список закрытый:
#   1. элементы с `data-org` — их у гостя нет вовсе (крестик, счётчик, поля);
#   2. `<select data-gost="X">…</select>` → `X` — орган правки, вставший на место
#      гостевого текста; сам текст он и несёт в `data-gost`, поэтому подстановка
#      механическая, а не догадка;
#   3. атрибуты из закрытого списка `ATRIBUTY_ORGANA` на общих элементах.
# Из гостевой снимаются элементы `data-tolko-gost` — то, что роль намеренно НЕ
# показывает (кабинет в списках школьников: тому, кто раскладывает людей, он не
# нужен, решение владельца).
#
# Что гейт НЕ проверяет и не должен: скрипты и кнопку входа/выхода. Это не каркас
# страницы, а её поведение.
import re as _re

# 🔴 ЗАКРЫТЫЙ СПИСОК, И КАЖДОЕ ИМЯ В НЁМ ЗАРАБОТАНО. Сюда попадает атрибут,
# который у роли ЕСТЬ, а у гостя на том же элементе НЕТ. `data-tid` здесь стоял
# и был убран: он висит на строке таблицы у ОБОИХ, и снятие его только с одной
# стороны само создавало расхождение — гейт поймал это на себе же.
ATRIBUTY_ORGANA = ("data-org", "data-gost", "data-snyat", "data-slot", "data-gruppa",
                   "data-sid", "data-data", "role", "tabindex")
# `title` в этот список НЕ входит и входить не должен: у чипа кабинета он общий
# и объясняет, откуда взят номер. Подсказка «открепить» живёт на крестике, то
# есть на элементе, которого у гостя нет вовсе, и снимается вместе с ним.


def _razdel_raspredeleniya(html: str) -> str:
    m = _re.search(r'<section class="str holst" id="s-rasp">.*?(?=\n<script>|\Z)',
                   html, _re.S)
    assert m, "раздел распределения не найден — гейт нечего сверять"
    return m.group(0)


def _ubrat_elementy(html: str, priznak: str) -> str:
    """Удалить каждый элемент, в открывающем теге которого есть `priznak`, целиком.

    🔴 РАЗБОР С БАЛАНСИРОВКОЙ, А НЕ РЕГУЛЯРКА. Регулярка здесь была и была неверна:
    нежадное `.*?</span>` останавливалось на ПЕРВОМ закрывающем теге и оставляло
    лишний, а вариант с оглядкой не брал вложенные одноимённые теги вовсе —
    `<span data-tolko-gost><span class="kab">…</span></span>` не удалялся никогда.
    Оба раза это поймал сам гейт на первом же прогоне, и оба раза он был прав.
    Вложенность тегов регулярными выражениями не разбирается — это её свойство,
    а не невезение.
    """
    out, i = [], 0
    while True:
        j = html.find("<", i)
        if j == -1:
            out.append(html[i:])
            return "".join(out)
        k = html.find(">", j)
        if k == -1:
            out.append(html[i:])
            return "".join(out)
        teg = html[j:k + 1]
        m = _re.match(r"<([a-zA-Z][\w-]*)", teg)
        if not m or priznak not in teg or teg.endswith("/>"):
            out.append(html[i:k + 1])
            i = k + 1
            continue
        # нашли открывающий тег с признаком — ищем ЕГО закрытие, считая вложенные
        imya = m.group(1)
        out.append(html[i:j])
        glubina, pos = 1, k + 1
        otkr = _re.compile(r"<" + imya + r"(?=[\s/>])", _re.I)
        zakr = "</" + imya + ">"
        while glubina and pos < len(html):
            sled_o = otkr.search(html, pos)
            sled_z = html.find(zakr, pos)
            if sled_z == -1:
                pos = len(html)
                break
            if sled_o and sled_o.start() < sled_z:
                glubina += 1
                pos = sled_o.end()
            else:
                glubina -= 1
                pos = sled_z + len(zakr)
        i = pos


def _snyat_organy(html: str) -> str:
    """Убрать из страницы всё, что добавила возможность. Больше ничего."""
    # 2. орган правки на месте гостевого текста — вернуть текст, который он несёт
    html = _re.sub(r'<select\b[^>]*\bdata-gost="([^"]*)"[^>]*>.*?</select>',
                   lambda m: m.group(1), html, flags=_re.S)
    # 1. элементы, которых у гостя нет вовсе
    html = _ubrat_elementy(html, "data-org=")
    # 3. атрибуты-надстройки на общих элементах
    for atr in ATRIBUTY_ORGANA:
        html = _re.sub(r'\s' + atr + r'="[^"]*"', "", html)
    return html


def _snyat_gostevoe(html: str) -> str:
    """То же самое с другой стороны: убрать то, что роль намеренно НЕ показывает."""
    return _ubrat_elementy(html, "data-tolko-gost")


def proverit_karkas(roli=("organizator",)) -> list:
    """Сверить каркас каждой роли с гостевым. Возвращает список расхождений.

    Пустой список — каркас един. Зовётся из `sobrat()` на каждой сборке, поэтому
    разъехаться незаметно нельзя: страница просто не соберётся.
    """
    gost = _snyat_gostevoe(_razdel_raspredeleniya(sobrat_html("gost")))
    bedy = []
    for rol in roli:
        s_rolyu = _snyat_organy(_razdel_raspredeleniya(
            sobrat_html("admin" if rol == "organizator" else rol)))
        if s_rolyu != gost:
            # назвать ПЕРВОЕ расхождение — по нему чинят, а не по факту «не равно»
            i = next((i for i in range(min(len(gost), len(s_rolyu)))
                      if gost[i] != s_rolyu[i]), min(len(gost), len(s_rolyu)))
            bedy.append(
                f"каркас роли «{rol}» разошёлся с гостевым на позиции {i}:\n"
                f"    гость: …{gost[max(0, i - 60):i + 60]!r}\n"
                f"    {rol}: …{s_rolyu[max(0, i - 60):i + 60]!r}")
    return bedy


def sobrat(svodka: list | None = None) -> int:
    """Пишет ГОСТЕВУЮ страницу в `docs/index.html`. Зовётся руками и из сервера.

    \U0001f534 ПАДАЕТ ГРОМКО. Ни одного `except` вокруг: сервер зовёт эту функцию
    после каждой успешной записи в базу и обязан упасть вместе с ней. Тихая
    сборка вернула бы ровно то, от чего уходим, — новую базу при вчерашней
    странице, о которой никто не знает.
    """
    svodka = [] if svodka is None else svodka
    # 🔴 ГВОЗДЬ ЗАБИВАЕТСЯ ЗДЕСЬ, НА КАЖДОЙ СБОРКЕ. Каркас разъехался — страница
    # не собирается вовсе. Не предупреждение, не запись в лог: отказ. Владелец
    # 06.09: «мы не должны за этим следить, это должно быть прибито гвоздями».
    # Следить и не надо — не соберётся.
    bedy = proverit_karkas()
    if bedy:
        raise AssertionError(
            "каркас гостя и роли разошёлся — страница не собрана:\n" + "\n".join(bedy))
    svodka.append("  каркас: гость и организатор совпадают побайтово ✅")
    VYHOD.write_text(sobrat_html("gost", svodka), encoding="utf-8")
    print(f"собрано: {VYHOD}")
    for stroka in svodka:
        print(stroka)
    return 0


if __name__ == "__main__":
    sys.exit(sobrat())
