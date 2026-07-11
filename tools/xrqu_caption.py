# -*- coding: utf-8 -*-
"""Batch-caption xrqu emoji images with Doubao Seed 2.1 Pro (ARK Responses API).
For each image: produce {content, emotions, scenarios, tags}. One JSONL file per category.
Each record carries the image's unique relative path so a model can locate the file later.
Resume-safe: skips images already present in the category's JSONL.
Output: D:/video-grap/索引/xrqu_表情/<catkey>.jsonl + master index _index.json
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

IMG_ROOT = Path("D:/video-grap/Downloaded/xrqu_表情")
MANIFEST = Path("D:/video-grap/Downloaded/xrqu_表情/_manifest.json")
INDEX_ROOT = Path("D:/video-grap/索引/xrqu_表情")
MASTER_INDEX = Path("D:/video-grap/索引/_index.json")

# target category titles (exact match against manifest 'title')
TARGET_TITLES = [
    "可爱男孩纸👶", "是喵星人啦🐱", "可爱的女孩纸👧", "莲蓬头男孩👲", "仓鼠🐹",
    "熊本熊🐻", "胖虎🐯", "开心鸭🐥", "杰尼龟", "海绵宝宝", "让子弹飞",
]

ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def sanitize(name: str) -> str:
    name = ILLEGAL.sub("_", name or "").rstrip(" .")
    return name or "_"

PROMPT = (
    "你是表情包标注员。分析这张表情包图片，输出严格JSON（不要markdown代码块、不要解释、直接输出JSON对象）：\n"
    '{"content":"画面内容描述：人物/动物/动作/表情/配文，1-2句中文",'
    '"emotions":["这张图适合表达的情感词，3-6个，如 得意/无语/愤怒/开心/幸灾乐祸/尴尬/震惊/嫌弃/撒娇"],'
    '"scenarios":["适合使用的具体场景，2-4个，具体一些，如 别人吹牛时回复/看别人出丑时/表达无奈/吐槽对方"],'
    '"tags":["视觉标签，3-8个，如 男孩/猫/笑脸/文字/手势/流泪"]}'
)

def encode_image(path: Path) -> str:
    ext = path.suffix.lstrip(".").lower() or "png"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    with open(path, "rb") as f:
        b = f.read()
    return f"data:{mime};base64,{base64.b64encode(b).decode()}"

def call_doubao(image_url: str, retries=4):
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(
                ARK_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": MODEL,
                    "input": [{"role": "user", "content": [
                        {"type": "input_image", "image_url": image_url},
                        {"type": "input_text", "text": PROMPT},
                    ]}],
                    "thinking": {"type": "disabled"},
                },
                timeout=90,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = f"HTTP {resp.status_code}"
                time.sleep(2.0 * (attempt + 1))
                continue
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                time.sleep(1.5 * (attempt + 1))
                continue
            data = resp.json()
            text_out = []
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            text_out.append(c.get("text", ""))
            return "\n".join(text_out).strip()
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(1.5 * (attempt + 1))
    return None  # failed

def parse_json_obj(text: str):
    if not text:
        return None
    # strip markdown fences
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    # find first {...}
    m = re.search(r"\{.*\}", t, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        # try fixing common issues
        try:
            return json.loads(m.group(0).replace("\n", " "))
        except Exception:
            return None

def load_existing(jsonl_path: Path) -> set:
    if not jsonl_path.exists():
        return set()
    paths = set()
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        try:
            paths.add(json.loads(line).get("path"))
        except Exception:
            pass
    return paths

_lock = threading.Lock()
_cat_counts = {}

def caption_one(img_path: Path, rel_path: str, catkey: str, cat_title: str):
    image_url = encode_image(img_path)
    raw = call_doubao(image_url)
    if raw is None:
        return None, "api_failed"
    obj = parse_json_obj(raw)
    if not obj:
        # store raw text as content fallback
        obj = {"content": raw[:300], "emotions": [], "scenarios": [], "tags": [], "_parse_error": True}
    rec = {
        "path": rel_path,
        "catkey": catkey,
        "cat_title": cat_title,
        "filename": img_path.name,
        "content": obj.get("content", ""),
        "emotions": obj.get("emotions", []) or [],
        "scenarios": obj.get("scenarios", []) or [],
        "tags": obj.get("tags", []) or [],
    }
    if obj.get("_parse_error"):
        rec["_parse_error"] = True
    return rec, None

def process_category(cat):
    catkey = cat["catkey"]
    title = cat["title"]
    cat_dir = IMG_ROOT / sanitize(title)
    jsonl = INDEX_ROOT / f"{catkey}.jsonl"
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    done_paths = load_existing(jsonl)
    files = cat.get("files", [])
    # build tasks, skip done
    tasks = []
    for fl in files:
        fname = sanitize(fl["filename"])
        img_path = cat_dir / fname
        rel = f"xrqu_表情/{sanitize(title)}/{fname}"
        if not img_path.exists() or img_path.stat().st_size == 0:
            # try glob fallback (filename may differ slightly)
            cands = list(cat_dir.glob(f"*{Path(fname).stem}*"))
            if cands:
                img_path = cands[0]
                rel = f"xrqu_表情/{sanitize(title)}/{img_path.name}"
            else:
                continue
        if rel in done_paths:
            continue
        tasks.append((img_path, rel))
    if not tasks:
        print(f"[{title}] {len(files)} files, all already captioned. skip.", flush=True)
        return catkey, title, len(files), len(done_paths), 0, 0
    print(f"[{title}] {len(files)} files, {len(done_paths)} done, {len(tasks)} to caption ...", flush=True)
    ok = fail = 0
    t0 = time.time()
    # write incrementally under a lock
    out = open(jsonl, "a", encoding="utf-8")
    try:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(caption_one, p, r, catkey, title): r for (p, r) in tasks}
            for fu in as_completed(futs):
                rec, err = fu.result()
                if rec is None:
                    fail += 1
                    continue
                with _lock:
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    out.flush()
                    ok += 1
    finally:
        out.close()
    elapsed = time.time() - t0
    print(f"  -> ok={ok} fail={fail} ({elapsed:.0f}s)", flush=True)
    return catkey, title, len(files), len(done_paths) + ok, fail

def main():
    if not API_KEY:
        print("[ERROR] ARK_API_KEY not set", flush=True); return 2
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    targets = [m for m in manifest if m["title"] in TARGET_TITLES]
    print(f"target categories: {len(targets)}", flush=True)
    total_files = sum(len(m.get("files", [])) for m in targets)
    print(f"total images to caption (incl. already done): {total_files}", flush=True)
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    summary = []
    for cat in targets:
        ck, title, nfiles, ndone, nfail = process_category(cat)
        summary.append({"catkey": ck, "title": title, "files": nfiles, "captioned": ndone, "failed": nfail,
                        "jsonl": f"索引/xrqu_表情/{ck}.jsonl"})
    # master index
    MASTER_INDEX.parent.mkdir(parents=True, exist_ok=True)
    MASTER_INDEX.write_text(json.dumps({
        "schema": "each jsonl line = {path, catkey, cat_title, filename, content, emotions, scenarios, tags}",
        "image_root": "D:/video-grap/Downloaded/xrqu_表情",
        "categories": summary,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmaster index -> {MASTER_INDEX}", flush=True)
    print("summary:")
    for s in summary:
        print(f"  {s['title']}: {s['captioned']}/{s['files']} (fail={s['failed']})", flush=True)
    return 0

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
