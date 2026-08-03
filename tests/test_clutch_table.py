"""Post-specific tests for the current-roster clutch table."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from scripts.prototypes.clutch_table import (
    COLUMNS,
    FIRST_ROW_Y,
    MIN_CLUTCH_GAMES,
    ROW_HEIGHT,
    build_working_table,
    canva_copy_block,
    fg_fill,
    minutes_fill,
    points_fill,
    points_card_bounds,
    qualified_players,
    validate_working_table,
    win_fill,
)


def _roster() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"nba_id": 1, "official_roster_name": "Tre Jones"},
            {"nba_id": 2, "official_roster_name": "Norman Powell"},
            {"nba_id": 3, "official_roster_name": "Leonard Miller"},
            {"nba_id": 4, "official_roster_name": "Caleb Wilson"},
        ]
    )


def _clutch() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "PLAYER_ID": 1,
                "PLAYER_NAME": "Tre Jones",
                "TEAM_ABBREVIATION": "CHI",
                "GP": 12,
                "W": 7,
                "L": 5,
                "MIN": 45.4,
                "PTS": 30,
                "FGM": 11,
                "FGA": 20,
                "FTA": 10,
            },
            {
                "PLAYER_ID": 2,
                "PLAYER_NAME": "Norman Powell",
                "TEAM_ABBREVIATION": "MIA",
                "GP": 10,
                "W": 5,
                "L": 5,
                "MIN": 30.2,
                "PTS": 20,
                "FGM": 7,
                "FGA": 15,
                "FTA": 4,
            },
            {
                "PLAYER_ID": 3,
                "PLAYER_NAME": "Leonard Miller",
                "TEAM_ABBREVIATION": "CHI",
                "GP": 6,
                "W": 2,
                "L": 4,
                "MIN": 18.5,
                "PTS": 7,
                "FGM": 2,
                "FGA": 6,
                "FTA": 2,
            },
        ]
    )


def _table() -> pd.DataFrame:
    return build_working_table(
        _roster(),
        _clutch(),
        datetime(2026, 8, 2, 12, tzinfo=ZoneInfo("America/Chicago")),
    )


def test_joins_current_roster_to_full_season_team_context():
    table = _table()
    powell = table.loc[
        table["official_roster_name"] == "Norman Powell"
    ].iloc[0]

    assert powell["season_team_field"] == "MIA"
    assert powell["clutch_points"] == 20


def test_league_clutch_ts_is_weighted_from_all_player_totals():
    table = _table()
    expected = _clutch()["PTS"].sum() / (
        2 * (_clutch()["FGA"].sum() + 0.44 * _clutch()["FTA"].sum())
    )

    assert table["league_clutch_ts_pct"].nunique() == 1
    assert table["league_clutch_ts_pct"].iloc[0] == pytest.approx(expected)


def test_league_clutch_fg_is_weighted_from_all_player_totals():
    table = _table()
    expected = _clutch()["FGM"].sum() / _clutch()["FGA"].sum()

    assert table["league_clutch_fg_pct"].nunique() == 1
    assert table["league_clutch_fg_pct"].iloc[0] == pytest.approx(expected)


def test_ten_game_qualification_is_inclusive():
    powell = _table().loc[
        _table()["official_roster_name"] == "Norman Powell"
    ].iloc[0]

    assert powell["clutch_games"] == MIN_CLUTCH_GAMES
    assert bool(powell["qualified"])


def test_qualifiers_are_ranked_by_points_then_minutes():
    players = qualified_players(_table())

    assert players["official_roster_name"].tolist() == [
        "Tre Jones",
        "Norman Powell",
    ]
    assert players["clutch_points"].is_monotonic_decreasing


def test_shooting_and_win_rate_reconcile_to_raw_totals():
    table = _table()
    tre = table.loc[table["official_roster_name"] == "Tre Jones"].iloc[0]
    expected_ts = 30 / (2 * (20 + 0.44 * 10))

    assert tre["ts_pct"] == pytest.approx(expected_ts)
    assert tre["relative_ts_pp"] == pytest.approx(
        (expected_ts - tre["league_clutch_ts_pct"]) * 100
    )
    assert tre["fg_pct"] == pytest.approx(11 / 20)
    assert tre["win_pct"] == pytest.approx(7 / 12)


def test_records_must_reconcile_to_clutch_games():
    table = _table()
    table.loc[table["official_roster_name"] == "Tre Jones", "clutch_wins"] = 8

    with pytest.raises(ValueError, match="do not reconcile"):
        validate_working_table(table)


def test_low_sample_and_no_data_players_remain_auditable():
    report = validate_working_table(_table())

    assert report["qualified_names"] == ["Tre Jones", "Norman Powell"]
    assert report["below_threshold_names"] == ["Leonard Miller"]
    assert report["no_2025_26_clutch_data_names"] == ["Caleb Wilson"]


def test_cell_fills_use_red_green_only_for_directional_metrics():
    positive = fg_fill(0.55, 0.45)
    negative = fg_fill(0.35, 0.45)
    high_win = win_fill(0.75)
    low_win = win_fill(0.25)
    minutes = minutes_fill(50, 100)
    high_points = points_fill(60, 10, 60)
    low_points = points_fill(10, 10, 60)

    assert positive[1] > positive[0]
    assert negative[0] > negative[1]
    assert high_win[1] > high_win[0]
    assert low_win[0] > low_win[1]
    assert minutes == pytest.approx(minutes_fill(5, 100))
    assert high_points[0] - high_points[1] > low_points[0] - low_points[1]


def test_columns_put_minutes_before_directional_context():
    assert list(COLUMNS) == ["PTS", "MIN", "FG", "WIN%"]


def test_points_card_intentionally_overlaps_the_table_footprint():
    left, right, bottom, top = points_card_bounds(8)

    assert left < COLUMNS["PTS"][0]
    assert right > COLUMNS["PTS"][1]
    assert top > FIRST_ROW_Y + ROW_HEIGHT / 2
    assert bottom < FIRST_ROW_Y - 7 * ROW_HEIGHT - ROW_HEIGHT / 2


def test_copy_block_carries_definitions_scope_and_caveat():
    copy = canva_copy_block(validate_working_table(_table()), "2026-08-02")

    assert "10+ clutch appearances" in copy
    assert "Full-season totals across all teams" in copy
    assert "FG = clutch field goals made–attempted" in copy
    assert "cell color compares FG% to the NBA clutch average" in copy
    assert "WIN% = team win rate" in copy
    assert "Clutch shooting samples are small" in copy
    assert "FGM–FGA makes the shooting sample visible" in copy
    assert "Current roster as of 2026-08-02" in copy


def test_chart_export_is_transparent_and_places_every_headshot(
    tmp_path, monkeypatch
):
    from PIL import Image

    import scripts.prototypes.clutch_table as clutch_table

    placements = []

    def record_headshot(ax, image_path, x, y, half_size, **kwargs):
        placements.append((image_path.stem, x, y, half_size))

    monkeypatch.setattr(clutch_table, "OUT", tmp_path)
    monkeypatch.setattr(clutch_table, "square_headshot_label", record_headshot)
    path = clutch_table.render_chart(
        qualified_players(_table()),
        "2026-08-02",
        final=False,
    )

    image = Image.open(path)
    assert image.mode == "RGBA"
    assert image.size == (1080, 1110)
    assert image.getpixel((0, 0))[3] == 0
    assert [placement[0] for placement in placements] == ["1", "2"]
