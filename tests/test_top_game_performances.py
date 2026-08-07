import pandas as pd
import pytest

from scripts.prototypes.top_game_performances import (
    DEFAULT_THEME,
    GAME_SCORE_FILL,
    decade_for_end_year,
    game_score,
    player_source_url,
    season_type_slug,
    slide_height,
    team_source_url,
    top_games_by_decade,
    true_shooting_pct,
)


def _box(**overrides):
    values = {
        "points": 30,
        "fgm": 10,
        "fga": 20,
        "ftm": 5,
        "fta": 6,
        "oreb": 3,
        "dreb": 5,
        "ast": 4,
        "stl": 2,
        "blk": 1,
        "pf": 3,
        "tov": 2,
    }
    values.update(overrides)
    return pd.Series(values)


def test_game_score_uses_the_settled_hollinger_formula():
    row = _box()
    expected = (
        30
        + 0.4 * 10
        - 0.7 * 20
        - 0.4 * (6 - 5)
        + 0.7 * 3
        + 0.3 * 5
        + 2
        + 0.7 * 4
        + 0.7 * 1
        - 0.4 * 3
        - 2
    )
    assert game_score(row) == pytest.approx(expected)


def test_true_shooting_pct_handles_free_throws():
    row = _box(points=30, fga=20, fta=6)
    assert true_shooting_pct(row) == pytest.approx(30 / (2 * (20 + 0.44 * 6)) * 100)


def test_true_shooting_pct_is_zero_without_shot_attempts():
    assert true_shooting_pct(_box(points=0, fga=0, fta=0)) == 0.0


def test_decade_mapping_uses_nba_season_end_years():
    assert decade_for_end_year(2001) == "2000s"
    assert decade_for_end_year(2011) == "2010s"
    assert decade_for_end_year(2021) == "2020s"
    with pytest.raises(ValueError):
        decade_for_end_year(2000)


def test_source_urls_can_switch_to_playoffs_without_reusing_regular_season_urls():
    assert season_type_slug("Playoffs") == "playoffs"
    assert "SeasonType=Playoffs" in player_source_url(2022, "Playoffs")
    assert "SeasonType=Playoffs" in team_source_url(2022, "Playoffs")
    assert "SeasonType=Regular%20Season" in player_source_url(2022)


def test_game_score_uses_one_solid_bulls_red_fill():
    assert GAME_SCORE_FILL == DEFAULT_THEME.accent


def test_ten_row_table_uses_the_taller_row_spacing():
    assert slide_height(10) == 1270


def test_top_games_keeps_only_ten_rows_and_breaks_ties_deterministically():
    rows = []
    for index in range(11):
        rows.append(
            {
                "decade": "2000s",
                "game_score": 40.0 if index < 2 else 39.0 - index,
                "points": 30,
                "ts_pct": 60.0,
                "game_date": f"200{index}-01-01",
                "player": f"Player {index:02d}",
                "player_id": index,
            }
        )
    rows.extend(
        [
            {
                "decade": "2010s",
                "game_score": 50.0,
                "points": 50,
                "ts_pct": 70.0,
                "game_date": "2012-01-01",
                "player": "Rose",
                "player_id": 100,
            },
            {
                "decade": "2020s",
                "game_score": 45.0,
                "points": 45,
                "ts_pct": 68.0,
                "game_date": "2022-01-01",
                "player": "LaVine",
                "player_id": 200,
            },
        ]
    )
    result = top_games_by_decade(pd.DataFrame(rows))
    assert result.groupby("decade").size().to_dict() == {"2000s": 10, "2010s": 1, "2020s": 1}
    assert result.loc[result["decade"].eq("2000s"), "player"].iloc[:2].tolist() == [
        "Player 00",
        "Player 01",
    ]
    assert result.loc[result["decade"].eq("2000s"), "rank"].tolist() == list(range(1, 11))
