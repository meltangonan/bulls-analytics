"""Find opponents associated with the most elite Bulls player-games.

The source player-game and team-game tables are the same structured NBA.com
feeds used by ``top_game_performances.py``.  This prototype reuses those
validated loaders, maps historical opponent abbreviations to the current 29
franchises, calculates Game Score 30+ and 30+ point performance counts/rates,
and renders transparent horizontal bar charts for Canva.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.image import imread
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch, Patch

from bulls.graphics.house import DEFAULT_THEME, export_dpi, helvetica
from scripts.prototypes.top_game_performances import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    build_working_table,
    fetch_bulls_history,
)


SLUG = "opponent-elite-performances"
PROJECT = _REPO / "docs" / "visuals" / f"2026-08-17-{SLUG}"
DATA_DIR = PROJECT / "data"
LOGO_DIR = PROJECT / "assets" / "logos"
OUT = _REPO / "output" / SLUG

ELITE_GAME_SCORE = 30.0
POINT_THRESHOLDS = (30, 40, 50)
MIN_MEETINGS = 40
CHART_WIDTH = 1800
CHART_HEIGHT = 2250
DRAFT_DPI = 150

# These are sampled from the user's All-Star uniform reference image. The
# reference has lighting variation, so the chart uses representative jersey
# colors rather than trying to preserve every highlight in the photograph.
WEST_GRADIENT = ("#FF003E", "#B70023")
EAST_GRADIENT = ("#2A54C0", "#152678")
WEST_SHADOW = "#7A1230"
EAST_SHADOW = "#1D2A62"

# NBA.com changes the abbreviation in MATCHUP when a franchise changes its
# public name.  These are franchise-continuity mappings, not attempts to
# rewrite the original source rows.
HISTORICAL_TO_CURRENT = {
    "NJN": "BKN",  # New Jersey Nets -> Brooklyn Nets
    "NOH": "NOP",  # New Orleans Hornets -> New Orleans Pelicans
    "NOK": "NOP",  # New Orleans/Oklahoma City -> New Orleans Pelicans
    "SEA": "OKC",  # Seattle SuperSonics -> Oklahoma City Thunder
    "VAN": "MEM",  # Vancouver Grizzlies -> Memphis Grizzlies
    "CHH": "CHA",  # Charlotte Bobcats/Hornets naming in older logs
}

FRANCHISE_NAMES = {
    "ATL": "Hawks",
    "BOS": "Celtics",
    "BKN": "Nets",
    "CHA": "Hornets",
    "CLE": "Cavaliers",
    "DAL": "Mavericks",
    "DEN": "Nuggets",
    "DET": "Pistons",
    "GSW": "Warriors",
    "HOU": "Rockets",
    "IND": "Pacers",
    "LAC": "Clippers",
    "LAL": "Lakers",
    "MEM": "Grizzlies",
    "MIA": "Heat",
    "MIL": "Bucks",
    "MIN": "Timberwolves",
    "NOP": "Pelicans",
    "NYK": "Knicks",
    "OKC": "Thunder",
    "ORL": "Magic",
    "PHI": "76ers",
    "PHX": "Suns",
    "POR": "Trail Blazers",
    "SAC": "Kings",
    "SAS": "Spurs",
    "TOR": "Raptors",
    "UTA": "Jazz",
    "WAS": "Wizards",
}

FRANCHISE_CONFERENCES = {
    "ATL": "East",
    "BOS": "East",
    "BKN": "East",
    "CHA": "East",
    "CLE": "East",
    "DAL": "West",
    "DEN": "West",
    "DET": "East",
    "GSW": "West",
    "HOU": "West",
    "IND": "East",
    "LAC": "West",
    "LAL": "West",
    "MEM": "West",
    "MIA": "East",
    "MIL": "East",
    "MIN": "West",
    "NOP": "West",
    "NYK": "East",
    "OKC": "West",
    "ORL": "East",
    "PHI": "East",
    "PHX": "West",
    "POR": "West",
    "SAC": "West",
    "SAS": "West",
    "TOR": "East",
    "UTA": "West",
    "WAS": "East",
}


def current_opponent(raw: str) -> str:
    """Map one NBA.com opponent abbreviation to its current franchise code."""
    return HISTORICAL_TO_CURRENT.get(str(raw), str(raw))


def build_opponent_summary(
    table: pd.DataFrame,
    *,
    threshold: float = ELITE_GAME_SCORE,
    min_meetings: int = MIN_MEETINGS,
) -> pd.DataFrame:
    """Return one row per current opponent, ranked by elite rate."""
    required = {"game_id", "opponent", "game_score"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Working table is missing {sorted(missing)}.")

    rows = table[["game_id", "opponent"]].drop_duplicates().copy()
    rows["franchise"] = rows["opponent"].map(current_opponent)
    meetings = rows.groupby("franchise", as_index=False).agg(meetings=("game_id", "nunique"))

    elite = table.loc[table["game_score"] >= threshold, ["game_id", "opponent"]].copy()
    elite["franchise"] = elite["opponent"].map(current_opponent)
    elite_counts = elite.groupby("franchise").size().rename("elite_player_games")

    summary = pd.DataFrame({"franchise": list(FRANCHISE_NAMES)}).merge(
        meetings, on="franchise", how="left", validate="one_to_one"
    )
    summary = summary.join(elite_counts, on="franchise")
    summary["elite_player_games"] = summary["elite_player_games"].fillna(0).astype(int)
    if summary["meetings"].isna().any():
        missing_codes = summary.loc[summary["meetings"].isna(), "franchise"].tolist()
        raise ValueError(f"Missing current opponent franchise rows: {missing_codes}")
    summary["meetings"] = summary["meetings"].astype(int)
    summary["rate_per_100"] = summary["elite_player_games"] / summary["meetings"] * 100
    total_elite = int(summary["elite_player_games"].sum())
    total_meetings = int(summary["meetings"].sum())
    overall_rate = total_elite / total_meetings * 100
    summary["relative_to_all"] = summary["rate_per_100"] / overall_rate
    summary["team"] = summary["franchise"].map(FRANCHISE_NAMES)
    summary["eligible"] = summary["meetings"] >= min_meetings
    if not summary["eligible"].all():
        excluded = summary.loc[~summary["eligible"], "franchise"].tolist()
        raise ValueError(f"Opponent sample is below the minimum for {excluded}")

    summary = summary.sort_values(
        ["rate_per_100", "elite_player_games", "meetings", "team"],
        ascending=[False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    summary["rank"] = summary.index + 1
    summary["threshold"] = float(threshold)
    summary["minimum_meetings"] = int(min_meetings)
    summary["coverage_start"] = f"{FIRST_SEASON_END_YEAR - 1}-{str(FIRST_SEASON_END_YEAR)[-2:]}"
    summary["coverage_end"] = f"{LAST_SEASON_END_YEAR - 1}-{str(LAST_SEASON_END_YEAR)[-2:]}"
    return summary[
        [
            "rank",
            "franchise",
            "team",
            "rate_per_100",
            "elite_player_games",
            "meetings",
            "relative_to_all",
            "threshold",
            "minimum_meetings",
            "coverage_start",
            "coverage_end",
        ]
    ]


def validate_summary(
    summary: pd.DataFrame,
    table: pd.DataFrame,
    *,
    threshold: float = ELITE_GAME_SCORE,
    min_meetings: int = MIN_MEETINGS,
) -> dict[str, object]:
    """Validate the full current-franchise field and count reconciliations."""
    if len(summary) != len(FRANCHISE_NAMES):
        raise ValueError(f"Expected 29 current opponents, got {len(summary)}")
    if summary["franchise"].duplicated().any():
        raise ValueError("Opponent summary contains duplicate franchises.")
    if summary["meetings"].min() < min_meetings:
        raise ValueError("Opponent summary contains a thin meeting sample.")
    expected_games = table[["game_id", "opponent"]].drop_duplicates()["game_id"].nunique()
    if int(summary["meetings"].sum()) != expected_games:
        raise ValueError("Opponent meetings do not reconcile to distinct Bulls team games.")
    expected_elite = int((table["game_score"] >= threshold).sum())
    if int(summary["elite_player_games"].sum()) != expected_elite:
        raise ValueError("Elite player-game counts do not reconcile to the working table.")
    if not np.isfinite(summary["rate_per_100"]).all():
        raise ValueError("Opponent rates must be finite.")
    return {
        "opponent_count": len(summary),
        "meeting_count": int(summary["meetings"].sum()),
        "elite_player_game_count": expected_elite,
        "elite_team_game_count": int(
            table.loc[table["game_score"] >= threshold, "game_id"].nunique()
        ),
        "overall_rate_per_100": expected_elite / expected_games * 100,
    }


def build_points_threshold_summary(
    table: pd.DataFrame,
    *,
    thresholds: tuple[int, ...] = POINT_THRESHOLDS,
    min_meetings: int = MIN_MEETINGS,
) -> pd.DataFrame:
    """Return one ranked opponent table for each points threshold."""
    required = {"game_id", "opponent", "points"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Working table is missing {sorted(missing)}.")
    if not thresholds or any(int(value) <= 0 for value in thresholds):
        raise ValueError("Point thresholds must be positive and non-empty.")

    rows = table[["game_id", "opponent"]].drop_duplicates().copy()
    rows["franchise"] = rows["opponent"].map(current_opponent)
    meetings = rows.groupby("franchise", as_index=False).agg(meetings=("game_id", "nunique"))
    if meetings["meetings"].min() < min_meetings:
        raise ValueError("Opponent sample is below the minimum meeting threshold.")

    outputs: list[pd.DataFrame] = []
    total_meetings = int(meetings["meetings"].sum())
    for threshold in sorted({int(value) for value in thresholds}):
        points = table.loc[table["points"] >= threshold, ["game_id", "opponent"]].copy()
        points["franchise"] = points["opponent"].map(current_opponent)
        counts = points.groupby("franchise").size().rename("point_games")
        result = pd.DataFrame({"franchise": list(FRANCHISE_NAMES)}).merge(
            meetings, on="franchise", how="left", validate="one_to_one"
        )
        result = result.join(counts, on="franchise")
        result["point_games"] = result["point_games"].fillna(0).astype(int)
        result["meetings"] = result["meetings"].astype(int)
        result["rate_per_100"] = result["point_games"] / result["meetings"] * 100
        overall_rate = int((table["points"] >= threshold).sum()) / total_meetings * 100
        result["relative_to_all"] = result["rate_per_100"] / overall_rate if overall_rate else 0.0
        result["team"] = result["franchise"].map(FRANCHISE_NAMES)
        result = result.sort_values(
            ["rate_per_100", "point_games", "meetings", "team"],
            ascending=[False, False, False, True],
            kind="stable",
        ).reset_index(drop=True)
        result["rank"] = result.index + 1
        result["threshold"] = threshold
        result["minimum_meetings"] = min_meetings
        result["coverage_start"] = f"{FIRST_SEASON_END_YEAR - 1}-{str(FIRST_SEASON_END_YEAR)[-2:]}"
        result["coverage_end"] = f"{LAST_SEASON_END_YEAR - 1}-{str(LAST_SEASON_END_YEAR)[-2:]}"
        outputs.append(result)

    return pd.concat(outputs, ignore_index=True)[
        [
            "threshold",
            "rank",
            "franchise",
            "team",
            "rate_per_100",
            "point_games",
            "meetings",
            "relative_to_all",
            "minimum_meetings",
            "coverage_start",
            "coverage_end",
        ]
    ]


def validate_points_threshold_summary(
    summary: pd.DataFrame,
    table: pd.DataFrame,
    *,
    thresholds: tuple[int, ...] = POINT_THRESHOLDS,
) -> dict[int, int]:
    """Reconcile each threshold's player-game count and meeting denominator."""
    expected_games = table[["game_id", "opponent"]].drop_duplicates()["game_id"].nunique()
    expected_thresholds = tuple(sorted({int(value) for value in thresholds}))
    if tuple(sorted(summary["threshold"].unique())) != expected_thresholds:
        raise ValueError("Point summary does not contain exactly the requested thresholds.")
    counts: dict[int, int] = {}
    for threshold in expected_thresholds:
        subset = summary.loc[summary["threshold"].eq(threshold)]
        if len(subset) != len(FRANCHISE_NAMES):
            raise ValueError(f"Expected 29 opponents at {threshold}+ points.")
        if int(subset["meetings"].sum()) != expected_games:
            raise ValueError(f"Opponent meetings do not reconcile at {threshold}+ points.")
        expected_count = int((table["points"] >= threshold).sum())
        if int(subset["point_games"].sum()) != expected_count:
            raise ValueError(f"Point-game counts do not reconcile at {threshold}+ points.")
        counts[threshold] = expected_count
    return counts


def build_count_summary(
    table: pd.DataFrame,
    *,
    metric: str,
    threshold: float = ELITE_GAME_SCORE,
    min_meetings: int = MIN_MEETINGS,
) -> pd.DataFrame:
    """Rank current opponents by the total number of qualifying player-games."""
    fields = {"points": "points", "game_score": "game_score"}
    if metric not in fields:
        raise ValueError(f"Unknown count metric: {metric}")
    required = {"game_id", "opponent", fields[metric]}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Working table is missing {sorted(missing)}.")

    rows = table[["game_id", "opponent"]].drop_duplicates().copy()
    rows["franchise"] = rows["opponent"].map(current_opponent)
    meetings = rows.groupby("franchise", as_index=False).agg(meetings=("game_id", "nunique"))
    summary = pd.DataFrame({"franchise": list(FRANCHISE_NAMES)}).merge(
        meetings, on="franchise", how="left", validate="one_to_one"
    )
    if summary["meetings"].isna().any():
        missing_codes = summary.loc[summary["meetings"].isna(), "franchise"].tolist()
        raise ValueError(f"Missing current opponent franchise rows: {missing_codes}")
    summary["meetings"] = summary["meetings"].astype(int)
    if (summary["meetings"] < min_meetings).any():
        excluded = summary.loc[summary["meetings"] < min_meetings, "franchise"].tolist()
        raise ValueError(f"Opponent sample is below the minimum for {excluded}")

    qualifying = table.loc[table[fields[metric]] >= threshold, ["game_id", "opponent"]].copy()
    qualifying["franchise"] = qualifying["opponent"].map(current_opponent)
    counts = qualifying.groupby("franchise").size().rename("qualifying_player_games")
    summary = summary.join(counts, on="franchise")
    summary["qualifying_player_games"] = summary["qualifying_player_games"].fillna(0).astype(int)
    summary["rate_per_100"] = summary["qualifying_player_games"] / summary["meetings"] * 100
    summary["team"] = summary["franchise"].map(FRANCHISE_NAMES)
    summary["conference"] = summary["franchise"].map(FRANCHISE_CONFERENCES)
    if summary["conference"].isna().any():
        missing_codes = summary.loc[summary["conference"].isna(), "franchise"].tolist()
        raise ValueError(f"Missing conference mapping for {missing_codes}")
    summary = summary.sort_values(
        ["qualifying_player_games", "rate_per_100", "team"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    summary["rank"] = summary.index + 1
    summary["metric"] = metric
    summary["threshold"] = float(threshold)
    summary["minimum_meetings"] = int(min_meetings)
    summary["coverage_start"] = f"{FIRST_SEASON_END_YEAR - 1}-{str(FIRST_SEASON_END_YEAR)[-2:]}"
    summary["coverage_end"] = f"{LAST_SEASON_END_YEAR - 1}-{str(LAST_SEASON_END_YEAR)[-2:]}"
    return summary[
        [
            "rank",
            "franchise",
            "team",
            "conference",
            "metric",
            "threshold",
            "qualifying_player_games",
            "meetings",
            "rate_per_100",
            "minimum_meetings",
            "coverage_start",
            "coverage_end",
        ]
    ]


def validate_count_summary(
    summary: pd.DataFrame,
    table: pd.DataFrame,
    *,
    metric: str,
    threshold: float = ELITE_GAME_SCORE,
) -> dict[str, object]:
    """Reconcile the 29-opponent count ranking to the working table."""
    if len(summary) != len(FRANCHISE_NAMES):
        raise ValueError(f"Expected 29 current opponents, got {len(summary)}")
    if summary["franchise"].duplicated().any():
        raise ValueError("Count summary contains duplicate franchises.")
    expected_games = table[["game_id", "opponent"]].drop_duplicates()["game_id"].nunique()
    if int(summary["meetings"].sum()) != expected_games:
        raise ValueError("Opponent meetings do not reconcile to distinct Bulls team games.")
    field = {"points": "points", "game_score": "game_score"}.get(metric)
    if field is None:
        raise ValueError(f"Unknown count metric: {metric}")
    expected_count = int((table[field] >= threshold).sum())
    if int(summary["qualifying_player_games"].sum()) != expected_count:
        raise ValueError("Qualifying player-game counts do not reconcile to the working table.")
    return {
        "opponent_count": len(summary),
        "meeting_count": int(summary["meetings"].sum()),
        "qualifying_player_game_count": expected_count,
        "qualifying_team_game_count": int(table.loc[table[field] >= threshold, "game_id"].nunique()),
    }


def rank_percentage_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """Return a count summary sorted by qualifying performances per meeting."""
    required = {"rate_per_100", "qualifying_player_games", "meetings", "team"}
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(f"Summary is missing {sorted(missing)}.")
    ranked = summary.sort_values(
        ["rate_per_100", "qualifying_player_games", "meetings", "team"],
        ascending=[False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    ranked["percentage_rank"] = ranked.index + 1
    return ranked


def _draw_gradient_bar(ax, x0: float, x1: float, y: float, height: float, colors, shadow_color) -> None:
    """Draw the rounded gradient bar used by the national-TV chart."""
    if x1 <= x0:
        return
    rounding = height * 0.28
    shape = dict(boxstyle=f"round,pad=0,rounding_size={rounding}", edgecolor="none", linewidth=0)
    shadow = FancyBboxPatch(
        (x0, y - height / 2),
        x1 - x0,
        height,
        facecolor=colors[1],
        path_effects=[
            PathEffects.withSimplePatchShadow(
                offset=(1.5, -2), shadow_rgbFace=shadow_color, alpha=0.30, rho=0.9
            ),
            PathEffects.Normal(),
        ],
        zorder=3,
        **shape,
    )
    ax.add_patch(shadow)
    clip = FancyBboxPatch(
        (x0, y - height / 2), x1 - x0, height, facecolor="none", zorder=4, **shape
    )
    ax.add_patch(clip)
    top, bottom = (np.array(to_rgb(color)) for color in colors)
    ramp = np.linspace(bottom, top, 256).reshape(256, 1, 3)
    image = ax.imshow(
        ramp,
        extent=(x0, x1, y - height / 2, y + height / 2),
        origin="lower",
        aspect="auto",
        interpolation="bicubic",
        zorder=4,
    )
    image.set_clip_path(clip)


def render_chart(summary: pd.DataFrame, *, final: bool = False) -> Path:
    """Render a national-TV-style ranked horizontal bar chart."""
    theme = DEFAULT_THEME
    label_font = helvetica()
    bold_font = helvetica("bold")
    fig, ax = plt.subplots(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    y = list(range(len(summary)))
    bar_height = 0.68
    max_rate = float(summary["rate_per_100"].max())
    x_max = max(15, int(math.ceil(max_rate / 5) * 5))
    for row_y, (_, row) in zip(y, summary.iterrows()):
        is_leader = int(row["rank"]) == 1
        gradient = ("#B5123C", "#7E0C2B") if is_leader else ("#333333", "#0C0C0C")
        shadow = "#7A1230" if is_leader else "#5A5048"
        _draw_gradient_bar(ax, 0, float(row["rate_per_100"]), row_y, bar_height, gradient, shadow)
        value_color = theme.accent if is_leader else theme.ink
        label = f"{row['rate_per_100']:.1f}%  {int(row['elite_player_games'])}/{int(row['meetings'])}"
        ax.text(
            float(row["rate_per_100"]) + 0.30,
            row_y,
            label,
            ha="left",
            va="center",
            color=value_color,
            fontproperties=bold_font,
            fontsize=13,
            zorder=5,
        )

    ax.set_xlim(-0.35, x_max + 1.55)
    ax.set_yticks(y, summary["team"].tolist())
    ax.set_ylim(len(summary) - 0.45, -0.78)
    ax.tick_params(axis="y", length=0, pad=10, colors=theme.muted, labelsize=12)
    for label in ax.get_yticklabels():
        label.set_fontproperties(bold_font)

    ax.set_xticks(range(0, x_max + 1, 5))
    ax.tick_params(axis="x", length=0, pad=8, colors=theme.muted, labelsize=10)
    for label in ax.get_xticklabels():
        label.set_fontproperties(label_font)
    ax.set_xlabel(
        "ELITE BULLS PERFORMANCES PER 100 MEETINGS",
        color=theme.muted,
        fontproperties=bold_font,
        fontsize=11,
        labelpad=14,
    )

    ax.xaxis.grid(True, color=theme.grid, linewidth=1.2, zorder=0)
    ax.get_xgridlines()[0].set_visible(False)
    ax.yaxis.grid(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    fig.subplots_adjust(left=0.215, right=0.985, top=0.985, bottom=0.08)
    OUT.mkdir(parents=True, exist_ok=True)
    resolution = "final" if final else "draft"
    output = OUT / f"2026-08-17-opponent-elite-performances-horizontal-{resolution}.png"
    fig.savefig(output, dpi=export_dpi(final), transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return output


def render_points_threshold_chart(summary: pd.DataFrame, *, final: bool = False) -> Path:
    """Render three national-TV-style panels for 30+, 40+, and 50+ points."""
    theme = DEFAULT_THEME
    label_font = helvetica()
    bold_font = helvetica("bold")
    thresholds = sorted(summary["threshold"].astype(int).unique())
    fig, axes = plt.subplots(
        1,
        len(thresholds),
        figsize=(24, CHART_HEIGHT / DRAFT_DPI),
        sharey=False,
        squeeze=False,
    )
    axes = axes[0]
    fig.patch.set_alpha(0)

    for axis, threshold in zip(axes, thresholds):
        panel = summary.loc[summary["threshold"].eq(threshold)].sort_values("rank")
        y = list(range(len(panel)))
        bar_height = 0.68
        max_rate = float(panel["rate_per_100"].max())
        x_max = max(2, int(math.ceil(max_rate / 5) * 5))
        for row_y, (_, row) in zip(y, panel.iterrows()):
            is_leader = int(row["rank"]) == 1
            gradient = ("#B5123C", "#7E0C2B") if is_leader else ("#333333", "#0C0C0C")
            shadow = "#7A1230" if is_leader else "#5A5048"
            _draw_gradient_bar(
                axis,
                0,
                float(row["rate_per_100"]),
                row_y,
                bar_height,
                gradient,
                shadow,
            )
            value_color = theme.accent if is_leader else theme.ink
            axis.text(
                float(row["rate_per_100"]) + max(x_max * 0.012, 0.08),
                row_y,
                f"{row['rate_per_100']:.1f}%  {int(row['point_games'])}/{int(row['meetings'])}",
                ha="left",
                va="center",
                color=value_color,
                fontproperties=bold_font,
                fontsize=10.5,
                zorder=5,
            )

        axis.set_xlim(-0.35, x_max + max(x_max * 0.30, 1.0))
        axis.set_yticks(y, panel["team"].tolist())
        axis.set_ylim(len(panel) - 0.45, -0.78)
        axis.tick_params(axis="y", length=0, pad=8, colors=theme.muted, labelsize=10.5)
        for label in axis.get_yticklabels():
            label.set_fontproperties(bold_font)
        axis.set_xticks(range(0, x_max + 1, 5) if x_max >= 5 else range(0, x_max + 1))
        axis.tick_params(axis="x", length=0, pad=7, colors=theme.muted, labelsize=9)
        for label in axis.get_xticklabels():
            label.set_fontproperties(label_font)
        axis.set_title(
            f"{threshold}+ POINTS",
            color=theme.ink,
            fontproperties=bold_font,
            fontsize=15,
            pad=16,
        )
        axis.set_xlabel(
            "PER 100 MEETINGS",
            color=theme.muted,
            fontproperties=bold_font,
            fontsize=9.5,
            labelpad=12,
        )
        axis.xaxis.grid(True, color=theme.grid, linewidth=1.2, zorder=0)
        axis.get_xgridlines()[0].set_visible(False)
        axis.yaxis.grid(False)
        for side in ("top", "right", "bottom", "left"):
            axis.spines[side].set_visible(False)

    fig.subplots_adjust(left=0.05, right=0.99, top=0.965, bottom=0.08, wspace=0.22)
    OUT.mkdir(parents=True, exist_ok=True)
    resolution = "final" if final else "draft"
    output = OUT / f"2026-08-17-opponent-points-thresholds-horizontal-{resolution}.png"
    fig.savefig(output, dpi=export_dpi(final), transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return output


def render_count_chart(
    summary: pd.DataFrame,
    *,
    metric: str,
    mode: str = "count",
    clean: bool = False,
    axisless: bool = False,
    final: bool = False,
) -> Path:
    """Render one opponent chart with a logo beside every team.

    ``clean=True`` is the logo-and-bars-only Canva handoff variant.  The
    ``axisless=True`` variant keeps team names and data labels while removing
    the x-axis decorations, which is the primary handoff for this post.
    """
    if mode not in {"count", "percentage"}:
        raise ValueError(f"Unknown chart mode: {mode}")
    if clean and mode != "percentage":
        raise ValueError("The clean handoff chart is only defined for percentage mode.")
    theme = DEFAULT_THEME
    label_font = helvetica()
    bold_font = helvetica("bold")
    fig, ax = plt.subplots(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    display_summary = rank_percentage_summary(summary) if mode == "percentage" else summary.copy()
    y = list(range(len(display_summary)))
    bar_height = 0.68
    threshold = int(display_summary["threshold"].iloc[0])
    value_column = "qualifying_player_games" if mode == "count" else "rate_per_100"
    max_value = float(display_summary[value_column].max())
    tick_step = 5 if mode == "count" else 10
    x_max = max(tick_step * 2, int(math.ceil(max_value / tick_step) * tick_step))
    for row_y, (_, row) in zip(y, display_summary.iterrows()):
        conference = row["conference"]
        if mode == "percentage":
            gradient = WEST_GRADIENT if conference == "West" else EAST_GRADIENT
            shadow = WEST_SHADOW if conference == "West" else EAST_SHADOW
        else:
            is_leader = row_y == 0
            gradient = ("#B5123C", "#7E0C2B") if is_leader else ("#333333", "#0C0C0C")
            shadow = "#7A1230" if is_leader else "#5A5048"
        value = float(row[value_column])
        _draw_gradient_bar(ax, 0, value, row_y, bar_height, gradient, shadow)
        if not clean or axisless:
            value_color = (WEST_GRADIENT[1] if conference == "West" else EAST_GRADIENT[1]) if mode == "percentage" else (theme.accent if row_y == 0 else theme.ink)
            label = (
                f"{int(row['qualifying_player_games'])}/{int(row['meetings'])} ({value:.1f}%)"
                if mode == "percentage"
                else f"{int(row['qualifying_player_games'])}"
            )
            ax.text(
                value + 0.30,
                row_y,
                label,
                ha="left",
                va="center",
                color=value_color,
                fontproperties=bold_font,
                fontsize=13,
                zorder=5,
            )

        # Team names and marks are drawn explicitly so the logos stay aligned
        # even when a name wraps or a count is zero.
        if not clean or axisless:
            ax.text(
                -0.02,
                row_y,
                row["team"],
                ha="right",
                va="center",
                color=theme.muted,
                fontproperties=bold_font,
                fontsize=11 if len(str(row["team"])) > 10 else 12,
                transform=ax.get_yaxis_transform(),
                clip_on=False,
                zorder=5,
            )
        logo_path = LOGO_DIR / f"{row['franchise']}.png"
        if logo_path.exists():
            logo = OffsetImage(imread(logo_path), zoom=0.085)
            logo_box = AnnotationBbox(
                logo,
                (-0.055 if clean and not axisless else -0.16, row_y),
                xycoords=("axes fraction", "data"),
                box_alignment=(0.5, 0.5),
                frameon=False,
                pad=0,
                annotation_clip=False,
                zorder=6,
            )
            ax.add_artist(logo_box)

    if clean or axisless:
        # Keep the logo margin inside the saved transparent canvas while
        # removing every axis decoration from the Canva handoff asset.
        if clean:
            ax.set_xlim(-0.55, max_value * 1.04)
            ax.set_ylim(len(summary) - 0.45, -0.45)
        else:
            ax.set_xlim(-0.35, max_value + max(3.0, max_value * 0.16))
            ax.set_ylim(len(summary) - 0.45, -0.78)
        ax.set_axis_off()
    else:
        ax.set_xlim(-0.35, x_max + max(3.0, x_max * 0.16))
        ax.set_ylim(len(summary) - 0.45, -0.78)
        ax.set_yticks([])
        ax.set_xticks(range(0, x_max + 1, tick_step))
        ax.tick_params(axis="x", length=0, pad=8, colors=theme.muted, labelsize=10)
        for label in ax.get_xticklabels():
            label.set_fontproperties(label_font)
        if mode == "percentage":
            xlabel = "QUALIFYING PLAYER-GAMES / BULLS MEETINGS (%)"
        else:
            xlabel = (
                f"TOTAL {threshold}+ POINT PLAYER-GAMES"
                if metric == "points"
                else f"TOTAL GAME SCORE {threshold}+ PLAYER-GAMES"
            )
        ax.set_xlabel(
            xlabel,
            color=theme.muted,
            fontproperties=bold_font,
            fontsize=11,
            labelpad=14,
        )
        ax.xaxis.grid(True, color=theme.grid, linewidth=1.2, zorder=0)
        ax.get_xgridlines()[0].set_visible(False)
        ax.yaxis.grid(False)
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(False)

    if mode == "percentage" and not clean and not axisless:
        handles = [
            Patch(facecolor=WEST_GRADIENT[0], edgecolor="none", label="WEST"),
            Patch(facecolor=EAST_GRADIENT[0], edgecolor="none", label="EAST"),
        ]
        fig.legend(
            handles=handles,
            loc="upper right",
            bbox_to_anchor=(0.985, 1.01),
            ncol=2,
            frameon=False,
            prop=bold_font,
            labelcolor=theme.muted,
            handlelength=1.3,
            handleheight=0.8,
            columnspacing=1.0,
        )

    fig.subplots_adjust(
        left=0.08 if clean else 0.24,
        right=0.985,
        top=0.985,
        bottom=0.03 if clean or axisless else 0.08,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    resolution = "final" if final else "draft"
    name = f"{threshold}plus-points" if metric == "points" else "game-score"
    suffix = "total-count" if mode == "count" else "percentage"
    if clean:
        output = OUT / f"2026-08-18-opponent-{name}-{suffix}-bars-only-horizontal-{resolution}.png"
    elif axisless:
        output = OUT / f"2026-08-18-opponent-{name}-{suffix}-labeled-axisless-horizontal-{resolution}.png"
    else:
        output = OUT / f"2026-08-17-opponent-{name}-{suffix}-horizontal-{resolution}.png"
    fig.savefig(output, dpi=export_dpi(final), transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return output


def write_data(table: pd.DataFrame, teams: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Write the post-owned audit tables beside the chart."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    player_columns = [
        "season_end_year",
        "season",
        "player_id",
        "player",
        "game_id",
        "game_date",
        "matchup",
        "opponent",
        "result",
        "minutes",
        "points",
        "fgm",
        "fga",
        "ftm",
        "fta",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pf",
        "game_score",
        "ts_pct",
        "player_source_url",
    ]
    table[player_columns].assign(franchise=table["opponent"].map(current_opponent)).to_csv(
        DATA_DIR / "opponent-elite-performance-player-games.csv", index=False
    )
    team_columns = [
        "season_end_year",
        "game_id",
        "game_date",
        "matchup",
        "result",
        "team_points",
        "team_plus_minus",
        "team_source_url",
    ]
    teams[team_columns].assign(franchise=teams["matchup"].str.extract(r"(?:vs\.|@)\s*([A-Z]+)$")[0].map(current_opponent)).to_csv(
        DATA_DIR / "opponent-elite-performance-team-games.csv", index=False
    )
    summary.to_csv(DATA_DIR / "opponent-elite-performance-summary.csv", index=False)


def copy_block(summary: pd.DataFrame, audit: dict[str, object]) -> str:
    leader = summary.iloc[0]
    return "\n".join(
        [
            "CANVA COPY",
            "Title: WHICH TEAMS BRING OUT THE BEST BULLS PERFORMANCES?",
            "Subtitle: Game Score 30+ performances per 100 meetings, regular season since 2000",
            (
                "Method: Count every Bulls player-game with a Hollinger Game Score of 30 or higher, "
                "then divide by Bulls regular-season meetings with that opponent. Multiple qualifying "
                "players in one game count separately."
            ),
            (
                "Footnote: All 29 current opponent franchises qualify for the 40-meeting minimum. "
                "Historical abbreviations are mapped to current franchises. Game Score measures "
                "box-score productivity, not complete player impact."
            ),
            "Source: NBA.com PlayerGameLogs and LeagueGameFinder; calculated locally",
            (
                f"Check: {leader['team']} leads at {leader['rate_per_100']:.1f}% "
                f"({int(leader['elite_player_games'])} in {int(leader['meetings'])}); "
                f"{audit['elite_player_game_count']} qualifying player-games across "
                f"{audit['meeting_count']} Bulls team games"
            ),
        ]
    )


def points_copy_block(summary: pd.DataFrame, counts: dict[int, int]) -> str:
    lines = [
        "CANVA COPY",
        "Title: WHICH TEAMS BRING OUT THE MOST BIG BULLS SCORING GAMES?",
        "Subtitle: 30+, 40+ and 50-point games per 100 meetings, regular season since 2000",
        (
            "Method: Count Bulls player-games at each points threshold, then divide by Bulls "
            "regular-season meetings with that opponent. Multiple qualifying players in one game count separately."
        ),
        (
            "Footnote: All 29 current opponent franchises qualify for the 40-meeting minimum. "
            "This is a scoring-volume view, separate from Game Score productivity."
        ),
        "Source: NBA.com PlayerGameLogs and LeagueGameFinder; calculated locally",
    ]
    for threshold in sorted(counts):
        leader = summary.loc[summary["threshold"].eq(threshold)].sort_values("rank").iloc[0]
        lines.append(
            f"Check {threshold}+: {leader['team']} leads at {leader['rate_per_100']:.1f}% "
            f"({int(leader['point_games'])} in {int(leader['meetings'])}); {counts[threshold]} total player-games"
        )
    return "\n".join(lines)


def count_copy_block(summary: pd.DataFrame, audit: dict[str, object], *, metric: str) -> str:
    """Print the exact copy block for one count-based mockup."""
    leader = summary.iloc[0]
    threshold = int(summary["threshold"].iloc[0])
    if metric == "points":
        title = f"WHICH TEAMS PRODUCE THE MOST {threshold}-POINT BULLS GAMES?"
        subtitle = f"Total Bulls player-games with {threshold}+ points, regular season since 2000"
        method = (
            f"Count every Bulls player-game with at least {threshold} points against each opponent. "
            "Multiple qualifying players in one game count separately."
        )
    else:
        title = "WHICH TEAMS PRODUCE THE MOST ELITE BULLS GAMES?"
        subtitle = f"Total Bulls player-games with a Game Score of {threshold}+, regular season since 2000"
        method = (
            f"Count every Bulls player-game with a Hollinger Game Score of {threshold} or higher against "
            "each opponent. Multiple qualifying players in one game count separately."
        )
    return "\n".join(
        [
            "CANVA COPY",
            f"Title: {title}",
            f"Subtitle: {subtitle}",
            f"Method: {method}",
            (
                "Footnote: All 29 current opponent franchises qualify for the 40-meeting minimum. "
                "This chart shows raw qualifying-game counts, not a percentage or rate."
            ),
            "Source: NBA.com PlayerGameLogs and LeagueGameFinder; calculated locally",
            (
                f"Check: {leader['team']} leads with {int(leader['qualifying_player_games'])} qualifying "
                f"player-games across {int(leader['meetings'])} meetings; "
                f"{audit['qualifying_player_game_count']} total qualifying player-games"
            ),
        ]
    )


def write_count_data(summary: pd.DataFrame, *, metric: str) -> Path:
    """Write one tracked summary table for a count-based mockup."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    threshold = int(summary["threshold"].iloc[0])
    name = f"{threshold}plus-points" if metric == "points" else "game-score"
    path = DATA_DIR / f"opponent-{name}-total-count-summary.csv"
    summary.to_csv(path, index=False)
    return path


def percentage_copy_block(summary: pd.DataFrame, audit: dict[str, object], *, metric: str) -> str:
    """Print the exact copy block for a percentage-ranked mockup."""
    ranked = rank_percentage_summary(summary)
    leader = ranked.iloc[0]
    threshold = int(leader["threshold"])
    if metric == "points":
        title = f"WHICH TEAMS PRODUCE THE MOST {threshold}-POINT BULLS GAMES?"
        subtitle = f"30+ point games per Bulls meeting, regular season since 2000" if threshold == 30 else f"25+ point games per Bulls meeting, regular season since 2000"
    else:
        title = "WHICH TEAMS PRODUCE THE MOST ELITE BULLS GAMES?"
        subtitle = "Game Score 30+ games per Bulls meeting, regular season since 2000"
    return "\n".join(
        [
            "CANVA COPY",
            f"Title: {title}",
            f"Subtitle: {subtitle}",
            (
                "Method: Count qualifying Bulls player-games against each opponent and divide by "
                "distinct Bulls meetings with that opponent. Multiple qualifying players in one game count separately."
            ),
            (
                "Footnote: All 29 current opponent franchises qualify for the 40-meeting minimum. "
                "Labels show count / meetings (%); this is a qualifying-performance rate, not strictly "
                "the percentage of team games with at least one qualifier."
            ),
            "Source: NBA.com PlayerGameLogs and LeagueGameFinder; calculated locally",
            (
                f"Check: {leader['team']} leads at {leader['rate_per_100']:.1f}% "
                f"({int(leader['qualifying_player_games'])} / {int(leader['meetings'])}); "
                f"{audit['qualifying_player_game_count']} total qualifying player-games"
            ),
        ]
    )


def write_percentage_data(summary: pd.DataFrame, *, metric: str) -> Path:
    """Write the percentage-ranked view used by the chart."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ranked = rank_percentage_summary(summary)
    threshold = int(ranked["threshold"].iloc[0])
    name = f"{threshold}plus-points" if metric == "points" else "game-score"
    path = DATA_DIR / f"opponent-{name}-percentage-summary.csv"
    ranked.to_csv(path, index=False)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true", help="render the full-resolution chart")
    parser.add_argument("--refresh", action="store_true", help="refetch missing NBA.com cache rows")
    parser.add_argument(
        "--points-thresholds",
        action="store_true",
        help="render the alternate 30+, 40+, and 50+ points comparison",
    )
    parser.add_argument(
        "--count-versions",
        action="store_true",
        help="render the 30+ points and Game Score 30+ count-ranked mockups",
    )
    parser.add_argument(
        "--points-25",
        action="store_true",
        help="render the 25+ points count-ranked mockup",
    )
    parser.add_argument(
        "--percentage-versions",
        action="store_true",
        help="render normalized 25+ points, 30+ points, and Game Score 30+ mockups",
    )
    parser.add_argument(
        "--clean-30plus",
        action="store_true",
        help="render the label-free 30+ points Canva handoff with conference-colored bars and logos",
    )
    parser.add_argument(
        "--axisless-30plus",
        action="store_true",
        help="render the 30+ points handoff with team names and data labels but no x-axis decorations",
    )
    args = parser.parse_args()

    players, teams = fetch_bulls_history(refresh=args.refresh)
    table = build_working_table(players, teams)
    if args.clean_30plus:
        summary = build_count_summary(table, metric="points", threshold=30)
        audit = validate_count_summary(summary, table, metric="points", threshold=30)
        write_percentage_data(summary, metric="points")
        output = render_count_chart(
            summary,
            metric="points",
            mode="percentage",
            clean=True,
            final=args.final,
        )
        print(f"Saved {output.relative_to(_REPO)}")
        print(f"Audit: {audit}")
        print(
            rank_percentage_summary(summary)[
                ["percentage_rank", "team", "conference", "qualifying_player_games", "meetings", "rate_per_100"]
            ].to_string(index=False)
        )
        return
    if args.axisless_30plus:
        summary = build_count_summary(table, metric="points", threshold=30)
        audit = validate_count_summary(summary, table, metric="points", threshold=30)
        write_percentage_data(summary, metric="points")
        output = render_count_chart(
            summary,
            metric="points",
            mode="percentage",
            axisless=True,
            final=args.final,
        )
        print(f"Saved {output.relative_to(_REPO)}")
        print(f"Audit: {audit}")
        print(
            rank_percentage_summary(summary)[
                ["percentage_rank", "team", "conference", "qualifying_player_games", "meetings", "rate_per_100"]
            ].to_string(index=False)
        )
        return
    if args.count_versions:
        for metric in ("points", "game_score"):
            summary = build_count_summary(table, metric=metric)
            audit = validate_count_summary(summary, table, metric=metric)
            write_count_data(summary, metric=metric)
            output = render_count_chart(summary, metric=metric, final=args.final)
            print(f"Saved {output.relative_to(_REPO)}")
            print(f"Audit: {audit}")
            print(count_copy_block(summary, audit, metric=metric))
            print()
            print(
                summary[["rank", "team", "qualifying_player_games", "meetings"]]
                .head(10)
                .to_string(index=False)
            )
            print()
        return
    if args.points_25:
        summary = build_count_summary(table, metric="points", threshold=25)
        audit = validate_count_summary(summary, table, metric="points", threshold=25)
        write_count_data(summary, metric="points")
        output = render_count_chart(summary, metric="points", final=args.final)
        print(f"Saved {output.relative_to(_REPO)}")
        print(f"Audit: {audit}")
        print(count_copy_block(summary, audit, metric="points"))
        print()
        print(summary[["rank", "team", "qualifying_player_games", "meetings"]].to_string(index=False))
        return
    if args.percentage_versions:
        versions = (("points", 25), ("points", 30), ("game_score", 30))
        for metric, threshold in versions:
            summary = build_count_summary(table, metric=metric, threshold=threshold)
            audit = validate_count_summary(summary, table, metric=metric, threshold=threshold)
            write_percentage_data(summary, metric=metric)
            output = render_count_chart(summary, metric=metric, mode="percentage", final=args.final)
            print(f"Saved {output.relative_to(_REPO)}")
            print(f"Audit: {audit}")
            print(percentage_copy_block(summary, audit, metric=metric))
            print()
            print(
                rank_percentage_summary(summary)[
                    ["percentage_rank", "team", "qualifying_player_games", "meetings", "rate_per_100"]
                ]
                .head(10)
                .to_string(index=False)
            )
            print()
        return
    if args.points_thresholds:
        summary = build_points_threshold_summary(table)
        counts = validate_points_threshold_summary(summary, table)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary.to_csv(DATA_DIR / "opponent-points-threshold-summary.csv", index=False)
        output = render_points_threshold_chart(summary, final=args.final)
        print(f"Saved {output.relative_to(_REPO)}")
        print(points_copy_block(summary, counts))
        print()
        print(summary[["threshold", "rank", "team", "rate_per_100", "point_games", "meetings"]].to_string(index=False))
        return
    summary = build_opponent_summary(table)
    audit = validate_summary(summary, table)
    write_data(table, teams, summary)
    output = render_chart(summary, final=args.final)
    print(f"Saved {output.relative_to(_REPO)}")
    print(f"Audit: {audit}")
    print()
    print(copy_block(summary, audit))
    print()
    print(summary[["rank", "team", "rate_per_100", "elite_player_games", "meetings"]].to_string(index=False))


if __name__ == "__main__":
    main()
