# -*- coding: utf-8 -*-
"""Batch caption multiple xrqu video categories. Sequential across categories, 4 workers within each."""
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xrqu_video_caption import (encode_video, call_doubao, parse_json_obj, load_existing,
                                 VID_ROOT, INDEX_ROOT, MASTER_INDEX, PROMPT)

# 8 target categories: catkey -> Chinese title
TARGETS = [
    ("memes", "经典搞笑剪辑片段"),
    ("memes-cn", "国内搞笑转场片段"),
    ("emoji", "Emoji表情动画"),
    ("show剪辑", "综艺动画：剪辑特效"),
    ("time-card", "海绵宝宝时间卡"),
    ("countdown", "倒计时加载特效"),
    ("scene年会", "年会开场颁奖典礼"),
    ("show花字", "综艺动画：花字配文"),
]

_lock = threading.Lock()

def caption_one(img_path, rel_path, catkey, cat_title):
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
        "path": rel_path, "catkey": catkey, "cat_title": cat_title, "filename": img_path.name,
        "content": obj.get("content", ""),
        "emotions": obj.get("emotions", []) or [],
        "scenarios": obj.get("scenarios", []) or [],
        "tags": obj.get("tags", []) or [],
        **({"_parse_error": True} if obj.get("_parse_error") else {}),
    }, None

def process_cat(catkey, cat_title):
    cat_dir = VID_ROOT / f"{catkey}_previews"
    jsonl = INDEX_ROOT / f"{catkey}.jsonl"
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    if not cat_dir.exists():
        print(f"[{catkey}] {cat_title}: DIR NOT FOUND {cat_dir}", flush=True)
        return 0, 0
    files = sorted(cat_dir.glob("*.mp4"))
    done = load_existing(jsonl)
    todo = [(p, f"xrqu_视频/{catkey}_previews/{p.name}") for p in files
            if f"xrqu_视频/{catkey}_previews/{p.name}" not in done]
    print(f"[{catkey}] {cat_title}: {len(files)} mp4, {len(done)} done, {len(todo)} to caption", flush=True)
    if not todo:
        return len(done), 0
    ok = fail = 0
    t0 = time.time()
    out = open(jsonl, "a", encoding="utf-8")
    try:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(caption_one, p, r, catkey, cat_title): r for (p, r) in todo}
            for fu in as_completed(futs):
                rec, err = fu.result()
                if rec is None:
                    fail += 1; continue
                with _lock:
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush(); ok += 1
                if (ok + fail) % 50 == 0:
                    print(f"  [{catkey}] progress ok={ok} fail={fail} ({time.time()-t0:.0f}s)", flush=True)
    finally:
        out.close()
    print(f"[{catkey}] DONE ok={ok} fail={fail} ({time.time()-t0:.0f}s)", flush=True)
    return len(done) + ok, fail

def main():
    if not os.environ.get("ARK_API_KEY"):
        print("[ERROR] ARK_API_KEY not set", flush=True); return 2
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    grand_ok = grand_fail = 0
    for i, (ck, title) in enumerate(TARGETS, 1):
        print(f"=== [{i}/{len(TARGETS)}] ===", flush=True)
        ncap, nfail = process_cat(ck, title)
        results.append({"type": "video", "catkey": ck, "title": title, "files": ncap, "captioned": ncap, "failed": nfail, "jsonl": f"索引/xrqu_视频/{ck}.jsonl"})
        grand_fail += nfail
    # update master index
    mi = json.loads(MASTER_INDEX.read_text(encoding="utf-8")) if MASTER_INDEX.exists() else {"categories": []}
    cats = [c for c in mi.get("categories", []) if not (c.get("type") == "video" and c.get("catkey") in {t[0] for t in TARGETS})]
    cats.extend(results)
    mi["categories"] = cats
    MASTER_INDEX.write_text(json.dumps(mi, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGRAND: fail={grand_fail}", flush=True)
    for r in results:
        print(f"  {r['title']}: {r['captioned']}", flush=True)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
