# -*- coding: utf-8 -*-
"""Download the 18 item cover thumbnails from aigei.com set page (no login).
Item thumbs are on s1.aigei.com/src/img/(jpg|gif|png)/ (token-signed, far-future expiry, public).
Excludes avatars/logos/ads. Downloads via Playwright context.request."""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.aigei.com/set/hongbaoyujinbifudait.html"
OUT = Path("D:/video-grap/Downloaded/aigei_vjshi/aigei_set_红包雨_covers")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
# item thumb: s*.aigei.com/src/img/<fmt>/<xx>/<hash>.<ext>  (exclude /ad/ /icon/ /logo/)
ITEM_RE = re.compile(r"https?://s\d*\.aigei\.com/src/img/(jpg|gif|png)/(?!ad/|icon/|logo/)[^?]+\.(?:jpg|jpeg|gif|png)", re.I)

def base_of(url):
    return url.split("?")[0]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    thumbs = []
    seen_base = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        # scroll progressively to trigger lazy-load on all items
        for _ in range(12):
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
        # collect from all common lazy-load attributes + srcset
        attrs = page.eval_on_selector_all("img", r"""els => {
            const out = [];
            for (const e of els) {
                const vals = [e.src, e.currentSrc, e.getAttribute('data-src'), e.getAttribute('data-original'),
                              e.getAttribute('data-lazy'), e.getAttribute('original'), e.getAttribute('_src'),
                              e.getAttribute('data-lazy-src'), e.getAttribute('srcset')];
                for (const v of vals) if (v) out.push(v);
            }
            return out;
        }""")
        for u in attrs:
            # srcset may contain multiple urls; split on comma
            for piece in u.split(","):
                piece = piece.strip().split(" ")[0]
                m = ITEM_RE.search(piece)
                if m:
                    b = base_of(piece)
                    if b in seen_base: continue
                    seen_base.add(b)
                    ext = b.split(".")[-1].lower()
                    thumbs.append((b, piece, ext))
        # also check <a> hrefs pointing to src/img (some thumbs are link backgrounds)
        for href in page.eval_on_selector_all("a", "els=>els.map(e=>e.href).filter(Boolean)"):
            m = ITEM_RE.search(href)
            if m:
                b = base_of(href)
                if b in seen_base: continue
                seen_base.add(b)
                ext = b.split(".")[-1].lower()
                thumbs.append((b, href, ext))
        browser.close()

    print(f"collected {len(thumbs)} item thumbnails", flush=True)

    # download via a fresh context (page ctx closed after browser.close above)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        ok = skip = fail = 0
        for i, (b, u, ext) in enumerate(thumbs):
            fname = f"aigei_set_{i+1:02d}.{ext}"
            target = OUT / fname
            if target.exists() and target.stat().st_size > 0:
                skip += 1; continue
            try:
                r = ctx.request.get(u, headers={"Referer": "https://www.aigei.com/"}, timeout=30000)
                if r.ok:
                    body = r.body()
                    if body and len(body) > 500:
                        target.write_bytes(body); ok += 1
                    else:
                        fail += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
        browser.close()
    print(f"DONE thumbs={len(thumbs)} ok={ok} skip={skip} fail={fail} -> {OUT}", flush=True)

if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8"); main()
