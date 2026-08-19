"""Tests for the chronological 300-minute Bulls rookie table."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.bulls_rookie_chronological_table import (
    HEAT_GREEN,
    HEAT_RED,
    HEAT_MID,
    MIN_TRANSPARENT_FRACTION,
    PAGE_ROW_COUNTS,
    PAGE_SEASON_RANGES,
    ROW_HEIGHT,
    COLUMN_SCALES,
    ERA_RELATIVE_METRICS,
    SHADED_METRICS,
    STAT_COLUMNS,
    SILHOUETTE_PATH,
    STAT_COLUMNS,
    HEADSHOT_HALF_SIZE,
    background_removed,
    column_bounds,
    draft_caption,
    draft_label,
    headshot_clip_bounds,
    heat_fill,
    heat_scales,
    portrait_path,
    prepare_table,
    season_marker,
    slide_height,
    split_pages,
)
from bulls.graphics.house import DEFAULT_THEME
from matplotlib.colors import to_rgb


def test_draft_label_uses_overall_pick_and_udfa():
    assert draft_label("1") == "PK1"
    assert draft_label("38") == "PK38"
    assert draft_label("Undrafted") == "UDFA"
    with pytest.raises(ValueError, match="Unrecognized"):
        draft_label("Second round")


def test_draft_caption_carries_the_year_of_the_players_own_draft():
    assert draft_caption(2008, "1") == "2008, #1 pick"
    assert draft_caption(2004, "38") == "2004, #38 pick"
    # The draft year is not the rookie season: Tarlac was a 1995 pick who first
    # played in 2000-01, and that gap is worth showing.
    assert draft_caption(1995, "31") == "1995, #31 pick"
    # NBA.com stores "Undrafted" in the year field too, so there is no year to
    # print. Guessing one would invent a fact the source does not hold.
    assert draft_caption("Undrafted", "Undrafted") == "Undrafted"


def test_season_marker_matches_recent_superscript_table_style():
    assert season_marker("2000-01") == "00–01"
    assert season_marker("2025-26") == "25–26"


def test_prepare_table_calculates_per_game_stats_and_orders_chronologically():
    rows = []
    draft_rows = []
    for index in range(46):
        season = 2001 + min(index, 25)
        rows.append(
            {
                "season": season,
                "season_label": f"{season - 1}-{str(season)[2:]}",
                "player_id": index,
                "player_name": f"Player {index}",
                "games": 30,
                "minutes": 300 + index,
                "points": 300,
                "rebounds": 150,
                "assists": 90,
                "steals": 30,
                "blocks": 15,
                "turnovers": 60,
                "field_goal_attempts": 300,
                "free_throw_attempts": 100,
                "net_rating": 0.0,
                "ts_pct": 0.55,
                "ws": 1.0,
                "bpm": 0.0,
            }
        )
        draft_rows.append(
            {
                "player_id": index,
                "draft_year": str(season - 1),
                "draft_round": "1",
                "draft_number": "Undrafted" if index == 0 else str(index),
            }
        )
    table = prepare_table(pd.DataFrame(rows), pd.DataFrame(draft_rows))
    assert len(table) == 46
    oldest = table.loc[table["player_id"] == 0].iloc[0]
    assert oldest["draft_label"] == "UDFA"
    assert oldest["draft_caption"] == "Undrafted"
    assert oldest["ppg"] == 10
    assert oldest["tov_per_game"] == 2
    # Still derived into the working CSV even though it is no longer a column.
    assert oldest["tov_pct"] == pytest.approx(60 / (300 + 0.44 * 100 + 60) * 100)
    assert oldest["spg"] == 1
    assert oldest["bpg"] == 0.5
    assert "stocks_per_game" not in table.columns
    assert table["season"].is_monotonic_decreasing


def test_split_pages_runs_newest_first_on_settled_season_boundaries():
    rows = []
    for season, count in ((2026, 16), (2015, 17), (2004, 13)):
        rows.extend({"season": season, "player_id": len(rows) + i} for i in range(count))
    pages = split_pages(pd.DataFrame(rows))
    assert tuple(len(page) for page in pages) == PAGE_ROW_COUNTS
    assert [page["season"].max() for page in pages] == [2026, 2015, 2004]


def test_every_slide_gets_one_identical_canvas():
    heights = {slide_height(count) for count in PAGE_ROW_COUNTS}
    assert len(heights) == 1
    assert heights == {slide_height(max(PAGE_ROW_COUNTS))}


def test_every_statistic_column_is_the_same_width():
    columns = column_bounds(320)
    widths = [right - left for left, right, _ in columns.values()]
    assert len(columns) == len(STAT_COLUMNS)
    assert widths == pytest.approx([widths[0]] * len(widths))
    assert min(left for left, _, _ in columns.values()) == 320


def test_portrait_without_a_removed_background_falls_back_to_the_silhouette(tmp_path):
    from PIL import Image
    import numpy as np

    flat = tmp_path / "flat.png"
    Image.fromarray(np.full((40, 40, 4), 255, dtype=np.uint8)).save(flat)
    assert background_removed(flat) is False

    cut_out = tmp_path / "cutout.png"
    pixels = np.full((40, 40, 4), 255, dtype=np.uint8)
    pixels[:20, :, 3] = 0
    Image.fromarray(pixels).save(cut_out)
    assert background_removed(cut_out) is True
    assert 0.0 < MIN_TRANSPARENT_FRACTION < 0.5


def test_portrait_path_returns_the_silhouette_for_a_player_with_no_portrait():
    assert portrait_path(-1) == SILHOUETTE_PATH


def test_red_white_green_scale_leaves_the_whole_neutral_band_unhighlighted():
    scale = (0, 4, 6, 10)
    assert heat_fill(0, *scale) == pytest.approx(to_rgb(HEAT_RED))
    assert heat_fill(10, *scale) == pytest.approx(to_rgb(HEAT_GREEN))
    # Every value inside the band is blank, not just the exact midpoint.
    for value in (4, 4.5, 5, 5.5, 6):
        assert heat_fill(value, *scale) == pytest.approx(to_rgb(HEAT_MID))
    # An average cell shows nothing, because the midpoint is the page itself.
    assert to_rgb(HEAT_MID) == pytest.approx(to_rgb(DEFAULT_THEME.canvas))


def test_true_shooting_leaves_the_middle_half_of_rookies_blank():
    scale = COLUMN_SCALES["ts_pct"]
    red_at, n_low, n_high, green_at = scale
    assert red_at < n_low < 0 < n_high < green_at
    assert "ts_pct" in ERA_RELATIVE_METRICS
    # Slightly below league average is ordinary for a rookie, so it is blank.
    for relative in (-6.0, -3.0, 0.0, 0.5):
        assert heat_fill(relative, *scale) == pytest.approx(to_rgb(HEAT_MID))
    assert heat_fill(-12.0, *scale) == pytest.approx(to_rgb(HEAT_RED))
    assert heat_fill(6.0, *scale) == pytest.approx(to_rgb(HEAT_GREEN))


def test_win_shares_is_no_longer_a_column():
    assert "ws" not in dict(STAT_COLUMNS)
    assert "ws" not in SHADED_METRICS
    assert "ws" not in COLUMN_SCALES


def test_impact_column_is_anchored_on_zero_so_a_negative_never_reads_green():
    assert "bpm" not in SHADED_METRICS
    assert "tov_per_game" not in dict(STAT_COLUMNS)
    assert dict(STAT_COLUMNS)["impact"] == "ON/OFF"
    assert "tov_pct" not in dict(STAT_COLUMNS), "TOV% was cut to quieten the table"
    assert "tov_pct" not in COLUMN_SCALES
    red_at, n_low, n_high, green_at = COLUMN_SCALES["impact"]
    assert n_low == -n_high, "the band stays centred on zero"
    assert red_at == -green_at
    assert heat_fill(-6.0, *COLUMN_SCALES["impact"]) != pytest.approx(to_rgb(HEAT_GREEN))


def test_counting_columns_only_colour_a_standout_rookie_season():
    """The complaint was 1.8 assists reading green. Neutral is the 75th."""
    for metric, unremarkable in (
        ("ppg", 7.0), ("rpg", 3.4), ("apg", 1.8), ("spg", 0.6), ("bpg", 0.4)
    ):
        assert heat_fill(unremarkable, *COLUMN_SCALES[metric]) == pytest.approx(
            to_rgb(HEAT_MID)
        ), f"{metric} still colours {unremarkable}"


def test_a_low_counting_stat_is_uncolored_rather_than_red():
    """A guard with 0.1 blocks has a role, not a failure. Do not paint it red."""
    for metric in ("ppg", "rpg", "apg", "spg", "bpg"):
        red_at, n_low, n_high, green_at = COLUMN_SCALES[metric]
        assert red_at == n_low == n_high, f"{metric} should be sequential"
        assert heat_fill(0.0, *COLUMN_SCALES[metric]) == pytest.approx(to_rgb(HEAT_MID))
    assert heat_fill(0.1, *COLUMN_SCALES["bpg"]) == pytest.approx(to_rgb(HEAT_MID))
    assert heat_fill(0.4, *COLUMN_SCALES["spg"]) == pytest.approx(to_rgb(HEAT_MID))


def test_three_slides_stay_even_with_the_short_one_last():
    assert len(PAGE_ROW_COUNTS) == 3
    assert sum(PAGE_ROW_COUNTS) == 46
    assert PAGE_ROW_COUNTS[-1] == min(PAGE_ROW_COUNTS)
    assert max(PAGE_ROW_COUNTS) - min(PAGE_ROW_COUNTS) <= 4
    starts = [lo for lo, _ in PAGE_SEASON_RANGES]
    assert starts == sorted(starts, reverse=True), "slides must run newest first"
    starts = [lo for lo, _ in PAGE_SEASON_RANGES]
    assert starts == sorted(starts, reverse=True), "slides must run newest first"


def test_the_scale_never_depends_on_which_rookies_are_in_the_pool():
    small = pd.DataFrame({metric: [0.0, 1.0] for metric in SHADED_METRICS})
    large = pd.DataFrame({metric: [-99.0, 99.0] for metric in SHADED_METRICS})
    assert heat_scales(small) == heat_scales(large) == COLUMN_SCALES


def test_a_portrait_never_spills_into_the_row_below_but_may_rise_above():
    left, bottom, width, height = headshot_clip_bounds(row_y=500.0)
    assert bottom == pytest.approx(500.0 - ROW_HEIGHT / 2)
    assert bottom + height > 500.0 + ROW_HEIGHT / 2
    assert width == pytest.approx(2 * HEADSHOT_HALF_SIZE)


def test_opportunity_columns_stay_plain():
    assert "games" not in SHADED_METRICS
    assert "mpg" not in SHADED_METRICS
    assert set(COLUMN_SCALES) == set(SHADED_METRICS)
