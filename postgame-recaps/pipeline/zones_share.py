"""Mockup-stage zones chart: pills show makes/attempts and share of FGA, larger, no "vs NBA" lines.

Patches make_shot_chart's pill drawing in place; a production version needs a real pill option there.
Run from the repo root with the primary venv (league shots come from the shared cache):
    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/zones_share.py \
        postgame-recaps/stress-tests/0022500248 output/postgame-recap/zones-share.png 13 11 33
Arguments: game data folder, output PNG, figure size, share size, line gap.
"""
import sys
from pathlib import Path
import pandas as pd
from matplotlib.patches import FancyBboxPatch
sys.path.insert(0, "scripts")
import make_shot_chart as msc
from bulls.data import shots as shot_data
from bulls.graphics.house import geist

GAME, OUT = Path(sys.argv[1]), Path(sys.argv[2])
FIG, SHARE, GAP = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])

def block(ax, to_px, z, fill, theme, pill="full", style=msc.ZONE12_DEFAULT_STYLE):
    px, py = to_px(*msc.ZONE12_ANCHORS[z.zone])
    look = msc.ZONE12_STYLES[style]
    if not z.fga:
        lines = [("0 FGA", FIG)]
    else:
        lines = [(f"{z.fgm}/{z.fga} ({z.fg * 100:.0f}%)", FIG), (f"{z.fga_share_pct:.0f}% of FGA", SHARE)]
    ink = msc.ZONE12_PILL_INK if (z.fga and z.rated) else msc.ZONE12_THIN_INK
    alpha = 1.0 if (z.fga and z.rated) else msc.ZONE12_THIN_PILL_ALPHA
    half_w = max(msc._zone12_measure(ax, s, size) for s, size in lines) / 2 + msc.ZONE12_PILL_PAD_X + 2
    span = GAP * (len(lines) - 1)
    half_h = span / 2 + FIG * 1.35 + msc.ZONE12_PILL_PAD_Y
    ax.add_patch(FancyBboxPatch((px - half_w, py - half_h), 2 * half_w, 2 * half_h,
                 boxstyle=f"round,pad=0,rounding_size={look['pill_round']}",
                 facecolor=look["pill_face"], edgecolor=look["pill_edge"],
                 linewidth=look["pill_lw"], alpha=alpha, zorder=10))
    top = py + span / 2
    for i, (s, size) in enumerate(lines):
        ax.text(px, top, s, fontsize=size, zorder=11, color=ink if i == 0 else "#5F5B57",
                alpha=alpha, ha="center", va="center", fontproperties=geist("semibold"))
        top -= GAP

msc._zone12_block = block
g = pd.read_csv(GAME / "shots_chi.csv"); lg = shot_data.league_shots("2025-26")
ctx = {"player": g, "league": lg, "name": "Chicago Bulls", "subtitle": "", "season": "2025-26",
       "min_fga": 8, "palette": None, "pill": "full", "merge_mid": True, "summary_metrics": True}
OUT.parent.mkdir(parents=True, exist_ok=True)
msc.render_zones(ctx, OUT, final=False)
print("wrote")
