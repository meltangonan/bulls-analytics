"""Independently replay NBA sources for season leaders and target-rank checks."""
from __future__ import annotations
import gzip,json,sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.prototypes.points_created_games_nba_ranks import (
 DATA,OUT,logs,raw_game,normalize_literal_first_prefixes,parse_game,
 certificate,classify,sha,dump,stamp,ordinal,
)
DEST=OUT/'leaderboards'

def run(season,limit):
    # Begin from original league box populations, not previously computed totals.
    f=logs(season)
    targets=pd.read_csv(DATA/'top15.csv',dtype={'GAME_ID':str})
    targets=targets[targets.season==season]
    guaranteed=int(f.minimum_created.nlargest(limit).min())
    threshold=min(guaranteed,int(targets.created.min()))
    candidates=f[f.maximum_created>=threshold]
    sources=[];events_all=[];issues_all=[]
    print(f'{season}: independent replay {candidates.GAME_ID.nunique()} games; threshold={threshold}',flush=True)
    for gid in candidates.GAME_ID.drop_duplicates():
        rows=f[f.GAME_ID==gid];frame,source=raw_game(season,gid)
        normalized,changes=normalize_literal_first_prefixes(frame,rows)
        events,issues=parse_game(normalized,rows)
        if any(i.get('severity')=='error' for i in issues):
            dump(DEST/f'issues-{season}.json',issues);raise ValueError(f'Independent source replay failed {gid}')
        values=events.groupby('assister_id').shot_value.sum()
        for idx,row in rows.iterrows():
            value=int(values.get(row.PLAYER_ID,0));total=int(row.PTS)+value
            f.loc[idx,'assist_pts']=value;f.loc[idx,'created']=total
            f.loc[idx,['minimum_created','maximum_created']]=total
            f.loc[idx,'status']='exact'
        source['assister_name_normalizations']=changes;sources.append(source)
        events_all.append(events);issues_all.extend(issues)
    exact=f[f.created.notna()].sort_values(['created','GAME_DATE','PLAYER_ID'],ascending=[False,True,True])
    cutoff=int(exact.iloc[limit-1].created)
    if f.loc[f.created.isna(),'maximum_created'].ge(cutoff).any():raise ValueError('Leaderboard cutoff not certified')
    leaders=exact[exact.created>=cutoff].copy()
    leaders['rank']=leaders.created.astype(int).rank(method='min',ascending=False).astype(int)
    ties=leaders.groupby('created').created.transform('size')
    leaders['rank_label']=[f'T-{ordinal(r)}' if t>1 else ordinal(r) for r,t in zip(leaders['rank'],ties)]
    leaders['GAME_DATE']=pd.to_datetime(leaders.GAME_DATE).dt.strftime('%Y-%m-%d')
    leaders['season']=season
    cols=['rank','rank_label','PLAYER_NAME','PLAYER_ID','GAME_ID','GAME_DATE','MATCHUP','WL','PTS','AST','assist_pts','created','season']
    leaders=leaders[cols]
    proofs=[];rechecked=[]
    for target in targets.itertuples():
        c=certificate(f,target)
        if c['nba_season_rank']!=target.nba_season_rank or c['nba_season_tie_count']!=target.nba_season_tie_count:raise ValueError('Published target certificate differs from independent replay')
        rechecked.append(c)
        p=f[['GAME_ID','PLAYER_ID','PLAYER_NAME','minimum_created','maximum_created','status']].copy()
        p['target_game_id']=target.GAME_ID;p['target_created']=target.created;p['relation']=classify(f,int(target.created));proofs.append(p)
    leaders.to_csv(DEST/f'top{limit}-with-ties-{season}.csv',index=False)
    f.to_csv(DEST/f'population-proof-{season}.csv.gz',index=False)
    pd.concat(proofs,ignore_index=True).to_csv(DEST/f'target-recheck-proof-{season}.csv.gz',index=False)
    pd.concat(events_all,ignore_index=True).to_csv(DEST/f'assisted-baskets-{season}.csv.gz',index=False)
    dump(DEST/f'sources-{season}.json',{'season':season,'games':sources,'league_box':str((OUT/f'player-game-logs-{season}.json').relative_to(ROOT)),'league_box_sha256':sha(OUT/f'player-game-logs-{season}.json'),'coverage_source':str((OUT/f'league-summary-{season}.json').relative_to(ROOT)),'coverage_source_sha256':sha(OUT/f'league-summary-{season}.json')})
    dump(DEST/f'issues-{season}.json',issues_all)
    dump(DEST/f'verification-summary-{season}.json',{'generated_at':stamp(),'status':'complete','method':'Independent replay from original full-league NBA box logs and raw PBP; no reuse of derived points-created totals.','leaderboard_limit':limit,'display_rows':len(leaders),'cutoff_created':cutoff,'population_player_games':len(f),'population_games':int(f.GAME_ID.nunique()),'pbp_games_replayed':len(sources),'maximum_unresolved_bound':int(f.loc[f.created.isna(),'maximum_created'].max()),'source_errors':0,'source_warnings':sum(i.get('severity')=='warning' for i in issues_all),'targets_rechecked':rechecked,'published_ranks_changed':False,'proof_sha256':{p.name:sha(p) for p in DEST.glob(f'*{season}*') if p.suffix in ['.gz','.csv']}})
    print(leaders.to_string(index=False),flush=True)

def main():
    DEST.mkdir(exist_ok=True)
    for season,limit in [('2010-11',3),('2023-24',10)]:run(season,limit)
if __name__=='__main__':main()
