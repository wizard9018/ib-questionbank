import re
from pathlib import Path

files = 0
begin_bare = begin_ok = end_bare = end_ok = 0
for md in Path("questions").rglob("*.md"):
    if md.name in ("README.md", "INDEX.md"):
        continue
    t = md.read_text(encoding="utf-8", errors="replace")
    if "\\begin" not in t:
        continue
    files += 1
    begin_bare += len(re.findall(r"\\begin(?!\{)", t))
    begin_ok += len(re.findall(r"\\begin\{", t))
    end_bare += len(re.findall(r"\\end(?!\{)", t))
    end_ok += len(re.findall(r"\\end\{", t))

print(f"含 \\begin 的文件: {files}")
print(f"裸 \\begin (无括号): {begin_bare}   带括号: {begin_ok}")
print(f"裸 \\end   (无括号): {end_bare}   带括号: {end_ok}")
