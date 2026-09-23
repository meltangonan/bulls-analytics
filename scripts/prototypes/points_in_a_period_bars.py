"""Render the Bulls most-points-in-a-quarter or -half table (one slide per post).

Layout follows ``pull_up_points_bars.py``; rows come from
``points_in_a_period_data.py`` (the top ten plus anything tied with tenth,
up to 15 rows, regular season and playoffs together). Tied rows share a "T-n"
rank; playoff rows carry "(RD n GMm)". The asset is sized to fill the Canva
page frame edge to edge, so row height follows from the page shape.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.graphics import house
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica, rendered_width

DATA = _REPO / "docs/visuals/2026-09-16-most-points-in-a-half/data"
PRIMARY_HEADSHOTS = Path("/Users/meltangonan/projects/bulls-analytics/cache/headshots")
BOARDS = ["quarter", "half"]

FULL_ROWS, MAX_ROWS = 10, 15  # boards of 10+ rows fill the page frame
# Canva content width / chart-to-footer height. 3:4 matches the block-leaders page
# (compact two-line title, source line only below), which leaves the most body space.
PAGE_FRAMES = {"3:4": 0.84, "4:5": 1029.32 / 1101.0}
ROW_RATIO = 0.536  # portrait half-size and bar height as a share of row height
WIDTH = 2300
HEADER = 150
BOTTOM = 20
RANK_X = 98  # centre; wide enough for "T-10" at the stat-column size
# Portraits use a square frame (no width-preserving crop): Coby White's hair is 1.36x
# the standard width and would otherwise collide with the rank column.
PORTRAIT_X = 310
NAME_X = 465
BAR_LEFT = 1205
TEXT_GAP = 30  # minimum space between the name block and the bar
BAR_RIGHT = 1760  # bars get the width; they stay zero-based so length is proportional to points
SUPPORT_X = (1920, 2170)
NAME_DY, SUB_DY = 32, -44  # name/game-line offsets; the pair is optically centred on the row
SUB_SIZE = 26
WORD_GAP = 16
INK = house.BLACK
RED = house.RED
WIN = "#218347"
LOSS = "#B53939"
SUB_GREY = "#6E6963"
RULE = "#B8B0A8"


# Hand-sourced cut-outs for players NBA.com serves a silhouette for (see data/portraits_source).
POST_PORTRAITS = DATA / "portraits"


def _portrait_path(player_id: int) -> Path:
    local = POST_PORTRAITS / f"{int(player_id)}.png"
    if local.exists():
        return local
    primary = PRIMARY_HEADSHOTS / f"{int(player_id)}.png"
    return primary if primary.exists() else house.HEADSHOT_CACHE / f"{int(player_id)}.png"


def game_segments(row: pd.Series) -> list[tuple[str, str, str]]:
    """The context line as (text, colour, font style) runs, e.g. ``4Q Nov 23, 2019 @ CHA W``.

    Date and matchup spelling match the other game tables ("vs IND", "@ CHA").
    """
    date = pd.Timestamp(row.game_date)
    where = "vs" if bool(row.home) else "@"
    context = f"{date:%b} {date.day}, {date.year} {where} {row.opponent}"
    segments = [(row.split_label, INK, "bold")]
    segments.append((context, SUB_GREY, "oblique"))
    # A playoff or play-in game gets an asterisk, explained in the caption: the full
    # "(RD n GMm)" tag does not fit beside the game line or the name.
    expected_prefix = {"Regular Season": "002", "Playoffs": "004", "PlayIn": "005"}[row.season_type]
    if not str(int(row.game_id)).zfill(10).startswith(expected_prefix):
        raise ValueError(f"{row.player_name}: season type and game id disagree")
    marker = "" if row.season_type == "Regular Season" else "*"
    segments.append((row.result + marker, WIN if row.result == "W" else LOSS, "bold"))
    return segments


def draw_segments(ax, x: float, y: float, segments) -> None:
    """Lay differently styled runs left to right, one word gap apart; return the right edge."""
    for text, colour, style in segments:
        artist = ax.text(x, y, text, ha="left", va="center", fontsize=SUB_SIZE, color=colour,
                         fontproperties=helvetica(style), zorder=3)
        x += rendered_width(ax, artist) + WORD_GAP
    return x - WORD_GAP


def rank_label(row: pd.Series) -> str:
    return f"T-{int(row['rank'])}" if bool(row.tied) else str(int(row["rank"]))


def render(board: str, output_path: Path, *, page: str = "3:4", final: bool = False) -> Path:
    frame = pd.read_csv(DATA / f"top_{board}.csv")  # already in display order
    if not 1 <= len(frame) <= MAX_ROWS:
        raise ValueError(f"{board}: expected at most {MAX_ROWS} rows, found {len(frame)}")
    if not frame.pts.is_monotonic_decreasing or frame["rank"].max() > FULL_ROWS:
        raise ValueError(f"{board}: rows out of order or ranked past {FULL_ROWS}")
    if len(frame) > FULL_ROWS and (frame.pts.iloc[FULL_ROWS - 1:] != frame.pts.iloc[FULL_ROWS - 1]).any():
        raise ValueError(f"{board}: rows past {FULL_ROWS} must tie {FULL_ROWS}th place")
    if not frame.season.str[:4].astype(int).ge(1996).all():
        raise ValueError("Rows before 1996-97, where period data begins")
    if not (frame.pts == 2 * frame.fgm + frame.fg3m + frame.ftm).all():
        raise ValueError("Points do not match the shooting line")
    if not frame.result.isin(["W", "L"]).all():
        raise ValueError("Missing W/L")
    house.ensure_headshots(frame.player_id.astype(int).unique())

    # Short boards keep the ten-row height instead of stretching rows; the asset is shorter.
    frame_height = round(WIDTH / PAGE_FRAMES[page])
    row_h = (frame_height - HEADER - BOTTOM) / max(len(frame), FULL_ROWS)
    height = round(HEADER + BOTTOM + row_h * len(frame))
    bar_h = portrait_half = round(row_h * ROW_RATIO)
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, WIDTH), ylim=(0, height)); ax.axis("off")
    bold = helvetica("bold")
    header_y = height - 70
    ax.text(RANK_X, header_y, "#", ha="center", va="center", fontsize=32, color=INK, fontproperties=bold)
    ax.text(NAME_X, header_y, "PLAYER / GAME", ha="left", va="center", fontsize=32, color=INK, fontproperties=bold)
    ax.text(BAR_LEFT, header_y, "PTS", ha="left", va="center", fontsize=32, color=INK, fontproperties=bold)
    for x, label in zip(SUPPORT_X, ("FG", "3PT")):
        ax.text(x, header_y, label, ha="center", va="center", fontsize=32, color=INK, fontproperties=bold)
    top = height - HEADER
    ax.plot([0, WIDTH], [top + 12, top + 12], color=INK, linewidth=2.4)
    scale = (BAR_RIGHT - BAR_LEFT) / float(frame.pts.max())

    for i, row in frame.iterrows():
        y = top - row_h * (i + .5)
        if i % 2 == 0:
            ax.axhspan(y - row_h / 2, y + row_h / 2, color=RULE, alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + row_h / 2] * 2, color=RULE, linewidth=1.2, zorder=0)
        house.top_anchored_headshot_label(
            ax, _portrait_path(int(row.player_id)), PORTRAIT_X,
            y - row_h / 2 + portrait_half, portrait_half,
            crop_fraction=0.64, zorder=2,
        )
        ax.text(RANK_X, y, rank_label(row), ha="center", va="center", fontsize=38,
                color=INK, fontproperties=bold, zorder=3)
        name = ax.text(NAME_X, y + NAME_DY, str(row.player_name), ha="left", va="center", fontsize=42,
                       color=INK, fontproperties=bold, zorder=3)
        name_end = NAME_X + rendered_width(ax, name)
        line_end = draw_segments(ax, NAME_X, y + SUB_DY, game_segments(row))
        if max(name_end, line_end) > BAR_LEFT - TEXT_GAP:
            raise ValueError(f"{board}: {row.player_name}'s name block runs into the bar")
        values = (f"{int(row.fgm)}-{int(row.fga)}", f"{int(row.fg3m)}-{int(row.fg3a)}")
        for x, value in zip(SUPPORT_X, values):
            ax.text(x, y, value, ha="center", va="center", fontsize=38, color=INK, fontproperties=bold, zorder=3)
        width = float(row.pts) * scale
        ax.add_patch(FancyBboxPatch((BAR_LEFT, y - bar_h / 2), width, bar_h,
                                    boxstyle="round,pad=0,rounding_size=10", linewidth=0,
                                    facecolor=RED, zorder=1))
        ax.text(BAR_LEFT + width - 22, y, str(int(row.pts)), ha="right", va="center",
                fontsize=38, color="white", fontproperties=bold, zorder=3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    from PIL import Image
    with Image.open(output_path) as image:
        aspect = image.width / image.height
    if len(frame) >= FULL_ROWS and abs(aspect - PAGE_FRAMES[page]) > .005:
        raise ValueError(f"{board}: aspect {aspect:.3f} drifted from the {page} frame {PAGE_FRAMES[page]:.3f}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", choices=BOARDS + ["all"], required=True)
    parser.add_argument("--output-dir", type=Path, default=_REPO / "output/most-points-in-a-half")
    parser.add_argument("--page", choices=sorted(PAGE_FRAMES), default="3:4",
                        help="Canva page shape the asset is sized to fill")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    for board in BOARDS if args.board == "all" else [args.board]:
        print(render(board, args.output_dir / f"{board}.png", page=args.page, final=args.final))


if __name__ == "__main__":
    main()
