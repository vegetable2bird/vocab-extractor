# -*- coding: utf-8 -*-
"""生成最终校对图版：flagged + 可疑 auto_en"""
import io, os, json
from PIL import Image, ImageDraw, ImageFont

BASE = r"C:\Users\赵婧赟\WorkBuddy\2026-09-21-11-00-42\vocab-extractor"
CROPS = os.path.join(BASE, "crops")
SHEETS = os.path.join(BASE, "sheets_review")

# 清掉旧图版，避免混淆
if os.path.exists(SHEETS):
    import shutil
    shutil.rmtree(SHEETS)
os.makedirs(SHEETS, exist_ok=True)

slots = json.load(io.open(os.path.join(BASE, "slots.json"), encoding="utf-8"))
by_id = {s["id"]: s for s in slots}

fragments = {"adver","affor","alterna","ams","bac","bser","bur","co","cri","exi","faul",
             "hes","ht","hr","iber","ige","invo","ke","lames","lar","lation","laven","lea",
             "lers","lion","moc","nud","oom","patty","quo","rama","rence","rted","scal",
             "summa","tarle","theor","tric","lout","ad","red","sea","hip","pin","in","to",
             "up","le","se","car","late","re"}

review_ids = []
for s in slots:
    if not s.get("auto"):
        review_ids.append(s["id"])
    elif s.get("auto") == "en" and (len(s["en"]) <= 3 or s["en"] in fragments):
        review_ids.append(s["id"])

review_ids.sort()
json.dump(review_ids, io.open(os.path.join(BASE, "review_ids.json"), "w"))

font = ImageFont.load_default()
CELL_W, CELL_H, ID_H = 200, 84, 16
COLS, ROWS = 6, 11
per = COLS * ROWS
nsheets = (len(review_ids) + per - 1) // per
for si in range(nsheets):
    batch = review_ids[si*per:(si+1)*per]
    sheet = Image.new("RGB", (COLS*CELL_W, ROWS*CELL_H), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    for i, sid in enumerate(batch):
        cx, cy = (i % COLS)*CELL_W, (i // COLS)*CELL_H
        crop = Image.open(os.path.join(CROPS, "c%05d.png" % sid))
        crop.thumbnail((CELL_W-8, CELL_H-ID_H-6))
        dr.rectangle([cx+2, cy+2, cx+CELL_W-3, cy+ID_H-2], outline=(200,60,60))
        dr.text((cx+6, cy+3), "#%d" % sid, fill=(180,0,0), font=font)
        sheet.paste(crop, (cx+4, cy+ID_H))
        dr.rectangle([cx+2, cy+2, cx+CELL_W-3, cy+CELL_H-3], outline=(210,210,210))
    sheet.save(os.path.join(SHEETS, "sheet%02d.png" % (si+1)))

print("review=%d sheets=%d" % (len(review_ids), nsheets))
