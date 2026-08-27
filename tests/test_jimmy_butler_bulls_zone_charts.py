"""Scope and reconciliation checks for Jimmy Butler's Bulls charts."""
from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes import jimmy_butler_bulls_zone_charts as charts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"


def test_scope_is_all_six_bulls_seasons():
    assert charts.PLAYER_ID == 202710
    assert charts.ALL_BULLS_SEASONS == (
        "2011-12", "2012-13", "2013-14", "2014-15", "2015-16", "2016-17",
    )


def test_page_and_zone_floors_are_distinct():
    assert charts.MIN_SEASON_FGA == 300
    assert charts.SEASON_MIN_ZONE_FGA == 20
    assert charts.TENURE_MIN_ZONE_FGA == 120


def test_reconciliation_checks_attempts_and_makes():
    totals = pd.Series({"FGA": 3, "FGM": 2})
    shots = pd.DataFrame({"shot_made": [1, 0, 1]})
    charts.reconcile_shots("season", totals, shots)
    with pytest.raises(ValueError, match="shot rows"):
        charts.reconcile_shots("season", totals, shots.iloc[:2])
    with pytest.raises(ValueError, match="shot makes"):
        charts.reconcile_shots("season", totals, shots.assign(shot_made=0))


def test_saved_data_reconstructs_every_season_and_full_tenure():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv")
    assert summary.window.tolist() == [*charts.ALL_BULLS_SEASONS, "Bulls tenure"]
    total = 0
    for season in charts.ALL_BULLS_SEASONS:
        totals = pd.read_csv(
            DATA / f"{season}-jimmy-butler-bulls-totals.csv"
        ).iloc[0]
        shots = pd.read_csv(
            DATA / f"{season}-jimmy-butler-bulls-shots.csv"
        )
        charts.reconcile_shots(season, totals, shots)
        charts.assert_source_family_reconciliation(season, shots)
        saved = summary.loc[summary.window.eq(season)].iloc[0]
        assert int(saved.points) == int(totals.PTS)
        assert float(saved.ppg) == pytest.approx(
            round(float(totals.PTS) / int(totals.GP), 1)
        )
        rendered = bool(saved.rendered_detail_page)
        assert rendered == (int(totals.FGA) >= charts.MIN_SEASON_FGA)
        total += len(shots)
    tenure = summary[summary.window.eq("Bulls tenure")].iloc[0]
    assert int(tenure.bulls_fga) == total
    assert int(tenure.shot_rows) == total
    assert int(tenure.min_zone_fga) == charts.TENURE_MIN_ZONE_FGA
    all_totals = [
        pd.read_csv(DATA / f"{season}-jimmy-butler-bulls-totals.csv").iloc[0]
        for season in charts.ALL_BULLS_SEASONS
    ]
    assert int(tenure.points) == sum(int(row.PTS) for row in all_totals)
    assert float(tenure.ppg) == pytest.approx(
        round(sum(int(row.PTS) for row in all_totals)
              / sum(int(row.GP) for row in all_totals), 1)
    )


def test_saved_zone_tables_cover_each_mapped_attempt():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    splits = pd.read_csv(DATA / "zone-splits.csv")
    assert all(len(group) == 12 for _, group in splits.groupby("window"))
    for window, group in splits.groupby("window"):
        assert int(group.fga.sum()) == int(summary.loc[window, "mapped_zone_fga"])
        assert int(group.fga.sum() + group.subject_excluded_fga.iloc[0]) == int(
            summary.loc[window, "shot_rows"]
        )
