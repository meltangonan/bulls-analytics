"""Data-only comparison; NBA Bulls totals plus full-league pbpstats ranks."""
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

ROOT = Path('/Users/meltangonan/projects/bulls-analytics')
HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
SOURCE = Path('/Users/meltangonan/.codex/visualizations/2026/09/21/01a0c4d8-44a0-7d93-b091-a8e0d7f6f4b5/bulls-points-created-1996-2026.csv')
d = pd.read_csv(DATA / 'bulls-source-totals.csv' if (DATA / 'bulls-source-totals.csv').exists() else SOURCE)
d.to_csv(DATA / 'bulls-source-totals.csv', index=False)
d['start'] = d.season.str[:4].astype(int)
cuts = [('2000s', 2000, 2009, 10), ('2010s', 2010, 2019, 10), ('2020s', 2020, 2025, 10), ('since-2000', 2000, 2025, 15), ('since-1996', 1996, 2025, 15)]
selected = pd.concat([d[d.start.between(lo, hi)].nlargest(n, 'created') for _, lo, hi, n in cuts]).drop_duplicates(['PLAYER_ID', 'season'])
audits = []
for season in sorted(selected.season.unique(), key=lambda s: (int(s[:4]) < 2000, s)):
    path = DATA / 'raw' / f'league-{season}.json'
    params = dict(Season=season, SeasonType='Regular Season', Type='Player')
    if not path.exists():
        try:
            r = requests.get('https://api.pbpstats.com/get-totals/nba', params=params, timeout=50)
        except requests.RequestException as exc:
            print('UNAVAILABLE', season, type(exc).__name__, flush=True)
            continue
        if not r.ok:
            print('UNAVAILABLE', season, r.status_code, flush=True)
            continue
        payload = r.json()
        assert len(payload['multi_row_table_data']) > 300
        path.write_text(json.dumps(dict(url=r.url, retrieved_utc=datetime.now(timezone.utc).isoformat(), response=payload)))
    league = pd.DataFrame(json.loads(path.read_text())['response']['multi_row_table_data'])
    assert not league.EntityId.duplicated().any()
    # This endpoint returns sparse event counters: absent counting keys mean no events.
    for key in ['Points', 'AssistPoints', 'TwoPtAssists', 'ThreePtAssists']:
        league[key] = league[key].fillna(0)
    assert (league.AssistPoints == 2 * league.TwoPtAssists + 3 * league.ThreePtAssists).all()
    league['created'] = league.Points + league.AssistPoints
    league['rank'] = league.created.rank(method='min', ascending=False).astype(int)
    league['EntityId'] = league.EntityId.astype(int)
    league[['EntityId', 'Name', 'Points', 'AssistPoints', 'created', 'rank']].sort_values('rank').to_csv(DATA / f'league-ranked-{season}.csv', index=False)
    year = int(season[:4]) + 1
    box = pd.read_csv(ROOT / f'docs/visuals/2026-09-03-bench-points-season/data/raw/chi-total-{year}.csv')
    team_pts = int(box.PTS.sum())
    log_path = ROOT / f'docs/visuals/2026-08-08-assist-duos/data/seasons/game-log-{season}.csv'
    if log_path.exists():
        assert team_pts == pd.read_csv(log_path).PTS.sum()
    for ix, row in selected[selected.season == season].iterrows():
        match = league[league.EntityId == row.PLAYER_ID]
        assert len(match) == 1
        match = match.iloc[0]
        points_diff = match.Points - row.PTS
        assist_diff = match.AssistPoints - row.assist_pts
        # All selected seasons are complete Bulls stints; audit source differences explicitly.
        nba_rank = 1 + int(((league.created > row.created) & (league.EntityId != row.PLAYER_ID)).sum())
        selected.loc[ix, 'nba_rank'] = nba_rank
        selected.loc[ix, 'team_points'] = team_pts
        selected.loc[ix, 'team_pct'] = 100 * row.created / team_pts
        audits.append(dict(season=season, player=row.PLAYER_NAME, nba_points=row.PTS, nba_assist_points=row.assist_pts, pbpstats_points=match.Points, pbpstats_assist_points=match.AssistPoints, points_diff=points_diff, assist_diff=assist_diff, nba_rank=nba_rank, league_players=len(league), team_points=team_pts))
    print(season, len(league), 'players; Bulls points', team_pts, flush=True)
pd.DataFrame(audits).to_csv(DATA / 'source-audit.csv', index=False)
selected.to_csv(DATA / 'selected-with-context.csv', index=False)
sections = []
for label, lo, hi, n in cuts:
    cut = selected[selected.start.between(lo, hi)].nlargest(n, 'created').copy()
    cut['PLAYER_NAME'] = cut.PLAYER_NAME.replace({'Jimmy Butler III': 'Jimmy Butler'})
    cut.to_csv(DATA / f'{label}.csv', index=False)
    cols = ['PLAYER_NAME', 'season', 'PTS', 'assist_pts', 'created', 'nba_rank', 'team_pct']
    cut['nba_rank'] = cut.nba_rank.astype('Int64')
    cut['team_pct'] = cut.team_pct.map(lambda x: f'{x:.1f}%')
    sections.append(label + '\n' + cut[cols].to_string(index=False))
(DATA / 'tables.txt').write_text('\n\n'.join(sections))
print('\n\n'.join(sections))
print('SOURCE DIFFERENCES:', [x for x in audits if x['points_diff'] or x['assist_diff']])
