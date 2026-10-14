"""Estimate Bulls career miles since the 1976 merger, beyond the tracking era.

Tracking (2013-14 on) measures distance; earlier seasons have only minutes. For each player:

* tracked seasons use measured miles from ``data/raw`` (``bulls_miles_marathons_data.py``);
* untracked seasons (1976-77 to 2012-13) use Bulls minutes x one rate for every player: the NBA
  average miles per player-minute across all tracked regular seasons (2013-14 to 2025-26).

One rule for everyone, chosen by the user for defensibility over fine-tuning: no player gets his own
pace and no seasons are hand-picked. Ranges use the 10th and 90th percentile of NBA player-season
rates (500+ regular-season minutes) over the same seasons, applied to untracked minutes only. They
show player-to-player variation, not changes in the speed of play between eras.

Inputs, snapshotted under ``data/estimates/raw``: NBA.com ``FranchisePlayers`` (Bulls, regular
season and playoffs) to choose candidates, ``PlayerCareerStats`` for each candidate's Bulls minutes
by season, and league-wide ``LeagueDashPtStats`` SpeedDistance player totals for the rate. Candidates are players with ``MIN_GP`` or more regular-season Bulls games; the
build proves nobody below that cutoff could reach the top 15.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/visuals/2026-10-04-bulls-miles-marathons/data'
RAW = DATA / 'estimates/raw'
CHI = 1610612741
MARATHON_MILES = 26.2
FIRST_SEASON, FIRST_TRACKED = 1976, 2013
MIN_GP, TOP_N = 200, 15
LAST_TRACKED = 2025


def _franchise(season_type: str) -> pd.DataFrame:
    path = RAW / f'franchise-players-{season_type.split()[0].lower()}.csv'
    if not path.exists():
        from nba_api.stats.endpoints import franchiseplayers
        path.parent.mkdir(parents=True, exist_ok=True)
        franchiseplayers.FranchisePlayers(
            team_id=CHI, season_type_all_star=season_type, timeout=60,
        ).get_data_frames()[0].to_csv(path, index=False)
        time.sleep(0.6)
    return pd.read_csv(path)


def _career_minutes(player_ids: list[int]) -> pd.DataFrame:
    path = RAW / 'career-minutes.csv'
    have = set(pd.read_csv(path).PLAYER_ID) if path.exists() else set()
    missing = [pid for pid in player_ids if pid not in have]
    if missing:
        from nba_api.stats.endpoints import playercareerstats
        rows = [pd.read_csv(path)] if have else []
        for pid in missing:
            frames = playercareerstats.PlayerCareerStats(player_id=pid, timeout=60).get_data_frames()
            for index, season_type in ((0, 'Regular Season'), (2, 'Playoffs')):
                f = frames[index]
                rows.append(f[f.TEAM_ID == CHI][['PLAYER_ID', 'SEASON_ID', 'GP', 'MIN']]
                            .assign(TYPE=season_type))
            time.sleep(0.6)
        pd.concat(rows).to_csv(path, index=False)
    return pd.read_csv(path)


def _league() -> pd.DataFrame:
    frames = []
    for year in range(FIRST_TRACKED, LAST_TRACKED + 1):
        season = f'{year}-{str(year + 1)[2:]}'
        path = RAW / f'league-players-{season}.csv'
        if not path.exists():
            from nba_api.stats.endpoints import leaguedashptstats
            leaguedashptstats.LeagueDashPtStats(
                season=season, season_type_all_star='Regular Season', pt_measure_type='SpeedDistance',
                per_mode_simple='Totals', player_or_team='Player', timeout=60,
            ).get_data_frames()[0].to_csv(path, index=False)
            time.sleep(0.6)
        frames.append(pd.read_csv(path).assign(SEASON=season))
    return pd.concat(frames, ignore_index=True)


def _tracked() -> pd.DataFrame:
    frames = []
    for path in sorted((DATA / 'raw').glob('player-*.csv')):
        season_type = ('Playoffs' if 'playoffs' in path.name
                       else 'PlayIn' if 'playin' in path.name else 'Regular Season')
        frames.append(pd.read_csv(path).assign(TYPE=season_type, SEASON=path.name[7:14]))
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    regular, playoffs = _franchise('Regular Season'), _franchise('Playoffs')
    candidates = regular[regular.GP >= MIN_GP]
    # Cutoff proof: the most minutes anyone below MIN_GP could log (48 per game, including their
    # playoff games) must fall short of the 15th estimate even at the highest era rate.
    below = regular[regular.GP < MIN_GP].merge(
        playoffs[['PERSON_ID', 'GP']], on='PERSON_ID', how='left', suffixes=('', '_PO')).fillna(0)
    max_below_min = ((below.GP + below.GP_PO) * 48).max()

    minutes = _career_minutes(candidates.PERSON_ID.astype(int).tolist())
    minutes = minutes[minutes.SEASON_ID.str[:4].astype(int) >= FIRST_SEASON]
    tracked = _tracked()

    league = _league()
    rate = league.DIST_MILES.sum() / league.MIN.sum()
    seasons = league[league.MIN >= 500]
    lo, hi = (seasons.DIST_MILES / seasons.MIN).quantile([0.1, 0.9])

    names = candidates.set_index('PERSON_ID').PLAYER
    out = []
    for pid, group in minutes.groupby('PLAYER_ID'):
        mine = tracked[tracked.PLAYER_ID == pid]
        untracked = group[group.SEASON_ID.str[:4].astype(int) < FIRST_TRACKED]
        tracked_min, tracked_mi = mine.MIN.sum(), mine.DIST_MILES.sum()
        years = group.SEASON_ID.str[:4].astype(int)
        playin = mine[mine.TYPE == 'PlayIn']
        out.append({
            'PLAYER_ID': pid, 'player': names[pid],
            'first_season': years.min(), 'last_season': years.max(),
            'games': int(group.GP.sum() + playin.GP.sum()),
            'minutes': group.MIN.sum() + playin.MIN.sum(),
            'untracked_minutes': untracked.MIN.sum(),
            'measured_miles': tracked_mi,
            # NBA.com's own speed, minute-weighted (as on the tracking-era slide); blank if untracked.
            'measured_mph': (mine.AVG_SPEED * mine.MIN).sum() / tracked_min if tracked_min else None,
            'rate_mi_per_min': rate,
            'miles': tracked_mi + untracked.MIN.sum() * rate,
            'miles_lo': tracked_mi + untracked.MIN.sum() * lo,
            'miles_hi': tracked_mi + untracked.MIN.sum() * hi,
        })
    est = pd.DataFrame(out).sort_values('miles', ascending=False, ignore_index=True)
    for col in ('miles', 'miles_lo', 'miles_hi'):
        est[col.replace('miles', 'marathons')] = est[col] / MARATHON_MILES
    est['measured_share'] = est.measured_miles / est.miles
    est.insert(0, 'rank', range(1, len(est) + 1))

    cutoff_miles = est.miles.iloc[TOP_N - 1]
    if max_below_min * hi >= cutoff_miles:
        raise ValueError('A player below the games cutoff could reach the top 15; lower MIN_GP.')
    if abs(est.set_index('player').loc['Michael Jordan', 'minutes'] - 43364) > 1:
        raise ValueError('Jordan Bulls minutes changed; recheck the career-stats snapshot.')

    est.round(4).to_csv(DATA / 'estimates-all.csv', index=False)
    est.head(TOP_N).round(4).to_csv(DATA / f'estimates-top{TOP_N}.csv', index=False)
    print(f'NBA rate {rate:.4f} mi/min ({lo:.4f}-{hi:.4f}) from {len(seasons)} player-seasons; cutoff proof: '
          f'{max_below_min:,.0f} max minutes below {MIN_GP} GP < {cutoff_miles / hi:,.0f} needed')
    print(est.head(TOP_N)[['rank', 'player', 'minutes', 'measured_share',
                           'marathons', 'marathons_lo', 'marathons_hi']].round(2).to_string(index=False))


if __name__ == '__main__':
    main()
