"""Render the Taj Gibson retirement post's assets.

The brief is deliberately plain: Basketball Reference's reading grammar, not a
chart. Numbers carry the story, so nothing here encodes a rank as a length.
A position-only treatment was built and cut: without the underlying totals
beside it, showing where a rank sits told a reader less than the table does.

Each asset is transparent and cropped to its own content. Several slides exist
in competing treatments so the editorial choice can be made from real renders:

* ``regular-season`` / ``playoffs``          per-game Bulls line by season
* ``top-games-table``                        best five by Game Score as the accent-card
  table, the 2025-26 best-games grammar, without the three-point and free-throw splits
* ``career-high-grid`` / ``career-high-strip``  single-game bests, number and stat only
* ``franchise-ranks``                        all-time Bulls rank in twelve categories
* ``milestones``                             how often he cleared each threshold
* ``shot-diet``                              career shot families, share and FG%
  (built by ``taj_gibson_bulls_zone_charts.py``)

Competing treatments were built for several of these and cut once the editorial
choice was made: a rank dot plot, a boxed-card leaderboard, a career-high card
grid and table, a banded rank table, and pie and 100% bar forms of the shot
diet. Their renders are kept in the project's asset history rather than here.

Canva owns the titles, subtitles, source line, and framing. The only
qualification that ships inside an asset is the coverage footnote on the rank
slides, which has to travel with its own rows to be interpretable: four of
those rows are measured against a smaller population than the rest.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.graphics import house
from bulls.graphics.house import BLACK, DRAFT_DPI, RED, export_dpi, helvetica

DEFAULT_DATA = _REPO / "docs/visuals/2026-09-15-taj-gibson-retirement/data"
DEFAULT_OUTPUT = _REPO / "output/taj-gibson-retirement"

# Pale red from the low end of the magnitude scale. Readable against both the
# cream and the darker warm Canva grounds, and quiet enough that the shaded
# rows do not outshout the numbers.
HIGHLIGHT_FILL = "#F6E3E8"
# Body separators stay quieter than the header and total rules.
ROW_RULE = "#B8B0A8"
# The alternating band, matching the catch-and-shoot leaderboard: the neutral
# separator grey painted at low alpha rather than a solid tint. A translucent
# band darkens whichever Canva ground it lands on by the same relative amount,
# so one value works on both the cream and the darker warm page. A solid fill
# cannot: tuned for cream it turns into a *lighter* band on the warm ground.
STRIPE_FILL = "#B8B0A8"
STRIPE_ALPHA = 0.22

ROW_HEIGHT = 90
HEADER_GAP = 26
SIDE_PAD = 36
TOP_PAD = 24
BOTTOM_PAD = 24
FOOTNOTE_GAP = 56

# Sizes are points against axes measured in pixels, so a point is DRAFT_DPI/72
# pixels wide here, not one pixel. Getting that wrong collides the columns, so
# _draw_table measures every string it draws and refuses to save an overflow.
HEADER_SIZE = 18
BODY_SIZE = 24
FOOTNOTE_SIZE = 15
FOOTNOTE_LINE = 30

# Quieter than the table ink but still near 4.5:1 on the cream ground, per the
# accepted treatment in DESIGN.md.
FOOTNOTE_INK = "#5F5B57"

# Breathing room each cell keeps inside its column before it counts as an overflow.
CELL_PAD = 14

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class Column:
    """One table column: its header, its width, and how its cells sit."""

    header: str
    width: int
    align: str = "right"


def _month_year(date_text: str) -> str:
    stamp = pd.Timestamp(date_text)
    return f"{MONTHS[stamp.month - 1]} {stamp.year}"


def _long_date(date_text: str) -> str:
    """Readable date for the boxed rows, e.g. "Apr 27, 2014"."""
    stamp = pd.Timestamp(date_text)
    return f"{MONTHS[stamp.month - 1]} {stamp.day}, {stamp.year}"


def _iso(date_text: str) -> str:
    return pd.Timestamp(date_text).strftime("%Y-%m-%d")


def _pct(value: float) -> str:
    """Basketball Reference's leading-dot percentage, e.g. .495."""
    return f"{value:.3f}".lstrip("0")


def _column_edges(columns: list[Column]) -> list[tuple[int, int]]:
    """Left and right x of each column, laid out from the left padding."""
    edges = []
    cursor = SIDE_PAD
    for column in columns:
        edges.append((cursor, cursor + column.width))
        cursor += column.width
    return edges


def _anchor_for(columns: list[Column], index: int) -> tuple[float, str]:
    """Where a cell's text anchors, inset from its column edge by CELL_PAD.

    The inset is what keeps a right-aligned column off the left-aligned one
    beside it. Without it the two anchor on the same coordinate and the strings
    touch, which reads as '74Double-doubles' while each cell still measures as
    fitting its own column.
    """
    left, right = _column_edges(columns)[index]
    align = columns[index].align
    if align == "left":
        return left + CELL_PAD, "left"
    if align == "center":
        return (left + right) / 2, "center"
    return right - CELL_PAD, "right"


def _data_widths(ax, artists) -> list[float]:
    """Rendered widths in axes units, from a single canvas draw.

    ``house.rendered_width`` redraws per call, which is wasteful for a whole
    table; this measures every artist against one draw instead.
    """
    ax.figure.canvas.draw()
    inverse = ax.transData.inverted()
    widths = []
    for artist in artists:
        bbox = artist.get_window_extent()
        x0, _ = inverse.transform((bbox.x0, bbox.y0))
        x1, _ = inverse.transform((bbox.x1, bbox.y0))
        widths.append(x1 - x0)
    return widths


# Result colours, shared with the game-score-by-height rows.
WIN = "#3FAE63"
LOSS = "#D64545"


def _segment_line(ax, x, y, segments, zorder=4):
    """Lay coloured text segments left to right, measuring as it goes.

    The game context line mixes inks and sizes in one sentence, so it cannot be
    one text artist: the date and matchup are ink, the round marker is quieter
    and smaller, and the result is green or red. Each piece is measured before
    the next is placed, the same way the game-score-by-height row is built.
    """
    drawn = []
    cursor = x
    for text, size, colour, weight in segments:
        if not text:
            continue
        artist = ax.text(
            cursor, y, text, ha="left", va="center", fontsize=size, color=colour,
            fontproperties=helvetica(weight), zorder=zorder,
        )
        cursor += _data_widths(ax, [artist])[0] + size * 0.7
        drawn.append(artist)
    return drawn, cursor - x


def _check_widths(ax, measured: list[tuple[object, str, int]], columns: list[Column]) -> None:
    """Fail if any drawn cell is wider than the column holding it.

    Font sizes are points while the axes are measured in pixels, so a column
    width that looks generous in the source can still collide once rendered.
    Failing here beats shipping a table whose columns run into each other.
    """
    widths = _data_widths(ax, [artist for artist, _, _ in measured])
    overflows = [
        f"{columns[index].header!r} column is {columns[index].width}px but "
        f"{value!r} renders {rendered:.0f}px"
        for (_, value, index), rendered in zip(measured, widths)
        # Both sides are inset by CELL_PAD, so that is the budget a cell loses.
        if rendered > columns[index].width - CELL_PAD * 2
    ]
    if overflows:
        raise ValueError(
            "Table columns are too narrow for their contents:\n  " + "\n  ".join(overflows)
        )


def _check_footnote(ax, artists, allowed: float) -> None:
    """Fail if a pre-wrapped footnote line runs past the table's content width."""
    overflows = [
        f"{artist.get_text()!r} renders {rendered:.0f}px against {allowed:.0f}px"
        for artist, rendered in zip(artists, _data_widths(ax, artists))
        if rendered > allowed
    ]
    if overflows:
        raise ValueError(
            "Footnote lines are too long for the table:\n  " + "\n  ".join(overflows)
        )


def _draw_table(
    columns: list[Column],
    rows: list[list[str]],
    *,
    output_path: Path,
    highlight: set[int] | None = None,
    total_row: int | None = None,
    red_cells: set[tuple[int, int]] | None = None,
    footnote: tuple[str, ...] = (),
    striped: bool = False,
    final: bool = False,
) -> Path:
    """Draw one plain table and save it as a transparent, content-cropped asset.

    ``highlight`` shades whole rows, ``red_cells`` recolours single cells, and
    ``total_row`` gets a rule above it and bold type. All three take row indices
    into ``rows`` so the caller keeps every editorial decision. ``footnote``
    lines are pre-wrapped by the caller and measured like any other string.
    """
    highlight = highlight or set()
    red_cells = red_cells or set()

    width = SIDE_PAD * 2 + sum(column.width for column in columns)
    footnote_block = len(footnote) * FOOTNOTE_LINE + (FOOTNOTE_GAP if footnote else 0)
    height = (
        TOP_PAD + HEADER_SIZE + HEADER_GAP + len(rows) * ROW_HEIGHT + BOTTOM_PAD
        + footnote_block
    )

    fig = plt.figure(figsize=(width / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")

    def cell_x(index: int) -> tuple[float, str]:
        return _anchor_for(columns, index)

    measured: list[tuple[object, str, int]] = []

    # Footnote space is reserved at the bottom by `height`, so the header sits
    # against the top padding regardless of whether there is a footnote.
    header_baseline = height - TOP_PAD - HEADER_SIZE
    for index, column in enumerate(columns):
        x, align = cell_x(index)
        artist = ax.text(
            x, header_baseline, column.header, ha=align, va="center",
            fontsize=HEADER_SIZE, color=BLACK, fontproperties=helvetica("bold"),
        )
        measured.append((artist, column.header, index))

    rule_y = header_baseline - HEADER_SIZE / 2 - 14
    ax.plot(
        [SIDE_PAD, width - SIDE_PAD], [rule_y, rule_y],
        color=BLACK, linewidth=2.4, solid_capstyle="butt",
    )

    first_row_center = rule_y - ROW_HEIGHT / 2
    for row_index, row in enumerate(rows):
        y = first_row_center - row_index * ROW_HEIGHT
        is_total = row_index == total_row

        # A highlight always wins over a stripe; they never stack. The stripe
        # is grey and translucent while the highlight is a solid pale red, so
        # the two stay tellable apart when a table uses both.
        band, alpha = None, 1.0
        if row_index in highlight:
            band = HIGHLIGHT_FILL
        elif striped and not is_total and row_index % 2 == 0:
            band, alpha = STRIPE_FILL, STRIPE_ALPHA
        if band is not None:
            ax.add_patch(Rectangle(
                (SIDE_PAD, y - ROW_HEIGHT / 2), width - SIDE_PAD * 2, ROW_HEIGHT,
                facecolor=band, alpha=alpha, edgecolor="none", zorder=1,
            ))

        if is_total:
            top = y + ROW_HEIGHT / 2
            ax.plot(
                [SIDE_PAD, width - SIDE_PAD], [top, top],
                color=BLACK, linewidth=2.4, solid_capstyle="butt", zorder=3,
            )
        elif not striped and row_index < len(rows) - 1:
            # Stripes and hairlines do the same job; running both is noise.
            bottom = y - ROW_HEIGHT / 2
            ax.plot(
                [SIDE_PAD, width - SIDE_PAD], [bottom, bottom],
                color=ROW_RULE, linewidth=1.0, solid_capstyle="butt", zorder=2,
            )

        weight = "bold" if is_total else "regular"
        for column_index, value in enumerate(row):
            x, align = cell_x(column_index)
            red = (row_index, column_index) in red_cells
            artist = ax.text(
                x, y, value, ha=align, va="center", fontsize=BODY_SIZE,
                color=RED if red else BLACK,
                fontproperties=helvetica("bold" if red else weight), zorder=4,
            )
            measured.append((artist, value, column_index))

    footnote_artists = []
    for line_index, line in enumerate(footnote):
        y = BOTTOM_PAD + (len(footnote) - 1 - line_index) * FOOTNOTE_LINE + FOOTNOTE_LINE / 2
        footnote_artists.append(ax.text(
            SIDE_PAD, y, line, ha="left", va="center", fontsize=FOOTNOTE_SIZE,
            color=FOOTNOTE_INK, fontproperties=helvetica(),
        ))

    try:
        _check_widths(ax, measured, columns)
        _check_footnote(ax, footnote_artists, width - SIDE_PAD * 2)
    except ValueError:
        plt.close(fig)
        raise

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


# Per-game columns eligible for the season-best mark, as (csv column, column
# index in the rendered table, decimals shown). Games and games started are
# counts, not per-game rates, so they are not eligible.
SEASON_BEST_COLUMNS = (
    ("minutes", 3, 1),
    ("points", 4, 1),
    ("rebounds", 5, 1),
    ("offensive_rebounds", 6, 1),
    ("blocks", 7, 1),
    ("fg_pct", 8, 3),
)


def season_best_cells(frame: pd.DataFrame) -> set[tuple[int, int]]:
    """Cells holding his best season in each per-game column.

    Compared on the DISPLAYED value, not the stored one. NBA.com publishes
    per-game figures already rounded to a tenth, so two seasons can be
    genuinely tied there: 2.8 offensive rebounds in 2009-10 and 2015-16, 1.4
    blocks in 2012-13 and 2013-14. Both get marked. Highlighting one of two
    identical printed numbers would look like an error to anyone reading the
    column, and nothing in the data justifies picking between them.

    The career row is never eligible; it is an average of the rows above it,
    not a season.
    """
    seasons = frame[~frame["is_career"]]
    marked: set[tuple[int, int]] = set()
    for column, index, decimals in SEASON_BEST_COLUMNS:
        shown = seasons[column].round(decimals)
        for row_index in seasons.index[shown == shown.max()]:
            marked.add((int(row_index), index))
    return marked


def render_season(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    frame = pd.read_csv(data_path)
    columns = [
        Column("SEASON", 330, "left"),
        Column("G", 120),
        Column("GS", 130),
        Column("MP", 150),
        Column("PTS", 150),
        Column("TRB", 150),
        Column("ORB", 150),
        Column("BLK", 150),
        Column("FG%", 170),
    ]
    rows = [
        [
            str(row.season), f"{int(row.games)}", f"{int(row.starts)}",
            f"{row.minutes:.1f}", f"{row.points:.1f}", f"{row.rebounds:.1f}",
            f"{row.offensive_rebounds:.1f}", f"{row.blocks:.1f}", _pct(row.fg_pct),
        ]
        for row in frame.itertuples()
    ]
    total_index = next(
        (index for index, row in enumerate(frame.itertuples()) if row.is_career), None
    )
    return _draw_table(
        columns, rows, output_path=output_path, total_row=total_index,
        red_cells=season_best_cells(frame), striped=True, final=final,
    )


# The 2025-26 best-games grammar: one continuous accent card down the hero
# column with the values reversed out of it, and the header rule broken either
# side of the card so it reads as sitting on the table rather than as another
# cell in it. Three-point and free-throw splits are left out; he attempted no
# threes in any of these games and the free-throw line adds width without
# telling the reader anything the points column has not already.
TABLE_ROW_H = 176
TABLE_GAME_W = 940
TABLE_CARD_W = 210
TABLE_DATE_SIZE = 28
TABLE_SUB_SIZE = 20
# Close to the hero size on purpose: at only five rows the table can be set
# large, and a hero that towers over its own box score makes the supporting
# numbers look like a footnote to it rather than the evidence behind it.
TABLE_STAT_SIZE = 32
TABLE_HERO_SIZE = 34
# The accent card's bounds reach ACCENT_CARD_OUTSET_X past its column on each
# side, so a stat column starting at the column edge actually starts inside
# the card's visible edge. This gutter is measured from the card's real bounds.
TABLE_CARD_GUTTER = 44
# The accent card reaches above its column to overlap the header rule, so the
# header LABEL needs clearance a plain table does not: at the standard gap,
# "GMSC" lands on the card and renders red on red.
TABLE_HEADER_GAP = 40
# Headers scale with the table: left at the plain-table size they read as a
# caption under a much larger body rather than as column labels.
TABLE_HEADER_SIZE = 24

TABLE_STATS = (
    ("PTS", 132, lambda r: f"{int(r.points)}"),
    ("FG", 248, lambda r: f"{int(r.fgm)}-{int(r.fga)}"),
    ("REB", 132, lambda r: f"{int(r.reb)}"),
    ("AST", 132, lambda r: f"{int(r.ast)}"),
    ("STL", 132, lambda r: f"{int(r.stl)}"),
    ("BLK", 132, lambda r: f"{int(r.blk)}"),
    ("TOV", 132, lambda r: f"{int(r.tov)}"),
    ("+/-", 158, lambda r: f"{int(r.plus_minus):+d}"),
)


def render_top_games(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    """Best five by Game Score, as the accent-card table."""
    frame = pd.read_csv(data_path)
    stat_total = sum(w for _, w, _ in TABLE_STATS)
    width = (
        SIDE_PAD * 2 + TABLE_GAME_W + TABLE_CARD_W + TABLE_CARD_GUTTER + stat_total
    )
    height = (
        TOP_PAD + TABLE_HEADER_SIZE + TABLE_HEADER_GAP + len(frame) * TABLE_ROW_H
        + BOTTOM_PAD + 28
    )
    fig, ax = _new_asset(width, height)

    card_left = SIDE_PAD + TABLE_GAME_W
    card_right = card_left + TABLE_CARD_W
    card_mid = (card_left + card_right) / 2

    header_y = height - TOP_PAD - TABLE_HEADER_SIZE
    first_row_y = (
        header_y - TABLE_HEADER_SIZE / 2 - TABLE_HEADER_GAP - TABLE_ROW_H / 2
    )

    box_left, box_right, _, _ = house.draw_accent_card(
        ax, card_left, card_right, first_row_y, len(frame), TABLE_ROW_H, zorder=4,
    )

    ax.text(SIDE_PAD, header_y, "GAME", ha="left", va="center",
            fontsize=TABLE_HEADER_SIZE, color=BLACK, fontproperties=helvetica("bold"),
            zorder=6)
    ax.text(card_mid, header_y, "GMSC", ha="center", va="center",
            fontsize=TABLE_HEADER_SIZE, color=RED, fontproperties=helvetica("bold"),
            zorder=6)

    # Measured from the card's drawn edge, not its column edge.
    cursor = box_right + TABLE_CARD_GUTTER
    centres = []
    for label, stat_width, _ in TABLE_STATS:
        centre = cursor + stat_width / 2
        centres.append(centre)
        ax.text(centre, header_y, label, ha="center", va="center",
                fontsize=TABLE_HEADER_SIZE, color=BLACK,
                fontproperties=helvetica("bold"), zorder=3)
        cursor += stat_width

    rule_y = header_y - TABLE_HEADER_SIZE / 2 - TABLE_HEADER_GAP
    for x0, x1 in ((SIDE_PAD, box_left), (box_right, width - SIDE_PAD)):
        ax.plot([x0, x1], [rule_y, rule_y], color=BLACK, linewidth=2.4,
                solid_capstyle="butt", zorder=3)

    cells = []
    for index, row in enumerate(frame.itertuples()):
        y = first_row_y - index * TABLE_ROW_H
        if index:
            top = y + TABLE_ROW_H / 2
            for x0, x1 in ((SIDE_PAD, box_left), (box_right, width - SIDE_PAD)):
                ax.plot([x0, x1], [top, top], color=ROW_RULE, linewidth=1.0,
                        solid_capstyle="butt", zorder=2)

        label = str(row.playoff_label) if isinstance(row.playoff_label, str) else ""
        _, line_width = _segment_line(ax, SIDE_PAD, y, (
            (_long_date(row.game_date), TABLE_DATE_SIZE, BLACK, "bold"),
            (str(row.opponent), TABLE_DATE_SIZE, BLACK, "bold"),
            (label, TABLE_SUB_SIZE, FOOTNOTE_INK, "regular"),
            (str(row.result), TABLE_DATE_SIZE, WIN if row.result == "W" else LOSS, "bold"),
        ), zorder=3)
        if line_width > TABLE_GAME_W - CELL_PAD:
            plt.close(fig)
            raise ValueError(
                f"Game line for {row.game_date} runs {line_width:.0f}px into the card."
            )

        ax.text(card_mid, y, f"{row.game_score:.1f}", ha="center", va="center",
                fontsize=TABLE_HERO_SIZE, color="#FFFFFF",
                fontproperties=helvetica("bold"), zorder=6)

        for centre, (_, stat_width, fmt) in zip(centres, TABLE_STATS):
            cells.append((ax.text(
                centre, y, fmt(row), ha="center", va="center",
                fontsize=TABLE_STAT_SIZE, color=BLACK, fontproperties=helvetica(),
                zorder=3,
            ), stat_width))

    # The stat columns had no width guard while the plain tables did, so a
    # font bump could have collided them silently.
    overflows = [
        f"{artist.get_text()!r} renders {rendered:.0f}px against {allowed}px"
        for (artist, allowed), rendered in zip(
            cells, _data_widths(ax, [a for a, _ in cells])
        )
        if rendered > allowed - CELL_PAD * 2
    ]
    if overflows:
        plt.close(fig)
        raise ValueError("Table stat cells do not fit:\n  " + "\n  ".join(overflows))
    return _save(fig, output_path, final=final)


def render_franchise_ranks(data_path: Path, output_path: Path, *,
                          final: bool = False) -> Path:
    frame = pd.read_csv(data_path)
    columns = [
        Column("CATEGORY", 620, "left"),
        Column("TOTAL", 260),
        Column("RANK", 210),
    ]
    rows = []
    highlight: set[int] = set()
    red_cells: set[tuple[int, int]] = set()
    for index, row in enumerate(frame.itertuples()):
        rows.append([str(row.category), f"{int(row.total):,}", _ordinal(int(row.rank))])
        if int(row.rank) <= 10:
            highlight.add(index)
            red_cells.add((index, 2))

    pools = sorted(frame.loc[frame["partial_coverage"], "pool"].unique())
    if len(pools) != 1:
        raise ValueError(f"Expected one partial-coverage pool size, saw {pools}.")

    # Stripes and the top-10 highlight can coexist now that the stripe is a
    # translucent grey and the highlight a solid pale red: they read as two
    # different marks rather than two strengths of the same one. That was not
    # true when both were pink.
    # Wrapped by hand so each line is measured and no line is silently clipped.
    footnote = (
        "Rows in red are top-10 finishes in franchise history.",
        f"Blocks, steals and rebound splits rank among the {pools[0]} Bulls with those",
        "stats recorded; the NBA did not track them before 1973-74.",
    )
    return _draw_table(
        columns, rows, output_path=output_path, highlight=highlight,
        red_cells=red_cells, footnote=footnote, final=final,
    )


def _new_asset(width: int, height: int):
    """A transparent, pixel-coordinate canvas for the non-table assets."""
    fig = plt.figure(figsize=(width / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    return fig, ax


def _save(fig, output_path: Path, *, final: bool) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


# ------------------------------------------------- career highs, two treatments

# Three-letter box-score codes, in reading order. Minutes was cut: a career
# high in minutes describes a coach's rotation, not a performance.
HIGH_CODES = {
    "Points": "PTS",
    "Rebounds": "TRB",
    "Offensive rebounds": "ORB",
    "Defensive rebounds": "DRB",
    "Blocks": "BLK",
    "Assists": "AST",
    "Steals": "STL",
    "Plus-minus": "+/-",
}


def _high_value(row) -> str:
    """A career-high value, signed where the category is a differential."""
    value = int(row.value)
    return f"{value:+d}" if row.category == "Plus-minus" else f"{value}"

# Shared type scale for the two number-and-stat treatments.
HERO_SIZE = 76
CARD_LABEL_SIZE = 21

STRIP_CELL_W = 300
STRIP_H = 250


def render_career_high_strip(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    """Career highs as a single box-score line, ruled top and bottom."""
    frame = pd.read_csv(data_path)
    width = SIDE_PAD * 2 + len(frame) * STRIP_CELL_W
    # Same reasoning as the grid: a postseason high needs saying so. Reserved
    # at the bottom only; the strip itself still starts against the top pad.
    from_playoffs = bool(frame["in_playoffs"].any()) if "in_playoffs" in frame else False
    note_block = FOOTNOTE_LINE + FOOTNOTE_GAP if from_playoffs else 0
    height = TOP_PAD + STRIP_H + BOTTOM_PAD + note_block
    fig, ax = _new_asset(width, height)

    top = height - TOP_PAD
    bottom = BOTTOM_PAD + note_block
    for edge in (top, bottom):
        ax.plot(
            [SIDE_PAD, width - SIDE_PAD], [edge, edge],
            color=BLACK, linewidth=2.4, solid_capstyle="butt", zorder=3,
        )

    cells = []
    for index, row in enumerate(frame.itertuples()):
        left = SIDE_PAD + index * STRIP_CELL_W
        centre = left + STRIP_CELL_W / 2
        if index:
            ax.plot(
                [left, left], [bottom + 22, top - 22],
                color=ROW_RULE, linewidth=1.0, solid_capstyle="butt", zorder=2,
            )
        cells.append(ax.text(
            centre, bottom + STRIP_H * 0.56, _high_value(row), ha="center", va="center",
            fontsize=HERO_SIZE, color=BLACK, fontproperties=helvetica("bold"), zorder=4,
        ))
        ax.text(
            centre, bottom + STRIP_H * 0.22, HIGH_CODES[row.category], ha="center",
            va="center", fontsize=CARD_LABEL_SIZE, color=FOOTNOTE_INK,
            fontproperties=helvetica("bold"), zorder=4,
        )

    if from_playoffs:
        ax.text(
            SIDE_PAD, BOTTOM_PAD + FOOTNOTE_LINE / 2,
            "His 32-point high came in the 2014 playoffs; his regular-season high was 26.",
            ha="left", va="center", fontsize=FOOTNOTE_SIZE, color=FOOTNOTE_INK,
            fontproperties=helvetica(),
        )

    # A two-digit number at hero size very nearly fills a cell; keep it off the
    # dividers rather than discovering the collision on the rendered page.
    overflows = [
        f"{artist.get_text()!r} renders {rendered:.0f}px against a {STRIP_CELL_W}px cell"
        for artist, rendered in zip(cells, _data_widths(ax, cells))
        if rendered > STRIP_CELL_W - CELL_PAD * 2
    ]
    if overflows:
        plt.close(fig)
        raise ValueError("Strip cells do not fit:\n  " + "\n  ".join(overflows))
    return _save(fig, output_path, final=final)


GRID_COL_W, GRID_ROW_H = 468, 232
GRID_PER_ROW = 4


def render_career_high_grid(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    """Career highs as a ruled grid, with no card behind each number.

    The pill-shaped cards read as decoration rather than structure. Here the
    hairlines do the separating and the number does the talking, which is the
    same grammar as the season tables: rules and type, no containers.
    """
    frame = pd.read_csv(data_path)
    lines = -(-len(frame) // GRID_PER_ROW)
    width = SIDE_PAD * 2 + GRID_PER_ROW * GRID_COL_W
    # A high set in the postseason is still a career high, but a reader seeing
    # 32 beside a set of regular-season figures deserves to know which night it
    # came from. Every value is house black, so the note carries that on its
    # own rather than asking a colour to mean something.
    from_playoffs = bool(frame["in_playoffs"].any()) if "in_playoffs" in frame else False
    note_block = FOOTNOTE_LINE + FOOTNOTE_GAP if from_playoffs else 0
    height = TOP_PAD + lines * GRID_ROW_H + BOTTOM_PAD + note_block
    fig, ax = _new_asset(width, height)

    # Horizontal rules span the whole block, not just the occupied cells: a
    # rule that stops short on the last, partly filled line reads as a broken
    # table rather than a deliberate edge.
    for line in range(lines + 1):
        y = height - TOP_PAD - line * GRID_ROW_H
        first = line == 0
        ax.plot(
            [SIDE_PAD, width - SIDE_PAD], [y, y],
            color=BLACK if first else ROW_RULE,
            linewidth=2.4 if first else 1.0, solid_capstyle="butt", zorder=3,
        )

    labels = []
    for index, row in enumerate(frame.itertuples()):
        column = index % GRID_PER_ROW
        line = index // GRID_PER_ROW
        left = SIDE_PAD + column * GRID_COL_W
        top = height - TOP_PAD - line * GRID_ROW_H
        centre = left + GRID_COL_W / 2

        if column:
            ax.plot(
                [left, left], [top - GRID_ROW_H + 36, top - 24],
                color=ROW_RULE, linewidth=1.0, solid_capstyle="butt", zorder=2,
            )
        ax.text(
            centre, top - GRID_ROW_H * 0.46, _high_value(row), ha="center", va="center",
            fontsize=HERO_SIZE, color=BLACK, fontproperties=helvetica("bold"), zorder=4,
        )
        labels.append(ax.text(
            centre, top - GRID_ROW_H * 0.83, str(row.category), ha="center", va="center",
            fontsize=CARD_LABEL_SIZE, color=FOOTNOTE_INK, fontproperties=helvetica(), zorder=4,
        ))

    if from_playoffs:
        ax.text(
            SIDE_PAD, BOTTOM_PAD + FOOTNOTE_LINE / 2,
            "His 32-point high came in the 2014 playoffs; his regular-season high was 26.",
            ha="left", va="center", fontsize=FOOTNOTE_SIZE, color=FOOTNOTE_INK,
            fontproperties=helvetica(),
        )

    overflows = [
        f"{artist.get_text()!r} renders {rendered:.0f}px against a {GRID_COL_W}px column"
        for artist, rendered in zip(labels, _data_widths(ax, labels))
        if rendered > GRID_COL_W - CELL_PAD * 2
    ]
    if overflows:
        plt.close(fig)
        raise ValueError("Grid labels do not fit:\n  " + "\n  ".join(overflows))
    return _save(fig, output_path, final=final)


# ------------------------------------------------------------------ shot diet

DIET_ROW_H = 96
DIET_LABEL_W = 510
DIET_BAR_SPAN = 620
DIET_SHARE_W = 180
DIET_FG_W = 180
DIET_BAR_H = 44
# Air between the longest bar and the share column, which otherwise touched.
DIET_BAR_GUTTER = 70
DIET_LABEL_SIZE = 26
DIET_VALUE_SIZE = 26


def render_shot_diet(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    """Career shot diet: how often each family, and how well.

    Share is a proportion with a true zero, so the bar is drawn from zero and
    its length means what it looks like. FG% is printed rather than encoded,
    and only where the family holds enough attempts to stand behind a rate:
    ``shot_families`` marks that with ``rated``, and a 50% on ten attempts is
    not a shooting percentage.
    """
    frame = pd.read_csv(data_path)
    width = (
        SIDE_PAD * 2 + DIET_LABEL_W + DIET_BAR_SPAN + DIET_BAR_GUTTER
        + DIET_SHARE_W + DIET_FG_W
    )
    footnote = (
        "\u201cStandard jumpers\u201d is NBA.com\u2019s unlabelled default, not a recorded technique.",
        "FG% is shown only where a family holds at least 20 attempts.",
    )
    height = (
        TOP_PAD + HEADER_SIZE + HEADER_GAP + len(frame) * DIET_ROW_H + BOTTOM_PAD
        + len(footnote) * FOOTNOTE_LINE + FOOTNOTE_GAP
    )
    fig, ax = _new_asset(width, height)

    bar_left = SIDE_PAD + DIET_LABEL_W
    share_x = bar_left + DIET_BAR_SPAN + DIET_BAR_GUTTER + DIET_SHARE_W
    fg_x = share_x + DIET_FG_W

    header_y = height - TOP_PAD - HEADER_SIZE
    ax.text(SIDE_PAD, header_y, "SHOT TYPE", ha="left", va="center",
            fontsize=HEADER_SIZE, color=BLACK, fontproperties=helvetica("bold"))
    ax.text(share_x - CELL_PAD, header_y, "SHARE", ha="right", va="center",
            fontsize=HEADER_SIZE, color=BLACK, fontproperties=helvetica("bold"))
    ax.text(fg_x - CELL_PAD, header_y, "FG%", ha="right", va="center",
            fontsize=HEADER_SIZE, color=BLACK, fontproperties=helvetica("bold"))

    rule_y = header_y - HEADER_SIZE / 2 - 16
    ax.plot([SIDE_PAD, width - SIDE_PAD], [rule_y, rule_y], color=BLACK,
            linewidth=2.4, solid_capstyle="butt")

    scale = DIET_BAR_SPAN / float(frame["share_pct"].max())
    first_row_y = rule_y - DIET_ROW_H / 2
    labels = []
    for index, row in enumerate(frame.itertuples()):
        y = first_row_y - index * DIET_ROW_H
        if index % 2 == 0:
            ax.add_patch(Rectangle(
                (SIDE_PAD, y - DIET_ROW_H / 2), width - SIDE_PAD * 2, DIET_ROW_H,
                facecolor=STRIPE_FILL, alpha=STRIPE_ALPHA, edgecolor="none", zorder=1,
            ))
        labels.append(ax.text(
            SIDE_PAD, y, str(row.family), ha="left", va="center",
            fontsize=DIET_LABEL_SIZE, color=BLACK, fontproperties=helvetica(), zorder=3,
        ))
        bar_w = float(row.share_pct) * scale
        if bar_w > 1:
            ax.add_patch(FancyBboxPatch(
                (bar_left, y - DIET_BAR_H / 2), bar_w, DIET_BAR_H,
                boxstyle="round,pad=0,rounding_size=6",
                facecolor=RED, edgecolor="none", zorder=3,
            ))
        ax.text(share_x - CELL_PAD, y, f"{row.share_pct:.1f}%", ha="right", va="center",
                fontsize=DIET_VALUE_SIZE, color=BLACK, fontproperties=helvetica("bold"),
                zorder=3)
        # An unrated family shows a dash, never a rate the sample cannot carry.
        rate = f"{row.fg_pct:.1f}" if bool(row.rated) else "\u2013"
        ax.text(fg_x - CELL_PAD, y, rate, ha="right", va="center",
                fontsize=DIET_VALUE_SIZE,
                color=BLACK if bool(row.rated) else FOOTNOTE_INK,
                fontproperties=helvetica(), zorder=3)

    for line_index, line in enumerate(footnote):
        fy = BOTTOM_PAD + (len(footnote) - 1 - line_index) * FOOTNOTE_LINE + FOOTNOTE_LINE / 2
        ax.text(SIDE_PAD, fy, line, ha="left", va="center", fontsize=FOOTNOTE_SIZE,
                color=FOOTNOTE_INK, fontproperties=helvetica())

    overflows = [
        f"{a.get_text()!r} renders {w:.0f}px against {DIET_LABEL_W}px"
        for a, w in zip(labels, _data_widths(ax, labels))
        if w > DIET_LABEL_W - CELL_PAD * 2
    ]
    if overflows:
        plt.close(fig)
        raise ValueError("Shot-diet labels do not fit:\n  " + "\n  ".join(overflows))
    return _save(fig, output_path, final=final)


# ------------------------------------------------------------------- milestones

def render_milestones(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    """How often he cleared each threshold, count leading and share trailing."""
    frame = pd.read_csv(data_path)
    columns = [
        Column("", 190),
        Column("", 790, "left"),
        Column("", 350),
    ]
    rows = [
        [f"{int(row.games)}", str(row.milestone), f"{row.share * 100:.0f}% of games"]
        for row in frame.itertuples()
    ]
    of_games = int(frame["of_games"].iloc[0])
    return _draw_table(
        columns, rows, output_path=output_path, striped=True,
        footnote=(f"Across {of_games} regular-season games in a Bulls uniform.",),
        final=final,
    )


SLIDES = {
    "regular-season": ("season-regular.csv", render_season),
    "playoffs": ("season-playoffs.csv", render_season),
    "top-games-table": ("top-games.csv", render_top_games),
    "career-high-strip": ("career-highs.csv", render_career_high_strip),
    "career-high-grid": ("career-highs.csv", render_career_high_grid),
    "franchise-ranks": ("franchise-ranks.csv", render_franchise_ranks),  # hairlines
    "milestones": ("milestones.csv", render_milestones),
    "shot-diet": ("shot-diet.csv", render_shot_diet),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--slide", choices=sorted(SLIDES), action="append")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()

    for name in args.slide or sorted(SLIDES):
        source, renderer = SLIDES[name]
        path = renderer(
            args.data / source,
            args.output / f"taj-gibson-{name}.png",
            final=args.final,
        )
        print(path)


if __name__ == "__main__":
    main()
