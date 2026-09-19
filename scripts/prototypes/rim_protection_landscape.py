"""Render the Bulls rim-protection landscape from saved, verified tables.

Follows Tipoff's rim-protection chart: rim attempts defended per 100
possessions across, rim points saved per 100 possessions up. Every qualified
league player-season since 2013-14 is a grey dot; qualified Chicago seasons
that saved more than one point per 100 are headshots centred on their true
point. Close seasons overlap; the higher-saving season draws on top, and each
name sits on the side given in LABEL_SIDES. Dashed lines mark the all-defender
league average on both axes.

Run `rim_protection_data.py` first; this script never fetches stats.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from bulls.graphics.house import (
    BLACK,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    RED,
    ensure_headshots,
    export_dpi,
    helvetica,
    rendered_width,
    square_headshot_label,
)

POST = ROOT / "docs/visuals/2026-09-18-rim-protection-landscape"
DATA = POST / "data"
OUT = ROOT / "output"

WIDTH, HEIGHT = 1080, 1080
PANEL = (205, 150, 1040, 1040)  # x0, y0, x1, y1
X_LIMITS = (4.0, 16.0)          # rim attempts defended per 100 possessions
Y_LIMITS = (-1.8, 4.8)          # rim points saved per 100 possessions
HALF = 32.0
LABEL_H = 28.0
GREY = "#8C857E"
GRID = "#DDD7CF"

SHORT = {
    "Pau Gasol": "GASOL",
    "Robin Lopez": "LOPEZ",
    "Joakim Noah": "NOAH",
    "Taj Gibson": "GIBSON",
    "Matas Buzelis": "BUZELIS",
    "Daniel Gafford": "GAFFORD",
    "Jalen Smith": "J. SMITH",
    "Wendell Carter Jr.": "CARTER JR.",
}


def px(value: float) -> float:
    x0, _, x1, _ = PANEL
    return x0 + (value - X_LIMITS[0]) / (X_LIMITS[1] - X_LIMITS[0]) * (x1 - x0)


def py(value: float) -> float:
    _, y0, _, y1 = PANEL
    return y0 + (value - Y_LIMITS[0]) / (Y_LIMITS[1] - Y_LIMITS[0]) * (y1 - y0)


def season_tag(season: str) -> str:
    return f"{season[:4]}-{season[5:]}"


# Which side of its face each name sits on; default below.
LABEL_SIDES = {
    ("Pau Gasol", "2015-16"): "above",
    ("Robin Lopez", "2018-19"): "left",
    ("Pau Gasol", "2014-15"): "below",
}


def axis_label(ax, text: str, direction: str, vertical: bool, center: float,
               name_at: float, arrow_at: float) -> None:
    rotation = 90 if vertical else 0
    xy = (name_at, center) if vertical else (center, name_at)
    ax.text(*xy, text, ha="center", va="center", rotation=rotation, fontsize=15,
            color=BLACK, fontproperties=helvetica("bold"))
    probe = ax.text(0, 0, direction, fontsize=9.5, fontproperties=helvetica("bold"), alpha=0)
    extent = rendered_width(ax, probe)
    probe.remove()
    gap, arrow = 8, 34
    start = center - (extent + gap + arrow) / 2
    if vertical:
        ax.text(arrow_at, start + extent / 2, direction, ha="center", va="center",
                rotation=90, fontsize=9.5, color=BLACK, fontproperties=helvetica("bold"))
        a, b = (arrow_at - 3, start + extent + gap), (arrow_at - 3, start + extent + gap + arrow)
    else:
        ax.text(start, arrow_at, direction, ha="left", va="center", fontsize=9.5,
                color=BLACK, fontproperties=helvetica("bold"))
        a, b = (start + extent + gap, arrow_at + 3), (start + extent + gap + arrow, arrow_at + 3)
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11,
                                 linewidth=1.35, color=RED, zorder=8))


def render(final: bool) -> Path:
    background = pd.read_csv(DATA / "league_background_per100.csv")
    qualified = pd.read_csv(DATA / "bulls_qualified_per100.csv")
    top = qualified.loc[qualified.featured]
    ensure_headshots(top.player_id.unique())

    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, HEIGHT / DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.set_aspect("equal")
    ax.axis("off")
    x0, y0, x1, y1 = PANEL

    for value in range(4, 17, 2):
        x = px(value)
        ax.plot([x, x], [y0, y1], color=GRID, lw=0.9, zorder=1)
        ax.plot([x, x], [y0, y0 - 8], color=BLACK, lw=1.4, zorder=5)
        ax.text(x, y0 - 18, str(value), ha="center", va="top", fontsize=12,
                color=BLACK, fontproperties=helvetica())
    for value in range(-1, 5):
        y = py(value)
        ax.plot([x0, x1], [y, y], color=GRID, lw=0.9, zorder=1)
        ax.plot([x0, x0 - 8], [y, y], color=BLACK, lw=1.4, zorder=5)
        label = "0" if value == 0 else f"{'−' if value < 0 else '+'}{abs(value)}"
        ax.text(x0 - 16, y, label, ha="right", va="center", fontsize=12,
                color=BLACK, fontproperties=helvetica("bold" if value == 0 else "regular"))

    zero = py(0)
    ax.plot([x0, x1], [zero, zero], color=BLACK, lw=1.3, linestyle=(0, (5, 4)), zorder=3)
    ax.text(x1 - 6, zero + 8, "LEAGUE AVERAGE", ha="right", va="bottom", fontsize=8.5,
            color=BLACK, fontproperties=helvetica("bold"), zorder=4)
    avg_x = px(json.loads((DATA / "chart_reference.json").read_text())["league_rim_fga_per_100_all_defenders"])
    ax.plot([avg_x, avg_x], [y0, y1], color=BLACK, lw=1.3, linestyle=(0, (5, 4)), zorder=3)
    ax.text(avg_x + 8, y1 - 8, "LEAGUE AVERAGE", ha="left", va="top", fontsize=8.5,
            color=BLACK, fontproperties=helvetica("bold"), zorder=4)
    ax.plot([x0, x1], [y0, y0], color=BLACK, lw=2.0, zorder=5)
    ax.plot([x0, x0], [y0, y1], color=BLACK, lw=2.0, zorder=5)

    grey = background.loc[~background.featured]
    ax.scatter([px(v) for v in grey.rim_fga_per_100], [py(v) for v in grey.rim_points_saved_per_100],
               s=44, facecolor=GREY, edgecolor="none", alpha=0.3, zorder=2)

    anchors = np.array([[px(r.rim_fga_per_100), py(r.rim_points_saved_per_100)] for r in top.itertuples()])
    # Lower-saving seasons first, so the stronger season's face sits on top.
    for i, row in enumerate(top.sort_values("rim_points_saved_per_100").itertuples()):
        fx, fy = px(row.rim_fga_per_100), py(row.rim_points_saved_per_100)
        z = 7 + i * 0.2
        square_headshot_label(ax, HEADSHOT_CACHE / f"{int(row.player_id)}.png", fx, fy,
                              half_size=HALF, face_fraction=0.74, zorder=z)
        side = LABEL_SIDES.get((row.player_name, row.season), "below")
        if side == "above":
            nx, ny, ha, va, sy = fx, fy + HALF + 15, "center", "bottom", -12
        elif side == "left":
            nx, ny, ha, va, sy = fx - HALF - 6, fy + 7, "right", "center", -12
        elif side == "right":
            nx, ny, ha, va, sy = fx + HALF + 6, fy + 7, "left", "center", -12
        else:
            nx, ny, ha, va, sy = fx, fy - HALF - 4, "center", "top", -12
        name_va = "center" if side in ("left", "right") else va
        ax.text(nx, ny, SHORT[row.player_name], ha=ha, va=name_va if side != "above" else "bottom",
                fontsize=9, color=BLACK, fontproperties=helvetica("bold"), zorder=z + 0.1)
        season_y = ny + sy if side != "above" else fy + HALF + 3
        ax.text(nx, season_y, season_tag(row.season), ha=ha,
                va="bottom" if side == "above" else ("top" if side == "below" else "center"),
                fontsize=8, color=BLACK, fontproperties=helvetica(), zorder=z + 0.1)

    axis_label(ax, "RIM ATTEMPTS DEFENDED PER 100 POSSESSIONS", "MORE SHOTS CHALLENGED", False,
               (x0 + x1) / 2, 88, 52)
    axis_label(ax, "RIM POINTS SAVED PER 100 POSSESSIONS", "MORE POINTS SAVED", True,
               (y0 + y1) / 2, 48, 84)

    out = OUT / "rim-protection-landscape.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true", help="publish DPI")
    print(render(parser.parse_args().final))
