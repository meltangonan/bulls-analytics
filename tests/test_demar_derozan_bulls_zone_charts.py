"""Coverage, pooling, and saved-data checks for DeRozan's Bulls tenure."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bulls.graphics.court import nba_to_basket_bottom_px
from scripts.prototypes import demar_derozan_bulls_zone_charts as charts
from scripts import make_shot_chart as shot_chart


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
    assert all(len(group) == 13 for _, group in baselines.groupby("window"))
    for _, group in splits.groupby("window"):
        excluded = int(group.subject_excluded_fga.iloc[0])
        assert group.fga.sum() + excluded == {
            "2021-22": 1535,
            "2022-23": 1303,
            "2023-24": 1355,
            "Bulls tenure": 4193,
        }[group.window.iloc[0]]
    for _, group in baselines.groupby("window"):
        assert group.fga_share_pct.sum() == pytest.approx(100.0, abs=0.001)


def test_2021_22_corner_counts_follow_nba_labels_and_basket_bottom_display():
    """The published reversal that prompted the global orientation repair."""
    splits = pd.read_csv(DATA / "zone-splits.csv")
    corners = splits[
        splits.window.eq("2021-22")
        & splits.zone.isin(["Left Corner 3", "Right Corner 3"])
    ].set_index("zone")

    assert (int(corners.loc["Left Corner 3", "fgm"]),
            int(corners.loc["Left Corner 3", "fga"])) == (11, 29)
    assert (int(corners.loc["Right Corner 3", "fgm"]),
            int(corners.loc["Right Corner 3", "fga"])) == (7, 28)

    def display_x(zone):
        x, y = shot_chart.ZONE12_ANCHORS[zone]
        return nba_to_basket_bottom_px(0.0, 0.0, 1.0, x, y)[0]

    assert display_x("Left Corner 3") > 250.0
    assert display_x("Right Corner 3") < 250.0


def test_2021_22_physical_paint_matches_nba_labels_before_custom_angle_split():
    shots = pd.read_csv(DATA / "2021-22-demar-derozan-bulls-shots.csv")
    zones = pd.Series(charts.sm.zone12_of_shots(shots))

    assert int(zones.eq("Restricted Area").sum()) == 293
    assert int(zones.eq("In The Paint (Non-RA)").sum()) == 359
    assert int(zones.isin(["Restricted Area", "In The Paint (Non-RA)"]).sum()) == 652
    assert int(zones.eq("Backcourt").sum()) == 4


@pytest.mark.parametrize("season", charts.SEASONS)
def test_custom_zones_reconcile_to_every_nba_basic_physical_family(season):
    """Custom rays may subdivide a family; they may never move a shot between families."""
    shots = pd.read_csv(DATA / f"{season}-demar-derozan-bulls-shots.csv")
    custom = pd.Series(charts.sm.zone12_of_shots(shots), index=shots.index)
    family = custom.replace({
        "Left Baseline": "Mid-Range",
        "Left Mid-Range": "Mid-Range",
        "Center Mid-Range": "Mid-Range",
        "Right Mid-Range": "Mid-Range",
        "Right Baseline": "Mid-Range",
        "Left Wing 3": "Above the Break 3",
        "Top of Key 3": "Above the Break 3",
        "Right Wing 3": "Above the Break 3",
    })

    assert family.value_counts().sort_index().to_dict() == (
        shots.shot_zone.value_counts().sort_index().to_dict()
    )


def test_the_nineteen_disputed_2021_22_attempts_are_nba_mid_range():
    """The old 142.5 cutoff wrongly absorbed these y=139..142 rows into paint."""
    shots = pd.read_csv(DATA / "2021-22-demar-derozan-bulls-shots.csv")
    old_paint = (
        shots.loc_x.abs().le(80)
        & shots.loc_y.le(142.5)
        & np.hypot(shots.loc_x, shots.loc_y).gt(40)
    )
    disputed = shots[old_paint & shots.shot_zone.eq("Mid-Range")]

    assert len(disputed) == 19
    assert disputed.loc_y.min() == 139
    assert disputed.loc_y.max() == 142


@pytest.mark.parametrize("season", charts.SEASONS)
def test_custom_sectors_never_cross_the_centre_line_nba_drew(season):
    """Our rays may sit at different angles than NBA's; they may not change side.

    The family reconciliation test above cannot see a left/right swap -- mid-range
    still totals 741 with its two wings exchanged, and only the pair of numbers
    printed in each half would move. NBA's own ``shot_zone_area`` is an
    independent angular labelling of the same shots, so it is the check that can
    see it: a shot NBA puts on the Left Side or Left Side Center must never land
    in a zone we name Right, or the reverse. Disagreement between *neighbouring*
    sectors is expected and allowed -- the cut angles differ deliberately.
    """
    shots = pd.read_csv(DATA / f"{season}-demar-derozan-bulls-shots.csv")
    ours = pd.Series(charts.sm.zone12_of_shots(shots), index=shots.index)
    area = shots.shot_zone_area

    nba_left = area.isin(["Left Side(L)", "Left Side Center(LC)"])
    nba_right = area.isin(["Right Side(R)", "Right Side Center(RC)"])
    ours_left = ours.str.startswith("Left ")
    ours_right = ours.str.startswith("Right ")

    assert int((nba_left & ours_right).sum()) == 0
    assert int((nba_right & ours_left).sum()) == 0
    # And the check is not vacuous: both sides carry real volume.
    assert int((nba_left & ours_left).sum()) > 100
    assert int((nba_right & ours_right).sum()) > 100
