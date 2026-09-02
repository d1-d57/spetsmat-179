#!/bin/bash
# Достаёт OWNER_ID из последних сообщений боту и вписывает в secrets/bot.env.
# Перед запуском: написать боту @conduit179_bot любое сообщение.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . secrets/bot.env; set +a

RESP=$(curl -s -m 20 "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates")

python3 - "$RESP" <<'PY'
import json, re, sys, pathlib

d = json.loads(sys.argv[1])
if not d.get("ok"):
    sys.exit(f"Telegram ответил отказом: {d}")

users = {}
for u in d.get("result", []):
    msg = u.get("message") or u.get("edited_message") or {}
    frm = msg.get("from") or {}
    if frm.get("id") and not frm.get("is_bot"):
        users[frm["id"]] = f"{frm.get('first_name','')} {frm.get('last_name','') or ''}".strip() \
                           + (f" (@{frm['username']})" if frm.get("username") else "")

if not users:
    sys.exit("Сообщений нет. Напишите боту @conduit179_bot что-нибудь и запустите снова.\n"
             "Если писали давно — Telegram хранит апдейты сутки; напишите ещё раз.")

if len(users) > 1:
    print("Писали несколько человек, выбираю первого. Все:")
    for i, n in users.items():
        print(f"   {i} — {n}")

oid, name = next(iter(users.items()))
p = pathlib.Path("secrets/bot.env")
text = p.read_text(encoding="utf-8")
text = re.sub(r"^OWNER_ID=.*$", f"OWNER_ID={oid}", text, flags=re.M)
p.write_text(text, encoding="utf-8")
print(f"OWNER_ID={oid}  ({name})  — вписан в secrets/bot.env")
PY
