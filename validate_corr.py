# -*- coding: utf-8 -*-
"""校验 corrections.json：语言冲突 / 与OCR相似度过低 / 覆盖缺失 / 越界ID"""
import io, os, json, unicodedata

BASE = r"C:\Users\赵婧赟\WorkBuddy\2026-09-21-11-00-42\vocab-extractor"
slots = json.load(io.open(os.path.join(BASE, "slots.json"), encoding="utf-8"))
corr = json.load(io.open(os.path.join(BASE, "corrections.json"), encoding="utf-8"))
review_ids = set(json.load(io.open(os.path.join(BASE, "review_ids.json"), encoding="utf-8")))
by_id = {s["id"]: s for s in slots}

def is_en(s):
    return s and all(ord(c) < 128 for c in s) and any(c.isalpha() for c in s)
def has_cjk(s):
    return any('\u4e00' <= c <= '\u9fff' for c in s)
def letters(s):
    return "".join(c for c in s.lower() if c.isalpha())

def sim_bad(a, b):
    a, b = letters(a), letters(b)
    if not a or not b:
        return False
    if a[:2] == b[:2] or a[-2:] == b[-2:]:
        return False
    if abs(len(a) - len(b)) <= 1 and a[:1] == b[:1]:
        return False
    common = set(a) & set(b)
    return len(common) < max(1, min(len(a), len(b)) // 2)

problems = []
for sid_str, val in corr.items():
    sid = int(sid_str)
    s = by_id.get(sid)
    if s is None:
        problems.append(("NO_SLOT", sid, val)); continue
    if sid not in review_ids:
        problems.append(("NOT_IN_REVIEW", sid, val, s.get("v4"), s.get("v8"), s.get("auto"))); continue
    if s.get("auto") == "zh" and is_en(val) and len(letters(val)) > 2:
        problems.append(("ZH_BUT_EN", sid, val, s.get("zh"))); continue
    if s.get("auto") == "en" and has_cjk(val):
        problems.append(("EN_BUT_ZH", sid, val, s.get("en"))); continue
    v4, v8 = s.get("v4") or "", s.get("v8") or ""
    cands = [v for v in (v4, v8) if v]
    if cands and all(sim_bad(val, c) for c in cands):
        problems.append(("SIM_LOW", sid, val, v4, v8))

missing = [i for i in sorted(review_ids) if str(i) not in corr]

lines = []
for p in problems:
    lines.append(" | ".join(str(x) for x in p))
lines.append("")
lines.append("MISSING(%d): %s" % (len(missing), ",".join(map(str, missing))))
io.open(os.path.join(BASE, "validation.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("problems=%d missing=%d" % (len(problems), len(missing)))
