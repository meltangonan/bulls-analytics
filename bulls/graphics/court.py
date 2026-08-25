"""Standard half-court geometry shared by conventional shot charts.

The hotspot, hex, roster-hot-spots, and zone-deep-dive renderers use this court.
Concentric rings and ladders draw specialized overlays in ``make_shot_chart.py``
because their markings need different clipping, layering, and opacity. Everything
here works in raw NBA shot-chart coordinates: tenths of a foot, hoop at the
origin, court 500 units wide, regulation baseline at y=-52.5.
"""
from __future__ import annotations

import numpy as np
from matplotlib.path import Path
from matplotlib.patches import Arc, Circle, FancyBboxPatch, PathPatch


# Court constants, tenths of a foot.
ARC = 237.5              # three-point radius
CORNER_X = 220.0         # where the arc meets the corner lines
BASELINE_Y = -52.5
PAINT_HALF_WIDTH = 80.0
FT_LINE_Y = 137.5
COURT_HALF_WIDTH = 250.0
HOOP_RADIUS = 7.5
# The board is 1.25 ft behind the hoop center. The baseline is four feet behind
# the board and the free-throw line is fifteen feet in front of it, matching
# NBA Rule No. 1. Its connector stops at the
# rear edge of the 18-inch rim rather than continuing through the circle.
BACKBOARD_Y = -12.5
BACKBOARD_HALF_WIDTH = 30.0
RESTRICTED_RADIUS = 40.0
FT_RADIUS = 60.0
LANE_MARKS_FT = (7.0, 8.0, 11.0, 14.0)
HASH_FROM_BASELINE_FT = 28.0

# Warm court line for pale panels; the Summer League report's original value.
COURT_LINE = "#C9A8B5"


def restricted_area_patch(ax, hoop_x: float, hoop_y: float, s: float,
                          color: str, lw: float, zorder: int,
                          alpha: float = 1.0) -> PathPatch:
    """Draw the restricted-area D as one continuous anti-aliased path."""
    radius = RESTRICTED_RADIUS * s
    board_y = hoop_y + BACKBOARD_Y * s
    arc = Path.arc(0, 180)
    arc_vertices = arc.vertices * np.array([radius, radius]) + np.array([hoop_x, hoop_y])
    vertices = np.vstack([
        [hoop_x + radius, board_y],
        [hoop_x + radius, hoop_y],
        arc_vertices[1:],
        [hoop_x - radius, board_y],
    ])
    codes = np.concatenate([
        [Path.MOVETO, Path.LINETO],
        arc.codes[1:],
        [Path.LINETO],
    ])
    patch = PathPatch(
        Path(vertices, codes), facecolor="none", edgecolor=color, lw=lw,
        alpha=alpha, zorder=zorder, antialiased=True,
        capstyle="round", joinstyle="round", snap=False,
    )
    ax.add_patch(patch)
    return patch

def nba_to_basket_bottom_px(x0: float, y0: float, s: float, loc_x, loc_y):
    """Map NBA shot coordinates onto a court whose basket is at the bottom.

    NBA's left/right zone names use the league's basket-at-the-top view. Turning
    that court around to put the basket at the bottom reverses the horizontal
    screen position: NBA ``Left`` belongs on the viewer's right, and NBA
    ``Right`` belongs on the viewer's left. Keep the source labels and figures
    unchanged; this render-boundary mirror is the only conversion required.

    ``loc_x`` and ``loc_y`` may be scalars, NumPy arrays, or pandas Series.
    """
    return (
        x0 + (COURT_HALF_WIDTH - loc_x) * s,
        y0 + (loc_y - BASELINE_Y) * s,
    )


def draw_half_court(ax, center_x: float, center_y: float, s: float,
                    color: str = COURT_LINE, lw: float = 1.1, zorder: int = 5):
    """Draw a half court centred at (center_x, center_y), hoop toward the bottom.

    ``s`` scales the 500-unit court width to pixels (s=1.0 -> 500 px wide).
    Returns the ``(x0, y0)`` origin so callers can map shot coordinates into the
    same pixel space::

        px, py = nba_to_basket_bottom_px(x0, y0, s, loc_x, loc_y)

    Do not reproduce the old ``x0 + (loc_x + 250) * s`` shortcut. It puts NBA
    Left on the viewer's left even though rotating the basket to the bottom
    requires Left to appear on the viewer's right.
    """
    top_y = 280.0
    x0 = center_x - COURT_HALF_WIDTH * s
    y0 = center_y - (top_y - BASELINE_Y) * s / 2.0

    def t(cx, cy):
        return x0 + (cx + COURT_HALF_WIDTH) * s, y0 + (cy - BASELINE_Y) * s

    line = dict(color=color, lw=lw, zorder=zorder)
    ax.plot([t(-250, BASELINE_Y)[0], t(250, BASELINE_Y)[0]], [y0, y0], **line)
    for side in (-250, 250):
        ax.plot([t(side, BASELINE_Y)[0]] * 2,
                [t(side, BASELINE_Y)[1], t(side, 110)[1]], **line)
    ax.add_patch(FancyBboxPatch(
        t(-PAINT_HALF_WIDTH, BASELINE_Y), 2 * PAINT_HALF_WIDTH * s,
        (FT_LINE_Y - BASELINE_Y) * s,
        boxstyle="square,pad=0", facecolor="none", edgecolor=color,
        lw=lw, zorder=zorder))

    # The same lane-space and sideline markings used by the shot-value ladder.
    # They are court geography, not chart decoration, so conventional shot maps
    # should not lose them just because their data layer is made of hexagons.
    for ft in LANE_MARKS_FT:
        mark_y = BASELINE_Y + ft * 10
        for side, direction in ((-PAINT_HALF_WIDTH, -1), (PAINT_HALF_WIDTH, 1)):
            ax.plot([t(side, mark_y)[0], t(side + direction * 8, mark_y)[0]],
                    [t(0, mark_y)[1]] * 2, **line)

    hash_y = BASELINE_Y + HASH_FROM_BASELINE_FT * 10
    for side, direction in ((-COURT_HALF_WIDTH, 1), (COURT_HALF_WIDTH, -1)):
        ax.plot([t(side, hash_y)[0], t(side + direction * 18, hash_y)[0]],
                [t(0, hash_y)[1]] * 2, **line)

    hoop_x, hoop_y = t(0, 0)
    ax.add_patch(Circle((hoop_x, hoop_y), HOOP_RADIUS * s, facecolor="none",
                        edgecolor=color, lw=lw, zorder=zorder))
    # Backboard: a six-foot plate behind the rim, plus the short connector that
    # makes it read as a basket assembly rather than another court tick.
    board_y = t(0, BACKBOARD_Y)[1]
    ax.plot([t(-BACKBOARD_HALF_WIDTH, BACKBOARD_Y)[0],
             t(BACKBOARD_HALF_WIDTH, BACKBOARD_Y)[0]], [board_y] * 2,
            color=color, lw=lw * 2.5, zorder=zorder + 1,
            solid_capstyle="butt")
    rim_back_y = hoop_y - HOOP_RADIUS * s
    ax.plot([hoop_x, hoop_x], [board_y, rim_back_y], color=color,
            lw=lw * 1.25, zorder=zorder + 1)
    restricted_area_patch(ax, hoop_x, hoop_y, s, color, lw, zorder)
    # Free-throw circle: solid above the line, dashed below.
    ft_x, ft_y = t(0, FT_LINE_Y)
    ax.add_patch(Arc((ft_x, ft_y), 2 * FT_RADIUS * s, 2 * FT_RADIUS * s,
                     theta1=0, theta2=180,
                     color=color, lw=lw, zorder=zorder))
    ax.add_patch(Arc((ft_x, ft_y), 2 * FT_RADIUS * s, 2 * FT_RADIUS * s,
                     theta1=180, theta2=360,
                     color=color, lw=lw, linestyle=(0, (4, 3)), zorder=zorder))
    # Three-point line: straight corner runs, then the arc between them.
    corner_top = (ARC ** 2 - CORNER_X ** 2) ** 0.5
    for side in (-CORNER_X, CORNER_X):
        ax.plot([t(side, BASELINE_Y)[0]] * 2,
                [t(side, BASELINE_Y)[1], t(side, corner_top)[1]], **line)
    theta = float(np.degrees(np.arctan2(corner_top, CORNER_X)))
    ax.add_patch(Arc((hoop_x, hoop_y), 2 * ARC * s, 2 * ARC * s, theta1=theta,
                     theta2=180 - theta, color=color, lw=lw, zorder=zorder))
    return x0, y0
