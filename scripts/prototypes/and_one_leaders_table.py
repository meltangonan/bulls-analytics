"""Render the top Bulls and-1 seasons as a table-bar hybrid."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.graphics import house
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica


DEFAULT_DATA = _REPO / "docs/visuals/2026-09-16-and-one-leaders/data/top15.csv"
DEFAULT_OUTPUT = _REPO / "output/and-one-leaders/table.png"
PRIMARY_HEADSHOTS = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")

# Geometry follows pull_up_points_bars.py; two wider support columns replace three.
WIDTH = 2600
ROW_HEIGHT = 190
TOP_BOTTOM = 175
PORTRAIT_X = 150
PORTRAIT_HALF = 105
NAME_X = 315
BAR_LEFT = 930
BAR_RIGHT = 1700
BAR_HEIGHT = 104
SUPPORT_X = (1965, 2350)
INK = house.BLACK
RED = house.RED
GREY = "#5F5B57"
SEASON_GREY = "#6E6963"
RULE = "#B8B0A8"


def _portrait_path(player_id: int) -> Path:
    primary = PRIMARY_HEADSHOTS / f"{int(player_id)}.png"
    return primary if primary.exists() else house.HEADSHOT_CACHE / f"{int(player_id)}.png"


def _height(rows: int) -> int:
    needed = TOP_BOTTOM * 2 + rows * ROW_HEIGHT
    return max(1200, ((needed + DRAFT_DPI - 1) // DRAFT_DPI) * DRAFT_DPI)


def _ordinal(value: int) -> str:
    suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def render(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    metric = "and1s"
    required = {"player_id", "player_name", "season", metric, "per_100", "nba_rank"}
    frame = pd.read_csv(data_path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    frame = frame.sort_values([metric, "per_100"], ascending=False,
                              kind="stable").reset_index(drop=True)

    height = _height(len(frame))
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    first_y = height - TOP_BOTTOM - ROW_HEIGHT / 2
    scale = (BAR_RIGHT - BAR_LEFT) / float(frame[metric].max())
    header_y = height - TOP_BOTTOM + 58
    bold = helvetica("bold")
    ax.text(NAME_X, header_y, "PLAYER / SEASON", ha="left", va="center",
            fontsize=28, color=INK, fontproperties=bold, zorder=3)
    ax.text(BAR_LEFT, header_y, "AND-1s", ha="left", va="center",
            fontsize=28, color=INK, fontproperties=bold, zorder=3)
    for x, label in zip(SUPPORT_X, ("NBA RANK", "PER 100 POSS")):
        ax.text(x, header_y, label, ha="center", va="center", fontsize=27,
                color=INK, fontproperties=bold, zorder=3)
    rule_y = height - TOP_BOTTOM + 15
    ax.plot([0, WIDTH], [rule_y, rule_y], color=INK, linewidth=2.0, zorder=3)

    for i, row in frame.iterrows():
        y = first_y - i * ROW_HEIGHT
        if i % 2 == 0:
            ax.axhspan(y - ROW_HEIGHT / 2, y + ROW_HEIGHT / 2,
                       color=RULE, alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + ROW_HEIGHT / 2] * 2, color=RULE, linewidth=1.1, zorder=0)

        house.top_anchored_headshot_label(
            ax, _portrait_path(int(row.player_id)), PORTRAIT_X,
            y - ROW_HEIGHT / 2 + PORTRAIT_HALF, PORTRAIT_HALF,
            crop_fraction=0.64, preserve_width=True, zorder=2,
        )
        ax.text(NAME_X, y + 28, str(row.player_name), ha="left", va="center",
                fontsize=34, color=INK, fontproperties=bold, zorder=3)
        ax.text(NAME_X, y - 32, str(row.season), ha="left", va="center", fontsize=20,
                color=SEASON_GREY, fontproperties=helvetica("oblique"), zorder=3)

        ax.text(SUPPORT_X[0], y, _ordinal(int(row.nba_rank)), ha="center", va="center",
                fontsize=30, color=INK, fontproperties=bold, zorder=3)
        ax.text(SUPPORT_X[1], y, f"{float(row.per_100):.2f}", ha="center", va="center",
                fontsize=30, color=INK, fontproperties=bold, zorder=3)

        width = float(row[metric]) * scale
        ax.add_patch(FancyBboxPatch(
            (BAR_LEFT, y - BAR_HEIGHT / 2), width, BAR_HEIGHT,
            boxstyle="round,pad=0,rounding_size=8", linewidth=0, facecolor=RED, zorder=1,
        ))
        ax.text(BAR_LEFT + width - 18, y, f"{int(row[metric])}", ha="right", va="center",
                fontsize=29, color="white", fontproperties=bold, zorder=3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    print(render(args.data, args.output, final=args.final))


if __name__ == "__main__":
    main()
