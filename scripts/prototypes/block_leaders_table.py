"""Render Bulls single-season block leaders as a table-bar hybrid."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bulls.graphics import house
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica


DEFAULT_DATA = ROOT / "docs/visuals/2026-09-19-block-leaders/data/top15.csv"
DEFAULT_OUTPUT = ROOT / "output/block-leaders/table.png"
PRIMARY_HEADSHOTS = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")
WIDTH = 3240
TOP_BOTTOM = 175
# The blocks page has a compact two-line title and no explanatory footer above
# the source line, leaving more vertical body space than the rim-protection
# page.  The taller 3:4 ratio is measured from the composed Canva draft.
PAGE_FRAMES = {"3:4": 0.84, "4:5": 1029.32 / 1101.0}
PORTRAIT_X = 155
NAME_X = 330
BAR_LEFT = 1050
BAR_RIGHT = 2350
SUPPORT_X = (2640, 3020)
RIGHT_MARGIN = 80
ROW_RATIO = 0.536
INK = house.BLACK
RED = house.RED
SEASON_GREY = "#6E6963"
RULE = "#B8B0A8"


def _portrait_path(player_id: int) -> Path:
    primary = PRIMARY_HEADSHOTS / f"{player_id}.png"
    return primary if primary.exists() else house.HEADSHOT_CACHE / f"{player_id}.png"


def _ordinal(value: int) -> str:
    suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _row_height(rows: int, aspect: float) -> int:
    return round((WIDTH / aspect - 2 * TOP_BOTTOM) / rows)


def render(data_path: Path, output_path: Path, *, final: bool = False, page: str = "3:4") -> Path:
    required = {"player_id", "player_name", "season", "blocks", "nba_rank", "blocks_per_game"}
    frame = pd.read_csv(data_path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    frame = frame.sort_values(
        ["blocks", "blocks_per_game", "season"], ascending=[False, False, True], kind="stable"
    ).reset_index(drop=True)

    row_height = _row_height(len(frame), PAGE_FRAMES[page])
    portrait_half = round(row_height * ROW_RATIO)
    bar_height = portrait_half
    height = TOP_BOTTOM * 2 + len(frame) * row_height
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    bold = helvetica("bold")
    first_y = height - TOP_BOTTOM - row_height / 2
    header_y = height - TOP_BOTTOM + 66
    scale = (BAR_RIGHT - BAR_LEFT) / float(frame["blocks"].max())

    ax.text(NAME_X, header_y, "PLAYER / SEASON", ha="left", va="center", fontsize=31,
            color=INK, fontproperties=bold)
    ax.text(BAR_LEFT, header_y, "BLOCKS", ha="left", va="center", fontsize=31,
            color=INK, fontproperties=bold)
    for line_index, line in enumerate(("NBA", "RANK")):
        ax.text(SUPPORT_X[0], header_y + (1 - line_index) * 62, line,
                ha="center", va="center", fontsize=30, color=INK,
                fontproperties=bold)
    ax.text(SUPPORT_X[1], header_y, "BLK/G", ha="center", va="center",
            fontsize=30, color=INK, fontproperties=bold)
    ax.plot([0, WIDTH], [height - TOP_BOTTOM + 15] * 2, color=INK, linewidth=2.0)

    for i, row in frame.iterrows():
        y = first_y - i * row_height
        if i % 2 == 0:
            ax.axhspan(y - row_height / 2, y + row_height / 2, color=RULE, alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + row_height / 2] * 2, color=RULE, linewidth=1.1, zorder=0)

        house.top_anchored_headshot_label(
            ax, _portrait_path(int(row.player_id)), PORTRAIT_X,
            y - row_height / 2 + portrait_half, portrait_half,
            crop_fraction=.64, preserve_width=True, zorder=2,
        )
        name = ax.text(NAME_X, y + 32, str(row.player_name), ha="left", va="center",
                       fontsize=36, color=INK, fontproperties=bold, zorder=3)
        if NAME_X + house.rendered_width(ax, name) > BAR_LEFT - 20:
            raise ValueError(f"{row.player_name} overruns the bar column")
        ax.text(NAME_X, y - 36, str(row.season), ha="left", va="center", fontsize=22,
                color=SEASON_GREY, fontproperties=helvetica("oblique"), zorder=3)

        value = int(row.blocks)
        width = value * scale
        ax.add_patch(FancyBboxPatch(
            (BAR_LEFT, y - bar_height / 2), width, bar_height,
            boxstyle="round,pad=0,rounding_size=8", linewidth=0, facecolor=RED, zorder=1,
        ))
        ax.text(BAR_LEFT + width - 18, y, str(value), ha="right", va="center",
                fontsize=34, color="white", fontproperties=bold, zorder=3)
        ax.text(SUPPORT_X[0], y, _ordinal(int(row.nba_rank)), ha="center", va="center",
                fontsize=34, color=INK, fontproperties=bold, zorder=3)
        ax.text(SUPPORT_X[1], y, f"{float(row.blocks_per_game):.2f}", ha="center", va="center",
                fontsize=34, color=INK, fontproperties=bold, zorder=3)

    if SUPPORT_X[-1] >= WIDTH - RIGHT_MARGIN:
        raise ValueError("Supporting columns exceed the right margin")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--page", choices=sorted(PAGE_FRAMES), default="3:4")
    args = parser.parse_args()
    print(render(args.data, args.output, final=args.final, page=args.page))


if __name__ == "__main__":
    main()
