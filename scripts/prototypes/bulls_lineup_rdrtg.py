"""Rank the best Bulls five-man defenses since 2000-01.

pbpstats supplies exact five-player lineup opponent points and defensive
possessions. The ranking compares each lineup's points allowed per 100
possessions with the NBA's same-season defensive rating. Players are shown in
functional lineup order from point guard through center; that display order
is editorial metadata, not a field supplied by pbpstats.
"""

from __future__ import annotations

import argparse
from io import BytesIO
import json
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
import requests
from PIL import Image

from bulls.graphics.craft import draw_metric_badge
from bulls.graphics.house import DEFAULT_THEME, DRAFT_DPI, HEADSHOT_CACHE, export_dpi, helvetica, square_headshot_label
from scripts.prototypes import bulls_lineup_rortg as rortg


PROJECT = "bulls-lineup-rdrtg-since-2000"
POST_DATE = "2026-08-30"
FIRST_SEASON = 2000
LAST_SEASON = 2025
TEAM_ID = "1610612741"
MIN_POSSESSIONS = 500
TOP_N = 10
API_ROOT = rortg.API_ROOT

OUT = _REPO / "output" / f"{POST_DATE}-{PROJECT}"
DATA = _REPO / "docs" / "visuals" / f"{POST_DATE}-{PROJECT}" / "data"
LINEUP_SOURCE = DATA / "pbpstats-bulls-lineups-2000-01-to-2025-26.csv"
LEAGUE_SOURCE = DATA / "pbpstats-league-drtg-2000-01-to-2025-26.csv"
FETCH_AUDIT = DATA / "pbpstats-lineup-fetch-audit.csv"
TOP_TEN = DATA / "bulls-lineup-rdrtg-top-10.csv"
SEASON_SNAPSHOTS = DATA / "season-lineup-source"
SOURCE_LEAGUE_ORTG = _REPO / "docs" / "visuals" / "2026-08-29-bulls-lineup-rortg-since-2000" / "data" / "pbpstats-league-ortg-2000-01-to-2025-26.csv"
PROJECT_HEADSHOT_OVERRIDES = {
    213: DATA.parent / "assets" / "antonio-davis-cutout.png",
}

CHART_WIDTH = 1080
ROW_HEIGHT = 125
CHART_HEIGHT = 1350
POSITION_COLUMNS = ("PG", "SG", "SF", "PF", "C")
MIN_USABLE_HEADSHOT_BYTES = 20_000
HISTORICAL_HEADSHOT_URLS = {
    213: "https://commons.wikimedia.org/wiki/Special:FilePath/AD33Cincy2009.jpg",
    2201: "https://a.espncdn.com/i/headshots/nba/players/full/990.png",
    2768: "https://a.espncdn.com/i/headshots/nba/players/full/2377.png",
    2804: "https://a.espncdn.com/i/headshots/nba/players/full/2456.png",
    203107: "https://a.espncdn.com/i/headshots/nba/players/full/6621.png",
}

# These are the ten functional orders in the defensive result. The source
# exposes identities, but not PG-to-C role slots, so this map is explicit and
# checked against both the source names and entity IDs before rendering.
POSITION_ORDER = {
    ("2004-05", "213-2201-2550-2736-2768"): (
        "Kirk Hinrich",
        "Chris Duhon",
        "Luol Deng",
        "Antonio Davis",
        "Eddy Curry",
    ),
    ("2019-20", "1627739-1628374-1628976-203107-203897"): (
        "Kris Dunn",
        "Zach LaVine",
        "Tomas Satoransky",
        "Lauri Markkanen",
        "Wendell Carter Jr.",
    ),
    ("2022-23", "1627936-201942-201976-202696-203897"): (
        "Patrick Beverley",
        "Alex Caruso",
        "Zach LaVine",
        "DeMar DeRozan",
        "Nikola Vucevic",
    ),
    ("2013-14", "201149-202710-2399-2430-2550"): (
        "Kirk Hinrich",
        "Jimmy Butler",
        "Mike Dunleavy",
        "Carlos Boozer",
        "Joakim Noah",
    ),
    ("2011-12", "200758-201149-201565-2430-2736"): (
        "Derrick Rose",
        "Ronnie Brewer",
        "Luol Deng",
        "Carlos Boozer",
        "Joakim Noah",
    ),
    ("2010-11", "201149-201565-2430-2586-2736"): (
        "Derrick Rose",
        "Keith Bogans",
        "Luol Deng",
        "Carlos Boozer",
        "Joakim Noah",
    ),
    ("2006-07", "1112-2550-2736-2768-2804"): (
        "Kirk Hinrich",
        "Chris Duhon",
        "Luol Deng",
        "Andres Nocioni",
        "Ben Wallace",
    ),
    ("2012-13", "1888-201149-2430-2550-2736"): (
        "Kirk Hinrich",
        "Richard Hamilton",
        "Luol Deng",
        "Carlos Boozer",
        "Joakim Noah",
    ),
    ("2009-10", "201149-201565-201959-2550-2736"): (
        "Derrick Rose",
        "Kirk Hinrich",
        "Luol Deng",
        "Taj Gibson",
        "Joakim Noah",
    ),
    ("2023-24", "1627936-1629632-1630245-201942-202696"): (
        "Coby White",
        "Ayo Dosunmu",
        "DeMar DeRozan",
        "Alex Caruso",
        "Nikola Vucevic",
    ),
}

LINEUP_REQUIRED = {
    "Season",
    "EntityId",
    "Name",
    "TeamAbbreviation",
    "SecondsPlayed",
    "GamesPlayed",
    "DefPoss",
    "OpponentPoints",
}


def season_label(start_year: int) -> str:
    return f"{start_year:04d}-{(start_year + 1) % 100:02d}"


def _validated_lineup_response(payload: dict, season: str) -> tuple[list[dict], dict]:
    rows = payload.get("multi_row_table_data")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"pbpstats returned no lineup rows for {season}")
    missing = {"EntityId", "Name", "TeamAbbreviation", "SecondsPlayed", "GamesPlayed", "DefPoss", "OpponentPoints"} - set(rows[0])
    if missing:
        raise ValueError(f"pbpstats lineup rows for {season} are missing: {sorted(missing)}")
    if {str(row.get("TeamAbbreviation")) for row in rows} != {"CHI"}:
        raise ValueError(f"pbpstats returned a non-Bulls lineup for {season}")
    seconds = pd.Series([float(row.get("SecondsPlayed") or 0) for row in rows])
    if not seconds.is_monotonic_decreasing:
        raise ValueError(f"pbpstats lineup rows are not minutes-sorted for {season}")
    last_def_poss = int(rows[-1].get("DefPoss") or 0)
    audit = {
        "Season": season,
        "RowsReturned": len(rows),
        "RowsWithDefPoss": sum(int(row.get("DefPoss") or 0) > 0 for row in rows),
        "RowsSkippedMissingMetrics": sum(
            int(row.get("DefPoss") or 0) > 0
            and any(row.get(field) is None for field in ("SecondsPlayed", "GamesPlayed", "OpponentPoints"))
            for row in rows
        ),
        "LastRowDefPoss": last_def_poss,
        "SecondsSortedDescending": True,
    }
    return rows, audit


def _lineup_params(season: str) -> dict[str, str]:
    return {"Season": season, "SeasonType": "Regular Season", "Type": "Lineup", "TeamId": TEAM_ID}


def _league_params(season: str) -> dict[str, str]:
    return {"Season": season, "SeasonType": "Regular Season", "Type": "Team"}


def fetch_source_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch and save lineup rows, season league baselines and completeness audit."""
    DATA.mkdir(parents=True, exist_ok=True)
    SEASON_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    lineup_rows: list[dict] = []
    audit_rows: list[dict] = []

    for start_year in range(FIRST_SEASON, LAST_SEASON + 1):
        season = season_label(start_year)
        snapshot_path = SEASON_SNAPSHOTS / f"{season}.json"
        if snapshot_path.is_file():
            snapshot = json.loads(snapshot_path.read_text())
            season_rows = snapshot["rows"]
            audit = snapshot["audit"]
            print(f"Loaded cached {season}")
        else:
            payload = rortg.get_json("/get-totals/nba", _lineup_params(season))
            rows, audit = _validated_lineup_response(payload, season)
            season_rows = []
            for row in rows:
                def_poss = int(row.get("DefPoss") or 0)
                opponent_points = row.get("OpponentPoints")
                if def_poss <= 0 or opponent_points is None:
                    continue
                if row.get("SecondsPlayed") is None or row.get("GamesPlayed") is None:
                    if def_poss >= MIN_POSSESSIONS:
                        raise ValueError(f"A qualifying {season} lineup is missing playing-time fields: {row.get('EntityId')}")
                    continue
                season_rows.append(
                    {
                        "Season": season,
                        "EntityId": str(row["EntityId"]),
                        "Name": str(row["Name"]),
                        "TeamAbbreviation": str(row["TeamAbbreviation"]),
                        "SecondsPlayed": float(row["SecondsPlayed"]),
                        "GamesPlayed": int(row["GamesPlayed"]),
                        "DefPoss": def_poss,
                        "OpponentPoints": int(opponent_points),
                    }
                )
            snapshot_path.write_text(json.dumps({"source": f"{API_ROOT}/get-totals/nba", "parameters": _lineup_params(season), "audit": audit, "rows": season_rows}, indent=2) + "\n")
            print(f"Fetched and saved {season}")
        lineup_rows.extend(season_rows)
        audit_rows.append(audit)

    if not SOURCE_LEAGUE_ORTG.is_file():
        raise FileNotFoundError(f"Missing reusable league baseline: {SOURCE_LEAGUE_ORTG}")
    source_league = pd.read_csv(SOURCE_LEAGUE_ORTG)
    wanted = {season_label(year) for year in range(FIRST_SEASON, LAST_SEASON + 1)}
    if set(source_league["Season"]) != wanted or source_league["Season"].duplicated().any():
        raise ValueError("Reusable league ORTG source does not contain exactly one row for all 26 seasons")
    # Across the full NBA, every offensive possession is also one opponent
    # defensive possession, so aggregate league ORTG equals aggregate DRTG.
    league = source_league.rename(columns={"LeagueORTG": "LeagueDRTG"})[["Season", "LeagueDRTG"]].copy()
    league["LeagueDRTG"] = league["LeagueDRTG"].astype(float)
    print("Reused the verified league ORTG table as league DRTG: full-league offense and defense are the same possession pool")

    lineups = pd.DataFrame(lineup_rows).sort_values(["Season", "SecondsPlayed"], ascending=[True, False], kind="stable")
    league = league.sort_values("Season", kind="stable")
    audit = pd.DataFrame(audit_rows).sort_values("Season", kind="stable")
    lineups.to_csv(LINEUP_SOURCE, index=False)
    league.to_csv(LEAGUE_SOURCE, index=False)
    audit.to_csv(FETCH_AUDIT, index=False)
    return lineups, league, audit


def load_source_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [path for path in (LINEUP_SOURCE, LEAGUE_SOURCE, FETCH_AUDIT) if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing source snapshots; run with --refresh: " + ", ".join(str(path) for path in missing))
    return pd.read_csv(LINEUP_SOURCE, dtype={"EntityId": str}), pd.read_csv(LEAGUE_SOURCE), pd.read_csv(FETCH_AUDIT)


def _source_names(value: str) -> set[str]:
    return {part.strip() for part in str(value).split(",") if part.strip()}


def _surname(value: str) -> str:
    surname = str(value).split()[-1]
    if surname in {"Jr.", "Sr.", "II", "III", "IV"}:
        surname = str(value).split()[-2]
    return surname.upper()


def ensure_historical_headshots(player_ids: list[int]) -> None:
    """Replace old NBA CDN silhouettes with stable external portraits."""
    for player_id in {int(value) for value in player_ids}:
        if PROJECT_HEADSHOT_OVERRIDES.get(player_id, Path()).is_file():
            continue
        url = HISTORICAL_HEADSHOT_URLS.get(player_id)
        if url is None:
            continue
        path = HEADSHOT_CACHE / f"{player_id}.png"
        if path.is_file() and path.stat().st_size >= MIN_USABLE_HEADSHOT_BYTES:
            continue
        response = requests.get(url, headers={"User-Agent": "@chicagobullsdata analytics archive"}, timeout=30)
        response.raise_for_status()
        if len(response.content) < MIN_USABLE_HEADSHOT_BYTES:
            raise ValueError(f"Fallback portrait for {player_id} is too small")
        path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(BytesIO(response.content)) as image:
            image.convert("RGBA").save(path, format="PNG")


def headshot_path(player_id: int) -> Path:
    """Return a project-specific portrait when one is part of this post."""
    return PROJECT_HEADSHOT_OVERRIDES.get(int(player_id), HEADSHOT_CACHE / f"{int(player_id)}.png")


def prepare_ranking(lineups: pd.DataFrame, league: pd.DataFrame, *, min_possessions: int = MIN_POSSESSIONS, top_n: int = TOP_N) -> pd.DataFrame:
    missing = LINEUP_REQUIRED - set(lineups)
    if missing:
        raise ValueError(f"Lineup source is missing columns: {sorted(missing)}")
    if set(league) < {"Season", "LeagueDRTG"}:
        raise ValueError("League source must contain Season and LeagueDRTG")
    if lineups.duplicated(["Season", "EntityId"]).any():
        raise ValueError("Duplicate season-lineup rows in pbpstats source")
    if league["Season"].duplicated().any():
        raise ValueError("Duplicate season rows in league DRTG source")

    merged = lineups.merge(league, on="Season", how="left", validate="many_to_one")
    numeric = ["OpponentPoints", "DefPoss", "SecondsPlayed", "LeagueDRTG"]
    if merged[numeric].isna().any().any():
        raise ValueError("A lineup is missing opponent points, possessions, time or baseline")
    if (merged["DefPoss"] <= 0).any():
        raise ValueError("Defensive possessions must be positive")

    merged["DRTG"] = 100 * merged["OpponentPoints"] / merged["DefPoss"]
    merged["rDRTG"] = merged["LeagueDRTG"] - merged["DRTG"]
    merged["Minutes"] = merged["SecondsPlayed"] / 60
    eligible = merged.loc[merged["DefPoss"] >= min_possessions].copy()
    if len(eligible) < top_n:
        raise ValueError(f"Only {len(eligible)} lineups reached {min_possessions} possessions; {top_n} are required.")
    rows = eligible.sort_values(["rDRTG", "DefPoss", "Season", "Name"], ascending=[False, False, True, True], kind="stable").head(top_n).reset_index(drop=True)
    rows.insert(0, "Rank", np.arange(1, len(rows) + 1))

    for index, row in rows.iterrows():
        key = (str(row["Season"]), str(row["EntityId"]))
        order = POSITION_ORDER.get(key)
        if order is None:
            raise ValueError(f"No PG-to-C display order recorded for {key}")
        if set(order) != _source_names(row["Name"]):
            raise ValueError(f"Position order does not match source names for {key}")
        source_pairs = dict(zip([part.strip() for part in str(row["Name"]).split(",")], str(row["EntityId"]).split("-")))
        for position, player in zip(POSITION_COLUMNS, order):
            rows.loc[index, position] = player
            rows.loc[index, f"{position}_LABEL"] = _surname(player)
            rows.loc[index, f"{position}_ID"] = int(source_pairs[player])

    if not rows["rDRTG"].is_monotonic_decreasing:
        raise ValueError("Selected lineups are not ordered by rDRTG")
    return rows


def write_top_ten(rows: pd.DataFrame) -> Path:
    columns = ["Rank", "Season", "EntityId", *POSITION_COLUMNS, "GamesPlayed", "Minutes", "DefPoss", "OpponentPoints", "DRTG", "LeagueDRTG", "rDRTG"]
    table = rows[columns].copy()
    for column in ["Minutes", "DRTG", "LeagueDRTG", "rDRTG"]:
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


def render_chart(rows: pd.DataFrame, *, final: bool = False) -> Path:
    theme = DEFAULT_THEME
    player_ids = [int(row[f"{position}_ID"]) for _, row in rows.iterrows() for position in POSITION_COLUMNS]
    ensure_historical_headshots(player_ids)
    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
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
        ax.plot([145, 903], [y, y], color=theme.accent, lw=1.2, solid_capstyle="round", zorder=1)
        ax.text(125, y + 32, str(row["Season"]), ha="right", va="center", fontsize=11, color=theme.muted, fontproperties=helvetica("bold_oblique"))
        for position in POSITION_COLUMNS:
            x = position_x[position]
            player_id = int(row[f"{position}_ID"])
            face_fraction = 0.80 if player_id == 213 else 0.72
            square_headshot_label(ax, headshot_path(player_id), x, y + 11, 49, zorder=3, face_fraction=face_fraction)
            ax.text(x, y - 56, row[f"{position}_LABEL"], ha="center", va="center", fontsize=7.4, color=theme.ink, fontproperties=helvetica("bold"), zorder=5)
        draw_metric_badge(
            ax, x_metric, y, _rating_label(row["rDRTG"]),
            f"{int(row['DefPoss']):,} POSS",
        )

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{POST_DATE}-bulls-lineup-rdrtg-top-10.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return path


def canva_copy_block(rows: pd.DataFrame) -> str:
    leader = rows.iloc[0]
    leader_names = " / ".join(str(leader[pos]) for pos in POSITION_COLUMNS)
    return "\n".join([
        "=== CANVA COPY (DATA-BOUND) ===", "",
        "TITLE: THE BULLS’ BEST DEFENSIVE LINEUPS SINCE 2000", "",
        "SUBTITLE: Chicago’s top five-man units by defensive rating relative to the NBA average that season", "",
        f"LEAD NOTE: {leader_names} ranked first at {_rating_label(leader['rDRTG'])} rDRTG.", "",
        f"QUALIFICATION: 2000-01 through 2025-26 regular seasons · Minimum {MIN_POSSESSIONS:,} defensive possessions", "",
        "METHOD: rDRTG = NBA points allowed per 100 possessions in the same season minus lineup points allowed per 100 possessions. Players are ordered PG to C by functional lineup role.", "",
        "SOURCE: pbpstats.com · Derived from NBA play-by-play", "",
        "HANDLE: @chicagobullsdata", "", "=== END CANVA COPY ===",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank Bulls five-man lineup defense relative to each season.")
    parser.add_argument("--refresh", action="store_true", help="Fetch and replace the tracked pbpstats source snapshots.")
    parser.add_argument("--final", action="store_true", help="Export the chart asset at publish resolution.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Accepted for CLI consistency; the post folder remains dated 2026-08-30.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lineups, league, audit = fetch_source_tables() if args.refresh else load_source_tables()
    if len(audit) != LAST_SEASON - FIRST_SEASON + 1:
        raise ValueError("Fetch audit does not contain all 26 seasons")
    rows = prepare_ranking(lineups, league)
    table_path = write_top_ten(rows)
    chart_path = render_chart(rows, final=args.final)
    print(rows[["Rank", "Season", *POSITION_COLUMNS, "DefPoss", "DRTG", "rDRTG"]].to_string(index=False))
    print(f"\nSource lineups: {LINEUP_SOURCE}\nLeague baselines: {LEAGUE_SOURCE}\nFetch audit: {FETCH_AUDIT}\nTop-ten table: {table_path}\nChart asset: {chart_path}")
    scale = 2 if args.final else 1
    print(f"Chart export: {CHART_WIDTH * scale}×{CHART_HEIGHT * scale} px\n")
    print(canva_copy_block(rows))


if __name__ == "__main__":
    main()
