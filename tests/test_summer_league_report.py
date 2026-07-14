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


def test_shot_diet_covers_the_whole_team_when_no_player_is_given():
    chart = shots((7, "Restricted Area"), (8, "Above the Break 3"), (9, "Mid-Range"))

    assert report.shot_diet(chart, None) == {"rim": 1, "paint": 0, "mid": 1, "three": 1}
    assert report.shot_diet_line(chart, None) == "1 RIM/PAINT · 1 MID · 1 3PT"


def test_minutes_played_reads_both_nba_clock_formats():
    assert report.minutes_played(pd.Series({"minutes": "22:34"})) == 22
    assert report.minutes_played(pd.Series({"minutes": "PT22M34.00S"})) == 22
    assert report.minutes_played(pd.Series({"minutes": ""})) == 0
    assert report.minutes_played(pd.Series({"minutes": None})) == 0


def test_zone_splits_count_makes_and_attempts_per_zone_group():
    chart = pd.DataFrame(
        [
            (7, "Restricted Area", True),
            (7, "In The Paint (Non-RA)", False),
            (7, "Mid-Range", True),
            (7, "Left Corner 3", False),
            (8, "Above the Break 3", True),
        ],
        columns=["player_id", "shot_zone", "shot_made"],
    )

    assert report.zone_splits(chart, 7) == {"rim_paint": (1, 2), "mid": (1, 1), "three": (0, 1)}
    assert report.zone_splits(chart, None)["three"] == (1, 2)


def test_one_ft_rule_gate_matches_summer_league_seasons():
    assert report.one_ft_rule_applies("1522600012")  # 2026 SL: rule active
    assert not report.one_ft_rule_applies("1522500033")  # 2025 SL rehearsal: normal rules
    assert not report.one_ft_rule_applies("0022600123")  # regular NBA game


def _team_row():
    return pd.Series(
        {
            "teamTricode": "CHI",
            "points": 96,
            "reboundsTotal": 29,
            "assists": 14,
            "steals": 8,
            "blocks": 11,
            "turnovers": 13,
            "fieldGoalsMade": 30,
            "fieldGoalsAttempted": 69,
            "threePointersMade": 14,
            "threePointersAttempted": 32,
            "freeThrowsMade": 13,
            "freeThrowsAttempted": 25,
        }
    )


def _opponent_row():
    return pd.Series(
        {
            "teamTricode": "MEM",
            "points": 97,
            "reboundsTotal": 35,
            "assists": 18,
            "steals": 8,
            "blocks": 7,
            "turnovers": 14,
            "fieldGoalsMade": 33,
            "fieldGoalsAttempted": 70,
            "threePointersMade": 5,
            "threePointersAttempted": 35,
            "freeThrowsMade": 17,
            "freeThrowsAttempted": 22,
        }
    )


def _player_row():
    return pd.Series(
        {
            "personId": 7,
            "firstName": "Caleb",
            "familyName": "Wilson",
            "minutes": "32:15",
            "points": 35,
            "reboundsTotal": 5,
            "assists": 0,
            "turnovers": 6,
            "steals": 2,
            "blocks": 3,
            "fieldGoalsMade": 12,
            "fieldGoalsAttempted": 21,
            "threePointersMade": 7,
            "threePointersAttempted": 11,
            "freeThrowsMade": 2,
            "freeThrowsAttempted": 6,
            "usagePercentage": 0.371,
            "trueShootingPercentage": 0.740,
            "netRating": -13.6,
            "plusMinusPoints": -11,
        }
    )


def _located_shots():
    return pd.DataFrame(
        [
            (7, "Restricted Area", True, 0, 10),
            (7, "Above the Break 3", False, 20, 240),
            (8, "Mid-Range", True, -80, 120),
            (8, "Left Corner 3", False, -220, 40),
        ],
        columns=["player_id", "shot_zone", "shot_made", "loc_x", "loc_y"],
    )


def test_prepare_team_slide_removes_raw_api_fields_from_renderer_input(monkeypatch):
    monkeypatch.setattr(report, "_headshot_path", lambda player: None)

    data = report.prepare_team_slide(
        _team_row(),
        _opponent_row(),
        [_player_row()],
        _located_shots(),
        "JUL 10, 2026",
        None,
    )

    assert [text for text, _ in data.header.title_segments] == ["CHI", " VS ", "MEM"]
    assert data.header.subtitle_parts[0][0] == "Bulls 96"
    assert [item.label for item in data.comparison_stats] == ["REB", "AST", "STL", "BLK", "TO", "FG%", "3P%", "FT%"]
    assert data.comparison_stats[0].bulls_display == "29"
    assert data.comparison_stats[0].opponent_display == "35"
    assert data.comparison_stats[6].bulls_display == "43.8"
    assert next(zone for zone in data.zones if zone.key == "restricted").share == 25.0
    assert next(zone for zone in data.zones if zone.key == "above_break").attempts == 1
    assert data.shooting_splits == ("FG  30-69  (43.5%)", "3PT  14-32  (43.8%)", "FT  13-25  (52.0%)")
    assert data.players[0].player == "Caleb Wilson"
    assert data.players[0].true_shooting == 74.0


def test_prepare_player_slide_contains_display_ready_story_content(monkeypatch):
    monkeypatch.setattr(report, "_headshot_path", lambda player: None)

    data = report.prepare_player_slide(
        _player_row(),
        _team_row(),
        _opponent_row(),
        _located_shots(),
        "JUL 10, 2026",
        None,
    )

    assert data.display_name == "CALEB WILSON"
    assert data.attempts_label == "SHOT CHART"
    assert [item.label for item in data.identity_stats] == ["PTS", "MIN", "REB", "AST", "STL", "BLK"]
    assert [(item.value, item.label) for item in data.zone_stats] == [
        ("1-1", "RIM / PAINT"),
        ("0-0", "MID-RANGE"),
        ("0-1", "THREES"),
    ]
    assert [item.label for item in data.profile_stats] == [
        "FIELD GOALS",
        "THREES",
        "FREE THROWS",
        "TRUE SHOOTING",
        "OF BULLS FGA",
        "PLUS/MINUS",
    ]
    true_shooting = next(item for item in data.profile_stats if item.label == "TRUE SHOOTING")
    assert true_shooting.value == "74.0%"
    assert not true_shooting.highlight
    assert not any(item.highlight for item in data.profile_stats)
