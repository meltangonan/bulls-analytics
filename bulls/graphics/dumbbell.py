"""The dumbbell row: a subject mark and a reference ring on one track (docs/design/tables-cards.md)."""
from __future__ import annotations

from bulls.graphics import house
from bulls.graphics.house import DRAFT_DPI

INK = house.BLACK
SUBJECT = house.RED
REFERENCE_GREY = "#6E6862"    # the reference mark: data, so darkest of the greys
CONNECTOR_GREY = "#8A837B"    # the bar between the marks: also data
LEADER_GREY = "#A8A199"       # dotted leader; a dash reads lighter than a solid rule
GRIDLINE = "#B8B0A8"
FOOTNOTE_GREY = "#7A736C"

# Marker diameters in points, drawn through ``plot`` rather than ``scatter`` so the
# number here is the size on the page: at DRAFT_DPI a point is 150/72 px.
SUBJECT_DOT = 13.5
REFERENCE_DOT = 10.5
REFERENCE_RING_WIDTH = 2.6
REFERENCE_RING_RADIUS = (REFERENCE_DOT + REFERENCE_RING_WIDTH) / 2 * DRAFT_DPI / 72

TYPE_LABEL = 19.0
TYPE_VALUE = 21.0
TYPE_AXIS = 17.0
TYPE_LEGEND = 18.0

GRIDLINE_WIDTH = 1.2
CONNECTOR_WIDTH = 4.0
LEADER_WIDTH = 1.8
LEADER_DASH = (0, (2, 4))
LEADER_GAP = 30
LEGEND_TEXT_GAP = 26
LEGEND_DROP = 66              # below the scale, so the top of the chart is headers only
AXIS_LABEL_DROP = 42
GRIDLINE_FOOT_FACTOR = 0.42


def dot(ax, x: float, y: float, size: float, color: str, zorder: int = 4,
        hollow: bool = False) -> None:
    """A filled mark, or a ring when ``hollow``."""
    ax.plot([x], [y], marker="o", markersize=size, linestyle="none", zorder=zorder,
            markerfacecolor="none" if hollow else color, markeredgecolor=color,
            markeredgewidth=REFERENCE_RING_WIDTH if hollow else 0)


def connector(ax, subject_x: float, reference_x: float, y: float) -> None:
    """The bar between the marks, stopped at the ring's edge.

    Dropped entirely when the two values sit so close that the ring already spans
    the gap; a stub of bar poking out of a ring reads as a drawing error.
    """
    start, end = min(subject_x, reference_x), max(subject_x, reference_x)
    if reference_x > subject_x:
        end -= REFERENCE_RING_RADIUS
    else:
        start += REFERENCE_RING_RADIUS
    if end > start:
        ax.plot([start, end], [y, y], color=CONNECTOR_GREY, linewidth=CONNECTOR_WIDTH,
                solid_capstyle="butt", zorder=2)


def leader(ax, from_x: float, to_x: float, y: float) -> None:
    """The dotted run from the marks to the value column."""
    ax.plot([from_x + LEADER_GAP, to_x], [y, y], color=LEADER_GREY,
            linewidth=LEADER_WIDTH, linestyle=LEADER_DASH, zorder=1)
