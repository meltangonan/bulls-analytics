"""Certify exact displayed NBA ranks with NBA-only inputs and conservative bounds.

Unknown assisted field goals are bounded at two to three points each; never estimated.
Download games serially until every opponent is provably above/below each Bulls total.
Raw NBA replies, basket rows, reconciliation issues, and per-opponent proofs are saved.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, shutil, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from nba_api.stats.endpoints import playergamelogs, playbyplayv3
from bulls.data.fetch import _NBA_HEADERS
from scripts.prototypes.points_created_nba_parse import parse_game
PRIMARY=Path('/Users/meltangonan/projects/bulls-analytics')
POST=ROOT/'docs/visuals/2026-09-21-points-created'
DATA=POST/'data'; OUT=DATA/'nba-league'
CHI=1610612741

def stamp():return datetime.now(timezone.utc).isoformat()
def read_frame(path):
    raw=json.loads(path.read_text())
    obj=raw['resultSets'][0]
    return pd.DataFrame(obj['rowSet'],columns=obj['headers'])
def request(factory,label):
    for attempt in range(5):
        try:return factory()
        except Exception as e:
            print(f'RETRY {label} attempt {attempt+1}: {e}',flush=True)
            if attempt==4:raise
            time.sleep((3,10,30,60)[attempt])
def league(season):
    path=PRIMARY/f'docs/visuals/2026-09-19-block-leaders/data/raw/league-{season}.json'
    if not path.exists():path=DATA/f'raw/nba-league-{season}.json'
    saved=OUT/f'league-summary-{season}.json'
    if not saved.exists():
        shutil.copyfile(path,saved)
        saved.with_suffix('.meta.json').write_text(json.dumps({'source_path':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'archived_at':stamp(),'retrieved_at':None,'note':'Reused saved NBA response; original capture timestamp unavailable.'},indent=2))
    f=read_frame(saved)
    if f.PLAYER_ID.duplicated().any():raise ValueError('Duplicate NBA season player')
    return f.set_index('PLAYER_ID')
def logs(season):
    path=OUT/f'player-game-logs-{season}.json'
    if not path.exists():
        o=request(lambda:playergamelogs.PlayerGameLogs(season_nullable=season,season_type_nullable='Regular Season',headers=_NBA_HEADERS,timeout=30),season)
        path.write_text(o.get_json())
        path.with_suffix('.meta.json').write_text(json.dumps({'endpoint':'https://stats.nba.com/stats/playergamelogs','parameters':o.parameters,'retrieved_at':stamp()},indent=2))
    f=read_frame(path);f.GAME_ID=f.GAME_ID.astype(str).str.zfill(10)
    if f.empty or f.duplicated(['GAME_ID','PLAYER_ID']).any():raise ValueError('Empty/duplicate NBA logs')
    return f

def raw_game(season,gid,fetch=True):
    path=OUT/'raw'/f'{season}_{gid}.json.gz'
    old=PRIMARY/f'cache/nba.com/and-one-pbp/{season}_{gid}.json'
    if path.exists():
        with gzip.open(path,'rt') as h:raw=json.load(h)
        return pd.DataFrame(raw['records']),str(path.relative_to(ROOT)),raw['retrieved_at']
    if old.exists():
        records=json.loads(old.read_text())
        path.parent.mkdir(parents=True,exist_ok=True)
        raw={'records':records,'url':'https://stats.nba.com/stats/playbyplayv3',
             'source_path':str(old),'source_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
             'retrieved_at':None,'archived_at':stamp(),
             'note':'Reused normalized NBA actions; original capture time and complete request metadata unavailable.'}
        with gzip.open(path,'wt') as h:json.dump(raw,h,separators=(',',':'))
        return pd.DataFrame(records),str(path.relative_to(ROOT)),None
    if not fetch:return None,None,None
    o=request(lambda:playbyplayv3.PlayByPlayV3(game_id=gid,headers=_NBA_HEADERS,timeout=30),gid)
    f=o.get_data_frames()[0]
    if f.empty:raise ValueError(f'Empty PBP {gid}')
    captured=stamp();path.parent.mkdir(parents=True,exist_ok=True)
    raw={'url':'https://stats.nba.com/stats/playbyplayv3','parameters':o.parameters,'retrieved_at':captured,'response':o.get_dict(),'records':json.loads(f.to_json(orient='records'))}
    tmp=path.with_suffix('.tmp')
    with gzip.open(tmp,'wt') as h:json.dump(raw,h,separators=(',',':'))
    tmp.rename(path)
    time.sleep(.15)
    return f,str(path.relative_to(ROOT)),captured

def game_assist_bounds(game_logs):
    """A passer cannot assist more threes/twos than his teammates made."""
    f=game_logs.copy()
    teammates=f.groupby(['GAME_ID','TEAM_ID'])[['FGM','FG3M']].transform('sum')-f[['FGM','FG3M']]
    maximum_threes=pd.concat([f.AST,teammates.FG3M],axis=1).min(axis=1)
    minimum_threes=(f.AST-(teammates.FGM-teammates.FG3M)).clip(lower=0)
    f['minimum_assist_points']=2*f.AST+minimum_threes
    f['maximum_assist_points']=2*f.AST+maximum_threes
    if (f.minimum_assist_points>f.maximum_assist_points).any():
        raise ValueError('Official assists exceed teammates made field goals')
    return f

def intervals(box,known):
    f=box[['PLAYER_NAME','PTS','AST']].copy()
    for col in ['known_ast','known_assist_points']:
        f[col]=known[col].reindex(f.index,fill_value=0).astype(int)
    f['remaining_ast']=f.AST-f.known_ast
    if (f.remaining_ast<0).any():raise ValueError('Extracted assists exceed official totals')
    if 'minimum_assist_points' in box:
        f['minimum_created']=f.PTS+f.known_assist_points+box.minimum_assist_points-known.resolved_minimum
        f['maximum_created']=f.PTS+f.known_assist_points+box.maximum_assist_points-known.resolved_maximum
    else:
        f['minimum_created']=f.PTS+f.known_assist_points+2*f.remaining_ast
        f['maximum_created']=f.PTS+f.known_assist_points+3*f.remaining_ast
    if (f.minimum_created>f.maximum_created).any():raise ValueError('Invalid comparison interval')
    return f

def compare(f,selected):
    rows=[]
    for r in selected.itertuples():
        for pid,p in f.iterrows():
            if pid==r.PLAYER_ID:continue
            relation='above' if p.minimum_created>r.created else 'not_above' if p.maximum_created<=r.created else 'unresolved'
            rows.append({'season':r.season,'target_id':r.PLAYER_ID,'target_name':r.PLAYER_NAME,'target_created':int(r.created),'opponent_id':int(pid),'opponent_name':p.PLAYER_NAME,'minimum_created':int(p.minimum_created),'maximum_created':int(p.maximum_created),'remaining_ast':int(p.remaining_ast),'relation':relation})
    return pd.DataFrame(rows)

def run_season(season,selected):
    box=league(season); game_logs=logs(season)
    sums=game_logs.groupby('PLAYER_ID')[['PTS','AST','FGM','FG3M']].sum()
    sums['GP']=game_logs.groupby('PLAYER_ID').size()
    official=box[['PTS','AST','FGM','FG3M','GP']]
    if set(sums.index)!=set(official.index) or not sums.reindex(official.index).eq(official).all().all():
        sums.join(official,lsuffix='_games',rsuffix='_season',how='outer').to_csv(OUT/f'box-discrepancies-{season}.csv')
        raise ValueError(f'{season}: game logs and season scoring/assists/games disagree')
    team_points=int(game_logs.loc[game_logs.TEAM_ID==CHI,'PTS'].sum())
    if not selected.team_points.eq(team_points).all():
        raise ValueError(f'{season}: Chicago season denominator disagrees')
    game_logs=game_assist_bounds(game_logs)
    box=box.join(game_logs.groupby('PLAYER_ID')[['minimum_assist_points','maximum_assist_points']].sum())
    by_game={str(g):f for g,f in game_logs.groupby('GAME_ID')}
    known=pd.DataFrame(0,index=box.index,columns=['known_ast','known_assist_points','resolved_minimum','resolved_maximum'])
    processed=set(); event_frames=[];issues_all=[];sources=[]
    def process(gid,fetch):
        frame,path,captured=raw_game(season,gid,fetch)
        if frame is None:return False
        events,issues=parse_game(frame,by_game[gid]);processed.add(gid)
        badteams={x['team_id'] for x in issues if x.get('severity')=='error'}
        valid=events[~events.team_id.isin(badteams)].copy()
        if len(valid):
            agg=valid.groupby('assister_id').shot_value.agg(['size','sum'])
            known.loc[agg.index,'known_ast']+=agg['size']
            known.loc[agg.index,'known_assist_points']+=agg['sum']
        validated_logs=by_game[gid][~by_game[gid].TEAM_ID.isin(badteams)].set_index('PLAYER_ID')
        known.loc[validated_logs.index,'resolved_minimum']+=validated_logs.minimum_assist_points
        known.loc[validated_logs.index,'resolved_maximum']+=validated_logs.maximum_assist_points
        events['validated_team_game']=~events.team_id.isin(badteams)
        event_frames.append(events);issues_all.extend(issues)
        sources.append({'game_id':gid,'path':path,'retrieved_at':captured,'status':'reconciled' if not badteams else 'excluded_team_games','excluded_teams':sorted(badteams)})
        return True
    for gid in sorted(by_game):process(gid,False)
    def save(f,proof):
        f.to_csv(OUT/f'comparison-intervals-{season}.csv')
        proof.to_csv(OUT/f'rank-proof-{season}.csv',index=False)
        pd.concat(event_frames,ignore_index=True).to_csv(OUT/f'assisted-baskets-{season}.csv.gz',index=False)
        (OUT/f'issues-{season}.json').write_text(json.dumps(issues_all,indent=2))
        (OUT/f'sources-{season}.json').write_text(json.dumps({'generated_at':stamp(),'season':season,'games':sources},indent=2))
    # Full Chicago games are already cached, and must reproduce the graphic totals.
    bulls_games=set(game_logs[game_logs.TEAM_ID==CHI].GAME_ID)
    for gid in sorted(bulls_games-processed):process(gid,True)
    all_events=pd.concat(event_frames,ignore_index=True)
    chi=all_events[(all_events.team_id==CHI)&all_events.validated_team_game].groupby('assister_id').shot_value.agg(['size','sum'])
    for r in selected.itertuples():
        if int(box.loc[r.PLAYER_ID,'PTS'])!=int(r.PTS) or int(box.loc[r.PLAYER_ID,'AST'])!=int(r.AST):
            raise ValueError(f'{season}: target has a different full-league stint; review rank scope')
        player_logs=game_logs[(game_logs.TEAM_ID==CHI)&(game_logs.PLAYER_ID==r.PLAYER_ID)]
        if int(player_logs.PTS.sum())!=int(r.PTS) or len(player_logs)!=int(r.GP) or int(r.created)!=int(r.PTS+r.assist_pts):
            raise ValueError(f'Bulls scoring/games/created discrepancy {season} {r.PLAYER_NAME}')
        if r.PLAYER_ID not in chi.index or int(chi.loc[r.PLAYER_ID,'sum'])!=int(r.assist_pts) or int(chi.loc[r.PLAYER_ID,'size'])!=int(r.AST):
            raise ValueError(f'Bulls source discrepancy {season} {r.PLAYER_NAME}')
    count=0
    while True:
        f=intervals(box,known);proof=compare(f,selected)
        uncertain=set(proof.loc[proof.relation=='unresolved','opponent_id'])
        if count%20==0:
            save(f,proof)
            print(f'{season}: {len(processed)}/{len(by_game)} games; {len(uncertain)} uncertain players; {int((proof.relation=="unresolved").sum())} unresolved comparisons',flush=True)
        if not uncertain:break
        # Favor games containing the most still-relevant official assists.
        pending=game_logs[game_logs.PLAYER_ID.isin(uncertain)&~game_logs.GAME_ID.isin(processed)]
        weights=pending.groupby('GAME_ID').AST.sum().sort_values(ascending=False,kind='stable')
        if weights.empty or weights.iloc[0]==0:
            save(f,proof);raise ValueError(f'{season}: unresolved ranks require reconciliation of excluded game(s)')
        process(str(weights.index[0]),True);count+=1
    save(f,proof)
    ranks=[]
    for r in selected.itertuples():
        p=proof[proof.target_id==r.PLAYER_ID]
        ranks.append({'PLAYER_ID':int(r.PLAYER_ID),'PLAYER_NAME':r.PLAYER_NAME,'season':season,'old_nba_rank':int(r.nba_rank),'nba_rank':1+int((p.relation=='above').sum()),'league_players':len(box),'games_in_season':len(by_game),'games_inspected':len(processed),'unresolved_comparisons':0})
    pd.DataFrame(ranks).to_csv(OUT/f'verified-ranks-{season}.csv',index=False)
    print(f'CERTIFIED {season}: '+str(ranks),flush=True)
    return ranks

def finalize(selected):
    """Publish a canonical render input only when every opponent is classified."""
    paths=[OUT/f'verified-ranks-{s}.csv' for s in selected.season.unique()]
    if not all(p.exists() for p in paths):return False
    result=pd.concat([pd.read_csv(p) for p in paths],ignore_index=True)
    checked=[]
    for season,targets in selected.groupby('season'):
        proof=pd.read_csv(OUT/f'rank-proof-{season}.csv')
        box=league(season)
        if not proof.relation.isin(['above','not_above']).all():raise ValueError('Incomplete proof')
        for r in targets.itertuples():
            p=proof[proof.target_id==r.PLAYER_ID]
            if set(p.opponent_id)!=set(box.index)-{r.PLAYER_ID} or p.opponent_id.duplicated().any():
                raise ValueError('Incomplete/duplicate league comparison population')
            if not p.target_created.eq(r.created).all():raise ValueError('Stale target in proof')
            if not p.loc[p.relation=='above','minimum_created'].gt(r.created).all():raise ValueError('Invalid above proof')
            if not p.loc[p.relation=='not_above','maximum_created'].le(r.created).all():raise ValueError('Invalid not-above proof')
            rank=1+int(p.relation.eq('above').sum())
            stored=result[(result.season==season)&(result.PLAYER_ID==r.PLAYER_ID)]
            if len(stored)!=1 or int(stored.iloc[0].nba_rank)!=rank:raise ValueError('Certificate disagreement')
            checked.append({'season':season,'PLAYER_ID':r.PLAYER_ID,'nba_rank':rank})
    final=selected.drop(columns=['nba_rank']).merge(pd.DataFrame(checked),on=['season','PLAYER_ID'],validate='one_to_one')
    if len(final)!=15:raise ValueError('Expected all 15 verified ranks')
    final['created_per_game']=final.created/final.GP
    final['team_pct']=100*final.created/final.team_points
    final['nba_rank_source']='NBA.com'
    final=final.sort_values('created',ascending=False)
    final.to_csv(DATA/'nba-top15.csv',index=False)
    result.to_csv(OUT/'verified-ranks.csv',index=False)
    proof_paths=[OUT/f'rank-proof-{s}.csv' for s in selected.season.unique()]
    (OUT/'verification-summary.json').write_text(json.dumps({
        'generated_at':stamp(),'status':'complete','selected_rows':15,
        'method':'Exact competition ranks from NBA scoring and NBA play-by-play with conservative official box-score bounds for unexamined assists.',
        'unresolved_comparisons':0,
        'rank_changes':json.loads(result[result.nba_rank!=result.old_nba_rank].to_json(orient='records')),
        'proof_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in proof_paths},
    },indent=2))
    print('ALL 15 RANKS CERTIFIED; data/nba-top15.csv written',flush=True)
    return True

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--season');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    selected=pd.read_csv(DATA/'preview-since-1996.csv')
    expected=pd.read_csv(DATA/'bulls-source-totals.csv').nlargest(15,'created')
    if set(zip(selected.PLAYER_ID,selected.season))!=set(zip(expected.PLAYER_ID,expected.season)):
        raise ValueError('Selection disagrees with the full Bulls history')
    seasons=[args.season] if args.season else ['2010-11']+[s for s in sorted(selected.season.unique()) if s!='2010-11']
    for season in seasons:run_season(season,selected[selected.season==season])
    finalize(selected)
if __name__=='__main__':main()
