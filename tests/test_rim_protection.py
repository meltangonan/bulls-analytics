import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes import rim_protection_data as data
from scripts.prototypes import rim_protection_table as table


def test_points_saved_counts_makes_a_league_average_defender_would_allow():
    frame = pd.DataFrame({
        "PLAYER_ID": [1], "PLAYER_NAME": ["Player One"], "TEAM_ID": [data.BULLS],
        "GP": [80], "BLK": [100], "DEF_RIM_FGM": [274], "DEF_RIM_FGA": [522],
    })
    got = data.add_measures(frame, "2014-15", 0.6132).iloc[0]
    # 522 attempts x 61.32% = 320.1 expected makes, 274 allowed.
    assert got.rim_makes_saved == pytest.approx(46.09, abs=.01)
    assert got.pct_vs_league == pytest.approx(-8.83, abs=.01)


def test_nba_rank_excludes_the_players_own_combined_league_row():
    league = pd.DataFrame({
        "season": ["2016-17"] * 3,
        "player_id": [7, 8, 9],
        # A traded player's league row covers both teams, so it outranks the
        # Chicago stint it should not be compared against.
        "rim_points_saved": [80.0, 50.0, 20.0],
    })
    assert data.nba_rank(37.0, "2016-17", 7, league) == 2
    assert data.nba_rank(37.0, "2016-17", 99, league) == 3


def test_nba_rank_compares_within_the_same_season_only():
    league = pd.DataFrame({
        "season": ["2013-14", "2013-14", "2022-23"],
        "player_id": [1, 2, 3],
        "rim_points_saved": [90.0, 40.0, 95.0],
    })
    assert data.nba_rank(50.0, "2013-14", 1, league) == 1


def test_table_rows_apply_the_minutes_floor():
    bulls = pd.DataFrame({
        "season": ["2021-22", "2014-15"],
        "player_id": [1, 2],
        "minutes": [data.TABLE_MIN_MINUTES - 1, data.TABLE_MIN_MINUTES],
        "rim_points_saved": [48.6, 20.0],
        "rim_fga": [136, 200],
    })
    league = pd.DataFrame({"season": [], "player_id": [], "rim_points_saved": []})
    got = data.table_rows(bulls, league)
    assert got.player_id.tolist() == [2]


def test_table_rows_refuse_a_tie_at_the_cut(monkeypatch):
    monkeypatch.setattr(data, "TABLE_ROWS", 2)
    bulls = pd.DataFrame({
        "season": ["2013-14", "2014-15", "2015-16"],
        "player_id": [1, 2, 3],
        "minutes": [2000, 2000, 2000],
        "rim_points_saved": [50.0, 30.0, 30.0],
        "rim_fga": [300, 200, 200],
    })
    league = pd.DataFrame({"season": [], "player_id": [], "rim_points_saved": []})
    with pytest.raises(ValueError, match="Tie at the table cut"):
        data.table_rows(bulls, league)


def test_comparison_colour_reads_negative_as_good_defence():
    assert table._comparison_color(-8.8) == table.GREEN
    assert table._comparison_color(8.8) == table.RED
    # Inside the neutral band a small gap claims nothing.
    assert table._comparison_color(-2.6) == table.GREY


def test_signed_uses_a_true_minus_and_drops_a_rounding_zero_sign():
    assert table._signed(-8.83) == "−8.8"
    assert table._signed(4.9) == "+4.9"
    assert table._signed(-0.01) == "0.0"


@pytest.mark.parametrize("page", sorted(table.PAGE_FRAMES))
def test_row_height_fills_the_canva_frame(page):
    rows = 15
    height = table.TOP_BOTTOM * 2 + rows * table._row_height(rows, table.PAGE_FRAMES[page])
    assert table.WIDTH / height == pytest.approx(table.PAGE_FRAMES[page], abs=.01)


POST = Path(__file__).resolve().parents[1] / "docs/visuals/2026-09-18-rim-protection-landscape/data"


def test_saved_chicago_rows_reconcile_to_the_team_every_season():
    audit = pd.read_csv(POST / "season_audit.csv")
    assert len(audit) == 13
    assert (audit.chicago_player_sum_rim_fga == audit.chicago_team_rim_fga).all()


def test_2024_25_is_rebuilt_from_date_halves_because_the_aggregate_is_inflated():
    audit = pd.read_csv(POST / "season_audit.csv").set_index("season")
    broken = audit.loc["2024-25"]
    assert broken.source_path == "date halves"
    # NBA.com's own full-season aggregate is about 17% higher than its
    # game-level data; every other season matches exactly.
    assert broken.full_season_aggregate_rim_fga > 1.15 * broken.league_rim_fga
    others = audit.drop("2024-25")
    assert (others.source_path == "full season").all()


def test_published_selection_matches_the_recorded_qualifier():
    top = pd.read_csv(POST / "top15_table.csv")
    source = json.loads((POST / "source.json").read_text())
    assert len(top) == data.TABLE_ROWS
    assert (top.minutes >= data.TABLE_MIN_MINUTES).all()
    assert top.rim_points_saved.is_monotonic_decreasing
    assert str(data.TABLE_MIN_MINUTES) in source["selection_table"]
