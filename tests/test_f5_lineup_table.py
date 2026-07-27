"""Post-specific tests for the Bulls two-player lineup table."""

from __future__ import annotations

import pandas as pd
import pytest
from PIL import Image

from scripts.prototypes import f5_lineup_table
from scripts.prototypes.f5_lineup_table import prepare_lineup_rows


def _lineups(count: int = 12) -> pd.DataFrame:
    rows = []
    for index in range(count):
        off_rating = 115.0 - index / 10
        def_rating = 114.0 + index / 10
        rows.append(
            {
                "GROUP_ID": f"-{index}-{index + 100}-",
                "GROUP_NAME": f"Player {index} - Teammate {index}",
                "MIN": 100 + index * 10,
                "OFF_RATING": off_rating,
                "DEF_RATING": def_rating,
                "NET_RATING": round(off_rating - def_rating, 1),
            }
        )
    return pd.DataFrame(rows)


def test_prepare_selects_ten_pairs_in_minutes_order():
    rows = prepare_lineup_rows(_lineups())

    assert len(rows) == 10
    assert rows["MIN"].is_monotonic_decreasing
    assert rows.iloc[0]["GROUP_NAME"] == "Player 11 - Teammate 11"
    assert rows.iloc[-1]["GROUP_NAME"] == "Player 2 - Teammate 2"


def test_prepare_extracts_player_names_and_ids_for_horizontal_portraits():
    rows = prepare_lineup_rows(_lineups())

    assert rows.iloc[0]["PLAYER_1_NAME"] == "Player 11"
    assert rows.iloc[0]["PLAYER_2_NAME"] == "Teammate 11"
    assert rows.iloc[0]["PLAYER_1_LABEL"] == "11"
    assert rows.iloc[0]["PLAYER_2_LABEL"] == "11"
    assert rows.iloc[0]["PLAYER_1_ID"] == 11
    assert rows.iloc[0]["PLAYER_2_ID"] == 111


def test_prepare_selects_five_highest_net_ratings_above_minutes_gate():
    lineups = _lineups()
    lineups["MIN"] = [250, 300, 350, 399, 400, 410, 420, 430, 440, 450, 460, 470]
    lineups["NET_RATING"] = [
        20.0,
        19.0,
        18.0,
        17.0,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
        6.0,
        7.0,
        8.0,
    ]
    lineups["OFF_RATING"] = lineups["DEF_RATING"] + lineups["NET_RATING"]

    rows = prepare_lineup_rows(
        lineups,
        top_n=5,
        ranking="net-rating",
        min_minutes=400,
    )

    assert len(rows) == 5
    assert rows["MIN"].min() >= 400
    assert rows["NET_RATING"].tolist() == [8.0, 7.0, 6.0, 5.0, 4.0]


def test_prepare_rejects_a_net_rating_that_does_not_reconcile():
    lineups = _lineups()
    lineups.loc[lineups["MIN"].idxmax(), "NET_RATING"] += 1.0

    with pytest.raises(ValueError, match="does not reconcile"):
        prepare_lineup_rows(lineups)


def test_prepare_rejects_duplicate_group_ids():
    lineups = _lineups()
    lineups.loc[1, "GROUP_ID"] = lineups.loc[0, "GROUP_ID"]

    with pytest.raises(ValueError, match="Duplicate two-player group IDs"):
        prepare_lineup_rows(lineups)


def test_prepare_rejects_fewer_than_ten_pairs():
    with pytest.raises(ValueError, match="10 are required"):
        prepare_lineup_rows(_lineups(count=9))


def test_prepare_rejects_fewer_than_five_pairs_above_minutes_gate():
    lineups = _lineups(count=6)
    lineups["MIN"] = [100, 200, 300, 400, 500, 600]

    with pytest.raises(ValueError, match="3 eligible Bulls pairs"):
        prepare_lineup_rows(
            lineups,
            top_n=5,
            ranking="net-rating",
            min_minutes=400,
        )


def test_chart_export_has_expected_dimensions_and_transparency(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(f5_lineup_table, "OUT", tmp_path)
    rows = prepare_lineup_rows(_lineups())

    output = f5_lineup_table.render_chart(rows, "2026-07-25")
    image = Image.open(output)

    assert image.size == (1080, 1150)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0


def test_five_row_chart_keeps_row_scale_and_crops_unused_height(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(f5_lineup_table, "OUT", tmp_path)
    rows = prepare_lineup_rows(
        _lineups(),
        top_n=5,
        ranking="net-rating",
        min_minutes=100,
    )

    output = f5_lineup_table.render_chart(
        rows,
        "2026-07-26",
        ranking="net-rating",
        min_minutes=400,
    )
    image = Image.open(output)

    assert image.size == (1080, 630)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0
