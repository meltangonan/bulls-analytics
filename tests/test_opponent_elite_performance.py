import pandas as pd
import pytest

from scripts.prototypes.opponent_elite_performance import (
    FRANCHISE_CONFERENCES,
    FRANCHISE_NAMES,
    HISTORICAL_TO_CURRENT,
    build_opponent_summary,
    build_count_summary,
    build_points_threshold_summary,
    current_opponent,
    rank_percentage_summary,
    validate_count_summary,
    validate_points_threshold_summary,
    validate_summary,
)


def _table():
    rows = []
    game_number = 0
    for code in FRANCHISE_NAMES:
        for _ in range(2):
            game_number += 1
            rows.append(
                {
                    "game_id": f"{game_number:010d}",
                    "opponent": code,
                    "game_score": 30.0 if code == "SAC" else 20.0,
                    "points": 30.0 if code == "POR" else 20.0,
                }
            )
    return pd.DataFrame(rows)


def test_historical_abbreviations_map_to_current_franchises():
    assert current_opponent("NJN") == "BKN"
    assert current_opponent("NOH") == "NOP"
    assert current_opponent("NOK") == "NOP"
    assert current_opponent("SEA") == "OKC"
    assert current_opponent("VAN") == "MEM"
    assert current_opponent("CHH") == "CHA"
    assert set(HISTORICAL_TO_CURRENT) == {"NJN", "NOH", "NOK", "SEA", "VAN", "CHH"}


def test_every_current_opponent_has_one_conference_assignment():
    assert set(FRANCHISE_CONFERENCES) == set(FRANCHISE_NAMES)
    assert set(FRANCHISE_CONFERENCES.values()) == {"East", "West"}


def test_summary_counts_player_games_and_meetings_per_current_franchise():
    table = _table()
    summary = build_opponent_summary(table, min_meetings=2)
    leader = summary.iloc[0]
    assert leader["franchise"] == "SAC"
    assert leader["elite_player_games"] == 2
    assert leader["meetings"] == 2
    assert leader["rate_per_100"] == pytest.approx(100.0)
    assert len(summary) == 29


def test_summary_merges_historical_opponent_codes_into_one_denominator():
    rows = [
        {"game_id": "1", "opponent": "NJN", "game_score": 30.0},
        {"game_id": "2", "opponent": "BKN", "game_score": 20.0},
    ]
    rows.extend(
        {"game_id": str(i), "opponent": code, "game_score": 20.0}
        for i, code in enumerate(FRANCHISE_NAMES, start=3)
        if code not in {"BKN"}
    )
    table = pd.DataFrame(rows)
    summary = build_opponent_summary(table, min_meetings=1)
    nets = summary.loc[summary["franchise"].eq("BKN")].iloc[0]
    assert nets["meetings"] == 2
    assert nets["elite_player_games"] == 1


def test_validation_reconciles_all_29_opponents_and_player_games():
    table = _table()
    summary = build_opponent_summary(table, min_meetings=2)
    audit = validate_summary(summary, table, min_meetings=2)
    assert audit["opponent_count"] == 29
    assert audit["meeting_count"] == 58
    assert audit["elite_player_game_count"] == 2
    assert audit["elite_team_game_count"] == 2


def test_minimum_meetings_rejects_thin_opponent_samples():
    with pytest.raises(ValueError, match="below the minimum"):
        build_opponent_summary(_table(), min_meetings=3)


def test_points_threshold_summary_ranks_each_threshold_and_reconciles():
    table = _table().assign(points=lambda frame: frame["game_score"])
    summary = build_points_threshold_summary(table, thresholds=(20, 30), min_meetings=2)
    counts = validate_points_threshold_summary(summary, table, thresholds=(20, 30))
    assert counts == {20: 58, 30: 2}
    assert summary.loc[summary["threshold"].eq(30), "team"].iloc[0] == "Kings"
    assert summary.groupby("threshold").size().to_dict() == {20: 29, 30: 29}


def test_count_summary_ranks_raw_points_and_game_score_counts():
    table = _table()
    points = build_count_summary(table, metric="points", min_meetings=2)
    game_score = build_count_summary(table, metric="game_score", min_meetings=2)
    assert points.iloc[0]["franchise"] == "POR"
    assert points.iloc[0]["qualifying_player_games"] == 2
    assert game_score.iloc[0]["franchise"] == "SAC"
    assert game_score.iloc[0]["qualifying_player_games"] == 2
    assert "rate_per_100" in points.columns


def test_count_summary_validation_reconciles_each_metric():
    table = _table()
    for metric, expected in (("points", 2), ("game_score", 2)):
        summary = build_count_summary(table, metric=metric, min_meetings=2)
        audit = validate_count_summary(summary, table, metric=metric)
        assert audit["opponent_count"] == 29
        assert audit["meeting_count"] == 58
        assert audit["qualifying_player_game_count"] == expected


def test_count_summary_supports_a_lower_points_threshold():
    table = _table().assign(points=lambda frame: frame["game_score"])
    summary = build_count_summary(table, metric="points", threshold=25, min_meetings=2)
    audit = validate_count_summary(summary, table, metric="points", threshold=25)
    assert summary.iloc[0]["franchise"] == "SAC"
    assert audit["qualifying_player_game_count"] == 2
    assert summary["threshold"].eq(25).all()


def test_percentage_view_ranks_by_count_over_meetings_not_raw_count():
    table = _table()
    table = pd.concat(
        [
            table,
            pd.DataFrame(
                [
                    {"game_id": "extra-1", "opponent": "SAC", "game_score": 20.0, "points": 20.0},
                    {"game_id": "extra-2", "opponent": "SAC", "game_score": 20.0, "points": 20.0},
                ]
            ),
        ],
        ignore_index=True,
    )
    summary = build_count_summary(table, metric="points", threshold=25, min_meetings=2)
    ranked = rank_percentage_summary(summary)
    assert ranked.iloc[0]["franchise"] == "POR"
    assert ranked.iloc[0]["qualifying_player_games"] == 2
    assert ranked.iloc[0]["meetings"] == 2
    assert ranked.iloc[0]["percentage_rank"] == 1


def test_count_summary_rejects_unknown_metric():
    with pytest.raises(ValueError, match="Unknown count metric"):
        build_count_summary(_table(), metric="rebounds", min_meetings=2)
