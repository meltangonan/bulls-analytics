"""Render Bulls national-media assignments by season for a Canva feed page.

The snapshot is deliberately hand-captured from contemporaneous schedule-release
sources. Historical broadcast feeds reflect later flex additions and removals,
which would answer a different question from the newly released 2026-27 count.

Python owns the transparent chart and exact copy block. Canva owns the title,
subtitle, methodology/source line, background, and handle.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch

from bulls.graphics.house import DEFAULT_THEME, export_dpi, helvetica

SLUG = "2026-08-13-bulls-national-tv-history"
PROJECT = _REPO / "docs" / "visuals" / SLUG
SNAPSHOT = PROJECT / "data" / "bulls-national-tv-by-season.csv"
CURRENT_GAMES = PROJECT / "data" / "bulls-2026-27-national-games.csv"
CURRENT_COMPARISON = PROJECT / "data" / "2026-27-current-team-comparison.csv"
OUT = _REPO / "output" / SLUG

NETWORK_FIELDS = ("abc", "espn", "tnt", "nbc", "nbcsn", "peacock", "prime_video")
CHART_WIDTH = 1800
CHART_HEIGHT = 1050
DRAFT_DPI = 150
HISTORICAL_BAR_GRADIENT = ("#333333", "#0C0C0C")
CURRENT_BAR_GRADIENT = ("#B5123C", "#7E0C2B")
HISTORICAL_BAR_SHADOW = "#5A5048"
CURRENT_BAR_SHADOW = "#7A1230"


@dataclass(frozen=True)
class Season:
    season: str
    abc: int
    espn: int
    tnt: int
    nbc: int
    nbcsn: int
    peacock: int
    prime_video: int
    total: int
    release_type: str
    source_url: str
    secondary_source_url: str
    source_note: str

    @property
    def network_sum(self) -> int:
        return sum(getattr(self, field) for field in NETWORK_FIELDS)


def load_seasons(path: Path = SNAPSHOT) -> list[Season]:
    """Load and validate the committed schedule-release snapshot."""
    with path.open(encoding="utf-8") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        seasons = [
            Season(
                season=row["season"],
                **{field: int(row[field]) for field in NETWORK_FIELDS},
                total=int(row["total"]),
                release_type=row["release_type"],
                source_url=row["source_url"],
                secondary_source_url=row["secondary_source_url"],
                source_note=row["source_note"],
            )
            for row in rows
        ]
    if not seasons:
        raise ValueError(f"No seasons found in {path}")
    if any(season.total != season.network_sum for season in seasons):
        raise ValueError("A season total does not equal its network components")
    return seasons


def load_current_comparison(path: Path = CURRENT_COMPARISON) -> dict[str, int]:
    """Load the two-team current-season context used in the Canva copy."""
    with path.open(encoding="utf-8") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        return {row["team"]: int(row["national_games"]) for row in rows}


def order_seasons(seasons: list[Season], *, descending: bool = False) -> list[Season]:
    """Return seasons in the requested chronological display order."""
    return sorted(seasons, key=lambda season: season.season, reverse=descending)


def _short_label(season: Season) -> str:
    start, end = season.season.split("-")
    label = f"{start[-2:]}–{end[-2:]}"
    return f"{label}*" if season.release_type == "split" else label


def render_chart(seasons: list[Season], *, final: bool = False) -> Path:
    """Render one transparent bar-chart asset for placement in Canva."""
    theme = DEFAULT_THEME
    label_font = helvetica()
    bold_font = helvetica("bold")

    fig, ax = plt.subplots(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    x = list(range(len(seasons)))
    latest_season = max(season.season for season in seasons)
    colors = [
        theme.accent if season.season == latest_season else theme.contrast
        for season in seasons
    ]
    bars = ax.bar(x, [season.total for season in seasons], width=0.68, color=colors, zorder=3)

    for bar, season in zip(bars, seasons):
        color = CURRENT_BAR_GRADIENT[1] if season.season == latest_season else theme.ink
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            season.total + 0.65,
            str(season.total),
            ha="center",
            va="bottom",
            color=color,
            fontproperties=bold_font,
            fontsize=15,
            zorder=5,
        )

    ax.set_xlim(-0.75, len(seasons) - 0.25)
    ax.set_ylim(0, 29)
    ax.set_xticks(x, [_short_label(season) for season in seasons])
    ax.tick_params(axis="x", length=0, pad=9, colors=theme.muted, labelsize=10)
    for label in ax.get_xticklabels():
        label.set_fontproperties(bold_font)
        label.set_rotation(45)
        label.set_ha("right")

    ax.set_yticks(range(0, 30, 5))
    ax.tick_params(axis="y", length=0, pad=8, colors=theme.muted, labelsize=10)
    for label in ax.get_yticklabels():
        label.set_fontproperties(label_font)
    ax.set_ylabel(
        "SCHEDULED NATIONAL GAMES",
        color=theme.muted,
        fontproperties=bold_font,
        fontsize=11,
        labelpad=18,
    )

    ax.yaxis.grid(True, color=theme.grid, linewidth=1.2, zorder=0)
    ax.xaxis.grid(False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme.rule)
    ax.spines["bottom"].set_linewidth(1.1)

    fig.subplots_adjust(left=0.075, right=0.99, top=0.94, bottom=0.19)
    OUT.mkdir(parents=True, exist_ok=True)
    resolution = "final" if final else "draft"
    order = "descending" if seasons[0].season == latest_season else "ascending"
    output = OUT / f"2026-08-13-bulls-national-tv-games-{order}-{resolution}.png"
    fig.savefig(output, dpi=export_dpi(final), transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return output


def render_horizontal_chart(seasons: list[Season], *, final: bool = False) -> Path:
    """Render a transparent horizontal bar chart for placement in Canva."""
    theme = DEFAULT_THEME
    label_font = helvetica()
    bold_font = helvetica("bold")
    latest_season = max(season.season for season in seasons)

    fig, ax = plt.subplots(figsize=(CHART_WIDTH / DRAFT_DPI, 1350 / DRAFT_DPI))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    y = list(range(len(seasons)))
    bar_height = 0.68
    for row_y, season in zip(y, seasons):
        gradient = (
            CURRENT_BAR_GRADIENT
            if season.season == latest_season
            else HISTORICAL_BAR_GRADIENT
        )
        shadow = (
            CURRENT_BAR_SHADOW
            if season.season == latest_season
            else HISTORICAL_BAR_SHADOW
        )
        _draw_gradient_bar(ax, 0, season.total, row_y, bar_height, gradient, shadow)
        color = theme.accent if season.season == latest_season else theme.ink
        ax.text(
            season.total + 0.45,
            row_y,
            str(season.total),
            ha="left",
            va="center",
            color=color,
            fontproperties=bold_font,
            fontsize=15,
            zorder=5,
        )

    ax.set_xlim(-0.35, 29)
    ax.set_yticks(y, [_short_label(season) for season in seasons])
    # Leave enough room above the newest bar for its rounded edge, cast shadow,
    # and value label to survive the transparent tight crop.
    ax.set_ylim(len(seasons) - 0.45, -0.78)
    ax.tick_params(axis="y", length=0, pad=10, colors=theme.muted, labelsize=13)
    for label in ax.get_yticklabels():
        label.set_fontproperties(bold_font)

    ax.set_xticks(range(0, 30, 5))
    ax.tick_params(axis="x", length=0, pad=8, colors=theme.muted, labelsize=10)
    for label in ax.get_xticklabels():
        label.set_fontproperties(label_font)
    ax.set_xlabel(
        "SCHEDULED NATIONAL GAMES",
        color=theme.muted,
        fontproperties=bold_font,
        fontsize=11,
        labelpad=14,
    )

    ax.xaxis.grid(True, color=theme.grid, linewidth=1.2, zorder=0)
    # Keep the numeric zero tick without drawing a vertical rule through the
    # rounded bar starts. The first visible gridline is five games.
    ax.get_xgridlines()[0].set_visible(False)
    ax.yaxis.grid(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    fig.subplots_adjust(left=0.12, right=0.985, top=0.985, bottom=0.10)
    OUT.mkdir(parents=True, exist_ok=True)
    resolution = "final" if final else "draft"
    order = "descending" if seasons[0].season == latest_season else "ascending"
    output = OUT / (
        f"2026-08-13-bulls-national-tv-games-horizontal-{order}-black-red-{resolution}.png"
    )
    fig.savefig(output, dpi=export_dpi(final), transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return output


def _draw_gradient_bar(ax, x0, x1, y, height, colors, shadow_color) -> None:
    """Draw one assist-duos-style rounded red bar with a soft cast shadow."""
    rounding = height * 0.28
    shape = dict(
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        edgecolor="none",
        linewidth=0,
    )
    shadow = FancyBboxPatch(
        (x0, y - height / 2),
        x1 - x0,
        height,
        facecolor=colors[1],
        path_effects=[
            PathEffects.withSimplePatchShadow(
                offset=(1.5, -2), shadow_rgbFace=shadow_color, alpha=0.30, rho=0.9
            ),
            PathEffects.Normal(),
        ],
        zorder=3,
        **shape,
    )
    ax.add_patch(shadow)

    clip = FancyBboxPatch(
        (x0, y - height / 2),
        x1 - x0,
        height,
        facecolor="none",
        zorder=4,
        **shape,
    )
    ax.add_patch(clip)

    top, bottom = (np.array(to_rgb(color)) for color in colors)
    ramp = np.linspace(bottom, top, 256).reshape(256, 1, 3)
    image = ax.imshow(
        ramp,
        extent=(x0, x1, y - height / 2, y + height / 2),
        origin="lower",
        aspect="auto",
        interpolation="bicubic",
        zorder=4,
    )
    image.set_clip_path(clip)


def copy_block(seasons: list[Season], comparison: dict[str, int]) -> str:
    peak = max(seasons, key=lambda season: season.total)
    current = seasons[-1]
    return "\n".join(
        [
            "CANVA COPY",
            "Title: BULLS NATIONAL TV GAMES, BY SEASON",
            "Subtitle: From the Rose-era spotlight to 3 games in 2026–27",
            (
                "Method: Original regular-season schedule assignments on the NBA's main "
                "national partners. Excludes NBA TV, local broadcasts, playoffs and later flexes."
            ),
            "Footnote: *2020–21 combines the NBA's separately released first- and second-half schedules.",
            "Source: NBA, Chicago Bulls and national network schedule releases",
            f"Check: peak {peak.total} ({peak.season}); current {current.total} ({current.season})",
            (
                "Current context: New York has "
                f"{comparison['New York Knicks']} scheduled national games in 2026–27."
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true", help="render the full-resolution chart asset")
    parser.add_argument(
        "--descending",
        action="store_true",
        help="place the newest season first in the chart",
    )
    parser.add_argument(
        "--horizontal",
        action="store_true",
        help="place counts on the x-axis and seasons on the y-axis",
    )
    args = parser.parse_args()

    seasons = load_seasons()
    comparison = load_current_comparison()
    displayed_seasons = order_seasons(seasons, descending=args.descending)
    renderer = render_horizontal_chart if args.horizontal else render_chart
    output = renderer(displayed_seasons, final=args.final)
    print(f"Saved {output.relative_to(_REPO)}")
    print()
    print(copy_block(seasons, comparison))


if __name__ == "__main__":
    main()
