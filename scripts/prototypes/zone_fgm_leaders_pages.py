"""Build and export the zone FGM leaders pages as 1080x1440 HTML slides.

    venv/bin/python scripts/prototypes/zone_fgm_leaders_pages.py [--export]

A cover (the single-season court with heads only, fading under the
question), then two pages, single seasons then Bulls careers, each one
all-in-one court. Positions and wording follow the user's Canva draft. Python
draws the bare court (``zone_fgm_leaders_court_assets.py``) and supplies every
figure from the saved values; ``zone_fgm_leaders_page.html`` only lays them out.
Writes output/zone-fgm-leaders/pages.html (both pages, phone-width preview);
``--export`` saves each page through headless Chromium (Playwright) to
output/zone-fgm-leaders/pages/, reports which fonts rendered, and prints any tag
or head that collides with another, leaves the page or reaches the legend.
``--asset`` instead saves only each chart (court, tags, heads, legend) on a
transparent background at 2x, cropped to its content, for placing in Canva:
output/zone-fgm-leaders/assets/.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
import sys

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prototypes import zone_fgm_leaders_court_assets as courts

DATA, OUT = courts.DATA, courts.OUT
HERE = Path(__file__).resolve().parent
PORTRAITS = DATA / "portraits"

# NBA cutouts are 1040 x 760. Rows above 456 hold the head and neck on every
# leader's portrait; the collar starts below, and current portraits show other
# teams' jerseys. Columns keep the widest hair.
HEAD_BOX = (220, 0, 820, 456)

# Wording and order as on the user's Canva draft (DAHXXIx9Ve0, October 12).
COVER = {
    "title": "Which Chicago Bull made the most shots from each zone?",
    "subtitle": "*Since 1997-98",
}
PAGES = {
    "season": {
        "title": "Chicago Bulls with the most shots made from each zone",
        "subtitle": "Chicago Bulls with the most field goals made in each zone, in one season (since 1997-98)",
        "foot": "1997-98 to 2025-26 regular season | Backcourt shots excluded",
    },
    "tenure": {
        "title": "Chicago Bulls with the most shots made from each zone",
        "subtitle": "Chicago Bulls with the most field goals made in each zone, over their entire Bulls career (since 1997-98)",
        "foot": "1997-98 to 2025-26 regular season, Bulls games only | Backcourt shots excluded",
    },
}


def data_uri(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def head(player_id: int) -> str:
    image = Image.open(PORTRAITS / f"{player_id}.png").convert("RGBA").crop(HEAD_BOX)
    return data_uri(image.resize((300, 228), Image.LANCZOS))


def signed(points: float) -> str:
    """One decimal with a true minus; no sign when it rounds to zero."""
    shown = round(points, 1)
    return f"{'+' if shown > 0 else '−' if shown < 0 else ''}{abs(shown):.1f}"


def page_data(scope: str) -> dict:
    tenure = scope == "tenure"
    prefix = "tenure-" if tenure else ""
    values = pd.read_csv(DATA / f"{prefix}carousel-values.csv")
    courts.render_court(values, OUT / scope)
    layout = json.loads((OUT / scope / "court.json").read_text())
    with Image.open(OUT / scope / "court.png") as court:
        court_uri = data_uri(court.convert("RGBA"))
    tags = []
    for row in values.itertuples():
        gap = row.FG_PCT_vs_NBA
        tags.append({
            "zone": row.zone, "id": int(row.player_id), "name": row.player_name,
            "season": "" if tenure else row.season,
            "made": f"{row.FGM:,}/{row.FGA:,}", "pct": f"{row.FG_PCT:.1f}%",
            "gap": f"{signed(gap)} vs NBA",
            "dir": "neutral" if abs(gap) < layout["neutral_points"] else "up" if gap > 0 else "down",
            **{k: layout["zones"][row.zone][k] for k in ("x", "y")},
        })
    ids = {t["id"] for t in tags}
    return {**PAGES[scope], "scope": scope, "court": court_uri, "aspect": layout["aspect"],
            "bands": layout["bands"], "ink": layout["ink"], "tags": tags,
            "hoop": layout["hoop"], "arc_r": layout["arc_r"],
            "heads": {i: head(i) for i in sorted(ids)}}


def build() -> Path:
    assets = {"cover": COVER, "pages": [page_data("season"), page_data("tenure")]}
    out = OUT / "pages.html"
    template = (HERE / "zone_fgm_leaders_page.html").read_text()
    out.write_text(template.replace("__ASSETS__", json.dumps(assets, ensure_ascii=False)))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return out


def export(html: Path, asset: bool = False) -> None:
    from playwright.sync_api import sync_playwright
    folder = OUT / ("assets" if asset else "pages")
    folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1440},
                                device_scale_factor=2 if asset else 1)
        page.goto(html.as_uri() + ("?export&asset" if asset else "?export"))
        page.wait_for_function("window.READY === true", timeout=60000)
        fonts = page.evaluate("""[...document.fonts].filter(f => f.status === 'loaded')
            .map(f => f.family + ' ' + f.weight + ' ' + f.style)""")
        print("fonts loaded:", ", ".join(sorted(set(fonts))) or "none")
        print("serif:", page.evaluate("window.SERIF_FACE"), "| sans:", page.evaluate("window.SANS_FACE"))
        for k, name in enumerate(("cover", "season", "tenure"), 1):
            path = folder / f"{k:02d}-{name}.png"
            if asset and name == "cover":
                page.locator(".page").first.screenshot(path=str(path), omit_background=True)
            elif asset:
                clip = page.evaluate(f"window.CLIPS[{k - 2}]")
                page.screenshot(path=str(path), clip=clip, full_page=True, omit_background=True)
            else:
                page.locator(".page").nth(k - 1).screenshot(path=str(path))
            print(path, Image.open(path).size)
        for line in page.evaluate("window.CROWDING"):
            print("  crowding:", line)
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true", help="save each page as a 1080x1440 PNG")
    parser.add_argument("--asset", action="store_true", help="save each chart alone, transparent, at 2x")
    args = parser.parse_args()
    html = build()
    if args.export:
        export(html)
    if args.asset:
        export(html, asset=True)


if __name__ == "__main__":
    main()
