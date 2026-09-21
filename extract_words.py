# -*- coding: utf-8 -*-
"""提取 PDF 中的词级图片槽位，OCR 双投票分类：自动采纳 / 待人工校对"""
import io, os, json, traceback
import fitz
from PIL import Image, ImageOps, ImageDraw, ImageFont
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from wordfreq import zipf_frequency

PDF = r"E:\笔记\学习\考研资料\27考研1-21.pdf"
BASE = r"C:\Users\赵婧赟\WorkBuddy\2026-09-21-11-00-42\vocab-extractor"
CROPS = os.path.join(BASE, "crops")
SHEETS = os.path.join(BASE, "sheets")
LOG = r"C:\Users\赵婧赟\WorkBuddy\2026-09-21-11-00-42\_pipeline_log.txt"

def log(msg):
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

try:
    os.makedirs(CROPS, exist_ok=True)
    os.makedirs(SHEETS, exist_ok=True)
    log("start")
    ocr = RapidOCR()
    doc = fitz.open(PDF)

    # 断点续跑：跳过已完成的页
    slots = []
    done_pages = set()
    sid = 0
    sp = os.path.join(BASE, "slots.json")
    if os.path.exists(sp):
        try:
            slots = json.load(io.open(sp, encoding="utf-8"))
            done_pages = set(s["page"] for s in slots)
            sid = max(s["id"] for s in slots)
            log("resume from page, done=%d, sid=%d" % (len(done_pages), sid))
        except Exception:
            slots = []
    tmp_png = os.path.join(CROPS, "_tmp.png")
    for pno in range(doc.page_count):
        if (pno + 1) in done_pages:
            continue
        page = doc[pno]
        d = page.get_text("dict")
        blocks = [b for b in d["blocks"] if b["type"] == 1]
        # 词级小图
        words_blocks = []
        for b in blocks:
            x0, y0, x1, y1 = b["bbox"]
            if (y1 - y0) <= 30 and (x1 - x0) <= 280:
                words_blocks.append(b)
        if not words_blocks:
            continue
        # 按 y,x 排序
        words_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        for b in words_blocks:
            x0, y0, x1, y1 = b["bbox"]
            sid += 1
            rec = {"id": sid, "page": pno + 1, "bbox": [round(x0,1), round(y0,1), round(x1,1), round(y1,1)]}
            # 裁剪：直接用嵌入原图
            img = None
            try:
                raw = b.get("image")
                if raw:
                    img = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:
                img = None
            if img is None:
                pix = page.get_pixmap(clip=fitz.Rect(x0, y0, x1, y1), dpi=200)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            # 保存原图副本
            crop_path = os.path.join(CROPS, "c%05d.png" % sid)
            img.save(crop_path)

            # OCR 两尺度（限制放大后尺寸，防内存爆掉）
            def ocr_var(scale):
                try:
                    w, h = img.size
                    max_side = max(w, h)
                    if max_side * scale > 2000:
                        scale = max(1, int(2000 / max_side))
                    g = img
                    if scale > 1:
                        g = g.resize((w*scale, h*scale), Image.LANCZOS)
                    g = ImageOps.autocontrast(g.convert("L"))
                    res, _ = ocr(np.array(g.convert("RGB")))
                    if not res:
                        return ""
                    return " ".join(r[1] for r in res).strip()
                except Exception:
                    return ""
            v4 = ocr_var(4)
            v8 = ocr_var(8)
            rec["v4"], rec["v8"] = v4, v8
            del img

            def is_en(s):
                s2 = "".join(ch for ch in s if ch.isalpha())
                return s2 and all(ord(ch) < 128 for ch in s2) and len(s2) == len(s.replace(" ", "").replace("-", ""))
            def norm_en(s):
                s2 = "".join(ch for ch in s.lower() if ch.isalpha())
                return s2
            has_cjk = lambda s: any('\u4e00' <= ch <= '\u9fff' for ch in s)

            auto = None
            if v4 and v8 and v4 == v8:
                if has_cjk(v4):
                    auto = "zh"; rec["zh"] = v4
                else:
                    w = norm_en(v4)
                    if w and zipf_frequency(w, "en") > 0:
                        auto = "en"; rec["en"] = w
            rec["auto"] = auto
            slots.append(rec)
        # 每页增量保存，防崩溃丢进度
        with io.open(os.path.join(BASE, "slots.json"), "w", encoding="utf-8") as f:
            json.dump(slots, f, ensure_ascii=False)
        log("page %d done, slots=%d" % (pno+1, sid))

    with io.open(os.path.join(BASE, "slots.json"), "w", encoding="utf-8") as f:
        json.dump(slots, f, ensure_ascii=False)

    # 待校对槽位 → 拼图版
    flagged = [s for s in slots if not s["auto"]]
    log("total=%d flagged=%d" % (len(slots), len(flagged)))

    font = ImageFont.load_default()
    CELL_W, CELL_H, ID_H = 200, 78, 16
    COLS, ROWS = 6, 11
    per_sheet = COLS * ROWS
    nsheets = (len(flagged) + per_sheet - 1) // per_sheet
    for si in range(nsheets):
        batch = flagged[si*per_sheet:(si+1)*per_sheet]
        W, H = COLS*CELL_W, ROWS*CELL_H
        sheet = Image.new("RGB", (W, H), (255, 255, 255))
        dr = ImageDraw.Draw(sheet)
        for i, s in enumerate(batch):
            cx, cy = (i % COLS)*CELL_W, (i // COLS)*CELL_H
            crop = Image.open(os.path.join(CROPS, "c%05d.png" % s["id"]))
            crop.thumbnail((CELL_W-8, CELL_H-ID_H-6))
            dr.rectangle([cx+2, cy+2, cx+CELL_W-3, cy+ID_H-2], outline=(200,60,60))
            dr.text((cx+6, cy+3), "#%d" % s["id"], fill=(180,0,0), font=font)
            sheet.paste(crop, (cx+4, cy+ID_H))
            dr.rectangle([cx+2, cy+2, cx+CELL_W-3, cy+CELL_H-3], outline=(210,210,210))
        sheet.save(os.path.join(SHEETS, "sheet%02d.png" % (si+1)))

    with io.open(os.path.join(BASE, "flagged.json"), "w", encoding="utf-8") as f:
        json.dump([s["id"] for s in flagged], f)
    log("DONE sheets=%d" % nsheets)
except Exception:
    log(traceback.format_exc())
    log("FAILED")
