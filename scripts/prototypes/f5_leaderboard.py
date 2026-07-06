"""Prototype: F5-style eye-candy leaderboard — Bulls scoring leaders.

Top-10 Bulls by points per game in The F5's engagement format (headshot
rows, magnitude-colored bars, outlined values) restyled to the house
look. Reads cached season box scores, renders 1080x1350 at 300 DPI
(2160x2700 export). Two views: all players + current roster.

Change STAT_COL / labels below for future topics — layout stays put.
"""
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd

from bulls.data.fetch import get_player_headshot
from bulls.graphics.craft import (
    FAINT,
    INK,
    MUTED,
    RULE,
    gradient_bar,
    headshot_label,
    stacked_label,
    threshold_footer,
)
from bulls.graphics.feed import (
    DEFAULT_DPI,
    INSTAGRAM_FEED_HEIGHT_PX,
    INSTAGRAM_FEED_WIDTH_PX,
    _fp_body,
    _fp_title,
    save_feed_post,
)

BOX_CSV = _REPO / "cache" / "box_scores_2025-26.csv"
ROSTER_CSV = _REPO / "cache" / "roster_2025-26.csv"
HEADSHOT_CACHE = _REPO / "cache" / "headshots"
OUTPUT_DIR = _REPO / "output" / "feed"

MIN_GAMES = 20
TOP_N = 10
EXPORT_DPI = 300  # 2160x2700 — text survives Instagram recompression

STAT_COL = "ppg"
TITLE = "Bulls Scoring Leaders"
SUBTITLE = "Points per game | 2025-26 Season"
COVERAGE = "2025-26 regular season"


def parse_minutes(val) -> float:
    """BoxScoreTraditionalV3 minutes come as 'MM:SS' strings ('' for DNP)."""
    if pd.isna(val):
        return 0.0
    s = str(val)
    if ":" not in s:
        return float(s) if s.strip() else 0.0
    mm, ss = s.split(":")
    return int(mm) + int(ss) / 60


def compute_leaders(box: pd.DataFrame) -> pd.DataFrame:
    box = box.copy()
    box["min_played"] = box["minutes"].map(parse_minutes)
    played = box[box["min_played"] > 0]

    agg = played.groupby(["personId", "name"], as_index=False).agg(
        games=("game_id", "nunique"),
        pts=("points", "sum"),
        mins=("min_played", "sum"),
    )
    agg["ppg"] = agg["pts"] / agg["games"]
    agg["mpg"] = agg["mins"] / agg["games"]

    agg = agg[agg["games"] >= MIN_GAMES]
    return agg.sort_values(STAT_COL, ascending=False).reset_index(drop=True)


def build_leaderboard(
    leaders: pd.DataFrame,
    title: str = TITLE,
    subtitle: str = SUBTITLE,
) -> plt.Figure:
    rows = leaders.head(TOP_N)

    figsize = (INSTAGRAM_FEED_WIDTH_PX / DEFAULT_DPI, INSTAGRAM_FEED_HEIGHT_PX / DEFAULT_DPI)
    fig = plt.figure(figsize=figsize, facecolor="#FFFFFF")
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, INSTAGRAM_FEED_WIDTH_PX)
    ax.set_ylim(0, INSTAGRAM_FEED_HEIGHT_PX)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    top = INSTAGRAM_FEED_HEIGHT_PX
    ax.text(60, top - 70, title, ha="left", va="top",
            fontsize=44, color=INK, fontproperties=_fp_title(weight="bold"))
    ax.text(60, top - 185, subtitle, ha="left", va="top",
            fontsize=18, color=MUTED, fontproperties=_fp_body(weight="medium"))

    # Row geometry
    x_rank = 85
    x_photo = 152
    x_name = 210
    bar_x0 = 455
    bar_len = 475  # full length at the board's max value
    val_pad = 12

    row_top = top - 250
    row_h = 96
    bar_h = 34
    vmax = max(rows[STAT_COL].max(), 1.0)

    photo_r = 37

    for i, row in rows.iterrows():
        y = row_top - i * row_h - row_h / 2

        if i > 0:
            ax.plot([60, 1020], [y + row_h / 2, y + row_h / 2],
                    color=RULE, lw=0.8, solid_capstyle="butt")

        ax.text(x_rank, y, str(i + 1), ha="right", va="center",
                fontsize=20, color=FAINT, fontproperties=_fp_body(weight="bold"))

        headshot = get_player_headshot(int(row["personId"]), cache_dir=str(HEADSHOT_CACHE))
        headshot_label(ax, Path(headshot) if headshot else None, x_photo, y, radius=photo_r)

        stacked_label(
            ax, x_name, y,
            primary=row["name"],
            secondary=f"{int(row['games'])} GP · {row['mpg']:.1f} MPG",
            gap=13, primary_size=16, secondary_size=11,
        )

        bar = gradient_bar(ax, y, row[STAT_COL], vmin=0.0, vmax=vmax,
                           x0=bar_x0, length=bar_len, height=bar_h)
        bar_w = bar.get_width()

        # Outlined value at the bar tip: inside when it fits, outside when not.
        label = f"{row[STAT_COL]:.1f}"
        if bar_w > 110:
            ax.text(bar_x0 + bar_w - val_pad, y, label, ha="right", va="center",
                    fontsize=18, color="#FFFFFF",
                    fontproperties=_fp_body(weight="bold"),
                    path_effects=[pe.withStroke(linewidth=2.2, foreground=INK)])
        else:
            ax.text(bar_x0 + bar_w + val_pad, y, label, ha="left", va="center",
                    fontsize=18, color=INK, fontproperties=_fp_body(weight="bold"))

    threshold_footer(fig, f"Min. {MIN_GAMES} games", COVERAGE, "data: NBA.com/Stats")
    return fig


def main():
    if not BOX_CSV.exists() or not ROSTER_CSV.exists():
        sys.exit("Missing season cache CSVs — see scripts/prototypes/README.md to rebuild.")
    box = pd.read_csv(BOX_CSV)
    leaders = compute_leaders(box)
    print(leaders[["name", "games", "ppg", "mpg"]].head(TOP_N).to_string())

    stamp = date.today().isoformat()

    fig = build_leaderboard(leaders)
    path = save_feed_post(fig, OUTPUT_DIR / f"{stamp}-f5-leaderboard-season.png", dpi=EXPORT_DPI)
    print(f"Saved {path}")
    plt.close(fig)

    roster = pd.read_csv(ROSTER_CSV)
    roster_ids = set(roster["player_id"].astype(int))
    current = leaders[leaders["personId"].astype(int).isin(roster_ids)].reset_index(drop=True)
    if current.empty:
        sys.exit("No current-roster players meet the MIN_GAMES threshold — stale/empty roster cache?")
    print(current[["name", "games", "ppg", "mpg"]].head(TOP_N).to_string())
    fig = build_leaderboard(
        current, subtitle=SUBTITLE + " | Current Roster")
    path = save_feed_post(
        fig, OUTPUT_DIR / f"{stamp}-f5-leaderboard-current-roster.png", dpi=EXPORT_DPI)
    print(f"Saved {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
