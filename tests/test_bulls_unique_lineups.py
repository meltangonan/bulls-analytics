from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes import bulls_unique_lineups as lineups


def test_minute_floor_counts_a_lineup_at_exactly_the_floor():
    counts = lineups.lineup_counts(pd.Series([0.0, 2.99, 3.0, 12.5]))

    assert counts["Played"] == 3
    assert counts["Min3"] == 2
    assert counts["Min10"] == 1


def test_every_season_reconciles_and_matches_the_published_table():
    table = lineups.sensitivity_table()
    published = pd.read_csv(lineups.DATA / "bulls-unique-lineups-by-floor.csv")

    assert list(table["Season"]) == [lineups.season_label(y) for y in range(2000, 2026)]
    pd.testing.assert_frame_equal(table, published, check_dtype=False)


def test_2025_26_is_the_most_lineups_at_three_minutes():
    table = lineups.sensitivity_table().set_index("Season")["Min3"]

    assert table["2025-26"] == 343
    assert table.drop("2025-26").max() == 306


def test_both_sources_agree_at_the_selected_floor_where_they_overlap():
    overlap = lineups.source_overlap_table()
    floor = lineups.SELECTED_FLOOR

    assert len(overlap) >= 8
    assert (overlap[f"pbpstats{floor}Min"] == overlap[f"NBA.com{floor}Min"]).all()
    assert (overlap["NbaOnlyMaxMinutes"] < floor).all()


def test_records_cover_every_season_and_rejects_a_missing_one():
    table = lineups.sensitivity_table()[["Season", "Min3"]]
    merged = lineups.with_records(table)

    assert merged.set_index("Season").loc["2025-26", ["W", "L"]].tolist() == [31, 51]
    with pytest.raises(ValueError, match="no win-loss record"):
        lineups.with_records(pd.concat([table, pd.DataFrame([{"Season": "2026-27", "Min3": 1}])]))
