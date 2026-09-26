"""Selection, sophomore-definition, coverage-gap and render checks for the sophomore post."""
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
    first = ranked.iloc[0]
    assert (first.player, first.pool, first.context_note) == ('Michael Jordan', 'Playoffs', '(RD 1 GM2)')
    assert first.game_score == pytest.approx(47.2)
    assert ranked.pool.eq('Playoffs').sum() == 1
    assert ranked['rank'].tolist() == list(range(1, 16))
    assert ranked.player.value_counts().max() == 2


def test_the_top_row_matches_a_hand_computed_game_score():
    """Jordan's 63 at Boston: 63 + .4(22) - .7(41) - .4(21-19) + .7(1) + .3(4) + 3 + .7(6) + .7(2) - .4(4) - 4."""
    row = saved('top-fifteen').iloc[0]
    expected = (row.points + 0.4 * row.fgm - 0.7 * row.fga - 0.4 * (row.fta - row.ftm)
                + 0.7 * row.oreb + 0.3 * row.dreb + row.stl + 0.7 * row.ast + 0.7 * row.blk
                - 0.4 * row.pf - row.tov)
    assert expected == pytest.approx(47.2)


def test_the_points_tiebreak_orders_kukoc_before_brand_and_the_cutoff_is_clean():
    ranked = post.select_top(saved('sophomore-games'))
    tied = ranked.loc[ranked.game_score.eq(31.2)]
    assert tied.player.tolist() == ['Toni Kukoc', 'Elton Brand'] and tied.points.tolist() == [33, 30]
    scores = saved('sophomore-games').game_score.round(1).nlargest(16).tolist()
    assert scores[14] == pytest.approx(29.8) and scores[15] == pytest.approx(29.5)


def test_float_noise_does_not_override_the_points_tiebreak():
    rows = saved('sophomore-games').head(16).copy()
    rows['game_score'] = [30.0 - i for i in range(16)]
    rows.loc[rows.index[0], ['game_score', 'points']] = [25.2 - 1e-12, 30]
    rows.loc[rows.index[1], ['game_score', 'points']] = [25.2, 10]
    tied = post.select_top(rows).loc[lambda f: f.game_score.eq(25.2)]
    assert tied.points.tolist() == [30, 10]


def test_tie_across_the_cutoff_is_rejected():
    rows = saved('sophomore-games').head(16).copy()
    rows['game_score'] = [30.0 - i for i in range(14)] + [10.0, 10.0]
    with pytest.raises(ValueError, match='cutoff'):
        post.select_top(rows)


def test_second_season_counts_seasons_played_once_each():
    careers = pd.DataFrame({
        'PLAYER_ID': [1, 1, 1, 1, 2, 2, 3],
        'SEASON_ID': ['1986-87', '1986-87', '1986-87', '1988-89', '1990-91', '1991-92', '1995-96'],
        'LEAGUE_ID': [0] * 7,
        'GP': [16, 49, 65, 33, 10, 0, 40],
    })
    second = post.second_seasons_played(careers)
    # A traded player's team and TOT rows count once; a skipped season is not a season played;
    # a 0-game roster season does not count; one-season players have no sophomore year.
    assert second[1] == 1989 and 2 not in second and 3 not in second
    assert second[2839] == 2006  # James Thomas, from the hand-checked career gap


def test_rule_matches_nba_filter_everywhere_except_anstey():
    audit = saved('sophomore-audit')
    labelled = audit.loc[audit.nba_sophomore_filter.notna()]
    wrong = labelled.loc[labelled.nba_sophomore_filter.astype(bool) != labelled.second_season_played]
    assert set(zip(wrong.season, wrong.player_id)) == post.KNOWN_FILTER_DISAGREEMENTS == {(2000, 1512)}
    assert audit.loc[audit.season.lt(1997), 'nba_sophomore_filter'].isna().all()
    assert audit.second_season_played.sum() == 111


def test_first_season_audit_differs_only_for_players_who_missed_a_season():
    audit = saved('sophomore-audit')
    rule = audit.loc[audit.second_season_played]
    off = rule.loc[~rule.first_season_agrees]
    assert set(zip(off.season, off.player_id)) == post.KNOWN_FIRST_SEASON_DISAGREEMENTS
    assert (off.season - off.common_all_players_from_year).gt(2).all()


def test_documented_coverage_gaps_cannot_reach_the_top_fifteen():
    reconciliation = saved('reconciliation')
    short = reconciliation.loc[reconciliation.unattributed_points.gt(0)]
    assert dict(zip(short.game_id.astype(str).str.zfill(10), short.unattributed_points)) == post.UNATTRIBUTED_POINTS
    assert (reconciliation.player_points + reconciliation.unattributed_points).eq(reconciliation.team_points).all()
    cutoff = saved('top-fifteen').game_score.min()
    assert max(post.INCOMPLETE_BOX_SCORES.values()) < cutoff


def test_playoff_context_reads_round_and_game_from_the_nba_game_id():
    assert post.playoff_context('0048500102') == '(RD 1 GM2)'
    assert post.playoff_context(41000203) == '(RD 2 GM3)'


def test_playoff_games_come_only_from_bulls_postseason_runs():
    games = saved('sophomore-games')
    assert games.pool.value_counts().to_dict() == {'Regular season': 4865, 'Playoffs': 276}
    assert set(games.loc[games.pool.eq('Playoffs'), 'season_end_year']) <= post.PLAYOFF_SEASONS


def test_overtime_games_in_the_top_fifteen_are_recorded():
    top = saved('top-fifteen').set_index('rank')
    assert top.overtime_periods.gt(0).sum() == 3
    assert top.loc[[1, 5, 14], 'overtime_periods'].tolist() == [2, 1, 1]


def test_shooting_columns_follow_assists_and_default_order_is_unchanged():
    row = saved('top-fifteen').iloc[2]  # Rose: 39 pts, 15-22 FG, 0-0 3PT, 5 reb, 7 ast
    assert post.games._turnover_values(row, False)[:5] == ('39', '15–22', '0–0', '5', '7')
    assert post.games._turnover_values(row, False, True)[:5] == ('39', '5', '7', '15–22', '0–0')
    with pytest.raises(ValueError, match='without FT'):
        post.games.render_chart(saved('top-fifteen'), '2026-09-26', decade=post.LABEL,
                                show_free_throws=True, show_turnovers=True, top_n=15,
                                shooting_after_assists=True)


def test_table_renders_without_plus_minus(tmp_path, monkeypatch):
    ranked = post.select_top(saved('sophomore-games'))
    monkeypatch.setattr(post.games, 'OUT', tmp_path)
    monkeypatch.setattr(post.games, 'ensure_headshots', lambda _: None)
    table = post.games.render_chart(
        ranked, '2026-09-26', decade=post.LABEL, show_free_throws=False, show_turnovers=True,
        top_n=15, layout=post.TABLE_LAYOUT, emphasize_points=True, shooting_after_assists=True,
        show_plus_minus=False)
    assert table.exists()
