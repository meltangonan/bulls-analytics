"""Check the shot boundary and the saved leaderboard's source accounting."""

from pathlib import Path

import pandas as pd

from scripts.prototypes.deep_threes_career_data import PLAYOFF_SEASONS, eligible


DATA = Path(__file__).resolve().parents[1] / "docs/visuals/2026-09-25-deep-threes-career/data"


def test_eligibility_includes_27_and_39_but_excludes_halfcourt_and_heaves():
    shots = pd.DataFrame({
        "SHOT_TYPE": ["3PT Field Goal"] * 6,
        "SHOT_DISTANCE": [26, 27, 39, 40, 27, 27],
        "LOC_Y": [200, 200, 417, 200, 418, 200],
        "SHOT_MADE_FLAG": [1] * 6,
    })
    assert eligible(shots).index.tolist() == [1, 2, 5]


def test_saved_leaderboard_reconciles_and_uses_attempt_weighted_league_rate():
    audit = pd.read_csv(DATA / "season_audit.csv")
    assert len(audit) == 44
    assert audit.season_type.value_counts().to_dict() == {"Regular Season": 30, "Playoffs": 14}
    games = pd.read_csv(DATA / "raw/bulls-playoff-games.csv.gz")
    discovered = {
        f"{int(date[:4]) - 1}-{int(date[:4]) % 100:02d}"
        for date in games.GAME_DATE
    }
    assert len(games) == 136
    assert discovered == set(PLAYOFF_SEASONS)
    assert audit.official_3pa.eq(audit.shot_log_3pa).all()
    assert audit.official_3pm.eq(audit.shot_log_3pm).all()
    assert audit.excluded_frontcourt_40_plus_3pa.sum() == 227
    assert audit.excluded_frontcourt_40_plus_3pm.sum() == 8
    playoff_league = pd.read_csv(DATA / "league_27_39_playoffs_by_season.csv")
    assert len(playoff_league) == 14
    assert playoff_league.league_3pa.gt(0).all()
    assert playoff_league.league_3pm.le(playoff_league.league_3pa).all()

    top = pd.read_csv(DATA / "top15.csv")
    seasons = pd.read_csv(DATA / "player_seasons.csv")
    assert len(top) == 15
    assert top.iloc[0].player_name == "Zach LaVine"
    assert (top.iloc[0].deep_3pm, top.iloc[0].deep_3pa, top.iloc[0].gp) == (234, 622, 420)
    assert top.deep_3pa.ge(top.deep_3pm).all()
    assert top.all_3pa.ge(top.deep_3pa).all()
    assert top.league_three_pct.notna().all()
    for row in top.itertuples():
        played = seasons.loc[seasons.PLAYER_ID.eq(row.player_id)]
        assert played.deep_3pa.sum() == row.deep_3pa
        assert played.deep_3pm.sum() == row.deep_3pm
        assert played.all_3pa.sum() == row.all_3pa
        assert abs(100 * row.deep_3pa / row.all_3pa - row.deep_attempt_share_pct) < 1e-9
        expected_rate = 100 * played.expected_makes.sum() / row.deep_3pa
        assert abs(expected_rate - row.league_three_pct) < 1e-9
    lavine_playoffs = seasons.loc[
        seasons.PLAYER_NAME.eq("Zach LaVine") & seasons.season_type.eq("Playoffs")
    ]
    assert (lavine_playoffs.deep_3pm.sum(), lavine_playoffs.deep_3pa.sum()) == (2, 9)
