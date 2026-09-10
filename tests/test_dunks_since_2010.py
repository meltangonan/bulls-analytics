"""Tests for the since-2010 dunk-type leaderboards.

These guards protect the classification and ranking decisions that a PNG cannot
show: which ACTION_TYPE labels count on which slide, that a two-label dunk
lands on both matching boards, and that display ties never rewrite the total.
"""
from __future__ import annotations

import pandas as pd

from scripts.prototypes.dunks_since_2010 import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    SLIDES,
    SUPPORTING_STATS,
    TOP_N,
    display_name,
    display_season,
    is_dunk,
    rank_board,
    season_label,
    seasons,
)


def _slide(slug: str):
    return next(slide for slide in SLIDES if slide.slug == slug)


def test_is_dunk_accepts_nba_dunk_variants_only():
    assert is_dunk("Driving Dunk Shot")
    assert is_dunk("Running Alley Oop Dunk Shot")
    assert is_dunk("Tip Dunk Shot")
    assert is_dunk("Cutting Dunk Shot")
    assert not is_dunk("Driving Layup Shot")
    assert not is_dunk("Alley Oop Layup Shot")


def test_type_matchers_split_labels_without_dropping_hybrids():
    driving = _slide("driving")
    running = _slide("running")
    alley = _slide("alley-oop")
    putback = _slide("putback")
    total = _slide("total")

    assert driving.matches("Driving Reverse Dunk Shot")
    assert not running.matches("Driving Reverse Dunk Shot")
    assert running.matches("Running Alley Oop Dunk Shot")
    assert alley.matches("Running Alley Oop Dunk Shot")
    assert putback.matches("Tip Dunk Shot")
    assert putback.matches("Follow Up Dunk Shot")
    assert putback.matches("Putback Slam Dunk Shot")
    assert not putback.matches("Cutting Dunk Shot")
    assert not driving.matches("Dunk Shot")
    assert total.matches("Dunk Shot")
    assert total.matches("Cutting Dunk Shot")
    assert total.matches("Running Alley Oop Dunk Shot")


def test_season_window_is_2010_11_through_2025_26():
    labels = seasons()
    assert labels[0] == "2010-11"
    assert labels[-1] == "2025-26"
    assert len(labels) == LAST_SEASON_END_YEAR - FIRST_SEASON_END_YEAR + 1
    assert season_label(2011) == "2010-11"
    assert display_season("2013-14") == "2013–14"


def test_display_name_strips_generational_suffix():
    assert display_name("Jimmy Butler III") == "Jimmy Butler"
    assert display_name("Zach LaVine") == "Zach LaVine"


def _shots(rows: list[tuple[str, int, str, str, int]]) -> pd.DataFrame:
    """(season, player_id, name, action, made) -> dunk-attempt rows."""
    return pd.DataFrame(
        [
            {
                "season": season,
                "PLAYER_ID": pid,
                "PLAYER_NAME": name,
                "ACTION_TYPE": action,
                "SHOT_MADE_FLAG": made,
                "SHOT_ATTEMPTED_FLAG": 1,
                "GAME_ID": f"{season}-{pid}-{index}",
            }
            for index, (season, pid, name, action, made) in enumerate(rows)
        ]
    )


def _players(rows: list[tuple[str, int, str, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"season": season, "PLAYER_ID": pid, "PLAYER_NAME": name, "GP": gp}
            for season, pid, name, gp in rows
        ]
    )


def test_rank_board_counts_made_dunks_and_keeps_hybrids_on_both_slides():
    dunks = _shots(
        [
            ("2018-19", 1, "Zach LaVine", "Driving Dunk Shot", 1),
            ("2018-19", 1, "Zach LaVine", "Driving Dunk Shot", 1),
            ("2018-19", 1, "Zach LaVine", "Running Alley Oop Dunk Shot", 1),
            ("2015-16", 2, "Jimmy Butler III", "Alley Oop Dunk Shot", 1),
            ("2015-16", 2, "Jimmy Butler III", "Alley Oop Dunk Shot", 1),
            ("2015-16", 2, "Jimmy Butler III", "Alley Oop Dunk Shot", 1),
            ("2013-14", 3, "Taj Gibson", "Dunk Shot", 1),
            ("2019-20", 4, "Wendell Carter Jr.", "Putback Dunk Shot", 1),
            ("2019-20", 4, "Wendell Carter Jr.", "Tip Dunk Shot", 1),
            ("2019-20", 4, "Wendell Carter Jr.", "Follow Up Dunk Shot", 0),
        ]
    )
    players = _players(
        [
            ("2018-19", 1, "Zach LaVine", 63),
            ("2015-16", 2, "Jimmy Butler III", 67),
            ("2013-14", 3, "Taj Gibson", 82),
            ("2019-20", 4, "Wendell Carter Jr.", 43),
        ]
    )

    alley = rank_board(dunks, players, _slide("alley-oop"), top_n=2)
    assert list(alley["PLAYER_NAME"]) == ["Jimmy Butler III", "Zach LaVine"]
    assert list(alley["dunk_fgm"]) == [3, 1]
    assert alley.iloc[0]["display_name"] == "Jimmy Butler"

    running = rank_board(dunks, players, _slide("running"), top_n=1)
    assert int(running.iloc[0]["dunk_fgm"]) == 1
    assert running.iloc[0]["PLAYER_NAME"] == "Zach LaVine"

    putback = rank_board(dunks, players, _slide("putback"), top_n=1)
    assert int(putback.iloc[0]["dunk_fgm"]) == 2
    assert int(putback.iloc[0]["dunk_fga"]) == 3

    total = rank_board(dunks, players, _slide("total"), top_n=3)
    assert list(total["dunk_fgm"]) == [3, 3, 2]


def test_display_ties_break_on_rate_without_changing_the_count():
    dunks = _shots(
        [("2019-20", 1, "A", "Dunk Shot", 1)] * 8
        + [("2018-19", 2, "B", "Dunk Shot", 1)] * 8
        + [("2017-18", 3, "C", "Dunk Shot", 1)] * 7
    )
    players = _players(
        [
            ("2019-20", 1, "A", 40),
            ("2018-19", 2, "B", 80),
            ("2017-18", 3, "C", 70),
        ]
    )
    board = rank_board(dunks, players, _slide("total"), top_n=2)
    assert list(board["PLAYER_NAME"]) == ["A", "B"]
    assert list(board["dunk_fgm"]) == [8, 8]


def test_five_slides_and_ten_row_contract():
    assert [slide.slug for slide in SLIDES] == [
        "total",
        "driving",
        "running",
        "alley-oop",
        "putback",
    ]
    assert TOP_N == 10
    assert [label for label, _, _ in SUPPORTING_STATS] == ["ATT", "FG%", "GP", "/G"]
