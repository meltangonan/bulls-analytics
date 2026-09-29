"""Render Bulls single-season points off turnovers leaders as a table-bar hybrid.

The fast break points layout: season points off turnovers are the bar; NBA rank (top ten
in green), per game and the share of the player's points sit to the right.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bulls.graphics import house
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica


DEFAULT_DATA = ROOT / "docs/visuals/2026-09-29-points-off-turnovers/data/top15.csv"
DEFAULT_OUTPUT = ROOT / "output/points-off-turnovers/table.png"
POST_PORTRAITS = ROOT / "docs/visuals/2026-09-29-points-off-turnovers/data/portraits"
# Hand-supplied originals for players NBA.com serves a silhouette for (see SOURCES.md).
PORTRAIT_SOURCES: dict[int, Path] = {}
PRIMARY = Path("/Users/meltangonan/projects/bulls-analytics")
PRIMARY_HEADSHOTS = PRIMARY / "cache/headshots"
# Hand-framed cut-outs saved by earlier posts, reused before NBA.com.
EARLIER_PORTRAITS = [ROOT / "docs/visuals", PRIMARY / "docs/visuals"]
WIDTH = 3240
TOP_BOTTOM = 175
PAGE_FRAMES = {"3:4": 0.84, "4:5": 1029.32 / 1101.0}
PORTRAIT_X = 155
NAME_X = 330
BAR_LEFT = 1100  # clears the widest names on these boards at the approved 41.5 pt
BAR_RIGHT = 2080
SUPPORT_X = (2340, 2690, 3040)
SUPPORT_HEADERS = (("NBA", "RANK"), ("PER", "GAME"), ("% OF", "POINTS"))
RIGHT_MARGIN = 80
ROW_RATIO = 0.536
INK = house.BLACK
RED = house.RED
SEASON_GREY = "#6E6963"
RULE = "#B8B0A8"
# NBA.com lists the suffix; the account uses the familiar name.
DISPLAY_NAMES = {202710: "Jimmy Butler"}
TOP_TEN_GREEN = "#218347"  # Shared dark conditional green for readable table text.
NAME_SIZE = 41.5
SEASON_SIZE = 28.5
STAT_SIZE = 39
NAME_SEASON_GAP = 70
# Draft-only escape hatch; --final always refuses a silhouette.
ALLOW_SILHOUETTE = False


def build_post_portraits() -> None:
    """Rebuild post-local cut-outs from the supplied originals."""
    for player_id, source in PORTRAIT_SOURCES.items():
        house.cut_out_flat_background(source, POST_PORTRAITS / f"{player_id}.png")


def _portrait_path(player_id: int) -> Path:
    """Post-local cut-out first (hand-sourced where NBA.com serves a silhouette)."""
    local = POST_PORTRAITS / f"{player_id}.png"
    if local.exists():
        return local
    for visuals in EARLIER_PORTRAITS:
        earlier = sorted(visuals.glob(f"*/data/portraits/{player_id}.png"))
        if earlier:
            return earlier[-1]
    house.ensure_headshots([player_id])
    primary = PRIMARY_HEADSHOTS / f"{player_id}.png"
    path = primary if primary.exists() else house.HEADSHOT_CACHE / f"{player_id}.png"
    if _is_silhouette(path) and not ALLOW_SILHOUETTE:
        raise ValueError(f"NBA.com serves a silhouette for player {player_id}; source a portrait")
    return path


def _is_silhouette(path: Path) -> bool:
    """NBA.com's placeholder is a flat grey figure: almost no colour variation."""
    import numpy as np
    from PIL import Image
    pixels = np.array(Image.open(path).convert("RGBA"))
    body = pixels[pixels[:, :, 3] > 128][:, :3].astype(int)
    return len(body) > 0 and float(body.std()) < 12


def _ordinal(value: int) -> str:
    suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _center_identity(ax, name, season, y: float) -> None:
    """Shift the name/season pair so its rendered block is centred on the row."""
    ax.figure.canvas.draw()
    inverse = ax.transData.inverted()
    boxes = [artist.get_window_extent() for artist in (name, season)]
    top = inverse.transform((0, boxes[0].y1))[1]
    bottom = inverse.transform((0, boxes[1].y0))[1]
    shift = y - (top + bottom) / 2
    for artist in (name, season):
        artist.set_y(artist.get_position()[1] + shift)


def _row_height(rows: int, aspect: float) -> int:
    return round((WIDTH / aspect - 2 * TOP_BOTTOM) / rows)


def render(data_path: Path, output_path: Path, *, final: bool = False, page: str = "3:4") -> Path:
    required = {"player_id", "player_name", "season", "points", "nba_rank",
                "points_per_game", "share_of_points"}
    frame = pd.read_csv(data_path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    frame = frame.sort_values(
        ["points", "points_per_game", "season"],
        ascending=[False, False, True], kind="stable",
    ).reset_index(drop=True)

    row_height = _row_height(len(frame), PAGE_FRAMES[page])
    portrait_half = round(row_height * ROW_RATIO)
    bar_height = portrait_half
    height = TOP_BOTTOM * 2 + len(frame) * row_height
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    bold = helvetica("bold")
    first_y = height - TOP_BOTTOM - row_height / 2
    header_y = height - TOP_BOTTOM + 66
    scale = (BAR_RIGHT - BAR_LEFT) / float(frame["points"].max())

    ax.text(NAME_X, header_y, "PLAYER / SEASON", ha="left", va="center", fontsize=31,
            color=INK, fontproperties=bold)
    ax.text(BAR_LEFT, header_y, "POINTS OFF TURNOVERS", ha="left", va="center", fontsize=31,
            color=INK, fontproperties=bold)
    for x, lines in zip(SUPPORT_X, SUPPORT_HEADERS):
        for line_index, line in enumerate(lines):
            ax.text(x, header_y + (1 - line_index) * 62, line, ha="center", va="center",
                    fontsize=30, color=INK, fontproperties=bold)
    ax.plot([0, WIDTH], [height - TOP_BOTTOM + 15] * 2, color=INK, linewidth=2.0)

    for i, row in frame.iterrows():
        y = first_y - i * row_height
        if i % 2 == 0:
            ax.axhspan(y - row_height / 2, y + row_height / 2, color=RULE, alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + row_height / 2] * 2, color=RULE, linewidth=1.1, zorder=0)

        house.top_anchored_headshot_label(
            ax, _portrait_path(int(row.player_id)), PORTRAIT_X,
            y - row_height / 2 + portrait_half, portrait_half,
            crop_fraction=.64, preserve_width=True, zorder=2,
        )
        name = ax.text(NAME_X, y + NAME_SEASON_GAP / 2, DISPLAY_NAMES.get(int(row.player_id), str(row.player_name)), ha="left",
                       va="center", fontsize=NAME_SIZE, color=INK, fontproperties=bold, zorder=3)
        if NAME_X + house.rendered_width(ax, name) > BAR_LEFT - 20:
            raise ValueError(f"{row.player_name} overruns the bar column")
        season = ax.text(NAME_X, y - NAME_SEASON_GAP / 2, str(row.season), ha="left",
                         va="center", fontsize=SEASON_SIZE, color=SEASON_GREY,
                         fontproperties=helvetica("oblique"), zorder=3)
        _center_identity(ax, name, season, y)

        value = int(row.points)
        width = value * scale
        ax.add_patch(FancyBboxPatch(
            (BAR_LEFT, y - bar_height / 2), width, bar_height,
            boxstyle="round,pad=0,rounding_size=8", linewidth=0, facecolor=RED, zorder=1,
        ))
        ax.text(BAR_LEFT + width - 18, y, f"{value:,}", ha="right", va="center",
                fontsize=STAT_SIZE, color="white", fontproperties=bold, zorder=3)
        cells = (
            _ordinal(int(row.nba_rank)),
            f"{float(row.points_per_game):.1f}",
            f"{100 * float(row.share_of_points):.0f}%",
        )
        colors = (TOP_TEN_GREEN if int(row.nba_rank) <= 10 else INK, INK, INK)
        for x, text, color in zip(SUPPORT_X, cells, colors):
            ax.text(x, y, text, ha="center", va="center", fontsize=STAT_SIZE, color=color,
                    fontproperties=bold, zorder=3)

    if SUPPORT_X[-1] >= WIDTH - RIGHT_MARGIN:
        raise ValueError("Supporting columns exceed the right margin")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--page", choices=sorted(PAGE_FRAMES), default="3:4")
    parser.add_argument("--allow-silhouette", action="store_true",
                        help="draft only: render NBA.com placeholders instead of stopping")
    args = parser.parse_args()
    if args.allow_silhouette and args.final:
        parser.error("--allow-silhouette is for drafts; source the portrait before --final")
    global ALLOW_SILHOUETTE
    ALLOW_SILHOUETTE = args.allow_silhouette
    build_post_portraits()
    print(render(args.data, args.output, final=args.final, page=args.page))


if __name__ == "__main__":
    main()
