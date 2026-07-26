"""Build the league-wide rim-vs-three points-per-shot chart asset for Canva.

Both axes are points per shot attempt inside a single shot zone, so the two
locations sit on one common currency: a 1.20 three and a 1.20 layup are worth
the same per attempt. NBA.com's league player shot-location endpoint supplies
every zone's FGM/FGA in one call, and the Advanced player frame supplies the
possessions that turn attempts into a per-75 volume used for dot size.

Free throws are absent from shot-location data, so rim points per shot excludes
and-one and shooting-foul value and understates foul-drawing finishers. That
limitation is disclosed on the graphic rather than corrected.
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
from nba_api.stats.endpoints import (
    leaguedashplayershotlocations,
    leaguedashplayerstats,
)

from bulls.data.fetch import _NBA_HEADERS, get_current_roster, team_roster_url
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    rendered_width,
    square_headshot_label,
)


SEASON = "2025-26"
SEASON_TYPE = "Regular Season"
SNAPSHOT_TZ = ZoneInfo("America/Chicago")

# A rotation player's season, plus enough attempts in each zone that a zone
# field-goal percentage is separated from noise. Both bars are disclosed.
#
# The per-zone bar is deliberately NOT a total-attempt bar. Efficiency is
# undefined for a shot a player does not take, and total volume says nothing
# about whether one zone has enough attempts: `possessions >= 1500 and total
# FGA >= 250` would admit 261 players, 51 of them with under 75 attempts in a
# zone and several with zero threes. Nic Claxton is the case that settled it —
# 3-for-19 from three gives a 3PT points-per-shot 95% interval of roughly
# -0.02 to 0.97, wider than the chart's entire drawn Y range. He is reported as
# a non-qualifier instead. A chart that must include him has to plot shot
# *rates*, which are exact for everyone; that is a different post.
MIN_POSSESSIONS = 1500
MIN_ZONE_ATTEMPTS = 75

OUT = _REPO / "output" / "feed"

NBA_ROSTER_URL = team_roster_url()
NBA_SHOT_LOCATIONS_URL = (
    "https://www.nba.com/stats/players/shots-general"
    "?Season=2025-26&SeasonType=Regular%20Season&DistanceRange=By%20Zone"
)
NBA_ADVANCED_URL = (
    "https://www.nba.com/stats/players/advanced"
    "?Season=2025-26&SeasonType=Regular%20Season&PerMode=Totals"
)

CHART_WIDTH = 1080
CHART_HEIGHT = 1080
PANEL = (176, 176, 1016, 1004)  # x0, y0, x1, y1
RIM_LIMITS = (0.82, 1.72)
THREE_LIMITS = (0.50, 1.44)

# Keyed on NBA.com's official roster name. Matches the scoring landscape's
# labels so the two charts name the same player the same way.
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
    "Zach Collins": "COLLINS",
    "Noa Essengue": "ESSENGUE",
    "Caleb Wilson": "WILSON",
    "Dailyn Swain": "SWAIN",
    "Jaylin Sellers": "SELLERS",
    "Tobe Awaka": "AWAKA",
}

# Which side of its headshot each Bulls name sits on. Every player stays on the
# true coordinate; only the text anchor moves. Default is "below".
LABEL_SIDES: dict[str, str] = {
    "Isaac Okoro": "left",
    "Josh Giddey": "left",
    "Jalen Smith": "right",
    "Matas Buzelis": "right",
    "Norman Powell": "above",
}


def fetch_season_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch league zone shooting, league Advanced totals, and the roster.

    Roster membership comes from NBA.com's team page rather than the season's
    team field, so the chart shows the players on the roster today with their
    complete 2025-26 numbers, including games played for a previous team.
    """
    common = {
        "season": SEASON,
        "season_type_all_star": SEASON_TYPE,
        "per_mode_detailed": "Totals",
        "timeout": 90,
        "headers": _NBA_HEADERS,
    }
    locations = leaguedashplayershotlocations.LeagueDashPlayerShotLocations(
        distance_range="By Zone",
        **common,
    ).get_data_frames()[0]
    advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Advanced",
        **common,
    ).get_data_frames()[0]
    return flatten_locations(locations), advanced, get_current_roster()


def flatten_locations(locations: pd.DataFrame) -> pd.DataFrame:
    """Collapse the endpoint's two-level shot-category header to flat names."""
    if isinstance(locations.columns, pd.MultiIndex):
        locations = locations.copy()
        locations.columns = [
            f"{zone}|{field}" if zone else str(field)
            for zone, field in locations.columns
        ]
    return locations


def build_working_table(
    locations: pd.DataFrame,
    advanced: pd.DataFrame,
    roster: pd.DataFrame,
    snapshot_time: datetime,
) -> pd.DataFrame:
    """Join zone shooting to possessions and calculate both axes plus volume."""
    location_columns = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "Restricted Area|FGM",
        "Restricted Area|FGA",
        "Corner 3|FGM",
        "Corner 3|FGA",
        "Above the Break 3|FGM",
        "Above the Break 3|FGA",
    ]
    advanced_columns = ["PLAYER_ID", "POSS", "GP"]

    missing_location_columns = set(location_columns) - set(locations.columns)
    missing_advanced_columns = set(advanced_columns) - set(advanced.columns)
    if missing_location_columns or missing_advanced_columns:
        raise ValueError(
            "NBA.com response columns changed: "
            f"locations={sorted(missing_location_columns)}, "
            f"advanced={sorted(missing_advanced_columns)}"
        )
    if locations["PLAYER_ID"].duplicated().any():
        raise ValueError("NBA.com returned duplicate players in shot locations.")
    if advanced["PLAYER_ID"].duplicated().any():
        raise ValueError("NBA.com returned duplicate players in Advanced totals.")

    table = locations[location_columns].merge(
        advanced[advanced_columns],
        on="PLAYER_ID",
        how="inner",
        validate="one_to_one",
    )
    table = table.rename(
        columns={
            "PLAYER_ID": "nba_id",
            "PLAYER_NAME": "player_name",
            "TEAM_ABBREVIATION": "team",
            "Restricted Area|FGM": "rim_fgm",
            "Restricted Area|FGA": "rim_fga",
            "POSS": "possessions",
            "GP": "games",
        }
    )

    numeric_columns = [
        "rim_fgm",
        "rim_fga",
        "Corner 3|FGM",
        "Corner 3|FGA",
        "Above the Break 3|FGM",
        "Above the Break 3|FGA",
        "possessions",
        "games",
    ]
    for column in numeric_columns:
        table[column] = pd.to_numeric(table[column], errors="coerce")

    table["three_fgm"] = table["Corner 3|FGM"] + table["Above the Break 3|FGM"]
    table["three_fga"] = table["Corner 3|FGA"] + table["Above the Break 3|FGA"]

    # Points per attempt inside one zone. The zone's own point value is the
    # multiplier, which is what puts rim and three on a comparable scale.
    table["rim_pps"] = 2 * table["rim_fgm"] / table["rim_fga"]
    table["three_pps"] = 3 * table["three_fgm"] / table["three_fga"]
    table["zone_fga_per_75"] = (
        (table["rim_fga"] + table["three_fga"]) * 75 / table["possessions"]
    )

    table["qualified"] = (
        table["possessions"].ge(MIN_POSSESSIONS)
        & table["rim_fga"].ge(MIN_ZONE_ATTEMPTS)
        & table["three_fga"].ge(MIN_ZONE_ATTEMPTS)
        & table["rim_pps"].notna()
        & table["three_pps"].notna()
    )

    if roster["nba_id"].duplicated().any():
        raise ValueError("NBA.com returned duplicate players on the roster.")
    roster_names = dict(
        zip(roster["nba_id"].astype(int), roster["official_roster_name"])
    )
    table["is_bulls"] = table["nba_id"].isin(roster_names)
    # Label off NBA.com's roster spelling, falling back to the stats spelling.
    table["official_roster_name"] = (
        table["nba_id"].map(roster_names).fillna(table["player_name"])
    )

    qualifiers = table.loc[table["qualified"]]
    table["league_median_rim_pps"] = float(qualifiers["rim_pps"].median())
    table["league_median_three_pps"] = float(qualifiers["three_pps"].median())
    table["min_possessions"] = MIN_POSSESSIONS
    table["min_zone_attempts"] = MIN_ZONE_ATTEMPTS
    table["season"] = SEASON
    table["season_type"] = SEASON_TYPE
    table["roster_size"] = int(len(roster))
    table["roster_source"] = NBA_ROSTER_URL
    table["shot_locations_source"] = NBA_SHOT_LOCATIONS_URL
    table["advanced_source"] = NBA_ADVANCED_URL
    table["snapshot_date"] = snapshot_time.date().isoformat()
    table["snapshot_timestamp_ct"] = snapshot_time.isoformat(timespec="seconds")

    return table[
        [
            "nba_id",
            "player_name",
            "official_roster_name",
            "team",
            "games",
            "possessions",
            "rim_fgm",
            "rim_fga",
            "three_fgm",
            "three_fga",
            "rim_pps",
            "three_pps",
            "zone_fga_per_75",
            "qualified",
            "is_bulls",
            "league_median_rim_pps",
            "league_median_three_pps",
            "min_possessions",
            "min_zone_attempts",
            "roster_size",
            "season",
            "season_type",
            "roster_source",
            "shot_locations_source",
            "advanced_source",
            "snapshot_date",
            "snapshot_timestamp_ct",
        ]
    ]


def qualified_players(table: pd.DataFrame) -> pd.DataFrame:
    """Return qualifiers with Bulls last so their markers draw on top."""
    return (
        table.loc[table["qualified"]]
        .copy()
        .sort_values(["is_bulls", "official_roster_name"], ascending=[True, True])
    )


def bulls_players(table: pd.DataFrame) -> pd.DataFrame:
    """Return qualified Bulls in descending zone volume."""
    qualifiers = qualified_players(table)
    return qualifiers.loc[qualifiers["is_bulls"]].sort_values(
        "zone_fga_per_75", ascending=False
    )


def validate_working_table(table: pd.DataFrame) -> dict:
    """Validate identities, formulas, thresholds, and chart coverage."""
    if table["nba_id"].duplicated().any():
        raise ValueError("Working table contains duplicate NBA player IDs.")

    qualifiers = qualified_players(table)
    bulls = bulls_players(table)
    if qualifiers.empty:
        raise ValueError("No players met the possession and zone-volume bars.")
    if bulls.empty:
        raise ValueError("No Bulls met the possession and zone-volume bars.")

    missing_labels = sorted(
        set(bulls["official_roster_name"]) - set(SHORT_NAMES)
    )
    if missing_labels:
        raise ValueError(f"Missing chart labels for Bulls qualifiers: {missing_labels}")

    required_numbers = ["rim_pps", "three_pps", "zone_fga_per_75"]
    if qualifiers[required_numbers].isna().any().any():
        raise ValueError("Qualified rows contain missing calculated values.")
    if not qualifiers["possessions"].ge(MIN_POSSESSIONS).all():
        raise ValueError("A plotted player fell below the possession bar.")
    if not qualifiers["rim_fga"].ge(MIN_ZONE_ATTEMPTS).all():
        raise ValueError("A plotted player fell below the rim-attempt bar.")
    if not qualifiers["three_fga"].ge(MIN_ZONE_ATTEMPTS).all():
        raise ValueError("A plotted player fell below the three-attempt bar.")

    # Points per shot must reconstruct the zone's points from its attempts.
    rim_points_residual = float(
        (qualifiers["rim_pps"] * qualifiers["rim_fga"] - 2 * qualifiers["rim_fgm"])
        .abs()
        .max()
    )
    three_points_residual = float(
        (
            qualifiers["three_pps"] * qualifiers["three_fga"]
            - 3 * qualifiers["three_fgm"]
        )
        .abs()
        .max()
    )
    if max(rim_points_residual, three_points_residual) > 0.000001:
        raise ValueError(
            "Points per shot does not reconstruct zone points: "
            f"rim={rim_points_residual:.8f}, three={three_points_residual:.8f}"
        )

    off_panel = qualifiers.loc[
        ~qualifiers["rim_pps"].between(*RIM_LIMITS)
        | ~qualifiers["three_pps"].between(*THREE_LIMITS)
    ]
    if not off_panel.empty:
        raise ValueError(
            "Qualified players fall outside the drawn panel: "
            f"{off_panel['official_roster_name'].tolist()}"
        )

    bulls_all = table.loc[table["is_bulls"]]
    roster_size = int(table["roster_size"].iloc[0])
    return {
        "league_pool": int(len(table)),
        "roster_size": roster_size,
        # Roster players with no 2025-26 NBA minutes never reach the stats
        # frames at all, so they are counted here rather than listed.
        "roster_without_2025_26_data": roster_size - int(len(bulls_all)),
        "qualified_count": int(len(qualifiers)),
        "bulls_qualified_count": int(len(bulls)),
        "bulls_qualified_names": bulls["official_roster_name"].tolist(),
        "bulls_excluded_names": sorted(
            bulls_all.loc[~bulls_all["qualified"], "official_roster_name"].tolist()
        ),
        "league_median_rim_pps": float(qualifiers["rim_pps"].median()),
        "league_median_three_pps": float(qualifiers["three_pps"].median()),
        "rim_pps_range": [
            float(qualifiers["rim_pps"].min()),
            float(qualifiers["rim_pps"].max()),
        ],
        "three_pps_range": [
            float(qualifiers["three_pps"].min()),
            float(qualifiers["three_pps"].max()),
        ],
        "max_rim_points_residual": rim_points_residual,
        "max_three_points_residual": three_points_residual,
    }


def write_table(table: pd.DataFrame, snapshot_date: str) -> Path:
    """Write the complete league table, including non-qualifiers."""
    path = OUT / f"{snapshot_date}-rim-vs-three-pps-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def chart_x(rim_pps: float) -> float:
    """Map rim points per shot into chart pixels."""
    x0, _, x1, _ = PANEL
    return x0 + (rim_pps - RIM_LIMITS[0]) / (RIM_LIMITS[1] - RIM_LIMITS[0]) * (x1 - x0)


def chart_y(three_pps: float) -> float:
    """Map three-point points per shot into chart pixels."""
    _, y0, _, y1 = PANEL
    return y0 + (three_pps - THREE_LIMITS[0]) / (
        THREE_LIMITS[1] - THREE_LIMITS[0]
    ) * (y1 - y0)


# The league layer is context, not a second encoded variable: one uniform dot
# size keeps position the only thing a reader has to decode, matching the
# roster landscapes where every face is the same size. Per-player attempt
# volume stays in the printed Canva copy block.
LEAGUE_MARKER_AREA = 116.0
HEADSHOT_HALF_SIZE = 36.0


def _quadrant_pill(
    ax,
    anchor_x: float,
    anchor_y: float,
    horizontal: str,
    vertical: str,
    title: str,
) -> None:
    """Draw one descriptive quadrant key."""
    theme = DEFAULT_THEME
    line_count = title.count("\n") + 1
    probe = ax.text(
        0,
        0,
        title,
        fontsize=8.7,
        fontproperties=helvetica("bold"),
        linespacing=0.95,
        alpha=0,
    )
    title_width = rendered_width(ax, probe)
    probe.remove()

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


def _axis_label(
    ax,
    *,
    name: str,
    direction: str,
    vertical: bool,
    center: float,
    name_offset: float,
    direction_offset: float,
) -> None:
    """Draw one axis name plus its direction-of-good arrow."""
    theme = DEFAULT_THEME
    rotation = 90 if vertical else 0
    if vertical:
        ax.text(
            name_offset,
            center,
            name,
            ha="center",
            va="center",
            rotation=rotation,
            fontsize=17,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
    else:
        ax.text(
            center,
            name_offset,
            name,
            ha="center",
            va="center",
            fontsize=17,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )

    direction_fontsize = 9.7
    probe = ax.text(
        0,
        0,
        direction,
        fontsize=direction_fontsize,
        fontproperties=helvetica("bold"),
        alpha=0,
    )
    extent = rendered_width(ax, probe)
    probe.remove()

    gap = 9
    arrow = 36
    start = center - (extent + gap + arrow) / 2
    if vertical:
        ax.text(
            direction_offset,
            start + extent / 2,
            direction,
            ha="center",
            va="center",
            rotation=90,
            fontsize=direction_fontsize,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
        ax.add_patch(
            FancyArrowPatch(
                (direction_offset - 3, start + extent + gap),
                (direction_offset - 3, start + extent + gap + arrow),
                arrowstyle="-|>",
                mutation_scale=11,
                linewidth=1.35,
                color=theme.accent,
                zorder=8,
            )
        )
    else:
        ax.text(
            start,
            direction_offset,
            direction,
            ha="left",
            va="center",
            fontsize=direction_fontsize,
            color=theme.ink,
            fontproperties=helvetica("bold"),
        )
        ax.add_patch(
            FancyArrowPatch(
                (start + extent + gap, direction_offset + 3),
                (start + extent + gap + arrow, direction_offset + 3),
                arrowstyle="-|>",
                mutation_scale=11,
                linewidth=1.35,
                color=theme.accent,
                zorder=8,
            )
        )


def render_chart_only(
    table: pd.DataFrame,
    snapshot_date: str,
    final: bool,
) -> Path:
    """Render the transparent scatter asset for Canva framing."""
    theme = DEFAULT_THEME
    panel_fill = "#F5F1EC"
    qualifiers = qualified_players(table)
    bulls = bulls_players(table)
    median_rim = float(qualifiers["rim_pps"].median())
    median_three = float(qualifiers["three_pps"].median())

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

    for value in [0.9, 1.1, 1.3, 1.5, 1.7]:
        x = chart_x(value)
        ax.plot([x, x], [y0, y1], color=theme.grid, lw=1.0, zorder=2)
        ax.plot([x, x], [y0, y0 - 9], color=theme.ink, lw=1.5, zorder=5)
        ax.text(
            x,
            y0 - 20,
            f"{value:.1f}",
            ha="center",
            va="top",
            fontsize=12.5,
            color=theme.ink,
            fontproperties=helvetica(),
        )

    for value in [0.6, 0.8, 1.0, 1.2, 1.4]:
        y = chart_y(value)
        ax.plot([x0, x1], [y, y], color=theme.grid, lw=1.0, zorder=2)
        ax.plot([x0, x0 - 9], [y, y], color=theme.ink, lw=1.5, zorder=5)
        ax.text(
            x0 - 18,
            y,
            f"{value:.1f}",
            ha="right",
            va="center",
            fontsize=12.5,
            color=theme.ink,
            fontproperties=helvetica(),
        )

    median_x = chart_x(median_rim)
    median_y = chart_y(median_three)
    ax.plot(
        [median_x, median_x],
        [y0, y1],
        color=theme.muted,
        lw=1.25,
        linestyle=(0, (4, 4)),
        alpha=0.72,
        zorder=3,
    )
    ax.plot(
        [x0, x1],
        [median_y, median_y],
        color=theme.muted,
        lw=1.25,
        linestyle=(0, (4, 4)),
        alpha=0.72,
        zorder=3,
    )
    ax.text(
        median_x - 10,
        y0 + 96,
        f"LEAGUE MEDIAN  {median_rim:.2f}",
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
        median_y - 10,
        f"LEAGUE MEDIAN  {median_three:.2f}",
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
        ax, x0 + 14, y1 - 14, "left", "top", "SHOOTS IT IN,\nDOESN'T FINISH"
    )
    _quadrant_pill(ax, x1 - 14, y1 - 14, "right", "top", "SCORES FROM EVERYWHERE")
    _quadrant_pill(ax, x0 + 14, y0 + 14, "left", "bottom", "STRUGGLES\nAT BOTH")
    _quadrant_pill(
        ax, x1 - 14, y0 + 14, "right", "bottom", "FINISHES, DOESN'T SHOOT IT IN"
    )

    league = qualifiers.loc[~qualifiers["is_bulls"]]
    ax.scatter(
        [chart_x(v) for v in league["rim_pps"]],
        [chart_y(v) for v in league["three_pps"]],
        s=LEAGUE_MARKER_AREA,
        facecolor=theme.muted,
        edgecolor="none",
        alpha=0.26,
        zorder=6,
    )
    # Bulls draw as headshots in descending volume, so the largest portraits
    # land underneath and a smaller neighbour is never hidden behind them.
    for layer_index, row in enumerate(bulls.itertuples(index=False)):
        point_x = chart_x(float(row.rim_pps))
        point_y = chart_y(float(row.three_pps))
        half_size = HEADSHOT_HALF_SIZE
        image_zorder = 7.0 + layer_index * 0.2

        image = square_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(row.nba_id)}.png",
            point_x,
            point_y,
            half_size=half_size,
            zorder=image_zorder,
        )

        side = LABEL_SIDES.get(row.official_roster_name, "below")
        if side == "left":
            name_x, name_y = point_x - half_size - 8, point_y
            name_ha, name_va = "right", "center"
        elif side == "right":
            name_x, name_y = point_x + half_size + 8, point_y
            name_ha, name_va = "left", "center"
        elif side == "above":
            name_x, name_y = point_x, point_y + half_size + 8
            name_ha, name_va = "center", "bottom"
        else:
            name_x, name_y = point_x, point_y - half_size - 8
            name_ha, name_va = "center", "top"
        ax.text(
            name_x,
            name_y,
            SHORT_NAMES[row.official_roster_name],
            ha=name_ha,
            va=name_va,
            fontsize=8.6,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=image_zorder + 0.1,
        )

    _axis_label(
        ax,
        name="RIM PPS",
        direction="BETTER FINISHING AT THE RIM",
        vertical=False,
        center=(x0 + x1) / 2,
        name_offset=103,
        direction_offset=57,
    )
    _axis_label(
        ax,
        name="3PT PPS",
        direction="BETTER THREE-POINT SHOOTING",
        vertical=True,
        center=(y0 + y1) / 2,
        name_offset=72,
        direction_offset=118,
    )

    output = OUT / f"{snapshot_date}-rim-vs-three-pps-chart.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return output


def canva_copy_block(table: pd.DataFrame, summary: dict) -> str:
    """Print the exact strings for the Canva page so numbers come from one run."""
    bulls = bulls_players(table)
    lines = [
        "TITLE:  WHERE THE POINTS COME FROM",
        "SUBTITLE:  RIM VS THREE, POINTS PER SHOT  |  2025-26 REGULAR SEASON",
        "",
        f"QUALIFIED:  {summary['qualified_count']} NBA players with "
        f"{MIN_POSSESSIONS}+ possessions and {MIN_ZONE_ATTEMPTS}+ attempts in each zone",
        f"LEAGUE MEDIAN:  {summary['league_median_rim_pps']:.2f} rim PPS  |  "
        f"{summary['league_median_three_pps']:.2f} 3PT PPS",
        "",
        "MARKERS:  every marker is the same size — position is the only encoding. "
        "Grey = the rest of the qualified league.",
        "NOTE:  Free throws are not in shot-location data, so rim PPS excludes "
        "and-one and shooting-foul value.",
        f"ROSTER:  current {summary['roster_size']}-player Bulls roster, shown with "
        "complete 2025-26 totals including games played for a previous team",
        "SOURCE:  NBA.com/stats — player shot locations by zone; Advanced totals; "
        "NBA.com team roster page",
        "",
        "BULLS:",
    ]
    for row in bulls.itertuples(index=False):
        lines.append(
            f"  {SHORT_NAMES[row.official_roster_name]:<12} "
            f"rim {row.rim_pps:.2f} ({int(row.rim_fga)} FGA)   "
            f"3PT {row.three_pps:.2f} ({int(row.three_fga)} FGA)   "
            f"{row.zone_fga_per_75:.1f}/75"
        )
    if summary["bulls_excluded_names"]:
        lines.append("")
        lines.append(
            "BELOW THE BAR:  " + ", ".join(summary["bulls_excluded_names"])
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export at final DPI instead of draft DPI.",
    )
    args = parser.parse_args()

    snapshot_time = datetime.now(SNAPSHOT_TZ)
    locations, advanced, roster = fetch_season_frames()
    table = build_working_table(locations, advanced, roster, snapshot_time)
    summary = validate_working_table(table)

    snapshot_date = table["snapshot_date"].iloc[0]
    ensure_headshots(bulls_players(table)["nba_id"])
    table_path = write_table(table, snapshot_date)
    chart_path = render_chart_only(table, snapshot_date, args.final)

    print(json.dumps(summary, indent=2, default=float))
    print()
    print(canva_copy_block(table, summary))
    print()
    print(f"table: {table_path}")
    print(f"chart: {chart_path}")


if __name__ == "__main__":
    main()
