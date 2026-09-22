"""Scope, reconciliation, and cover-layout checks for LaVine's Bulls charts.

The reconciliation tests are the load-bearing ones. Every shot pull in this post
is scoped to one franchise, and a wrongly-scoped ShotChartDetail call returns an
empty frame rather than raising -- so "did we get the right shots" is a question
only an independent total can answer. The shared zone-grid geometry is pinned by
the Hinrich tests; this file checks only LaVine's 3-3-2 arrangement.
"""
from pathlib import Path

import pandas as pd

from scripts import make_shot_chart as shot_chart
from scripts.prototypes import lavine_bulls_zone_charts as charts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"


def test_scope_is_eight_consecutive_bulls_seasons():
    assert charts.PLAYER_ID == 203897
    assert charts.SEASONS == (
        "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23",
        "2023-24", "2024-25",
    )
    assert charts.TENURE_MIN_ZONE_FGA == 20 * len(charts.SEASONS) == 160


def test_saved_data_reconstructs_every_page_and_tenure_total():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv")
    assert summary.window.tolist() == [*charts.SEASONS, charts.TENURE_LABEL]
    assert summary.min_zone_fga.tolist() == [20] * len(charts.SEASONS) + [160]
    assert ((summary.ppg - summary.points / summary.games).abs() <= 0.05).all()
    official = drawn = 0
    for season in charts.SEASONS:
        totals = pd.read_csv(
            DATA / f"{season}-zach-lavine-bulls-totals.csv").iloc[0]
        shots = pd.read_csv(DATA / f"{season}-zach-lavine-bulls-shots.csv")
        charts.reconcile_shots(season, totals, shots)
        located, _ = charts.located_shots(season, shots)
        charts.assert_source_family_reconciliation(season, located)
        official += int(totals.FGA)
        drawn += len(located)
    tenure = summary[summary.window.eq(charts.TENURE_LABEL)].iloc[0]
    assert int(tenure.bulls_fga) == official == drawn == 7472
    assert int(tenure.points) == int(summary.iloc[:-1].points.sum()) == 10056
    assert int(tenure.unlocated_fga) == 0


def test_saved_zone_tables_are_complete_and_cover_each_mapped_attempt():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    splits = pd.read_csv(DATA / "zone-splits.csv")
    assert all(len(group) == 12 for _, group in splits.groupby("window"))
    for window, group in splits.groupby("window"):
        assert int(group.fga.sum()) == int(summary.loc[window, "mapped_zone_fga"])
        assert int(group.fga.sum() + group.subject_excluded_fga.iloc[0]) == int(
            summary.loc[window, "shot_rows"]
        )


def test_the_2024_25_slide_holds_only_his_chicago_games():
    """He was traded to Sacramento on 2025-02-03; those games are not here."""
    totals = pd.read_csv(DATA / "2024-25-zach-lavine-bulls-totals.csv").iloc[0]
    assert int(totals.GP) == 42 and int(totals.FGA) == 710
    # The label is the END-OF-SEASON team, not the filter: team_id-scoped
    # LeagueDashPlayerStats returns Chicago's line under "SAC". Same trap as
    # Hinrich's 2015-16 "ATL" row; the data is right and the label is not.
    assert totals.TEAM_ABBREVIATION == "SAC"


def test_every_season_clears_the_chart_floor():
    """All eight are drawn. The thinnest, 2017-18's ACL return, is 355 FGA."""
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    seasons = summary.loc[list(charts.SEASONS)]
    assert seasons.charted.all()
    assert seasons.bulls_fga.min() == 355 >= charts.CHART_MIN_SEASON_FGA


def test_the_cover_grid_is_three_wide_and_fits_the_page():
    from bulls.graphics import house

    plan = list(charts.GRID_ROW_PLAN)
    assert plan == [3, 3, 2] and sum(plan) == len(charts.SEASONS)
    s = shot_chart.zonegrid_scale(plan)
    court_w = 2 * shot_chart.COURT_HALF_WIDTH * s
    court_h = shot_chart.ZONEGRID_COURT_UNITS * s
    span = 3 * court_w + 2 * shot_chart.ZONEGRID_COL_GAP
    assert span < house.CANVAS_WIDTH
    label_block = (shot_chart.ZONEGRID_LABEL_GAP
                   + shot_chart.ZONEGRID_LABEL_SIZE * 2.08)
    cell_h = court_h + label_block + shot_chart.ZONEGRID_ROW_GAP
    bottom = (shot_chart.ZONEGRID_TOP - 2 * cell_h - court_h - label_block)
    assert bottom - 20 > 0, "bottom row's season label would be cropped away"


def test_the_cover_greys_the_same_zones_the_season_slides_grey():
    splits = pd.read_csv(DATA / "zone-splits.csv")
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    for window, group in splits.groupby("window"):
        fills = shot_chart._zone12_fills(group, shot_chart.ZONE12_DEFAULT_PALETTE)
        grey = sum(c == shot_chart.ZONE12_GREY for c in fills.values())
        assert grey == int(summary.loc[window, "zones_grey"])


def test_lavine_renders_in_the_default_tagged_style_and_five_pills_fit():
    """LaVine was the first post in the tagged look, now the house default."""
    assert shot_chart.ZONE12_DEFAULT_STYLE == "tagged"
    classic = shot_chart.ZONE12_STYLES["classic"]
    assert classic["reference"] == "LA" and classic["card_fill"] is None
    assert classic["summary_lift"] == 0
    tagged = shot_chart.ZONE12_STYLES["tagged"]
    assert tagged["reference"] == "NBA"
    assert tagged["card_fill"] == "#CE1141"
    # GP + PPG + FGA + eFG + 3PT sit inside the court's 80-1000 px span.
    assert 5 * 172 + 4 * 15 == 920
