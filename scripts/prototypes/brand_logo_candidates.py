"""Rebrand exploration — three logo candidates for @chicagobullsdata.

Comparison sheet, one row per candidate, three scales per row:
  1. Full mark
  2. Avatar size (simulated on a dark tile, like the IG profile ring)
  3. Watermark lockup (mark + handle, footer-sized)

Candidates:
  A. Season Shape — the red/black area-chart silhouette from the debut post,
     reduced to a glyph.
  B. Data Bull — an abstract bull face built from a descending bar chart with
     chart-line horns (deliberately distinct from the official Bulls mark).
  C. Varsity wordmark — BULLS / DATA stacked in Academic M54.

Marks size their text/linewidths off the axes' rendered width so the same
draw function works at full, avatar, and watermark scale (matplotlib sizes
text in points, not data units — without this the small tiles overflow).

Output: output/brand/logo-candidates.png
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

RED = "#CE1141"
BLACK = "#141414"
INK = "#1A1A1A"
MUTED = "#777777"
RING = "#DDDDDD"
DARK_TILE = "#1A1A1A"

_DISPLAY = fm.FontProperties(fname=str(_REPO / "assets/fonts/AcademicM54.ttf"))
_BODY_MED = fm.FontProperties(fname=str(_REPO / "assets/fonts/Archivo-500.ttf"))
_BODY_REG = fm.FontProperties(fname=str(_REPO / "assets/fonts/Archivo-400.ttf"))

# Width (figure fraction) of the full-size mark column; scale factor 1.0.
_FULL_W = 0.30


def _scale(ax):
    """Mark scale factor: 1.0 in the full-size column, smaller elsewhere."""
    return ax.get_position().width / _FULL_W


# ---------------------------------------------------------------- marks
# Every mark draws into a unit box: x,y in [-1, 1], centered at origin.

def mark_season_shape(ax):
    """Red-above / black-below area silhouette, echo of the debut post."""
    s = _scale(ax)
    lift = 0.14  # visually center: the trough is deeper than the peak
    x = np.linspace(-0.74, 0.74, 200)
    y = (0.46 * np.exp(-((x + 0.44) / 0.19) ** 2)
         + 0.22 * np.exp(-((x - 0.00) / 0.12) ** 2)
         - 0.62 * np.exp(-((x - 0.46) / 0.27) ** 2))
    ax.fill_between(x, lift, lift + np.clip(y, 0, None), color=RED, zorder=2)
    ax.fill_between(x, lift, lift + np.clip(y, None, 0), color=BLACK, zorder=2)
    ax.plot(x, lift + y, color=INK, lw=2.4 * s, solid_capstyle="round", zorder=3)
    ax.plot([-0.80, 0.80], [lift, lift], color=MUTED, lw=1.5 * s, zorder=1)


def _bezier(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    pts = ((1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1)
           + t ** 2 * np.array(p2))
    return pts[:, 0], pts[:, 1]


def mark_data_bull(ax):
    """Abstract bull face: descending-bar-chart snout + curved chart-line horns."""
    s = _scale(ax)
    bar_w = 0.30
    top = 0.22
    depths = [0.52, 0.92, 0.52]
    xs = [-0.51, -0.15, 0.21]
    for x0, d in zip(xs, depths):
        ax.add_patch(Rectangle((x0, top - d), bar_w, d,
                               facecolor=BLACK, edgecolor="none", zorder=2))
    for ex in (-0.36, 0.36):
        ax.add_patch(Circle((ex, 0.02), 0.055, facecolor="#FFFFFF",
                            edgecolor="none", zorder=3))
    # horns: rise from the outer bar tops, bow outward, hook back in at the tip
    for sgn in (-1, 1):
        hx, hy = _bezier((sgn * 0.36, top), (sgn * 0.72, 0.48), (sgn * 0.50, 0.76))
        ax.plot(hx, hy, color=RED, lw=8.5 * s, solid_capstyle="round",
                solid_joinstyle="round", zorder=2)


def mark_wordmark(ax):
    """BULLS / DATA stacked in the title face."""
    s = _scale(ax)
    ax.text(0, 0.36, "BULLS", ha="center", va="center", fontsize=46 * s,
            color=BLACK, fontproperties=_DISPLAY)
    ax.text(0, -0.34, "DATA", ha="center", va="center", fontsize=46 * s,
            color=RED, fontproperties=_DISPLAY)


MARKS = [
    ("A - SEASON SHAPE", "the grid's signature chart, as a glyph", mark_season_shape),
    ("B - DATA BULL", "bar-chart face, chart-line horns", mark_data_bull),
    ("C - VARSITY WORDMARK", "Academic M54, initials avoided on purpose", mark_wordmark),
]


# ---------------------------------------------------------------- helpers

def unit_axes(fig, rect, dark=False):
    ax = fig.add_axes(rect)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor(DARK_TILE if dark else "#FFFFFF")
    return ax


def sub_unit_axes(parent, rect):
    """Inset unit-box axes (transparent, no frame) inside `parent`."""
    sub = parent.inset_axes(rect, transform=parent.transAxes)
    sub.set_xlim(-1, 1)
    sub.set_ylim(-1, 1)
    sub.set_aspect("equal")
    sub.axis("off")
    sub.patch.set_alpha(0)
    return sub


# ---------------------------------------------------------------- sheet

W, H = 1600, 1750
DPI = 150
fig = plt.figure(figsize=(W / DPI, H / DPI), facecolor="#FFFFFF")

fig.text(0.045, 0.970, "LOGO CANDIDATES", fontsize=34, color=INK,
         fontproperties=_DISPLAY, va="top")
fig.text(0.045, 0.928, "@chicagobullsdata rebrand — each mark at full size, avatar size, and watermark size",
         fontsize=12.5, color=MUTED, fontproperties=_BODY_MED, va="top")

col_x = [0.045, 0.430, 0.660]
col_w = [_FULL_W, 0.150, 0.315]
col_labels = ["FULL MARK", "AVATAR (IG dark UI)", "WATERMARK LOCKUP"]

for cx, cl in zip(col_x, col_labels):
    fig.text(cx, 0.906, cl, fontsize=10, color=MUTED,
             fontproperties=_BODY_MED, va="top")

row_y = [0.610, 0.330, 0.050]
row_h = 0.225

for (title, sub, mark), y0 in zip(MARKS, row_y):
    fig.text(0.045, y0 + row_h + 0.034, title, fontsize=16, color=RED,
             fontproperties=_DISPLAY, va="bottom")
    fig.text(0.047, y0 + row_h + 0.014, sub, fontsize=10.5, color=MUTED,
             fontproperties=_BODY_REG, va="bottom")

    # full mark in a hairline circle
    ax = unit_axes(fig, [col_x[0], y0, col_w[0], row_h])
    ax.add_patch(Circle((0, 0), 0.96, facecolor="none", edgecolor=RING, lw=1.2))
    mark(ax)

    # avatar: white circle on a dark tile (simulates the IG profile ring)
    tile = unit_axes(fig, [col_x[1], y0 + row_h * 0.28, col_w[1] * 0.62, row_h * 0.55], dark=True)
    tile.add_patch(Circle((0, 0), 0.90, facecolor="#FFFFFF", edgecolor="none", zorder=1))
    av = sub_unit_axes(tile, [0.14, 0.14, 0.72, 0.72])
    mark(av)

    # watermark lockup: tiny mark + handle, footer-sized
    wm = fig.add_axes([col_x[2], y0 + row_h * 0.36, col_w[2], row_h * 0.26])
    wm.set_xlim(0, 10)
    wm.set_ylim(-1, 1)
    wm.axis("off")
    wmark = sub_unit_axes(wm, [0.0, 0.10, 0.105, 0.80])
    mark(wmark)
    wm.text(1.55, 0, "@chicagobullsdata", ha="left", va="center", fontsize=13,
            color=MUTED, fontproperties=_BODY_MED)

out = _REPO / "output" / "brand"
out.mkdir(parents=True, exist_ok=True)
path = out / "logo-candidates.png"
fig.savefig(path, dpi=DPI, facecolor="#FFFFFF")
print(f"Saved {path}")
