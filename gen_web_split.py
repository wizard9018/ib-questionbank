"""把题库导出成按科目拆分的网页数据（避免一次加载 30+ MB）。

输出：
    web/data/index.js           window.RV_INDEX = [{slug, name, count}]
    web/data/<slug>.js          window.RV_LOADED['<slug>'] = {name, topics}

前端点击某个科目时再动态插入 <script> 加载对应文件。
"""
import json
import re
from pathlib import Path
from urllib.parse import quote

SRC = Path("questions")
OUTDIR = Path("web/data")
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
IMG_RE = re.compile(r"!\[([^\]]*)\]\((?:<([^>]+)>|([^)\s]+))\)")


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "subject"


def parse_front_matter(text: str):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def rewrite_images(md: str, img_dir_rel: str) -> str:
    def repl(m):
        alt = m.group(1)
        ref = (m.group(2) or m.group(3) or "").strip()
        name = ref.split("/")[-1]
        return f'<img src="{img_dir_rel}/{quote(name)}" alt="{alt}">'
    return IMG_RE.sub(repl, md)


def split_sections(body: str):
    m = re.search(r"\n---\n\n## 评分标准[^\n]*\n", body)
    if not m:
        return body.strip(), ""
    return body[: m.start()].strip(), body[m.end():].strip()


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for old in OUTDIR.glob("*.js"):
        old.unlink()

    index = []
    total = 0
    for subj_dir in sorted(p for p in SRC.iterdir() if p.is_dir()):
        slug = slugify(subj_dir.name)
        topics = []
        count = 0
        for tdir in sorted(p for p in subj_dir.iterdir() if p.is_dir()):
            subtopics = []
            for sdir in sorted(p for p in tdir.iterdir() if p.is_dir()):
                qs = []
                for md in sorted(sdir.glob("*.md")):
                    if md.name in ("README.md", "INDEX.md"):
                        continue
                    fm, rest = parse_front_matter(md.read_text(encoding="utf-8", errors="replace"))
                    rest = re.sub(r"^#\s+.*?\n", "", rest, count=1).strip()
                    body, ms = split_sections(rest)
                    img_rel = (f"questions/{quote(subj_dir.name)}/"
                               f"{quote(tdir.name)}/{quote(sdir.name)}/images")
                    qs.append({
                        "ref": fm.get("reference", md.stem),
                        "marks": fm.get("marks", ""),
                        "difficulty": fm.get("difficulty", ""),
                        "calculator": fm.get("calculator", "") == "true",
                        "paper": fm.get("paper", ""),
                        "type": fm.get("type", ""),
                        "body": rewrite_images(body, img_rel),
                        "markScheme": rewrite_images(ms, img_rel) if ms else "",
                    })
                if qs:
                    subtopics.append({"name": sdir.name, "questions": qs})
                    count += len(qs)
            if subtopics:
                topics.append({"name": tdir.name, "subtopics": subtopics})

        if not topics:
            continue
        payload = json.dumps({"name": subj_dir.name, "topics": topics},
                             ensure_ascii=False, separators=(",", ":"))
        (OUTDIR / f"{slug}.js").write_text(
            f"window.RV_LOADED['{slug}'] = {payload};\n", encoding="utf-8")
        index.append({"slug": slug, "name": subj_dir.name, "count": count})
        total += count
        print(f"  {subj_dir.name:<26} {count:>5} 题 -> data/{slug}.js "
              f"({len(payload)/1024/1024:.1f} MB)")

    (OUTDIR / "index.js").write_text(
        "window.RV_INDEX = " + json.dumps(index, ensure_ascii=False) +
        ";\nwindow.RV_LOADED = window.RV_LOADED || {};\n", encoding="utf-8")
    print(f"\n共 {len(index)} 个科目、{total} 题，清单写入 data/index.js")


if __name__ == "__main__":
    main()
