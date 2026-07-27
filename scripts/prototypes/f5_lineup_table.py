"""Build the 2025-26 Bulls two-player lineup tables.

NBA.com owns the data. The default table selects the ten Bulls pairs with the
most total minutes together. The supplemental view selects the five highest net
ratings among pairs with at least 400 shared minutes. Both display the team's
offensive, defensive, and net rating while the two players were on court. The
script writes the validated analytical table, renders one transparent chart
asset for Canva, and prints the exact page copy that belongs around the chart.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle

from bulls.config import CURRENT_SEASON
from bulls.data import get_lineup_stats
from bulls.graphics.craft import MAGNITUDE_CMAP
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    square_headshot_label,
)


SEASON = CURRENT_SEASON
TOP_N = 10
NET_RATING_TOP_N = 5
NET_RATING_MIN_MINUTES = 400
OUT = _REPO / "output" / "feed"

CHART_WIDTH = 1080
ROW_HEIGHT = 104

REQUIRED_COLUMNS = [
    "GROUP_ID",
    "GROUP_NAME",
    "MIN",
    "OFF_RATING",
    "DEF_RATING",
    "NET_RATING",
]


def _split_pair(value: str, separator: str) -> tuple[str, str]:
    parts = [part.strip() for part in str(value).split(separator) if part.strip()]
    if len(parts) != 2:
        raise ValueError(f"Expected one two-player pair, received: {value}")
    return parts[0], parts[1]


def _player_label(value: str) -> str:
    """Use the surname in compact horizontal pair cells."""
    return str(value).split()[-1].upper()


def prepare_lineup_rows(
    lineups: pd.DataFrame,
    top_n: int = TOP_N,
    ranking: str = "minutes",
    min_minutes: float = 0,
) -> pd.DataFrame:
    """Validate and select Bulls two-player combinations for one ranking."""
    if ranking not in {"minutes", "net-rating"}:
        raise ValueError(f"Unsupported lineup ranking: {ranking}")

    missing = [column for column in REQUIRED_COLUMNS if column not in lineups]
    if missing:
        raise ValueError(f"Lineup data is missing columns: {', '.join(missing)}")
    if lineups.empty:
        raise ValueError("NBA.com returned no Bulls two-player lineup data.")
    if lineups["GROUP_ID"].duplicated().any():
        duplicates = lineups.loc[
            lineups["GROUP_ID"].duplicated(keep=False), "GROUP_ID"
        ].tolist()
        raise ValueError(f"Duplicate two-player group IDs: {duplicates}")
    eligible = lineups.copy()
    if ranking == "net-rating":
        eligible = eligible[eligible["MIN"] >= min_minutes].copy()

    if len(eligible) < top_n:
        qualifier = (
            f" with at least {min_minutes:,.0f} minutes"
            if ranking == "net-rating"
            else ""
        )
        raise ValueError(
            f"NBA.com returned {len(eligible)} eligible Bulls pairs{qualifier}; "
            f"{top_n} are required."
        )

    sort_columns = (
        ["MIN", "GROUP_NAME"]
        if ranking == "minutes"
        else ["NET_RATING", "MIN", "GROUP_NAME"]
    )
    sort_ascending = [False, True] if ranking == "minutes" else [False, False, True]
    rows = (
        eligible.sort_values(
            sort_columns,
            ascending=sort_ascending,
            kind="stable",
        )
        .head(top_n)
        .copy()
        .reset_index(drop=True)
    )

    numeric = ["MIN", "OFF_RATING", "DEF_RATING", "NET_RATING"]
    if rows[numeric].isna().any().any():
        raise ValueError("A selected lineup is missing minutes or a rating.")

    published_delta = (rows["OFF_RATING"] - rows["DEF_RATING"]).round(1)
    if not np.allclose(
        published_delta,
        rows["NET_RATING"],
        atol=0.11,
        rtol=0,
    ):
        raise ValueError(
            "A selected net rating does not reconcile to offensive minus "
            "defensive rating within NBA.com's published rounding."
        )

    if ranking == "minutes" and not rows["MIN"].is_monotonic_decreasing:
        raise ValueError("Selected lineups are not ordered by minutes.")
    if ranking == "net-rating" and not rows["NET_RATING"].is_monotonic_decreasing:
        raise ValueError("Selected lineups are not ordered by net rating.")

    names = rows["GROUP_NAME"].map(lambda value: _split_pair(value, " - "))
    ids = rows["GROUP_ID"].map(lambda value: _split_pair(value, "-"))
    rows["PLAYER_1_NAME"] = names.map(lambda pair: pair[0])
    rows["PLAYER_2_NAME"] = names.map(lambda pair: pair[1])
    rows["PLAYER_1_LABEL"] = rows["PLAYER_1_NAME"].map(_player_label)
    rows["PLAYER_2_LABEL"] = rows["PLAYER_2_NAME"].map(_player_label)
    rows["PLAYER_1_ID"] = ids.map(lambda pair: int(pair[0]))
    rows["PLAYER_2_ID"] = ids.map(lambda pair: int(pair[1]))
    return rows


def cache_selected_headshots(rows: pd.DataFrame) -> None:
    """Ensure every selected player has a cached NBA CDN portrait."""
    player_ids = pd.unique(
        pd.concat(
            [rows["PLAYER_1_ID"], rows["PLAYER_2_ID"]],
            ignore_index=True,
        )
    )
    ensure_headshots(player_ids)


def write_analytical_table(
    rows: pd.DataFrame,
    snapshot_date: str,
    ranking: str = "minutes",
    min_minutes: float = 0,
) -> Path:
    """Write the exact values rendered in the chart."""
    table = rows[
        [
            "GROUP_ID",
            "GROUP_NAME",
            "MIN",
            "OFF_RATING",
            "DEF_RATING",
            "NET_RATING",
        ]
    ].copy()
    table["MIN"] = table["MIN"].round(1)
    for column in ["OFF_RATING", "DEF_RATING", "NET_RATING"]:
        table[column] = table[column].round(1)

    suffix = (
        "bulls-two-man-lineups"
        if ranking == "minutes"
        else f"bulls-two-man-lineups-net-rating-{min_minutes:,.0f}min"
    )
    path = OUT / f"{snapshot_date}-{suffix}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def render_chart(
    rows: pd.DataFrame,
    snapshot_date: str,
    final: bool = False,
    ranking: str = "minutes",
    min_minutes: float = 0,
) -> Path:
    """Render the transparent F5-style table for Canva assembly."""
    theme = DEFAULT_THEME
    chart_height = 110 + ROW_HEIGHT * len(rows)
    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, chart_height / DRAFT_DPI)
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, chart_height)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    left = 20
    right = CHART_WIDTH - 20
    header_y = chart_height - 43
    header_rule_y = chart_height - 85
    first_row_y = chart_height - 138

    columns = {
        "PAIR": (28, "left"),
        "MIN": (510, "center"),
        "OFF RTG": (660, "center"),
        "DEF RTG": (810, "center"),
        "NET RTG": (1000, "center"),
    }

    for label, (x, alignment) in columns.items():
        ax.text(
            x,
            header_y,
            label,
            ha=alignment,
            va="center",
            fontsize=14,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
    ax.plot(
        [left, right],
        [header_rule_y, header_rule_y],
        color=theme.ink,
        lw=2.2,
    )

    net_min = float(rows["NET_RATING"].min())
    net_max = float(rows["NET_RATING"].max())
    net_span = net_max - net_min

    for index, row in rows.iterrows():
        y = first_row_y - index * ROW_HEIGHT
        divider_y = y - ROW_HEIGHT / 2

        if index % 2:
            ax.add_patch(
                Rectangle(
                    (left, divider_y + 4),
                    right - left,
                    ROW_HEIGHT - 8,
                    facecolor="#F5F1EC",
                    edgecolor="none",
                    zorder=-1,
                )
            )

        ax.text(
            132,
            y,
            row["PLAYER_1_LABEL"],
            ha="right",
            va="center",
            fontsize=12,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
        square_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(row['PLAYER_1_ID'])}.png",
            172,
            y,
            half_size=36,
            zorder=3,
        )
        ax.text(
            323,
            y,
            row["PLAYER_2_LABEL"],
            ha="right",
            va="center",
            fontsize=12,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
        square_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(row['PLAYER_2_ID'])}.png",
            365,
            y,
            half_size=36,
            zorder=3,
        )
        ax.text(
            columns["MIN"][0],
            y,
            f"{row['MIN']:,.0f}",
            ha="center",
            va="center",
            fontsize=15,
            color=theme.muted,
            fontproperties=helvetica(),
        )
        ax.text(
            columns["OFF RTG"][0],
            y,
            f"{row['OFF_RATING']:.1f}",
            ha="center",
            va="center",
            fontsize=15,
            color=theme.muted,
            fontproperties=helvetica(),
        )
        ax.text(
            columns["DEF RTG"][0],
            y,
            f"{row['DEF_RATING']:.1f}",
            ha="center",
            va="center",
            fontsize=15,
            color=theme.muted,
            fontproperties=helvetica(),
        )

        net_fraction = (
            1.0
            if net_span <= 0
            else (net_max - float(row["NET_RATING"])) / net_span
        )
        net_fill = MAGNITUDE_CMAP(net_fraction)
        net_text = "#FFFFFF" if net_fraction >= 0.46 else theme.ink
        ax.add_patch(
            FancyBboxPatch(
                (columns["NET RTG"][0] - 59, y - 32),
                118,
                64,
                boxstyle="round,pad=0,rounding_size=10",
                facecolor=net_fill,
                edgecolor="none",
                zorder=1,
            )
        )
        ax.text(
            columns["NET RTG"][0],
            y,
            f"{row['NET_RATING']:+.1f}",
            ha="center",
            va="center",
            fontsize=15.5,
            color=net_text,
            fontproperties=helvetica("bold"),
            zorder=2,
        )

        ax.plot(
            [left, right],
            [divider_y, divider_y],
            color=theme.rule,
            lw=1.1,
            zorder=0,
        )

    suffix = (
        "bulls-two-man-lineups-chart"
        if ranking == "minutes"
        else f"bulls-two-man-lineups-net-rating-{min_minutes:,.0f}min-chart"
    )
    path = OUT / f"{snapshot_date}-{suffix}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return path


def canva_copy_block(
    rows: pd.DataFrame,
    ranking: str = "minutes",
    min_minutes: float = 0,
) -> str:
    """Return the exact copy surrounding this chart on the Canva page."""
    if ranking == "net-rating":
        return "\n".join(
            [
                "=== CANVA COPY (DATA-BOUND) ===",
                "",
                "TITLE: BULLS DUOS",
                "",
                (
                    "SUBTITLE: LAST YEAR’S TOP 5 DUOS BY NET RATING"
                ),
                "",
                (
                    f"QUALIFICATION: Minimum {min_minutes:,.0f} minutes "
                    f"together · {SEASON} regular season · Ratings per 100 "
                    "possessions"
                ),
                "",
                (
                    "NET RATING KEY: Darker red = lower/worse net rating among "
                    "these 5 pairs."
                ),
                "",
                (
                    "METHOD NOTE: Ratings describe every minute with both players "
                    "on the court; they are not isolated two-player impact estimates."
                ),
                "",
                "SOURCE: Data via NBA.com/Stats",
                "",
                "HANDLE: @chicagobullsdata",
                "",
                "=== END CANVA COPY ===",
            ]
        )

    top_pair = rows.iloc[0]
    best_pair = rows.loc[rows["NET_RATING"].idxmax()]
    return "\n".join(
        [
            "=== CANVA COPY (DATA-BOUND) ===",
            "",
            "TITLE: THE BULLS’ MOST-USED DUOS",
            "",
            (
                "SUBTITLE: How Chicago performed with its 10 most-played "
                "pairs on the court"
            ),
            "",
            (
                f"LEAD NOTE: {top_pair['GROUP_NAME'].replace(' - ', ' + ')} "
                f"led the Bulls with {top_pair['MIN']:,.0f} minutes together."
            ),
            "",
            (
                f"PAYOFF: {best_pair['GROUP_NAME'].replace(' - ', ' + ')} "
                f"was the only top-10 pair above zero, though it was "
                f"essentially even ({best_pair['NET_RATING']:+.1f})."
            ),
            "",
            (
                f"QUALIFICATION: {SEASON} regular season · Bulls pairs ranked "
                "by total minutes together · Ratings per 100 possessions"
            ),
            "",
            (
                "NET RATING KEY: Darker red = lower/worse net rating among "
                "these 10 pairs."
            ),
            "",
            (
                "METHOD NOTE: Ratings describe every minute with both players "
                "on the court; they are not isolated two-player impact estimates."
            ),
            "",
            "SOURCE: Data via NBA.com/Stats",
            "",
            "HANDLE: @chicagobullsdata",
            "",
            "=== END CANVA COPY ===",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the Bulls' most-used two-player lineup table."
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Snapshot date used in output filenames (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export the chart asset at final 2x resolution.",
    )
    parser.add_argument(
        "--ranking",
        choices=["minutes", "net-rating"],
        default="minutes",
        help="Rank pairs by total minutes or by net rating.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lineups = get_lineup_stats(season=SEASON)
    top_n = TOP_N if args.ranking == "minutes" else NET_RATING_TOP_N
    min_minutes = 0 if args.ranking == "minutes" else NET_RATING_MIN_MINUTES
    rows = prepare_lineup_rows(
        lineups,
        top_n=top_n,
        ranking=args.ranking,
        min_minutes=min_minutes,
    )
    cache_selected_headshots(rows)
    table_path = write_analytical_table(
        rows,
        args.date,
        ranking=args.ranking,
        min_minutes=min_minutes,
    )
    chart_path = render_chart(
        rows,
        args.date,
        final=args.final,
        ranking=args.ranking,
        min_minutes=min_minutes,
    )

    print(
        rows[
            [
                "GROUP_NAME",
                "MIN",
                "OFF_RATING",
                "DEF_RATING",
                "NET_RATING",
            ]
        ].to_string(index=False)
    )
    print(f"\nAnalytical table: {table_path}")
    print(f"Chart asset: {chart_path}")
    output_width = CHART_WIDTH * (2 if args.final else 1)
    output_height = (110 + ROW_HEIGHT * len(rows)) * (2 if args.final else 1)
    print(f"Chart export: {output_width}×{output_height} px")
    print()
    print(
        canva_copy_block(
            rows,
            ranking=args.ranking,
            min_minutes=min_minutes,
        )
    )


if __name__ == "__main__":
    main()
