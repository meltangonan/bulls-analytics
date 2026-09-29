import pandas as pd
import pytest

from scripts.prototypes.second_chance_points_data import STAT, nba_rank, prepare_season, select_top15


def _frames():
    misc = pd.DataFrame({"PLAYER_ID": [1], "PLAYER_NAME": ["Player"], "GP": [50], STAT: [400.0]})
    base = pd.DataFrame({"PLAYER_ID": [1], "PTS": [1000.0]})
    league = pd.DataFrame({"PLAYER_ID": [1, 2, 3], STAT: [400.0, 500.0, 400.0], f"{STAT}_RANK": [2, 1, 2]})
    return misc, base, league


def test_nba_rank_uses_competition_ranking():
    league = pd.Series([500, 400, 400, 300])
    assert nba_rank(400, league) == 2
    assert nba_rank(350, league) == 4


def test_prepare_season_calculates_rate_share_and_rank():
    row = prepare_season("2010-11", *_frames()).iloc[0]
    assert row.points == 400
    assert row.points_per_game == 8.0
    assert row.share_of_points == 0.4
    assert row.nba_rank == 2
    assert row.nba_rank_endpoint == 2


def test_prepare_season_rejects_mismatched_player_sets():
    misc, base, league = _frames()
    base["PLAYER_ID"] = [9]
    with pytest.raises(ValueError, match="different Bulls players"):
        prepare_season("2010-11", misc, base, league)


def test_top15_breaks_ties_by_per_game_then_older_season():
    rows = [{"player_name": f"P{i}", "season": "2010-11", "player_id": i,
             "points": 900 - i, "points_per_game": 9.0} for i in range(14)]
    rows += [
        {"player_name": "Slower", "season": "2001-02", "player_id": 20, "points": 500, "points_per_game": 6.0},
        {"player_name": "Faster", "season": "2012-13", "player_id": 21, "points": 500, "points_per_game": 7.0},
    ]
    selected = select_top15(pd.DataFrame(rows))
    assert selected.iloc[-1].player_name == "Faster"
    assert list(selected.display_rank) == list(range(1, 16))
