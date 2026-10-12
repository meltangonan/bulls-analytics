"""Export each recap page as a 1080x1440 PNG, the Instagram 3:4 portrait size, ready to upload.

    venv/bin/python postgame-recaps/pipeline/export_slides.py 0022500248 [more ids]

Opens output/postgame-recap/mockup.html (build_mockup.py) in headless Chromium through Playwright,
waits for the web fonts, draws one game's pages and saves each page's SVG alone at its native size to
output/postgame-recap/<id>/slides/NN-<page>.png, keeping image data only (deliver.clean_png). The pages are
the same drawing as the mockup; nothing is recalculated here. Nothing leaves this Mac: deliver.py sends the slides
to the phone once Claude has reviewed them.

Each page is also measured (layout.json beside the slides, one "layout:" line per page), so the review has numbers
for what an eye misses at phone size: text that overlaps other text or runs past the 25 px margins, the tallest
empty band between the title and the footer (a hole), and the space left above the footer (cramped).
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from deliver import clean_png  # noqa: E402
from paths import OUTPUT  # noqa: E402
MOCKUP = OUTPUT / "mockup.html"
MARGIN, FOOTER = 25, 1370  # the page's side margins; the footer and its note sit below FOOTER
# Thresholds from the 16 saved test games (2026-10-10), so a normal page reads "ok": italic and serif capitals
# lean up to 4 px past the margin (OVERHANG); season so far keeps a band of up to 166 px between its two
# charts (HOLE); team stats ends 8 px above the footer (TIGHT). "FIX" is never acceptable on a published page;
# "LOOK" is unusual for the format and deserves a closer look, not a fix by default.
OVERHANG, HOLE, TIGHT = 6, 200, 4

# One page's layout in page pixels (the page is drawn at its native 1080x1440, so screen pixels are page pixels).
MEASURE = """svg => {
  const o = svg.getBoundingClientRect(), box = e => { const r = e.getBoundingClientRect();
    return {x0: r.left - o.left, y0: r.top - o.top, x1: r.right - o.left, y1: r.bottom - o.top}; };
  // A text's box spans its font's whole line height, so stacked lines would always "touch"; keep the letters'
  // own height instead: cap height above the baseline and a little below it (the baseline sits ~0.22 em above
  // the box's bottom in both families).
  const texts = [...svg.querySelectorAll('text')].filter(e => e.textContent.trim()).map(e => {
    const b = box(e), f = parseFloat(getComputedStyle(e).fontSize), base = b.y1 - 0.22 * f;
    return {t: e.textContent.trim().slice(0, 40), ...b, y0: base - 0.72 * f, y1: base + 0.1 * f};
  }).filter(b => b.x1 > b.x0);
  const shapes = [...svg.querySelectorAll('rect,image,path,line,circle,ellipse,polygon,polyline')].map(box)
    .filter(b => b.x1 - b.x0 < 1000 || b.y1 - b.y0 < 1000)   // not the page background
    .filter(b => b.y0 >= 13 && (b.x1 > b.x0 || b.y1 > b.y0)) // not the jersey trim, not empty
    .map(b => ({t: '', ...b}));
  return {texts, shapes};
}"""


def layout(m: dict) -> dict:
    """Overlapping text, text past the margins, the tallest empty band and the space above the footer."""
    texts, body = m["texts"], [b for b in m["texts"] + m["shapes"] if b["y0"] < FOOTER]
    overlaps = [f'"{a["t"]}" / "{b["t"]}"' for i, a in enumerate(texts) for b in texts[i + 1:]
                if min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]) > 1 and min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]) > 1]
    off = [f'"{b["t"]}"' for b in texts if b["x0"] < MARGIN - OVERHANG or b["x1"] > 1080 - MARGIN + OVERHANG or b["y1"] > 1440]
    foot_top = min((b["y0"] for b in texts if b["y0"] >= FOOTER), default=1440)
    low = max(body, key=lambda b: b["y1"], default={"y1": 0, "t": ""})
    bottom = low["y1"]
    hole, at, reach = 0, 0, min((b["y0"] for b in body), default=0)
    for b in sorted(body, key=lambda b: b["y0"]):
        if b["y0"] - reach > hole:
            hole, at = b["y0"] - reach, reach
        reach = max(reach, b["y1"])
    return {"overlaps": overlaps, "off_margin": off, "hole": round(hole), "hole_at": round(at),
            "above_footer": round(foot_top - bottom)}


def verdict(page: str, l: dict) -> str:
    """One line for the review: fix (overlap, off a margin), look (an unusual hole or a tight footer) or ok."""
    fix = [f"overlap {x}" for x in l["overlaps"]] + [f"off the margin {x}" for x in l["off_margin"]]
    look = ([f"empty band {l['hole']} px from y={l['hole_at']}"] if l["hole"] > HOLE else []) \
        + ([f"only {l['above_footer']} px above the footer"] if l["above_footer"] < TIGHT else [])
    word = "FIX" if fix else "LOOK" if look else "ok"
    return f"layout: {page}: {word}" + (": " + "; ".join(fix + look) if fix or look else
                                       f" (largest gap {l['hole']} px, {l['above_footer']} px above footer)")


def slug(caption: str) -> str:
    name = caption.split("·", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main(game_ids: list[str]) -> None:
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
        # The sans is Geist Regular and SemiBold, installed on this Mac, else the same faces from Google Fonts.
        geist = page.evaluate("[...document.fonts].filter(f => f.family === 'RecapSans' && f.status === 'loaded').length")
        print("sans:", "Geist from this Mac" if geist == 2 else "Geist from Google Fonts (not installed on this Mac)")
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
            measured = {}
            for k in range(n):
                caption = page.evaluate(f"""() => {{const d = [...document.querySelectorAll('#g > div')].filter(x => x.querySelector('svg'));
                    d.forEach((e, i) => {{ e.style.display = i === {k} ? 'block' : 'none'; }});
                    const s = d[{k}].querySelector('svg'); s.style.width = '1080px'; s.style.height = '1440px';
                    d[{k}].querySelector('.cap').style.display = 'none'; return d[{k}].querySelector('.cap').textContent; }}""")
                path = out / f"{int(caption.split('·')[0]):02d}-{slug(caption)}.png"  # the page's carousel number
                svg = page.locator("#g > div svg").nth(k)
                svg.screenshot(path=str(path))
                removed = clean_png(path)  # Instagram must never see anything but the picture
                print(path, f"(metadata removed: {', '.join(removed)})" if removed else "")
                measured[path.stem] = layout(svg.evaluate(MEASURE))
            (OUTPUT / game_id / "layout.json").write_text(json.dumps(measured, indent=1))
            for name, l in measured.items():
                print(verdict(name, l))
        browser.close()


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")])
