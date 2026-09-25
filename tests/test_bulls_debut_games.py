import pandas as pd
import pytest

from bulls.config import BULLS_TEAM_ID
from scripts.prototypes.bulls_debut_games import (
    classify_debuts,
    first_bulls_games,
    needs_career_check,
    rank_debuts,
    season_end_year,
)


def test_season_end_year_reads_nba_season_ids():
    assert season_end_year("2001-02") == 2002
    assert season_end_year("1999-00") == 2000


def test_first_bulls_games_skips_zero_minute_rows_and_orders_by_date():
    working = pd.DataFrame([
        {"player_id": 1, "game_id": "3", "game_date": "2002-02-22", "minutes": 30.0},
        {"player_id": 1, "game_id": "1", "game_date": "2002-02-18", "minutes": 0.0},
        {"player_id": 1, "game_id": "2", "game_date": "2002-02-20", "minutes": 44.2},
    ])
    assert first_bulls_games(working)["game_id"].tolist() == ["2"]


def test_classify_debuts_checks_only_pre_window_entrants_for_earlier_stints():
    audit = pd.DataFrame([
        # Entered 1976-77, first logged Bulls game 1984-85, but a Bulls stint in 1978-79.
        {"player_id": 1, "player": "Earlier stint", "season_end_year": 1985, "first_nba_season_end": 1977},
        # Entered 1979-80, first Bulls season is the logged one.
        {"player_id": 2, "player": "Veteran arrival", "season_end_year": 1988, "first_nba_season_end": 1980},
        # Entered after the logs begin: no career lookup needed.
        {"player_id": 3, "player": "Rookie", "season_end_year": 2020, "first_nba_season_end": 2020},
    ])
    career = pd.DataFrame([
        {"PLAYER_ID": 1, "SEASON_ID": "1978-79", "TEAM_ID": BULLS_TEAM_ID},
        {"PLAYER_ID": 1, "SEASON_ID": "1984-85", "TEAM_ID": BULLS_TEAM_ID},
        {"PLAYER_ID": 2, "SEASON_ID": "1979-80", "TEAM_ID": 99},
        {"PLAYER_ID": 2, "SEASON_ID": "1987-88", "TEAM_ID": BULLS_TEAM_ID},
    ])
    assert needs_career_check(audit).tolist() == [True, True, False]
    result = classify_debuts(audit, career).set_index("player")
    assert result["is_debut"].to_dict() == {"Earlier stint": False, "Veteran arrival": True, "Rookie": True}
    assert result["rookie_season"].to_dict() == {"Earlier stint": False, "Veteran arrival": False, "Rookie": True}


def test_classify_debuts_requires_career_rows_for_pre_window_entrants():
    audit = pd.DataFrame([{"player_id": 1, "player": "X", "season_end_year": 1985, "first_nba_season_end": 1980}])
    career = pd.DataFrame(columns=["PLAYER_ID", "SEASON_ID", "TEAM_ID"])
    with pytest.raises(ValueError, match="no Chicago season"):
        classify_debuts(audit, career)


def test_rank_debuts_breaks_game_score_ties_by_points():
    rows = pd.DataFrame([
        {"game_score": 14.7, "points": 13, "ts_pct": 70.0, "game_date": "2014-10-29",
         "player": "Brooks", "player_id": 1},
        {"game_score": 14.7, "points": 22, "ts_pct": 55.0, "game_date": "2026-02-05",
         "player": "Simons", "player_id": 2},
    ])
    ranked = rank_debuts(rows, top_n=2)
    assert ranked["player"].tolist() == ["Simons", "Brooks"]
    assert ranked["rank"].tolist() == [1, 2]


def test_rank_debuts_orders_a_displayed_tie_by_points():
    rows = pd.DataFrame([
        {"game_score": 14.44, "points": 17, "ts_pct": 60.0, "game_date": "2019-10-23",
         "player": "Young", "player_id": 1},
        {"game_score": 14.36, "points": 22, "ts_pct": 55.0, "game_date": "2016-10-27",
         "player": "Wade", "player_id": 2},
    ])
    assert rank_debuts(rows, top_n=2)["player"].tolist() == ["Wade", "Young"]
