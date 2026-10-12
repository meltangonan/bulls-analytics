"""Render the bare zone FGM leaders court for the HTML pages.

    venv/bin/python scripts/prototypes/zone_fgm_leaders_court_assets.py --scope season|tenure

Draws one half court with every zone in its FG%-vs-NBA band and nothing else:
no tags, heads or legend. Beside the PNG it writes ``court.json``: each zone's
band colour and tag centre as fractions of the image (0,0 top left), so the
page template (``zone_fgm_leaders_pages.py``) can place its tags on the zones
without knowing the court's geometry. Figures come from ``zone_fgm_leaders.py``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.transforms import Bbox

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.graphics import house
from bulls.graphics.court import ARC, BASELINE_Y, COURT_HALF_WIDTH
from scripts import make_shot_chart as zc


SLUG = "2026-10-07-zone-fgm-leaders"
DATA = ROOT / "docs/visuals" / SLUG / "data"
OUT = ROOT / "output/zone-fgm-leaders"
COURT_DPI = 300   # about 1850 px wide, placed near 1030 px on the page

# Tag centres in NBA court units, hoop at the origin; the tag's head stands on
# its top edge. Corner tags reach past the sidelines; baseline tags sit low and
# the mid-range wing tags drop toward them.
TAGS = {
    "Restricted Area":       (0, -34),
    "In The Paint (Non-RA)": (0, 72),
    "Left Baseline":         (-122, -16),
    "Right Baseline":        (122, -16),
    "Left Corner 3":         (-244, 24),
    "Right Corner 3":        (244, 24),
    "Left Mid-Range":        (-141, 112),
    "Right Mid-Range":       (141, 112),
    "Center Mid-Range":      (0, 184),
    "Left Wing 3":           (-186, 232),
    "Right Wing 3":          (186, 232),
    "Top of Key 3":          (0, 294),
}


def band(rel_points: float) -> str:
    return zc._zone12_band_color(rel_points / 100, zc.ZONE12_DEFAULT_PALETTE)


def render_court(values: pd.DataFrame, folder: Path) -> Path:
    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.axis("off"); ax.patch.set_alpha(0.0)
    fills = {row.zone: band(row.FG_PCT_vs_NBA) for row in values.itertuples()}
    to_px = zc._draw_zone_court(ax, house.CANVAS_WIDTH / 2, zc.ZONE12_COURT_Y,
                                zc.ZONE12_SCALE, fills, 1.0)
    # The sidelines and baseline, a little past them so their line width is kept.
    pad = 3
    x0, y0 = to_px(COURT_HALF_WIDTH, BASELINE_Y)   # NBA left is the viewer's right
    x1, y1 = to_px(-COURT_HALF_WIDTH, zc.ZONE12_TOP)
    x0, x1 = min(x0, x1) - pad, max(x0, x1) + pad
    y0, y1 = y0 - pad, y1 + pad
    folder.mkdir(parents=True, exist_ok=True)
    png = folder / "court.png"
    fig.savefig(png, dpi=COURT_DPI, transparent=True,
                bbox_inches=Bbox.from_extents(*(v / house.DRAFT_DPI for v in (x0, y0, x1, y1))))
    plt.close(fig)

    zones = {}
    for row in values.itertuples():
        cx, cy = to_px(*TAGS[row.zone])
        zones[row.zone] = {"x": (cx - x0) / (x1 - x0), "y": (y1 - cy) / (y1 - y0),
                           "fill": fills[row.zone]}
    hx, hy = to_px(0, 0)
    layout = {"aspect": (y1 - y0) / (x1 - x0), "zones": zones,
              # The hoop and three-point arc, so the page can keep the wing tags off the line.
              "hoop": {"x": (hx - x0) / (x1 - x0), "y": (y1 - hy) / (y1 - y0)},
              "arc_r": ARC * zc.ZONE12_SCALE / (x1 - x0),
              "bands": list(zc.ZONE12_PALETTES[zc.ZONE12_DEFAULT_PALETTE]),
              "neutral_points": zc.ZONE12_FG_NEUTRAL_POINTS,
              "ink": {"up": zc.ZONE12_UP_ON_LIGHT, "down": zc.ZONE12_DOWN_ON_LIGHT,
                      "neutral": zc.ZONE12_NEUTRAL_GAP}}
    (folder / "court.json").write_text(json.dumps(layout, indent=1))
    return png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("season", "tenure"), default="season")
    args = parser.parse_args()
    prefix = "tenure-" if args.scope == "tenure" else ""
    values = pd.read_csv(DATA / f"{prefix}carousel-values.csv")
    assert list(values.zone) == list(sm.ZONE12_ORDER)
    print(render_court(values, OUT / args.scope))


if __name__ == "__main__":
    main()
