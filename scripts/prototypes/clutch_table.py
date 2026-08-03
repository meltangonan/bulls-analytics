"""Build a current-Bulls clutch production table for Canva.

NBA.com supplies current roster membership and complete 2025-26 regular-season
clutch totals across all teams. The chart ranks current Bulls with at least ten
clutch appearances by total clutch points and adds relative true shooting,
clutch minutes, and team win percentage for context.
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
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch, Rectangle
from nba_api.stats.endpoints import leaguedashplayerclutch

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
MIN_CLUTCH_GAMES = 10
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
OUT = _REPO / "output" / "feed"

NBA_CLUTCH_URL = (
    "https://www.nba.com/stats/players/clutch-traditional"
    "?PerMode=Totals&Season=2025-26&SeasonType=Regular%20Season"
    "&ClutchTime=Last%205%20Minutes&PointDiff=5&dir=A&sort=PTS"
)

CHART_WIDTH = 1080
CHART_HEIGHT = 1110
ROW_HEIGHT = 120
HEADER_Y = 1060
HEADER_RULE_Y = 1016
FIRST_ROW_Y = 956

HEADSHOT_X = 68
HEADSHOT_HALF_SIZE = 58
NAME_X = 136

COLUMNS = {
    "PTS": (418, 570),
    "MIN": (570, 734),
    "FG": (734, 898),
    "WIN%": (898, 1062),
}

HEAT_GREEN = "#3FAE63"
HEAT_RED = "#D64545"
POINTS_CARD_OUTSET_X = 8
POINTS_CARD_OUTSET_Y = 9


def fetch_clutch_frame() -> pd.DataFrame:
    """Fetch league-wide player clutch totals from NBA.com."""
    return leaguedashplayerclutch.LeagueDashPlayerClutch(
        season=SEASON,
        season_type_all_star=SEASON_TYPE,
        per_mode_detailed="Totals",
        clutch_time="Last 5 Minutes",
        point_diff="5",
        ahead_behind="Ahead or Behind",
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]


def build_working_table(
    roster: pd.DataFrame,
    clutch: pd.DataFrame,
    snapshot_time: datetime,
) -> pd.DataFrame:
    """Join the current roster to full-season clutch totals and metrics."""
    roster_required = {"nba_id", "official_roster_name"}
    clutch_required = {
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GP",
        "W",
        "L",
        "MIN",
        "PTS",
        "FGM",
        "FGA",
        "FTA",
    }
    missing_roster = roster_required - set(roster.columns)
    missing_clutch = clutch_required - set(clutch.columns)
    if missing_roster or missing_clutch:
        raise ValueError(
            "Required columns changed: "
            f"roster={sorted(missing_roster)}, "
            f"clutch={sorted(missing_clutch)}"
        )
    if roster["nba_id"].duplicated().any():
        raise ValueError("Current roster contains duplicate NBA player IDs.")
    if clutch["PLAYER_ID"].duplicated().any():
        raise ValueError("NBA.com clutch response contains duplicate player IDs.")

    league_fga = float(clutch["FGA"].sum())
    if league_fga <= 0:
        raise ValueError("NBA.com clutch totals produced zero field-goal attempts.")
    league_fg_pct = float(clutch["FGM"].sum() / league_fga)
    league_tsa = float(clutch["FGA"].sum() + 0.44 * clutch["FTA"].sum())
    if league_tsa <= 0:
        raise ValueError("NBA.com clutch totals produced zero shooting attempts.")
    league_ts_pct = float(clutch["PTS"].sum() / (2 * league_tsa))

    season_rows = clutch[
        [
            "PLAYER_ID",
            "PLAYER_NAME",
            "TEAM_ABBREVIATION",
            "GP",
            "W",
            "L",
            "MIN",
            "PTS",
            "FGM",
            "FGA",
            "FTA",
        ]
    ].rename(
        columns={
            "PLAYER_ID": "nba_id",
            "PLAYER_NAME": "season_player_name",
            "TEAM_ABBREVIATION": "season_team_field",
            "GP": "clutch_games",
            "W": "clutch_wins",
            "L": "clutch_losses",
            "MIN": "clutch_minutes",
            "PTS": "clutch_points",
            "FGM": "clutch_fgm",
            "FGA": "clutch_fga",
            "FTA": "clutch_fta",
        }
    )
    table = roster[["nba_id", "official_roster_name"]].merge(
        season_rows,
        on="nba_id",
        how="left",
        validate="one_to_one",
    )
    numeric_columns = [
        "clutch_games",
        "clutch_wins",
        "clutch_losses",
        "clutch_minutes",
        "clutch_points",
        "clutch_fgm",
        "clutch_fga",
        "clutch_fta",
    ]
    for column in numeric_columns:
        table[column] = pd.to_numeric(table[column], errors="coerce")

    table["data_available"] = (
        table["clutch_games"].gt(0)
        & table["clutch_minutes"].notna()
        & table["clutch_points"].notna()
        & table["clutch_fgm"].notna()
        & table["clutch_fga"].notna()
        & table["clutch_fta"].notna()
    )
    table["true_shooting_attempts"] = (
        table["clutch_fga"] + 0.44 * table["clutch_fta"]
    )
    table["ts_pct"] = table["clutch_points"] / (
        2 * table["true_shooting_attempts"]
    )
    table["relative_ts_pp"] = (table["ts_pct"] - league_ts_pct) * 100
    table["fg_pct"] = table["clutch_fgm"] / table["clutch_fga"]
    table["win_pct"] = table["clutch_wins"] / table["clutch_games"]
    table["qualified"] = (
        table["data_available"]
        & table["clutch_games"].ge(MIN_CLUTCH_GAMES)
        & table["true_shooting_attempts"].gt(0)
    )
    table["league_clutch_ts_pct"] = league_ts_pct
    table["league_clutch_fg_pct"] = league_fg_pct
    table["qualification_games"] = MIN_CLUTCH_GAMES
    table["season"] = SEASON
    table["season_type"] = SEASON_TYPE
    table["clutch_definition"] = "Last 5 minutes, score within 5 points"
    table["roster_source"] = team_roster_url()
    table["clutch_source"] = NBA_CLUTCH_URL
    table["snapshot_date"] = snapshot_time.date().isoformat()
    table["snapshot_timestamp_ct"] = snapshot_time.isoformat(timespec="seconds")

    return table[
        [
            "nba_id",
            "official_roster_name",
            "season_player_name",
            "season_team_field",
            "clutch_games",
            "clutch_wins",
            "clutch_losses",
            "clutch_minutes",
            "clutch_points",
            "clutch_fgm",
            "clutch_fga",
            "clutch_fta",
            "true_shooting_attempts",
            "ts_pct",
            "league_clutch_ts_pct",
            "relative_ts_pp",
            "fg_pct",
            "league_clutch_fg_pct",
            "win_pct",
            "data_available",
            "qualified",
            "qualification_games",
            "season",
            "season_type",
            "clutch_definition",
            "roster_source",
            "clutch_source",
            "snapshot_date",
            "snapshot_timestamp_ct",
        ]
    ]


def qualified_players(table: pd.DataFrame) -> pd.DataFrame:
    """Return qualifying current Bulls ordered by clutch points."""
    return (
        table.loc[table["qualified"]]
        .copy()
        .sort_values(
            ["clutch_points", "clutch_minutes", "official_roster_name"],
            ascending=[False, False, True],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def validate_working_table(table: pd.DataFrame) -> dict:
    """Validate identities, formulas, qualifier scope, and ranking."""
    if table["nba_id"].duplicated().any():
        raise ValueError("Working table contains duplicate NBA player IDs.")
    if table["official_roster_name"].duplicated().any():
        raise ValueError("Working table contains duplicate roster names.")

    available = table.loc[table["data_available"]].copy()
    qualifiers = qualified_players(table)
    if available.empty:
        raise ValueError("No current-roster players had NBA.com clutch data.")
    if qualifiers.empty:
        raise ValueError(
            f"No current-roster players reached {MIN_CLUTCH_GAMES} clutch games."
        )

    record_gap = (
        available["clutch_wins"]
        + available["clutch_losses"]
        - available["clutch_games"]
    ).abs()
    if not record_gap.empty and float(record_gap.max()) > 0:
        raise ValueError("Clutch wins and losses do not reconcile to games played.")
    expected_win_pct = available["clutch_wins"] / available["clutch_games"]
    if not np.allclose(available["win_pct"], expected_win_pct, atol=1e-12):
        raise ValueError("Clutch win percentage does not reconcile to W / GP.")
    if not qualifiers["clutch_games"].ge(MIN_CLUTCH_GAMES).all():
        raise ValueError("A displayed player fell below the clutch-game cutoff.")
    if qualifiers[
        [
            "clutch_points",
            "clutch_minutes",
            "clutch_fgm",
            "clutch_fga",
            "fg_pct",
            "win_pct",
        ]
    ].isna().any().any():
        raise ValueError("A displayed player has a missing table value.")
    if not qualifiers["clutch_points"].is_monotonic_decreasing:
        raise ValueError("Displayed players are not ordered by clutch points.")

    reconstructed_ts = available["clutch_points"] / (
        2 * available["true_shooting_attempts"]
    )
    if not np.allclose(available["ts_pct"], reconstructed_ts, atol=1e-12):
        raise ValueError("Player clutch TS% does not reconcile to NBA.com totals.")
    shooting = available.loc[available["clutch_fga"].gt(0)]
    reconstructed_fg = shooting["clutch_fgm"] / shooting["clutch_fga"]
    if not np.allclose(shooting["fg_pct"], reconstructed_fg, atol=1e-12):
        raise ValueError("Player clutch FG% does not reconcile to FGM / FGA.")
    league_values = available["league_clutch_ts_pct"].dropna().unique()
    if len(league_values) != 1 or not 0 < float(league_values[0]) < 1:
        raise ValueError("League clutch TS% is missing or inconsistent.")
    league_fg_values = available["league_clutch_fg_pct"].dropna().unique()
    if len(league_fg_values) != 1 or not 0 < float(league_fg_values[0]) < 1:
        raise ValueError("League clutch FG% is missing or inconsistent.")

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
        "no_2025_26_clutch_data_names": sorted(
            table.loc[
                ~table["data_available"], "official_roster_name"
            ].tolist()
        ),
        "league_clutch_ts_pct": float(league_values[0]),
        "league_clutch_fg_pct": float(league_fg_values[0]),
        "min_clutch_games": MIN_CLUTCH_GAMES,
        "min_qualifier_tsa": float(qualifiers["true_shooting_attempts"].min()),
        "min_qualifier_fga": float(qualifiers["clutch_fga"].min()),
    }


def write_working_table(table: pd.DataFrame, date: str) -> Path:
    """Write the complete roster audit table, including excluded players."""
    path = OUT / f"{date}-current-bulls-clutch-table-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def _mix(base: str, target: str, strength: float) -> tuple[float, float, float]:
    """Blend two colors for restrained table-cell fills."""
    amount = min(max(float(strength), 0.0), 1.0)
    base_rgb = np.array(to_rgb(base))
    target_rgb = np.array(to_rgb(target))
    return tuple(base_rgb * (1 - amount) + target_rgb * amount)


def fg_fill(
    value: float,
    baseline: float,
    limit: float = 0.25,
) -> tuple[float, float, float]:
    """Map FG% around the weighted NBA clutch average."""
    delta = float(value) - float(baseline)
    fraction = min(abs(delta) / limit, 1.0)
    if delta >= 0:
        return _mix("#EAF5EC", HEAT_GREEN, 0.18 + fraction * 0.72)
    return _mix("#FAEAEA", HEAT_RED, 0.18 + fraction * 0.72)


def win_fill(value: float) -> tuple[float, float, float]:
    """Map team clutch-game win rate around .500 with red/green context."""
    delta = float(value) - 0.5
    fraction = min(abs(delta) / 0.25, 1.0)
    if delta >= 0:
        return _mix("#EAF5EC", HEAT_GREEN, 0.14 + fraction * 0.62)
    return _mix("#FAEAEA", HEAT_RED, 0.14 + fraction * 0.62)


def minutes_fill(value: float, maximum: float) -> tuple[float, float, float]:
    """Keep opportunity context on one uniform warm off-white fill."""
    del value, maximum
    return to_rgb(DEFAULT_THEME.canvas)


def points_fill(value: float, minimum: float, maximum: float) -> tuple[float, float, float]:
    """Reserve the Bulls-red scale for the table's ranking statistic."""
    span = maximum - minimum
    fraction = 1.0 if span <= 0 else (float(value) - minimum) / span
    return _mix("#F6DCE3", DEFAULT_THEME.accent, 0.35 + 0.65 * fraction)


def text_color(fill: tuple[float, float, float]) -> str:
    """Choose black or white text from a cell's luminance."""
    r, g, b = fill
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#FFFFFF" if luminance < 0.47 else DEFAULT_THEME.ink


def _cell(
    ax,
    left: float,
    right: float,
    y: float,
    fill,
    value: str,
    *,
    bold: bool = False,
) -> None:
    """Draw one edge-to-edge Basketball University-style heatmap cell."""
    height = ROW_HEIGHT
    ax.add_patch(
        Rectangle(
            (left, y - height / 2),
            right - left,
            height,
            facecolor=fill,
            edgecolor="none",
            linewidth=0,
            zorder=1,
        )
    )
    ax.text(
        (left + right) / 2,
        y,
        value,
        ha="center",
        va="center",
        fontsize=18.5,
        color=text_color(fill),
        fontproperties=helvetica("bold" if bold else "regular"),
        zorder=4,
    )


def points_card_bounds(row_count: int) -> tuple[float, float, float, float]:
    """Return an oversized PTS card footprint layered above the stat grid."""
    column_left, column_right = COLUMNS["PTS"]
    left = column_left - POINTS_CARD_OUTSET_X
    right = column_right + POINTS_CARD_OUTSET_X
    top = FIRST_ROW_Y + ROW_HEIGHT / 2 + POINTS_CARD_OUTSET_Y
    bottom = (
        FIRST_ROW_Y
        - (row_count - 1) * ROW_HEIGHT
        - ROW_HEIGHT / 2
        - POINTS_CARD_OUTSET_Y
    )
    return left, right, bottom, top


def _points_card(ax, players: pd.DataFrame) -> None:
    """Draw PTS as one rounded, continuous red card behind every value."""
    left, right, bottom, top = points_card_bounds(len(players))
    width = right - left
    height = top - bottom

    card = FancyBboxPatch(
        (left, bottom),
        width,
        height,
        boxstyle="round,pad=0,rounding_size=18",
        facecolor="none",
        edgecolor="none",
        zorder=2,
    )
    ax.add_patch(card)

    bottom_color = np.array(to_rgb("#E58DA5"))
    top_color = np.array(to_rgb(DEFAULT_THEME.accent))
    gradient = np.linspace(bottom_color, top_color, 768).reshape(768, 1, 3)
    image = ax.imshow(
        gradient,
        extent=(left, right, bottom, top),
        origin="lower",
        aspect="auto",
        interpolation="bicubic",
        zorder=2,
    )
    image.set_clip_path(card)


def _player_name(ax, name: str, y: float) -> None:
    """Draw a bold name, shrinking only when it would touch the PTS card."""
    base_size = 17.5
    card_left, _, _, _ = points_card_bounds(1)
    max_width = card_left - NAME_X - 12
    font = helvetica("bold")
    probe = ax.text(
        NAME_X,
        y,
        name,
        ha="left",
        va="center",
        fontsize=base_size,
        fontproperties=font,
        alpha=0,
    )
    width = rendered_width(ax, probe)
    probe.remove()
    size = base_size if width <= max_width else base_size * max_width / width
    ax.text(
        NAME_X,
        y,
        name,
        ha="left",
        va="center",
        fontsize=size,
        color=DEFAULT_THEME.ink,
        fontproperties=font,
        zorder=5,
    )


def render_chart(players: pd.DataFrame, date: str, final: bool = False) -> Path:
    """Render the transparent clutch table chart asset for Canva."""
    theme = DEFAULT_THEME
    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    ax.text(
        NAME_X,
        HEADER_Y,
        "PLAYER",
        ha="left",
        va="center",
        fontsize=15.0,
        color=theme.ink,
        fontproperties=helvetica("bold"),
    )
    for label, (left, right) in COLUMNS.items():
        ax.text(
            (left + right) / 2,
            HEADER_Y,
            label,
            ha="center",
            va="center",
            fontsize=15.0,
            color=theme.accent if label == "PTS" else theme.ink,
            fontproperties=helvetica("bold"),
        )
    ax.plot(
        [24, CHART_WIDTH - 18],
        [HEADER_RULE_Y, HEADER_RULE_Y],
        color=theme.ink,
        lw=2.0,
    )

    max_points = float(players["clutch_points"].max())
    max_minutes = float(players["clutch_minutes"].max())
    point_min = float(players["clutch_points"].min())
    _points_card(ax, players)

    for index, player in players.iterrows():
        y = FIRST_ROW_Y - index * ROW_HEIGHT
        if index:
            divider_y = y + ROW_HEIGHT / 2
            ax.plot(
                [24, 410],
                [divider_y, divider_y],
                color=theme.rule,
                lw=1.0,
                zorder=0,
            )

        square_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(player['nba_id'])}.png",
            HEADSHOT_X,
            y,
            HEADSHOT_HALF_SIZE,
            zorder=5,
        )
        _player_name(ax, str(player["official_roster_name"]), y)

        point_fill = points_fill(
            float(player["clutch_points"]), point_min, max_points
        )
        ax.text(
            sum(COLUMNS["PTS"]) / 2,
            y,
            f"{int(player['clutch_points'])}",
            ha="center",
            va="center",
            fontsize=18.5,
            color=text_color(point_fill),
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        _cell(
            ax,
            *COLUMNS["MIN"],
            y,
            minutes_fill(float(player["clutch_minutes"]), max_minutes),
            f"{float(player['clutch_minutes']):.0f}",
        )
        _cell(
            ax,
            *COLUMNS["FG"],
            y,
            fg_fill(
                float(player["fg_pct"]),
                float(player["league_clutch_fg_pct"]),
            ),
            f"{int(player['clutch_fgm'])}\N{EN DASH}{int(player['clutch_fga'])}",
        )
        _cell(
            ax,
            *COLUMNS["WIN%"],
            y,
            win_fill(float(player["win_pct"])),
            f"{float(player['win_pct']):.0%}",
        )

    path = OUT / f"{date}-current-bulls-clutch-table.png"
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
    """Return exact framing copy from the same validated run."""
    league_fg = report["league_clutch_fg_pct"]
    below = ", ".join(report["below_threshold_names"]) or "None"
    no_data = ", ".join(report["no_2025_26_clutch_data_names"]) or "None"
    return "\n".join(
        [
            "--- CANVA COPY BLOCK ---",
            "",
            "TITLE: CURRENT BULLS IN THE CLUTCH",
            "",
            "SUBTITLE: Last season's clutch production, efficiency, and results",
            "",
            (
                "QUALIFICATION: Current Bulls with 10+ clutch appearances in "
                "the 2025-26 regular season. Full-season totals across all teams."
            ),
            "",
            (
                "DEFINITIONS: Clutch = final 5:00 with the score within 5. "
                "FG = clutch field goals made–attempted; cell color compares "
                f"FG% to the NBA clutch average ({league_fg:.1%}). "
                "WIN% = team win rate in clutch games the player appeared in."
            ),
            "",
            (
                "SAMPLE NOTE: Clutch shooting samples are small; FGM–FGA makes "
                "the shooting sample visible and MIN shows opportunity context."
            ),
            "",
            f"BELOW 10 CLUTCH GAMES: {below}.",
            f"NO 2025-26 CLUTCH DATA: {no_data}.",
            "",
            f"SOURCE: Data via nba.com · Current roster as of {date}",
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
    clutch = fetch_clutch_frame()
    table = build_working_table(roster, clutch, snapshot)
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
