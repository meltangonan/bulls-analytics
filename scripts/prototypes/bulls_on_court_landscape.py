"""Build the 2025-26 Bulls on-court performance landscape chart.

This is an idea-specific chart asset for external page assembly. It fetches
Chicago-filtered player totals and advanced ratings, writes the qualifying
analytical table, and renders a transparent Sticky Stats-style scatter asset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyBboxPatch

from bulls.data import get_team_advanced_stats, get_team_player_advanced_stats
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    body_font,
    export_dpi,
    rendered_width,
)


SEASON = "2025-26"
DEFAULT_MIN_MINUTES = 500
OUT = _REPO / "output" / "feed"
HEADSHOTS = _REPO / "cache" / "headshots"

CHART_WIDTH = 1080
CHART_HEIGHT = 1030
PANEL = (190, 175, 1015, 950)  # x0, y0, x1, y1
OFF_LIMITS = (102.8, 117.5)
DEF_LIMITS = (121.6, 111.8)  # lower defensive rating maps upward

# Small display offsets keep equal-size portraits legible. The true point and a
# fine connector remain anchored to each player's data coordinates.
DISPLAY_OFFSETS = {
    "Tre Jones": (-28, 16),
    "Ayo Dosunmu": (28, -16),
    "Collin Sexton": (-16, 10),
    "Rob Dillingham": (16, -10),
    "Josh Giddey": (-12, -5),
    "Nikola Vučević": (12, 5),
    "Jalen Smith": (-5, -18),
}

SHORT_NAMES = {
    "Matas Buzelis": "BUZELIS",
    "Tre Jones": "T. JONES",
    "Josh Giddey": "GIDDEY",
    "Isaac Okoro": "OKORO",
    "Nikola Vučević": "VUČEVIĆ",
    "Patrick Williams": "P. WILLIAMS",
    "Ayo Dosunmu": "DOSUNMU",
    "Jalen Smith": "J. SMITH",
    "Kevin Huerter": "HUERTER",
    "Coby White": "C. WHITE",
    "Collin Sexton": "SEXTON",
    "Rob Dillingham": "DILLINGHAM",
    "Guerschon Yabusele": "YABUSELE",
    "Leonard Miller": "L. MILLER",
}

HELVETICA_TTC = Path("/System/Library/Fonts/Helvetica.ttc")
HELVETICA_FACES = {"regular": 0, "bold": 1}
FONT_CACHE_DIR = _REPO / "cache" / "fonts"


def helvetica(weight: str = "regular") -> FontProperties:
    """Match the approved Sticky Stats chart typography."""
    fallback = "bold" if weight == "bold" else "medium"
    if not HELVETICA_TTC.exists():
        return body_font(fallback)
    extracted = FONT_CACHE_DIR / f"Helvetica-{weight}.ttf"
    if not extracted.exists():
        try:
            from fontTools.ttLib import TTCollection

            collection = TTCollection(str(HELVETICA_TTC))
            FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            collection.fonts[HELVETICA_FACES.get(weight, 0)].save(str(extracted))
        except Exception:
            return body_font(fallback)
    return FontProperties(fname=str(extracted))


def chart_x(value: float) -> float:
    x0, _, x1, _ = PANEL
    return x0 + (value - OFF_LIMITS[0]) / (OFF_LIMITS[1] - OFF_LIMITS[0]) * (x1 - x0)


def chart_y(value: float) -> float:
    _, y0, _, y1 = PANEL
    bottom, top = DEF_LIMITS
    return y0 + (bottom - value) / (bottom - top) * (y1 - y0)


def fetch_landscape(min_minutes: float):
    players = get_team_player_advanced_stats(season=SEASON)
    team = get_team_advanced_stats(season=SEASON)
    if players.empty or team.empty:
        raise RuntimeError("NBA.com returned no Bulls advanced data.")

    qualified = players.loc[players["MIN"] >= min_minutes].copy()
    qualified = qualified.sort_values("MIN", ascending=False).reset_index(drop=True)
    return players, qualified, team.iloc[0]


def write_table(qualified, min_minutes: float) -> Path:
    table = qualified[
        ["PLAYER_NAME", "MIN", "OFF_RATING", "DEF_RATING", "NET_RATING"]
    ].copy()
    table.columns = [
        "PLAYER", "BULLS_MIN", "OFF_RATING", "DEF_RATING", "NET_RATING"
    ]
    table["BULLS_MIN"] = table["BULLS_MIN"].round(1)
    for column in ["OFF_RATING", "DEF_RATING", "NET_RATING"]:
        table[column] = table[column].round(1)

    path = OUT / f"2026-07-22-bulls-on-court-landscape-min-{int(min_minutes)}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def square_headshot_label(ax, image_path: Path, x: float, y: float, half_size: float):
    """Place a top-anchored square crop without the shared circular mask."""
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(FancyBboxPatch(
            (x - half_size, y - half_size), 2 * half_size, 2 * half_size,
            boxstyle="square,pad=0",
            facecolor="#DDD8D1", edgecolor="none", zorder=8,
        ))

    height, width = image.shape[:2]
    side = min(height, width)
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=8,
    )


def render_chart_only(qualified, team, final: bool) -> Path:
    """Render the transparent chart asset for external page assembly."""
    theme = DEFAULT_THEME
    panel_fill = "#F5F1EC"
    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    x0, y0, x1, y1 = PANEL
    panel = FancyBboxPatch(
        (x0 - 16, y0 - 14), x1 - x0 + 30, y1 - y0 + 26,
        boxstyle="round,pad=0,rounding_size=12",
        facecolor=panel_fill, edgecolor="none", zorder=0,
    )
    ax.add_patch(panel)

    for value in [104, 107, 110, 113, 116]:
        x = chart_x(float(value))
        ax.plot([x, x], [y0, y1], color=theme.grid, lw=1.1, zorder=2)
        ax.plot([x, x], [y0, y0 - 10], color=theme.ink, lw=1.6, zorder=5)
        ax.text(
            x, y0 - 22, str(value), ha="center", va="top", fontsize=13,
            color=theme.ink, fontproperties=helvetica(),
        )
    for value in [120, 118, 116, 114, 112]:
        y = chart_y(float(value))
        ax.plot([x0, x1], [y, y], color=theme.grid, lw=1.1, zorder=2)
        ax.plot([x0, x0 - 10], [y, y], color=theme.ink, lw=1.6, zorder=5)
        ax.text(
            x0 - 20, y, str(value), ha="right", va="center", fontsize=13,
            color=theme.ink, fontproperties=helvetica(),
        )
    ax.plot([x0, x1], [y0, y0], color=theme.ink, lw=2.2, zorder=5)
    ax.plot([x0, x0], [y0, y1], color=theme.ink, lw=2.2, zorder=5)

    team_x = chart_x(float(team["OFF_RATING"]))
    team_y = chart_y(float(team["DEF_RATING"]))
    ax.plot(
        [team_x, team_x], [y0, y1], color=theme.muted, lw=1.2,
        linestyle=(0, (4, 4)), alpha=0.8, zorder=4,
    )
    ax.plot(
        [x0, x1], [team_y, team_y], color=theme.muted, lw=1.2,
        linestyle=(0, (4, 4)), alpha=0.8, zorder=4,
    )
    ax.text(
        team_x - 9, y1 - 14, f"TEAM OFF {team['OFF_RATING']:.1f}",
        ha="right", va="top", fontsize=9, color=theme.muted,
        fontproperties=helvetica("bold"), zorder=6,
    )
    ax.text(
        x1 - 9, team_y + 12, f"TEAM DEF {team['DEF_RATING']:.1f}",
        ha="right", va="bottom", fontsize=9, color=theme.muted,
        fontproperties=helvetica("bold"), zorder=6,
    )

    def quadrant_pill(anchor_x, anchor_y, ha, va, title, detail):
        title_probe = ax.text(
            0, 0, title, fontsize=10.5, fontproperties=helvetica("bold"), alpha=0,
        )
        title_width = rendered_width(ax, title_probe)
        title_probe.remove()
        detail_probe = ax.text(
            0, 0, detail, fontsize=9.5, fontproperties=helvetica(), alpha=0,
        )
        detail_width = rendered_width(ax, detail_probe)
        detail_probe.remove()
        box_w = max(title_width, detail_width) + 32
        box_h = 66
        left = anchor_x if ha == "left" else anchor_x - box_w
        bottom = anchor_y if va == "bottom" else anchor_y - box_h
        ax.add_patch(FancyBboxPatch(
            (left, bottom), box_w, box_h,
            boxstyle="round,pad=0,rounding_size=11",
            facecolor=theme.canvas, edgecolor=theme.rule,
            linewidth=1.0, alpha=0.94, zorder=10,
        ))
        ax.text(
            left + 16, bottom + box_h - 21, title,
            ha="left", va="center", fontsize=10.5, color=theme.ink,
            fontproperties=helvetica("bold"), zorder=11,
        )
        ax.text(
            left + 16, bottom + 20, detail,
            ha="left", va="center", fontsize=9.5, color=theme.muted,
            fontproperties=helvetica(), zorder=11,
        )

    quadrant_pill(
        x0 + 14, y1 - 14, "left", "top",
        "DEFENSE-LED", "better DEF, lower OFF",
    )
    quadrant_pill(
        x1 - 14, y1 - 14, "right", "top",
        "ABOVE TEAM AVG", "better OFF, better DEF",
    )
    quadrant_pill(
        x0 + 14, y0 + 14, "left", "bottom",
        "BELOW TEAM AVG", "lower OFF, lower DEF",
    )
    quadrant_pill(
        x1 - 14, y0 + 14, "right", "bottom",
        "OFFENSE-LED", "better OFF, lower DEF",
    )

    radius = 31
    for row in qualified.itertuples(index=False):
        true_x = chart_x(float(row.OFF_RATING))
        true_y = chart_y(float(row.DEF_RATING))
        dx, dy = DISPLAY_OFFSETS.get(row.PLAYER_NAME, (0, 0))
        point_x, point_y = true_x + dx, true_y + dy

        if dx or dy:
            ax.plot(
                [true_x, point_x], [true_y, point_y],
                color=theme.muted, lw=0.8, alpha=0.62, zorder=6,
            )
            ax.add_patch(Circle(
                (true_x, true_y), radius=2.8,
                facecolor=theme.muted, edgecolor=panel_fill, linewidth=0.7, zorder=7,
            ))

        image = square_headshot_label(
            ax, HEADSHOTS / f"{int(row.PLAYER_ID)}.png",
            point_x, point_y, half_size=radius,
        )
        image.set_zorder(8)

        label_y = point_y - radius - 7
        ax.text(
            point_x, label_y,
            SHORT_NAMES.get(row.PLAYER_NAME, row.PLAYER_NAME.upper()),
            ha="center", va="top", fontsize=7.8, color=theme.ink,
            fontproperties=helvetica("bold"), zorder=9,
        )

    ax.text(
        (x0 + x1) / 2, 92,
        "OFF RTG",
        ha="center", va="center", fontsize=15.5, color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    ax.text(
        78, (y0 + y1) / 2,
        "DEF RTG",
        ha="center", va="center", rotation=90, fontsize=15.5, color=theme.ink,
        fontproperties=helvetica("bold"),
    )

    output = OUT / "2026-07-22-bulls-on-court-landscape-chart.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-minutes", type=float, default=DEFAULT_MIN_MINUTES)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()

    all_players, qualified, team = fetch_landscape(args.min_minutes)
    table_path = write_table(qualified, args.min_minutes)
    image_path = render_chart_only(qualified, team, args.final)

    print(f"Qualified players: {len(qualified)} of {len(all_players)}")
    print(f"Team crosshairs: {team['OFF_RATING']:.1f} OFF, {team['DEF_RATING']:.1f} DEF")
    print(f"Wrote {table_path}")
    print(f"Wrote {image_path}")


if __name__ == "__main__":
    main()
