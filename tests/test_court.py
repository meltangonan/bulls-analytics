"""Tests for the standard shot-chart court geometry."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest
from matplotlib.patches import Circle

from bulls.graphics.court import (
    BACKBOARD_HALF_WIDTH,
    BACKBOARD_Y,
    BASELINE_Y,
    COURT_HALF_WIDTH,
    HASH_FROM_BASELINE_FT,
    HOOP_RADIUS,
    LANE_MARKS_FT,
    PAINT_HALF_WIDTH,
    RESTRICTED_RADIUS,
    draw_half_court,
    restricted_area_patch,
)


def _segment(line):
    return tuple(line.get_xdata()), tuple(line.get_ydata())


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
