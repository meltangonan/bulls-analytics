"""Prototype: F5-style lineup table — Bulls two-man combos by net rating.

The "Doubling Up" format from The F5 restyled to the house look: most-used
Bulls 2-man lineups with minutes and off/def/net ratings, net rating
color-scaled around zero. Fetches live lineup data via bulls.data
(network required), renders 1080x1350 at 300 DPI (2160x2700 export).

Change TOP_N / MIN_MINUTES / column set below for future topics.
"""
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from plottable import ColumnDefinition, Table

from bulls.config import CURRENT_SEASON
from bulls.data import get_lineup_stats
from bulls.graphics.craft import FAINT, INK, MUTED, threshold_footer
from bulls.graphics.feed import (
    DEFAULT_DPI,
    INSTAGRAM_FEED_HEIGHT_PX,
    INSTAGRAM_FEED_WIDTH_PX,
    _fp_body,
    _fp_title,
    save_feed_post,
)

OUTPUT_DIR = _REPO / "output" / "feed"

MIN_MINUTES = 100
TOP_N = 10
EXPORT_DPI = 300  # 2160x2700

TITLE = "Bulls Two-Man Lineups"
SUBTITLE = f"Most-used pairs and their net rating | {CURRENT_SEASON} Season"
COVERAGE = f"{CURRENT_SEASON} regular season"

# Diverging: red for negative net rating, neutral at zero, green for positive.
NET_CMAP = LinearSegmentedColormap.from_list(
    "net_diverging", ["#B01030", "#F5F1EA", "#1E6E3C"]
)


def net_color(norm: TwoSlopeNorm):
    def _color(value: float):
        return NET_CMAP(norm(value))
    return _color


def build_lineup_table(lineups) -> plt.Figure:
    rows = lineups.sort_values("MIN", ascending=False).head(TOP_N).copy()

    # Two-line lineup label: one player per line.
    rows["combo"] = rows["GROUP_NAME"].str.replace(" - ", "\n", regex=False)
    table_df = rows[["combo", "GP", "MIN", "OFF_RATING", "DEF_RATING", "NET_RATING"]]
    table_df = table_df.set_index("combo")

    figsize = (INSTAGRAM_FEED_WIDTH_PX / DEFAULT_DPI, INSTAGRAM_FEED_HEIGHT_PX / DEFAULT_DPI)
    fig = plt.figure(figsize=figsize, facecolor="#FFFFFF")

    fig.text(0.055, 0.945, TITLE, ha="left", va="top",
             fontsize=42, color=INK, fontproperties=_fp_title(weight="bold"))
    fig.text(0.055, 0.868, SUBTITLE, ha="left", va="top",
             fontsize=17, color=MUTED, fontproperties=_fp_body(weight="medium"))

    ax = fig.add_axes([0.045, 0.08, 0.91, 0.72])
    ax.set_facecolor("#FFFFFF")

    limit = max(abs(table_df["NET_RATING"].min()), abs(table_df["NET_RATING"].max()), 1.0)
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)

    body_font = _fp_body(weight="medium")
    bold_font = _fp_body(weight="bold")

    Table(
        table_df,
        ax=ax,
        textprops={"fontsize": 12, "color": INK, "fontproperties": body_font, "ha": "center"},
        row_dividers=True,
        row_divider_kw={"color": "#DDDDDD", "linewidth": 0.8},
        col_label_divider_kw={"color": INK, "linewidth": 1.2},
        footer_divider=True,
        footer_divider_kw={"color": "#DDDDDD", "linewidth": 0.8},
        column_border_kw={"linewidth": 0},
        column_definitions=[
            ColumnDefinition(
                "combo", title="LINEUP", width=2.1,
                textprops={"ha": "left", "fontsize": 13, "fontproperties": bold_font},
            ),
            ColumnDefinition("GP", title="GP", width=0.6,
                             formatter="{:.0f}",
                             textprops={"color": MUTED, "fontproperties": body_font}),
            ColumnDefinition("MIN", title="MIN", width=0.8,
                             formatter="{:.0f}",
                             textprops={"color": MUTED, "fontproperties": body_font}),
            ColumnDefinition("OFF_RATING", title="OFF RTG", width=0.9,
                             formatter="{:.1f}",
                             textprops={"color": MUTED, "fontproperties": body_font}),
            ColumnDefinition("DEF_RATING", title="DEF RTG", width=0.9,
                             formatter="{:.1f}",
                             textprops={"color": MUTED, "fontproperties": body_font}),
            ColumnDefinition("NET_RATING", title="NET RTG", width=0.95,
                             formatter=lambda x: f"{x:+.1f}",
                             cmap=net_color(norm),
                             textprops={"fontproperties": bold_font, "fontsize": 13}),
        ],
    )

    threshold_footer(
        fig,
        f"Min. {MIN_MINUTES} minutes together",
        COVERAGE,
        "data: NBA.com/Stats",
    )
    return fig


def main():
    lineups = get_lineup_stats()
    if lineups.empty:
        sys.exit("No lineup data returned — NBA API unreachable?")
    qualified = lineups[lineups["MIN"] >= MIN_MINUTES].reset_index(drop=True)
    if qualified.empty:
        sys.exit(
            f"{len(lineups)} lineups returned but none played {MIN_MINUTES}+ minutes "
            "together — early in the season? Lower MIN_MINUTES."
        )
    print(qualified.sort_values("MIN", ascending=False).head(TOP_N).to_string())

    fig = build_lineup_table(qualified)
    stamp = date.today().isoformat()
    path = save_feed_post(fig, OUTPUT_DIR / f"{stamp}-f5-lineup-table.png", dpi=EXPORT_DPI)
    print(f"Saved {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
