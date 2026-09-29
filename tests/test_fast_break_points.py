import pandas as pd
import pytest

from scripts.prototypes.fast_break_points_data import nba_rank, prepare_season, select_top15


def _frames():
    misc = pd.DataFrame({"PLAYER_ID": [1], "PLAYER_NAME": ["Player"], "GP": [50], "PTS_FB": [200.0]})
    scoring = pd.DataFrame({"PLAYER_ID": [1], "PCT_PTS_FB": [0.18], "FG_PCT": [0.45]})
    league = pd.DataFrame({
        "PLAYER_ID": [1, 2, 3], "PTS_FB": [200.0, 300.0, 200.0], "PTS_FB_RANK": [2, 1, 2],
    })
    return misc, scoring, league


def test_nba_rank_uses_competition_ranking():
    league = pd.Series([300, 200, 200, 150])
    assert nba_rank(200, league) == 2
    assert nba_rank(160, league) == 4


def test_prepare_season_calculates_rate_share_and_rank():
    row = prepare_season("2010-11", *_frames()).iloc[0]
    assert row.fast_break_points == 200
    assert row.fast_break_points_per_game == 4.0
    assert row.share_of_points == 0.18
    assert row.nba_rank == 2
    assert row.nba_rank_endpoint == 2


def test_prepare_season_rejects_mismatched_player_sets():
    misc, scoring, league = _frames()
    scoring["PLAYER_ID"] = [9]
    with pytest.raises(ValueError, match="different Bulls players"):
        prepare_season("2010-11", misc, scoring, league)


def test_top15_breaks_ties_by_per_game_then_older_season():
    rows = [{"player_name": f"P{i}", "season": "2010-11", "player_id": i,
             "fast_break_points": 400 - i, "fast_break_points_per_game": 4.0} for i in range(14)]
    rows += [
        {"player_name": "Slower", "season": "2001-02", "player_id": 20,
         "fast_break_points": 220, "fast_break_points_per_game": 2.7},
        {"player_name": "Faster", "season": "2012-13", "player_id": 21,
         "fast_break_points": 220, "fast_break_points_per_game": 3.0},
    ]
    selected = select_top15(pd.DataFrame(rows))
    assert selected.iloc[-1].player_name == "Faster"
    assert list(selected.display_rank) == list(range(1, 16))
