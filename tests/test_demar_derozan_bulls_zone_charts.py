"""Coverage, pooling, and saved-data checks for DeRozan's Bulls tenure."""
from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes import demar_derozan_bulls_zone_charts as charts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"


def test_scope_is_exactly_derozans_three_bulls_seasons():
    assert charts.PLAYER_ID == 201942
    assert charts.SEASONS == ("2021-22", "2022-23", "2023-24")


def test_tenure_floor_is_three_times_the_season_floor():
    assert charts.SEASON_MIN_ZONE_FGA == 20
    assert charts.TENURE_MIN_ZONE_FGA == 60


def test_shot_rows_must_reconcile_to_official_bulls_fga():
    totals = pd.Series({"FGA": 3})
    shots = pd.DataFrame({"shot_made": [1, 0, 1]})
    charts.reconcile_shot_count("2021-22", totals, shots)
    with pytest.raises(ValueError, match="shot rows 2 != Bulls FGA 3"):
        charts.reconcile_shot_count("2021-22", totals, shots.iloc[:2])


def test_tenure_totals_add_the_three_nonoverlapping_seasons():
    rows = [
        pd.Series({"GP": 76, "MIN": 2743, "FGA": 1535}),
        pd.Series({"GP": 74, "MIN": 2682, "FGA": 1303}),
        pd.Series({"GP": 79, "MIN": 2989, "FGA": 1355}),
    ]
    total = charts.tenure_totals(rows)
    assert total.GP == 229
    assert total.FGA == 4193


def test_saved_data_reconstructs_every_page_and_pooled_total():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv")
    assert summary.window.tolist() == [*charts.SEASONS, "Bulls tenure"]
    assert summary.min_zone_fga.tolist() == [20, 20, 20, 60]

    season_fga = 0
    for season in charts.SEASONS:
        totals = pd.read_csv(DATA / f"{season}-demar-derozan-bulls-totals.csv").iloc[0]
        shots = pd.read_csv(DATA / f"{season}-demar-derozan-bulls-shots.csv")
        charts.reconcile_shot_count(season, totals, shots)
        season_fga += len(shots)
    tenure = summary[summary.window.eq("Bulls tenure")].iloc[0]
    assert int(tenure.bulls_fga) == season_fga
    assert int(tenure.shot_rows) == season_fga


def test_saved_zone_and_baseline_tables_are_complete():
    splits = pd.read_csv(DATA / "zone-splits.csv")
    baselines = pd.read_csv(DATA / "league-zone-baselines.csv")
    assert all(len(group) == 12 for _, group in splits.groupby("window"))
    assert all(len(group) == 12 for _, group in baselines.groupby("window"))
    for _, group in splits.groupby("window"):
        assert group.fga_share_pct.sum() == pytest.approx(100.0, abs=0.001)
    for _, group in baselines.groupby("window"):
        assert group.fga_share_pct.sum() == pytest.approx(100.0, abs=0.001)
