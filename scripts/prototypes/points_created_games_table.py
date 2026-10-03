"""Render verified top-15-plus-ties Bulls single-game points created in the season post's split-bar format.

Larger type at the same 1030 px placement; game context replaces season/MVP,
with exact NBA season rank and share of that game's Chicago points.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bulls.graphics import house
from scripts.prototypes.top_game_performances import _game_context_parts

PROJECT = ROOT / "docs/visuals/2026-10-02-points-created-games"
WIDTH, ROW, PAD = 3500, 238, 190
RANK_X, PORTRAIT_X = 85, 320
NAME_X, BAR_LEFT, BAR_SPAN = 505, 1410, 900
TOTAL_LEFT, TOTAL_RIGHT, NBA_X, SHARE_X = 2390, 2660, 2915, 3310
INK, RED, ASSIST = house.BLACK, house.RED, "#77716B"
QUIET, RULE = "#625D58", "#B8B0A8"


def load_data(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"GAME_ID": str})
    required = {"PLAYER_ID", "PLAYER_NAME", "PTS", "assist_pts", "created",
                "team_pts", "team_pct", "GAME_DATE", "MATCHUP", "WL", "status", "overtimes", "rank",
                "nba_season_rank", "nba_season_rank_label", "nba_season_rank_status"}
    if missing := required - set(frame.columns):
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if not frame.status.eq("exact").all() or frame.overtimes.isna().any():
        raise ValueError("Every displayed game needs exact assists and verified overtime")
    if (not frame.nba_season_rank_status.eq("complete").all()
            or frame.nba_season_rank.isna().any()
            or not frame.nba_season_rank.ge(1).all()
            or not frame.nba_season_rank.eq(frame.nba_season_rank.astype(int)).all()
            or frame.nba_season_rank_label.isna().any()):
        raise ValueError("Every displayed NBA season rank must be completely verified")
    if len(frame) < 15 or not frame.created.eq(frame.PTS + frame.assist_pts).all():
        raise ValueError("Expected top 15 plus cutoff ties with verified scoring-plus-assist totals")
    if not ((frame.created / frame.team_pts * 100 - frame.team_pct).abs() < .051).all():
        raise ValueError("Team shares do not match game scoring denominators")
    if not frame.created.is_monotonic_decreasing:
        raise ValueError("Selection must be sorted by points created")
    expected_ranks = frame.created.rank(method="min", ascending=False).astype(int)
    if not frame["rank"].eq(expected_ranks).all():
        raise ValueError("Displayed ranks must preserve statistical ties")
    if len(frame) > 15 and not frame.iloc[14:].created.eq(frame.iloc[14].created).all():
        raise ValueError("Extra rows must belong to the cutoff tie")
    frame["PLAYER_NAME"] = frame.PLAYER_NAME.replace({"Jimmy Butler III": "Jimmy Butler"})
    return frame


def render(data: Path, output: Path, final: bool = False) -> Path:
    frame = load_data(data)
    height = 2 * PAD + ROW * len(frame)
    fig = plt.figure(figsize=(WIDTH / house.DRAFT_DPI, height / house.DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH); ax.set_ylim(0, height); ax.axis("off")

    def text(x, y, label, size=42, color=INK, align="center", weight="bold", z=5):
        return ax.text(x, y, label, fontsize=size, fontproperties=house.helvetica(weight),
                       color=color, ha=align, va="center", multialignment="left", zorder=z)

    def checked(x, y, label, size, right, **kwargs):
        artist = text(x, y, label, size, align="left", **kwargs)
        if x + house.rendered_width(ax, artist) > right:
            raise ValueError(f"Text too wide: {label}")
        return artist

    first = height - PAD - ROW / 2
    hy = height - PAD + 111  # Raise labels 5 px at the standard 1030 px placement.
    text(RANK_X, hy, "#", 34)
    text(NAME_X, hy, "PLAYER / GAME", 34, align="left")
    for x, color, label in [(BAR_LEFT, INK, "Points\nscored"),
                            (BAR_LEFT + 500, ASSIST, "Assist\npoints")]:
        ax.add_patch(Rectangle((x, hy + 16), 36, 36, facecolor=color, edgecolor="none"))
        checked(x + 56, hy, label, 34, TOTAL_LEFT - 40)
    text((TOTAL_LEFT + TOTAL_RIGHT) / 2, hy, "POINTS\nCREATED", 32, color=RED)
    text(NBA_X, hy, "SEASON\nRANK", 34)
    text(SHARE_X, hy, "% TEAM\nPOINTS", 34)
    card = house.draw_accent_card(ax, TOTAL_LEFT, TOTAL_RIGHT, first, len(frame), ROW,
                                  scale=WIDTH / 1500)
    for lo, hi in [(0, card[0]), (card[1], WIDTH)]:
        ax.plot([lo, hi], [height - PAD + 15] * 2, color=INK, linewidth=2, zorder=3)
    scale = BAR_SPAN / frame.created.max()
    identity_groups = []
    tied_ranks = frame.loc[frame["rank"].duplicated(keep=False), "rank"]
    for i, r in frame.iterrows():
        y = first - i * ROW
        if i % 2 == 0:
            ax.axhspan(y - ROW / 2, y + ROW / 2, color=RULE, alpha=.12, zorder=0)
        if i:
            ax.plot([0, WIDTH], [y + ROW / 2] * 2, color=RULE, lw=1, zorder=0)
        rank_label = ("T" if r["rank"] in tied_ranks.values else "") + str(int(r["rank"]))
        text(RANK_X, y, rank_label, 36)
        portrait = house.HEADSHOT_CACHE / f"{int(r.PLAYER_ID)}.png"
        if not portrait.exists():
            house.ensure_headshots([int(r.PLAYER_ID)])
        # Keep the existing face size, but place its bottom on its own row's
        # lower boundary. The extra height overlaps only the preceding row.
        portrait_artist = house.top_anchored_headshot_label(
            ax, portrait, PORTRAIT_X, y - ROW / 2 + 155, 155,
            crop_fraction=.74, preserve_width=True, zorder=4)
        bottom = (portrait_artist.get_extent()[2] if hasattr(portrait_artist, "get_extent")
                  else portrait_artist.get_y())
        if bottom < y - ROW / 2 - .001:
            raise ValueError(f"Portrait extends below its own row: {r.PLAYER_NAME}")
        group = [checked(NAME_X, y + 28, r.PLAYER_NAME, 45.5, BAR_LEFT - 35)]
        date, matchup, result = _game_context_parts(pd.Series(
            {"game_date": r.GAME_DATE, "matchup": r.MATCHUP, "result": r.WL}))
        periods = int(r.overtimes)
        ot = "OT" if periods == 1 else f"{periods}OT" if periods > 1 else ""
        # Standard game table: one regular-weight date/matchup line, bold W/L
        # in its established color, and overtime at the same baseline.
        runs = [(date, QUIET, "regular"), (matchup, QUIET, "regular"),
                (result, "#3FAE63" if result == "W" else "#D64545", "bold")]
        if ot:
            runs.append((f"({ot})", QUIET, "regular"))
        x = NAME_X
        for label, color, weight in runs:
            # Increase the name/game gap by 2 px at the 1030 px Canva width,
            # then center both lines together from their rendered bounds below.
            artist = checked(x, y - 49 - 2 * WIDTH / 1030, label, 31.5, BAR_LEFT - 35,
                             color=color, weight=weight)
            group.append(artist)
            x += house.rendered_width(ax, artist) + 21
        identity_groups.append((y, group))
        end = BAR_LEFT + r.created * scale
        split = BAR_LEFT + r.PTS * scale
        bh = 120
        clip = FancyBboxPatch((BAR_LEFT, y - bh / 2), end - BAR_LEFT, bh,
                             boxstyle="round,pad=0,rounding_size=9", facecolor="none", edgecolor="none")
        ax.add_patch(clip)
        for lo, hi, color, value in [(BAR_LEFT, split, INK, r.PTS),
                                     (split, end, ASSIST, r.assist_pts)]:
            patch = ax.add_patch(Rectangle((lo, y - bh / 2), hi - lo, bh,
                                          facecolor=color, edgecolor="none", zorder=2))
            patch.set_clip_path(clip)
            label = text((lo + hi) / 2, y, str(int(value)), 41.5, color="white")
            if house.rendered_width(ax, label) > hi - lo - 24:
                raise ValueError(f"Bar label too wide: {r.PLAYER_NAME}")
        text((TOTAL_LEFT + TOTAL_RIGHT) / 2, y, str(int(r.created)), 46, color="white", z=6)
        text(NBA_X, y, r.nba_season_rank_label, 42,
             color="#218347" if int(r.nba_season_rank) <= 10 else INK)
        text(SHARE_X, y, f"{r.team_pct:.1f}%", 42)
    # Center the actual rendered name/game block, including all colored runs,
    # rather than averaging baselines of two differently sized text lines.
    fig.canvas.draw()
    inverse = ax.transData.inverted()
    for y, group in identity_groups:
        boxes = [artist.get_window_extent() for artist in group]
        top = inverse.transform((0, max(box.y1 for box in boxes)))[1]
        bottom = inverse.transform((0, min(box.y0 for box in boxes)))[1]
        shift = y - (top + bottom) / 2
        for artist in group:
            artist.set_y(artist.get_position()[1] + shift)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=house.export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    with Image.open(output) as image:
        bounds = image.getbbox()
        margin = round(20 * house.export_dpi(final) / house.DRAFT_DPI)
        image.crop((0, max(0, bounds[1] - margin), image.width,
                    min(image.height, bounds[3] + margin))).save(output, dpi=(house.export_dpi(final),) * 2)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROJECT / "data/top15.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "output/points-created-games/table.png")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    print(render(args.data, args.output, args.final))
