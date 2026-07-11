# -*- coding: utf-8 -*-
"""Download cover thumbnails from vjshi.com search page (no login needed).
Scrolls to load results, collects main.jpg cover URLs, downloads via Playwright context.request."""
import os
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.vjshi.com/so/6304.html?categoryIdForSoftware=230&st=y"
OUT = Path("D:/video-grap/Downloaded/aigei_vjshi/vjshi_金币_covers")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    covers = []
    seen = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        last_new_round = 0
        for i in range(50):
            imgs = page.eval_on_selector_all("img", "els=>els.map(e=>e.src||e.dataset.src||e.currentSrc).filter(Boolean)")
            new = 0
            for u in imgs:
                if "pic.vjshi.com" in u and "/main.jpg" in u and u not in seen:
                    seen.add(u); covers.append(u); new += 1
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1800)
            if i % 5 == 0:
                print(f"scroll {i}: covers={len(covers)} new={new}", flush=True)
            if new == 0:
                last_new_round += 1
                if last_new_round >= 6:
                    print(f"no new covers for 6 rounds, stop scrolling. total={len(covers)}", flush=True)
                    break
            else:
                last_new_round = 0
        print(f"collected {len(covers)} covers, downloading via context.request ...", flush=True)
        ok = skip = fail = 0
        for idx, u in enumerate(covers):
            fname = f"vjshi_{idx+1:04d}.jpg"
            target = OUT / fname
            if target.exists() and target.stat().st_size > 0:
                skip += 1; continue
            try:
                r = ctx.request.get(u, headers={"Referer": "https://www.vjshi.com/"}, timeout=30000)
                if r.ok:
                    body = r.body()
                    if body and len(body) > 1000:
                        target.write_bytes(body); ok += 1
                    else:
                        fail += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
            if (idx+1) % 50 == 0:
                print(f"  {idx+1}/{len(covers)} ok={ok} fail={fail}", flush=True)
        browser.close()
    print(f"DONE covers={len(covers)} ok={ok} skip={skip} fail={fail} -> {OUT}", flush=True)

if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8"); main()

