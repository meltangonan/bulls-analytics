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
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb, to_rgba
from matplotlib.patches import FancyBboxPatch, Rectangle, RegularPolygon, Wedge
from matplotlib.transforms import Bbox

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.config import CURRENT_SEASON
from bulls.data import shots as shot_data
from bulls.graphics import house
from bulls.graphics.court import (
    ARC,
    BACKBOARD_HALF_WIDTH,
    BACKBOARD_Y,
    CORNER_X,
    COURT_HALF_WIDTH,
    FT_LINE_Y,
    FT_RADIUS,
    HASH_FROM_BASELINE_FT,
    HOOP_RADIUS,
    LANE_MARKS_FT,
    PAINT_HALF_WIDTH,
    draw_half_court,
    nba_to_basket_bottom_px,
    restricted_area_patch,
)
from bulls.graphics.house import helvetica
from bulls.visuals import visual_dir

# --- Palettes ---------------------------------------------------------------
HOT_BANDS = ["#F6CDD7", "#E67C96", "#CE1141", "#7E0C2B"]
HOT_LINE = "#5E0820"
COURT_WARM = "#C9A8B5"

HEX_COLORS = ("#2166AC", "#92C5DE", "#F1CC5B", "#E8763C", "#A80F2A")
HEX_CUTS = (-0.075, -0.025, 0.025, 0.075)
REL_CMAP = LinearSegmentedColormap.from_list("rel", [
    "#6E1113", "#B3312A", "#DE6B3C", "#F0BE45", "#9FC24C", "#4A9C3A", "#1F6B2F"])

DARK_BG, DARK_TEXT, DARK_DIM, DARK_LINE = "#14110F", "#F4EFE9", "#A79E95", "#6C645C"

# The account's black (DESIGN.md section 2), not the theme ink. A filled court
# carries its markings over twelve saturated fills, so the lines have to be the
# one neutral that reads on all of them rather than a colour chosen per theme.
ZONE12_COURT_INK = "#242424"


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
    px, py = nba_to_basket_bottom_px(x0, y0, s, cx, cy)
    z = np.sqrt(field.T)
    levels = np.sqrt(np.linspace(thr, fmax, len(fill_colors) + 1))
    levels[-1] += 1e-9
    ax.contourf(px, py, z, levels=levels, colors=fill_colors, alpha=alpha, zorder=2)
    ax.contour(px, py, z, levels=levels[1:-1], colors=line_color, linewidths=0.7,
               alpha=min(1.0, alpha + 0.08), zorder=3)


# ---------------------------------------------------------------------------
# hex — size = volume, color = FG% vs league
# ---------------------------------------------------------------------------
GRIDSIZE, MIN_ATT, SMOOTH_R, MIN_SMOOTH = 18, 3, 45.0, 20
HEX_SIZE_CAP_PERCENTILE = 97.5
HEX_RADIUS_SCALE = 0.96
HEX_MIN_RADIUS_FRACTION = 0.25
HEX_EDGE_WIDTH = 0.30
HEX_SHADOW_OFFSET = 0.6
HEX_SHADOW_ALPHA = 0.055
# The hex chart is a Canva asset, not a full post page. Keep the complete court
# width but trim the unused transparent space above the longest shots and below
# the legend. Values are in the 1080 x 1350 draft-coordinate system.
# The legend sits 20 px below the earlier near-tangent placement. Extend the
# crop by the same amount so the bottom method label keeps its breathing room.
HEX_CROP_BOTTOM = 325
HEX_CROP_TOP = 1220
HEX_LEGEND_DY = 110
HEX_VOLUME_MARKS = ((245, 7), (270, 15))
HEX_COLOR_CENTERS = (690, 718, 746, 774, 802)
HEX_BAND_NAMES = ("well below", "below", "approximately average", "above", "well above")


def _hex_color(diff: float) -> str:
    """One of five discrete Kirk-style bands around league-average FG%."""
    return HEX_COLORS[int(np.digitize(diff, HEX_CUTS))]


def _hex_radius_fraction(attempts: float, cap: float) -> float:
    """Radius fraction with a readable low-volume floor and outlier cap.

    Hex area, not diameter, is what the eye reads. Since area grows with radius
    squared, ``sqrt(attempts / cap)`` makes a cell with four times the attempts
    occupy four times the area through the middle of the scale. The 25% floor
    keeps qualified three- to seven-attempt cells visible; the cap prevents rim
    outliers from shrinking everything else.
    """
    if attempts <= 0 or cap <= 0:
        return 0.0
    return min(max((attempts / cap) ** 0.5, HEX_MIN_RADIUS_FRACTION), 1.0)


def _hex_base_radius() -> float:
    """Full-volume radius from the original, deliberately overlapping scale."""
    return ((sm.GRID_X[1] - sm.GRID_X[0]) / GRIDSIZE / np.sqrt(3)
            * HEX_RADIUS_SCALE)


def _within_hex_extent(shots: pd.DataFrame) -> pd.DataFrame:
    """Attempts whose coordinates fit the plotted 30-foot court window."""
    return shots[
        shots.loc_x.between(*sm.GRID_X)
        & shots.loc_y.between(*sm.GRID_Y)
    ]


def _hex_display_mask(attempts: pd.Series, show_thin_gray: bool) -> pd.Series:
    """Cells to draw: established locations, plus 1-2 shot gray cells on request."""
    return attempts.gt(0) if show_thin_gray else attempts.ge(MIN_ATT)


def prepare_hex_table(ctx) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the auditable cell table used by both rendering and data exports."""
    from scipy.spatial import cKDTree

    p = _within_hex_extent(ctx["player"])
    league = _within_hex_extent(ctx["league"])
    centres, attempts = _hexbin(p.loc_x, p.loc_y)
    subject_fg, subject_pool = _pooled(
        cKDTree(np.c_[p.loc_x, p.loc_y]), p.shot_made.to_numpy(float), centres)
    league_fg, league_pool = _pooled(
        cKDTree(np.c_[league.loc_x, league.loc_y]), league.shot_made.to_numpy(float), centres)

    table = pd.DataFrame({
        "hex_center_x": centres[:, 0],
        "hex_center_y": centres[:, 1],
        "exact_fga": attempts.astype(int),
        "nearby_subject_fga": subject_pool.astype(int),
        "nearby_subject_fg_pct": subject_fg * 100,
        "nearby_nba_fga": league_pool.astype(int),
        "nearby_nba_fg_pct": league_fg * 100,
        "subject_vs_nba_fg_pct_points": (subject_fg - league_fg) * 100,
    })
    show_thin_gray = bool(ctx.get("show_thin_gray", False))
    table["displayed"] = _hex_display_mask(table.exact_fga, show_thin_gray)
    table["low_volume_gray"] = show_thin_gray & table.exact_fga.between(1, MIN_ATT - 1)
    table["color_rated"] = (
        table.exact_fga.ge(MIN_ATT) & table.nearby_subject_fga.ge(MIN_SMOOTH)
    )

    established = table.exact_fga.ge(MIN_ATT)
    cap_override = ctx.get("hex_size_cap")
    cap = (float(cap_override) if cap_override is not None else
           float(np.percentile(table.loc[established, "exact_fga"],
                               HEX_SIZE_CAP_PERCENTILE))
           if established.any() else 1.0)
    table["size_cap_fga"] = cap
    table["radius_fraction"] = [
        _hex_radius_fraction(fga, cap) if displayed else 0.0
        for fga, displayed in zip(table.exact_fga, table.displayed)
    ]
    table["color_band"] = "gray: insufficient exact-cell or nearby volume"
    rated = table.color_rated
    table.loc[rated, "color_band"] = [
        HEX_BAND_NAMES[int(np.digitize(value / 100, HEX_CUTS))]
        for value in table.loc[rated, "subject_vs_nba_fg_pct_points"]
    ]
    return p, table


def render_hex(ctx, out: Path, final: bool):
    theme = house.get_theme("jersey")
    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.patch.set_alpha(0.0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    s = 1.84
    x0, y0 = draw_half_court(ax, house.CANVAS_WIDTH / 2, 830, s, theme.ink,
                             lw=1.2)

    p, table = prepare_hex_table(ctx)
    sparse_attempts = int(table.loc[
        table.exact_fga.between(1, MIN_ATT - 1), "exact_fga"].sum())
    show_thin_gray = bool(ctx.get("show_thin_gray", False))
    df = table[table.displayed].copy()

    hex_r = _hex_base_radius()
    # A very small number of exact rim-coordinate cells are extreme outliers.
    # Capping at the 97.5th percentile keeps those from shrinking the entire
    # map while allowing more of the high-volume tail to remain distinct.
    # Keep the established-cell scale unchanged when the gray 1-2 shot cells
    # are added; otherwise merely revealing them would resize every other mark.
    cap = float(table.size_cap_fga.iloc[0])
    # Boundary bins are centred on the sideline; only the part of the mark that
    # lies on the court should be visible. Larger cells go down first, then
    # smaller cells sit above them like the raised plates in the value ladder.
    court_clip = Rectangle((x0, y0), 500 * s, 1000 * s, transform=ax.transData)
    ordered = df.sort_values("exact_fga", ascending=False)
    total = max(len(ordered), 1)
    for index, row in enumerate(ordered.itertuples()):
        r = hex_r * s * row.radius_fraction
        color = ("#D8D2CA" if not row.color_rated else
                 _hex_color(row.subject_vs_nba_fg_pct_points / 100))
        px, py = nba_to_basket_bottom_px(
            x0, y0, s, row.hex_center_x, row.hex_center_y
        )
        z = 2.0 + 2.0 * index / total
        shadow = ax.add_patch(RegularPolygon(
            (px + HEX_SHADOW_OFFSET, py - HEX_SHADOW_OFFSET), numVertices=6,
            radius=r + 0.2, orientation=0, facecolor=theme.ink,
            edgecolor="none", linewidth=0.0, alpha=HEX_SHADOW_ALPHA, zorder=z))
        shadow.set_clip_path(court_clip)
        mark = ax.add_patch(RegularPolygon(
            (px, py), numVertices=6, radius=r, orientation=0,
            facecolor=color, edgecolor="#FFFFFF", linewidth=HEX_EDGE_WIDTH,
            zorder=z + 0.01))
        mark.set_clip_path(court_clip)

    _hex_legend(ax, theme)
    off_map = len(ctx["player"]) - len(p)
    sparse = sparse_attempts
    made = ctx["player"].shot_made.sum()
    efg = (made + 0.5 * ctx["player"].loc[ctx["player"].shot_type == "3PT",
                                          "shot_made"].sum()) / len(ctx["player"]) * 100
    out.parent.mkdir(parents=True, exist_ok=True)
    crop = Bbox.from_extents(
        0,
        HEX_CROP_BOTTOM / house.DRAFT_DPI,
        house.CANVAS_WIDTH / house.DRAFT_DPI,
        HEX_CROP_TOP / house.DRAFT_DPI,
    )
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True,
                bbox_inches=crop)
    plt.close(fig)
    print(f"Saved {out}")
    print("\nCANVA COPY")
    print(f"Subtitle: {ctx['season']} Regular Season")
    print("Key: Five FG% bands · Blue = below NBA · Yellow = average · Orange/red = above")
    print(f"Summary: {len(ctx['player']):,} FGA · "
          f"{made / len(ctx['player']) * 100:.1f}% FG · {efg:.1f}% eFG")
    if show_thin_gray:
        print(f"Method: Color pools shots within 4.5 ft; gray = under {MIN_ATT} "
              f"attempts in the exact cell or under {MIN_SMOOTH} "
              f"{ctx['name']} attempts nearby")
        print(f"Coverage: {len(p):,} of {len(ctx['player']):,} attempts drawn; "
              f"{sparse} attempts in 1-2 shot cells shown gray and {off_map} "
              "beyond the 30-ft court window omitted")
    else:
        print(f"Method: Color pools shots within 4.5 ft; gray = under "
              f"{MIN_SMOOTH} {ctx['name']} attempts nearby")
        shown = len(p) - sparse
        print(f"Coverage: {shown:,} of {len(ctx['player']):,} attempts drawn; "
              f"{sparse} in sub-{MIN_ATT}-attempt hexes and {off_map} beyond the "
              "30-ft court window omitted")
    print("Source: NBA.com/stats")


def _draw_zone_court(ax, center_x: float, center_y: float, s: float,
                     fills: dict[str, str], fill_alpha: float,
                     court_ink: str = ZONE12_COURT_INK, seam_alpha: float = 1.0,
                     lw: float = 1.2):
    """Paint one twelve-zone half court onto a supplied axes, and nothing else.

    Everything the zone family draws below its type lives here: the court, the
    twelve fills, the rim disc, the white seams and the two edges the crop needs.
    It takes a position and a scale rather than owning the figure, which is what
    lets one court fill a page and eleven of them tile a cover from identical
    geometry. Returns the coordinate mapper so a caller can place its own marks.

    ``lw`` scales every line together. The rim disc and the closing edges were
    hand-set at 1.4 and 1.2 against a full-page court; expressed as ratios of
    ``lw`` they hold their relationship when the court shrinks, instead of a
    mini court drowning under lines sized for one four times its width.
    """
    x0, y0 = draw_half_court(ax, center_x, center_y, s, court_ink, lw=lw)

    def to_px(cx, cy):
        return nba_to_basket_bottom_px(x0, y0, s, cx, cy)

    gx, gy, grid = _zone12_grid()
    gx_px, gy_px = to_px(gx, gy)
    for zone in sm.ZONE12_ORDER:
        _zone12_fill(
            ax, gx_px, gy_px, grid == zone,
            to_rgba(fills[zone], fill_alpha), 2.0,
        )

    from matplotlib.patches import Circle as _Circle
    ax.add_patch(_Circle(
        to_px(0, 0), sm.RA_R * s,
        facecolor=to_rgba(fills["Restricted Area"], fill_alpha),
        edgecolor=to_rgba(ZONE12_SEAM, seam_alpha), lw=lw * (1.4 / 1.2),
        zorder=2.5,
    ))
    _zone12_seams(ax, to_px, color=to_rgba(ZONE12_SEAM, seam_alpha),
                  lw=ZONE12_SEAM_WIDTH * lw / 1.2)
    for side in (-250, 250):
        ax.plot([to_px(side, 0)[0]] * 2,
                [to_px(side, 110)[1], to_px(side, ZONE12_TOP)[1]],
                color=court_ink, lw=lw, zorder=5)
    left, right = to_px(-250, ZONE12_TOP), to_px(250, ZONE12_TOP)
    ax.plot([left[0], right[0]], [left[1], right[1]],
            color=court_ink, lw=lw, zorder=5)
    return to_px


def _render_cover_zones(out: Path, final: bool, fills: dict[str, str],
                        fill_alpha: float):
    """Render a data-free twelve-zone cover treatment from supplied fills."""
    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.patch.set_alpha(0.0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    _draw_zone_court(ax, house.CANVAS_WIDTH / 2, ZONE12_COURT_Y, ZONE12_SCALE,
                     fills, fill_alpha, seam_alpha=0.72)

    out.parent.mkdir(parents=True, exist_ok=True)
    crop = Bbox.from_extents(0, ZONE12_CROP_BOTTOM / house.DRAFT_DPI,
                             house.CANVAS_WIDTH / house.DRAFT_DPI,
                             ZONE12_CROP_TOP / house.DRAFT_DPI)
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True,
                bbox_inches=crop)
    plt.close(fig)
    print(f"Saved {out}")


def render_blank_zones(out: Path, final: bool):
    """Render the twelve-zone court as a quiet, data-free cover silhouette."""
    _render_cover_zones(
        out, final, {zone: ZONE12_GREY for zone in sm.ZONE12_ORDER}, 0.58
    )


def render_preview_zones(out: Path, final: bool):
    """Render a solid illustrative palette preview with no analytical data."""
    colors = ZONE12_PALETTES[ZONE12_DEFAULT_PALETTE]
    # Fixed placement makes the teaser reproducible. These bands are purely
    # illustrative and do not encode DeRozan's actual results.
    band_by_zone = (4, 3, 1, 0, 4, 2, 1, 0, 1, 3, 0, 3)
    fills = {
        zone: colors[band]
        for zone, band in zip(sm.ZONE12_ORDER, band_by_zone, strict=True)
    }
    _render_cover_zones(out, final, fills, 1.0)


# Physical neighbors in the twelve-zone half court. Cover colors are decorative,
# but equal neighboring fills merge visually into one region, so the cover
# generator treats this as a small graph-coloring problem.
ZONE12_COVER_ADJACENCY = (
    ("Restricted Area", "In The Paint (Non-RA)"),
    ("In The Paint (Non-RA)", "Left Baseline"),
    ("In The Paint (Non-RA)", "Left Mid-Range"),
    ("In The Paint (Non-RA)", "Center Mid-Range"),
    ("In The Paint (Non-RA)", "Right Mid-Range"),
    ("In The Paint (Non-RA)", "Right Baseline"),
    ("Left Baseline", "Left Mid-Range"),
    ("Left Mid-Range", "Center Mid-Range"),
    ("Center Mid-Range", "Right Mid-Range"),
    ("Right Mid-Range", "Right Baseline"),
    ("Left Baseline", "Left Corner 3"),
    ("Left Mid-Range", "Left Wing 3"),
    ("Center Mid-Range", "Top of Key 3"),
    ("Right Mid-Range", "Right Wing 3"),
    ("Right Baseline", "Right Corner 3"),
    ("Left Corner 3", "Left Wing 3"),
    ("Left Wing 3", "Top of Key 3"),
    ("Top of Key 3", "Right Wing 3"),
    ("Right Wing 3", "Right Corner 3"),
)


def randomized_cover_fills(seed: int) -> dict[str, str]:
    """Shuffle a green-forward cover while separating neighboring shades."""
    rng = random.Random(seed)
    colors = list(ZONE12_PALETTES[ZONE12_DEFAULT_PALETTE])
    # Twelve zones cannot split evenly across five colors. Give the two green
    # bands one extra region apiece, then use each warm band twice.
    target_counts = dict(zip(colors, (2, 2, 2, 3, 3), strict=True))
    neighbors = {zone: set() for zone in sm.ZONE12_ORDER}
    for left, right in ZONE12_COVER_ADJACENCY:
        neighbors[left].add(right)
        neighbors[right].add(left)
    candidate_orders = {}
    for zone in sm.ZONE12_ORDER:
        order = colors.copy()
        rng.shuffle(order)
        candidate_orders[zone] = order

    assigned: dict[str, str] = {}
    assigned_counts = {color: 0 for color in colors}

    def place(index: int) -> bool:
        if index == len(sm.ZONE12_ORDER):
            return assigned_counts == target_counts
        zone = sm.ZONE12_ORDER[index]
        for color in candidate_orders[zone]:
            if assigned_counts[color] >= target_counts[color]:
                continue
            if any(assigned.get(neighbor) == color
                   for neighbor in neighbors[zone]):
                continue
            assigned[zone] = color
            assigned_counts[color] += 1
            if place(index + 1):
                return True
            assigned_counts[color] -= 1
            assigned.pop(zone)
        return False

    if not place(0):
        raise ValueError("could not separate adjacent cover-zone colors")
    return assigned


def render_randomized_cover_zones(out: Path, final: bool, seed: int):
    """Render a reproducible decorative cover with separated zone colors."""
    _render_cover_zones(out, final, randomized_cover_fills(seed), 1.0)


def render_solid_cover_zones(out: Path, final: bool, fill: str):
    """Render a reusable player-neutral cover court in one opaque color."""
    _render_cover_zones(
        out, final, {zone: fill for zone in sm.ZONE12_ORDER}, 1.0
    )


def _hex_legend(ax, theme):
    """One horizontal band: volume on the left, efficiency on the right."""
    dy = HEX_LEGEND_DY
    ax.text(260, 380 + dy, "VOLUME", ha="center", va="center",
            fontsize=10, color=theme.accent, fontproperties=helvetica("bold"))
    ax.text(218, 337 + dy, "LESS", ha="right", va="center", fontsize=9,
            color=theme.muted, fontproperties=helvetica("bold"))
    for x, radius in HEX_VOLUME_MARKS:
        ax.add_patch(RegularPolygon((x, 337 + dy), numVertices=6, radius=radius,
                                    orientation=0, facecolor=theme.ink,
                                    edgecolor="none", linewidth=0.0, zorder=9))
    ax.text(295, 337 + dy, "MORE", ha="left", va="center", fontsize=9,
            color=theme.muted, fontproperties=helvetica("bold"))

    xs = np.asarray(HEX_COLOR_CENTERS)
    ax.text(xs.mean(), 380 + dy, "FG% VS. NBA AVG", ha="center", va="center",
            fontsize=10, color=theme.accent, fontproperties=helvetica("bold"))
    for x, color in zip(xs, HEX_COLORS):
        ax.add_patch(RegularPolygon((x, 337 + dy), numVertices=6, radius=13,
                                    orientation=0, facecolor=color,
                                    edgecolor="none", linewidth=0.0, zorder=9))
    ax.text(xs[0] - 18, 337 + dy, "BELOW", ha="right", va="center",
            fontsize=9, color=theme.muted, fontproperties=helvetica("bold"))
    ax.text(xs[-1] + 18, 337 + dy, "ABOVE", ha="left", va="center",
            fontsize=9, color=theme.muted, fontproperties=helvetica("bold"))


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
    ax.add_patch(Rectangle((hx - PAINT_HALF_WIDTH * s, base),
                           2 * PAINT_HALF_WIDTH * s, 190 * s, facecolor="none",
                           edgecolor=COURT_INK, lw=2.0, zorder=6))
    for ft in LANE_MARKS_FT:
        y = base + ft * 10 * s
        for side, direction in ((-PAINT_HALF_WIDTH, -1), (PAINT_HALF_WIDTH, 1)):
            ax.plot([hx + side * s, hx + (side + direction * 8) * s], [y, y], **line)
    hash_y = base + HASH_FROM_BASELINE_FT * 10 * s
    for side, direction in ((-250, 1), (250, -1)):
        ax.plot([hx + side * s, hx + (side + direction * 18) * s],
                [hash_y, hash_y], **line)
    ax.add_patch(_Circle((hx, hy), HOOP_RADIUS * s, facecolor="none", edgecolor=COURT_INK,
                         lw=2.0, zorder=7))
    board_y = hy + BACKBOARD_Y * s
    ax.plot([hx - BACKBOARD_HALF_WIDTH * s, hx + BACKBOARD_HALF_WIDTH * s],
            [board_y] * 2, color=COURT_INK, lw=4.2, zorder=7,
            solid_capstyle="butt")
    ax.plot([hx, hx], [board_y, hy - HOOP_RADIUS * s], color=COURT_INK,
            lw=1.6, zorder=7)
    restricted_area_patch(ax, hx, hy, s, COURT_INK, 2.0, 6)
    ft_y = hy + FT_LINE_Y * s
    ax.add_patch(_Arc((hx, ft_y), 2 * FT_RADIUS * s, 2 * FT_RADIUS * s,
                      theta1=0, theta2=180,
                      color=COURT_INK, lw=2.0, zorder=6))
    ax.add_patch(_Arc((hx, ft_y), 2 * FT_RADIUS * s, 2 * FT_RADIUS * s,
                      theta1=180, theta2=360,
                      color=COURT_INK, lw=2.0, linestyle=(0, (5, 4)), zorder=6))
    corner_top = (ARC ** 2 - CORNER_X ** 2) ** 0.5
    for side in (-CORNER_X, CORNER_X):
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

    ``sector_index`` counts from NBA's left -- the negative ``loc_x`` side --
    while Wedge measures anticlockwise from the +x axis, so the index first has
    to be turned into a source angle.

    That source angle is then mirrored, for the same reason
    ``nba_to_basket_bottom_px`` mirrors a shot: this court is drawn with the
    basket at the bottom, which puts NBA Left on the viewer's right. A wedge
    that skipped the flip would sit opposite the fills every other chart in the
    family draws, so one player's LEFT CORNER would appear on two different
    sides depending on which chart he was rendered into. Mirroring maps an angle
    to ``180 - theta`` and reverses the interval, which is why the endpoints swap.

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
    return 180.0 - t2, 180.0 - t1


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

    Anchors carry the same basket-at-the-bottom mirror as ``_cell_angles``, and
    for the same reason: a number printed on the opposite side from its own
    wedge is worse than no number at all. Sector 0 is NBA Left, so it anchors on
    the viewer's right.
    """
    if _is_corner(cell):
        return hx + (1 if cell.sector == 0 else -1) * CORNER_X * s, hy + CORNER_Y * s
    if cell.n_sectors == 1:
        mid = np.radians(90.0)
    else:
        mid = np.radians((cell.sector + 0.5) * (180.0 / cell.n_sectors))
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
    # Which sideline the pocket is drawn against, not which NBA label it carries:
    # sector 0 is NBA Left and the mirrored court puts it on the viewer's right.
    on_viewer_right = cell.sector == 0
    rot = 0 if not corner else (-90 if on_viewer_right else 90)
    # Rotated, the stacking axis turns with the text: "above" and "below" become
    # sideways on the page, so the two lines stay stacked as the reader sees them.
    if not corner:
        top, under = (0.0, 9.0), (0.0, -13.0)
    elif on_viewer_right:
        top, under = (9.0, 0.0), (-13.0, 0.0)
    else:
        top, under = (-9.0, 0.0), (13.0, 0.0)

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
PLAYER_LADDER_MIN_FGA = 15

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
    if ctx.get("blank"):
        _render_blank_ladder(out, final, ctx.get("band", sm.LADDER_STEP_FT))
        return

    metric = LADDER_METRICS[ctx["metric"]]
    step = ctx.get("band", sm.LADDER_STEP_FT)
    edges = sm.ladder_edges(step)
    min_fga = ctx.get("min_fga", sm.MIN_RING_FGA)
    rings = sm.distance_ladder(ctx["player"], ctx["league"], step=step,
                               min_fga=min_fga)
    col = metric["column"]
    # Coverage is told the ladder's REAL outer edge, not the nominal maximum:
    # at 2 ft wide the last band stops at 30, so 30-31 ft becomes excluded and
    # the "% shown" line has to say so.
    cover = sm.ladder_coverage(ctx["player"], max_ft=float(edges[-1]))
    corner = sm.corner_split(ctx["player"], ctx["league"], min_fga=min_fga)
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
        key += (f"  ·  GREY = UNDER {min_fga} ATTEMPTS, "
                f"TOO FEW TO RATE ({grey} BANDS)")
    _fit_note(ax, 90, key)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True)
    plt.close(fig)
    print(f"Saved {out}")


def _render_blank_ladder(out: Path, final: bool, step: float):
    """Render the ladder geometry as a neutral, data-free cover image."""
    from types import SimpleNamespace

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
    clip = Rectangle((hx - 250 * s, base), 500 * s, 1000 * s, transform=ax.transData)
    cx = sm.CORNER_LINE_X
    inner_clip = Rectangle((hx - cx * s, base), 2 * cx * s, 1000 * s,
                           transform=ax.transData)
    edges = sm.ladder_edges(step)
    rings = [SimpleNamespace(lo=lo, hi=hi, three=bool(lo >= sm.LADDER_TWO_MAX_FT))
             for lo, hi in zip(edges[:-1], edges[1:])]
    for i, ring in enumerate(reversed(rings)):
        _ladder_ring(ax, (hx, hy), ring, s, LADDER_THIN,
                     clip if ring.three else inner_clip, shadow=i > 0)

    # The corner pocket is part of the ladder's geometry even without data.
    for side in (-1, 1):
        strip = Rectangle((hx + side * cx * s if side > 0 else hx - 250 * s, base),
                          (250 - cx) * s, 1000 * s, transform=ax.transData)
        pocket = ax.add_patch(Wedge((hx, hy), sm.LADDER_TWO_MAX_FT * 10 * s,
                                    0, 360, facecolor=LADDER_THIN,
                                    edgecolor="none", zorder=3))
        pocket.set_clip_path(strip)

    _ladder_court(ax, hx, hy, s, clip)
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
def _ladder_court(ax, hx, hy, s, clip):
    """Court markings, drawn light because every ring sits under them."""
    from matplotlib.patches import Arc as _Arc, Circle as _Circle
    ink = LADDER_COURT_INK
    line = dict(color=ink, lw=LADDER_COURT_LW, zorder=6, alpha=LADDER_COURT_ALPHA)
    arcs = dict(color=ink, lw=LADDER_COURT_LW, alpha=LADDER_COURT_ALPHA, zorder=6)
    base = hy + sm.BASELINE_Y * s

    ax.plot([hx - 250 * s, hx + 250 * s], [base, base], **line)
    ax.add_patch(Rectangle((hx - PAINT_HALF_WIDTH * s, base),
                           2 * PAINT_HALF_WIDTH * s, 190 * s, facecolor="none",
                           edgecolor=ink, lw=LADDER_COURT_LW,
                           alpha=LADDER_COURT_ALPHA, zorder=6))

    # Lane marks: short ticks stepping out from each paint edge.
    for ft in LANE_MARKS_FT:
        y = base + ft * 10 * s
        for side, direction in ((-PAINT_HALF_WIDTH, -1), (PAINT_HALF_WIDTH, 1)):
            ax.plot([hx + side * s, hx + (side + direction * 8) * s], [y, y], **line)

    # Sideline hash marks, which the reference keeps and which quietly tell the
    # reader how far out the widest rings actually reach.
    y = base + HASH_FROM_BASELINE_FT * 10 * s
    for side, direction in ((-250, 1), (250, -1)):
        ax.plot([hx + side * s, hx + (side + direction * 18) * s], [y, y], **line)

    # Restricted area: 4 ft from the centre of the rim, the arc a defender
    # cannot draw a charge inside. It belongs on this chart more than most --
    # the rim ring's 1.51 points per shot is very largely taken inside it.
    restricted_area_patch(ax, hx, hy, s, ink, LADDER_COURT_LW, 6,
                          LADDER_COURT_ALPHA)

    # Backboard with depth: a thick plate over a soft drop shadow, then the rim
    # and its connector drawn on top.
    bb_y = hy + BACKBOARD_Y * s
    for dy, lw, alpha, color in ((-2.4, 5.0, 0.30, "#150F0A"),
                                 (0.0, 4.2, 0.95, ink)):
        ax.plot([hx - BACKBOARD_HALF_WIDTH * s, hx + BACKBOARD_HALF_WIDTH * s],
                [bb_y + dy] * 2, color=color, lw=lw,
                alpha=alpha, solid_capstyle="butt", zorder=7)
    ax.plot([hx, hx], [bb_y, hy - HOOP_RADIUS * s], color=ink, lw=1.6, alpha=0.9,
            zorder=7)
    # The rim goes lightest of all. It is the one marking that shares its exact
    # position with a number -- the innermost ring's value sits inside the hoop
    # -- so it has to locate the basket without competing with the digits.
    ax.add_patch(_Circle((hx, hy), HOOP_RADIUS * s, facecolor="none", edgecolor=ink,
                         lw=1.5, alpha=0.42, zorder=4))

    ft_y = hy + FT_LINE_Y * s
    for t1, t2, dash in ((0, 180, "solid"), (180, 360, (0, (5, 4)))):
        ax.add_patch(_Arc((hx, ft_y), 2 * FT_RADIUS * s, 2 * FT_RADIUS * s,
                          theta1=t1, theta2=t2,
                          linestyle=dash, **arcs))
    corner_top = (ARC ** 2 - CORNER_X ** 2) ** 0.5
    for side in (-CORNER_X, CORNER_X):
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


# ---------------------------------------------------------------------------
# zones — the twelve named regions, volume and accuracy both vs league
# ---------------------------------------------------------------------------
# The rings chart's two questions asked of twelve regions instead of four, in the
# hex chart's colours so the two posts read as one system. Fill answers "does he
# score better here than the league"; the printed pair answers that and "does he
# come here more often", weighted equally.
#
# The zone chart keeps the hex chart's five-band grammar but uses tighter outer
# cuts. A five-point gap inside one named region is already material: about 10
# points per 100 attempts for a two and 15 for a three. The hex chart stays at
# +/-7.5 because its smoothed local cells are a different, noisier mark.
ZONE12_CUTS = (-0.05, -0.025, 0.025, 0.05)
ZONE12_GREY = "#D8D2CA"          # below the colour floor, including zero attempts
ZONE12_SEAM = "#FAF8F5"          # divider between neighbouring fills
ZONE12_BULLS_RED = house.RED
ZONE12_BULLS_RED_LIGHT = "#E67C96"
# Every figure sits on a cream pill, so there is one ink and one green-red pair
# rather than one per fill. That is the real win of the pill: an earlier draft
# recoloured type per zone to survive the band underneath it, and the same
# figure changing colour from zone to zone read as though the colour meant
# something. Here colour means direction, and nothing else.
ZONE12_UP_ON_LIGHT, ZONE12_DOWN_ON_LIGHT = "#12693A", "#93150B"
ZONE12_NEUTRAL_GAP = "#6E6963"   # a gap too small to call a direction

# Two fill palettes, using the zone chart's five bands and cuts.
#
#   hex     blue -> yellow -> red, inherited from the hex carousel. Red is the
#           high end because red is the Bulls' colour, so "more red" reads as
#           "more Bulls", and nothing on the scale claims good or bad.
#   rdylgn  red -> yellow -> green. Instantly legible, because green-is-good
#           needs no legend at all -- at the cost of passing judgement in the
#           colour, and of clashing with a Bulls-red page.
ZONE12_PALETTES = {
    "hex": HEX_COLORS,
    "rdylgn": ("#A8322A", "#DC7B62", "#F1CC5B", "#8CBF63", "#357C41"),
}
ZONE12_DEFAULT_PALETTE = "rdylgn"



def _zone12_band_color(rel: float, palette: str) -> str:
    """One of five discrete bands around league-average FG%, in either scale."""
    colors = ZONE12_PALETTES[palette]
    if rel <= ZONE12_CUTS[0]:
        return colors[0]
    if rel < ZONE12_CUTS[1]:
        return colors[1]
    if rel <= ZONE12_CUTS[2]:
        return colors[2]
    if rel < ZONE12_CUTS[3]:
        return colors[3]
    return colors[4]
ZONE12_TRACE_STEP = 1.0          # court units per grid sample when tracing fills
ZONE12_TRACE_BLUR = 0.8          # softens the stair-stepping on radial dividers
# How deep the court is drawn: 33.5 ft from the hoop, a few feet past the
# deepest shots anyone takes on purpose. Drawing the whole half court to the
# centre line was tried and pulled back -- it is honest, and it spent the top
# third of the image on empty floor no shot ever reaches. This is the compromise
# the pills actually need: enough room above the arc for a label with air around
# it, and no more. Nothing is rescaled to make it fit; the court stays true.
ZONE12_TOP = 335.0

# Short names, kept for the printed table and the data exports. They are no
# longer drawn: a court is a diagram a reader already knows, so "TOP OF KEY" over
# the top of the key spends a line of type restating the picture. Dropping them
# is what let every block shrink to two lines.
ZONE12_SHORT = {
    "Restricted Area": "RIM",
    "In The Paint (Non-RA)": "PAINT",
    "Left Baseline": "LEFT BASELINE",
    "Left Mid-Range": "LEFT MID",
    "Center Mid-Range": "CENTER MID",
    "Right Mid-Range": "RIGHT MID",
    "Right Baseline": "RIGHT BASELINE",
    "Left Corner 3": "LEFT CORNER",
    "Left Wing 3": "LEFT WING",
    "Top of Key 3": "TOP OF KEY",
    "Right Wing 3": "RIGHT WING",
    "Right Corner 3": "RIGHT CORNER",
}

# Where each zone's block sits, in court coordinates with the hoop at the origin
# and y running away from the baseline. EVERY block now sits inside the zone it
# reports. It used to be that three did not -- the rim and the two corner strips
# dropped below the baseline -- and that was only legible because each block was
# captioned with its zone name. Removing the names removed the attribution, so a
# figure parked off-court became a figure belonging to nothing. Position is now
# the only thing saying which zone a number describes, which means position has
# to be right.
ZONE12_ANCHORS = {
    # Dead centre of the restricted area. The pill fits inside the 8 ft disc
    # only because its corners are rounded, which pulls its farthest point in
    # well short of the rectangle's diagonal; _zone12_rim_fit checks that on
    # every render and shrinks the type if a longer figure would burst it.
    "Restricted Area":       (0, 0),
    "In The Paint (Non-RA)": (0, 80),
    # Twelve pills on one court is a packing problem, not a placement one, and
    # the binding constraints are the arc and the paint rather than the zone
    # centres. A pill centred in the mid-range wing overhangs the arc, because
    # the zone narrows toward the top while the pill does not; these sit low and
    # inboard of centre so all four corners stay inside their own region.
    # Change one and check its neighbours, the arc, and the paint.
    "Left Corner 3":         (-235, 46),
    "Right Corner 3":        (235, 46),
    # Pulled slightly inward so the optional large four-line card keeps a real
    # gap from the adjacent corner card on every carousel slide.
    "Left Baseline":         (-140, -8),
    "Right Baseline":        (140, -8),
    "Left Mid-Range":        (-133, 120),
    "Right Mid-Range":       (133, 120),
    "Center Mid-Range":      (0, 196),
    # Clear of the arc by about 2 ft at the pill's INNER bottom corner, which is
    # the point that reaches the line first -- measuring from the pill's centre
    # put the corner on the arc while the centre looked fine.
    "Left Wing 3":           (-169, 245),
    "Right Wing 3":          (169, 245),
    "Top of Key 3":          (0, 285),
}




def _zone12_grid():
    """Sample grid over the drawn court, plus its zone classification."""
    step = ZONE12_TRACE_STEP
    xs = np.arange(-250.0, 250.0 + step, step)
    ys = np.arange(sm.BASELINE_Y, ZONE12_TOP + step, step)
    gx, gy = np.meshgrid(xs, ys)
    return gx, gy, sm.zone_of(gx, gy)


def _zone12_fill(ax, gx_px, gy_px, mask, color, zorder):
    """Fill one zone by tracing its mask.

    The regions are intersections of discs, rays, half-planes and the arc, and
    assembling twelve exact paths by hand is where a chart starts counting one
    set of regions while drawing another. Tracing the classifier itself makes
    that impossible by construction: the drawn boundary IS the counted boundary.
    The cost is a softened edge -- at this grid step and blur the traced line
    stays within about an inch of true, well under a pixel at export size.
    """
    from scipy.ndimage import gaussian_filter

    field = mask.astype(float)
    if field.max() == 0:
        return
    smooth = gaussian_filter(field, sigma=ZONE12_TRACE_BLUR / ZONE12_TRACE_STEP,
                             mode="nearest")
    filled = ax.contourf(gx_px, gy_px, smooth, levels=[0.5, 1.5], colors=[color],
                         zorder=zorder, antialiased=True)


# --- zonegrid: one tenure, one page ----------------------------------------
# Eleven courts on a 1080 x 1350 page. Three columns is the only arrangement
# that works in portrait: four makes each court 250 px wide, at which point the
# corner threes are three pixels across and the chart stops being readable as a
# court; two runs to six rows and off the bottom.
ZONEGRID_COLS = 3
# Scale is solved, not chosen. Three courts plus two gaps have to fit 1080 px
# across AND four rows plus their labels have to fit 1350 px down, and the court
# is 1.29 times wider than deep, so the two constraints fight. The vertical one
# binds: at 0.63 the bottom row's attempt count fell 2.7 units off the page when
# the season-to-count gap was widened by seven. Scale is where that space is
# taken back, because six-tenths of a percent off every court is invisible while
# a tighter label gap is exactly what was being fixed. It leaves a 55 px side
# margin, which is why the grid does not look width-constrained even though the
# height is fully spent. `tests/test_hinrich_bulls_zone_charts.py` re-solves both
# constraints, since an over-tall grid crops silently rather than failing.
ZONEGRID_SCALE = 0.615
ZONEGRID_COL_GAP = 24.0
ZONEGRID_TOP = 1310.0            # top edge of the first row's court
ZONEGRID_ROW_GAP = 32.0          # between one row's attempt count and the next court
ZONEGRID_LABEL_GAP = 10.0        # between a court's baseline and its season label
ZONEGRID_LABEL_SIZE = 13.0
ZONEGRID_COUNT_SIZE = 9.0
# The gap from the season to its attempt count is set against the LABEL's line
# height, not the count's. At 150 dpi one point is 2.08 canvas units, so the
# 13 pt season name stands about 27 units tall and a 16-unit gap put the count
# inside that line's own body -- legible, but reading as one crowded block
# rather than a heading with a figure under it.
ZONEGRID_COUNT_GAP = 23.0
# Court units the drawn court spans, baseline to the cropped top. draw_half_court
# centres on a 280-unit court, so the drawn extent is not the centring extent and
# using one for the other silently clips the top row.
ZONEGRID_COURT_UNITS = ZONE12_TOP - sm.BASELINE_Y
ZONEGRID_CENTRE_OFFSET = (280.0 - sm.BASELINE_Y) / 2.0


def render_zonegrid(ctx, out: Path, final: bool):
    """Every season of a tenure as one page of bare, comparable courts.

    The season charts answer "how did he shoot in 2006-07". This answers a
    question none of them can: what changed. Stripping the pills is what makes
    that possible -- eleven courts carrying twelve figures each is 132 numbers,
    which is a table pretending to be a picture. With only the fills left, the
    reader tracks one region down the page and sees its colour move.

    Each court is rated against its OWN season's league, so a zone going from
    yellow to green means he improved relative to the players he was actually
    playing against, not relative to a league average borrowed from another era.
    """
    by_season = ctx["by_season"]
    palette = ctx.get("palette") or ZONE12_DEFAULT_PALETTE
    min_fga = int(ctx.get("min_fga") or sm.MIN_ZONE12_FGA_PLAYER)
    court_ink = ctx.get("court_ink") or "#242424"
    theme = house.get_theme("jersey")

    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.patch.set_alpha(0.0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    s = ZONEGRID_SCALE
    court_h = ZONEGRID_COURT_UNITS * s
    court_w = 2 * COURT_HALF_WIDTH * s
    label_block = (ZONEGRID_LABEL_GAP + ZONEGRID_LABEL_SIZE * 2.08
                   + ZONEGRID_COUNT_GAP)
    cell_h = court_h + label_block + ZONEGRID_ROW_GAP
    col_pitch = court_w + ZONEGRID_COL_GAP
    seasons = list(by_season)
    rows = -(-len(seasons) // ZONEGRID_COLS)

    for i, season in enumerate(seasons):
        row, col = divmod(i, ZONEGRID_COLS)
        # A short final row centres rather than hanging left: an orphan court
        # under the left column reads as a missing season, which is a claim.
        in_row = min(ZONEGRID_COLS, len(seasons) - row * ZONEGRID_COLS)
        span = (in_row - 1) * col_pitch
        cx = house.CANVAS_WIDTH / 2 - span / 2 + col * col_pitch
        baseline_y = ZONEGRID_TOP - row * cell_h - court_h
        zones = sm.zone12_split(by_season[season]["subject"],
                                by_season[season]["league"], min_fga=min_fga)
        _draw_zone_court(ax, cx, baseline_y + ZONEGRID_CENTRE_OFFSET * s, s,
                         _zone12_fills(zones, palette), 1.0,
                         court_ink=court_ink, lw=0.7)
        fga = len(by_season[season]["subject"])
        ax.text(cx, baseline_y - ZONEGRID_LABEL_GAP - ZONEGRID_LABEL_SIZE * 2.08,
                season, ha="center", va="baseline", fontsize=ZONEGRID_LABEL_SIZE,
                color=theme.ink, fontproperties=helvetica("bold"))
        ax.text(cx, baseline_y - ZONEGRID_LABEL_GAP - ZONEGRID_LABEL_SIZE * 2.08
                - ZONEGRID_COUNT_GAP,
                f"{fga:,} FGA", ha="center", va="baseline",
                fontsize=ZONEGRID_COUNT_SIZE, color=theme.muted,
                fontproperties=helvetica("bold"))

    bottom = ZONEGRID_TOP - (rows - 1) * cell_h - court_h - label_block
    out.parent.mkdir(parents=True, exist_ok=True)
    crop = Bbox.from_extents(0, (bottom - 20) / house.DRAFT_DPI,
                             house.CANVAS_WIDTH / house.DRAFT_DPI,
                             (ZONEGRID_TOP + 18) / house.DRAFT_DPI)
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True,
                bbox_inches=crop)
    plt.close(fig)
    print(f"Saved {out}")

    scale_words = ("Red below, yellow average, green above" if palette == "rdylgn"
                   else "Blue below, yellow average, orange/red above")
    print("\nCANVA COPY")
    print(f"Key: Colour = FG% vs the NBA in that zone, that season · {scale_words}")
    print(f"Grey: fewer than {min_fga} attempts — too few to rate")


def _zone12_fills(zones, palette: str) -> dict[str, str]:
    """Zone -> fill colour, greying every zone too thin to make a claim.

    The floor does not decide whether a zone is drawn, only whether it earns an
    efficiency colour. A zone the sample cannot stand behind is still part of the
    court and still gets painted -- in neutral grey, which says "no claim" rather
    than the false "league average" a mid-band colour would say.
    """
    return {
        z.zone: (_zone12_band_color(z.fg_rel / 100, palette)
                 if z.rated else ZONE12_GREY)
        for z in zones.itertuples()
    }


def render_zones(ctx, out: Path, final: bool):
    min_fga = int(ctx.get("min_fga") or sm.MIN_ZONE12_FGA_PLAYER)
    palette = ctx.get("palette") or ZONE12_DEFAULT_PALETTE
    pill = str(ctx.get("pill") or "full")
    show_summary = bool(ctx.get("summary_metrics"))
    show_details = bool(ctx.get("show_details", True))
    court_ink = ctx.get("court_ink") or house.get_theme("jersey").ink
    # The floor still applies. It no longer decides whether a zone is drawn at
    # all -- it decides whether the zone earns an efficiency colour.
    zones = sm.zone12_split(ctx["player"], ctx["league"], min_fga=min_fga)
    excluded = int(zones.subject_excluded_fga.iloc[0])
    for z in zones.itertuples():
        rate = f"{z.fg * 100:5.1f}% FG ({z.fg_rel:+5.1f})" if z.fga else "     no attempts"
        print(f"  {ZONE12_SHORT[z.zone]:<15}{z.fga:>5} FGA  {rate}   "
              f"{z.fga_share_pct:5.1f}% share (LA {z.lg_fga_share_pct:4.1f}%)"
              f"{'' if z.rated else '   too thin to colour'}")

    theme = house.get_theme("jersey")
    fig = plt.figure(figsize=(house.CANVAS_WIDTH / house.DRAFT_DPI,
                              house.CANVAS_HEIGHT / house.DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, house.CANVAS_WIDTH); ax.set_ylim(0, house.CANVAS_HEIGHT)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.patch.set_alpha(0.0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    # Colour is the claim, so only a rated zone earns it. A thin zone stays
    # fully legible through its four-line pill but uses neutral grey ground.
    fills = _zone12_fills(zones, palette)
    to_px = _draw_zone_court(ax, house.CANVAS_WIDTH / 2, ZONE12_COURT_Y,
                             ZONE12_SCALE, fills, 1.0, court_ink=court_ink)

    if show_details:
        for z in zones.itertuples():
            _zone12_block(ax, to_px, z, fills[z.zone], theme, pill)
        _zone12_legend(
            ax, theme, palette, min_fga,
            show_thin=bool(ctx.get("show_thin_legend", True)),
        )
        if show_summary:
            _zone12_summary_cards(
                ax,
                ctx["player"],
                ctx["league"],
                theme,
                ppg=ctx.get("summary_ppg"),
            )
    out.parent.mkdir(parents=True, exist_ok=True)
    bottom = ZONE12_CROP_BOTTOM if show_details else ZONE12_BARE_CROP_BOTTOM
    crop = Bbox.from_extents(0, bottom / house.DRAFT_DPI,
                             house.CANVAS_WIDTH / house.DRAFT_DPI,
                             ZONE12_CROP_TOP / house.DRAFT_DPI)
    fig.savefig(out, dpi=house.export_dpi(final), transparent=True,
                bbox_inches=crop)
    plt.close(fig)
    print(f"Saved {out}")

    thin = zones[~zones.rated]
    total = len(ctx["player"])
    made = int(ctx["player"].shot_made.sum())
    # The chart carries the colour scale and nothing else, so everything the
    # legend used to explain has to be typed in Canva. It is all here.
    scale_words = ("Red below, yellow average, green above" if palette == "rdylgn"
                   else "Blue below, yellow average, orange/red above")
    print("\nCANVA COPY")
    print(f"Subtitle: {ctx['season']} Regular Season")
    print(f"Key: Colour = FG% vs the NBA in that zone · {scale_words}")
    print("Reading it: vs LA = the percentage-point gap to league average — "
          "FG% on the first pair, share of FGA on the second")
    print("Grey FG gap: inside the chart's ±2.5-point average band")
    if show_summary:
        overall = _zone12_overall_metrics(ctx["player"])
        summary_parts = []
        if ctx.get("summary_ppg") is not None:
            summary_parts.append(f"{float(ctx['summary_ppg']):.1f} PPG")
        summary_parts.extend((
            f"{total:,} FGA",
            f"{overall['efg_pct']:.1f}% eFG",
            _zone12_three_label(overall),
        ))
        print("Summary: " + " · ".join(summary_parts))
    else:
        print(f"Summary: {total:,} FGA · {made / total * 100:.1f}% FG · "
              "shot diet shown as each zone's share of all FGA")
    if len(thin):
        print(f"Method: Grey zones are under {min_fga} attempts, too few to rate "
              "the shooting percentage; their figures are shown but not coloured")
        print("Thin zones: " + ", ".join(
            f"{ZONE12_SHORT[z.zone]} ({z.fga})" for z in thin.itertuples()))
    if excluded:
        print(f"Coverage: {excluded} backcourt FGA excluded from the half-court zones")
    print("Source: NBA.com/stats")


ZONE12_SCALE = 1.84
ZONE12_COURT_Y = 771
ZONE12_CROP_BOTTOM = 205
ZONE12_CROP_TOP = 1180
# A chart with its pills, legend and summary cards suppressed stops using the
# space they occupied, and the crop has to follow or the asset ships with a
# quarter of its height empty. The floor of a detail chart is its legend; the
# floor of a bare one is the baseline of the court itself, plus a hairline so
# the boundary is not the outermost pixel.
ZONE12_BARE_CROP_BOTTOM = 450


ZONE12_SEAM_WIDTH = 1.2          # the same weight as the court markings


def _zone12_seam_segments() -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Every zone divider that the court's own black lines do not already draw.

    Solved from geometry rather than traced from the classified grid. Tracing
    ran each zone's mask through a blur and a contour, which is fine for a fill
    and wrong for a line: the blur pulled boundaries off true by a pixel or two,
    left white stubs hanging in the middle of a zone where a contour closed on
    itself, and drew a second faint edge alongside every black court line it ran
    beside. Every divider here is a straight segment with exact endpoints.

    Most boundaries need nothing. The arc, the corner lines, the paint edges and
    the free-throw line are all painted on a real court and already drawn in
    black, so a white seam beside them is a duplicate. What is left is the set of
    rays the floor does not paint, plus the corner break.
    """
    segments = []

    # Mid-range dividers: from where the ray leaves the paint out to the arc.
    # The baseline cuts end exactly on the corner break, because that is the
    # point the angle was derived from -- corner line, arc and divider meet.
    for degrees in sm.MID_SECTOR_CUTS:
        theta = np.radians(degrees)
        cos, sin = np.cos(theta), np.sin(theta)
        leaves_paint = min(sm.PAINT_HALF / abs(cos) if abs(cos) > 1e-9 else np.inf,
                           sm.FT_Y / sin if sin > 1e-9 else np.inf)
        meets_edge = min(sm.ARC_R,
                         sm.ZONE12_CORNER_X / abs(cos) if abs(cos) > 1e-9 else np.inf)
        if meets_edge > leaves_paint:
            segments.append(((leaves_paint * cos, leaves_paint * sin),
                             (meets_edge * cos, meets_edge * sin)))

    # Above-the-break dividers: literally the same two rays continuing past the
    # arc, taken from the same constant so they cannot drift apart.
    for degrees in sm.ATB_CUTS:
        theta = np.radians(degrees)
        cos, sin = np.cos(theta), np.sin(theta)
        far = min(ZONE12_TOP / sin,
                  COURT_HALF_WIDTH / abs(cos) if abs(cos) > 1e-9 else np.inf)
        segments.append(((sm.ARC_R * cos, sm.ARC_R * sin), (far * cos, far * sin)))

    # The corner break itself: where a corner three becomes a wing three, along
    # the strip between the corner line and the sideline.
    for side in (-1.0, 1.0):
        segments.append(((side * sm.ZONE12_CORNER_X, sm.CORNER_Y),
                         (side * COURT_HALF_WIDTH, sm.CORNER_Y)))
    return segments


def _zone12_seams(ax, to_px, color=ZONE12_SEAM, lw: float | None = None):
    """Draw the dividers, over the fills and under the court's black lines."""
    for (x1, y1), (x2, y2) in _zone12_seam_segments():
        p1, p2 = to_px(x1, y1), to_px(x2, y2)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color,
                lw=ZONE12_SEAM_WIDTH if lw is None else lw,
                zorder=3, solid_capstyle="butt")


# Rings-chart typography, unchanged: figure at 13, its gap to league average at
# 10.5 underneath. Both figures take the same size there and here, because sizing
# one larger would rank it above the other and the pair is meant to be read
# together.
ZONE12_FIGURE_SIZE = 8.0
ZONE12_DELTA_SIZE = 6.5
ZONE12_LARGE_FIGURE_SIZE = 10.0
ZONE12_LARGE_DELTA_SIZE = 7.5
# Line spacing is in canvas units and type is in points, and at this canvas's
# 150 dpi one point is 2.08 units. A 10 pt line therefore stands about 21 units
# tall, so any gap smaller than that guarantees the overlap the earlier drafts
# had: the gaps were set to 16 and 21 by eye against sizes of 11 and 13, which
# was always less than one line. These are measured against the line height, not
# guessed, and the two are deliberately unequal -- a gap belongs to the figure
# above it, so it sits nearer that figure than the next pair does.
ZONE12_PAIR_GAP = 15.0           # figure to its comparison/reference line
ZONE12_BLOCK_GAP = 23.0          # gap to the next figure
ZONE12_PILL_PAD_X = 7.0
ZONE12_PILL_PAD_Y = 5.0
ZONE12_PILL_INK = "#1F1D1A"      # the rings chart's pill text
ZONE12_PILL_ROUND = 10.0
# A pill on a zone the chart cannot rate keeps every figure but loses its
# weight: muted type on a faded card. The reader still gets the numbers and the
# comparison, and the pill still says at a glance that this one is not evidence
# the way its neighbours are.
ZONE12_THIN_PILL_ALPHA = 0.72
ZONE12_THIN_INK = "#6B6660"

# A shooting gap only earns a colour when it clears the fill scale's own +/-2.5
# point neutral band. If the zone is painted "about average", its gap is grey
# too, and colour never contradicts colour. The league shot share is a neutral
# reference value is converted to the same signed comparison grammar as FG%.
ZONE12_FG_NEUTRAL_POINTS = 2.5


def _zone12_rows(
    z, compact: bool = False
) -> tuple[tuple[str, str, bool, float], ...]:
    """The two (figure, reference, reference_is_directional, value) pairs.

    Shooting leads because the fill IS shooting: a zone's colour is its FG%
    against the league, so the first line of the pill has to be the figure that
    colour is about. Leading with shot share made the reader hunt past it for
    the number the region was already shouting. Shot share follows at the same
    size because it answers the independent question: how much of his shot diet
    came from here?

    The makes and attempts sit in front of the percentage rather than behind a
    floor. "11/32 FG (34.4%)" lets a reader see how much to trust the 34.4%,
    which is what makes a grey zone informative instead of something they have
    to take on faith -- the count explains why it did not earn a colour.

    ``compact`` drops to the counts line alone, for a simpler chart that gives up
    the shot-diet comparison.
    """
    shooting = (f"{z.fgm}/{z.fga} FG ({z.fg * 100:.1f}%)",
                f"{_signed(z.fg_rel, 1)} vs LA",
                abs(z.fg_rel) >= ZONE12_FG_NEUTRAL_POINTS, z.fg_rel)
    if compact:
        return (shooting,)
    share_rel = z.fga_share_pct - z.lg_fga_share_pct
    return (
        shooting,
        (f"{z.fga_share_pct:.1f}% of FGA",
         f"{_signed(share_rel, 1)} vs LA",
         round(share_rel, 1) != 0.0, share_rel),
    )


MINUS_SIGN = "−"


def _signed(value: float, decimals: int) -> str:
    """A gap with a true minus sign, and no sign at all when it rounds to zero.

    Two things a format string cannot do. "-" is a hyphen: beside figures it sits
    too high and too short, and next to a full-width "+" the pair reads as
    misaligned. And "+.0f" renders a gap of -0.4 as "-0%", a direction the
    printed number itself contradicts -- the sign has to follow the value the
    reader can see, which means deciding it after rounding rather than before.
    """
    rounded = round(value, decimals)
    body = f"{abs(rounded):.{decimals}f}"
    if rounded > 0:
        return f"+{body}"
    if rounded < 0:
        return f"{MINUS_SIGN}{body}"
    return body


def _zone12_delta_ink(value, meaningful: bool = True) -> str:
    """Green above, red below, grey when the gap is inside its own noise.

    A gap of +0.2 points printed in green claims a direction the number cannot
    support, and the reader has no way to know which greens to believe. Grey is
    the chart declining to make the claim, and it is the most common colour on a
    league-average team, which is itself the finding.
    """
    if not meaningful:
        return ZONE12_NEUTRAL_GAP
    return ZONE12_UP_ON_LIGHT if value >= 0 else ZONE12_DOWN_ON_LIGHT


def _zone12_block(ax, to_px, z, fill: str, theme, pill: str = "full"):
    """One cream pill of figures, floating over the zone it describes.

    A pill rather than type straight on the fill, for two reasons that both came
    out of the draft before this one. Type on the fill had to be recoloured per
    zone -- cream on dark bands, ink on pale ones -- and the same figure changing
    colour zone to zone read as if the colour meant something. And an opaque card
    can overhang a 3 ft corner strip and still be attributed to it, because it is
    centred on it.

    Every zone gets the same pill. A zone below the colour floor keeps all four
    figures and loses its weight instead: muted type on a faded card. The grey
    fill is what says the shooting percentage here is not evidence -- worth
    knowing, since a 40-attempt zone carries roughly +/-15 points of swing on its
    own, and the pill does not restate that.
    """
    px, py = to_px(*ZONE12_ANCHORS[z.zone])
    if not z.fga:
        # Zero attempts shares the grey ground but has its own explicit pill,
        # so it cannot be confused with a measured, below-floor zone.
        _zone12_empty_pill(ax, px, py, theme)
        return

    compact = pill == "counts"
    large = pill == "large"
    rows = _zone12_rows(z, compact)
    ink = ZONE12_PILL_INK if z.rated else ZONE12_THIN_INK
    alpha = 1.0 if z.rated else ZONE12_THIN_PILL_ALPHA

    # Measure before drawing so each card fits its own longest line. Type never
    # scales by zone: the rim card may cross the restricted-area boundary a
    # little, just as the corner cards overhang their narrow strips. Readability
    # is more important than trapping the whole card inside the region.
    strings = [t for row in rows for t in row[:2]]
    figure_size = ZONE12_LARGE_FIGURE_SIZE if large else ZONE12_FIGURE_SIZE
    delta_size = ZONE12_LARGE_DELTA_SIZE if large else ZONE12_DELTA_SIZE
    pair = 20.0 if large else ZONE12_PAIR_GAP
    block = 25.0 if large else ZONE12_BLOCK_GAP
    half_w = _zone12_widest(
        ax, strings, figure_size=figure_size, delta_size=delta_size
    ) / 2 + ZONE12_PILL_PAD_X
    span = pair if compact else pair * 2 + block
    half_h = span / 2 + 8 + ZONE12_PILL_PAD_Y

    ax.add_patch(FancyBboxPatch(
        (px - half_w, py - half_h), 2 * half_w, 2 * half_h,
        boxstyle=f"round,pad=0,rounding_size={ZONE12_PILL_ROUND}",
        facecolor=CREAM, edgecolor="none", alpha=alpha, zorder=10))

    # One column, not the rings chart's two. Side by side, a pill runs about
    # 330 px wide: the three above-the-arc zones alone would need 990 px of an
    # 860 px court, and a corner pill would hang off the canvas. Stacked it is
    # half that, every pill fits its own region, and it matches the reference
    # cards this chart is modelled on.
    # The larger top figure has more visible height than the smaller bottom
    # comparison line. A slight downward optical correction balances the cream
    # above line one with the cream below line four.
    top = py + span / 2 - (1.5 if large else 0.0)
    for fig_text, reference, directional, value in rows:
        ax.text(px, top, fig_text, fontsize=figure_size, zorder=11,
                color=ink, alpha=alpha, ha="center", va="center",
                fontproperties=helvetica("bold"))
        top -= pair
        ax.text(px, top, reference, fontsize=delta_size, zorder=11,
                color=_zone12_delta_ink(value, directional), alpha=alpha,
                ha="center", va="center", fontproperties=helvetica("bold"))
        top -= block


def _zone12_empty_pill(ax, px, py, theme):
    """One muted line for a zone with no attempts at all."""
    label = ax.text(px, py, "0 FGA", ha="center", va="center",
                    fontsize=ZONE12_FIGURE_SIZE, zorder=11,
                    color=ZONE12_THIN_INK, alpha=ZONE12_THIN_PILL_ALPHA,
                    fontproperties=helvetica("bold"))
    half_w = house.rendered_width(ax, label) / 2 + ZONE12_PILL_PAD_X
    half_h = 7 + ZONE12_PILL_PAD_Y
    ax.add_patch(FancyBboxPatch(
        (px - half_w, py - half_h), 2 * half_w, 2 * half_h,
        boxstyle=f"round,pad=0,rounding_size={ZONE12_PILL_ROUND}",
        facecolor=CREAM, edgecolor="none", alpha=ZONE12_THIN_PILL_ALPHA,
        zorder=10))


ZONE12_TAIL_GAP = 6.0            # between the shot-share figure and its reference


def _zone12_measure(ax, text: str, size: float) -> float:
    """Rendered width of one string at one size."""
    probe = ax.text(0, 0, text, fontsize=size, alpha=0.0,
                    fontproperties=helvetica("bold"))
    width = house.rendered_width(ax, probe)
    probe.remove()
    return width


def _zone12_widest(
    ax, strings, figure_size: float = ZONE12_FIGURE_SIZE,
    delta_size: float = ZONE12_DELTA_SIZE,
) -> float:
    """Width of the longest of these strings, at the size each is drawn.

    Measured off the renderer rather than estimated from character counts: a
    pill sized by guesswork is either padded unevenly or clipping its own type,
    and the strings vary from "LA: 1.0%" to "11/32 FG (34.4%)".
    """
    probes = []
    for index, text in enumerate(strings):
        size = figure_size if index % 2 == 0 else delta_size
        probes.append(ax.text(0, 0, text, fontsize=size, alpha=0.0,
                              fontproperties=helvetica("bold")))
    widest = max(house.rendered_width(ax, probe) for probe in probes)
    for probe in probes:
        probe.remove()
    return widest


def _zone12_thin_key(min_fga: int) -> str:
    """What the grey swatch means, as a number rather than as a verdict.

    "TOO FEW TO RATE" states a conclusion and hides the rule behind it; the
    reader has to take the chart's word for what counts as too few. The
    threshold is checkable against the figures in the grey pills themselves,
    which is the whole point of printing their attempt counts.

    It is set in the same muted grey as Below and Above, deliberately not in the
    accent red. The threshold is a footnote, and red on this chart already means
    "below league average" -- a red figure in the key would read as the bad end
    of the scale rather than as a caveat.
    """
    return f"Under {min_fga} FGA"


def _zone12_legend(ax, theme, palette: str, min_fga: int,
                   show_thin: bool = True):
    """One row: the colour scale, then the grey that sits outside it.

    Grey is a sixth state of the same encoding rather than a separate idea, so
    it reads as the tail of the scale instead of its own keyed block with its
    own heading. It prints on every chart whether or not a zone is currently
    grey -- this is a carousel, and a key that changes shape from slide to slide
    costs more than one redundant swatch. Its threshold does change between the
    team slide and the player slides, at 400 and 20, and that is correct rather
    than sloppy: the two are different subjects with different samples, and the
    floor is solved from each.

    What is NOT here: the lines explaining "vs LA" and the neutral grey gaps.
    Those belong on the page rather than on the asset, and they print in the
    Canva copy block instead, where they can be set once in the caption style.

    Laid out from measured text widths so the whole row centres on the canvas.
    The heading centres over the colour swatches alone, because those are what
    it names.
    """
    y = ZONE12_LEGEND_Y
    colors = ZONE12_PALETTES[palette]
    swatch, gap, pad, group = 28, 4, 12, 34
    scale_w = len(colors) * swatch + (len(colors) - 1) * gap
    label = dict(fontsize=9, color=theme.muted, fontproperties=helvetica("bold"))

    def width(text: str) -> float:
        probe = ax.text(0, 0, text, alpha=0.0, **label)
        measured = house.rendered_width(ax, probe)
        probe.remove()
        return measured

    thin_key = _zone12_thin_key(min_fga)
    below_w, above_w = width("Below"), width("Above")
    thin_w = width(thin_key) if show_thin else 0
    total = below_w + pad + scale_w + pad + above_w
    if show_thin:
        total += group + swatch + pad + thin_w
    x = house.CANVAS_WIDTH / 2 - total / 2

    ax.text(x + below_w, y, "Below", ha="right", va="center", **label)
    x += below_w + pad
    ax.text(x + scale_w / 2, y + 40, "FG% vs. NBA avg", ha="center", va="center",
            fontsize=10, color=theme.accent, fontproperties=helvetica("bold"))
    for i, color in enumerate(colors):
        ax.add_patch(Rectangle((x + i * (swatch + gap), y - 11), swatch, 22,
                               facecolor=color, edgecolor="none", zorder=9))
    x += scale_w + pad
    ax.text(x, y, "Above", ha="left", va="center", **label)
    if show_thin:
        x += above_w + group
        ax.add_patch(Rectangle((x, y - 11), swatch, 22, facecolor=ZONE12_GREY,
                               edgecolor="none", zorder=9))
        ax.text(x + swatch + pad, y, thin_key, ha="left", va="center", **label)


ZONE12_LEGEND_Y = 400

ZONE12_SUMMARY_Y = 270
ZONE12_SUMMARY_CARD_W = 210
ZONE12_SUMMARY_CARD_H = 76


def _zone12_overall_metrics(shots) -> dict[str, float | int]:
    """Overall volume, eFG%, and 3PT% from one shot-attempt table."""
    fga = len(shots)
    if not fga:
        raise ValueError("zone summary needs at least one field-goal attempt")
    threes = shots["shot_type"].astype(str).str.startswith("3PT")
    three_pa = int(threes.sum())
    three_pm = int(shots.loc[threes, "shot_made"].sum())
    fgm = int(shots["shot_made"].sum())
    return {
        "fga": fga,
        "efg_pct": (fgm + 0.5 * three_pm) / fga * 100,
        "three_pa": three_pa,
        "three_pct": three_pm / three_pa * 100 if three_pa else float("nan"),
    }


def _zone12_three_label(subject: dict[str, float | int]) -> str:
    """Avoid presenting a season 3PT% on fewer than 20 attempts."""
    three_pa = int(subject["three_pa"])
    if three_pa < 20:
        return f"{three_pa} 3PA"
    return f"{float(subject['three_pct']):.1f}% 3PT"


def _zone12_summary_cards(ax, player, _league, theme, ppg=None):
    """Three or four one-line overall cards in a Bulls-red gradient.

    PPG is optional because shot-attempt tables do not contain free throws. A
    caller that wants the scoring card must supply PPG from official box-score
    totals rather than asking this renderer to invent it from field goals.
    """
    subject = _zone12_overall_metrics(player)
    cards = [
        f"{int(subject['fga']):,} FGA",
        f"{subject['efg_pct']:.1f}% eFG",
        _zone12_three_label(subject),
    ]
    if ppg is not None:
        cards.insert(0, f"{float(ppg):.1f} PPG")
    gap = 22
    total_w = len(cards) * ZONE12_SUMMARY_CARD_W + (len(cards) - 1) * gap
    left = house.CANVAS_WIDTH / 2 - total_w / 2
    gradient_top = np.array(to_rgb("#B5123C"))
    gradient_bottom = np.array(to_rgb("#7E0C2B"))
    ramp = np.linspace(gradient_bottom, gradient_top, 256).reshape(256, 1, 3)
    for index, headline in enumerate(cards):
        x = left + index * (ZONE12_SUMMARY_CARD_W + gap)
        clip = FancyBboxPatch(
            (x, ZONE12_SUMMARY_Y - ZONE12_SUMMARY_CARD_H / 2),
            ZONE12_SUMMARY_CARD_W, ZONE12_SUMMARY_CARD_H,
            boxstyle="round,pad=0,rounding_size=14",
            facecolor="none", edgecolor="none", zorder=10)
        ax.add_patch(clip)
        image = ax.imshow(
            ramp,
            extent=(x, x + ZONE12_SUMMARY_CARD_W,
                    ZONE12_SUMMARY_Y - ZONE12_SUMMARY_CARD_H / 2,
                    ZONE12_SUMMARY_Y + ZONE12_SUMMARY_CARD_H / 2),
            origin="lower", aspect="auto", interpolation="bicubic", zorder=10,
        )
        image.set_clip_path(clip)
        center = x + ZONE12_SUMMARY_CARD_W / 2
        ax.text(center, ZONE12_SUMMARY_Y, headline,
                ha="center", va="center", fontsize=14, color="#FFFFFF",
                fontproperties=helvetica("bold"), zorder=11)


def _save(fig, out: Path, final: bool, facecolor: str):
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=house.export_dpi(final), facecolor=facecolor)
    plt.close(fig)
    print(f"Saved {out}")


CHARTS = {"hotspot": render_hotspot, "hex": render_hex, "rings": render_rings,
          "cells": render_cells, "ladder": render_ladder, "zones": render_zones}
# Charts that describe a shot profile rather than a shooter, so they accept
# --team in place of --player.
TEAM_CAPABLE = {"ladder", "hotspot", "hex", "cells", "zones"}


def _output_path(args, slug: str) -> Path:
    """``output/[<project>/]YYYY-MM-DD-{chart}-{mode}-{scope}.png``.

    Dated because these are dailies: a chart rebuilt a week later is a different
    chart, and an undated filename silently overwrites the version already sitting
    in a Canva page. The date stamps when the asset was cut; the trailing season
    states what it covers. Both are needed and neither substitutes for the other
    -- one build can cut eleven seasons on the same day, and one season can be
    rebuilt on eleven different days.

    ``--project`` puts renders in a folder named for the visual project, mirroring
    ``docs/visuals/<slug>/`` where reviewed versions are preserved. Scratch and
    archive then look alike, so a flat pile of PNGs in ``output/`` no longer
    reads as the convention being ignored. Without ``--project`` the render stays
    flat, which is right for one-off exploration that is not going anywhere.
    """
    from datetime import date

    mode = ("blank" if args.chart == "ladder" and getattr(args, "blank", False)
            else args.metric if args.chart == "ladder" else args.focus.strip().lower())
    parts = [date.today().isoformat(), args.chart] + ([mode] if mode else [])
    if args.chart == "ladder" and args.band != sm.LADDER_STEP_FT:
        parts.append(f"{args.band:g}ft")
    parts.append(slug)
    # The season belongs in the name for the same reason the date does. Eleven
    # seasons of one player rendered into one folder produced eleven files called
    # `...-zones-kirk-hinrich.png`, each overwriting the last, and the only sign
    # anything was wrong was a carousel with one slide in it.
    if season := getattr(args, "season", ""):
        parts.append(season)
    folder = ROOT / "output"
    if args.project:
        # Same dated folder shape as docs/visuals/, and the same reuse rule: an
        # existing folder for this project is found by slug whatever date it wears.
        folder = visual_dir(folder, args.project, create=False)
    return folder / ("-".join(parts) + ".png")


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
    ap.add_argument("--min-fga", type=int,
                    help="ladder only: attempts required to rate a band; defaults "
                         "to 15 for a player and 40 for a team or the league")
    ap.add_argument("--blank", action="store_true",
                    help="ladder only: render neutral geometry with no data or legend for a cover")
    ap.add_argument("--project", default="",
                    help="visual project slug; renders into output/<slug>/ so scratch "
                         "mirrors docs/visuals/<slug>/")
    ap.add_argument("--pill", default="full", choices=["full", "counts"],
                    help="zones only: full prints makes/attempts, the shooting "
                         "gap, FGA share and the NBA share; counts drops to the "
                         "shooting pair alone")
    ap.add_argument("--palette", default=ZONE12_DEFAULT_PALETTE,
                    choices=list(ZONE12_PALETTES),
                    help="zones only: fill scale — hex (blue/yellow/red) or "
                         "rdylgn (red/yellow/green)")
    ap.add_argument("--show-thin-gray", action="store_true",
                    help="hex only: draw occupied 1-2 shot cells in gray")
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    if args.blank and args.chart != "ladder":
        raise SystemExit("--blank is available only for --chart ladder")

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
        "blank": args.blank,
        "show_thin_gray": args.show_thin_gray,
    }
    if args.chart == "ladder":
        ctx["min_fga"] = args.min_fga if args.min_fga is not None else (
            sm.MIN_RING_FGA if args.team or args.league else PLAYER_LADDER_MIN_FGA
        )
    if args.chart == "zones":
        if args.league:
            raise SystemExit("--chart zones compares against the league; "
                             "the league cannot be its own subject")
        if args.team:
            ctx["min_fga"] = args.min_fga or sm.MIN_ZONE12_FGA_TEAM
        else:
            ctx["min_fga"] = args.min_fga or sm.MIN_ZONE12_FGA_PLAYER
        ctx["palette"] = args.palette
        ctx["pill"] = args.pill
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
