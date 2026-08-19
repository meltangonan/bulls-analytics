"""Render the top Bulls rookie seasons by an equal-weight six-category rank.

The analysis population is Bulls regular-season rookies since 2000-01 with at
least 1,000 minutes. Players are ranked in PTS, REB, AST, STL+BLK, TS%, and Win
Shares; tied category values receive their average rank, and the lowest average
category rank wins. Team record and change from the prior season are context
only. The renderer is a transparent Canva asset in the compact headshot-table
family used by the scoring- and assist-leaders-by-age posts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from bulls.graphics.house import (
    DEFAULT_THEME,
    HEADSHOT_CACHE,
    ensure_headshots,
    helvetica,
)
from bulls.visuals import ASSETS, visual_dir
from scripts.prototypes.bulls_rookie_metric_analysis import RANKING_CSV

PROJECT = "bulls-rookie-landscape"
TOP_N = 10
CHART_WIDTH = 1080
ROW_HEIGHT = 78
HEADER_HEIGHT = 88
BOTTOM_PAD = 28
CHART_HEIGHT = HEADER_HEIGHT + TOP_N * ROW_HEIGHT + BOTTOM_PAD

RANK_X = 34
HEADSHOT_X = 90
NAME_X = 137
METRIC_X = {
    "ppg": 430,
    "rpg": 504,
    "apg": 578,
    "stocks_per_game": 670,
    "ts_pct": 768,
    "ws": 848,
}
AVG_LEFT = 908
AVG_RIGHT = 1060
ROW_RULE_LEFT = 18
ROW_RULE_RIGHT = AVG_LEFT - 8

ASSET_DIR = visual_dir(_REPO / "docs" / "visuals", PROJECT) / ASSETS
DEFAULT_OUTPUT = ASSET_DIR / "2026-08-15-v01-bulls-rookie-composite-table.png"


def _format_rank(value: float) -> str:
    """Print tied average ranks without a meaningless trailing decimal."""
    return f"#{value:.0f}" if float(value).is_integer() else f"#{value:.1f}"


def _context(row: pd.Series) -> str:
    """Season, team record, and honest year-over-year team change."""
    if pd.notna(row["team_win_change"]):
        change = int(row["team_win_change"])
        change_text = f"{change:+d} wins"
    else:
        points = float(row["team_win_pct_change"]) * 100
        change_text = f"{points:+.1f} win% pts"
    season = str(row["season_label"]).replace("-", "–", 1)
    record = str(row["team_record"]).replace("-", "–", 1)
    return f"{season}  ·  {record}  ·  {change_text}"


def _table_headshot(ax, image_path: Path, x: float, y: float, half: float) -> None:
    """Crop to the head and shoulders so a later team's jersey is not prominent."""
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        ax.add_patch(
            FancyBboxPatch(
                (x - half, y - half), 2 * half, 2 * half,
                boxstyle="square,pad=0", facecolor="#DDD8D1", edgecolor="none", zorder=5,
            )
        )
        return
    height, width = image.shape[:2]
    side = min(int(height * 0.74), width)
    left = max(0, (width - side) // 2)
    crop = image[:side, left:left + side]
    ax.imshow(
        crop,
        extent=[x - half, x + half, y - half, y + half],
        interpolation="bilinear",
        zorder=5,
    )


def _draw_average_card(ax, row_count: int, first_y: float) -> None:
    """Draw the continuous Bulls-red result column used by recent table posts."""
    top = first_y + ROW_HEIGHT / 2 + 10
    bottom = first_y - (row_count - 1) * ROW_HEIGHT - ROW_HEIGHT / 2 - 10
    shape = dict(boxstyle="round,pad=0,rounding_size=14", edgecolor="none")
    card = FancyBboxPatch(
        (AVG_LEFT, bottom),
        AVG_RIGHT - AVG_LEFT,
        top - bottom,
        facecolor=DEFAULT_THEME.accent,
        zorder=2,
        path_effects=[
            PathEffects.withSimplePatchShadow(
                offset=(2.5, -3), shadow_rgbFace="#7A1230", alpha=0.30, rho=0.85
            ),
            PathEffects.Normal(),
        ],
        **shape,
    )
    ax.add_patch(card)
    clip = FancyBboxPatch(
        (AVG_LEFT, bottom),
        AVG_RIGHT - AVG_LEFT,
        top - bottom,
        facecolor="none",
        zorder=2,
        **shape,
    )
    ax.add_patch(clip)
    top_rgb = np.array([225, 44, 82]) / 255
    bottom_rgb = np.array([158, 12, 46]) / 255
    ramp = np.linspace(top_rgb, bottom_rgb, 512).reshape(512, 1, 3)
    image = ax.imshow(
        ramp,
        extent=[AVG_LEFT, AVG_RIGHT, bottom, top],
        origin="upper",
        aspect="auto",
        zorder=2.1,
    )
    image.set_clip_path(clip)


def validate_ranking(ranking: pd.DataFrame) -> None:
    """Fail before rendering if the published ranking cannot be audited."""
    required = {
        "composite_rank",
        "average_category_rank",
        "player_id",
        "player_name",
        "season_label",
        "team_record",
        "team_win_change",
        "team_win_pct_change",
        "ppg",
        "rpg",
        "apg",
        "stocks_per_game",
        "ts_pct",
        "ws",
        "rank_ppg",
        "rank_rpg",
        "rank_apg",
        "rank_stocks_per_game",
        "rank_ts_pct",
        "rank_ws",
    }
    missing = required - set(ranking.columns)
    if missing:
        raise ValueError(f"Composite ranking is missing {sorted(missing)}")
    if len(ranking) != 23:
        raise ValueError(f"Expected 23 qualified rookie seasons, found {len(ranking)}")
    rank_columns = [
        "rank_ppg",
        "rank_rpg",
        "rank_apg",
        "rank_stocks_per_game",
        "rank_ts_pct",
        "rank_ws",
    ]
    expected = ranking[rank_columns].mean(axis=1)
    if not np.allclose(expected, ranking["average_category_rank"]):
        raise ValueError("Average category ranks do not reconcile to the six inputs")
    if ranking["player_id"].duplicated().any():
        raise ValueError("Composite ranking contains duplicate rookie seasons")


def render_table(ranking: pd.DataFrame, output_path: Path = DEFAULT_OUTPUT) -> Path:
    """Render one transparent top-10 table asset for Canva."""
    validate_ranking(ranking)
    leaders = ranking.head(TOP_N).copy()
    ensure_headshots(leaders["player_id"])

    theme = DEFAULT_THEME
    fig = plt.figure(figsize=(CHART_WIDTH / 100, CHART_HEIGHT / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.axis("off")

    first_y = CHART_HEIGHT - HEADER_HEIGHT - ROW_HEIGHT / 2
    _draw_average_card(ax, len(leaders), first_y)

    header_y = CHART_HEIGHT - 38
    header_font = helvetica("bold")
    body_font = helvetica("regular")
    bold_font = helvetica("bold")
    ax.text(RANK_X, header_y, "#", ha="center", va="center", fontsize=13,
            color=theme.muted, fontproperties=header_font)
    ax.text(NAME_X, header_y, "ROOKIE", ha="left", va="center", fontsize=13,
            color=theme.ink, fontproperties=header_font)
    headers = {
        "ppg": "PTS",
        "rpg": "REB",
        "apg": "AST",
        "stocks_per_game": "STL+BLK",
        "ts_pct": "TS%",
        "ws": "WS",
    }
    for metric, label in headers.items():
        ax.text(METRIC_X[metric], header_y, label, ha="center", va="center",
                fontsize=12.5, color=theme.ink, fontproperties=header_font)
    ax.text((AVG_LEFT + AVG_RIGHT) / 2, header_y, "AVG RANK", ha="center", va="center",
            fontsize=12.5, color=theme.accent, fontproperties=header_font)
    ax.plot([ROW_RULE_LEFT, AVG_RIGHT], [CHART_HEIGHT - HEADER_HEIGHT, CHART_HEIGHT - HEADER_HEIGHT],
            color=theme.ink, linewidth=1.5, zorder=1)

    value_formats = {
        "ppg": lambda value: f"{value:.1f}",
        "rpg": lambda value: f"{value:.1f}",
        "apg": lambda value: f"{value:.1f}",
        "stocks_per_game": lambda value: f"{value:.1f}",
        "ts_pct": lambda value: f"{value * 100:.1f}%",
        "ws": lambda value: f"{value:.1f}",
    }

    for index, (_, row) in enumerate(leaders.iterrows()):
        y = first_y - index * ROW_HEIGHT
        bottom_rule = y - ROW_HEIGHT / 2
        if index < len(leaders) - 1:
            ax.plot([ROW_RULE_LEFT, ROW_RULE_RIGHT], [bottom_rule, bottom_rule],
                    color=theme.rule, linewidth=1.2, zorder=1)

        tied = int((leaders["composite_rank"] == row["composite_rank"]).sum()) > 1
        placement = f"T{int(row['composite_rank'])}" if tied else f"{int(row['composite_rank'])}"
        ax.text(RANK_X, y, placement, ha="center", va="center",
                fontsize=18, color=theme.accent, fontproperties=bold_font, zorder=5)
        _table_headshot(
            ax,
            HEADSHOT_CACHE / f"{int(row['player_id'])}.png",
            HEADSHOT_X,
            y + 2,
            36,
        )
        ax.text(NAME_X, y + 11, str(row["player_name"]), ha="left", va="center",
                fontsize=16.5, color=theme.ink, fontproperties=bold_font, zorder=5)
        ax.text(NAME_X, y - 17, _context(row), ha="left", va="center",
                fontsize=9.5, color=theme.muted, fontproperties=body_font, zorder=5)

        for metric in headers:
            x = METRIC_X[metric]
            ax.text(x, y + 8, value_formats[metric](float(row[metric])),
                    ha="center", va="center", fontsize=14.5, color=theme.ink,
                    fontproperties=bold_font, zorder=5)
            ax.text(x, y - 17, _format_rank(float(row[f"rank_{metric}"])),
                    ha="center", va="center", fontsize=9.5, color=theme.accent,
                    fontproperties=bold_font, zorder=5)

        ax.text((AVG_LEFT + AVG_RIGHT) / 2, y,
                f"{float(row['average_category_rank']):.1f}",
                ha="center", va="center", fontsize=19, color="white",
                fontproperties=bold_font, zorder=5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100, transparent=True, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return output_path


def canva_copy() -> str:
    """Exact framing copy generated alongside the analytical asset."""
    return "\n".join(
        [
            "TOP BULLS ROOKIE SEASONS SINCE 2000",
            "Each rookie is ranked in PTS, REB, AST, STL+BLK, TS% and Win Shares. Lowest average rank wins.",
            "Minimum 1,000 minutes · Regular season only · Team record shown for context",
            "Sources: NBA.com and Basketball Reference",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking-csv", type=Path, default=RANKING_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    ranking = pd.read_csv(args.ranking_csv)
    output = render_table(ranking, args.output)
    print(f"Wrote {output}")
    print("\nCanva copy:\n" + canva_copy())


if __name__ == "__main__":
    main()
