"""Scope, reconciliation, and orientation checks for Rose's Bulls charts."""
from pathlib import Path

import pandas as pd
import pytest

from bulls.graphics.court import nba_to_basket_bottom_px
from scripts import make_shot_chart as shot_chart
from scripts.prototypes import derrick_rose_bulls_zone_charts as charts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"


def test_scope_is_seven_played_bulls_seasons():
    assert charts.PLAYER_ID == 201565
    assert charts.SEASONS == (
        "2008-09", "2009-10", "2010-11", "2011-12",
        "2013-14", "2014-15", "2015-16",
    )
    assert charts.OMITTED_NO_FGA_SEASON == "2012-13"


def test_tenure_floor_scales_with_included_seasons():
    assert charts.SEASON_MIN_ZONE_FGA == 20
    assert charts.TENURE_MIN_ZONE_FGA == 140


def test_reconciliation_checks_attempts_and_makes():
    totals = pd.Series({"FGA": 3, "FGM": 2})
    shots = pd.DataFrame({"shot_made": [1, 0, 1]})
    charts.reconcile_shots("season", totals, shots)
    with pytest.raises(ValueError, match="shot rows"):
        charts.reconcile_shots("season", totals, shots.iloc[:2])
    with pytest.raises(ValueError, match="shot makes"):
        charts.reconcile_shots("season", totals, shots.assign(shot_made=0))


def test_only_completely_unlocated_league_rows_are_excluded():
    league = pd.DataFrame({
        "loc_x": [1.0, None], "loc_y": [2.0, None],
        "shot_distance": [3.0, None], "shot_zone": ["Restricted Area", None],
        "shot_zone_area": ["Center(C)", None],
    })
    located, excluded = charts.located_league_shots("season", league)
    assert len(located) == 1
    assert excluded == 1

    partial = league.copy()
    partial.loc[1, "loc_x"] = 1.0
    with pytest.raises(ValueError, match="partially missing"):
        charts.located_league_shots("season", partial)


@pytest.mark.parametrize("zone,expected_side", [
    ("Left Corner 3", "viewer-right"),
    ("Left Baseline", "viewer-right"),
    ("Left Mid-Range", "viewer-right"),
    ("Left Wing 3", "viewer-right"),
    ("Right Corner 3", "viewer-left"),
    ("Right Baseline", "viewer-left"),
    ("Right Mid-Range", "viewer-left"),
    ("Right Wing 3", "viewer-left"),
])
def test_every_named_side_uses_basket_bottom_screen_placement(zone, expected_side):
    x, y = shot_chart.ZONE12_ANCHORS[zone]
    display_x = nba_to_basket_bottom_px(0.0, 0.0, 1.0, x, y)[0]
    if expected_side == "viewer-right":
        assert display_x > 250.0
    else:
        assert display_x < 250.0


def test_saved_data_reconstructs_every_page_and_tenure_total():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv")
    assert summary.window.tolist() == [*charts.SEASONS, "Bulls tenure"]
    assert summary.min_zone_fga.tolist() == [20] * 7 + [140]
    total = 0
    for season in charts.SEASONS:
        totals = pd.read_csv(
            DATA / f"{season}-derrick-rose-bulls-totals.csv"
        ).iloc[0]
        shots = pd.read_csv(
            DATA / f"{season}-derrick-rose-bulls-shots.csv"
        )
        charts.reconcile_shots(season, totals, shots)
        charts.assert_source_family_reconciliation(season, shots)
        total += len(shots)
    tenure = summary[summary.window.eq("Bulls tenure")].iloc[0]
    assert int(tenure.bulls_fga) == total
    assert int(tenure.shot_rows) == total


def test_saved_zone_tables_are_complete_and_cover_each_mapped_attempt():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    splits = pd.read_csv(DATA / "zone-splits.csv")
    assert all(len(group) == 12 for _, group in splits.groupby("window"))
    for window, group in splits.groupby("window"):
        assert int(group.fga.sum()) == int(summary.loc[window, "mapped_zone_fga"])
        assert int(group.fga.sum() + group.subject_excluded_fga.iloc[0]) == int(
            summary.loc[window, "shot_rows"]
        )
