"""Build the Bulls' highest-rebounding season at every age since 2000.

This is the rebounding counterpart to ``stocks_age_ladder.py``.  The primary
asset deliberately reuses the Stocks table grammar: RPG is the heat cell and
the supporting columns are DREB, ORB, and GP.  A second renderer reuses the
compact table geometry from the height Game Score post and splits the same
twenty-row ladder across two ten-row pages.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.patches import Rectangle
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house
from bulls.graphics.house import ensure_headshots
from scripts.prototypes.assist_duos import display_name
from scripts.prototypes.scoring_age_ladder import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    MIN_TEAM_GAMES_SHARE,
    PPG_SCALE_RED_YELLOW_GREEN,
    SNAPSHOT_TZ,
    TableLayout,
    TrailingColumn,
    display_season_label,
    ensure_historical_headshot_fallbacks,
    name_block_width,
    render_chart,
    season_label,
)


RAW_CACHE = _REPO / "cache" / "nba.com" / "rebounds-age-ladder"
LEAGUE_CACHE = _REPO / "cache" / "nba.com" / "league-rebounds-baseline"
PROJECT_DATA = _REPO / "docs" / "visuals" / "2026-08-27-rebounds-age-ladder" / "data"
OUT = _REPO / "output" / "feed"

NBA_PLAYER_REBOUNDS_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_TEAM_REBOUNDS_URL = (
    "https://www.nba.com/stats/teams/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_REQUEST_ATTEMPTS = 3
LIVE_REQUEST_DELAY_SECONDS = 1.0

# Keep the same table dimensions, portrait treatment, and ratio-to-season-
# median color logic as the published Stocks asset.
REBOUNDS_TRAILING_COLUMNS = (
    TrailingColumn("DREB", "defensive_rebounds_per_game", decimals=1),
    TrailingColumn("ORB", "offensive_rebounds_per_game", decimals=1),
    TrailingColumn("GP", "games", decimals=0),
)
REBOUNDS_CHART_WIDTH = 1280
REBOUNDS_CHART_HEIGHT = 1200
REBOUNDS_METRIC_WIDTH = 120
REBOUNDS_TRAILING_SLOT_WIDTH = 112
REBOUNDS_NAME_COLUMN_GAP = 26
REBOUNDS_FACE_CROP_FRACTION = 0.67
REBOUNDS_LAYOUT = TableLayout(
    header_y=1155,
    header_rule_y=1130,
    first_row_y=1098,
    row_height=56,
    headshot_half_size=37,
    headshot_rise=5,
    header_font_size=15.5,
    name_font_size=18,
    age_font_size=17,
    ppg_font_size=18,
    season_font_size=10,
    season_rise=10.5,
)

# The second version is the height-post table's visual footprint and row
# spacing, with the age occupying the left red block instead of a height.
HEIGHT_TABLE_WIDTH = 1500
HEIGHT_TABLE_ROW_H = 116
HEIGHT_TABLE_TOP = 104
HEIGHT_TABLE_BOTTOM = 42
HEIGHT_TABLE_RED = house.DEFAULT_THEME.accent
HEIGHT_TABLE_THEME = house.DEFAULT_THEME

COLUMNS = [
    "season_end_year",
    "season",
    "player_id",
    "player",
    "age",
    "games",
    "offensive_rebounds",
    "defensive_rebounds",
    "rebounds",
    "offensive_rebounds_per_game",
    "defensive_rebounds_per_game",
    "rebounds_per_game",
    "team_games",
    "team_offensive_rebounds",
    "team_defensive_rebounds",
    "team_rebounds",
    "player_source_url",
    "team_source_url",
]


def player_source_url(end_year: int) -> str:
    return NBA_PLAYER_REBOUNDS_URL.format(season=season_label(end_year))


def team_source_url(end_year: int) -> str:
    return NBA_TEAM_REBOUNDS_URL.format(season=season_label(end_year))


def _required_columns(frame: pd.DataFrame, columns: set[str], source: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com {source} response is missing {sorted(missing)}.")


def _request_frame(factory: Callable[[], object], source: str) -> pd.DataFrame:
    for attempt in range(1, NBA_REQUEST_ATTEMPTS + 1):
        try:
            endpoint = factory()
            frame = endpoint.get_data_frames()[0]
            time.sleep(LIVE_REQUEST_DELAY_SECONDS)
            return frame
        except requests.RequestException:
            if attempt == NBA_REQUEST_ATTEMPTS:
                raise
            wait_seconds = 2**attempt
            print(f"NBA.com {source} request failed; retrying in {wait_seconds}s")
            time.sleep(wait_seconds)
    raise AssertionError("NBA.com retry loop ended unexpectedly.")


def fetch_bulls_season(end_year: int, *, refresh: bool = False) -> pd.DataFrame:
    """Load one Chicago-only regular season from cache or NBA.com."""
    cache_path = RAW_CACHE / f"CHI-{end_year}.csv"
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path)

    season = season_label(end_year)
    players = _request_frame(
        lambda: leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            team_id_nullable=BULLS_TEAM_ID,
            timeout=60,
            headers=_NBA_HEADERS,
        ),
        f"player totals for {season}",
    )
    teams = _request_frame(
        lambda: leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            team_id_nullable=BULLS_TEAM_ID,
            timeout=60,
            headers=_NBA_HEADERS,
        ),
        f"team totals for {season}",
    )
    _required_columns(
        players,
        {"PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "OREB", "DREB", "REB"},
        "player totals",
    )
    _required_columns(teams, {"TEAM_ID", "GP", "OREB", "DREB", "REB"}, "team totals")

    bulls = teams.loc[teams["TEAM_ID"] == BULLS_TEAM_ID]
    if len(bulls) != 1:
        raise ValueError(f"NBA.com did not return exactly one Bulls row for {season}.")
    if players["PLAYER_ID"].duplicated().any():
        raise ValueError(f"NBA.com returned duplicate Bulls players for {season}.")

    team = bulls.iloc[0]
    team_games = int(team["GP"])
    team_offensive_rebounds = int(team["OREB"])
    team_defensive_rebounds = int(team["DREB"])
    team_rebounds = int(team["REB"])
    numeric = players[["OREB", "DREB", "REB"]].apply(pd.to_numeric, errors="raise")
    if not numeric["REB"].eq(numeric["OREB"] + numeric["DREB"]).all():
        raise ValueError(f"NBA.com player rebounds do not equal OREB plus DREB for {season}.")
    for column, team_total, label in (
        ("OREB", team_offensive_rebounds, "offensive rebounds"),
        ("DREB", team_defensive_rebounds, "defensive rebounds"),
        ("REB", team_rebounds, "rebounds"),
    ):
        player_total = int(numeric[column].sum())
        if player_total != team_total:
            raise ValueError(
                f"NBA.com Bulls player {label} ({player_total}) do not reconcile to "
                f"team {label} ({team_total}) for {season}."
            )

    frame = players[["PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "OREB", "DREB", "REB"]].rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player",
            "AGE": "age",
            "GP": "games",
            "OREB": "offensive_rebounds",
            "DREB": "defensive_rebounds",
            "REB": "rebounds",
        }
    )
    frame["season_end_year"] = end_year
    frame["season"] = display_season_label(end_year)
    frame["team_games"] = team_games
    frame["team_offensive_rebounds"] = team_offensive_rebounds
    frame["team_defensive_rebounds"] = team_defensive_rebounds
    frame["team_rebounds"] = team_rebounds
    frame["offensive_rebounds_per_game"] = frame["offensive_rebounds"] / frame["games"]
    frame["defensive_rebounds_per_game"] = frame["defensive_rebounds"] / frame["games"]
    frame["rebounds_per_game"] = frame["rebounds"] / frame["games"]
    frame["player_source_url"] = player_source_url(end_year)
    frame["team_source_url"] = team_source_url(end_year)
    frame = frame[COLUMNS]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def fetch_league_season(end_year: int, *, refresh: bool = False) -> pd.DataFrame:
    """Load every NBA player's totals for the season's shading baseline."""
    cache_path = LEAGUE_CACHE / f"league-{end_year}.csv"
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path)

    season = season_label(end_year)
    players = _request_frame(
        lambda: leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            timeout=60,
            headers=_NBA_HEADERS,
        ),
        f"league totals for {season}",
    )
    _required_columns(players, {"PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "REB"}, "league totals")
    frame = players[["PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "REB"]]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def league_rotation_rates(rows: pd.DataFrame) -> pd.Series:
    """RPG for rotation regulars, using the observed season length."""
    frame = rows.copy()
    for column in ("GP", "MIN", "REB"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame = frame.loc[frame["GP"] > 0]
    minimum_games = math.ceil(frame["GP"].max() * MIN_TEAM_GAMES_SHARE)
    regulars = frame.loc[
        (frame["GP"] >= minimum_games) & (frame["MIN"] / frame["GP"] >= 20.0)
    ]
    if regulars.empty:
        raise ValueError("No league rotation regulars qualified for the baseline.")
    return (regulars["REB"] / regulars["GP"]).reset_index(drop=True)


def fetch_bulls_history(*, refresh: bool = False) -> pd.DataFrame:
    frames = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading {display_season_label(end_year)}")
        frames.append(fetch_bulls_season(end_year, refresh=refresh))
    return pd.concat(frames, ignore_index=True)


def fetch_league_baseline(*, refresh: bool = False) -> dict[int, pd.Series]:
    baseline: dict[int, pd.Series] = {}
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading league baseline {display_season_label(end_year)}")
        baseline[end_year] = league_rotation_rates(
            fetch_league_season(end_year, refresh=refresh)
        )
    return baseline


def build_working_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Apply the half-team-games floor and choose one RPG winner per age."""
    missing = set(COLUMNS) - set(rows.columns)
    if missing:
        raise ValueError(f"Historical rebound rows are missing {sorted(missing)}.")
    table = rows.copy()
    for column in (
        "season_end_year", "player_id", "age", "games", "offensive_rebounds",
        "defensive_rebounds", "rebounds", "team_games", "team_offensive_rebounds",
        "team_defensive_rebounds", "team_rebounds",
    ):
        table[column] = pd.to_numeric(table[column], errors="raise").astype(int)
    for column in (
        "offensive_rebounds_per_game", "defensive_rebounds_per_game", "rebounds_per_game",
    ):
        table[column] = pd.to_numeric(table[column], errors="raise").astype(float)
    table["minimum_games"] = (table["team_games"] * MIN_TEAM_GAMES_SHARE).apply(math.ceil).astype(int)
    table["qualified"] = table["games"] >= table["minimum_games"]
    winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "rebounds_per_game", "rebounds", "games", "player"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        .drop_duplicates("age", keep="first")
    )
    winner_keys = pd.MultiIndex.from_frame(winners[["season_end_year", "player_id"]])
    table_keys = pd.MultiIndex.from_frame(table[["season_end_year", "player_id"]])
    table["selected"] = table_keys.isin(winner_keys)
    return table.sort_values(
        ["age", "season_end_year", "player", "player_id"], kind="stable"
    ).reset_index(drop=True)


def age_winners(table: pd.DataFrame) -> pd.DataFrame:
    return table.loc[table["selected"]].sort_values("age", kind="stable").reset_index(drop=True)


def attach_league_baseline(table: pd.DataFrame, baseline: dict[int, pd.Series]) -> pd.DataFrame:
    missing = sorted(set(table["season_end_year"].astype(int)) - set(baseline))
    if missing:
        raise ValueError(f"No league baseline for seasons {missing}.")
    rated = table.copy()
    medians, percentiles, samples = [], [], []
    for _, row in rated.iterrows():
        rates = baseline[int(row["season_end_year"])]
        value = float(row["rebounds_per_game"])
        medians.append(float(rates.median()))
        percentiles.append(float((rates < value).mean() * 100.0))
        samples.append(int(len(rates)))
    rated["league_median"] = medians
    rated["league_ratio"] = rated["rebounds_per_game"] / rated["league_median"]
    rated["league_percentile"] = percentiles
    rated["league_sample"] = samples
    return rated


def validate_working_table(
    table: pd.DataFrame,
    *,
    first_season_end_year: int = FIRST_SEASON_END_YEAR,
    reconcile_team_totals: bool = True,
) -> dict[str, object]:
    expected_years = set(range(first_season_end_year, LAST_SEASON_END_YEAR + 1))
    if set(table["season_end_year"].astype(int)) != expected_years:
        raise ValueError("Historical source coverage does not include every requested season.")
    if table.duplicated(["season_end_year", "player_id"]).any():
        raise ValueError("A Bulls player appears more than once in a season.")
    if (table["games"] > table["team_games"]).any():
        raise ValueError("A player has more Bulls games than the team played.")
    if not table["qualified"].eq(table["games"] >= table["minimum_games"]).all():
        raise ValueError("Minimum-games qualification is inconsistent.")
    if not table["rebounds"].eq(table["offensive_rebounds"] + table["defensive_rebounds"]).all():
        raise ValueError("Rebounds do not equal offensive plus defensive rebounds.")
    if reconcile_team_totals:
        for component, team_column, label in (
            ("offensive_rebounds", "team_offensive_rebounds", "offensive rebounds"),
            ("defensive_rebounds", "team_defensive_rebounds", "defensive rebounds"),
            ("rebounds", "team_rebounds", "rebounds"),
        ):
            season_total = table.groupby("season_end_year", sort=False)[component].sum()
            team_total = table.groupby("season_end_year", sort=False)[team_column].first()
            if not season_total.eq(team_total).all():
                raise ValueError(f"Player {label} do not reconcile to Bulls team {label}.")
    if "league_ratio" in table.columns:
        if not pd.to_numeric(table["league_median"], errors="raise").gt(0).all():
            raise ValueError("A league rebound median is not positive.")
        if not pd.to_numeric(table["league_sample"], errors="raise").ge(50).all():
            raise ValueError("A league baseline season has too small a comparison pool.")
    winners = age_winners(table)
    expected = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "rebounds_per_game", "rebounds", "games", "player"],
            ascending=[True, False, False, False, True], kind="stable",
        )
        .drop_duplicates("age", keep="first")
    )
    if winners.empty or winners["age"].duplicated().any():
        raise ValueError("The rebound age ladder does not have one winner per age.")
    if set(zip(winners["season_end_year"], winners["player_id"])) != set(
        zip(expected["season_end_year"], expected["player_id"])
    ):
        raise ValueError("The selected rebound ladder does not use the correct winners.")
    return {
        "season_count": len(expected_years),
        "player_season_count": len(table),
        "qualified_count": int(table["qualified"].sum()),
        "age_count": len(winners),
        "youngest_age": int(winners["age"].min()),
        "oldest_age": int(winners["age"].max()),
        "highest_rpg": float(winners["rebounds_per_game"].max()),
        "lowest_rpg": float(winners["rebounds_per_game"].min()),
        "highest_ratio": float(winners["league_ratio"].max()) if "league_ratio" in winners else None,
        "lowest_ratio": float(winners["league_ratio"].min()) if "league_ratio" in winners else None,
        "winner_names": winners["player"].tolist(),
    }


def apply_display_names(winners: pd.DataFrame) -> pd.DataFrame:
    labeled = winners.copy()
    labeled["player"] = [
        display_name(str(row.player), int(row.player_id), int(row.season_end_year))
        for row in labeled.itertuples()
    ]
    return labeled


def write_data(table: pd.DataFrame, winners: pd.DataFrame) -> tuple[Path, Path]:
    PROJECT_DATA.mkdir(parents=True, exist_ok=True)
    table_path = PROJECT_DATA / "bulls-rebounds-age-ladder-working.csv"
    winners_path = PROJECT_DATA / "bulls-rebounds-age-ladder-winners.csv"
    table.to_csv(table_path, index=False)
    winners.to_csv(winners_path, index=False)
    return table_path, winners_path


def canva_copy_block(report: dict[str, object]) -> str:
    return "\n".join([
        "CANVA COPY",
        "TITLE: THE BULLS' REBOUND AGE LADDER",
        "SUBTITLE: Highest rebounds per game by a Bull at every age since 2000",
        "FOOTER: Data via nba.com | 2000–01 to 2025–26 regular seasons | "
        "Min. 50% of team games | Age as listed by NBA.com",
        "NOTE: RPG is total rebounds per game; DREB and ORB are shown as context.",
        "NOTE: Chicago-only player stints. One qualifying player-season per age.",
        "NOTE: Shading compares each season to the NBA median RPG for rotation regulars "
        "that year (half their team's games, 20+ minutes per game).",
        f"AUDIT: {report['age_count']} ages, {report['youngest_age']}–{report['oldest_age']}; "
        f"{report['qualified_count']} qualifying player-seasons across {report['season_count']} Bulls seasons; "
        f"displayed range {report['lowest_rpg']:.1f}–{report['highest_rpg']:.1f} RPG; "
        f"{report['lowest_ratio']:.2f}x–{report['highest_ratio']:.2f}x league average.",
    ])


def render_rebounds_table(winners: pd.DataFrame, date: str, *, final: bool = False) -> Path:
    """Render the exact Stocks-style one-slide table with rebound columns."""
    return render_chart(
        apply_display_names(winners), date,
        slug="one-slide", layout=REBOUNDS_LAYOUT,
        scale_min=0.85, scale_max=2.50,
        color_scale=PPG_SCALE_RED_YELLOW_GREEN,
        metric_column="rebounds_per_game", fill_column="league_ratio",
        fill_midpoint=1.00, metric_header="RPG", metric_decimals=1,
        output_stem="bulls-rebounds-age-ladder",
        trailing_columns=REBOUNDS_TRAILING_COLUMNS,
        chart_width=REBOUNDS_CHART_WIDTH, chart_height=REBOUNDS_CHART_HEIGHT,
        auto_name_column=True, name_column_gap=REBOUNDS_NAME_COLUMN_GAP,
        metric_width=REBOUNDS_METRIC_WIDTH,
        trailing_slot_width=REBOUNDS_TRAILING_SLOT_WIDTH,
        face_crop_fraction=REBOUNDS_FACE_CROP_FRACTION,
        clip_portraits_to_row=True, final=final,
    )


def _height_table_portrait(ax, row, x: float, y: float, size: float) -> None:
    path = house.HEADSHOT_CACHE / f"{int(row.player_id)}.png"
    try:
        image = plt.imread(path)
    except (FileNotFoundError, OSError, ValueError):
        return
    h, w = image.shape[:2]
    side = min(int(h * REBOUNDS_FACE_CROP_FRACTION), w)
    left = max(0, (w - side) // 2)
    ax.imshow(image[:side, left:left + side], extent=[x - size, x + size, y - size, y + size], zorder=5)


def render_height_table(rows: pd.DataFrame, page: int, date: str, *, final: bool = False) -> Path:
    """Render ten rows using the compact Game Score height-table geometry."""
    rows = apply_display_names(rows).reset_index(drop=True)
    height = HEIGHT_TABLE_TOP + len(rows) * HEIGHT_TABLE_ROW_H + HEIGHT_TABLE_BOTTOM
    fig, ax = plt.subplots(figsize=(HEIGHT_TABLE_WIDTH / 150, height / 150), dpi=150)
    fig.patch.set_alpha(0)
    ax.set_xlim(0, HEIGHT_TABLE_WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    headers = [
        (52, "AGE", "left"), (220, "PLAYER / SEASON", "left"),
        (758, "RPG", "center"), (875, "DREB", "center"),
        (990, "ORB", "center"), (1110, "GP", "center"),
    ]
    for x, label, align in headers:
        color = HEIGHT_TABLE_RED if label == "RPG" else HEIGHT_TABLE_THEME.ink
        ax.text(x, height - 54, label, ha=align, va="center", color=color,
                fontsize=11.5, fontproperties=house.helvetica("bold"))
    ax.plot([40, 1165], [height - 82, height - 82], color=HEIGHT_TABLE_THEME.ink, lw=2)
    for i, (_, row) in enumerate(rows.iterrows()):
        y = height - HEIGHT_TABLE_TOP - i * HEIGHT_TABLE_ROW_H - HEIGHT_TABLE_ROW_H / 2
        if i:
            ax.plot([40, 1165], [y + HEIGHT_TABLE_ROW_H / 2, y + HEIGHT_TABLE_ROW_H / 2],
                    color=HEIGHT_TABLE_THEME.rule, lw=1)
        ax.add_patch(Rectangle((42, y - 34), 112, 68, facecolor=HEIGHT_TABLE_RED, edgecolor="none"))
        ax.text(98, y, int(row.age), ha="center", va="center", color="white", fontsize=18,
                fontproperties=house.helvetica("bold"))
        _height_table_portrait(ax, row, 190, y + 3, 51)
        ax.text(252, y + 13, row.player, ha="left", va="center", color=HEIGHT_TABLE_THEME.ink,
                fontsize=19, fontproperties=house.helvetica("bold"))
        ax.text(252, y - 20, f"{row.season} · Chicago", ha="left", va="center",
                color=HEIGHT_TABLE_THEME.muted, fontsize=10.5, fontproperties=house.helvetica())
        ax.add_patch(Rectangle((708, y - 43), 100, 86, facecolor=HEIGHT_TABLE_RED, edgecolor="none"))
        values = [
            (758, f"{row.rebounds_per_game:.1f}", "white", "bold"),
            (875, f"{row.defensive_rebounds_per_game:.1f}", HEIGHT_TABLE_THEME.ink, "regular"),
            (990, f"{row.offensive_rebounds_per_game:.1f}", HEIGHT_TABLE_THEME.ink, "regular"),
            (1110, int(row.games), HEIGHT_TABLE_THEME.ink, "regular"),
        ]
        for x, value, color, weight in values:
            ax.text(x, y, str(value), ha="center", va="center", color=color, fontsize=14.5,
                    fontproperties=house.helvetica(weight))
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / f"{date}-bulls-rebounds-age-ladder-height-table-p{page}-{suffix}.png"
    fig.savefig(path, dpi=300 if final else 150, transparent=True, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls rebound age ladder chart assets.")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    snapshot = datetime.now(SNAPSHOT_TZ)
    table = build_working_table(fetch_bulls_history(refresh=args.refresh))
    rated = attach_league_baseline(table, fetch_league_baseline(refresh=args.refresh))
    report = validate_working_table(rated)
    winners = age_winners(rated)
    write_data(rated, winners)
    player_ids = sorted(set(winners["player_id"].astype(int)))
    ensure_headshots(player_ids)
    ensure_historical_headshot_fallbacks(player_ids)
    date = snapshot.date().isoformat()
    print(f"Stocks-style: {render_rebounds_table(winners, date, final=args.final)}")
    for page, rows in enumerate((winners.iloc[:10], winners.iloc[10:]), 1):
        print(f"Height-table page {page}: {render_height_table(rows, page, date, final=args.final)}")
    print(canva_copy_block(report))


if __name__ == "__main__":
    main()
