"""Post-specific tests for the most-dunks-in-a-Bulls-season leaderboard.

The behaviour worth pinning here is the dunk definition itself: ACTION_TYPE
contains "dunk", makes only, Restricted Area not required, and
get_team_shots is not the source (it drops ACTION_TYPE).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from bulls.config import BULLS_TEAM_ID
from scripts.prototypes.most_dunks_season import (
    FIRST_SEASON,
    HERO_GAP,
    HERO_METRIC,
    KEEP,
    LAST_SEASON,
    STAT_COLUMNS,
    TABLE_ROWS,
    assert_season_coverage,
    cell_label,
    column_bounds,
    dunk_rows,
    fetch_season_shots,
    is_dunk,
    player_seasons,
    prepare_table,
    season_labels,
    season_marker,
    shot_made,
    summarize_season,
    validate,
)

SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "prototypes" / "most_dunks_season.py"
)


def _shot(
    *,
    season="2000-01",
    player_id=1,
    name="Dunker",
    game_id="0020000001",
    action="Driving Dunk Shot",
    made=1,
    zone="Restricted Area",
    team_id=BULLS_TEAM_ID,
    attempted=1,
):
    return {
        "SEASON": season,
        "GAME_ID": game_id,
        "PLAYER_ID": player_id,
        "PLAYER_NAME": name,
        "TEAM_ID": team_id,
        "ACTION_TYPE": action,
        "SHOT_MADE_FLAG": made,
        "SHOT_ATTEMPTED_FLAG": attempted,
        "SHOT_ZONE_BASIC": zone,
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Driving Dunk Shot", True),
        ("Alley Oop Dunk Shot", True),
        ("Putback Dunk Shot", True),
        ("Tip Dunk Shot", True),
        ("Reverse Dunk Shot", True),
        ("Cutting Dunk Shot", True),
        ("Running Dunk Shot", True),
        ("Dunk Shot", True),
        ("DUNK SHOT", True),
        ("Follow Up Dunk Shot", True),
        ("Layup Shot", False),
        ("Driving Finger Roll Layup Shot", False),
        ("Jump Shot", False),
        ("Turnaround Hook Shot", False),
        ("", False),
        (None, False),
    ],
)
def test_is_dunk_matches_every_labelled_variant(raw, expected):
    assert is_dunk(raw) is expected


def test_made_only_counting_ignores_missed_dunks_and_non_dunks():
    """Two made dunks, one missed dunk, one made layup → 2 makes, 3 attempts."""
    shots = pd.DataFrame(
        [
            _shot(action="Driving Dunk Shot", made=1, game_id="g1"),
            _shot(action="Alley Oop Dunk Shot", made=1, game_id="g2"),
            _shot(action="Dunk Shot", made=0, game_id="g3"),
            _shot(action="Layup Shot", made=1, game_id="g4"),
        ]
    )
    seasons = player_seasons(dunk_rows(shots))
    assert len(seasons) == 1
    assert int(seasons.iloc[0]["dunks_made"]) == 2
    assert int(seasons.iloc[0]["dunks_attempted"]) == 3
    assert int(seasons.iloc[0]["games"]) == 3


def test_restricted_area_is_not_required_to_count_a_dunk():
    """A dunk labelled In The Paint (Non-RA) still counts on this board."""
    shots = pd.DataFrame(
        [
            _shot(action="Driving Dunk Shot", made=1, zone="In The Paint (Non-RA)"),
            _shot(action="Dunk Shot", made=1, zone="Restricted Area"),
        ]
    )
    seasons = player_seasons(dunk_rows(shots))
    assert int(seasons.iloc[0]["dunks_made"]) == 2
    assert int(seasons.iloc[0]["restricted_area_makes"]) == 1
    assert int(seasons.iloc[0]["non_ra_makes"]) == 1


def test_shot_made_accepts_float_flags():
    frame = pd.DataFrame({"SHOT_MADE_FLAG": [1.0, 0.0, 1, 0]})
    assert list(shot_made(frame)) == [True, False, True, False]


def _nba_frame(rows: list[dict]) -> pd.DataFrame:
    """A ShotChartDetail-shaped frame, without the SEASON column we insert."""
    frame = pd.DataFrame(rows)
    return frame.drop(columns=["SEASON"])


@patch("scripts.prototypes.most_dunks_season.shotchartdetail.ShotChartDetail")
def test_fetch_season_shots_keeps_action_type_and_uses_team_fga_call(mock_cls):
    mock_cls.return_value.get_data_frames.return_value = [
        _nba_frame(
            [
                _shot(action="Driving Dunk Shot", made=1),
                _shot(action="Layup Shot", made=1, game_id="0020000002"),
            ]
        )
    ]
    frame = fetch_season_shots("2000-01")
    assert list(frame.columns)[:1] == ["SEASON"]
    assert "ACTION_TYPE" in frame.columns
    assert set(KEEP).issubset(frame.columns)
    assert frame["SEASON"].eq("2000-01").all()
    kwargs = mock_cls.call_args.kwargs
    assert kwargs["team_id"] == BULLS_TEAM_ID
    assert kwargs["player_id"] == 0
    assert kwargs["season_nullable"] == "2000-01"
    assert kwargs["season_type_all_star"] == "Regular Season"
    assert kwargs["context_measure_simple"] == "FGA"
    assert kwargs["headers"]["Referer"] == "https://www.nba.com/"


@patch("scripts.prototypes.most_dunks_season.shotchartdetail.ShotChartDetail")
def test_fetch_season_shots_rejects_an_empty_season(mock_cls):
    mock_cls.return_value.get_data_frames.return_value = [pd.DataFrame()]
    with pytest.raises(RuntimeError, match="empty frame"):
        fetch_season_shots("1995-96")


@patch("scripts.prototypes.most_dunks_season.shotchartdetail.ShotChartDetail")
def test_fetch_season_shots_rejects_a_non_bulls_row(mock_cls):
    mock_cls.return_value.get_data_frames.return_value = [
        _nba_frame([_shot(team_id=1610612744)])
    ]
    with pytest.raises(ValueError, match="non-Bulls TEAM_ID"):
        fetch_season_shots("2000-01")


def test_prototype_does_not_call_get_team_shots():
    """get_team_shots drops ACTION_TYPE; this post cannot use it as written."""
    source = SCRIPT.read_text()
    assert "get_team_shots(" not in source
    assert "get_team_shots" in source


def test_summarize_season_counts_fga_and_made_dunks():
    shots = pd.DataFrame(
        [
            _shot(action="Driving Dunk Shot", made=1),
            _shot(action="Dunk Shot", made=0, game_id="g2"),
            _shot(action="Layup Shot", made=1, game_id="g3"),
        ]
    )
    summary = summarize_season(shots)
    assert summary["total_fga"] == 3
    assert summary["dunk_attempts"] == 2
    assert summary["dunk_makes"] == 1


def test_ranking_breaks_a_tie_toward_fewer_attempts():
    """Equal made dunks rank by who needed fewer attempts, then recency."""
    shots = pd.DataFrame(
        [
            _shot(season="2020-21", player_id=1, name="Efficient",
                  action="Dunk Shot", made=1, game_id="a"),
            _shot(season="2020-21", player_id=1, name="Efficient",
                  action="Dunk Shot", made=1, game_id="b"),
            _shot(season="2010-11", player_id=2, name="Grinder",
                  action="Dunk Shot", made=1, game_id="c"),
            _shot(season="2010-11", player_id=2, name="Grinder",
                  action="Dunk Shot", made=1, game_id="d"),
            _shot(season="2010-11", player_id=2, name="Grinder",
                  action="Dunk Shot", made=0, game_id="e"),
        ]
    )
    # Pad to 15 rows so prepare_table's cut is defined.
    extra = []
    for i in range(13):
        extra.append(_shot(
            season="2001-02", player_id=100 + i, name=f"Filler {i}",
            action="Dunk Shot", made=1, game_id=f"f{i}",
        ))
    seasons = player_seasons(dunk_rows(pd.concat([shots, pd.DataFrame(extra)], ignore_index=True)))
    table = prepare_table(seasons)
    assert list(table["PLAYER_NAME"])[:2] == ["Efficient", "Grinder"]
    assert int(table.iloc[0]["dunks_attempted"]) == 2
    assert int(table.iloc[1]["dunks_attempted"]) == 3


def test_a_cut_inside_a_tie_is_rejected():
    rows = []
    for i in range(16):
        rows.append(_shot(
            season="2000-01", player_id=i, name=f"Same {i}",
            action="Dunk Shot", made=1, game_id=str(i),
        ))
    seasons = player_seasons(dunk_rows(pd.DataFrame(rows)))
    with pytest.raises(ValueError, match="tie at 1"):
        prepare_table(seasons)


def test_assert_season_coverage_rejects_a_missing_season():
    audit = pd.DataFrame(
        [{"SEASON": season, "total_fga": 5000} for season in season_labels()[:-1]]
    )
    with pytest.raises(ValueError, match="does not cover"):
        assert_season_coverage(audit)


def test_assert_season_coverage_rejects_a_zero_fga_season():
    audit = pd.DataFrame(
        [{"SEASON": season, "total_fga": 0 if season == "2000-01" else 5000}
         for season in season_labels()]
    )
    with pytest.raises(ValueError, match="zero field-goal attempts"):
        assert_season_coverage(audit)


def _filled_table() -> pd.DataFrame:
    rows = []
    for i in range(TABLE_ROWS):
        made = 200 - i
        attempted = made + 5
        rows.append(
            {
                "SEASON": "2024-25" if i == 0 else "2000-01",
                "PLAYER_ID": i,
                "PLAYER_NAME": f"Player {i}",
                "dunks_made": made,
                "dunks_attempted": attempted,
                "games": 70,
                "fg_pct": made / attempted,
                "restricted_area_makes": made,
                "non_ra_makes": 0,
            }
        )
    return pd.DataFrame(rows)


def test_validate_catches_a_percentage_that_stopped_reconciling():
    table = _filled_table()
    table.loc[0, "fg_pct"] = 0.5
    audit = pd.DataFrame([{"SEASON": s, "total_fga": 100, "dunk_makes": 10} for s in season_labels()])
    with pytest.raises(ValueError, match="FG%"):
        validate(table, audit)


def test_cell_label_prints_whole_percent_and_counts():
    row = pd.Series({"dunks_made": 182, "dunks_attempted": 241, "fg_pct": 182 / 241, "games": 70})
    assert cell_label(row, "dunks_made") == "182"
    assert cell_label(row, "dunks_attempted") == "241"
    assert cell_label(row, "games") == "70"
    assert cell_label(row, "fg_pct") == "76%"


def test_season_marker_compacts_to_two_digit_years():
    assert season_marker("2023-24") == "23\N{EN DASH}24"


def test_columns_are_ordered_and_the_hero_has_a_gap():
    bounds = column_bounds(400.0)
    assert list(bounds) == [metric for metric, _, _ in STAT_COLUMNS]
    order = [metric for metric, _, _ in STAT_COLUMNS]
    for before, after in zip(order, order[1:]):
        gap = bounds[after][0] - bounds[before][1]
        assert gap == pytest.approx(HERO_GAP if before == HERO_METRIC else 0.0)


def test_the_table_is_exactly_the_agreed_depth():
    assert TABLE_ROWS == 15


def test_the_window_starts_where_the_headline_says():
    """2000-01 is a choice; the shot-location floor is 1996-97 (DEVELOPMENT.md)."""
    assert FIRST_SEASON == 2000
    assert LAST_SEASON == 2025
    assert season_labels()[0] == "2000-01"
    assert season_labels()[-1] == "2025-26"


def test_no_games_played_floor_on_v1():
    """A 10-game stint with enough dunks still ranks; totals are the claim."""
    shots = []
    shots.append(_shot(season="2024-25", player_id=1, name="Short", made=1, game_id="s1"))
    for g in range(9):
        shots.append(_shot(season="2024-25", player_id=1, name="Short", made=1, game_id=f"s{g+2}"))
    for i in range(14):
        shots.append(_shot(
            season="2001-02", player_id=10 + i, name=f"Filler {i}",
            made=1, game_id=f"f{i}",
        ))
    table = prepare_table(player_seasons(dunk_rows(pd.DataFrame(shots))))
    assert table.iloc[0]["PLAYER_NAME"] == "Short"
    assert int(table.iloc[0]["games"]) == 10
