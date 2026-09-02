#!/bin/bash
# Спрашивает ключ OpenRouter, вписывает в secrets/bot.env, проверяет.
set -euo pipefail
cd "$(dirname "$0")/.."

printf 'Вставьте ключ OpenRouter и нажмите Enter (на экране он не появится):\n> '
read -rs KEY
echo

if [ -z "${KEY}" ]; then echo "Пусто — ничего не записал."; exit 1; fi

python3 - "$KEY" <<'PY'
import re, sys, pathlib
key = sys.argv[1].strip()
p = pathlib.Path("secrets/bot.env")
t = p.read_text(encoding="utf-8")
t = re.sub(r"^LLM_API_KEY=.*$", "LLM_API_KEY=" + key, t, flags=re.M)
p.write_text(t, encoding="utf-8")
print(f"записан ключ длиной {len(key)} символов")
PY

echo "проверяю ключ..."
set -a; . secrets/bot.env; set +a
curl -s -m 25 https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer ${LLM_API_KEY}" -o /tmp/or_models.json || true

python3 - <<'PY'
import json, pathlib
try:
    d = json.loads(pathlib.Path("/tmp/or_models.json").read_text())
except Exception as e:
    raise SystemExit(f"❌ OpenRouter не ответил или ключ не принят: {e}")
if "data" not in d:
    raise SystemExit(f"❌ ответ без списка моделей: {str(d)[:300]}")

models = d["data"]
free = [m for m in models if m["id"].endswith(":free")]
def sees_images(m):
    inp = (m.get("architecture") or {}).get("input_modalities") or []
    return "image" in inp
vision_free = [m for m in free if sees_images(m)]

print(f"✅ ключ рабочий · моделей всего {len(models)} · бесплатных {len(free)} · из них видят картинки {len(vision_free)}")
print("\nбесплатные, умеющие смотреть на картинки (это нужно для фото бланков):")
for m in sorted(vision_free, key=lambda x: -(x.get("context_length") or 0))[:12]:
    ctx = m.get("context_length") or 0
    print(f"   {m['id']:<58} контекст {ctx}")
PY
