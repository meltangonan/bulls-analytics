"""Metric, selection and source-coverage checks for the contested-jumper leaderboard."""
import json

import pandas as pd
import pytest

from scripts.prototypes import contested_jumpers_data as post


def snapshot(name):
    raw = json.loads((post.DATA / 'raw' / f'{name}.json').read_text())
    return raw['response']


def players(scope, season):
    out = {}
    for bucket in post.BUCKETS:
        result = snapshot(f'{scope}_{season}_{bucket}')['resultSets'][0]
        out[bucket] = pd.DataFrame(result['rowSet'], columns=result['headers'])
    return out


def season_rows(season):
    return post.summarize(players('bulls', season), players('league', season),
                          post.fetch_team(season), season)


def test_saved_snapshots_reproduce_the_published_fifteen():
    rows = pd.concat([season_rows(season)[0] for season in post.SEASONS], ignore_index=True)
    top = post.select(rows)
    saved = pd.read_csv(post.DATA / 'top15.csv')
    assert len(top) == 15
    assert top.c_fgm.tolist() == [311, 256, 203, 133, 120, 107, 68, 65, 65, 63, 58, 57, 57, 56, 54]
    for column in ['player_id', 'season', 'c_fgm', 'c_fga', 'u_fgm', 'u_fga', 'nba_rank']:
        assert top[column].tolist() == saved[column].tolist()
    for column in ['c_fg_pct', 'u_fg_pct', 'c_vs_league_pp']:
        assert top[column].tolist() == pytest.approx(saved[column].tolist())
    assert not top.partial_season.any()


def test_derozan_worked_row():
    rows, audit = season_rows('2021-22')
    row = rows.loc[rows.player_id == 201942].iloc[0]
    # Very Tight 5/14 plus Tight 306/622; Open 190/408 plus Wide Open 34/79.
    assert (row.c_fgm, row.c_fga, row.u_fgm, row.u_fga) == (311, 636, 224, 487)
    assert row.c_fg_pct == pytest.approx(100 * 311 / 636)
    assert row.u_fg_pct == pytest.approx(100 * 224 / 487)
    assert audit['league_c_fg_pct'] == pytest.approx(100 * 9143 / 26090)
    assert row.nba_rank == 1


def test_tie_on_makes_goes_to_higher_contested_percentage():
    top = pd.read_csv(post.DATA / 'top15.csv')
    tied = top[top.c_fgm == 65]
    assert tied.player_name.tolist() == ['Jimmy Butler', 'Carlos Boozer']
    assert tied.c_fg_pct.is_monotonic_decreasing
    assert top.iloc[-1].c_fgm > pd.read_csv(post.DATA / 'all_player_seasons.csv').c_fgm.nlargest(16).iloc[-1]


def test_team_reconciliation_is_recorded_and_small():
    audit = pd.read_csv(post.DATA / 'season_audit.csv')
    assert audit.season.tolist() == post.SEASONS
    differences = audit.filter(like='_difference')
    assert differences.abs().max().max() <= 2
    assert audit.loc[audit.season == '2025-26', differences.columns].eq(0).all(axis=None)


def test_large_team_mismatch_stops_the_build():
    season = '2025-26'
    bulls = players('bulls', season)
    bulls['tight'].loc[bulls['tight'].index[0], 'FGA'] += 40
    with pytest.raises(ValueError, match='team total'):
        post.summarize(bulls, players('league', season), post.fetch_team(season), season)


def test_player_missing_from_a_bucket_counts_as_zero_attempts():
    frame = lambda ids, fgm, fga: pd.DataFrame(
        {'PLAYER_ID': ids, 'PLAYER_NAME': [str(i) for i in ids], 'FGM': fgm, 'FGA': fga})
    buckets = {'very_tight': frame([1], [1], [2]), 'tight': frame([1, 2], [3, 1], [6, 4]),
               'open': frame([2], [2], [5]), 'wide_open': frame([1, 2], [1, 0], [1, 1])}
    out = post.split(buckets).set_index('PLAYER_ID')
    assert out.loc[1, ['c_fgm', 'c_fga', 'u_fgm', 'u_fga']].tolist() == [4, 8, 1, 1]
    assert out.loc[2, ['c_fgm', 'c_fga', 'u_fgm', 'u_fga']].tolist() == [1, 4, 2, 6]
