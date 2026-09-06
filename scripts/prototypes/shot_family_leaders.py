"""Bulls single-season leaders for any NBA shot family, from one registry.

`layup_season_leaders.py` and `floater_season_leaders.py` are the shipped, published
members of this family; this entry point generalises the same pipeline so a new family
(dunks, hooks, ...) is a `Family` registry entry rather than another copied file.
It never reads, writes or re-renders either shipped post's directory.

Each family declares what it matches, how a three-point row carrying its label is
treated, and its page copy. The season a ranking may start from is *not* declared:
it is derived from `action_label_audit.csv`, because an ACTION_TYPE that NBA.com had
not invented yet means unavailable classification, never zero shots of that kind.

    --family dunks --prepare        snapshot, reconcile and audit every season
    --family dunks --relative-fg    league baselines for the rFG% column
    --family dunks --render         table from saved data
    --family dunks --from-season 2025-26 --prepare      narrow the ranking window
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
# Own namespace, one directory per family slug. The two shipped posts keep their
# own directories and are never written to from here.
DATA_ROOT = ROOT / 'docs/visuals/shot-family-leaders'
AUDIT_FROM = 2000
LAST_SEASON = 2025


class Family:
    """One shot family. Adding a family means adding one of these to FAMILIES.

    Plain class rather than a dataclass: these prototypes are loaded by path with
    `spec_from_file_location`, where dataclass field resolution fails.
    """

    def __init__(self, slug, noun, include, exclude='', three_point='reject',
                 declared_rank_from=None, definition=''):
        self.slug = slug
        self.noun = noun                 # singular, used in column names and copy
        self.include = include           # ACTION_TYPE regex, matched lower-case
        self.exclude = exclude           # labels the include pattern over-catches
        self.three_point = three_point   # 'reject' (impossible) | 'heaves' (expected)
        self.declared_rank_from = declared_rank_from  # documentation; evidence wins
        self.definition = definition


FAMILIES: dict[str, Family] = {
    'dunks': Family(
        slug='dunks', noun='dunk', include='dunk', exclude='tip',
        three_point='reject',
        definition='All NBA dunk labels, including alley-oops and putback dunks. Excludes tip-ins.'),
    'hooks': Family(
        slug='hooks', noun='hook', include='hook',
        three_point='reject',
        definition='All NBA hook-shot labels, including bank, jump and turnaround hooks.'),
    # The two shipped posts, expressed as registry entries so the derived ranking
    # window can be checked against a published result. Their data lives here, not
    # in the published posts' directories.
    'layups': Family(
        slug='layups', noun='layup', include='layup|finger roll', exclude='tip|dunk|floating',
        three_point='reject', declared_rank_from=2000,
        definition='Includes finger rolls and putback layups. Excludes tips, dunks and floaters.'),
    'floaters': Family(
        slug='floaters', noun='floater', include='floating',
        three_point='heaves', declared_rank_from=2015,
        definition='NBA floating-shot labels, including driving and bank floaters.'),
}


def get_family(slug: str) -> Family:
    if slug not in FAMILIES:
        raise ValueError(f'Unknown family {slug!r}; known: {sorted(FAMILIES)}')
    return FAMILIES[slug]


def matches(fam: Family, labels: pd.Series) -> pd.Series:
    text = labels.fillna('').str.lower()
    hit = text.str.contains(fam.include, regex=True)
    if fam.exclude:
        hit &= ~text.str.contains(fam.exclude, regex=True)
    return hit


def season_label(year: int) -> str:
    return f'{year}-{str(year + 1)[-2:]}'


def season_year(season: str) -> int:
    return int(season[:4])


def data_dir(fam: Family) -> Path:
    return DATA_ROOT / fam.slug / 'data'


def snapshot_paths(fam: Family, kind: str, season: str) -> tuple[Path, Path]:
    """Snapshot file and its provenance sidecar.

    The sidecar name *appends* to the full data file name. Deriving it with
    `with_suffix` instead (shots_2015-16.csv.gz -> shots_2015-16.json) once
    produced a name a neighbouring script also used, and silently overwrote its
    snapshots. Appending cannot collide with any data file's own name.
    """
    path = data_dir(fam) / 'raw' / f'{fam.slug}_{kind}_{season}.csv.gz'
    return path, path.with_name(path.name + '.meta.json')


def league_snapshot_paths(fam: Family, name: str) -> tuple[Path, Path]:
    path = data_dir(fam) / 'league_raw' / name
    return path, path.with_name(path.name + '.meta.json')


def write_meta(path: Path, endpoint: str, params: dict, rows: int) -> None:
    path.write_text(json.dumps(dict(endpoint=endpoint, parameters=params,
        fetched_at=datetime.now(timezone.utc).isoformat(), rows=rows), indent=2))


def fetch_frame(fam: Family, kind: str, season: str) -> pd.DataFrame:
    path, meta = snapshot_paths(fam, kind, season)
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
                write_meta(meta, cls.__name__, params, len(frame))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        time.sleep(.65)
    return pd.read_csv(path, dtype={'GAME_ID':str, 'GAME_DATE':str})


def fetch_league_season(fam: Family, season: str) -> pd.DataFrame:
    """Fetch every team's shot rows, avoiding the league endpoint's row cap."""
    frames = []
    for team_id in NBA_TEAM_IDS:
        path, meta = league_snapshot_paths(fam, f'{team_id}_{season}.csv.gz')
        if not path.exists():
            params = dict(team_id=team_id, player_id=0, season_nullable=season,
                          season_type_all_star='Regular Season', context_measure_simple='FGA')
            frame = shotchartdetail.ShotChartDetail(
                **params, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
            if frame.empty:
                raise ValueError(f'Unavailable league team pull: {team_id} {season}')
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False)
            write_meta(meta, 'ShotChartDetail', params, len(frame))
            time.sleep(.65)
        frame = pd.read_csv(path, dtype={'GAME_ID':str, 'GAME_DATE':str})
        if not frame.TEAM_ID.eq(team_id).all():
            raise ValueError(f'Unexpected team rows in {path}')
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def fetch_league_totals(fam: Family, season: str) -> pd.DataFrame:
    path, meta = league_snapshot_paths(fam, f'teams_{season}.csv.gz')
    if not path.exists():
        params = dict(season=season, season_type_all_star='Regular Season',
                      per_mode_detailed='Totals')
        frame = leaguedashteamstats.LeagueDashTeamStats(
            **params, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
        if frame.empty:
            raise ValueError(f'Unavailable official league totals: {season}')
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        write_meta(meta, 'LeagueDashTeamStats', params, len(frame))
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


# --- label stability -------------------------------------------------------
# A family's meaning is only comparable across seasons where NBA.com used the same
# vocabulary for it. An ACTION_TYPE missing from an earlier season is unavailable
# classification, NOT zero shots: those shots existed, they were filed under some
# other label or not distinguished at all. So the ranking window is derived from
# label evidence rather than declared.
#
# Two kinds of vocabulary change look alike in the label list but differ in the data:
#   - a *split*, where NBA.com carved an existing label into finer ones (layups
#     gained 'Cutting Layup Shot' in 2015-16). Family coverage is unchanged, so
#     earlier seasons stay comparable.
#   - an *addition*, where a genuinely new kind of shot enters the family (floaters
#     gained the two driving labels in 2015-16 and roughly tripled). Earlier
#     seasons under-count the family and must not be ranked.
# The counts already in the audit separate them: on an addition the family's share
# of all attempts rises by about the new labels' own share; on a split the older
# labels give that share up.
ADDITION_RATIO = .75   # share gained / new labels' share, above which it is new coverage
MATERIAL_SHARE = .005  # new labels below this share of all FGA are season-to-season noise


class Stability:
    def __init__(self, boundary, audited_from, markers, introductions, sporadic):
        self.boundary = boundary          # earliest season the family may be ranked from
        self.audited_from = audited_from
        self.markers = markers            # label -> first season, for labels still in use
        self.introductions = introductions  # per-season evidence rows
        self.sporadic = sporadic          # labels with gaps: sampling, not era changes


def label_stability(audit: pd.DataFrame, fam: Family) -> Stability:
    """Earliest season this family's label set is stable, from action_label_audit.csv."""
    if audit.empty:
        raise ValueError('Empty action label audit; cannot establish label stability')
    seasons = sorted(audit.SEASON.unique())
    totals = audit.groupby('SEASON').FGA.sum()
    fam_rows = audit.loc[matches(fam, audit.ACTION_TYPE)]
    fam_share = (fam_rows.groupby('SEASON').FGA.sum() / totals).reindex(seasons).fillna(0)
    markers, sporadic, intro = {}, [], {}
    for label, group in fam_rows.groupby('ACTION_TYPE'):
        seen = sorted(group.SEASON.unique())
        first, last = seasons.index(seen[0]), seasons.index(seen[-1])
        # A label used in every season since it appeared, and still used in the last
        # audited season, marks an era. One with gaps is a rare shot the Bulls simply
        # did not take that year; a retired label does not shrink later coverage,
        # since the family is matched by pattern and its shots moved to a sibling.
        if len(seen) == last - first + 1 and seen[-1] == seasons[-1]:
            markers[label] = seen[0]
            intro.setdefault(seen[0], []).append(label)
        else:
            sporadic.append(label)
    boundary, rows = seasons[0], []
    for season in sorted(intro):
        index = seasons.index(season)
        new = fam_rows.loc[fam_rows.SEASON.eq(season)
                           & fam_rows.ACTION_TYPE.isin(intro[season]), 'FGA'].sum() / totals[season]
        if index == 0:
            rows.append(dict(SEASON=season, labels='; '.join(intro[season]), new_share=new,
                             prior_share=float('nan'), ratio=float('nan'), verdict='first audited'))
            continue
        prior = fam_share.iloc[max(0, index - 5):index].median()
        ratio = (fam_share[season] - prior) / new if new else 0.
        addition = new >= MATERIAL_SHARE and ratio >= ADDITION_RATIO
        rows.append(dict(SEASON=season, labels='; '.join(intro[season]), new_share=new,
                         prior_share=prior, ratio=ratio,
                         verdict='addition' if addition else 'relabel'))
        if addition:
            boundary = season
    return Stability(boundary=boundary, audited_from=seasons[0], markers=markers,
                     introductions=rows, sporadic=sporadic)


def resolve_rank_from(audit: pd.DataFrame, fam: Family, requested: str | None = None,
                      allow_unstable: bool = False) -> tuple[str, Stability, list[str]]:
    """Ranking window start, refusing seasons before the evidenced boundary."""
    stability = label_stability(audit, fam)
    notes = []
    if fam.declared_rank_from and season_year(stability.boundary) != fam.declared_rank_from:
        notes.append(f'Detected label boundary {stability.boundary} differs from the '
                     f'declared {season_label(fam.declared_rank_from)} for {fam.slug}.')
    chosen = requested or stability.boundary
    if season_year(chosen) < season_year(stability.boundary):
        message = (f'{fam.slug}: cannot rank from {chosen}. The family gains labels at '
                   f'{stability.boundary} ({"; ".join(l for l, s in stability.markers.items() if s == stability.boundary)}), '
                   f'so earlier seasons carry unavailable classification, not zero '
                   f'{fam.noun}s. Pass --allow-unstable-labels to override.')
        if not allow_unstable:
            raise ValueError(message)
        notes.append('OVERRIDE: ' + message)
    if requested and season_year(requested) > season_year(stability.boundary):
        notes.append(f'Ranking narrowed to {requested}; seasons back to '
                     f'{stability.boundary} are audited but not ranked.')
    return chosen, stability, notes


def merge_relative_fg(fam: Family, top: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    column = f'league_{fam.noun}_fg_pct'
    result = top.merge(baseline, on='SEASON', how='left', validate='many_to_one')
    if result[column].isna().any():
        raise ValueError(f'Missing seasonal {fam.noun} baseline')
    result['rFG_PCT'] = (result.FG_PCT - result[column]) * 100
    return result


def add_relative_fg(fam: Family) -> None:
    data = data_dir(fam)
    top = pd.read_csv(data / 'top15.csv')
    rows, audits = [], []
    for season in top.SEASON.unique():
        league = fetch_league_season(fam, season)
        audit = reconcile_league(league, fetch_league_totals(fam, season))
        audit.insert(0, 'SEASON', season)
        audits.append(audit)
        pd.concat(audits, ignore_index=True).to_csv(data / 'league_team_reconciliation.csv', index=False)
        if not audit[['fga_delta', 'fgm_delta', 'gp_delta']].eq(0).all().all():
            raise ValueError(f'League totals mismatch: {season}; inspect saved audit')
        included = matches(fam, league.ACTION_TYPE)
        excluded_value = included & ~league.SHOT_TYPE.eq('2PT Field Goal')
        # A family label on a three is either a bad action/value combination or a
        # heave. Either way it is not the shot the baseline describes: quarantine
        # it and keep the count in the audit.
        included &= league.SHOT_TYPE.eq('2PT Field Goal')
        league_fga = int(included.sum())
        league_fgm = int(league.loc[included, 'SHOT_MADE_FLAG'].sum())
        rows.append({'SEASON': season, 'excluded_non_two_point': int(excluded_value.sum()),
                     f'league_{fam.noun}_fga': league_fga,
                     f'league_{fam.noun}_fgm': league_fgm,
                     f'league_{fam.noun}_fg_pct': league_fgm / league_fga})
        print(season, league_fga, league_fgm, league_fgm / league_fga, flush=True)
    baseline = pd.DataFrame(rows)
    result = merge_relative_fg(fam, top, baseline)
    result.to_csv(data / 'top15_with_relative_fg.csv', index=False)
    baseline.to_csv(data / f'league_{fam.noun}_baselines.csv', index=False)
    print(result[['RANK','PLAYER_NAME','SEASON','FGM','FGA','FG_PCT',
                  f'league_{fam.noun}_fg_pct','rFG_PCT']].to_string(index=False), flush=True)


def summarize(fam: Family, shots: pd.DataFrame, players: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    labelled = matches(fam, shots.ACTION_TYPE)
    two_point = shots.SHOT_TYPE.eq('2PT Field Goal')
    heaves = shots.loc[labelled & ~two_point]
    if fam.three_point == 'reject' and len(heaves):
        raise ValueError(f'Non-two-point {fam.noun} requires inspection')
    # Where three-point family labels are expected (halfcourt heaves), they leave
    # the count but stay visible in EXCLUDED_HEAVES and in the attempt partition.
    f = shots.loc[labelled & two_point].copy()
    counts = f.groupby('PLAYER_ID').agg(FGA=('SHOT_MADE_FLAG','size'), FGM=('SHOT_MADE_FLAG','sum'))
    result = players[['PLAYER_ID','PLAYER_NAME','GP','FGA']].rename(columns={'FGA':'TOTAL_FGA'}).merge(counts, on='PLAYER_ID', how='left', validate='one_to_one')
    result[['FGA','FGM']] = result[['FGA','FGM']].fillna(0).astype(int)
    other = shots.loc[~(labelled & two_point)].groupby('PLAYER_ID').size()
    result['OTHER_FGA'] = result.PLAYER_ID.map(other).fillna(0).astype(int)
    result['FGA_SHARE'] = result.FGA.div(result.TOTAL_FGA.where(result.TOTAL_FGA.gt(0)))
    partition = result[['PLAYER_ID','FGA','OTHER_FGA']].rename(columns={'FGA':f'{fam.noun}_fga'})
    audit = audit.merge(partition, on='PLAYER_ID', how='left', validate='one_to_one')
    audit['partition_delta'] = audit[f'{fam.noun}_fga'] + audit.OTHER_FGA - audit.FGA
    result['ATT_G'] = result.FGA / result.GP
    result['FG_PCT'] = result.FGM.div(result.FGA.where(result.FGA.gt(0)))
    result['PPS'] = 2 * result.FG_PCT
    result['EXCLUDED_HEAVES'] = result.PLAYER_ID.map(
        heaves.groupby('PLAYER_ID').size()).fillna(0).astype(int)
    return result, audit


def prepare(fam: Family, from_season: str | None = None, allow_unstable: bool = False) -> None:
    data = data_dir(fam)
    data.mkdir(parents=True, exist_ok=True)
    results, audits, coverage, actions = [], [], [], []
    for year in range(AUDIT_FROM, LAST_SEASON + 1):
        season = season_label(year)
        shots, players, teams = [fetch_frame(fam, k, season) for k in ['shots','players','teams']]
        result, audit = summarize(fam, shots, players)
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
        labels['included'] = matches(fam, labels.ACTION_TYPE)
        actions.append(labels)
        pd.concat(audits).to_csv(data / 'player_reconciliation.csv', index=False)
        pd.DataFrame(coverage).to_csv(data / 'season_coverage.csv', index=False)
        pd.concat(actions).to_csv(data / 'action_label_audit.csv', index=False)
        print(season, 'shots', len(shots), f'{fam.noun} makes', result.FGM.sum(),
              'heaves excluded', result.EXCLUDED_HEAVES.sum(), flush=True)
    audit = pd.concat(audits)
    cover = pd.DataFrame(coverage)
    if not audit[['fga_delta','fgm_delta','partition_delta']].eq(0).all().all():
        raise ValueError('Player reconciliation mismatch; inspect saved audit')
    if not (cover.games.eq(cover.official_gp) & cover.shots.eq(cover.official_fga)
            & cover.makes.eq(cover.official_fgm)).all():
        raise ValueError('Team reconciliation mismatch; inspect saved audit')
    everything = pd.concat(results)
    everything.to_csv(data / 'all_player_seasons.csv', index=False)
    rank_from, stability, notes = resolve_rank_from(
        pd.concat(actions), fam, from_season, allow_unstable)
    pd.DataFrame(stability.introductions).to_csv(data / 'label_stability.csv', index=False)
    for note in notes:
        print(note, flush=True)
    print(f'Ranking {fam.slug} from {rank_from}; audited from {stability.audited_from}.', flush=True)
    ranked = everything.loc[everything.SEASON.map(season_year).ge(season_year(rank_from))]
    ranked = ranked.sort_values(['FGM','FGA','SEASON','PLAYER_ID'], ascending=[False,True,False,True])
    ranked['RANK'] = ranked.FGM.rank(method='min', ascending=False).astype(int)
    ranked.to_csv(data / 'ranked_player_seasons.csv', index=False)
    ranked[['SEASON','PLAYER_ID','PLAYER_NAME','FGA','OTHER_FGA','TOTAL_FGA','FGA_SHARE']].to_csv(data / 'shot_share_reconciliation.csv', index=False)
    # Preserve tied ranks at the last included row, rather than arbitrarily omit one.
    top = ranked.loc[ranked.FGM.ge(ranked.iloc[14].FGM)].copy()
    top.to_csv(data / 'top15.csv', index=False)
    (data / 'window.json').write_text(json.dumps(dict(
        family=fam.slug, rank_from=rank_from, audited_from=stability.audited_from,
        boundary=stability.boundary, notes=notes), indent=2))
    print(top.to_string(index=False), flush=True)


def render(fam: Family) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from bulls.graphics.house import (helvetica, BLACK, HEADSHOT_CACHE, ensure_headshots,
                                     draw_accent_card, top_anchored_headshot_label)
    from bulls.graphics.craft import draw_table_cell
    from matplotlib.offsetbox import AnnotationBbox, TextArea, HPacker
    data = data_dir(fam)
    top = pd.read_csv(data / 'top15.csv')
    baseline = pd.read_csv(data / f'league_{fam.noun}_baselines.csv')
    top = merge_relative_fg(fam, top, baseline)
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
    out = ROOT / f'output/{fam.slug}-season-leaders'
    out.mkdir(parents=True,exist_ok=True)
    fig.savefig(out / f'{fam.slug}_season_leaders.png',dpi=300,transparent=True)
    plt.close(fig)
    (data / 'canva_copy.json').write_text(json.dumps(
        family_copy(fam, top.SEASON.min()), indent=2, ensure_ascii=False))
    print(out / f'{fam.slug}_season_leaders.png')


def family_copy(fam: Family, rank_from: str) -> dict:
    """Page copy, with the window taken from the data rather than restated by hand."""
    span = f'{rank_from.replace("-", "–")} to {season_label(LAST_SEASON).replace("-", "–")}'
    definition = fam.definition
    if season_year(rank_from) > AUDIT_FROM:
        definition += (f' Ranked from {rank_from.replace("-", "–")}, the first season '
                       f'carrying every {fam.noun} label.')
    return dict(title=f'Bulls {fam.noun} scoring leaders',
                subtitle=f'Top 15 in {fam.noun}s made in one season, since {rank_from.replace("-", "–")}',
                scope=f'{span} regular season · Chicago games only',
                definition=definition,
                relative_fg=f'rFG% = {fam.noun} FG% minus that season’s NBA {fam.noun} FG%, in percentage points.',
                shot_share=f'% OF FGA = {fam.noun} attempts / all field-goal attempts in Bulls games.',
                source='Source: NBA.com · Shot classifications', handle='@chicagobullsdata')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', required=True, choices=sorted(FAMILIES))
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--relative-fg', action='store_true')
    parser.add_argument('--from-season', help='e.g. 2025-26; narrows the ranking window')
    parser.add_argument('--allow-unstable-labels', action='store_true',
                        help='rank before the evidenced label boundary anyway')
    args = parser.parse_args()
    family = get_family(args.family)
    if args.prepare:
        prepare(family, args.from_season, args.allow_unstable_labels)
    if args.render:
        render(family)
    if args.relative_fg:
        add_relative_fg(family)
