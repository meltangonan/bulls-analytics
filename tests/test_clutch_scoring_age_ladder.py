from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.clutch_scoring_age_ladder import (
    CLUTCH_ROW_RULE_COLOR,
    MIN_CLUTCH_GAMES,
    age_winners,
    attach_league_average,
    build_working_table,
    league_averages,
    validate,
)


def test_row_rules_use_the_documented_structural_gray():
    assert CLUTCH_ROW_RULE_COLOR == "#B8B0A8"


def _rows() -> pd.DataFrame:
    rows = []
    for season in [f"{y}-{str(y + 1)[-2:]}" for y in range(2000, 2026)]:
        rows.append({
            "season": season, "player_id": int(season[:4]), "player": "Regular",
            "age": 25, "clutch_games": 10, "clutch_minutes": 20, "clutch_points": 20,
            "clutch_fgm": 8, "clutch_fga": 16, "clutch_ftm": 4, "clutch_fta": 4,
            "wins": 6, "losses": 4, "source_url": "https://nba.com",
        })
    rows += [
        {**rows[0], "player_id": 9001, "player": "Volume", "age": 26,
         "clutch_games": 20, "wins": 11, "losses": 9, "clutch_points": 50},
        {**rows[0], "player_id": 9002, "player": "Rate", "age": 26,
         "clutch_games": 10, "wins": 5, "losses": 5, "clutch_points": 40},
        {**rows[0], "player_id": 9003, "player": "Tiny", "age": 27,
         "clutch_games": MIN_CLUTCH_GAMES - 1, "wins": 4, "losses": 5, "clutch_points": 99},
    ]
    return pd.DataFrame(rows)


def test_total_points_is_the_primary_rank_with_rate_as_context():
    winners = age_winners(build_working_table(_rows()))
    age_26 = winners.loc[winners.age.eq(26)].iloc[0]
    assert age_26.player == "Volume"
    assert age_26.clutch_points_per_game == pytest.approx(2.5)
    assert age_26.clutch_points_per_5_minutes == pytest.approx(12.5)


def test_points_per_five_uses_actual_total_clutch_minutes():
    table = build_working_table(_rows())
    rate = table.loc[table.player.eq("Volume"), "clutch_points_per_5_minutes"].item()
    assert rate == pytest.approx(50 / 20 * 5)


def test_zero_rounded_minutes_leave_rate_unavailable_instead_of_zero():
    rows = _rows()
    rows.loc[0, "clutch_minutes"] = 0
    table = build_working_table(rows)
    assert pd.isna(table.loc[table.player_id.eq(2000), "clutch_points_per_5_minutes"].item())


def test_antonio_davis_portrait_is_a_real_transparent_cutout():
    from PIL import Image
    from scripts.prototypes.clutch_scoring_age_ladder import ANTONIO_DAVIS_PORTRAIT

    image = Image.open(ANTONIO_DAVIS_PORTRAIT)
    assert image.mode == "RGBA"
    assert image.getchannel("A").getextrema() == (0, 255)


def test_minimum_clutch_appearances_is_inclusive():
    table = build_working_table(_rows())
    assert table.loc[table.player.eq("Rate"), "qualified"].item()
    assert not table.loc[table.player.eq("Tiny"), "qualified"].item()


def test_validation_checks_coverage_and_game_records():
    table = attach_league_average(build_working_table(_rows()), _league_rows())
    report = validate(table)
    assert report["season_count"] == 26
    broken = table.copy()
    broken.loc[0, "wins"] += 1
    with pytest.raises(ValueError, match="reconcile"):
        validate(broken)


def _league_rows() -> pd.DataFrame:
    rows = []
    for season in [f"{y}-{str(y + 1)[-2:]}" for y in range(2000, 2026)]:
        for player_id in range(60):
            rows.append({
                "season": season, "player_id": player_id, "player": f"Player {player_id}",
                "clutch_games": 10, "clutch_points": 20 + player_id,
            })
    return pd.DataFrame(rows)


def test_league_average_uses_the_same_clutch_game_floor():
    league = _league_rows()
    league.loc[len(league)] = {
        "season": "2000-01", "player_id": 999, "player": "Tiny sample",
        "clutch_games": 9, "clutch_points": 999,
    }
    baseline = league_averages(league).set_index("season")
    assert baseline.loc["2000-01", "league_average_clutch_points"] == pytest.approx(49.5)


def test_ratio_compares_bulls_total_to_its_own_season_average():
    table = attach_league_average(build_working_table(_rows()), _league_rows())
    volume = table.loc[table.player.eq("Volume")].iloc[0]
    assert volume.league_average_ratio == pytest.approx(50 / 49.5)
