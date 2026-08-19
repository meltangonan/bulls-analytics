"""Analyze and rank Bulls rookie seasons since 2000-01.

NBA.com defines the rookie population and supplies Bulls-stint totals and player
possessions. Basketball Reference supplies TS%, Win Shares, BPM, and VORP. The
settled fan-facing table shows every 300-minute rookie chronologically; the
earlier composite ranking remains an exploratory sensitivity artifact.

The three candidate headline measures answer different questions:

* VORP: estimated total value above a replacement player, including playing time.
* PPG: familiar scoring output per game.
* PRA/75: points + rebounds + assists per 75 player possessions.

PRA/75 is a descriptive workload statistic, not an impact metric: it gives one
unit of credit to each point, rebound, and assist and ignores shooting efficiency,
turnovers, defense, and the value of the outcomes it combines.
"""

from __future__ import annotations

import argparse
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from nba_api.stats.endpoints import (
    leaguedashplayershotlocations,
    leaguedashplayerstats,
    leaguedashteamstats,
)

from bulls.config import BULLS_TEAM_ID
from bulls.data import fetch
from bulls.visuals import DATA, visual_dir

FIRST_SEASON_END = 2001
LAST_SEASON_END = 2026
PROJECT = "bulls-rookie-landscape"
DATA_DIR = visual_dir(
    _REPO / "docs" / "visuals", PROJECT, when="2026-08-14"
) / DATA
NBA_RAW_CSV = DATA_DIR / "nba-bulls-rookies-since-2000.csv"
SHOT_PROFILE_RAW_CSV = DATA_DIR / "nba-bulls-rookie-shot-zones-since-2000.csv"
TEAM_RECORD_RAW_CSV = DATA_DIR / "nba-bulls-team-records-1999-2026.csv"
WORKING_CSV = DATA_DIR / "bulls-rookie-metric-comparison.csv"
RANKING_CSV = DATA_DIR / "bulls-rookie-composite-ranking.csv"
LEAGUE_TS_CSV = DATA_DIR / "nba-league-ts-by-season.csv"
TS_SENSITIVITY_CSV = DATA_DIR / "rookie-ts-era-sensitivity.csv"
REPORT_MD = DATA_DIR / "rookie-metric-analysis.md"
BREF_SOURCE_CSV = (
    _REPO
    / "docs"
    / "visuals"
    / "2026-08-09-impactful-bulls-bpm"
    / "data"
    / "bulls-advanced-by-season.csv"
)

MINUTE_THRESHOLDS = (0, 300, 500, 750, 1000)
REPORT_TOP_N = 10

# Source-specific display names that are genuinely the same player. Keep this
# tiny and explicit: a fuzzy name join could silently attach a rookie to the
# wrong historical player.
NAME_KEY_ALIASES = {
    "norman richardson": "norm richardson",
}


def season_label(end_year: int) -> str:
    """Convert 2009 to the display/storage label ``2008-09``."""
    return f"{end_year - 1}-{str(end_year)[2:]}"


def normalize_name(name: str) -> str:
    """Normalize source-specific punctuation and suffixes for a safe join."""
    # Unicode's dotless i has no ASCII decomposition, so normalize it before
    # stripping diacritics (Basketball Reference: Ömer Aşık; NBA: Omer Asik).
    source = str(name).replace("ı", "i").replace("İ", "I")
    text = unicodedata.normalize("NFKD", source).encode("ascii", "ignore").decode()
    text = "".join(char for char in text.lower() if char.isalnum() or char == " ")
    for suffix in (" jr", " iii", " ii", " sr"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    key = " ".join(text.split())
    return NAME_KEY_ALIASES.get(key, key)


def fetch_rookie_season(end_year: int) -> pd.DataFrame:
    """Fetch one season of Bulls rookies from NBA.com's explicit Rookie filter."""
    season = season_label(end_year)
    kwargs = {
        "team_id_nullable": BULLS_TEAM_ID,
        "season": season,
        "season_type_all_star": "Regular Season",
        "player_experience_nullable": "Rookie",
        "per_mode_detailed": "Totals",
        "timeout": 60,
        "headers": fetch._NBA_HEADERS,
    }

    base = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Base", **kwargs
    ).get_data_frames()[0]
    time.sleep(0.6)
    advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Advanced", **kwargs
    ).get_data_frames()[0]
    time.sleep(0.6)

    columns = [
        "season",
        "season_label",
        "player_id",
        "player_name",
        "games",
        "minutes",
        "points",
        "rebounds",
        "assists",
        "steals",
        "blocks",
        "turnovers",
        "field_goal_attempts",
        "free_throw_attempts",
        "possessions",
        "net_rating",
    ]
    if base.empty:
        return pd.DataFrame(columns=columns)

    totals = base[
        [
            "PLAYER_ID",
            "PLAYER_NAME",
            "GP",
            "MIN",
            "PTS",
            "REB",
            "AST",
            "STL",
            "BLK",
            "TOV",
            "FGA",
            "FTA",
        ]
    ]
    advanced_fields = (
        advanced[["PLAYER_ID", "POSS", "NET_RATING"]]
        if not advanced.empty
        else pd.DataFrame()
    )
    if advanced_fields.empty:
        raise ValueError(f"NBA.com returned no advanced rookie rows for {season}")
    joined = totals.merge(
        advanced_fields, on="PLAYER_ID", how="left", validate="one_to_one"
    )
    joined = joined.rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player_name",
            "GP": "games",
            "MIN": "minutes",
            "PTS": "points",
            "REB": "rebounds",
            "AST": "assists",
            "STL": "steals",
            "BLK": "blocks",
            "TOV": "turnovers",
            "FGA": "field_goal_attempts",
            "FTA": "free_throw_attempts",
            "POSS": "possessions",
            "NET_RATING": "net_rating",
        }
    )
    joined.insert(0, "season_label", season)
    joined.insert(0, "season", end_year)
    return joined[columns]


def load_or_fetch_rookies(path: Path, refresh: bool = False) -> pd.DataFrame:
    """Load the complete NBA rookie input or fetch every season into one CSV."""
    expected = set(range(FIRST_SEASON_END, LAST_SEASON_END + 1))
    if path.exists() and not refresh:
        cached = pd.read_csv(path)
        # Seasons with no Bulls rookie still need a fetch audit. The separate
        # ``season_coverage`` column stores the requested season on every real
        # row; validation below reports truly empty seasons from the final set.
        required = {"steals", "blocks", "turnovers"}
        if required.issubset(cached.columns) and set(cached["season"].astype(int)).issubset(expected):
            return cached

    frames = []
    for end_year in sorted(expected):
        print(f"Fetching NBA.com Bulls rookies: {season_label(end_year)}")
        frames.append(fetch_rookie_season(end_year))
    result = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    return result


def fetch_rookie_shot_season(end_year: int) -> pd.DataFrame:
    """Fetch rookie shooting by NBA.com's mutually exclusive basic zones."""
    season = season_label(end_year)
    frame = leaguedashplayershotlocations.LeagueDashPlayerShotLocations(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        team_id_nullable=BULLS_TEAM_ID,
        player_experience_nullable="Rookie",
        distance_range="By Zone",
        timeout=60,
        headers=fetch._NBA_HEADERS,
    ).get_data_frames()[0]
    time.sleep(0.6)
    if frame.empty:
        return pd.DataFrame()

    # This endpoint returns a two-level header: zone, then FGM/FGA/FG_PCT.
    flattened = []
    for zone, field in frame.columns:
        zone = str(zone).strip().lower().replace(" ", "_").replace("-", "_")
        zone = zone.replace("(", "").replace(")", "")
        field = str(field).strip().lower()
        flattened.append(field if not zone else f"{zone}_{field}")
    frame.columns = flattened
    frame.insert(0, "season_label", season)
    frame.insert(0, "season", end_year)
    return frame


def load_or_fetch_shot_profiles(path: Path, refresh: bool = False) -> pd.DataFrame:
    """Return every available Bulls rookie basic-zone shooting row."""
    if path.exists() and not refresh:
        return pd.read_csv(path)
    frames = []
    for end_year in range(FIRST_SEASON_END, LAST_SEASON_END + 1):
        print(f"Fetching NBA.com Bulls rookie shot zones: {season_label(end_year)}")
        frame = fetch_rookie_shot_season(end_year)
        if not frame.empty:
            frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    return result


def fetch_team_record(end_year: int) -> dict:
    """Fetch one Bulls regular-season record for team context."""
    season = season_label(end_year)
    frame = leaguedashteamstats.LeagueDashTeamStats(
        team_id_nullable=BULLS_TEAM_ID,
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        measure_type_detailed_defense="Base",
        timeout=60,
        headers=fetch._NBA_HEADERS,
    ).get_data_frames()[0]
    time.sleep(0.6)
    if len(frame) != 1:
        raise ValueError(f"Expected one Bulls team row for {season}, got {len(frame)}")
    row = frame.iloc[0]
    return {
        "season": end_year,
        "season_label": season,
        "team_wins": int(row["W"]),
        "team_losses": int(row["L"]),
        "team_games": int(row["GP"]),
    }


def load_or_fetch_team_records(path: Path, refresh: bool = False) -> pd.DataFrame:
    """Return Bulls records plus the preceding season needed for win change."""
    if path.exists() and not refresh:
        return pd.read_csv(path)
    records = []
    for end_year in range(FIRST_SEASON_END - 1, LAST_SEASON_END + 1):
        print(f"Fetching NBA.com Bulls team record: {season_label(end_year)}")
        records.append(fetch_team_record(end_year))
    result = pd.DataFrame(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    return result


def add_playstyle_and_win_context(
    table: pd.DataFrame, shots: pd.DataFrame, team_records: pd.DataFrame
) -> pd.DataFrame:
    """Add shot-diet shares, Win Share ranks, and non-causal team context."""
    table = table.copy()
    shots = shots.copy()
    shot_columns = {
        "restricted_area_fga": "rim_fga",
        "in_the_paint_non_ra_fga": "paint_non_rim_fga",
        "mid_range_fga": "midrange_fga",
        "left_corner_3_fga": "left_corner_three_fga",
        "right_corner_3_fga": "right_corner_three_fga",
        "above_the_break_3_fga": "above_break_three_fga",
        "backcourt_fga": "backcourt_fga",
    }
    required = ["season", "player_id", *shot_columns]
    missing = sorted(set(required) - set(shots.columns))
    if missing:
        raise ValueError(f"Shot profile is missing columns: {missing}")
    shot_working = shots[required].rename(columns=shot_columns)
    shot_working["three_fga"] = shot_working[
        [
            "left_corner_three_fga",
            "right_corner_three_fga",
            "above_break_three_fga",
            "backcourt_fga",
        ]
    ].sum(axis=1)
    shot_working["shot_zone_fga"] = shot_working[
        ["rim_fga", "paint_non_rim_fga", "midrange_fga", "three_fga"]
    ].sum(axis=1)
    shot_working["rim_attempt_share"] = (
        shot_working["rim_fga"] / shot_working["shot_zone_fga"]
    )
    shot_working["three_attempt_share"] = (
        shot_working["three_fga"] / shot_working["shot_zone_fga"]
    )
    table = table.merge(
        shot_working,
        on=["season", "player_id"],
        how="left",
        validate="one_to_one",
    )

    records = team_records.copy().sort_values("season")
    records["previous_team_wins"] = records["team_wins"].shift(1)
    records["previous_team_games"] = records["team_games"].shift(1)
    records["team_win_pct"] = records["team_wins"] / records["team_games"]
    records["previous_team_win_pct"] = records["team_win_pct"].shift(1)
    records["team_win_pct_change"] = (
        records["team_win_pct"] - records["previous_team_win_pct"]
    )
    # A raw win delta is only comparable when both schedules were the same
    # length. Win-percentage change remains valid through shortened seasons.
    same_length = records["team_games"].eq(records["previous_team_games"])
    records["team_win_change"] = (
        records["team_wins"] - records["previous_team_wins"]
    ).where(same_length)
    table = table.merge(
        records[
            [
                "season",
                "team_wins",
                "team_losses",
                "team_games",
                "previous_team_wins",
                "previous_team_games",
                "team_win_change",
                "team_win_pct",
                "previous_team_win_pct",
                "team_win_pct_change",
            ]
        ],
        on="season",
        how="left",
        validate="many_to_one",
    )
    for threshold in MINUTE_THRESHOLDS:
        mask = table[f"qualified_{threshold}"]
        table.loc[mask, f"rank_ws_{threshold}"] = table.loc[mask, "ws"].rank(
            method="min", ascending=False
        )
    return table


def build_working_table(nba: pd.DataFrame, bref: pd.DataFrame) -> pd.DataFrame:
    """Join the two sources and derive the candidate measures and ranks."""
    nba = nba.copy()
    bref = bref.copy()
    nba["name_key"] = nba["player_name"].map(normalize_name)
    bref["name_key"] = bref["player_name"].map(normalize_name)

    advanced = bref[
        [
            "season",
            "name_key",
            "player_name",
            "obpm",
            "dbpm",
            "bpm",
            "vorp",
            "ws",
            "ts_pct",
        ]
    ].rename(columns={"player_name": "bref_player_name"})
    table = nba.merge(
        advanced,
        on=["season", "name_key"],
        how="left",
        validate="one_to_one",
    )

    table["minutes_per_game"] = table["minutes"] / table["games"]
    table["ppg"] = table["points"] / table["games"]
    table["pra"] = table["points"] + table["rebounds"] + table["assists"]
    table["pra_per_75"] = table["pra"] * 75 / table["possessions"]
    table["points_per_75"] = table["points"] * 75 / table["possessions"]
    for threshold in MINUTE_THRESHOLDS:
        table[f"qualified_{threshold}"] = table["minutes"].ge(threshold)

    rank_metrics = ("bpm", "vorp", "ppg", "pra_per_75")
    for threshold in MINUTE_THRESHOLDS:
        mask = table[f"qualified_{threshold}"]
        for metric in rank_metrics:
            table.loc[mask, f"rank_{metric}_{threshold}"] = table.loc[
                mask, metric
            ].rank(method="min", ascending=False)

    order = [
        "season",
        "season_label",
        "player_id",
        "player_name",
        "games",
        "minutes",
        "minutes_per_game",
        "possessions",
        "points",
        "rebounds",
        "assists",
        "steals",
        "blocks",
        "turnovers",
        "field_goal_attempts",
        "free_throw_attempts",
        "net_rating",
        "ppg",
        "points_per_75",
        "pra",
        "pra_per_75",
        "obpm",
        "dbpm",
        "bpm",
        "vorp",
        "ws",
        "ts_pct",
    ]
    order += [f"qualified_{value}" for value in MINUTE_THRESHOLDS]
    order += [
        f"rank_{metric}_{value}"
        for value in MINUTE_THRESHOLDS
        for metric in rank_metrics
    ]
    return table[order].sort_values(["season", "minutes"], ascending=[True, False])


COMPOSITE_METRICS = (
    "ppg",
    "rpg",
    "apg",
    "stocks_per_game",
    "ts_pct",
    "ws",
)


def build_composite_ranking(table: pd.DataFrame, threshold: int = 1000) -> pd.DataFrame:
    """Rank qualified rookie seasons in six equal-weight, fan-facing categories.

    Category ties receive their average rank. Team record and year-over-year win
    change are retained as context but never enter the composite.
    """
    required = {
        "season",
        "season_label",
        "player_id",
        "player_name",
        "games",
        "minutes",
        "points",
        "rebounds",
        "assists",
        "steals",
        "blocks",
        "ts_pct",
        "ws",
        "team_wins",
        "team_losses",
        "team_games",
        "team_win_change",
        "team_win_pct_change",
        f"qualified_{threshold}",
    }
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Rookie composite input is missing {sorted(missing)}")

    ranking = table.loc[table[f"qualified_{threshold}"]].copy()
    ranking["ppg"] = ranking["points"] / ranking["games"]
    ranking["rpg"] = ranking["rebounds"] / ranking["games"]
    ranking["apg"] = ranking["assists"] / ranking["games"]
    ranking["steals_per_game"] = ranking["steals"] / ranking["games"]
    ranking["blocks_per_game"] = ranking["blocks"] / ranking["games"]
    ranking["stocks_per_game"] = (
        ranking["steals"] + ranking["blocks"]
    ) / ranking["games"]

    rank_columns = []
    for metric in COMPOSITE_METRICS:
        rank_column = f"rank_{metric}"
        ranking[rank_column] = ranking[metric].rank(method="average", ascending=False)
        rank_columns.append(rank_column)
    ranking["average_category_rank"] = ranking[rank_columns].mean(axis=1)
    ranking["composite_rank"] = ranking["average_category_rank"].rank(
        method="min", ascending=True
    )
    ranking["team_record"] = (
        ranking["team_wins"].astype(int).astype(str)
        + "-"
        + ranking["team_losses"].astype(int).astype(str)
    )

    output_columns = [
        "composite_rank",
        "average_category_rank",
        "season",
        "season_label",
        "player_id",
        "player_name",
        "games",
        "minutes",
        "ppg",
        "rpg",
        "apg",
        "steals_per_game",
        "blocks_per_game",
        "stocks_per_game",
        "ts_pct",
        "ws",
        *rank_columns,
        "team_record",
        "team_wins",
        "team_losses",
        "team_games",
        "team_win_change",
        "team_win_pct_change",
    ]
    return ranking[output_columns].sort_values(
        ["average_category_rank", "ws", "minutes", "player_name"],
        ascending=[True, False, False, True],
        kind="stable",
    ).reset_index(drop=True)


def build_ts_era_sensitivity(
    ranking: pd.DataFrame, league_baselines: pd.DataFrame
) -> pd.DataFrame:
    """Re-rank only the TS category relative to each season's NBA baseline.

    This is a private fairness check, not the reader-facing formula. It reveals
    whether raw TS% materially favors rookies from a more efficient scoring era.
    """
    required = {"season", "league_ts_pct"}
    missing = required - set(league_baselines.columns)
    if missing:
        raise ValueError(f"League TS baseline is missing {sorted(missing)}")
    baselines = league_baselines.copy()
    baselines["season_end_year"] = (
        baselines["season"].astype(str).str[:4].astype(int) + 1
    )
    result = ranking.merge(
        baselines[["season_end_year", "league_ts_pct"]],
        left_on="season",
        right_on="season_end_year",
        how="left",
        validate="many_to_one",
    )
    if result["league_ts_pct"].isna().any():
        raise ValueError("Every qualified rookie season needs a league TS baseline")
    result["relative_ts_pp"] = (result["ts_pct"] - result["league_ts_pct"]) * 100
    result["rank_relative_ts"] = result["relative_ts_pp"].rank(
        method="average", ascending=False
    )
    sensitivity_ranks = [
        "rank_ppg",
        "rank_rpg",
        "rank_apg",
        "rank_stocks_per_game",
        "rank_relative_ts",
        "rank_ws",
    ]
    result["era_adjusted_average_rank"] = result[sensitivity_ranks].mean(axis=1)
    result["era_adjusted_composite_rank"] = result[
        "era_adjusted_average_rank"
    ].rank(method="min", ascending=True)
    return result.sort_values(
        ["era_adjusted_average_rank", "ws", "minutes", "player_name"],
        ascending=[True, False, False, True],
        kind="stable",
    ).reset_index(drop=True)


def validate(table: pd.DataFrame) -> dict:
    """Fail before reporting if population, joins, or derived rates are suspect."""
    if table.empty:
        raise ValueError("Rookie table is empty")
    if table.duplicated(["season", "player_id"]).any():
        raise ValueError("Duplicate NBA player-season rows")
    missing_bref = table.loc[table["vorp"].isna(), ["season_label", "player_name"]]
    if not missing_bref.empty:
        raise ValueError(
            "Basketball Reference join failed for: "
            + ", ".join(
                f"{row.player_name} ({row.season_label})"
                for row in missing_bref.itertuples()
            )
        )
    if table["possessions"].isna().any() or table["possessions"].le(0).any():
        raise ValueError("Every rookie row needs positive NBA.com possessions")

    expected_pra75 = (
        (table["points"] + table["rebounds"] + table["assists"])
        * 75
        / table["possessions"]
    )
    if not expected_pra75.round(10).equals(table["pra_per_75"].round(10)):
        raise ValueError("PRA/75 does not reconcile to source totals")

    if "shot_zone_fga" in table:
        meaningful = table["minutes"].ge(500)
        if table.loc[meaningful, "shot_zone_fga"].isna().any():
            raise ValueError("Every 500-minute rookie needs a shot-zone row")
        mismatch = table.loc[
            table["shot_zone_fga"].notna()
            & table["field_goal_attempts"].ne(table["shot_zone_fga"])
        ]
        if not mismatch.empty:
            raise ValueError(
                "Shot-zone attempts do not reconcile for: "
                + ", ".join(mismatch["player_name"].tolist())
            )
    if "team_wins" in table and table["team_wins"].isna().any():
        raise ValueError("Every rookie season needs Bulls team record context")

    all_seasons = set(range(FIRST_SEASON_END, LAST_SEASON_END + 1))
    represented = set(table["season"].astype(int))
    return {
        "rookie_seasons": int(len(table)),
        "players": int(table["player_id"].nunique()),
        "seasons_with_rookie": int(table["season"].nunique()),
        "seasons_without_rookie": [season_label(y) for y in sorted(all_seasons - represented)],
        "qualifiers": {
            str(threshold): int(table[f"qualified_{threshold}"].sum())
            for threshold in MINUTE_THRESHOLDS
        },
    }


def _top_table(table: pd.DataFrame, metric: str, threshold: int) -> str:
    rows = (
        table[table[f"qualified_{threshold}"]]
        .sort_values([metric, "minutes"], ascending=[False, False])
        .head(REPORT_TOP_N)
        .copy()
    )
    lines = [
        "| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(rows.itertuples(), 1):
        lines.append(
            f"| {rank} | {row.player_name}, {row.season_label} | "
            f"{row.minutes:,.0f} | {row.bpm:+.1f} | "
            f"{row.vorp:.1f} | {row.ws:.1f} | {row.ppg:.1f} | {row.pra_per_75:.1f} |"
        )
    return "\n".join(lines)


def _composite_top_table(table: pd.DataFrame) -> str:
    ranking = build_composite_ranking(table).head(10)
    lines = [
        "| Overall | Rookie season | PTS | REB | AST | STL+BLK | TS% | WS | Avg rank | Record | Change |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in ranking.itertuples():
        change = (
            f"{int(row.team_win_change):+d} wins"
            if pd.notna(row.team_win_change)
            else f"{row.team_win_pct_change * 100:+.1f} win% pts"
        )
        lines.append(
            f"| {int(row.composite_rank)} | {row.player_name}, {row.season_label} | "
            f"{row.ppg:.1f} (#{row.rank_ppg:g}) | {row.rpg:.1f} (#{row.rank_rpg:g}) | "
            f"{row.apg:.1f} (#{row.rank_apg:g}) | {row.stocks_per_game:.1f} "
            f"(#{row.rank_stocks_per_game:g}) | {row.ts_pct * 100:.1f}% "
            f"(#{row.rank_ts_pct:g}) | {row.ws:.1f} (#{row.rank_ws:g}) | "
            f"{row.average_category_rank:.1f} | {row.team_record} | {change} |"
        )
    return "\n".join(lines)


def build_report(table: pd.DataFrame, audit: dict) -> str:
    """Create the review document the owner uses to select a metric."""
    qualified = table[table["qualified_500"]]
    correlation = qualified[["bpm", "vorp", "ws", "ppg", "pra_per_75"]].corr(
        method="spearman"
    )
    threshold_rows = "\n".join(
        f"- {threshold:,}+ minutes: {audit['qualifiers'][str(threshold)]} rookie seasons"
        for threshold in MINUTE_THRESHOLDS
    )
    correlation = correlation.rename(
        index={
            "bpm": "BPM",
            "vorp": "VORP",
            "ws": "Win Shares",
            "ppg": "PPG",
            "pra_per_75": "PRA/75",
        },
        columns={
            "bpm": "BPM",
            "vorp": "VORP",
            "ws": "Win Shares",
            "ppg": "PPG",
            "pra_per_75": "PRA/75",
        },
    ).round(2)
    labels = list(correlation.columns)
    correlation_lines = [
        "| Measure | " + " | ".join(labels) + " |",
        "| --- | " + " | ".join("---:" for _ in labels) + " |",
    ]
    for label, row in correlation.iterrows():
        correlation_lines.append(
            f"| {label} | " + " | ".join(f"{row[column]:.2f}" for column in labels) + " |"
        )
    correlation_md = "\n".join(correlation_lines)

    sections = [
        "# Bulls rookie metric comparison",
        "",
        "Regular-season Bulls rookie seasons from 2000-01 through 2025-26. "
        "NBA.com defines `Rookie` and supplies Bulls-stint totals and player "
        "possessions. Basketball Reference supplies TS%, Win Shares, BPM, and VORP.",
        "",
        "## Population audit",
        "",
        f"- {audit['rookie_seasons']} player-seasons from {audit['players']} players",
        f"- {audit['seasons_with_rookie']} of 26 seasons contain at least one Bulls rookie",
        f"- Seasons with none: {', '.join(audit['seasons_without_rookie']) or 'None'}",
        threshold_rows,
        "- Without a floor, Max Strus's 6-minute stint ranks first in BPM and "
        "Adama Sanogo's 66-minute stint ranks first in PRA/75. A role or minutes "
        "dimension is mandatory for either rate statistic.",
        "",
        "## What each measure rewards",
        "",
        "- **BPM:** estimated box-score contribution per 100 possessions. Rate only; "
        "small samples can rank highly.",
        "- **VORP:** BPM translated into estimated total value above replacement, so "
        "playing time is part of the result.",
        "- **Win Shares:** estimated player contribution to team wins, split from "
        "offensive and defensive components. It is cumulative and team-influenced, "
        "so it fits the owner's win-context intuition without assigning the entire "
        "year-over-year team change to one rookie.",
        "- **PPG:** scoring per appearance. Familiar, but rewards scoring only and is "
        "affected by minutes per game and pace.",
        "- **PRA/75:** points + rebounds + assists per 75 player possessions. Adjusts "
        "for pace/opportunity, but does not measure efficiency or overall impact and "
        "weights unlike box-score events equally.",
        "",
        "## Rank agreement (500+ minutes)",
        "",
        "Spearman correlation compares ordering, not whether the metric values have "
        "the same units. A value near 1 means the two measures rank these rookies "
        "similarly.",
        "",
        correlation_md,
        "",
        "## Selected fan-facing table",
        "",
        "The selected direction shows all 46 rookies with at least 300 Bulls "
        "regular-season minutes in chronological order. Columns are original "
        "overall draft pick or UDFA, GP, MPG, PTS, REB, AST, STL+BLK, TOV, TS%, "
        "Win Shares, and BPM. Square performance cells reuse the recent table "
        "family's red-yellow-green scale from each full-pool column minimum to "
        "maximum; opportunity and TOV remain plain. Color is not an overall ranking.",
        "",
        "The earlier equal-weight composite remains in the tracked data as an "
        "exploratory sensitivity check, not the selected editorial framing.",
        "",
        "## Derrick Rose and the Bulls' eight-win improvement",
        "",
        "Chicago improved from 33-49 in 2007-08 to 41-41 in Rose's 2008-09 "
        "rookie season. That is valid team context, not a causal estimate of eight "
        "wins created by Rose. Rose recorded 4.9 Win Shares, second among the "
        "1,000-minute rookies in this dataset, and 1.2 VORP despite a -0.4 BPM. "
        "His BPM combines +1.1 OBPM and -1.5 DBPM; the box-score defensive estimate "
        "is what pulls the rate slightly below league average.",
        "",
        "## Discarded playstyle direction",
        "",
        "A three-point-share versus restricted-area-share scatter was explored, "
        "but it answers a playstyle question rather than the owner's eventual "
        "best-rookie-season question. Its shot-zone inputs remain archived for audit "
        "and possible reuse, but they do not enter the composite or first table draft.",
    ]

    for threshold in (500, 1000):
        sections.extend(["", f"## Leaders with {threshold:,}+ minutes"])
        for metric, label in (
            ("bpm", "BPM"),
            ("vorp", "VORP"),
            ("ws", "Win Shares"),
            ("ppg", "PPG"),
            ("pra_per_75", "PRA per 75 possessions"),
        ):
            sections.extend(["", f"### {label}", "", _top_table(table, metric, threshold)])

    return "\n".join(sections) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refetch NBA.com seasons")
    parser.add_argument(
        "--bref-csv",
        type=Path,
        default=BREF_SOURCE_CSV,
        help="Tracked Basketball Reference season table containing BPM and VORP",
    )
    args = parser.parse_args()

    nba = load_or_fetch_rookies(NBA_RAW_CSV, refresh=args.refresh)
    shots = load_or_fetch_shot_profiles(SHOT_PROFILE_RAW_CSV, refresh=args.refresh)
    team_records = load_or_fetch_team_records(TEAM_RECORD_RAW_CSV, refresh=args.refresh)
    bref = pd.read_csv(args.bref_csv)
    table = build_working_table(nba, bref)
    table = add_playstyle_and_win_context(table, shots, team_records)
    audit = validate(table)
    ranking = build_composite_ranking(table, threshold=1000)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(WORKING_CSV, index=False)
    ranking.to_csv(RANKING_CSV, index=False)
    if LEAGUE_TS_CSV.exists():
        sensitivity = build_ts_era_sensitivity(ranking, pd.read_csv(LEAGUE_TS_CSV))
        sensitivity.to_csv(TS_SENSITIVITY_CSV, index=False)
        print(f"Wrote {TS_SENSITIVITY_CSV}")
    REPORT_MD.write_text(build_report(table, audit))
    print(f"Wrote {WORKING_CSV}")
    print(f"Wrote {RANKING_CSV}")
    print(f"Wrote {REPORT_MD}")
    print(audit)


if __name__ == "__main__":
    main()


LEAGUE_ROOKIE_CSV = DATA_DIR / "nba-league-rookies-since-2000.csv"


def fetch_league_rookie_season(end_year: int) -> pd.DataFrame:
    """Fetch one season of every NBA rookie, not only Chicago's.

    This is the same endpoint and Rookie filter as `fetch_rookie_season` with
    the team filter dropped. It exists to give the table's colour scale a real
    reference population: "good for a rookie" has to be measured against other
    rookies, not against this table's own best and worst rows.
    """
    season = season_label(end_year)
    kwargs = {
        "season": season,
        "season_type_all_star": "Regular Season",
        "player_experience_nullable": "Rookie",
        "per_mode_detailed": "Totals",
        "timeout": 60,
        "headers": fetch._NBA_HEADERS,
    }
    base = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Base", **kwargs
    ).get_data_frames()[0]
    time.sleep(0.6)
    if base.empty:
        return pd.DataFrame()
    advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Advanced", **kwargs
    ).get_data_frames()[0]
    time.sleep(0.6)
    base = base.merge(
        advanced[["PLAYER_ID", "NET_RATING"]], on="PLAYER_ID", how="left",
        validate="one_to_one",
    )
    frame = base.rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player_name",
            "GP": "games",
            "MIN": "minutes",
            "PTS": "points",
            "REB": "rebounds",
            "AST": "assists",
            "STL": "steals",
            "BLK": "blocks",
            "TOV": "turnovers",
            "FGA": "field_goal_attempts",
            "FTA": "free_throw_attempts",
            "NET_RATING": "net_rating",
        }
    )
    frame["season"] = end_year
    frame["season_label"] = season
    return frame[
        [
            "season",
            "season_label",
            "player_id",
            "player_name",
            "games",
            "minutes",
            "points",
            "rebounds",
            "assists",
            "steals",
            "blocks",
            "turnovers",
            "field_goal_attempts",
            "free_throw_attempts",
            "net_rating",
        ]
    ]


def load_or_fetch_league_rookies(
    path: Path = LEAGUE_ROOKIE_CSV, refresh: bool = False
) -> pd.DataFrame:
    """Cache every NBA rookie season in the window in the post's data folder."""
    if path.exists() and not refresh:
        return pd.read_csv(path)
    frames = [
        fetch_league_rookie_season(end_year)
        for end_year in range(FIRST_SEASON_END, LAST_SEASON_END + 1)
    ]
    league = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    missing = set(range(FIRST_SEASON_END, LAST_SEASON_END + 1)) - set(league["season"])
    if missing:
        raise ValueError(f"League rookie fetch missed seasons: {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    league.to_csv(path, index=False)
    return league
