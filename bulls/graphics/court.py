"""Shared half-court geometry for the shot-chart family.

Promoted out of the prototypes once the same court appeared in four of them
(roster hot spots, hex chart, zone deep-dive, zone rings). Everything here works
in raw NBA shot-chart coordinates: tenths of a foot, hoop at the origin, court
500 units wide, baseline at y=-47.5.
"""
from __future__ import annotations

from matplotlib.patches import Arc, Circle, FancyBboxPatch


# Court constants, tenths of a foot.
ARC = 237.5              # three-point radius
CORNER_X = 220.0         # where the arc meets the corner lines
BASELINE_Y = -47.5
PAINT_HALF_WIDTH = 80.0
FT_LINE_Y = 142.5
COURT_HALF_WIDTH = 250.0

# Warm court line for pale panels; the Summer League report's original value.
COURT_LINE = "#C9A8B5"

def draw_half_court(ax, center_x: float, center_y: float, s: float,
                    color: str = COURT_LINE, lw: float = 1.1, zorder: int = 5):
    """Draw a half court centred at (center_x, center_y), hoop toward the bottom.

    ``s`` scales the 500-unit court width to pixels (s=1.0 -> 500 px wide).
    Returns the ``(x0, y0)`` origin so callers can map shot coordinates into the
    same pixel space::

        px = x0 + (loc_x + 250) * s
        py = y0 + (loc_y + 47.5) * s
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
        t(-PAINT_HALF_WIDTH, BASELINE_Y), 2 * PAINT_HALF_WIDTH * s, 190 * s,
        boxstyle="square,pad=0", facecolor="none", edgecolor=color,
        lw=lw, zorder=zorder))

    hoop_x, hoop_y = t(0, 0)
    ax.add_patch(Circle((hoop_x, hoop_y), 7.5 * s * 2, facecolor="none",
                        edgecolor=color, lw=lw, zorder=zorder))
    # Backboard: 6 ft wide, 1 ft behind the rim.
    ax.plot([t(-30, -7.5)[0], t(30, -7.5)[0]], [t(0, -7.5)[1]] * 2, **line)
    # Restricted-area arc.
    ax.add_patch(Arc((hoop_x, hoop_y), 2 * 40 * s, 2 * 40 * s, theta1=0,
                     theta2=180, color=color, lw=lw, zorder=zorder))
    # Free-throw circle: solid above the line, dashed below.
    ft_x, ft_y = t(0, FT_LINE_Y)
    ax.add_patch(Arc((ft_x, ft_y), 2 * 60 * s, 2 * 60 * s, theta1=0, theta2=180,
                     color=color, lw=lw, zorder=zorder))
    ax.add_patch(Arc((ft_x, ft_y), 2 * 60 * s, 2 * 60 * s, theta1=180, theta2=360,
                     color=color, lw=lw, linestyle=(0, (4, 3)), zorder=zorder))
    # Three-point line: straight corner runs, then the arc between them.
    corner_top = (ARC ** 2 - CORNER_X ** 2) ** 0.5
    for side in (-CORNER_X, CORNER_X):
        ax.plot([t(side, BASELINE_Y)[0]] * 2,
                [t(side, BASELINE_Y)[1], t(side, corner_top)[1]], **line)
    theta = 22.1  # angle where the arc meets the corner lines
    ax.add_patch(Arc((hoop_x, hoop_y), 2 * ARC * s, 2 * ARC * s, theta1=theta,
                     theta2=180 - theta, color=color, lw=lw, zorder=zorder))
    return x0, y0
