"""为所有已抓科目生成索引：根 INDEX.md + 每科 README.md。"""
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path("questions")


def read_fm(md: Path) -> dict:
    text = md.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def rel(md: Path, base: Path) -> str:
    return quote(str(md.relative_to(base)).replace("\\", "/"))


def subject_readme(subj: Path) -> int:
    mds = [m for m in sorted(subj.rglob("*.md")) if m.name != "README.md"]
    lines = [f"# {subj.name}", "", f"共 **{len(mds)}** 题，含题面、评分标准与配图。", ""]
    lines.append("> 公式为 LaTeX，需 KaTeX/MathJax 渲染（Obsidian、Typora、VS Code + Markdown Preview Enhanced）。")
    lines.append("")
    for topic in sorted(p for p in subj.iterdir() if p.is_dir()):
        topic_mds = sorted(topic.rglob("*.md"))
        if not topic_mds:
            continue
        lines.append(f"## {topic.name}（{len(topic_mds)} 题）")
        lines.append("")
        for sub in sorted(p for p in topic.iterdir() if p.is_dir()):
            sub_mds = sorted(sub.glob("*.md"))
            if not sub_mds:
                continue
            lines.append(f"### {sub.name}（{len(sub_mds)}）")
            lines.append("")
            lines.append("| 题号 | 分值 | 难度 | 计算器 |")
            lines.append("|---|---|---|---|")
            for md in sub_mds:
                fm = read_fm(md)
                lines.append(
                    f"| [{fm.get('reference', md.stem)}]({rel(md, subj)}) "
                    f"| {fm.get('marks', '')} | {fm.get('difficulty', '')} "
                    f"| {'✓' if fm.get('calculator') == 'true' else ''} |"
                )
            lines.append("")
    (subj / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return len(mds)


subjects = sorted(p for p in ROOT.iterdir() if p.is_dir())
rows, grand = [], 0
for subj in subjects:
    n = subject_readme(subj)
    grand += n
    topics = len([p for p in subj.iterdir() if p.is_dir()])
    rows.append((subj.name, n, topics))

lines = ["# IB 题库（六科）", ""]
lines.append(f"共 **{len(rows)} 个科目、{grand} 题**。每题一个 Markdown 文件，含题面、评分标准（A1/M1 给分点）与配图。")
lines.append("")
lines.append("| 科目 | 题数 | topic 数 |")
lines.append("|---|---|---|")
for name, n, topics in rows:
    lines.append(f"| [{name}]({quote(name)}/README.md) | {n} | {topics} |")
lines.append("")
lines.append("## 说明")
lines.append("")
lines.append("- **SL 的题目是 HL 的子集**：AA SL 的 225 个题号、AI SL 的 182 个题号全部出现在对应 HL 里，且内容逐字节相同。")
lines.append("  也就是说去重后的独立题目是 AA HL + AI HL + Physics HL + Chemistry HL 四科。")
lines.append("- 各科 topic 覆盖情况：AA HL 6/6、Physics HL 6/6、Chemistry HL 7/7 全开；AA SL / AI HL / AI SL 只开了前 2 个 topic（会员按科目售卖）。")
lines.append("- 公式为 LaTeX，需 KaTeX/MathJax 渲染。")
lines.append("- 图片在各题目录的 `images/` 下。")
(ROOT / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")

print(f"总索引 {ROOT / 'INDEX.md'}")
for name, n, topics in rows:
    print(f"  {name:<26} {n:>4} 题 / {topics} topics")
print(f"  合计 {grand} 题")
