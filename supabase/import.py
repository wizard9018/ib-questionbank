"""把本地 questions/ 下的题目导入 Supabase。

用法：
    python supabase/import.py              # 全量导入
    python supabase/import.py --limit 50   # 先导 50 题试水

前置：在 supabase/.env 里填 SUPABASE_URL / SUPABASE_SERVICE_KEY
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "questions"
ENV = Path(__file__).resolve().parent / ".env"


def load_env() -> dict:
    cfg = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    if not cfg.get("SUPABASE_URL"):
        sys.exit("缺 SUPABASE_URL：先填 supabase/.env")
    if not cfg.get("SUPABASE_SERVICE_KEY"):
        sys.exit("缺 SUPABASE_SERVICE_KEY（导数据要写权限，anon key 不够）")
    return cfg


def parse_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
        text = text[m.end():]

    # 去掉开头的一级标题（# PH0001）
    text = re.sub(r"^#\s+\S+\s*\n+", "", text.lstrip())

    parts = re.split(r"^##\s*评分标准.*$", text, flags=re.M)
    body = parts[0].strip()
    mark_scheme = parts[1].strip() if len(parts) > 1 else ""
    return fm, body, mark_scheme


def level_of(name: str):
    if name.endswith(" HL"):
        return "HL"
    if name.endswith(" SL"):
        return "SL"
    return None


def collect(limit=None):
    subjects, topics, subtopics, questions = {}, {}, {}, []

    mds = [p for p in QUESTIONS.rglob("*.md") if p.name not in ("README.md", "INDEX.md")]
    mds.sort(key=lambda p: str(p))
    if limit:
        mds = mds[:limit]

    seen = {}   # (subject_slug, ref) -> 记录；同一题在多处归档时只留最具体的

    for i, p in enumerate(mds, 1):
        rel = p.relative_to(QUESTIONS).parts
        if len(rel) < 4:
            continue
        subject_name, topic_name, subtopic_name = rel[0], rel[1], rel[2]
        fm, body, ms = parse_md(p)
        if not body:
            continue

        def generic(t, st):
            return t.strip().lower().startswith("scientific skills") or st.strip().lower() == "unassigned"

        slug_pre = subject_name.lower().replace(" ", "-").replace(".", "")
        ref_pre = fm.get("reference") or p.stem
        k = (slug_pre, ref_pre)
        if k in seen:
            prev = seen[k]
            # 已存的是兜底分类、新的是具体章节 -> 用新的替换掉
            if generic(prev["topic"], prev["subtopic"]) and not generic(topic_name, subtopic_name):
                seen[k] = None   # 稍后覆盖，先标记
                replace_key = k
            else:
                continue
        else:
            replace_key = None

        slug = subject_name.lower().replace(" ", "-").replace(".", "")
        group_key = re.sub(r"-(hl|sl)$", "", slug)

        subjects.setdefault(slug, {
            "slug": slug, "group_key": group_key, "name": subject_name,
            "level": level_of(subject_name), "position": 0, "question_count": 0,
        })
        subjects[slug]["question_count"] += 1

        tkey = (slug, topic_name)
        if tkey not in topics:
            topics[tkey] = {"subject_slug": slug, "name": topic_name,
                            "position": len([k for k in topics if k[0] == slug])}

        stkey = (slug, topic_name, subtopic_name)
        if stkey not in subtopics:
            subtopics[stkey] = {"topic": tkey, "name": subtopic_name, "position": 0}

        marks = fm.get("marks", "")
        questions.append({
            "ref": fm.get("reference") or p.stem,
            "subject_slug": slug,
            "subject_key": group_key,
            "topic": topic_name,
            "subtopic": subtopic_name,
            "body": body,
            "mark_scheme": ms or None,
            "difficulty": fm.get("difficulty") or None,
            "marks": int(marks) if marks.isdigit() else None,
            "paper": fm.get("paper") or None,
            "calculator": (fm.get("calculator", "").lower() == "true"),
            "images": [],
        })

        rec = questions[-1]
        if replace_key is not None or replace_key == ():
            pass
        if k in seen and seen[k] is None:
            # 覆盖之前那条
            for idx in range(len(questions) - 2, -1, -1):
                q = questions[idx]
                if (q["subject_slug"], q["ref"]) == k:
                    questions[idx] = rec
                    questions.pop()
                    break
        seen[k] = rec

        if i % 2000 == 0:
            print(f"  解析 {i}/{len(mds)} …")

    return subjects, topics, subtopics, questions


def post(cfg, table, rows, chunk=400):
    url = cfg["SUPABASE_URL"].rstrip("/") + f"/rest/v1/{table}"
    headers = {
        "apikey": cfg["SUPABASE_SERVICE_KEY"],
        "Authorization": "Bearer " + cfg["SUPABASE_SERVICE_KEY"],
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    total = 0
    for i in range(0, len(rows), chunk):
        batch = rows[i:i + chunk]
        for attempt in range(4):
            r = requests.post(url, headers=headers, json=batch, timeout=90)
            if r.status_code in (200, 201, 204):
                break
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 * (attempt + 1))
                continue
            sys.exit(f"{table} 导入失败 {r.status_code}: {r.text[:400]}")
        else:
            sys.exit(f"{table} 重试耗尽: {r.text[:300]}")
        total += len(batch)
        print(f"  {table}: {total}/{len(rows)}")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    cfg = load_env()
    print("解析本地题目 …")
    subjects, topics, subtopics, questions = collect(args.limit)
    print(f"  科目 {len(subjects)} · 章节 {len(topics)} · 小节 {len(subtopics)} · 题目 {len(questions)}")

    print("导入科目 …")
    post(cfg, "subjects", list(subjects.values()))

    # topics / subtopics 需要回填自增 id，先清空再插
    print("导入章节 …")
    topic_rows = [{"subject_slug": k[0], "name": k[1], "position": v["position"]}
                  for k, v in topics.items()]
    post(cfg, "topics", topic_rows)

    url = cfg["SUPABASE_URL"].rstrip("/") + "/rest/v1/topics?select=id,subject_slug,name"
    headers = {"apikey": cfg["SUPABASE_SERVICE_KEY"],
               "Authorization": "Bearer " + cfg["SUPABASE_SERVICE_KEY"]}
    got = requests.get(url, headers=headers, timeout=90).json()
    tmap = {(t["subject_slug"], t["name"]): t["id"] for t in got}

    sub_rows = []
    for (slug, topic, sub), v in subtopics.items():
        tid = tmap.get((slug, topic))
        if tid:
            sub_rows.append({"topic_id": tid, "name": sub, "position": v["position"]})
    print("导入小节 …")
    post(cfg, "subtopics", sub_rows)

    print("导入题目 …")
    post(cfg, "questions", questions, chunk=300)

    print("完成。")


if __name__ == "__main__":
    main()
