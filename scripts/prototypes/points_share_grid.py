"""Render the 2025-26 Bulls share of team points as a 10x10 headshot grid.

Each square is 1% of the team's regular-season points, scored as a Bull. Shares
are rounded to whole squares by largest remainder so the grid totals exactly 100.
Squares fill in snake order (rows alternate direction) so every player's block is
one connected shape; each block gets its own rounded outline, a gap and a pale
tint that differs from every touching block. The asset is transparent and sized
to fill a 1080x1440 Canva page frame (0.887).

    venv/bin/python scripts/prototypes/points_share_grid.py [--final]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.graphics.house import BLACK, DRAFT_DPI, export_dpi, helvetica  # noqa: E402

POST = ROOT / "docs" / "visuals" / "2026-10-04-points-share-grid"
DATA = POST / "data" / "bulls_2025_26_player_game_logs.csv"
# NBA.com 1040x760 cut-outs, fetched 2026-10-04 (cdn.nba.com/headshots/nba/latest).
PORTRAITS = POST / "data" / "portraits"
DEFAULT_OUTPUT = ROOT / "output" / "2026-10-04-points-share-grid" / "points_share_grid.png"

# Sum of TeamGameLogs PTS over 82 regular-season games; no play-in or playoffs.
TEAM_TOTAL = 9537
COLS = 10

WIDTH = 1030  # placed width on a 1080 px Canva page
HEIGHT = round(WIDTH / 0.887)  # fills the 3:4 page frame
KEY_COLS, KEY_ROW, KEY_GAP = 5, 34, 22
GRID = HEIGHT - KEY_GAP - 5 * KEY_ROW
INSET, RADIUS, STROKE = 5.0, 16.0, 4.0  # px: half the gap between blocks, corner radius, outline
# Square crop from the 1040x760 NBA headshot with transparent headroom above
# the hair, so the top outline never touches a head.
FACE_BOX = (270, -5, 770, 495)
MUTED = "#5F5B57"
# Pale cool tints behind each block, rotated so touching blocks never share one.
# They only separate neighbors and carry no meaning. Cool hues stay clear of skin
# tones and of the warm #E9E5E1 Canva page (neutral and red options: v08 assets).
TINTS = ["#CAD3D9", "#D0D7CB", "#D4D0DC", "#C9D5D6"]


def prepare(path: Path = DATA) -> pd.DataFrame:
    """Points per player as a Bull, share of team points, and whole squares."""
    logs = pd.read_csv(path)
    pts = logs.groupby(["PLAYER_ID", "PLAYER_NAME"], as_index=False).PTS.sum()
    if pts.PTS.sum() != TEAM_TOTAL:
        raise ValueError(f"player points {pts.PTS.sum()} != team total {TEAM_TOTAL}")
    pts["SHARE"] = 100 * pts.PTS / TEAM_TOTAL
    pts["SQUARES"] = largest_remainder(pts.SHARE)
    return pts.sort_values("PTS", ascending=False, kind="stable").reset_index(drop=True)


def largest_remainder(shares: pd.Series, total: int = COLS * COLS) -> pd.Series:
    floor = np.floor(shares).astype(int)
    extra = (shares - floor).sort_values(ascending=False, kind="stable").index[: total - floor.sum()]
    floor[extra] += 1
    return floor


def short_name(name: str) -> str:
    first, rest = name.split(" ", 1)
    # Two Millers played; the initial keeps the key and footnote unambiguous.
    return f"{first[0]}. {rest}" if rest == "Miller" else rest


def snake_cells(players: pd.DataFrame) -> dict[int, set[tuple[int, int]]]:
    """(row, col) cells per player, filling rows alternately left and right."""
    cells: dict[int, set[tuple[int, int]]] = {}
    i = 0
    for pid, n in zip(players.PLAYER_ID, players.SQUARES):
        for _ in range(int(n)):
            r, c = divmod(i, COLS)
            cells.setdefault(int(pid), set()).add((r, c if r % 2 == 0 else COLS - 1 - c))
            i += 1
    return cells


def outline(cells: set[tuple[int, int]]) -> list[tuple[int, int]]:
    """Clockwise (screen coordinates) corners around one connected block of cells."""
    nxt = {}
    for r, c in cells:
        if (r - 1, c) not in cells:
            nxt[(c, r)] = (c + 1, r)
        if (r, c + 1) not in cells:
            nxt[(c + 1, r)] = (c + 1, r + 1)
        if (r + 1, c) not in cells:
            nxt[(c + 1, r + 1)] = (c, r + 1)
        if (r, c - 1) not in cells:
            nxt[(c, r + 1)] = (c, r)
    start = min(nxt)
    pts, p = [start], nxt[start]
    while p != start:
        pts.append(p)
        p = nxt[p]
    if len(pts) != len(nxt):
        raise ValueError("block is not one connected shape")
    n = len(pts)
    return [
        pts[i] for i in range(n)
        if (pts[i - 1][0] == pts[i][0]) != (pts[i][0] == pts[(i + 1) % n][0])
    ]


def rounded_inset(corners, size: float, x0: float, y0: float) -> MplPath:
    """Shrink a right-angled outline by INSET px and round every corner."""
    n = len(corners)
    pts = []
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = corners[i - 1], corners[i], corners[(i + 1) % n]
        # Clockwise in screen coordinates: the inward normal of (dx, dy) is (-dy, dx).
        n1 = (-np.sign(by - ay), np.sign(bx - ax))
        n2 = (-np.sign(cy - by), np.sign(cx - bx))
        pts.append(
            np.array([x0 + bx * size + INSET * (n1[0] + n2[0]),
                      y0 + by * size + INSET * (n1[1] + n2[1])])
        )

    def toward(p, q):
        return p + (q - p) * RADIUS / np.linalg.norm(q - p)

    verts, codes = [], []
    for i in range(n):
        cur = pts[i]
        verts += [toward(cur, pts[i - 1]), cur, toward(cur, pts[(i + 1) % n])]
        codes += [MplPath.MOVETO if i == 0 else MplPath.LINETO, MplPath.CURVE3, MplPath.CURVE3]
    verts.append(verts[0])
    codes.append(MplPath.CLOSEPOLY)
    return MplPath(verts, codes)


def assign_tints(blocks: dict[int, set[tuple[int, int]]], palette: list[str]) -> dict[int, str]:
    """Rotate through the palette in rank order, skipping colors a touching block holds."""
    owner = {cell: pid for pid, cells in blocks.items() for cell in cells}
    tints: dict[int, str] = {}
    for rank, (pid, cells) in enumerate(blocks.items()):
        taken = {
            tints.get(owner.get((r + dr, c + dc)))
            for r, c in cells for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
        }
        k = len(palette)
        tints[pid] = next(
            palette[(rank + j) % k] for j in range(k) if palette[(rank + j) % k] not in taken
        )
    return tints


def face(player_id: int) -> np.ndarray:
    im = Image.open(PORTRAITS / f"{player_id}.png").convert("RGBA")
    return np.asarray(im.crop(FACE_BOX).resize((400, 400), Image.LANCZOS))


def render(
    players: pd.DataFrame, output: Path, *, final: bool = False
) -> Path:
    shown = players[players.SQUARES > 0]
    px = 72 / DRAFT_DPI  # points per layout pixel
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, HEIGHT / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(HEIGHT, 0)
    ax.axis("off")

    size = GRID / COLS
    x0 = (WIDTH - GRID) / 2
    blocks = snake_cells(shown)
    tints = assign_tints(blocks, TINTS)
    for pid, cells in blocks.items():
        path = rounded_inset(outline(cells), size, x0, 0)
        clip = PathPatch(path, transform=ax.transData)
        ax.add_patch(PathPatch(path, facecolor=tints[pid], edgecolor="none", zorder=0))
        img = face(pid)
        for r, c in cells:
            x, y = x0 + c * size, r * size
            art = ax.imshow(img, extent=(x, x + size, y + size, y), interpolation="antialiased",
                            zorder=1)
            art.set_clip_path(clip)
            if (r - 1, c) not in cells:
                # Tall hair overlaps the block's top outline instead of being cut by it:
                # redraw only the band from the cell top through the line, above the line.
                over = ax.imshow(img, extent=(x, x + size, y + size, y),
                                 interpolation="antialiased", zorder=4)
                over.set_clip_path(Rectangle((x, y), size, INSET + STROKE, transform=ax.transData))
        ax.add_patch(PathPatch(path, fill=False, edgecolor=BLACK, linewidth=STROKE * px, zorder=3))

    # The key spans the grid's outline edges, with a gutter between columns.
    key_left, key_right, gutter = x0 + INSET, x0 + GRID - INSET, 22
    col_w = (key_right - key_left + gutter) / KEY_COLS
    renderer = fig.canvas.get_renderer()
    for i, row in enumerate(shown.itertuples()):
        r, c = divmod(i, KEY_COLS)
        y = GRID + KEY_GAP + r * KEY_ROW + KEY_ROW / 2
        left = key_left + c * col_w
        name = ax.text(left, y, short_name(row.PLAYER_NAME), va="center", ha="left",
                       color=BLACK, fontproperties=helvetica("bold"), fontsize=20 * px)
        # The share follows its name a word space later, measured from the drawn text.
        box = name.get_window_extent(renderer).transformed(ax.transData.inverted())
        ax.text(box.x1 + 7, y, f"{row.SHARE:.1f}%", va="center", ha="left",
                color=MUTED, fontproperties=helvetica("regular"), fontsize=20 * px)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output


def canva_copy(players: pd.DataFrame) -> str:
    hidden = players[players.SQUARES == 0]
    return (
        f"Subtitle: {len(players)} players, {TEAM_TOTAL:,} points. "
        "Each face is 1% of the team's points.\n"
        "Footnote: 2025-26 regular season, points scored as a Bull. Squares rounded to whole "
        f"percents. Not shown, under 0.5%: {', '.join(short_name(n) for n in hidden.PLAYER_NAME)}. "
        "Source: NBA.com."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    players = prepare()
    print(render(players, args.output, final=args.final))
    print(canva_copy(players))


if __name__ == "__main__":
    main()
