import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).parents[1] / "scripts/prototypes/bulls_scoring_lines.py"
SPEC = importlib.util.spec_from_file_location("bulls_scoring_lines", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

IDENTITY_SCRIPT = Path(__file__).parents[1] / "scripts/prototypes/scoring_line_identity_mockups.py"
IDENTITY_SPEC = importlib.util.spec_from_file_location(
    "scoring_line_identity_mockups", IDENTITY_SCRIPT
)
IDENTITY = importlib.util.module_from_spec(IDENTITY_SPEC)
assert IDENTITY_SPEC.loader is not None
IDENTITY_SPEC.loader.exec_module(IDENTITY)


def test_prepare_data_uses_bulls_games_and_applies_minimum():
    logs = pd.DataFrame(
        {
            "PLAYER_ID": [1, 1],
            "PLAYER_NAME": ["Veteran Player", "Veteran Player"],
            "TEAM_ABBREVIATION": ["AAA", "BBB"],
            "GAME_ID": ["01", "02"],
            "GAME_DATE": ["2025-10-20", "2025-10-22"],
            "MATCHUP": ["AAA vs. CCC", "BBB @ DDD"],
            "MIN": [30, 28],
            "PTS": [10, 20],
        }
    )

    games, audit = MODULE.prepare_data(logs, min_games=2)

    veteran = audit.loc[audit["player_id"] == 1].iloc[0]
    assert games["game_number"].tolist() == [1, 2]
    assert veteran["games_played"] == 2
    assert veteran["total_points"] == 30
    assert veteran["ppg"] == 15.0
    assert veteran["teams"] == "AAA/BBB"
    assert bool(veteran["qualifies"])


def test_prepare_data_filters_unqualified_player_games():
    logs = pd.DataFrame(
        {
            "PLAYER_ID": [1, 3, 3],
            "PLAYER_NAME": ["Low Scorer", "High Scorer", "High Scorer"],
            "TEAM_ABBREVIATION": ["AAA", "BBB", "BBB"],
            "GAME_ID": ["01", "02", "03"],
            "GAME_DATE": ["2025-10-20", "2025-10-20", "2025-10-22"],
            "MATCHUP": ["AAA vs. CCC", "BBB @ DDD", "BBB vs. EEE"],
            "MIN": [20, 30, 31],
            "PTS": [8, 24, 20],
        }
    )

    games, audit = MODULE.prepare_data(logs, min_games=2)

    assert audit["player_name"].tolist() == ["High Scorer", "Low Scorer"]
    assert audit["qualifies"].tolist() == [True, False]
    assert games["player_id"].unique().tolist() == [3]


def test_current_roster_order_is_balanced_ppg_order():
    games, audit = IDENTITY._current_roster_data()
    qualified = audit[audit["qualifies"]].sort_values("ppg", ascending=False)

    assert list(IDENTITY.PLAYERS) == qualified["player_name"].tolist()
    assert len(IDENTITY.PLAYERS) == 10
    assert games["player_id"].nunique() == 10
    assert audit.loc[audit["player_name"].isin(["Noa Essengue", "Zach Collins"]), "qualifies"].tolist() == [False, False]


def test_team_season_label_puts_chicago_first():
    assert IDENTITY._team_season_label("CHI") == "CHI, 2025-26"
    assert IDENTITY._team_season_label("MIN/CHI") == "CHI/MIN, 2025-26"
    assert IDENTITY._team_season_label("MIA") == "MIA, 2025-26"


def test_games_played_label_uses_compact_identity_format():
    assert IDENTITY._games_played_label(77) == "77 GP"


def test_rolling_points_is_trailing_and_starts_after_five_games():
    featured = pd.DataFrame({"points": [10, 20, 30, 40, 50, 60]})

    trend = MODULE.rolling_points(featured)

    assert trend.iloc[:4].isna().all()
    assert trend.iloc[4] == 30.0
    assert trend.iloc[5] == 35.0
