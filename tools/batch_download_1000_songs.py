"""批量下载1000首歌曲 - 先测试10首验证。"""
import json, subprocess, time, re
from pathlib import Path

DATA = Path("D:/video-grap/Downloaded/qishui_music_song_list.json")
OUT = Path("D:/video-grap/Downloaded/music_batch")
YTDLP = "C:/Users/VAIO/.local/bin/yt-dlp.exe"
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def sanitize(name):
    name = ILLEGAL.sub("_", name or "")
    return name.rstrip(" .")[:60]

def download_one(idx, title, artist, test=True):
    query = f"{title} {artist}"
    fname = f"{idx:04d}_{sanitize(title)}_{sanitize(artist)}"
    target = OUT / f"{fname}.mp3"

    if target.exists() and target.stat().st_size > 1000:
        return {"status": "skipped", "path": str(target)}

    cmd = [
        YTDLP, "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--no-playlist", "-o", str(OUT / fname) + ".%(ext)s",
        f"ytsearch:{query}"
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          encoding="utf-8", errors="replace")
        if r.returncode == 0:
            # Find output file
            mp3_files = list(OUT.glob(f"{fname}*"))
            actual = [f for f in mp3_files if not f.name.endswith(".part") and f.suffix in (".mp3", ".m4a", ".webm")]
            if actual:
                fpath = actual[0]
                if fpath.suffix != ".mp3":
                    target = fpath.with_suffix(".mp3")
                    fpath.rename(target)
                    fpath = target
                return {"status": "success", "path": str(fpath)}
        return {"status": "failed", "error": f"yt-dlp exit {r.returncode}: {r.stderr[:200]}"}
    except Exception as e:
        return {"status": "failed", "error": str(e)[:200]}

def main(start_idx=1, end_idx=None):
    data = json.loads(DATA.read_text(encoding="utf-8"))
    songs = data["✅可用"]["songs"]
    total = len(songs)

    if end_idx is None:
        end_idx = min(start_idx + 9, total)  # default 10 test

    batch = songs[start_idx-1:end_idx]
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    print(f"Downloading songs {start_idx}-{end_idx}...")
    for song in batch:
        idx = start_idx + batch.index(song)
        # ...

if __name__ == "__main__":
    main()
