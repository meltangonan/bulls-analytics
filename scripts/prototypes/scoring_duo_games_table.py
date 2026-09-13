"""Render the Bulls' top combined-scoring duo games as a ranked table.

Structure follows the assist-duos table: paired portraits, two names tied to
the two halves of one split bar, and a continuous red card behind the total.
Surface treatment follows the newer pull-up and catch-and-shoot leaderboards:
alternating row bands, top-anchored portraits and flat fills rather than the
gradient bars the earlier duo table used.

Overtime games carry a period marker beside the matchup. Eight of the fifteen
rows went to overtime against 6.7% of all Bulls games since 2000-01, so the
marker is load-bearing rather than decorative.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from scripts.prototypes.top_game_performances import _display_date, _game_context_parts

from bulls.graphics import house
from bulls.graphics.house import (
    rendered_width,
    DRAFT_DPI,
    draw_accent_card,
    ensure_headshots,
    export_dpi,
    helvetica,
)

DEFAULT_DATA = _REPO / "docs/visuals/2026-09-13-top-scoring-duo-games/data/top15.csv"
DEFAULT_OUTPUT = _REPO / "output/top-scoring-duo-games/duo-games-top15.png"
PRIMARY_HEADSHOTS = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")

WIDTH = 3300
ROW_HEIGHT = 252
TOP_BOTTOM = 190

PORTRAIT_1_X = 140
PORTRAIT_2_X = 318
PORTRAIT_HALF = 116

NAME_X = 534
SWATCH_X = 506
SWATCH = 15

BAR_LEFT = 1170
BAR_SPAN = 960
BAR_HEIGHT = 124
BAR_RADIUS = 9
CARD_OVERLAP_Y = 30   # how far the total card rises past the header rule
HEADER_GAP = 50       # clear space each column header keeps from its neighbour
MIN_SEGMENT_LABEL = 62
NAME_1_DY = 36
NAME_2_DY = -28
GAME_X = 2657
DATE_DY = 32
RESULT_DY = -30
RESULT_SIZE = 26
RESULT_GAP = 14
OT_GAP = 16
NAME_SIZE = 35
NAME_GUTTER = 36  # clear space between the longest name and the bar column

TOTAL_LEFT = 2190
TOTAL_RIGHT = 2400
SHARE_X = 3083

INK = house.BLACK
RED = house.RED
GREY = "#5F5B57"
QUIET = "#6E6963"
RULE = "#B8B0A8"
BAND = "#B8B0A8"
# Same pair the pull-up table uses for signed text: darkened for small-type
# contrast on the warm Canva background rather than the brighter heat scale.
WIN = "#218347"
LOSS = "#B53939"


def _portrait_path(player_id: int) -> Path:
    """Prefer the primary checkout's cache so a worktree never populates one."""
    primary = PRIMARY_HEADSHOTS / f"{int(player_id)}.png"
    return primary if primary.exists() else house.HEADSHOT_CACHE / f"{int(player_id)}.png"


def _height(rows: int) -> int:
    needed = TOP_BOTTOM * 2 + rows * ROW_HEIGHT
    return ((needed + DRAFT_DPI - 1) // DRAFT_DPI) * DRAFT_DPI


def _game_lines(row: pd.Series) -> tuple[str, list[tuple[str, str]]]:
    """The date, and the second line as coloured segments.

    Date and matchup formatting come from the game-score post's helpers so both
    tables spell a game the same way. The only change is a space after "@",
    which matches the "vs " the same helper already emits.

    W and L carry colour, but the letter already states the result, so the
    colour reinforces rather than carries it (DESIGN.md, "Color and hierarchy").
    """
    date_label, matchup, result = _game_context_parts(row)
    matchup = matchup.replace("@", "@ ") if matchup.startswith("@") else matchup
    segments = [(matchup, INK, RESULT_GAP)]
    segments.append((result, WIN if result == "W" else LOSS if result == "L" else INK, OT_GAP))
    overtime = str(row.overtime_label)
    if overtime:
        segments.append((f"({overtime})", RED, 0))
    return date_label, segments


def _centered_segments(ax, centre: float, y: float, segments) -> None:
    """Draw one line built from differently coloured runs, centred as a whole.

    Each segment is (text, colour, gap-after). Matplotlib centres a single text
    artist, so a multi-colour line has to be measured first and then laid out
    left to right from a computed start.
    """
    widths = []
    for text, _, _ in segments:
        probe = ax.text(0, 0, text, fontsize=RESULT_SIZE, alpha=0,
                        fontproperties=helvetica("bold"))
        widths.append(rendered_width(ax, probe))
        probe.remove()
    total = sum(widths) + sum(gap for _, _, gap in segments[:-1])
    x = centre - total / 2
    for (text, colour, gap), width in zip(segments, widths):
        italic = text.startswith("(")   # the overtime tag stays italic
        ax.text(x, y, text, ha="left", va="center", fontsize=RESULT_SIZE, color=colour,
                fontproperties=helvetica("bold_oblique" if italic else "bold"), zorder=3)
        x += width + gap


def _rounded(x0: float, x1: float, y: float, height: float, **kwargs) -> FancyBboxPatch:
    """A rounded box whose outer bounds are exactly (x0, x1) and height."""
    return FancyBboxPatch(
        (x0 + BAR_RADIUS, y - height / 2 + BAR_RADIUS),
        max(x1 - x0 - 2 * BAR_RADIUS, 0.1),
        height - 2 * BAR_RADIUS,
        boxstyle=f"round,pad={BAR_RADIUS},rounding_size={BAR_RADIUS}",
        **kwargs,
    )


def _draw_split_bar(ax, left: float, split: float, end: float, y: float) -> None:
    """One bar broken by colour: red is the game's leading scorer, black the second.

    Both halves are clipped to a single rounded outline so only the outer ends
    round off and the split stays a hard vertical edge. That keeps it reading as
    one game's points rather than two pills pushed together.
    """
    outline = _rounded(left, end, y, BAR_HEIGHT, facecolor="none", edgecolor="none", zorder=2)
    ax.add_patch(outline)
    for x0, x1, colour in ((left, split, RED), (split, end, INK)):
        patch = ax.add_patch(
            plt.Rectangle(
                (x0, y - BAR_HEIGHT / 2), max(x1 - x0, 0.1), BAR_HEIGHT,
                facecolor=colour, edgecolor="none", zorder=2,
            )
        )
        patch.set_clip_path(outline)


def _segment_label(ax, x0: float, x1: float, y: float, value: int) -> None:
    """Print a segment's points inside it, or just outside when it is too narrow."""
    width = x1 - x0
    if width >= MIN_SEGMENT_LABEL:
        ax.text((x0 + x1) / 2, y, f"{value}", ha="center", va="center", fontsize=34,
                color="white", fontproperties=helvetica("bold"), zorder=4)
    else:
        ax.text(x1 + 16, y, f"{value}", ha="left", va="center", fontsize=34,
                color=INK, fontproperties=helvetica("bold"), zorder=4)


def render(data_path: Path, output_path: Path, *, final: bool = False) -> Path:
    required = {
        "rank", "player_1_id", "player_1_label", "player_1_points",
        "player_2_id", "player_2_label", "player_2_points",
        "combined_points", "team_share_pct", "season_label", "matchup",
        "result", "overtime_label", "team_points", "game_date",
    }
    frame = pd.read_csv(data_path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    frame = frame.sort_values("rank", kind="stable").reset_index(drop=True)
    frame["overtime_label"] = frame["overtime_label"].fillna("")
    if (frame["player_1_points"] < frame["player_2_points"]).any():
        raise ValueError("player_1 must be the game's leading scorer.")
    if not (frame["player_1_points"] + frame["player_2_points"]).eq(frame["combined_points"]).all():
        raise ValueError("combined_points must equal the two printed scores.")

    ensure_headshots(
        pd.concat([frame["player_1_id"], frame["player_2_id"]]).astype(int).unique()
    )

    rows = len(frame)
    height = _height(rows)
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")

    first_y = height - TOP_BOTTOM - ROW_HEIGHT / 2
    scale = BAR_SPAN / float(frame["combined_points"].max())

    # Header, then the card, then the header rule broken at the card's bounds.
    header_y = height - TOP_BOTTOM + 92
    ax.text(NAME_X, header_y, "DUO", ha="left", va="center", fontsize=30,
            color=INK, fontproperties=helvetica("bold"), zorder=3)
    ax.text(BAR_LEFT, header_y, "POINTS", ha="left", va="center", fontsize=30,
            color=INK, fontproperties=helvetica("bold"), zorder=3)
    ax.text((TOTAL_LEFT + TOTAL_RIGHT) / 2, header_y, "TOTAL", ha="center", va="center",
            fontsize=30, color=RED, fontproperties=helvetica("bold"), zorder=6)
    ax.text(GAME_X, header_y, "GAME", ha="center", va="center", fontsize=30,
            color=INK, fontproperties=helvetica("bold"), zorder=3)
    share_header = ax.text(SHARE_X, header_y, "% OF TEAM", ha="center", va="center",
                           fontsize=30, color=INK, fontproperties=helvetica("bold"), zorder=3)

    card = draw_accent_card(ax, TOTAL_LEFT, TOTAL_RIGHT, first_y, rows, ROW_HEIGHT,
                            zorder=4, overlap_y=CARD_OVERLAP_Y)
    card_left, card_right, _, _ = card

    half = rendered_width(ax, share_header) / 2
    if SHARE_X + half > WIDTH:
        raise ValueError("The share header runs off the canvas; widen it or move SHARE_X left.")
    if SHARE_X - half < card_right + HEADER_GAP:
        raise ValueError(
            "The share header crowds the total card; widen the canvas or move SHARE_X right."
        )

    rule_y = height - TOP_BOTTOM + 18
    for x0, x1 in ((0, card_left), (card_right, WIDTH)):
        ax.plot([x0, x1], [rule_y, rule_y], color=INK, linewidth=2.2, zorder=3)

    for i, row in frame.iterrows():
        y = first_y - i * ROW_HEIGHT
        if i % 2 == 0:
            ax.axhspan(y - ROW_HEIGHT / 2, y + ROW_HEIGHT / 2, color=BAND, alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + ROW_HEIGHT / 2] * 2, color=RULE, linewidth=1.1, zorder=0)

        portrait_y = y - ROW_HEIGHT / 2 + PORTRAIT_HALF
        for x, player_id, z in (
            (PORTRAIT_2_X, int(row.player_2_id), 2),
            (PORTRAIT_1_X, int(row.player_1_id), 3),
        ):
            house.top_anchored_headshot_label(
                ax, _portrait_path(player_id), x, portrait_y, PORTRAIT_HALF,
                crop_fraction=0.64, preserve_width=True, zorder=z,
            )

        for dy, label, colour in (
            (NAME_1_DY, str(row.player_1_label), RED),
            (NAME_2_DY, str(row.player_2_label), INK),
        ):
            ax.add_patch(plt.Rectangle(
                (SWATCH_X - SWATCH, y + dy - SWATCH / 2), SWATCH, SWATCH,
                facecolor=colour, edgecolor="none", zorder=3,
            ))
            name = ax.text(NAME_X, y + dy, label, ha="left", va="center", fontsize=NAME_SIZE,
                           color=INK, fontproperties=helvetica("bold"), zorder=3)
            overrun = NAME_X + rendered_width(ax, name) + NAME_GUTTER - BAR_LEFT
            if overrun > 0:
                raise ValueError(
                    f"'{label}' overruns the bar column by {overrun:.0f}px; "
                    "widen the canvas or move BAR_LEFT right."
                )

        split = BAR_LEFT + float(row.player_1_points) * scale
        end = BAR_LEFT + float(row.combined_points) * scale
        _draw_split_bar(ax, BAR_LEFT, split, end, y)
        _segment_label(ax, BAR_LEFT, split, y, int(row.player_1_points))
        _segment_label(ax, split, end, y, int(row.player_2_points))

        ax.text((TOTAL_LEFT + TOTAL_RIGHT) / 2, y, f"{int(row.combined_points)}",
                ha="center", va="center", fontsize=46, color="white",
                fontproperties=helvetica("bold"), zorder=6)

        date_label, segments = _game_lines(row)
        ax.text(GAME_X, y + DATE_DY, date_label, ha="center", va="center", fontsize=28,
                color=INK, fontproperties=helvetica("bold"), zorder=3)
        _centered_segments(ax, GAME_X, y + RESULT_DY, segments)

        ax.text(SHARE_X, y, f"{float(row.team_share_pct):.0f}%", ha="center", va="center",
                fontsize=40, color=INK, fontproperties=helvetica("bold"), zorder=3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    print(render(args.data, args.output, final=args.final))


if __name__ == "__main__":
    main()
