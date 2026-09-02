"""Генератор печатного бланка приёма задач.

Бланк — сетка «ученик × номера задач». Преподаватель обводит или зачёркивает
клетки от руки, фотографирует, бот разбирает. Печатная сетка снимает почти всю
неоднозначность: путать нечего, координаты клетки заданы бумагой.
"""
import csv
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1654, 2339            # A4 при 200 dpi
MARGIN = 70
ROW_H = 46
COL_W = 62
NAME_W = 340


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/Library/Fonts/Arial.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw(students, labels, sheet_no, room, out):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_head, f_cell, f_name = font(38), font(22), font(26)

    d.text((MARGIN, 40), f"Листок {sheet_no}", font=f_head, fill="black")
    d.text((W - MARGIN - 420, 48), f"кабинет {room}    дата ________", font=f_cell, fill="black")

    top = 120
    x0 = MARGIN + NAME_W
    for j, lab in enumerate(labels):
        d.text((x0 + j * COL_W + 12, top - 34), str(lab), font=f_cell, fill="black")

    for i, s in enumerate(students):
        y = top + i * ROW_H
        d.text((MARGIN + 8, y + 10), s, font=f_name, fill="black")
        d.line([(MARGIN, y), (x0 + len(labels) * COL_W, y)], fill="#999", width=1)
        for j in range(len(labels)):
            d.rectangle([x0 + j * COL_W, y, x0 + (j + 1) * COL_W, y + ROW_H], outline="#999")

    y_end = top + len(students) * ROW_H
    d.line([(MARGIN, y_end), (x0 + len(labels) * COL_W, y_end)], fill="#999", width=1)
    d.line([(x0, top - 6), (x0, y_end)], fill="#333", width=2)
    d.text((MARGIN, y_end + 24),
           "Сдал — крестик в клетке. Снято — прочерк. Пусто — не сдавал.",
           font=f_cell, fill="#444")
    img.save(out, "PNG")
    return out


if __name__ == "__main__":
    csv_path = Path("seed/students.csv")
    students = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("technical", "").strip().lower() in ("1", "true", "да"):
                    continue
                students.append(f"{r['surname']} {r['name'][:1]}.")
    students = students[:18] or [f"Ученик {i}" for i in range(1, 19)]
    labels = ["1", "2", "3а", "3б", "4", "5", "6", "7а", "7б", "8", "9", "10*", "11*"]
    out = sys.argv[1] if len(sys.argv) > 1 else "tools/proba/blank.png"
    print("бланк:", draw(students, labels, sys.argv[2] if len(sys.argv) > 2 else "3", "302", out))
