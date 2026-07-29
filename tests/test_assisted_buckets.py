"""Post-specific tests for the current-roster assisted-buckets chart."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from scripts.prototypes.assisted_buckets import (
    MIN_FIELD_GOALS_MADE,
    build_working_table,
    canva_copy_block,
    qualified_players,
    segment_colors,
    segment_label,
    validate_working_table,
)
from bulls.graphics.house import DEFAULT_THEME


def _roster() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"nba_id": 1, "official_roster_name": "Rob Dillingham"},
            {"nba_id": 2, "official_roster_name": "Jalen Smith"},
            {"nba_id": 3, "official_roster_name": "Zach Collins"},
            {"nba_id": 4, "official_roster_name": "Caleb Wilson"},
        ]
    )


def _scoring() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "PLAYER_ID": 1,
                "PLAYER_NAME": "Rob Dillingham",
                "TEAM_ABBREVIATION": "MIN",
                "GP": 65,
                "FGM": 100,
                "PCT_AST_FGM": 0.450,
                "PCT_UAST_FGM": 0.550,
            },
            {
                "PLAYER_ID": 2,
                "PLAYER_NAME": "Jalen Smith",
                "TEAM_ABBREVIATION": "CHI",
                "GP": 53,
                "FGM": 195,
                "PCT_AST_FGM": 0.867,
                "PCT_UAST_FGM": 0.133,
            },
            {
                "PLAYER_ID": 3,
                "PLAYER_NAME": "Zach Collins",
                "TEAM_ABBREVIATION": "CHI",
                "GP": 10,
                "FGM": 37,
                "PCT_AST_FGM": 0.865,
                "PCT_UAST_FGM": 0.135,
            },
        ]
    )


def _table() -> pd.DataFrame:
    return build_working_table(
        _roster(),
        _scoring(),
        datetime(2026, 7, 29, 12, tzinfo=ZoneInfo("America/Chicago")),
    )


def test_uses_full_season_profile_for_a_current_bull():
    table = _table()
    dillingham = table.loc[
        table["official_roster_name"] == "Rob Dillingham"
    ].iloc[0]

    assert dillingham["season_team_field"] == "MIN"
    assert dillingham["assisted_pct"] == pytest.approx(45.0)
    assert dillingham["unassisted_pct"] == pytest.approx(55.0)


def test_threshold_is_inclusive_at_100_made_field_goals():
    table = _table()
    dillingham = table.loc[
        table["official_roster_name"] == "Rob Dillingham"
    ].iloc[0]

    assert dillingham["field_goals_made"] == MIN_FIELD_GOALS_MADE
    assert bool(dillingham["qualified"])


def test_qualifiers_are_sorted_by_unassisted_share():
    players = qualified_players(_table())

    assert players["official_roster_name"].tolist() == [
        "Rob Dillingham",
        "Jalen Smith",
    ]
    assert players["unassisted_share"].is_monotonic_decreasing


def test_inferred_segment_counts_reconcile_to_official_total():
    table = _table()
    report = validate_working_table(table)
    dillingham = table.loc[
        table["official_roster_name"] == "Rob Dillingham"
    ].iloc[0]
    jalen = table.loc[
        table["official_roster_name"] == "Jalen Smith"
    ].iloc[0]

    assert dillingham["unassisted_fgm"] == 55
    assert dillingham["assisted_fgm"] == 45
    assert jalen["unassisted_fgm"] == 26
    assert jalen["assisted_fgm"] == 169
    assert report["max_count_inference_gap"] <= 0.00051


def test_segment_label_puts_fgm_count_in_parentheses():
    assert segment_label(54.6, 89) == "55%\n(89 FGM)"


def test_unassisted_is_red_and_assisted_is_near_black():
    unassisted, assisted = segment_colors()
    assert unassisted == DEFAULT_THEME.accent
    assert assisted == DEFAULT_THEME.ink


def test_low_sample_and_no_data_players_remain_auditable():
    table = _table()
    report = validate_working_table(table)

    assert report["below_threshold_names"] == ["Zach Collins"]
    assert report["no_data_names"] == ["Caleb Wilson"]
    assert report["qualified_count"] == 2


def test_assisted_and_unassisted_shares_must_total_100_percent():
    table = _table()
    table.loc[
        table["official_roster_name"] == "Rob Dillingham",
        "assisted_share",
    ] = 0.400
    table.loc[
        table["official_roster_name"] == "Rob Dillingham",
        "share_total",
    ] = 0.946

    with pytest.raises(ValueError, match="do not reconcile"):
        validate_working_table(table)


def test_copy_block_carries_scope_and_interpretation_guardrail():
    report = validate_working_table(_table())
    copy = canva_copy_block(report, "2026-07-29")

    assert "100+ made field goals" in copy
    assert "Full-season totals across all teams" in copy
    assert "not necessarily self-created" in copy
    assert "Roster as of 2026-07-29" in copy


def test_chart_export_is_transparent(tmp_path, monkeypatch):
    from PIL import Image

    import scripts.prototypes.assisted_buckets as assisted

    placed_headshots = []

    def record_headshot(
        ax,
        image_path,
        x,
        y,
        half_width,
        half_height,
        **kwargs,
    ):
        placed_headshots.append(
            (image_path.stem, x, y, half_width, half_height)
        )

    monkeypatch.setattr(assisted, "OUT", tmp_path)
    monkeypatch.setattr(assisted, "portrait_headshot_label", record_headshot)
    path = assisted.render_chart(
        qualified_players(_table()),
        "2026-07-29",
        final=False,
    )

    image = Image.open(path)
    assert image.mode == "RGBA"
    assert image.size == (1080, 1000)
    assert image.getpixel((0, 0))[3] == 0
    assert [placement[0] for placement in placed_headshots] == ["1", "2"]
    assert all(width < height for _, _, _, width, height in placed_headshots)
