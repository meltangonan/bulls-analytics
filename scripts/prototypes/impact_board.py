"""Prototype: Most Impactful Bulls 2025-26 — ranked Game Score board.

Reads cached season box scores, computes avg Game Score per player,
renders a 1080x1350 board in the repo house style. Two views:
all players + current roster only.
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bulls.config import BULLS_RED
from bulls.data.fetch import get_player_headshot
from bulls.graphics.craft import _make_circular_headshot
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
OUTPUT_DIR = _REPO / "output" / "feed"

MIN_GAMES = 20
TOP_N = 10

INK = "#1A1A1A"
MUTED = "#777777"
FAINT = "#AAAAAA"
RULE = "#DDDDDD"
RED = "#CE1141"


def parse_minutes(val) -> float:
    """BoxScoreTraditionalV3 minutes come as 'MM:SS' strings ('' for DNP)."""
    if pd.isna(val):
        return 0.0
    s = str(val)
    if ":" not in s:
        return float(s) if s.strip() else 0.0
    mm, ss = s.split(":")
    return int(mm) + int(ss) / 60


def game_score(row) -> float:
    """Hollinger Game Score from a box-score line."""
    return (
        row["points"]
        + 0.4 * row["fieldGoalsMade"]
        - 0.7 * row["fieldGoalsAttempted"]
        - 0.4 * (row["freeThrowsAttempted"] - row["freeThrowsMade"])
        + 0.7 * row["reboundsOffensive"]
        + 0.3 * row["reboundsDefensive"]
        + row["steals"]
        + 0.7 * row["assists"]
        + 0.7 * row["blocks"]
        - 0.4 * row["foulsPersonal"]
        - row["turnovers"]
    )


def compute_board(box: pd.DataFrame) -> pd.DataFrame:
    box = box.copy()
    box["min_played"] = box["minutes"].map(parse_minutes)
    played = box[box["min_played"] > 0].copy()
    played["gmsc"] = played.apply(game_score, axis=1)

    agg = played.groupby(["personId", "name"], as_index=False).agg(
        games=("game_id", "nunique"),
        gmsc_avg=("gmsc", "mean"),
        pts=("points", "sum"),
        fga=("fieldGoalsAttempted", "sum"),
        fta=("freeThrowsAttempted", "sum"),
    )
    agg["ppg"] = agg["pts"] / agg["games"]
    tsa = agg["fga"] + 0.44 * agg["fta"]
    agg["ts_pct"] = np.where(tsa > 0, agg["pts"] / (2 * tsa) * 100, 0.0)

    agg = agg[agg["games"] >= MIN_GAMES]
    return agg.sort_values("gmsc_avg", ascending=False).reset_index(drop=True)


def build_impact_board(
    board: pd.DataFrame,
    title: str = "Most Impactful Bulls",
    subtitle: str = "Chicago Bulls | 2025-26 Season",
    kicker: str = f"Ranked by Avg. Game Score | Min. {MIN_GAMES} Games",
) -> plt.Figure:
    rows = board.head(TOP_N)

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
    ax.text(60, top - 235, kicker, ha="left", va="top",
            fontsize=14, color=RED, style="italic", fontproperties=_fp_body(weight="medium"))

    # Column geometry
    x_rank = 85
    x_photo = 150
    x_name = 205
    bar_x0, bar_x1 = 435, 720
    x_gmsc = bar_x1 + 18
    x_ppg, x_ts, x_gp = 870, 960, 1035

    header_y = top - 300
    ax.text(x_name, header_y, "PLAYER", ha="left", va="center",
            fontsize=11, color=MUTED, fontproperties=_fp_body(weight="bold"))
    ax.text(bar_x0, header_y, "AVG. GAME SCORE", ha="left", va="center",
            fontsize=11, color=MUTED, fontproperties=_fp_body(weight="bold"))
    for x, label in ((x_ppg, "PPG"), (x_ts, "TS%"), (x_gp, "GP")):
        ax.text(x, header_y, label, ha="center", va="center",
                fontsize=11, color=MUTED, fontproperties=_fp_body(weight="bold"))

    row_top = header_y - 30
    row_h = 92
    bar_h = 24
    max_gmsc = max(rows["gmsc_avg"].max(), 1.0)

    for i, row in rows.iterrows():
        y = row_top - i * row_h - row_h / 2

        if i > 0:
            ax.plot([60, 1035], [y + row_h / 2, y + row_h / 2],
                    color=RULE, lw=0.8, solid_capstyle="butt")

        ax.text(x_rank, y, str(i + 1), ha="right", va="center",
                fontsize=20, color=FAINT, fontproperties=_fp_body(weight="bold"))

        headshot_path = get_player_headshot(int(row["personId"]))
        if headshot_path and Path(headshot_path).exists():
            circ = _make_circular_headshot(Path(headshot_path))
            if circ is not None:
                r = 34
                ax.imshow(circ, extent=[x_photo - r, x_photo + r, y - r, y + r],
                          zorder=3, interpolation="bilinear")

        name = row["name"]
        if len(name) > 16:
            first, rest = name.split(" ", 1)
            name = f"{first[0]}. {rest}"
        ax.text(x_name, y, name, ha="left", va="center",
                fontsize=15, color=INK, fontproperties=_fp_body(weight="bold"))

        # Shared-scale bar
        w = (row["gmsc_avg"] / max_gmsc) * (bar_x1 - bar_x0)
        ax.add_patch(plt.Rectangle((bar_x0, y - bar_h / 2), w, bar_h,
                                   facecolor=RED, edgecolor="none", zorder=2))
        ax.text(x_gmsc, y, f"{row['gmsc_avg']:.1f}", ha="left", va="center",
                fontsize=17, color=INK, fontproperties=_fp_body(weight="bold"))

        ax.text(x_ppg, y, f"{row['ppg']:.1f}", ha="center", va="center",
                fontsize=14, color=MUTED, fontproperties=_fp_body(weight="medium"))
        ax.text(x_ts, y, f"{row['ts_pct']:.1f}", ha="center", va="center",
                fontsize=14, color=MUTED, fontproperties=_fp_body(weight="medium"))
        ax.text(x_gp, y, f"{int(row['games'])}", ha="center", va="center",
                fontsize=14, color=MUTED, fontproperties=_fp_body(weight="medium"))

    ax.text(60, 40, "Data via NBA.com/Stats", ha="left", va="bottom",
            fontsize=8.5, color=FAINT, fontproperties=_fp_body())
    ax.text(60, 62,
            "Game Score (Hollinger): one box-score number covering scoring, "
            "rebounds, assists, defense, turnovers.",
            ha="left", va="bottom", fontsize=8.5, color=FAINT, fontproperties=_fp_body())

    return fig


def main():
    if not BOX_CSV.exists() or not ROSTER_CSV.exists():
        sys.exit("Missing season cache CSVs — see scripts/prototypes/README.md to rebuild.")
    box = pd.read_csv(BOX_CSV)
    board = compute_board(box)
    print(board[["name", "games", "gmsc_avg", "ppg", "ts_pct"]].head(15).to_string())

    fig = build_impact_board(board)
    path = save_feed_post(fig, OUTPUT_DIR / "2026-07-03-impact-board-season.png")
    print(f"Saved {path}")
    plt.close(fig)

    roster = pd.read_csv(ROSTER_CSV)
    roster_ids = set(roster["player_id"].astype(int))
    current = board[board["personId"].astype(int).isin(roster_ids)].reset_index(drop=True)
    fig = build_impact_board(
        current, subtitle="Chicago Bulls | 2025-26 Season | Current Roster")
    path = save_feed_post(fig, OUTPUT_DIR / "2026-07-03-impact-board-season-current-roster.png")
    print(f"Saved {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
