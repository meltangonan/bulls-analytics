"""Export each recap page as a 1080x1440 PNG, the Instagram 3:4 portrait size, ready to upload.

    venv/bin/python postgame-recaps/pipeline/export_slides.py 0022500248 [more ids] [--icloud]

Opens output/postgame-recap/mockup.html (build_mockup.py) in headless Chromium through Playwright,
waits for the web fonts, draws one game's pages and saves each page's SVG alone at its native size to
output/postgame-recap/<id>/slides/NN-<page>.png, keeping image data only (deliver.clean_png). The pages are
the same drawing as the mockup; nothing is recalculated here. --icloud also copies them to iCloud Drive/Bulls recaps/<date> <matchup>/,
so they reach the phone's Files app for saving to Photos and posting from the Instagram app.
"""
import re
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from deliver import clean_png  # noqa: E402
from paths import OUTPUT  # noqa: E402
MOCKUP = OUTPUT / "mockup.html"
ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bulls recaps"


def slug(caption: str) -> str:
    name = caption.split("·", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main(game_ids: list[str], icloud: bool = False) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1440}, device_scale_factor=1)
        page.goto(MOCKUP.as_uri())
        # The page draws its first game only after its web fonts load, so a drawn page means fonts are in.
        page.wait_for_function("document.querySelectorAll('#g svg').length > 0", timeout=60000)
        page.evaluate("document.fonts.ready")
        ids = page.evaluate("A.games.map(g => g.game_id)")
        # The serif is Georgia Pro Condensed when that licensed font is installed on this Mac, else Source
        # Serif 4 from Google Fonts. Font files never enter the repo.
        georgia = page.evaluate("[...document.fonts].some(f => f.family === 'RecapSerif' && f.status === 'loaded')")
        print("serif:", "Georgia Pro Condensed Bold" if georgia else "Source Serif 4 (Georgia Pro Condensed is not installed)")
        for game_id in game_ids:
            if game_id not in ids:
                raise SystemExit(f"{game_id} is not in the mockup; rebuild it with build_mockup.py")
            n = page.evaluate(f"""() => {{render({ids.index(game_id)});
                // Show one page at a time at its native 1080x1440, nothing around it.
                document.querySelector('header').style.display = 'none';
                const g = document.getElementById('g');
                g.style.cssText = 'display:block;padding:0;margin:0;gap:0';
                document.body.style.margin = '0';
                return document.querySelectorAll('#g > div svg').length; }}""")
            out = OUTPUT / game_id / "slides"
            out.mkdir(parents=True, exist_ok=True)
            for old in out.glob("*.png"):
                old.unlink()
            for k in range(n):
                caption = page.evaluate(f"""() => {{const d = [...document.querySelectorAll('#g > div')].filter(x => x.querySelector('svg'));
                    d.forEach((e, i) => {{ e.style.display = i === {k} ? 'block' : 'none'; }});
                    const s = d[{k}].querySelector('svg'); s.style.width = '1080px'; s.style.height = '1440px';
                    d[{k}].querySelector('.cap').style.display = 'none'; return d[{k}].querySelector('.cap').textContent; }}""")
                path = out / f"{k + 1:02d}-{slug(caption)}.png"
                page.locator("#g > div svg").nth(k).screenshot(path=str(path))
                removed = clean_png(path)  # Instagram must never see anything but the picture
                print(path, f"(metadata removed: {', '.join(removed)})" if removed else "")
            if icloud:
                g = page.evaluate(f"A.games[{ids.index(game_id)}]")
                folder = ICLOUD / f"{g['date_short']} {g['chi']['tri']} {'vs' if g['home'] else 'at'} {g['opp']['tri']}"
                folder.mkdir(parents=True, exist_ok=True)
                for f in sorted(out.glob("*.png")):
                    shutil.copy(f, folder / f.name)
                print("copied to", folder)
        browser.close()


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")], icloud="--icloud" in sys.argv)
