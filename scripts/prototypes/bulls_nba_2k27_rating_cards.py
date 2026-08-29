"""Render the Bulls' NBA 2K27 player-rating bars for Canva.

The ratings are a dated, manually verified snapshot from the independent
2KRatings.com website. Each player gets one transparent six-bar asset; Canva
owns the surrounding player-card layout.
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
from matplotlib.colors import to_hex, to_rgb
from matplotlib.patches import FancyBboxPatch

from bulls.graphics.house import DEFAULT_THEME, DRAFT_DPI, export_dpi, helvetica


PROJECT = "bulls-nba-2k27-ratings"
PROJECT_DATE = "2026-08-17"
CAPTURE_DATE = "2026-08-28"
DATA_PATH = (
    _REPO
    / "docs"
    / "visuals"
    / f"{PROJECT_DATE}-{PROJECT}"
    / "data"
    / f"player-ratings-{CAPTURE_DATE}.csv"
)
OUT_DIR = _REPO / "output" / f"{PROJECT_DATE}-{PROJECT}"

CATEGORIES = [
    ("INSIDE", "inside_scoring"),
    ("OUTSIDE", "outside_scoring"),
    ("ATHLETICISM", "athleticism"),
    ("PLAYMAKING", "playmaking"),
    ("DEFENSE", "defense"),
    ("REBOUNDING", "rebounding"),
]

ASSET_WIDTH = 500
ASSET_HEIGHT = 200
ASSET_MARGIN = 4
BAR_LABEL_W = 104
BAR_H = 27
BAR_GAP = 6

TRACK_FILL = "#EDE7E0"
TRACK_EDGE = "#DCD4CB"

# A fixed rating scale, not one fitted to these four players. That keeps the
# same number the same color when the rest of the roster is added later.
_RATING_ANCHORS = [40, 60, 70, 80, 90, 99]
_RATING_COLORS = [
    "#A90F2A",  # deep red
    "#E0582A",  # orange-red
    "#F2C14E",  # yellow
    "#75B84A",  # light green
    "#1F8A4C",  # dark green
    "#0E6337",  # deep green
]
def load_cards(path: Path = DATA_PATH) -> pd.DataFrame:
    """Read and validate the tracked ratings snapshot."""
    cards = pd.read_csv(path, comment="#")
    validate_cards(cards)
    return cards


def validate_cards(cards: pd.DataFrame) -> None:
    """Reject incomplete or internally inconsistent rating rows."""
    required = {
        "player_name",
        "slug",
        "nba_2k27_ovr",
        "nba_2k26_ovr",
        "ovr_change",
        "official_confirmed",
        "detailed_ratings_available",
        "archetype",
        *(key for _, key in CATEGORIES),
    }
    missing = required - set(cards.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if cards.empty:
        raise ValueError("No cards found")
    if cards["player_name"].duplicated().any():
        raise ValueError("Player names must be unique")
    if not cards["official_confirmed"].fillna(False).all():
        raise ValueError("The draft may contain only confirmed ratings")
    if not cards["nba_2k27_ovr"].between(40, 99).all():
        raise ValueError("NBA 2K27 overall ratings must be between 40 and 99")

    detail_mask = cards["detailed_ratings_available"].fillna(False)
    detail_values = cards.loc[detail_mask, [key for _, key in CATEGORIES]]
    if detail_values.isna().any().any():
        raise ValueError("Detailed cards need all six group ratings")
    if not detail_values.apply(lambda column: column.between(0, 99).all()).all():
        raise ValueError("Group ratings must be between 0 and 99")

    unavailable = cards.loc[~detail_mask, [key for _, key in CATEGORIES]]
    if not unavailable.isna().all().all():
        raise ValueError("Unavailable detail ratings must remain blank")

    prior_mask = cards["nba_2k26_ovr"].notna()
    expected_change = (
        cards.loc[prior_mask, "nba_2k27_ovr"]
        - cards.loc[prior_mask, "nba_2k26_ovr"]
    )
    actual_change = cards.loc[prior_mask, "ovr_change"]
    if not np.allclose(expected_change, actual_change):
        raise ValueError("ovr_change must equal NBA 2K27 OVR minus NBA 2K26 OVR")


def change_label(player: pd.Series) -> str:
    """Return the compact year-over-year label shown below OVR."""
    if pd.isna(player["nba_2k26_ovr"]):
        return "2K DEBUT"
    change = int(player["ovr_change"])
    if change == 0:
        return "0 VS 2K26"
    return f"{abs(change)} VS 2K26"


def change_color(player: pd.Series, theme=DEFAULT_THEME) -> str:
    """Use green for gains, red for drops, and muted ink otherwise."""
    if pd.isna(player["nba_2k26_ovr"]) or int(player["ovr_change"]) == 0:
        return theme.muted
    return "#1F8A4C" if int(player["ovr_change"]) > 0 else "#A90F2A"


def rating_fill(value: float) -> str:
    """Map a 2K rating to the fixed red-yellow-green visual scale."""
    clipped = min(max(float(value), _RATING_ANCHORS[0]), _RATING_ANCHORS[-1])
    for index in range(len(_RATING_ANCHORS) - 1):
        low_value = _RATING_ANCHORS[index]
        high_value = _RATING_ANCHORS[index + 1]
        if clipped <= high_value:
            position = (clipped - low_value) / (high_value - low_value)
            low_rgb = to_rgb(_RATING_COLORS[index])
            high_rgb = to_rgb(_RATING_COLORS[index + 1])
            rgb = tuple(
                low + position * (high - low)
                for low, high in zip(low_rgb, high_rgb, strict=True)
            )
            return to_hex(rgb, keep_alpha=False)
    return _RATING_COLORS[-1].lower()


def text_color_for_fill(fill: str) -> str:
    """Choose readable type over both dark green/red and bright yellow bars."""
    red, green, blue = to_rgb(fill)
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#141414" if luminance >= 0.56 else "#FFFFFF"


def _draw_bar(
    ax: plt.Axes,
    theme,
    x: float,
    y: float,
    width: float,
    label: str,
    value: float | None,
) -> None:
    track_x = x + BAR_LABEL_W
    track_w = width - BAR_LABEL_W
    ax.text(
        x,
        y + BAR_H / 2,
        label,
        fontproperties=helvetica("bold"),
        fontsize=6.8,
        color=theme.muted,
        ha="left",
        va="center",
        zorder=7,
    )
    ax.add_patch(
        FancyBboxPatch(
            (track_x, y),
            track_w,
            BAR_H,
            boxstyle="round,pad=0,rounding_size=4",
            facecolor=TRACK_FILL,
            edgecolor=TRACK_EDGE,
            lw=0.6,
            zorder=5,
        )
    )
    if value is None or pd.isna(value):
        ax.text(
            track_x + track_w / 2,
            y + BAR_H / 2,
            "—",
            fontproperties=helvetica("bold"),
            fontsize=8.0,
            color=theme.faint,
            ha="center",
            va="center",
            zorder=7,
        )
        return

    filled = max(track_w * float(value) / 100.0, 4.0)
    fill = rating_fill(float(value))
    ax.add_patch(
        FancyBboxPatch(
            (track_x, y),
            filled,
            BAR_H,
            boxstyle="round,pad=0,rounding_size=4",
            facecolor=fill,
            edgecolor=theme.ink,
            lw=0.35,
            zorder=6,
        )
    )
    value_text = f"{int(value)}"
    if value >= 26:
        ax.text(
            track_x + filled - 7,
            y + BAR_H / 2,
            value_text,
            fontproperties=helvetica("bold"),
            fontsize=9.6,
            color=text_color_for_fill(fill),
            ha="right",
            va="center",
            zorder=7,
        )
    else:
        ax.text(
            track_x + filled + 6,
            y + BAR_H / 2,
            value_text,
            fontproperties=helvetica("bold"),
            fontsize=9.6,
            color=theme.ink,
            ha="left",
            va="center",
            zorder=7,
        )


def _draw_player_bars(ax: plt.Axes, theme, player: pd.Series) -> None:
    """Draw the six data-owned bars and no Canva-owned card furniture."""
    bar_top = ASSET_HEIGHT - ASSET_MARGIN
    for slot, (label, key) in enumerate(CATEGORIES):
        value = player[key] if bool(player["detailed_ratings_available"]) else None
        _draw_bar(
            ax,
            theme,
            ASSET_MARGIN,
            bar_top - BAR_H - slot * (BAR_H + BAR_GAP),
            ASSET_WIDTH - 2 * ASSET_MARGIN,
            label,
            value,
        )


def render_player_bars(
    cards: pd.DataFrame,
    *,
    final: bool = False,
) -> list[Path]:
    """Render one transparent six-bar asset per player for Canva."""
    theme = DEFAULT_THEME
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "-final" if final else ""
    outputs: list[Path] = []
    for _, player in cards.iterrows():
        fig = plt.figure(
            figsize=(ASSET_WIDTH / DRAFT_DPI, ASSET_HEIGHT / DRAFT_DPI)
        )
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, ASSET_WIDTH)
        ax.set_ylim(0, ASSET_HEIGHT)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.patch.set_alpha(0)
        _draw_player_bars(ax, theme, player)

        output = OUT_DIR / (
            f"{CAPTURE_DATE}-2k27-rating-bars-{player['slug']}{suffix}.png"
        )
        fig.savefig(output, dpi=export_dpi(final), transparent=True)
        plt.close(fig)
        outputs.append(output)
    return outputs


def canva_copy_block(cards: pd.DataFrame) -> str:
    return "\n".join(
        [
            "--- CANVA COPY BLOCK ---",
            "",
            "TITLE: BULLS' NBA 2K27 RATINGS",
            "SUBTITLE: Chicago's full launch roster",
            "",
            "ASSETS: One transparent six-bar rating group per player.",
            "",
            (
                f"COVERAGE: {len(cards)} players listed on the Bulls' NBA 2K27 roster "
                "as of Aug. 28, 2026."
            ),
            "",
            "SOURCE: 2KRatings.com · Independent database",
            "",
            "--- END ---",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Render the chart asset at final export resolution.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cards = load_cards()
    outputs = render_player_bars(cards, final=args.final)
    for output in outputs:
        print(f"Wrote {output}")
    print()
    print(canva_copy_block(cards))


if __name__ == "__main__":
    main()
