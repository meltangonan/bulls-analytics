import importlib.util
from pathlib import Path

import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location('layups', Path(__file__).parents[1] / 'scripts/prototypes/layup_season_leaders.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_historical_family_and_tip_exclusion():
    labels = pd.Series(['Layup Shot', 'Driving Finger Roll Shot', 'Finger Roll Shot',
                        'Cutting Finger Roll Layup Shot', 'Putback Layup Shot',
                        'Tip Shot', 'Tip Layup Shot', 'Tip Dunk Shot', 'Dunk Shot',
                        'Driving Floating Jump Shot', None])
    assert mod.is_layup(labels).tolist() == [True]*5 + [False]*6


def fixtures():
    shots = pd.DataFrame(dict(PLAYER_ID=[1,1,1], TEAM_ID=[mod.TEAM]*3,
                              GAME_ID=['a','b','b'], GAME_EVENT_ID=[1,2,3],
                              ACTION_TYPE=['Layup Shot','Finger Roll Shot','Jump Shot'],
                              SHOT_MADE_FLAG=[1,0,1], SHOT_TYPE=['2PT Field Goal']*3))
    players = pd.DataFrame(dict(PLAYER_ID=[1,2], PLAYER_NAME=['A','B'], GP=[4,2],
                                FGA=[3,0], FGM=[2,0]))
    return shots, players


def test_rates_use_all_games_and_zero_attempt_efficiency_is_missing():
    result, audit = mod.summarize(*fixtures())
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
    shots, players = fixtures()
    _, audit = mod.summarize(shots.iloc[:0], players)
    assert pd.isna(audit.iloc[0].fga_delta)
    assert audit.iloc[0].partition_delta == -3


def test_duplicate_event_and_three_point_layup_are_rejected():
    shots, players = fixtures()
    with pytest.raises(ValueError, match='Duplicate shot'):
        mod.summarize(pd.concat([shots, shots.iloc[:1]]), players)
    shots.loc[0,'SHOT_TYPE'] = '3PT Field Goal'
    with pytest.raises(ValueError, match='Non-two-point'):
        mod.summarize(shots, players)


def test_wide_portrait_preserves_visible_hair_and_equal_axis_scale(tmp_path):
    import numpy as np
    import matplotlib.pyplot as plt
    from bulls.graphics.house import top_anchored_headshot_label
    source = np.zeros((100,160,4))
    source[:60,15:150,:] = 1
    path = tmp_path / 'wide.png'
    plt.imsave(path,source)
    fig,ax = plt.subplots()
    artist = top_anchored_headshot_label(ax,path,100,100,40,crop_fraction=.64,preserve_width=True)
    drawn = np.asarray(artist.get_array())
    left,right,bottom,top = artist.get_extent()
    assert drawn[:,:,3].sum() == pytest.approx(source[:64,:,3].sum())
    assert (right-left)/drawn.shape[1] == pytest.approx((top-bottom)/drawn.shape[0])
    plt.close(fig)


def test_relative_baseline_cannot_drop_a_player_season():
    top = pd.DataFrame({'SEASON': ['2000-01', '2001-02'], 'FG_PCT': [.6, .5]})
    baseline = pd.DataFrame({'SEASON': ['2000-01'], 'league_layup_fg_pct': [.55]})
    with pytest.raises(ValueError, match='Missing seasonal'):
        mod.merge_relative_fg(top, baseline)
    baseline = pd.concat([baseline, pd.DataFrame({'SEASON': ['2001-02'],
                                                'league_layup_fg_pct': [.6]})])
    result = mod.merge_relative_fg(top, baseline)
    assert result.SEASON.tolist() == top.SEASON.tolist()
    assert result.rFG_PCT.tolist() == pytest.approx([5., -10.])


def test_league_reconciliation_exposes_missing_or_truncated_team():
    shots, _ = fixtures()
    official = pd.DataFrame(dict(TEAM_ID=[mod.TEAM, 2], TEAM_NAME=['Bulls', 'Other'],
                                 GP=[2, 1], FGA=[3, 1], FGM=[2, 1]))
    audit = mod.reconcile_league(shots, official).set_index('TEAM_ID')
    assert audit.loc[mod.TEAM][['fga_delta','fgm_delta','gp_delta']].eq(0).all()
    assert audit.loc[2][['fga_delta','fgm_delta','gp_delta']].isna().all()
    truncated = mod.reconcile_league(shots.iloc[:2], official).set_index('TEAM_ID')
    assert truncated.loc[mod.TEAM].fga_delta == -1
    with pytest.raises(ValueError, match='Duplicate league shot'):
        mod.reconcile_league(pd.concat([shots,shots.iloc[:1]]), official)


def test_compressed_snapshot_loads_without_fetching(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'DATA', tmp_path)
    (tmp_path / 'raw').mkdir()
    pd.DataFrame({'GAME_ID': ['001'], 'GAME_DATE': ['20200101'], 'FGA': [2]}).to_csv(
        tmp_path / 'raw' / 'shots_2000-01.csv.gz', index=False)
    result = mod.fetch_frame('shots', '2000-01')
    assert result.GAME_ID.tolist() == ['001']
    assert result.FGA.tolist() == [2]
