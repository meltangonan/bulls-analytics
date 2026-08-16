import pandas as pd
import pytest

from scripts.prototypes.season_opener_performances import (
    rank_season_openers,
    season_opener_player_games,
    select_season_openers,
)


def test_select_season_openers_uses_first_team_game_not_first_player_row():
    games = pd.DataFrame(
        [
            {"season_end_year": 2022, "game_id": 2, "game_date": "2021-10-22", "matchup": "CHI vs. NOP", "result": "W"},
            {"season_end_year": 2022, "game_id": 1, "game_date": "2021-10-20", "matchup": "CHI @ DET", "result": "W"},
            {"season_end_year": 2023, "game_id": 4, "game_date": "2022-10-22", "matchup": "CHI vs. CLE", "result": "L"},
            {"season_end_year": 2023, "game_id": 3, "game_date": "2022-10-19", "matchup": "CHI @ MIA", "result": "W"},
        ]
    )
    result = select_season_openers(games)
    assert result["game_id"].astype(str).tolist() == ["1", "3"]


def test_season_opener_player_games_keeps_every_player_from_selected_games():
    working = pd.DataFrame(
        [
            {"season_end_year": 2022, "game_id": "1", "player_id": 10},
            {"season_end_year": 2022, "game_id": "1", "player_id": 11},
            {"season_end_year": 2022, "game_id": "2", "player_id": 12},
        ]
    )
    openers = pd.DataFrame([{"season_end_year": 2022, "game_id": 1}])
    result = season_opener_player_games(working, openers)
    assert result["player_id"].tolist() == [10, 11]


def test_rank_season_openers_uses_settled_tie_breaks():
    row_data = [
        {
            "game_score": 30.0,
            "points": 31,
            "ts_pct": 60.0,
            "game_date": "2021-10-20",
            "player": "Second",
            "player_id": 2,
        },
        {
            "game_score": 30.0,
            "points": 32,
            "ts_pct": 55.0,
            "game_date": "2022-10-19",
            "player": "First",
            "player_id": 1,
        },
    ]
    row_data.extend(
        {
                "game_score": 29.0 - index,
                "points": 20,
                "ts_pct": 50.0,
                "game_date": f"200{index}-10-20",
                "player": f"Player {index}",
                "player_id": index + 10,
            }
            for index in range(9)
    )
    rows = pd.DataFrame(row_data)
    result = rank_season_openers(rows)
    assert result.iloc[0]["player"] == "First"
    assert result["rank"].tolist() == list(range(1, 11))


def test_rank_season_openers_requires_the_full_top_ten():
    with pytest.raises(ValueError, match="Expected 10"):
        rank_season_openers(
            pd.DataFrame(
                [
                    {
                        "game_score": 1.0,
                        "points": 1,
                        "ts_pct": 1.0,
                        "game_date": "2022-10-19",
                        "player": "Only",
                        "player_id": 1,
                    }
                ]
            )
        )
