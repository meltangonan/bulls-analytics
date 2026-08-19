"""Rank the biggest Bulls rookie workloads since 2000 by PRA/75.

Two slides off one qualified pool. Every Bulls rookie season since 2000-01 with
1,000 or more Bulls minutes qualifies — 23 of them — ranked by points, rebounds
and assists per 75 player possessions. Slide one is the top ten; slide two is
the remaining thirteen, so the ranking is a real cut of a stated field rather
than a top ten with an unexplained edge.

PRA/75 measures production, not quality. It weights a point, a rebound and an
assist equally and knows nothing about efficiency, turnovers or defence, which
is why Bobby Portis ranks fifth while shooting seven points below his season's
league average. The headline has to say "did the most", never "were the best" —
the same claim the rejected composite made. TS% sits beside the ranking so the
reader can see the difference for himself.
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
import pandas as pd
from matplotlib.patches import Rectangle

from bulls.graphics.house import (
    DEFAULT_THEME,
    draw_accent_card,
    ensure_headshots,
    ensure_silhouette,
    export_dpi,
    heat_fill,
    heat_text_color,
    helvetica,
    portrait_path,
    rendered_width,
)
from bulls.visuals import DATA, visual_dir
from scripts.prototypes.bulls_rookie_chronological_table import (
    DRAFT_CSV,
    ON_OFF_CSV,
    display_name,
    draft_caption,
    era_relative_ts,
    load_or_fetch_draft_info,
    season_marker,
)
from scripts.prototypes.bulls_rookie_metric_analysis import WORKING_CSV, normalize_name

PROJECT = "bulls-rookie-landscape"
MIN_MINUTES = 1000
TOP_N = 10
DATA_DIR = visual_dir(_REPO / "docs" / "visuals", PROJECT, when="2026-08-14") / DATA
DISPLAY_CSV = DATA_DIR / "bulls-rookie-leaderboard.csv"
OUTPUT_DIR = _REPO / "output" / "2026-08-14-bulls-rookie-landscape"

# On/off is blanked below this, exactly as on the chronological table.
MIN_IMPACT_MINUTES = 750

# Narrower and taller than the page, on purpose. Placed on a 1080x1350 Canva
# page the asset has roughly 960x875 to live in, and whichever dimension binds
# first sets the scale. At 1080x875 the width bound first, so the chart shrank
# to 89% and left vertical space empty. At 1000x960 the height binds instead:
# the asset scales to 91% and every row lands about 14% larger on the page.
CHART_WIDTH = 1000
TABLE_LEFT = 16
TABLE_RIGHT = 984
CANVAS_HEIGHT = 960
HEADER_FROM_TOP = 40
HEADER_RULE_FROM_TOP = 64
BOTTOM_PAD = 20

RANK_X = 32
HEADSHOT_X = 92
NAME_X = 136
NAME_GAP = 12
RANK_FONT_SIZE = 17.0
NAME_FONT_SIZE = 16.0
SEASON_FONT_SIZE = 9.8
VALUE_FONT_SIZE = 14.5
HEADER_FONT_SIZE = 13.0
HERO_FONT_SIZE = 17.0
CAPTION_FONT_SIZE = 11.0
CARD_OUTSET_Y = 7.0
CARD_OVERLAP_Y = 3.0

# The hero column carries the ranking, styled like the game-score table's GMSC.
#
# Rate and total answer different questions, and the headline has to match the
# one chosen. "Did the most" is a total: Derrick Rose out-produced Nikola
# Mirotic 2,190 to 1,334, because he played 3,000 minutes to Mirotic's 1,654.
# PRA/75 instead asks who produced fastest per possession, which flatters a
# bench role — production per possession usually falls as minutes grow, so a
# 20-minute player is not being asked to sustain what a 37-minute player is.
HERO_MODES = {
    "total": ("pra_total", "PRA", "{:.0f}"),
    "per-75": ("pra_per_75", "PRA/75", "{:.1f}"),
    "per-game": ("pra_pg", "PRA/G", "{:.1f}"),
}
DEFAULT_HERO_MODE = "per-75"
STAT_COLUMNS = (
    ("games", "GP"),
    ("mpg", "MPG"),
    ("ppg", "PTS"),
    ("rpg", "REB"),
    ("apg", "AST"),
    ("ts_pct", "TS%"),
    ("impact", "ON/OFF"),
)
SHADED_METRICS = ("ppg", "rpg", "apg", "ts_pct", "impact")
SCALE_POPULATION = "NBA rookies with 1,000+ minutes, 2000-01 to 2025-26"
SCALE_SAMPLE_SIZE = 558
ERA_RELATIVE_METRICS = ("ts_pct",)

# Calibrated against the peer group this table is actually about: 558 NBA rookie
# seasons at 1,000+ minutes, not the 1,147 at 300+. Everyone here cleared the
# same bar, so grading them against rookies who barely played was too generous —
# it painted ordinary starter production green. Neutral is that pool's 75th
# percentile, green its 95th:
#
#            50th    75th    95th
#   PTS      8.58   11.28   16.70
#   REB      3.56    4.93    7.54
#   AST      1.54    2.71    5.40
#
# See DESIGN.md: calibrate from the population the chart is about, never from
# the chart's own range.
COLUMN_SCALES = {
    "ppg": (11.28, 11.28, 11.28, 16.70),
    "rpg": (4.93, 4.93, 4.93, 7.54),
    "apg": (2.71, 2.71, 2.71, 5.40),
    "ts_pct": (-11.92, -6.38, 0.55, 5.67),
    "impact": (-10.0, -2.0, 2.0, 10.0),
}


def row_height(row_count: int) -> float:
    """Fill the shared canvas whatever this slide's row count is.

    The top ten gets taller rows than the remaining thirteen. That is the
    editorial hierarchy made visible rather than an inconsistency: the ranked
    slide is the post, the second slide is the rest of the field.
    """
    return (CANVAS_HEIGHT - HEADER_RULE_FROM_TOP - 21.5 - BOTTOM_PAD) / row_count


def column_bounds(stats_left: float, hero_right: float) -> dict:
    """Equal-width statistic columns to the right of the hero column."""
    width = (TABLE_RIGHT - stats_left) / len(STAT_COLUMNS)
    return {
        metric: (stats_left + i * width, stats_left + (i + 1) * width, label)
        for i, (metric, label) in enumerate(STAT_COLUMNS)
    }


def prepare_table(working: pd.DataFrame, hero_metric: str = "pra_total") -> pd.DataFrame:
    """Qualify at 1,000 minutes, attach on/off, and rank by PRA/75."""
    q = working[working["minutes"].ge(MIN_MINUTES)].copy()
    q["rpg"] = q["rebounds"] / q["games"]
    q["apg"] = q["assists"] / q["games"]
    q["mpg"] = q["minutes"] / q["games"]
    q["ts_pct_relative"] = era_relative_ts(q)
    q["pra_total"] = q["points"] + q["rebounds"] + q["assists"]
    q["pra_pg"] = q["pra_total"] / q["games"]

    snapshot = pd.read_csv(ON_OFF_CSV)
    snapshot["key"] = snapshot["player_name"].map(normalize_name)
    q["key"] = q["player_name"].map(normalize_name)
    q = q.merge(
        snapshot[["season", "key", "net_on_off"]],
        on=["season", "key"],
        how="left",
        validate="one_to_one",
    )
    if q["net_on_off"].isna().any():
        missing = sorted(q.loc[q["net_on_off"].isna(), "player_name"])
        raise ValueError(f"No captured on/off row for: {missing}")
    q["impact"] = q["net_on_off"].where(q["minutes"].ge(MIN_IMPACT_MINUTES))

    draft = load_or_fetch_draft_info(
        q["player_id"].astype(int).tolist(), DRAFT_CSV, refresh=False
    )
    q = q.merge(draft[["player_id", "draft_year", "draft_number"]], on="player_id",
                how="left", validate="one_to_one")
    if q["draft_number"].isna().any():
        missing = sorted(q.loc[q["draft_number"].isna(), "player_name"])
        raise ValueError(f"No draft record for: {missing}")
    q["draft_caption"] = [
        draft_caption(year, number)
        for year, number in zip(q["draft_year"], q["draft_number"])
    ]

    q = q.sort_values(hero_metric, ascending=False).reset_index(drop=True)
    q["rank"] = range(1, len(q) + 1)
    return q


def split_pages(table: pd.DataFrame) -> list[pd.DataFrame]:
    """Slide one is the top ten; slide two is everyone else who qualified."""
    return [
        table.iloc[:TOP_N].reset_index(drop=True),
        table.iloc[TOP_N:].reset_index(drop=True),
    ]


def shaded_value(row: pd.Series, metric: str) -> float:
    """Give a column the number its scale is calibrated on."""
    if metric in ERA_RELATIVE_METRICS:
        return float(row[f"{metric}_relative"])
    return float(row[metric])


def measure_stats_left(table: pd.DataFrame, hero_right: float) -> float:
    """Start the statistics after the widest name in the qualified pool."""
    fig = plt.figure(figsize=(CHART_WIDTH / 100, CANVAS_HEIGHT / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CANVAS_HEIGHT)
    ax.axis("off")
    season_font = helvetica("regular")
    season_font.set_style("italic")
    widest = 0.0
    for _, row in table.iterrows():
        name = ax.text(0, 0, display_name(row["player_name"]), fontsize=NAME_FONT_SIZE,
                       fontproperties=helvetica("bold"), alpha=0)
        season = ax.text(0, 0, season_marker(str(row["season_label"])),
                         fontsize=SEASON_FONT_SIZE, fontproperties=season_font, alpha=0)
        widest = max(widest, rendered_width(ax, name) + 5 + rendered_width(ax, season))
        name.remove()
        season.remove()
    plt.close(fig)
    return NAME_X + widest + NAME_GAP


def _portrait(ax, player_id: int, row_y: float, rh: float) -> None:
    """Face crop, clipped at this row's own separator like the other tables."""
    half = rh * 0.62
    y = row_y + rh * 0.05
    try:
        image = plt.imread(portrait_path(int(player_id)))
    except (FileNotFoundError, OSError, ValueError):
        return
    h, w = image.shape[:2]
    side = min(int(h * 0.74), w)
    left = max(0, (w - side) // 2)
    artist = ax.imshow(
        image[:side, left:left + side],
        extent=[HEADSHOT_X - half, HEADSHOT_X + half, y - half, y + half],
        interpolation="bilinear",
        zorder=4,
    )
    artist.set_clip_path(
        Rectangle(
            (HEADSHOT_X - half, row_y - rh / 2), 2 * half, (y + half) - (row_y - rh / 2),
            transform=ax.transData,
        )
    )


def render_page(
    page: pd.DataFrame,
    page_number: int,
    output_path: Path,
    stats_left: float,
    hero_bounds: tuple[float, float],
    hero: tuple[str, str, str],
    final: bool = False,
) -> Path:
    """Render one transparent, Canva-ready leaderboard slide."""
    theme = DEFAULT_THEME
    rh = row_height(len(page))
    columns = column_bounds(stats_left, hero_bounds[1])
    header_y = CANVAS_HEIGHT - HEADER_FROM_TOP
    rule_y = CANVAS_HEIGHT - HEADER_RULE_FROM_TOP
    first_row_y = rule_y - rh / 2 - 1.5

    fig = plt.figure(figsize=(CHART_WIDTH / 100, CANVAS_HEIGHT / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CANVAS_HEIGHT)
    ax.axis("off")

    bold = helvetica("bold")
    regular = helvetica("regular")
    season_font = helvetica("regular")
    season_font.set_style("italic")

    ax.text(NAME_X, header_y, "ROOKIE", ha="left", va="center",
            fontsize=HEADER_FONT_SIZE + 1, color=theme.ink, fontproperties=bold)
    ax.text(sum(hero_bounds) / 2, header_y, hero[1], ha="center", va="center",
            fontsize=HEADER_FONT_SIZE, color=theme.accent, fontproperties=bold)
    for left, right, label in columns.values():
        ax.text((left + right) / 2, header_y, label, ha="center", va="center",
                fontsize=HEADER_FONT_SIZE, color=theme.ink, fontproperties=bold)
    for a, b in ((TABLE_LEFT, hero_bounds[0] - 8), (hero_bounds[1] + 8, TABLE_RIGHT)):
        ax.plot([a, b], [rule_y, rule_y], color=theme.ink, linewidth=1.5,
                zorder=3, solid_capstyle="butt")

    # One continuous card behind the ranking column, drawn before the rows so
    # the values sit on top of it.
    # A shorter reach than the game-score default: this canvas is tighter, and
    # the full outset crowded the PRA/75 header.
    card = draw_accent_card(ax, hero_bounds[0], hero_bounds[1], first_row_y,
                            len(page), rh, outset_y=CARD_OUTSET_Y,
                            overlap_y=CARD_OVERLAP_Y)
    card_left, card_right = card[0], card[1]

    for i, row in page.iterrows():
        y = first_row_y - i * rh
        if i < len(page) - 1:
            # Leave the card edge-to-edge: a rule crossing it would cut the
            # block into cells and undo the point of drawing it as one shape.
            sep = y - rh / 2
            for a, b in ((TABLE_LEFT, card_left), (card_right, TABLE_RIGHT)):
                ax.plot([a, b], [sep, sep], color=theme.rule, linewidth=0.9, zorder=3)

        # Bulls red, matching the hero card the ranking comes from.
        ax.text(RANK_X, y, str(int(row["rank"])), ha="center", va="center",
                fontsize=RANK_FONT_SIZE, color=theme.accent, fontproperties=bold,
                zorder=5)
        _portrait(ax, row["player_id"], y, rh)

        # Name and draft slot share the row, offset from its centre in
        # proportion to the row so both slides read the same way.
        name_rise = rh * 0.13
        caption_drop = rh * 0.20
        name = display_name(row["player_name"])
        artist = ax.text(NAME_X, y + name_rise, name, ha="left", va="center",
                         fontsize=NAME_FONT_SIZE, color=theme.ink,
                         fontproperties=bold, zorder=5)
        ax.text(NAME_X + rendered_width(ax, artist) + 5, y + name_rise + 7,
                season_marker(str(row["season_label"])), ha="left", va="center",
                fontsize=SEASON_FONT_SIZE, color=theme.muted,
                fontproperties=season_font, zorder=5)
        ax.text(NAME_X, y - caption_drop, str(row["draft_caption"]), ha="left",
                va="center", fontsize=CAPTION_FONT_SIZE, color=theme.muted,
                fontproperties=regular, zorder=5)

        ax.text(sum(hero_bounds) / 2, y, hero[2].format(float(row[hero[0]])), ha="center",
                va="center", fontsize=HERO_FONT_SIZE, color="#FFFFFF",
                fontproperties=bold, zorder=6)

        for metric, (left, right, _) in columns.items():
            if pd.isna(row[metric]):
                ax.text((left + right) / 2, y, "—", ha="center", va="center",
                        fontsize=VALUE_FONT_SIZE, color=theme.faint,
                        fontproperties=regular, zorder=4)
                continue
            color = theme.ink
            if metric in SHADED_METRICS:
                fill = heat_fill(shaded_value(row, metric), *COLUMN_SCALES[metric])
                ax.add_patch(Rectangle((left, y - rh / 2), right - left, rh,
                                       facecolor=fill, edgecolor="none", zorder=2))
                color = heat_text_color(fill)
            value = row[metric]
            if metric == "games":
                label = f"{int(value)}"
            elif metric == "ts_pct":
                label = f"{float(value) * 100:.1f}%"
            elif metric == "impact":
                label = f"{float(value):+.1f}"
            else:
                label = f"{float(value):.1f}"
            ax.text((left + right) / 2, y, label, ha="center", va="center",
                    fontsize=VALUE_FONT_SIZE, color=color, fontproperties=regular, zorder=4)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True,
                bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return output_path


def canva_copy(table: pd.DataFrame, mode: str = DEFAULT_HERO_MODE) -> str:
    measure = {
        "total": "total points + rebounds + assists",
        "per-75": "points + rebounds + assists per 75 possessions",
        "per-game": "points + rebounds + assists per game",
    }[mode]
    return "\n".join([
        "BULLS ROOKIE PRODUCTION",
        f"Ranked by {measure}, 1,000+ minutes, since 2000",
        f"Top {TOP_N} out of {len(table)} qualifying Bulls rookies",
        f"Every Bulls rookie season with {MIN_MINUTES:,}+ minutes qualifies "
        f"({len(table)} of them)",
        "Slide 2: the remaining " f"{len(table) - TOP_N}",
        "PRA/75 measures production, not quality — it weights a point, a rebound "
        "and an assist equally and ignores efficiency, turnovers and defence",
        "TS% is judged against the league average of its own season",
        "ON/OFF is how much better the Bulls were with him on the floor than off it",
        "Sources: NBA.com (box score) and databallr (on/off)",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working-csv", type=Path, default=WORKING_CSV)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--rank-by", choices=tuple(HERO_MODES), default=DEFAULT_HERO_MODE)
    args = parser.parse_args()

    hero = HERO_MODES[args.rank_by]
    table = prepare_table(pd.read_csv(args.working_csv), hero[0])
    ensure_headshots(table["player_id"])
    ensure_silhouette()
    DISPLAY_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(DISPLAY_CSV, index=False)

    hero_bounds = (0.0, 0.0)
    stats_left = measure_stats_left(table, 0.0)
    hero_width = 80.0
    hero_bounds = (stats_left, stats_left + hero_width)
    stats_left = hero_bounds[1] + 8

    for page_number, page in enumerate(split_pages(table), 1):
        suffix = "final" if args.final else "draft"
        variant = "" if args.rank_by == DEFAULT_HERO_MODE else f"-{args.rank_by}"
        out = OUTPUT_DIR / f"rookie-leaderboard{variant}-slide-{page_number}-{suffix}.png"
        render_page(page, page_number, out, stats_left, hero_bounds, hero,
                    final=args.final)
        print(f"Wrote {out}")
    print(f"Wrote {DISPLAY_CSV}")
    print("\nCanva copy:\n" + canva_copy(table, args.rank_by))


if __name__ == "__main__":
    main()
