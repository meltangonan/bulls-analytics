"""Post-specific tests for the Bulls five-man rORTG ranking."""

from __future__ import annotations

import pandas as pd
import pytest
from PIL import Image

from scripts.prototypes import bulls_lineup_rortg


def _lineup_rows(count: int = 12) -> pd.DataFrame:
    keys = list(bulls_lineup_rortg.POSITION_ORDER)
    rows = []
    for index in range(count):
        season, entity_id = keys[index % len(keys)]
        names = bulls_lineup_rortg.POSITION_ORDER[(season, entity_id)]
        rows.append(
            {
                "Season": season,
                "EntityId": entity_id,
                "Name": ", ".join(names),
                "TeamAbbreviation": "CHI",
                "SecondsPlayed": 30_000 - index,
                "GamesPlayed": 30,
                "OffPoss": 500 + index,
                "Points": 650 - index * 3,
            }
        )
    # Tests using more than the ten real keys need unique season-lineup pairs.
    for index in range(len(keys), len(rows)):
        rows[index]["EntityId"] = f"test-{index}"
    return pd.DataFrame(rows)


def _real_position_rows() -> pd.DataFrame:
    rows = []
    for index, ((season, entity_id), names) in enumerate(
        bulls_lineup_rortg.POSITION_ORDER.items()
    ):
        rows.append(
            {
                "Season": season,
                "EntityId": entity_id,
                "Name": ", ".join(names),
                "TeamAbbreviation": "CHI",
                "SecondsPlayed": 30_000 - index,
                "GamesPlayed": 30,
                "OffPoss": 600,
                "Points": 720 - index * 3,
            }
        )
    return pd.DataFrame(rows)


def _league_for(lineups: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Season": sorted(lineups["Season"].unique()),
            "LeagueORTG": 108.0,
        }
    )


def test_prepare_computes_same_season_relative_ortg_and_ranks():
    lineups = _real_position_rows()
    rows = bulls_lineup_rortg.prepare_ranking(lineups, _league_for(lineups))

    assert len(rows) == 10
    assert rows["rORTG"].is_monotonic_decreasing
    expected = 100 * rows.iloc[0]["Points"] / rows.iloc[0]["OffPoss"] - 108
    assert rows.iloc[0]["rORTG"] == pytest.approx(expected)


def test_prepare_applies_500_possession_floor_before_ranking():
    lineups = _real_position_rows()
    lineups.loc[lineups.index[0], "OffPoss"] = 499

    with pytest.raises(ValueError, match="Only 9 lineups reached 500 possessions"):
        bulls_lineup_rortg.prepare_ranking(lineups, _league_for(lineups))


def test_position_order_must_match_exact_source_names():
    lineups = _real_position_rows()
    lineups.loc[lineups.index[0], "Name"] = lineups.loc[
        lineups.index[0], "Name"
    ].replace("Derrick Rose", "Different Player")

    with pytest.raises(ValueError, match="Position order does not match"):
        bulls_lineup_rortg.prepare_ranking(lineups, _league_for(lineups))


def test_position_columns_read_pg_through_center():
    lineups = _real_position_rows()
    rows = bulls_lineup_rortg.prepare_ranking(lineups, _league_for(lineups))
    rose_row = rows.loc[
        rows["EntityId"] == "200758-201149-201565-2430-2736"
    ].iloc[0]

    assert [rose_row[position] for position in bulls_lineup_rortg.POSITION_COLUMNS] == [
        "Derrick Rose",
        "Ronnie Brewer",
        "Luol Deng",
        "Carlos Boozer",
        "Joakim Noah",
    ]


def test_prepare_rejects_duplicate_season_lineups():
    lineups = _real_position_rows()
    lineups = pd.concat([lineups, lineups.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate season-lineup"):
        bulls_lineup_rortg.prepare_ranking(lineups, _league_for(lineups))


def test_fetch_response_requires_minutes_order_and_safe_tail():
    names = next(iter(bulls_lineup_rortg.POSITION_ORDER.values()))
    base = {
        "EntityId": "1-2-3-4-5",
        "Name": ", ".join(names),
        "TeamAbbreviation": "CHI",
        "SecondsPlayed": 1000,
        "GamesPlayed": 10,
        "OffPoss": 100,
        "Points": 110,
        "Season": "2000-01",
    }
    payload = {"multi_row_table_data": [base, {**base, "SecondsPlayed": 10, "OffPoss": 1}]}
    _, audit = bulls_lineup_rortg._validated_lineup_response(payload, "2000-01")

    assert audit["RowsReturned"] == 2
    assert audit["LastRowOffPoss"] == 1

    reversed_payload = {"multi_row_table_data": list(reversed(payload["multi_row_table_data"]))}
    with pytest.raises(ValueError, match="not minutes-sorted"):
        bulls_lineup_rortg._validated_lineup_response(reversed_payload, "2000-01")


def test_chart_export_has_expected_dimensions_and_transparency(tmp_path, monkeypatch):
    monkeypatch.setattr(bulls_lineup_rortg, "OUT", tmp_path)
    lineups = _real_position_rows()
    rows = bulls_lineup_rortg.prepare_ranking(lineups, _league_for(lineups))

    output = bulls_lineup_rortg.render_chart(rows)
    image = Image.open(output)

    assert image.size == (1080, 1350)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0


def test_rating_label_uses_true_minus_and_suppresses_signed_zero():
    assert bulls_lineup_rortg._rating_label(3.24) == "+3.2"
    assert bulls_lineup_rortg._rating_label(-1.34) == "−1.3"
    assert bulls_lineup_rortg._rating_label(-0.01) == "0.0"


def test_tracked_snapshot_reproduces_the_published_top_ten():
    lineups, league, audit = bulls_lineup_rortg.load_source_tables()
    rows = bulls_lineup_rortg.prepare_ranking(lineups, league)

    assert audit["Season"].nunique() == 26
    assert audit["Season"].min() == "2000-01"
    assert audit["Season"].max() == "2025-26"
    assert audit["SecondsSortedDescending"].all()
    assert (audit["LastRowOffPoss"] < bulls_lineup_rortg.MIN_POSSESSIONS).all()
    assert (lineups["OffPoss"] >= bulls_lineup_rortg.MIN_POSSESSIONS).sum() == 24
    assert rows.iloc[0]["Season"] == "2011-12"
    assert rows.iloc[0]["rORTG"] == pytest.approx(9.2236779026)
    assert rows.iloc[-1]["Season"] == "2012-13"
    assert rows.iloc[-1]["rORTG"] == pytest.approx(-1.9139750623)
