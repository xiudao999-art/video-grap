"""Download all xrqu emoji images listed in _manifest.json.
Image host (xrqu-file.gongyier.com:3321) is not rate-limited, unlike the API host.
- Concurrent (8 workers), rate-limited, resume-safe (skip existing non-empty files).
- Saves to D:/video-grap/Downloaded/xrqu_表情/<cat_title>/<filename>
- Writes _download_report.json with failures."""
import json
import os
import re
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("D:/video-grap/Downloaded/xrqu_表情")
MANIFEST = ROOT / "_manifest.json"
REPORT = ROOT / "_download_report.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Referer": "https://www.xrqu.com/",
    "Origin": "https://www.xrqu.com",
}
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def sanitize(name: str) -> str:
    name = ILLEGAL.sub("_", name or "")
    name = name.rstrip(" .")  # Windows hates trailing dot/space
    return name or "_"

_lock = threading.Lock()
_done = 0
_failed = []
_ok = 0
_skip = 0
_bytes = 0

def download_one(cat_dir: Path, fl: dict) -> tuple:
    """Returns (status, bytes). status in {'ok','skip','fail'}."""
    fname = sanitize(fl["filename"])
    if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")):
        fname += "." + (fl.get("format") or "img").lower()
    target = cat_dir / fname
    if target.exists() and target.stat().st_size > 0:
        return ("skip", target.stat().st_size)
    url = fl["preview"]
    if not url:
        return ("fail", 0)
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=40)
            if r.status_code == 200 and r.content:
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_suffix(target.suffix + ".part")
                tmp.write_bytes(r.content)
                os.replace(tmp, target)
                return ("ok", len(r.content))
            time.sleep(1.0 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return ("fail", 0)

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # build flat task list
    tasks = []  # (cat_dir, fl, cat_title)
    for m in manifest:
        cat_dir = ROOT / sanitize(m["title"])
        for fl in m["files"]:
            tasks.append((cat_dir, fl, m["title"]))
    total = len(tasks)
    print(f"Total files to download: {total}", flush=True)
    t0 = time.time()

    def worker(task):
        cat_dir, fl, title = task
        st, n = download_one(cat_dir, fl)
        global _done, _ok, _skip, _failed, _bytes
        with _lock:
            _done += 1
            if st == "ok":
                _ok += 1; _bytes += n
            elif st == "skip":
                _skip += 1
            else:
                _failed.append({"cat": title, "filename": fl.get("filename"), "fileid": fl.get("fileid")})
            if _done % 100 == 0 or _done == total:
                elapsed = time.time() - t0
                print(f"  progress {_done}/{total}  ok={_ok} skip={_skip} fail={len(_failed)}  "
                      f"bytes={_bytes}  {elapsed:.0f}s", flush=True)
        return st

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(worker, tasks))

    elapsed = time.time() - t0
    REPORT.write_text(json.dumps({
        "total": total, "ok": _ok, "skip": _skip, "failed": len(_failed),
        "bytes": _bytes, "elapsed_seconds": round(elapsed, 1),
        "failures": _failed[:500],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE. ok={_ok} skip={_skip} fail={len(_failed)} bytes={_bytes} ({elapsed:.0f}s)", flush=True)
    print(f"Report -> {REPORT}", flush=True)

if __name__ == "__main__":
    main()
