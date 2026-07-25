"""Post-specific tests for the current-roster NBA Jam cards."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.current_roster_jam_cards import (
    CATEGORIES,
    MIN_POSSESSIONS,
    PER_POSSESSIONS,
    ZONE_POINT_VALUES,
    build_league_table,
    roster_cards,
    validate_league_table,
)


def _zones(rows: list[dict]) -> pd.DataFrame:
    """Build a shot-locations frame with the flattened two-level columns."""
    records = []
    for row in rows:
        record = {"PLAYER_ID": row["PLAYER_ID"]}
        for zone in ZONE_POINT_VALUES:
            record[f"{zone}|FGM"] = row.get(f"{zone}|FGM", 0)
            record[f"{zone}|FGA"] = row.get(f"{zone}|FGA", 0)
        records.append(record)
    return pd.DataFrame(records)


def _base(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "TEAM_ABBREVIATION": "CHI", "GP": 60, "MIN": 1800.0,
        "FTM": 0, "FTA": 0, "AST": 0,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def _frames():
    """Two qualified scorers and one player below the attempt threshold."""
    zones = _zones([
        {"PLAYER_ID": 1, "Restricted Area|FGM": 100, "Restricted Area|FGA": 150,
         "Above the Break 3|FGM": 60, "Above the Break 3|FGA": 150},
        {"PLAYER_ID": 2, "Mid-Range|FGM": 90, "Mid-Range|FGA": 200,
         "In The Paint (Non-RA)|FGM": 40, "In The Paint (Non-RA)|FGA": 100},
        {"PLAYER_ID": 3, "Restricted Area|FGM": 5, "Restricted Area|FGA": 10},
    ])
    base = _base([
        {"PLAYER_ID": 1, "PLAYER_NAME": "Josh Giddey", "FGM": 160,
         "FGA": 300, "PTS": 380, "AST": 400, "MIN": 1500.0},
        {"PLAYER_ID": 2, "PLAYER_NAME": "Nic Claxton", "FGM": 130,
         "FGA": 300, "PTS": 260, "AST": 100, "MIN": 2000.0},
        {"PLAYER_ID": 3, "PLAYER_NAME": "Caleb Wilson", "FGM": 5,
         "FGA": 10, "PTS": 10, "AST": 4, "MIN": 90.0},
    ])
    advanced = pd.DataFrame([
        {"PLAYER_ID": 1, "POSS": 3000.0},
        {"PLAYER_ID": 2, "POSS": 3000.0},
        {"PLAYER_ID": 3, "POSS": 100.0},
    ])
    return zones, base, advanced


def _roster() -> pd.DataFrame:
    return pd.DataFrame([
        {"nba_id": 1, "official_roster_name": "Josh Giddey"},
        {"nba_id": 2, "official_roster_name": "Nic Claxton"},
        {"nba_id": 3, "official_roster_name": "Caleb Wilson"},
    ])


def test_rates_are_per_75_possessions():
    table = build_league_table(*_frames()).set_index("nba_id")
    # 100 restricted-area makes = 200 points over 3000 possessions.
    expected = 200 * PER_POSSESSIONS / 3000
    assert table.loc[1, "rate_rim"] == pytest.approx(expected)
    assert table.loc[1, "rate_pass"] == pytest.approx(400 * 75 / 3000)


def test_three_point_makes_count_three_points():
    table = build_league_table(*_frames()).set_index("nba_id")
    assert table.loc[1, "three_total"] == 180
    assert table.loc[2, "mid_total"] == 180


def test_percentiles_rank_only_qualified_players():
    """The unqualified player must not dilute or enter the percentile pool."""
    table = build_league_table(*_frames()).set_index("nba_id")
    assert not table.loc[3, "qualified"]
    assert pd.isna(table.loc[3, "pct_rim"])
    # Two qualifiers: the higher rate is the 100th percentile, the other 50th.
    assert table.loc[1, "pct_rim"] == pytest.approx(100.0)
    assert table.loc[2, "pct_rim"] == pytest.approx(50.0)


def test_qualification_is_playing_time_not_shot_volume():
    """A high-volume shooter below the possession gate must stay unranked."""
    zones, base, advanced = _frames()
    advanced.loc[advanced["PLAYER_ID"] == 3, "POSS"] = MIN_POSSESSIONS - 1
    base.loc[base["PLAYER_ID"] == 3, "FGA"] = 2000  # shooting cannot qualify him
    table = build_league_table(zones, base, advanced).set_index("nba_id")
    assert not table.loc[3, "qualified"]

    advanced.loc[advanced["PLAYER_ID"] == 3, "POSS"] = MIN_POSSESSIONS
    table = build_league_table(zones, base, advanced).set_index("nba_id")
    assert bool(table.loc[3, "qualified"])


def test_cards_are_ordered_by_minutes_not_by_production():
    """Minutes order reads as the rotation; it must not rank the roster."""
    table = build_league_table(*_frames())
    cards = roster_cards(table, _roster())
    # Giddey out-produces Claxton in every category but plays fewer minutes.
    assert cards["player_name"].tolist() == ["Nic Claxton", "Josh Giddey"]
    assert cards["MIN"].is_monotonic_decreasing


def test_the_cards_carry_no_defensive_category():
    labels = [label for label, _, _ in CATEGORIES]
    assert labels == ["RIM", "PAINT NON-RA", "MID", "THREE", "PASS"]


def test_validation_rejects_zone_totals_that_miss_the_box_score():
    zones, base, advanced = _frames()
    table = build_league_table(zones, base, advanced)
    table.loc[table["nba_id"] == 1, "FGM"] += 3
    with pytest.raises(ValueError, match="do not reconcile"):
        validate_league_table(table, _roster(), roster_cards(table, _roster()))


def test_validation_reports_excluded_roster_players():
    table = build_league_table(*_frames())
    roster = _roster()
    report = validate_league_table(table, roster, roster_cards(table, roster))
    assert report["excluded_roster_names"] == ["Caleb Wilson"]
    assert report["card_count"] == 2
    assert report["qualified_league_players"] == 2


def test_validation_rejects_a_card_without_a_display_name():
    zones, base, advanced = _frames()
    base.loc[base["PLAYER_ID"] == 1, "PLAYER_NAME"] = "Unlisted Player"
    table = build_league_table(zones, base, advanced)
    roster = _roster()
    with pytest.raises(ValueError, match="Missing card labels"):
        validate_league_table(table, roster, roster_cards(table, roster))


def test_validation_rejects_more_cards_than_the_grid_holds():
    table = build_league_table(*_frames())
    cards = roster_cards(table, _roster())
    oversized = pd.concat([cards] * 6, ignore_index=True)
    with pytest.raises(ValueError, match="exceed"):
        validate_league_table(table, _roster(), oversized)


def test_chart_export_is_transparent(tmp_path, monkeypatch):
    """The Canva page supplies the background, so the asset must not."""
    from PIL import Image

    import scripts.prototypes.current_roster_jam_cards as jam

    monkeypatch.setattr(jam, "OUT", tmp_path)
    monkeypatch.setattr(jam, "ensure_headshots", lambda cards: None)
    table = build_league_table(*_frames())
    path = jam.render_chart_only(
        roster_cards(table, _roster()), "2026-07-25", final=False
    )
    image = Image.open(path)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0


def test_every_category_has_a_rate_and_a_percentile():
    table = build_league_table(*_frames())
    for _, key, _ in CATEGORIES:
        assert f"rate_{key}" in table.columns
        assert f"pct_{key}" in table.columns
