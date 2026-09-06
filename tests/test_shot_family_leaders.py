import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location(
    'shot_family', ROOT / 'scripts/prototypes/shot_family_leaders.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

LAYUPS = mod.get_family('layups')
FLOATERS = mod.get_family('floaters')
DUNKS = mod.get_family('dunks')
HOOKS = mod.get_family('hooks')


def test_registry_families_match_their_labels_and_not_their_neighbours():
    labels = pd.Series(['Layup Shot', 'Driving Finger Roll Shot', 'Cutting Layup Shot',
                        'Tip Layup Shot', 'Tip Dunk Shot', 'Alley Oop Dunk Shot',
                        'Putback Dunk Shot', 'Floating Jump shot',
                        'Driving Floating Bank Jump Shot', 'Turnaround Hook Shot',
                        'Driving Bank Hook Shot', 'Jump Shot', None])
    got = {fam.slug: labels[mod.matches(fam, labels)].tolist()
           for fam in [LAYUPS, FLOATERS, DUNKS, HOOKS]}
    assert got['layups'] == ['Layup Shot', 'Driving Finger Roll Shot', 'Cutting Layup Shot']
    assert got['floaters'] == ['Floating Jump shot', 'Driving Floating Bank Jump Shot']
    assert got['dunks'] == ['Alley Oop Dunk Shot', 'Putback Dunk Shot']
    assert got['hooks'] == ['Turnaround Hook Shot', 'Driving Bank Hook Shot']


def test_unknown_family_is_rejected():
    with pytest.raises(ValueError, match='Unknown family'):
        mod.get_family('stepbacks')


def fixtures(action_types):
    shots = pd.DataFrame(dict(PLAYER_ID=[1,1,1], TEAM_ID=[mod.TEAM]*3,
                              GAME_ID=['a','b','b'], GAME_EVENT_ID=[1,2,3],
                              ACTION_TYPE=action_types,
                              SHOT_MADE_FLAG=[1,0,1], SHOT_TYPE=['2PT Field Goal']*3))
    players = pd.DataFrame(dict(PLAYER_ID=[1,2], PLAYER_NAME=['A','B'], GP=[4,2],
                                FGA=[3,0], FGM=[2,0]))
    return shots, players


def dunk_fixtures():
    return fixtures(['Dunk Shot', 'Putback Dunk Shot', 'Jump Shot'])


def test_rates_use_all_games_and_zero_attempt_efficiency_is_missing():
    result, audit = mod.summarize(DUNKS, *dunk_fixtures())
    assert result.iloc[0].ATT_G == .5
    assert result.iloc[0].FG_PCT == .5
    assert result.iloc[0].PPS == 1
    assert result.iloc[0].FGA_SHARE == pytest.approx(2/3)
    assert result.iloc[0].OTHER_FGA == 1
    assert result.iloc[0].FGA + result.iloc[0].OTHER_FGA == result.iloc[0].TOTAL_FGA
    assert result.iloc[1].FGA == 0
    assert pd.isna(result.iloc[1].FG_PCT)
    assert pd.isna(result.iloc[1].FGA_SHARE)
    assert audit[['fga_delta','fgm_delta','partition_delta']].eq(0).all().all()


def test_missing_shots_do_not_reconcile_as_zero():
    shots, players = dunk_fixtures()
    _, audit = mod.summarize(DUNKS, shots.iloc[:0], players)
    assert pd.isna(audit.iloc[0].fga_delta)
    assert audit.iloc[0].partition_delta == -3


def test_duplicate_event_and_foreign_team_are_rejected():
    shots, players = dunk_fixtures()
    with pytest.raises(ValueError, match='Duplicate shot'):
        mod.summarize(DUNKS, pd.concat([shots, shots.iloc[:1]]), players)
    foreign = shots.copy()
    foreign.loc[0, 'TEAM_ID'] = 1610612738
    with pytest.raises(ValueError, match='Non-Bulls'):
        mod.summarize(DUNKS, foreign, players)


def test_three_point_policy_reject_raises_and_heaves_are_quarantined():
    shots, players = dunk_fixtures()
    shots.loc[0, 'SHOT_TYPE'] = '3PT Field Goal'
    with pytest.raises(ValueError, match='Non-two-point dunk'):
        mod.summarize(DUNKS, shots, players)

    shots, players = fixtures(['Floating Jump shot', 'Driving Floating Bank Jump Shot', 'Jump Shot'])
    shots.loc[0, 'SHOT_TYPE'] = '3PT Field Goal'
    result, audit = mod.summarize(FLOATERS, shots, players)
    row = result.iloc[0]
    assert row.FGA == 1 and row.FGM == 0
    assert row.EXCLUDED_HEAVES == 1
    # The heave still belongs to total attempts; only the floater count drops it.
    assert row.OTHER_FGA == 2
    assert row.FGA + row.OTHER_FGA == row.TOTAL_FGA
    assert audit[['fga_delta','fgm_delta','partition_delta']].eq(0).all().all()


def test_relative_baseline_cannot_drop_a_player_season():
    top = pd.DataFrame({'SEASON': ['2015-16', '2016-17'], 'FG_PCT': [.6, .5]})
    baseline = pd.DataFrame({'SEASON': ['2015-16'], 'league_dunk_fg_pct': [.55]})
    with pytest.raises(ValueError, match='Missing seasonal dunk baseline'):
        mod.merge_relative_fg(DUNKS, top, baseline)
    baseline = pd.concat([baseline, pd.DataFrame({'SEASON': ['2016-17'],
                                                  'league_dunk_fg_pct': [.6]})])
    result = mod.merge_relative_fg(DUNKS, top, baseline)
    assert result.SEASON.tolist() == top.SEASON.tolist()
    assert result.rFG_PCT.tolist() == pytest.approx([5., -10.])


def test_league_reconciliation_exposes_missing_or_truncated_team():
    shots, _ = dunk_fixtures()
    official = pd.DataFrame(dict(TEAM_ID=[mod.TEAM, 2], TEAM_NAME=['Bulls', 'Other'],
                                 GP=[2, 1], FGA=[3, 1], FGM=[2, 1]))
    audit = mod.reconcile_league(shots, official).set_index('TEAM_ID')
    assert audit.loc[mod.TEAM][['fga_delta','fgm_delta','gp_delta']].eq(0).all()
    assert audit.loc[2][['fga_delta','fgm_delta','gp_delta']].isna().all()
    truncated = mod.reconcile_league(shots.iloc[:2], official).set_index('TEAM_ID')
    assert truncated.loc[mod.TEAM].fga_delta == -1
    with pytest.raises(ValueError, match='Duplicate league shot'):
        mod.reconcile_league(pd.concat([shots, shots.iloc[:1]]), official)


# --- snapshot naming -------------------------------------------------------

def test_snapshot_names_are_family_scoped_and_sidecars_cannot_collide():
    data, meta = mod.snapshot_paths(DUNKS, 'shots', '2015-16')
    other, other_meta = mod.snapshot_paths(HOOKS, 'shots', '2015-16')
    assert data.name == 'dunks_shots_2015-16.csv.gz'
    # The sidecar appends; the with_suffix idiom would yield 'shots_2015-16.json',
    # a name a neighbouring script can also produce.
    assert meta.name == 'dunks_shots_2015-16.csv.gz.meta.json'
    assert meta.name != data.with_suffix('').with_suffix('.json').name
    assert data.parent != other.parent and data.name != other.name
    assert {meta, other_meta}.isdisjoint({data, other})


def test_family_data_never_touches_the_published_post_directories():
    published = {mod.ROOT / 'docs/visuals/2026-09-05-layup-season-leaders',
                 mod.ROOT / 'docs/visuals/2026-09-05-floater-season-leaders'}
    for fam in mod.FAMILIES.values():
        directory = mod.data_dir(fam)
        assert published.isdisjoint(set(directory.parents))
    assert len({mod.data_dir(f) for f in mod.FAMILIES.values()}) == len(mod.FAMILIES)


# --- label stability -------------------------------------------------------

def audit_frame(rows):
    """rows: (season, label, fga) — FGM is irrelevant to stability."""
    return pd.DataFrame([dict(SEASON=s, ACTION_TYPE=l, FGA=n, FGM=0) for s, l, n in rows])


def test_new_label_that_adds_volume_moves_the_boundary():
    rows = []
    for year in range(2010, 2016):
        rows += [(mod.season_label(year), 'Floating Jump shot', 10),
                 (mod.season_label(year), 'Jump Shot', 990)]
    for year in range(2016, 2019):
        rows += [(mod.season_label(year), 'Floating Jump shot', 10),
                 (mod.season_label(year), 'Driving Floating Jump Shot', 30),
                 (mod.season_label(year), 'Jump Shot', 960)]
    stability = mod.label_stability(audit_frame(rows), FLOATERS)
    assert stability.boundary == '2016-17'
    assert stability.audited_from == '2010-11'
    verdicts = {r['SEASON']: r['verdict'] for r in stability.introductions}
    assert verdicts['2016-17'] == 'addition'


def test_relabelled_split_keeps_the_earlier_seasons_rankable():
    # The same new label, but the older label gives up the volume: a rename inside
    # the family, so coverage never changed and early seasons stay comparable.
    rows = []
    for year in range(2010, 2016):
        rows += [(mod.season_label(year), 'Layup Shot', 240),
                 (mod.season_label(year), 'Jump Shot', 760)]
    for year in range(2016, 2019):
        rows += [(mod.season_label(year), 'Layup Shot', 200),
                 (mod.season_label(year), 'Cutting Layup Shot', 40),
                 (mod.season_label(year), 'Jump Shot', 760)]
    stability = mod.label_stability(audit_frame(rows), LAYUPS)
    assert stability.boundary == '2010-11'
    assert [r['verdict'] for r in stability.introductions] == ['first audited', 'relabel']


def test_a_label_with_gaps_is_sampling_not_an_era_change():
    rows = []
    for year in range(2010, 2019):
        rows += [(mod.season_label(year), 'Hook Shot', 50),
                 (mod.season_label(year), 'Jump Shot', 950)]
    for year in [2012, 2017, 2018]:   # a rare shot, not taken every season
        rows.append((mod.season_label(year), 'Driving Bank Hook Shot', 20))
    stability = mod.label_stability(audit_frame(rows), HOOKS)
    assert stability.boundary == '2010-11'
    assert stability.sporadic == ['Driving Bank Hook Shot']


def test_an_absent_label_is_unavailable_classification_not_zero():
    rows = [(mod.season_label(y), 'Jump Shot', 1000) for y in range(2010, 2013)]
    for year in range(2013, 2016):
        rows += [(mod.season_label(year), 'Floating Jump shot', 40),
                 (mod.season_label(year), 'Jump Shot', 960)]
    stability = mod.label_stability(audit_frame(rows), FLOATERS)
    # Seasons with no floater label at all are audited, but ranking starts where
    # the classification begins; they are not seasons of zero floaters.
    assert stability.audited_from == '2010-11'
    assert stability.boundary == '2013-14'


def test_empty_audit_cannot_silently_produce_a_window():
    with pytest.raises(ValueError, match='Empty action label audit'):
        mod.label_stability(audit_frame([]), DUNKS)


def test_window_refuses_earlier_seasons_unless_overridden():
    rows = []
    for year in range(2010, 2016):
        rows += [(mod.season_label(year), 'Floating Jump shot', 10),
                 (mod.season_label(year), 'Jump Shot', 990)]
    for year in range(2016, 2019):
        rows += [(mod.season_label(year), 'Floating Jump shot', 10),
                 (mod.season_label(year), 'Driving Floating Jump Shot', 30),
                 (mod.season_label(year), 'Jump Shot', 960)]
    audit = audit_frame(rows)
    chosen, stability, notes = mod.resolve_rank_from(audit, FLOATERS)
    assert chosen == '2016-17'
    # The registry's declared expectation differs from the evidence here; the
    # evidence wins and the difference is reported.
    assert any('differs from the declared' in n for n in notes)
    with pytest.raises(ValueError, match='unavailable classification, not zero floaters'):
        mod.resolve_rank_from(audit, FLOATERS, '2012-13')
    chosen, _, notes = mod.resolve_rank_from(audit, FLOATERS, '2012-13', allow_unstable=True)
    assert chosen == '2012-13'
    assert any(n.startswith('OVERRIDE') for n in notes)


def test_from_season_can_narrow_to_a_single_recent_season():
    rows = []
    for year in range(2016, 2026):
        rows += [(mod.season_label(year), 'Dunk Shot', 200),
                 (mod.season_label(year), 'Jump Shot', 800)]
    chosen, _, notes = mod.resolve_rank_from(audit_frame(rows), DUNKS, '2025-26')
    assert chosen == '2025-26'
    assert any('audited but not ranked' in n for n in notes)


def test_published_windows_are_reproduced_from_the_real_label_audit():
    """The rule must land on both shipped posts' published windows."""
    path = mod.ROOT / 'docs/visuals/2026-09-05-layup-season-leaders/data/action_label_audit.csv'
    if not path.exists():
        pytest.skip('published layup label audit unavailable')
    audit = pd.read_csv(path)
    assert mod.label_stability(audit, LAYUPS).boundary == '2000-01'
    assert mod.label_stability(audit, FLOATERS).boundary == '2015-16'
    # New families, from the same evidence.
    assert mod.label_stability(audit, DUNKS).boundary == '2000-01'
    assert mod.label_stability(audit, HOOKS).boundary == '2000-01'


def test_copy_states_the_window_it_was_ranked_from():
    copy = mod.family_copy(FLOATERS, '2015-16')
    assert copy['title'] == 'Bulls floater scoring leaders'
    assert '2015–16' in copy['subtitle'] and '2015–16' in copy['scope']
    assert 'first season carrying every floater label' in copy['definition']
    assert mod.family_copy(DUNKS, '2000-01')['definition'] == DUNKS.definition
