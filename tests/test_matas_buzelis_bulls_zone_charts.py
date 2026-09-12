"""Coverage, pooling, and saved-data checks for Buzelis's Bulls tenure."""
from pathlib import Path

import pandas as pd
import pytest

from bulls.graphics.court import nba_to_basket_bottom_px
from scripts.prototypes import matas_buzelis_bulls_zone_charts as charts
from scripts import make_shot_chart as shot_chart


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"

# Official Chicago regular-season FGA, the figure every saved log must reproduce.
SEASON_FGA = {"2024-25": 555, "2025-26": 963}
TENURE_FGA = 1518


def test_scope_is_exactly_buzelis_two_bulls_seasons():
    assert charts.PLAYER_ID == 1641824
    assert charts.SEASONS == ("2024-25", "2025-26")


def test_tenure_floor_is_twice_the_season_floor():
    assert charts.SEASON_MIN_ZONE_FGA == 20
    assert charts.TENURE_MIN_ZONE_FGA == 40


def test_shot_rows_must_reconcile_to_official_bulls_fga():
    totals = pd.Series({"FGA": 3})
    shots = pd.DataFrame({"shot_made": [1, 0, 1]})
    charts.reconcile_shot_count("2024-25", totals, shots)
    with pytest.raises(ValueError, match="shot rows 2 != Bulls FGA 3"):
        charts.reconcile_shot_count("2024-25", totals, shots.iloc[:2])


def test_tenure_totals_add_the_two_nonoverlapping_seasons():
    rows = [
        pd.Series({"GP": 80, "MIN": 1511.3, "PTS": 688, "FGA": 555}),
        pd.Series({"GP": 77, "MIN": 2248.2, "PTS": 1255, "FGA": 963}),
    ]
    total = charts.tenure_totals(rows)
    assert total.GP == 157
    assert total.PTS == 1943
    assert total.FGA == TENURE_FGA


def test_saved_data_reconstructs_every_page_and_pooled_total():
    summary = pd.read_csv(DATA / "zone-chart-summary.csv")
    assert summary.window.tolist() == [*charts.SEASONS, "Bulls tenure"]
    assert summary.min_zone_fga.tolist() == [20, 20, 40]

    season_fga = 0
    for season in charts.SEASONS:
        totals = pd.read_csv(DATA / f"{season}-matas-buzelis-bulls-totals.csv").iloc[0]
        shots = pd.read_csv(DATA / f"{season}-matas-buzelis-bulls-shots.csv")
        charts.reconcile_shot_count(season, totals, shots)
        assert len(shots) == SEASON_FGA[season]
        season_fga += len(shots)
    assert season_fga == TENURE_FGA
    tenure = summary[summary.window.eq("Bulls tenure")].iloc[0]
    assert int(tenure.bulls_fga) == season_fga
    assert int(tenure.shot_rows) == season_fga


def test_saved_zone_and_baseline_tables_are_complete():
    splits = pd.read_csv(DATA / "zone-splits.csv")
    baselines = pd.read_csv(DATA / "league-zone-baselines.csv")
    assert all(len(group) == 12 for _, group in splits.groupby("window"))
    assert all(len(group) == 13 for _, group in baselines.groupby("window"))
    expected = {**SEASON_FGA, "Bulls tenure": TENURE_FGA}
    for _, group in splits.groupby("window"):
        excluded = int(group.subject_excluded_fga.iloc[0])
        assert group.fga.sum() + excluded == expected[group.window.iloc[0]]
    for _, group in baselines.groupby("window"):
        assert group.fga_share_pct.sum() == pytest.approx(100.0, abs=0.001)


def test_every_window_rates_the_same_seven_high_volume_zones():
    """The five grey zones are the mid-range, and that is the post's finding.

    Buzelis takes so few mid-range shots that no window clears the colour floor
    there. Guarding the rated set keeps a future data refresh from quietly
    turning the editorial claim -- rim and three, nothing between -- false.
    """
    splits = pd.read_csv(DATA / "zone-splits.csv")
    rated_everywhere = {
        "Restricted Area", "In The Paint (Non-RA)", "Left Corner 3",
        "Left Wing 3", "Top of Key 3", "Right Wing 3", "Right Corner 3",
    }
    for window, group in splits.groupby("window"):
        assert set(group[group.rated].zone) == rated_everywhere, window
        assert group[group.rated].fga.sum() / group.fga.sum() > 0.96, window


def test_custom_zones_never_move_a_shot_between_nba_physical_families():
    """Custom rays may subdivide a family; they may never move a shot across one."""
    collapse = {
        "Left Baseline": "Mid-Range",
        "Left Mid-Range": "Mid-Range",
        "Center Mid-Range": "Mid-Range",
        "Right Mid-Range": "Mid-Range",
        "Right Baseline": "Mid-Range",
        "Left Wing 3": "Above the Break 3",
        "Top of Key 3": "Above the Break 3",
        "Right Wing 3": "Above the Break 3",
    }
    for season in charts.SEASONS:
        shots = pd.read_csv(DATA / f"{season}-matas-buzelis-bulls-shots.csv")
        custom = pd.Series(charts.sm.zone12_of_shots(shots), index=shots.index)
        family = custom.replace(collapse)
        assert family.value_counts().sort_index().to_dict() == (
            shots.shot_zone.value_counts().sort_index().to_dict()
        ), season


def test_custom_sectors_never_cross_the_centre_line_nba_drew():
    """Guards the left/right swap that a family reconciliation cannot see.

    NBA's ``shot_zone_area`` is an independent angular labelling of the same
    shots, so a shot NBA puts on a Left side must never land in a zone we name
    Right. Neighbouring-sector disagreement is expected: the cut angles differ
    deliberately. This matters here because Buzelis's left/right split is the
    chart's sharpest claim.
    """
    for season in charts.SEASONS:
        shots = pd.read_csv(DATA / f"{season}-matas-buzelis-bulls-shots.csv")
        ours = pd.Series(charts.sm.zone12_of_shots(shots), index=shots.index)
        area = shots.shot_zone_area

        nba_left = area.isin(["Left Side(L)", "Left Side Center(LC)"])
        nba_right = area.isin(["Right Side(R)", "Right Side Center(RC)"])
        ours_left = ours.str.startswith("Left ")
        ours_right = ours.str.startswith("Right ")

        assert int((nba_left & ours_right).sum()) == 0, season
        assert int((nba_right & ours_left).sum()) == 0, season
        # And the check is not vacuous: both sides carry real volume.
        assert int((nba_left & ours_left).sum()) > 100, season
        assert int((nba_right & ours_right).sum()) > 100, season


def test_corner_zones_draw_on_the_basket_bottom_side_they_are_named_for():
    """The orientation repair that followed the published mirrored hot-spot post."""
    def display_x(zone):
        x, y = shot_chart.ZONE12_ANCHORS[zone]
        return nba_to_basket_bottom_px(0.0, 0.0, 1.0, x, y)[0]

    assert display_x("Left Corner 3") > 250.0
    assert display_x("Right Corner 3") < 250.0


# --- Merged mid-range variant ----------------------------------------------
# Buzelis's five mid-range sectors hold 17, 19 and 36 attempts, so all five sit
# under the colour floor in every window. Merging them buys one readable figure
# instead of five unreadable ones; it does not buy a colour.
MID = list(charts.sm.MID_ZONES)


def _splits(stem=""):
    return pd.read_csv(DATA / f"{stem}zone-splits.csv")


def test_merged_table_has_eight_zones_per_window():
    merged = _splits("merged-mid-")
    assert all(len(g) == 8 for _, g in merged.groupby("window"))
    assert all(set(g.zone) == set(charts.sm.ZONE8_ORDER)
               for _, g in merged.groupby("window"))


def test_merged_mid_range_is_the_pooled_sum_of_the_five_sectors():
    twelve, merged = _splits(), _splits("merged-mid-")
    for window, group in twelve.groupby("window"):
        mid = group[group.zone.isin(MID)]
        row = merged[merged.window.eq(window) & merged.zone.eq("Mid-Range")].iloc[0]
        assert int(row.fga) == int(mid.fga.sum()), window
        assert int(row.fgm) == int(mid.fgm.sum()), window
        # Attempt-weighted, not an average of five rates. The tolerance is the
        # saved tables' own 4-decimal float format, not a modelling allowance.
        assert row.fg == pytest.approx(mid.fgm.sum() / mid.fga.sum(), abs=1e-4), window


def test_merging_leaves_every_other_zone_untouched():
    """The merge must not disturb a zone it does not touch."""
    twelve, merged = _splits(), _splits("merged-mid-")
    keys = ["fga", "fgm", "fg", "lg_fg", "fg_rel", "fga_share_pct",
            "lg_fga_share_pct", "rated"]
    for window, group in twelve.groupby("window"):
        kept = group[~group.zone.isin(MID)].set_index("zone")
        after = merged[merged.window.eq(window)].set_index("zone")
        for zone in kept.index:
            for key in keys:
                assert after.loc[zone, key] == pytest.approx(
                    kept.loc[zone, key], abs=1e-4, nan_ok=True), (window, zone, key)


def test_pooling_the_mid_range_earns_no_exemption_from_the_colour_floor():
    """The editorial claim rests on this: even merged, it stays grey.

    All five sectors pooled over two entire seasons reach 36 attempts against a
    40-attempt pooled floor. If a data refresh ever pushes this over the line the
    post's framing changes, and this check is what surfaces that.
    """
    merged = _splits("merged-mid-")
    mid = merged[merged.zone.eq("Mid-Range")].set_index("window")
    assert not mid.rated.any()
    assert int(mid.loc["2024-25", "fga"]) == 17
    assert int(mid.loc["2025-26", "fga"]) == 19
    assert int(mid.loc["Bulls tenure", "fga"]) == 36


def test_merged_windows_still_reconcile_to_official_fga():
    merged = _splits("merged-mid-")
    expected = {**SEASON_FGA, "Bulls tenure": TENURE_FGA}
    for window, group in merged.groupby("window"):
        excluded = int(group.subject_excluded_fga.iloc[0])
        assert group.fga.sum() + excluded == expected[window]


def test_merged_mode_keeps_a_short_name_and_an_anchor_inside_the_band():
    """Position is the only thing attributing a pill to a zone, so it must exist."""
    assert shot_chart.ZONE12_SHORT["Mid-Range"] == "MID-RANGE"
    x, y = shot_chart.ZONE12_ANCHORS["Mid-Range"]
    assert charts.sm.zone_of(x, y) in MID


def test_merged_court_drops_only_the_internal_mid_range_seams():
    full = shot_chart._zone12_seam_segments(include_mid_cuts=True)
    merged = shot_chart._zone12_seam_segments(include_mid_cuts=False)
    assert len(merged) < len(full)
    # Every seam the merged court still draws is one the full court drew.
    assert set(map(tuple, merged)) < set(map(tuple, full))


# --- Summary cards ----------------------------------------------------------
def test_ppg_leads_the_summary_cards_and_comes_from_the_box_score():
    """PPG is the settled lead card on a player-tenure zone post.

    It cannot be derived from the shot log, which holds no free throws, so it
    must come from official points and games. This guards both halves: that the
    figure is present at all, and that it is the box-score one.
    """
    summary = pd.read_csv(DATA / "zone-chart-summary.csv")
    assert {"points", "ppg"} <= set(summary.columns)
    for row in summary.itertuples(index=False):
        assert row.ppg == pytest.approx(row.points / row.games, abs=0.05)
        # Free throws are why this exceeds anything the shot log could produce.
        assert row.points > 2 * row.fgm


def test_tenure_ppg_is_games_weighted_not_a_mean_of_seasons():
    """80 games at 8.6 and 77 at 16.3 is 12.4, not the 12.45 midpoint."""
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    seasons = summary.loc[list(charts.SEASONS)]
    tenure = summary.loc["Bulls tenure"]
    assert tenure.points == seasons.points.sum()
    assert tenure.games == seasons.games.sum()
    assert tenure.ppg == pytest.approx(
        seasons.points.sum() / seasons.games.sum(), abs=0.05)
    assert tenure.ppg != pytest.approx(seasons.ppg.mean(), abs=0.001)


def test_the_scoring_leap_between_the_two_seasons_is_real():
    """The post's headline pairs a near-doubled scoring rate with a flat diet."""
    summary = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    assert summary.loc["2024-25", "ppg"] == pytest.approx(8.6, abs=0.05)
    assert summary.loc["2025-26", "ppg"] == pytest.approx(16.3, abs=0.05)
