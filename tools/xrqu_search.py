# -*- coding: utf-8 -*-
"""Keyword search over xrqu caption JSONL files (档1, no vector DB needed).
Usage:
  python tools/xrqu_search.py "得意"              # 全库搜情感/场景/标签/内容
  python tools/xrqu_search.py "得意" --cat 仓鼠🐹  # 限定分类
  python tools/xrqu_search.py "看别人出丑" --limit 20
Prints: path | emotions | scenarios  for each match.
"""
import argparse
import json
import sys
from pathlib import Path

INDEX_ROOT = Path("D:/video-grap/索引")
DL_ROOT = Path("D:/video-grap/Downloaded")

def iter_records(cat_filter=None):
    for sub in ("xrqu_表情", "xrqu_视频"):
        d = INDEX_ROOT / sub
        if not d.exists():
            continue
        for jf in d.glob("*.jsonl"):
            for line in jf.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if cat_filter and cat_filter not in rec.get("cat_title", "") and cat_filter not in rec.get("catkey", ""):
                    continue
                yield rec

def match(rec, q):
    blob = " ".join([
        rec.get("content", ""),
        " ".join(rec.get("emotions", [])),
        " ".join(rec.get("scenarios", [])),
        " ".join(rec.get("tags", [])),
    ])
    return q.lower() in blob.lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--cat", default=None, help="限定分类标题或 catkey 子串")
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()
    n = 0
    for rec in iter_records(args.cat):
        if match(rec, args.query):
            print(f"{rec['path']}")
            print(f"  情感: {rec.get('emotions', [])}")
            print(f"  场景: {rec.get('scenarios', [])}")
            print(f"  内容: {rec.get('content', '')[:80]}")
            n += 1
            if n >= args.limit:
                break
    print(f"\n[{n} matches{', truncated' if n>=args.limit else ''}]", file=sys.stderr)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
