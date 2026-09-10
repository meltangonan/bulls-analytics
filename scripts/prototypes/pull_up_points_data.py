"""Prepare Bulls pull-up points season leaders from NBA tracking, 2013-14 onward.

Raw responses remain untouched. League eFG uses all tracked player attempts;
PTS/G uses official Chicago appearances, including games with no pull-up shot.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashptstats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bulls.data.fetch import _NBA_HEADERS

DATA = ROOT / 'docs/visuals/2026-09-10-pull-up-points-leaders/data'
BULLS = 1610612741
SEASONS = [f'{year}-{str(year + 1)[-2:]}' for year in range(2013, 2026)]


def fetch(kind: str, season: str, refresh: bool = False) -> pd.DataFrame:
    path = DATA / 'raw' / f'{kind}_{season}.json'
    if refresh or not path.exists():
        common = dict(season=season, season_type_all_star='Regular Season')
        if kind == 'official':
            params = dict(**common, team_id_nullable=BULLS, per_mode_detailed='Totals')
            call = leaguedashplayerstats.LeagueDashPlayerStats
        else:
            params = dict(**common, player_or_team='Team' if kind == 'league' else 'Player',
                          pt_measure_type='PullUpShot', per_mode_simple='Totals',
                          team_id_nullable=BULLS if kind == 'bulls' else '')
            call = leaguedashptstats.LeagueDashPtStats
        response = call(**params, headers=_NBA_HEADERS, timeout=30)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(endpoint=call.__name__, parameters=params,
            retrieved_at=datetime.now(timezone.utc).isoformat(), response=response.get_dict()),
            ensure_ascii=False))
    raw = json.loads(path.read_text())['response']['resultSets'][0]
    frame = pd.DataFrame(raw['rowSet'], columns=raw['headers'])
    if frame.empty:
        raise ValueError(f'Missing source: {kind} {season}')
    return frame


def weighted_efg(frame: pd.DataFrame) -> float:
    # Points / (2 * attempts) equals eFG, including when FG3M is unavailable.
    cols = ['PULL_UP_PTS', 'PULL_UP_FGA']
    if frame[cols].isna().any().any() or frame.PULL_UP_FGA.sum() <= 0:
        raise ValueError('Missing or empty tracking baseline')
    return 50 * frame.PULL_UP_PTS.sum() / frame.PULL_UP_FGA.sum()


def summarize(players: pd.DataFrame, official: pd.DataFrame, league: pd.DataFrame,
              season: str, league_players: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    required = ['PLAYER_ID', 'GP', 'PULL_UP_FGM', 'PULL_UP_FGA', 'PULL_UP_PTS']
    if players[required].isna().any().any() or players.PULL_UP_FGA.sum() <= 0:
        raise ValueError(f'Missing player tracking data: {season}')
    if league.TEAM_ID.nunique() != 30 or len(league) != 30:
        raise ValueError(f'Incomplete league: {season}')
    bull_team = league.loc[league.TEAM_ID == BULLS].iloc[0]
    checks = {}
    for col in ['PULL_UP_FGM', 'PULL_UP_FGA', 'PULL_UP_PTS']:
        checks[col + '_difference'] = int(players[col].sum() - bull_team[col])
        # Preserve provider discrepancies, never alter player counts to force agreement.
    known = players.PULL_UP_FG3M.notna()
    if not (players.loc[known, 'PULL_UP_PTS'] ==
            2 * players.loc[known, 'PULL_UP_FGM'] + players.loc[known, 'PULL_UP_FG3M']).all():
        raise ValueError('Points disagree with makes and threes')
    merged = players.merge(official[['PLAYER_ID', 'GP', 'FGM', 'FGA', 'PTS']],
                           on='PLAYER_ID', suffixes=('_tracking', '_official'),
                           how='left', validate='one_to_one')
    if merged.GP_official.isna().any() or (merged.GP_official <= 0).any():
        raise ValueError('Missing official Chicago games played')
    if not (merged.GP_tracking == merged.GP_official).all():
        raise ValueError('Tracking GP differs from official Chicago GP')
    for track, box in [('PULL_UP_FGA', 'FGA'), ('PULL_UP_FGM', 'FGM'), ('PULL_UP_PTS', 'PTS')]:
        if (merged[track] > merged[box]).any():
            raise ValueError(f'Tracking exceeds official total: {track}')
    out = pd.DataFrame(dict(player_id=merged.PLAYER_ID,
        player_name=merged.PLAYER_NAME.replace({'Jimmy Butler III': 'Jimmy Butler'}),
        season=season, gp=merged.GP_official, fgm=merged.PULL_UP_FGM,
        fga=merged.PULL_UP_FGA, fg3m=merged.PULL_UP_FG3M, pts=merged.PULL_UP_PTS))
    out['efg_pct'] = 50 * out.pts / out.fga.replace(0, float('nan'))
    if league_players.PLAYER_ID.duplicated().any():
        raise ValueError('Duplicate player in league baseline')
    out['league_efg_pct'] = weighted_efg(league_players)
    out['relative_efg_pp'] = out.efg_pct - out.league_efg_pct
    out['fga_per_game'] = out.fga / out.gp
    out['pts_per_game'] = out.pts / out.gp
    return out, dict(season=season, player_rows=len(players), league_teams=len(league),
        official_gp_match=True, missing_raw_fg3m=int((~known).sum()),
        league_player_rows=len(league_players),
        league_fga=int(league_players.PULL_UP_FGA.sum()), league_pts=int(league_players.PULL_UP_PTS.sum()),
        league_efg_pct=weighted_efg(league_players), league_team_efg_pct=weighted_efg(league), **checks)


def main(refresh: bool = False) -> None:
    frames, audits = [], []
    for season in SEASONS:
        players, official, league, league_players = [fetch(kind, season, refresh)
            for kind in ('bulls', 'official', 'league', 'league_players')]
        frame, audit = summarize(players, official, league, season, league_players)
        frames.append(frame)
        audits.append(audit)
        print(f'{season}: {len(frame)} Bulls player rows, GP verified, team differences audited', flush=True)
    all_rows = pd.concat(frames, ignore_index=True).sort_values(
        ['pts', 'fgm', 'season', 'player_id'], ascending=[False, False, True, True])
    top = all_rows.head(15).copy()
    # Equal point totals are resolved by makes, then season and player ID so the
    # requested fixed-size board stays at fifteen rows.
    top.insert(0, 'rank', range(1, 16))
    all_rows.to_csv(DATA / 'all_player_seasons.csv', index=False)
    top.to_csv(DATA / 'top15.csv', index=False)
    # Keep the earlier ten-row extract available for audit/test comparisons.
    top.head(10).to_csv(DATA / 'top10.csv', index=False)
    pd.DataFrame(audits).to_csv(DATA / 'season_audit.csv', index=False)
    copy = dict(title='Bulls pull-up scoring leaders',
        subtitle='Most pull-up points in a season · Top 15 since 2013–14',
        scope='2013–14 to 2025–26 regular season · Chicago games only',
        source='Source: NBA.com · Player tracking', handle='@chicagobullsdata',
        definition='Pull-up points exclude free throws. All supporting shooting stats refer to pull-ups.',
        relative='rEFG = pull-up eFG% minus the same-season NBA pull-up eFG%, in percentage points.',
        per_game='FGA/G and PTS/G use all official Bulls appearances that season.',
        leader=dict(player=top.iloc[0].player_name, season=top.iloc[0].season,
                    points=int(top.iloc[0].pts)))
    (DATA / 'canva_copy.json').write_text(json.dumps(copy, indent=2, ensure_ascii=False))
    print(top.to_string(index=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    main(parser.parse_args().refresh)
