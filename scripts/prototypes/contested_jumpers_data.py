"""Prepare Bulls contested-jumper season leaders from NBA tracking, 2013-14 onward.

A jumper is a field-goal attempt from 10+ feet. It is contested when the closest
defender was within 4 feet at release (Very Tight + Tight), uncontested otherwise
(Open + Wide Open). Chicago rows use the Bulls team filter, so a traded player's
row covers only his Chicago games; NBA rank and the league average use the
unfiltered league pool, where a traded player's row covers his full season.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerptshot, teamdashptshots

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bulls.data.fetch import _NBA_HEADERS

DATA = ROOT / 'docs/visuals/2026-09-19-contested-jumpers/data'
BULLS = 1610612741
SEASONS = [f'{year}-{str(year + 1)[-2:]}' for year in range(2013, 2026)]
BUCKETS = {
    'very_tight': '0-2 Feet - Very Tight',
    'tight': '2-4 Feet - Tight',
    'open': '4-6 Feet - Open',
    'wide_open': '6+ Feet - Wide Open',
}
CONTESTED = ('very_tight', 'tight')
JUMPER = '>=10.0'
NAMES = {'Jimmy Butler III': 'Jimmy Butler'}


def _save(path: Path, endpoint: str, params: dict, response: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(endpoint=endpoint, parameters=params,
        retrieved_at=datetime.now(timezone.utc).isoformat(), response=response),
        ensure_ascii=False))


def fetch_players(scope: str, season: str, bucket: str, refresh: bool = False) -> pd.DataFrame:
    """One bucket of 10+ ft shots for Chicago players ('bulls') or every player ('league')."""
    path = DATA / 'raw' / f'{scope}_{season}_{bucket}.json'
    if refresh or not path.exists():
        params = dict(season=season, season_type_all_star='Regular Season',
                      per_mode_simple='Totals', shot_dist_range_nullable=JUMPER,
                      close_def_dist_range_nullable=BUCKETS[bucket],
                      team_id_nullable=BULLS if scope == 'bulls' else '')
        response = leaguedashplayerptshot.LeagueDashPlayerPtShot(
            **params, headers=_NBA_HEADERS, timeout=60)
        _save(path, 'LeagueDashPlayerPtShot', params, response.get_dict())
    raw = json.loads(path.read_text())['response']['resultSets'][0]
    frame = pd.DataFrame(raw['rowSet'], columns=raw['headers'])
    if frame.empty:
        raise ValueError(f'Missing source: {scope} {season} {bucket}')
    return frame


def fetch_team(season: str, refresh: bool = False) -> pd.DataFrame:
    """Chicago's team total by defender distance on 10+ ft shots, for reconciliation."""
    path = DATA / 'raw' / f'team_{season}.json'
    if refresh or not path.exists():
        params = dict(team_id=BULLS, season=season, season_type_all_star='Regular Season',
                      per_mode_simple='Totals')
        response = teamdashptshots.TeamDashPtShots(**params, headers=_NBA_HEADERS, timeout=60)
        _save(path, 'TeamDashPtShots', params, response.get_dict())
    sets = json.loads(path.read_text())['response']['resultSets']
    raw = next(s for s in sets if s['name'] == 'ClosestDefender10ftPlusShooting')
    return pd.DataFrame(raw['rowSet'], columns=raw['headers'])


def split(buckets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Sum the four buckets into contested and uncontested makes and attempts per player."""
    parts = []
    for bucket, frame in buckets.items():
        if frame.PLAYER_ID.duplicated().any():
            raise ValueError(f'Duplicate player in {bucket}')
        if frame[['FGM', 'FGA']].isna().any().any() or (frame.FGM > frame.FGA).any():
            raise ValueError(f'Missing or impossible makes in {bucket}')
        kind = 'c' if bucket in CONTESTED else 'u'
        parts.append(frame[['PLAYER_ID', 'PLAYER_NAME', 'FGM', 'FGA']].rename(
            columns={'FGM': f'{kind}_fgm', 'FGA': f'{kind}_fga'}))
    out = pd.concat(parts).groupby(['PLAYER_ID', 'PLAYER_NAME'], as_index=False).sum(min_count=1)
    return out.fillna(0)  # A player absent from a bucket took no shots in it.


def summarize(bulls: dict[str, pd.DataFrame], league: dict[str, pd.DataFrame],
              team: pd.DataFrame, season: str) -> tuple[pd.DataFrame, dict]:
    chi, nba = split(bulls), split(league)
    league_avg = 100 * nba.c_fgm.sum() / nba.c_fga.sum()
    nba['nba_rank'] = nba.c_fgm.rank(ascending=False, method='min').astype(int)

    # The team dashboard is an independent total of the same Chicago shots. Small provider
    # differences are recorded, never forced away; a large one means a broken pull.
    checks = {}
    for kind, labels in (('c', CONTESTED), ('u', ('open', 'wide_open'))):
        rows = team[team.CLOSE_DEF_DIST_RANGE.isin([BUCKETS[b] for b in labels])]
        for stat in ('fgm', 'fga'):
            team_total = rows[stat.upper()].sum()
            difference = int(chi[f'{kind}_{stat}'].sum() - team_total)
            if abs(difference) > max(5, 0.01 * team_total):
                raise ValueError(f'Chicago players do not sum to the team total: {season} {kind}_{stat}')
            checks[f'{kind}_{stat}_difference'] = difference

    out = chi.merge(nba[['PLAYER_ID', 'c_fgm', 'nba_rank']], on='PLAYER_ID', how='left',
                    suffixes=('', '_full_season'), validate='one_to_one')
    if out.nba_rank.isna().any():
        raise ValueError(f'Chicago player missing from league pool: {season}')
    out = out.rename(columns={'PLAYER_ID': 'player_id', 'PLAYER_NAME': 'player_name'})
    out['player_name'] = out.player_name.replace(NAMES)
    out.insert(2, 'season', season)
    out['c_fg_pct'] = 100 * out.c_fgm / out.c_fga.replace(0, float('nan'))
    out['u_fg_pct'] = 100 * out.u_fgm / out.u_fga.replace(0, float('nan'))
    out['league_c_fg_pct'] = league_avg
    out['c_vs_league_pp'] = out.c_fg_pct - league_avg
    # Differs from c_fgm only for a player who also played for another team that season.
    out['partial_season'] = out.c_fgm != out.c_fgm_full_season
    return out, dict(season=season, bulls_players=len(chi), league_players=len(nba),
                     league_c_fgm=int(nba.c_fgm.sum()), league_c_fga=int(nba.c_fga.sum()),
                     league_c_fg_pct=league_avg, **checks)


def select(all_rows: pd.DataFrame, size: int = 15) -> pd.DataFrame:
    """Most contested makes; ties go to the higher contested FG%, then the older season."""
    ranked = all_rows.sort_values(['c_fgm', 'c_fg_pct', 'season'],
                                  ascending=[False, False, True], kind='stable')
    top = ranked.head(size).copy()
    top.insert(0, 'rank', range(1, len(top) + 1))
    return top


def main(refresh: bool = False) -> None:
    frames, audits = [], []
    for season in SEASONS:
        bulls = {b: fetch_players('bulls', season, b, refresh) for b in BUCKETS}
        league = {b: fetch_players('league', season, b, refresh) for b in BUCKETS}
        frame, audit = summarize(bulls, league, fetch_team(season, refresh), season)
        frames.append(frame)
        audits.append(audit)
        print(f'{season}: {len(frame)} Bulls players, team total reconciled', flush=True)
    all_rows = pd.concat(frames, ignore_index=True)
    top = select(all_rows)
    all_rows.to_csv(DATA / 'all_player_seasons.csv', index=False)
    top.to_csv(DATA / 'top15.csv', index=False)
    pd.DataFrame(audits).to_csv(DATA / 'season_audit.csv', index=False)
    print(top[['rank', 'player_name', 'season', 'c_fgm', 'c_fga', 'c_fg_pct',
               'c_vs_league_pp', 'u_fg_pct', 'nba_rank', 'partial_season']].round(1).to_string(index=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    main(parser.parse_args().refresh)
