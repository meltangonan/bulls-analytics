#!/usr/bin/env python3
"""Build any shot chart in the family, for any player, from one entry point.

    venv/bin/python scripts/make_shot_chart.py --player "Matas Buzelis" --chart rings

Four charts, three questions:

    hotspot   WHERE he shoots, vs the league          (frequency only)
    hex       where AND how well, at full resolution  (size = volume, color = efficiency)
    rings     how often AND how well, by zone         (both, vs the league)

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


CHARTS = {"hotspot": render_hotspot, "hex": render_hex, "rings": render_rings}


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
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    if args.player_id and args.player:
        pid, name = args.player_id, args.player
    elif args.player:
        pid, name = resolve_player(args.player)
    else:
        raise SystemExit("Pass --player NAME (and optionally --player-id)")

    player = shot_data.player_shots(pid, args.season, args.refresh)
    if player.empty:
        raise SystemExit(f"No {args.season} shots for {name}")
    ctx = {
        "player": player,
        "league": shot_data.league_shots(args.season, args.refresh),
        "name": name,
        "subtitle": args.subtitle or f"{args.season} Regular Season",
        "season": args.season,
    }
    if args.chart == "rings":
        ctx["poss"] = shot_data.player_possessions(pid, args.season)
        ctx["league_poss"] = shot_data.league_possessions(args.season)
        if args.focus:
            key = args.focus.strip().lower()
            if key not in FOCUS_ALIASES:
                raise SystemExit(f"--focus must be one of {sorted(set(FOCUS_ALIASES))}")
            ctx["focus"] = FOCUS_ALIASES[key]

    print(f"{name}: {len(player)} FGA  ({args.chart})")
    slug = name.lower().replace(" ", "-").replace(".", "")
    tag = f"-{args.focus.strip().lower()}" if args.focus else ""
    out = Path(args.output or ROOT / "output" / "feed" / f"{args.chart}{tag}-{slug}.png")
    CHARTS[args.chart](ctx, out, args.final)


if __name__ == "__main__":
    main()
