"""Tests for the Bulls opponent win-percentage carousel analysis."""

import pandas as pd

from scripts.prototypes import bulls_opponent_win_percentage as post


def _games() -> pd.DataFrame:
    rows = []
    for opponent in post.FRANCHISE_NAMES:
        source = {"BKN": "NJN", "NOP": "NOH", "OKC": "SEA", "MEM": "VAN", "CHA": "CHH"}.get(opponent, opponent)
        for game in range(40):
            rows.append({
                "game_id": f"{opponent}-{game}", "matchup": f"CHI vs. {source}",
                "result": "W" if game < 20 else "L", "season_end_year": 2026,
            })
    return pd.DataFrame(rows)


def test_summary_maps_historical_codes_and_reconciles_wins_and_meetings():
    games = _games()
    summary = post.build_summary(games)
    audit = post.validate_summary(summary, games)
    assert len(summary) == 29
    assert set(summary.franchise) == set(post.FRANCHISE_NAMES)
    assert summary.loc[summary.franchise.eq("CHA"), "conference"].iloc[0] == "East"
    assert summary.loc[summary.franchise.eq("LAC"), "conference"].iloc[0] == "West"
    assert int(summary.meetings.sum()) == len(games)
    assert int(summary.wins.sum()) == 29 * 20
    assert audit["min_meetings"] == 40


def test_ranking_is_descending_and_ties_have_a_deterministic_secondary_order():
    games = _games()
    summary = post.build_summary(games)
    assert summary.win_pct.is_monotonic_decreasing
    assert summary["rank"].tolist() == list(range(1, 30))
    assert summary["team"].tolist() == sorted(summary["team"].tolist())


def test_slide_layout_uses_a_fixed_shared_scale_with_minnesota_on_slide_two():
    assert post.SLIDES == ((1, 14), (15, 29))
    assert post.SCALE_MIN == 25
    assert post.SCALE_MAX == 65
    assert post.CHART_HEIGHT == 1600
    assert post.CHART_WIDTH * 2 == 3600
    assert post.CHART_WIDTH > post.CHART_HEIGHT


def test_canva_copy_matches_the_logo_callout_chart_grammar():
    summary = post.build_summary(_games())
    copy = post.copy_block(summary, post.validate_summary(summary, _games()))
    assert "Blue = Eastern Conference opponent" in copy
    assert "red = Western Conference opponent" in copy
    assert "Team abbreviation" not in copy
