# -*- coding: utf-8 -*-
"""根据 slots.json + corrections.json 重建完整文本（词图位置插回识别结果）

v2: 增加段落识别——利用行间距区分「段内换行」与「段落边界」。
    PDF 中同一自然段的视觉行距约 23pt，跨段约 33pt+。用相对基准自适应判定。
"""
import io, os, json
import fitz

PDF = r"E:\笔记\学习\考研资料\27考研1-21.pdf"
BASE = r"C:\Users\赵婧赟\WorkBuddy\2026-09-21-11-00-42\vocab-extractor"
OUT = os.path.join(BASE, "27kaoyan-full.txt")
CORR = os.path.join(BASE, "corrections.json")

# 段落判定参数
GAP_MULT = 1.22        # 间距 > 段内基准 × 该系数 → 视为段落边界
GAP_MIN = 5.0          # 基准计算时的最小间距过滤
MERGE_CJK = True       # 中文行之间不插空格（中文段落内通常直接接续）


def has_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)


def cjk_punct_start(s):
    return s and s[0] in "，。；：、！？）》”’】』〕〉…—%分之"


def join_tokens(a, b):
    if not a:
        return b
    if has_cjk(a[-1]) and (has_cjk(b[0]) or cjk_punct_start(b)):
        return a + b
    if b[0] in "，。；：、！？）》”’】』〕〉…—%,.;:!?)]}":
        return a + b
    if a[-1] in "([{《“‘【〔〈":
        return a + b
    return a + " " + b


def build_lines(page, page_slots, finals):
    """把页面上的文字块与词图块合并，按 y 坐标聚成视觉行。返回 [(y, text), ...]"""
    items = []  # (y, x, text)
    for w in page.get_text("words"):
        items.append((w[1], w[0], w[4]))
    for s in page_slots:
        x0, y0, x1, y1 = s["bbox"]
        t = finals.get(s["id"], "")
        if not t:
            continue
        items.append((y0, x0, t))

    items.sort(key=lambda t: (t[0], t[1]))
    lines, cur, cur_y = [], [], None
    for y, x, t in items:
        if cur_y is None or abs(y - cur_y) <= 6.0:
            cur.append((x, t))
            cur_y = y if cur_y is None else cur_y
        else:
            lines.append((cur_y, cur)); cur = [(x, t)]; cur_y = y
    if cur:
        lines.append((cur_y, cur))

    out = []
    for y, toks in lines:
        toks.sort(key=lambda t: t[0])
        text = ""
        for x, t in toks:
            text = join_tokens(text, t)
        if text.strip():
            out.append((y, text))
    return out


def median(vals):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[len(s) // 2]


def main():
    slots = json.load(io.open(os.path.join(BASE, "slots.json"), encoding="utf-8"))
    corr = {}
    if os.path.exists(CORR):
        corr = json.load(io.open(CORR, encoding="utf-8"))

    finals = {}
    unresolved = []
    for s in slots:
        sid = str(s["id"])
        if sid in corr:
            v = corr[sid]
            finals[s["id"]] = "" if v == "SKIP" else v
        elif s.get("auto") == "en":
            finals[s["id"]] = s["en"]
        elif s.get("auto") == "zh":
            finals[s["id"]] = s["zh"]
        else:
            guess = s.get("v4") or s.get("v8") or ""
            finals[s["id"]] = guess if guess else "[图]"
            unresolved.append(s["id"])

    by_page = {}
    for s in slots:
        by_page.setdefault(s["page"], []).append(s)

    doc = fitz.open(PDF)
    para_count = 0
    with io.open(OUT, "w", encoding="utf-8") as f:
        for pno in range(doc.page_count):
            page = doc[pno]
            lines = build_lines(page, by_page.get(pno + 1, []), finals)
            if not lines:
                continue

            # 用本页行距中位数作为「段内基准」
            gaps = [lines[i][0] - lines[i - 1][0] for i in range(1, len(lines))]
            base = median([g for g in gaps if g >= GAP_MIN])
            if base <= 0:
                base = 23.4
            thresh = max(base * GAP_MULT, base + 6.0)

            f.write("\n===== 第 %d 页 =====\n\n" % (pno + 1))
            para_count += 1
            prev_was_boundary = True
            for i, (y, text) in enumerate(lines):
                gap = (y - lines[i - 1][0]) if i else 0
                boundary = (i == 0) or (gap > thresh)
                if boundary:
                    if not prev_was_boundary:
                        f.write("\n")          # 段落之间空一行
                    f.write(text + "\n")
                    para_count += 1
                else:
                    # 段内换行：中文段落直接接续，英文按空格接续
                    if MERGE_CJK and has_cjk(text):
                        f.write(text + "\n")
                    else:
                        f.write(text + "\n")
                prev_was_boundary = boundary

    print("unresolved:", len(unresolved))
    print("段落块数约:", para_count)
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
