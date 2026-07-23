#!/usr/bin/env python3
"""Current Bulls roster hot-spot shot charts — a small-multiples chart asset.

Faithful port of Owen Phillips' F5 "hot spot" method
(https://thef5.substack.com/p/how-to-make-a-hot-spot-shot-chart) to this repo's
Python stack. For each player we estimate a smooth shot-location density and
subtract the league-average density, then draw the difference the way Owen does:
banded filled contours plus contour-line outlines. By default we draw only the
red "shoots here more than a typical NBA player" layer; ``--cold`` adds Owen's
second gray "shoots less" layer. This is a map of shot *location/frequency*, not
accuracy.

His R rendering, mirrored here:
  geom_raster(aes(alpha=sqrt(z), fill=sqrt(z)))              -> contourf (bands)
  stat_contour(aes(z=sqrt(z), color=..level..), bins = 4)   -> contour  (lines)
  scale_fill_gradient2(low='floralwhite', high='#cc0000')   -> Bulls-red ramp
  ... a second new_scale layer with high='#aaaaaa'          -> gray cold layer
  filter(z >= mean(z)); trans = 'sqrt'                      -> threshold + sqrt

Data comes from the existing NBA-stats fetchers (``get_player_shots`` with
``team_id=0`` so a player's full season is captured wherever he played, plus
``get_league_shots`` for the baseline). By default this prints a transparent,
chrome-free chart asset for Canva assembly; ``--full-post`` renders the framed
house layout instead.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Arc, Circle, FancyBboxPatch
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nba_api.stats.endpoints import leaguedashplayerstats

from bulls import data
from bulls.config import CURRENT_SEASON
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house

CACHE = ROOT / "cache" / "hot_spots"

# --- Population -------------------------------------------------------------
# Official 2026-27 roster, snapshot 2026-07-23 (docs/handoffs). Only the players
# with NBA history are listed; the four 2026 rookies (Awaka, Sellers, Swain,
# C. Wilson) have no 2025-26 shots to map and are disclosed in the caption.
ROSTER = [
    (1641824, "Matas Buzelis", "BUZELIS"),
    (1626181, "Norman Powell", "POWELL"),      # 2025-26 with Miami
    (1630581, "Josh Giddey", "GIDDEY"),
    (1630200, "Tre Jones", "JONES"),
    (1629651, "Nicolas Claxton", "CLAXTON"),   # 2025-26 with Brooklyn
    (1630172, "Patrick Williams", "WILLIAMS"),
    (1630171, "Isaac Okoro", "OKORO"),
    (1642265, "Rob Dillingham", "DILLINGHAM"),
    (1630188, "Jalen Smith", "SMITH"),
    (1631159, "Leonard Miller", "MILLER"),
    (1628380, "Zach Collins", "COLLINS"),      # thin 2025-26 sample
    (1642855, "Noa Essengue", "ESSENGUE"),     # essentially no 2025-26 shots
]

MIN_FGA = 150       # field-goal attempts needed for a stable location map
MAX_DIST_FT = 35    # drop half-court heaves, matching the F5 filter

# --- Density grid (raw NBA coords: tenths of a foot, hoop at origin) ---------
GRID_X = (-250.0, 250.0)     # court is 500 wide
GRID_Y = (-50.0, 300.0)      # baseline at -47.5; covers shots out to ~30 ft
CELL = 5.0                   # grid cell size in tenths of a foot (0.5 ft)
BLUR_FT = 3.8                # Gaussian bandwidth in feet (smoothing radius)
BASELINE_Y = -47.5

# Row layout for the small-multiples grid (players per row, top to bottom).
# Symmetric so the grid never looks top- or bottom-heavy.
DEFAULT_ROWS = [2, 3, 3, 2]

# Warm, faint court lines (from the Summer League report) so the geometry
# anchors the heat without competing with it.
COURT_LINE = "#C9A8B5"

# F5 layers: filled contour bands + outline color, hot (Bulls red) and cold
# (gray). Low band is faint; the ramp climbs through Bulls red to a deep red.
HOT_BANDS = ["#F6CDD7", "#E67C96", "#CE1141", "#7E0C2B"]
HOT_LINE = "#5E0820"
COLD_BANDS = ["#E7E7E7", "#C7C7C7", "#A2A2A2"]
COLD_LINE = "#8A8A8A"
HOT_ALPHA = 0.92
COLD_ALPHA = 0.55

HEADSHOT_HALF = 30.0  # half the square headshot side, left of each name

# Helvetica bold, matching the landscape/Sticky Stats chart typography. Extracted
# from the macOS system .ttc (face 0 regular, face 1 bold); Archivo is the fallback.
HELVETICA_TTC = Path("/System/Library/Fonts/Helvetica.ttc")
HELVETICA_FACES = {"regular": 0, "bold": 1}
FONT_CACHE_DIR = ROOT / "cache" / "fonts"


def helvetica(weight: str = "bold") -> FontProperties:
    fallback = "bold" if weight == "bold" else "medium"
    if not HELVETICA_TTC.exists():
        return house.body_font(fallback)
    extracted = FONT_CACHE_DIR / f"Helvetica-{weight}.ttf"
    if not extracted.exists():
        try:
            from fontTools.ttLib import TTCollection

            FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            TTCollection(str(HELVETICA_TTC)).fonts[HELVETICA_FACES.get(weight, 0)].save(str(extracted))
        except Exception:
            return house.body_font(fallback)
    return FontProperties(fname=str(extracted))


# ---------------------------------------------------------------------------
# Fetch (cached so the visual can iterate without re-hitting the API)
# ---------------------------------------------------------------------------
def _player_cache(pid: int) -> Path:
    return CACHE / f"player_{pid}_{CURRENT_SEASON}.csv"


def _league_cache() -> Path:
    return CACHE / f"league_{CURRENT_SEASON}.csv"


def load_player_shots(pid: int, refresh: bool) -> pd.DataFrame:
    path = _player_cache(pid)
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = data.get_player_shots(pid, team_id=0, season=CURRENT_SEASON)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["loc_x", "loc_y", "shot_distance", "shot_type"]
    df = df[cols] if not df.empty else pd.DataFrame(columns=cols)
    df.to_csv(path, index=False)
    return df


def load_league_shots(refresh: bool) -> pd.DataFrame:
    path = _league_cache()
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = data.get_league_shots(season=CURRENT_SEASON)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df[["loc_x", "loc_y", "shot_distance"]]
    df.to_csv(path, index=False)
    return df


def load_games_played(refresh: bool) -> dict[int, int]:
    """Official season games played per player (team-agnostic, one call)."""
    path = CACHE / f"games_played_{CURRENT_SEASON}.csv"
    if path.exists() and not refresh:
        df = pd.read_csv(path)
    else:
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=CURRENT_SEASON, season_type_all_star="Regular Season",
            per_mode_detailed="Totals", timeout=60, headers=_NBA_HEADERS,
        )
        df = stats.get_data_frames()[0][["PLAYER_ID", "GP"]]
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    return {int(pid): int(gp) for pid, gp in zip(df["PLAYER_ID"], df["GP"])}


# ---------------------------------------------------------------------------
# Prepare: shot locations -> normalized density difference (the F5 method)
# ---------------------------------------------------------------------------
def _edges():
    xe = np.arange(GRID_X[0], GRID_X[1] + CELL, CELL)
    ye = np.arange(GRID_Y[0], GRID_Y[1] + CELL, CELL)
    return xe, ye


def density(df: pd.DataFrame) -> np.ndarray:
    """Smoothed, normalized shot-location density on the shared grid (nx, ny)."""
    xe, ye = _edges()
    counts, _, _ = np.histogram2d(df["loc_x"], df["loc_y"], bins=[xe, ye])
    sigma = BLUR_FT * 10.0 / CELL  # feet -> grid cells
    smooth = gaussian_filter(counts, sigma=sigma, mode="constant")
    total = smooth.sum()
    return smooth / total if total else smooth


def signed_diff(player_pdf: np.ndarray, league_pdf: np.ndarray) -> np.ndarray:
    """Player-minus-league density, with off-court cells zeroed.

    Positive where the player shoots MORE than league average, negative where he
    shoots LESS. Cells at/below the baseline are zeroed so heat never bleeds off
    the court bottom.
    """
    diff = player_pdf - league_pdf
    _, ye = _edges()
    yc = (ye[:-1] + ye[1:]) / 2.0
    diff[:, yc <= BASELINE_Y] = 0.0
    return diff


@dataclass
class PlayerMap:
    name: str
    short: str
    fga: int
    gp: int
    headshot: object  # Path to the cached headshot, or None
    diff: np.ndarray  # player_pdf - league_pdf, (nx, ny)


def prepare(refresh: bool) -> list[PlayerMap]:
    league_pdf = density(_filter(load_league_shots(refresh)))
    gp_by_id = load_games_played(refresh)
    maps: list[PlayerMap] = []
    for pid, name, short in ROSTER:
        shots = load_player_shots(pid, refresh)
        fga = len(shots)  # total season FGA (matches nba.com); the label shows this
        if fga < MIN_FGA:
            print(f"  skip {name}: {fga} FGA (< {MIN_FGA})")
            continue
        maps.append(PlayerMap(
            name=name, short=short, fga=fga,
            gp=gp_by_id.get(pid, 0),
            headshot=data.get_player_headshot(pid),
            # Density maps only shots within 35 ft (Owen's filter); a rare heave
            # counts toward FGA above but is off the grid and would not render.
            diff=signed_diff(density(_filter(shots)), league_pdf),
        ))
    return maps


def _filter(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["shot_distance"] <= MAX_DIST_FT]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def draw_half_court(ax, center_x: float, center_y: float, s: float, color: str):
    """Reusable half-court geometry (from summer_league_report), center-anchored.

    Returns the (x0, y0) origin so the density grid can be transformed into the
    same pixel space: px = x0 + (loc_x + 250) * s, py = y0 + (loc_y + 47.5) * s.
    """
    top_y = 280.0
    x0 = center_x - 250.0 * s
    y0 = center_y - (top_y + 47.5) * s / 2.0

    def t(cx, cy):
        return x0 + (cx + 250.0) * s, y0 + (cy + 47.5) * s

    line = dict(color=color, lw=1.1, zorder=5)
    ax.plot([t(-250, -47.5)[0], t(250, -47.5)[0]], [y0, y0], **line)
    for side in (-250, 250):
        ax.plot([t(side, -47.5)[0]] * 2, [t(side, -47.5)[1], t(side, 110)[1]], **line)
    ax.add_patch(FancyBboxPatch(
        t(-80, -47.5), 160 * s, 190 * s, boxstyle="square,pad=0",
        facecolor="none", edgecolor=color, lw=1.1, zorder=5))
    hoop_x, hoop_y = t(0, 0)
    ax.add_patch(Circle((hoop_x, hoop_y), 7.5 * s * 2, facecolor="none", edgecolor=color, lw=1.1, zorder=5))
    ax.plot([t(-30, -7.5)[0], t(30, -7.5)[0]], [t(0, -7.5)[1]] * 2, **line)  # backboard
    ax.add_patch(Arc((hoop_x, hoop_y), 2 * 40 * s, 2 * 40 * s, theta1=0, theta2=180, color=color, lw=1.1, zorder=5))
    ft_x, ft_y = t(0, 142.5)
    ax.add_patch(Arc((ft_x, ft_y), 2 * 60 * s, 2 * 60 * s, theta1=0, theta2=180, color=color, lw=1.1, zorder=5))
    ax.add_patch(Arc((ft_x, ft_y), 2 * 60 * s, 2 * 60 * s, theta1=180, theta2=360, color=color, lw=1.1, linestyle=(0, (4, 3)), zorder=5))
    corner_top = (237.5 ** 2 - 220 ** 2) ** 0.5
    for side in (-220, 220):
        ax.plot([t(side, -47.5)[0]] * 2, [t(side, -47.5)[1], t(side, corner_top)[1]], **line)
    theta = 22.1
    ax.add_patch(Arc((hoop_x, hoop_y), 2 * 237.5 * s, 2 * 237.5 * s, theta1=theta, theta2=180 - theta, color=color, lw=1.1, zorder=5))
    return x0, y0


def _draw_field(ax, x0, y0, s, field, fill_colors, line_color, alpha):
    """One F5 density layer: filled contour bands + contour-line outlines.

    ``field`` is the non-negative half of the density difference (nx, ny). Only
    cells above the mean positive value are shown (Owen's ``filter(z >= mean(z)``)
    and the color/level spacing is sqrt-scaled (his ``trans = 'sqrt'``).
    """
    live = field[field > 0]
    if live.size == 0:
        return
    thr = float(live.mean())
    fmax = float(field.max())
    if fmax <= thr:
        return

    xe, ye = _edges()
    xc = (xe[:-1] + xe[1:]) / 2.0
    yc = (ye[:-1] + ye[1:]) / 2.0
    cx, cy = np.meshgrid(xc, yc)          # (ny, nx)
    px = x0 + (cx + 250.0) * s
    py = y0 + (cy + 47.5) * s
    z = np.sqrt(field.T)                  # (ny, nx), sqrt transform

    edges = np.sqrt(np.linspace(thr, fmax, len(fill_colors) + 1))
    edges[-1] += 1e-9                     # keep the peak cell inside the top band
    ax.contourf(px, py, z, levels=edges, colors=fill_colors, alpha=alpha, zorder=2)
    ax.contour(px, py, z, levels=edges[1:-1], colors=line_color,
               linewidths=0.7, alpha=min(1.0, alpha + 0.08), zorder=3)


def square_headshot_label(ax, image_path, cx: float, cy: float, half: float):
    """Square center-crop headshot centered at (cx, cy); placeholder if missing."""
    extent = [cx - half, cx + half, cy - half, cy + half]
    image = None
    if image_path is not None:
        try:
            image = plt.imread(image_path)
        except (FileNotFoundError, OSError, ValueError):
            image = None
    if image is None:
        ax.add_patch(FancyBboxPatch((cx - half, cy - half), 2 * half, 2 * half,
                     boxstyle="square,pad=0", facecolor="#DDD8D1", edgecolor="none", zorder=6))
        return
    h, w = image.shape[:2]
    side = min(h, w)
    top, left = (h - side) // 2, (w - side) // 2
    ax.imshow(image[top:top + side, left:left + side], extent=extent,
              interpolation="bilinear", zorder=6)


def draw_player(ax, pm: PlayerMap, center_x: float, court_y: float, s: float,
                theme, show_cold: bool):
    x0, y0 = draw_half_court(ax, center_x, court_y, s, COURT_LINE)
    if show_cold:
        _draw_field(ax, x0, y0, s, np.clip(-pm.diff, 0, None), COLD_BANDS, COLD_LINE, COLD_ALPHA)
    _draw_field(ax, x0, y0, s, np.clip(pm.diff, 0, None), HOT_BANDS, HOT_LINE, HOT_ALPHA)

    # Square headshot to the left of the name (top) over the metrics (bottom).
    # The whole group hugs the court baseline (y0) and is centered under the court.
    # Helvetica bold, matching the landscape chart family.
    half = HEADSHOT_HALF
    name_fs, stat_fs = 16, 12
    line_gap = 10.0
    name_h, stat_h = name_fs * 1.15, stat_fs * 1.15
    text_h = name_h + line_gap + stat_h

    name_art = ax.text(0, 0, pm.short, ha="left", va="top", zorder=6,
                       fontsize=name_fs, color=theme.ink, fontproperties=helvetica("bold"))
    stat_art = ax.text(0, 0, f"{pm.fga} FGA, {pm.gp} GP", ha="left", va="top", zorder=6,
                       fontsize=stat_fs, color=theme.muted, fontproperties=helvetica("bold"))
    block_w = max(house.rendered_width(ax, name_art), house.rendered_width(ax, stat_art))

    pad = 14.0
    left = center_x - (2 * half + pad + block_w) / 2.0
    hs_cy = y0 - 12.0 - half                       # headshot top sits 12 px below the baseline
    square_headshot_label(ax, pm.headshot, left + half, hs_cy, half)
    text_x = left + 2 * half + pad
    text_top = hs_cy + text_h / 2.0                # text block centered against the headshot
    name_art.set_position((text_x, text_top))
    stat_art.set_position((text_x, text_top - name_h - line_gap))


def render(maps, rows, theme_name, out, *, final, chart_only, show_cold):
    theme = house.get_theme(theme_name)
    fig, ax = house.new_canvas(theme)

    if chart_only:
        top, bottom = house.CANVAS_HEIGHT - 40, 40
    else:
        house.draw_header(
            ax,
            [("WHERE THE BULLS ", theme.ink), ("SHOOT", theme.accent)],
            [f"{len(maps)} current Bulls", "2025-26", "vs. league average"],
            kicker="Red = shoots here more than a typical NBA player",
            theme=theme,
        )
        house.draw_footer(ax, note=f"Min. {MIN_FGA} FGA · 2025-26 regular season", theme=theme)
        ax.text(house.CANVAS_WIDTH / 2, 70,
                "Acquired players (Powell, Claxton) shown with their prior team",
                ha="center", va="bottom", fontsize=9.5, color=theme.faint,
                fontproperties=house.body_font())
        top, bottom = house.CANVAS_HEIGHT - 244, 92

    # Each row reserves a strip below the court for the label group (square
    # headshot + name + metrics), which draw_player hangs off the court baseline.
    label_h, gap = 76.0, 20.0
    col_w = (house.CANVAS_WIDTH - 2 * house.SIDE_MARGIN) / 3.0
    row_h = (top - bottom) / len(rows)
    region_h = row_h - label_h - gap
    court_s = min(col_w * 0.90 / 500.0, region_h * 0.92 / (GRID_Y[1] - GRID_Y[0]))

    i = 0
    for r, n in enumerate(rows):
        tile_top = top - r * row_h
        court_y = tile_top - region_h / 2.0
        row_left = (house.CANVAS_WIDTH - n * col_w) / 2.0
        for c in range(n):
            if i >= len(maps):
                break
            cx = row_left + (c + 0.5) * col_w
            draw_player(ax, maps[i], cx, court_y, court_s, theme, show_cold)
            i += 1

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if chart_only:
        fig.savefig(out, dpi=house.export_dpi(final), transparent=True)
    else:
        house.save_post(fig, out, final=final)
    print(f"Saved {out} ({'final 300' if final else 'draft 150'} DPI"
          f"{', chart-only/transparent' if chart_only else ''})")


def parse_args():
    p = argparse.ArgumentParser(description="Bulls roster hot-spot shot charts")
    p.add_argument("--final", action="store_true", help="export at 300 DPI")
    p.add_argument("--refresh", action="store_true", help="re-fetch shots (ignore cache)")
    p.add_argument("--full-post", action="store_true",
                   help="render the framed house layout (default: transparent chart asset)")
    p.add_argument("--cold", action="store_true",
                   help="add Owen's gray 'shoots less' layer (default: red hot layer only)")
    p.add_argument("--theme", default="jersey")
    p.add_argument("--output", default="")
    return p.parse_args()


def main():
    args = parse_args()
    chart_only = not args.full_post
    suffix = "hot-spots" if args.full_post else "hot-spots-chart"
    out = args.output or str(
        ROOT / "output" / "feed" / f"{datetime.now():%Y-%m-%d}-roster-{suffix}.png"
    )
    print("Preparing hot-spot maps...")
    maps = prepare(args.refresh)
    print(f"Rendering {len(maps)} players...")
    render(maps, DEFAULT_ROWS, args.theme, out,
           final=args.final, chart_only=chart_only, show_cold=args.cold)


if __name__ == "__main__":
    main()
