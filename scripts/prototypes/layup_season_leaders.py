"""Bulls regular-season layup leaders, 2000-01 through 2025-26.

Raw NBA snapshots and reconciliation stay with this post. Rendering reuses them.
Layups include legacy finger rolls and putback layups, but exclude tips,
dunks and floaters consistently across eras.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
from nba_api.stats.endpoints import shotchartdetail, leaguedashplayerstats, leaguedashteamstats
from bulls.data.fetch import _NBA_HEADERS

TEAM = 1610612741
NBA_TEAM_IDS = [1610612737,1610612738,1610612751,1610612766,1610612752,
                1610612764,1610612753,1610612754,1610612760,1610612750,
                1610612743,1610612757,1610612762,1610612746,1610612756,
                1610612744,1610612742,1610612745,1610612763,1610612749,
                1610612748,1610612761,1610612755,1610612759,1610612765,
                1610612747,1610612758,1610612740,1610612741,1610612739]
DATA = ROOT / 'docs/visuals/2026-09-05-layup-season-leaders/data'


def is_layup(labels: pd.Series) -> pd.Series:
    text = labels.fillna('').str.lower()
    return (text.str.contains('layup|finger roll', regex=True)
            & ~text.str.contains('tip|dunk|floating', regex=True))


def fetch_frame(kind: str, season: str) -> pd.DataFrame:
    path = DATA / 'raw' / f'{kind}_{season}.csv.gz'
    if not path.exists():
        base = dict(headers=_NBA_HEADERS, timeout=35)
        if kind == 'shots':
            cls = shotchartdetail.ShotChartDetail
            params = dict(team_id=TEAM, player_id=0, season_nullable=season,
                          season_type_all_star='Regular Season', context_measure_simple='FGA')
        else:
            cls = (leaguedashplayerstats.LeagueDashPlayerStats if kind == 'players'
                   else leaguedashteamstats.LeagueDashTeamStats)
            params = dict(team_id_nullable=TEAM, season=season,
                          season_type_all_star='Regular Season', per_mode_detailed='Totals')
        for attempt in range(3):
            try:
                frame = cls(**params, **base).get_data_frames()[0]
                if frame.empty:
                    raise ValueError(f'Unavailable: {kind} {season}')
                path.parent.mkdir(parents=True, exist_ok=True)
                frame.to_csv(path, index=False)
                path.with_suffix('').with_suffix('.json').write_text(json.dumps(dict(
                    endpoint=cls.__name__, parameters=params,
                    fetched_at=datetime.now(timezone.utc).isoformat(), rows=len(frame)), indent=2))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        time.sleep(.65)
    return pd.read_csv(path, dtype={'GAME_ID':str, 'GAME_DATE':str})


def fetch_league_season(season: str) -> pd.DataFrame:
    """Fetch every team's shot rows, avoiding the league endpoint's row cap."""
    frames = []
    for team_id in NBA_TEAM_IDS:
        path = DATA / 'league_raw' / f'{team_id}_{season}.csv.gz'
        if not path.exists():
            params = dict(team_id=team_id, player_id=0, season_nullable=season,
                          season_type_all_star='Regular Season', context_measure_simple='FGA')
            frame = shotchartdetail.ShotChartDetail(
                **params, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
            if frame.empty:
                raise ValueError(f'Unavailable league team pull: {team_id} {season}')
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False)
            path.with_suffix('').with_suffix('.json').write_text(json.dumps(dict(
                endpoint='ShotChartDetail', parameters=params,
                fetched_at=datetime.now(timezone.utc).isoformat(), rows=len(frame)), indent=2))
            time.sleep(.65)
        frame = pd.read_csv(path, dtype={'GAME_ID':str, 'GAME_DATE':str})
        if not frame.TEAM_ID.eq(team_id).all():
            raise ValueError(f'Unexpected team rows in {path}')
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def fetch_league_totals(season: str) -> pd.DataFrame:
    path = DATA / 'league_raw' / f'teams_{season}.csv.gz'
    if not path.exists():
        params = dict(season=season, season_type_all_star='Regular Season',
                      per_mode_detailed='Totals')
        frame = leaguedashteamstats.LeagueDashTeamStats(
            **params, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
        if frame.empty:
            raise ValueError(f'Unavailable official league totals: {season}')
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        path.with_suffix('').with_suffix('.json').write_text(json.dumps(dict(
            endpoint='LeagueDashTeamStats', parameters=params,
            fetched_at=datetime.now(timezone.utc).isoformat(), rows=len(frame)), indent=2))
        time.sleep(.65)
    return pd.read_csv(path)


def reconcile_league(shots: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    if shots.duplicated(['GAME_ID', 'GAME_EVENT_ID']).any():
        raise ValueError('Duplicate league shot event')
    totals = shots.groupby('TEAM_ID').agg(shot_fga=('SHOT_MADE_FLAG', 'size'),
        shot_fgm=('SHOT_MADE_FLAG', 'sum'), shot_gp=('GAME_ID', 'nunique'))
    audit = official[['TEAM_ID', 'TEAM_NAME', 'GP', 'FGA', 'FGM']].merge(
        totals, on='TEAM_ID', how='outer', validate='one_to_one')
    for metric in ['fga', 'fgm', 'gp']:
        audit[f'{metric}_delta'] = audit[f'shot_{metric}'] - audit[metric.upper()]
    return audit


def merge_relative_fg(top: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    result = top.merge(baseline, on='SEASON', how='left', validate='many_to_one')
    if result.league_layup_fg_pct.isna().any():
        raise ValueError('Missing seasonal layup baseline')
    result['rFG_PCT'] = (result.FG_PCT - result.league_layup_fg_pct) * 100
    return result


def add_relative_fg() -> None:
    top = pd.read_csv(DATA / 'top15.csv')
    rows, audits = [], []
    for season in top.SEASON.unique():
        league = fetch_league_season(season)
        audit = reconcile_league(league, fetch_league_totals(season))
        audit.insert(0, 'SEASON', season)
        audits.append(audit)
        pd.concat(audits, ignore_index=True).to_csv(DATA / 'league_team_reconciliation.csv', index=False)
        if not audit[['fga_delta', 'fgm_delta', 'gp_delta']].eq(0).all().all():
            raise ValueError(f'League totals mismatch: {season}; inspect saved audit')
        labels = league.ACTION_TYPE.fillna('').str.lower()
        included = labels.str.contains('layup|finger roll') & ~labels.str.contains('tip|dunk|floating')
        excluded_value = included & ~league.SHOT_TYPE.eq('2PT Field Goal')
        # NBA occasionally carries an obviously bad action/value combination
        # (for example a 55-foot "Running Layup Shot" recorded as a three).
        # Quarantine it from the layup baseline and retain the audit count.
        included &= league.SHOT_TYPE.eq('2PT Field Goal')
        league_fga = int(included.sum())
        league_fgm = int(league.loc[included, 'SHOT_MADE_FLAG'].sum())
        rows.append(dict(SEASON=season, excluded_non_two_point=int(excluded_value.sum()),
                         league_layup_fga=league_fga,
                         league_layup_fgm=league_fgm,
                         league_layup_fg_pct=league_fgm / league_fga))
        print(season, league_fga, league_fgm, league_fgm / league_fga, flush=True)
    baseline = pd.DataFrame(rows)
    result = merge_relative_fg(top, baseline)
    result.to_csv(DATA / 'top15_with_relative_fg.csv', index=False)
    baseline.to_csv(DATA / 'league_layup_baselines.csv', index=False)
    print(result[['RANK','PLAYER_NAME','SEASON','FGM','FGA','FG_PCT',
                  'league_layup_fg_pct','rFG_PCT']].to_string(index=False), flush=True)


def summarize(shots: pd.DataFrame, players: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if shots.duplicated(['GAME_ID', 'GAME_EVENT_ID']).any():
        raise ValueError('Duplicate shot event')
    if not shots.TEAM_ID.eq(TEAM).all():
        raise ValueError('Non-Bulls shot')
    if players.PLAYER_ID.duplicated().any():
        raise ValueError('Duplicate official player row')
    totals = shots.groupby('PLAYER_ID').agg(shot_fga=('SHOT_MADE_FLAG','size'),
                                            shot_fgm=('SHOT_MADE_FLAG','sum'))
    audit = players[['PLAYER_ID','PLAYER_NAME','GP','FGA','FGM']].merge(
        totals, on='PLAYER_ID', how='outer', validate='one_to_one')
    # An official zero-attempt player can legitimately have no shot rows.
    for col in ['shot_fga','shot_fgm']:
        audit.loc[audit.FGA.eq(0) & audit[col].isna(), col] = 0
    audit['fga_delta'] = audit.shot_fga - audit.FGA
    audit['fgm_delta'] = audit.shot_fgm - audit.FGM
    f = shots.loc[is_layup(shots.ACTION_TYPE)].copy()
    if not f.SHOT_TYPE.eq('2PT Field Goal').all():
        raise ValueError('Non-two-point layup requires inspection')
    counts = f.groupby('PLAYER_ID').agg(FGA=('SHOT_MADE_FLAG','size'), FGM=('SHOT_MADE_FLAG','sum'))
    result = players[['PLAYER_ID','PLAYER_NAME','GP','FGA']].rename(columns={'FGA':'TOTAL_FGA'}).merge(counts, on='PLAYER_ID', how='left', validate='one_to_one')
    result[['FGA','FGM']] = result[['FGA','FGM']].fillna(0).astype(int)
    other = shots.loc[~is_layup(shots.ACTION_TYPE)].groupby('PLAYER_ID').size()
    result['OTHER_FGA'] = result.PLAYER_ID.map(other).fillna(0).astype(int)
    result['FGA_SHARE'] = result.FGA.div(result.TOTAL_FGA.where(result.TOTAL_FGA.gt(0)))
    partition = result[['PLAYER_ID','FGA','OTHER_FGA']].rename(columns={'FGA':'layup_fga'})
    audit = audit.merge(partition, on='PLAYER_ID', how='left', validate='one_to_one')
    audit['partition_delta'] = audit.layup_fga + audit.OTHER_FGA - audit.FGA
    result['ATT_G'] = result.FGA / result.GP
    result['FG_PCT'] = result.FGM.div(result.FGA.where(result.FGA.gt(0)))
    result['PPS'] = 2 * result.FG_PCT
    return result, audit


def prepare() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    results, audits, coverage, actions = [], [], [], []
    for year in range(2000, 2026):
        season = f'{year}-{str(year + 1)[-2:]}'
        shots, players, teams = [fetch_frame(k, season) for k in ['shots','players','teams']]
        result, audit = summarize(shots, players)
        for frame in [result, audit]:
            frame.insert(0, 'SEASON', season)
        results.append(result)
        audits.append(audit)
        team = teams.loc[teams.TEAM_ID.eq(TEAM)].iloc[0]
        coverage.append(dict(SEASON=season, games=shots.GAME_ID.nunique(), official_gp=team.GP,
                             shots=len(shots), official_fga=team.FGA,
                             makes=int(shots.SHOT_MADE_FLAG.sum()), official_fgm=team.FGM))
        labels = shots.groupby('ACTION_TYPE').agg(FGA=('SHOT_MADE_FLAG','size'), FGM=('SHOT_MADE_FLAG','sum')).reset_index()
        labels.insert(0, 'SEASON', season)
        labels['included'] = is_layup(labels.ACTION_TYPE)
        actions.append(labels)
        pd.concat(audits).to_csv(DATA / 'player_reconciliation.csv', index=False)
        pd.DataFrame(coverage).to_csv(DATA / 'season_coverage.csv', index=False)
        pd.concat(actions).to_csv(DATA / 'action_label_audit.csv', index=False)
        print(season, 'shots',len(shots),'layup makes',result.FGM.sum(), flush=True)
    audit = pd.concat(audits)
    cover = pd.DataFrame(coverage)
    if not audit[['fga_delta','fgm_delta','partition_delta']].eq(0).all().all():
        raise ValueError('Player reconciliation mismatch; inspect saved audit')
    if not (cover.games.eq(cover.official_gp) & cover.shots.eq(cover.official_fga)
            & cover.makes.eq(cover.official_fgm)).all():
        raise ValueError('Team reconciliation mismatch; inspect saved audit')
    ranked = pd.concat(results).sort_values(['FGM','FGA','SEASON','PLAYER_ID'], ascending=[False,True,False,True])
    ranked['RANK'] = ranked.FGM.rank(method='min', ascending=False).astype(int)
    ranked.to_csv(DATA / 'all_player_seasons.csv', index=False)
    ranked[['SEASON','PLAYER_ID','PLAYER_NAME','FGA','OTHER_FGA','TOTAL_FGA','FGA_SHARE']].to_csv(DATA / 'shot_share_reconciliation.csv', index=False)
    # Preserve tied ranks at the last included row, rather than arbitrarily omit one.
    top = ranked.loc[ranked.FGM.ge(ranked.iloc[14].FGM)].copy()
    top.to_csv(DATA / 'top15.csv', index=False)
    print(top.to_string(index=False), flush=True)


def render() -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from bulls.graphics.house import (helvetica, BLACK, HEADSHOT_CACHE, ensure_headshots,
                                     draw_accent_card, top_anchored_headshot_label)
    from bulls.graphics.craft import draw_table_cell
    from matplotlib.offsetbox import AnnotationBbox, TextArea, HPacker
    top = pd.read_csv(DATA / 'top15.csv')
    baseline = pd.read_csv(DATA / 'league_layup_baselines.csv')
    top = merge_relative_fg(top, baseline)
    ensure_headshots(top.PLAYER_ID.unique())
    width, row_h = 2200, 145
    height = 150 + row_h * len(top)
    fig = plt.figure(figsize=(width / 150, height / 150), dpi=300)
    ax = fig.add_axes([0,0,1,1])
    ax.set(xlim=(0,width), ylim=(0,height))
    ax.axis('off')
    first_y = height - 190
    header_y = height - 48
    # Keep a consistent 35-unit gutter between columns. The FG% header gets
    # extra width inside its column, rather than creating a larger outside gap.
    cols = [(850,1050,'FGM'), (1085,1285,'FGA'), (1320,1645,'FG% (rFG%)'),
            (1680,1880,'ATT/G'), (1915,2115,'% OF FGA')]
    card_left,card_right,_,_ = draw_accent_card(ax,850,1050,first_y,len(top),row_h,overlap_y=15)
    ax.text(275,header_y,'PLAYER / SEASON',fontproperties=helvetica('bold'),fontsize=21,color=BLACK,va='center')
    for left,right,label in cols:
        draw_table_cell(ax,label,left,right,header_y,40,fontsize=21,color=BLACK,fontproperties=helvetica('bold'))
    rule_y=height-105
    ax.hlines(rule_y,0,card_left-10,color=BLACK,lw=1)
    ax.hlines(rule_y,card_right+10,width,color=BLACK,lw=1)
    for i,row in enumerate(top.itertuples()):
        y=first_y-i*row_h
        if i % 2 == 0:
            ax.axhspan(y-row_h/2,y+row_h/2,color='#B8B0A8',alpha=.09,zorder=0)
        if i:
            ax.hlines(y+row_h/2,0,width,color='#B8B0A8',lw=.65,zorder=0)
        top_anchored_headshot_label(ax,HEADSHOT_CACHE / f'{row.PLAYER_ID}.png',125,y+10,85,
                                   crop_fraction=.64,preserve_width=True,zorder=3+i*.01)
        ax.text(275,y+22,row.PLAYER_NAME,fontproperties=helvetica('bold'),fontsize=27,color=BLACK,va='center')
        ax.text(275,y-32,row.SEASON.replace('-', '–'),fontproperties=helvetica('oblique'),
                fontsize=16,color='#5F5B57',va='center')
        values=[str(row.FGM),str(row.FGA),f'{100*row.FG_PCT:.1f}%',f'{row.ATT_G:.1f}',f'{100*row.FGA_SHARE:.1f}%']
        for j,((left,right,_),value) in enumerate(zip(cols,values)):
            if j == 2:
                relative = round(row.rFG_PCT, 1)
                signed = f'{relative:+.1f}'.replace('-', '−') if relative else '0.0'
                color = '#D64545' if relative < 0 else '#218347' if relative > 0 else BLACK
                parts = [TextArea(value, textprops=dict(fontproperties=helvetica(),fontsize=25,color=BLACK)),
                         TextArea(f' ({signed})', textprops=dict(fontproperties=helvetica(),fontsize=25,color=color))]
                box = HPacker(children=parts,align='center',pad=0,sep=0)
                ax.add_artist(AnnotationBbox(box,((left+right)/2,y),xycoords='data',
                                            frameon=False,box_alignment=(.5,.5),pad=0,zorder=6))
                continue
            draw_table_cell(ax,value,left,right,y,row_h,fontsize=28 if j==0 else 25,
                            color='white' if j==0 else BLACK,zorder=6,
                            fontproperties=helvetica('bold' if j==0 else 'regular'))
    out = ROOT / 'output/layup-season-leaders'
    out.mkdir(parents=True,exist_ok=True)
    fig.savefig(out / 'layup_season_leaders.png',dpi=300,transparent=True)
    plt.close(fig)
    copy = dict(title='Bulls layup scoring leaders',subtitle='Top 15 in layups made in one season, since 2000–01',
                scope='2000–01 to 2025–26 regular season · Chicago games only',
                definition='Includes finger rolls and putback layups. Excludes tips, dunks and floaters.',
                relative_fg='rFG% = layup FG% minus that season’s NBA layup FG%, in percentage points.',
                shot_share='% OF FGA = layup attempts / all field-goal attempts in Bulls games.',
                source='Source: NBA.com · Shot classifications',handle='@chicagobullsdata')
    (DATA / 'canva_copy.json').write_text(json.dumps(copy,indent=2,ensure_ascii=False))
    print(out / 'layup_season_leaders.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--relative-fg', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.render:
        render()
    if args.relative_fg:
        add_relative_fg()
