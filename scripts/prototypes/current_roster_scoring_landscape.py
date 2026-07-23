"""Build a current Bulls roster scoring landscape chart for Canva.

NBA.com supplies current roster membership and each player's complete 2025-26
regular-season totals across all teams. The same official totals produce the
250-true-shooting-attempt qualification and both plotted axes: true shooting
attempts per 100 possessions (SHOTS) and relative true shooting percentage.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats

from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    body_font,
    draw_footer,
    draw_header,
    export_dpi,
    new_canvas,
    rendered_width,
    save_post,
)
from scripts.prototypes.current_roster_darko_landscape import (
    NBA_ROSTER_URL,
    _fetch_html,
    ensure_headshots,
    helvetica,
    parse_nba_roster,
    square_headshot_label,
)


SEASON = "2025-26"
SEASON_TYPE = "Regular Season"
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
MIN_TRUE_SHOOTING_ATTEMPTS = 250.0
OUT = _REPO / "output" / "feed"
HEADSHOTS = _REPO / "cache" / "headshots"

NBA_PLAYER_STATS_URL = (
    "https://www.nba.com/stats/players/advanced"
    "?Season=2025-26&SeasonType=Regular%20Season"
)
NBA_TEAM_STATS_URL = (
    "https://www.nba.com/stats/teams/traditional"
    "?Season=2025-26&SeasonType=Regular%20Season&PerMode=Totals"
)

CHART_WIDTH = 1080
CHART_HEIGHT = 1030
PANEL = (188, 178, 1015, 956)  # x0, y0, x1, y1
RTS_LIMITS = (-14.5, 8.0)
SHOTS_LIMITS = (12.0, 29.5)

SHORT_NAMES = {
    "Josh Giddey": "GIDDEY",
    "Rob Dillingham": "DILLINGHAM",
    "Nic Claxton": "CLAXTON",
    "Leonard Miller": "L. MILLER",
    "Matas Buzelis": "BUZELIS",
    "Norman Powell": "POWELL",
    "Jalen Smith": "J. SMITH",
    "Tre Jones": "T. JONES",
    "Isaac Okoro": "OKORO",
    "Patrick Williams": "P. WILLIAMS",
}

# Tre Jones and Leonard Miller remain on their true, naturally overlapping
# coordinates. Separate text anchors keep both identities readable.
CUSTOM_LABELS = {
    "Tre Jones": {
        "dx": 48,
        "dy": 10,
        "ha": "left",
        "va": "center",
    },
    "Leonard Miller": {
        "dx": -12,
        "dy": -43,
        "ha": "right",
        "va": "top",
    },
}


def fetch_season_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch full-season player totals and league team totals from NBA.com."""
    common = {
        "season": SEASON,
        "season_type_all_star": SEASON_TYPE,
        "per_mode_detailed": "Totals",
        "timeout": 60,
        "headers": _NBA_HEADERS,
    }
    base = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Base",
        **common,
    ).get_data_frames()[0]
    advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Advanced",
        **common,
    ).get_data_frames()[0]
    teams = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense="Base",
        **common,
    ).get_data_frames()[0]
    return base, advanced, teams


def build_working_table(
    roster: pd.DataFrame,
    base: pd.DataFrame,
    advanced: pd.DataFrame,
    teams: pd.DataFrame,
    snapshot_time: datetime,
) -> pd.DataFrame:
    """Join the current roster to full-season NBA totals and calculate axes."""
    player_columns = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GP",
        "MIN",
        "FGA",
        "FTA",
        "PTS",
    ]
    advanced_columns = ["PLAYER_ID", "POSS", "TS_PCT"]
    team_columns = ["PTS", "FGA", "FTA"]

    missing_player_columns = set(player_columns) - set(base.columns)
    missing_advanced_columns = set(advanced_columns) - set(advanced.columns)
    missing_team_columns = set(team_columns) - set(teams.columns)
    if missing_player_columns or missing_advanced_columns or missing_team_columns:
        raise ValueError(
            "NBA.com response columns changed: "
            f"base={sorted(missing_player_columns)}, "
            f"advanced={sorted(missing_advanced_columns)}, "
            f"teams={sorted(missing_team_columns)}"
        )

    league_tsa = float(teams["FGA"].sum() + 0.44 * teams["FTA"].sum())
    if league_tsa <= 0:
        raise ValueError("NBA.com league totals produced zero true shooting attempts.")
    league_ts_pct = float(teams["PTS"].sum() / (2 * league_tsa))

    players = base[player_columns].merge(
        advanced[advanced_columns],
        on="PLAYER_ID",
        how="inner",
        validate="one_to_one",
    )
    players = players.rename(
        columns={
            "PLAYER_ID": "nba_id",
            "PLAYER_NAME": "season_player_name",
            "TEAM_ABBREVIATION": "season_team_field",
            "GP": "games",
            "MIN": "minutes",
            "FGA": "fga",
            "FTA": "fta",
            "PTS": "points",
            "POSS": "possessions",
            "TS_PCT": "nba_ts_pct",
        }
    )

    table = roster.merge(players, on="nba_id", how="left", validate="one_to_one")
    numeric_columns = [
        "games",
        "minutes",
        "fga",
        "fta",
        "points",
        "possessions",
        "nba_ts_pct",
    ]
    for column in numeric_columns:
        table[column] = pd.to_numeric(table[column], errors="coerce")

    table["data_available"] = (
        table["fga"].notna()
        & table["fta"].notna()
        & table["points"].notna()
        & table["possessions"].gt(0)
    )
    table["true_shooting_attempts"] = table["fga"] + 0.44 * table["fta"]
    table["ts_pct"] = table["points"] / (
        2 * table["true_shooting_attempts"]
    )
    table["relative_ts_pp"] = (table["ts_pct"] - league_ts_pct) * 100
    table["shots_per_100"] = (
        table["true_shooting_attempts"] * 100 / table["possessions"]
    )
    table["qualified"] = (
        table["data_available"]
        & table["true_shooting_attempts"].ge(MIN_TRUE_SHOOTING_ATTEMPTS)
    )
    table["league_ts_pct"] = league_ts_pct
    table["qualification_tsa"] = MIN_TRUE_SHOOTING_ATTEMPTS
    table["roster_source"] = NBA_ROSTER_URL
    table["player_stats_source"] = NBA_PLAYER_STATS_URL
    table["league_stats_source"] = NBA_TEAM_STATS_URL
    table["snapshot_date"] = snapshot_time.date().isoformat()
    table["snapshot_timestamp_ct"] = snapshot_time.isoformat(timespec="seconds")
    table["season"] = SEASON
    table["season_type"] = SEASON_TYPE

    return table[
        [
            "nba_id",
            "official_roster_name",
            "season_player_name",
            "season_team_field",
            "games",
            "minutes",
            "fga",
            "fta",
            "points",
            "possessions",
            "true_shooting_attempts",
            "nba_ts_pct",
            "ts_pct",
            "league_ts_pct",
            "relative_ts_pp",
            "shots_per_100",
            "data_available",
            "qualified",
            "qualification_tsa",
            "season",
            "season_type",
            "roster_source",
            "player_stats_source",
            "league_stats_source",
            "snapshot_date",
            "snapshot_timestamp_ct",
        ]
    ]


def qualified_players(table: pd.DataFrame) -> pd.DataFrame:
    """Return qualifiers in portrait-layer order, with lower rTS drawn last."""
    return (
        table.loc[table["qualified"]]
        .copy()
        .sort_values(
            ["relative_ts_pp", "official_roster_name"],
            ascending=[False, True],
        )
    )


def validate_working_table(table: pd.DataFrame) -> dict:
    """Validate identities, formulas, threshold behavior, and chart coverage."""
    if table["nba_id"].duplicated().any():
        raise ValueError("Working table contains duplicate NBA player IDs.")
    if table["official_roster_name"].duplicated().any():
        raise ValueError("Working table contains duplicate roster names.")

    available = table.loc[table["data_available"]].copy()
    qualifiers = qualified_players(table)
    if available.empty:
        raise ValueError("No current-roster players had 2025-26 NBA data.")
    if qualifiers.empty:
        raise ValueError("No current-roster players met the TSA qualification.")
    if qualifiers["official_roster_name"].map(SHORT_NAMES).isna().any():
        missing = qualifiers.loc[
            qualifiers["official_roster_name"].map(SHORT_NAMES).isna(),
            "official_roster_name",
        ].tolist()
        raise ValueError(f"Missing chart labels for qualifiers: {missing}")

    required_numbers = [
        "true_shooting_attempts",
        "ts_pct",
        "league_ts_pct",
        "relative_ts_pp",
        "shots_per_100",
    ]
    if qualifiers[required_numbers].isna().any().any():
        raise ValueError("Qualified rows contain missing calculated values.")
    if not qualifiers["true_shooting_attempts"].ge(
        MIN_TRUE_SHOOTING_ATTEMPTS
    ).all():
        raise ValueError("A plotted player fell below the TSA qualification.")

    official_ts_gap = (
        available["nba_ts_pct"] - available["ts_pct"]
    ).abs()
    max_official_ts_gap = float(official_ts_gap.max())
    if max_official_ts_gap > 0.00051:
        raise ValueError(
            "Calculated TS% diverged from NBA.com's rounded TS%: "
            f"{max_official_ts_gap:.6f}"
        )

    raw_points_per_100 = available["points"] * 100 / available["possessions"]
    axes_points_per_100 = 2 * available["ts_pct"] * available["shots_per_100"]
    max_points_per_100_residual = float(
        (raw_points_per_100 - axes_points_per_100).abs().max()
    )
    if max_points_per_100_residual > 0.000001:
        raise ValueError(
            "NBA.com formulas do not reconstruct points per 100: "
            f"{max_points_per_100_residual:.8f}"
        )

    return {
        "roster_count": int(len(table)),
        "data_available_count": int(len(available)),
        "qualified_count": int(len(qualifiers)),
        "qualified_names": qualifiers["official_roster_name"].tolist(),
        "below_threshold_names": sorted(
            table.loc[
                table["data_available"] & ~table["qualified"],
                "official_roster_name",
            ].tolist()
        ),
        "no_2025_26_nba_data_names": sorted(
            table.loc[~table["data_available"], "official_roster_name"].tolist()
        ),
        "league_ts_pct": float(qualifiers["league_ts_pct"].iloc[0]),
        "roster_median_shots_per_100": float(
            qualifiers["shots_per_100"].median()
        ),
        "max_official_ts_gap": max_official_ts_gap,
        "max_points_per_100_residual": max_points_per_100_residual,
    }


def write_table(table: pd.DataFrame, snapshot_date: str) -> Path:
    """Write the complete roster table, including excluded players."""
    path = OUT / f"{snapshot_date}-current-bulls-scoring-landscape-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def chart_x(shots_per_100: float) -> float:
    """Map DataBallr SHOTS into chart pixels."""
    x0, _, x1, _ = PANEL
    return x0 + (shots_per_100 - SHOTS_LIMITS[0]) / (
        SHOTS_LIMITS[1] - SHOTS_LIMITS[0]
    ) * (x1 - x0)


def chart_y(relative_ts_pp: float) -> float:
    """Map relative TS percentage points into chart pixels."""
    _, y0, _, y1 = PANEL
    return y0 + (relative_ts_pp - RTS_LIMITS[0]) / (
        RTS_LIMITS[1] - RTS_LIMITS[0]
    ) * (y1 - y0)


def _quadrant_pill(
    ax,
    anchor_x: float,
    anchor_y: float,
    horizontal: str,
    vertical: str,
    title: str,
) -> None:
    """Draw one DARKO-style descriptive quadrant key."""
    theme = DEFAULT_THEME
    line_count = title.count("\n") + 1
    title_probe = ax.text(
        0,
        0,
        title,
        fontsize=8.7,
        fontproperties=helvetica("bold"),
        linespacing=0.95,
        alpha=0,
    )
    title_width = rendered_width(ax, title_probe)
    title_probe.remove()

    box_width = title_width + 24
    box_height = 32 if line_count == 1 else 54
    left = anchor_x if horizontal == "left" else anchor_x - box_width
    bottom = anchor_y if vertical == "bottom" else anchor_y - box_height
    ax.add_patch(
        FancyBboxPatch(
            (left, bottom),
            box_width,
            box_height,
            boxstyle="round,pad=0,rounding_size=9",
            facecolor=theme.canvas,
            edgecolor=theme.rule,
            linewidth=1.0,
            alpha=0.94,
            zorder=10,
        )
    )
    ax.text(
        left + 12,
        bottom + box_height / 2,
        title,
        ha="left",
        va="center",
        fontsize=8.7,
        color=theme.ink,
        fontproperties=helvetica("bold"),
        linespacing=1.14,
        zorder=11,
    )


def render_chart_only(
    table: pd.DataFrame,
    snapshot_date: str,
    final: bool,
) -> Path:
    """Render the transparent DARKO-style chart asset for Canva framing."""
    theme = DEFAULT_THEME
    panel_fill = "#F5F1EC"
    qualifiers = qualified_players(table)
    roster_median = float(qualifiers["shots_per_100"].median())

    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    x0, y0, x1, y1 = PANEL
    ax.add_patch(
        FancyBboxPatch(
            (x0 - 16, y0 - 14),
            x1 - x0 + 30,
            y1 - y0 + 26,
            boxstyle="round,pad=0,rounding_size=12",
            facecolor=panel_fill,
            edgecolor="none",
            zorder=0,
        )
    )

    for value in [15.0, 20.0, 25.0]:
        x = chart_x(value)
        ax.plot(
            [x, x],
            [y0, y1],
            color=theme.grid,
            lw=1.0,
            zorder=2,
        )
        ax.plot([x, x], [y0, y0 - 9], color=theme.ink, lw=1.5, zorder=5)
        ax.text(
            x,
            y0 - 20,
            f"{value:g}",
            ha="center",
            va="top",
            fontsize=12.5,
            color=theme.ink,
            fontproperties=helvetica(),
        )

    for value in [-10.0, -5.0, 0.0, 5.0]:
        y = chart_y(value)
        is_baseline = value == 0.0
        ax.plot(
            [x0, x1],
            [y, y],
            color=theme.muted if is_baseline else theme.grid,
            lw=1.25 if is_baseline else 1.0,
            linestyle=(0, (4, 4)) if is_baseline else "solid",
            alpha=0.72 if is_baseline else 1.0,
            zorder=2,
        )
        ax.plot([x0, x0 - 9], [y, y], color=theme.ink, lw=1.5, zorder=5)
        tick = f"+{value:g}" if value > 0 else f"{value:g}"
        ax.text(
            x0 - 18,
            y,
            tick,
            ha="right",
            va="center",
            fontsize=12.5,
            color=theme.ink,
            fontproperties=helvetica(),
        )

    median_x = chart_x(roster_median)
    ax.plot(
        [median_x, median_x],
        [y0, y1],
        color=theme.muted,
        lw=1.25,
        linestyle=(0, (4, 4)),
        alpha=0.72,
        zorder=3,
    )
    ax.text(
        median_x - 10,
        chart_y(-6.5),
        f"ROSTER MEDIAN  {roster_median:.1f}",
        ha="center",
        va="center",
        rotation=90,
        fontsize=7.8,
        color=theme.muted,
        fontproperties=helvetica("bold"),
        zorder=6,
    )
    ax.text(
        x1 - 14,
        chart_y(0.0) - 10,
        "NBA-AVERAGE TS%",
        ha="right",
        va="top",
        fontsize=7.8,
        color=theme.muted,
        fontproperties=helvetica("bold"),
        zorder=6,
    )

    ax.plot([x0, x1], [y0, y0], color=theme.ink, lw=2.1, zorder=5)
    ax.plot([x0, x0], [y0, y1], color=theme.ink, lw=2.1, zorder=5)

    _quadrant_pill(
        ax,
        x0 + 14,
        y1 - 14,
        "left",
        "top",
        "LOW VOLUME,\nHIGH EFFICIENCY",
    )
    _quadrant_pill(
        ax,
        x1 - 14,
        y1 - 14,
        "right",
        "top",
        "HIGH VOLUME, HIGH EFFICIENCY",
    )
    _quadrant_pill(
        ax,
        x0 + 14,
        y0 + 14,
        "left",
        "bottom",
        "LOW VOLUME,\nLOW EFFICIENCY",
    )
    _quadrant_pill(
        ax,
        x1 - 14,
        y0 + 14,
        "right",
        "bottom",
        "HIGH VOLUME, LOW EFFICIENCY",
    )

    half_size = 36
    for layer_index, row in enumerate(qualifiers.itertuples(index=False)):
        point_x = chart_x(float(row.shots_per_100))
        point_y = chart_y(float(row.relative_ts_pp))
        image_zorder = 6.0 + layer_index * 0.2
        label_zorder = image_zorder + 0.1

        image = square_headshot_label(
            ax,
            HEADSHOTS / f"{int(row.nba_id)}.png",
            point_x,
            point_y,
            half_size=half_size,
        )
        image.set_zorder(image_zorder)

        custom_label = CUSTOM_LABELS.get(row.official_roster_name)
        if custom_label:
            name_x = point_x + custom_label["dx"]
            name_y = point_y + custom_label["dy"]
            name_ha = custom_label["ha"]
            name_va = custom_label["va"]
        else:
            name_x = point_x
            name_y = point_y - half_size - 7
            name_ha = "center"
            name_va = "top"
        ax.text(
            name_x,
            name_y,
            SHORT_NAMES[row.official_roster_name],
            ha=name_ha,
            va=name_va,
            fontsize=8.4,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=label_zorder,
        )

    ax.text(
        (x0 + x1) / 2,
        105,
        "SHOTS",
        ha="center",
        va="center",
        fontsize=17,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    direction_fontsize = 9.7
    x_direction = "MORE TRUE SHOT ATTEMPTS"
    x_probe = ax.text(
        0,
        0,
        x_direction,
        fontsize=direction_fontsize,
        fontproperties=helvetica("bold"),
        alpha=0,
    )
    x_direction_width = rendered_width(ax, x_probe)
    x_probe.remove()
    x_arrow_gap = 9
    x_arrow_width = 36
    x_group_width = x_direction_width + x_arrow_gap + x_arrow_width
    x_direction_x = (x0 + x1) / 2 - x_group_width / 2
    ax.text(
        x_direction_x,
        59,
        x_direction,
        ha="left",
        va="center",
        fontsize=direction_fontsize,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    ax.add_patch(
        FancyArrowPatch(
            (
                x_direction_x + x_direction_width + x_arrow_gap,
                62,
            ),
            (
                x_direction_x
                + x_direction_width
                + x_arrow_gap
                + x_arrow_width,
                62,
            ),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.35,
            color=theme.accent,
            zorder=8,
        )
    )

    ax.text(
        90,
        (y0 + y1) / 2,
        "rTS%",
        ha="center",
        va="center",
        rotation=90,
        fontsize=17,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    y_direction = "BETTER SCORING EFFICIENCY"
    y_probe = ax.text(
        0,
        0,
        y_direction,
        fontsize=direction_fontsize,
        fontproperties=helvetica("bold"),
        alpha=0,
    )
    y_direction_height = rendered_width(ax, y_probe)
    y_probe.remove()
    y_arrow_gap = 9
    y_arrow_height = 36
    y_group_height = y_direction_height + y_arrow_gap + y_arrow_height
    y_direction_bottom = (y0 + y1) / 2 - y_group_height / 2
    y_direction_x = 124
    ax.text(
        y_direction_x,
        y_direction_bottom + y_direction_height / 2,
        y_direction,
        ha="center",
        va="center",
        rotation=90,
        fontsize=direction_fontsize,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    ax.add_patch(
        FancyArrowPatch(
            (
                y_direction_x - 3,
                y_direction_bottom + y_direction_height + y_arrow_gap,
            ),
            (
                y_direction_x - 3,
                y_direction_bottom
                + y_direction_height
                + y_arrow_gap
                + y_arrow_height,
            ),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.35,
            color=theme.accent,
            zorder=8,
        )
    )

    output = OUT / f"{snapshot_date}-current-bulls-scoring-landscape-chart.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return output


def _explainer_card(
    ax,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    kicker: str,
    title_size: float = 18,
) -> None:
    """Draw one warm-neutral explainer card."""
    theme = DEFAULT_THEME
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0,rounding_size=18",
            facecolor="#F5F1EC",
            edgecolor=theme.rule,
            linewidth=1.2,
            zorder=1,
        )
    )
    ax.text(
        x + 26,
        y + height - 28,
        title,
        ha="left",
        va="top",
        fontsize=title_size,
        color=theme.accent,
        fontproperties=body_font("bold"),
        zorder=2,
    )
    ax.text(
        x + 26,
        y + height - 67,
        kicker,
        ha="left",
        va="top",
        fontsize=7.5,
        color=theme.muted,
        fontproperties=body_font("bold"),
        zorder=2,
    )


def render_explainer_page(
    table: pd.DataFrame,
    snapshot_date: str,
    final: bool,
) -> Path:
    """Render the full-page formulas and scope explainer for Canva slide two."""
    theme = DEFAULT_THEME
    matas = table.loc[
        table["official_roster_name"].eq("Matas Buzelis")
        & table["data_available"]
    ].iloc[0]
    league_ts_pct = float(matas["league_ts_pct"])

    fig, ax = new_canvas()
    draw_header(
        ax,
        [("HOW TO READ ", theme.ink), ("THE CHART", theme.accent)],
        ["SHOTS + rTS%", "2025–26 REGULAR SEASON"],
        kicker="Volume on the X-axis. Efficiency on the Y-axis.",
        title_base_size=76,
    )
    ax.text(
        1020,
        1162,
        "2 / 2",
        ha="right",
        va="top",
        fontsize=11,
        color=theme.faint,
        fontproperties=body_font("bold"),
    )

    _explainer_card(
        ax,
        x=60,
        y=690,
        width=460,
        height=400,
        title="SHOTS",
        kicker="SCORING-ATTEMPT VOLUME",
    )
    ax.text(
        86,
        978,
        "True shot attempts per 100 possessions.",
        ha="left",
        va="top",
        fontsize=10.5,
        color=theme.ink,
        fontproperties=body_font("medium"),
    )
    ax.text(
        86,
        913,
        "TSA = FGA + 0.44 × FTA",
        ha="left",
        va="top",
        fontsize=12.5,
        color=theme.ink,
        fontproperties=body_font("bold"),
    )
    ax.text(
        86,
        867,
        "SHOTS = TSA × 100 ÷ POSS",
        ha="left",
        va="top",
        fontsize=12.5,
        color=theme.ink,
        fontproperties=body_font("bold"),
    )
    ax.text(
        86,
        796,
        "MATAS EXAMPLE",
        ha="left",
        va="top",
        fontsize=7.5,
        color=theme.accent,
        fontproperties=body_font("bold"),
    )
    ax.text(
        86,
        765,
        (
            f"{float(matas['true_shooting_attempts']):,.1f} TSA ÷ "
            f"{int(matas['possessions']):,} POSS × 100\n"
            f"= {float(matas['shots_per_100']):.1f} SHOTS"
        ),
        ha="left",
        va="top",
        fontsize=9.5,
        linespacing=1.35,
        color=theme.ink,
        fontproperties=body_font("medium"),
    )
    ax.text(
        86,
        704,
        "POSS = player possessions. Higher = more volume.",
        ha="left",
        va="bottom",
        fontsize=7.5,
        color=theme.muted,
        fontproperties=body_font("medium"),
    )

    _explainer_card(
        ax,
        x=560,
        y=690,
        width=460,
        height=400,
        title="rTS%",
        kicker="EFFICIENCY VS. THE LEAGUE",
    )
    ax.text(
        586,
        978,
        "True shooting relative to the NBA average.",
        ha="left",
        va="top",
        fontsize=10.5,
        color=theme.ink,
        fontproperties=body_font("medium"),
    )
    ax.text(
        586,
        913,
        "TS% = PTS ÷ (2 × TSA)",
        ha="left",
        va="top",
        fontsize=12.5,
        color=theme.ink,
        fontproperties=body_font("bold"),
    )
    ax.text(
        586,
        867,
        "rTS% = PLAYER TS% − NBA TS%",
        ha="left",
        va="top",
        fontsize=11.5,
        color=theme.ink,
        fontproperties=body_font("bold"),
    )
    ax.text(
        586,
        796,
        "MATAS EXAMPLE",
        ha="left",
        va="top",
        fontsize=7.5,
        color=theme.accent,
        fontproperties=body_font("bold"),
    )
    ax.text(
        586,
        765,
        (
            f"{float(matas['ts_pct']) * 100:.2f}% − "
            f"{league_ts_pct * 100:.2f}%\n"
            f"= {float(matas['relative_ts_pp']):+.2f} rTS%"
        ),
        ha="left",
        va="top",
        fontsize=9.5,
        linespacing=1.35,
        color=theme.ink,
        fontproperties=body_font("medium"),
    )
    ax.text(
        586,
        704,
        "0 = average. Positive = more efficient.",
        ha="left",
        va="bottom",
        fontsize=7.5,
        color=theme.muted,
        fontproperties=body_font("medium"),
    )

    _explainer_card(
        ax,
        x=60,
        y=385,
        width=960,
        height=260,
        title="HOW TO READ THE QUADRANTS",
        kicker="THE DASHED LINES CREATE THE FOUR PLAYER TYPES",
        title_size=15,
    )
    quadrant_items = [
        (86, 532, "LOW VOLUME", "HIGH EFFICIENCY"),
        (548, 532, "HIGH VOLUME", "HIGH EFFICIENCY"),
        (86, 463, "LOW VOLUME", "LOW EFFICIENCY"),
        (548, 463, "HIGH VOLUME", "LOW EFFICIENCY"),
    ]
    for x, y, volume, efficiency in quadrant_items:
        ax.text(
            x,
            y,
            volume,
            ha="left",
            va="top",
            fontsize=9.5,
            color=theme.ink,
            fontproperties=body_font("bold"),
        )
        ax.text(
            x,
            y - 28,
            efficiency,
            ha="left",
            va="top",
            fontsize=8,
            color=theme.muted,
            fontproperties=body_font("medium"),
        )
    ax.text(
        86,
        397,
        (
            f"VERTICAL: ROSTER MEDIAN = "
            f"{qualified_players(table)['shots_per_100'].median():.1f} SHOTS"
        ),
        ha="left",
        va="bottom",
        fontsize=6.5,
        color=theme.faint,
        fontproperties=body_font("medium"),
    )
    ax.text(
        548,
        397,
        f"HORIZONTAL: NBA AVG TS% = {league_ts_pct * 100:.2f}%",
        ha="left",
        va="bottom",
        fontsize=6.5,
        color=theme.faint,
        fontproperties=body_font("medium"),
    )

    _explainer_card(
        ax,
        x=60,
        y=105,
        width=960,
        height=235,
        title="WHO IS INCLUDED",
        kicker="CURRENT ROSTER, PRIOR-SEASON SAMPLE",
        title_size=15,
    )
    scope_items = [
        (
            86,
            "CURRENT ROSTER",
            "Official Bulls roster\nsnapshot: Jul 23, 2026",
        ),
        (
            394,
            "FULL 2025–26 SEASON",
            "All teams included, so acquired\nplayers carry prior-team stats",
        ),
        (
            725,
            "MIN. 250 TSA",
            "Rookies, no-data players and\nsmaller samples stay off the chart",
        ),
    ]
    for x, heading, body in scope_items:
        ax.text(
            x,
            245,
            heading,
            ha="left",
            va="top",
            fontsize=9,
            color=theme.ink,
            fontproperties=body_font("bold"),
        )
        ax.text(
            x,
            209,
            body,
            ha="left",
            va="top",
            fontsize=7.5,
            linespacing=1.35,
            color=theme.muted,
            fontproperties=body_font("medium"),
        )

    draw_footer(
        ax,
        source="Data via nba.com",
        note="Min. 250 TSA · Current roster as of Jul 23, 2026",
    )
    output = (
        OUT
        / f"{snapshot_date}-current-bulls-scoring-landscape-explainer.png"
    )
    save_post(fig, output, final=final)
    plt.close(fig)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export at 300 DPI; first-review drafts should omit this.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot_time = datetime.now(SNAPSHOT_TZ)
    roster = parse_nba_roster(_fetch_html(NBA_ROSTER_URL))
    base, advanced, teams = fetch_season_frames()
    table = build_working_table(roster, base, advanced, teams, snapshot_time)
    report = validate_working_table(table)

    snapshot_date = snapshot_time.date().isoformat()
    table_path = write_table(table, snapshot_date)
    ensure_headshots(qualified_players(table))
    chart_path = render_chart_only(table, snapshot_date, args.final)
    explainer_path = render_explainer_page(table, snapshot_date, args.final)

    print(json.dumps(report, indent=2))
    print(f"Wrote {table_path}")
    print(f"Wrote {chart_path}")
    print(f"Wrote {explainer_path}")


if __name__ == "__main__":
    main()
