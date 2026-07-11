# -*- coding: utf-8 -*-
"""Caption xrqu video previews with Doubao Seed 2.1 Pro via ARK input_video (VLM watches the clip).
One JSONL per category. Resume-safe. Usage:
  python tools/xrqu_video_caption.py <catkey> [cat_title]
  e.g. python tools/xrqu_video_caption.py funny-abroad 国外搞笑沙雕短视频
"""
import base64
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

MODEL = os.environ.get("ARK_VISION_MODEL", "doubao-seed-2-1-pro-260628")
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
API_KEY = os.environ.get("ARK_API_KEY", "")

VID_ROOT = Path("D:/video-grap/Downloaded/xrqu_视频")
INDEX_ROOT = Path("D:/video-grap/索引/xrqu_视频")
MASTER_INDEX = Path("D:/video-grap/索引/_index.json")

CATKEY = sys.argv[1] if len(sys.argv) > 1 else "funny-abroad"
CAT_TITLE = sys.argv[2] if len(sys.argv) > 2 else CATKEY
CAT_DIR = VID_ROOT / f"{CATKEY}_previews"
JSONL = INDEX_ROOT / f"{CATKEY}.jsonl"

PROMPT = (
    "你是视频素材标注员。这是一段短视频素材（表情/搞笑/转场/特效/场景）。分析后输出严格JSON"
    "（不要markdown代码块、直接输出JSON对象，数组每项是独立的词不要用斜杠合并）：\n"
    '{"content":"画面内容与动作/动效描述，1-3句，注意是视频要描述动态变化、发生了什么",'
    '"emotions":["情感词，每项一个词，如 搞笑","震惊","无语","尴尬","得意"],'
    '"scenarios":["适合使用的场景，每项一条，如 聊天回复搞笑瞬间","视频剪辑转场","吐槽时配图"],'
    '"tags":["视觉或动效标签，每项一个词，如 搞笑","转场","倒计时","绿幕","特效","字幕","真人","动画"]}'
)

def encode_video(path: Path) -> str:
    ext = path.suffix.lstrip(".").lower() or "mp4"
    mime = "video/mp4" if ext in ("mp4", "m4v") else f"video/{ext}"
    with open(path, "rb") as f:
        b = f.read()
    return f"data:{mime};base64,{base64.b64encode(b).decode()}"

def call_doubao(video_url: str, retries=4):
    for attempt in range(retries):
        try:
            resp = requests.post(ARK_URL, headers={"Authorization": f"Bearer {API_KEY}"},
                json={"model": MODEL,
                      "input": [{"role": "user", "content": [
                          {"type": "input_video", "video_url": video_url},
                          {"type": "input_text", "text": PROMPT}]}],
                      "thinking": {"type": "disabled"}},
                timeout=120)
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(2.0 * (attempt + 1)); continue
            if resp.status_code != 200:
                time.sleep(1.5 * (attempt + 1)); continue
            data = resp.json()
            txt = []
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            txt.append(c.get("text", ""))
            return "\n".join(txt).strip()
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None

def parse_json_obj(text):
    if not text: return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t); t = re.sub(r"\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.DOTALL)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception:
        try: return json.loads(m.group(0).replace("\n", " "))
        except Exception: return None

def load_existing(jsonl_path):
    if not jsonl_path.exists(): return set()
    return {json.loads(l).get("path") for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip() and l.strip().startswith("{")}

_lock = threading.Lock()

def caption_one(img_path, rel_path):
    try:
        vurl = encode_video(img_path)
    except Exception as e:
        return None, f"encode_err:{e}"
    raw = call_doubao(vurl)
    if raw is None:
        return None, "api_failed"
    obj = parse_json_obj(raw)
    if not obj:
        obj = {"content": raw[:300], "emotions": [], "scenarios": [], "tags": [], "_parse_error": True}
    return {
        "path": rel_path, "catkey": CATKEY, "cat_title": CAT_TITLE, "filename": img_path.name,
        "content": obj.get("content", ""),
        "emotions": obj.get("emotions", []) or [],
        "scenarios": obj.get("scenarios", []) or [],
        "tags": obj.get("tags", []) or [],
        **({"_parse_error": True} if obj.get("_parse_error") else {}),
    }, None

def main():
    if not API_KEY:
        print("[ERROR] ARK_API_KEY not set", flush=True); return 2
    if not CAT_DIR.exists():
        print(f"[ERROR] {CAT_DIR} not found", flush=True); return 2
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    files = sorted(CAT_DIR.glob("*.mp4"))
    done = load_existing(JSONL)
    todo = [(p, f"xrqu_视频/{CATKEY}_previews/{p.name}") for p in files
            if f"xrqu_视频/{CATKEY}_previews/{p.name}" not in done]
    print(f"[{CATKEY}] {CAT_TITLE}: {len(files)} mp4, {len(done)} done, {len(todo)} to caption", flush=True)
    if not todo:
        print("all done.", flush=True); return 0
    ok = fail = 0
    t0 = time.time()
    out = open(JSONL, "a", encoding="utf-8")
    fails = []
    try:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(caption_one, p, r): r for (p, r) in todo}
            for fu in as_completed(futs):
                rec, err = fu.result()
                if rec is None:
                    fail += 1; fails.append(futs[fu]); continue
                with _lock:
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush(); ok += 1
                if (ok + fail) % 50 == 0:
                    print(f"  progress ok={ok} fail={fail} ({time.time()-t0:.0f}s)", flush=True)
    finally:
        out.close()
    print(f"DONE ok={ok} fail={fail} ({time.time()-t0:.0f}s) -> {JSONL}", flush=True)
    # update master index
    mi = json.loads(MASTER_INDEX.read_text(encoding="utf-8")) if MASTER_INDEX.exists() else {"categories": []}
    cats = [c for c in mi.get("categories", []) if c.get("catkey") != CATKEY or c.get("type") != "video"]
    cats.append({"type": "video", "catkey": CATKEY, "title": CAT_TITLE, "files": len(files),
                 "captioned": len(done) + ok, "failed": fail, "jsonl": f"索引/xrqu_视频/{CATKEY}.jsonl"})
    mi["categories"] = cats
    MASTER_INDEX.write_text(json.dumps(mi, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
