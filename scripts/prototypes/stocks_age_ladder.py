"""Build the Bulls' highest-stocks season at every age since 2000 for Canva.

Fifth entry in the age-ladder family and the first defensive one, following
``scoring_age_ladder.py``, ``assist_age_ladder.py`` and their siblings.  It
keeps the approved table layout while ranking qualifying Chicago
player-seasons by "stocks" — steals plus blocks — per game.

Unlike the rebounding ladder, which shows a single total, this page prints the
steal and block components beside the combined figure.  A stock is two
different events produced by different positions: a guard's 1.9 steals and a
centre's 1.9 blocks read as the same number and mean nothing alike, so the
components stay visible rather than being folded away (`POSTING_WORKFLOW.md`
fairness guardrails).  The components replace the games-played column, which
the footer's qualification rule already covers.

Stocks count visible defensive events, not defensive value.  The Canva copy
block says so on the page; nothing here should be read as a defensive rating.
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
from bulls.graphics.house import ensure_headshots
from scripts.prototypes.assist_age_ladder import ensure_blank_headshot
from scripts.prototypes.assist_duos import display_name
from scripts.prototypes.scoring_age_ladder import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    MIN_TEAM_GAMES_SHARE,
    PPG_SCALE_RED_YELLOW_GREEN,
    TableLayout,
    SNAPSHOT_TZ,
    TrailingColumn,
    display_season_label,
    ensure_historical_headshot_fallbacks,
    render_chart,
    season_label,
)


RAW_CACHE = _REPO / "cache" / "nba.com" / "stocks-age-ladder"
LEAGUE_CACHE = _REPO / "cache" / "nba.com" / "league-stocks-baseline"
OUT = _REPO / "output" / "feed"
NBA_PLAYER_STOCKS_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_TEAM_STOCKS_URL = (
    "https://www.nba.com/stats/teams/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}"
)
NBA_REQUEST_ATTEMPTS = 3
LIVE_REQUEST_DELAY_SECONDS = 1.0

# The steal and block components sit where games played sits on the other
# ladders; the qualification rule stays in the footer instead.
STOCKS_TRAILING_COLUMNS = (
    TrailingColumn("STL", "steals_per_game", decimals=1),
    TrailingColumn("BLK", "blocks_per_game", decimals=1),
    # Games played is supplemental, not part of the claim: it tells the reader
    # how much season is behind a rate without letting availability pick the
    # winner. Kris Dunn's 52 games and Pau Gasol's 78 are different evidence.
    TrailingColumn("GP", "games"),
)
# The asset's height is not free real estate: Canva scales the whole chart to
# fit the space under the title, so a taller asset is a *smaller* one on the
# page. Height stays close to the other ladders and the portraits instead take
# a larger share of each row — that is what makes a face bigger in the feed.
STOCKS_CHART_WIDTH = 1280
STOCKS_CHART_HEIGHT = 1200
STOCKS_METRIC_WIDTH = 120
# All three trailing columns share one width — games played is presented as an
# equal citizen of the row, not a squeezed afterthought. Three columns at the
# original width no longer fit 1080px, so the asset itself widens; Canva scales
# it to the page either way.
STOCKS_TRAILING_SLOT_WIDTH = 112
# Clear air between the longest season marker and the STK fill.
STOCKS_NAME_COLUMN_GAP = 26

# The colour behind each row is that season's league percentile, not the row's
# place within this chart. Min-max shading against the chart's own range made
# Ben Wallace's 3.47 stretch the scale until Jimmy Butler's 89th-percentile
# season rendered dead centre — "average" — which it plainly was not.
#
# The comparison pool is rotation regulars: half their season's games at 20+
# minutes a night. Bench players at four minutes a game would drag the
# distribution down and flatter every row on this ladder.
LEAGUE_MIN_MINUTES_PER_GAME = 20.0
LEAGUE_MIN_GAMES_SHARE = 0.50
# Shading reads the ratio to that season's league median, not the percentile.
# Percentile is externally anchored but compresses the tail: 3rd of 220 and 13th
# of 220 differ by four points on a hundred-point scale, so every elite season
# came out the same green. The ratio keeps the anchor — 1.00x is exactly league
# average — while preserving how far clear of it a season actually was.
LEAGUE_RATIO_FLOOR = 0.85
LEAGUE_RATIO_AVERAGE = 1.00
LEAGUE_RATIO_CEILING = 2.50
# The older ladders keep 0.72 of the source portrait's height, which is a face
# plus a collar and a slab of shoulder. Two-thirds keeps the whole head and the
# chin with a little room under it; tighter than this starts cutting jaws.
STOCKS_FACE_CROP_FRACTION = 0.67

# Portrait diameter is 1.32x the row height, so it rises into the row above and
# is clipped at its own separator — the rookie-leaderboard treatment, and the
# only way to enlarge a face when the row count is fixed at twenty. The top row
# has no row above it, so its portrait crosses the header rule instead; the
# rule draws underneath (zorder 2 against the portrait's 4), which is what makes
# the row read as a card rather than a head cropped flat against a line.
STOCKS_LAYOUT = TableLayout(
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

COLUMNS = [
    "season_end_year",
    "season",
    "player_id",
    "player",
    "age",
    "games",
    "steals",
    "blocks",
    "stocks",
    "steals_per_game",
    "blocks_per_game",
    "stocks_per_game",
    "team_games",
    "team_steals",
    "team_blocks",
    "player_source_url",
    "team_source_url",
]


def player_source_url(end_year: int) -> str:
    """Return the NBA.com player-totals source for one season."""
    return NBA_PLAYER_STOCKS_URL.format(season=season_label(end_year))


def team_source_url(end_year: int) -> str:
    """Return the NBA.com team-totals source for one season."""
    return NBA_TEAM_STOCKS_URL.format(season=season_label(end_year))


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
    _required_columns(
        players,
        {"PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "STL", "BLK"},
        "player totals",
    )
    _required_columns(teams, {"TEAM_ID", "GP", "STL", "BLK"}, "team totals")

    bulls = teams.loc[teams["TEAM_ID"] == BULLS_TEAM_ID]
    if len(bulls) != 1:
        raise ValueError(f"NBA.com did not return exactly one Bulls row for {season}.")
    if players["PLAYER_ID"].duplicated().any():
        raise ValueError(f"NBA.com returned duplicate Bulls players for {season}.")
    team = bulls.iloc[0]
    team_games = int(team["GP"])
    team_steals = int(team["STL"])
    team_blocks = int(team["BLK"])

    # Both components reconcile separately: a combined check would let a steal
    # surplus hide a block shortfall.
    player_steals = int(pd.to_numeric(players["STL"], errors="raise").sum())
    if player_steals != team_steals:
        raise ValueError(
            f"NBA.com Bulls player steals ({player_steals}) do not reconcile to "
            f"team steals ({team_steals}) for {season}."
        )
    player_blocks = int(pd.to_numeric(players["BLK"], errors="raise").sum())
    if player_blocks != team_blocks:
        raise ValueError(
            f"NBA.com Bulls player blocks ({player_blocks}) do not reconcile to "
            f"team blocks ({team_blocks}) for {season}."
        )

    frame = players[["PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "STL", "BLK"]].rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player",
            "AGE": "age",
            "GP": "games",
            "STL": "steals",
            "BLK": "blocks",
        }
    )
    frame["season_end_year"] = end_year
    frame["season"] = display_season_label(end_year)
    frame["team_games"] = team_games
    frame["team_steals"] = team_steals
    frame["team_blocks"] = team_blocks
    frame["stocks"] = frame["steals"] + frame["blocks"]
    frame["steals_per_game"] = frame["steals"] / frame["games"]
    frame["blocks_per_game"] = frame["blocks"] / frame["games"]
    frame["stocks_per_game"] = frame["stocks"] / frame["games"]
    frame["player_source_url"] = player_source_url(end_year)
    frame["team_source_url"] = team_source_url(end_year)
    frame = frame[COLUMNS]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def fetch_league_season(end_year: int, *, refresh: bool = False) -> pd.DataFrame:
    """Load every NBA player's totals for one season, for the baseline pool."""
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
    _required_columns(
        players, {"PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "STL", "BLK"}, "league totals"
    )
    frame = players[["PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "STL", "BLK"]]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


def league_rotation_rates(rows: pd.DataFrame) -> pd.Series:
    """Stocks per game for one season's rotation regulars.

    Games played is qualified against the longest season any player actually
    logged rather than a fixed 41, so the lockout and pandemic seasons are not
    held to an 82-game bar they never had.
    """
    frame = rows.copy()
    for column in ("GP", "MIN", "STL", "BLK"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame = frame.loc[frame["GP"] > 0]
    minimum_games = math.ceil(frame["GP"].max() * LEAGUE_MIN_GAMES_SHARE)
    regulars = frame.loc[
        (frame["GP"] >= minimum_games)
        & (frame["MIN"] / frame["GP"] >= LEAGUE_MIN_MINUTES_PER_GAME)
    ]
    if regulars.empty:
        raise ValueError("No league rotation regulars qualified for the baseline.")
    return ((regulars["STL"] + regulars["BLK"]) / regulars["GP"]).reset_index(drop=True)


def fetch_league_baseline(*, refresh: bool = False) -> dict[int, pd.Series]:
    """Build the season-by-season comparison pool the shading reads from."""
    baseline: dict[int, pd.Series] = {}
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading league baseline {display_season_label(end_year)}")
        baseline[end_year] = league_rotation_rates(
            fetch_league_season(end_year, refresh=refresh)
        )
    return baseline


def attach_league_percentile(
    table: pd.DataFrame, baseline: dict[int, pd.Series]
) -> pd.DataFrame:
    """Rate every player-season against its own league year, not this chart."""
    missing = sorted(set(table["season_end_year"].astype(int)) - set(baseline))
    if missing:
        raise ValueError(f"No league baseline for seasons {missing}.")

    rated = table.copy()
    percentiles, medians, samples = [], [], []
    for _, row in rated.iterrows():
        rates = baseline[int(row["season_end_year"])]
        percentiles.append(float((rates < float(row["stocks_per_game"])).mean() * 100.0))
        medians.append(float(rates.median()))
        samples.append(int(len(rates)))
    rated["league_percentile"] = percentiles
    rated["league_median"] = medians
    rated["league_ratio"] = rated["stocks_per_game"] / rated["league_median"]
    rated["league_sample"] = samples
    return rated


def fetch_bulls_history(*, refresh: bool = False) -> pd.DataFrame:
    """Load every Bulls regular season from 2000-01 through 2025-26."""
    frames: list[pd.DataFrame] = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        print(f"Loading {display_season_label(end_year)}")
        frames.append(fetch_bulls_season(end_year, refresh=refresh))
    return pd.concat(frames, ignore_index=True)


def build_working_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Apply the minimum-games rule and select one stocks winner at each age."""
    missing = set(COLUMNS) - set(rows.columns)
    if missing:
        raise ValueError(f"Historical stocks rows are missing {sorted(missing)}.")

    table = rows.copy()
    for column in (
        "season_end_year",
        "player_id",
        "age",
        "games",
        "steals",
        "blocks",
        "stocks",
        "team_games",
        "team_steals",
        "team_blocks",
    ):
        table[column] = pd.to_numeric(table[column], errors="raise").astype(int)
    for column in ("steals_per_game", "blocks_per_game", "stocks_per_game"):
        table[column] = pd.to_numeric(table[column], errors="raise").astype(float)
    table["minimum_games"] = (
        table["team_games"] * MIN_TEAM_GAMES_SHARE
    ).apply(math.ceil).astype(int)
    table["qualified"] = table["games"] >= table["minimum_games"]

    winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "stocks_per_game", "stocks", "games", "player"],
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
    if not table["stocks"].eq(table["steals"] + table["blocks"]).all():
        raise ValueError("Stocks do not equal steals plus blocks.")

    for component, team_column, label in (
        ("steals", "team_steals", "steals"),
        ("blocks", "team_blocks", "blocks"),
    ):
        season_total = table.groupby("season_end_year", sort=False)[component].sum()
        team_total = table.groupby("season_end_year", sort=False)[team_column].first()
        if not season_total.eq(team_total).all():
            raise ValueError(f"Player {label} do not reconcile to Bulls team {label}.")

    if "league_percentile" in table.columns:
        percentile = pd.to_numeric(table["league_percentile"], errors="raise")
        if not percentile.between(0.0, 100.0).all():
            raise ValueError("A league percentile falls outside 0–100.")
        if (pd.to_numeric(table["league_sample"], errors="raise") < 50).any():
            raise ValueError("A league baseline season has too small a comparison pool.")
        if (pd.to_numeric(table["league_median"], errors="raise") <= 0).all() is None:
            raise ValueError("A league median is not positive.")
        if not (pd.to_numeric(table["league_median"], errors="raise") > 0).all():
            raise ValueError("A league median is not positive.")

    winners = age_winners(table)
    if winners.empty:
        raise ValueError("No Bulls player-seasons qualified for the stocks age ladder.")
    if winners["age"].duplicated().any():
        raise ValueError("The stocks age ladder has more than one winner for an age.")
    expected_winners = (
        table.loc[table["qualified"]]
        .sort_values(
            ["age", "stocks_per_game", "stocks", "games", "player"],
            ascending=[True, False, False, False, True],
            kind="stable",
        )
        .drop_duplicates("age", keep="first")
    )
    actual_keys = set(zip(winners["season_end_year"], winners["player_id"]))
    expected_keys = set(zip(expected_winners["season_end_year"], expected_winners["player_id"]))
    if actual_keys != expected_keys:
        raise ValueError("The selected stocks ladder does not use the correct winners.")
    return {
        "season_count": len(present_years),
        "player_season_count": len(table),
        "qualified_count": int(table["qualified"].sum()),
        "age_count": len(winners),
        "youngest_age": int(winners["age"].min()),
        "oldest_age": int(winners["age"].max()),
        "highest_stocks": float(winners["stocks_per_game"].max()),
        "lowest_stocks": float(winners["stocks_per_game"].min()),
        "steal_led_count": int((winners["steals_per_game"] > winners["blocks_per_game"]).sum()),
        "block_led_count": int((winners["blocks_per_game"] > winners["steals_per_game"]).sum()),
        "winner_names": winners["player"].tolist(),
        "lowest_ratio": float(winners["league_ratio"].min())
        if "league_ratio" in winners.columns else None,
        "highest_ratio": float(winners["league_ratio"].max())
        if "league_ratio" in winners.columns else None,
        "lowest_percentile": float(winners["league_percentile"].min())
        if "league_percentile" in winners.columns else None,
        "highest_percentile": float(winners["league_percentile"].max())
        if "league_percentile" in winners.columns else None,
        "league_sample_low": int(winners["league_sample"].min())
        if "league_sample" in winners.columns else None,
        "league_sample_high": int(winners["league_sample"].max())
        if "league_sample" in winners.columns else None,
    }


def apply_display_names(winners: pd.DataFrame) -> pd.DataFrame:
    """Label each row with the name that player went by that season.

    Reuses the assist-duo convention so the account never prints "Metta World
    Peace" beside a 2000–01 season, or NBA.com's registered "Jimmy Butler III".
    The audit table keeps the raw source name; only the render is relabelled.
    """
    labeled = winners.copy()
    labeled["player"] = [
        display_name(str(row.player), int(row.player_id), int(row.season_end_year))
        for row in labeled.itertuples()
    ]
    return labeled


def write_working_table(table: pd.DataFrame, date: str) -> Path:
    """Write all player-seasons so exclusions and runners-up remain auditable."""
    path = OUT / f"{date}-bulls-stocks-age-ladder-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def canva_copy_block(report: dict[str, object]) -> str:
    """Return the exact data-bound framing to paste around the chart asset."""
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: THE BULLS' STOCKS AGE LADDER",
            "SUBTITLE: Highest steals plus blocks per game by a Bull at every age since 2000",
            "FOOTER: Data via nba.com | 2000–01 to 2025–26 regular seasons | "
            "Min. 50% of team games | Age as listed by NBA.com",
            "NOTE: Stocks = steals + blocks. It counts visible defensive events, "
            "not defensive value.",
            "NOTE: Chicago-only player stints. One qualifying player-season per age.",
            "NOTE: Shading compares each season to the NBA median for rotation regulars "
            "that year (half their team's games, 20+ minutes per game). "
            "Yellow is exactly league average; green is 2.5x it.",
            f"AUDIT: {report['age_count']} ages, {report['youngest_age']}–{report['oldest_age']}; "
            f"{report['qualified_count']} qualifying player-seasons across "
            f"{report['season_count']} Bulls seasons; displayed range "
            f"{report['lowest_stocks']:.1f}–{report['highest_stocks']:.1f} stocks per game; "
            f"{report['steal_led_count']} steal-led rows, {report['block_led_count']} block-led; "
            f"{report['lowest_ratio']:.2f}x–{report['highest_ratio']:.2f}x league average "
            f"(percentiles {report['lowest_percentile']:.0f}–{report['highest_percentile']:.0f}) "
            f"against pools of {report['league_sample_low']}–{report['league_sample_high']} players.",
        ]
    )


def render_stocks_table(winners: pd.DataFrame, date: str, *, final: bool = False) -> Path:
    """Render the ladder as a table, in the current house table treatment."""
    return render_chart(
        apply_display_names(winners),
        date,
        slug="one-slide",
        layout=STOCKS_LAYOUT,
        scale_min=LEAGUE_RATIO_FLOOR,
        scale_max=LEAGUE_RATIO_CEILING,
        color_scale=PPG_SCALE_RED_YELLOW_GREEN,
        metric_column="stocks_per_game",
        fill_column="league_ratio",
        fill_midpoint=LEAGUE_RATIO_AVERAGE,
        metric_header="STK",
        output_stem="bulls-stocks-age-ladder",
        trailing_columns=STOCKS_TRAILING_COLUMNS,
        chart_width=STOCKS_CHART_WIDTH,
        chart_height=STOCKS_CHART_HEIGHT,
        auto_name_column=True,
        name_column_gap=STOCKS_NAME_COLUMN_GAP,
        metric_width=STOCKS_METRIC_WIDTH,
        trailing_slot_width=STOCKS_TRAILING_SLOT_WIDTH,
        face_crop_fraction=STOCKS_FACE_CROP_FRACTION,
        clip_portraits_to_row=True,
        final=final,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls stocks age ladder chart asset.")
    parser.add_argument("--refresh", action="store_true", help="Refetch every cached NBA.com season response.")
    parser.add_argument("--final", action="store_true", help="Export at final resolution after the draft is approved.")
    args = parser.parse_args()

    snapshot = datetime.now(SNAPSHOT_TZ)
    table = attach_league_percentile(
        build_working_table(fetch_bulls_history(refresh=args.refresh)),
        fetch_league_baseline(refresh=args.refresh),
    )
    report = validate_working_table(table)
    date = snapshot.date().isoformat()
    audit_path = write_working_table(table, date)
    winners = age_winners(table)
    player_ids = sorted(set(winners["player_id"]))
    ensure_headshots(player_ids)
    ensure_historical_headshot_fallbacks(player_ids)
    ensure_blank_headshot()
    chart_path = render_stocks_table(winners, date, final=args.final)
    print(f"Audit: {audit_path}")
    print(f"Chart: {chart_path}")
    print(canva_copy_block(report))


if __name__ == "__main__":
    main()
