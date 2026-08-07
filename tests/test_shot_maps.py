"""Tests for the shared shot-map analysis layer.

Covers the two things every chart in the family depends on: the density method
(normalisation, the player-minus-league difference, off-court masking) and the
zone method (relative volume and efficiency, plus the noise guard).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bulls.analysis import shot_maps as sm


def _grid_shape():
    xe, ye = sm.edges()
    return len(xe) - 1, len(ye) - 1


def _shots(rows):
    """rows: (loc_x, loc_y, distance, made, type)"""
    return pd.DataFrame(rows, columns=["loc_x", "loc_y", "shot_distance",
                                       "shot_made", "shot_type"])


# --- density ---------------------------------------------------------------
def test_density_is_a_normalized_distribution():
    df = pd.DataFrame({"loc_x": [0, 10, -20, 40], "loc_y": [0, 50, 100, 20]})
    grid = sm.density(df)
    assert grid.shape == _grid_shape()
    assert grid.sum() == pytest.approx(1.0)


def test_density_of_no_shots_is_zero_not_nan():
    grid = sm.density(pd.DataFrame({"loc_x": [], "loc_y": []}))
    assert grid.sum() == 0.0
    assert not np.isnan(grid).any()


def test_normalization_makes_volume_irrelevant():
    """A player who shoots twice as much from the same spots has the same map.

    This is the property that lets a 262-attempt player and a 963-attempt player
    sit on the same grid: density encodes shot *diet*, not playing time.
    """
    few = pd.DataFrame({"loc_x": [0, 100, -100], "loc_y": [10, 120, 120]})
    many = pd.concat([few] * 4, ignore_index=True)
    assert np.allclose(sm.density(few), sm.density(many))


def test_signed_diff_signs_track_over_and_under_indexing():
    nx, ny = _grid_shape()
    league = np.full((nx, ny), 1.0 / (nx * ny))
    player = league.copy()
    player[40, 60] += 0.5
    player[41, 60] -= 0.5
    diff = sm.signed_diff(player, league)
    assert diff[40, 60] > 0
    assert diff[41, 60] < 0


def test_signed_diff_masks_at_and_below_the_baseline():
    _, ye = sm.edges()
    centres = (ye[:-1] + ye[1:]) / 2.0
    below = int(np.argmax(centres <= sm.BASELINE_Y))
    above = int(np.argmax(centres > 0))
    nx, ny = _grid_shape()
    league = np.full((nx, ny), 1.0 / (nx * ny))
    player = league.copy()
    player[40, below] += 0.5
    player[40, above] += 0.5
    diff = sm.signed_diff(player, league)
    assert diff[40, below] == 0.0
    assert diff[40, above] > 0.0


def test_within_range_drops_only_beyond_the_limit():
    df = pd.DataFrame({"shot_distance": [0, sm.MAX_DIST_FT, sm.MAX_DIST_FT + 1, 60]})
    assert sm.within_range(df)["shot_distance"].tolist() == [0, sm.MAX_DIST_FT]


def test_grid_reaches_past_the_three_point_line():
    assert sm.GRID_Y[1] >= 260  # arc tops out at 237.5 (23.75 ft)


# --- zones -----------------------------------------------------------------
def test_zone_masks_partition_every_shot_exactly_once():
    df = _shots([
        (0, 5, 1.0, 1, "2PT"), (0, 60, 6.0, 0, "2PT"),
        (0, 150, 16.0, 1, "2PT"), (0, 260, 26.0, 0, "3PT"),
    ])
    masks = sm.zone_masks(df)
    stacked = np.vstack([m.to_numpy() for m in masks.values()])
    assert stacked.sum(axis=0).tolist() == [1, 1, 1, 1]
    assert set(masks) == set(sm.ZONE_ORDER)


def test_zone_split_reports_both_dimensions_against_the_league():
    player = _shots([(0, 5, 1.0, 1, "2PT")] * 8 + [(0, 5, 1.0, 0, "2PT")] * 2)
    league = _shots([(0, 5, 1.0, 1, "2PT")] * 5 + [(0, 5, 1.0, 0, "2PT")] * 5)
    out = sm.zone_split(player, league, player_poss=100, league_poss=1000)
    row = out[out.zone == "RIM"].iloc[0]

    assert row.fga == 10 and row.fgm == 8
    assert row.fg == pytest.approx(0.8)
    assert row.fg_rel == pytest.approx(30.0)      # 80% vs a 50% league
    assert row.per75 == pytest.approx(7.5)        # 10 shots / 100 poss * 75
    assert row.lg_per75 == pytest.approx(0.75)
    assert row.vol_rel == pytest.approx(900.0)    # ten times the league rate


def test_zone_split_keeps_zone_order():
    df = _shots([(0, 5, 1.0, 1, "2PT"), (0, 60, 6.0, 0, "2PT"),
                 (0, 150, 16.0, 1, "2PT"), (0, 260, 26.0, 0, "3PT")])
    out = sm.zone_split(df, df, player_poss=100, league_poss=100)
    assert out.zone.tolist() == list(sm.ZONE_ORDER)


def test_three_pointers_are_zoned_by_type_not_distance():
    """A corner three is only ~22 ft, so distance alone would misfile it."""
    corner_three = _shots([(220, 20, 22.0, 1, "3PT")])
    assert sm.zone_masks(corner_three)["THREE"].all()
    assert not sm.zone_masks(corner_three)["LONG MID"].any()


# --- noise guard -----------------------------------------------------------
def test_separable_rejects_a_hot_looking_small_sample():
    # 16/29 = 55.2% against a 38.6% league looks huge, but 29 attempts cannot
    # carry it -- this is the real right-corner case from a live chart.
    assert not sm.separable(16, 29, 0.386)


def test_separable_accepts_a_gap_the_sample_supports():
    # 22/36 = 61.1% against 38.7% clears the interval even at 36 attempts.
    assert sm.separable(22, 36, 0.387)


def test_separable_needs_attempts():
    assert not sm.separable(0, 0, 0.4)
