"""Render the top ten Bulls pull-up points player-seasons as boxed rows.

The renderer expects a prepared ``top10.csv``. Calculations and qualification
belong upstream; this file only validates the display contract and composes a
transparent chart asset for Canva.
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.graphics import house
from bulls.graphics.house import FINAL_DPI, helvetica

PROJECT = "pull-up-points-leaders"
DEFAULT_DATA = _REPO / "docs" / "visuals" / "2026-09-10-pull-up-points-leaders" / "data" / "top10.csv"
DEFAULT_OUTPUT = _REPO / "output" / PROJECT / "boxed-pull-up-points.png"
PRIMARY_CACHE = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")

INK = "#242424"
MUTED = "#5F5B57"
RED = "#CE1141"
ROW_FILL = "#F8EDEF"
RULE = "#B8B0A8"
NEUTRAL = "#FAF8F5"
GREEN = "#3FAE63"
HEAT_RED = "#D64545"

REQUIRED = (
    "rank", "player_id", "player_name", "season", "gp", "fgm", "fga",
    "fg3m", "pts", "efg_pct", "league_efg_pct", "relative_efg_pp", "pts_per_game",
)

FIG_W = 10.0
ROW_H_IN = 0.92
PAD_TOP_IN = 0.18
PAD_BOTTOM_IN = 0.16
ROW_L, ROW_R = 0.012, 0.988
PORTRAIT_X = 0.125
NAME_X = 0.205
STATS_L = 0.515
HERO_L = 0.865
STRIPE = 0.006


def figure_height(row_count: int) -> float:
    return PAD_TOP_IN + row_count * ROW_H_IN + PAD_BOTTOM_IN


def one_decimal(value: object) -> str:
    return str(Decimal(repr(float(value))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def season_label(value: object) -> str:
    return str(value).replace("-", "–")


def display_name(value: object) -> str:
    return str(value).replace(" III", "")


def blend(a: str, b: str, amount: float) -> tuple[float, float, float]:
    from matplotlib.colors import to_rgb
    x, y = np.array(to_rgb(a)), np.array(to_rgb(b))
    return tuple(x * (1 - amount) + y * amount)


def relative_fill(value: float):
    """Color relative eFG% around zero; +/-2pp is deliberately neutral."""
    value = float(value)
    if -2 <= value <= 2:
        return NEUTRAL
    if value < -2:
        return blend(NEUTRAL, HEAT_RED, min((abs(value) - 2) / 8, 1.0))
    return blend(NEUTRAL, GREEN, min((value - 2) / 8, 1.0))


def relative_text(value: float) -> str:
    rounded = one_decimal(value)
    numeric = float(rounded)
    sign = "+" if numeric > 0 else ""  # sign follows display rounding
    return f"{sign}{rounded}".replace("-", "−")


def relative_color(value: float) -> str:
    """Use color only when the gap clears the meaningful +/-2 pp band."""
    value = float(value)
    if value > 2:
        return "#218347"
    if value < -2:
        return "#B53939"
    return INK


def portrait_path(player_id: int) -> Path:
    candidate = PRIMARY_CACHE / f"{int(player_id)}.png"
    if candidate.is_file():
        return candidate
    local = house.HEADSHOT_CACHE / f"{int(player_id)}.png"
    return local


def draw_box(ax, left: float, bottom: float, right: float, top: float, *, fill, edge=RED, zorder=2):
    ax.add_patch(Rectangle((left, bottom), right - left, top - bottom,
                           facecolor=fill, edgecolor=edge, linewidth=1.7,
                           joinstyle="round", zorder=zorder))


def load_data(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    if len(frame) != 10:
        raise ValueError(f"Expected exactly 10 rows; got {len(frame)}")
    frame = frame.sort_values("rank", kind="stable").reset_index(drop=True)
    if frame["rank"].tolist() != list(range(1, 11)):
        raise ValueError("rank must contain 1 through 10 in ascending order")
    for column in REQUIRED[4:]:
        if frame[column].isna().any():
            raise ValueError(f"{column} contains missing values")
    return frame


def fit_name_size(frame: pd.DataFrame, fig_h: float) -> float:
    available = STATS_L - NAME_X - 0.015
    fig, ax = plt.subplots(figsize=(FIG_W, fig_h))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_axis_off()
    size = 20.0
    for value in frame["player_name"].map(display_name):
        artist = ax.text(0, 0.5, value, fontproperties=helvetica("bold"), fontsize=size)
        width = house.rendered_width(ax, artist)
        if width > available:
            size = min(size, size * available / width)
        artist.remove()
    plt.close(fig)
    return round(size, 1)


def render(frame: pd.DataFrame, output: Path) -> Path:
    fig_h = figure_height(len(frame))
    fig, ax = plt.subplots(figsize=(FIG_W, fig_h))
    fig.patch.set_alpha(0)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_aspect("auto"); ax.autoscale(False)

    row_h = ROW_H_IN / fig_h
    top = 1 - PAD_TOP_IN / fig_h
    name_size = fit_name_size(frame, fig_h)
    stat_width = (HERO_L - STATS_L) / 4
    stats = (("FGM", "fgm", lambda v: str(int(v))),
             ("eFG%", "efg_pct", lambda v: f"{one_decimal(v)}%"),
             ("rEFG", "relative_efg_pp", relative_text),
             ("PTS/G", "pts_per_game", one_decimal))

    for index, row in frame.iterrows():
        y = top - (index + 0.5) * row_h
        box_h = row_h * 0.84
        bottom, upper = y - box_h / 2, y + box_h / 2
        draw_box(ax, ROW_L, bottom, ROW_R, upper, fill=ROW_FILL, edge=RED, zorder=2)

        portrait = portrait_path(int(row["player_id"]))
        house.top_anchored_headshot_label(
            ax, portrait, PORTRAIT_X, y, row_h * 0.38,
            crop_fraction=0.68, scale=1.18, preserve_width=True, zorder=4,
        )
        name = display_name(row["player_name"])
        ax.text(NAME_X, y + row_h * 0.12, name, fontproperties=helvetica("bold"),
                fontsize=name_size, color=INK, ha="left", va="center", zorder=5)
        ax.text(NAME_X, y - row_h * 0.18,
                f"{season_label(row['season'])}  ·  {int(row['gp'])} GP",
                fontproperties=helvetica(), fontsize=11.5, color=MUTED,
                ha="left", va="center", zorder=5)

        cursor = STATS_L
        for label, key, formatter in stats:
            left, right = cursor, cursor + stat_width - 0.006
            x = (left + right) / 2
            text_color = relative_color(row[key]) if key == "relative_efg_pp" else INK
            ax.text(x, y + row_h * 0.09, formatter(row[key]),
                    fontproperties=helvetica("bold"), fontsize=16.5, color=text_color,
                    ha="center", va="center", zorder=6)
            ax.text(x, y - row_h * 0.115, label, fontproperties=helvetica("bold"),
                    fontsize=8.8, color=MUTED, ha="center", va="center", zorder=6)
            cursor += stat_width

        draw_box(ax, HERO_L, bottom, ROW_R, upper, fill=RED, edge=RED, zorder=5)
        ax.text((HERO_L + ROW_R) / 2, y + row_h * 0.08, str(int(row["pts"])),
                fontproperties=helvetica("bold"), fontsize=23, color="white",
                ha="center", va="center", zorder=7)
        ax.text((HERO_L + ROW_R) / 2, y - row_h * 0.16, "PTS",
                fontproperties=helvetica("bold"), fontsize=9, color="white",
                ha="center", va="center", zorder=7)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=FINAL_DPI, transparent=True, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = render(load_data(args.data), args.output)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
