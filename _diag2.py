import re
from collections import Counter
from pathlib import Path

FM = re.compile(r"^---\n(.*?)\n---", re.S)
by_subject = {}
for md in Path("questions").rglob("*.md"):
    if md.name in ("README.md", "INDEX.md"):
        continue
    subj = md.relative_to("questions").parts[0]
    t = md.read_text(encoding="utf-8", errors="replace")
    m = FM.match(t)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
    d = by_subject.setdefault(subj, {"total": 0, "diff": Counter(), "no_diff": 0, "type": Counter()})
    d["total"] += 1
    if fm.get("difficulty"):
        d["diff"][fm["difficulty"]] += 1
    else:
        d["no_diff"] += 1
    d["type"][fm.get("type", "?")] += 1

print(f"{'科目':<26} {'题数':>5} {'有难度':>5} {'无难度':>5}  难度构成")
for subj, d in sorted(by_subject.items(), key=lambda kv: -kv[1]["total"]):
    diff = d["diff"]
    detail = " ".join(f"{k}:{v}" for k, v in diff.most_common()) or "-"
    print(f"{subj:<26} {d['total']:>5} {d['total']-d['no_diff']:>5} {d['no_diff']:>5}  {detail}")

tot = sum(d["total"] for d in by_subject.values())
nod = sum(d["no_diff"] for d in by_subject.values())
print(f"\n总计 {tot} 题，有难度 {tot-nod}，无难度 {nod}")
