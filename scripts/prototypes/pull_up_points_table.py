"""Render the regular Bulls pull-up points top-10 table."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DEFAULT_DATA = ROOT / "docs/visuals/2026-09-10-pull-up-points-leaders/data/top10.csv"
DEFAULT_OUTPUT = ROOT / "output/pull-up-points-leaders/table.png"

REQUIRED = [
    "rank", "player_id", "player_name", "season", "gp", "fgm", "fga",
    "fg3m", "pts", "efg_pct", "league_efg_pct", "relative_efg_pp", "pts_per_game",
]


def render(data_path: Path, output_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea

    from bulls.graphics.craft import draw_table_cell
    from bulls.graphics.house import (
        BLACK,
        HEADSHOT_CACHE,
        draw_accent_card,
        ensure_headshots,
        helvetica,
        top_anchored_headshot_label,
    )

    table = pd.read_csv(data_path)
    missing = [column for column in REQUIRED if column not in table.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    table = table.sort_values("rank", kind="stable").reset_index(drop=True)
    if not table["rank"].eq(range(1, len(table) + 1)).all():
        raise ValueError("Input rows must be rank ordered from 1 through the row count")
    if table.empty:
        raise ValueError("Input table is empty")

    table["player_id"] = table["player_id"].astype(int)
    ensure_headshots(table["player_id"].unique())

    # This follows the regular layup table: a single red hero column, quiet row
    # rules, and no individual boxes. The hero number is the story metric here.
    width, row_h = 2200, 145
    height = 150 + row_h * len(table)
    fig = plt.figure(figsize=(width / 150, height / 150), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, width), ylim=(0, height))
    ax.axis("off")

    first_y = height - 190
    header_y = height - 48
    cols = [
        (850, 1100, "PTS"),
        (1135, 1335, "FGM"),
        (1370, 1810, "eFG% (rEFG)"),
        (1845, 2165, "PTS/G"),
    ]
    card_left, card_right, _, _ = draw_accent_card(
        ax, 850, 1100, first_y, len(table), row_h, overlap_y=15
    )
    ax.text(275, header_y, "PLAYER / SEASON", fontproperties=helvetica("bold"),
            fontsize=21, color=BLACK, va="center")
    for left, right, label in cols:
        draw_table_cell(ax, label, left, right, header_y, 40, fontsize=21,
                        color=BLACK, fontproperties=helvetica("bold"))
    rule_y = height - 105
    ax.hlines(rule_y, 0, card_left - 10, color=BLACK, lw=1)
    ax.hlines(rule_y, card_right + 10, width, color=BLACK, lw=1)

    for i, row in enumerate(table.itertuples(index=False)):
        y = first_y - i * row_h
        if i % 2 == 0:
            ax.axhspan(y - row_h / 2, y + row_h / 2, color="#B8B0A8", alpha=.09, zorder=0)
        if i:
            ax.hlines(y + row_h / 2, 0, width, color="#B8B0A8", lw=.65, zorder=0)

        top_anchored_headshot_label(
            ax, HEADSHOT_CACHE / f"{int(row.player_id)}.png", 125, y + 10, 85,
            crop_fraction=.64, preserve_width=True, zorder=3 + i * .01,
        )
        ax.text(275, y + 22, row.player_name, fontproperties=helvetica("bold"),
                fontsize=27, color=BLACK, va="center")
        ax.text(275, y - 32, str(row.season).replace("-", "–"),
                fontproperties=helvetica("oblique"), fontsize=16,
                color="#5F5B57", va="center")

        relative = float(row.relative_efg_pp)
        relative_display = round(relative, 1)
        signed = f"{relative_display:+.1f}".replace("-", "−") if relative_display else "0.0"
        relative_color = "#D64545" if relative_display < -2 else "#218347" if relative_display > 2 else BLACK
        values = [str(int(round(row.pts))), str(int(round(row.fgm))),
                  f"{float(row.efg_pct):.1f}%", f"{float(row.pts_per_game):.1f}"]
        for j, ((left, right, _), value) in enumerate(zip(cols, values)):
            if j == 2:
                parts = [
                    TextArea(value, textprops=dict(fontproperties=helvetica(), fontsize=25, color=BLACK)),
                    TextArea(f" ({signed})", textprops=dict(fontproperties=helvetica(), fontsize=25, color=relative_color)),
                ]
                box = HPacker(children=parts, align="center", pad=0, sep=0)
                ax.add_artist(AnnotationBbox(box, ((left + right) / 2, y), xycoords="data",
                                             frameon=False, box_alignment=(.5, .5), pad=0, zorder=6))
                continue
            draw_table_cell(ax, value, left, right, y, row_h,
                            fontsize=28 if j == 0 else 25,
                            color="white" if j == 0 else BLACK, zorder=6,
                            fontproperties=helvetica("bold" if j == 0 else "regular"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, transparent=True)
    plt.close(fig)
    print(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.data, args.output)
