"""Top-ten Bulls dunk seasons since 2010-11, by type, as boxed leaderboard cards.

Dunks are not a box-score stat. NBA shot charts label every dunk variant with
the word Dunk in ACTION_TYPE; this post counts made attempts of those labels
on Chicago-only regular-season stints, 2010-11 through 2025-26.

Five slides share one grammar: all dunks, then driving, running, alley-oop, and
putback. A dunk with two labels (a running alley-oop, a driving reverse) counts
on each matching type slide. Cutting and standing dunks stay inside the total
board only — cutting is a 2015-16-onward label, and standing absorbs whatever
the scorer has not split out.

The renderer produces transparent chart assets. Canva owns the title, subtitle,
source line, and page framing.
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.patches import Rectangle
from nba_api.stats.endpoints import leaguedashplayerstats, shotchartdetail

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.config import API_DELAY, BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house
from bulls.graphics.house import FINAL_DPI, HEADSHOT_CACHE, helvetica
from bulls.visuals import visual_dir
from scripts.prototypes import height_ladder_cards as height_cards

PROJECT = "most-dunks-since-2010"
FIRST_SEASON_END_YEAR = 2011
LAST_SEASON_END_YEAR = 2026
TOP_N = 10
RETRY_ATTEMPTS = 4

OUT = _REPO / "output" / PROJECT
POST_DATA = visual_dir(_REPO / "docs" / "visuals", PROJECT) / "data"
RAW_SHOTS = POST_DATA / "raw" / "shots"
RAW_PLAYERS = POST_DATA / "raw" / "players"

INK = "#242424"
MUTED = "#5F5B57"
BULLS_RED = "#CE1141"

SHOT_COLS = [
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ID",
    "GAME_ID",
    "ACTION_TYPE",
    "SHOT_ATTEMPTED_FLAG",
    "SHOT_MADE_FLAG",
    "SHOT_ZONE_BASIC",
]
PLAYER_COLS = ["PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "FGA", "FGM"]

SUPPORTING_STATS = (
    ("ATT", "dunk_fga", 0.070),
    ("FG%", "fg_pct_display", 0.080),
    ("GP", "games_played", 0.055),
    ("/G", "per_game_display", 0.070),
)


@dataclass(frozen=True)
class DunkType:
    """One carousel slide: a label-matcher over shot-chart ACTION_TYPE."""

    slug: str
    title: str
    subtitle: str
    kind: str  # "all", "contains", or "putback"
    needle: str = ""

    def matches(self, action_type: object) -> bool:
        if self.kind == "all":
            return is_dunk(action_type)
        if self.kind == "putback":
            action = str(action_type or "").lower()
            return any(token in action for token in ("putback", "follow up", "tip dunk"))
        return self.needle in str(action_type or "").lower()


SLIDES = (
    DunkType(
        "total",
        "MOST DUNKS IN A SEASON",
        "Top 10 Bulls dunk seasons since 2010–11",
        "all",
    ),
    DunkType(
        "driving",
        "MOST DRIVING DUNKS",
        "Off the dribble, half-court attack — since 2010–11",
        "contains",
        "driving",
    ),
    DunkType(
        "running",
        "MOST RUNNING DUNKS",
        "Already in motion — leak-outs, filling the lane — since 2010–11",
        "contains",
        "running",
    ),
    DunkType(
        "alley-oop",
        "MOST ALLEY-OOPS",
        "Catch-and-finish dunks since 2010–11",
        "contains",
        "alley oop",
    ),
    DunkType(
        "putback",
        "MOST PUTBACK DUNKS",
        "Putbacks, tips, and follow-ups since 2010–11",
        "putback",
    ),
)


def is_dunk(action_type: object) -> bool:
    """NBA shot-detail labels every dunk variant with the word Dunk."""
    return "dunk" in str(action_type or "").lower()


def season_label(end_year: int) -> str:
    return f"{end_year - 1}-{str(end_year)[2:]}"


def display_season(season: str) -> str:
    return str(season).replace("-", "–")


def display_name(name: object) -> str:
    return str(name).replace(" III", "")


def one_decimal(value: float) -> str:
    return str(Decimal(repr(float(value))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def two_decimals(value: float) -> str:
    return str(Decimal(repr(float(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def seasons() -> list[str]:
    return [season_label(end_year) for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1)]


def _request_frame(endpoint, **kwargs) -> pd.DataFrame:
    last_error = None
    for attempt in range(RETRY_ATTEMPTS):
        time.sleep(API_DELAY * (1 + attempt * 4))
        try:
            return endpoint(timeout=60, headers=_NBA_HEADERS, **kwargs).get_data_frames()[0]
        except (requests.Timeout, requests.ConnectionError, ValueError) as error:
            last_error = error
            print(f"  retry {attempt + 1}/{RETRY_ATTEMPTS - 1}: {error}", flush=True)
    raise RuntimeError("NBA.com did not respond") from last_error


def _cached_csv(path: Path, fetch) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = fetch()
    frame.to_csv(path, index=False)
    return frame


def fetch_season_shots(season: str) -> pd.DataFrame:
    def pull() -> pd.DataFrame:
        print(f"fetching shots {season}", flush=True)
        frame = _request_frame(
            shotchartdetail.ShotChartDetail,
            team_id=BULLS_TEAM_ID,
            player_id=0,
            season_nullable=season,
            season_type_all_star="Regular Season",
            context_measure_simple="FGA",
        )
        if frame.empty:
            raise RuntimeError(f"no shot chart for {season}")
        missing = [col for col in SHOT_COLS if col not in frame.columns]
        if missing:
            raise RuntimeError(f"{season} shots missing {missing}")
        return frame[SHOT_COLS].copy()

    return _cached_csv(RAW_SHOTS / f"{season}.csv", pull)


def fetch_season_players(season: str) -> pd.DataFrame:
    def pull() -> pd.DataFrame:
        print(f"fetching players {season}", flush=True)
        frame = _request_frame(
            leaguedashplayerstats.LeagueDashPlayerStats,
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            team_id_nullable=BULLS_TEAM_ID,
        )
        if frame.empty:
            raise RuntimeError(f"no player stats for {season}")
        return frame[PLAYER_COLS].copy()

    return _cached_csv(RAW_PLAYERS / f"{season}.csv", pull)


def load_dunks() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return every Chicago dunk attempt in the window, plus player-season GP."""
    dunk_rows = []
    player_rows = []
    for season in seasons():
        shots = fetch_season_shots(season)
        if shots.empty:
            raise RuntimeError(f"empty shot chart for {season}")
        dunks = shots.loc[shots["ACTION_TYPE"].map(is_dunk)].copy()
        dunks["season"] = season
        dunk_rows.append(dunks)
        players = fetch_season_players(season).copy()
        players["season"] = season
        player_rows.append(players)
    dunks = pd.concat(dunk_rows, ignore_index=True)
    players = pd.concat(player_rows, ignore_index=True)
    if set(dunks["season"].unique()) != set(seasons()):
        raise RuntimeError("shot-chart coverage is missing a season in the window")
    if set(players["season"].unique()) != set(seasons()):
        raise RuntimeError("player-stat coverage is missing a season in the window")
    return dunks, players


def rank_board(
    dunks: pd.DataFrame,
    players: pd.DataFrame,
    dunk_type: DunkType,
    top_n: int = TOP_N,
) -> pd.DataFrame:
    """Top player-seasons for one dunk type, Chicago-only regular-season stints."""
    matched = dunks.loc[dunks["ACTION_TYPE"].map(dunk_type.matches)].copy()
    if matched.empty:
        raise RuntimeError(f"no {dunk_type.slug} dunks in the window")
    agg = (
        matched.groupby(["season", "PLAYER_ID", "PLAYER_NAME"], as_index=False)
        .agg(
            dunk_fgm=("SHOT_MADE_FLAG", "sum"),
            dunk_fga=("SHOT_ATTEMPTED_FLAG", "sum"),
        )
    )
    merged = agg.merge(
        players[["season", "PLAYER_ID", "GP"]],
        on=["season", "PLAYER_ID"],
        how="left",
    )
    if merged["GP"].isna().any():
        missing = merged.loc[merged["GP"].isna(), ["PLAYER_NAME", "season"]]
        raise RuntimeError(f"dunk seasons with no GP join: {missing.to_dict('records')}")
    merged["games_played"] = merged["GP"].astype(int)
    merged["dunk_fg_pct"] = 100 * merged["dunk_fgm"] / merged["dunk_fga"]
    merged["dunks_per_game"] = merged["dunk_fgm"] / merged["games_played"]
    ranked = merged.sort_values(
        ["dunk_fgm", "dunks_per_game", "dunk_fg_pct", "season"],
        ascending=[False, False, False, False],
        kind="stable",
    ).reset_index(drop=True)
    ranked.insert(0, "rank", ranked.index + 1)
    ranked["display_name"] = ranked["PLAYER_NAME"].map(display_name)
    ranked["season_display"] = ranked["season"].map(display_season)
    ranked["fg_pct_display"] = ranked["dunk_fg_pct"].map(one_decimal)
    ranked["per_game_display"] = ranked["dunks_per_game"].map(two_decimals)
    ranked["dunk_type"] = dunk_type.slug
    top = ranked.head(top_n).copy()
    if len(top) != top_n:
        raise RuntimeError(f"{dunk_type.slug} produced {len(top)} rows, not {top_n}")
    return top


def build_all_boards(dunks: pd.DataFrame, players: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {slide.slug: rank_board(dunks, players, slide) for slide in SLIDES}


def save_working_tables(dunks: pd.DataFrame, boards: dict[str, pd.DataFrame]) -> None:
    POST_DATA.mkdir(parents=True, exist_ok=True)
    dunks.to_csv(POST_DATA / "all-dunk-attempts.csv", index=False)
    pd.concat(boards.values(), ignore_index=True).to_csv(
        POST_DATA / "top-ten-by-type.csv", index=False
    )
    for slug, board in boards.items():
        board.to_csv(POST_DATA / f"top-ten-{slug}.csv", index=False)


def render_board(board: pd.DataFrame, dunk_type: DunkType, *, final: bool = False) -> Path:
    if len(board) != TOP_N:
        raise ValueError(f"Expected {TOP_N} rows; got {len(board)}.")
    rows = board.sort_values("rank", kind="stable").reset_index(drop=True)
    house.ensure_headshots(rows["PLAYER_ID"])
    house.ensure_silhouette()

    fig_h = height_cards.figure_height(TOP_N)
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
    rank_right = 0.112
    portrait_x = 0.170
    name_x = 0.235
    dunks_left = 0.895

    for index, row in rows.iterrows():
        y = top - (index + 0.5) * row_h
        zorder = 10 + index
        box_h = row_h * 0.86
        bottom = y - box_h / 2
        height_cards.striped_box(
            ax,
            height_cards.X_ROW_L,
            bottom,
            height_cards.X_ROW_R - height_cards.X_ROW_L,
            box_h,
            BULLS_RED,
            height_cards._mix("#FFFFFF", BULLS_RED, 0.11),
            fig_h,
            zorder=2,
        )
        ax.add_patch(
            Rectangle(
                (height_cards.X_ROW_L + height_cards.STRIPE, bottom + stripe_y),
                rank_right - height_cards.X_ROW_L - height_cards.STRIPE,
                box_h - 2 * stripe_y,
                facecolor=BULLS_RED,
                edgecolor="none",
                zorder=3,
            )
        )
        ax.text(
            (height_cards.X_ROW_L + height_cards.STRIPE + rank_right) / 2,
            y,
            f"#{int(row['rank'])}",
            fontproperties=helvetica("bold"),
            fontsize=25,
            color="white",
            ha="center",
            va="center",
            zorder=4,
        )
        portrait = HEADSHOT_CACHE / f"{int(row['PLAYER_ID'])}.png"
        height_cards.place_portrait(
            ax,
            portrait if portrait.is_file() else house.portrait_path(int(row["PLAYER_ID"])),
            portrait_x,
            bottom + height_cards.PORTRAIT_LIFT_IN / fig_h,
            row_h * height_cards.PORTRAIT_SCALE,
            fig_h,
            zorder,
        )
        ax.text(
            name_x,
            y + row_h * 0.12,
            row["display_name"],
            fontproperties=helvetica("bold"),
            fontsize=19,
            color=INK,
            ha="left",
            va="center",
            zorder=5,
        )
        ax.text(
            name_x,
            y - row_h * 0.18,
            row["season_display"],
            fontproperties=helvetica(),
            fontsize=13,
            color=MUTED,
            ha="left",
            va="center",
            zorder=5,
        )

        values = {
            "dunk_fga": int(row["dunk_fga"]),
            "fg_pct_display": row["fg_pct_display"],
            "games_played": int(row["games_played"]),
            "per_game_display": row["per_game_display"],
        }
        stat_cursor = 0.520
        stat_gutter = 0.008
        for label, key, width in SUPPORTING_STATS:
            x = stat_cursor + width / 2
            ax.text(
                x,
                y + row_h * 0.105,
                str(values[key]),
                ha="center",
                va="center",
                color=INK,
                fontsize=19,
                fontproperties=helvetica("bold"),
                zorder=5,
            )
            ax.text(
                x,
                y - row_h * 0.105,
                label,
                ha="center",
                va="center",
                color=MUTED,
                fontsize=10,
                fontproperties=helvetica("bold"),
                zorder=5,
            )
            stat_cursor += width + stat_gutter

        height_cards.striped_box(
            ax,
            dunks_left,
            bottom,
            height_cards.X_ROW_R - dunks_left,
            box_h,
            BULLS_RED,
            BULLS_RED,
            fig_h,
            zorder=5,
        )
        ax.text(
            (dunks_left + height_cards.X_ROW_R) / 2,
            y,
            str(int(row["dunk_fgm"])),
            fontproperties=helvetica("bold"),
            fontsize=25,
            color="white",
            ha="center",
            va="center",
            zorder=7,
            path_effects=[
                height_cards.path_effects.withStroke(linewidth=3.5, foreground="#242424")
            ],
        )

    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / f"dunks-since-2010-{dunk_type.slug}-{suffix}.png"
    fig.savefig(path, dpi=FINAL_DPI if final else 300, transparent=True)
    plt.close(fig)
    return path


def canva_copy_block(boards: dict[str, pd.DataFrame]) -> str:
    lines = [
        "CANVA COPY",
        "COVER TITLE: THE BULLS' BEST DUNK SEASONS",
        "COVER SUBTITLE: Since 2010–11, by type",
        "",
    ]
    for slide in SLIDES:
        board = boards[slide.slug]
        cutoff = int(board.iloc[-1]["dunk_fgm"])
        lines.extend(
            [
                f"SLIDE: {slide.slug}",
                f"TITLE: {slide.title}",
                f"SUBTITLE: {slide.subtitle}",
                (
                    "FOOTER: Data via nba.com | 2010–11 to 2025–26 regular seasons | "
                    "Chicago-only stints | Shot-chart ACTION_TYPE"
                ),
                (
                    "NOTE: Made dunks. A play with two labels (running alley-oop, "
                    "driving reverse) counts on each matching slide. Ordered by made "
                    "dunks; per-game and FG% break display ties only."
                ),
                f"AUDIT: top-ten cutoff {cutoff} made {slide.slug} dunks.",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    parser.add_argument(
        "--slide",
        choices=[slide.slug for slide in SLIDES],
        default=None,
        help="render one slide instead of all five",
    )
    args = parser.parse_args()

    dunks, players = load_dunks()
    boards = build_all_boards(dunks, players)
    save_working_tables(dunks, boards)

    slides = [slide for slide in SLIDES if args.slide in (None, slide.slug)]
    for slide in slides:
        path = render_board(boards[slide.slug], slide, final=args.final)
        print(f"wrote {path}  ({len(boards[slide.slug])} rows)")

    print()
    print(canva_copy_block(boards))


if __name__ == "__main__":
    main()
