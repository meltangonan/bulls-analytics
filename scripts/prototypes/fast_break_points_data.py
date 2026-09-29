"""Prepare Bulls single-season fast-break points leaders since 1996-97.

NBA.com LeagueDashPlayerStats (MeasureType=Misc) supplies PTS_FB, the points a
player scored on possessions the league's scorers flagged as fast breaks.  The
series begins in 1996-97; earlier seasons return no rows, so they are
unavailable rather than zero.  Chicago-only requests keep a traded player's
Bulls portion; the league request supplies the population for NBA rank.  The
Scoring measure adds the published share of the player's points that came on
fast breaks (PCT_PTS_FB).

Display order: fast-break points, then fast-break points per game, then the
older season.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS


FIRST_SEASON = "1996-97"
LAST_SEASON = "2025-26"
POST = ROOT / "docs/visuals/2026-09-29-fast-break-points"
DATA = POST / "data"
RAW = DATA / "raw"


def seasons(first: str = FIRST_SEASON, last: str = LAST_SEASON) -> list[str]:
    return [f"{year}-{str(year + 1)[-2:]}" for year in range(int(first[:4]), int(last[:4]) + 1)]


def _frame_from_payload(payload: dict) -> pd.DataFrame:
    result = payload["resultSets"][0]
    return pd.DataFrame(result["rowSet"], columns=result["headers"])


def fetch_frame(season: str, measure: str, *, team_id: int | None,
                refresh: bool = False) -> pd.DataFrame:
    scope = "bulls" if team_id else "league"
    path = RAW / f"{measure.lower()}-{scope}-{season}.json"
    if path.exists() and not refresh:
        return _frame_from_payload(json.loads(path.read_text()))

    payload = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense=measure,
        per_mode_detailed="Totals",
        team_id_nullable=team_id,
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_dict()
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")))
    time.sleep(0.6)
    return _frame_from_payload(payload)


def nba_rank(points: int, league_points: pd.Series) -> int:
    """Competition rank of a total; tied totals share a rank."""
    return int((pd.to_numeric(league_points, errors="raise") > points).sum() + 1)


def prepare_season(season: str, misc: pd.DataFrame, scoring: pd.DataFrame,
                   league: pd.DataFrame) -> pd.DataFrame:
    for label, frame, cols in (
        ("Bulls Misc", misc, {"PLAYER_ID", "PLAYER_NAME", "GP", "PTS_FB"}),
        ("Bulls Scoring", scoring, {"PLAYER_ID", "PCT_PTS_FB", "FG_PCT"}),
        ("league Misc", league, {"PLAYER_ID", "PTS_FB", "PTS_FB_RANK"}),
    ):
        missing = cols - set(frame.columns)
        if missing:
            raise ValueError(f"{season} {label} frame is missing {sorted(missing)}")
    if set(misc["PLAYER_ID"]) != set(scoring["PLAYER_ID"]):
        raise ValueError(f"{season} Misc and Scoring cover different Bulls players")

    result = pd.DataFrame({
        "season": season,
        "player_id": pd.to_numeric(misc["PLAYER_ID"], errors="raise").astype(int),
        "player_name": misc["PLAYER_NAME"],
        "games": pd.to_numeric(misc["GP"], errors="raise").astype(int),
        "fast_break_points": pd.to_numeric(misc["PTS_FB"], errors="raise").round().astype(int),
    })
    if (result["games"] <= 0).any():
        raise ValueError(f"{season} contains a non-positive games value")
    result["fast_break_points_per_game"] = result["fast_break_points"] / result["games"]
    scoring_lookup = scoring.set_index("PLAYER_ID")
    result["share_of_points"] = result["player_id"].map(scoring_lookup["PCT_PTS_FB"])
    result["fg_pct_overall"] = result["player_id"].map(scoring_lookup["FG_PCT"])
    result["nba_rank"] = [nba_rank(v, league["PTS_FB"]) for v in result["fast_break_points"]]
    league_lookup = league.set_index("PLAYER_ID")
    result["league_full_season_fast_break_points"] = result["player_id"].map(league_lookup["PTS_FB"])
    result["nba_rank_endpoint"] = result["player_id"].map(league_lookup["PTS_FB_RANK"])
    return result


def select_top15(all_rows: pd.DataFrame) -> pd.DataFrame:
    ordered = all_rows.sort_values(
        ["fast_break_points", "fast_break_points_per_game", "season"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    selected = ordered.head(15).copy()
    selected.insert(0, "display_rank", range(1, len(selected) + 1))
    return selected


def build(*, refresh: bool = False) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    audits: list[dict[str, int | str]] = []
    for season in seasons():
        misc = fetch_frame(season, "Misc", team_id=BULLS_TEAM_ID, refresh=refresh)
        scoring = fetch_frame(season, "Scoring", team_id=BULLS_TEAM_ID, refresh=refresh)
        league = fetch_frame(season, "Misc", team_id=None, refresh=refresh)
        if misc.empty or league.empty:
            raise ValueError(f"{season} returned no rows; the window must start where PTS_FB exists")
        rows.append(prepare_season(season, misc, scoring, league))
        audits.append({
            "season": season,
            "bulls_player_rows": len(misc),
            "bulls_fast_break_points": int(pd.to_numeric(misc["PTS_FB"]).sum()),
            "league_player_rows": len(league),
            "league_fast_break_points": int(pd.to_numeric(league["PTS_FB"]).sum()),
        })
        print(f"{season}: {len(misc)} Bulls rows, {len(league)} league rows")

    all_rows = pd.concat(rows, ignore_index=True)
    selected = select_top15(all_rows)
    traded = selected["fast_break_points"].ne(selected["league_full_season_fast_break_points"])
    if not selected.loc[~traded, "nba_rank"].eq(selected.loc[~traded, "nba_rank_endpoint"]).all():
        raise ValueError("A selected calculated NBA rank differs from NBA.com's rank")

    cutoff = selected.iloc[-1]
    keys = set(zip(selected["season"], selected["player_id"]))
    outside = pd.Series([(s, p) not in keys for s, p in zip(all_rows["season"], all_rows["player_id"])],
                        index=all_rows.index)
    tied_out = all_rows.loc[(all_rows["fast_break_points"] == cutoff["fast_break_points"]) & outside]

    DATA.mkdir(parents=True, exist_ok=True)
    all_rows.to_csv(DATA / "bulls_player_seasons.csv", index=False)
    selected.to_csv(DATA / "top15.csv", index=False)
    selected.assign(traded_mid_season=traded)[[
        "season", "player_id", "player_name", "fast_break_points",
        "league_full_season_fast_break_points", "traded_mid_season",
        "nba_rank", "nba_rank_endpoint",
    ]].to_csv(DATA / "selection_audit.csv", index=False)
    pd.DataFrame(audits).to_csv(DATA / "season_audit.csv", index=False)
    (DATA / "source.json").write_text(json.dumps({
        "endpoint": "LeagueDashPlayerStats",
        "measures": {"Misc": "PTS_FB (Bulls and league)", "Scoring": "PCT_PTS_FB, FG_PCT (Bulls)"},
        "parameters": {
            "season_type_all_star": "Regular Season",
            "per_mode_detailed": "Totals",
            "bulls_team_id": BULLS_TEAM_ID,
        },
        "window": f"{FIRST_SEASON} through {LAST_SEASON}; 1995-96 and earlier return no rows",
        "ranking": "fast_break_points desc, fast_break_points_per_game desc, older season",
        "nba_rank": "Bulls total against every player's full-season league total",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cutoff_fast_break_points": int(cutoff["fast_break_points"]),
        "cutoff_ties_outside_table": tied_out[
            ["season", "player_name", "fast_break_points", "fast_break_points_per_game"]
        ].to_dict("records"),
    }, indent=2))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    selected = build(refresh=args.refresh)
    print(selected[[
        "display_rank", "season", "player_name", "games", "fast_break_points", "nba_rank",
        "fast_break_points_per_game", "share_of_points", "fg_pct_overall",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
