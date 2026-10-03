from types import SimpleNamespace
import pandas as pd
import pytest
from scripts.prototypes.points_created_games_nba_ranks import certificate,classify,validate_population


def population():
    return pd.DataFrame({'GAME_ID':['a','b','c','d'], 'PLAYER_ID':[1,1,2,3], 'minimum_created':[70,72,70,69], 'maximum_created':[70,72,70,69]})


def test_rank_counts_same_player_other_game_and_exact_ties():
    f=population()
    r=certificate(f,SimpleNamespace(season='2023-24',GAME_ID='a',PLAYER_ID=1,created=70))
    assert r['nba_season_rank']==2
    assert r['nba_season_tie_count']==2
    assert r['nba_season_rank_label']=='T-2nd'


def test_unavailable_pbp_is_safe_only_when_strictly_outside_target():
    f=population()
    f.loc[3,['minimum_created','maximum_created']]=[40,69]
    assert certificate(f,SimpleNamespace(season='2023-24',GAME_ID='a',PLAYER_ID=1,created=70))['nba_season_rank']==2
    f.loc[3,'maximum_created']=70
    with pytest.raises(ValueError,match='Unavailable/unresolved'):
        certificate(f,SimpleNamespace(season='2023-24',GAME_ID='a',PLAYER_ID=1,created=70))


def test_bounds_equal_to_target_are_unresolved_unless_collapsed():
    f=pd.DataFrame({'minimum_created':[70,69,71,70], 'maximum_created':[72,70,74,70]})
    assert classify(f,70).tolist()==['unresolved','unresolved','above','equal']


def test_population_coverage_rejects_missing_game_row():
    f=pd.DataFrame({'GAME_ID':['a','a'], 'PLAYER_ID':[1,2], 'TEAM_ID':[10,20], 'PTS':[3,4], 'AST':[0,0], 'FGM':[1,2], 'FG3M':[1,0]})
    s=f[['PLAYER_ID','PTS','AST','FGM','FG3M']].assign(GP=1)
    validate_population(f,s)
    with pytest.raises(ValueError,match='full-season totals'):
        validate_population(f.iloc[:1],s)


def test_target_game_itself_must_be_reconciled():
    with pytest.raises(ValueError,match='Target reconciliation'):
        certificate(population(),SimpleNamespace(season='2023-24',GAME_ID='wrong',PLAYER_ID=1,created=70))


def test_literal_prefix_normalization_requires_unique_same_team_roster():
    from scripts.prototypes.points_created_games_nba_ranks import normalize_literal_first_prefixes
    frame=pd.DataFrame({'description':['Ilyasova Layup (Marc Morris 1 AST)'],'teamId':[10],'actionNumber':[236],'personId':[9]})
    logs=pd.DataFrame({'TEAM_ID':[10,20],'PLAYER_NAME':['Marcus Morris Sr.','Markieff Morris'],'PLAYER_ID':[1,2]})
    result,changes=normalize_literal_first_prefixes(frame,logs)
    assert result.description.iloc[0]=='Ilyasova Layup (Marc. Morris 1 AST)'
    assert changes[0]['player_id']==1
    ambiguous=pd.concat([logs,pd.DataFrame({'TEAM_ID':[10],'PLAYER_NAME':['Marcellus Morris'],'PLAYER_ID':[3]})],ignore_index=True)
    result,changes=normalize_literal_first_prefixes(frame,ambiguous)
    assert result.description.iloc[0]==frame.description.iloc[0]
    assert changes==[]


def test_historical_alias_has_direct_person_id_evidence_and_ambiguity_guard():
    from scripts.prototypes.points_created_games_nba_ranks import normalize_literal_first_prefixes
    frame=pd.DataFrame({'description':['MISS Kanter Layup','Westbrook Layup (Kanter 1 AST)'],'teamId':[10,10],'actionNumber':[1,2],'personId':[202683,1]})
    logs=pd.DataFrame({'TEAM_ID':[10,10],'PLAYER_NAME':['Enes Freedom','Russell Westbrook'],'PLAYER_ID':[202683,1]})
    result,changes=normalize_literal_first_prefixes(frame,logs)
    assert result.description.iloc[1]=='Westbrook Layup (Enes Freedom 1 AST)'
    assert changes[0]['evidence_action_number']==1
    missing=frame.copy();missing.loc[0,'description']='MISS Freedom Layup'
    with pytest.raises(ValueError,match='direct NBA person-ID evidence'):
        normalize_literal_first_prefixes(missing,logs)
    ambiguous=pd.concat([logs,pd.DataFrame({'TEAM_ID':[10],'PLAYER_NAME':['Other Kanter'],'PLAYER_ID':[3]})],ignore_index=True)
    with pytest.raises(ValueError,match='Ambiguous historical name'):
        normalize_literal_first_prefixes(frame,ambiguous)
