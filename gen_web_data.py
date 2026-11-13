"""把抓好的题目导出成网页用的数据（data.js，用 <script> 加载以绕开 file:// 的 fetch 限制）。

输出：web/data.js  ->  window.RV_DATA = {...}
图片路径在这里就改写成相对 web 目录的 URL 编码路径，前端直接 <img src>。
"""
import json
import re
from pathlib import Path
from urllib.parse import quote

SRC = Path("questions")
OUT = Path("web/data.js")
SUBJECTS = sorted(p.name for p in SRC.iterdir() if p.is_dir())

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
IMG_RE = re.compile(r"!\[([^\]]*)\]\((?:<([^>]+)>|([^)\s]+))\)")


def parse_front_matter(text: str) -> tuple[dict, str]:
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
    """把 Markdown 图片换成 <img>（路径 URL 编码），免得 marked 在空格/括号上截断。"""

    def repl(m):
        alt = m.group(1)
        ref = (m.group(2) or m.group(3) or "").strip()
        name = ref.split("/")[-1]
        src = img_dir_rel + "/" + quote(name)
        return f'<img src="{src}" alt="{alt}">'

    return IMG_RE.sub(repl, md)


def split_sections(body: str) -> tuple[str, str]:
    """题面 / 评分标准分开。"""
    m = re.search(r"\n---\n\n## 评分标准[^\n]*\n", body)
    if not m:
        return body.strip(), ""
    return body[: m.start()].strip(), body[m.end():].strip()


def main():
    data = []
    for subject in SUBJECTS:
        sroot = SRC / subject
        if not sroot.exists():
            continue
        topics = []
        for tdir in sorted(p for p in sroot.iterdir() if p.is_dir()):
            subtopics = []
            for sdir in sorted(p for p in tdir.iterdir() if p.is_dir()):
                qs = []
                for md in sorted(sdir.glob("*.md")):
                    fm, rest = parse_front_matter(md.read_text(encoding="utf-8", errors="replace"))
                    rest = re.sub(r"^#\s+.*?\n", "", rest, count=1).strip()
                    body, ms = split_sections(rest)
                    # 图片目录：相对 web/ 的路径
                    img_rel = f"questions/{quote(subject)}/{quote(tdir.name)}/{quote(sdir.name)}/images"
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
            if subtopics:
                topics.append({"name": tdir.name, "subtopics": subtopics})
        if topics:
            data.append({"name": subject, "topics": topics})

    total = sum(len(s["questions"]) for sub in data for t in sub["topics"] for s in t["subtopics"])
    payload = json.dumps({"subjects": data}, ensure_ascii=False, separators=(",", ":"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.RV_DATA = " + payload + ";\n", encoding="utf-8")
    print(f"写入 {OUT}　{len(payload)/1024/1024:.2f} MB，{total} 题")
    for sub in data:
        n = sum(len(s["questions"]) for t in sub["topics"] for s in t["subtopics"])
        print(f"  {sub['name']}: {n} 题, {len(sub['topics'])} topics")


if __name__ == "__main__":
    main()
