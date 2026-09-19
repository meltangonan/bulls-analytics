"""Prepare Bulls single-season block leaders since 2000-01.

NBA.com LeagueDashPlayerStats supplies both the Chicago-only season totals and
the league population used for NBA rank.  The display ranks Bulls seasons by
blocks, then blocks per game, then the older season.  NBA rank is the standing
of the Chicago block total against every player's full-season total.
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


FIRST_SEASON = "2000-01"
LAST_SEASON = "2025-26"
POST = ROOT / "docs/visuals/2026-09-19-block-leaders"
DATA = POST / "data"
RAW = DATA / "raw"


def seasons(first: str = FIRST_SEASON, last: str = LAST_SEASON) -> list[str]:
    first_year = int(first[:4])
    last_year = int(last[:4])
    return [f"{year}-{str(year + 1)[-2:]}" for year in range(first_year, last_year + 1)]


def _raw_path(season: str, scope: str) -> Path:
    return RAW / f"{scope}-{season}.json"


def _frame_from_payload(payload: dict) -> pd.DataFrame:
    result = payload["resultSets"][0]
    return pd.DataFrame(result["rowSet"], columns=result["headers"])


def fetch_frame(season: str, *, team_id: int | None, refresh: bool = False) -> pd.DataFrame:
    scope = "bulls" if team_id else "league"
    path = _raw_path(season, scope)
    if path.exists() and not refresh:
        return _frame_from_payload(json.loads(path.read_text()))

    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="Totals",
        team_id_nullable=team_id,
        timeout=60,
        headers=_NBA_HEADERS,
    )
    payload = endpoint.get_dict()
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")))
    time.sleep(0.6)
    return _frame_from_payload(payload)


def nba_rank(blocks: int, league_blocks: pd.Series) -> int:
    """Competition rank of a block total; tied totals share a rank."""
    values = pd.to_numeric(league_blocks, errors="raise")
    return int((values > blocks).sum() + 1)


def prepare_season(season: str, bulls: pd.DataFrame, league: pd.DataFrame) -> pd.DataFrame:
    required = {"PLAYER_ID", "PLAYER_NAME", "GP", "BLK"}
    for label, frame in (("Bulls", bulls), ("league", league)):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{season} {label} frame is missing {sorted(missing)}")

    result = bulls[["PLAYER_ID", "PLAYER_NAME", "GP", "BLK"]].copy()
    result["season"] = season
    result["player_id"] = pd.to_numeric(result.pop("PLAYER_ID"), errors="raise").astype(int)
    result["player_name"] = result.pop("PLAYER_NAME")
    result["games"] = pd.to_numeric(result.pop("GP"), errors="raise").astype(int)
    result["blocks"] = pd.to_numeric(result.pop("BLK"), errors="raise").astype(int)
    if (result["games"] <= 0).any():
        raise ValueError(f"{season} contains a non-positive games value")
    result["blocks_per_game"] = result["blocks"] / result["games"]
    result["nba_rank"] = [nba_rank(value, league["BLK"]) for value in result["blocks"]]
    league_lookup = league.set_index("PLAYER_ID")
    result["league_full_season_blocks"] = result["player_id"].map(league_lookup["BLK"])
    result["nba_rank_endpoint"] = result["player_id"].map(league_lookup["BLK_RANK"])
    return result


def select_top15(all_rows: pd.DataFrame) -> pd.DataFrame:
    ordered = all_rows.sort_values(
        ["blocks", "blocks_per_game", "season"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    selected = ordered.head(15).copy()
    selected.insert(0, "display_rank", range(1, 16))
    return selected


def build(*, refresh: bool = False) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    audits: list[dict[str, int | str]] = []
    for season in seasons():
        bulls = fetch_frame(season, team_id=BULLS_TEAM_ID, refresh=refresh)
        league = fetch_frame(season, team_id=None, refresh=refresh)
        prepared = prepare_season(season, bulls, league)
        rows.append(prepared)
        audits.append({
            "season": season,
            "bulls_player_rows": len(bulls),
            "bulls_blocks": int(pd.to_numeric(bulls["BLK"]).sum()),
            "league_player_rows": len(league),
        })
        print(f"{season}: {len(bulls)} Bulls rows, {len(league)} league rows")

    all_rows = pd.concat(rows, ignore_index=True)
    selected = select_top15(all_rows)
    if not selected["blocks"].eq(selected["league_full_season_blocks"]).all():
        raise ValueError("A selected Bulls total differs from that player's full-season total")
    if not selected["nba_rank"].eq(selected["nba_rank_endpoint"]).all():
        raise ValueError("A selected calculated NBA rank differs from NBA.com's rank")
    cutoff = selected.iloc[-1]
    selected_keys = set(zip(selected["season"], selected["player_id"]))
    tied_out = all_rows.loc[
        (all_rows["blocks"] == cutoff["blocks"])
        & ~pd.Series(
            [(season, player_id) in selected_keys
             for season, player_id in zip(all_rows["season"], all_rows["player_id"])],
            index=all_rows.index,
        )
    ]

    DATA.mkdir(parents=True, exist_ok=True)
    all_rows.to_csv(DATA / "bulls_player_seasons.csv", index=False)
    selected.to_csv(DATA / "top15.csv", index=False)
    selected[[
        "season", "player_id", "player_name", "blocks",
        "league_full_season_blocks", "nba_rank", "nba_rank_endpoint",
    ]].to_csv(DATA / "selection_audit.csv", index=False)
    pd.DataFrame(audits).to_csv(DATA / "season_audit.csv", index=False)
    (DATA / "source.json").write_text(json.dumps({
        "endpoint": "LeagueDashPlayerStats",
        "parameters": {
            "season_type_all_star": "Regular Season",
            "per_mode_detailed": "Totals",
            "bulls_team_id": BULLS_TEAM_ID,
        },
        "window": f"{FIRST_SEASON} through {LAST_SEASON}",
        "ranking": "blocks desc, blocks_per_game desc, older season",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "cutoff_blocks": int(cutoff["blocks"]),
        "cutoff_ties_outside_table": tied_out[
            ["season", "player_name", "blocks", "blocks_per_game"]
        ].to_dict("records"),
    }, indent=2))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    selected = build(refresh=args.refresh)
    print(selected[["display_rank", "season", "player_name", "blocks", "nba_rank", "blocks_per_game"]].to_string(index=False))


if __name__ == "__main__":
    main()
