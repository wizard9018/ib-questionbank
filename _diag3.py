import re
from pathlib import Path

FM = re.compile(r"^---\n(.*?)\n---", re.S)


def refs(subj):
    out = {}
    for md in (Path("questions") / subj).rglob("*.md"):
        if md.name in ("README.md", "INDEX.md"):
            continue
        t = md.read_text(encoding="utf-8", errors="replace")
        m = FM.match(t)
        if not m:
            continue
        ref = None
        for line in m.group(1).splitlines():
            if line.startswith("reference:"):
                ref = line.split(":", 1)[1].strip()
        if ref:
            out[ref] = md
    return out


for hl, sl in [("IB Physics HL", "IB Physics SL"),
               ("IB Chemistry HL", "IB Chemistry SL"),
               ("IB Biology HL", "IB Biology SL"),
               ("IB Mathematics AA HL", "IB Mathematics AA SL"),
               ("IB Mathematics AI HL", "IB Mathematics AI SL")]:
    H, S = refs(hl), refs(sl)
    common = set(H) & set(S)
    only_sl = set(S) - set(H)
    print(f"{hl.split()[-2]} vs {hl.split()[-1]}: HL {len(H)}, SL {len(S)}, 交集 {len(common)}, SL独有 {len(only_sl)}")
    if only_sl:
        print(f"    SL 独有样例: {sorted(only_sl)[:5]}")
