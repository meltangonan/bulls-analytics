"""Build the Bulls' highest-assist season at every age since 2000 for Canva.

This is the assist counterpart to ``scoring_age_ladder.py``. It keeps the
approved table layout unchanged while ranking qualifying Chicago player-seasons
by assists per game instead of points per game.
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

import pandas as pd
import requests
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import HEADSHOT_CACHE, ensure_headshots
from scripts.prototypes.scoring_age_ladder import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    METRIC_FILL_ROUNDED_BAND,
    METRIC_FILL_SQUARE_CELLS,
    MIN_TEAM_GAMES_SHARE,
    ONE_SLIDE_LAYOUT,
    PPG_SCALE_RED,
    PPG_SCALE_RED_YELLOW_GREEN,
    SNAPSHOT_TZ,
    TableLayout,
    display_season_label,
    ensure_historical_headshot_fallbacks,
    render_chart,
    season_label,
)


RAW_CACHE = _REPO / "cache" / "nba.com" / "assist-age-ladder"
OUT = _REPO / "output" / "feed"
NBA_PLAYER_ASSIST_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_TEAM_ASSIST_URL = (
    "https://www.nba.com/stats/teams/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_REQUEST_ATTEMPTS = 3
LIVE_REQUEST_DELAY_SECONDS = 1.0
BLANK_HEADSHOT_PLAYER_IDS = {1724, 1563}  # Bryce Drew and Kevin Ollie
NBA_BLANK_HEADSHOT_URL = (
    "https://cdn.nba.com/headshots/nba/latest/1040x760/1724.png"
)


def ensure_blank_headshot() -> Path:
    """Cache NBA's neutral silhouette for retired-player placeholder rows."""
    path = HEADSHOT_CACHE / "blank-headshot.png"
    if path.exists():
        return path
    response = requests.get(NBA_BLANK_HEADSHOT_URL, timeout=30)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return path

SEASON_LEADERS_LAYOUT = TableLayout(
    header_y=1043,
    header_rule_y=1018,
    first_row_y=998.5,
    row_height=39,
    headshot_half_size=24,
    headshot_rise=3,
    header_font_size=15,
    name_font_size=15.5,
    age_font_size=15,
    ppg_font_size=15,
    season_font_size=8.5,
    season_rise=7,
)


def player_source_url(end_year: int) -> str:
    """Return the NBA.com player-totals source for one season."""
    return NBA_PLAYER_ASSIST_URL.format(season=season_label(end_year))


def team_source_url(end_year: int) -> str:
    """Return the NBA.com team-totals source for one season."""
    return NBA_TEAM_ASSIST_URL.format(season=season_label(end_year))


def _required_columns(frame: pd.DataFrame, columns: set[str], source: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com {source} response is missing {sorted(missing)}.")


def _request_frame(factory: Callable[[], object], source: str) -> pd.DataFrame:
    """Make a paced NBA.com request with small retries for transient failures."""
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
    _required_columns(players, {"PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "AST"}, "player totals")
    _required_columns(teams, {"TEAM_ID", "GP", "AST"}, "team totals")

    bulls = teams.loc[teams["TEAM_ID"] == BULLS_TEAM_ID]
    if len(bulls) != 1:
        raise ValueError(f"NBA.com did not return exactly one Bulls row for {season}.")
    if players["PLAYER_ID"].duplicated().any():
        raise ValueError(f"NBA.com returned duplicate Bulls players for {season}.")
    team = bulls.iloc[0]
    team_games = int(team["GP"])
    team_assists = int(team["AST"])
    player_assists = int(pd.to_numeric(players["AST"], errors="raise").sum())
    if player_assists != team_assists:
        raise ValueError(
            f"NBA.com Bulls player assists ({player_assists}) do not reconcile to "
            f"team assists ({team_assists}) for {season}."
        )

    frame = players[["PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "AST"]].rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player",
            "AGE": "age",
            "GP": "games",
            "AST": "assists",
        }
    )
    frame["season_end_year"] = end_year
    frame["season"] = display_season_label(end_year)
    frame["team_games"] = team_games
    frame["team_assists"] = team_assists
    frame["assists_per_game"] = frame["assists"] / frame["games"]
    frame["player_source_url"] = player_source_url(end_year)
    frame["team_source_url"] = team_source_url(end_year)
    frame = frame[
        [
            "season_end_year",
            "season",
            "player_id",
            "player",
            "age",
            "games",
            "assists",
            "assists_per_game",
            "team_games",
            "team_assists",
            "player_source_url",
            "team_source_url",
        ]
    ]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def fetch_bulls_history(*, refresh: bool = False) -> pd.DataFrame:
    """Load every Bulls regular season from 2000-01 through 2025-26."""
    frames: list[pd.DataFrame] = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading {display_season_label(end_year)}")
        frames.append(fetch_bulls_season(end_year, refresh=refresh))
    return pd.concat(frames, ignore_index=True)


def build_working_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Apply the minimum-games rule and select one APG winner at each age."""
    required = {
        "season_end_year",
        "season",
        "player_id",
        "player",
        "age",
        "games",
        "assists",
        "assists_per_game",
        "team_games",
        "team_assists",
        "player_source_url",
        "team_source_url",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Historical assist rows are missing {sorted(missing)}.")

    table = rows.copy()
    for column in (
        "season_end_year",
        "player_id",
        "age",
        "games",
        "assists",
        "team_games",
        "team_assists",
    ):
        table[column] = pd.to_numeric(table[column], errors="raise").astype(int)
    table["assists_per_game"] = pd.to_numeric(
        table["assists_per_game"], errors="raise"
    ).astype(float)
    table["minimum_games"] = (
        table["team_games"] * MIN_TEAM_GAMES_SHARE
    ).apply(math.ceil).astype(int)
    table["qualified"] = table["games"] >= table["minimum_games"]
    table["selected"] = False

    winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "assists_per_game", "assists", "games", "player"],
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
    """Return the selected Bulls season in ascending age order."""
    return table.loc[table["selected"]].sort_values("age", kind="stable").reset_index(drop=True)


def season_winners(table: pd.DataFrame) -> pd.DataFrame:
    """Return one qualifying APG leader per season, sorted from high to low."""
    return (
        table.loc[table["qualified"]]
        .sort_values(
            ["season_end_year", "assists_per_game", "assists", "games", "player"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        .drop_duplicates("season_end_year", keep="first")
        .sort_values(
            ["assists_per_game", "assists", "games", "season_end_year"],
            ascending=[False, False, False, True],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def season_winners_by_year(table: pd.DataFrame) -> pd.DataFrame:
    """Return the same season leaders from newest season to oldest."""
    return season_winners(table).sort_values(
        "season_end_year", ascending=False, kind="stable"
    ).reset_index(drop=True)


def validate_working_table(table: pd.DataFrame) -> dict[str, object]:
    """Validate coverage, team reconciliation, qualification, and winners."""
    expected_years = set(range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1))
    present_years = set(table["season_end_year"].astype(int))
    if present_years != expected_years:
        raise ValueError("Historical source coverage does not include every season since 2000.")
    if table.duplicated(["season_end_year", "player_id"]).any():
        raise ValueError("A Bulls player appears more than once in a season.")
    if (table["games"] > table["team_games"]).any():
        raise ValueError("A player has more Bulls games than the team played.")
    if not table["qualified"].eq(table["games"] >= table["minimum_games"]).all():
        raise ValueError("Minimum-games qualification is inconsistent.")

    season_assists = table.groupby("season_end_year", sort=False)["assists"].sum()
    team_assists = table.groupby("season_end_year", sort=False)["team_assists"].first()
    if not season_assists.eq(team_assists).all():
        raise ValueError("Player assists do not reconcile to Bulls team assists.")

    winners = age_winners(table)
    if winners.empty:
        raise ValueError("No Bulls player-seasons qualified for the assist age ladder.")
    if winners["age"].duplicated().any():
        raise ValueError("The assist age ladder has more than one winner for an age.")
    expected_winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "assists_per_game", "assists", "games", "player"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        .drop_duplicates("age", keep="first")
    )
    actual_keys = set(zip(winners["season_end_year"], winners["player_id"]))
    expected_keys = set(zip(expected_winners["season_end_year"], expected_winners["player_id"]))
    if actual_keys != expected_keys:
        raise ValueError("The selected assist ladder does not use the correct winners.")
    return {
        "season_count": len(present_years),
        "player_season_count": len(table),
        "qualified_count": int(table["qualified"].sum()),
        "age_count": len(winners),
        "youngest_age": int(winners["age"].min()),
        "oldest_age": int(winners["age"].max()),
        "winner_names": winners["player"].tolist(),
    }


def validate_season_winners(table: pd.DataFrame) -> dict[str, object]:
    """Validate that every season contributes its correct qualified APG leader."""
    winners = season_winners(table)
    expected_years = set(range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1))
    if set(winners["season_end_year"].astype(int)) != expected_years:
        raise ValueError("Assist season leaders do not include every season since 2000.")
    if winners["season_end_year"].duplicated().any():
        raise ValueError("Assist season leaders include more than one player for a season.")

    expected = (
        table.loc[table["qualified"]]
        .sort_values(
            ["season_end_year", "assists_per_game", "assists", "games", "player"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        .drop_duplicates("season_end_year", keep="first")
    )
    actual_keys = set(zip(winners["season_end_year"], winners["player_id"]))
    expected_keys = set(zip(expected["season_end_year"], expected["player_id"]))
    if actual_keys != expected_keys:
        raise ValueError("The selected assist season leaders are not the correct winners.")
    if not winners["assists_per_game"].is_monotonic_decreasing:
        raise ValueError("Assist season leaders are not sorted by APG descending.")
    return {
        "season_count": len(winners),
        "highest_apg": float(winners["assists_per_game"].max()),
        "lowest_apg": float(winners["assists_per_game"].min()),
        "winner_names": winners["player"].tolist(),
    }


def write_working_table(table: pd.DataFrame, date: str) -> Path:
    """Write all player-seasons so exclusions and runners-up remain auditable."""
    path = OUT / f"{date}-bulls-assist-age-ladder-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def canva_copy_block(report: dict[str, object]) -> str:
    """Return the exact data-bound framing to paste into the cloned Canva page."""
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: Bulls assist leaders by age",
            "SUBTITLE: Highest assists per game at every age since 2000",
            "FOOTER: Data via nba.com | 2000\u201301 to 2025\u201326 | Min. 50% team games played | "
            "NBA-listed age",
            "NOTE: Chicago-only regular-season player stints. One qualifying player-season per age.",
            f"AUDIT: {report['age_count']} ages, {report['youngest_age']}\u2013{report['oldest_age']}; "
            f"{report['qualified_count']} qualifying player-seasons across {report['season_count']} Bulls seasons.",
        ]
    )


def season_canva_copy_block(report: dict[str, object]) -> str:
    """Return the data-bound framing for the season-leader comparison page."""
    return "\n".join(
        [
            "CANVA COPY — SEASON LEADERS",
            "TITLE: Bulls assist leaders by season",
            "SUBTITLE: Highest assists per game by a Bull each season since 2000",
            "FOOTER: Data via nba.com | 2000\u201301 to 2025\u201326 | Min. 50% team games played",
            "NOTE: Chicago-only regular-season player stints. One qualifying leader per season.",
            f"AUDIT: {report['season_count']} seasons; displayed APG range "
            f"{report['lowest_apg']:.1f}\u2013{report['highest_apg']:.1f}.",
        ]
    )


def season_chronological_canva_copy_block(report: dict[str, object]) -> str:
    """Return the framing for the reverse-chronological comparison page."""
    return "\n".join(
        [
            "CANVA COPY — SEASON LEADERS, NEWEST TO OLDEST",
            "TITLE: Bulls assist leaders by season",
            "SUBTITLE: Each season's assists-per-game leader, newest to oldest",
            "FOOTER: Data via nba.com | 2000\u201301 to 2025\u201326 | Min. 50% team games played",
            "NOTE: Chicago-only regular-season player stints. One qualifying leader per season.",
            f"AUDIT: {report['season_count']} seasons; displayed APG range "
            f"{report['lowest_apg']:.1f}\u2013{report['highest_apg']:.1f}.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls assist age ladder chart asset.")
    parser.add_argument("--refresh", action="store_true", help="Refetch all NBA.com season responses.")
    parser.add_argument("--final", action="store_true", help="Export at final resolution after approval.")
    args = parser.parse_args()

    snapshot = datetime.now(SNAPSHOT_TZ)
    table = build_working_table(fetch_bulls_history(refresh=args.refresh))
    report = validate_working_table(table)
    season_report = validate_season_winners(table)
    date = snapshot.date().isoformat()
    audit_path = write_working_table(table, date)
    age_players = age_winners(table)
    season_players = season_winners(table)
    chronological_players = season_winners_by_year(table)
    player_ids = sorted(set(age_players["player_id"]) | set(season_players["player_id"]))
    ensure_headshots(player_ids)
    ensure_historical_headshot_fallbacks(player_ids)
    ensure_blank_headshot()
    age_chart_path = render_chart(
        age_players,
        date,
        slug="one-slide",
        layout=ONE_SLIDE_LAYOUT,
        scale_min=float(age_players["assists_per_game"].min()),
        scale_max=float(age_players["assists_per_game"].max()),
        color_scale=PPG_SCALE_RED_YELLOW_GREEN,
        metric_column="assists_per_game",
        metric_header="APG",
        output_stem="bulls-assist-age-ladder",
        final=args.final,
    )
    season_chart_path = render_chart(
        season_players,
        date,
        slug="one-slide",
        layout=SEASON_LEADERS_LAYOUT,
        scale_min=float(season_players["assists_per_game"].min()),
        scale_max=float(season_players["assists_per_game"].max()),
        color_scale=PPG_SCALE_RED,
        metric_column="assists_per_game",
        metric_header="APG",
        output_stem="bulls-assist-season-leaders",
        show_age=False,
        headshot_x=120,
        name_x=175,
        row_rule_left=80,
        sort_by=["assists_per_game", "assists", "games", "season_end_year"],
        sort_ascending=[False, False, False, True],
        metric_fill_style=METRIC_FILL_ROUNDED_BAND,
        blank_headshot_ids=BLANK_HEADSHOT_PLAYER_IDS,
        final=args.final,
    )
    chronological_chart_path = render_chart(
        chronological_players,
        date,
        slug="one-slide",
        layout=SEASON_LEADERS_LAYOUT,
        scale_min=float(season_players["assists_per_game"].min()),
        scale_max=float(season_players["assists_per_game"].max()),
        color_scale=PPG_SCALE_RED,
        metric_column="assists_per_game",
        metric_header="APG",
        output_stem="bulls-assist-season-leaders-chronological",
        show_age=False,
        headshot_x=120,
        name_x=175,
        row_rule_left=80,
        sort_by=["season_end_year"],
        sort_ascending=[False],
        metric_fill_style=METRIC_FILL_SQUARE_CELLS,
        blank_headshot_ids=BLANK_HEADSHOT_PLAYER_IDS,
        final=args.final,
    )
    print(f"Audit: {audit_path}")
    print(f"Age chart: {age_chart_path}")
    print(f"Season chart: {season_chart_path}")
    print(f"Chronological season chart: {chronological_chart_path}")
    print(canva_copy_block(report))
    print(season_canva_copy_block(season_report))
    print(season_chronological_canva_copy_block(season_report))


if __name__ == "__main__":
    main()
