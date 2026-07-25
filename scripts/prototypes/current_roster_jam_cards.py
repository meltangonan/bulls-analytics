"""Build NBA Jam-style player cards for the current Bulls roster.

Each card carries six bars whose length is the player's league percentile in a
per-75-possession production rate, so the shape of a card describes how a player
fills a box score rather than how good he is.

Ported from Owen Phillips' F5 tutorial "How To Make A NBA Jam Style Small
Multiple" (thef5.substack.com, Apr 27 2025). His R/ggplot2 anatomy is preserved:
percentile-length rounded bars over a faint full-length track, the value printed
on the bar, a portrait and name band inside a hairline card border, and cards
ordered by summed percentile. Card orientation is landscape here because ten
subjects on a 4:5 page want wide bars, where his thirty-six wanted tall cards.

NBA.com owns roster membership, the zone definitions, and every input total.
Zone field goals reconcile exactly to each player's box-score FGM and FGA.
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
from matplotlib.patches import FancyBboxPatch
from nba_api.stats.endpoints import (
    leaguedashplayershotlocations,
    leaguedashplayerstats,
)

from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    export_dpi,
    helvetica,
)
from scripts.prototypes.current_roster_darko_landscape import (
    NBA_ROSTER_URL,
    _fetch_html,
    ensure_headshots,
    parse_nba_roster,
    square_headshot_label,
)

SEASON = "2025-26"
SEASON_TYPE = "Regular Season"
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
# Qualification is a playing-time gate, not a shooting gate. An attempt
# threshold would decide who ranks in PASS by how much a player shot, and it
# is measured in the same unit as the per-75 rates it screens.
MIN_POSSESSIONS = 1500.0
PER_POSSESSIONS = 75.0
OUT = _REPO / "output" / "feed"

NBA_SHOT_LOCATIONS_URL = (
    "https://www.nba.com/stats/players/shots-general"
    "?Season=2025-26&SeasonType=Regular%20Season"
)
NBA_PLAYER_STATS_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?Season=2025-26&SeasonType=Regular%20Season&PerMode=Totals"
)

# Bar order is the shot chart read outward from the basket, then playmaking.
# Label, working-table key, and the definition that has to appear on the Canva
# page. Every bar is an offensive dimension: steals and blocks were tested as a
# defence bar and cut, because they rank good defenders badly.
CATEGORIES = [
    ("RIM", "rim", "Restricted-area points"),
    ("PAINT NON-RA", "paint", "Paint points outside the restricted area"),
    ("MID", "mid", "Mid-range points"),
    ("THREE", "three", "Three-point points"),
    ("PASS", "pass", "Assists"),
]

ZONE_POINT_VALUES = {
    "Restricted Area": 2,
    "In The Paint (Non-RA)": 2,
    "Mid-Range": 2,
    "Left Corner 3": 3,
    "Right Corner 3": 3,
    "Above the Break 3": 3,
    "Backcourt": 3,
}

SHORT_NAMES = {
    "Josh Giddey": "GIDDEY",
    "Nic Claxton": "CLAXTON",
    "Norman Powell": "POWELL",
    "Rob Dillingham": "DILLINGHAM",
    "Tre Jones": "TRE JONES",
    "Matas Buzelis": "BUZELIS",
    "Jalen Smith": "JALEN SMITH",
    "Leonard Miller": "L. MILLER",
    "Patrick Williams": "P. WILLIAMS",
    "Isaac Okoro": "OKORO",
}

# Canvas geometry. Coordinate units export at 2x when --final doubles the DPI.
CHART_WIDTH = 1080
MARGIN_X = 30
MARGIN_Y = 24
COLUMNS = 2
CARD_W = 505
CARD_H = 200
GUTTER_X = 10
GUTTER_Y = 14

PORTRAIT_HALF = 46
LEFT_BLOCK_W = 150
LEFT_BLOCK_H = 142  # portrait, name plate, and the games/minutes line
BAR_H = 19
BAR_GAP = 9
LABEL_W = 100  # wide enough for the longest label, "PAINT NON-RA"
VALUE_INSIDE_MIN = 26.0  # percentile below which the value sits outside the bar

BAR_EDGE = "#900C2E"  # theme.accent darkened, matching the tutorial's edge rule
TRACK_FILL = "#EDE7E0"
TRACK_EDGE = "#DCD4CB"
CARD_FILL = "#F5F1EC"


def fetch_league_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch league-wide zone splits, traditional totals, and possessions."""
    common = {
        "season": SEASON,
        "season_type_all_star": SEASON_TYPE,
        "per_mode_detailed": "Totals",
        "timeout": 90,
        "headers": _NBA_HEADERS,
    }
    zones = leaguedashplayershotlocations.LeagueDashPlayerShotLocations(
        distance_range="By Zone",
        **common,
    ).get_data_frames()[0]
    zones.columns = [
        second if not first else f"{first}|{second}"
        for first, second in zones.columns
    ]
    base = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Base",
        **common,
    ).get_data_frames()[0]
    advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense="Advanced",
        **common,
    ).get_data_frames()[0]
    return zones, base, advanced


def build_league_table(
    zones: pd.DataFrame,
    base: pd.DataFrame,
    advanced: pd.DataFrame,
) -> pd.DataFrame:
    """Join league frames and derive per-75 rates and league percentiles.

    Percentiles rank each qualified player against every other qualified player,
    so a bar answers "where does this rate sit in the NBA" rather than "where
    does it sit among the Bulls".
    """
    base_columns = [
        "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN",
        "FGM", "FGA", "FTM", "FTA", "PTS", "AST",
    ]
    zone_columns = [
        f"{zone}|{stat}"
        for zone in ZONE_POINT_VALUES
        for stat in ("FGM", "FGA")
    ]

    missing = (
        (set(base_columns) - set(base.columns))
        | ({"PLAYER_ID", "POSS"} - set(advanced.columns))
        | (set(zone_columns) | {"PLAYER_ID"}) - set(zones.columns)
    )
    if missing:
        raise ValueError(f"NBA.com response columns changed: {sorted(missing)}")

    table = (
        base[base_columns]
        .merge(
            advanced[["PLAYER_ID", "POSS"]],
            on="PLAYER_ID",
            how="inner",
            validate="one_to_one",
        )
        .merge(
            zones[["PLAYER_ID"] + zone_columns],
            on="PLAYER_ID",
            how="inner",
            validate="one_to_one",
        )
        .rename(columns={"PLAYER_ID": "nba_id", "PLAYER_NAME": "player_name"})
    )

    table["true_shooting_attempts"] = table["FGA"] + 0.44 * table["FTA"]
    table["zone_fgm"] = sum(table[f"{z}|FGM"] for z in ZONE_POINT_VALUES)
    table["zone_fga"] = sum(table[f"{z}|FGA"] for z in ZONE_POINT_VALUES)
    table["zone_points"] = sum(
        table[f"{zone}|FGM"] * points
        for zone, points in ZONE_POINT_VALUES.items()
    )

    table["rim_total"] = table["Restricted Area|FGM"] * 2
    table["paint_total"] = table["In The Paint (Non-RA)|FGM"] * 2
    table["mid_total"] = table["Mid-Range|FGM"] * 2
    table["three_total"] = (
        table["Left Corner 3|FGM"]
        + table["Right Corner 3|FGM"]
        + table["Above the Break 3|FGM"]
    ) * 3
    table["pass_total"] = table["AST"]

    table["qualified"] = table["POSS"].ge(MIN_POSSESSIONS)

    for _, key, _ in CATEGORIES:
        table[f"rate_{key}"] = (
            table[f"{key}_total"] * PER_POSSESSIONS / table["POSS"]
        )
        ranked = table.loc[table["qualified"], f"rate_{key}"]
        table[f"pct_{key}"] = ranked.rank(pct=True) * 100

    return table


def roster_cards(table: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """Return qualified roster players in card order, most minutes first.

    Minutes order reads as the rotation rather than as a ranking, which the
    summed-percentile order used by the source tutorial would imply. These are
    style profiles, so no card should be positioned as the worst one.
    """
    cards = table[
        table["nba_id"].isin(roster["nba_id"]) & table["qualified"]
    ].copy()
    return cards.sort_values(
        ["MIN", "player_name"], ascending=[False, True]
    ).reset_index(drop=True)


def validate_league_table(
    table: pd.DataFrame,
    roster: pd.DataFrame,
    cards: pd.DataFrame,
) -> dict:
    """Check identities, NBA.com reconciliation, and percentile integrity."""
    if table["nba_id"].duplicated().any():
        raise ValueError("League table contains duplicate NBA player IDs.")

    fgm_residual = float((table["zone_fgm"] - table["FGM"]).abs().max())
    fga_residual = float((table["zone_fga"] - table["FGA"]).abs().max())
    if fgm_residual or fga_residual:
        raise ValueError(
            "NBA.com zone splits do not reconcile to box-score field goals: "
            f"FGM {fgm_residual}, FGA {fga_residual}"
        )

    points_residual = (
        table["zone_points"] + table["FTM"] - table["PTS"]
    ).abs()
    max_points_residual = float(points_residual.max())
    if max_points_residual > 1.0:
        raise ValueError(
            "Zone points plus free throws do not reconstruct total points: "
            f"{max_points_residual}"
        )
    unreconciled = table.loc[points_residual > 0, "player_name"].tolist()

    qualifiers = table[table["qualified"]]
    if qualifiers.empty:
        raise ValueError("No league players met the attempt qualification.")
    if cards.empty:
        raise ValueError("No current-roster players met the qualification.")
    if cards["player_name"].map(SHORT_NAMES).isna().any():
        unlabeled = cards.loc[
            cards["player_name"].map(SHORT_NAMES).isna(), "player_name"
        ].tolist()
        raise ValueError(f"Missing card labels: {unlabeled}")

    percentile_columns = [f"pct_{key}" for _, key, _ in CATEGORIES]
    if cards[percentile_columns].isna().any().any():
        raise ValueError("A card is missing a percentile value.")
    out_of_range = (
        cards[percentile_columns].lt(0).any().any()
        or cards[percentile_columns].gt(100).any().any()
    )
    if out_of_range:
        raise ValueError("A percentile fell outside 0-100.")
    if len(cards) > COLUMNS * 5:
        raise ValueError(
            f"{len(cards)} cards exceed the {COLUMNS}x5 grid; re-scope the layout."
        )

    excluded = roster[~roster["nba_id"].isin(cards["nba_id"])]
    return {
        "league_players": int(len(table)),
        "qualified_league_players": int(len(qualifiers)),
        "roster_count": int(len(roster)),
        "card_count": int(len(cards)),
        "card_order": cards["player_name"].tolist(),
        "excluded_roster_names": sorted(
            excluded["official_roster_name"].tolist()
        ),
        "zone_fgm_residual": fgm_residual,
        "zone_fga_residual": fga_residual,
        "max_points_residual": max_points_residual,
        "players_with_points_residual": unreconciled,
        "qualification_possessions": MIN_POSSESSIONS,
    }


def write_table(table: pd.DataFrame, roster: pd.DataFrame, date: str) -> Path:
    """Write every roster player, including those the qualification excludes."""
    columns = (
        ["nba_id", "player_name", "TEAM_ABBREVIATION", "GP", "MIN", "POSS",
         "true_shooting_attempts", "qualified"]
        + [f"rate_{key}" for _, key, _ in CATEGORIES]
        + [f"pct_{key}" for _, key, _ in CATEGORIES]
    )
    working = table[table["nba_id"].isin(roster["nba_id"])][columns].copy()
    working = working.merge(
        roster[["nba_id", "official_roster_name"]], on="nba_id", how="right"
    ).sort_values("MIN", ascending=False)
    working["season"] = SEASON
    working["season_type"] = SEASON_TYPE
    working["per_possessions"] = PER_POSSESSIONS
    working["roster_source"] = NBA_ROSTER_URL
    working["zone_source"] = NBA_SHOT_LOCATIONS_URL
    working["stats_source"] = NBA_PLAYER_STATS_URL
    working["snapshot_date"] = date

    path = OUT / f"{date}-current-bulls-jam-cards-working.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    working.to_csv(path, index=False)
    return path


def _card_origin(index: int) -> tuple[float, float, float]:
    """Return the lower-left corner and top edge of the card at grid index."""
    column = index % COLUMNS
    row = index // COLUMNS
    x = MARGIN_X + column * (CARD_W + GUTTER_X)
    top = CHART_HEIGHT - MARGIN_Y - row * (CARD_H + GUTTER_Y)
    return x, top - CARD_H, top


def _rows() -> int:
    return 5


CHART_HEIGHT = MARGIN_Y * 2 + _rows() * CARD_H + (_rows() - 1) * GUTTER_Y


def _draw_bar(ax, theme, x: float, y: float, width: float,
              label: str, percentile: float) -> None:
    """Draw one labelled percentile bar over its full-length track."""
    track_x = x + LABEL_W
    track_w = width - LABEL_W

    ax.text(
        x, y + BAR_H / 2, label,
        fontproperties=helvetica("bold"), fontsize=6.0, color=theme.muted,
        ha="left", va="center", zorder=6,
    )
    ax.add_patch(
        FancyBboxPatch(
            (track_x, y), track_w, BAR_H,
            boxstyle="round,pad=0,rounding_size=4",
            facecolor=TRACK_FILL, edgecolor=TRACK_EDGE, lw=0.6, zorder=4,
        )
    )

    filled = max(track_w * percentile / 100.0, 3.0)
    ax.add_patch(
        FancyBboxPatch(
            (track_x, y), filled, BAR_H,
            boxstyle="round,pad=0,rounding_size=4",
            facecolor=theme.accent, edgecolor=BAR_EDGE, lw=0.7, zorder=5,
        )
    )

    value = f"{percentile:.0f}"
    if percentile >= VALUE_INSIDE_MIN:
        ax.text(
            track_x + filled - 7, y + BAR_H / 2, value,
            fontproperties=helvetica("bold"), fontsize=8.2, color="#FFFFFF",
            ha="right", va="center", zorder=7,
        )
    else:
        ax.text(
            track_x + filled + 6, y + BAR_H / 2, value,
            fontproperties=helvetica("bold"), fontsize=8.2, color=theme.ink,
            ha="left", va="center", zorder=7,
        )


def _draw_card(ax, theme, index: int, player: pd.Series) -> None:
    """Draw one player card: portrait and name at left, six bars at right."""
    x0, y0, y1 = _card_origin(index)

    ax.add_patch(
        FancyBboxPatch(
            (x0, y0), CARD_W, CARD_H,
            boxstyle="round,pad=0,rounding_size=7",
            facecolor=CARD_FILL, edgecolor=theme.ink, lw=0.9, zorder=2,
        )
    )

    # The two halves differ in height, so each is centred in the card on its
    # own rather than sharing one top edge.
    bar_block_h = len(CATEGORIES) * BAR_H + (len(CATEGORIES) - 1) * BAR_GAP
    bar_top = y0 + (CARD_H + bar_block_h) / 2
    left_top = y0 + (CARD_H + LEFT_BLOCK_H) / 2

    portrait_cx = x0 + LEFT_BLOCK_W / 2
    portrait_cy = left_top - PORTRAIT_HALF - 4
    square_headshot_label(
        ax,
        _REPO / "cache" / "headshots" / f"{int(player['nba_id'])}.png",
        portrait_cx,
        portrait_cy,
        PORTRAIT_HALF,
    )

    # The name plate clears the portrait's lower edge; NBA CDN crops vary in
    # how low the torso sits, so an overlap reads as a mistake on some players.
    name_y = portrait_cy - PORTRAIT_HALF - 26
    ax.add_patch(
        FancyBboxPatch(
            (x0 + 10, name_y - 2), LEFT_BLOCK_W - 20, 24,
            boxstyle="round,pad=0,rounding_size=4",
            facecolor="#FFFFFF", edgecolor=theme.ink, lw=0.8, zorder=6,
        )
    )
    ax.text(
        portrait_cx, name_y + 10, SHORT_NAMES[player["player_name"]],
        fontproperties=helvetica("bold"), fontsize=8.0, color=theme.ink,
        ha="center", va="center", zorder=7,
    )
    ax.text(
        portrait_cx, name_y - 15,
        f"{int(player['GP'])} GP · {int(round(player['MIN'])):,} MIN",
        fontproperties=helvetica(), fontsize=6.2, color=theme.muted,
        ha="center", va="center", zorder=7,
    )

    bar_x = x0 + LEFT_BLOCK_W
    bar_w = CARD_W - LEFT_BLOCK_W - 22

    for slot, (label, key, _) in enumerate(CATEGORIES):
        _draw_bar(
            ax, theme, bar_x,
            bar_top - BAR_H - slot * (BAR_H + BAR_GAP), bar_w,
            label, float(player[f"pct_{key}"]),
        )


def render_chart_only(cards: pd.DataFrame, date: str, final: bool) -> Path:
    """Render the transparent card wall for Canva framing."""
    theme = DEFAULT_THEME
    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI)
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    for index, (_, player) in enumerate(cards.iterrows()):
        _draw_card(ax, theme, index, player)

    path = OUT / f"{date}-current-bulls-jam-cards.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    # house.save_post bakes in an opaque facecolor; the Canva page supplies the
    # background, so this asset has to leave it alone.
    fig.savefig(path, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return path


def canva_copy_block(cards: pd.DataFrame, report: dict, date: str) -> str:
    """Exact strings for the Canva page, so no number is retyped by eye."""
    definitions = " · ".join(
        f"{label} {definition}" for label, _, definition in CATEGORIES
    )
    excluded = ", ".join(report["excluded_roster_names"])
    return "\n".join([
        "--- CANVA COPY BLOCK ---",
        "",
        "BARS: " + definitions,
        "",
        (
            "LEGEND: Each bar is the player's percentile rank among "
            f"{report['qualified_league_players']} qualified NBA players in "
            f"that rate per {PER_POSSESSIONS:.0f} possessions. Longer = more "
            "of it, not better."
        ),
        "",
        (
            "OFFENSE ONLY: there is no defense bar. Steals and blocks are the "
            "only defensive events in a box score and they rank good "
            "defenders badly, so these cards describe offensive style only."
        ),
        "",
        "ORDER: most minutes played first. This is not a ranking.",
        "",
        (
            f"QUALIFICATION: {SEASON} regular season, minimum "
            f"{MIN_POSSESSIONS:.0f} possessions played. "
            f"{report['card_count']} of {report['roster_count']} current "
            f"Bulls qualify, ranked against "
            f"{report['qualified_league_players']} qualified NBA players."
        ),
        "",
        (
            "PRIOR TEAMS: totals follow each player across all of "
            f"{SEASON}; new Bulls did not produce them in Chicago."
        ),
        "",
        f"BELOW THE LINE: {excluded}.",
        "",
        f"SOURCE: Data via nba.com · Roster as of {date}",
        "CREDIT: Format after Owen Phillips / The F5",
        "",
        "--- END ---",
    ])


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
    snapshot = datetime.now(SNAPSHOT_TZ)
    date = snapshot.date().isoformat()

    roster = parse_nba_roster(_fetch_html(NBA_ROSTER_URL))
    zones, base, advanced = fetch_league_frames()
    table = build_league_table(zones, base, advanced)
    cards = roster_cards(table, roster)
    report = validate_league_table(table, roster, cards)

    table_path = write_table(table, roster, date)
    ensure_headshots(cards)
    chart_path = render_chart_only(cards, date, args.final)

    print(json.dumps(report, indent=2))
    print(f"\nWrote {table_path}")
    print(f"Wrote {chart_path}\n")
    print(canva_copy_block(cards, report, date))


if __name__ == "__main__":
    main()
