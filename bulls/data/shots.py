"""Cached shot-location inputs for the shot-chart family.

Shot charts re-render many times while a design is iterated, and the league
baseline costs 30 API calls. Everything here caches to ``cache/shot_charts/`` so
only the first build pays for the fetch.

Player pulls deliberately pass ``team_id=0``: a player's season follows him
across trades, so scoping to one team silently returns nothing for anyone who
moved. That mistake is invisible in the output -- an empty chart looks like a
player who never shot -- so the team-agnostic default is the safe one.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bulls.config import BULLS_TEAM_ID, CURRENT_SEASON
from bulls.data import fetch

CACHE = Path(__file__).resolve().parents[2] / "cache" / "shot_charts"
SHOT_COLUMNS = ["loc_x", "loc_y", "shot_distance", "shot_made", "shot_type"]


def player_shots(player_id: int, season: str = CURRENT_SEASON,
                 refresh: bool = False) -> pd.DataFrame:
    """One player's full season of shots, wherever he played."""
    path = CACHE / f"player_{player_id}_{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = fetch.get_player_shots(player_id, team_id=0, season=season)
    df = df[SHOT_COLUMNS] if not df.empty else pd.DataFrame(columns=SHOT_COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def team_shots(team_id: int = BULLS_TEAM_ID, season: str = CURRENT_SEASON,
               refresh: bool = False) -> pd.DataFrame:
    """Every shot the team took, by whoever took it.

    Traded players are kept deliberately, which is the opposite of the roster
    filter most posts want. This is the team's *offence*: a shot taken in a
    Bulls uniform in November belongs to the team's shot profile whether or not
    the man who took it is still here.
    """
    path = CACHE / f"team_{team_id}_{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = fetch.get_team_shots(team_id=team_id, season=season)
    df = df[SHOT_COLUMNS] if not df.empty else pd.DataFrame(columns=SHOT_COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def league_shots(season: str = CURRENT_SEASON, refresh: bool = False) -> pd.DataFrame:
    """Every shot from all 30 teams -- the baseline every comparison uses."""
    path = CACHE / f"league_{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = fetch.get_league_shots(season=season)[SHOT_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def league_possessions(season: str = CURRENT_SEASON, refresh: bool = False) -> float:
    """Total league player-possessions, for per-75 rate comparisons.

    Derived per player as ``FGA_total / (FGA per 100) * 100`` and summed, which
    counts each of the five on-court players separately -- the right denominator
    for comparing one player's per-75 rate against a league-average player.
    """
    path = CACHE / f"league_possessions_{season}.txt"
    if path.exists() and not refresh:
        return float(path.read_text().strip())

    from nba_api.stats.endpoints import leaguedashplayerstats

    def pull(mode: str) -> pd.DataFrame:
        return leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, season_type_all_star="Regular Season",
            per_mode_detailed=mode, timeout=60, headers=fetch._NBA_HEADERS,
        ).get_data_frames()[0][["PLAYER_ID", "FGA"]]

    merged = pull("Totals").merge(pull("Per100Possessions"), on="PLAYER_ID",
                                  suffixes=("_total", "_per100"))
    merged = merged[merged.FGA_per100 > 0]
    total = float((merged.FGA_total / merged.FGA_per100 * 100).sum())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(total))
    return total


def player_possessions(player_id: int, season: str = CURRENT_SEASON) -> float:
    """One player's on-court possessions, for his per-75 rates."""
    from nba_api.stats.endpoints import leaguedashplayerstats

    frames = {}
    for mode in ("Totals", "Per100Possessions"):
        df = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, season_type_all_star="Regular Season",
            per_mode_detailed=mode, timeout=60, headers=fetch._NBA_HEADERS,
        ).get_data_frames()[0]
        row = df[df.PLAYER_ID == player_id]
        if row.empty:
            raise ValueError(f"No {season} row for player {player_id}")
        frames[mode] = float(row.iloc[0].FGA)
    if frames["Per100Possessions"] <= 0:
        raise ValueError(f"Player {player_id} has no attempts in {season}")
    return frames["Totals"] / frames["Per100Possessions"] * 100
