"""把题目配图上传到 Supabase Storage 的 questions 桶。

用法：
    python supabase/upload_images.py --dry-run   # 只看要传多少
    python supabase/upload_images.py             # 真传

路径保持 questions/<科目>/<topic>/<小节>/images/<文件> 的层级，
前端用 public URL 拼同一个相对路径即可。
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "questions"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module  # noqa: E402
load_env = import_module("import").load_env

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"}
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp"}


def upload(cfg, path: Path, rel: str, session: requests.Session):
    url = cfg["SUPABASE_URL"].rstrip("/") + "/storage/v1/object/questions/" + quote(rel)
    headers = {
        "Authorization": "Bearer " + cfg["SUPABASE_SERVICE_KEY"],
        "Content-Type": MIME.get(path.suffix.lower(), "application/octet-stream"),
        "x-upsert": "true",
        "Cache-Control": "public, max-age=31536000",
    }
    for attempt in range(3):
        try:
            r = session.post(url, headers=headers, data=path.read_bytes(), timeout=120)
            if r.status_code in (200, 201):
                return None
            if r.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            return f"{rel} → {r.status_code} {r.text[:120]}"
        except requests.RequestException as e:
            time.sleep(1.5 * (attempt + 1))
            if attempt == 2:
                return f"{rel} → {e}"
    return f"{rel} → 重试耗尽"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    files = [p for p in QUESTIONS.rglob("*") if p.suffix.lower() in IMG_EXT]
    total_mb = sum(p.stat().st_size for p in files) / 1024 / 1024
    print(f"待传图片 {len(files)} 个，{total_mb:.1f} MB")
    if args.dry_run:
        for p in files[:5]:
            print("  例:", p.relative_to(QUESTIONS).as_posix())
        return

    cfg = load_env()
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16)
    session.mount("https://", adapter)

    done, failed = 0, []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(upload, cfg, p, p.relative_to(QUESTIONS).as_posix(), session): p
            for p in files
        }
        for fut in as_completed(futures):
            err = fut.result()
            done += 1
            if err:
                failed.append(err)
            if done % 300 == 0:
                rate = done / max(time.time() - t0, 1e-6)
                print(f"  {done}/{len(files)}  ({rate:.1f} 张/秒, 失败 {len(failed)})")

    print(f"\n完成 {done - len(failed)} 个，失败 {len(failed)} 个，耗时 {time.time() - t0:.0f}s")
    for e in failed[:10]:
        print("  ", e)


if __name__ == "__main__":
    main()
