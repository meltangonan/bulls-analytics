import pandas as pd

from scripts.prototypes.game_score_by_height import (
    canonical_heights,
    display_height,
    game_score_fill,
    height_inches,
    select_height_winners,
)


def _game(player_id, player, score_inputs, date, minutes=30):
    row = {
        "player_id": player_id, "player": player, "game_date": date, "minutes": minutes,
        "points": 0, "fgm": 0, "fga": 0, "ftm": 0, "fta": 0, "oreb": 0,
        "dreb": 0, "ast": 0, "stl": 0, "blk": 0, "pf": 0, "tov": 0,
    }
    row.update(score_inputs)
    return row


def test_height_parser_and_display_are_exact():
    assert height_inches("5-10") == 70
    assert height_inches("7-2") == 86
    assert display_height("6-3") == "6′3″"


def test_game_score_colours_use_settled_explainer_bands_not_sample_minmax():
    assert game_score_fill(9.9) == "#D64545"
    assert game_score_fill(20.0) == "#E98B52"
    assert game_score_fill(30.0) == "#F2D46B"
    assert game_score_fill(40.0) == "#70AD5A"
    assert game_score_fill(50.0) == "#2F8F4E"


def test_canonical_height_uses_latest_roster_listing():
    rosters = pd.DataFrame([
        {"PLAYER_ID": 999999, "HEIGHT": "6-3", "SEASON": "2020-21"},
        {"PLAYER_ID": 999999, "HEIGHT": "6-4", "SEASON": "2021-22"},
    ])
    result = canonical_heights(rosters)
    assert result.loc[result.PLAYER_ID.eq(999999), "HEIGHT"].item() == "6-4"


def test_one_winner_per_height_combines_regular_season_and_playoffs():
    games = pd.DataFrame([
        _game(1, "Regular", {"points": 20, "fgm": 8, "fga": 16}, "2020-01-01"),
        _game(2, "Playoff", {"points": 30, "fgm": 12, "fga": 20}, "2020-05-01"),
        _game(3, "Tall", {"points": 10, "fgm": 4, "fga": 8}, "2020-02-01"),
    ])
    heights = pd.DataFrame({"PLAYER_ID": [1, 2, 3], "HEIGHT": ["6-3", "6-3", "7-0"]})
    result = select_height_winners(games, heights)
    assert result[["HEIGHT", "player"]].values.tolist() == [["6-3", "Playoff"], ["7-0", "Tall"]]
