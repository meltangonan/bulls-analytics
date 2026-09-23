import pandas as pd
import pytest

from scripts.prototypes import points_in_a_period_bars as bars
from scripts.prototypes import points_in_a_period_data as data

LABELS = {"h1": "1H", "h2": "2H", "q1": "1Q", "q2": "2Q", "q3": "3Q", "q4": "4Q"}


def wide(points: list[int], season_type: str = "Regular Season") -> pd.DataFrame:
    """Player-games whose whole game is one 4th quarter of the given points."""
    rows = []
    for i, pts in enumerate(points):
        row = {"season": "2020-21", "season_type": season_type, "GAME_ID": 22000001 + i,
               "PLAYER_ID": 100 + i, "PLAYER_NAME": f"P{i}", "GAME_DATE": f"2021-01-{i + 1:02d}",
               "MATCHUP": "CHI vs. NYK", "WL": "W"}
        for stat in data.STATS:
            row[stat] = 0
        row.update(PTS=pts, FGM=pts // 2, FGA=pts)
        for split in [s for s in data.SPLITS if s != "full"]:
            for stat in data.STATS:
                row[f"{split}_{stat}"] = row[stat] if split in ("q4", "h2") else 0
            row[f"{split}_played"] = split in ("q4", "h2")
        rows.append(row)
    return pd.DataFrame(rows)


def test_reconcile_rejects_a_split_that_does_not_sum_to_the_game():
    frame = wide([20])
    data.reconcile(frame)
    frame.loc[0, "q4_PTS"] = 19
    with pytest.raises(ValueError, match="q3\\+q4=h2"):
        data.reconcile(frame)


def test_ties_with_tenth_are_kept_and_share_a_rank():
    top = data.leaderboard(wide([30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 21, 21]), ["q4"], LABELS)
    assert len(top) == 12
    assert top["rank"].tolist()[-3:] == [10, 10, 10] and top.tied.tolist()[-3:] == [True] * 3


def test_a_tie_past_the_row_cap_stops_the_board_above_it():
    points = [40, 39, 38, 37, 36, 35, 34, 33] + [20] * (data.MAX_ROWS)
    top = data.leaderboard(wide(points), ["q4"], LABELS)
    assert len(top) == 8 and top.pts.min() == 33


def test_quarter_board_excludes_play_in_and_half_board_includes_it():
    assert data.BOARDS["quarter"][1] == ["Regular Season", "Playoffs"]
    assert "PlayIn" in data.BOARDS["half"][1]


@pytest.mark.parametrize("season_type, game_id, marker", [
    ("Regular Season", 22300723, "W"),
    ("Playoffs", 41200134, "W*"),
    ("PlayIn", 52200111, "W*"),
])
def test_non_regular_season_games_carry_an_asterisk(season_type, game_id, marker):
    row = pd.Series({"game_date": "2023-04-12", "home": False, "opponent": "TOR", "split_label": "2H",
                     "season_type": season_type, "game_id": game_id, "result": "W",
                     "player_name": "P"})
    assert bars.game_segments(row)[-1][0] == marker


def test_game_id_must_match_season_type():
    row = pd.Series({"game_date": "2023-04-12", "home": False, "opponent": "TOR", "split_label": "2H",
                     "season_type": "Playoffs", "game_id": 52200111, "result": "W", "player_name": "P"})
    with pytest.raises(ValueError, match="disagree"):
        bars.game_segments(row)
