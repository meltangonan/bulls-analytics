"""Render one of the three Bulls drive-leader table assets."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "docs/visuals/2026-09-15-drive-leaders/data"

MODES = {
    "drives": {
        "file": "top15_drives.csv",
        "hero": "drives",
        "columns": [("drives", "DRIVES"), ("drives_per_game", "DRIVES/G"),
                    ("drive_shot_pct", "SHOT%"), ("drive_pass_pct", "PASS%")],
    },
    "points": {
        "file": "top15_drive_points.csv",
        "hero": "drive_pts",
        "columns": [("drive_pts", "PTS"), ("fg", "FGM–FGA"),
                    ("drive_fg_pct", "FG%"), ("drive_pf", "FOULS")],
    },
    "assists": {
        "file": "top15_drive_assists.csv",
        "hero": "drive_ast",
        "columns": [("drive_ast", "AST"), ("drive_passes", "PASSES"),
                    ("drive_pass_pct", "PASS%"),
                    ("drive_ast_pct", "AST%")],
    },
}


def display(row: pd.Series, key: str) -> str:
    if key == "fg":
        return f"{int(row.drive_fgm)}–{int(row.drive_fga)}"
    if key in {"drive_fg_pct", "drive_shot_pct", "drive_pass_pct", "drive_ast_pct"}:
        return f"{float(row[key]):.1f}%"
    if key == "drives_per_game":
        return f"{float(row[key]):.1f}"
    return str(int(row[key]))


def render(mode: str, output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from bulls.graphics.craft import draw_table_cell
    from bulls.graphics.house import (
        BLACK, HEADSHOT_CACHE, draw_accent_card, ensure_headshots, helvetica,
        top_anchored_headshot_label,
    )

    config = MODES[mode]
    table = pd.read_csv(DATA / config["file"]).sort_values("rank", kind="stable")
    if table.empty or not table["rank"].eq(range(1, len(table) + 1)).all():
        raise ValueError("Input rows must be ranked 1 through row count")
    table["player_id"] = table.player_id.astype(int)
    ensure_headshots(table.player_id.unique())

    width, row_h = 2050, 145
    height = 150 + row_h * len(table)
    fig = plt.figure(figsize=(width / 150, height / 150), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, width), ylim=(0, height)); ax.axis("off")
    first_y, header_y = height - 190, height - 48
    # Four identical 285 px columns with identical 30 px gutters. Equal centers
    # matter visually as much as the literal gaps, especially for short values.
    bounds = [(790, 1075), (1105, 1390), (1420, 1705), (1735, 2020)]
    card_left, card_right, _, _ = draw_accent_card(
        ax, *bounds[0], first_y, len(table), row_h, overlap_y=15
    )
    ax.text(260, header_y, "PLAYER / SEASON", fontproperties=helvetica("bold"),
            fontsize=21, color=BLACK, va="center")
    for (left, right), (_, label) in zip(bounds, config["columns"]):
        draw_table_cell(ax, label, left, right, header_y, 40, fontsize=20,
                        color=BLACK, fontproperties=helvetica("bold"))
    rule_y = height - 105
    ax.hlines(rule_y, 0, card_left - 10, color=BLACK, lw=1)
    ax.hlines(rule_y, card_right + 10, width, color=BLACK, lw=1)

    for i, (_, row) in enumerate(table.iterrows()):
        y = first_y - i * row_h
        if i % 2 == 0:
            ax.axhspan(y-row_h/2, y+row_h/2, color="#B8B0A8", alpha=.09, zorder=0)
        if i:
            ax.hlines(y+row_h/2, 0, width, color="#B8B0A8", lw=.65, zorder=0)
        top_anchored_headshot_label(
            ax, HEADSHOT_CACHE / f"{int(row.player_id)}.png", 130, y+10, 88,
            crop_fraction=.64, preserve_width=True, zorder=3+i*.01,
        )
        ax.text(260, y+22, row.player_name, fontproperties=helvetica("bold"),
                fontsize=27, color=BLACK, va="center")
        ax.text(260, y-32, str(row.season).replace("-", "–"),
                fontproperties=helvetica("oblique"), fontsize=16,
                color="#5F5B57", va="center")
        for j, ((left, right), (key, _)) in enumerate(zip(bounds, config["columns"])):
            draw_table_cell(ax, display(row, key), left, right, y, row_h,
                            fontsize=28 if j == 0 else 24,
                            color="white" if j == 0 else BLACK, zorder=6,
                            fontproperties=helvetica("bold" if j == 0 else "regular"))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, transparent=True)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    render(args.mode, args.output or ROOT / "output/drive-leaders" / f"{args.mode}.png")
