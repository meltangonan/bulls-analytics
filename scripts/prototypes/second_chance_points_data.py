"""Prepare Bulls single-season second chance points leaders since 1996-97.

NBA.com LeagueDashPlayerStats (MeasureType=Misc) supplies PTS_2ND_CHANCE, a player's
second chance points (NBA.com: "Second Chance Points").  The Misc series begins in 1996-97;
earlier seasons return no rows, so they are unavailable rather than zero.
Chicago-only requests keep a traded player's Bulls portion; the league request
supplies the population for NBA rank.  The Base measure supplies total points,
the denominator for the share of the player's points (NBA.com publishes no share for this stat, so it is derived only).

Display order: second chance points, then per game, then the older season.
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


STAT = "PTS_2ND_CHANCE"
PUBLISHED_SHARE = None  # NBA.com Scoring-measure share, used as a check when it exists
FIRST_SEASON = "1996-97"
LAST_SEASON = "2025-26"
POST = ROOT / "docs/visuals/2026-09-29-second-chance-points"
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


def prepare_season(season: str, misc: pd.DataFrame, base: pd.DataFrame,
                   league: pd.DataFrame, scoring: pd.DataFrame | None = None) -> pd.DataFrame:
    for label, frame, cols in (
        ("Bulls Misc", misc, {"PLAYER_ID", "PLAYER_NAME", "GP", STAT}),
        ("Bulls Base", base, {"PLAYER_ID", "PTS"}),
        ("league Misc", league, {"PLAYER_ID", STAT, f"{STAT}_RANK"}),
    ):
        missing = cols - set(frame.columns)
        if missing:
            raise ValueError(f"{season} {label} frame is missing {sorted(missing)}")
    if set(misc["PLAYER_ID"]) != set(base["PLAYER_ID"]):
        raise ValueError(f"{season} Misc and Base cover different Bulls players")

    result = pd.DataFrame({
        "season": season,
        "player_id": pd.to_numeric(misc["PLAYER_ID"], errors="raise").astype(int),
        "player_name": misc["PLAYER_NAME"],
        "games": pd.to_numeric(misc["GP"], errors="raise").astype(int),
        "points": pd.to_numeric(misc[STAT], errors="raise").round().astype(int),
    })
    if (result["games"] <= 0).any():
        raise ValueError(f"{season} contains a non-positive games value")
    result["points_per_game"] = result["points"] / result["games"]
    total = result["player_id"].map(base.set_index("PLAYER_ID")["PTS"]).astype(float)
    result["total_points"] = total
    result["share_of_points"] = (result["points"] / total).where(total > 0)
    if scoring is not None and PUBLISHED_SHARE:
        result["published_share"] = result["player_id"].map(
            scoring.set_index("PLAYER_ID")[PUBLISHED_SHARE])
    result["nba_rank"] = [nba_rank(v, league[STAT]) for v in result["points"]]
    league_lookup = league.set_index("PLAYER_ID")
    result["league_full_season_points"] = result["player_id"].map(league_lookup[STAT])
    result["nba_rank_endpoint"] = result["player_id"].map(league_lookup[f"{STAT}_RANK"])
    return result


def select_top15(all_rows: pd.DataFrame) -> pd.DataFrame:
    ordered = all_rows.sort_values(
        ["points", "points_per_game", "season"],
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
        base = fetch_frame(season, "Base", team_id=BULLS_TEAM_ID, refresh=refresh)
        league = fetch_frame(season, "Misc", team_id=None, refresh=refresh)
        scoring = (fetch_frame(season, "Scoring", team_id=BULLS_TEAM_ID, refresh=refresh)
                   if PUBLISHED_SHARE else None)
        if misc.empty or league.empty:
            raise ValueError(f"{season} returned no rows; the window must start where {STAT} exists")
        if pd.to_numeric(league[STAT]).isna().any() or pd.to_numeric(league[STAT]).sum() <= 0:
            raise ValueError(f"{season} league {STAT} is missing or zero")
        rows.append(prepare_season(season, misc, base, league, scoring))
        audits.append({
            "season": season,
            "bulls_player_rows": len(misc),
            "bulls_points": int(pd.to_numeric(misc[STAT]).sum()),
            "league_player_rows": len(league),
            "league_points": int(pd.to_numeric(league[STAT]).sum()),
        })
        print(f"{season}: {len(misc)} Bulls rows, {len(league)} league rows")

    all_rows = pd.concat(rows, ignore_index=True)
    selected = select_top15(all_rows)
    traded = selected["points"].ne(selected["league_full_season_points"])
    if not selected.loc[~traded, "nba_rank"].eq(selected.loc[~traded, "nba_rank_endpoint"]).all():
        raise ValueError("A selected calculated NBA rank differs from NBA.com's rank")
    share_check = None
    if PUBLISHED_SHARE:
        diff = (selected["share_of_points"] - selected["published_share"]).abs()
        share_check = float(diff.max())
        if share_check > 0.0006:
            raise ValueError(f"Derived share differs from NBA.com {PUBLISHED_SHARE} by {share_check}")

    cutoff = selected.iloc[-1]
    keys = set(zip(selected["season"], selected["player_id"]))
    outside = pd.Series([(s, p) not in keys for s, p in zip(all_rows["season"], all_rows["player_id"])],
                        index=all_rows.index)
    tied_out = all_rows.loc[(all_rows["points"] == cutoff["points"]) & outside]

    DATA.mkdir(parents=True, exist_ok=True)
    all_rows.to_csv(DATA / "bulls_player_seasons.csv", index=False)
    selected.to_csv(DATA / "top15.csv", index=False)
    selected.assign(traded_mid_season=traded)[[
        "season", "player_id", "player_name", "points", "league_full_season_points",
        "traded_mid_season", "nba_rank", "nba_rank_endpoint",
    ]].to_csv(DATA / "selection_audit.csv", index=False)
    pd.DataFrame(audits).to_csv(DATA / "season_audit.csv", index=False)
    (DATA / "source.json").write_text(json.dumps({
        "endpoint": "LeagueDashPlayerStats",
        "measures": {
            "Misc": f"{STAT} (Bulls and league)",
            "Base": "PTS (Bulls), share denominator",
            **({"Scoring": f"{PUBLISHED_SHARE} (Bulls), share check"} if PUBLISHED_SHARE else {}),
        },
        "parameters": {
            "season_type_all_star": "Regular Season",
            "per_mode_detailed": "Totals",
            "bulls_team_id": BULLS_TEAM_ID,
        },
        "window": f"{FIRST_SEASON} through {LAST_SEASON}; 1995-96 and earlier return no rows",
        "ranking": "points desc, points_per_game desc, older season",
        "share_of_points": f"{STAT} / Base PTS",
        "share_max_abs_diff_vs_published": share_check,
        "nba_rank": "Bulls total against every player's full-season league total",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cutoff_points": int(cutoff["points"]),
        "cutoff_ties_outside_table": tied_out[
            ["season", "player_name", "points", "points_per_game"]
        ].to_dict("records"),
    }, indent=2))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    selected = build(refresh=args.refresh)
    print(selected[[
        "display_rank", "season", "player_name", "games", "points", "nba_rank",
        "points_per_game", "share_of_points",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
