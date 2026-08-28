"""Tests for the Bulls rebound age ladder prototype."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.rebounds_age_ladder import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    REBOUNDS_CHART_HEIGHT,
    REBOUNDS_CHART_WIDTH,
    REBOUNDS_TRAILING_COLUMNS,
    age_winners,
    attach_league_baseline,
    build_working_table,
    canva_copy_block,
    display_season_label,
    league_rotation_rates,
    player_source_url,
    validate_working_table,
)


def _source_rows() -> pd.DataFrame:
    records = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        team_games = {2012: 66, 2020: 65, 2021: 72}.get(end_year, 82)
        for player_id, player, age, games, orb, dreb in (
            (1000 + end_year, "Glass Cleaner", 28, team_games, 3 * team_games, 9 * team_games),
            (2000 + end_year, "Guard Rebounder", 22, team_games, 2 * team_games, 8 * team_games),
        ):
            records.append({
                "season_end_year": end_year,
                "season": display_season_label(end_year),
                "player_id": player_id,
                "player": player,
                "age": age,
                "games": games,
                "offensive_rebounds": orb,
                "defensive_rebounds": dreb,
                "rebounds": orb + dreb,
                "offensive_rebounds_per_game": orb / games,
                "defensive_rebounds_per_game": dreb / games,
                "rebounds_per_game": (orb + dreb) / games,
                "team_games": team_games,
                "team_offensive_rebounds": 5 * team_games,
                "team_defensive_rebounds": 17 * team_games,
                "team_rebounds": 22 * team_games,
                "player_source_url": player_source_url(end_year),
                "team_source_url": "https://example.test/team",
            })
    return pd.DataFrame(records)


def _baseline() -> dict[int, pd.Series]:
    rates = pd.Series([4.0 + 8.0 * i / 199 for i in range(200)])
    return {year: rates for year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1)}


def _rated_table() -> pd.DataFrame:
    return attach_league_baseline(build_working_table(_source_rows()), _baseline())


def test_source_url_keeps_requested_bulls_season():
    url = player_source_url(2026)
    assert "Season=2025-26" in url
    assert "TeamID=1610612741" in url


def test_shortened_seasons_use_half_of_that_seasons_schedule():
    rows = _source_rows()
    rows.loc[(rows["season_end_year"] == 2012) & (rows["player"] == "Glass Cleaner"), "games"] = 32
    rows.loc[(rows["season_end_year"] == 2021) & (rows["player"] == "Glass Cleaner"), "games"] = 36
    table = build_working_table(rows)
    short = table.loc[table["season_end_year"].isin([2012, 2021]) & (table["player"] == "Glass Cleaner")]
    assert short["minimum_games"].tolist() == [33, 36]
    assert short["qualified"].tolist() == [False, True]


def test_winner_is_rpg_then_total_rebounds_then_games():
    rows = _source_rows()
    year = FIRST_SEASON_END_YEAR
    rows.loc[rows["player_id"] == 1000 + year, ["age", "rebounds_per_game", "rebounds", "games"]] = [30, 12.0, 600, 50]
    challenger = rows.loc[rows["player_id"] == 2000 + year].copy()
    challenger["player_id"] = 999999
    challenger["player"] = "Rebound Tie"
    challenger[["age", "rebounds_per_game", "rebounds", "games"]] = [30, 12.0, 620, 52]
    rows = pd.concat([rows, challenger], ignore_index=True)
    rows.loc[rows["season_end_year"] == year, "team_rebounds"] = rows.loc[rows["season_end_year"] == year, "rebounds"].sum()
    rows.loc[rows["season_end_year"] == year, "team_offensive_rebounds"] = rows.loc[rows["season_end_year"] == year, "offensive_rebounds"].sum()
    rows.loc[rows["season_end_year"] == year, "team_defensive_rebounds"] = rows.loc[rows["season_end_year"] == year, "defensive_rebounds"].sum()
    winner = age_winners(build_working_table(rows))
    age_30 = winner.loc[winner["age"] == 30].iloc[0]
    assert age_30["player"] == "Rebound Tie"
    assert age_30["rebounds"] == 620


def test_validation_covers_all_seasons_and_reconciles_components():
    report = validate_working_table(build_working_table(_source_rows()))
    assert report["season_count"] == 26
    assert report["age_count"] == 2
    assert report["youngest_age"] == 22
    assert report["oldest_age"] == 28


def test_validation_rejects_a_rebound_component_mismatch():
    table = build_working_table(_source_rows())
    table.loc[0, "rebounds"] += 1
    with pytest.raises(ValueError, match="Rebounds do not equal"):
        validate_working_table(table)


def test_components_lead_and_games_played_trails():
    assert [entry.header for entry in REBOUNDS_TRAILING_COLUMNS] == ["DREB", "ORB", "GP"]
    assert [entry.decimals for entry in REBOUNDS_TRAILING_COLUMNS] == [1, 1, 0]


def test_canva_copy_names_total_rpg_and_qualifier():
    copy = canva_copy_block(validate_working_table(_rated_table()))
    assert "Highest rebounds per game" in copy
    assert "DREB and ORB" in copy
    assert "Min. 50% of team games" in copy
    assert "NBA median RPG" in copy


def test_league_rotation_rates_excludes_short_or_low_minute_players():
    rows = pd.DataFrame([
        {"PLAYER_ID": 1, "PLAYER_NAME": "Regular", "GP": 82, "MIN": 2000, "REB": 820},
        {"PLAYER_ID": 2, "PLAYER_NAME": "Short", "GP": 20, "MIN": 500, "REB": 200},
        {"PLAYER_ID": 3, "PLAYER_NAME": "Bench", "GP": 82, "MIN": 1000, "REB": 410},
    ])
    assert league_rotation_rates(rows).tolist() == [10.0]


def test_primary_asset_keeps_stocks_dimensions():
    assert (REBOUNDS_CHART_WIDTH, REBOUNDS_CHART_HEIGHT) == (1280, 1200)
