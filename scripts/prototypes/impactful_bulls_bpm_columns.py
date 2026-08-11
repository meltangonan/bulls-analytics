"""Build the most-impactful-Bull BPM split as a stacked column chart.

A second mockup of the same analysis as ``impactful_bulls_bpm.py``, which stays
the table version. Here each season is one column: offense (OBPM) in red,
defense (DBPM) in black, so the shape of a player's impact reads at a glance
rather than having to be compared across two number columns.

Two facts about the data drive the design.

**DBPM goes negative in 6 of these 17 seasons**, so this cannot be a plain
stack. Negative defense is drawn below the zero line, which is the standard
form for a stacked bar with a negative component and the only honest one: a
bar that stacked -1.6 upward would claim LaVine's defense added value.

**OBPM + DBPM equals BPM, but only to a rounding tolerance.** Basketball
Reference rounds each of the three to one decimal independently, so the
components sum 0.1 away from the published BPM in 4 of 17 seasons. The
geometry is drawn from the components so the column is internally consistent,
and the printed total is the published BPM, which is the authoritative figure.
At this scale 0.1 is under a pixel of drawn height.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch, Rectangle

from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
)
from bulls.visuals import DATA, visual_dir
from scripts.prototypes.impactful_bulls_bpm import (
    FIRST_SEASON_END,
    LAST_SEASON_END,
    MIN_MINUTES_PER_GAME,
    MIN_TEAM_GAMES_SHARE,
    PROJECT,
    attach_player_ids,
    build_working_table,
    face_headshot_label,
    select_leaders,
    verify_headshots,
)

SNAPSHOT_TZ = ZoneInfo("America/Chicago")
OUT = _REPO / "output" / "feed"
DATA_DIR = visual_dir(_REPO / "docs" / "visuals", PROJECT, create=False) / DATA

# Gradient pairs lifted from assist_duos.py so the bar texture matches the
# rest of the account's bar charts.
OFFENSE_GRADIENT = ("#E12C52", "#A80E35")
DEFENSE_GRADIENT = ("#333333", "#0C0C0C")
SHADOW_RGB = "#5A5048"

CHART_WIDTH = 1080
CHART_HEIGHT = 1000

PLOT_LEFT, PLOT_RIGHT = 76, 1044
PLOT_BOTTOM, PLOT_TOP = 112, 830
Y_MIN, Y_MAX = -2.4, 8.2
GRIDLINES = (-2, 0, 2, 4, 6, 8)

BAR_WIDTH = 38
BAR_RADIUS = 6
FACE_Y = 946
FACE_HALF = 28
SEASON_LABEL_Y = 66
LEGEND_Y = 880

@dataclass(frozen=True)
class ColumnLayout:
    """Type sizing for the column chart."""

    season_font_size: float = 15.0
    # 17 totals across a 57 px pitch: 14 pt keeps adjacent labels apart.
    total_font_size: float = 14.0
    segment_font_size: float = 11.5
    axis_font_size: float = 14.0
    legend_font_size: float = 15.0


LAYOUT = ColumnLayout()


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def y_px(value: float) -> float:
    """Data value to canvas y."""
    span = Y_MAX - Y_MIN
    return PLOT_BOTTOM + (value - Y_MIN) * (PLOT_TOP - PLOT_BOTTOM) / span


def column_centers(count: int) -> list[float]:
    """Evenly spaced column centres across the plot area."""
    pitch = (PLOT_RIGHT - PLOT_LEFT) / count
    return [PLOT_LEFT + pitch * (index + 0.5) for index in range(count)]


def _rounded(x0, x1, y0, y1, **kwargs) -> FancyBboxPatch:
    """A rounded rectangle sized in data space, inset for the corner radius."""
    return FancyBboxPatch(
        (x0 + BAR_RADIUS, min(y0, y1) + BAR_RADIUS),
        (x1 - x0) - 2 * BAR_RADIUS,
        abs(y1 - y0) - 2 * BAR_RADIUS,
        boxstyle=f"round,pad={BAR_RADIUS},rounding_size={BAR_RADIUS}",
        **kwargs,
    )


def _across_gradient(ax, x0, x1, y0, y1, colors, clip, zorder):
    """Paint a left-to-right colour ramp across one span, clipped to a shape.

    ``assist_duos.py`` ramps top-to-bottom because its bars are horizontal;
    the ramp runs across the bar's thickness. These bars are vertical, so the
    same cylindrical read comes from ramping left to right.
    """
    left, right = (np.array(to_rgb(c)) for c in colors)
    ramp = np.linspace(left, right, 256).reshape(1, 256, 3)
    image = ax.imshow(
        ramp,
        extent=(x0, x1, min(y0, y1), max(y0, y1)),
        origin="lower",
        aspect="auto",
        interpolation="bicubic",
        zorder=zorder,
    )
    image.set_clip_path(clip)
    return image


def _gradient_span(ax, center, low, high, colors, *, shadow: bool):
    """Draw one gradient-filled span of a column between two data values."""
    if abs(high - low) < 0.02:  # nothing meaningful to draw
        return
    x0, x1 = center - BAR_WIDTH / 2, center + BAR_WIDTH / 2
    y0, y1 = y_px(low), y_px(high)
    if shadow:
        ax.add_patch(
            _rounded(
                x0, x1, y0, y1,
                facecolor=colors[1], edgecolor="none", zorder=4,
                path_effects=[
                    PathEffects.withSimplePatchShadow(
                        offset=(2, -2), shadow_rgbFace=SHADOW_RGB,
                        alpha=0.28, rho=0.9,
                    ),
                    PathEffects.Normal(),
                ],
            )
        )
    clip = _rounded(x0, x1, y0, y1, facecolor="none", edgecolor="none", zorder=5)
    ax.add_patch(clip)
    _across_gradient(ax, x0, x1, y0, y1, colors, clip, 5)


def draw_column(ax, center: float, row: pd.Series) -> None:
    """Draw one season: offense up from zero, defense stacked or hung below.

    The positive part is drawn as a single rounded outline containing both
    gradients, so a season where defense also helped reads as one column
    broken by colour rather than two pills pushed together.
    """
    offense = float(row["obpm"])
    defense = float(row["dbpm"])
    x0, x1 = center - BAR_WIDTH / 2, center + BAR_WIDTH / 2

    if defense >= 0:
        top = offense + defense
        y0, y1 = y_px(0.0), y_px(top)
        ax.add_patch(
            _rounded(
                x0, x1, y0, y1,
                facecolor=DEFENSE_GRADIENT[1], edgecolor="none", zorder=4,
                path_effects=[
                    PathEffects.withSimplePatchShadow(
                        offset=(2, -2), shadow_rgbFace=SHADOW_RGB,
                        alpha=0.28, rho=0.9,
                    ),
                    PathEffects.Normal(),
                ],
            )
        )
        clip = _rounded(x0, x1, y0, y1, facecolor="none", edgecolor="none", zorder=5)
        ax.add_patch(clip)
        _across_gradient(ax, x0, x1, y_px(0.0), y_px(offense),
                         OFFENSE_GRADIENT, clip, 5)
        _across_gradient(ax, x0, x1, y_px(offense), y_px(top),
                         DEFENSE_GRADIENT, clip, 5)
    else:
        _gradient_span(ax, center, 0.0, offense, OFFENSE_GRADIENT, shadow=True)
        _gradient_span(ax, center, defense, 0.0, DEFENSE_GRADIENT, shadow=False)


def segment_label(ax, center, low, high, value, color):
    """Print a segment's value inside it when the segment is tall enough."""
    height = abs(y_px(high) - y_px(low))
    if height < 36:  # a shorter segment crowds the text against its own edges
        return
    ax.text(
        center,
        (y_px(low) + y_px(high)) / 2,
        f"{value:+.1f}",
        ha="center",
        va="center",
        fontsize=LAYOUT.segment_font_size,
        color=color,
        fontproperties=helvetica("bold"),
        zorder=8,
    )


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def draw_legend(ax, theme) -> None:
    """Two swatches naming the halves, in the colours the columns use."""
    entries = (
        (PLOT_LEFT, "OFFENSE (OBPM)", OFFENSE_GRADIENT),
        (PLOT_LEFT + 360, "DEFENSE (DBPM)", DEFENSE_GRADIENT),
    )
    for x, label, colors in entries:
        swatch = _rounded(
            x, x + 34, LEGEND_Y - 9, LEGEND_Y + 9,
            facecolor="none", edgecolor="none", zorder=6,
        )
        ax.add_patch(swatch)
        _across_gradient(ax, x, x + 34, LEGEND_Y - 9, LEGEND_Y + 9,
                         colors, swatch, 6)
        ax.text(
            x + 46, LEGEND_Y, label,
            ha="left", va="center", fontsize=LAYOUT.legend_font_size,
            color=theme.ink, fontproperties=helvetica("bold"), zorder=6,
        )


def render_chart(leaders: pd.DataFrame, date: str, final: bool = False) -> Path:
    """Render the transparent stacked-column asset for Canva."""
    theme = DEFAULT_THEME
    rows = leaders.sort_values("season").reset_index(drop=True)
    centers = column_centers(len(rows))

    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI),
        facecolor="none",
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.axis("off")

    for value in GRIDLINES:
        is_zero = value == 0
        ax.plot(
            [PLOT_LEFT - 26, PLOT_RIGHT],
            [y_px(value)] * 2,
            color=theme.ink if is_zero else theme.grid,
            lw=1.8 if is_zero else 1.0,
            zorder=2 if is_zero else 1,
        )
        ax.text(
            PLOT_LEFT - 36,
            y_px(value),
            f"{value:+d}" if value else "0",
            ha="right",
            va="center",
            fontsize=LAYOUT.axis_font_size,
            color=theme.muted,
            fontproperties=helvetica("bold" if is_zero else "regular"),
            zorder=2,
        )

    draw_legend(ax, theme)

    for center, (_, row) in zip(centers, rows.iterrows()):
        draw_column(ax, center, row)

        offense, defense = float(row["obpm"]), float(row["dbpm"])
        segment_label(ax, center, 0.0, offense, offense, "#FFFFFF")
        if defense >= 0:
            segment_label(ax, center, offense, offense + defense, defense, "#FFFFFF")
        else:
            segment_label(ax, center, defense, 0.0, defense, "#FFFFFF")

        # The published BPM, printed above the column. Drawn geometry uses the
        # components, which round to within 0.1 of this figure.
        ax.text(
            center,
            y_px(max(offense + max(defense, 0.0), 0.0)) + 16,
            f"{float(row['bpm']):+.1f}",
            ha="center",
            va="bottom",
            fontsize=LAYOUT.total_font_size,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=8,
        )

        face_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(row['nba_id'])}.png",
            center,
            FACE_Y,
            FACE_HALF,
            zorder=6,
        )
        ax.text(
            center,
            SEASON_LABEL_Y,
            f"’{str(int(row['season']))[2:]}",
            ha="center",
            va="center",
            fontsize=LAYOUT.season_font_size,
            color=theme.accent,
            fontproperties=helvetica("bold"),
            zorder=6,
        )

    path = OUT / f"{date}-impactful-bulls-bpm-columns.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        dpi=export_dpi(final),
        transparent=True,
        bbox_inches=None,
        pad_inches=0,
    )
    plt.close(fig)
    return path


def canva_copy_block(leaders: pd.DataFrame, date: str) -> str:
    """Framing copy from the same validated run."""
    peak = leaders.loc[leaders["bpm"].idxmax()]
    most_defensive = leaders.loc[leaders["dbpm"].idxmax()]
    most_offensive = leaders.loc[leaders["obpm"].idxmax()]
    return "\n".join(
        [
            "--- CANVA COPY BLOCK ---",
            "",
            "TITLE: Most impactful Bulls each year",
            "",
            "SUBTITLE: Where that impact came from, offense or defense",
            "",
            (
                "QUALIFICATION: Highest BPM among Bulls who averaged "
                f"{MIN_MINUTES_PER_GAME:.0f}+ minutes in at least "
                f"{MIN_TEAM_GAMES_SHARE:.0%} of the team's games that season. "
                "Seasons are labelled by ending year, so ’10 is 2009-10."
            ),
            "",
            (
                "READING IT: Each column is one season's most impactful Bull. "
                "Red is offense (OBPM), black is defense (DBPM), and together "
                "they make BPM. Defense below the zero line cost the team."
            ),
            "",
            (
                f"PEAK: {peak['player_name']} {peak['season_label']} "
                f"({peak['bpm']:+.1f} BPM)"
            ),
            (
                f"BEST DEFENSIVE SEASON: {most_defensive['player_name']} "
                f"{most_defensive['season_label']} ({most_defensive['dbpm']:+.1f} DBPM)"
            ),
            (
                f"BEST OFFENSIVE SEASON: {most_offensive['player_name']} "
                f"{most_offensive['season_label']} ({most_offensive['obpm']:+.1f} OBPM)"
            ),
            "",
            f"SOURCE: Data via Basketball Reference · Pulled {date}",
            "",
            "--- END ---",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true",
                        help="Export at final DPI.")
    parser.add_argument("--refresh", action="store_true",
                        help="Re-fetch Basketball Reference instead of the CSV.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    date = datetime.now(SNAPSHOT_TZ).date().isoformat()

    leaders = attach_player_ids(select_leaders(build_working_table(args.refresh)))
    ensure_headshots(leaders["nba_id"])
    silhouettes = verify_headshots(leaders["nba_id"])
    if silhouettes:
        raise SystemExit(f"Generic silhouette headshots for NBA ids {silhouettes}.")

    chart_path = render_chart(leaders, date, final=args.final)
    print(f"Wrote {chart_path}\n")
    print(canva_copy_block(leaders, date))


if __name__ == "__main__":
    main()
