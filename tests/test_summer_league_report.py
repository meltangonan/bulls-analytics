"""Tests for the pure story-metric helpers in the Summer League prototype."""
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd
import pytest


REPORT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "prototypes" / "summer_league_report.py"
SPEC = spec_from_file_location("summer_league_report", REPORT_PATH)
report = module_from_spec(SPEC)
SPEC.loader.exec_module(report)


def shots(*rows):
    """Build the two get_game_shots columns that shot_diet reads."""
    return pd.DataFrame(list(rows), columns=["player_id", "shot_zone"])


def test_shot_diet_groups_nba_shot_zones_into_readable_buckets():
    chart = shots(
        (7, "Restricted Area"),
        (7, "In The Paint (Non-RA)"),
        (7, "Mid-Range"),
        (7, "Above the Break 3"),
        (8, "Above the Break 3"),
    )

    assert report.shot_diet(chart, 7) == {"rim": 1, "paint": 1, "mid": 1, "three": 1}
    assert report.shot_diet_line(chart, 7) == "2 RIM/PAINT · 1 MID · 1 3PT"


def test_shot_diet_keeps_the_nba_mid_range_zone_out_of_the_paint():
    """A 14-ft baseline fadeaway is Mid-Range to the NBA even though it is close."""
    chart = shots((7, "Mid-Range"), (7, "Mid-Range"), (7, "Restricted Area"))

    assert report.shot_diet_line(chart, 7) == "1 RIM/PAINT · 2 MID · 0 3PT"


def test_every_three_point_zone_counts_as_a_three():
    chart = shots(
        (7, "Left Corner 3"),
        (7, "Right Corner 3"),
        (7, "Above the Break 3"),
        (7, "Backcourt"),
    )

    assert report.shot_diet(chart, 7) == {"rim": 0, "paint": 0, "mid": 0, "three": 4}


def test_shot_diet_line_reports_a_player_who_never_shot():
    assert report.shot_diet_line(shots((8, "Mid-Range")), 7) == "NO FIELD-GOAL ATTEMPTS"


def test_league_is_derived_from_the_game_id_prefix():
    from bulls.data import league_for_game

    assert league_for_game("1522500033") == "15"  # Summer League
    assert league_for_game("0022500123") == "00"  # regular NBA


def test_team_nickname_strips_the_city_including_two_word_nicknames():
    assert report.team_nickname("MEM") == "Grizzlies"
    assert report.team_nickname("IND") == "Pacers"
    assert report.team_nickname("ATL") == "Hawks"
    assert report.team_nickname("OKC") == "Thunder"
    assert report.team_nickname("POR") == "Trail Blazers"


def test_game_day_uses_the_game_date_not_the_render_date():
    assert report.game_day({"gameEt": "2026-07-10T20:00:00Z"}) == date(2026, 7, 10)


def test_game_day_prefers_eastern_time_over_utc():
    """A late tip rolls over midnight UTC while still belonging to the prior game day."""
    summary = {"gameEt": "2026-07-10T22:00:00Z", "gameTimeUTC": "2026-07-11T02:00:00Z"}

    assert report.game_day(summary) == date(2026, 7, 10)


def test_require_final_rejects_a_game_in_progress():
    with pytest.raises(SystemExit, match="not final"):
        report.require_final({"gameStatus": 2, "gameStatusText": "Q3 4:21"}, "1522600001")


def test_require_final_accepts_a_completed_game():
    assert report.require_final({"gameStatus": 3, "gameStatusText": "Final"}, "1522600001") is None




def test_role_and_impact_lenses_use_box_score_values_without_true_shooting():
    player = pd.Series(
        {
            "personId": 7,
            "fieldGoalsMade": 6,
            "fieldGoalsAttempted": 12,
            "threePointersMade": 2,
            "plusMinusPoints": -4,
        }
    )
    team = pd.Series({"fieldGoalsAttempted": 60})

    assert report.role_share_pct(player, team) == 20.0
    assert report.efg_pct(player) == 58.333333333333336
    assert report.lens_copy("role", player, team, shots()) == ("THE ROLE", "20% OF BULLS FGA")
    assert report.lens_copy("impact", player, team, shots()) == ("THE IMPACT", "BULLS -4 IN HIS MINUTES")
