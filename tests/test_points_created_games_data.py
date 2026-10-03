"""Meaningful metric, completeness and tie-preservation checks for game post."""
import json

import pandas as pd

from scripts.prototypes.points_created_games_data import DATA
from scripts.prototypes.points_created_nba_ranks import game_assist_bounds


def test_teammate_field_goals_tighten_assist_bounds():
    logs = pd.DataFrame([
        {'GAME_ID':'x','TEAM_ID':1,'PTS':30,'AST':4,'FGM':10,'FG3M':8},
        {'GAME_ID':'x','TEAM_ID':1,'PTS':20,'AST':0,'FGM':5,'FG3M':1},
    ])
    bound = game_assist_bounds(logs)
    # The passer's own eight threes cannot be assisted by himself.
    assert bound.loc[0,'minimum_assist_points'] == 8
    assert bound.loc[0,'maximum_assist_points'] == 9


def test_saved_population_certifies_cutoff_and_preserves_every_tie():
    proof = pd.read_csv(DATA/'selection-proof.csv.gz')
    top = pd.read_csv(DATA/'top15.csv')
    coverage = pd.read_csv(DATA/'coverage.csv')
    summary = json.loads((DATA/'verification-summary.json').read_text())
    assert len(coverage) == 30
    assert coverage.games.sum() == proof.GAME_ID.nunique() == 2385
    assert len(proof) == summary['population_player_games'] == 24660
    assert not proof.duplicated(['GAME_ID','PLAYER_ID']).any()
    cutoff = top.created.min()
    exact = proof[proof.status == 'exact']
    assert exact.created.between(exact.minimum_created,exact.maximum_created).all()
    expected = exact[exact.created >= cutoff]
    assert set(zip(top.GAME_ID,top.PLAYER_ID)) == set(zip(expected.GAME_ID,expected.PLAYER_ID))
    assert proof.loc[proof.status=='excluded_by_bound','maximum_created'].max() < cutoff
    assert len(top) == 16
    assert top.created.min() == 61
    assert top['rank'].tolist() == top.created.rank(method='min',ascending=False).astype(int).tolist()
    assert top['rank'].eq(13).sum() == 4


def test_exact_basket_values_match_official_assists_and_graphic():
    proof = pd.read_csv(DATA/'selection-proof.csv.gz')
    events = pd.read_csv(DATA/'candidate-assisted-baskets.csv.gz')
    exact = proof[proof.status == 'exact'].set_index(['GAME_ID','PLAYER_ID'])
    aggregate = events.groupby(['game_id','assister_id']).shot_value.agg(['size','sum'])
    observed = aggregate.reindex(exact.index,fill_value=0)
    assert observed['size'].eq(exact.AST).all()
    assert observed['sum'].eq(exact.assist_pts).all()
    assert exact.created.eq(exact.PTS+exact.assist_pts).all()
    assert events.shot_value.isin([2,3]).all()
    top = pd.read_csv(DATA/'top15.csv')
    demar = top.iloc[0]
    assert (demar.PLAYER_NAME,demar.PTS,demar.AST,demar.assist_pts,demar.created) == ('DeMar DeRozan',41,11,29,70)
    assert abs(demar.team_pct - 100*70/129) < 1e-10
    lavine = top[(top.PLAYER_NAME=='Zach LaVine') & (top.GAME_DATE=='2019-03-01')].iloc[0]
    assert lavine.overtimes == 4
    assert lavine.overtime_label == '4OT'
