"""Download songs batch by range."""
import json, subprocess, re, sys
from pathlib import Path

OUT = Path("D:/video-grap/Downloaded/music_batch")
YTDLP = "C:/Users/VAIO/.local/bin/yt-dlp.exe"
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
OUT.mkdir(parents=True, exist_ok=True)

def sanitize(name):
    return ILLEGAL.sub("_", name or "").rstrip(" .")[:60]

def download_one(idx, title, artist):
    query = f"{title} {artist}"
    fname = f"{idx:04d}_{sanitize(title)}_{sanitize(artist)}"
    target = OUT / f"{fname}.mp3"
    if target.exists() and target.stat().st_size > 1000:
        return {"status": "SKIPPED", "path": str(target)}

    cmd = [YTDLP, "-x", "--audio-format", "mp3", "--audio-quality", "0",
           "--no-playlist", "-o", str(OUT / fname) + ".%(ext)s", f"ytsearch:{query}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          encoding="utf-8", errors="replace")
        if r.returncode == 0:
            mp3_files = list(OUT.glob(f"{fname}*"))
            actual = [f for f in mp3_files if not f.name.endswith(".part") and f.suffix in (".mp3", ".m4a", ".webm")]
            if actual:
                fpath = actual[0]
                if fpath.suffix != ".mp3":
                    new_target = fpath.with_suffix(".mp3")
                    fpath.rename(new_target)
                    fpath = new_target
                return {"status": "OK", "path": str(fpath)}
        return {"status": "FAIL", "error": r.stderr[:150]}
    except Exception as e:
        return {"status": "FAIL", "error": str(e)[:150]}

# Usage: python tools/download_batch.py START END
if __name__ == "__main__":
    data = json.loads(Path("D:/video-grap/Downloaded/qishui_music_song_list.json").read_text(encoding="utf-8"))
    songs = data["✅可用"]["songs"]

    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end = int(sys.argv[2]) if len(sys.argv) > 2 else min(start + 9, len(songs))

    results = []
    for song in songs[start-1:end]:
        idx = start + songs[start-1:end].index(song)
        title = song["col_1"]
        artist = song["col_2"]
        r = download_one(idx, title, artist)
        print(f"[{idx:04d}] {r['status']} {title[:40]} - {artist[:30]}")
        results.append({"idx": idx, "title": title, "artist": artist, **r})

    batch_report = OUT / f"_batch_{start}_{end}.json"
    batch_report.write_text(json.dumps({
        "range": [start, end],
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] in ("OK", "SKIPPED")),
        "failed": sum(1 for r in results if r["status"] == "FAIL"),
        "results": results
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Batch done: {start}-{end}, report: {batch_report}")
