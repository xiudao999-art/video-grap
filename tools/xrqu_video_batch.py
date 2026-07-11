"""Batch-download preview clips for ALL video categories on xrqu.com/video.
Skips already-downloaded categories (memes, memes-cn, time-card) and skips existing files (resume)."""
import json
import os
import re
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "https://xrqu-api.gongyier.com:3321"
BASE = Path("D:/video-grap/Downloaded/xrqu_视频")
DONE_CATS = {"memes", "memes-cn", "time-card"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.xrqu.com",
    "Referer": "https://www.xrqu.com/",
}
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def sanitize(name):
    name = ILLEGAL.sub("_", name or "").rstrip(" .")
    return name or "_"

def list_cats():
    r = requests.post(API + "/file/data/list_cat",
                      data={"type": "video", "page": "1", "num": "200", "tag": "", "token": ""},
                      headers=HEADERS, timeout=30)
    return (r.json() or {}).get("result", {}).get("cats", []) or []

def get_files(catkey):
    files = []
    pg = 1
    while pg <= 10:
        try:
            r = requests.post(API + "/file/data/list",
                              data={"catkey": catkey, "page": str(pg), "num": "500", "token": ""},
                              headers=HEADERS, timeout=40)
            arr = (r.json() or {}).get("result") or []
        except Exception:
            arr = []
        if not arr:
            break
        files.extend(arr)
        if len(arr) < 500:
            break
        pg += 1
        time.sleep(0.2)
    return files

def download_one(target: Path, url: str):
    if target.exists() and target.stat().st_size > 0:
        return ("skip", target.stat().st_size)
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200 and r.content and len(r.content) > 1000:
                tmp = target.with_suffix(target.suffix + ".part")
                tmp.write_bytes(r.content)
                os.replace(tmp, target)
                return ("ok", len(r.content))
            time.sleep(0.8 * (attempt + 1))
        except Exception:
            time.sleep(1.2 * (attempt + 1))
    return ("fail", 0)

def process_cat(cat):
    ck = cat["catkey"]
    title = cat.get("title", "")
    cat_dir = BASE / f"{sanitize(ck)}_previews"
    cat_dir.mkdir(parents=True, exist_ok=True)
    files = get_files(ck)
    if not files:
        return (ck, title, 0, 0, 0, 0, ["empty"])
    ok = skip = fail = 0
    failures = []
    t0 = time.time()
    def work(fl):
        fname = sanitize(fl["filename"])
        if not fname.lower().endswith(".mp4"):
            fname += ".mp4"
        target = cat_dir / fname
        st, _ = download_one(target, fl.get("preview", ""))
        return (st, fl.get("filename"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(work, f) for f in files]
        for fu in as_completed(futs):
            st, fn = fu.result()
            if st == "ok": ok += 1
            elif st == "skip": skip += 1
            else:
                fail += 1
                failures.append(fn)
    elapsed = time.time() - t0
    print(f"[{ck}] {title}: files={len(files)} ok={ok} skip={skip} fail={fail} ({elapsed:.0f}s)", flush=True)
    return (ck, title, len(files), ok, skip, fail, failures)

def main():
    BASE.mkdir(parents=True, exist_ok=True)
    cats = list_cats()
    print(f"total video cats: {len(cats)}", flush=True)
    todo = [c for c in cats if c["catkey"] not in DONE_CATS]
    print(f"to download: {len(todo)} cats (skipping {len(DONE_CATS)} done)", flush=True)
    grand = {"ok": 0, "skip": 0, "fail": 0, "files": 0}
    all_failures = []
    for i, c in enumerate(todo, 1):
        print(f"--- [{i}/{len(todo)}] ---", flush=True)
        ck, title, nfiles, ok, skip, fail, fails = process_cat(c)
        grand["files"] += nfiles
        grand["ok"] += ok
        grand["skip"] += skip
        grand["fail"] += fail
        if fails and fails != ["empty"]:
            all_failures.append({"cat": ck, "fails": fails[:20]})
    report = BASE / "_batch_report.json"
    report.write_text(json.dumps({"todo_cats": len(todo), **grand, "failures_by_cat": all_failures},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGRAND TOTAL: files={grand['files']} ok={grand['ok']} skip={grand['skip']} fail={grand['fail']}", flush=True)
    print(f"report -> {report}", flush=True)

if __name__ == "__main__":
    main()
