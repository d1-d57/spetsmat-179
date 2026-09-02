"""Прогон бесплатных vision-моделей OpenRouter на тестовом бланке.

Проверяет две разные вещи, которые легко спутать:
  1. отдаёт ли модель СТРОГИЙ JSON по схеме (без этого она будет выдумывать фамилии);
  2. правильно ли читает отметки в клетках.

Запуск:  python3 tools/proba_modelej.py tools/proba/zapolnennyj.jpg
Без аргумента берёт пустой бланк — тогда правильный ответ «ни одной отметки»,
и это тоже проверка: модель, которая на пустом бланке что-то находит, врёт.
"""
import base64, json, os, pathlib, re, sys, time, urllib.request

KEY = None
for line in pathlib.Path("secrets/bot.env").read_text(encoding="utf-8").splitlines():
    if line.startswith("LLM_API_KEY="):
        KEY = line.split("=", 1)[1].strip()
if not KEY:
    sys.exit("нет LLM_API_KEY в secrets/bot.env — запустите tools/kluch.sh")

MODELS = [
    "thinkingmachines/inkling:free",
    "thinkingmachines/inkling-small:free",
    "minimax/minimax-m3:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "dots-studio/dots-3-note-preview:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]

import csv
students = []
with open("seed/students.csv", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r.get("technical") == "1":
            continue
        students.append(f"{r['surname']} {r['name'][:1]}.")
ROSTER = students[:18]
LABELS = ["1", "2", "3а", "3б", "4", "5", "6", "7а", "7б", "8", "9", "10*", "11*"]

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["rows"],
    "properties": {"rows": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["row_index", "raw_name", "solved"],
        "properties": {
            "row_index": {"type": "integer"},
            "raw_name": {"type": "string"},
            "solved": {"type": "array", "items": {"type": "string", "enum": LABELS}},
        }}}},
}

PROMPT = (
    "На фотографии печатный бланк приёма задач: строки — ученики в том же порядке, "
    "что в списке ниже, столбцы — номера задач.\n\n"
    f"Строки по порядку (индекс с 0):\n" + "\n".join(f"{i}. {n}" for i, n in enumerate(ROSTER)) +
    f"\n\nСтолбцы: {', '.join(LABELS)}\n\n"
    "Верни для КАЖДОЙ строки, в клетках которой есть пометка, список номеров задач с пометкой. "
    "Пометка — крестик, галочка, любая закраска. Пустая клетка не считается. "
    "raw_name — фамилия, как она напечатана в строке. "
    "Если пометок нет нигде, верни пустой список rows."
)

img = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "tools/proba/blank.png")
b64 = base64.b64encode(img.read_bytes()).decode()
mime = "image/jpeg" if img.suffix.lower() in (".jpg", ".jpeg") else "image/png"

print(f"бланк: {img}  ({img.stat().st_size // 1024} КБ)\n")

for model in MODELS:
    body = {
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        "response_format": {"type": "json_schema", "json_schema":
                            {"name": "blank", "strict": True, "schema": SCHEMA}},
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    time.sleep(2)          # 429 у gemma — лимит частоты, разносим вызовы
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read())
    except Exception as e:
        print(f"❌ {model:<52} {type(e).__name__}: {str(e)[:80]}")
        continue
    dt = time.time() - t0

    if "error" in d:
        print(f"❌ {model:<52} {str(d['error'])[:80]}")
        continue
    txt = d["choices"][0]["message"]["content"]
    # Модели оборачивают JSON в markdown даже при strict-схеме — снимаем обёртку.
    # Замер 02.09: minimax-m3 вернула верный ответ внутри ```json ... ```
    clean = txt.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", clean).strip()
    try:
        parsed = json.loads(clean)
        rows = parsed.get("rows", [])
        marks = sum(len(r.get("solved", [])) for r in rows)
        print(f"✅ {model:<52} {dt:5.1f}с  строк {len(rows):>2}  отметок {marks:>3}")
        for r in rows[:3]:
            print(f"      {r.get('raw_name','?')}: {', '.join(r.get('solved', []))}")
    except json.JSONDecodeError:
        print(f"⚠️  {model:<52} {dt:5.1f}с  не JSON даже после снятия обёртки: {clean[:60]}")
