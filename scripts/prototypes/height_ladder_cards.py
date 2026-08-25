"""Render the most-PPG-at-each-height ladder as bordered card rows.

The layout follows the Basketball-University style of card row -- an outlined
box per player, a boxed headline number, and a portrait that breaks out of its
row -- rebuilt in our house style.

Two departures from that reference are deliberate. Its accent box holds the
stat; ours holds the *height*, on the left, because height is what the ladder
is sorted by and the reader is looking for their own. And the row is Bulls red
while only the PPG cell takes the red-yellow-green scale, so colour means one
thing on the page: every row is a Bull, and the cell that varies is the number.

⚠️ Vertical geometry is specified in **inches**, not as a fraction of the
figure, and the figure grows with its row count. A carousel whose slides hold
different numbers of rows would otherwise draw a taller row on the shorter
slide, and the two would not read as one set.

⚠️ The axes is 0-1 x 0-1 with ``aspect='auto'``. Anything meant to look square
needs a different half-extent in x than in y, and the axes must be forced back
to 'auto' after every ``imshow`` because imshow resets it to 'equal'. Boxes are
square-cornered for the same reason: a rounded corner drawn in these
coordinates comes out elliptical, and a square inset box bleeds past a rounded
outer one.
"""
import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle
import pandas as pd

from bulls.graphics import house

DATA = Path("docs/visuals/2026-08-20-most-ppg-at-each-height/data")
POST_PORTRAITS = DATA / "portraits"
OUT = Path("output")

# The age ladder's red-yellow-green ramp, reused so the two posts read as one
# family. Red is the weakest scorer at that height, green the strongest.
HEAT_RED = "#D64545"
HEAT_YELLOW = "#F2D46B"
HEAT_GREEN = "#3FAE63"

BULLS_RED = "#CE1141"

# Wider than tall per row, and near full-bleed: the asset is placed on a Canva
# page by width, so a narrow canvas leaves a gap at the right margin that no
# amount of scaling closes.
FIG_W = 9.2
ROW_H_IN = 1.02
PAD_TOP_IN = 0.62      # room for the first portrait to break out of its card
PAD_BOTTOM_IN = 0.20

# Column edges as a fraction of figure width.
X_ROW_L, X_ROW_R = 0.012, 0.988
X_HEIGHT_R = 0.165
X_PORTRAIT = 0.250
X_NAME = 0.345
X_PPG_L = 0.845

NAME_SIZE = 22.0
SEASON_SIZE = 16.0
SEASON_SUP_RATIO = 0.58   # season superscript, as a fraction of the name size
HEIGHT_SIZE = 28.0
PPG_SIZE = 25.0
PORTRAIT_SCALE = 1.18
# Measured from the card's outer bottom edge: the 2.2pt border is ~0.031in, so
# this clears the line by a hair and no more.
PORTRAIT_LIFT_IN = 0.042
FACE_CROP_FRACTION = 0.72   # matches the age ladder and BPM tables

STRIPE = 0.007   # border inset, in x units


def figure_height(rows: int) -> float:
    return PAD_TOP_IN + rows * ROW_H_IN + PAD_BOTTOM_IN


def one_decimal(value: float) -> str:
    """Round half-up to one decimal, the convention basketball stats use.

    Python's ``%.1f`` rounds an exact half to even, so 2.25 MPG prints as "2.2"
    where NBA.com shows 2.3. Round explicitly rather than inheriting the
    formatter's tie-breaking rule.
    """
    return str(Decimal(repr(float(value))).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP))


def _mix(base: str, target: str, strength: float) -> tuple[float, float, float]:
    amount = min(max(float(strength), 0.0), 1.0)
    return tuple(
        np.array(to_rgb(base)) * (1 - amount) + np.array(to_rgb(target)) * amount
    )


# Fixed anchors, calibrated to what a scoring average means in the NBA rather
# than to this ladder's own spread (house.heat_fill makes the same argument).
# A min-max scale anchored on Jordan describes Jordan: it drags every honest
# starter toward red and makes 27 a mid-tone, because one outlier owns the top.
RED_AT = 8.0      # deep bench scoring
YELLOW_AT = 18.0  # a solid NBA starter
GREEN_AT = 28.0   # a first option; anything above simply stays green


def ppg_fill(value: float):
    """Map PPG onto red -> yellow -> green against fixed scoring anchors."""
    value = float(value)
    if value <= YELLOW_AT:
        span = YELLOW_AT - RED_AT
        fraction = 0.0 if span <= 0 else (value - RED_AT) / span
        return _mix(HEAT_RED, HEAT_YELLOW, min(max(fraction, 0.0), 1.0))
    span = GREEN_AT - YELLOW_AT
    fraction = 1.0 if span <= 0 else (value - YELLOW_AT) / span
    return _mix(HEAT_YELLOW, HEAT_GREEN, min(max(fraction, 0.0), 1.0))


def portrait_for(player_id: int) -> Path:
    """Prefer a hand-sourced portrait, fall back to the CDN or the silhouette."""
    local = POST_PORTRAITS / f"{int(player_id)}.png"
    return local if local.is_file() else house.portrait_path(int(player_id))


def striped_box(ax, x, y, w, h, colour, fill, fig_h, zorder):
    """A box with a colour border, a canvas-coloured stripe, then the fill."""
    stripe_y = STRIPE * FIG_W / fig_h
    ax.add_patch(Rectangle(
        (x, y), w, h, facecolor=house.DEFAULT_THEME.canvas,
        edgecolor=colour, linewidth=2.2, zorder=zorder,
    ))
    ax.add_patch(Rectangle(
        (x + STRIPE, y + stripe_y), w - 2 * STRIPE, h - 2 * stripe_y,
        facecolor=fill, edgecolor="none", zorder=zorder + 0.1,
    ))


def place_portrait(ax, path, x, bottom, height_frac, fig_h, zorder):
    """Draw a portrait sitting on `bottom`, tall enough to break its row."""
    try:
        image = plt.imread(path)
    except (FileNotFoundError, OSError, ValueError):
        return None
    h, w = image.shape[:2]
    side = min(int(h * FACE_CROP_FRACTION), w)
    left = max(0, (w - side) // 2)
    square = image[0:side, left:left + side]

    half_x = (height_frac * fig_h / FIG_W) / 2  # keep it visually square
    ax.imshow(
        square,
        extent=[x - half_x, x + half_x, bottom, bottom + height_frac],
        interpolation="bilinear", zorder=zorder,
    )
    ax.set_aspect("auto")


def draw_row(ax, row, y, row_h, name_size, fig_h, theme, zorder) -> None:
    """Draw one bordered card row centred on y, in figure-fraction coords."""
    heat = ppg_fill(row.PPG)
    box_h = row_h * 0.86
    stripe_y = STRIPE * FIG_W / fig_h
    bottom = y - box_h / 2

    # Every row is Bulls red: the page is one team, so the row colour is not
    # carrying a variable. Only the PPG cell does.
    striped_box(ax, X_ROW_L, bottom, X_ROW_R - X_ROW_L, box_h,
                BULLS_RED, _mix("#FFFFFF", BULLS_RED, 0.07), fig_h, zorder=2)

    ax.add_patch(Rectangle(
        (X_ROW_L + STRIPE, bottom + stripe_y),
        X_HEIGHT_R - X_ROW_L - STRIPE, box_h - 2 * stripe_y,
        facecolor=BULLS_RED, edgecolor="none", zorder=3,
    ))
    ax.text(
        (X_ROW_L + X_HEIGHT_R) / 2, y, row.HEIGHT,
        fontproperties=house.helvetica(
            "bold_oblique" if not row.QUALIFIED else "bold"),
        fontsize=HEIGHT_SIZE,
        color="#FFFFFF", ha="center", va="center", zorder=4,
    )

    # Lift the portrait clear of the border so it does not sit on the line.
    place_portrait(
        ax, portrait_for(row.PLAYER_ID), X_PORTRAIT,
        bottom + PORTRAIT_LIFT_IN / fig_h,
        row_h * PORTRAIT_SCALE, fig_h, zorder,
    )

    # A fallback row is set in oblique instead of carrying an asterisk: the
    # slant marks the whole row at once, and the footnote is added in Canva.
    italic = not row.QUALIFIED
    face_bold = house.helvetica("bold_oblique" if italic else "bold")
    face_regular = house.helvetica("oblique" if italic else "regular")

    name = row.PLAYER_NAME.replace(" III", "")
    label = ax.text(
        X_NAME, y + row_h * 0.15, name, fontproperties=face_bold,
        fontsize=name_size, color=theme.ink, ha="left", va="center", zorder=5,
    )
    ax.text(
        X_NAME + house.rendered_width(ax, label) + 0.005,
        y + row_h * 0.27, str(row.SEASON_ID).replace("-", "–"),
        fontproperties=face_regular, fontsize=name_size * SEASON_SUP_RATIO,
        color=theme.muted, ha="left", va="center", zorder=5,
    )
    ax.text(
        X_NAME, y - row_h * 0.21,
        f"{int(row.GP)} GP, {one_decimal(row.MPG)} MPG",
        fontproperties=face_regular, fontsize=SEASON_SIZE,
        color=theme.muted, ha="left", va="center", zorder=5,
    )

    # The one box on the page whose colour is carrying a value.
    striped_box(ax, X_PPG_L, bottom, X_ROW_R - X_PPG_L, box_h,
                heat, heat, fig_h, zorder=5)
    ax.text(
        (X_PPG_L + X_ROW_R) / 2, y, one_decimal(row.PPG),
        fontproperties=house.helvetica(
            "bold_oblique" if not row.QUALIFIED else "bold"),
        fontsize=PPG_SIZE,
        color="#FFFFFF", ha="center", va="center", zorder=7,
        path_effects=[
            path_effects.withStroke(linewidth=4.5, foreground=house.BULLS_BLACK)
        ],
    )


def fit_name_size(ladder: pd.DataFrame, fig_h: float) -> float:
    """One name size for the whole post, set by the longest name.

    Shrinking only the names that overflow makes the page look inconsistent,
    so the longest name sets the size and every row uses it.
    """
    available = X_PPG_L - X_NAME - 0.115   # leaves room for the season superscript
    fig, ax = plt.subplots(figsize=(FIG_W, fig_h))
    # ⚠️ The axes must reach its final size before anything is measured. At
    # matplotlib's default margins it spans 77.5% of the figure, so a width
    # taken now reads ~1.29x too wide and every name shrinks for no reason.
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("auto")
    ax.autoscale(False)
    size = NAME_SIZE
    for name in ladder["PLAYER_NAME"].str.replace(" III", "", regex=False):
        artist = ax.text(0, 0.5, name, fontproperties=house.helvetica("bold"),
                         fontsize=NAME_SIZE)
        width = house.rendered_width(ax, artist)
        if width > available:
            size = min(size, NAME_SIZE * available / width)
        artist.remove()
    plt.close(fig)
    return round(size, 1)


def draw_slide(ladder: pd.DataFrame, rows_tall: int, name_size, path: Path, theme):
    """Draw one slide on a canvas sized for `rows_tall` rows.

    Both slides of a carousel share one canvas even when the split is uneven,
    so the second reads as a continuation of the first: same row height, same
    column positions, same page size. A shorter slide simply ends early.
    """
    fig_h = figure_height(rows_tall)
    fig, ax = plt.subplots(figsize=(FIG_W, fig_h))
    fig.patch.set_alpha(0)
    # Size the axes first: the superscript is placed from a measured name
    # width, and a measurement taken before this reads ~1.29x too wide.
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_axis_off()
    ax.patch.set_alpha(0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("auto")
    ax.autoscale(False)

    row_h = ROW_H_IN / fig_h
    top = 1 - PAD_TOP_IN / fig_h
    for i, row in enumerate(ladder.itertuples()):
        y = top - (i + 0.5) * row_h
        # Later rows draw on top, so each portrait overlaps the card above it.
        draw_row(ax, row, y, row_h, name_size, fig_h, theme, zorder=10 + i)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, transparent=True)
    plt.close(fig)
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["strict", "fallback"], required=True)
    ap.add_argument("--split", type=int, default=None,
                    help="rows on slide 1 (default: half)")
    args = ap.parse_args()

    ladder = pd.read_csv(DATA / f"ladder_{args.variant}.csv")
    house.ensure_headshots(ladder["PLAYER_ID"])
    house.ensure_silhouette()
    theme = house.get_theme("jersey")

    split = args.split or (len(ladder) + 1) // 2
    parts = [ladder.iloc[:split], ladder.iloc[split:]]
    rows_tall = max(len(part) for part in parts)
    name_size = fit_name_size(ladder, figure_height(rows_tall))

    for n, part in enumerate(parts, start=1):
        out = OUT / f"height_ladder_{args.variant}_slide{n}.png"
        draw_slide(part.reset_index(drop=True), rows_tall, name_size, out, theme)
        print(f"wrote {out}  ({len(part)} rows, "
              f"{FIG_W:.1f}x{figure_height(rows_tall):.2f} in)")

    missing = [
        r.PLAYER_NAME for r in ladder.itertuples()
        if portrait_for(r.PLAYER_ID) == house.SILHOUETTE_PATH
    ]
    print(f"\nname size: {name_size} pt")
    if missing:
        print(f"still on the silhouette: {', '.join(missing)}")
    else:
        print("every rung has a real portrait")

    fallbacks = ladder[~ladder["QUALIFIED"]]
    print("--- Canva copy block ---")
    print("Qualifier: best single season, 41+ GP and 20+ MPG, one player per height")
    if len(fallbacks):
        print(f"Italic rows ({', '.join(fallbacks['HEIGHT'])}): no Bull this "
              f"height ever cleared the minimum; best season shown instead")
    print("Bulls player-seasons, 1976–77 to 2025–26 · Listed height · NBA.com Stats")


if __name__ == "__main__":
    main()
