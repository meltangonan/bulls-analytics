"""Plot every Bulls rookie season since 2000 as production against quality.

The x-axis is PRA per 75 possessions: points, rebounds and assists at a common
pace, so 2001 and 2026 are comparable. The y-axis is a quality measure that
does not simply reward playing time, defaulting to BPM. Dot area is minutes
played, which puts the qualification question on the chart instead of in a
threshold: a rookie who barely played is a small dot, not an excluded row.

Net rating on/off was tested for the y-axis and rejected. NBA.com publishes it
only from 2007-08, and across the rookies it does cover it correlates +0.16
with BPM and -0.38 with minutes, which makes it closer to a small-sample
artifact than a measure of how good a rookie was.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle
from matplotlib.ticker import MaxNLocator

from bulls.graphics.house import (
    DEFAULT_THEME,
    ensure_headshots,
    ensure_silhouette,
    export_dpi,
    helvetica,
    portrait_path,
    square_headshot_label,
)
from bulls.visuals import DATA, visual_dir

PROJECT = "bulls-rookie-landscape"
MIN_MINUTES = 300
DATA_DIR = visual_dir(_REPO / "docs" / "visuals", PROJECT, when="2026-08-14") / DATA
COMPARISON_CSV = DATA_DIR / "bulls-rookie-metric-comparison.csv"
LEAGUE_TS_CSV = DATA_DIR / "nba-league-ts-by-season.csv"
DISPLAY_CSV = DATA_DIR / "bulls-rookie-landscape-scatter.csv"
OUTPUT_DIR = _REPO / "output" / "2026-08-14-bulls-rookie-landscape"

CHART_WIDTH = 1080
CHART_HEIGHT = 1080
PLOT_LEFT, PLOT_RIGHT = 92, 1046
PLOT_BOTTOM, PLOT_TOP = 86, 1024

# Mark radius in canvas pixels for the fewest and the most minutes in the pool.
# Faces and plain dots share one scale, so size always means playing time and
# never means "this player is the interesting one".
MIN_MARK_RADIUS = 13.0
MAX_MARK_RADIUS = 46.0
# Below this radius a face is no longer recognisable, so the rookie keeps a dot
# even when he was selected for a portrait.
MIN_FACE_RADIUS = 19.0
# Keep the top of the portrait only. A centre crop of an NBA headshot is mostly
# jersey, which is unreadable at the size these marks run.
FACE_CROP_FRACTION = 0.74

Y_AXES = {
    "bpm": ("bpm", "BOX PLUS/MINUS", "{:+.1f}"),
    "ts-rel": ("ts_rel", "TS% VS LEAGUE AVERAGE", "{:+.1f}"),
    "ws": ("ws", "WIN SHARES", "{:.1f}"),
}


def load_pool(min_minutes: int = MIN_MINUTES) -> pd.DataFrame:
    """Join the rookie working table to the season league-efficiency baseline."""
    rookies = pd.read_csv(COMPARISON_CSV)
    league = pd.read_csv(LEAGUE_TS_CSV).rename(columns={"season": "season_label"})
    joined = rookies.merge(
        league[["season_label", "league_ts_pct"]], on="season_label", how="left"
    )
    if joined["league_ts_pct"].isna().any():
        missing = joined.loc[joined["league_ts_pct"].isna(), "season_label"].unique()
        raise ValueError(f"No league TS baseline for {list(missing)}")
    joined["ts_rel"] = (joined["ts_pct"] - joined["league_ts_pct"]) * 100
    pool = joined.loc[joined["minutes"].ge(min_minutes)].copy()
    return pool.sort_values("minutes", ascending=False).reset_index(drop=True)


def mark_radii(minutes: pd.Series) -> np.ndarray:
    """Scale mark *area* with minutes, so the mark reads as playing time.

    Area rather than radius, because a circle twice as wide looks four times
    as big. Returns the radius each area implies, in canvas pixels.
    """
    low, high = float(minutes.min()), float(minutes.max())
    span = high - low
    fraction = np.zeros(len(minutes)) if span <= 0 else np.asarray((minutes - low) / span)
    areas = MIN_MARK_RADIUS ** 2 + fraction * (MAX_MARK_RADIUS ** 2 - MIN_MARK_RADIUS ** 2)
    return np.sqrt(areas)


def quadrant_split(values: pd.Series) -> float:
    """Divide on the pool median, the honest 'typical Bulls rookie' line."""
    return float(values.median())


def label_choices(pool: pd.DataFrame, x: str, y: str, count: int = 14) -> list[int]:
    """Name the rookies a reader would look for: the extremes on either axis.

    Labelling all 46 is unreadable, so this picks the corners and the biggest
    roles rather than a hand-kept list that would rot as seasons are added.
    """
    per_axis = count // 3 + 1
    candidates: list[int] = []
    for column, largest in ((x, True), (y, True), (y, False), ("minutes", True)):
        ordered = pool.nlargest(count, column) if largest else pool.nsmallest(count, column)
        candidates.extend(ordered.index.tolist()[:per_axis])
    # The four lists overlap heavily, so top up by minutes to always return
    # `count` names rather than however many survived the de-duplication.
    candidates.extend(pool.sort_values("minutes", ascending=False).index.tolist())
    chosen: list[int] = []
    for index in candidates:
        if index not in chosen:
            chosen.append(index)
        if len(chosen) == count:
            break
    return chosen


def face_choices(pool: pd.DataFrame, x: str, y: str, count: int) -> list[int]:
    """Pick which rookies are worth a face rather than a plain dot.

    The rule is the same one the labels use: the corners of the chart plus the
    biggest roles. That keeps the selection reproducible as seasons are added,
    instead of a hand-kept list of favourites that quietly rots.
    """
    return label_choices(pool, x, y, count)


def _axis_mapper(lo: float, hi: float, pixel_lo: float, pixel_hi: float):
    """Map a data value onto the canvas, the way the landscape family does."""
    span = hi - lo

    def to_pixels(value):
        fraction = 0.5 if span <= 0 else (np.asarray(value, dtype=float) - lo) / span
        return pixel_lo + fraction * (pixel_hi - pixel_lo)

    return to_pixels


def render(
    pool: pd.DataFrame,
    y_key: str,
    output_path: Path,
    faces: int = 0,
    final: bool = False,
) -> Path:
    """Render one transparent, Canva-ready scatter asset."""
    theme = DEFAULT_THEME
    y_column, y_label, _ = Y_AXES[y_key]
    x_column = "pra_per_75"

    radii = mark_radii(pool["minutes"])
    face_rows = set(face_choices(pool, x_column, y_column, faces)) if faces else set()

    x_pad = (pool[x_column].max() - pool[x_column].min()) * 0.09
    y_pad = (pool[y_column].max() - pool[y_column].min()) * 0.10
    x_lo, x_hi = pool[x_column].min() - x_pad, pool[x_column].max() + x_pad
    y_lo, y_hi = pool[y_column].min() - y_pad, pool[y_column].max() + y_pad
    to_x = _axis_mapper(x_lo, x_hi, PLOT_LEFT, PLOT_RIGHT)
    to_y = _axis_mapper(y_lo, y_hi, PLOT_BOTTOM, PLOT_TOP)

    fig = plt.figure(figsize=(CHART_WIDTH / 100, CHART_HEIGHT / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_aspect("equal")
    ax.axis("off")

    tick_font = helvetica("regular")
    axis_font = helvetica("bold")
    x_ticks = [t for t in MaxNLocator(6).tick_values(x_lo, x_hi) if x_lo <= t <= x_hi]
    y_ticks = [t for t in MaxNLocator(6).tick_values(y_lo, y_hi) if y_lo <= t <= y_hi]
    for tick in x_ticks:
        ax.plot([to_x(tick)] * 2, [PLOT_BOTTOM, PLOT_TOP], color=theme.grid,
                linewidth=0.9, zorder=0)
        ax.text(to_x(tick), PLOT_BOTTOM - 18, f"{tick:g}", ha="center", va="top",
                fontsize=10.5, color=theme.muted, fontproperties=tick_font)
    for tick in y_ticks:
        ax.plot([PLOT_LEFT, PLOT_RIGHT], [to_y(tick)] * 2, color=theme.grid,
                linewidth=0.9, zorder=0)
        ax.text(PLOT_LEFT - 14, to_y(tick), f"{tick:g}", ha="right", va="center",
                fontsize=10.5, color=theme.muted, fontproperties=tick_font)

    # The median lines split the chart into the four quadrants a reader expects,
    # against the typical Bulls rookie rather than an invented round number.
    x_split, y_split = quadrant_split(pool[x_column]), quadrant_split(pool[y_column])
    ax.plot([to_x(x_split)] * 2, [PLOT_BOTTOM, PLOT_TOP], color=theme.rule,
            linewidth=1.1, linestyle=(0, (5, 4)), zorder=1)
    ax.plot([PLOT_LEFT, PLOT_RIGHT], [to_y(y_split)] * 2, color=theme.rule,
            linewidth=1.1, linestyle=(0, (5, 4)), zorder=1)
    ax.plot([PLOT_LEFT, PLOT_LEFT], [PLOT_BOTTOM, PLOT_TOP], color=theme.rule,
            linewidth=1.2, zorder=1)
    ax.plot([PLOT_LEFT, PLOT_RIGHT], [PLOT_BOTTOM, PLOT_BOTTOM], color=theme.rule,
            linewidth=1.2, zorder=1)

    # Biggest first, so the smallest roles end up on top and stay visible.
    order = np.argsort(-radii)
    name_font = helvetica("bold")
    for position in order:
        row = pool.iloc[position]
        radius = float(radii[position])
        px, py = float(to_x(row[x_column])), float(to_y(row[y_column]))
        wants_face = pool.index[position] in face_rows and radius >= MIN_FACE_RADIUS
        if wants_face:
            square_headshot_label(ax, portrait_path(int(row["player_id"])),
                                  px, py, radius, zorder=6,
                                  face_fraction=FACE_CROP_FRACTION)
        else:
            above = row[y_column] >= y_split
            ax.add_patch(Circle(
                (px, py), radius,
                facecolor=theme.accent if above else theme.contrast,
                alpha=0.72 if above else 0.30,
                edgecolor="none", zorder=3,
            ))
        if wants_face or pool.index[position] in face_rows:
            name = str(row["player_name"]).removesuffix(" Jr.").removesuffix(" III")
            ax.text(px, py - radius - 11,
                    f"{name}  {str(row['season_label'])[2:4]}",
                    ha="center", va="top", fontsize=10.0, color=theme.ink,
                    fontproperties=name_font, zorder=7)

    ax.text((PLOT_LEFT + PLOT_RIGHT) / 2, PLOT_BOTTOM - 52,
            "PRA PER 75 POSSESSIONS", ha="center", va="top", fontsize=11.5,
            color=theme.muted, fontproperties=axis_font)
    ax.text(PLOT_LEFT - 54, (PLOT_BOTTOM + PLOT_TOP) / 2, y_label,
            ha="center", va="center", rotation=90, fontsize=11.5,
            color=theme.muted, fontproperties=axis_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--y", choices=sorted(Y_AXES), default="bpm")
    parser.add_argument("--faces", type=int, default=14,
                        help="how many rookies are drawn as portraits (0 for none)")
    parser.add_argument("--min-minutes", type=int, default=MIN_MINUTES)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()

    pool = load_pool(args.min_minutes)
    if args.faces:
        ensure_headshots(pool["player_id"])
        ensure_silhouette()
    DISPLAY_CSV.parent.mkdir(parents=True, exist_ok=True)
    pool.to_csv(DISPLAY_CSV, index=False)
    suffix = "final" if args.final else "draft"
    output = OUTPUT_DIR / f"rookie-landscape-scatter-{args.y}-{args.faces}faces-{suffix}.png"
    render(pool, args.y, output, faces=args.faces, final=args.final)
    print(f"Wrote {output}")
    print(f"Wrote {DISPLAY_CSV}  ({len(pool)} rookie seasons)")


if __name__ == "__main__":
    main()
