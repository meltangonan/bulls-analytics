"""Tests for the Sticky Stats analysis, Canva copy, and chart export."""

import argparse
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from PIL import Image
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prototypes" / "summer_league_sticky_stats.py"
SPEC = importlib.util.spec_from_file_location("summer_league_sticky_stats", SCRIPT)
sticky = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sticky
SPEC.loader.exec_module(sticky)


def chart_profiles() -> pd.DataFrame:
    rows = [
        (1, "Caleb Wilson", True, 45.6, 23.5),
        (2, "Dailyn Swain", True, 22.6, 41.9),
        (3, "Jaylin Sellers", True, 62.3, 34.4),
        (4, "Donovan Atwell", True, 91.7, 2.8),
        (5, "Pool Player", True, 40.0, 30.0),
        (6, "Incomplete Player", True, 50.0, np.nan),
        (7, "Unqualified Player", False, 10.0, 90.0),
    ]
    return pd.DataFrame(
        [
            {
                "player_id": player_id,
                "name": name,
                "qualified": qualified,
                "three_pt_attempt_rate": three_rate,
                "rim_rate": rim_rate,
                "games": 4,
                "minutes": 80.0,
                "rim_fga": 10,
                "rim_percentile": 50.0,
                "box_3pa": 12,
                "three_pt_percentile": 50.0,
            }
            for player_id, name, qualified, three_rate, rim_rate in rows
        ]
    )


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
    boxes = pd.DataFrame(
        [
            {
                "personId": 5,
                "firstName": "Echo",
                "familyName": "Five",
                "teamTricode": "EEE",
                "minutes": "60:00",
                "fieldGoalsAttempted": 2,
            }
        ]
    )
    shots = pd.DataFrame(
        [
            {
                "PLAYER_ID": 5,
                "SHOT_ATTEMPTED_FLAG": 1,
                "SHOT_ZONE_BASIC": "Restricted Area",
                "ACTION_TYPE": "Dunk Shot",
            }
        ]
    )

    player = sticky.prepare_shot_profiles(boxes, shots).iloc[0]

    assert player["fga_gap"] == 1
    assert player["shot_complete"] == False
    assert pd.isna(player["dunk_rate"])


def test_is_dunk_accepts_nba_dunk_variants_only():
    assert sticky.is_dunk("Reverse Dunk Shot")
    assert sticky.is_dunk("Alley Oop Dunk Shot")
    assert not sticky.is_dunk("Driving Layup Shot")


def test_prepare_chart_content_uses_only_rankable_players_for_counts_and_medians():
    content = sticky.prepare_chart_content(chart_profiles())

    assert content.qualified_count == 6
    assert content.reconciled_count == 5
    assert content.median_three_pt_rate == pytest.approx(45.6)
    assert content.median_rim_rate == pytest.approx(30.0)
    assert content.featured["name"].tolist() == list(sticky.FEATURED_PLAYERS)


def test_prepare_chart_content_omits_missing_or_unqualified_featured_players():
    profiles = chart_profiles()
    profiles = profiles[~profiles["name"].isin(["Jaylin Sellers", "Donovan Atwell"])]
    profiles.loc[profiles["name"].eq("Dailyn Swain"), "qualified"] = False

    content = sticky.prepare_chart_content(profiles)

    assert content.featured["name"].tolist() == ["Caleb Wilson"]
    assert content.missing_featured == ("Dailyn Swain", "Jaylin Sellers", "Donovan Atwell")


def test_format_canva_copy_is_authoritative_and_delimited():
    content = sticky.prepare_chart_content(chart_profiles())

    assert sticky.format_canva_copy(content) == "\n".join(
        [
            "=== CANVA COPY (DATA-BOUND) ===",
            "SUBTITLE: SL 2026 | MIN. 50 SL MINUTES | 5 PLAYERS",
            "QUALIFICATION: Min. 50 SL minutes · 5 of 6 qualified players have fully reconciled shot detail",
            "INTERPRETATION: Each axis is a separate Summer League-to-rookie signal; this scatter is not a regression between the axes.",
            "SOURCE: Data via nba.com · R²: Phillips, The F5 · Lee, The Hardwood Collective",
            "=== END CANVA COPY ===",
        ]
    )


def test_chart_export_has_expected_dimensions_and_transparency(tmp_path, monkeypatch):
    content = sticky.prepare_chart_content(chart_profiles())
    monkeypatch.setattr(sticky, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(sticky, "_headshot_path", lambda player_id, name=None: None)

    output = sticky.render_chart_only(content)
    assert output.name == "2026-07-21-sl-sticky-stats-chart.png"
    with Image.open(output) as image:
        assert image.size == (1080, 1030)
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0

    sticky.render_chart_only(content, final=True)
    with Image.open(output) as image:
        assert image.size == (2160, 2060)
        assert image.getpixel((0, 0))[3] == 0


def test_main_renders_only_the_chart_and_prints_canva_copy(monkeypatch, capsys):
    profiles = chart_profiles()
    boxes = pd.DataFrame([{"fieldGoalsAttempted": 10}])
    shots = pd.DataFrame([{"SHOT_ATTEMPTED_FLAG": 1} for _ in range(10)])
    calls = []

    monkeypatch.setattr(
        sticky,
        "parse_args",
        lambda: argparse.Namespace(refresh=False, final=False, fetch_only=False),
    )
    monkeypatch.setattr(sticky, "fetch_league_data", lambda refresh=False: (boxes, shots))
    monkeypatch.setattr(sticky, "prepare_shot_profiles", lambda box_scores, shot_rows: profiles)

    def fake_render(content, final=False):
        calls.append((content, final))
        return Path("/tmp/sticky-chart.png")

    monkeypatch.setattr(sticky, "render_chart_only", fake_render)
    monkeypatch.setattr(sticky, "format_canva_copy", lambda content: "CANVA COPY SENTINEL")

    sticky.main()

    assert len(calls) == 1
    assert calls[0][1] is False
    output = capsys.readouterr().out
    assert "CANVA COPY SENTINEL" in output
    assert output.rstrip().endswith("/tmp/sticky-chart.png")
