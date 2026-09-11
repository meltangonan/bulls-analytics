"""Coverage, metric, uncertainty and selection checks for catch-and-shoot."""
import pandas as pd
import pytest
from scripts.prototypes import catch_and_shoot_points_data as post


def test_weighted_efficiency_rejects_missing():
    rows = pd.DataFrame({'CATCH_SHOOT_PTS': [3, 8], 'CATCH_SHOOT_FGA': [1, 9]})
    assert post.weighted_efg(rows) == 55
    rows.loc[0, 'CATCH_SHOOT_PTS'] = float('nan')
    with pytest.raises(ValueError, match='Missing'):
        post.weighted_efg(rows)


def test_missing_three_attempts_stay_bounded():
    players = pd.DataFrame(dict(PLAYER_ID=[1, 2], CATCH_SHOOT_PTS=[4, 0],
        CATCH_SHOOT_FGM=[2, 0], CATCH_SHOOT_FGA=[8, 0],
        CATCH_SHOOT_FG3M=[None, None], CATCH_SHOOT_FG3A=[None, None]))
    official = pd.DataFrame(dict(PLAYER_ID=[1, 2], FG3M=[0, 0], FG3A=[1, 3]))
    result = post.three_bounds(players, official)
    assert result.fg3m.tolist() == [0, 0]
    assert result.fg3a_low.tolist() == [0, 0]
    assert result.fg3a_high.tolist() == [1, 0]


def test_all_seasons_and_rankings_reproduce():
    frames = []
    for season in post.SEASONS:
        frame, _ = post.summarize(post.fetch('bulls', season), post.fetch('official', season),
            post.fetch('league', season), season, post.fetch('league_players', season))
        frames.append(frame)
    all_rows = pd.concat(frames, ignore_index=True)
    total = post.ranked(all_rows)
    saved = pd.read_csv(post.DATA / 'top15.csv')
    assert len(frames) == 13
    assert total.pts.tolist() == saved.pts.tolist()
    assert total.player_id.tolist() == saved.player_id.tolist()
    assert total.iloc[0].pts == 529
    assert total.iloc[0].pts_per_game == pytest.approx(529 / 82)
    three = all_rows.copy()
    three['pts'] = 3 * three.fg3m
    three['fgm'] = three.fg3m
    ranked = post.ranked(three)
    saved_three = pd.read_csv(post.DATA / 'top15_three_point.csv')
    assert ranked.player_id.tolist() == saved_three.player_id.tolist()
    assert ranked.pts.tolist() == saved_three.pts.tolist()
    assert ranked.iloc[0].pts == 435
    assert (three.pts == ranked.iloc[-1].pts).sum() == 3  # All cutoff ties included.


def test_saved_attempt_baselines_use_player_appearances():
    for season in post.SEASONS:
        rows = pd.read_csv(post.DATA / 'top15.csv').query('season == @season')
        official = post.fetch('official_league', season)
        league = post.fetch('league_players', season)
        baseline = league.CATCH_SHOOT_FGA.sum() / official.GP.sum()
        points_baseline = league.CATCH_SHOOT_PTS.sum() / official.GP.sum()
        assert rows.relative_pts_per_game.tolist() == pytest.approx(
            (rows.pts / rows.gp - points_baseline).tolist())
        threes = pd.read_csv(post.DATA / 'top15_three_point.csv').query('season == @season')
        three_points_baseline = 3 * (league.CATCH_SHOOT_PTS - 2 * league.CATCH_SHOOT_FGM).sum() / official.GP.sum()
        assert threes.relative_pts_per_game.tolist() == pytest.approx(
            (threes.pts / threes.gp - three_points_baseline).tolist())
        assert rows.league_fga_per_game.tolist() == pytest.approx([baseline] * len(rows))
        assert rows.relative_fga_per_game.tolist() == pytest.approx(
            (rows.fga / rows.gp - baseline).tolist())


def test_unresolved_attempts_cannot_change_displayed_values():
    rows = pd.read_csv(post.DATA / 'top15_three_point.csv')
    assert rows.fga.notna().all()
    assert rows.efg_pct.tolist() == pytest.approx((100 * rows.fg3m / rows.fg3a).tolist())
    assert (rows.relative_efg_pp.round(1) == rows.relative_3p_pp_high.round(1)).all()
    assert (rows.relative_fga_per_game.round(1) == rows.relative_3pa_per_game_low.round(1)).all()


def test_wrong_chicago_gp_rejected_and_source_difference_preserved():
    season = '2024-25'
    players, official, league, league_players = [post.fetch(k, season) for k in
        ['bulls', 'official', 'league', 'league_players']]
    result, audit = post.summarize(players, official, league, season, league_players)
    assert audit['CATCH_SHOOT_FGA_difference'] == -25
    assert result.fga.sum() == players.CATCH_SHOOT_FGA.sum()
    official.loc[official.PLAYER_ID == 203897, 'GP'] = 63
    with pytest.raises(ValueError, match='GP differs'):
        post.summarize(players, official, league, season, league_players)
