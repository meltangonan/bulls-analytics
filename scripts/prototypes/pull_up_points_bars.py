"""Render the top Bulls pull-up points seasons as a compact table-bar hybrid."""

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
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica, rendered_width


DEFAULT_DATA = _REPO / "docs/visuals/2026-09-10-pull-up-points-leaders/data/top15.csv"
DEFAULT_OUTPUT = _REPO / "output/pull-up-points-leaders/bars-top15.png"
PRIMARY_HEADSHOTS = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")

WIDTH = 2600
ROW_HEIGHT = 190
TOP_BOTTOM = 175
PORTRAIT_X = 150
PORTRAIT_HALF = 105
NAME_X = 315
BAR_LEFT = 930
BAR_RIGHT = 1760
BAR_HEIGHT = 104
VALUE_GAP = 22
SUPPORT_X = (1880, 2170, 2470)
INK = house.BLACK
RED = house.RED
GREY = "#5F5B57"
SEASON_GREY = "#6E6963"
RULE = "#B8B0A8"


def _portrait_path(player_id: int) -> Path:
    """Use the primary checkout's cache so this worktree never populates one."""
    primary = PRIMARY_HEADSHOTS / f"{int(player_id)}.png"
    return primary if primary.exists() else house.HEADSHOT_CACHE / f"{int(player_id)}.png"


def _height(rows: int) -> int:
    needed = TOP_BOTTOM * 2 + rows * ROW_HEIGHT
    return max(1200, ((needed + DRAFT_DPI - 1) // DRAFT_DPI) * DRAFT_DPI)


def _signed(value: float) -> str:
    if abs(value) < 0.05:
        return "0.0 pp"
    rendered = f"{value:+.1f} pp"
    return rendered.replace("-", "−")


def _season_label(value: object) -> str:
    return str(value).replace("–", "-").replace("—", "-")


def render(data_path: Path, output_path: Path, *, final: bool = False,
           efficiency_label: str = "eFG%", volume_comparisons: bool = False) -> Path:
    required = {
        "rank", "player_id", "player_name", "season", "gp", "fgm", "fga",
        "fg3m", "pts", "efg_pct", "league_efg_pct", "relative_efg_pp", "pts_per_game",
    }
    frame = pd.read_csv(data_path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    if volume_comparisons and not {"relative_fga_per_game", "relative_pts_per_game"} <= set(frame.columns):
        raise ValueError("Volume comparisons require relative FGA/G and PTS/G")
    frame = frame.sort_values("rank", kind="stable").reset_index(drop=True)
    if len(frame) != 15:
        raise ValueError(f"Expected exactly 15 rows, found {len(frame)}")
    if frame["pts"].isna().any() or (frame["pts"] < 0).any():
        raise ValueError("PTS must be present and non-negative for zero-based bars")

    height = _height(len(frame))
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    first_y = height - TOP_BOTTOM - ROW_HEIGHT / 2
    scale = (BAR_RIGHT - BAR_LEFT) / float(frame["pts"].max())
    header_y = height - TOP_BOTTOM + 58
    ax.text(NAME_X, header_y, "PLAYER / SEASON", ha="left", va="center",
            fontsize=28, color=INK, fontproperties=helvetica("bold"), zorder=3)
    ax.text(BAR_LEFT, header_y, "PTS", ha="left", va="center",
                fontsize=28, color=INK, fontproperties=helvetica("bold"), zorder=3)
    for x, label in zip(SUPPORT_X, ("PTS/G", efficiency_label, "FGA/G")):
        ax.text(x, header_y, label, ha="center", va="center", fontsize=27,
                color=INK, fontproperties=helvetica("bold"), zorder=3)
    rule_y = height - TOP_BOTTOM + 15
    ax.plot([0, WIDTH], [rule_y, rule_y], color=INK, linewidth=2.0, zorder=3)

    for i, row in frame.iterrows():
        y = first_y - i * ROW_HEIGHT
        if i % 2 == 0:
            ax.axhspan(y - ROW_HEIGHT / 2, y + ROW_HEIGHT / 2,
                       color="#B8B0A8", alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + ROW_HEIGHT / 2, y + ROW_HEIGHT / 2],
                    color=RULE, linewidth=1.1, zorder=0)

        house.top_anchored_headshot_label(
            ax, _portrait_path(int(row.player_id)), PORTRAIT_X,
            y - ROW_HEIGHT / 2 + PORTRAIT_HALF, PORTRAIT_HALF,
            crop_fraction=0.64, preserve_width=True, zorder=2,
        )
        name = ax.text(NAME_X, y + 28, str(row.player_name), ha="left", va="center",
                       fontsize=34, color=INK, fontproperties=helvetica("bold"), zorder=3)
        season = ax.text(NAME_X, y - 32, _season_label(row.season), ha="left", va="center", fontsize=20,
                         color=SEASON_GREY, fontproperties=helvetica("oblique"), zorder=3)
        rel = float(row.relative_efg_pp)
        rel_color = GREY if -2 <= rel <= 2 else ("#218347" if rel > 2 else "#B53939")
        ax.text(SUPPORT_X[0], y + (16 if volume_comparisons else 0), f"{float(row.pts_per_game):.1f}", ha="center", va="center", fontsize=30,
                color=INK, fontproperties=helvetica("bold"), zorder=3)
        ax.text(SUPPORT_X[1], y + 16, f"{float(row.efg_pct):.1f}%", ha="center", va="center",
                fontsize=30, color=INK, fontproperties=helvetica("bold"), zorder=3)
        ax.text(SUPPORT_X[1], y - 30, f"({_signed(rel).replace(' pp', '')}{'' if volume_comparisons else ' vs. LA'})", ha="center", va="center",
                fontsize=23, color=rel_color, fontproperties=helvetica("bold"), zorder=3)
        ax.text(SUPPORT_X[2], y + (16 if volume_comparisons else 0), f"{float(row.fga_per_game):.1f}", ha="center", va="center",
                fontsize=30, color=INK, fontproperties=helvetica("bold"), zorder=3)

        if volume_comparisons:
            ax.text(SUPPORT_X[0], y - 30,
                    f"({_signed(float(row.relative_pts_per_game)).replace(' pp', '')})",
                    ha="center", va="center", fontsize=23, color=GREY,
                    fontproperties=helvetica("bold"), zorder=3)
            ax.text(SUPPORT_X[2], y - 30,
                    f"({_signed(float(row.relative_fga_per_game)).replace(' pp', '')})",
                    ha="center", va="center", fontsize=23, color=GREY,
                    fontproperties=helvetica("bold"), zorder=3)

        width = float(row.pts) * scale
        ax.add_patch(FancyBboxPatch(
            (BAR_LEFT, y - BAR_HEIGHT / 2), width, BAR_HEIGHT,
            boxstyle="round,pad=0,rounding_size=8", linewidth=0,
            facecolor=RED, zorder=1,
        ))
        value = ax.text(BAR_LEFT + width - 18, y, f"{int(row.pts):,}",
                        ha="right", va="center", fontsize=29, color="white",
                        fontproperties=helvetica("bold"), zorder=3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--efficiency-label", default="eFG%")
    parser.add_argument("--volume-comparisons", action="store_true")
    args = parser.parse_args()
    path = render(args.data, args.output, final=args.final, efficiency_label=args.efficiency_label,
                  volume_comparisons=args.volume_comparisons)
    print(path)


if __name__ == "__main__":
    main()
