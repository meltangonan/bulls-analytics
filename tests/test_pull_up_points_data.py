"""Metric and source-coverage checks for the pull-up leaderboard."""
import json

import pandas as pd
import pytest

from scripts.prototypes import pull_up_points_data as post


def snapshot(kind, season):
    raw = json.loads((post.DATA / 'raw' / f'{kind}_{season}.json').read_text())
    result = raw['response']['resultSets'][0]
    return pd.DataFrame(result['rowSet'], columns=result['headers'])


def test_league_baseline_weights_attempts_and_rejects_missing():
    frame = pd.DataFrame({'PULL_UP_PTS': [3, 8], 'PULL_UP_FGA': [1, 9]})
    assert post.weighted_efg(frame) == 55  # Not the mean of 150% and 44.44%.
    frame.loc[0, 'PULL_UP_PTS'] = float('nan')
    with pytest.raises(ValueError, match='Missing'):
        post.weighted_efg(frame)


def test_all_saved_seasons_and_selected_values_reproduce():
    rows = []
    for season in post.SEASONS:
        data, _ = post.summarize(snapshot('bulls', season), snapshot('official', season),
                                snapshot('league', season), season, snapshot('league_players', season))
        rows.append(data)
    ranked = pd.concat(rows).sort_values('pts', ascending=False).head(10).reset_index(drop=True)
    saved = pd.read_csv(post.DATA / 'top10.csv')
    assert len(rows) == 13
    assert ranked.pts.tolist() == [923, 712, 596, 558, 541, 512, 440, 419, 401, 362]
    for column in ['player_id', 'season', 'pts', 'fgm', 'gp']:
        assert ranked[column].tolist() == saved[column].tolist()
    for column in ['efg_pct', 'relative_efg_pp', 'pts_per_game']:
        assert ranked[column].tolist() == pytest.approx(saved[column].tolist())
    assert ranked.iloc[0].efg_pct == pytest.approx(50 * 923 / 929)
    assert ranked.iloc[0].pts_per_game == pytest.approx(923 / 76)


def test_chicago_games_are_required_even_when_tracking_row_names_later_team():
    season = '2024-25'
    official = snapshot('official', season)
    official.loc[official.PLAYER_ID == 203897, 'GP'] = 63  # Replace Chicago stint with another scope.
    with pytest.raises(ValueError, match='GP differs'):
        post.summarize(snapshot('bulls', season), official, snapshot('league', season),
                       season, snapshot('league_players', season))


def test_provider_discrepancy_is_reported_without_rewriting_counts():
    season = '2016-17'
    players = snapshot('bulls', season)
    result, audit = post.summarize(players, snapshot('official', season),
        snapshot('league', season), season, snapshot('league_players', season))
    assert audit['PULL_UP_FGA_difference'] == 36
    assert result.fga.sum() == players.PULL_UP_FGA.sum()
    butler = result.loc[result.player_id == 202710].iloc[0]
    assert butler.pts == 440
    assert butler.efg_pct == pytest.approx(50 * 440 / 560)
