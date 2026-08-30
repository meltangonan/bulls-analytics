"""Rank the best Bulls five-man offenses since 2000-01.

pbpstats supplies exact five-player lineup points and offensive possessions.
The ranking compares each lineup's points per 100 possessions with the NBA's
points per 100 possessions in the same regular season.  Players are displayed
in functional lineup order from point guard through center; that display order
is editorial metadata, not a field supplied by pbpstats.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from matplotlib.patches import FancyBboxPatch

from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    square_headshot_label,
)


PROJECT = "bulls-lineup-rortg-since-2000"
POST_DATE = "2026-08-29"
FIRST_SEASON = 2000
LAST_SEASON = 2025
TEAM_ID = "1610612741"
MIN_POSSESSIONS = 500
TOP_N = 10
API_ROOT = "https://api.pbpstats.com"

OUT = _REPO / "output" / f"{POST_DATE}-{PROJECT}"
DATA = _REPO / "docs" / "visuals" / f"{POST_DATE}-{PROJECT}" / "data"
LINEUP_SOURCE = DATA / "pbpstats-bulls-lineups-2000-01-to-2025-26.csv"
LEAGUE_SOURCE = DATA / "pbpstats-league-ortg-2000-01-to-2025-26.csv"
FETCH_AUDIT = DATA / "pbpstats-lineup-fetch-audit.csv"
TOP_TEN = DATA / "bulls-lineup-rortg-top-10.csv"
SEASON_SNAPSHOTS = DATA / "season-lineup-source"

CHART_WIDTH = 1080
ROW_HEIGHT = 125
CHART_HEIGHT = 1350
POSITION_COLUMNS = ("PG", "SG", "SF", "PF", "C")
MIN_USABLE_HEADSHOT_BYTES = 50_000
HISTORICAL_HEADSHOT_URLS = {
    200758: "https://a.espncdn.com/i/headshots/nba/players/full/2991.png",
    2430: "https://a.espncdn.com/i/headshots/nba/players/full/1703.png",
    2586: "https://a.espncdn.com/i/headshots/nba/players/full/1995.png",
    1888: "https://a.espncdn.com/i/headshots/nba/players/full/294.png",
}

LINEUP_REQUIRED = {
    "Season",
    "EntityId",
    "Name",
    "TeamAbbreviation",
    "SecondsPlayed",
    "GamesPlayed",
    "OffPoss",
    "Points",
}
LINEUP_API_REQUIRED = LINEUP_REQUIRED - {"Season"}

# pbpstats returns names in entity-ID order, which has no basketball meaning.
# This small map orders only the selected historical units by their functional
# PG-to-C roles.  Tests require an exact five-name match, so a changed ranking
# cannot silently inherit the wrong order.
POSITION_ORDER: dict[tuple[str, str], tuple[str, str, str, str, str]] = {
    ("2011-12", "200758-201149-201565-2430-2736"): (
        "Derrick Rose",
        "Ronnie Brewer",
        "Luol Deng",
        "Carlos Boozer",
        "Joakim Noah",
    ),
    ("2021-22", "1629750-1630245-201942-202696-203897"): (
        "Ayo Dosunmu",
        "Zach LaVine",
        "DeMar DeRozan",
        "Javonte Green",
        "Nikola Vucevic",
    ),
    ("2010-11", "201565-2430-2586-2736-703"): (
        "Derrick Rose",
        "Keith Bogans",
        "Luol Deng",
        "Carlos Boozer",
        "Kurt Thomas",
    ),
    ("2009-10", "1802-201565-201959-2550-2736"): (
        "Derrick Rose",
        "Kirk Hinrich",
        "Luol Deng",
        "Taj Gibson",
        "Brad Miller",
    ),
    ("2014-15", "201149-201565-202710-2200-2399"): (
        "Derrick Rose",
        "Jimmy Butler",
        "Mike Dunleavy",
        "Pau Gasol",
        "Joakim Noah",
    ),
    ("2008-09", "200748-201149-201565-2422-2732"): (
        "Derrick Rose",
        "Ben Gordon",
        "John Salmons",
        "Tyrus Thomas",
        "Joakim Noah",
    ),
    ("2022-23", "1627936-201942-201976-202696-203897"): (
        "Patrick Beverley",
        "Alex Caruso",
        "Zach LaVine",
        "DeMar DeRozan",
        "Nikola Vucevic",
    ),
    ("2016-17", "200765-201577-201959-202710-2548"): (
        "Rajon Rondo",
        "Dwyane Wade",
        "Jimmy Butler",
        "Taj Gibson",
        "Robin Lopez",
    ),
    ("2010-11", "201149-201565-2430-2586-2736"): (
        "Derrick Rose",
        "Keith Bogans",
        "Luol Deng",
        "Carlos Boozer",
        "Joakim Noah",
    ),
    ("2012-13", "1888-201149-2430-2550-2736"): (
        "Kirk Hinrich",
        "Richard Hamilton",
        "Luol Deng",
        "Carlos Boozer",
        "Joakim Noah",
    ),
}


def season_label(start_year: int) -> str:
    return f"{start_year:04d}-{(start_year + 1) % 100:02d}"


def get_json(
    path: str,
    params: dict[str, str],
    *,
    attempts: int = 4,
    timeout: int = 45,
) -> dict:
    """Fetch one public pbpstats response with bounded sequential retries."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                f"{API_ROOT}{path}", params=params, timeout=timeout
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("pbpstats returned a non-object JSON response")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise RuntimeError(
        f"pbpstats request failed after {attempts} attempts: {path} {params}"
    ) from last_error


def _validated_lineup_response(
    payload: dict, season: str
) -> tuple[list[dict], dict]:
    rows = payload.get("multi_row_table_data")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"pbpstats returned no lineup rows for {season}")
    missing = LINEUP_API_REQUIRED - set(rows[0])
    if missing:
        raise ValueError(
            f"pbpstats lineup rows for {season} are missing: {sorted(missing)}"
        )
    if {str(row.get("TeamAbbreviation")) for row in rows} != {"CHI"}:
        raise ValueError(f"pbpstats returned a non-Bulls lineup for {season}")

    seconds = pd.Series(
        [float(row.get("SecondsPlayed") or 0) for row in rows]
    )
    if not seconds.is_monotonic_decreasing:
        raise ValueError(f"pbpstats lineup rows are not minutes-sorted for {season}")
    last_off_poss = int(rows[-1].get("OffPoss") or 0)
    if last_off_poss >= MIN_POSSESSIONS:
        raise ValueError(
            f"The {season} response ends at {last_off_poss} possessions; "
            "the 500-possession pool may be truncated."
        )

    audit = {
        "Season": season,
        "RowsReturned": len(rows),
        "RowsWithOffPoss": sum(int(row.get("OffPoss") or 0) > 0 for row in rows),
        "RowsSkippedMissingMetrics": sum(
            int(row.get("OffPoss") or 0) > 0
            and any(
                row.get(field) is None
                for field in ("SecondsPlayed", "GamesPlayed", "Points")
            )
            for row in rows
        ),
        "LastRowOffPoss": last_off_poss,
        "SecondsSortedDescending": True,
    }
    return rows, audit


def fetch_source_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch and save the post's lineup rows, league baselines and audit."""
    DATA.mkdir(parents=True, exist_ok=True)
    SEASON_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    lineup_rows: list[dict] = []
    audit_rows: list[dict] = []
    for start_year in range(FIRST_SEASON, LAST_SEASON + 1):
        season = season_label(start_year)
        params = {
                "Season": season,
                "SeasonType": "Regular Season",
                "Type": "Lineup",
                "TeamId": TEAM_ID,
        }
        snapshot_path = SEASON_SNAPSHOTS / f"{season}.json"
        if snapshot_path.is_file():
            snapshot = json.loads(snapshot_path.read_text())
            season_rows = snapshot["rows"]
            audit = snapshot["audit"]
            print(f"Loaded cached {season}")
        else:
            payload = get_json("/get-totals/nba", params)
            rows, audit = _validated_lineup_response(payload, season)
            season_rows = []
            for row in rows:
                off_poss = int(row.get("OffPoss") or 0)
                points = row.get("Points")
                if off_poss <= 0 or points is None:
                    continue
                if row.get("SecondsPlayed") is None or row.get("GamesPlayed") is None:
                    if off_poss >= MIN_POSSESSIONS:
                        raise ValueError(
                            f"A qualifying {season} lineup is missing playing-time "
                            f"fields: {row.get('EntityId')}"
                        )
                    continue
                season_rows.append(
                    {
                        "Season": season,
                        "EntityId": str(row["EntityId"]),
                        "Name": str(row["Name"]),
                        "TeamAbbreviation": str(row["TeamAbbreviation"]),
                        "SecondsPlayed": float(row["SecondsPlayed"]),
                        "GamesPlayed": int(row["GamesPlayed"]),
                        "OffPoss": off_poss,
                        "Points": int(points),
                    }
                )
            snapshot_path.write_text(
                json.dumps(
                    {
                        "source": f"{API_ROOT}/get-totals/nba",
                        "parameters": params,
                        "audit": audit,
                        "rows": season_rows,
                    },
                    indent=2,
                )
                + "\n"
            )
            print(f"Fetched and saved {season}")
        lineup_rows.extend(season_rows)
        audit_rows.append(audit)

    league_payload = get_json(
        "/get-league-year-over-year-plots/nba",
        {"SeasonType": "Regular Season", "LeftAxis": "PtsPer100Poss"},
    )
    league_results = league_payload.get("results")
    if not isinstance(league_results, list):
        raise ValueError("pbpstats returned no league year-over-year results")
    wanted = {
        season_label(year) for year in range(FIRST_SEASON, LAST_SEASON + 1)
    }
    league_rows = [
        {"Season": row["season"], "LeagueORTG": float(row["left_value"])}
        for row in league_results
        if row.get("season") in wanted
    ]
    if {row["Season"] for row in league_rows} != wanted:
        raise ValueError("pbpstats league ORTG coverage is incomplete")

    lineups = pd.DataFrame(lineup_rows).sort_values(
        ["Season", "SecondsPlayed"], ascending=[True, False], kind="stable"
    )
    league = pd.DataFrame(league_rows).sort_values("Season", kind="stable")
    audit = pd.DataFrame(audit_rows).sort_values("Season", kind="stable")
    lineups.to_csv(LINEUP_SOURCE, index=False)
    league.to_csv(LEAGUE_SOURCE, index=False)
    audit.to_csv(FETCH_AUDIT, index=False)
    return lineups, league, audit


def load_source_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [
        path for path in (LINEUP_SOURCE, LEAGUE_SOURCE, FETCH_AUDIT)
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing source snapshots; run with --refresh: "
            + ", ".join(str(path) for path in missing)
        )
    return (
        pd.read_csv(LINEUP_SOURCE, dtype={"EntityId": str}),
        pd.read_csv(LEAGUE_SOURCE),
        pd.read_csv(FETCH_AUDIT),
    )


def _source_names(value: str) -> set[str]:
    return {part.strip() for part in str(value).split(",") if part.strip()}


def _surname(value: str) -> str:
    surname = str(value).split()[-1]
    suffixes = {"Jr.", "Sr.", "II", "III", "IV"}
    if surname in suffixes:
        surname = str(value).split()[-2]
    return surname.upper()


def prepare_ranking(
    lineups: pd.DataFrame,
    league: pd.DataFrame,
    *,
    min_possessions: int = MIN_POSSESSIONS,
    top_n: int = TOP_N,
) -> pd.DataFrame:
    """Validate sources, compute same-season rORTG and attach position order."""
    missing = LINEUP_REQUIRED - set(lineups)
    if missing:
        raise ValueError(f"Lineup source is missing columns: {sorted(missing)}")
    if set(league) < {"Season", "LeagueORTG"}:
        raise ValueError("League source must contain Season and LeagueORTG")
    if lineups.duplicated(["Season", "EntityId"]).any():
        raise ValueError("Duplicate season-lineup rows in pbpstats source")
    if league["Season"].duplicated().any():
        raise ValueError("Duplicate season rows in league ORTG source")

    merged = lineups.merge(league, on="Season", how="left", validate="many_to_one")
    numeric = ["Points", "OffPoss", "SecondsPlayed", "LeagueORTG"]
    if merged[numeric].isna().any().any():
        raise ValueError("A lineup is missing points, possessions, time or baseline")
    if (merged["OffPoss"] <= 0).any():
        raise ValueError("Offensive possessions must be positive")

    merged["ORTG"] = 100 * merged["Points"] / merged["OffPoss"]
    merged["rORTG"] = merged["ORTG"] - merged["LeagueORTG"]
    merged["Minutes"] = merged["SecondsPlayed"] / 60
    eligible = merged.loc[merged["OffPoss"] >= min_possessions].copy()
    if len(eligible) < top_n:
        raise ValueError(
            f"Only {len(eligible)} lineups reached {min_possessions} possessions; "
            f"{top_n} are required."
        )
    rows = (
        eligible.sort_values(
            ["rORTG", "OffPoss", "Season", "Name"],
            ascending=[False, False, True, True],
            kind="stable",
        )
        .head(top_n)
        .reset_index(drop=True)
    )
    rows.insert(0, "Rank", np.arange(1, len(rows) + 1))

    for index, row in rows.iterrows():
        key = (str(row["Season"]), str(row["EntityId"]))
        order = POSITION_ORDER.get(key)
        if order is None:
            raise ValueError(f"No PG-to-C display order recorded for {key}")
        if set(order) != _source_names(row["Name"]):
            raise ValueError(f"Position order does not match source names for {key}")
        for position, player in zip(POSITION_COLUMNS, order):
            rows.loc[index, position] = player
            rows.loc[index, f"{position}_LABEL"] = _surname(player)
            source_pairs = dict(
                zip(
                    [part.strip() for part in str(row["Name"]).split(",")],
                    str(row["EntityId"]).split("-"),
                )
            )
            rows.loc[index, f"{position}_ID"] = int(source_pairs[player])

    if not rows["rORTG"].is_monotonic_decreasing:
        raise ValueError("Selected lineups are not ordered by rORTG")
    return rows


def write_top_ten(rows: pd.DataFrame) -> Path:
    columns = [
        "Rank",
        "Season",
        "EntityId",
        *POSITION_COLUMNS,
        "GamesPlayed",
        "Minutes",
        "OffPoss",
        "Points",
        "ORTG",
        "LeagueORTG",
        "rORTG",
    ]
    table = rows[columns].copy()
    for column in ["Minutes", "ORTG", "LeagueORTG", "rORTG"]:
        table[column] = table[column].round(3)
    TOP_TEN.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(TOP_TEN, index=False)
    return TOP_TEN


def _rating_label(value: float) -> str:
    rounded = round(float(value), 1)
    if rounded > 0:
        return f"+{rounded:.1f}"
    if rounded < 0:
        return f"−{abs(rounded):.1f}"
    return "0.0"


def ensure_historical_headshots(player_ids: list[int]) -> None:
    """Replace NBA CDN silhouettes with stable ESPN studio portraits."""
    for player_id in {int(value) for value in player_ids}:
        url = HISTORICAL_HEADSHOT_URLS.get(player_id)
        if url is None:
            continue
        path = HEADSHOT_CACHE / f"{player_id}.png"
        if path.is_file() and path.stat().st_size >= MIN_USABLE_HEADSHOT_BYTES:
            continue
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        if len(response.content) < MIN_USABLE_HEADSHOT_BYTES:
            raise ValueError(f"Fallback portrait for {player_id} is too small")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)


def render_chart(rows: pd.DataFrame, *, final: bool = False) -> Path:
    """Render the reference-inspired lineup shelf as a transparent Canva asset."""
    theme = DEFAULT_THEME
    player_ids = [
        int(row[f"{position}_ID"])
        for _, row in rows.iterrows()
        for position in POSITION_COLUMNS
    ]
    ensure_headshots(player_ids)
    ensure_historical_headshots(player_ids)
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

    first_row_y = CHART_HEIGHT - 76
    position_x = {"PG": 180, "SG": 334, "SF": 488, "PF": 642, "C": 796}
    x_metric = 960

    for index, row in rows.iterrows():
        y = first_row_y - index * ROW_HEIGHT
        shelf_y = y
        ax.plot(
            [145, 903],
            [shelf_y, shelf_y],
            color=theme.accent,
            lw=1.2,
            solid_capstyle="round",
            zorder=1,
        )
        ax.text(
            125,
            y + 32,
            str(row["Season"]),
            ha="right",
            va="center",
            fontsize=11,
            color=theme.muted,
            fontproperties=helvetica("bold_oblique"),
        )
        for position in POSITION_COLUMNS:
            x = position_x[position]
            square_headshot_label(
                ax,
                HEADSHOT_CACHE / f"{int(row[f'{position}_ID'])}.png",
                x,
                y + 11,
                49,
                zorder=3,
                face_fraction=0.72,
            )
            ax.text(
                x,
                y - 56,
                row[f"{position}_LABEL"],
                ha="center",
                va="center",
                fontsize=7.4,
                color=theme.ink,
                fontproperties=helvetica("bold"),
                zorder=5,
            )

        positive = float(row["rORTG"]) >= 0
        badge_fill = "#B5123C"
        # The zone-chart summary cards use this Bulls-red rounded pill grammar.
        ax.add_patch(
            FancyBboxPatch(
                (x_metric - 57, y - 35),
                114,
                70,
                boxstyle="round,pad=0,rounding_size=13",
                facecolor=badge_fill,
                edgecolor="none",
                zorder=3,
            )
        )
        ax.text(
            x_metric,
            y + 10,
            _rating_label(row["rORTG"]),
            ha="center",
            va="center",
            fontsize=16,
            color="#FFFFFF",
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        ax.text(
            x_metric,
            y - 16,
            f"{int(row['OffPoss']):,} POSS",
            ha="center",
            va="center",
            fontsize=8,
            color="#FFFFFF",
            fontproperties=helvetica("oblique"),
            zorder=4,
        )

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{POST_DATE}-bulls-lineup-rortg-top-10.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return path


def canva_copy_block(rows: pd.DataFrame) -> str:
    leader = rows.iloc[0]
    leader_names = " / ".join(str(leader[pos]) for pos in POSITION_COLUMNS)
    return "\n".join(
        [
            "=== CANVA COPY (DATA-BOUND) ===",
            "",
            "TITLE: THE BULLS’ BEST OFFENSIVE LINEUPS SINCE 2000",
            "",
            (
                "SUBTITLE: Chicago’s top five-man units by offensive rating "
                "relative to the NBA average that season"
            ),
            "",
            f"LEAD NOTE: {leader_names} ranked first at {_rating_label(leader['rORTG'])} rORTG.",
            "",
            (
                "QUALIFICATION: 2000-01 through 2025-26 regular seasons · "
                f"Minimum {MIN_POSSESSIONS:,} offensive possessions"
            ),
            "",
            (
                "METHOD: rORTG = lineup points per 100 possessions minus NBA "
                "points per 100 possessions in the same season. Players are "
                "ordered PG to C by functional lineup role."
            ),
            "",
            "SOURCE: pbpstats.com · Derived from NBA play-by-play",
            "",
            "HANDLE: @chicagobullsdata",
            "",
            "=== END CANVA COPY ===",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank Bulls five-man lineup offense relative to each season."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch and replace the tracked pbpstats source snapshots.",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export the chart asset at publish resolution.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Accepted for CLI consistency; the post folder remains dated 2026-08-29.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.refresh:
        lineups, league, audit = fetch_source_tables()
    else:
        lineups, league, audit = load_source_tables()
    if len(audit) != LAST_SEASON - FIRST_SEASON + 1:
        raise ValueError("Fetch audit does not contain all 26 seasons")

    rows = prepare_ranking(lineups, league)
    table_path = write_top_ten(rows)
    chart_path = render_chart(rows, final=args.final)
    print(
        rows[
            ["Rank", "Season", *POSITION_COLUMNS, "OffPoss", "ORTG", "rORTG"]
        ].to_string(index=False)
    )
    print(f"\nSource lineups: {LINEUP_SOURCE}")
    print(f"League baselines: {LEAGUE_SOURCE}")
    print(f"Fetch audit: {FETCH_AUDIT}")
    print(f"Top-ten table: {table_path}")
    print(f"Chart asset: {chart_path}")
    scale = 2 if args.final else 1
    print(f"Chart export: {CHART_WIDTH * scale}×{CHART_HEIGHT * scale} px")
    print()
    print(canva_copy_block(rows))


if __name__ == "__main__":
    main()
