"""Tests for the pure calculations in the sticky-stats prototype."""

import importlib.util
from pathlib import Path
import sys

import pandas as pd
from PIL import Image
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prototypes" / "summer_league_sticky_stats.py"
SPEC = importlib.util.spec_from_file_location("summer_league_sticky_stats", SCRIPT)
sticky = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sticky
SPEC.loader.exec_module(sticky)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("22:30", 22.5), ("PT22M30.00S", 22.5), ("129:53", 29 + 53 / 60), ("15", 15.0), (None, 0.0)],
)
def test_parse_minutes_handles_nba_clock_formats(raw, expected):
    assert sticky.parse_minutes(raw) == pytest.approx(expected)


def test_dunk_rate_is_share_of_all_fga_and_keeps_zero_dunk_player_ranked():
    boxes = pd.DataFrame(
        [
            {"personId": 1, "firstName": "Alpha", "familyName": "One", "teamTricode": "AAA", "minutes": "30:00", "fieldGoalsAttempted": 2},
            {"personId": 1, "firstName": "Alpha", "familyName": "One", "teamTricode": "AAA", "minutes": "30:00", "fieldGoalsAttempted": 1},
            {"personId": 2, "firstName": "Beta", "familyName": "Two", "teamTricode": "BBB", "minutes": "55:00", "fieldGoalsAttempted": 1},
            {"personId": 3, "firstName": "Gamma", "familyName": "Three", "teamTricode": "CCC", "minutes": "49:59", "fieldGoalsAttempted": 1},
            {"personId": 4, "firstName": "Delta", "familyName": "Four", "teamTricode": "DDD", "minutes": "60:00", "fieldGoalsAttempted": 1},
        ]
    )
    shots = pd.DataFrame(
        [
            {"PLAYER_ID": 1, "SHOT_ATTEMPTED_FLAG": 1, "SHOT_ZONE_BASIC": "Restricted Area", "ACTION_TYPE": "Driving Dunk Shot"},
            {"PLAYER_ID": 1, "SHOT_ATTEMPTED_FLAG": 1, "SHOT_ZONE_BASIC": "Restricted Area", "ACTION_TYPE": "Layup Shot"},
            {"PLAYER_ID": 1, "SHOT_ATTEMPTED_FLAG": 1, "SHOT_ZONE_BASIC": "Above the Break 3", "ACTION_TYPE": "Jump Shot"},
            {"PLAYER_ID": 2, "SHOT_ATTEMPTED_FLAG": 1, "SHOT_ZONE_BASIC": "Restricted Area", "ACTION_TYPE": "Cutting Dunk Shot"},
            {"PLAYER_ID": 3, "SHOT_ATTEMPTED_FLAG": 1, "SHOT_ZONE_BASIC": "Restricted Area", "ACTION_TYPE": "Dunk Shot"},
            {"PLAYER_ID": 4, "SHOT_ATTEMPTED_FLAG": 1, "SHOT_ZONE_BASIC": "Mid-Range", "ACTION_TYPE": "Jump Shot"},
        ]
    )

    profiles = sticky.prepare_shot_profiles(boxes, shots)
    alpha = profiles.set_index("player_id").loc[1]
    beta = profiles.set_index("player_id").loc[2]
    gamma = profiles.set_index("player_id").loc[3]
    delta = profiles.set_index("player_id").loc[4]

    assert alpha["dunk_rate"] == pytest.approx(100 / 3)
    assert beta["dunk_rate"] == pytest.approx(100.0)
    assert beta["dunk_rank"] == 1
    assert alpha["dunk_rank"] == 2
    assert gamma["qualified"] == False
    assert delta["qualified"] == True
    assert delta["dunk_rate"] == pytest.approx(0.0)
    assert delta["dunk_rank"] == 3


def test_caleb_definition_matches_seven_dunks_on_68_official_fga():
    boxes = pd.DataFrame(
        [
            {
                "personId": 1643410,
                "firstName": "Caleb",
                "familyName": "Wilson",
                "teamTricode": "CHI",
                "minutes": "110:39",
                "fieldGoalsAttempted": 68,
                "threePointersAttempted": 20,
            }
        ]
    )
    shots = pd.DataFrame(
        [
            {
                "PLAYER_ID": 1643410,
                "SHOT_ATTEMPTED_FLAG": 1,
                "SHOT_ZONE_BASIC": "Restricted Area" if attempt < 16 else "Above the Break 3",
                "ACTION_TYPE": "Dunk Shot" if attempt < 7 else "Jump Shot",
            }
            for attempt in range(68)
        ]
    )

    player = sticky.prepare_shot_profiles(boxes, shots).iloc[0]

    assert player["box_fga"] == 68
    assert player["rim_fga"] == 16
    assert player["dunks"] == 7
    assert player["dunk_rate"] == pytest.approx(100 * 7 / 68)
    assert player["rim_rate"] == pytest.approx(100 * 16 / 68)
    assert player["three_pt_attempt_rate"] == pytest.approx(100 * 20 / 68)


def test_incomplete_shot_detail_is_not_ranked():
    boxes = pd.DataFrame([
        {"personId": 5, "firstName": "Echo", "familyName": "Five", "teamTricode": "EEE", "minutes": "60:00", "fieldGoalsAttempted": 2}
    ])
    shots = pd.DataFrame([
        {"PLAYER_ID": 5, "SHOT_ATTEMPTED_FLAG": 1, "SHOT_ZONE_BASIC": "Restricted Area", "ACTION_TYPE": "Dunk Shot"}
    ])

    player = sticky.prepare_shot_profiles(boxes, shots).iloc[0]

    assert player["fga_gap"] == 1
    assert player["shot_complete"] == False
    assert pd.isna(player["dunk_rate"])


def test_is_dunk_accepts_nba_dunk_variants_only():
    assert sticky.is_dunk("Reverse Dunk Shot")
    assert sticky.is_dunk("Alley Oop Dunk Shot")
    assert not sticky.is_dunk("Driving Layup Shot")


def test_three_slide_carousel_renders_standard_draft_files(tmp_path, monkeypatch):
    profiles = pd.DataFrame(
        [
            {
                "player_id": player_id,
                "name": name,
                "qualified": True,
                "rim_rate": rim_rate,
                "three_pt_attempt_rate": three_rate,
            }
            for player_id, name, three_rate, rim_rate in (
                (1, "Caleb Wilson", 45.6, 23.5),
                (2, "Dailyn Swain", 22.6, 41.9),
                (3, "Noa Essengue", 37.5, 43.8),
                (4, "Jaylin Sellers", 62.3, 34.4),
                (5, "Donovan Atwell", 91.7, 2.8),
            )
        ]
    )
    monkeypatch.setattr(sticky, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(sticky, "_headshot_path", lambda player_id, name=None: None)

    outputs = (
        sticky.render_cover(profiles),
        sticky.render_definitions(),
        sticky.render_shot_profile(profiles),
    )

    assert [path.name for path in outputs] == [
        "2026-07-20-sl-shot-profile-s1-cover.png",
        "2026-07-20-sl-shot-profile-s2-research.png",
        "2026-07-20-sl-shot-profile-s3-bulls.png",
    ]
    for path in outputs:
        assert path.exists()
        with Image.open(path) as image:
            assert image.size == (1080, 1350)
