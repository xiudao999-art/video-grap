"""Download all free preview clips for an xrqu.com video category (e.g. memes, memes-cn).
Preview URLs return small mp4 clips (no points needed). Output kept separate from images.
Usage: python xrqu_video_preview_dl.py <catkey> [output_subdir]
   e.g. python xrqu_video_preview_dl.py memes-cn memes-cn_previews"""
import json
import os
import re
import sys
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "https://xrqu-api.gongyier.com:3321"
CATKEY = sys.argv[1] if len(sys.argv) > 1 else "memes"
SUBDIR = sys.argv[2] if len(sys.argv) > 2 else f"{CATKEY}_previews"
ROOT = Path("D:/video-grap/Downloaded/xrqu_视频") / SUBDIR
MANIFEST = ROOT / "_manifest.json"
REPORT = ROOT / "_download_report.json"
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

def get_files(catkey="memes"):
    files = []
    pg = 1
    while pg <= 5:
        r = requests.post(API + "/file/data/list",
                          data={"catkey": catkey, "page": str(pg), "num": "500", "token": ""},
                          headers=HEADERS, timeout=40)
        arr = (r.json() or {}).get("result") or []
        if not arr: break
        files.extend(arr)
        if len(arr) < 500: break
        pg += 1
        time.sleep(0.3)
    return files

_lock = threading.Lock()
_done = _ok = _skip = _fail = 0
_failed = []

def download_one(fl):
    global _done, _ok, _skip, _fail
    fname = sanitize(fl["filename"])
    if not fname.lower().endswith(".mp4"):
        fname += ".mp4"
    target = ROOT / fname
    if target.exists() and target.stat().st_size > 0:
        with _lock:
            _done += 1; _skip += 1
        return ("skip", target.stat().st_size)
    url = fl["preview"]
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=40)
            if r.status_code == 200 and r.content and len(r.content) > 1000:
                tmp = target.with_suffix(".mp4.part")
                tmp.write_bytes(r.content)
                os.replace(tmp, target)
                with _lock:
                    _done += 1; _ok += 1
                return ("ok", len(r.content))
            time.sleep(1.0 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    with _lock:
        _done += 1; _fail += 1
        _failed.append({"filename": fl.get("filename"), "fileid": fl.get("fileid")})
    return ("fail", 0)

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    print(f"[1/2] fetching file list for cat={CATKEY} ...", flush=True)
    files = get_files(CATKEY)
    print(f"  got {len(files)} files", flush=True)
    MANIFEST.write_text(json.dumps([
        {"fileid": f.get("fileid"), "filename": f.get("filename"), "title": f.get("title"),
         "size": f.get("size"), "width": f.get("width"), "height": f.get("height"),
         "preview": f.get("preview"), "cover": f.get("cover")}
        for f in files
    ], ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[2/2] downloading {len(files)} preview clips ...", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(download_one, f) for f in files]
        for fu in as_completed(futs):
            fu.result()
    elapsed = time.time() - t0
    REPORT.write_text(json.dumps({
        "total": len(files), "ok": _ok, "skip": _skip, "failed": _fail,
        "elapsed_seconds": round(elapsed, 1), "failures": _failed,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE. ok={_ok} skip={_skip} fail={_fail} ({elapsed:.0f}s) -> {REPORT}", flush=True)

if __name__ == "__main__":
    main()
