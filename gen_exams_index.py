"""把 structure.json + 已抓题库 + 补抓的新题，生成一份人可读的组卷清单。

每题标注来源：
    [题库]      已抓题库里就有（可直接打开）
    [新抓]      只在卷子里出现，已补抓到 exams/
    [付费]      该题所在卷子需要额外权限，没拿到
"""
import json
import re
from pathlib import Path

STRUCT = Path("exams/structure.json")
QROOT = Path("questions")
OUT = Path("exams/README.md")
OK_RE = re.compile(r"^[A-Z]{2}\d+$")


def index_questions():
    """题号 -> 相对 questions/ 的路径"""
    idx = {}
    for md in QROOT.rglob("*.md"):
        t = md.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^reference:\s*(\S+)", t, re.M)
        if m:
            idx.setdefault(m.group(1).strip(), md)
    return idx


def index_exams():
    idx = {}
    for md in Path("exams").rglob("*.md"):
        if md.name == "README.md":
            continue
        t = md.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^reference:\s*(\S+)", t, re.M)
        if m:
            idx.setdefault(m.group(1).strip(), md)
    return idx


def main():
    struct = json.loads(STRUCT.read_text(encoding="utf-8"))
    bank = index_questions()
    extra = index_exams()

    lines = ["# 组卷结构", ""]
    lines.append(f"题库已有 **{len(bank)}** 个题号；卷子里另有 **{len(extra)}** 道题库中没有的题（已补抓在 `exams/` 下）。")
    lines.append("")
    lines.append("每题来源标记：`[题库]` 已抓题库 · `[新抓]` 只在卷子里出现 · `[付费]` 该卷需额外权限，未获取")
    lines.append("")

    grand = {"bank": 0, "extra": 0, "paid": 0}

    for sub in struct["subjects"]:
        lines.append(f"## {sub['name']}")
        lines.append("")
        for st in sub["sets"]:
            papers = st["papers"]
            accessible = any(p.get("questions") for p in papers)
            # 权限判断：整卷题的来源统计
            refs_all = [q.get("reference", "").strip() for p in papers for q in p["questions"]]
            refs_ok = [r for r in refs_all if OK_RE.match(r)]
            n_bank = sum(1 for r in refs_ok if r in bank)
            n_extra = sum(1 for r in refs_ok if r not in bank and r in extra)
            n_paid = sum(1 for r in refs_ok if r not in bank and r not in extra)

            kind_label = {"mock": "模拟考", "prediction": "预测卷", "quiz": "主题小测"}[st["type"]]
            head = f"### {kind_label} · {st['name']}"
            if st.get("access_level"):
                head += f"　`{st['access_level']}`"
            lines.append(head)
            lines.append("")
            dur = ", ".join(f"{p.get('name')} {p.get('duration')}min" for p in papers if p.get("duration"))
            if dur:
                lines.append(f"时长：{dur}")
                lines.append("")
            lines.append(f"共 {len(refs_ok)} 题 —— [题库] {n_bank} · [新抓] {n_extra} · [付费] {n_paid}")
            lines.append("")

            for p in papers:
                qs = [q for q in p["questions"] if OK_RE.match(q.get("reference", "").strip())]
                if not qs:
                    continue
                lines.append(f"**{p.get('name')}**（{len(qs)} 题"
                             + (f"，{p.get('maximum_mark')} 分" if p.get("maximum_mark") else "")
                             + "）")
                lines.append("")
                cells = []
                for q in qs:
                    r = q["reference"].strip()
                    marks = f"/{q['marks']}" if q.get("marks") else ""
                    if r in bank:
                        cells.append(f"`{r}`{marks}[题库]")
                        grand["bank"] += 1
                    elif r in extra:
                        cells.append(f"`{r}`{marks}[新抓]")
                        grand["extra"] += 1
                    else:
                        cells.append(f"`{r}`{marks}[付费]")
                        grand["paid"] += 1
                lines.append("、".join(cells))
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"## 总计")
    lines.append("")
    lines.append(f"- [题库] 已有：{grand['bank']} 题次")
    lines.append(f"- [新抓] 卷子独有：{grand['extra']} 题次")
    lines.append(f"- [付费] 未获取：{grand['paid']} 题次")
    lines.append("")
    lines.append("> 同一道题可能在多套卷子里重复出现，所以这里按「题次」统计。")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"写入 {OUT}")
    print(f"  题库 {grand['bank']} 题次 / 新抓 {grand['extra']} / 付费未取 {grand['paid']}")


if __name__ == "__main__":
    main()
