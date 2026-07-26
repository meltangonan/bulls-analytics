"""Post-specific tests for the rim-vs-three points-per-shot landscape."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from scripts.prototypes.rim_vs_three_pps_landscape import (
    HEADSHOT_HALF_SIZE,
    LABEL_SIDES,
    LEAGUE_MARKER_AREA,
    MIN_POSSESSIONS,
    MIN_ZONE_ATTEMPTS,
    PANEL,
    SHORT_NAMES,
    RIM_LIMITS,
    THREE_LIMITS,
    build_working_table,
    bulls_players,
    canva_copy_block,
    chart_x,
    chart_y,
    flatten_locations,
    qualified_players,
    validate_working_table,
)


SNAPSHOT = datetime(2026, 7, 25, 9, 0, tzinfo=ZoneInfo("America/Chicago"))


def _location_row(
    player_id: int,
    name: str,
    team: str,
    *,
    rim_fgm: int,
    rim_fga: int,
    corner_fgm: int,
    corner_fga: int,
    break_fgm: int,
    break_fga: int,
) -> dict:
    return {
        "PLAYER_ID": player_id,
        "PLAYER_NAME": name,
        "TEAM_ABBREVIATION": team,
        "Restricted Area|FGM": rim_fgm,
        "Restricted Area|FGA": rim_fga,
        "Corner 3|FGM": corner_fgm,
        "Corner 3|FGA": corner_fga,
        "Above the Break 3|FGM": break_fgm,
        "Above the Break 3|FGA": break_fga,
    }


def _locations() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # Qualified Bull: 200/400 rim, 100/300 three.
            _location_row(
                1,
                "Matas Buzelis",
                "CHI",
                rim_fgm=200,
                rim_fga=400,
                corner_fgm=40,
                corner_fga=100,
                break_fgm=60,
                break_fga=200,
            ),
            # Qualified Bull with a different profile.
            _location_row(
                2,
                "Tre Jones",
                "CHI",
                rim_fgm=180,
                rim_fga=300,
                corner_fgm=20,
                corner_fga=50,
                break_fgm=40,
                break_fga=150,
            ),
            # Qualified non-Bull, supplies league-median context.
            _location_row(
                3,
                "Nikola Jokic",
                "DEN",
                rim_fgm=150,
                rim_fga=250,
                corner_fgm=30,
                corner_fga=80,
                break_fgm=70,
                break_fga=180,
            ),
            # Bull below the three-attempt bar only.
            _location_row(
                4,
                "Nic Claxton",
                "BKN",
                rim_fgm=200,
                rim_fga=320,
                corner_fgm=4,
                corner_fga=12,
                break_fgm=10,
                break_fga=40,
            ),
            # Bull below the possession bar only.
            _location_row(
                5,
                "Noa Essengue",
                "CHI",
                rim_fgm=60,
                rim_fga=100,
                corner_fgm=30,
                corner_fga=80,
                break_fgm=30,
                break_fga=100,
            ),
        ]
    )


def _advanced() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"PLAYER_ID": 1, "POSS": 5000, "GP": 77},
            {"PLAYER_ID": 2, "POSS": 4000, "GP": 65},
            {"PLAYER_ID": 3, "POSS": 3000, "GP": 60},
            {"PLAYER_ID": 4, "POSS": 2800, "GP": 55},
            {"PLAYER_ID": 5, "POSS": 400, "GP": 12},
        ]
    )


def _roster() -> pd.DataFrame:
    """Current roster: two qualifiers, two below a bar, one with no NBA data."""
    return pd.DataFrame(
        [
            {"nba_id": 1, "official_roster_name": "Matas Buzelis"},
            {"nba_id": 2, "official_roster_name": "Tre Jones"},
            {"nba_id": 4, "official_roster_name": "Nic Claxton"},
            {"nba_id": 5, "official_roster_name": "Noa Essengue"},
            {"nba_id": 99, "official_roster_name": "Caleb Wilson"},
        ]
    )


def _table() -> pd.DataFrame:
    return build_working_table(_locations(), _advanced(), _roster(), SNAPSHOT)


def test_flatten_locations_collapses_the_shot_category_header():
    raw = pd.DataFrame(
        [[1, "A", 5, 10]],
        columns=pd.MultiIndex.from_tuples(
            [
                ("", "PLAYER_ID"),
                ("", "PLAYER_NAME"),
                ("Restricted Area", "FGM"),
                ("Restricted Area", "FGA"),
            ]
        ),
    )
    flat = flatten_locations(raw)
    assert list(flat.columns) == [
        "PLAYER_ID",
        "PLAYER_NAME",
        "Restricted Area|FGM",
        "Restricted Area|FGA",
    ]
    # Already-flat frames pass through unchanged.
    assert list(flatten_locations(flat).columns) == list(flat.columns)


def test_points_per_shot_uses_each_zone_own_point_value():
    table = _table().set_index("player_name")
    buzelis = table.loc["Matas Buzelis"]
    # 200/400 rim = 50% -> 1.00 PPS; 100/300 three = 33.3% -> 1.00 PPS.
    assert buzelis["rim_pps"] == pytest.approx(1.0)
    assert buzelis["three_pps"] == pytest.approx(1.0)
    assert buzelis["three_fga"] == 300
    assert buzelis["three_fgm"] == 100


def test_a_fifty_percent_two_and_a_thirty_four_percent_three_are_comparable():
    """The axes only mean anything if equal value lands on equal numbers."""
    table = _table().set_index("player_name")
    jokic = table.loc["Nikola Jokic"]
    # 150/250 rim = 60% -> 1.20; 100/260 three = 38.5% -> 1.154.
    assert jokic["rim_pps"] == pytest.approx(1.2)
    assert jokic["three_pps"] == pytest.approx(3 * 100 / 260)


def test_volume_is_per_seventy_five_possessions():
    table = _table().set_index("player_name")
    buzelis = table.loc["Matas Buzelis"]
    assert buzelis["zone_fga_per_75"] == pytest.approx((400 + 300) * 75 / 5000)


def test_qualification_applies_both_bars_independently():
    table = _table().set_index("player_name")
    assert table.loc["Matas Buzelis", "qualified"]
    assert table.loc["Tre Jones", "qualified"]
    assert table.loc["Nikola Jokic", "qualified"]
    # Enough possessions and rim volume, but only 52 three-point attempts.
    assert not table.loc["Nic Claxton", "qualified"]
    # Enough attempts in both zones, but only 400 possessions.
    assert not table.loc["Noa Essengue", "qualified"]


def test_bulls_flag_and_draw_order_put_bulls_last():
    table = _table()
    qualifiers = qualified_players(table)
    assert qualifiers["is_bulls"].tolist() == [False, True, True]
    assert bulls_players(table)["player_name"].tolist() == [
        "Matas Buzelis",
        "Tre Jones",
    ]


def test_validate_reports_thresholds_and_excluded_bulls():
    summary = validate_working_table(_table())
    assert summary["qualified_count"] == 3
    assert summary["bulls_qualified_count"] == 2
    assert summary["bulls_excluded_names"] == ["Nic Claxton", "Noa Essengue"]
    assert summary["roster_size"] == 5
    # Caleb Wilson never reaches the stats frames at all.
    assert summary["roster_without_2025_26_data"] == 1
    assert summary["max_rim_points_residual"] < 1e-6
    assert summary["max_three_points_residual"] < 1e-6


def test_validate_rejects_a_qualifier_outside_the_drawn_panel():
    table = _table()
    # Stay internally consistent so the earlier reconstruction check passes and
    # the panel bound is what actually rejects the row.
    jones = table["player_name"].eq("Tre Jones")
    table.loc[jones, "rim_fgm"] = 293
    table.loc[jones, "rim_pps"] = 2 * 293 / 300
    with pytest.raises(ValueError, match="outside the drawn panel"):
        validate_working_table(table)


def test_validate_rejects_a_bull_without_a_chart_label():
    table = _table()
    table.loc[
        table["official_roster_name"].eq("Tre Jones"), "official_roster_name"
    ] = "Someone New"
    with pytest.raises(ValueError, match="Missing chart labels"):
        validate_working_table(table)


def test_validate_rejects_duplicate_players():
    table = pd.concat([_table(), _table()], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate NBA player IDs"):
        validate_working_table(table)


def test_build_rejects_a_changed_nba_response():
    locations = _locations().drop(columns=["Restricted Area|FGA"])
    with pytest.raises(ValueError, match="response columns changed"):
        build_working_table(locations, _advanced(), _roster(), SNAPSHOT)


def test_axis_mapping_spans_the_panel():
    x0, y0, x1, y1 = PANEL
    assert chart_x(RIM_LIMITS[0]) == pytest.approx(x0)
    assert chart_x(RIM_LIMITS[1]) == pytest.approx(x1)
    assert chart_y(THREE_LIMITS[0]) == pytest.approx(y0)
    assert chart_y(THREE_LIMITS[1]) == pytest.approx(y1)


def test_headshots_match_the_roster_landscape_size():
    """Same square face size as the DARKO and scoring landscapes."""
    assert HEADSHOT_HALF_SIZE == 36.0
    assert LEAGUE_MARKER_AREA > 0


def test_every_label_side_names_a_real_bulls_label():
    assert set(LABEL_SIDES) <= set(SHORT_NAMES)
    assert set(LABEL_SIDES.values()) <= {"left", "right", "above", "below"}


def test_canva_copy_block_carries_the_disclosed_scope():
    table = _table()
    block = canva_copy_block(table, validate_working_table(table))
    assert f"{MIN_POSSESSIONS}+ possessions" in block
    assert f"{MIN_ZONE_ATTEMPTS}+ attempts in each zone" in block
    assert "Free throws are not in shot-location data" in block
    assert "NBA.com/stats" in block
    assert "BUZELIS" in block
    assert "BELOW THE BAR:  Nic Claxton, Noa Essengue" in block
    assert "current 5-player Bulls roster" in block
