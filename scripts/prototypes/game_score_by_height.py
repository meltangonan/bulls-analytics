"""Rank and render the best Bulls game at every listed height since 2000.

Regular-season and playoff player-games share one eligibility pool. The script
reuses the audited Hollinger Game Score calculation and the player-level height
contract from the existing height ladder, then renders three review formats.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.graphics import house
from scripts.prototypes import height_ladder_cards as height_cards
from scripts.prototypes.top_game_performances import game_score

FIRST_END_YEAR = 2001
LAST_END_YEAR = 2026
PROJECT = "game-score-by-height"
DATA = _REPO / "docs" / "visuals" / "2026-08-25-game-score-by-height" / "data"
HEIGHT_DATA = _REPO / "docs" / "visuals" / "2026-08-20-most-ppg-at-each-height" / "data"
CACHE = _REPO / "cache" / "nba.com" / "top-game-performances"
OUT = _REPO / "output"

# Players absent from the historical Bulls roster snapshots. These values are
# from NBA.com's CommonPlayerInfo endpoint and complete the player-height join.
PROFILE_HEIGHTS = {
    1724: "6-3", 2064: "5-10", 21: "6-1", 1563: "6-2", 2839: "6-9",
    101211: "6-6", 2450: "6-9", 693: "6-10", 201242: "6-5",
    203129: "6-9", 203513: "6-10", 202363: "6-9", 201858: "6-7",
    1626154: "6-5", 202347: "6-7", 1627770: "5-9", 203960: "6-7",
    203953: "6-7", 1627755: "5-10", 1628035: "6-7", 1628395: "6-7",
    1628993: "6-8", 201609: "6-4", 1630537: "6-5", 1631093: "6-3",
    1642280: "6-9",
}

# NBA game id 0041000203 is 2011 Eastern Conference Semifinals Game 3.
PLAYOFF_GAME_CONTEXT = {"0041000203": "(RD 2 GM3)"}

WIDTH = 1500
ROW_H = 116
TOP = 104
BOTTOM = 42
RED = house.DEFAULT_THEME.accent
THEME = house.DEFAULT_THEME

# Fixed to the interpretation printed on the existing Game Score explainer:
# 10+ average, 20+ very good, 30+ star-level, 40+ dominant, 50+ historic.
# These are semantic bands, never recalculated from the ladder's min/max.
GAME_SCORE_BANDS = (
    (50.0, "#2F8F4E"),
    (40.0, "#70AD5A"),
    (30.0, "#F2D46B"),
    (20.0, "#E98B52"),
    (float("-inf"), "#D64545"),
)


def game_score_fill(value: float) -> str:
    """Return the settled interpretation colour for a Game Score."""
    score = float(value)
    return next(color for minimum, color in GAME_SCORE_BANDS if score >= minimum)


def height_inches(value: str) -> int:
    feet, inches = str(value).split("-")
    return int(feet) * 12 + int(inches)


def display_height(value: str) -> str:
    feet, inches = str(value).split("-")
    return f"{feet}′{inches}″"


def canonical_heights(rosters: pd.DataFrame) -> pd.DataFrame:
    """Return one listed height per player, matching the original ladder."""
    heights = (
        rosters[["PLAYER_ID", "HEIGHT", "SEASON"]]
        .dropna(subset=["HEIGHT"])
        .sort_values("SEASON")
        .drop_duplicates("PLAYER_ID", keep="last")[["PLAYER_ID", "HEIGHT"]]
    )
    supplements = pd.DataFrame(
        {"PLAYER_ID": list(PROFILE_HEIGHTS), "HEIGHT": list(PROFILE_HEIGHTS.values())}
    )
    return pd.concat([heights, supplements], ignore_index=True).drop_duplicates(
        "PLAYER_ID", keep="last"
    )


def select_height_winners(games: pd.DataFrame, heights: pd.DataFrame) -> pd.DataFrame:
    """Select the top player-game per height with deterministic tie-breaking."""
    joined = games.merge(
        heights, left_on="player_id", right_on="PLAYER_ID", how="left", validate="many_to_one"
    )
    if joined["HEIGHT"].isna().any():
        missing = joined.loc[joined["HEIGHT"].isna(), "player"].drop_duplicates().tolist()
        raise ValueError(f"Missing listed heights for: {missing}")
    joined["height_in"] = joined["HEIGHT"].map(height_inches)
    joined["game_score"] = joined.apply(game_score, axis=1)
    return (
        joined.sort_values(
            ["height_in", "game_score", "minutes", "game_date"],
            ascending=[True, False, False, True],
        )
        .drop_duplicates("height_in")
        .sort_values("height_in")
        .reset_index(drop=True)
    )


def load_games() -> pd.DataFrame:
    frames = []
    for pool, slug in (("Regular season", "regular-season"), ("Playoffs", "playoffs")):
        for end_year in range(FIRST_END_YEAR, LAST_END_YEAR + 1):
            path = CACHE / f"CHI-players-{slug}-{end_year}.csv"
            frame = pd.read_csv(path, dtype={"game_id": str})
            frame["pool"] = pool
            frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build_data() -> pd.DataFrame:
    games = load_games()
    rosters = pd.read_csv(HEIGHT_DATA / "raw_rosters.csv")
    winners = select_height_winners(games, canonical_heights(rosters))
    DATA.mkdir(parents=True, exist_ok=True)
    winners.to_csv(DATA / "game-score-by-height.csv", index=False)
    return winners


def _name(value: str) -> str:
    return str(value).replace(" III", "")


def _context(row: pd.Series) -> str:
    date = pd.Timestamp(row.game_date).strftime("%b %-d, %Y")
    site = "vs" if "vs." in row.matchup else "at"
    marker = " · PO" if row.pool == "Playoffs" else ""
    return f"{date} · {site} {row.opponent} · {row.result}{marker}"


def _context_parts(row: pd.Series) -> tuple[str, str, str, str]:
    """Return context pieces so result alone can carry semantic colour."""
    date = pd.Timestamp(row.game_date).strftime("%b %-d, %Y")
    site = "vs" if "vs." in row.matchup else "at"
    playoff = PLAYOFF_GAME_CONTEXT.get(str(row.game_id), "")
    return date, f"{site} {row.opponent}", str(row.result), playoff


def _portrait(ax, row, x: float, y: float, size: float) -> None:
    post_portrait = HEIGHT_DATA / "portraits" / f"{int(row.player_id)}.png"
    path = post_portrait if post_portrait.is_file() else house.HEADSHOT_CACHE / f"{int(row.player_id)}.png"
    try:
        image = plt.imread(path)
    except (FileNotFoundError, OSError, ValueError):
        return
    h, w = image.shape[:2]
    side = min(int(h * 0.72), w)
    left = max(0, (w - side) // 2)
    ax.imshow(image[:side, left:left + side], extent=[x-size, x+size, y-size, y+size], zorder=5)


def _canvas(rows: int):
    height = TOP + rows * ROW_H + BOTTOM
    fig, ax = plt.subplots(figsize=(WIDTH / 150, height / 150), dpi=150)
    fig.patch.set_alpha(0)
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    return fig, ax, height


def _save(fig, variant: str, page: int, final: bool) -> Path:
    OUT.mkdir(exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / f"game-score-by-height-{variant}-p{page}-{suffix}.png"
    fig.savefig(path, dpi=300 if final else 150, transparent=True, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return path


def render_table(rows: pd.DataFrame, page: int, final: bool) -> Path:
    fig, ax, height = _canvas(len(rows))
    headers = [(52, "HT", "left"), (220, "PLAYER / GAME", "left"), (758, "GMSC", "center"),
               (862, "PTS", "center"), (952, "FG", "center"), (1055, "3PT", "center"),
               (1150, "FT", "center"), (1245, "REB", "center"), (1335, "AST", "center"),
               (1420, "STK", "center")]
    for x, label, align in headers:
        ax.text(x, height-54, label, ha=align, va="center", color=RED if label == "GMSC" else THEME.ink,
                fontsize=11.5, fontproperties=house.helvetica("bold"))
    ax.plot([40,1460],[height-82,height-82],color=THEME.ink,lw=2)
    for i, (_, row) in enumerate(rows.iterrows()):
        y = height - TOP - i*ROW_H - ROW_H/2
        if i: ax.plot([40,1460],[y+ROW_H/2,y+ROW_H/2],color=THEME.rule,lw=1)
        ax.add_patch(Rectangle((42,y-34),112,68,facecolor=RED,edgecolor="none"))
        ax.text(98,y,display_height(row.HEIGHT),ha="center",va="center",color="white",fontsize=18,
                fontproperties=house.helvetica("bold"))
        _portrait(ax,row,190,y+3,51)
        ax.text(252,y+13,_name(row.player),ha="left",va="center",color=THEME.ink,fontsize=19,
                fontproperties=house.helvetica("bold"))
        ax.text(252,y-20,_context(row),ha="left",va="center",color=THEME.muted,fontsize=10.5,
                fontproperties=house.helvetica())
        ax.add_patch(Rectangle((708,y-43),100,86,facecolor=RED,edgecolor="none"))
        vals=[(758,f"{row.game_score:.1f}","white"),(862,int(row.points),THEME.ink),
              (952,f"{int(row.fgm)}–{int(row.fga)}",THEME.ink),(1055,f"{int(row.fg3m)}–{int(row.fg3a)}",THEME.ink),
              (1150,f"{int(row.ftm)}–{int(row.fta)}",THEME.ink),(1245,int(row.reb),THEME.ink),
              (1335,int(row.ast),THEME.ink),(1420,f"{int(row.stl)}+{int(row.blk)}",THEME.ink)]
        for x,val,color in vals:
            ax.text(x,y,str(val),ha="center",va="center",color=color,fontsize=14.5,
                    fontproperties=house.helvetica("bold" if x==758 else "regular"))
    return _save(fig,"table",page,final)


def render_ladder(rows: pd.DataFrame, page: int, final: bool) -> Path:
    fig, ax, height = _canvas(len(rows))
    for i, (_, row) in enumerate(rows.iterrows()):
        y=height-TOP-i*ROW_H-ROW_H/2
        ax.add_patch(Rectangle((28,y-47),1444,94,facecolor="#F8E9ED",edgecolor=RED,lw=2.2))
        ax.add_patch(Rectangle((31,y-44),190,88,facecolor=RED,edgecolor="none"))
        ax.text(126,y,display_height(row.HEIGHT),ha="center",va="center",color="white",fontsize=25,
                fontproperties=house.helvetica("bold"))
        _portrait(ax,row,294,y+6,61)
        ax.text(374,y+15,_name(row.player),ha="left",va="center",color=THEME.ink,fontsize=18,
                fontproperties=house.helvetica("bold"))
        ax.text(374,y-20,_context(row),ha="left",va="center",color=THEME.muted,fontsize=11,
                fontproperties=house.helvetica())
        ax.text(760,y+15,f"{int(row.points)} PTS · {int(row.reb)} REB · {int(row.ast)} AST",ha="left",va="center",
                color=THEME.ink,fontsize=12.5,fontproperties=house.helvetica("bold"))
        ax.text(760,y-20,f"{int(row.stl)} STL · {int(row.blk)} BLK · {int(row.tov)} TOV",ha="left",va="center",
                color=THEME.muted,fontsize=11,fontproperties=house.helvetica())
        ax.add_patch(Rectangle((1130,y-44),339,88,facecolor=RED,edgecolor="none"))
        ax.text(1299,y+13,f"{row.game_score:.1f}",ha="center",va="center",color="white",fontsize=27,
                fontproperties=house.helvetica("bold"))
        ax.text(1299,y-23,"GAME SCORE",ha="center",va="center",color="white",fontsize=11,
                fontproperties=house.helvetica("bold"))
    return _save(fig,"ladder",page,final)


def render_hybrid(rows: pd.DataFrame, page: int, final: bool) -> Path:
    """Reuse the PPG ladder exactly, replacing its content rather than its grammar."""
    rows_tall = 10
    fig_h = height_cards.figure_height(rows_tall)
    fig, ax = plt.subplots(figsize=(height_cards.FIG_W, fig_h))
    fig.patch.set_alpha(0)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_axis_off()
    ax.patch.set_alpha(0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("auto")
    ax.autoscale(False)

    row_h = height_cards.ROW_H_IN / fig_h
    top = 1 - height_cards.PAD_TOP_IN / fig_h
    stripe_y = height_cards.STRIPE * height_cards.FIG_W / fig_h
    height_right = 0.112
    portrait_x = 0.170
    name_x = 0.235
    game_score_left = 0.895
    for i, (_, row) in enumerate(rows.iterrows()):
        y = top - (i + 0.5) * row_h
        zorder = 10 + i
        box_h = row_h * 0.86
        bottom = y - box_h / 2
        height_cards.striped_box(
            ax, height_cards.X_ROW_L, bottom,
            height_cards.X_ROW_R - height_cards.X_ROW_L, box_h,
            height_cards.BULLS_RED,
            height_cards._mix("#FFFFFF", height_cards.BULLS_RED, 0.11),
            fig_h, zorder=2,
        )
        ax.add_patch(Rectangle(
            (height_cards.X_ROW_L + height_cards.STRIPE, bottom + stripe_y),
            height_right - height_cards.X_ROW_L - height_cards.STRIPE,
            box_h - 2 * stripe_y, facecolor=height_cards.BULLS_RED,
            edgecolor="none", zorder=3,
        ))
        ax.text(
            (
                height_cards.X_ROW_L
                + height_cards.STRIPE
                + height_right
            ) / 2,
            y, row.HEIGHT,
            fontproperties=house.helvetica("bold"), fontsize=26,
            color="white", ha="center", va="center", zorder=4,
        )
        project_portrait = DATA / "portraits" / f"{int(row.player_id)}.png"
        height_ladder_portrait = HEIGHT_DATA / "portraits" / f"{int(row.player_id)}.png"
        if project_portrait.is_file():
            portrait = project_portrait
        elif height_ladder_portrait.is_file():
            portrait = height_ladder_portrait
        else:
            portrait = house.HEADSHOT_CACHE / f"{int(row.player_id)}.png"
        player_id = int(row.player_id)
        framed_portrait = DATA / "portraits" / f"{player_id}-framed.png"
        if framed_portrait.is_file():
            portrait = framed_portrait
        portrait_scale = {
            101249: 1.05,  # John Lucas: bring the smaller crop back toward the shared scale.
            2064: 0.98,   # Khalid El-Amin: full-height frame shows more neck.
            2398: 0.98,   # Jay Williams: full-height frame shows more neck.
        }.get(player_id, height_cards.PORTRAIT_SCALE)
        face_crop_fraction = 1.0 if player_id in {2064, 2398} else None
        height_cards.place_portrait(
            ax, portrait, portrait_x,
            bottom + height_cards.PORTRAIT_LIFT_IN / fig_h,
            row_h * portrait_scale, fig_h, zorder,
            face_crop_fraction=face_crop_fraction,
        )

        ax.text(
            name_x, y + row_h * 0.12, _name(row.player),
            fontproperties=house.helvetica("bold"), fontsize=19,
            color=THEME.ink, ha="left", va="center", zorder=5,
        )
        date, opponent, result, playoff = _context_parts(row)
        context_y = y - row_h * 0.18
        context_font = house.helvetica()
        date_artist = ax.text(
            name_x, context_y, date, fontproperties=context_font, fontsize=12,
            color=THEME.muted, ha="left", va="center", zorder=5,
        )
        opponent_x = name_x + house.rendered_width(ax, date_artist) + 0.006
        opponent_artist = ax.text(
            opponent_x, context_y, opponent, fontproperties=context_font, fontsize=12,
            color=THEME.muted, ha="left", va="center", zorder=5,
        )
        playoff_x = opponent_x + house.rendered_width(ax, opponent_artist) + 0.006
        if playoff:
            playoff_artist = ax.text(
                playoff_x, context_y, playoff, fontproperties=house.helvetica(),
                fontsize=10.5, color=THEME.muted, ha="left", va="center", zorder=5,
            )
            result_x = playoff_x + house.rendered_width(ax, playoff_artist) + 0.006
        else:
            result_x = playoff_x
        result_color = "#3FAE63" if result == "W" else "#D64545"
        ax.text(
            result_x, context_y, result, fontproperties=house.helvetica("bold"),
            fontsize=12, color=result_color, ha="left", va="center", zorder=5,
        )

        # Give every stat block the same visible gutter. FG needs a wider block
        # for made-attempted strings, so equal centre points would make its
        # neighbouring gaps look tighter than the others.
        stat_specs = (
            ("PTS", int(row.points), 0.040),
            ("FG", f"{int(row.fgm)}-{int(row.fga)}", 0.065),
            ("REB", int(row.reb), 0.045),
            ("AST", int(row.ast), 0.040),
            ("STL", int(row.stl), 0.040),
            ("BLK", int(row.blk), 0.040),
            ("+/-", f"{int(row.plus_minus):+d}", 0.045),
        )
        stat_cells = []
        stat_cursor = 0.520
        stat_gutter = 0.005
        for label, value, width in stat_specs:
            stat_cells.append((stat_cursor + width / 2, label, value))
            stat_cursor += width + stat_gutter
        for x, label, value in stat_cells:
            ax.text(x, y + row_h * 0.105, str(value), ha="center", va="center",
                    color=THEME.ink, fontsize=19,
                    fontproperties=house.helvetica("bold"), zorder=5)
            ax.text(x, y - row_h * 0.105, label, ha="center", va="center",
                    color=THEME.muted, fontsize=10,
                    fontproperties=house.helvetica("bold"), zorder=5)

        score_fill = game_score_fill(row.game_score)
        height_cards.striped_box(
            ax, game_score_left, bottom,
            height_cards.X_ROW_R - game_score_left, box_h,
            score_fill, score_fill, fig_h, zorder=5,
        )
        ax.text(
            (game_score_left + height_cards.X_ROW_R) / 2, y,
            f"{row.game_score:.1f}", fontproperties=house.helvetica("bold"),
            fontsize=21.5, color="white", ha="center", va="center", zorder=7,
            path_effects=[
                height_cards.path_effects.withStroke(
                    linewidth=3.5, foreground=house.BULLS_BLACK
                )
            ],
        )

    OUT.mkdir(exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / f"game-score-by-height-hybrid-p{page}-{suffix}.png"
    fig.savefig(path, dpi=400 if final else 200, transparent=True)
    plt.close(fig)
    return path


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--final",action="store_true")
    args=parser.parse_args()
    winners=build_data()
    house.ensure_headshots(winners.player_id.astype(int).tolist())
    paths=[]
    for page, rows in enumerate((winners.iloc[:10],winners.iloc[10:]),1):
        rows=rows.reset_index(drop=True)
        paths.extend([render_table(rows,page,args.final),render_ladder(rows,page,args.final),render_hybrid(rows,page,args.final)])
    print("\n".join(str(p) for p in paths))
    print("\nCANVA COPY")
    print("BEST BULLS GAME AT EVERY HEIGHT")
    print("Highest Game Score at each listed height since 2000")
    print("Regular season and playoffs · Listed height · NBA.com Stats")


if __name__ == "__main__":
    main()
