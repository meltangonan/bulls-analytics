"""Bulls career distance run, in marathons, since player tracking began (2013-14).

Source: NBA.com ``LeagueDashPtStats`` SpeedDistance totals, Bulls team filter, for regular
season, playoffs and play-in. Raw responses are snapshotted under ``data/raw``; reruns use the
snapshot unless ``--refresh`` is passed.

Checks: every season has regular-season rows, and each season type's player miles reconcile to
the team-level total. Team-filtered rows can carry a player's *last* team abbreviation (Coby White
2025-26 is stamped CHA), so rows are never re-filtered by abbreviation.

Speed is NBA.com's AVG_SPEED weighted by minutes. Miles divided by minutes disagrees with it by a
season-dependent offset (about +0.27 mph in 2018-19 to 2023-24), so it is not recomputed here.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/visuals/2026-10-04-bulls-miles-marathons/data'
RAW = DATA / 'raw'
CHI = 1610612741
MARATHON_MILES = 26.2
SEASONS = [f'{y}-{str(y + 1)[2:]}' for y in range(2013, 2026)]
SEASON_TYPES = ['Regular Season', 'Playoffs', 'PlayIn']
TOP_N = 15


def _fetch(season: str, season_type: str, level: str) -> pd.DataFrame:
    from nba_api.stats.endpoints import leaguedashptstats

    for attempt in range(3):
        try:
            return leaguedashptstats.LeagueDashPtStats(
                season=season, season_type_all_star=season_type,
                pt_measure_type='SpeedDistance', per_mode_simple='Totals',
                player_or_team=level, team_id_nullable=CHI, timeout=60,
            ).get_data_frames()[0]
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3)


def load(refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = {'Player': [], 'Team': []}
    for season in SEASONS:
        for season_type in SEASON_TYPES:
            for level in frames:
                path = RAW / f'{level.lower()}-{season}-{season_type.lower().replace(" ", "-")}.csv'
                if refresh or not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    _fetch(season, season_type, level).to_csv(path, index=False)
                    time.sleep(0.6)
                df = pd.read_csv(path)
                df['SEASON'], df['SEASON_TYPE'] = season, season_type
                frames[level].append(df)
    players, teams = (pd.concat(frames[k], ignore_index=True) for k in ('Player', 'Team'))
    if 'TEAM_ID' in teams:
        teams = teams[teams.TEAM_ID == CHI]
    return players, teams


def coverage(players: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    p = players.groupby(['SEASON', 'SEASON_TYPE']).agg(
        players=('PLAYER_ID', 'size'), player_miles=('DIST_MILES', 'sum'))
    t = teams.groupby(['SEASON', 'SEASON_TYPE']).agg(team_miles=('DIST_MILES', 'sum'))
    cov = p.join(t, how='outer').fillna(0).reset_index()
    missing = set(SEASONS) - set(cov[(cov.SEASON_TYPE == 'Regular Season') & (cov.players > 0)].SEASON)
    if missing:
        raise ValueError(f'No regular-season tracking rows for {sorted(missing)}')
    # Player rows are rounded to 0.1 mile, so allow rounding drift across a roster.
    cov['diff'] = cov.player_miles - cov.team_miles
    bad = cov[cov['diff'].abs() > 0.05 * cov.players + 0.1]
    if not bad.empty:
        raise ValueError(f'Player miles do not reconcile to team miles:\n{bad}')
    return cov


def leaderboard(players: pd.DataFrame) -> pd.DataFrame:
    p = players.assign(speed_x_min=players.AVG_SPEED * players.MIN)
    c = p.groupby('PLAYER_ID').agg(
        player=('PLAYER_NAME', 'last'), first_season=('SEASON', 'min'),
        last_season=('SEASON', 'max'), games=('GP', 'sum'), minutes=('MIN', 'sum'),
        miles=('DIST_MILES', 'sum'), speed_x_min=('speed_x_min', 'sum')).reset_index()
    c['marathons'] = c.miles / MARATHON_MILES
    c['avg_mph'] = c.speed_x_min / c.minutes
    c = c.drop(columns='speed_x_min').sort_values('miles', ascending=False, ignore_index=True)
    c.insert(0, 'rank', range(1, len(c) + 1))
    return c


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true', help='refetch NBA.com snapshots')
    args = parser.parse_args()
    players, teams = load(args.refresh)
    coverage(players, teams).round(2).to_csv(DATA / 'coverage.csv', index=False)
    board = leaderboard(players)
    board.round(3).to_csv(DATA / 'career-all.csv', index=False)
    top = board.head(TOP_N).copy()
    top[['miles', 'marathons', 'avg_mph']] = top[['miles', 'marathons', 'avg_mph']].round(
        {'miles': 1, 'marathons': 1, 'avg_mph': 2})
    top.to_csv(DATA / f'top{TOP_N}.csv', index=False)
    print(top.to_string(index=False))


if __name__ == '__main__':
    main()
