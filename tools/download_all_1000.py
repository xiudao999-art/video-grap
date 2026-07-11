"""Download all 1000 songs with ThreadPoolExecutor - reliable single-process."""
import json, subprocess, re, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = Path("D:/video-grap/Downloaded/music_batch")
YTDLP = "C:/Users/VAIO/.local/bin/yt-dlp.exe"
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
OUT.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_results = []
_downloaded = 0

def sanitize(name):
    return ILLEGAL.sub("_", name or "").rstrip(" .")[:60]

def download_one(idx, title, artist):
    global _downloaded
    query = f"{title} {artist}"
    fname = f"{idx:04d}_{sanitize(title)}_{sanitize(artist)}"
    target = OUT / f"{fname}.mp3"

    if target.exists() and target.stat().st_size > 1000:
        with _lock:
            _downloaded += 1
        return {"idx": idx, "title": title, "artist": artist, "status": "SKIPPED"}

    cmd = [YTDLP, "-x", "--audio-format", "mp3", "--audio-quality", "0",
           "--no-playlist", "-o", str(OUT / fname) + ".%(ext)s",
           f"ytsearch:{query}"]

    for attempt in range(2):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=180, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                mp3_files = list(OUT.glob(f"{fname}.*"))
                actual = [f for f in mp3_files if f.suffix in (".mp3", ".m4a") and f.stat().st_size > 1000]
                if actual:
                    fpath = actual[0]
                    if fpath.suffix != ".mp3":
                        new_target = fpath.with_suffix(".mp3")
                        fpath.rename(new_target)
                        fpath = new_target
                    with _lock:
                        _downloaded += 1
                        _results.append({"idx": idx, "title": title, "artist": artist,
                                        "status": "OK", "path": str(fpath)})
                    return {"idx": idx, "title": title, "artist": artist, "status": "OK"}
            time.sleep(2 * (attempt + 1))
        except subprocess.TimeoutExpired:
            time.sleep(3)
        except Exception as e:
            time.sleep(2)

    with _lock:
        _results.append({"idx": idx, "title": title, "artist": artist,
                        "status": "FAIL", "error": r.stderr[:100] if 'r' in dir() else "timeout"})
    return {"idx": idx, "title": title, "artist": artist, "status": "FAIL"}

def main():
    data = json.loads(Path("D:/video-grap/Downloaded/qishui_music_song_list.json").read_text(encoding="utf-8"))
    songs = data["✅可用"]["songs"]
    total = len(songs)

    print(f"Starting download of {total} songs with 8 workers...")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(download_one, i+1, s["col_1"], s["col_2"]): s for i, s in enumerate(songs)}
        for fu in as_completed(futures):
            r = fu.result()
            if r["status"] in ("OK", "SKIPPED"):
                if _downloaded % 100 == 0:
                    elapsed = time.time() - t0
                    print(f"  [{_downloaded}/{total}] OK={sum(1 for x in _results if x['status']=='OK')} "
                          f"SKIP={sum(1 for x in _results if x['status']=='SKIPPED')} "
                          f"FAIL={sum(1 for x in _results if x['status']=='FAIL')} "
                          f"({elapsed:.0f}s)")

    elapsed = time.time() - t0
    ok = sum(1 for r in _results if r["status"] == "OK")
    skip = sum(1 for r in _results if r["status"] == "SKIPPED")
    fail = sum(1 for r in _results if r["status"] == "FAIL")

    print(f"\nDONE in {elapsed:.0f}s")
    print(f"OK: {ok}, SKIPPED: {skip}, FAILED: {fail}")

    report = OUT / "_full_report.json"
    report.write_text(json.dumps({
        "total": total, "ok": ok, "skipped": skip, "failed": fail,
        "elapsed_seconds": round(elapsed),
        "results": _results
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {report}")

if __name__ == "__main__":
    main()
