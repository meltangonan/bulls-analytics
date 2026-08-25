"""Tests for the standard shot-chart court geometry."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.patches import Circle

from bulls.graphics.court import (
    ARC,
    BACKBOARD_HALF_WIDTH,
    BACKBOARD_Y,
    BASELINE_Y,
    COURT_HALF_WIDTH,
    CORNER_X,
    HASH_FROM_BASELINE_FT,
    FT_LINE_Y,
    HOOP_RADIUS,
    LANE_MARKS_FT,
    PAINT_HALF_WIDTH,
    RESTRICTED_RADIUS,
    draw_half_court,
    nba_to_basket_bottom_px,
    restricted_area_patch,
)
from bulls.analysis import shot_maps as sm


def _segment(line):
    return tuple(line.get_xdata()), tuple(line.get_ydata())


def test_basket_bottom_mapping_puts_nba_left_on_viewer_right():
    """Rotating NBA's basket-top source view reverses screen left and right."""
    px, py = nba_to_basket_bottom_px(
        x0=100.0,
        y0=200.0,
        s=2.0,
        loc_x=np.array([-220.0, 0.0, 220.0]),
        loc_y=np.array([0.0, 0.0, 0.0]),
    )

    court_center = 100.0 + COURT_HALF_WIDTH * 2.0
    assert px[0] > court_center  # NBA Left is viewer-right.
    assert px[1] == pytest.approx(court_center)
    assert px[2] < court_center  # NBA Right is viewer-left.
    assert np.all(py == pytest.approx(200.0 - BASELINE_Y * 2.0))


def test_baseline_backboard_and_free_throw_line_match_nba_dimensions():
    """Backboard is 4 ft from baseline; free-throw line is 15 ft beyond it."""
    assert BACKBOARD_Y - BASELINE_Y == pytest.approx(40.0)
    assert FT_LINE_Y - BACKBOARD_Y == pytest.approx(150.0)


def test_court_markers_and_zone_geometry_share_the_same_physical_constants():
    """Black court lines and coloured-zone boundaries must never drift apart."""
    assert PAINT_HALF_WIDTH == sm.PAINT_HALF
    assert FT_LINE_Y == sm.FT_Y
    assert RESTRICTED_RADIUS == sm.RA_R
    assert ARC == sm.ARC_R
    assert CORNER_X == sm.ZONE12_CORNER_X


def test_standard_court_includes_ladder_lane_and_sideline_marks():
    fig, ax = plt.subplots()
    x0, y0 = draw_half_court(ax, center_x=0, center_y=0, s=1.0)

    def t(x, y):
        return x0 + x + COURT_HALF_WIDTH, y0 + y - BASELINE_Y

    segments = {_segment(line) for line in ax.lines}
    for ft in LANE_MARKS_FT:
        y = BASELINE_Y + ft * 10
        for side, direction in ((-PAINT_HALF_WIDTH, -1), (PAINT_HALF_WIDTH, 1)):
            assert ((t(side, y)[0], t(side + direction * 8, y)[0]),
                    (t(0, y)[1], t(0, y)[1])) in segments

    y = BASELINE_Y + HASH_FROM_BASELINE_FT * 10
    for side, direction in ((-COURT_HALF_WIDTH, 1), (COURT_HALF_WIDTH, -1)):
        assert ((t(side, y)[0], t(side + direction * 18, y)[0]),
                (t(0, y)[1], t(0, y)[1])) in segments
    plt.close(fig)


def test_standard_court_backboard_is_heavier_than_other_lines():
    fig, ax = plt.subplots()
    draw_half_court(ax, center_x=0, center_y=0, s=1.0, lw=1.2)
    assert max(line.get_linewidth() for line in ax.lines) == pytest.approx(3.0)
    plt.close(fig)


def test_backboard_connector_stops_at_the_rear_edge_of_the_hoop():
    fig, ax = plt.subplots()
    scale = 2.0
    draw_half_court(ax, center_x=0, center_y=0, s=scale, lw=1.2)

    rim = next(patch for patch in ax.patches if isinstance(patch, Circle))
    board = max(ax.lines, key=lambda line: line.get_linewidth())
    board_x, board_y = board.get_xdata(), board.get_ydata()

    assert rim.radius == pytest.approx(HOOP_RADIUS * scale)
    assert board_y[0] == pytest.approx(rim.center[1] + BACKBOARD_Y * scale)
    assert board_y[0] < rim.center[1] - rim.radius
    assert board_x == pytest.approx([
        rim.center[0] - BACKBOARD_HALF_WIDTH * scale,
        rim.center[0] + BACKBOARD_HALF_WIDTH * scale,
    ])
    connector = next(
        line for line in ax.lines
        if len(set(line.get_xdata())) == 1
        and line.get_xdata()[0] == pytest.approx(rim.center[0])
        and line.get_ydata()[0] == pytest.approx(board_y[0])
    )
    assert connector.get_ydata()[-1] == pytest.approx(rim.center[1] - rim.radius)
    plt.close(fig)


def test_restricted_area_is_one_smooth_continuous_d_path():
    fig, ax = plt.subplots()
    patch = restricted_area_patch(ax, 100, 200, 2.0, "#141414", 1.2, 5)
    vertices = patch.get_path().vertices

    assert vertices[0] == pytest.approx([
        100 + RESTRICTED_RADIUS * 2.0,
        200 + BACKBOARD_Y * 2.0,
    ])
    assert vertices[1] == pytest.approx([100 + RESTRICTED_RADIUS * 2.0, 200])
    assert vertices[-1] == pytest.approx([
        100 - RESTRICTED_RADIUS * 2.0,
        200 + BACKBOARD_Y * 2.0,
    ])
    assert patch.get_antialiased()
    assert patch.get_snap() is False
    plt.close(fig)
