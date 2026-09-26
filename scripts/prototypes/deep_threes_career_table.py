"""Render the Bulls career deep-threes top 15 as a transparent bar table."""

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


DEFAULT_DATA = ROOT / "docs/visuals/2026-09-25-deep-threes-career/data/top15.csv"
DEFAULT_OUTPUT = ROOT / "output/deep-threes-career/table.png"
PRIMARY_HEADSHOTS = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")

WIDTH = 2900
ROW_HEIGHT = 205
TOP_PADDING = 200
BOTTOM_PADDING = 80
PORTRAIT_X = 150
PORTRAIT_HALF = 111
NAME_X = 320
BAR_LEFT = 970
BAR_RIGHT = 1840
BAR_HEIGHT = 105
SUPPORT_X = (2010, 2265, 2645)
INK = house.BLACK
RED = house.RED
GREY = "#5F5B57"
GREEN = "#218347"
DARK_RED = "#B53939"
RULE = "#B8B0A8"


def _portrait_path(player_id: int) -> Path:
    primary = PRIMARY_HEADSHOTS / f"{player_id}.png"
    path = primary if primary.exists() else house.HEADSHOT_CACHE / f"{player_id}.png"
    if not path.exists():
        raise FileNotFoundError(f"No cached NBA portrait for player {player_id}")
    return path


def _signed(value: float) -> str:
    if abs(value) < 0.05:
        return "0.0"
    return f"{value:+.1f}".replace("-", "−")


def render(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    frame = pd.read_csv(data_path)
    required = {"rank", "player_id", "player_name", "deep_3pm", "deep_3pa",
                "attempts_per_game", "three_pct", "league_three_pct", "relative_pp"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Missing data columns: {sorted(missing)}")
    if len(frame) != 15 or frame.deep_3pm.isna().any():
        raise ValueError("The bar table requires 15 complete rows")
    frame = frame.sort_values(["deep_3pm", "deep_3pa"], ascending=[False, False]).reset_index(drop=True)
    if not (frame.deep_3pm.diff().dropna() <= 0).all():
        raise ValueError("Makes must be sorted descending")

    height = TOP_PADDING + BOTTOM_PADDING + ROW_HEIGHT * len(frame)
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    bold = helvetica("bold")
    first_y = height - TOP_PADDING - ROW_HEIGHT / 2
    header_y = height - TOP_PADDING + 77
    bar_scale = (BAR_RIGHT - BAR_LEFT) / float(frame.deep_3pm.max())

    for x, label, align in (
        (NAME_X, "PLAYER", "left"),
        (BAR_LEFT, "MAKES", "left"),
        (SUPPORT_X[0], "ATT", "center"),
        (SUPPORT_X[1], "ATT/G", "center"),
        (SUPPORT_X[2], "3P%", "center"),
    ):
        ax.text(x, header_y, label, ha=align, va="center", fontsize=30,
                color=INK, fontproperties=bold, zorder=3)
    ax.plot([0, WIDTH], [height - TOP_PADDING + 19] * 2,
            color=INK, linewidth=2.0, zorder=3)

    for index, row in frame.iterrows():
        y = first_y - index * ROW_HEIGHT
        if index % 2 == 0:
            ax.axhspan(y - ROW_HEIGHT / 2, y + ROW_HEIGHT / 2,
                       color=RULE, alpha=.12, zorder=0)
        if index:
            ax.plot([0, WIDTH], [y + ROW_HEIGHT / 2] * 2,
                    color=RULE, linewidth=1.1, zorder=0)

        house.top_anchored_headshot_label(
            ax, _portrait_path(int(row.player_id)), PORTRAIT_X,
            y - ROW_HEIGHT / 2 + PORTRAIT_HALF, PORTRAIT_HALF,
            crop_fraction=.64, preserve_width=True, zorder=2,
        )
        name = ax.text(NAME_X, y, row.player_name, ha="left", va="center",
                       fontsize=37, color=INK, fontproperties=bold, zorder=3)
        if NAME_X + house.rendered_width(ax, name) > BAR_LEFT - 27:
            raise ValueError(f"Name overruns the makes bar: {row.player_name}")

        width = float(row.deep_3pm) * bar_scale
        ax.add_patch(FancyBboxPatch(
            (BAR_LEFT, y - BAR_HEIGHT / 2), width, BAR_HEIGHT,
            boxstyle="round,pad=0,rounding_size=9", linewidth=0,
            facecolor=RED, zorder=1,
        ))
        inside = row.deep_3pm >= 40
        ax.text(BAR_LEFT + width + (-20 if inside else 20), y,
                f"{int(row.deep_3pm)}", ha="right" if inside else "left",
                va="center", fontsize=33, color="white" if inside else INK,
                fontproperties=bold, zorder=3)

        ax.text(SUPPORT_X[0], y, f"{int(row.deep_3pa)}", ha="center", va="center",
                fontsize=32, color=INK, fontproperties=bold, zorder=3)
        ax.text(SUPPORT_X[1], y, f"{row.attempts_per_game:.2f}", ha="center", va="center",
                fontsize=32, color=INK, fontproperties=bold, zorder=3)
        ax.text(SUPPORT_X[2], y + 24, f"{row.three_pct:.1f}%",
                ha="center", va="center", fontsize=32, color=INK,
                fontproperties=bold, zorder=3)
        relative = float(row.relative_pp)
        relative_color = GREY if -2 <= relative <= 2 else (GREEN if relative > 2 else DARK_RED)
        ax.text(SUPPORT_X[2], y - 33, f"({_signed(relative)} vs. NBA)",
                ha="center", va="center", fontsize=25, color=relative_color,
                fontproperties=bold, zorder=3)

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
