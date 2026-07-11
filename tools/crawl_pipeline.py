#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
crawl_pipeline.py - Hybrid crawling layer 2: Use Crawl4AI for规模化采集

[Project Adapted Version]
- Uses global Python 3.12
- Output directory: D:/video-grap/Downloaded/design_crawls/
- Supports design website presets (landing.love, onepagelove, framer, siteinspire)
"""
import os, sys, io, re, json, asyncio, argparse, urllib.parse
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

# Project configuration
PROJECT_ROOT = Path("D:/video-grap")
DOWNLOAD_DIR = PROJECT_ROOT / "Downloaded" / "design_crawls"
STORAGE_DIR = DOWNLOAD_DIR / "storage_states"
URLS_DIR = DOWNLOAD_DIR / "urls"
CONTENT_DIR = DOWNLOAD_DIR / "content"
DATA_DIR = DOWNLOAD_DIR / "data"
SCHEMA_DIR = PROJECT_ROOT / "tools" / "schemas"

DEFAULT_CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME = os.environ.get("HYBRID_CHROME", DEFAULT_CHROME)

try:
    from crawl4ai import (AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode,
                          JsonCssExtractionStrategy)
except ImportError:
    sys.exit("ERROR: crawl4ai not installed. Run: pip install crawl4ai && crawl4ai-setup")

try:
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    _HAS_FILTER = True
except Exception:
    _HAS_FILTER = False

# Design website presets
DESIGN_PRESETS = {
    "landing-love": {
        "url": "https://landing.love",
        "max_depth": 2,
        "max_pages": 100,
        "include": "/",
        "description": "Landing page design gallery"
    },
    "onepagelove": {
        "url": "https://onepagelove.com",
        "max_depth": 3,
        "max_pages": 200,
        "include": "/",
        "description": "One page website inspiration"
    },
    "framer-templates": {
        "url": "https://www.framer.com/templates/",
        "max_depth": 2,
        "max_pages": 150,
        "include": "/templates/",
        "description": "Framer website templates"
    },
    "siteinspire": {
        "url": "https://www.siteinspire.com",
        "max_depth": 3,
        "max_pages": 200,
        "include": "/",
        "description": "Web design inspiration gallery"
    }
}


def ensure_dirs():
    """Create necessary directories."""
    for d in [DOWNLOAD_DIR, STORAGE_DIR, URLS_DIR, CONTENT_DIR, DATA_DIR, SCHEMA_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def build_browser_cfg(args):
    """Build browser config based on authentication method."""
    if getattr(args, "cdp", None):
        print(f"[bridge] Using external Chrome (CDP): {args.cdp}")
        return BrowserConfig(browser_mode="cdp", cdp_url=args.cdp, headless=True)
    if getattr(args, "user_data_dir", None):
        print(f"[bridge] Using persistent profile: {args.user_data_dir}")
        return BrowserConfig(headless=True, use_managed_browser=True,
                             use_persistent_context=True,
                             user_data_dir=os.path.abspath(args.user_data_dir),
                             chrome_channel="chrome")
    if getattr(args, "state", None) and os.path.exists(args.state):
        print(f"[bridge] Using storage_state: {args.state}")
        return BrowserConfig(headless=True, storage_state=os.path.abspath(args.state))
    print("[bridge] No auth state (public pages mode)")
    return BrowserConfig(headless=True)


def make_run_cfg(fit=False, deep=None):
    md_gen = None
    if fit and _HAS_FILTER:
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter())
    kw = dict(cache_mode=CacheMode.BYPASS, markdown_generator=md_gen)
    if deep is not None:
        kw["deep_crawl_strategy"] = deep
    return CrawlerRunConfig(**kw)


def slugify(url, title, idx):
    base = (title or "").strip() or urllib.parse.urlparse(url).path.strip("/").replace("/", "_") or urllib.parse.urlparse(url).netloc
    base = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", base)
    base = re.sub(r"\s+", "_", base).strip("_")[:60]
    return f"{idx:02d}_{base or 'page'}"


def read_url_list(spec):
    """Read URLs from file or comma-separated string."""
    if os.path.exists(spec):
        with open(spec, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("urls", [])
        return list(data)
    return [u.strip() for u in spec.split(",") if u.strip()]


async def cmd_map(args):
    from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
    from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter, DomainFilter

    filters = []
    host = urllib.parse.urlparse(args.url).netloc
    filters.append(DomainFilter(allowed_domains=[host]))
    if args.include:
        pats = [p.strip() for p in args.include.split(",") if p.strip()]
        filters.append(URLPatternFilter(patterns=[f"*{p}*" for p in pats]))

    deep = BFSDeepCrawlStrategy(max_depth=args.max_depth, max_pages=args.max_pages,
                                filter_chain=FilterChain(filters), include_external=False)
    browser_cfg = build_browser_cfg(args)
    run_cfg = make_run_cfg(fit=False, deep=deep)
    print(f"[map] BFS crawling {args.url}  max_depth={args.max_depth} max_pages={args.max_pages}")

    urls = []
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        results = await crawler.arun(url=args.url, config=run_cfg)
        seq = results if isinstance(results, list) else [results]
        for r in seq:
            if getattr(r, "url", None):
                urls.append(r.url)

    urls = list(dict.fromkeys(urls))
    ensure_dirs()
    out_path = URLS_DIR / args.out if not os.path.isabs(args.out) else Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"seed": args.url, "count": len(urls), "urls": urls}, f, ensure_ascii=False, indent=2)
    print(f"[map] Found {len(urls)} URLs → {out_path}")
    print("VERIFY_MAP: PASS" if urls else "VERIFY_MAP: FAIL")


async def cmd_crawl(args):
    urls = read_url_list(args.urls)
    if not urls:
        sys.exit("ERROR: No URLs provided. Use --urls with urls.json or comma-separated URLs.")

    browser_cfg = build_browser_cfg(args)

    schema = None
    if args.schema:
        schema_path = SCHEMA_DIR / args.schema if not os.path.isabs(args.schema) else Path(args.schema)
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)

    extraction = JsonCssExtractionStrategy(schema) if schema else None
    run_cfg = make_run_cfg(fit=args.fit)
    if extraction:
        run_cfg.extraction_strategy = extraction

    structured = bool(schema)
    ensure_dirs()

    if structured:
        out_path = DATA_DIR / args.out if not os.path.isabs(args.out) else Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_f = open(out_path, "w", encoding="utf-8")
    else:
        out_path = CONTENT_DIR / args.out if not os.path.isabs(args.out) else Path(args.out)
        out_path.mkdir(parents=True, exist_ok=True)

    summary = {"mode": "json" if structured else "markdown", "total": len(urls), "ok": 0, "failed": 0}
    print(f"[crawl] {len(urls)} URLs → {'JSONL' if structured else 'Markdown'} ({out_path})")

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        results = await crawler.arun_many(urls=urls, config=run_cfg)
        for i, r in enumerate(results, 1):
            url = getattr(r, "url", urls[i - 1] if i <= len(urls) else "?")
            if not getattr(r, "success", False):
                print(f"  [{i}] ✗ {url}")
                summary["failed"] += 1
                continue

            if structured:
                try:
                    rows = json.loads(r.extracted_content) if r.extracted_content else []
                except Exception:
                    rows = []
                for row in (rows if isinstance(rows, list) else [rows]):
                    row["_url"] = url
                    out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"  [{i}] ✓ {url}  ({len(rows)} records)")
                summary["ok"] += 1
            else:
                md_obj = getattr(r, "markdown", None)
                if md_obj is not None and hasattr(md_obj, "fit_markdown"):
                    md = md_obj.fit_markdown or md_obj.raw_markdown or ""
                else:
                    md = str(md_obj or "")
                title = (r.metadata or {}).get("title", "") if getattr(r, "metadata", None) else ""
                if len(md.strip()) < 80:
                    print(f"  [{i}] ✗ {url} (content too short: {len(md)} chars)")
                    summary["failed"] += 1
                    continue

                file_path = out_path / (slugify(url, title, i) + ".md")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"---\nurl: {url}\ntitle: {title}\nmd_chars: {len(md)}\n---\n\n{md.strip()}\n")
                print(f"  [{i}] ✓ {title[:40] or url} → {file_path.name} ({len(md)} chars)")
                summary["ok"] += 1

    if structured:
        out_f.close()

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print("VERIFY_CRAWL: PASS" if summary["ok"] else "VERIFY_CRAWL: FAIL")


def cmd_preset(args):
    """Run map with a preset configuration for design websites."""
    if args.preset not in DESIGN_PRESETS:
        print(f"ERROR: Unknown preset '{args.preset}'")
        print(f"Available presets: {', '.join(DESIGN_PRESETS.keys())}")
        sys.exit(1)

    preset = DESIGN_PRESETS[args.preset]
    print(f"[preset] Using preset: {args.preset}")
    print(f"  URL: {preset['url']}")
    print(f"  Description: {preset['description']}")
    print(f"  Max depth: {preset['max_depth']}, Max pages: {preset['max_pages']}")

    # Override args with preset values
    args.url = preset['url']
    args.max_depth = preset['max_depth']
    args.max_pages = preset['max_pages']
    args.include = preset['include']

    # Set default output filename based on preset
    if not args.out or args.out == "urls.json":
        args.out = f"{args.preset.replace('-', '_')}.json"

    # Run map command
    asyncio.run(cmd_map(args))


def main():
    ensure_dirs()

    ap = argparse.ArgumentParser(description="Crawl4AI采集层: map(发现) + crawl(抓取)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_bridge(p):
        p.add_argument("--state", help="storage_state.json (default auth bridge)")
        p.add_argument("--user-data-dir", help="Persistent Chrome profile directory")
        p.add_argument("--cdp", help="Share external Chrome CDP ws:// endpoint")

    # Map command
    p_map = sub.add_parser("map", help="Deep crawl to discover links → urls.json")
    p_map.add_argument("--url", required=True, help="Entry/index page URL")
    p_map.add_argument("--out", default="urls.json")
    p_map.add_argument("--max-depth", type=int, default=2)
    p_map.add_argument("--max-pages", type=int, default=30)
    p_map.add_argument("--include", help="URL path whitelist (comma-separated, e.g., /news/,/blog/)")
    add_bridge(p_map)
    p_map.set_defaults(func=cmd_map)

    # Crawl command
    p_crawl = sub.add_parser("crawl", help="Concurrent crawl → Markdown or JSONL")
    p_crawl.add_argument("--urls", required=True, help="urls.json or comma-separated URLs")
    p_crawl.add_argument("--out", default="content", help="Output directory (md) or file (jsonl)")
    p_crawl.add_argument("--schema", help="JsonCssExtractionStrategy CSS schema (outputs JSONL)")
    p_crawl.add_argument("--fit", action="store_true", help="Prune content for cleaner output")
    add_bridge(p_crawl)
    p_crawl.set_defaults(func=cmd_crawl)

    # Preset command
    p_preset = sub.add_parser("preset", help="Use preset configuration for design websites")
    p_preset.add_argument("preset", choices=list(DESIGN_PRESETS.keys()),
                         help="Preset name: " + ", ".join(DESIGN_PRESETS.keys()))
    p_preset.add_argument("--out", help="Output filename (default: {preset_name}.json)")
    add_bridge(p_preset)
    p_preset.set_defaults(func=cmd_preset)

    args = ap.parse_args()

    if args.cmd == "preset":
        cmd_preset(args)
    else:
        asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
