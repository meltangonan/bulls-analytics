"""Post-specific tests for the current-roster hot-spot shot-chart workflow.

Covers the F5-derived density math (normalization, the player-minus-league
signed difference, off-court masking) and the shot-distance filter — the
analytical behavior the graphic depends on. The NBA fetch path is not exercised
here, and the contour rendering is judged visually rather than in tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.prototypes.current_roster_hot_spots import (
    BASELINE_Y,
    GRID_Y,
    MAX_DIST_FT,
    _edges,
    _filter,
    density,
    signed_diff,
)


def _grid_shape():
    xe, ye = _edges()
    return len(xe) - 1, len(ye) - 1  # (nx, ny)


def test_density_is_a_normalized_distribution():
    df = pd.DataFrame({"loc_x": [0, 10, -20, 40], "loc_y": [0, 50, 100, 20]})
    grid = density(df)
    nx, ny = _grid_shape()
    assert grid.shape == (nx, ny)
    assert grid.sum() == pytest.approx(1.0)  # normalized to a probability distribution


def test_density_of_no_shots_is_all_zero_not_nan():
    empty = pd.DataFrame({"loc_x": [], "loc_y": []})
    grid = density(empty)
    assert grid.sum() == 0.0
    assert not np.isnan(grid).any()  # no divide-by-zero blowup


def test_signed_diff_signs_track_over_and_under_indexing():
    nx, ny = _grid_shape()
    league = np.full((nx, ny), 1.0 / (nx * ny))  # flat league baseline
    player = league.copy()
    player[40, 60] += 0.5  # player takes more shots from this on-court cell
    player[41, 60] -= 0.5  # ...and fewer from this one
    diff = signed_diff(player, league)

    assert diff.shape == (nx, ny)
    assert diff[40, 60] > 0  # red (hot) territory
    assert diff[41, 60] < 0  # gray (cold) territory


def test_signed_diff_masks_at_and_below_the_baseline():
    xe, ye = _edges()
    yc = (ye[:-1] + ye[1:]) / 2.0
    below = int(np.argmax(yc <= BASELINE_Y))  # cell at/behind the baseline
    above = int(np.argmax(yc > 0))            # a cell on the court
    nx, ny = _grid_shape()
    league = np.full((nx, ny), 1.0 / (nx * ny))
    player = league.copy()
    player[40, below] += 0.5
    player[40, above] += 0.5
    diff = signed_diff(player, league)

    assert diff[40, below] == 0.0   # off-court difference is masked out
    assert diff[40, above] > 0.0    # on-court difference survives


def test_filter_drops_only_beyond_max_distance():
    df = pd.DataFrame({"shot_distance": [0, MAX_DIST_FT, MAX_DIST_FT + 1, 60]})
    kept = _filter(df)
    assert kept["shot_distance"].tolist() == [0, MAX_DIST_FT]


def test_grid_top_covers_the_three_point_line():
    # The density grid must reach past the arc so above-the-break threes register.
    assert GRID_Y[1] >= 260  # ~26 ft; NBA arc tops out ~23.75 ft (237.5 tenths)
