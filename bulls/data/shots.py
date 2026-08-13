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


def _team_possession_table(season: str, refresh: bool) -> pd.DataFrame:
    """Every team's season possessions, by the same Totals / Per100 identity.

    Cached as one table because both team figures a chart needs -- one club's
    possessions and all thirty clubs' -- come from the same two calls.
    """
    path = CACHE / f"team_possessions_{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)

    from nba_api.stats.endpoints import leaguedashteamstats

    def pull(mode: str) -> pd.DataFrame:
        return leaguedashteamstats.LeagueDashTeamStats(
            season=season, season_type_all_star="Regular Season",
            per_mode_detailed=mode, timeout=60, headers=fetch._NBA_HEADERS,
        ).get_data_frames()[0][["TEAM_ID", "FGA"]]

    merged = pull("Totals").merge(pull("Per100Possessions"), on="TEAM_ID",
                                  suffixes=("_total", "_per100"))
    merged = merged[merged.FGA_per100 > 0]
    merged["possessions"] = merged.FGA_total / merged.FGA_per100 * 100
    out = merged[["TEAM_ID", "possessions"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    return out


def team_possessions(team_id: int = BULLS_TEAM_ID, season: str = CURRENT_SEASON,
                     refresh: bool = False) -> float:
    """One team's season possessions, for its per-75 rates.

    A team rate and a player rate are different denominators and must not be
    compared with each other: five players share every team possession, so the
    Bulls take roughly five times a rotation player's attempts from the same
    floor time. Each is only ever measured against its own baseline --
    ``team_possessions`` against ``league_team_possessions``, ``player_possessions``
    against ``league_possessions`` -- which is what keeps the two charts' *deltas*
    on the same scale even though their raw rates are not.
    """
    table = _team_possession_table(season, refresh)
    row = table[table.TEAM_ID == team_id]
    if row.empty:
        raise ValueError(f"No {season} possessions for team {team_id}")
    return float(row.iloc[0].possessions)


def league_team_possessions(season: str = CURRENT_SEASON,
                            refresh: bool = False) -> float:
    """All thirty teams' possessions summed -- the team-level league baseline."""
    return float(_team_possession_table(season, refresh).possessions.sum())


def _player_possession_table(season: str, refresh: bool) -> pd.DataFrame:
    """Every player's season possessions, cached as one table.

    The two endpoint calls return the whole league either way, so asking per
    player threw away 499 rows and paid for them again on the next player. A
    carousel of ten made twenty rate-limited calls where two would do, and that
    is what made it time out rather than merely run slowly.
    """
    path = CACHE / f"player_possessions_{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)

    from nba_api.stats.endpoints import leaguedashplayerstats

    def pull(mode: str) -> pd.DataFrame:
        return leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, season_type_all_star="Regular Season",
            per_mode_detailed=mode, timeout=60, headers=fetch._NBA_HEADERS,
        ).get_data_frames()[0][["PLAYER_ID", "FGA"]]

    merged = pull("Totals").merge(pull("Per100Possessions"), on="PLAYER_ID",
                                  suffixes=("_total", "_per100"))
    merged = merged[merged.FGA_per100 > 0]
    merged["possessions"] = merged.FGA_total / merged.FGA_per100 * 100
    out = merged[["PLAYER_ID", "possessions"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    return out


def player_possessions(player_id: int, season: str = CURRENT_SEASON,
                       refresh: bool = False) -> float:
    """One player's on-court possessions, for his per-75 rates."""
    table = _player_possession_table(season, refresh)
    row = table[table.PLAYER_ID == player_id]
    if row.empty:
        raise ValueError(f"No {season} possessions for player {player_id}")
    return float(row.iloc[0].possessions)
