"""Scope, reconciliation, and cover-layout checks for Hinrich's Bulls charts.

The reconciliation tests are the load-bearing ones. Every shot pull in this post
is scoped to one franchise, and a wrongly-scoped ShotChartDetail call returns an
empty frame rather than raising -- so "did we get the right shots" is a question
only an independent total can answer.
"""
from pathlib import Path

import pandas as pd
import pytest

from scripts import make_shot_chart as shot_chart
from scripts.prototypes import hinrich_bulls_zone_charts as charts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"


def test_scope_is_eleven_bulls_seasons_split_by_two_years_away():
    assert charts.PLAYER_ID == 2550
    assert charts.SEASONS == (
        "2003-04", "2004-05", "2005-06", "2006-07", "2007-08", "2008-09",
        "2009-10", "2012-13", "2013-14", "2014-15", "2015-16",
    )
    # Named rather than merely absent. The gap is a fact about his career, not a
    # fetch that came back short, and the caption has to be able to say so.
    assert charts.AWAY_SEASONS == ("2010-11", "2011-12")
    assert not set(charts.AWAY_SEASONS) & set(charts.SEASONS)


def test_tenure_floor_scales_with_included_seasons():
    """The same rule the Rose, DeRozan and Butler charts use, at eleven seasons.

    A pooled chart holding eleven times the attempts would clear a per-season
    floor in zones that carry only a season or two of real evidence, so the floor
    scales with the pool. Diverging here would make this post's grey mean
    something different from its three siblings' grey.
    """
    assert charts.SEASON_MIN_ZONE_FGA == 20
    assert charts.TENURE_MIN_ZONE_FGA == 20 * len(charts.SEASONS) == 220


def test_reconciliation_checks_attempts_and_makes():
    totals = pd.Series({"FGA": 3, "FGM": 2})
    shots = pd.DataFrame({"shot_made": [1, 0, 1]})
    charts.reconcile_shots("season", totals, shots)
    with pytest.raises(ValueError, match="shot rows"):
        charts.reconcile_shots("season", totals, shots.iloc[:2])
    with pytest.raises(ValueError, match="shot makes"):
        charts.reconcile_shots("season", totals, shots.assign(shot_made=0))


def test_only_completely_unlocated_rows_are_excluded():
    frame = pd.DataFrame({
        "loc_x": [1.0, None], "loc_y": [2.0, None],
        "shot_distance": [3.0, None], "shot_zone": ["Restricted Area", None],
        "shot_zone_area": ["Center(C)", None],
    })
    located, excluded = charts.located_shots("label", frame)
    assert len(located) == 1
    assert excluded == 1

    partial = frame.copy()
    partial.loc[1, "loc_x"] = 1.0
    with pytest.raises(ValueError, match="partially missing"):
        charts.located_shots("label", partial)


def test_saved_data_reconstructs_every_page_and_tenure_total():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv")
    assert summary.window.tolist() == [*charts.SEASONS, charts.TENURE_LABEL]
    assert summary.min_zone_fga.tolist() == [20] * len(charts.SEASONS) + [220]
    # Compared with a tolerance rather than by re-rounding. Python's round() and
    # numpy's disagree on an exact .05 boundary -- 2012-13's 459/60 = 7.65 stores
    # as 7.7 and re-rounds to 7.6 -- and that is a rounding-rule difference, not
    # the thing this test is for, which is that PPG really is points over games.
    assert ((summary.ppg - summary.points / summary.games).abs() <= 0.05).all()
    official = drawn = 0
    for season in charts.SEASONS:
        totals = pd.read_csv(
            DATA / f"{season}-kirk-hinrich-bulls-totals.csv").iloc[0]
        shots = pd.read_csv(DATA / f"{season}-kirk-hinrich-bulls-shots.csv")
        charts.reconcile_shots(season, totals, shots)
        located, _ = charts.located_shots(season, shots)
        charts.assert_source_family_reconciliation(season, located)
        official += int(totals.FGA)
        drawn += len(located)
    tenure = summary[summary.window.eq(charts.TENURE_LABEL)].iloc[0]
    assert int(tenure.bulls_fga) == official
    assert int(tenure.shot_rows) == drawn
    assert int(tenure.points) == int(summary.iloc[:-1].points.sum())
    # Two attempts across eleven seasons carry no location at all, so the drawn
    # count is allowed to fall short of the official one -- by exactly that much
    # and no more. Without this the two numbers could drift apart unnoticed.
    assert official - drawn == int(tenure.unlocated_fga) == 2


def test_saved_zone_tables_are_complete_and_cover_each_mapped_attempt():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    splits = pd.read_csv(DATA / "zone-splits.csv")
    assert all(len(group) == 12 for _, group in splits.groupby("window"))
    for window, group in splits.groupby("window"):
        assert int(group.fga.sum()) == int(summary.loc[window, "mapped_zone_fga"])
        assert int(group.fga.sum() + group.subject_excluded_fga.iloc[0]) == int(
            summary.loc[window, "shot_rows"]
        )


def test_the_2015_16_slide_holds_only_his_chicago_half():
    """He was traded to Atlanta in February 2016; those 11 games are not here."""
    totals = pd.read_csv(DATA / "2015-16-kirk-hinrich-bulls-totals.csv").iloc[0]
    # The numbers are the Chicago half: 35 games and 118 attempts, against the 11
    # and 11 he added in Atlanta. Those are what the slide is built from.
    assert int(totals.GP) == 35 and int(totals.FGA) == 118
    # TEAM_ABBREVIATION is NOT. LeagueDashPlayerStats filtered by team_id returns
    # the club's numbers under the player's END-OF-SEASON team label, so this row
    # reads "ATL" while carrying Chicago's line. Pinned here because the trap runs
    # the dangerous way: the label looks wrong on data that is right, and
    # "correcting" it would break a correct chart.
    assert totals.TEAM_ABBREVIATION == "ATL"
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    assert int(summary.loc["2015-16", "bulls_fga"]) == 118
    # Almost every zone is under the floor at 118 attempts, which is the point:
    # the slide shows an end-of-career sample too thin to rate, rather than
    # rating it anyway.
    assert int(summary.loc["2015-16", "zones_grey"]) == 10


# --- the cover -------------------------------------------------------------
def _grid_geometry(count: int):
    """Where render_zonegrid would place `count` courts, without drawing them."""
    s = shot_chart.ZONEGRID_SCALE
    court_h = shot_chart.ZONEGRID_COURT_UNITS * s
    court_w = 2 * shot_chart.COURT_HALF_WIDTH * s
    label_block = (shot_chart.ZONEGRID_LABEL_GAP
                   + shot_chart.ZONEGRID_LABEL_SIZE * 2.08
                   + shot_chart.ZONEGRID_COUNT_GAP)
    cell_h = court_h + label_block + shot_chart.ZONEGRID_ROW_GAP
    pitch = court_w + shot_chart.ZONEGRID_COL_GAP
    rows = -(-count // shot_chart.ZONEGRID_COLS)
    return court_w, court_h, cell_h, pitch, label_block, rows


def test_the_cover_grid_fits_the_page_at_eleven_seasons():
    """Eleven courts have to fit 1080 x 1350 with their labels attached.

    Solved arithmetically rather than by eye, because the failure is silent: an
    over-tall grid does not error, it crops the bottom row's attempt count off
    the asset, and the asset still looks finished.
    """
    from bulls.graphics import house

    court_w, court_h, cell_h, pitch, label_block, rows = _grid_geometry(11)
    assert rows == 4
    widest = 3 * court_w + 2 * shot_chart.ZONEGRID_COL_GAP
    assert widest < house.CANVAS_WIDTH
    # The crop, not the content, is what has to fit: the renderer pads 20 units
    # below the last attempt count and 18 above the first court, and matplotlib
    # silently clamps a crop that runs off the canvas rather than raising.
    bottom = (shot_chart.ZONEGRID_TOP - (rows - 1) * cell_h - court_h
              - label_block)
    assert bottom - 20 > 0, "bottom row's attempt count would be cropped away"
    assert shot_chart.ZONEGRID_TOP + 18 < house.CANVAS_HEIGHT


def test_a_short_last_row_is_centred_not_left_hung():
    """Two courts under three read as a missing season unless they are centred."""
    from bulls.graphics import house

    court_w, _, _, pitch, _, _ = _grid_geometry(11)
    # Row 3 of Hinrich's grid holds 2003-04..2015-16's final pair.
    in_row = 2
    span = (in_row - 1) * pitch
    centres = [house.CANVAS_WIDTH / 2 - span / 2 + col * pitch
               for col in range(in_row)]
    assert sum(centres) / in_row == pytest.approx(house.CANVAS_WIDTH / 2)
    assert min(centres) - court_w / 2 > 0
    assert max(centres) + court_w / 2 < house.CANVAS_WIDTH


def test_the_cover_greys_the_same_zones_the_season_slides_grey():
    """One rule, two renderers. The cover is a summary, never a second opinion."""
    splits = pd.read_csv(DATA / "zone-splits.csv")
    season_rows = splits[splits.window.ne(charts.TENURE_LABEL)]
    fills = {
        window: shot_chart._zone12_fills(group, shot_chart.ZONE12_DEFAULT_PALETTE)
        for window, group in season_rows.groupby("window")
    }
    grey = {w: sum(c == shot_chart.ZONE12_GREY for c in f.values())
            for w, f in fills.items()}
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    for window, count in grey.items():
        assert count == int(summary.loc[window, "zones_grey"])
