"""Download Nicepage HTML templates by visiting template detail pages."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json, time, os

OUT_DIR = Path("D:/video-grap/Downloaded/templates/downloaded/nicepage/html_templates")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TOP_TEMPLATES = [
    ("Neon_Club", "https://nicepage.com/st/44240/neon-club-website-template"),
    ("DJ_Night_About", "https://nicepage.com/st/359886/about-dj-night-website-template"),
    ("Neon_Club_Entertainment", "https://nicepage.com/st/50032/neon-club-and-entertainment-website-template"),
    ("Neon_Night_Club", "https://nicepage.com/st/48740/neon-night-club-website-template"),
    ("DJ_Night_Biography", "https://nicepage.com/st/365193/dj-night-biography-website-template"),
    ("Prime_Home_Gamers", "https://nicepage.com/st/362235/the-prime-home-for-gamers-website-template"),
    ("Coctail_Party", "https://nicepage.com/st/338958/coctail-party-website-template"),
    ("Club_Life", "https://nicepage.com/st/48745/club-life-website-template"),
    ("Games_Every_Interest", "https://nicepage.com/st/362411/games-for-every-interest-website-template"),
    ("Concept_Festival", "https://nicepage.com/st/105466/concept-festival-website-template"),
]

def main():
    pl = sync_playwright()
    p = pl.__enter__()
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(accept_downloads=True)

    results = []

    for idx, (name, url) in enumerate(TOP_TEMPLATES, 1):
        t_dir = OUT_DIR / name
        t_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[{idx:02d}] {name}: {url}")

        page = context.new_page()

        downloads = []
        def on_download(dl):
            downloads.append(dl)
            fpath = t_dir / dl.suggested_filename
            dl.save_as(str(fpath))
            print(f"    DOWNLOADED: {fpath}")

        page.on("download", on_download)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Try to find and click Download button
        clicked = page.evaluate("""
            () => {
                // Try common Nicepage download button patterns
                const all = document.querySelectorAll('a, button, .btn, [class*="button"]');
                for (const el of all) {
                    const text = (el.textContent || '').toLowerCase().trim();
                    const href = (el.getAttribute('href') || '').toLowerCase();
                    const cls = (el.className || '').toLowerCase();
                    if (text.includes('download') || href.includes('download') ||
                        cls.includes('download') || text === 'download template') {
                        el.click();
                        return { found: true, text: text, tag: el.tagName };
                    }
                }
                return { found: false };
            }
        """)
        print(f"    Click result: {clicked}")
        page.wait_for_timeout(5000)

        # Screenshot
        page.screenshot(path=str(t_dir / "preview.png"), full_page=True)
        title = page.title()
        info = {
            "name": name, "url": url, "title": title,
            "downloaded": len(downloads) > 0,
            "click_result": clicked,
            "files": [d.suggested_filename for d in downloads]
        }
        (t_dir / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

        if downloads:
            print(f"    Files: {[d.suggested_filename for d in downloads]}")
        else:
            print(f"    No download triggered")
            # Try clicking a more specific button
            try:
                btn = page.locator("text=Download").first
                if btn:
                    btn.click()
                    page.wait_for_timeout(5000)
            except:
                pass

        results.append(info)
        page.close()
        time.sleep(1)

    # Report
    report = OUT_DIR / "_report.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    downloaded = sum(1 for r in results if r.get("downloaded"))
    print(f"\n{'='*60}")
    print(f"DONE. Downloaded: {downloaded}/{len(results)}")
    print(f"Output: {OUT_DIR}")
    for d in sorted(OUT_DIR.iterdir()):
        if d.is_dir():
            files = list(d.iterdir())
            has_html = any(f.suffix in ('.html', '.zip', '.htm') for f in files)
            print(f"  {d.name}: {len(files)} files {'[HAS HTML]' if has_html else ''}")

    browser.close()
    pl.__exit__(None, None, None)

if __name__ == "__main__":
    main()
