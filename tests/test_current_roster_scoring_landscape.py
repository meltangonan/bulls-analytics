"""Post-specific tests for the current-roster scoring landscape."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from scripts.prototypes.current_roster_scoring_landscape import (
    MIN_TRUE_SHOOTING_ATTEMPTS,
    build_working_table,
    chart_x,
    chart_y,
    qualified_players,
    validate_working_table,
)


def _roster() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"nba_id": 1, "official_roster_name": "Norman Powell"},
            {"nba_id": 2, "official_roster_name": "Nic Claxton"},
            {"nba_id": 3, "official_roster_name": "Caleb Wilson"},
        ]
    )


def _base() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "PLAYER_ID": 1,
                "PLAYER_NAME": "Norman Powell",
                "TEAM_ABBREVIATION": "MIA",
                "GP": 60,
                "MIN": 1800.0,
                "FGA": 700.0,
                "FTA": 250.0,
                "PTS": 1100.0,
            },
            {
                "PLAYER_ID": 2,
                "PLAYER_NAME": "Nic Claxton",
                "TEAM_ABBREVIATION": "BKN",
                "GP": 65,
                "MIN": 1750.0,
                "FGA": 250.0,
                "FTA": 0.0,
                "PTS": 250.0,
            },
        ]
    )


def _advanced() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "PLAYER_ID": 1,
                "POSS": 3900.0,
                "TS_PCT": round(1100 / (2 * (700 + 0.44 * 250)), 3),
            },
            {
                "PLAYER_ID": 2,
                "POSS": 3600.0,
                "TS_PCT": 0.500,
            },
        ]
    )


def _teams() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"PTS": 9000.0, "FGA": 7000.0, "FTA": 1800.0},
            {"PTS": 9200.0, "FGA": 7100.0, "FTA": 1900.0},
        ]
    )


def _table() -> pd.DataFrame:
    return build_working_table(
        _roster(),
        _base(),
        _advanced(),
        _teams(),
        datetime(2026, 7, 23, 12, tzinfo=ZoneInfo("America/Chicago")),
    )


def test_uses_full_season_team_field_for_new_bulls():
    table = _table()

    powell = table.loc[table["official_roster_name"] == "Norman Powell"].iloc[0]
    claxton = table.loc[table["official_roster_name"] == "Nic Claxton"].iloc[0]

    assert powell["season_team_field"] == "MIA"
    assert claxton["season_team_field"] == "BKN"


def test_threshold_is_inclusive_at_250_true_shooting_attempts():
    table = _table()
    claxton = table.loc[table["official_roster_name"] == "Nic Claxton"].iloc[0]

    assert claxton["true_shooting_attempts"] == MIN_TRUE_SHOOTING_ATTEMPTS
    assert claxton["qualified"]


def test_rookie_without_nba_row_remains_unavailable_and_unplotted():
    table = _table()
    rookie = table.loc[table["official_roster_name"] == "Caleb Wilson"].iloc[0]

    assert not rookie["data_available"]
    assert not rookie["qualified"]
    assert "Caleb Wilson" not in qualified_players(table)[
        "official_roster_name"
    ].tolist()


def test_nba_formula_reconstructs_points_per_100_and_axes():
    table = _table()
    report = validate_working_table(table)
    powell = table.loc[table["official_roster_name"] == "Norman Powell"].iloc[0]

    raw_points_per_100 = powell["points"] * 100 / powell["possessions"]
    axes_points_per_100 = 2 * powell["ts_pct"] * powell["shots_per_100"]

    expected_league_ts = 18200 / (2 * (14100 + 0.44 * 3700))
    expected_powell_shots = (700 + 0.44 * 250) * 100 / 3900
    expected_powell_ts = 1100 / (2 * (700 + 0.44 * 250))

    assert axes_points_per_100 == pytest.approx(raw_points_per_100)
    assert powell["shots_per_100"] == pytest.approx(expected_powell_shots)
    assert powell["relative_ts_pp"] == pytest.approx(
        (expected_powell_ts - expected_league_ts) * 100
    )
    assert report["roster_count"] == 3
    assert report["data_available_count"] == 2
    assert report["qualified_count"] == 2
    assert report["roster_median_shots_per_100"] == pytest.approx(
        (
            expected_powell_shots
            + (250 * 100 / 3600)
        )
        / 2
    )
    assert report["no_2025_26_nba_data_names"] == ["Caleb Wilson"]


def test_chart_places_volume_on_x_and_efficiency_on_y():
    assert chart_x(20.0) > chart_x(10.0)
    assert chart_y(5.0) > chart_y(-5.0)
