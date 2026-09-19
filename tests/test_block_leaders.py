import pandas as pd

from scripts.prototypes.block_leaders_data import nba_rank, prepare_season, select_top15


def test_nba_rank_uses_competition_ranking():
    league = pd.Series([20, 12, 12, 9, 4])
    assert nba_rank(12, league) == 2
    assert nba_rank(10, league) == 4


def test_prepare_season_calculates_rate_and_rank():
    bulls = pd.DataFrame({
        "PLAYER_ID": [1], "PLAYER_NAME": ["Player"], "GP": [50], "BLK": [75]
    })
    league = pd.DataFrame({
        "PLAYER_ID": [1, 2, 3], "PLAYER_NAME": ["Player", "A", "B"],
        "GP": [50, 80, 70], "BLK": [75, 100, 75], "BLK_RANK": [2, 1, 2],
    })
    row = prepare_season("2025-26", bulls, league).iloc[0]
    assert row.blocks_per_game == 1.5
    assert row.nba_rank == 2
    assert row.league_full_season_blocks == 75
    assert row.nba_rank_endpoint == 2


def test_top15_breaks_cutoff_tie_with_blocks_per_game():
    rows = []
    for i in range(14):
        rows.append({"player_name": f"P{i}", "season": f"20{i:02d}-01", "blocks": 200 - i,
                     "blocks_per_game": 2.0, "player_id": i, "games": 80, "nba_rank": 1})
    rows.extend([
        {"player_name": "Chandler", "season": "2005-06", "blocks": 104,
         "blocks_per_game": 104 / 79, "player_id": 20, "games": 79, "nba_rank": 9},
        {"player_name": "Gibson", "season": "2009-10", "blocks": 104,
         "blocks_per_game": 104 / 82, "player_id": 21, "games": 82, "nba_rank": 9},
    ])
    selected = select_top15(pd.DataFrame(rows))
    assert selected.iloc[-1].player_name == "Chandler"
    assert "Gibson" not in set(selected.player_name)
