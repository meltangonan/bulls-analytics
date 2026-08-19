"""Tests for the analysis-first Bulls rookie metric comparison."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.bulls_rookie_metric_analysis import (
    add_playstyle_and_win_context,
    build_composite_ranking,
    build_ts_era_sensitivity,
    build_working_table,
    normalize_name,
    season_label,
    validate,
)


def _sources() -> tuple[pd.DataFrame, pd.DataFrame]:
    nba = pd.DataFrame(
        [
            (2009, "2008-09", 1, "Derrick Rose", 81, 3000.0, 1361, 317, 512, 60, 16, 202, 1208, 250, -1.8, 5907),
            (2016, "2015-16", 2, "Bobby Portis Jr.", 62, 1060.0, 435, 341, 51, 22, 21, 54, 437, 66, -7.6, 2200),
        ],
        columns=[
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
            "possessions",
        ],
    )
    bref = pd.DataFrame(
        [
            (2009, "Derrick Rose", 1.1, -1.5, -0.4, 1.2, 4.9, 0.516),
            (2016, "Bobby Portis", -1.1, -2.2, -3.3, -0.4, 1.5, 0.498),
        ],
        columns=[
            "season",
            "player_name",
            "obpm",
            "dbpm",
            "bpm",
            "vorp",
            "ws",
            "ts_pct",
        ],
    )
    return nba, bref


def test_season_label_starts_since_2000_at_2000_01():
    assert season_label(2001) == "2000-01"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Bobby Portis Jr.", "bobby portis"),
        ("Nikola Vučević", "nikola vucevic"),
        ("Ömer Aşık", "omer asik"),
        ("Norman Richardson", "norm richardson"),
        ("Jimmy Butler III", "jimmy butler"),
    ],
)
def test_normalize_name_handles_source_differences(raw, expected):
    assert normalize_name(raw) == expected


def test_metrics_use_games_and_player_possessions():
    table = build_working_table(*_sources())
    rose = table.loc[table["player_name"] == "Derrick Rose"].iloc[0]
    assert rose["ppg"] == pytest.approx(1361 / 81)
    assert rose["pra_per_75"] == pytest.approx((1361 + 317 + 512) * 75 / 5907)


def test_vorp_rank_rewards_total_value_while_pra75_is_rate_only():
    table = build_working_table(*_sources())
    rose = table.loc[table["player_name"] == "Derrick Rose"].iloc[0]
    portis = table.loc[table["player_name"] == "Bobby Portis Jr."].iloc[0]
    assert rose["rank_vorp_1000"] == 1
    assert portis["rank_vorp_1000"] == 2
    assert rose["qualified_1000"]
    assert portis["qualified_1000"]


def test_validation_rejects_an_unmatched_bref_row():
    nba, bref = _sources()
    table = build_working_table(nba, bref.iloc[:1])
    with pytest.raises(ValueError, match="Basketball Reference join failed"):
        validate(table)


def test_validation_reports_population_and_qualifiers():
    table = build_working_table(*_sources())
    audit = validate(table)
    assert audit["rookie_seasons"] == 2
    assert audit["qualifiers"]["1000"] == 2


def test_playstyle_shares_and_team_context_are_derived_separately():
    table = build_working_table(*_sources())
    shots = pd.DataFrame(
        [
            (2009, 1, 484, 130, 522, 4, 6, 55, 7),
            (2016, 2, 200, 70, 80, 20, 15, 50, 2),
        ],
        columns=[
            "season",
            "player_id",
            "restricted_area_fga",
            "in_the_paint_non_ra_fga",
            "mid_range_fga",
            "left_corner_3_fga",
            "right_corner_3_fga",
            "above_the_break_3_fga",
            "backcourt_fga",
        ],
    )
    records = pd.DataFrame(
        [
            (2008, "2007-08", 33, 49, 82),
            (2009, "2008-09", 41, 41, 82),
            (2016, "2015-16", 42, 40, 82),
        ],
        columns=["season", "season_label", "team_wins", "team_losses", "team_games"],
    )
    result = add_playstyle_and_win_context(table, shots, records)
    rose = result.loc[result["player_name"] == "Derrick Rose"].iloc[0]
    assert rose["shot_zone_fga"] == 1208
    assert rose["rim_attempt_share"] == pytest.approx(484 / 1208)
    assert rose["three_attempt_share"] == pytest.approx((4 + 6 + 55 + 7) / 1208)
    assert rose["team_wins"] == 41
    assert rose["previous_team_wins"] == 33
    assert rose["team_win_change"] == 8
    assert rose["team_win_pct_change"] == pytest.approx(8 / 82)
    assert rose["rank_ws_1000"] == 1


def test_composite_uses_six_equal_weight_ranks_and_keeps_team_record_as_context():
    table = build_working_table(*_sources())
    shots = pd.DataFrame(
        [
            (2009, 1, 484, 130, 522, 4, 6, 55, 7),
            (2016, 2, 200, 70, 80, 20, 15, 50, 2),
        ],
        columns=[
            "season", "player_id", "restricted_area_fga", "in_the_paint_non_ra_fga",
            "mid_range_fga", "left_corner_3_fga", "right_corner_3_fga",
            "above_the_break_3_fga", "backcourt_fga",
        ],
    )
    records = pd.DataFrame(
        [(2008, "2007-08", 33, 49, 82), (2009, "2008-09", 41, 41, 82),
         (2016, "2015-16", 42, 40, 82)],
        columns=["season", "season_label", "team_wins", "team_losses", "team_games"],
    )
    enriched = add_playstyle_and_win_context(table, shots, records)
    ranking = build_composite_ranking(enriched)
    rose = ranking.loc[ranking.player_name == "Derrick Rose"].iloc[0]
    expected = rose[
        ["rank_ppg", "rank_rpg", "rank_apg", "rank_stocks_per_game", "rank_ts_pct", "rank_ws"]
    ].mean()
    assert rose["stocks_per_game"] == pytest.approx((60 + 16) / 81)
    assert rose["average_category_rank"] == pytest.approx(expected)
    assert rose["team_record"] == "41-41"
    assert rose["team_win_change"] == 8


def test_ts_sensitivity_replaces_only_raw_ts_rank():
    table = build_working_table(*_sources())
    shots = pd.DataFrame(
        [(2009, 1, 484, 130, 522, 4, 6, 55, 7),
         (2016, 2, 200, 70, 80, 20, 15, 50, 2)],
        columns=["season", "player_id", "restricted_area_fga", "in_the_paint_non_ra_fga",
                 "mid_range_fga", "left_corner_3_fga", "right_corner_3_fga",
                 "above_the_break_3_fga", "backcourt_fga"],
    )
    records = pd.DataFrame(
        [(2008, "2007-08", 33, 49, 82), (2009, "2008-09", 41, 41, 82),
         (2016, "2015-16", 42, 40, 82)],
        columns=["season", "season_label", "team_wins", "team_losses", "team_games"],
    )
    ranking = build_composite_ranking(add_playstyle_and_win_context(table, shots, records))
    baselines = pd.DataFrame(
        [("2008-09", 0.545), ("2015-16", 0.541)],
        columns=["season", "league_ts_pct"],
    )
    sensitivity = build_ts_era_sensitivity(ranking, baselines)
    rose = sensitivity.loc[sensitivity.player_name == "Derrick Rose"].iloc[0]
    assert rose["relative_ts_pp"] == pytest.approx((0.516 - 0.545) * 100)
    assert rose["era_adjusted_average_rank"] == pytest.approx(
        rose[["rank_ppg", "rank_rpg", "rank_apg", "rank_stocks_per_game",
              "rank_relative_ts", "rank_ws"]].mean()
    )
