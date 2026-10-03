import pandas as pd

from scripts.prototypes.preseason_performances import rank_preseason


def test_rank_preseason_breaks_equal_game_scores_by_points_despite_float_noise():
    rows = pd.DataFrame(
        [
            {"player": "Joakim Noah", "player_id": 1, "game_score": 23.800000000000004, "points": 20,
             "ts_pct": 62.7, "game_date": "2009-10-13"},
            {"player": "Carlos Boozer", "player_id": 2, "game_score": 23.8, "points": 24,
             "ts_pct": 61.1, "game_date": "2012-10-19"},
        ]
    )
    ranked = rank_preseason(rows, top_n=2)
    assert ranked["player"].tolist() == ["Carlos Boozer", "Joakim Noah"]
    assert ranked["rank"].tolist() == [1, 2]
