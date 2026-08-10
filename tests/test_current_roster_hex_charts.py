"""Contracts for the current-roster player hex batch."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "current_roster_hex_charts",
    ROOT / "scripts" / "prototypes" / "current_roster_hex_charts.py")
charts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(charts)


def test_player_qualifier_is_inclusive_at_250_fga():
    assert charts.MIN_PLAYER_FGA == 250
    assert charts.qualifies_player(250)
    assert not charts.qualifies_player(249)


def test_player_summary_keeps_missing_data_missing_not_zero():
    cells = pd.DataFrame({
        "displayed": pd.Series(dtype=bool),
        "exact_fga": pd.Series(dtype=int),
        "color_rated": pd.Series(dtype=bool),
    })

    row = charts.player_summary(
        "Rookie", 1,
        pd.DataFrame(columns=["shot_made", "shot_type"]),
        pd.DataFrame(), cells, 250)

    assert pd.isna(row["season_fg_pct"])
    assert pd.isna(row["season_efg_pct"])
    assert pd.isna(row["season_3pt_pct"])
    assert row["season_fga"] == 0
    assert not row["qualified"]


def test_canva_stats_row_includes_team_or_player_fga_efg_and_three_point_rate():
    shots = pd.DataFrame({
        "shot_made": [True, True, False, False],
        "shot_type": ["2PT", "3PT", "3PT", "2PT"],
    })

    assert charts.canva_stats_row("Chicago Bulls", "Chicago attempts", shots) == {
        "subject": "Chicago Bulls",
        "scope": "Chicago attempts",
        "fga": 4,
        "efg_pct": 62.5,
        "three_pt_pct": 50.0,
    }
