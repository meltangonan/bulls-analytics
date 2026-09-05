"""Post-specific tests for the Bulls five-man rDRTG ranking."""

from __future__ import annotations

import pandas as pd
import pytest
from PIL import Image

from scripts.prototypes import bulls_lineup_rdrtg


def _lineup_rows(count: int = 10) -> pd.DataFrame:
    keys = list(bulls_lineup_rdrtg.POSITION_ORDER)
    rows = []
    for index in range(count):
        season, entity_id = keys[index % len(keys)]
        names = bulls_lineup_rdrtg.POSITION_ORDER[(season, entity_id)]
        rows.append(
            {
                "Season": season,
                "EntityId": entity_id,
                "Name": ", ".join(names),
                "TeamAbbreviation": "CHI",
                "SecondsPlayed": 30_000 - index,
                "GamesPlayed": 30,
                "DefPoss": 500 + index,
                "OpponentPoints": 650 - index * 3,
            }
        )
    return pd.DataFrame(rows)


def _league_for(lineups: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"Season": sorted(lineups["Season"].unique()), "LeagueDRTG": 108.0})


def test_prepare_computes_same_season_relative_drtg_and_ranks():
    lineups = _lineup_rows()
    rows = bulls_lineup_rdrtg.prepare_ranking(lineups, _league_for(lineups))

    assert len(rows) == 10
    assert rows["rDRTG"].is_monotonic_decreasing
    expected = 108 - 100 * rows.iloc[0]["OpponentPoints"] / rows.iloc[0]["DefPoss"]
    assert rows.iloc[0]["rDRTG"] == pytest.approx(expected)


def test_prepare_applies_500_possession_floor_before_ranking():
    lineups = _lineup_rows()
    lineups.loc[lineups.index[0], "DefPoss"] = 499

    with pytest.raises(ValueError, match="Only 9 lineups reached 500 possessions"):
        bulls_lineup_rdrtg.prepare_ranking(lineups, _league_for(lineups))


def test_position_order_must_match_exact_source_names():
    lineups = _lineup_rows()
    lineups.loc[lineups.index[0], "Name"] = lineups.loc[lineups.index[0], "Name"].replace("Kirk Hinrich", "Different Player")

    with pytest.raises(ValueError, match="Position order does not match"):
        bulls_lineup_rdrtg.prepare_ranking(lineups, _league_for(lineups))


def test_2022_23_display_order_matches_the_paired_rortg_post():
    expected = (
        "Patrick Beverley",
        "Alex Caruso",
        "Zach LaVine",
        "DeMar DeRozan",
        "Nikola Vucevic",
    )

    assert bulls_lineup_rdrtg.POSITION_ORDER[("2022-23", "1627936-201942-201976-202696-203897")] == expected


def test_prepare_rejects_duplicate_season_lineups():
    lineups = pd.concat([_lineup_rows(), _lineup_rows().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate season-lineup"):
        bulls_lineup_rdrtg.prepare_ranking(lineups, _league_for(lineups))


def test_chart_export_has_expected_dimensions_and_transparency(tmp_path, monkeypatch):
    monkeypatch.setattr(bulls_lineup_rdrtg, "OUT", tmp_path)
    monkeypatch.setattr(bulls_lineup_rdrtg, "ensure_historical_headshots", lambda ids: None)
    rows = bulls_lineup_rdrtg.prepare_ranking(_lineup_rows(), _league_for(_lineup_rows()))

    output = bulls_lineup_rdrtg.render_chart(rows)
    image = Image.open(output)

    assert image.size == (1080, 1350)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0


def test_rating_label_uses_true_minus_and_suppresses_signed_zero():
    assert bulls_lineup_rdrtg._rating_label(3.24) == "+3.2"
    assert bulls_lineup_rdrtg._rating_label(-1.34) == "−1.3"
    assert bulls_lineup_rdrtg._rating_label(-0.01) == "0.0"


def test_tracked_snapshot_reproduces_the_published_top_ten():
    lineups, league, audit = bulls_lineup_rdrtg.load_source_tables()
    rows = bulls_lineup_rdrtg.prepare_ranking(lineups, league)

    assert audit["Season"].nunique() == 26
    assert audit["Season"].min() == "2000-01"
    assert audit["Season"].max() == "2025-26"
    assert audit["SecondsSortedDescending"].all()
    assert (audit["LastRowDefPoss"] < bulls_lineup_rdrtg.MIN_POSSESSIONS).all()
    assert (lineups["DefPoss"] >= bulls_lineup_rdrtg.MIN_POSSESSIONS).sum() == 24
    assert rows.iloc[0]["Season"] == "2004-05"
    assert rows.iloc[0]["rDRTG"] == pytest.approx(12.5739337343)
    assert rows.iloc[-1]["Season"] == "2023-24"
    assert rows.iloc[-1]["rDRTG"] == pytest.approx(4.1360909091)
