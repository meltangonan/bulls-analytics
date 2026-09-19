"""Render the top Bulls rim-protection seasons as a table-bar hybrid.

Same layout as `and_one_leaders_table.py`, with three support columns instead
of two. The bar is rim points saved; the FG% column carries its league
comparison on a second line, the way the name column carries its season.

Run `rim_protection_data.py` first; this script never fetches stats.
"""

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


DEFAULT_DATA = _REPO / "docs/visuals/2026-09-18-rim-protection-landscape/data/top15_table.csv"
DEFAULT_OUTPUT = _REPO / "output/rim-protection/table.png"
PRIMARY_HEADSHOTS = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")

# Geometry follows and_one_leaders_table.py, widened for four support columns
# and made taller to fill the Canva page.
#
# The composed page is 1080x1440 with 25.34pt side margins, so a chart placed
# to the margins is 1029.32 wide. It starts under the title at y=217.9 and the
# footer begins at y=1409.4, leaving about 1160 of height. That is a
# width-to-height ratio near TARGET_ASPECT; the asset is rendered to match so
# the page needs no vertical gap-filling.
# 3:4 is the 1080x1440 page measured above; 4:5 is 1080x1350, whose shorter
# body leaves about 1101 of height between the same title and footer.
PAGE_FRAMES = {"3:4": 1029.32 / 1160.0, "4:5": 1029.32 / 1101.0}
WIDTH = 3240
TOP_BOTTOM = 175
PORTRAIT_X = 155
NAME_X = 330
ROW_RATIO = 0.536  # portrait and bar height as a share of row height
RIGHT_MARGIN = 90
COLUMN_MIN_GAP = 40
BAR_LEFT = 1120
BAR_RIGHT = 1770
SUPPORT_X = (1880, 2273, 2667, 3060)  # evenly spaced centres
INK = house.BLACK
RED = house.RED
SEASON_GREY = "#6E6963"
RULE = "#B8B0A8"
GREY = "#5F5B57"
GREEN = "#218347"
# Colours follow pull_up_points_bars.py but invert: at the rim a negative
# comparison is good defence. Seasons inside +/- NEUTRAL_PP of league average
# stay grey rather than claiming a defensive effect the gap cannot support.
NEUTRAL_PP = 3.0
# Bars shorter than this cannot hold a legible white label inside them.
OUTSIDE_LABEL_BELOW = 30.0


def _portrait_path(player_id: int) -> Path:
    primary = PRIMARY_HEADSHOTS / f"{int(player_id)}.png"
    return primary if primary.exists() else house.HEADSHOT_CACHE / f"{int(player_id)}.png"


def _row_height(rows: int, aspect: float) -> int:
    """Row height that makes the asset fill its Canva frame exactly."""
    return round((WIDTH / aspect - 2 * TOP_BOTTOM) / rows)


def _ordinal(value: int) -> str:
    suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _signed(value: float) -> str:
    """One decimal with a true minus; a value rounding to zero keeps no sign."""
    if abs(value) < 0.05:
        return "0.0"
    return f"{value:+.1f}".replace("-", "−")


def _comparison_color(value: float) -> str:
    """Green when opponents shot well below average, red when above."""
    if value <= -NEUTRAL_PP:
        return GREEN
    if value >= NEUTRAL_PP:
        return RED
    return GREY


def render(data_path: Path, output_path: Path, *, final: bool = False,
           page: str = "3:4") -> Path:
    metric = "rim_points_saved"
    required = {"player_id", "player_name", "season", metric, "rim_fg_pct",
                "pct_vs_league", "rim_fga", "blocks", "nba_rank"}
    frame = pd.read_csv(data_path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    frame = frame.sort_values([metric, "rim_fga"], ascending=False,
                              kind="stable").reset_index(drop=True)

    row_height = _row_height(len(frame), PAGE_FRAMES[page])
    portrait_half = round(row_height * ROW_RATIO)
    bar_height = portrait_half
    height = TOP_BOTTOM * 2 + len(frame) * row_height
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    first_y = height - TOP_BOTTOM - row_height / 2
    scale = (BAR_RIGHT - BAR_LEFT) / float(frame[metric].max())
    header_y = height - TOP_BOTTOM + 66
    bold = helvetica("bold")

    def width_of(text: str, size: float) -> float:
        probe = ax.text(0, 0, text, fontsize=size, fontproperties=bold, alpha=0)
        measured = house.rendered_width(ax, probe)
        probe.remove()
        return measured

    # Support columns: header (| wraps a line) and the row values, so each
    # column can be measured and the gaps between them made equal.
    columns = [
        ("NBA|RANK", [_ordinal(int(v)) for v in frame.nba_rank]),
        ("RIM FG%|ALLOWED", [f"{v:.1f}%" for v in frame.rim_fg_pct]),
        ("RIM FGA|DEFENDED", [f"{int(v)}" for v in frame.rim_fga]),
        ("BLOCKS", [f"{int(v)}" for v in frame.blocks]),
    ]
    widths = [
        max([width_of(line, 30) for line in header.split("|")]
            + [width_of(value, 34) for value in values])
        for header, values in columns
    ]

    # The bar header wraps to two lines; its widest line bounds the columns.
    bar_header_right = BAR_LEFT + max(width_of(line, 31) for line in ("RIM POINTS", "SAVED"))
    span_start = max(bar_header_right, BAR_RIGHT)
    gap = (WIDTH - RIGHT_MARGIN - span_start - sum(widths)) / len(widths)
    if gap < COLUMN_MIN_GAP:
        raise ValueError(f"Support columns need {gap:.0f}px gaps; widen WIDTH or shrink columns")
    centres, cursor = [], span_start
    for column_width in widths:
        cursor += gap
        centres.append(cursor + column_width / 2)
        cursor += column_width

    ax.text(NAME_X, header_y, "PLAYER / SEASON", ha="left", va="center",
            fontsize=31, color=INK, fontproperties=bold, zorder=3)
    # A wrapped header sits on the shared baseline with its LAST line and
    # stacks the rest above, so every column header ends at the same height.
    # 30pt at this DPI draws about 60px tall, so wrapped lines step by 62.
    for line_index, line in enumerate(("RIM POINTS", "SAVED")):
        ax.text(BAR_LEFT, header_y + (1 - line_index) * 62, line, ha="left",
                va="center", fontsize=31, color=INK, fontproperties=bold, zorder=3)
    for x, (header, _) in zip(centres, columns):
        lines = header.split("|")
        for line_index, line in enumerate(lines):
            ax.text(x, header_y + (len(lines) - 1 - line_index) * 62, line,
                    ha="center", va="center", fontsize=30, color=INK,
                    fontproperties=bold, zorder=3)
    rule_y = height - TOP_BOTTOM + 15
    ax.plot([0, WIDTH], [rule_y, rule_y], color=INK, linewidth=2.0, zorder=3)

    for i, row in frame.iterrows():
        y = first_y - i * row_height
        if i % 2 == 0:
            ax.axhspan(y - row_height / 2, y + row_height / 2,
                       color=RULE, alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + row_height / 2] * 2, color=RULE, linewidth=1.1, zorder=0)

        house.top_anchored_headshot_label(
            ax, _portrait_path(int(row.player_id)), PORTRAIT_X,
            y - row_height / 2 + portrait_half, portrait_half,
            crop_fraction=0.64, preserve_width=True, zorder=2,
        )
        name = ax.text(NAME_X, y + 32, str(row.player_name), ha="left", va="center",
                       fontsize=36, color=INK, fontproperties=bold, zorder=3)
        if NAME_X + house.rendered_width(ax, name) > BAR_LEFT - 20:
            raise ValueError(f"{row.player_name} overruns the bar column")
        ax.text(NAME_X, y - 36, str(row.season), ha="left", va="center", fontsize=22,
                color=SEASON_GREY, fontproperties=helvetica("oblique"), zorder=3)

        ax.text(centres[0], y, _ordinal(int(row.nba_rank)), ha="center", va="center",
                fontsize=34, color=INK, fontproperties=bold, zorder=3)
        ax.text(centres[1], y + 24, f"{float(row.rim_fg_pct):.1f}%", ha="center", va="center",
                fontsize=34, color=INK, fontproperties=bold, zorder=3)
        relative = float(row.pct_vs_league)
        ax.text(centres[1], y - 34, f"({_signed(relative)})", ha="center", va="center",
                fontsize=26, color=_comparison_color(relative),
                fontproperties=bold, zorder=3)
        ax.text(centres[2], y, f"{int(row.rim_fga)}", ha="center", va="center",
                fontsize=34, color=INK, fontproperties=bold, zorder=3)
        ax.text(centres[3], y, f"{int(row.blocks)}", ha="center", va="center",
                fontsize=34, color=INK, fontproperties=bold, zorder=3)

        value = float(row[metric])
        width = value * scale
        ax.add_patch(FancyBboxPatch(
            (BAR_LEFT, y - bar_height / 2), width, bar_height,
            boxstyle="round,pad=0,rounding_size=8", linewidth=0, facecolor=RED, zorder=1,
        ))
        # A short bar cannot hold its own label, so the value sits outside it
        # in the house black instead of white-on-red inside a sliver.
        if value < OUTSIDE_LABEL_BELOW:
            ax.text(BAR_LEFT + width + 16, y, f"{round(value):d}", ha="left", va="center",
                    fontsize=33, color=INK, fontproperties=bold, zorder=3)
        else:
            ax.text(BAR_LEFT + width - 18, y, f"{round(value):d}", ha="right", va="center",
                    fontsize=33, color="white", fontproperties=bold, zorder=3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--page", choices=sorted(PAGE_FRAMES), default="3:4",
                        help="Canva page shape the asset is sized to fill")
    args = parser.parse_args()
    print(render(args.data, args.output, final=args.final, page=args.page))


if __name__ == "__main__":
    main()
