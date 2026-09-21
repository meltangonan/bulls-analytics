"""Exact rank certification must stay conservative until unresolved assists are read."""
import pandas as pd
import pytest
from scripts.prototypes.points_created_nba_ranks import intervals, compare


def test_unknown_assists_remain_an_interval_and_ties_do_not_rank_above():
    box=pd.DataFrame({'PLAYER_ID':[1,2,3,4], 'PLAYER_NAME':['Bull','Tie','Above','Unknown'],
                      'PTS':[100,90,101,90], 'AST':[10,10,10,10]}).set_index('PLAYER_ID')
    known=pd.DataFrame({'PLAYER_ID':[1,2,3,4], 'known_ast':[10,10,0,0],
                        'known_assist_points':[20,30,0,0]}).set_index('PLAYER_ID')
    target=pd.DataFrame([{'PLAYER_ID':1,'PLAYER_NAME':'Bull','season':'2010-11','created':120}])
    f=intervals(box,known)
    p=compare(f,target).set_index('opponent_id')
    assert 1 not in p.index
    assert p.loc[2,'relation']=='not_above'  # Equal totals share rank.
    assert p.loc[3,'relation']=='above'      # Even all twos puts him above.
    assert p.loc[4,'relation']=='not_above'  # Even all threes merely ties.
    target.loc[0,'created']=119
    assert compare(f,target).set_index('opponent_id').loc[4,'relation']=='unresolved'


def test_verified_baskets_narrow_bounds_without_imputing_remaining_values():
    box=pd.DataFrame({'PLAYER_ID':[2],'PLAYER_NAME':['Other'],'PTS':[100],'AST':[10]}).set_index('PLAYER_ID')
    known=pd.DataFrame({'PLAYER_ID':[2],'known_ast':[6],'known_assist_points':[15]}).set_index('PLAYER_ID')
    f=intervals(box,known)
    assert f.loc[2,'minimum_created']==123
    assert f.loc[2,'maximum_created']==127
    assert f.loc[2,'remaining_ast']==4
    known.loc[2,'known_ast']=11
    with pytest.raises(ValueError,match='exceed'):intervals(box,known)


def test_teammate_baskets_tighten_limits_without_assumptions():
    from scripts.prototypes.points_created_nba_ranks import game_assist_bounds
    rows=pd.DataFrame({'GAME_ID':['1']*3,'TEAM_ID':[1]*3,'PLAYER_ID':[1,2,3],
                       'AST':[4,0,0],'FGM':[2,3,1],'FG3M':[2,1,0]})
    f=game_assist_bounds(rows).set_index('PLAYER_ID')
    # Player1 assisted all four teammate baskets: three twos and one three.
    # His own two made threes cannot be among his assists.
    assert f.loc[1,'minimum_assist_points']==9
    assert f.loc[1,'maximum_assist_points']==9
    for ast in range(5):
        rows.loc[0,'AST']=ast
        f=game_assist_bounds(rows).set_index('PLAYER_ID')
        feasible=[2*twos+3*threes for twos in range(4) for threes in range(2)
                  if twos+threes==ast]
        assert f.loc[1,'minimum_assist_points']==min(feasible)
        assert f.loc[1,'maximum_assist_points']==max(feasible)
