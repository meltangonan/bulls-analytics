"""Build a current-Bulls assisted vs. unassisted scoring chart for Canva.

NBA.com supplies current roster membership and each player's complete 2025-26
regular-season scoring totals across all teams. The chart shows the share of
made field goals that NBA.com records as assisted or unassisted; the two shares
form one 100% bar for every player with at least 100 made field goals.
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
from matplotlib.patches import Rectangle
from nba_api.stats.endpoints import leaguedashplayerstats

from bulls.data.fetch import _NBA_HEADERS, get_current_roster, team_roster_url
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
)


SEASON = "2025-26"
SEASON_TYPE = "Regular Season"
MIN_FIELD_GOALS_MADE = 100
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
OUT = _REPO / "output"

NBA_PLAYER_SCORING_URL = (
    "https://www.nba.com/stats/players/scoring"
    "?Season=2025-26&SeasonType=Regular%20Season&PerMode=Totals"
)
NBA_GLOSSARY_URL = "https://www.nba.com/stats/help/glossary"

CHART_WIDTH = 1080
CHART_HEIGHT = 1000
HEADSHOT_X = 55
HEADSHOT_HALF_WIDTH = 38
HEADSHOT_HALF_HEIGHT = 44
BAR_X = 125
BAR_WIDTH = 925
BAR_HEIGHT = 64
FIRST_BAR_Y = 865
ROW_STEP = 94


def fetch_scoring_frame() -> pd.DataFrame:
    """Fetch full-season NBA.com player scoring totals and assist shares."""
    return leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star=SEASON_TYPE,
        measure_type_detailed_defense="Scoring",
        per_mode_detailed="Totals",
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]


def build_working_table(
    roster: pd.DataFrame,
    scoring: pd.DataFrame,
    snapshot_time: datetime,
) -> pd.DataFrame:
    """Join the current roster to last season's full-season scoring profile."""
    roster_required = {"nba_id", "official_roster_name"}
    scoring_required = {
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GP",
        "FGM",
        "PCT_AST_FGM",
        "PCT_UAST_FGM",
    }
    missing_roster = roster_required - set(roster.columns)
    missing_scoring = scoring_required - set(scoring.columns)
    if missing_roster or missing_scoring:
        raise ValueError(
            "Required columns changed: "
            f"roster={sorted(missing_roster)}, "
            f"scoring={sorted(missing_scoring)}"
        )
    if roster["nba_id"].duplicated().any():
        raise ValueError("Current roster contains duplicate NBA player IDs.")

    season_rows = scoring[
        [
            "PLAYER_ID",
            "PLAYER_NAME",
            "TEAM_ABBREVIATION",
            "GP",
            "FGM",
            "PCT_AST_FGM",
            "PCT_UAST_FGM",
        ]
    ].rename(
        columns={
            "PLAYER_ID": "nba_id",
            "PLAYER_NAME": "season_player_name",
            "TEAM_ABBREVIATION": "season_team_field",
            "GP": "games",
            "FGM": "field_goals_made",
            "PCT_AST_FGM": "assisted_share",
            "PCT_UAST_FGM": "unassisted_share",
        }
    )
    if season_rows["nba_id"].duplicated().any():
        raise ValueError("NBA.com scoring response contains duplicate player IDs.")

    table = roster[["nba_id", "official_roster_name"]].merge(
        season_rows,
        on="nba_id",
        how="left",
        validate="one_to_one",
    )
    numeric_columns = [
        "games",
        "field_goals_made",
        "assisted_share",
        "unassisted_share",
    ]
    for column in numeric_columns:
        table[column] = pd.to_numeric(table[column], errors="coerce")

    table["data_available"] = (
        table["field_goals_made"].notna()
        & table["assisted_share"].notna()
        & table["unassisted_share"].notna()
    )
    table["share_total"] = table["assisted_share"] + table["unassisted_share"]
    table["qualified"] = (
        table["data_available"]
        & table["field_goals_made"].ge(MIN_FIELD_GOALS_MADE)
    )
    table["assisted_pct"] = (table["assisted_share"] * 100).round(1)
    table["unassisted_pct"] = (table["unassisted_share"] * 100).round(1)
    table["assisted_fgm"] = pd.Series(pd.NA, index=table.index, dtype="Int64")
    table["unassisted_fgm"] = pd.Series(pd.NA, index=table.index, dtype="Int64")
    made_a_field_goal = table["data_available"] & table["field_goals_made"].gt(0)
    table.loc[made_a_field_goal, "unassisted_fgm"] = (
        table.loc[made_a_field_goal, "field_goals_made"]
        .mul(table.loc[made_a_field_goal, "unassisted_share"])
        .round()
        .astype("Int64")
    )
    table.loc[made_a_field_goal, "assisted_fgm"] = (
        table.loc[made_a_field_goal, "field_goals_made"].astype("Int64")
        - table.loc[made_a_field_goal, "unassisted_fgm"]
    )
    zero_makes = table["data_available"] & table["field_goals_made"].eq(0)
    table.loc[zero_makes, ["assisted_fgm", "unassisted_fgm"]] = 0
    table["season"] = SEASON
    table["season_type"] = SEASON_TYPE
    table["qualification_fgm"] = MIN_FIELD_GOALS_MADE
    table["roster_source"] = team_roster_url()
    table["scoring_source"] = NBA_PLAYER_SCORING_URL
    table["glossary_source"] = NBA_GLOSSARY_URL
    table["snapshot_date"] = snapshot_time.date().isoformat()
    table["snapshot_timestamp_ct"] = snapshot_time.isoformat(timespec="seconds")

    return table[
        [
            "nba_id",
            "official_roster_name",
            "season_player_name",
            "season_team_field",
            "games",
            "field_goals_made",
            "assisted_share",
            "unassisted_share",
            "share_total",
            "assisted_pct",
            "unassisted_pct",
            "assisted_fgm",
            "unassisted_fgm",
            "data_available",
            "qualified",
            "qualification_fgm",
            "season",
            "season_type",
            "roster_source",
            "scoring_source",
            "glossary_source",
            "snapshot_date",
            "snapshot_timestamp_ct",
        ]
    ]


def qualified_players(table: pd.DataFrame) -> pd.DataFrame:
    """Return qualifying current Bulls from most to least unassisted."""
    return (
        table.loc[table["qualified"]]
        .copy()
        .sort_values(
            ["unassisted_share", "official_roster_name"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )


def validate_working_table(table: pd.DataFrame) -> dict:
    """Validate identities, qualification, and the 100% composition."""
    if table["nba_id"].duplicated().any():
        raise ValueError("Working table contains duplicate NBA player IDs.")
    if table["official_roster_name"].duplicated().any():
        raise ValueError("Working table contains duplicate roster names.")

    available = table.loc[table["data_available"]].copy()
    qualifiers = qualified_players(table)
    if available.empty:
        raise ValueError("No current-roster players had NBA.com scoring data.")
    if qualifiers.empty:
        raise ValueError(
            f"No current-roster players reached {MIN_FIELD_GOALS_MADE} FGM."
        )

    positive_fgm = available.loc[available["field_goals_made"].gt(0)]
    share_gap = (positive_fgm["share_total"] - 1.0).abs()
    if not share_gap.empty and float(share_gap.max()) > 0.0011:
        raise ValueError(
            "NBA.com assisted and unassisted shares do not reconcile to 100%."
        )
    if not qualifiers["field_goals_made"].ge(MIN_FIELD_GOALS_MADE).all():
        raise ValueError("A plotted player fell below the FGM qualification.")
    if not qualifiers["unassisted_share"].is_monotonic_decreasing:
        raise ValueError("Qualifying players are not sorted by unassisted share.")

    inferred_total = qualifiers["assisted_fgm"] + qualifiers["unassisted_fgm"]
    if not inferred_total.eq(qualifiers["field_goals_made"]).all():
        raise ValueError("Inferred assisted and unassisted FGM do not sum to FGM.")
    assisted_inference_gap = (
        qualifiers["assisted_fgm"] / qualifiers["field_goals_made"]
        - qualifiers["assisted_share"]
    ).abs()
    unassisted_inference_gap = (
        qualifiers["unassisted_fgm"] / qualifiers["field_goals_made"]
        - qualifiers["unassisted_share"]
    ).abs()
    max_inference_gap = float(
        pd.concat([assisted_inference_gap, unassisted_inference_gap]).max()
    )
    if max_inference_gap > 0.00051:
        raise ValueError(
            "NBA.com rounded shares do not identify a reliable FGM count."
        )

    below_threshold = table.loc[
        table["data_available"] & ~table["qualified"],
        "official_roster_name",
    ].tolist()
    no_data = table.loc[
        ~table["data_available"],
        "official_roster_name",
    ].tolist()
    return {
        "roster_count": int(len(table)),
        "data_available_count": int(len(available)),
        "qualified_count": int(len(qualifiers)),
        "qualified_names": qualifiers["official_roster_name"].tolist(),
        "below_threshold_names": below_threshold,
        "no_data_names": no_data,
        "max_share_gap": (
            float(share_gap.max()) if not share_gap.empty else None
        ),
        "max_count_inference_gap": max_inference_gap,
    }


def write_working_table(table: pd.DataFrame, date: str) -> Path:
    """Write the complete roster audit table, including excluded players."""
    path = OUT / f"{date}-current-bulls-assisted-buckets-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def segment_label(percentage: float, made: int) -> str:
    """Pair the composition percentage with its inferred made-basket count."""
    return f"{percentage:.0f}%\n({made} FGM)"


def segment_colors(theme=DEFAULT_THEME) -> tuple[str, str]:
    """Return unassisted red first and assisted near-black second."""
    return theme.accent, theme.ink


def portrait_headshot_label(
    ax,
    image_path: str | Path,
    x: float,
    y: float,
    half_width: float,
    half_height: float,
    *,
    zorder: float = 8,
):
    """Place a centered portrait crop without stretching the source image."""
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            Rectangle(
                (x - half_width, y - half_height),
                2 * half_width,
                2 * half_height,
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=zorder,
            )
        )

    height, width = image.shape[:2]
    target_ratio = half_width / half_height
    source_ratio = width / height
    if source_ratio > target_ratio:
        crop_width = max(1, round(height * target_ratio))
        left = max(0, (width - crop_width) // 2)
        portrait = image[:, left:left + crop_width]
    else:
        crop_height = max(1, round(width / target_ratio))
        top = max(0, (height - crop_height) // 2)
        portrait = image[top:top + crop_height, :]

    return ax.imshow(
        portrait,
        extent=[
            x - half_width,
            x + half_width,
            y - half_height,
            y + half_height,
        ],
        interpolation="bilinear",
        zorder=zorder,
    )


def render_chart(
    players: pd.DataFrame,
    date: str,
    final: bool = False,
) -> Path:
    """Render the transparent 100% stacked bars for Canva."""
    theme = DEFAULT_THEME
    unassisted_color, assisted_color = segment_colors(theme)
    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI)
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    legend_y = 970
    legend_items = [
        (BAR_X, unassisted_color, "UNASSISTED"),
        (BAR_X + 230, assisted_color, "ASSISTED"),
    ]
    for x, color, label in legend_items:
        ax.add_patch(
            Rectangle(
                (x, legend_y - 11),
                24,
                24,
                facecolor=color,
                edgecolor="none",
            )
        )
        ax.text(
            x + 36,
            legend_y + 1,
            label,
            ha="left",
            va="center",
            color=theme.ink,
            fontsize=10,
            fontproperties=helvetica("bold"),
        )

    for index, player in players.iterrows():
        y = FIRST_BAR_Y - index * ROW_STEP
        unassisted_pct = float(player["unassisted_pct"])
        assisted_pct = float(player["assisted_pct"])
        unassisted_width = BAR_WIDTH * unassisted_pct / 100
        assisted_width = BAR_WIDTH - unassisted_width

        portrait_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(player['nba_id'])}.png",
            HEADSHOT_X,
            y + BAR_HEIGHT / 2,
            HEADSHOT_HALF_WIDTH,
            HEADSHOT_HALF_HEIGHT,
            zorder=8,
        )
        ax.add_patch(
            Rectangle(
                (BAR_X, y),
                unassisted_width,
                BAR_HEIGHT,
                facecolor=unassisted_color,
                edgecolor="none",
            )
        )
        ax.add_patch(
            Rectangle(
                (BAR_X + unassisted_width, y),
                assisted_width,
                BAR_HEIGHT,
                facecolor=assisted_color,
                edgecolor="none",
            )
        )
        ax.text(
            BAR_X + unassisted_width / 2,
            y + BAR_HEIGHT / 2,
            segment_label(
                unassisted_pct,
                int(player["unassisted_fgm"]),
            ),
            ha="center",
            va="center",
            color="#FFFFFF",
            fontsize=9.5,
            linespacing=1.18,
            fontproperties=helvetica("bold"),
        )
        ax.text(
            BAR_X + unassisted_width + assisted_width / 2,
            y + BAR_HEIGHT / 2,
            segment_label(
                assisted_pct,
                int(player["assisted_fgm"]),
            ),
            ha="center",
            va="center",
            color="#FFFFFF",
            fontsize=9.5,
            linespacing=1.18,
            fontproperties=helvetica("bold"),
        )

    path = OUT / f"{date}-assisted-buckets-current-roster.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        dpi=export_dpi(final),
        transparent=True,
        bbox_inches=None,
        pad_inches=0,
    )
    plt.close(fig)
    return path


def canva_copy_block(report: dict, date: str) -> str:
    """Return exact page copy produced from the same validated run."""
    below = ", ".join(report["below_threshold_names"]) or "None"
    no_data = ", ".join(report["no_data_names"]) or "None"
    return "\n".join(
        [
            "--- CANVA COPY BLOCK ---",
            "",
            "TITLE: HOW THE CURRENT BULLS GET THEIR BUCKETS",
            "",
            (
                "SUBTITLE: Share of each player's 2025-26 made field goals "
                "that were assisted vs. unassisted"
            ),
            "",
            (
                "QUALIFICATION: Current Bulls with 100+ made field goals in "
                "the 2025-26 regular season. Full-season totals across all "
                "teams."
            ),
            "",
            (
                "METHOD NOTE: “Unassisted” is NBA bookkeeping, not necessarily "
                "self-created."
            ),
            "",
            f"BELOW 100 FGM: {below}.",
            f"NO 2025-26 NBA DATA: {no_data}.",
            "",
            f"SOURCE: Data via nba.com · Roster as of {date}",
            "",
            "--- END ---",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export at final DPI; first-review drafts should omit this.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = datetime.now(SNAPSHOT_TZ)
    date = snapshot.date().isoformat()

    roster = get_current_roster()
    scoring = fetch_scoring_frame()
    table = build_working_table(roster, scoring, snapshot)
    report = validate_working_table(table)
    players = qualified_players(table)

    table_path = write_working_table(table, date)
    ensure_headshots(players["nba_id"])
    chart_path = render_chart(players, date, final=args.final)

    print(json.dumps(report, indent=2))
    print(f"\nWrote {table_path}")
    print(f"Wrote {chart_path}\n")
    print(canva_copy_block(report, date))


if __name__ == "__main__":
    main()
