"""Independent full-league assist-points comparison, preserving provider differences."""
import html, json, re, time, unicodedata
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import requests
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguedashplayerstats
import sys
ROOT = Path('/Users/meltangonan/projects/bulls-analytics')
sys.path.insert(0, str(ROOT))
from bulls.data.fetch import _NBA_HEADERS
HERE=Path(__file__).resolve().parent
DATA=HERE/'data'
def norm(n):
    n=n.replace('ı','i').replace('ß','ss')
    n=unicodedata.normalize('NFKD', n).encode('ascii','ignore').decode().lower()
    n=re.sub(r'[\s,]+(jr|sr|iii|ii|iv)\.?$', '', n)
    return re.sub('[^a-z]', '', n)
names={norm(p['full_name']):p['id'] for p in players.get_players()}
names.update({'ronartest':1897,'mettaartest':1897,'nenê':2403,'nenehilario':2403,'nene':2403})
names.update({'clarenceweatherspoon':221,'stevesmith':120,'isaacaustin':1134,'dannyschayes':7,'richmanning':316})
names['kiwanelemorrisgarris']=1619
names['ronaldmurray']=2436
names['eugenejeter']=200817
names.update({'ronholland':1641842,'cuiyongxi':1642385})
d=pd.read_csv(DATA/'bulls-source-totals.csv');d['start']=d.season.str[:4].astype(int)
cuts=[('2000s',2000,2009,10),('2010s',2010,2019,10),('2020s',2020,2025,10),('since-2000',2000,2025,15),('since-1996',1996,2025,15)]
selected=pd.concat([d[d.start.between(lo,hi)].nlargest(n,'created') for _,lo,hi,n in cuts]).drop_duplicates(['PLAYER_ID','season'])
all_league=[];audits=[]
for season in sorted(selected.season.unique()):
    y=int(season[:4])+1
    path=DATA/'raw'/f'bbr-{y}-pbp.html'
    if not path.exists():
        r=requests.get(f'https://www.basketball-reference.com/leagues/NBA_{y}_play-by-play.html',timeout=30)
        r.raise_for_status();r.encoding='utf-8';path.write_text(r.text);time.sleep(3)
    text=path.read_text()
    if 'KukoÄ' in text:
        text=text.encode('latin1').decode('utf-8');path.write_text(text)
    block=re.search(r'<table[^>]+id="pbp_stats"[^>]*>(.*?)</table>',text,re.S)
    assert block, (season,'table not found')
    rows=[]
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>',block.group(1),re.S):
        cells={k:html.unescape(re.sub('<[^>]+>','',v)).strip() for k,v in re.findall(r'data-stat="([a-z_0-9]+)"[^>]*>(.*?)</t[dh]>',row,re.S)}
        if not cells.get('name_display') or not cells.get('games','').isdigit():continue
        cells['bbr_id']=re.search(r'/players/[^/]+/([^"/]+)\.html',row).group(1)
        rows.append(cells)
    f=pd.DataFrame(rows)
    # Whole-season combined rows precede individual team stints.
    f=f.drop_duplicates('bbr_id',keep='first')
    nba_path=ROOT/f'docs/visuals/2026-09-19-block-leaders/data/raw/league-{season}.json'
    if not nba_path.exists():
        nba_path=DATA/'raw'/f'nba-league-{season}.json'
        if not nba_path.exists():
            obj=leaguedashplayerstats.LeagueDashPlayerStats(season=season,per_mode_detailed='Totals',headers=_NBA_HEADERS,timeout=30)
            nba_path.write_text(obj.get_json())
    raw=json.loads(nba_path.read_text())['resultSets'][0];nba=pd.DataFrame(raw['rowSet'],columns=raw['headers'])
    season_names={norm(r.PLAYER_NAME):r.PLAYER_ID for r in nba.itertuples()}
    def identify(row):
        n=row.name_display
        candidates=nba[nba.PLAYER_NAME.map(norm)==norm(n)]
        if len(candidates)>1:
            candidates=candidates[candidates.GP==int(row.games)]
            assert len(candidates)==1,(season,n,'ambiguous identity')
        if len(candidates)==1:return candidates.iloc[0].PLAYER_ID
        exact=names.get(norm(n))
        if exact is not None and exact in set(nba.PLAYER_ID):return exact
        tokens=n.split();surname=norm(tokens[-1]);initial=norm(tokens[0])[0]
        candidates=[r.PLAYER_ID for r in nba.itertuples() if norm(r.PLAYER_NAME.split()[-1])==surname and norm(r.PLAYER_NAME)[0]==initial]
        return candidates[0] if len(candidates)==1 else None
    f['PLAYER_ID']=f.apply(identify,axis=1)
    missing=f[f.PLAYER_ID.isna()]
    assert not len(missing),missing.name_display.tolist()
    f['PLAYER_ID']=f.PLAYER_ID.astype(int)
    f['bbr_assist_pts']=pd.to_numeric(f.astd_pts,errors='raise')
    league=nba.merge(f[['PLAYER_ID','bbr_assist_pts']],on='PLAYER_ID',how='outer',indicator=True)
    assert (league['_merge']=='both').all(),league[league['_merge']!='both'][['PLAYER_NAME','PLAYER_ID','_merge']].to_dict('records')
    league['created']=league.PTS+league.bbr_assist_pts
    league['season']=season
    all_league.append(league)
    box=pd.read_csv(ROOT/f'docs/visuals/2026-09-03-bench-points-season/data/raw/chi-total-{y}.csv')
    team_pts=int(box.PTS.sum())
    for ix,r in selected[selected.season==season].iterrows():
        m=league[league.PLAYER_ID==r.PLAYER_ID].iloc[0]
        rank=1+int(((league.created>r.created)&(league.PLAYER_ID!=r.PLAYER_ID)).sum())
        own_rank=1+int((league.created>m.created).sum())
        selected.loc[ix,'nba_rank']=rank
        selected.loc[ix,'team_points']=team_pts
        selected.loc[ix,'team_pct']=r.created/team_pts*100
        selected.loc[ix,'created_per_game']=r.created/r.GP
        audits.append(dict(season=season,PLAYER_ID=r.PLAYER_ID,player=r.PLAYER_NAME,nba_assist_pts=r.assist_pts,bbr_assist_pts=m.bbr_assist_pts,difference=m.bbr_assist_pts-r.assist_pts,rank=rank,bbr_own_rank=own_rank))
    print(season,len(league),'league rows',flush=True)
    pd.concat(all_league).to_csv(DATA/'bbr-league-comparison.csv',index=False)
    pd.DataFrame(audits).to_csv(DATA/'bbr-source-audit.csv',index=False)
    selected.to_csv(DATA/'preview-with-context.csv',index=False)
for label,lo,hi,n in cuts:
    f=selected[selected.start.between(lo,hi)].nlargest(n,'created')
    f.to_csv(DATA/f'preview-{label}.csv',index=False)
    print(label);print(f[['PLAYER_NAME','season','PTS','assist_pts','created','nba_rank','team_pct','created_per_game']].round(1).to_string(index=False))
