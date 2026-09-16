import pandas as pd
import pytest

from scripts.prototypes import drive_leaders_data as data
from scripts.prototypes import drive_leaders_table as table


def sample() -> pd.DataFrame:
    return pd.DataFrame({
        "PLAYER_ID": [1], "PLAYER_NAME": ["Player One"], "TEAM_ID": [data.BULLS],
        "GP": [10], "DRIVES": [100], "DRIVE_FGM": [20], "DRIVE_FGA": [40],
        "DRIVE_FG_PCT": [.5], "DRIVE_FTM": [8], "DRIVE_FTA": [10],
        "DRIVE_PTS": [50], "DRIVE_PTS_PCT": [.5], "DRIVE_PASSES": [45],
        "DRIVE_PASSES_PCT": [.45], "DRIVE_AST": [12], "DRIVE_AST_PCT": [.12],
        "DRIVE_TOV": [5], "DRIVE_TOV_PCT": [.05], "DRIVE_PF": [9],
        "DRIVE_PF_PCT": [.09],
    })


def test_drive_point_residual_is_preserved_without_calling_it_threes():
    got = data.validate_rows(sample())
    assert got.DRIVE_POINTS_RESIDUAL.iloc[0] == 2


def test_negative_drive_point_residual_is_retained_for_audit():
    frame = sample(); frame.loc[0, "DRIVE_PTS"] = 45
    got = data.validate_rows(frame)
    assert got.DRIVE_POINTS_RESIDUAL.iloc[0] == -3


def test_ranked_uses_metric_then_drive_volume():
    frame = pd.DataFrame({"drive_pts": [10, 10, 8], "drives": [50, 60, 90],
                          "season": ["2020-21"]*3, "player_id": [1, 2, 3]})
    got = data.ranked(frame, "drive_pts")
    assert got.player_id.tolist() == [2, 1, 3]
    assert got["rank"].tolist() == [1, 2, 3]


def test_display_formats_each_table_unit():
    row = pd.Series({"drive_fgm": 20, "drive_fga": 40, "drive_fg_pct": 50.04,
                     "drive_shot_pct": 40.04, "drives_per_game": 10.04,
                     "drive_ast_pct": 16.66,
                     "drive_pts": 50})
    assert table.display(row, "fg") == "20–40"
    assert table.display(row, "drive_fg_pct") == "50.0%"
    assert table.display(row, "drive_shot_pct") == "40.0%"
    assert table.display(row, "drives_per_game") == "10.0"
    assert table.display(row, "drive_ast_pct") == "16.7%"
    assert table.display(row, "drive_pts") == "50"
