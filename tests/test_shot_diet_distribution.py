import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location(
    'shot_diet', ROOT / 'scripts/prototypes/shot_diet_distribution.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PUBLISHED = ROOT / 'docs/visuals/2026-09-06-shot-diet-distribution/data'
BULLS_FGA = 7417  # official 2025-26 regular-season team total


def test_classification_priority_keeps_compound_labels_with_the_right_family():
    """The order of FAMILY_RULES is the claim; a flat sweep miscounts these."""
    assert mod.classify('Turnaround Hook Shot') == 'Hooks'
    assert mod.classify('Turnaround Fadeaway shot') == 'Turnarounds/fades'
    assert mod.classify('Driving Floating Bank Jump Shot') == 'Floaters'
    assert mod.classify('Tip Layup Shot') == 'Tip-ins'
    assert mod.classify('Putback Dunk Shot') == 'Dunks'
    assert mod.classify('Driving Finger Roll Layup Shot') == 'Layups'
    assert mod.classify('Running Pull-Up Jump Shot') == 'Pull-ups'
    assert mod.classify('Step Back Bank Jump Shot') == 'Step-backs'


def test_unlabelled_default_is_its_own_family_not_a_technique():
    assert mod.classify('Jump Shot') == mod.UNLABELLED
    assert mod.classify('Jump Bank Shot') == mod.UNLABELLED
    # It stays a separate family rather than being folded into a technique bucket:
    # tracking corroborates its size and rank, but it is still not a described shot.
    assert mod.UNLABELLED not in dict(mod.FAMILY_RULES)


def test_every_action_type_lands_in_exactly_one_family():
    """Coverage: an unmatched label must fall to the default, never disappear."""
    families = {name for name, _ in mod.FAMILY_RULES} | {mod.UNLABELLED}
    labels = ['Jump Shot', 'Driving Layup Shot', 'Cutting Dunk Shot', 'Hook Shot',
              'No Shot', 'Running Alley Oop Layup Shot', '']
    assert all(mod.classify(label) in families for label in labels)


def test_reconcile_rejects_shot_rows_that_disagree_with_official_totals(monkeypatch):
    shots = pd.DataFrame({'TEAM_ID': [mod.BULLS] * 3, 'SHOT_MADE_FLAG': [1, 0, 1]})
    monkeypatch.setattr(mod, 'official_totals', lambda: pd.DataFrame(
        {'TEAM_ID': [mod.BULLS], 'TEAM_NAME': ['Chicago Bulls'], 'FGA': [4], 'FGM': [2]}))
    with pytest.raises(ValueError, match='disagree with official totals'):
        mod.reconcile(shots)

    monkeypatch.setattr(mod, 'official_totals', lambda: pd.DataFrame(
        {'TEAM_ID': [mod.BULLS], 'TEAM_NAME': ['Chicago Bulls'], 'FGA': [3], 'FGM': [2]}))
    assert mod.reconcile(shots).FGA_DIFF.eq(0).all()


def test_shares_are_derived_from_attempts_not_restated():
    shots = pd.DataFrame({
        'TEAM_ID': [mod.BULLS] * 4, 'TEAM_NAME': ['Chicago Bulls'] * 4,
        'ACTION_TYPE': ['Jump Shot', 'Jump Shot', 'Driving Layup Shot', 'Hook Shot'],
        'SHOT_MADE_FLAG': [1, 0, 1, 0]})
    shots['FAMILY'] = shots.ACTION_TYPE.map(mod.classify)
    _, chart = mod.build_tables(shots)
    shares = dict(zip(chart.FAMILY, chart.SHARE))
    assert shares[mod.UNLABELLED] == pytest.approx(50.0)
    assert shares['Layups'] == pytest.approx(25.0)
    assert chart.SHARE.sum() == pytest.approx(100.0)


def test_ordinal_handles_the_teens_that_break_the_last_digit_rule():
    assert [mod.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 30)] == [
        '1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '30th']


@pytest.mark.skipif(not PUBLISHED.exists(), reason='post data not prepared')
def test_published_table_covers_the_whole_season_and_sums_to_one_hundred():
    chart = pd.read_csv(PUBLISHED / 'bulls-family-shares.csv')
    assert chart.FGA.sum() == BULLS_FGA
    assert chart.SHARE.sum() == pytest.approx(100.0, abs=0.05)
    assert chart.LEAGUE_SHARE.sum() == pytest.approx(100.0, abs=0.05)
    # Sorted by share, so the chart's row order comes from the data, not a literal list.
    assert chart.SHARE.is_monotonic_decreasing
    assert chart.RANK.between(1, 30).all()


def test_display_label_trims_only_the_shared_shot_suffix():
    assert mod.display_label('Driving Finger Roll Layup Shot') == 'Driving Finger Roll Layup'
    assert mod.display_label('Floating Jump shot') == 'Floating Jump'   # lower-case variant
    assert mod.display_label('Jump Shot') == 'Jump'
    # "Shot" inside a label, not at the end, must survive.
    assert mod.display_label('Shot Clock Jump Shot') == 'Shot Clock Jump'


def test_split_families_balances_on_rendered_lines_and_keeps_families_whole():
    vocab = pd.DataFrame({
        'FAMILY': ['Big'] * 14 + ['Mid'] * 4 + ['Small'] * 1 + ['Tiny'] * 1,
        'ACTION_TYPE': [f'a{i}' for i in range(20)]})
    left, right = mod.split_families(vocab)
    assert [name for name, _ in left] + [name for name, _ in right] == [
        'Big', 'Mid', 'Small', 'Tiny']
    lines = lambda side: sum(len(g) + 1 for _, g in side)
    # Balanced on lines: Big alone is 15 lines against the other three families' 9.
    assert lines(left) == 15 and lines(right) == 9
    assert all(len(g.FAMILY.unique()) == 1 for _, g in left + right)


@pytest.mark.skipif(not PUBLISHED.exists(), reason='post data not prepared')
def test_vocabulary_accounts_for_every_attempt_and_every_label():
    vocab = pd.read_csv(PUBLISHED / 'bulls-shot-vocabulary.csv')
    chart = pd.read_csv(PUBLISHED / 'bulls-family-shares.csv')
    assert vocab.FGA.sum() == BULLS_FGA
    assert vocab.FGM.sum() == chart.FGM.sum()
    assert len(vocab) == vocab.ACTION_TYPE.nunique() == 48
    # Every family total on slide one is reproduced by its labels on slide two.
    rolled = vocab.groupby('FAMILY').FGA.sum()
    assert (rolled[chart.FAMILY].values == chart.FGA.values).all()
    # Families keep slide one's share order so the two slides can be read together.
    assert list(dict.fromkeys(vocab.FAMILY)) == list(chart.FAMILY)
    assert vocab.SHARE.sum() == pytest.approx(100.0, abs=0.05)


def test_format_share_never_prints_a_rounded_zero():
    assert mod.format_share(34.53) == '34.5'
    assert mod.format_share(0.05) == '0.1'
    # 1 attempt in 7,417 is 0.013% -- "0.0" would read as none at all.
    assert mod.format_share(1 / 7417 * 100) == '<0.1'
    assert mod.format_share(0.0) == '<0.1'


@pytest.mark.skipif(not PUBLISHED.exists(), reason='post data not prepared')
def test_low_attempt_labels_exist_and_would_have_their_percentage_suppressed():
    """The suppression rule only matters if the season actually contains such labels."""
    vocab = pd.read_csv(PUBLISHED / 'bulls-shot-vocabulary.csv')
    thin = vocab[vocab.FGA < mod.MIN_ATTEMPTS_FOR_PCT]
    assert len(thin) > 0
    assert thin.FGA.max() < mod.MIN_ATTEMPTS_FOR_PCT
    # A 1-for-1 label would otherwise print as 100%, which is not a shooting rate.
    assert (thin.FG_PCT.max() == 100.0) or (thin.FGA.min() == 1)


@pytest.mark.skipif(not PUBLISHED.exists(), reason='post data not prepared')
def test_published_reconciliation_shows_no_team_off_by_a_single_attempt():
    recon = pd.read_csv(PUBLISHED / 'team-fga-reconciliation.csv')
    assert len(recon) == 30
    assert recon.FGA_DIFF.eq(0).all()
    assert recon.FGM_DIFF.eq(0).all()
