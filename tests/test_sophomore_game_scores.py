"""Selection, sophomore-definition and render checks for the sophomore Game Score post."""
import pandas as pd
import pytest

from scripts.prototypes import sophomore_game_scores as post

DATA = post.DATA


def saved(name):
    return pd.read_csv(DATA / f'{name}.csv')


def test_saved_selection_reproduces_from_saved_sophomore_games():
    ranked = post.select_top(saved('sophomore-games'))
    top = saved('top-fifteen')
    assert ranked.player_id.tolist() == top.player_id.tolist()
    assert ranked.game_id.astype(int).tolist() == top.game_id.astype(int).tolist()
    assert (ranked.iloc[0].player, ranked.iloc[0].pool) == ('Derrick Rose', 'Regular season')
    assert ranked.iloc[0].game_score == pytest.approx(35.7)
    assert ranked['rank'].tolist() == list(range(1, 16))
    assert ranked.player.value_counts().max() == 2


def test_the_top_row_matches_a_hand_computed_game_score():
    """Game Score = PTS + .4FGM - .7FGA - .4(FTA-FTM) + .7ORB + .3DRB + STL + .7AST + .7BLK - .4PF - TOV."""
    row = saved('top-fifteen').iloc[0]
    expected = (row.points + 0.4 * row.fgm - 0.7 * row.fga - 0.4 * (row.fta - row.ftm)
                + 0.7 * row.oreb + 0.3 * row.dreb + row.stl + 0.7 * row.ast + 0.7 * row.blk
                - 0.4 * row.pf - row.tov)
    assert expected == pytest.approx(35.7)


def test_the_cutoff_is_clean_and_no_score_repeats_inside_the_top_fifteen():
    scores = saved('sophomore-games').game_score.round(1).nlargest(16).tolist()
    assert scores[14] == pytest.approx(28.9) and scores[15] == pytest.approx(28.4)
    top = saved('top-fifteen')
    assert not top.game_score.duplicated().any()


def test_float_noise_does_not_override_the_points_tiebreak():
    rows = saved('sophomore-games').head(16).copy()
    rows['game_score'] = [30.0 - i for i in range(16)]
    rows.loc[rows.index[0], ['game_score', 'points']] = [25.2 - 1e-12, 30]
    rows.loc[rows.index[1], ['game_score', 'points']] = [25.2, 10]
    ranked = post.select_top(rows)
    tied = ranked.loc[ranked.game_score.eq(25.2)]
    assert tied.points.tolist() == [30, 10]


def test_tie_across_the_cutoff_is_rejected():
    rows = saved('sophomore-games').head(16).copy()
    rows['game_score'] = [30.0 - i for i in range(14)] + [10.0, 10.0]
    with pytest.raises(ValueError, match='cutoff'):
        post.select_top(rows)


def test_sophomore_filter_agrees_with_first_season_except_the_missed_seasons():
    audit = saved('sophomore-audit')
    assert audit.games.eq(audit.bulls_game_rows).all()
    disagreements = audit.loc[~audit.first_season_agrees, ['season', 'player_id']]
    assert set(map(tuple, disagreements.values)) == post.KNOWN_FIRST_SEASON_DISAGREEMENTS
    # Each is a player who missed a full season, so NBA.com's experience clock starts later
    # than CommonAllPlayers' first roster year.
    assert (audit.loc[~audit.first_season_agrees, 'season']
            - audit.loc[~audit.first_season_agrees, 'common_all_players_from_year']).gt(2).all()


def test_playoff_games_share_the_pool_even_though_none_reached_the_top_fifteen():
    games = saved('sophomore-games')
    assert games.pool.eq('Playoffs').sum() == 117
    assert set(games.loc[games.pool.eq('Playoffs'), 'season_end_year']) <= post.PLAYOFF_SEASONS
    assert saved('top-fifteen').pool.eq('Regular season').all()


def test_playoff_context_reads_round_and_game_from_the_nba_game_id():
    assert post.playoff_context('0040800101') == '(RD 1 GM1)'
    assert post.playoff_context(41000203) == '(RD 2 GM3)'


def test_overtime_games_in_the_top_fifteen_are_recorded():
    top = saved('top-fifteen').set_index('rank')
    assert top.overtime_periods.gt(0).sum() == 3
    assert top.loc[[3, 10, 14], 'overtime_periods'].tolist() == [1, 1, 1]


def test_both_formats_render_without_free_throws(tmp_path, monkeypatch):
    ranked = post.select_top(saved('sophomore-games'))
    monkeypatch.setattr(post.games, 'OUT', tmp_path)
    monkeypatch.setattr(post.games, 'ensure_headshots', lambda _: None)
    table = post.games.render_chart(
        ranked, '2026-09-20', decade=post.LABEL, show_free_throws=False, show_turnovers=True,
        top_n=15, layout=post.TABLE_LAYOUT, emphasize_points=True, shooting_after_assists=True)
    assert table.exists()
    assert post.render_boxed(ranked, final=False).exists()


def test_shooting_columns_follow_assists_and_default_order_is_unchanged():
    row = saved('top-fifteen').iloc[0]  # Rose: 39 pts, 15-22 FG, 0-0 3PT, 5 reb, 7 ast
    assert post.games._turnover_values(row, False)[:5] == ('39', '15–22', '0–0', '5', '7')
    assert post.games._turnover_values(row, False, True)[:5] == ('39', '5', '7', '15–22', '0–0')
    with pytest.raises(ValueError, match='without FT'):
        post.games.render_chart(saved('top-fifteen'), '2026-09-24', decade=post.LABEL,
                                show_free_throws=True, show_turnovers=True, top_n=15,
                                shooting_after_assists=True)
