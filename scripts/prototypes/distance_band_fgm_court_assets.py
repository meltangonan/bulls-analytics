"""Render sixteen tightly cropped distance-band courts for Canva composition."""
from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from bulls.graphics.court import (
    BASELINE_Y, CHART_COURT_INK, HALFCOURT_Y,
    draw_chart_court, draw_halfcourt_boundary,
)
from bulls.graphics import house
from scripts.make_shot_chart import _ladder_ring


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/distance-band-fgm"
HOOP_X, HOOP_Y, SCALE = 540.0, 480.0, 1.8
CREAM, RED = "#FAF8F5", "#CE1141"
GRAY_A, GRAY_B = "#DFDAD6", "#CFCAC7"
COURT_INK = CHART_COURT_INK


def render(start: int | None, *, final: bool = False) -> Path:
    """Use one fixed half-court frame; None highlights 30 ft to midcourt."""
    left, right = HOOP_X - 250 * SCALE, HOOP_X + 250 * SCALE
    baseline = HOOP_Y + BASELINE_Y * SCALE
    halfcourt = HOOP_Y + HALFCOURT_Y * SCALE
    width, height = right - left, halfcourt - baseline
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100, facecolor=CREAM)
    ax = fig.add_axes((0, 0, 1, 1), facecolor=CREAM)
    ax.set_xlim(left, right)
    ax.set_ylim(baseline, halfcourt)
    ax.set_aspect("equal")
    ax.axis("off")

    clip = Rectangle((left, baseline), right - left, halfcourt - baseline,
                     transform=ax.transData)
    # The outer region is the 30-ft-to-midcourt zone on the last page.
    ax.add_patch(Rectangle((left, baseline), right - left, halfcourt - baseline,
                           facecolor=RED if start is None else GRAY_A,
                           edgecolor="none", zorder=1))
    for index, band_start in enumerate(reversed(range(0, 30, 2))):
        band = SimpleNamespace(lo=band_start, hi=band_start + 2)
        color = (RED if band_start == start else
                 GRAY_A if band_start % 4 == 0 else GRAY_B)
        _ladder_ring(ax, (HOOP_X, HOOP_Y), band, SCALE, color, clip,
                     shadow=index > 0)

    # Same selected lane marks as the reviewed sample, with no text or portraits.
    court_center_y = HOOP_Y + ((280.0 - BASELINE_Y) / 2.0 + BASELINE_Y) * SCALE
    draw_chart_court(ax, HOOP_X, court_center_y, SCALE, lw=1.15, zorder=7)
    for side in (left, right):
        ax.plot((side, side), (HOOP_Y + 110 * SCALE, halfcourt),
                color=COURT_INK, lw=1.15, zorder=7)
    draw_halfcourt_boundary(ax, HOOP_X, HOOP_Y, SCALE, lw=1.15, zorder=7)

    output_dir = OUT / ("court-only-final" if final else "court-only")
    output_dir.mkdir(parents=True, exist_ok=True)
    name = (f"distance-band-{start:02d}-{start + 2:02d}-court.png"
            if start is not None else "distance-band-30-halfcourt-court.png")
    path = output_dir / name
    fig.savefig(path, dpi=house.FINAL_DPI if final else 100, facecolor=CREAM)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true", help="export at 300 DPI")
    args = parser.parse_args()
    for start in (*range(0, 30, 2), None):
        print(render(start, final=args.final))


if __name__ == "__main__":
    main()
