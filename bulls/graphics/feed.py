"""Single-image feed post builders."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Rectangle

from bulls import analysis
from bulls.config import BULLS_BLACK, BULLS_RED

import matplotlib.font_manager as _fm

_FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"

# Instagram portrait feed post (4:5)
INSTAGRAM_FEED_WIDTH_PX = 1080
INSTAGRAM_FEED_HEIGHT_PX = 1350
DEFAULT_DPI = 150


def _mpl_color(rgb: Sequence[int]) -> tuple:
    """Convert RGB values (0-255) to matplotlib color tuple (0-1)."""
    return tuple(channel / 255 for channel in rgb)


def build_zone_pps_post(
    team_shots: pd.DataFrame,
    title: str = "Bulls Shot Value by Zone",
    subtitle: str = "Points per shot (higher is better)",
    min_shots: int = 20,
) -> plt.Figure:
    """
    Build an Instagram-ready zone PPS post from team shot-level data.

    Args:
        team_shots: DataFrame from bulls.data.get_team_shots()
        title: Main post title
        subtitle: Post subtitle
        min_shots: Minimum shots required for zone inclusion

    Returns:
        Matplotlib Figure sized for Instagram portrait feed post.
    """
    figsize = (INSTAGRAM_FEED_WIDTH_PX / 100, INSTAGRAM_FEED_HEIGHT_PX / 100)
    fig, ax = plt.subplots(figsize=figsize, facecolor="white")

    if team_shots.empty:
        ax.text(0.5, 0.5, "No shot data available", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    pps_stats = analysis.points_per_shot(team_shots, by_zone=True)
    overall_pps = float(pps_stats.get("overall", {}).get("pps", 0.0))
    zone_data = pps_stats.get("by_zone", {})

    rows = []
    for zone, stats in zone_data.items():
        total_shots = int(stats.get("total_shots", 0))
        if total_shots < min_shots:
            continue
        rows.append(
            {
                "zone": zone,
                "pps": float(stats.get("pps", 0.0)),
                "shots": total_shots,
                "fg_pct": float(stats.get("fg_pct", 0.0)),
            }
        )

    if not rows:
        ax.text(
            0.5,
            0.5,
            f"No zones meet min_shots={min_shots}",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        return fig

    frame = pd.DataFrame(rows).sort_values("pps", ascending=True).reset_index(drop=True)

    bar_colors = [
        _mpl_color(BULLS_RED) if pps >= overall_pps else _mpl_color(BULLS_BLACK)
        for pps in frame["pps"]
    ]
    bars = ax.barh(frame["zone"], frame["pps"], color=bar_colors, alpha=0.9)

    for bar, pps, shots in zip(bars, frame["pps"], frame["shots"]):
        label = f"{pps:.2f} PPS | {shots} shots"
        ax.text(
            bar.get_width() + 0.01,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=11,
            color="black",
        )

    ax.axvline(overall_pps, color="dimgray", linestyle="--", linewidth=1.5)
    ax.text(
        overall_pps + 0.01,
        0.02,
        f"Overall: {overall_pps:.2f}",
        transform=ax.get_xaxis_transform(),
        fontsize=11,
        color="dimgray",
    )

    ax.set_xlim(0, max(frame["pps"].max() + 0.35, 1.2))
    ax.set_xlabel("Points Per Shot", fontsize=12, fontweight="bold")
    ax.set_ylabel("")
    ax.tick_params(axis="y", labelsize=11)
    ax.tick_params(axis="x", labelsize=10)
    ax.xaxis.grid(True, alpha=0.2)

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)

    fig.text(0.5, 0.965, title, ha="center", fontsize=28, fontweight="bold", color="black")
    fig.text(0.5, 0.935, subtitle, ha="center", fontsize=14, color="dimgray")
    fig.text(
        0.5,
        0.02,
        "Red bars are above team average PPS",
        ha="center",
        fontsize=11,
        color="dimgray",
    )

    fig.subplots_adjust(left=0.22, right=0.94, top=0.88, bottom=0.08)
    return fig


def _fp_title(**kwargs) -> _fm.FontProperties:
    """FontProperties for Playfair Display headings."""
    return _fm.FontProperties(fname=str(_FONT_DIR / "PlayfairDisplay.ttf"), **kwargs)


def _fp_body(**kwargs) -> _fm.FontProperties:
    """FontProperties for DM Sans body text."""
    return _fm.FontProperties(fname=str(_FONT_DIR / "DMSans.ttf"), **kwargs)


def _draw_court(ax, line_color: str = "#888888", line_alpha: float = 1.0,
                lw: float = 1.2, show_boundary: bool = True):
    """Draw a half-court diagram."""
    kw = dict(linewidth=lw, color=line_color, alpha=line_alpha, fill=False)
    # Backboard + hoop
    ax.plot([-30, 30], [-7.5, -7.5], linewidth=lw, color=line_color, alpha=line_alpha)
    ax.add_patch(Circle((0, 0), radius=7.5, **kw))
    # Paint
    ax.add_patch(Rectangle((-80, -47.5), 160, 190, **kw))
    # Free throw circles
    ax.add_patch(Arc((0, 142.5), 120, 120, theta1=0, theta2=180, linewidth=lw, color=line_color, alpha=line_alpha))
    ax.add_patch(Arc((0, 142.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=line_color, alpha=line_alpha * 0.5, linestyle="dashed"))
    # Restricted area
    ax.add_patch(Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=line_color, alpha=line_alpha))
    # Corner 3 lines
    ax.plot([-220, -220], [-47.5, 92.5], linewidth=lw, color=line_color, alpha=line_alpha)
    ax.plot([220, 220], [-47.5, 92.5], linewidth=lw, color=line_color, alpha=line_alpha)
    # 3-point arc
    ax.add_patch(Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=line_color, alpha=line_alpha))
    if show_boundary:
        # Half court
        ax.add_patch(Arc((0, 422.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=line_color, alpha=line_alpha * 0.5))
        ax.plot([-250, 250], [422.5, 422.5], linewidth=lw, color=line_color, alpha=line_alpha * 0.5)
        # Boundary
        ax.add_patch(Rectangle((-250, -47.5), 500, 470, linewidth=lw + 0.5, color=line_color, alpha=line_alpha, fill=False))


# Size tier per zone – controls headshot zoom and label sizing
_ZONE_TIER = {
    "Restricted Area": "xl",
    "In The Paint (Non-RA)": "lg",
    "Center Mid-Range": "md",
    "Top of Key 3": "md",
    "Left Wing 3": "sm",
    "Right Wing 3": "sm",
    "Left Mid-Range": "sm",
    "Right Mid-Range": "sm",
    "Left Baseline": "sm",
    "Right Baseline": "sm",
    "Left Corner 3": "sm",
    "Right Corner 3": "sm",
    "Mid-Range": "sm",
    "Above the Break 3": "md",
}
_TIER_SETTINGS = {
    "xl": {"zoom": 0.092, "gap": 37, "fs_name": 10.5},
    "lg": {"zoom": 0.092, "gap": 37, "fs_name": 10.5},
    "md": {"zoom": 0.088, "gap": 35, "fs_name": 10},
    "sm": {"zoom": 0.088, "gap": 35, "fs_name": 10},
}


def _zone_positions() -> dict:
    """Court positions (x, y) for 12 zones.

    Geographically accurate: basket at (0,0), 3pt arc radius ~237.5,
    corner lines at x=±220, paint x=±80 up to y=142.5.
    """
    return {
        # Interior
        "Restricted Area": (0, -2),
        "In The Paint (Non-RA)": (0, 100),
        # Baseline mid-range (short corner)
        "Left Baseline": (-145, 30),
        "Right Baseline": (145, 30),
        # Wing mid-range
        "Left Mid-Range": (-145, 140),
        "Right Mid-Range": (145, 140),
        # Top-of-key mid-range
        "Center Mid-Range": (0, 188),
        # Corner 3s — clearly outside the 3pt line (line at x=±220)
        "Left Corner 3": (-250, 25),
        "Right Corner 3": (250, 25),
        # Wing 3s — above the arc, names clear of the line
        "Left Wing 3": (-172, 213),
        "Right Wing 3": (172, 213),
        # Top of key 3 — above the arc apex (237.5)
        "Top of Key 3": (0, 267),
        # Fallbacks for basic (6-zone) data
        "Mid-Range": (-140, 140),
        "Above the Break 3": (0, 268),
    }


def _make_circular_headshot(
    img_path: Path,
    border_color: Optional[tuple] = None,
    border_frac: float = 0.035,
) -> Optional[np.ndarray]:
    """Load an image, crop to circle, optionally add a colored border ring."""
    try:
        img = mpimg.imread(str(img_path))
    except Exception:
        return None

    h, w = img.shape[:2]
    sq = min(h, w)
    x_start = (w - sq) // 2
    img = img[:sq, x_start:x_start + sq]

    h, w = img.shape[:2]
    Y, X = np.ogrid[:h, :w]
    center = h // 2
    outer_mask = ((X - center) ** 2 + (Y - center) ** 2) <= center ** 2

    # Ensure RGBA
    if img.shape[2] == 3:
        if img.dtype == np.uint8:
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        else:
            alpha = np.ones((h, w, 1), dtype=img.dtype)
        img = np.concatenate([img, alpha], axis=2)

    # Paint border ring
    if border_color is not None:
        border_px = max(int(center * border_frac), 2)
        inner_radius = center - border_px
        inner_mask = ((X - center) ** 2 + (Y - center) ** 2) <= inner_radius ** 2
        ring = outer_mask & ~inner_mask
        if img.dtype == np.uint8:
            img[ring] = [int(c) for c in border_color[:3]] + [255]
        else:
            img[ring] = [c / 255 for c in border_color[:3]] + [1.0]

    # Transparency outside circle
    if img.dtype == np.uint8:
        img[~outer_mask, 3] = 0
    else:
        img[~outer_mask, 3] = 0.0

    return img


def _build_court_canvas(title, subtitle, footnote):
    """Create a figure with court layout and title block. Returns (fig, ax, coords)."""
    bg = "#FFFFFF"
    court_line = "#C8C8C8"
    ink = "#1A1A1A"
    muted = "#777777"
    red = "#CE1141"

    figsize = (INSTAGRAM_FEED_WIDTH_PX / DEFAULT_DPI, INSTAGRAM_FEED_HEIGHT_PX / DEFAULT_DPI)
    fig = plt.figure(figsize=figsize, facecolor=bg)

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor(bg)

    x_lo, x_hi = -280, 280
    x_range = x_hi - x_lo
    y_range = x_range * (INSTAGRAM_FEED_HEIGHT_PX / INSTAGRAM_FEED_WIDTH_PX)
    y_lo = -185
    y_hi = y_lo + y_range

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.text(x_lo + 15, y_hi - 90, title,
            ha="left", va="top", fontsize=44, color=ink,
            fontproperties=_fp_title(weight="bold"))
    ax.text(x_lo + 15, y_hi - 148, subtitle,
            ha="left", va="top", fontsize=18, color=muted,
            fontproperties=_fp_body(weight="medium"))
    ax.text(x_lo + 15, y_hi - 175, footnote,
            ha="left", va="top", fontsize=14, color=red, style="italic",
            fontproperties=_fp_body(weight="medium"))

    _draw_court(ax, line_color=court_line, line_alpha=1.0, lw=1.3, show_boundary=False)
    ax.plot([-220, 220], [-47.5, -47.5], linewidth=1.3, color=court_line)

    ax.text(x_lo + 20, y_lo + 15, "Data via NBA.com/Stats",
            ha="left", va="bottom", fontsize=8.5, color="#AAAAAA",
            fontproperties=_fp_body())

    return fig, ax, {"ink": ink, "x_lo": x_lo, "y_lo": y_lo}


def _place_headshots(ax, leaders, ink, headshot_cache_dir, skip_zero_points=False):
    """Place headshots and name labels on the court for a dict of zone leaders."""
    from bulls.data.fetch import get_player_headshot

    positions = _zone_positions()

    for zone_name, leader in leaders.items():
        if zone_name not in positions:
            continue
        if skip_zero_points and int(leader.get("total_points", 0)) == 0:
            continue

        x, y = positions[zone_name]
        player_id = leader["player_id"]
        player_name = leader["player_name"]

        tier_key = _ZONE_TIER.get(zone_name, "sm")
        tier = _TIER_SETTINGS[tier_key]

        headshot_path = get_player_headshot(player_id, cache_dir=headshot_cache_dir)
        headshot_placed = False

        if headshot_path and headshot_path.exists():
            circular = _make_circular_headshot(headshot_path)
            if circular is not None:
                im = OffsetImage(circular, zoom=tier["zoom"])
                im.image.axes = ax
                ab = AnnotationBbox(im, (x, y), frameon=False, pad=0)
                ax.add_artist(ab)
                headshot_placed = True

        label_y = y - tier["gap"] if headshot_placed else y
        last_name = player_name.split()[-1]

        ax.text(x, label_y, last_name,
                ha="center", va="top", fontsize=tier["fs_name"], color=ink,
                fontproperties=_fp_body(weight="bold"))


def build_zone_leaders_post(
    team_shots: pd.DataFrame,
    title: str = "Leading Scorers By Zone",
    subtitle: str = "Chicago Bulls | 2025-26 Season",
    footnote: str = "Points Per Game by Court Area",
    min_shots: int = 5,
    headshot_cache_dir: str = "cache/headshots",
) -> plt.Figure:
    """Build a zone leaders (PPG) graphic with player headshots."""
    fig, ax, ctx = _build_court_canvas(title, subtitle, footnote)

    if team_shots.empty:
        ax.text(0, 130, "No shot data available", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    shots_detailed = analysis.detailed_zones(team_shots)
    leaders = analysis.zone_leaders(shots_detailed, min_shots=min_shots)

    if not leaders:
        ax.text(0, 130, "No zone leaders found", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    _place_headshots(ax, leaders, ctx["ink"], headshot_cache_dir,
                     skip_zero_points=True)
    return fig


def build_zone_frequency_post(
    team_shots: pd.DataFrame,
    title: str = "Shot Frequency By Zone",
    subtitle: str = "Chicago Bulls | 2025-26 Season",
    footnote: str = "Shot Attempts Per Game by Court Area",
    min_shots: int = 5,
    headshot_cache_dir: str = "cache/headshots",
) -> plt.Figure:
    """Build a zone frequency (FGA/game) graphic with player headshots."""
    fig, ax, ctx = _build_court_canvas(title, subtitle, footnote)

    if team_shots.empty:
        ax.text(0, 130, "No shot data available", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    shots_detailed = analysis.detailed_zones(team_shots)
    leaders = analysis.zone_leaders_by_frequency(shots_detailed,
                                                  min_shots=min_shots)

    if not leaders:
        ax.text(0, 130, "No zone leaders found", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    _place_headshots(ax, leaders, ctx["ink"], headshot_cache_dir)
    return fig


def _draw_zone_borders(ax, color: str = "#BBBBBB", alpha: float = 0.5, lw: float = 1.0):
    """Draw semi-transparent lines dividing the court into 12 zones."""
    pass


# Font sizes per zone tier for text-only zone stats
_TIER_TEXT_SETTINGS = {
    "xl": {"fs_main": 13, "fs_sub": 11},
    "lg": {"fs_main": 12, "fs_sub": 10},
    "md": {"fs_main": 11, "fs_sub": 9.5},
    "sm": {"fs_main": 10, "fs_sub": 8.5},
}


def _place_zone_text(ax, zone_data: dict, ink: str, mode: str = "team",
                     total_shots: int = 0):
    """Place text stats on the court for each zone.

    Args:
        ax: Matplotlib axes with court drawn
        zone_data: Dict mapping zone name -> stats dict
        ink: Text color
        mode: "team" shows FGM/FGA + distribution %, "volume" shows player name + FGM/FGA + FG%
        total_shots: Total shot attempts across all zones (used for distribution % in team mode)
    """
    positions = _zone_positions()

    for zone_name, stats in zone_data.items():
        if zone_name not in positions:
            continue

        x, y = positions[zone_name]
        tier_key = _ZONE_TIER.get(zone_name, "sm")
        tier = _TIER_TEXT_SETTINGS[tier_key]

        if mode == "team":
            made = stats.get('made', 0)
            attempted = stats.get('attempted', 0)

            if total_shots > 0:
                dist_pct = attempted / total_shots * 100
                sub_label = f"{dist_pct:.1f}% of shots"
            else:
                pct = stats.get('pct', 0.0)
                sub_label = f"{pct:.1f}%"

            main_label = f"{made}/{attempted}"
            fs_sub = 8.5 if tier_key == "sm" else 10.5

            ax.text(x, y + 8, main_label,
                    ha="center", va="center", fontsize=12,
                    color=ink, fontproperties=_fp_body(weight="bold"))
            ax.text(x, y - 12, sub_label,
                    ha="center", va="center", fontsize=fs_sub,
                    color=ink, fontproperties=_fp_body(weight="bold"))

        elif mode == "volume":
            player_name = stats.get('player_name', '')
            fgm = stats.get('fgm', 0)
            fga = stats.get('fga', 0)
            fg_pct = stats.get('fg_pct', 0.0)

            last_name = player_name.split()[-1] if player_name else ''

            ax.text(x, y + 16, last_name,
                    ha="center", va="center", fontsize=tier["fs_main"],
                    color=ink, fontproperties=_fp_body(weight="bold"))
            ax.text(x, y - 4, f"{fgm}/{fga}",
                    ha="center", va="center", fontsize=tier["fs_sub"],
                    color=ink, fontproperties=_fp_body(weight="medium"))
            ax.text(x, y - 22, f"{fg_pct:.1f}%",
                    ha="center", va="center", fontsize=tier["fs_sub"],
                    color=ink, fontproperties=_fp_body(weight="medium"))


def build_zone_team_stats_post(
    team_shots: pd.DataFrame,
    title: str = "Zone Shooting",
    subtitle: str = "Chicago Bulls | 2025-26 Season",
    footnote: str = "Shot Attempts and Distribution by Court Area",
) -> plt.Figure:
    """Build a court map showing team aggregate FGM/FGA and shot distribution % per zone."""
    fig, ax, ctx = _build_court_canvas(title, subtitle, footnote)

    if team_shots.empty:
        ax.text(0, 130, "No shot data available", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    shots_detailed = analysis.detailed_zones(team_shots)
    shots_detailed = shots_detailed[shots_detailed['shot_zone'] != 'Backcourt']
    zone_stats = analysis.game_zone_stats(shots_detailed)

    if not zone_stats:
        ax.text(0, 130, "No zone stats found", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    total_made = sum(s['made'] for s in zone_stats.values())
    total_attempted = sum(s['attempted'] for s in zone_stats.values())
    fg_pct = (total_made / total_attempted * 100) if total_attempted > 0 else 0.0

    _draw_zone_borders(ax)
    _place_zone_text(ax, zone_stats, ctx["ink"], mode="team",
                     total_shots=total_attempted)

    # Overall totals at the bottom
    totals_label = f"TOTAL: {total_made}/{total_attempted} FG  ({fg_pct:.1f}%)"
    ax.text(0, -110, totals_label,
            ha="center", va="center", fontsize=16, color=ctx["ink"],
            fontproperties=_fp_body(weight="bold"))

    return fig


def build_zone_volume_leaders_post(
    team_shots: pd.DataFrame,
    title: str = "Zone Volume Leaders",
    subtitle: str = "Chicago Bulls | 2025-26 Season",
    footnote: str = "Highest FGA by Court Area",
    min_shots: int = 5,
) -> plt.Figure:
    """Build a court map showing the top volume shooter per zone."""
    fig, ax, ctx = _build_court_canvas(title, subtitle, footnote)

    if team_shots.empty:
        ax.text(0, 130, "No shot data available", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    shots_detailed = analysis.detailed_zones(team_shots)
    leaders = analysis.zone_volume_leaders(shots_detailed, min_shots=min_shots)

    if not leaders:
        ax.text(0, 130, "No zone leaders found", ha="center", va="center",
                fontsize=16, color=ctx["ink"])
        return fig

    _draw_zone_borders(ax)
    _place_zone_text(ax, leaders, ctx["ink"], mode="volume")
    return fig


def save_feed_post(fig: plt.Figure, output_path: str, dpi: int = DEFAULT_DPI) -> Path:
    """
    Save a feed post figure to disk.

    Args:
        fig: Figure from a graphics builder
        output_path: Destination image path (e.g., output/feed/post.png)
        dpi: Export DPI

    Returns:
        Path to written image file.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, facecolor=fig.get_facecolor())
    return output
