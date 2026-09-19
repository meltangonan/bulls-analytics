"""Selection, rookie-definition and portrait checks for the rookie Game Score post."""
import pandas as pd
import pytest
from PIL import Image

from scripts.prototypes import rookie_game_scores as post

DATA = post.DATA


def saved(name):
    return pd.read_csv(DATA / f'{name}.csv')


def test_saved_selection_reproduces_from_saved_rookie_games():
    ranked = post.select_top(saved('rookie-games'))
    top = saved('top-fifteen')
    assert ranked.player_id.tolist() == top.player_id.tolist()
    assert ranked.game_id.astype(int).tolist() == top.game_id.astype(int).tolist()
    assert (ranked.iloc[0].player, ranked.iloc[0].pool) == ('Derrick Rose', 'Playoffs')
    assert ranked.iloc[0].game_score == pytest.approx(30.4)
    assert ranked.iloc[0].context_note == '(RD 1 GM1)'
    assert ranked.pool.eq('Playoffs').sum() == 1
    assert ranked['rank'].tolist() == list(range(1, 16))
    assert ranked.player.value_counts().max() == 2


def test_exact_ties_fall_to_points_and_cutoff_is_clean():
    ranked = post.select_top(saved('rookie-games'))
    # Mirotic (27 pts) and Rose (23) both score 25.2; Coby White (33) and Buzelis (28) both 24.9.
    for score, expected in ((25.2, ['Nikola Mirotic', 'Derrick Rose']),
                            (24.9, ['Coby White', 'Matas Buzelis'])):
        assert ranked.loc[ranked.game_score.eq(score), 'player'].tolist() == expected
    scores = saved('rookie-games').game_score.round(1).nlargest(16).tolist()
    assert scores[14] == pytest.approx(24.7) and scores[15] == pytest.approx(24.6)


def test_float_noise_does_not_override_the_points_tiebreak():
    rows = saved('rookie-games').head(16).copy()
    rows['game_score'] = [30.0 - i for i in range(16)]
    rows.loc[rows.index[0], ['game_score', 'points']] = [25.2 - 1e-12, 30]
    rows.loc[rows.index[1], ['game_score', 'points']] = [25.2, 10]
    ranked = post.select_top(rows)
    tied = ranked.loc[ranked.game_score.eq(25.2)]
    assert tied.points.tolist() == [30, 10]


def test_tie_across_the_cutoff_is_rejected():
    rows = saved('rookie-games').head(16).copy()
    rows['game_score'] = [30.0 - i for i in range(14)] + [10.0, 10.0]
    with pytest.raises(ValueError, match='cutoff'):
        post.select_top(rows)


def test_rookie_filter_agrees_with_first_season_except_holcomb():
    audit = saved('rookie-audit')
    assert audit.games.eq(audit.bulls_game_rows).all()
    disagreements = audit.loc[~audit.first_season_agrees, ['season', 'player_id']]
    assert set(map(tuple, disagreements.values)) == post.KNOWN_FIRST_SEASON_DISAGREEMENTS


def test_tight_portrait_is_framed_on_a_cdn_shaped_canvas():
    with Image.open(post.PORTRAITS / '2398.png') as source:
        framed = post.frame_like_cdn_headshot(source)
    assert framed.size == (1040, 760)
    alpha = framed.getchannel('A')
    assert alpha.getpixel((0, 0)) == 0 and alpha.getpixel((520, 380)) > 0


def test_playoff_context_reads_round_and_game_from_the_nba_game_id():
    assert post.playoff_context('0040800101') == '(RD 1 GM1)'
    assert post.playoff_context(41000203) == '(RD 2 GM3)'


def test_playoff_seasons_are_exactly_the_bulls_postseason_runs():
    games = saved('rookie-games')
    assert set(games.loc[games.pool.eq('Playoffs'), 'season_end_year']) <= post.PLAYOFF_SEASONS


def test_both_formats_render_without_free_throws(tmp_path, monkeypatch):
    ranked = post.select_top(saved('rookie-games'))
    monkeypatch.setattr(post.games, 'OUT', tmp_path)
    monkeypatch.setattr(post.games, 'ensure_headshots', lambda _: None)
    table = post.games.render_chart(
        ranked, '2026-09-18', decade=post.LABEL, show_free_throws=False, show_turnovers=True,
        top_n=15, layout=post.TABLE_LAYOUT, emphasize_points=True)
    assert table.exists()
    assert post.render_boxed(ranked, final=False).exists()


def test_columns_without_free_throws_share_one_visible_gap():
    import matplotlib.pyplot as plt
    ranked = post.select_top(saved('rookie-games'))
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, post.games.CHART_WIDTH)
    cells = [('PTS', 'FG', '3PT', 'REB', 'AST', 'STL', 'BLK', 'TOV', '+/-')] + [
        post.games._turnover_values(row, False) for _, row in ranked.iterrows()]
    bounds = post.games.equal_gap_bounds(ax, cells, left=660, right=1465, header_size=20, value_size=20)
    plt.close(fig)
    assert len(bounds) == 9 and bounds[0][0] == 660 and bounds[-1][1] == pytest.approx(1465)
    assert all(a[1] == pytest.approx(b[0]) for a, b in zip(bounds, bounds[1:]))
    widths = [right - left for left, right in bounds]
    assert widths[1] > widths[0]  # FG's made-attempted cells take more room than PTS


def test_overtime_games_in_the_top_fifteen_are_recorded():
    top = saved('top-fifteen').set_index('rank')
    assert top.overtime_periods.gt(0).sum() == 4
    assert top.loc[1, 'overtime_periods'] == 1 and top.loc[6, 'overtime_periods'] == 2
