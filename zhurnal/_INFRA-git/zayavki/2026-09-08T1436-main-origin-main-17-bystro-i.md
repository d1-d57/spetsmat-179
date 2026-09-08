ЗАЯВКА: 2026-09-08T14:36 · автор: host · арка: не названа
СРОЧНОСТЬ: obychnaya
РОД: git-operaciya

main опережает origin/main на 17 коммитов (замер захода bystro-i-bezopasno, 2026-09-08 14:40): среди них ветки profil-bezopasnosti, vygruzka-v-tablicu, bystro-i-bezopasno, коммит восьми kod_*.md арки (aca18f4) и хвост Cowork. Заход вывезти не может: дверь vyvezti отказывает на открытых заявках 2026-09-08T0031 и T0853, а обход --vsyo-ravno означал бы вывоз main вопреки прямому запрету WARNING-блока §5 захода И поверх открытого инцидента 2026-09-02T1431 (живой токен бота в ПУБЛИЧНОМ репозитории d1-d57/spetsmat-179). Порядок, снимающий обе блокировки: сначала /revoke токена в @BotFather и новый токен в secrets/bot.env (действие владельца), затем push origin main.

КАК ВЛИВАТЬ: ЧТО: вливать нечего — всё уже в локальном main (zahod/bystro-i-bezopasno влита заходом самостоятельно, git log main..zahod/bystro-i-bezopasno = 0); нужен ТОЛЬКО вывоз push origin main · ГДЕ ЖДАТЬ КОНФЛИКТА: конфликта нет, операция односторонняя; если origin успел уйти вперёд — на README.md, реестр регистраций · ЧЬЕЙ СТОРОНОЙ: README.md разрешать ОБЪЕДИНЕНИЕМ записей реестра, никогда выбором стороны · ПОСЛЕ: git log --oneline origin/main..main | wc -l -> 0
