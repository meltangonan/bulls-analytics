"""Certify Bulls regular-season single-game points created, 1996-97–2025-26.

Use exact NBA assisted basket values only for games that can affect the top 15.
All other player-games are excluded with conservative official box-score bounds.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.prototypes.points_created_nba_parse import parse_game
from scripts.prototypes.points_created_nba_ranks import game_assist_bounds

DATA = ROOT / 'docs/visuals/2026-10-02-points-created-games/data'
BOX = ROOT / 'docs/visuals/2026-09-25-season-opener-performances/data/raw'
SEASON = ROOT / 'docs/visuals/2026-09-21-points-created/data/nba-league'
DUOS = ROOT / 'docs/visuals/2026-08-08-assist-duos/data/seasons'
CHI = 1610612741


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_population():
    """Check complete season game populations and official team scoring totals."""
    players, teams, sources = [], [], []
    for end in range(1997, 2027):
        for kind, target in [('players', players), ('team', teams)]:
            original = BOX / f'CHI-{kind}-regular-season-{end}.csv'
            saved = DATA / 'raw' / original.name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, saved)
            target.append(pd.read_csv(saved, dtype={'game_id': str}))
            sources.append({'path': str(saved.relative_to(ROOT)),
                            'source_path': str(original.relative_to(ROOT)),
                            'sha256': sha(saved), 'original_capture_date': None})
    p, t = pd.concat(players, ignore_index=True), pd.concat(teams, ignore_index=True)
    p = p.rename(columns={'player_id':'PLAYER_ID', 'player':'PLAYER_NAME',
                          'game_id':'GAME_ID', 'game_date':'GAME_DATE',
                          'matchup':'MATCHUP', 'result':'WL', 'points':'PTS',
                          'ast':'AST', 'fgm':'FGM', 'fg3m':'FG3M'})
    p['TEAM_ID'] = CHI
    p['season'] = p.season.str.replace('–', '-', regex=False)
    p.GAME_ID = p.GAME_ID.str.zfill(10)
    t.game_id = t.game_id.str.zfill(10)
    required = ['PLAYER_ID','PLAYER_NAME','GAME_ID','PTS','AST','FGM','FG3M']
    if p[required].isna().any().any() or p.duplicated(['GAME_ID','PLAYER_ID']).any():
        raise ValueError('Missing or duplicate player-game data')
    if t.duplicated('game_id').any() or set(p.GAME_ID) != set(t.game_id):
        raise ValueError('Team and player game populations differ')
    expected = {end:82 for end in range(1997,2027)}
    expected.update({1999:50,2012:66,2020:65,2021:72})
    coverage = []
    for end, n in expected.items():
        games = t[t.season_end_year == end]
        if len(games) != n:
            raise ValueError(f'Incomplete {end}: {len(games)} of {n}')
        coverage.append({'season':f'{end-1}-{str(end)[-2:]}','games':n,
                         'player_game_rows':int((p.season_end_year==end).sum())})
    sums = p.groupby('GAME_ID').PTS.sum()
    if not sums.reindex(t.game_id).to_numpy().tolist() == t.team_points.tolist():
        raise ValueError('Player scoring does not reconcile to official team scores')
    p = game_assist_bounds(p)
    p['minimum_created'] = p.PTS + p.minimum_assist_points
    p['maximum_created'] = p.PTS + p.maximum_assist_points
    p = p.merge(t[['game_id','team_points','team_plus_minus']], left_on='GAME_ID',
                right_on='game_id', validate='many_to_one').drop(columns='game_id')
    p = p.rename(columns={'team_points':'team_pts'})
    p['opponent_pts'] = p.team_pts - p.team_plus_minus
    return p, coverage, sources


def assisted_game(season, gid, logs):
    """Prefer original NBA actions; otherwise reuse saved NBA basket extraction."""
    raw = SEASON / 'raw' / f'{season}_{gid}.json.gz'
    if raw.exists():
        with gzip.open(raw,'rt') as h:
            data = json.load(h)
        frame = pd.DataFrame(data['records'])
        # Only Chicago is in this population; restrict opponent events before audit.
        events, issues = parse_game(frame[frame.teamId == CHI], logs)
        saved = DATA / 'raw' / raw.name
        shutil.copyfile(raw, saved)
        source = {'path':str(saved.relative_to(ROOT)), 'source_path':str(raw.relative_to(ROOT)),
                  'sha256':sha(saved), 'retrieved_at':data.get('retrieved_at'),
                  'type':'NBA PlayByPlayV3 raw actions'}
        overtime = max(0, int(frame.period.max()) - 4)
    else:
        original = DUOS / f'assisted-baskets-{season}.csv'
        if not original.exists():
            raise ValueError(f'No saved NBA basket input for candidate {season} {gid}')
        all_events = pd.read_csv(original, dtype={'game_id':str})
        events = all_events[all_events.game_id.str.zfill(10) == gid].copy()
        events['team_id'] = CHI
        issues = []
        source = {'path':str(original.relative_to(ROOT)), 'sha256':sha(original),
                  'type':'Saved normalized NBA PlayByPlayV3 assisted baskets',
                  'original_capture_date':None, 'game_id':gid}
        total_minutes = float(logs.minutes.sum())
        overtime = round((total_minutes - 240) / 25)
        if overtime < 0 or abs(total_minutes - (240 + 25 * overtime)) > 0.2:
            raise ValueError(f'Cannot verify overtime from official minutes: {gid}')
        source['overtime_source'] = 'Official player-game MIN sum: 240 + 25 per overtime'
        saved = DATA / 'raw' / f'assisted-baskets-{season}-{gid}.csv'
        events.to_csv(saved, index=False)
        source['archived_game_path'] = str(saved.relative_to(ROOT))
        source['archived_game_sha256'] = sha(saved)
    count = events.groupby('assister_id').size()
    for row in logs.itertuples():
        if int(count.get(row.PLAYER_ID,0)) != int(row.AST):
            issues.append({'game_id':gid,'severity':'error','kind':'assist_count_mismatch',
                           'player_id':int(row.PLAYER_ID),'official_ast':int(row.AST),
                           'pbp_ast':int(count.get(row.PLAYER_ID,0))})
    roster = set(logs.PLAYER_ID)
    if (not set(events.assister_id).issubset(roster)
            or not set(events.scorer_id).issubset(roster)
            or events.assister_id.eq(events.scorer_id).any()
            or not events.shot_value.isin([2,3]).all()):
        raise ValueError(f'Invalid teammate assist identity/value {gid}')
    if 'action_number' in events and events.action_number.duplicated().any():
        raise ValueError(f'Duplicate assisted action {gid}')
    made = events.groupby(['scorer_id','shot_value']).size()
    for row in logs.itertuples():
        if (int(made.get((row.PLAYER_ID,3),0)) > int(row.FG3M)
                or int(made.get((row.PLAYER_ID,2),0)) > int(row.FGM-row.FG3M)):
            raise ValueError(f'Assisted baskets exceed official scorer field goals {gid}')
    if any(i.get('severity') == 'error' for i in issues):
        (DATA / 'issues.json').write_text(json.dumps(issues, indent=2))
        raise ValueError(f'Assist audit failed: {gid}: {issues}')
    return events, issues, source, overtime


def certify(population, limit=15):
    """Resolve a game only while it can meet or exceed the current cutoff."""
    p = population.copy()
    p['assist_pts'] = pd.NA
    p['created'] = pd.NA
    p['overtimes'] = pd.NA
    event_frames, sources, issues = [], [], []
    while True:
        exact = p[p.created.notna()].sort_values('created',ascending=False)
        guaranteed_cutoff = int(p.minimum_created.nlargest(limit).min())
        cutoff = max(guaranteed_cutoff, int(exact.iloc[limit-1].created)) if len(exact) >= limit else guaranteed_cutoff
        pending = p[p.created.isna() & (p.maximum_created >= cutoff)]
        if pending.empty:
            break
        candidate = pending.sort_values(['maximum_created','minimum_created'],ascending=False).iloc[0]
        gid, season = candidate.GAME_ID, candidate.season
        logs = p[p.GAME_ID == gid]
        events, problems, source, overtime = assisted_game(season,gid,logs)
        totals = events.groupby('assister_id').shot_value.sum()
        for idx, row in logs.iterrows():
            value = int(totals.get(row.PLAYER_ID,0))
            p.loc[idx,'assist_pts'] = value
            p.loc[idx,'created'] = int(row.PTS) + value
            p.loc[idx,'overtimes'] = overtime
        event_frames.append(events); sources.append(source); issues.extend(problems)
        print(f'{gid} resolved; {len(sources)} candidate games; cutoff {cutoff}',flush=True)
    p['status'] = p.created.notna().map({True:'exact',False:'excluded_by_bound'})
    top = p[p.created.notna()].sort_values(['created','GAME_DATE','PLAYER_ID'],ascending=[False,True,True]).head(limit).copy()
    cutoff = int(top.created.min())
    if p.loc[p.created.isna(),'maximum_created'].ge(cutoff).any():
        raise ValueError('Selection is not certified')
    # Keep every cutoff tie; the renderer must never silently truncate a tie.
    top = p[p.created.notna() & (p.created >= cutoff)].sort_values(['created','GAME_DATE','PLAYER_ID'],ascending=[False,True,True]).copy()
    top['rank'] = top.created.astype(int).rank(method='min',ascending=False).astype(int)
    top['team_pct'] = 100 * top.created.astype(float) / top.team_pts
    top['overtime_label'] = top.overtimes.map(lambda n: '' if n == 0 else 'OT' if n == 1 else f'{int(n)}OT')
    return top, p, pd.concat(event_frames,ignore_index=True), sources, issues


def main():
    DATA.mkdir(parents=True,exist_ok=True)
    p, coverage, box_sources = load_population()
    top, proof, events, sources, issues = certify(p)
    top.to_csv(DATA/'top15.csv',index=False)
    proof.to_csv(DATA/'selection-proof.csv.gz',index=False)
    pd.DataFrame(coverage).to_csv(DATA/'coverage.csv',index=False)
    events.to_csv(DATA/'candidate-assisted-baskets.csv.gz',index=False)
    (DATA/'issues.json').write_text(json.dumps(issues,indent=2))
    result = {'generated_at':datetime.now(timezone.utc).isoformat(), 'status':'complete',
              'population_player_games':len(p), 'population_games':p.GAME_ID.nunique(),
              'candidate_games_resolved':len(sources), 'display_rows':len(top),
              'cutoff_created':int(top.created.min()),
              'maximum_excluded_bound':int(proof.loc[proof.status=='excluded_by_bound','maximum_created'].max()),
              'error_count':0, 'box_sources':box_sources, 'basket_sources':sources,
              'output_sha256':{name:sha(DATA/name) for name in ['top15.csv','selection-proof.csv.gz','coverage.csv','candidate-assisted-baskets.csv.gz']}}
    (DATA/'verification-summary.json').write_text(json.dumps(result,indent=2))
    print(top[['rank','PLAYER_NAME','GAME_DATE','MATCHUP','PTS','AST','assist_pts','created','team_pts','team_pct']].to_string(index=False))


if __name__ == '__main__':
    main()
