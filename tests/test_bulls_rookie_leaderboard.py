"""Tests for the ranked Bulls rookie production leaderboard."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.bulls_rookie_leaderboard import (
    BOTTOM_PAD,
    CANVAS_HEIGHT,
    CHART_WIDTH,
    HEADER_RULE_FROM_TOP,
    COLUMN_SCALES,
    DEFAULT_HERO_MODE,
    HERO_MODES,
    MIN_MINUTES,
    SHADED_METRICS,
    STAT_COLUMNS,
    CARD_OUTSET_Y,
    CARD_OVERLAP_Y,
    SCALE_SAMPLE_SIZE,
    TOP_N,
    canva_copy,
    row_height,
    split_pages,
)


def test_the_qualified_pool_is_stated_not_implied():
    """A top ten of an unstated field invites 'why isn't X here?'."""
    assert MIN_MINUTES == 1000
    assert TOP_N == 10


def test_split_puts_the_top_ten_first_and_the_rest_behind_it():
    table = pd.DataFrame({"rank": range(1, 24)})
    first, second = split_pages(table)
    assert len(first) == TOP_N
    assert len(second) == 13
    assert first["rank"].tolist() == list(range(1, 11))
    assert second["rank"].tolist() == list(range(11, 24))


def test_both_slides_fill_one_shared_canvas():
    """Rows stretch to fit, so neither slide carries an empty tail."""
    for count in (TOP_N, 13):
        used = row_height(count) * count
        assert used == pytest.approx(
            CANVAS_HEIGHT - HEADER_RULE_FROM_TOP - 21.5 - BOTTOM_PAD
        )
    assert row_height(TOP_N) > row_height(13), "the ranked slide gets more presence"


def test_the_asset_is_shaped_so_height_binds_when_it_is_placed():
    """Narrower and taller than the box it lands in, on purpose.

    A 1080x1350 Canva page leaves the chart roughly 960x875 once the title and
    footer take their share, and whichever dimension binds first sets the scale.
    An asset wider than that box scales down on width and strands vertical
    space; one shaped like this scales down on height and uses all of it.
    """
    box_w, box_h = 960, 875
    assert box_w / CHART_WIDTH > box_h / CANVAS_HEIGHT, "width must not bind first"
    scale = min(box_w / CHART_WIDTH, box_h / CANVAS_HEIGHT)
    assert CHART_WIDTH * scale <= box_w
    assert CANVAS_HEIGHT * scale == pytest.approx(box_h)


def test_games_played_sits_before_minutes():
    labels = [label for _, label in STAT_COLUMNS]
    assert labels.index("GP") < labels.index("MPG")


def test_opportunity_columns_are_never_shaded():
    """GP and MPG describe the chance he got, not how he took it."""
    assert "games" not in SHADED_METRICS
    assert "mpg" not in SHADED_METRICS
    assert set(SHADED_METRICS) <= set(COLUMN_SCALES)


def test_the_hero_metric_is_not_also_a_shaded_column():
    for metric, _, _ in HERO_MODES.values():
        assert metric not in dict(STAT_COLUMNS)
        assert metric not in SHADED_METRICS


def test_the_default_ranking_is_the_rate_that_shipped():
    """The published post ranks by PRA/75, so a rerun must reproduce that.

    Totals and per-game correlate 0.82 and 0.77 with minutes played; PRA/75
    correlates 0.03. The rate measures the player, the others largely measure
    how much the coach used him. Both remain available behind --rank-by.
    """
    assert DEFAULT_HERO_MODE == "per-75"
    metric, label, fmt = HERO_MODES["per-75"]
    assert (metric, label) == ("pra_per_75", "PRA/75")
    assert fmt.format(30.727) == "30.7"
    assert set(HERO_MODES) == {"total", "per-75", "per-game"}


def test_the_caption_claims_production_and_never_claims_best():
    """PRA/75 is production. Claiming 'best' is the composite's rejected error."""
    for mode in HERO_MODES:
        copy = canva_copy(pd.DataFrame({"x": range(23)}), mode).lower()
        assert "production" in copy
        assert "production, not quality" in copy
        assert "best" not in copy
        assert f"top {TOP_N} out of 23" in copy, "state the field the cut came from"


def test_the_hero_card_matches_the_game_score_table_exactly():
    """Same shape, same shadow, one implementation — see DESIGN.md."""
    from bulls.graphics.house import accent_card_bounds
    from scripts.prototypes.top_game_performances import (
        DECADE_LAYOUT,
        GMSC_LEFT,
        GMSC_RIGHT,
        game_score_card_bounds,
    )

    theirs = game_score_card_bounds(10, 800.0)
    ours = accent_card_bounds(GMSC_LEFT, GMSC_RIGHT, 800.0, 10, DECADE_LAYOUT.row_height)
    assert ours == theirs


def test_the_card_overlaps_the_header_rule_rather_than_butting_into_it():
    from bulls.graphics.house import accent_card_bounds

    _, _, _, top = accent_card_bounds(400, 486, first_row_y=800, row_count=10, row_height=76)
    assert top > 800 + 76 / 2, "the card must reach above the first row"


def test_scales_are_calibrated_on_the_thousand_minute_peer_group():
    """Everyone here cleared 1,000 minutes, so grade them against that pool."""
    from bulls.graphics.house import HEAT_MID, heat_fill
    from matplotlib.colors import to_rgb

    assert SCALE_SAMPLE_SIZE == 558
    # Ordinary starter production for this pool takes no colour.
    for metric, ordinary in (("ppg", 10.2), ("rpg", 4.9), ("apg", 2.0)):
        assert heat_fill(ordinary, *COLUMN_SCALES[metric]) == pytest.approx(
            to_rgb(HEAT_MID)
        ), f"{metric} still colours {ordinary}"
    # A genuine standout still does.
    assert heat_fill(16.8, *COLUMN_SCALES["ppg"]) != pytest.approx(to_rgb(HEAT_MID))


def test_the_card_reaches_less_far_than_the_game_score_default():
    """This canvas is tighter, so the card must not crowd its own header."""
    from bulls.graphics.house import ACCENT_CARD_OUTSET_Y, ACCENT_CARD_OVERLAP_Y

    assert CARD_OUTSET_Y + CARD_OVERLAP_Y < ACCENT_CARD_OUTSET_Y + ACCENT_CARD_OVERLAP_Y
