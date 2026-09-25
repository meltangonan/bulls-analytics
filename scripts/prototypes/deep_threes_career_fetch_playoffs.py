"""Snapshot NBA playoff shots and Bulls player totals for the deep-threes post.

Only seasons in which Chicago played a postseason game are requested. The
league-wide shot responses also supply the matching playoff comparison rate.
Reruns reuse successful saved responses.
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import pandas as pd
from nba_api.stats.endpoints import (
    leaguedashplayerstats, leaguedashteamstats, leaguegamefinder, shotchartdetail,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bulls.data.fetch import _NBA_HEADERS
from scripts.prototypes.deep_threes_career_data import PLAYOFF_SEASONS


DATA = ROOT / "docs/visuals/2026-09-25-deep-threes-career/data/raw"
BULLS_ID = 1610612741


def verify_playoff_seasons() -> None:
    path = DATA / "bulls-playoff-games.csv.gz"
    if path.exists():
        games = pd.read_csv(path)
    else:
        games = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=BULLS_ID, season_type_nullable="Playoffs",
            timeout=60, headers=_NBA_HEADERS,
        ).get_data_frames()[0]
        games = games.loc[games.GAME_DATE.between("1996-10-01", "2026-08-01")].copy()
        path.parent.mkdir(parents=True, exist_ok=True)
        games.to_csv(path, index=False, compression="gzip")
    discovered = {
        f"{int(date[:4]) - 1}-{int(date[:4]) % 100:02d}"
        for date in games.GAME_DATE
    }
    if discovered != set(PLAYOFF_SEASONS):
        raise ValueError(f"Bulls playoff season list disagrees with LeagueGameFinder: {discovered}")


def fetch_once(season: str) -> None:
    shots_path = DATA / "league-playoff-shots" / f"{season}.csv.gz"
    totals_path = DATA / "bulls-playoff-totals" / f"{season}.csv.gz"
    league_totals_path = DATA / "league-playoff-team-totals" / f"{season}.csv.gz"
    shots_path.parent.mkdir(parents=True, exist_ok=True)
    totals_path.parent.mkdir(parents=True, exist_ok=True)
    league_totals_path.parent.mkdir(parents=True, exist_ok=True)

    if not shots_path.exists():
        shots = shotchartdetail.ShotChartDetail(
            team_id=0, player_id=0, season_nullable=season,
            season_type_all_star="Playoffs", context_measure_simple="FGA",
            timeout=60, headers=_NBA_HEADERS,
        ).get_data_frames()[0]
        if shots.empty or not shots.TEAM_ID.eq(BULLS_ID).any():
            raise ValueError(f"{season}: league shot response lacks Chicago")
        shots.to_csv(shots_path, index=False, compression="gzip")
        print(f"{season}: saved {len(shots):,} league playoff shots", flush=True)

    if not totals_path.exists():
        totals = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, season_type_all_star="Playoffs",
            team_id_nullable=BULLS_ID, per_mode_detailed="Totals",
            measure_type_detailed_defense="Base", timeout=60,
            headers=_NBA_HEADERS,
        ).get_data_frames()[0]
        if totals.empty:
            raise ValueError(f"{season}: no Bulls playoff player totals")
        totals.to_csv(totals_path, index=False, compression="gzip")
        print(f"{season}: saved {len(totals)} Bulls player totals", flush=True)

    if not league_totals_path.exists():
        league_totals = leaguedashteamstats.LeagueDashTeamStats(
            season=season, season_type_all_star="Playoffs",
            per_mode_detailed="Totals", measure_type_detailed_defense="Base",
            timeout=60, headers=_NBA_HEADERS,
        ).get_data_frames()[0]
        if league_totals.empty:
            raise ValueError(f"{season}: no league playoff team totals")
        league_totals.to_csv(league_totals_path, index=False, compression="gzip")
        print(f"{season}: saved {len(league_totals)} league team totals", flush=True)


def main() -> None:
    verify_playoff_seasons()
    for season in PLAYOFF_SEASONS:
        for attempt in range(3):
            try:
                fetch_once(season)
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                print(f"{season}: {type(exc).__name__}; retrying", flush=True)
                time.sleep(2 * (attempt + 1))
        time.sleep(0.4)


if __name__ == "__main__":
    main()
