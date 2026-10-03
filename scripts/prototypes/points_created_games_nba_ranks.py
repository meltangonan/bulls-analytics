"""Certify NBA season competition ranks for selected individual player-games.

All regular-season player-games count, including another game by the same player.
Box-derived intervals are proofs, never estimates; resolve every interval that
could equal or cross a selected total with reconciled NBA assisted baskets.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, re, shutil, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from nba_api.stats.endpoints import playergamelogs, playbyplayv3
from bulls.data.fetch import _NBA_HEADERS
from scripts.prototypes.points_created_nba_parse import parse_game
from scripts.prototypes.assist_duos_fetch import surname_key
from scripts.prototypes.points_created_nba_ranks import game_assist_bounds,read_frame
DATA=ROOT/'docs/visuals/2026-10-02-points-created-games/data'
OUT=DATA/'nba-game-ranks'
OLD=ROOT/'docs/visuals/2026-09-21-points-created/data/nba-league'

def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(path,obj): path.write_text(json.dumps(obj,indent=2))
def request(factory,label):
    for attempt in range(3):
        try: return factory()
        except Exception as e:
            print(f'RETRY {label}: {e}',flush=True)
            if attempt==2: raise
            time.sleep(2+attempt*3)

def validate_population(f,summary):
    required=['GAME_ID','PLAYER_ID','TEAM_ID','PTS','AST','FGM','FG3M']
    if f.empty or f[required].isna().any().any() or f.duplicated(['GAME_ID','PLAYER_ID']).any():
        raise ValueError('Empty/missing/duplicate NBA player-game population')
    sums=f.groupby('PLAYER_ID')[['PTS','AST','FGM','FG3M']].sum()
    sums['GP']=f.groupby('PLAYER_ID').size()
    official=summary.set_index('PLAYER_ID')[['PTS','AST','FGM','FG3M','GP']]
    if official.index.duplicated().any() or set(sums.index)!=set(official.index) or not sums.reindex(official.index).eq(official).all().all():
        raise ValueError('NBA game-log population disagrees with official full-season totals')
    if not f.groupby('GAME_ID').TEAM_ID.nunique().eq(2).all():
        raise ValueError('Incomplete game roster population')

def logs(season):
    path=OUT/f'player-game-logs-{season}.json'
    source=OLD/path.name
    if not path.exists():
        if source.exists():
            shutil.copyfile(source,path)
            dump(path.with_suffix('.meta.json'),{'source_path':str(source.relative_to(ROOT)),'source_sha256':sha(source),'archived_at':stamp()})
        else:
            obj=request(lambda:playergamelogs.PlayerGameLogs(season_nullable=season,season_type_nullable='Regular Season',headers=_NBA_HEADERS,timeout=30),season)
            path.write_text(obj.get_json())
            dump(path.with_suffix('.meta.json'),{'endpoint':'https://stats.nba.com/stats/playergamelogs','parameters':obj.parameters,'retrieved_at':stamp()})
    summary=OUT/f'league-summary-{season}.json'
    if not summary.exists():
        choices=[OLD/summary.name,ROOT/f'docs/visuals/2026-09-19-block-leaders/data/raw/league-{season}.json',ROOT/f'docs/visuals/2026-09-21-points-created/data/raw/league-{season}.json']
        source=next((p for p in choices if p.exists()),None)
        if source is None: raise ValueError(f'Missing official season coverage source {season}')
        shutil.copyfile(source,summary)
        dump(summary.with_suffix('.meta.json'),{'source_path':str(source.relative_to(ROOT)),'source_sha256':sha(source),'archived_at':stamp(),'endpoint':'https://stats.nba.com/stats/leaguedashplayerstats','parameters':json.loads(source.read_text()).get('parameters')})
    f=read_frame(path);f.GAME_ID=f.GAME_ID.astype(str).str.zfill(10)
    validate_population(f,read_frame(summary))
    f=game_assist_bounds(f)
    f['minimum_created']=f.PTS+f.minimum_assist_points
    f['maximum_created']=f.PTS+f.maximum_assist_points
    f['created']=pd.NA;f['assist_pts']=pd.NA
    f['status']='bounded'
    return f

def classify(f,total):
    """Equality needs an exact interval, except intervals strictly below/above."""
    return pd.Series(['above' if lo>total else 'below' if hi<total else 'equal' if lo==hi==total else 'unresolved'
                      for lo,hi in zip(f.minimum_created,f.maximum_created)],index=f.index)

def ordinal(n):
    suffix='th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')
    return f'{n}{suffix}'

def certificate(f,target):
    relations=classify(f,int(target.created))
    if relations.eq('unresolved').any(): raise ValueError('Unavailable/unresolved source can affect rank or ties')
    own=f[(f.PLAYER_ID==target.PLAYER_ID)&(f.GAME_ID==target.GAME_ID)]
    if len(own)!=1 or not relations.loc[own.index].eq('equal').all(): raise ValueError('Target reconciliation missing')
    rank=1+int(relations.eq('above').sum());ties=int(relations.eq('equal').sum())
    return {'season':target.season,'GAME_ID':target.GAME_ID,'PLAYER_ID':int(target.PLAYER_ID),'created':int(target.created),'nba_season_rank':rank,'nba_season_rank_label':f'T-{ordinal(rank)}' if ties>1 else ordinal(rank),'nba_season_tie_count':ties,'nba_season_rank_status':'complete','population_player_games':len(f),'population_games':f.GAME_ID.nunique(),'unresolved_comparisons':0}

def raw_game(season,gid):
    path=OUT/'raw'/f'{season}_{gid}.json.gz';path.parent.mkdir(exist_ok=True)
    source=OLD/'raw'/path.name
    if not path.exists() and source.exists(): shutil.copyfile(source,path)
    if not path.exists():
        obj=request(lambda:playbyplayv3.PlayByPlayV3(game_id=gid,headers=_NBA_HEADERS,timeout=30),gid)
        frame=obj.get_data_frames()[0]
        if frame.empty: raise ValueError(f'Unavailable PBP {gid}')
        with gzip.open(path,'wt') as h: json.dump({'records':json.loads(frame.to_json(orient='records')),'response':obj.get_dict(),'parameters':obj.parameters,'retrieved_at':stamp(),'url':'https://stats.nba.com/stats/playbyplayv3'},h,separators=(',',':'))
        time.sleep(.15)
    with gzip.open(path,'rt') as h: raw=json.load(h)
    return pd.DataFrame(raw['records']),{'game_id':gid,'path':str(path.relative_to(ROOT)),'sha256':sha(path),'retrieved_at':raw.get('retrieved_at'),'reused_source':str(source.relative_to(ROOT)) if source.exists() else None}

def normalize_literal_first_prefixes(frame,logs):
    """NBA sometimes emits Marc Morris instead of Marc. Morris.

    Add punctuation only when the same-team box roster uniquely identifies the
    literal first-name prefix and surname. Keep raw replies unchanged.
    """
    result=frame.copy();changes=[]
    historical={202683:'Kanter',1627815:'McClellan'}
    for pid,alias in historical.items():
        own=frame[frame.personId==pid]
        roster=logs[logs.PLAYER_ID==pid]
        if own.empty or roster.empty or not frame.description.fillna('').str.contains(r'\('+re.escape(alias)+r' \d+ AST\)',regex=True).any(): continue
        evidence=own[own.description.fillna('').str.contains(r'\b'+re.escape(alias)+r'\b',regex=True)]
        if evidence.empty: raise ValueError(f'Historical-name alias missing direct NBA person-ID evidence: {pid}')
        team=int(roster.iloc[0].TEAM_ID);replacement=roster.iloc[0].PLAYER_NAME
        collisions=logs[(logs.TEAM_ID==team)&(logs.PLAYER_ID!=pid)].PLAYER_NAME.map(lambda n: surname_key(' '.join(n.split()[1:]))==surname_key(alias))
        if collisions.any(): raise ValueError(f'Ambiguous historical name alias {alias}')
        for idx in result[result.teamId==team].index:
            description=result.loc[idx,'description']
            if not isinstance(description,str): continue
            updated=re.sub(r'\('+re.escape(alias)+r' (\d+ AST\))',lambda m:'('+replacement+' '+m.group(1),description)
            if updated!=description:
                result.loc[idx,'description']=updated
                changes.append({'action_number':int(result.loc[idx,'actionNumber']),'raw_assister':alias,'normalized_assister':replacement,'player_id':pid,'rule':'Historical name tied to NBA person-ID by own raw actions','evidence_action_number':int(evidence.iloc[0].actionNumber),'evidence_description':evidence.iloc[0].description})
    for idx in result.index:
        description=result.loc[idx,'description']
        if isinstance(description,str):
            updated=re.sub(r'(\([^()]+), (Jr\.|Sr\.) (\d+ AST\))',r'\1 \2 \3',description)
            if updated!=description:
                result.loc[idx,'description']=updated
                changes.append({'action_number':int(result.loc[idx,'actionNumber']),'rule':'Remove comma before generational suffix','original_description':description,'normalized_description':updated})
    for idx,row in result.iterrows():
        description=row.description
        if not isinstance(description,str): continue
        match=re.search(r'\(([^()]+) \d+ AST\)',description)
        if not match: continue
        raw=match.group(1);parts=raw.split()
        if len(parts)<2 or '.' in parts[0]: continue
        prefix=parts[0];surname=' '.join(parts[1:])
        candidates=[]
        for player in logs[logs.TEAM_ID==row.teamId].itertuples():
            name=player.PLAYER_NAME.split()
            if len(name)>1 and name[0].lower().startswith(prefix.lower()) and name[0].lower()!=prefix.lower() and surname_key(' '.join(name[1:]))==surname_key(surname): candidates.append(player.PLAYER_ID)
        if len(candidates)==1:
            dotted=f'{prefix}. {surname}'
            result.loc[idx,'description']=description[:match.start(1)]+dotted+description[match.end(1):]
            changes.append({'action_number':int(row.actionNumber),'raw_assister':raw,'normalized_assister':dotted,'player_id':int(candidates[0]),'rule':'unique literal first-name prefix within same-team official roster'})
    return result,changes

def run_season(season,targets):
    f=logs(season);events_all=[];sources=[];issues_all=[];processed=set()
    prior=OUT/f'population-proof-{season}.csv.gz'
    if prior.exists():
        saved=pd.read_csv(prior,dtype={'GAME_ID':str})
        if not saved[['GAME_ID','PLAYER_ID','PTS','AST']].equals(f[['GAME_ID','PLAYER_ID','PTS','AST']]): raise ValueError('Cached population proof disagrees with official game logs')
        f=saved
        prior_sources=json.loads((OUT/f'sources-{season}.json').read_text())['games']
        still_needed=set(f.loc[pd.concat([classify(f,int(t)).eq('unresolved') for t in targets.created.unique()],axis=1).any(axis=1),'GAME_ID'])
        sources=[x for x in prior_sources if x['game_id'] not in still_needed]
        old_events=pd.read_csv(OUT/f'assisted-baskets-{season}.csv.gz',dtype={'game_id':str})
        events_all=[old_events[~old_events.game_id.isin(still_needed)]]
        issues_all=[x for x in json.loads((OUT/f'issues-{season}.json').read_text()) if x['game_id'] not in still_needed]
    totals=sorted(set(targets.created.astype(int)))
    def unresolved():
        return pd.concat([classify(f,t).eq('unresolved') for t in totals],axis=1).any(axis=1)
    pending=f[unresolved()]
    cached=sum((OLD/'raw'/f'{season}_{gid}.json.gz').exists() for gid in pending.GAME_ID.unique())
    print(f'{season}: population={len(f)} games={f.GAME_ID.nunique()} candidates={len(pending)} candidate-games={pending.GAME_ID.nunique()} cached={cached}',flush=True)
    # Reconcile own target games even if their original bounds happen to be exact.
    order=list(dict.fromkeys(list(targets.GAME_ID)+list(pending.sort_values('maximum_created',ascending=False).GAME_ID)))
    for gid in order:
        rows=f[f.GAME_ID==gid]
        if not unresolved().loc[rows.index].any() and rows.created.notna().all(): continue
        if gid not in set(targets.GAME_ID) and not unresolved().loc[rows.index].any(): continue
        frame,source=raw_game(season,gid)
        normalized,changes=normalize_literal_first_prefixes(frame,rows)
        events,issues=parse_game(normalized,rows)
        source['assister_prefix_normalizations']=changes
        bad={i['team_id'] for i in issues if i.get('severity')=='error'}
        valid=events[~events.team_id.isin(bad)]
        values=valid.groupby('assister_id').shot_value.sum()
        for idx,row in rows.iterrows():
            if row.TEAM_ID in bad: continue
            value=int(values.get(row.PLAYER_ID,0));f.loc[idx,'assist_pts']=value;f.loc[idx,'created']=int(row.PTS)+value
            f.loc[idx,['minimum_created','maximum_created']]=int(row.PTS)+value;f.loc[idx,'status']='exact'
        source['excluded_teams']=sorted(bad);sources.append(source);issues_all.extend(issues)
        events['validated_team_game']=~events.team_id.isin(bad);events_all.append(events);processed.add(gid)
        if len(processed)%20==0: print(f'{season}: resolved {len(processed)} games; unresolved rows={int(unresolved().sum())}',flush=True)
    f.to_csv(OUT/f'population-proof-{season}.csv.gz',index=False)
    pd.concat(events_all,ignore_index=True).to_csv(OUT/f'assisted-baskets-{season}.csv.gz',index=False)
    dump(OUT/f'issues-{season}.json',issues_all);dump(OUT/f'sources-{season}.json',{'season':season,'games':sources,'generated_at':stamp()})
    proofs=[];ranks=[]
    for target in targets.itertuples():
        own=f[(f.GAME_ID==target.GAME_ID)&(f.PLAYER_ID==target.PLAYER_ID)].iloc[0]
        if pd.isna(own.created) or int(own.created)!=int(target.created) or int(own.assist_pts)!=int(target.assist_pts):
            raise ValueError(f'Target points-created reconciliation failed {target.GAME_ID}')
        proof=f[['GAME_ID','PLAYER_ID','PLAYER_NAME','PTS','AST','minimum_created','maximum_created','status']].copy()
        proof['target_game_id']=target.GAME_ID;proof['target_player_id']=target.PLAYER_ID;proof['target_created']=target.created
        proof['relation']=classify(f,int(target.created));proofs.append(proof)
        ranks.append(certificate(f,target))
    pd.concat(proofs,ignore_index=True).to_csv(OUT/f'rank-proof-{season}.csv.gz',index=False)
    pd.DataFrame(ranks).to_csv(OUT/f'verified-ranks-{season}.csv',index=False)
    print(f'CERTIFIED {season}: '+str([(r['GAME_ID'],r['nba_season_rank_label'],r['nba_season_tie_count']) for r in ranks]),flush=True)
    return ranks

def finalize(selected):
    paths=[OUT/f'verified-ranks-{s}.csv' for s in selected.season.unique()]
    if not all(p.exists() for p in paths): return False
    ranks=pd.concat([pd.read_csv(p,dtype={'GAME_ID':str,'nba_season_rank_label':str}) for p in paths],ignore_index=True)
    if len(ranks)!=len(selected): raise ValueError('Incomplete selected rank coverage')
    cols=['nba_season_rank','nba_season_rank_label','nba_season_tie_count','nba_season_rank_status']
    for season,targets in selected.groupby('season'):
        f=pd.read_csv(OUT/f'population-proof-{season}.csv.gz',dtype={'GAME_ID':str})
        for target in targets.itertuples():
            verified=certificate(f,target)
            record=ranks[(ranks.season==season)&(ranks.GAME_ID==target.GAME_ID)&(ranks.PLAYER_ID==target.PLAYER_ID)]
            if len(record)!=1 or any(int(record.iloc[0][c])!=int(verified[c]) for c in ['nba_season_rank','nba_season_tie_count']): raise ValueError('Rank certificate disagreement')
            for c in cols: ranks.loc[record.index,c]=verified[c]
        ranks[ranks.season==season].to_csv(OUT/f'verified-ranks-{season}.csv',index=False)
    final=selected.drop(columns=cols,errors='ignore').merge(ranks[['season','GAME_ID','PLAYER_ID']+cols],on=['season','GAME_ID','PLAYER_ID'],how='left',validate='one_to_one')
    if final[cols].isna().any().any(): raise ValueError('Missing selected rank')
    final.to_csv(DATA/'top15.csv',index=False);ranks.to_csv(OUT/'verified-ranks.csv',index=False)
    selection_summary=DATA/'verification-summary.json'
    original=json.loads(selection_summary.read_text())
    original.setdefault('pre_rank_top15_sha256',original['output_sha256']['top15.csv'])
    original['output_sha256']['top15.csv']=sha(DATA/'top15.csv')
    original['nba_season_rank_enrichment']={'verification_summary':'nba-game-ranks/verification-summary.json','note':'Bulls selection and original metric values preserved; NBA ranks added from exact complete season-game proofs.'}
    dump(selection_summary,original)
    dump(OUT/'verification-summary.json',{'generated_at':stamp(),'status':'complete','selected_rows':len(final),'scope':'All NBA regular-season player-games in each target season, including overtime and other games by the same player.','metric':'PTS plus actual points scored on assisted field goals (2 or 3).','rank':'Competition rank: 1 + count of player-games strictly above target; T prefix when >1 player-game equals target.','unresolved_comparisons':0,'proof_sha256':{p.name:sha(p) for p in OUT.glob('*proof-*.csv.gz')},'top15_sha256':sha(DATA/'top15.csv')})
    summary_path=OUT/'verification-summary.json'
    summary=json.loads(summary_path.read_text())
    populations=[];source_rows=[];all_issues=[];normalizations=[]
    for season in selected.season.unique():
        f=pd.read_csv(OUT/f'population-proof-{season}.csv.gz',dtype={'GAME_ID':str})
        source=json.loads((OUT/f'sources-{season}.json').read_text())['games']
        issues=json.loads((OUT/f'issues-{season}.json').read_text())
        populations.append({'season':season,'player_games':len(f),'games':int(f.GAME_ID.nunique()),'resolved_player_games':int(f.status.eq('exact').sum()),'inspected_games':len(source),'proof_comparisons':len(f)*int((selected.season==season).sum())})
        source_rows.extend(source);all_issues.extend(issues)
        normalizations.extend(c for row in source for c in row.get('assister_prefix_normalizations',[]))
    summary.update(populations=populations,population_player_games=sum(p['player_games'] for p in populations),population_games=sum(p['games'] for p in populations),proof_comparisons=sum(p['proof_comparisons'] for p in populations),inspected_games=len(source_rows),old_post_pbp_reused=sum(bool(x.get('reused_source')) for x in source_rows),pbp_new_for_this_post=sum(not bool(x.get('reused_source')) for x in source_rows),source_errors=sum(i.get('severity')=='error' for i in all_issues),source_warnings=sum(i.get('severity')=='warning' for i in all_issues),recorded_name_normalizations=len(normalizations),excluded_source_team_games=[{'game_id':x['game_id'],'team_id':t} for x in source_rows for t in x.get('excluded_teams',[])],endpoints={'league_summary':'https://stats.nba.com/stats/leaguedashplayerstats','game_logs':'https://stats.nba.com/stats/playergamelogs','play_by_play':'https://stats.nba.com/stats/playbyplayv3'})
    dump(summary_path,summary)
    return True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--season');args=ap.parse_args();OUT.mkdir(exist_ok=True)
    selected=pd.read_csv(DATA/'top15.csv',dtype={'GAME_ID':str})
    for season,targets in selected.groupby('season'):
        if args.season and season!=args.season: continue
        verified=OUT/f'verified-ranks-{season}.csv'
        if verified.exists(): print(f'REUSE CERTIFICATE {season}',flush=True);continue
        run_season(season,targets)
    if finalize(selected): print('ALL 16 RANKS VERIFIED; top15.csv enriched',flush=True)
if __name__=='__main__': main()
