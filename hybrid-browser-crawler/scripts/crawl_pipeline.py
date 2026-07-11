#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
crawl_pipeline.py — 混合打法第 2 层「规模化采集」：用 Crawl4AI 吃 browser_unlock.py
产出的登录态(storage_state.json 或持久 user_data_dir)，做 deep crawl / arun_many /
结构化抽取，输出 Markdown 或 JSONL。

原则：Crawl4AI 负责"规模与结构化输出"，browser-use 只在它抓不到时补救。

身份桥接(二选一, 默认 storage_state)：
  --state storage_state.json         轻量可移植(BrowserConfig storage_state=...)
  --user-data-dir <dir>              持久 profile(use_managed_browser + user_data_dir, sessionStorage 站更稳)
  --cdp ws://...                     共享 browser_unlock cdp 启的同一个 Chrome

两个子命令：
  map   : 从入口页/索引页深抓同域链接 → urls.json (BFS, 带 max_depth/max_pages/include 过滤)
  crawl : 吃一组 URL → 并发抓取 → Markdown(.md) 或 结构化 JSON(.jsonl, 给 --schema 时)

用法：
  PY=cloak-test/.venv/Scripts/python.exe
  # 发现链接
  $PY scripts/crawl_pipeline.py map --url "https://target.com/dashboard" --state storage_state.json \
      --max-depth 2 --max-pages 30 --include "/article/,/news/" --out urls.json
  # 抓成 Markdown
  $PY scripts/crawl_pipeline.py crawl --urls urls.json --state storage_state.json --out youwang/web_sources --fit
  # 结构化抽取(CSS schema)
  $PY scripts/crawl_pipeline.py crawl --urls urls.json --state storage_state.json --schema schema.json --out data.jsonl
"""
import os, sys, io, re, json, asyncio, argparse, urllib.parse

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from crawl4ai import (AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode,
                          JsonCssExtractionStrategy)
except ImportError:
    sys.exit("ERROR: 未装 crawl4ai。 cloak-test/.venv/Scripts/python.exe -m pip install crawl4ai && crawl4ai-setup")

try:
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    _HAS_FILTER = True
except Exception:
    _HAS_FILTER = False

CHROME = os.environ.get("HYBRID_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def build_browser_cfg(args):
    """按 --cdp / --user-data-dir / --state 优先级构建身份桥接。"""
    if getattr(args, "cdp", None):
        print(f"[bridge] 共享外部 Chrome (CDP): {args.cdp}")
        return BrowserConfig(browser_mode="cdp", cdp_url=args.cdp, headless=True)
    if getattr(args, "user_data_dir", None):
        print(f"[bridge] 持久 profile: {args.user_data_dir}")
        return BrowserConfig(headless=True, use_managed_browser=True,
                             use_persistent_context=True,
                             user_data_dir=os.path.abspath(args.user_data_dir),
                             chrome_channel="chrome")
    if getattr(args, "state", None) and os.path.exists(args.state):
        print(f"[bridge] storage_state: {args.state}")
        return BrowserConfig(headless=True, storage_state=os.path.abspath(args.state))
    print("[bridge] 无登录态(公开页模式)")
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
    """spec 可以是 urls.json(支持 {"urls":[...]} 或 [...]), 或逗号分隔字符串。"""
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
    print(f"[map] BFS 深抓 {args.url}  max_depth={args.max_depth} max_pages={args.max_pages}")
    urls = []
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        results = await crawler.arun(url=args.url, config=run_cfg)
        # deep crawl 非 stream 模式返回 list
        seq = results if isinstance(results, list) else [results]
        for r in seq:
            if getattr(r, "url", None):
                urls.append(r.url)
    urls = list(dict.fromkeys(urls))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"seed": args.url, "count": len(urls), "urls": urls}, f, ensure_ascii=False, indent=2)
    print(f"[map] ✓ 发现 {len(urls)} 条 → {args.out}")
    print("VERIFY_MAP: PASS" if urls else "VERIFY_MAP: FAIL")


async def cmd_crawl(args):
    urls = read_url_list(args.urls)
    if not urls:
        sys.exit("ERROR: 没有 URL。--urls 传 urls.json 或逗号分隔串。")
    browser_cfg = build_browser_cfg(args)

    schema = None
    if args.schema:
        with open(args.schema, encoding="utf-8") as f:
            schema = json.load(f)
    extraction = JsonCssExtractionStrategy(schema) if schema else None
    run_cfg = make_run_cfg(fit=args.fit)
    if extraction:
        run_cfg.extraction_strategy = extraction

    structured = bool(schema)
    if structured:
        out_f = open(args.out, "w", encoding="utf-8")
    else:
        os.makedirs(args.out, exist_ok=True)

    summary = {"mode": "json" if structured else "markdown", "total": len(urls), "ok": 0, "failed": 0}
    print(f"[crawl] {len(urls)} 个 URL → {'JSONL' if structured else 'Markdown'} ({args.out})")
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
                print(f"  [{i}] ✓ {url}  ({len(rows)} 条记录)")
                summary["ok"] += 1
            else:
                md_obj = getattr(r, "markdown", None)
                if md_obj is not None and hasattr(md_obj, "fit_markdown"):
                    md = md_obj.fit_markdown or md_obj.raw_markdown or ""
                else:
                    md = str(md_obj or "")
                title = (r.metadata or {}).get("title", "") if getattr(r, "metadata", None) else ""
                if len(md.strip()) < 80:
                    print(f"  [{i}] ✗ {url} (正文过短 {len(md)}字)")
                    summary["failed"] += 1
                    continue
                path = os.path.join(args.out, slugify(url, title, i) + ".md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"---\nurl: {url}\ntitle: {title}\nmd_chars: {len(md)}\n---\n\n{md.strip()}\n")
                print(f"  [{i}] ✓ {title[:40] or url} → {path} ({len(md)}字)")
                summary["ok"] += 1
    if structured:
        out_f.close()
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print("VERIFY_CRAWL: PASS" if summary["ok"] else "VERIFY_CRAWL: FAIL")


def main():
    ap = argparse.ArgumentParser(description="Crawl4AI 采集层: map(发现) + crawl(抓取)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_bridge(p):
        p.add_argument("--state", help="storage_state.json(默认身份桥接)")
        p.add_argument("--user-data-dir", help="持久 Chrome profile 目录")
        p.add_argument("--cdp", help="共享外部 Chrome 的 CDP ws:// 端点")

    p_map = sub.add_parser("map", help="深抓发现同域链接 → urls.json")
    p_map.add_argument("--url", required=True, help="入口/索引页")
    p_map.add_argument("--out", default="urls.json")
    p_map.add_argument("--max-depth", type=int, default=2)
    p_map.add_argument("--max-pages", type=int, default=30)
    p_map.add_argument("--include", help="路径关键词白名单(逗号分隔, 如 /news/,/blog/)")
    add_bridge(p_map)
    p_map.set_defaults(func=cmd_map)

    p_crawl = sub.add_parser("crawl", help="并发抓取 → Markdown 或 JSONL")
    p_crawl.add_argument("--urls", required=True, help="urls.json 或逗号分隔 URL 串")
    p_crawl.add_argument("--out", default="youwang/web_sources", help="md 目录 或 jsonl 文件")
    p_crawl.add_argument("--schema", help="JsonCssExtractionStrategy 的 CSS schema(给了就出 JSONL)")
    p_crawl.add_argument("--fit", action="store_true", help="正文剪枝, 更干净")
    add_bridge(p_crawl)
    p_crawl.set_defaults(func=cmd_crawl)

    args = ap.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
