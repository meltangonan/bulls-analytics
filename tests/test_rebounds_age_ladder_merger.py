"""Tests for the merger-era rebound ladder scope and card treatment."""

from __future__ import annotations

import pandas as pd

from scripts.prototypes.rebounds_age_ladder_merger import (
    HYBRID_ROWS_TALL,
    MERGER_FIRST_SEASON_END_YEAR,
    build_merger_rows,
    fetch_team_year_by_year,
)


def test_merger_source_starts_with_1976_77():
    assert MERGER_FIRST_SEASON_END_YEAR == 1977


def test_team_year_source_covers_the_full_merger_window():
    team = fetch_team_year_by_year()
    years = team["YEAR"].astype(str)
    assert "1976-77" in years.tolist()
    assert "2025-26" in years.tolist()


def test_merger_rows_use_player_career_rebounds_and_team_schedule():
    rows = build_merger_rows(fetch_team_year_by_year())
    assert rows["season_end_year"].min() == 1977
    assert rows["season_end_year"].max() == 2026
    assert rows["rebounds"].eq(
        rows["offensive_rebounds"] + rows["defensive_rebounds"]
    ).all()
    assert rows["team_games"].gt(0).all()


def test_merger_winners_keep_the_extra_age_43_row():
    winners = pd.read_csv(
        "docs/visuals/2026-08-27-rebounds-age-ladder/data/"
        "bulls-rebounds-age-ladder-since-merger-winners.csv"
    )
    assert len(winners) == 21
    assert winners["age"].min() == 19
    assert winners["age"].max() == 43
    assert int(winners.loc[winners["age"].eq(43), "player_id"].item()) == 305


def test_hybrid_split_has_room_for_the_complete_first_page():
    assert HYBRID_ROWS_TALL == 11
