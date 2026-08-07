#!/usr/bin/env python3
"""Build any shot chart in the family, for any player, from one entry point.

    venv/bin/python scripts/make_shot_chart.py --player "Matas Buzelis" --chart rings

Four charts, three questions:

    hotspot   WHERE he shoots, vs the league          (frequency only)
    hex       where AND how well, at full resolution  (size = volume, color = efficiency)
    rings     how often AND how well, by zone         (both, vs the league)
    cells     how well, spot by spot                  (18 polar cells, vs the league)

``rings`` and ``cells`` are the same question at two resolutions, and the choice
between them is a sample-size trade. Four zones give every band a large enough
sample to also carry volume; 18 cells locate a strength or a hole precisely but
leave several cells too thin to rate, which is why ``cells`` drops volume and
greys what it cannot stand behind.

A density-blob variant coloured by efficiency was tried and removed: thresholding on
over-indexed volume drew only 27% of a player's shots and hid 100% of his rim and
corner attempts -- structurally hiding the spots he is best at.

All four share the court geometry, the cached NBA data, and the league baseline
in ``bulls.graphics.court`` / ``bulls.data.shots`` / ``bulls.analysis.shot_maps``.
Add a chart by writing one render function here; the data layer is already done.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import FancyBboxPatch, Rectangle, RegularPolygon, Wedge

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.config import CURRENT_SEASON
from bulls.data import shots as shot_data
from bulls.graphics import house
from bulls.graphics.court import ARC, draw_half_court
from bulls.graphics.house import helvetica

# --- Palettes ---------------------------------------------------------------
HOT_BANDS = ["#F6CDD7", "#E67C96", "#CE1141", "#7E0C2B"]
HOT_LINE = "#5E0820"
COURT_WARM = "#C9A8B5"

HEX_CMAP = LinearSegmentedColormap.from_list(
    "hexdiff", ["#2C6FB5", "#8FB4D6", "#EFEAE4", "#E8896F", "#C42B1C"])
REL_CMAP = LinearSegmentedColormap.from_list("rel", [
    "#6E1113", "#B3312A", "#DE6B3C", "#F0BE45", "#9FC24C", "#4A9C3A", "#1F6B2F"])

DARK_BG, DARK_TEXT, DARK_DIM, DARK_LINE = "#14110F", "#F4EFE9", "#A79E95", "#6C645C"


def resolve_player(name: str) -> tuple[int, str]:
    from nba_api.stats.static import players

    matches = [p for p in players.get_players()
               if name.lower() in p["full_name"].lower()]
    if not matches:
        raise SystemExit(f"No NBA player matching '{name}'")
    if len(matches) > 1:
        exact = [p for p in matches if p["full_name"].lower() == name.lower()]
        if not exact:
            names = ", ".join(p["full_name"] for p in matches[:8])
            raise SystemExit(f"'{name}' is ambiguous: {names}")
        matches = exact
    return matches[0]["id"], matches[0]["full_name"]


# ---------------------------------------------------------------------------
# hotspot — the F5 density method
# ---------------------------------------------------------------------------
def render_hotspot(ctx, out: Path, final: bool):
    theme = house.get_theme("jersey")
    fig, ax = house.new_canvas(theme)
    s = 1.72
    x0, y0 = draw_half_court(ax, house.CANVAS_WIDTH / 2, 700, s, COURT_WARM)

    player = sm.within_range(ctx["player"])
    league = sm.within_range(ctx["league"])
    diff = sm.signed_diff(sm.density(player), sm.density(league))
    _contour_field(ax, x0, y0, s, np.clip(diff, 0, None), HOT_BANDS, HOT_LINE, 0.92)

    _header(ax, theme, ctx, "Red = he shoots here more often than a typical NBA player")
    ax.text(house.CANVAS_WIDTH / 2, 250,
            f"{len(ctx['player'])} field-goal attempts", ha="center", va="bottom",
            fontsize=16, color=theme.ink, fontproperties=helvetica("bold"))
    ax.text(house.CANVAS_WIDTH / 2, 214,
            "Shot location only — this chart says nothing about accuracy",
            ha="center", va="bottom", fontsize=12, color=theme.muted,
            fontproperties=helvetica("bold"))
    _footer(ax, theme, ctx)
    _save(fig, out, final, theme.canvas)


def _contour_field(ax, x0, y0, s, field, fill_colors, line_color, alpha):
    """Filled contour bands plus outlines — the F5 geom_raster + stat_contour pair."""
    live = field[field > 0]
    if live.size == 0:
        return
    thr, fmax = float(live.mean()), float(field.max())
    if fmax <= thr:
        return
    xe, ye = sm.edges()
    cx, cy = np.meshgrid((xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2)
    px, py = x0 + (cx + 250.0) * s, y0 + (cy + 47.5) * s
    z = np.sqrt(field.T)
    levels = np.sqrt(np.linspace(thr, fmax, len(fill_colors) + 1))
    levels[-1] += 1e-9
    ax.contourf(px, py, z, levels=levels, colors=fill_colors, alpha=alpha, zorder=2)
    ax.contour(px, py, z, levels=levels[1:-1], colors=line_color, linewidths=0.7,
               alpha=min(1.0, alpha + 0.08), zorder=3)


# ---------------------------------------------------------------------------
# hex — size = volume, color = efficiency vs league
# ---------------------------------------------------------------------------
GRIDSIZE, MIN_ATT, SMOOTH_R, MIN_SMOOTH, DIFF_CLAMP = 18, 2, 45.0, 20, 0.10


def render_hex(ctx, out: Path, final: bool):
    from scipy.spatial import cKDTree

    theme = house.get_theme("jersey")
    fig, ax = house.new_canvas(theme)
    s = 1.72
    x0, y0 = draw_half_court(ax, house.CANVAS_WIDTH / 2, 700, s, COURT_WARM)

    p = ctx["player"][ctx["player"].shot_distance <= 30]
    l = ctx["league"][ctx["league"].shot_distance <= 30]
    centres, att = _hexbin(p.loc_x, p.loc_y)

    # Efficiency is pooled from a neighbourhood: a hex holding three shots can
    # only score 0/33/67/100%, which is noise dressed as signal.
    p_fg, pool = _pooled(cKDTree(np.c_[p.loc_x, p.loc_y]),
                         p.shot_made.to_numpy(float), centres)
    l_fg, _ = _pooled(cKDTree(np.c_[l.loc_x, l.loc_y]),
                      l.shot_made.to_numpy(float), centres)
    df = pd.DataFrame({"x": centres[:, 0], "y": centres[:, 1], "att": att,
                       "pool": pool, "diff": p_fg - l_fg})
    df = df[df.att >= MIN_ATT].copy()
    df.loc[df.pool < MIN_SMOOTH, "diff"] = np.nan

    hex_r = (sm.GRID_X[1] - sm.GRID_X[0]) / GRIDSIZE / np.sqrt(3) * 1.08
    cap = float(np.percentile(df.att, 92))
    norm = Normalize(-DIFF_CLAMP, DIFF_CLAMP)
    for row in df.itertuples():
        r = hex_r * s * (0.34 + 0.66 * min(row.att / cap, 1.0) ** 0.5)
        color = "#D8D2CA" if np.isnan(row.diff) else HEX_CMAP(norm(row.diff))
        ax.add_patch(RegularPolygon(
            (x0 + (row.x + 250.0) * s, y0 + (row.y + 47.5) * s), numVertices=6,
            radius=r, orientation=0, facecolor=color, edgecolor=theme.canvas,
            linewidth=0.5, zorder=3))

    _header(ax, theme, ctx, "Size = shot frequency  ·  Color = FG% vs. league from that spot")
    made = ctx["player"].shot_made.sum()
    efg = (made + 0.5 * ctx["player"].loc[ctx["player"].shot_type == "3PT",
                                          "shot_made"].sum()) / len(ctx["player"]) * 100
    ax.text(house.CANVAS_WIDTH / 2, 236,
            f"{len(ctx['player'])} FGA  ·  {made / len(ctx['player']) * 100:.1f}% FG"
            f"  ·  {efg:.1f}% eFG", ha="center", va="bottom", fontsize=16,
            color=theme.ink, fontproperties=helvetica("bold"))
    ax.text(house.CANVAS_WIDTH / 2, 202, "gray = too few shots nearby to judge",
            ha="center", va="bottom", fontsize=11, color=theme.faint,
            fontproperties=helvetica("bold"))
    _footer(ax, theme, ctx)
    _save(fig, out, final, theme.canvas)


def _hexbin(x, y, c=None):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    kw = dict(gridsize=GRIDSIZE, extent=(*sm.GRID_X, *sm.GRID_Y), mincnt=0)
    hb = ax.hexbin(x, y, C=c, reduce_C_function=np.sum, **kw) if c is not None \
        else ax.hexbin(x, y, **kw)
    centres, values = hb.get_offsets(), np.asarray(hb.get_array(), dtype=float)
    plt.close(fig)
    return centres, values


def _pooled(tree, made, centres, radius=SMOOTH_R):
    att = np.zeros(len(centres))
    hit = np.zeros(len(centres))
    for i, idx in enumerate(tree.query_ball_point(centres, radius)):
        att[i] = len(idx)
        hit[i] = made[idx].sum() if idx else 0.0
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(att > 0, hit / att, np.nan), att


# ---------------------------------------------------------------------------
# rings — concentric zones, volume and efficiency both vs league
# ---------------------------------------------------------------------------
# Chart-only asset: transparent, no title or footer, so page framing belongs to
# the layout tool. Type sits directly on the bands -- no cards -- with hierarchy
# carried by size, colour and spacing instead of containers.
OUTER = 355.0

# Four buckets rather than a continuous ramp. A smooth scale rendered three of a
# player's four zones in nearly the same green, because they genuinely sat within
# a point of each other; binning states the size of the gap honestly and gives
# each zone a colour a reader can name. The legend on the chart is the same four.
ZONE_BINS = [
    (-1e9, -5.0, "#8C3227", "-5% or worse", "WORSE"),
    (-5.0, 0.0, "#B04A3C", "-5 to 0", "SLIGHTLY WORSE"),
    (0.0, 5.0, "#3E7D57", "0 to +5", "SLIGHTLY BETTER"),
    (5.0, 1e9, "#245A3B", "+5% or better", "BETTER"),
]

COURT_INK = "#141414"        # court markings, per the reference card
CREAM = "#F5EFE2"            # headline figures and the zone pill
# Bright enough to carry their meaning while sitting on a coloured band: a
# delta and its band are often the same hue, so the tint has to do the work.
UP, DOWN = "#8FE8A8", "#FFA79B"
LEGEND_INK = "#808080"       # mid grey, legible on a light or a dark page
MUTED_BAND = "#B0ABA3"       # a zone that is not the subject of this slide

# --focus accepts the short forms a person would actually type.
FOCUS_ALIASES = {"rim": "RIM", "short": "SHORT MID", "short mid": "SHORT MID",
                 "smr": "SHORT MID", "long": "LONG MID", "long mid": "LONG MID",
                 "lmr": "LONG MID", "3pt": "THREE", "three": "THREE"}

ZONE_LABEL = {"THREE": "3PT"}                    # 3PT reads better than THREE
# Two columns rather than one stack makes each block short enough to sit inside
# its own band. The rim is the exception: its block drops to the basket, pill
# tucked under the backboard, where there is room the 3 ft band cannot offer.
LABEL_R = {"RIM": -28.0, "SHORT MID": 68.0, "LONG MID": 186.0, "THREE": 268.0}


def _zone_color(rel: float) -> str:
    for lo, hi, color, _, _ in ZONE_BINS:
        if lo <= rel < hi:
            return color
    return ZONE_BINS[-1][2]


def render_rings(ctx, out: Path, final: bool):
    zones = sm.zone_split(ctx["player"], ctx["league"], ctx["poss"], ctx["league_poss"])
    for z in zones.itertuples():
        print(f"  {z.zone:<11}{z.fg * 100:5.1f}% FG ({z.fg_rel:+.1f} vs lg)   "
              f"{z.per75:.1f}/75 ({z.vol_rel:+.0f}% vs lg)   [{z.fga} FGA]")

    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.patch.set_alpha(0.0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    s, hx, hy = 2.0, house.CANVAS_WIDTH / 2, 470
    base = hy + sm.BASELINE_Y * s
    # THREE is drawn as a full disc, not a ring. The corner-three pocket sits
    # inside the arc radius but outside the corner line, so an annulus starting
    # at ARC would leave it unpainted; the inner bands then cover the middle.
    bounds = {"RIM": (0.0, sm.RIM_MAX_FT * 10),
              "SHORT MID": (sm.RIM_MAX_FT * 10, sm.SHORT_MID_MAX_FT * 10),
              "LONG MID": (sm.SHORT_MID_MAX_FT * 10, ARC),
              "THREE": (0.0, OUTER)}

    # Trim at the sidelines and the baseline only. Capping the top as well would
    # square the outer band into a filled rectangle instead of an arc.
    clip = Rectangle((hx - 250 * s, base), 500 * s, 900 * s, transform=ax.transData)
    # The two-point area is bounded by the corner-three lines, not by radius
    # alone: past |x| = 220 a shot is a corner three however close to the hoop it
    # is, so the inner bands stop there and the outer band owns the corners.
    two_pt = Rectangle((hx - 220 * s, base), 440 * s, 900 * s, transform=ax.transData)
    focus = ctx.get("focus")
    for z in sorted(zones.itertuples(), key=lambda r: -bounds[r.zone][1]):
        band_clip = clip if z.zone == "THREE" else two_pt
        lit = focus is None or z.zone == focus
        color = _zone_color(z.fg_rel) if lit else MUTED_BAND
        _band(ax, (hx, hy), *bounds[z.zone], s, color, band_clip)
    for r_edge in (sm.RIM_MAX_FT * 10, sm.SHORT_MID_MAX_FT * 10):
        seam = ax.add_patch(Wedge((hx, hy), r_edge * s, 0, 360, width=2.0,
                                  facecolor=CREAM, edgecolor="none",
                                  alpha=0.5, zorder=5))
        seam.set_clip_path(two_pt)
    _ring_court(ax, hx, hy, s, clip)

    # The rim band is only a few feet across, so its block sits above the hoop
    # inside the paint; the pill names the zone so nothing is ambiguous.
    for z in zones.itertuples():
        y = hy + LABEL_R[z.zone] * s
        if focus is None or z.zone == focus:
            _zone_label(ax, hx, y, z)
        else:
            _muted_pill(ax, hx, y, ZONE_LABEL.get(z.zone, z.zone))

    _scale_legend(ax)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True)
    plt.close(fig)
    print(f"Saved {out}")


def _band(ax, centre, r_in, r_out, s, color, clip):
    """One zone as stacked sub-rings, tinted light at the inner edge for depth."""
    edges = np.linspace(r_in, r_out, BAND_STEPS + 1)
    for i in range(BAND_STEPS):
        lo, hi = edges[i], edges[i + 1]
        tint = _blend(color, "#FFFFFF", 0.10 * (1 - i / (BAND_STEPS - 1)))
        w = ax.add_patch(Wedge(centre, hi * s + 0.6, 0, 360,
                               width=None if lo == 0 else (hi - lo) * s + 0.6,
                               facecolor=tint, edgecolor="none", zorder=2))
        w.set_clip_path(clip)


BAND_STEPS = 14


def _ring_court(ax, hx, hy, s, clip):
    """Court markings in black, including the restricted-area arc."""
    from matplotlib.patches import Arc as _Arc, Circle as _Circle
    line = dict(color=COURT_INK, lw=2.0, zorder=6)
    base = hy + sm.BASELINE_Y * s

    ax.plot([hx - 250 * s, hx + 250 * s], [base, base], **line)
    ax.add_patch(Rectangle((hx - 80 * s, base), 160 * s, 190 * s, facecolor="none",
                           edgecolor=COURT_INK, lw=2.0, zorder=6))
    ax.add_patch(_Circle((hx, hy), 7.5 * s, facecolor="none", edgecolor=COURT_INK,
                         lw=2.0, zorder=7))
    ax.plot([hx - 30 * s, hx + 30 * s], [hy - 7.5 * s] * 2, **line)
    ax.add_patch(_Arc((hx, hy), 2 * 40 * s, 2 * 40 * s, theta1=0, theta2=180,
                      color=COURT_INK, lw=2.0, zorder=6))
    ft_y = hy + 142.5 * s
    ax.add_patch(_Arc((hx, ft_y), 120 * s, 120 * s, theta1=0, theta2=180,
                      color=COURT_INK, lw=2.0, zorder=6))
    ax.add_patch(_Arc((hx, ft_y), 120 * s, 120 * s, theta1=180, theta2=360,
                      color=COURT_INK, lw=2.0, linestyle=(0, (5, 4)), zorder=6))
    corner_top = (ARC ** 2 - 220 ** 2) ** 0.5
    for side in (-220, 220):
        ax.plot([hx + side * s] * 2, [base, hy + corner_top * s], **line)
    a = ax.add_patch(_Arc((hx, hy), 2 * ARC * s, 2 * ARC * s, theta1=22.1,
                          theta2=157.9, color=COURT_INK, lw=2.0, zorder=6))
    a.set_clip_path(clip)


def _zone_label(ax, x, y, z):
    """Pill, then two equally weighted figures each with its league delta.

    Shooting and volume carry the same type size deliberately: sizing FG% larger
    would rank it above how often he goes there, and the whole point of the chart
    is that the two are read together.
    """
    name = ZONE_LABEL.get(z.zone, z.zone)
    label = ax.text(x, y + 45, name, ha="center", va="center", fontsize=14,
                    color="#1F1D1A", zorder=10, fontproperties=helvetica("bold"))
    pill_w = max(house.rendered_width(ax, label) + 46, 118)
    ax.add_patch(FancyBboxPatch((x - pill_w / 2, y + 30), pill_w, 36,
                 boxstyle="round,pad=0,rounding_size=18", facecolor=CREAM,
                 edgecolor="none", zorder=9))

    # Shooting on the left, volume on the right. Side by side keeps the block
    # short enough to sit inside its band, and neither figure outranks the other.
    val = dict(ha="center", va="center", fontsize=13, color=CREAM, zorder=10,
               fontproperties=helvetica("bold"))
    delta = dict(ha="center", va="center", fontsize=10.5, zorder=10,
                 fontproperties=helvetica("bold"))
    columns = (
        (x - 70, f"{z.fg * 100:.1f}%", z.fg_rel, f"{z.fg_rel:+.1f} vs LA"),
        (x + 70, f"{z.per75:.1f} FGA / 75", z.vol_rel, f"{z.vol_rel:+.0f}% vs LA"),
    )
    for cx, figure, rel, caption in columns:
        ax.text(cx, y + 4, figure, **val)
        ax.text(cx, y - 18, caption, color=UP if rel >= 0 else DOWN, **delta)


def _muted_pill(ax, x, y, name):
    """Name only, for a zone this slide is not about."""
    label = ax.text(x, y + 45, name, ha="center", va="center", fontsize=13,
                    color="#5E5A55", alpha=0.9, zorder=10,
                    fontproperties=helvetica("bold"))
    w = max(house.rendered_width(ax, label) + 40, 108)
    ax.add_patch(FancyBboxPatch((x - w / 2, y + 31), w, 33,
                 boxstyle="round,pad=0,rounding_size=16", facecolor=CREAM,
                 edgecolor="none", alpha=0.55, zorder=9))


def _scale_legend(ax):
    """The four buckets, printed on the chart so the colours are self-explaining."""
    n = len(ZONE_BINS)
    w, gap = 214, 16
    total = n * w + (n - 1) * gap
    x0, y = (house.CANVAS_WIDTH - total) / 2, 178
    ax.text(house.CANVAS_WIDTH / 2, y + 54, "FG% VS LEAGUE AVERAGE", ha="center",
            va="center", fontsize=11, color=LEGEND_INK, zorder=9,
            fontproperties=helvetica("bold"))
    for i, (_, _, color, span, word) in enumerate(ZONE_BINS):
        cx = x0 + i * (w + gap)
        ax.add_patch(Rectangle((cx, y), w, 22, facecolor=color, edgecolor="none",
                               zorder=9))
        ax.text(cx + w / 2, y - 18, span, ha="center", va="center", fontsize=11,
                color=LEGEND_INK, zorder=9, fontproperties=helvetica("bold"))
        ax.text(cx + w / 2, y - 40, word, ha="center", va="center", fontsize=9,
                color=LEGEND_INK, alpha=0.85, zorder=9,
                fontproperties=helvetica("bold"))


# ---------------------------------------------------------------------------
# cells — the fine polar grid
# ---------------------------------------------------------------------------
# Same chart-only contract as rings: transparent, no title or footer, page
# framing belongs to Canva. Colour is FG% vs league from the same cell, binned
# into the family's four buckets rather than a continuous ramp. A ramp would
# imply a precision the sample does not have -- several cells hold 20-40 shots,
# where FG% swings on chance alone -- and it would break with the rings chart,
# which a reader may meet in the same carousel.
# Light enough that a wall of unrated cells recedes. Matas takes 12% of his
# shots between 4 ft and the arc, so more than half the grid greys out; at the
# rings chart's muted tone that emptiness read louder than the findings.
CELL_GREY = "#D2CDC5"
CELL_SEAM = "#F5EFE2"


def render_cells(ctx, out: Path, final: bool):
    cells = sm.polar_split(ctx["player"], ctx["league"])
    rated, thin = cells[cells.rated], cells[~cells.rated]
    print(f"  {len(rated)}/{len(cells)} cells rated, holding "
          f"{rated.fga.sum() / len(ctx['player']) * 100:.0f}% of his attempts")
    for c in cells.sort_values("fga", ascending=False).itertuples():
        rel = f"{c.fg_rel:+5.1f}" if c.fga else "    -"
        fg = c.fg * 100 if c.fga else 0.0
        print(f"  {c.name:<18}{c.fga:>4} FGA  {fg:5.1f}% ({rel} vs lg)"
              f"{'' if c.rated else '   (too few to rate)'}")

    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.patch.set_alpha(0.0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    s, hx, hy = 2.0, house.CANVAS_WIDTH / 2, 470
    base = hy + sm.BASELINE_Y * s
    # Two clips, exactly as in rings: threes may run to the sidelines, twos stop
    # at the corner line so the corner pocket belongs to the three-point cells.
    clip = Rectangle((hx - 250 * s, base), 500 * s, 900 * s, transform=ax.transData)
    two_pt = Rectangle((hx - 220 * s, base), 440 * s, 900 * s, transform=ax.transData)

    for c in cells.itertuples():
        color = _zone_color(c.fg_rel) if c.rated else CELL_GREY
        _cell_wedge(ax, (hx, hy), c, s, color, clip if c.three else two_pt)
    _ring_court(ax, hx, hy, s, clip)
    for c in cells.itertuples():
        _cell_label(ax, hx, hy, c, s)

    _scale_legend(ax)
    ax.text(house.CANVAS_WIDTH / 2, 108,
            f"GREY = UNDER {sm.MIN_CELL_FGA} ATTEMPTS, TOO FEW TO RATE",
            ha="center", va="center", fontsize=10, color=LEGEND_INK, alpha=0.9,
            zorder=9, fontproperties=helvetica("bold"))

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True)
    plt.close(fig)
    print(f"Saved {out}")


def _cell_angles(cell) -> tuple[float, float]:
    """Matplotlib start/end angles for a cell's wedge, in degrees.

    ``sector_index`` counts from the viewer's left while Wedge measures
    anticlockwise from the +x axis, so the index has to be mirrored.

    The two outermost sectors are extended below the hoop line, to 270 and -90,
    which fills the strip between the hoop and the baseline. That is not a
    cosmetic stretch: ``sector_index`` clamps a behind-the-hoop shot's angle to
    0 or 180, so those shots already count in the outermost sectors, and the
    drawn wedge now covers exactly the ground its own arithmetic claims.
    """
    if cell.n_sectors == 1:
        return 0.0, 360.0
    step = 180.0 / cell.n_sectors
    t1 = -90.0 if cell.sector == cell.n_sectors - 1 else 180.0 - (cell.sector + 1) * step
    t2 = 270.0 if cell.sector == 0 else 180.0 - cell.sector * step
    return t1, t2


def _cell_wedge(ax, centre, cell, s, color, clip):
    t1, t2 = _cell_angles(cell)
    r_out, r_in = cell.r_out * 10 * s, cell.draw_in * 10 * s
    w = ax.add_patch(Wedge(centre, r_out + 0.6, t1, t2,
                           width=None if r_in <= 0 else r_out - r_in + 0.6,
                           facecolor=color, edgecolor=CELL_SEAM, linewidth=1.6,
                           zorder=2))
    w.set_clip_path(clip)


MIN_LABELLED_FGA = 5     # a grey cell holding fewer is left blank, not annotated
CORNER_X, CORNER_Y = 235.0, 62.0     # label anchor inside the corner pocket


def _is_corner(cell) -> bool:
    return bool(cell.three and cell.sector in (0, cell.n_sectors - 1))


def _label_anchor(cell, hx, hy, s) -> tuple[float, float]:
    """Where a cell's number sits, in pixels.

    The angular midline at the radial midpoint lands near enough to a wedge's
    visual centre for every cell but two. Corner threes are the exception: the
    pocket is a strip 3 ft wide running up the sideline, so the sector's
    geometric centroid falls off the canvas entirely. Those get a fixed anchor
    inside the pocket instead. Angles come from the *unextended* sector span --
    the below-hoop extension is drawn area, not where a reader looks.
    """
    if _is_corner(cell):
        return hx + (-1 if cell.sector == 0 else 1) * CORNER_X * s, hy + CORNER_Y * s
    if cell.n_sectors == 1:
        mid = np.radians(90.0)
    else:
        mid = np.radians(180.0 - (cell.sector + 0.5) * (180.0 / cell.n_sectors))
    r = (cell.r_in + 2.4) if cell.three else (cell.r_in + cell.r_out) / 2
    return hx + np.cos(mid) * r * 10 * s, hy + np.sin(mid) * r * 10 * s


def _cell_label(ax, hx, hy, cell, s):
    """FG% at the cell's anchor, with its league delta alongside.

    Corner labels are turned to read up the sideline. Horizontal type cannot fit
    a 3 ft pocket at any size worth reading, and those two cells carry 170 of
    his attempts -- too many to leave unlabelled or to shrink into illegibility.
    """
    if not cell.fga or (not cell.rated and cell.fga < MIN_LABELLED_FGA):
        return
    x, y = _label_anchor(cell, hx, hy, s)
    corner = _is_corner(cell)
    rot = 0 if not corner else (90 if cell.sector == 0 else -90)
    # Rotated, the stacking axis turns with the text: "above" and "below" become
    # sideways on the page, so the two lines stay stacked as the reader sees them.
    if not corner:
        top, under = (0.0, 9.0), (0.0, -13.0)
    elif cell.sector == 0:
        top, under = (-9.0, 0.0), (13.0, 0.0)
    else:
        top, under = (9.0, 0.0), (-13.0, 0.0)

    if cell.rated:
        ax.text(x + top[0], y + top[1], f"{cell.fg * 100:.0f}%", ha="center",
                va="center", fontsize=17, color=CREAM, rotation=rot, zorder=10,
                fontproperties=helvetica("bold"))
        ax.text(x + under[0], y + under[1], f"{cell.fg_rel:+.0f} vs LA",
                ha="center", va="center", fontsize=10, rotation=rot,
                color=UP if cell.fg_rel >= 0 else DOWN, zorder=10,
                fontproperties=helvetica("bold"))
    else:
        ax.text(x, y, f"{cell.fga} FGA", ha="center", va="center", fontsize=10,
                color="#4A463F", alpha=0.75, rotation=rot, zorder=10,
                fontproperties=helvetica("bold"))


# ---------------------------------------------------------------------------
# ladder — concentric distance bands, the "Midrange Is Dead" form
# ---------------------------------------------------------------------------
# Distance and nothing else. Two metrics, and they are not interchangeable:
#
#   pps     points per shot, the absolute value of a shot from that far out
#   fg-rel  FG% minus the league's FG% from the same ring
#
# PPS is the one that carries the argument, because it is the only scale on
# which a two and a three can be compared -- and it is the reason the floor of
# the chart sits just INSIDE the arc rather than at the top of the key.
LADDER_CMAP = LinearSegmentedColormap.from_list("ladder", [
    "#5E1119", "#8C1D22", "#C0392B", "#E2614A", "#F0A05F", "#EFD07A",
    "#BFD16C", "#7FBF5E", "#4C9B4A", "#2E7D3A", "#1B5E2A"])
LADDER_SEAM = "#00000022"     # a hairline between rings, dark and nearly invisible
LADDER_INK, LADDER_INK_DARK = "#FFFFFF", "#2A2118"
# Light, so the run of unrated rings recedes into "nothing happens here" rather
# than reading as a rendering fault. Those rings are a finding in their own
# right: the Bulls take 79 shots all season from 16-21 ft, which is why the
# band is empty at all.
# Warm neutral rather than near-white: the asset exports transparent and may
# land on a pale Canva page, where a lighter grey would vanish into it.
LADDER_THIN = "#C2BAAE"

# Fixed, round, symmetric scales -- never fitted to the data.
#
# Two separate ideas, and getting either wrong misreads the chart:
#
# 1. CLAMPED range. The rim ring is a huge outlier at 1.51, and letting it set
#    the range squashes every other ring into two shades of red. The reference
#    card clamps the same way: its key stops at 1.20 while its rim reads 1.51.
# 2. MEANINGFUL midpoint. The colour turn must sit on a number a reader can
#    name. For points per shot that is 1.00 -- a shot worth exactly one point --
#    which is where the reference turns from orange to green. Centring on the
#    league mean instead (1.09) was wrong: it pushed the turn up so that 1.00
#    rendered orange and nothing went green until about 1.15, quietly flattering
#    every ring between the two.
#
# Steps are round in each metric's own units so the key reads as a ruler.
LADDER_SCALES = {
    "pps": {"lo": 0.80, "hi": 1.20, "step": 0.05},
    "pps-rel": {"lo": -0.20, "hi": 0.20, "step": 0.05},
    "fg-rel": {"lo": -10.0, "hi": 10.0, "step": 5.0},
}


def _ladder_ticks(scale: dict) -> list[float]:
    n = int(round((scale["hi"] - scale["lo"]) / scale["step"]))
    return [scale["lo"] + i * scale["step"] for i in range(n + 1)]


def scale_eps(span: float) -> float:
    """Tolerance for 'is this the midpoint tick', robust to float drift."""
    return span * 1e-6


def _fit_note(ax, y: float, text: str, pt: float = 8.5):
    """A centred note that shrinks rather than running off the canvas.

    The coverage line is generated from the data, so its length changes with
    the numbers in it; sizing it by hand would work until the day it didn't.
    """
    t = ax.text(house.CANVAS_WIDTH / 2, y, text, ha="center", va="center",
                fontsize=pt, color=LEGEND_INK, alpha=0.9, zorder=9,
                fontproperties=helvetica("bold"))
    avail = house.CANVAS_WIDTH - 2 * house.SIDE_MARGIN
    width = house.rendered_width(ax, t)
    if width > avail:
        t.set_fontsize(pt * avail / width)
    return t

LADDER_METRICS = {
    "pps": {"column": "pps", "fmt": lambda v: f"{v:.2f}",
            "title": "POINTS PER SHOT",
            "tick_fmt": lambda v: f"{v:.2f}"},
    "fg-rel": {"column": "fg_rel", "fmt": lambda v: _signed(v) + "%",
               "title": "FG% VS LEAGUE AVERAGE",
               "tick_fmt": lambda v: _signed(v) + "%"},
    # The counterpart to fg-rel, and the sharper of the two for a team read:
    # it asks not "did they shoot it well" but "did the shot pay", which folds
    # accuracy and the extra point for a three into one number.
    "pps-rel": {"column": "pps_rel", "fmt": lambda v: _signed2(v),
                "title": "POINTS PER SHOT VS LEAGUE AVERAGE",
                "tick_fmt": lambda v: _signed2(v)},
}

# 30 rings share ~580 px of column, so the type has to clear its own line
# height with room left over or the stack reads as a solid block.
LADDER_LABEL_PT = 7.5
# Slightly INSIDE each ring's midpoint. Matplotlib centres a text *box*, not the
# digits inside it, and that box carries descender space no digit uses -- so a
# geometrically centred number sits visibly high in its band. The value is
# measured, not guessed: rendering and comparing glyph-ink centres against band
# centres puts the residual at 0 px here. It also drops the innermost label into
# the rim itself, where the reference puts it.
LABEL_NUDGE_PX = -1.0


def _signed(v: float) -> str:
    """Signed whole number, with no "-0". A ring level with the league reads 0."""
    return "0" if round(v) == 0 else f"{v:+.0f}"


def _signed2(v: float) -> str:
    """Signed to two places, with no "-0.00"."""
    return "0" if abs(round(v, 2)) < 0.005 else f"{v:+.2f}"


def render_ladder(ctx, out: Path, final: bool):
    metric = LADDER_METRICS[ctx["metric"]]
    step = ctx.get("band", sm.LADDER_STEP_FT)
    edges = sm.ladder_edges(step)
    rings = sm.distance_ladder(ctx["player"], ctx["league"], step=step)
    col = metric["column"]
    # Coverage is told the ladder's REAL outer edge, not the nominal maximum:
    # at 2 ft wide the last band stops at 30, so 30-31 ft becomes excluded and
    # the "% shown" line has to say so.
    cover = sm.ladder_coverage(ctx["player"], max_ft=float(edges[-1]))
    corner = sm.corner_split(ctx["player"], ctx["league"])
    for r in rings.itertuples():
        flag = "" if r.rated else "   (too few to rate)"
        kind = "3PT" if r.three else "2PT"
        print(f"  {r.lo:5.0f}-{r.hi:<3.0f} ft {kind} {r.fga:>5} FGA   "
              f"PPS {r.pps:.2f}   FG {r.fg * 100:5.1f}% ({r.fg_rel:+.1f} vs lg)"
              f"{flag}")
    print(f"  CORNER 3    {corner['fga']:>5} FGA   PPS {corner['pps']:.2f}   "
          f"FG {corner['fg'] * 100:5.1f}% ({corner['fg_rel']:+.1f} vs lg)"
          f"{'' if corner['rated'] else '   (too few to rate)'}")
    print(f"  coverage: {cover['total'] - cover['excluded']} of {cover['total']} "
          f"attempts on the chart ({(1 - cover['excluded_share']) * 100:.1f}%); "
          f"excluded {cover['stray_threes']} threes registering inside "
          f"{sm.LADDER_TWO_MAX_FT:.0f} ft off the corner "
          f"({cover['three_share_excluded'] * 100:.1f}% of 3PA), "
          f"{cover['long_twos']} long twos, {cover['beyond_range']} beyond range")

    live = rings[rings.rated & rings[col].notna()]
    if live.empty:
        raise SystemExit("No ring has enough attempts to draw")
    scale = LADDER_SCALES[ctx["metric"]]
    ticks = _ladder_ticks(scale)
    norm = Normalize(scale["lo"], scale["hi"], clip=True)
    below = int((live[col] < scale["lo"]).sum())
    above = int((live[col] > scale["hi"]).sum())
    print(f"  scale {scale['lo']:.2f} to {scale['hi']:.2f} in steps of "
          f"{scale['step']:.2f}, turning at "
          f"{(scale['lo'] + scale['hi']) / 2:.2f}; {below} rings clamp low, "
          f"{above} clamp high")

    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.patch.set_alpha(0.0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    s, hx, hy = 2.0, house.CANVAS_WIDTH / 2, 470
    base = hy + sm.BASELINE_Y * s
    # Rings run past the sidelines and are cut there, exactly as the reference
    # does: the court, not the data, decides how wide the fan gets.
    clip = Rectangle((hx - 250 * s, base), 500 * s, 1000 * s, transform=ax.transData)
    # Two-point rings stop at the corner line; the pocket beyond it is drawn
    # separately with its own value, because a corner three is not a long two.
    cx = sm.CORNER_LINE_X
    inner_clip = Rectangle((hx - cx * s, base), 2 * cx * s, 1000 * s,
                           transform=ax.transData)

    # Outermost first, so each ring paints over its larger neighbour and can
    # drop a shadow onto it -- the stacked-plate look the reference has.
    for i, r in enumerate(reversed(list(rings.itertuples()))):
        drawable = r.rated and not np.isnan(getattr(r, col))
        color = LADDER_CMAP(norm(getattr(r, col))) if drawable else LADDER_THIN
        _ladder_ring(ax, (hx, hy), r, s, color, clip if r.three else inner_clip,
                     shadow=i > 0)
    _corner_pocket(ax, hx, hy, s, base, corner, col, norm, metric)

    _ladder_court(ax, hx, hy, s, clip)
    for r in rings.itertuples():
        _ladder_label(ax, hx, hy, s, r, col, metric, norm)
    _ladder_legend(ax, norm, metric, ticks)
    # Required by the working guide: the coverage window stays on the graphic.
    # The grey key is not optional either -- on a team season a third of the
    # ladder can grey out, and unexplained grey reads as "average" rather than
    # "unknown", which is the opposite of what it means.
    _fit_note(ax, 112,
              f"INSIDE {sm.LADDER_TWO_MAX_FT:.0f} FT COUNTS 2-POINTERS  ·  "
              f"OUTSIDE COUNTS 3-POINTERS  ·  CORNER POCKET SHOWN SEPARATELY")
    grey = int((~rings.rated).sum()) + (0 if corner["rated"] else 1)
    key = f"{(1 - cover['excluded_share']) * 100:.0f}% OF ALL ATTEMPTS SHOWN"
    if grey:
        key += (f"  ·  GREY = UNDER {sm.MIN_RING_FGA} ATTEMPTS, "
                f"TOO FEW TO RATE ({grey} BANDS)")
    _fit_note(ax, 90, key)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True)
    plt.close(fig)
    print(f"Saved {out}")


RING_STEPS = 6          # sub-bands per ring, for the inner-edge lift
RING_LIFT = 0.13        # how far the inner edge tints toward white
SHADOW_PX, SHADOW_ALPHA, SHADOW_STEPS = 7.0, 0.20, 7


def _corner_pocket(ax, hx, hy, s, base, corner, col, norm, metric):
    """The corner-three pocket, painted with its own value and labelled.

    Drawn as a disc out to the split radius, clipped to the strip beyond each
    corner line -- so it fills exactly the ground the two-point rings vacated,
    with no seam and no overlap. The label reads up the sideline for the same
    reason the ``cells`` chart's does: the pocket is 3 ft wide and horizontal
    type cannot fit at any size worth reading.
    """
    value = corner.get(col)
    drawable = corner["rated"] and value is not None and not np.isnan(value)
    color = LADDER_CMAP(norm(value)) if drawable else LADDER_THIN
    cx = sm.CORNER_LINE_X
    for side in (-1, 1):
        strip = Rectangle((hx + side * cx * s if side > 0 else hx - 250 * s, base),
                          (250 - cx) * s, 1000 * s, transform=ax.transData)
        w = ax.add_patch(Wedge((hx, hy), sm.LADDER_TWO_MAX_FT * 10 * s, 0, 360,
                               facecolor=color, edgecolor="none", zorder=3))
        w.set_clip_path(strip)
    if not drawable:
        return

    rgb = LADDER_CMAP(norm(value))[:3]
    dark_ink = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] > 0.62
    lx, ly = _corner_centroid()
    for side in (-1, 1):
        ax.text(hx + side * lx * s, hy + ly * s, metric["fmt"](value),
                ha="center", va="center", fontsize=LADDER_LABEL_PT + 1.5,
                rotation=90 if side < 0 else -90,
                color=LADDER_INK_DARK if dark_ink else LADDER_INK, zorder=10,
                fontproperties=helvetica("bold"))


def _corner_centroid() -> tuple[float, float]:
    """Area centroid of the corner pocket, in NBA units from the hoop.

    The pocket is not a rectangle, so no fixed offset can sit in the middle of
    it. Its outer edge is the split-radius circle, which means it is tallest
    against the corner line and tapers to nothing where that circle crosses the
    sideline -- so its true centre sits low and inward of where eyeballing puts
    it. Computed rather than tuned, so it follows if the split radius or the
    corner line ever moves.
    """
    r = sm.LADDER_TWO_MAX_FT * 10.0
    xs = np.linspace(sm.CORNER_LINE_X, min(250.0, r), 512)
    tops = np.sqrt(np.maximum(r ** 2 - xs ** 2, 0.0))
    heights = np.maximum(tops - sm.BASELINE_Y, 0.0)
    area = heights.sum()
    if area <= 0:
        return sm.CORNER_LINE_X + 15.0, 0.0
    return (float((xs * heights).sum() / area),
            float(((tops + sm.BASELINE_Y) / 2 * heights).sum() / area))


def _ladder_ring(ax, centre, ring, s, color, clip, shadow: bool):
    """One ring, drawn as a raised plate sitting on the ring outside it.

    Two effects together sell the depth, and neither is decoration for its own
    sake -- they are what separates 30 abutting bands into 30 readable steps:

    * a **cast shadow** just outside the ring, darkening the larger neighbour
      that was drawn a moment ago, as if this ring floated above it;
    * an **inner-edge lift**, each ring tinted slightly lighter where it meets
      the smaller ring, which reads as the light catching a bevelled edge.

    Both are drawn as stacks of thin annuli. Matplotlib has no blur, so a
    gradient built from a handful of steps is how a soft edge gets made.
    """
    r_out, r_in = ring.hi * 10 * s, ring.lo * 10 * s
    if shadow:
        for k in range(SHADOW_STEPS):
            t = k / SHADOW_STEPS
            w = ax.add_patch(Wedge(centre, r_out + SHADOW_PX * (1 - t), 0, 360,
                                   width=SHADOW_PX / SHADOW_STEPS + 0.6,
                                   facecolor="#1A120C", edgecolor="none",
                                   alpha=SHADOW_ALPHA * t ** 1.6, zorder=2))
            w.set_clip_path(clip)

    edges_px = np.linspace(r_in, r_out, RING_STEPS + 1)
    for k in range(RING_STEPS):
        lo, hi = edges_px[k], edges_px[k + 1]
        tint = _blend(color, "#FFFFFF", RING_LIFT * (1 - k / (RING_STEPS - 1)))
        w = ax.add_patch(Wedge(centre, hi + 0.6, 0, 360,
                               width=None if lo <= 0 else hi - lo + 0.6,
                               facecolor=tint, edgecolor="none", zorder=3))
        w.set_clip_path(clip)


def _ladder_label(ax, hx, hy, s, ring, col, metric, norm):
    """One number per ring, stacked up the middle of the court.

    Ink flips with the ring beneath it. The ramp runs from near-black reds to
    pale yellow-greens, so a single ink colour is unreadable somewhere on the
    scale whichever one is chosen; luminance decides it per ring instead.
    """
    if not ring.fga:
        return
    value = getattr(ring, col)
    # An unrated ring is left blank. The grey band already says "nothing
    # happens here"; printing its attempt count invited the number to be read
    # on the same scale as the rated rings, which it is not.
    if not ring.rated or np.isnan(value):
        return
    # Ring midpoint, nudged out by a few pixels. Dead-centre puts the innermost
    # label inside the rim circle, where the hoop draws straight through it; the
    # nudge is small enough that every number still sits within its own band.
    y = hy + (ring.lo + ring.hi) / 2 * 10 * s + LABEL_NUDGE_PX
    rgb = LADDER_CMAP(norm(value))[:3]
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    ax.text(hx, y, metric["fmt"](value), ha="center", va="center",
            fontsize=LADDER_LABEL_PT,
            color=LADDER_INK_DARK if lum > 0.62 else LADDER_INK, zorder=10,
            fontproperties=helvetica("bold"))


# Court ink. Softer and thinner than the zone charts use: here the markings sit
# on top of 30 saturated bands, so a hard white line fights the data for
# attention instead of quietly locating it.
LADDER_COURT_INK = "#FBF7F1"
# Dropped a notch from 0.68 so the rim label stays legible. The innermost
# value in the number column sits inside the hoop, and with the label
# outlines removed an opaque rim circle drew straight through white digits.
LADDER_COURT_ALPHA, LADDER_COURT_LW = 0.52, 1.3
# Lane-space marks, in feet from the baseline along the paint edge. These are
# the real NBA positions -- the block, then the three rebounding slots.
LANE_MARKS_FT = (7.0, 8.0, 11.0, 14.0)
HASH_FROM_BASELINE_FT = 28.0     # sideline hash, where the coaching box begins


def _ladder_court(ax, hx, hy, s, clip):
    """Court markings, drawn light because every ring sits under them."""
    from matplotlib.patches import Arc as _Arc, Circle as _Circle
    ink = LADDER_COURT_INK
    line = dict(color=ink, lw=LADDER_COURT_LW, zorder=6, alpha=LADDER_COURT_ALPHA)
    arcs = dict(color=ink, lw=LADDER_COURT_LW, alpha=LADDER_COURT_ALPHA, zorder=6)
    base = hy + sm.BASELINE_Y * s

    ax.plot([hx - 250 * s, hx + 250 * s], [base, base], **line)
    ax.add_patch(Rectangle((hx - 80 * s, base), 160 * s, 190 * s, facecolor="none",
                           edgecolor=ink, lw=LADDER_COURT_LW,
                           alpha=LADDER_COURT_ALPHA, zorder=6))

    # Lane marks: short ticks stepping out from each paint edge.
    for ft in LANE_MARKS_FT:
        y = base + ft * 10 * s
        for side, direction in ((-80, -1), (80, 1)):
            ax.plot([hx + side * s, hx + (side + direction * 8) * s], [y, y], **line)

    # Sideline hash marks, which the reference keeps and which quietly tell the
    # reader how far out the widest rings actually reach.
    y = base + HASH_FROM_BASELINE_FT * 10 * s
    for side, direction in ((-250, 1), (250, -1)):
        ax.plot([hx + side * s, hx + (side + direction * 18) * s], [y, y], **line)

    # Restricted area: 4 ft from the centre of the rim, the arc a defender
    # cannot draw a charge inside. It belongs on this chart more than most --
    # the rim ring's 1.51 points per shot is very largely taken inside it.
    ax.add_patch(_Arc((hx, hy), 2 * 40 * s, 2 * 40 * s, theta1=0, theta2=180, **arcs))
    for side in (-40, 40):
        ax.plot([hx + side * s] * 2, [hy, hy - 7.5 * s], **line)

    # Backboard with depth: a thick plate over a soft drop shadow, then the rim
    # and its connector drawn on top.
    bb_y = hy - 7.5 * s
    for dy, lw, alpha, color in ((-2.4, 5.0, 0.30, "#150F0A"),
                                 (0.0, 4.2, 0.95, ink)):
        ax.plot([hx - 30 * s, hx + 30 * s], [bb_y + dy] * 2, color=color, lw=lw,
                alpha=alpha, solid_capstyle="butt", zorder=7)
    ax.plot([hx, hx], [bb_y, hy - 7.5 * s + 5.0], color=ink, lw=1.6, alpha=0.9,
            zorder=7)
    # The rim goes lightest of all. It is the one marking that shares its exact
    # position with a number -- the innermost ring's value sits inside the hoop
    # -- so it has to locate the basket without competing with the digits.
    ax.add_patch(_Circle((hx, hy), 7.5 * s, facecolor="none", edgecolor=ink,
                         lw=1.5, alpha=0.42, zorder=4))

    ft_y = hy + 142.5 * s
    for t1, t2, dash in ((0, 180, "solid"), (180, 360, (0, (5, 4)))):
        ax.add_patch(_Arc((hx, ft_y), 120 * s, 120 * s, theta1=t1, theta2=t2,
                          linestyle=dash, **arcs))
    corner_top = (ARC ** 2 - 220 ** 2) ** 0.5
    for side in (-220, 220):
        ax.plot([hx + side * s] * 2, [base, hy + corner_top * s], **line)
    a = ax.add_patch(_Arc((hx, hy), 2 * ARC * s, 2 * ARC * s, theta1=22.1,
                          theta2=157.9, **arcs))
    a.set_clip_path(clip)


def _ladder_legend(ax, norm, metric, ticks):
    """A continuous bar, because the encoding is continuous.

    The binned legend the zone charts use would misdescribe this one: here every
    ring gets its own value off a ramp, and rounding that into four buckets on
    the key while the art shows a gradient is the kind of mismatch a reader
    notices without being able to name.
    """
    w, h, y = 760.0, 22.0, 176.0
    x0 = (house.CANVAS_WIDTH - w) / 2
    grad = np.linspace(0, 1, 512).reshape(1, -1)
    ax.imshow(grad, extent=(x0, x0 + w, y, y + h), aspect="auto",
              cmap=LADDER_CMAP, zorder=9)
    ax.text(house.CANVAS_WIDTH / 2, y + h + 26, metric["title"], ha="center",
            va="center", fontsize=11, color=LEGEND_INK, zorder=9,
            fontproperties=helvetica("bold"))
    lo, hi = norm.vmin, norm.vmax
    mid = (lo + hi) / 2
    for tick in ticks:
        tx = x0 + (tick - lo) / (hi - lo) * w
        # The midpoint tick is the one that carries meaning -- it is where the
        # ramp turns -- so it is drawn heavier than the rest of the ruler.
        turn = abs(tick - mid) < scale_eps(hi - lo)
        ax.plot([tx, tx], [y - (3 if turn else 0), y + h + (3 if turn else 0)],
                color="#FFFFFF" if not turn else "#3A342C",
                lw=1.8 if turn else 0.9, alpha=0.9 if turn else 0.5, zorder=10)
        ax.text(tx, y - 19, metric["tick_fmt"](tick), ha="center", va="center",
                fontsize=8.5, color=LEGEND_INK,
                alpha=1.0 if turn else 0.85, zorder=9,
                fontproperties=helvetica("bold"))


def _blend(color, other, amount):
    """Mix ``color`` toward ``other`` by ``amount`` (0 = unchanged, 1 = other)."""
    import matplotlib.colors as mc
    a, b = np.array(mc.to_rgb(color)), np.array(mc.to_rgb(other))
    return tuple(a + (b - a) * amount)


# ---------------------------------------------------------------------------
# Shared chrome
# ---------------------------------------------------------------------------
def _header(ax, theme, ctx, rule: str):
    title = ax.text(house.SIDE_MARGIN, house.CANVAS_HEIGHT - 66, ctx["name"].upper(),
                    ha="left", va="top", fontsize=42, color=theme.ink,
                    fontproperties=helvetica("bold"))
    avail = house.CANVAS_WIDTH - 2 * house.SIDE_MARGIN
    width = house.rendered_width(ax, title)
    if width > avail:
        title.set_fontsize(42 * avail / width)
    ax.text(house.SIDE_MARGIN, house.CANVAS_HEIGHT - 148, ctx["subtitle"],
            ha="left", va="top", fontsize=14, color=theme.muted,
            fontproperties=helvetica("bold"))
    ax.text(house.SIDE_MARGIN, house.CANVAS_HEIGHT - 180, rule, ha="left", va="top",
            fontsize=12.5, color=theme.accent, fontproperties=helvetica("bold"))


def _footer(ax, theme, ctx):
    ax.text(house.SIDE_MARGIN, 44, "Data: nba.com/stats", ha="left", va="bottom",
            fontsize=9, color=theme.faint, fontproperties=helvetica())


def _save(fig, out: Path, final: bool, facecolor: str):
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=house.export_dpi(final), facecolor=facecolor)
    plt.close(fig)
    print(f"Saved {out}")


CHARTS = {"hotspot": render_hotspot, "hex": render_hex, "rings": render_rings,
          "cells": render_cells, "ladder": render_ladder}
# Charts that describe a shot profile rather than a shooter, so they accept
# --team in place of --player.
TEAM_CAPABLE = {"ladder", "hotspot", "hex", "cells"}


def _output_path(args, slug: str) -> Path:
    """``YYYY-MM-DD-{chart}-{mode}-{scope}.png``, the convention in DEVELOPMENT.md.

    Dated because these are dailies: a chart rebuilt a week later is a different
    chart, and an undated filename silently overwrites the version already sitting
    in a Canva page. The date comes from the filesystem clock rather than the
    season string, since it stamps when the asset was cut, not what it covers.
    """
    from datetime import date

    mode = args.metric if args.chart == "ladder" else args.focus.strip().lower()
    parts = [date.today().isoformat(), args.chart] + ([mode] if mode else [])
    if args.chart == "ladder" and args.band != sm.LADDER_STEP_FT:
        parts.append(f"{args.band:g}ft")
    parts.append(slug)
    return ROOT / "output" / "feed" / ("-".join(parts) + ".png")


def main():
    ap = argparse.ArgumentParser(description="Build a player shot chart")
    ap.add_argument("--player", help="player name, e.g. 'Matas Buzelis'")
    ap.add_argument("--player-id", type=int)
    ap.add_argument("--chart", choices=list(CHARTS), required=True)
    ap.add_argument("--season", default=CURRENT_SEASON)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--focus", default="",
                    help="rings only: spotlight one zone (rim, short, long, 3pt)")
    ap.add_argument("--team", action="store_true",
                    help="chart the Bulls' whole shot profile instead of a player")
    ap.add_argument("--league", action="store_true",
                    help="chart all 30 teams — the baseline every other chart compares to")
    ap.add_argument("--metric", default="pps", choices=list(LADDER_METRICS),
                    help="ladder only: what each ring's colour and number mean")
    ap.add_argument("--band", type=float, default=sm.LADDER_STEP_FT,
                    help="ladder only: band width in feet (1 for the league, "
                         "2 suits a single team's smaller sample)")
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    league = shot_data.league_shots(args.season, args.refresh)
    if args.team or args.league:
        if args.chart not in TEAM_CAPABLE:
            raise SystemExit(f"--team/--league is not available for --chart {args.chart}")
        if args.team and args.league:
            raise SystemExit("Pass one of --team or --league, not both")
    if args.league:
        # The league is its own baseline, so any "vs league" metric is all zeros.
        if args.metric.endswith("-rel"):
            raise SystemExit("--league has no league to compare against; "
                             "use --metric pps")
        shots, name, slug = league, "NBA", "league"
    elif args.team:
        shots, name, slug = (shot_data.team_shots(season=args.season,
                                                  refresh=args.refresh),
                             "Chicago Bulls", "bulls")
    else:
        if args.player_id and args.player:
            pid, name = args.player_id, args.player
        elif args.player:
            pid, name = resolve_player(args.player)
        else:
            raise SystemExit("Pass --player NAME, or --team for the whole team")
        shots = shot_data.player_shots(pid, args.season, args.refresh)
        slug = name.lower().replace(" ", "-").replace(".", "")
    if shots.empty:
        raise SystemExit(f"No {args.season} shots for {name}")

    ctx = {
        "player": shots,
        "league": league,
        "name": name,
        "subtitle": args.subtitle or f"{args.season} Regular Season",
        "season": args.season,
        "metric": args.metric,
        "band": args.band,
    }
    if args.chart == "rings":
        if args.team:
            raise SystemExit("rings needs per-75 rates, which are player-scoped")
        ctx["poss"] = shot_data.player_possessions(pid, args.season)
        ctx["league_poss"] = shot_data.league_possessions(args.season)
        if args.focus:
            key = args.focus.strip().lower()
            if key not in FOCUS_ALIASES:
                raise SystemExit(f"--focus must be one of {sorted(set(FOCUS_ALIASES))}")
            ctx["focus"] = FOCUS_ALIASES[key]

    print(f"{name}: {len(shots)} FGA  ({args.chart})")
    out = Path(args.output) if args.output else _output_path(args, slug)
    CHARTS[args.chart](ctx, out, args.final)


if __name__ == "__main__":
    main()
