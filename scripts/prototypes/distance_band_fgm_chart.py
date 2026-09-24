"""Sample one-band slides for Bulls player-season shot-distance leaders."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd
from PIL import Image

from bulls.graphics import house
from bulls.graphics.court import BASELINE_Y, CHART_COURT_INK, draw_chart_court
from scripts.make_shot_chart import _ladder_ring


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs/visuals/2026-09-23-distance-band-fgm/data"
PORTRAITS = DATA / "portraits"
OUT = ROOT / "output/distance-band-fgm"
EXAMPLES = (0, 22, 28)
WIDTH, HEIGHT = 1080, 1350
HOOP_X, HOOP_Y, SCALE = 540.0, 565.0, 2.0
CREAM, INK, RED = "#FAF8F5", "#242424", "#CE1141"
GRAY_A, GRAY_B = "#DFDAD6", "#CFCAC7"
COURT_INK = CHART_COURT_INK


def label(ax, x, y, value, size, *, bold=False, color=INK, ha="left", z=12):
    ax.text(x, y, value, va="center", ha=ha, fontsize=size,
            color=color, fontproperties=house.helvetica("bold" if bold else "regular"),
            zorder=z)


def headshot(ax, player_id: int):
    """Place a large full-color NBA cutout without a colored frame."""
    image = Image.open(PORTRAITS / f"{player_id}.png").convert("RGBA")
    width, height = image.size
    side = int(height * 0.83)
    face = image.crop(((width - side) // 2, 0, (width + side) // 2, side))
    canvas = Image.new("RGBA", face.size, CREAM)
    canvas.alpha_composite(face)
    face = canvas.convert("RGB").resize((700, 700), Image.Resampling.LANCZOS)
    ax.imshow(np.asarray(face), extent=(56, 356, 70, 370),
              interpolation="bilinear", zorder=12)


def court(ax, active_start: int):
    """Show every two-foot ring and the shared zone-chart court landmarks."""
    left, right = HOOP_X - 250 * SCALE, HOOP_X + 250 * SCALE
    baseline = HOOP_Y + BASELINE_Y * SCALE
    top = HOOP_Y + 300 * SCALE
    clip = Rectangle((left, baseline), right - left, top - baseline,
                     transform=ax.transData)
    for index, start in enumerate(reversed(range(0, 30, 2))):
        band = SimpleNamespace(lo=start, hi=start + 2)
        color = RED if start == active_start else (GRAY_A if start % 4 == 0 else GRAY_B)
        _ladder_ring(ax, (HOOP_X, HOOP_Y), band, SCALE, color, clip,
                     shadow=index > 0)

    # Use the exact shared court geometry drawn by the zone shot charts.
    court_center_y = HOOP_Y + ((280.0 - BASELINE_Y) / 2.0 + BASELINE_Y) * SCALE
    draw_chart_court(ax, HOOP_X, court_center_y, SCALE, lw=1.15, zorder=7)
    for side in (left, right):
        ax.plot((side, side), (baseline + 110 * SCALE, top),
                color=COURT_INK, lw=1.15, zorder=7)


def distance_pill(ax, start: int):
    # The zone-chart tag grammar: opaque page color, near-square corners,
    # and a thin dark rule. Keeping it above the court leaves the small rim
    # band visible instead of covering its entire highlight.
    width, height = 190, 53
    x, y = (WIDTH - width) / 2, 1226
    ax.add_patch(FancyBboxPatch(
        (x, y), width, height, boxstyle="round,pad=0,rounding_size=3",
        facecolor=CREAM, edgecolor=INK, lw=1.1, zorder=15,
    ))
    label(ax, WIDTH / 2, y + height / 2, f"{start}–{start + 2} ft",
          22, bold=True, ha="center", z=16)


def details(ax, row):
    headshot(ax, int(row.PLAYER_ID))
    label(ax, 365, 350, row.PLAYER_NAME, 36, bold=True)
    label(ax, 366, 296, row.season, 23, color="#5F5B57")
    ax.plot((365, 1010), (254, 254), color="#D7D1CC", lw=1.0, zorder=12)
    for x, title, value in (
        (365, "FGM", f"{int(row.FGM)}"),
        (690, "PPS", f"{row.PPS:.3f}"),
    ):
        label(ax, x, 222, title, 18, bold=True, color="#5F5B57")
        label(ax, x, 158, value, 60, bold=True, color=RED)


def render(row):
    start = int(row.band_start_ft)
    fig = plt.figure(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100, facecolor=CREAM)
    ax = fig.add_axes((0, 0, 1, 1), facecolor=CREAM)
    ax.set_xlim(0, WIDTH); ax.set_ylim(0, HEIGHT); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), WIDTH, HEIGHT, facecolor=CREAM, zorder=-10))
    court(ax, start)
    distance_pill(ax, start)
    details(ax, row)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"distance-band-{start:02d}-{start + 2:02d}.png"
    fig.savefig(path, dpi=100, facecolor=CREAM)
    plt.close(fig)
    print(path)


def main():
    leaders = pd.read_csv(DATA / "distance-band-leaders.csv")
    if len(leaders) != 15 or leaders.band_start_ft.nunique() != 15:
        raise ValueError("Expected one winner for each of fifteen bounded bands")
    for start in EXAMPLES:
        row = leaders.loc[leaders.band_start_ft.eq(start)]
        if len(row) != 1:
            raise ValueError(f"Expected one winner for {start}–{start + 2} ft")
        player_id = int(row.iloc[0].PLAYER_ID)
        if not (PORTRAITS / f"{player_id}.png").exists():
            raise FileNotFoundError(f"Missing portrait for {player_id}")
        render(row.iloc[0])


if __name__ == "__main__":
    main()
