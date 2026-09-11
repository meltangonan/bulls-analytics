"""Prepare Bulls catch-and-shoot points season leaders from NBA tracking, 2013-14 onward.

Raw responses remain untouched. League eFG uses all tracked player attempts;
PTS/G uses official Chicago appearances, including games with no catch-and-shoot shot.
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

DATA = ROOT / 'docs/visuals/2026-09-11-catch-and-shoot-points-leaders/data'
BULLS = 1610612741
SEASONS = [f'{year}-{str(year + 1)[-2:]}' for year in range(2013, 2026)]


def fetch(kind: str, season: str, refresh: bool = False) -> pd.DataFrame:
    path = DATA / 'raw' / f'{kind}_{season}.json'
    if refresh or not path.exists():
        common = dict(season=season, season_type_all_star='Regular Season')
        if kind in ('official', 'official_league'):
            params = dict(**common, team_id_nullable=BULLS if kind == 'official' else '', per_mode_detailed='Totals')
            call = leaguedashplayerstats.LeagueDashPlayerStats
        else:
            params = dict(**common, player_or_team='Team' if kind == 'league' else 'Player',
                          pt_measure_type='CatchShoot', per_mode_simple='Totals',
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
    cols = ['CATCH_SHOOT_PTS', 'CATCH_SHOOT_FGA']
    if frame[cols].isna().any().any() or frame.CATCH_SHOOT_FGA.sum() <= 0:
        raise ValueError('Missing or empty tracking baseline')
    return 50 * frame.CATCH_SHOOT_PTS.sum() / frame.CATCH_SHOOT_FGA.sum()


def summarize(players: pd.DataFrame, official: pd.DataFrame, league: pd.DataFrame,
              season: str, league_players: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    required = ['PLAYER_ID', 'GP', 'CATCH_SHOOT_FGM', 'CATCH_SHOOT_FGA', 'CATCH_SHOOT_PTS']
    if players[required].isna().any().any() or players.CATCH_SHOOT_FGA.sum() <= 0:
        raise ValueError(f'Missing player tracking data: {season}')
    if league.TEAM_ID.nunique() != 30 or len(league) != 30:
        raise ValueError(f'Incomplete league: {season}')
    bull_team = league.loc[league.TEAM_ID == BULLS].iloc[0]
    checks = {}
    for col in ['CATCH_SHOOT_FGM', 'CATCH_SHOOT_FGA', 'CATCH_SHOOT_PTS']:
        checks[col + '_difference'] = int(players[col].sum() - bull_team[col])
        # Preserve provider discrepancies, never alter player counts to force agreement.
    known = players.CATCH_SHOOT_FG3M.notna()
    if not (players.loc[known, 'CATCH_SHOOT_PTS'] ==
            2 * players.loc[known, 'CATCH_SHOOT_FGM'] + players.loc[known, 'CATCH_SHOOT_FG3M']).all():
        raise ValueError('Points disagree with makes and threes')
    merged = players.merge(official[['PLAYER_ID', 'GP', 'FGM', 'FGA', 'FG3M', 'FG3A', 'PTS']],
                           on='PLAYER_ID', suffixes=('_tracking', '_official'),
                           how='left', validate='one_to_one')
    if merged.GP_official.isna().any() or (merged.GP_official <= 0).any():
        raise ValueError('Missing official Chicago games played')
    if not (merged.GP_tracking == merged.GP_official).all():
        raise ValueError('Tracking GP differs from official Chicago GP')
    for track, box in [('CATCH_SHOOT_FGA', 'FGA'), ('CATCH_SHOOT_FGM', 'FGM'), ('CATCH_SHOOT_PTS', 'PTS')]:
        if (merged[track] > merged[box]).any():
            raise ValueError(f'Tracking exceeds official total: {track}')
    out = pd.DataFrame(dict(player_id=merged.PLAYER_ID,
        player_name=merged.PLAYER_NAME.replace({'Jimmy Butler III': 'Jimmy Butler'}),
        season=season, gp=merged.GP_official, fgm=merged.CATCH_SHOOT_FGM,
        fga=merged.CATCH_SHOOT_FGA, fg3m=merged.CATCH_SHOOT_PTS - 2 * merged.CATCH_SHOOT_FGM,
        fg3a=merged.CATCH_SHOOT_FG3A, pts=merged.CATCH_SHOOT_PTS))
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
        league_fga=int(league_players.CATCH_SHOOT_FGA.sum()), league_pts=int(league_players.CATCH_SHOOT_PTS.sum()),
        league_efg_pct=weighted_efg(league_players), league_team_efg_pct=weighted_efg(league), **checks)


def three_bounds(players: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    """Retain unknown 3PA as an interval, bounded by official total 3PA."""
    merged = players.merge(official[['PLAYER_ID', 'FG3M', 'FG3A']], on='PLAYER_ID',
                           how='left', validate='one_to_one')
    if merged[['FG3M', 'FG3A']].isna().any().any():
        raise ValueError('Missing official three-point bounds')
    if merged[['CATCH_SHOOT_PTS', 'CATCH_SHOOT_FGM', 'CATCH_SHOOT_FGA']].isna().any().any():
        raise ValueError('Missing tracking counts')
    made = merged.CATCH_SHOOT_PTS - 2 * merged.CATCH_SHOOT_FGM
    known = merged.CATCH_SHOOT_FG3M.notna()
    if (made < 0).any() or (made > merged.CATCH_SHOOT_FGM).any() or (made > merged.FG3M).any() or not (
            made[known] == merged.loc[known, 'CATCH_SHOOT_FG3M']).all():
        raise ValueError('Invalid three-point makes')
    cap = merged[['CATCH_SHOOT_FGA', 'FG3A']].min(axis=1)
    low = merged.CATCH_SHOOT_FG3A.fillna(made)
    high = merged.CATCH_SHOOT_FG3A.fillna(cap)
    if (low < made).any() or (high < low).any() or (high > merged.CATCH_SHOOT_FGA).any():
        raise ValueError('Invalid three-point attempts')
    return pd.DataFrame(dict(player_id=merged.PLAYER_ID, fg3m=made,
        fg3a_low=low, fg3a_high=high, raw_fg3a_missing=merged.CATCH_SHOOT_FG3A.isna(),
        official_3pa_excess=(merged.CATCH_SHOOT_FG3A - merged.FG3A).clip(lower=0)))


def ranked(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values(['pts', 'fgm', 'season', 'player_id'],
                           ascending=[False, False, True, True]).head(15).copy()
    out.insert(0, 'rank', range(1, len(out) + 1))
    return out


def main(refresh: bool = False) -> None:
    frames, threes, audits, missing_rows = [], [], [], []
    for season in SEASONS:
        players, official, league, league_players, official_league = [fetch(kind, season, refresh)
            for kind in ('bulls', 'official', 'league', 'league_players', 'official_league')]
        frame, audit = summarize(players, official, league, season, league_players)
        if set(league_players.PLAYER_ID) != set(official_league.PLAYER_ID):
            raise ValueError(f'League player coverage differs: {season}')
        appearances = official_league.GP.sum()
        if appearances <= 0 or official_league.GP.isna().any():
            raise ValueError('Missing official league appearances')
        frame['league_fga_per_game'] = league_players.CATCH_SHOOT_FGA.sum() / appearances
        frame['relative_fga_per_game'] = frame.fga_per_game - frame.league_fga_per_game
        frame['league_pts_per_game'] = league_players.CATCH_SHOOT_PTS.sum() / appearances
        frame['relative_pts_per_game'] = frame.pts_per_game - frame.league_pts_per_game
        lb = three_bounds(league_players, official_league)
        pb = three_bounds(players, official)
        if pb.official_3pa_excess.sum() > 0:
            raise ValueError('Chicago tracked 3PA exceeds official total')
        misses = lb[lb.raw_fg3a_missing].copy()
        misses['season'] = season
        missing_rows.append(misses)
        made, low, high = lb.fg3m.sum(), lb.fg3a_low.sum(), lb.fg3a_high.sum()
        if low <= 0:
            raise ValueError('Empty league three-point baseline')
        three = frame.drop(columns=['fg3m', 'fg3a']).merge(pb, on='player_id', validate='one_to_one')
        three['pts'] = 3 * three.fg3m
        three['fgm'] = three.fg3m
        three['fga'] = three.fg3a_low.where(three.fg3a_low == three.fg3a_high)
        three['fg3a'] = three.fga
        three['efg_pct'] = 100 * three.fg3m / three.fga.replace(0, float('nan'))
        three['league_efg_pct'] = 100 * made / low
        three['league_3p_pct_low'] = 100 * made / high
        three['league_3p_pct_high'] = 100 * made / low
        three['relative_efg_pp'] = three.efg_pct - three.league_efg_pct
        three['relative_3p_pp_high'] = three.efg_pct - three.league_3p_pct_low
        three['fga_per_game'] = three.fga / three.gp
        three['pts_per_game'] = three.pts / three.gp
        three['league_pts_per_game'] = 3 * made / appearances
        three['relative_pts_per_game'] = three.pts_per_game - three.league_pts_per_game
        three['league_fga_per_game'] = low / appearances
        three['league_3pa_per_game_high'] = high / appearances
        three['relative_fga_per_game'] = three.fga_per_game - three.league_fga_per_game
        three['relative_3pa_per_game_low'] = three.fga_per_game - high / appearances
        audit.update(league_official_appearances=int(appearances),
            league_fga_per_game=frame.league_fga_per_game.iloc[0],
            league_official_3pa_excess=int(lb.official_3pa_excess.sum()),
            league_3pm=int(made), league_3pa_low=int(low), league_3pa_high=int(high),
            league_3p_pct_low=100 * made / high, league_3p_pct_high=100 * made / low,
            league_3pa_player_minus_team=int(low - league.CATCH_SHOOT_FG3A.sum()))
        frames.append(frame); threes.append(three); audits.append(audit)
        print(f'{season}: Chicago GP and counts verified; league unknown 3PA range {int(high-low)}', flush=True)
    all_rows = pd.concat(frames, ignore_index=True)
    all_threes = pd.concat(threes, ignore_index=True)
    top, top_three = ranked(all_rows), ranked(all_threes)
    if top_three[['fga', 'efg_pct']].isna().any().any():
        raise ValueError('Selected three-point row has unresolved attempts')
    # All plausible missing-attempt assignments must produce the same printed value.
    for left, right in [('relative_efg_pp', 'relative_3p_pp_high'),
                        ('relative_fga_per_game', 'relative_3pa_per_game_low')]:
        if not (top_three[left].round(1) == top_three[right].round(1)).all():
            raise ValueError(f'Unresolved attempts affect printed {left}')
    for name, data in [('all_player_seasons', all_rows), ('all_three_point_seasons', all_threes),
                       ('top15', top), ('top15_three_point', top_three),
                       ('season_audit', pd.DataFrame(audits)),
                       ('missing_three_point_attempts', pd.concat(missing_rows, ignore_index=True))]:
        data.to_csv(DATA / f'{name}.csv', index=False)
    copy = dict(title='Bulls catch-and-shoot scoring leaders',
        three_point_title='Bulls three-point catch-and-shoot scoring leaders',
        subtitle='Top 15 Bulls seasons by catch-and-shoot points since 2013–14',
        scope='2013–14 to 2025–26 regular season · Chicago games only',
        source='Source: NBA.com · Player tracking', handle='@chicagobullsdata',
        definition='Catch-and-shoot points exclude free throws.',
        relative='Efficiency comparisons use same-season catch-and-shoot league baselines: eFG% for all shots; 3P% for threes.',
        per_game='PTS/G and FGA/G use official Chicago appearances.',
        volume='PTS/G and FGA/G comparisons subtract same-season league catch-and-shoot points and attempts per official player appearance. No player qualification filter.',
        comparison_legend='Parentheses: difference from same-season league average. Efficiency in percentage points; PTS/G and FGA/G per player appearance.',
        missing='Unresolved league three-point attempts remain bounded, not zero-filled. Both bounds produce identical one-decimal comparisons for all selected rows.',
        leader=dict(player=top.iloc[0].player_name, season=top.iloc[0].season, points=int(top.iloc[0].pts)),
        three_point_leader=dict(player=top_three.iloc[0].player_name, season=top_three.iloc[0].season, points=int(top_three.iloc[0].pts)))
    (DATA / 'canva_copy.json').write_text(json.dumps(copy, indent=2, ensure_ascii=False))
    print(top[['rank', 'player_name', 'season', 'pts']].to_string(index=False))
    print(top_three[['rank', 'player_name', 'season', 'pts']].to_string(index=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    main(parser.parse_args().refresh)
