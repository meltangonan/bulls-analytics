"""Post-specific tests for the current-roster DARKO landscape workflow."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from scripts.prototypes.current_roster_darko_landscape import (
    build_working_table,
    order_available_for_portrait_layers,
    parse_darko_roster,
    parse_nba_roster,
    validate_working_table,
)


def test_lower_ddpm_portraits_are_drawn_last():
    table = pd.DataFrame(
        [
            {
                "official_roster_name": "Leonard Miller",
                "d_dpm": -0.8,
                "data_available": True,
            },
            {
                "official_roster_name": "Matas Buzelis",
                "d_dpm": -0.7,
                "data_available": True,
            },
            {
                "official_roster_name": "Missing Rookie",
                "d_dpm": None,
                "data_available": False,
            },
        ]
    )

    ordered = order_available_for_portrait_layers(table)

    assert ordered["official_roster_name"].tolist() == [
        "Matas Buzelis",
        "Leonard Miller",
    ]


def test_parses_official_nba_roster_payload():
    html = (
        '<script>{"roster":['
        '{"PLAYER_ID":1630188,"PLAYER":"Jalen Smith"},'
        '{"PLAYER_ID":1643591,"PLAYER":"Tobe Awaka"}'
        '],"next":"value"}</script>'
    )

    roster = parse_nba_roster(html)

    assert roster.to_dict("records") == [
        {"nba_id": 1630188, "official_roster_name": "Jalen Smith"},
        {"nba_id": 1643591, "official_roster_name": "Tobe Awaka"},
    ]


def test_extracts_only_requested_full_precision_darko_rows():
    html = (
        '{nba_id:1630188,player_name:"Jalen Smith",'
        'team_name:"Chicago Bulls",tm_id:1610612741,position:"F-C",'
        'season:2026,career_game_num:522,dpm:1.17962,o_dpm:.434329,'
        'd_dpm:.745292,box_dpm:.26676},'
        '{nba_id:9999999,player_name:"Not A Bull",'
        'team_name:"Other",tm_id:1,position:"G",season:2026,'
        'career_game_num:1,dpm:-.5,o_dpm:-.2,d_dpm:-.3,box_dpm:0}'
    )

    darko = parse_darko_roster(html, {1630188})

    assert darko.to_dict("records") == [
        {
            "nba_id": 1630188,
            "darko_name": "Jalen Smith",
            "darko_team_field": "Chicago Bulls",
            "darko_team_id": 1610612741,
            "darko_position": "F-C",
            "darko_season": 2026,
            "darko_career_game_num": 522,
            "dpm": 1.17962,
            "o_dpm": 0.434329,
            "d_dpm": 0.745292,
        }
    ]


def test_join_preserves_unavailable_rookie_as_missing():
    roster = parse_nba_roster(
        '<script>{"roster":['
        '{"PLAYER_ID":1630188,"PLAYER":"Jalen Smith"},'
        '{"PLAYER_ID":1643591,"PLAYER":"Tobe Awaka"}'
        "]}</script>"
    )
    darko = parse_darko_roster(
        '{nba_id:1630188,player_name:"Jalen Smith",'
        'team_name:"Chicago Bulls",tm_id:1610612741,position:"F-C",'
        'season:2026,career_game_num:522,dpm:1.17962,o_dpm:.434329,'
        "d_dpm:.745292,box_dpm:.26676}",
        {1630188, 1643591},
    )
    snapshot = datetime(2026, 7, 23, 12, tzinfo=ZoneInfo("America/Chicago"))

    table = build_working_table(roster, darko, snapshot)
    report = validate_working_table(table)
    rookie = table.loc[table["official_roster_name"] == "Tobe Awaka"].iloc[0]

    assert not rookie["data_available"]
    assert rookie[["o_dpm", "d_dpm", "dpm"]].isna().all()
    assert report["available_count"] == 1
    assert report["missing_names"] == ["Tobe Awaka"]
    assert report["max_component_residual"] < 0.00002
