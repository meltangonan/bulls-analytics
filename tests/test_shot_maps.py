"""Tests for the shared shot-map analysis layer.

Covers the two things every chart in the family depends on: the density method
(normalisation, the player-minus-league difference, off-court masking) and the
zone method (relative volume and efficiency, plus the noise guard).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bulls.analysis import shot_maps as sm


def _grid_shape():
    xe, ye = sm.edges()
    return len(xe) - 1, len(ye) - 1


def _shots(rows):
    """rows: (loc_x, loc_y, distance, made, type)"""
    return pd.DataFrame(rows, columns=["loc_x", "loc_y", "shot_distance",
                                       "shot_made", "shot_type"])


# --- density ---------------------------------------------------------------
def test_density_is_a_normalized_distribution():
    df = pd.DataFrame({"loc_x": [0, 10, -20, 40], "loc_y": [0, 50, 100, 20]})
    grid = sm.density(df)
    assert grid.shape == _grid_shape()
    assert grid.sum() == pytest.approx(1.0)


def test_density_of_no_shots_is_zero_not_nan():
    grid = sm.density(pd.DataFrame({"loc_x": [], "loc_y": []}))
    assert grid.sum() == 0.0
    assert not np.isnan(grid).any()


def test_normalization_makes_volume_irrelevant():
    """A player who shoots twice as much from the same spots has the same map.

    This is the property that lets a 262-attempt player and a 963-attempt player
    sit on the same grid: density encodes shot *diet*, not playing time.
    """
    few = pd.DataFrame({"loc_x": [0, 100, -100], "loc_y": [10, 120, 120]})
    many = pd.concat([few] * 4, ignore_index=True)
    assert np.allclose(sm.density(few), sm.density(many))


def test_signed_diff_signs_track_over_and_under_indexing():
    nx, ny = _grid_shape()
    league = np.full((nx, ny), 1.0 / (nx * ny))
    player = league.copy()
    player[40, 60] += 0.5
    player[41, 60] -= 0.5
    diff = sm.signed_diff(player, league)
    assert diff[40, 60] > 0
    assert diff[41, 60] < 0


def test_signed_diff_masks_at_and_below_the_baseline():
    _, ye = sm.edges()
    centres = (ye[:-1] + ye[1:]) / 2.0
    below = int(np.argmax(centres <= sm.BASELINE_Y))
    above = int(np.argmax(centres > 0))
    nx, ny = _grid_shape()
    league = np.full((nx, ny), 1.0 / (nx * ny))
    player = league.copy()
    player[40, below] += 0.5
    player[40, above] += 0.5
    diff = sm.signed_diff(player, league)
    assert diff[40, below] == 0.0
    assert diff[40, above] > 0.0


def test_within_range_drops_only_beyond_the_limit():
    df = pd.DataFrame({"shot_distance": [0, sm.MAX_DIST_FT, sm.MAX_DIST_FT + 1, 60]})
    assert sm.within_range(df)["shot_distance"].tolist() == [0, sm.MAX_DIST_FT]


def test_grid_reaches_past_the_three_point_line():
    assert sm.GRID_Y[1] >= 260  # arc tops out at 237.5 (23.75 ft)


# --- zones -----------------------------------------------------------------
def test_zone_masks_partition_every_shot_exactly_once():
    df = _shots([
        (0, 5, 1.0, 1, "2PT"), (0, 60, 6.0, 0, "2PT"),
        (0, 150, 16.0, 1, "2PT"), (0, 260, 26.0, 0, "3PT"),
    ])
    masks = sm.zone_masks(df)
    stacked = np.vstack([m.to_numpy() for m in masks.values()])
    assert stacked.sum(axis=0).tolist() == [1, 1, 1, 1]
    assert set(masks) == set(sm.ZONE_ORDER)


def test_zone_split_reports_both_dimensions_against_the_league():
    player = _shots([(0, 5, 1.0, 1, "2PT")] * 8 + [(0, 5, 1.0, 0, "2PT")] * 2)
    league = _shots([(0, 5, 1.0, 1, "2PT")] * 5 + [(0, 5, 1.0, 0, "2PT")] * 5)
    out = sm.zone_split(player, league, player_poss=100, league_poss=1000)
    row = out[out.zone == "RIM"].iloc[0]

    assert row.fga == 10 and row.fgm == 8
    assert row.fg == pytest.approx(0.8)
    assert row.fg_rel == pytest.approx(30.0)      # 80% vs a 50% league
    assert row.per75 == pytest.approx(7.5)        # 10 shots / 100 poss * 75
    assert row.lg_per75 == pytest.approx(0.75)
    assert row.vol_rel == pytest.approx(900.0)    # ten times the league rate


def test_zone_split_keeps_zone_order():
    df = _shots([(0, 5, 1.0, 1, "2PT"), (0, 60, 6.0, 0, "2PT"),
                 (0, 150, 16.0, 1, "2PT"), (0, 260, 26.0, 0, "3PT")])
    out = sm.zone_split(df, df, player_poss=100, league_poss=100)
    assert out.zone.tolist() == list(sm.ZONE_ORDER)


def test_three_pointers_are_zoned_by_type_not_distance():
    """A corner three is only ~22 ft, so distance alone would misfile it."""
    corner_three = _shots([(220, 20, 22.0, 1, "3PT")])
    assert sm.zone_masks(corner_three)["THREE"].all()
    assert not sm.zone_masks(corner_three)["LONG MID"].any()


# --- noise guard -----------------------------------------------------------
def test_separable_rejects_a_hot_looking_small_sample():
    # 16/29 = 55.2% against a 38.6% league looks huge, but 29 attempts cannot
    # carry it -- this is the real right-corner case from a live chart.
    assert not sm.separable(16, 29, 0.386)


def test_separable_accepts_a_gap_the_sample_supports():
    # 22/36 = 61.1% against 38.7% clears the interval even at 36 attempts.
    assert sm.separable(22, 36, 0.387)


def test_separable_needs_attempts():
    assert not sm.separable(0, 0, 0.4)


# --- polar cells -----------------------------------------------------------
def test_sector_index_counts_from_the_viewers_left():
    # Straight out to the left, straight ahead, straight out to the right.
    idx = sm.sector_index([-200, 0, 200], [1, 200, 1], 3)
    assert list(idx) == [0, 1, 2]


def test_sector_index_puts_behind_the_hoop_shots_in_the_outer_sectors():
    """A shot from behind the baseline has no meaningful angle.

    ``sector_index`` clamps its y to zero, which files it in the nearest
    outermost sector -- and the renderer extends exactly those two wedges below
    the hoop line so the drawn area matches.
    """
    idx = sm.sector_index([-100, 100], [-30, -30], 5)
    assert list(idx) == [0, 4]


def test_polar_cells_change_sector_count_only_at_the_arc():
    cells = sm.polar_cells()
    counts = {c["band"]: c["n_sectors"] for c in cells}
    assert counts["0-4 FT"] == 1
    assert all(counts[f"{a:.0f}-{b:.0f} FT"] == sm.INNER_SECTORS
               for a, b in zip(sm.POLAR_BANDS[1:-1], sm.POLAR_BANDS[2:]))
    assert counts["3PT"] == sm.THREE_SECTORS


def test_polar_cells_tile_the_court_without_overlap():
    """Every shot lands in exactly one cell -- the property the chart rests on."""
    rng = np.random.default_rng(7)
    x = rng.uniform(-249, 249, 400)
    y = rng.uniform(-40, 280, 400)
    d = np.hypot(x, y) / 10
    df = _shots([(x[i], y[i], d[i], i % 2, "3PT" if d[i] >= 23.75 else "2PT")
                 for i in range(len(x))])
    df = df[df.shot_distance <= sm.THREE_MAX_FT]
    hits = np.zeros(len(df), dtype=int)
    for cell in sm.polar_cells():
        hits += sm._cell_mask(df, cell).to_numpy().astype(int)
    assert set(np.unique(hits)) == {1}


def test_polar_split_flags_thin_cells_as_unrated():
    league = _shots([(0, 60, 6.0, 1, "2PT")] * 200)
    player = _shots([(0, 60, 6.0, 1, "2PT")] * 3)
    row = sm.polar_split(player, league).set_index("key").loc["1-1"]
    assert row.fga == 3
    assert not row.rated


def test_polar_split_rates_a_cell_that_clears_the_floor():
    league = _shots([(0, 60, 6.0, 1, "2PT")] * 100
                    + [(0, 60, 6.0, 0, "2PT")] * 100)
    player = _shots([(0, 60, 6.0, 1, "2PT")] * sm.MIN_CELL_FGA)
    row = sm.polar_split(player, league).set_index("key").loc["1-1"]
    assert row.rated
    assert row.fg == pytest.approx(1.0)
    assert row.fg_rel == pytest.approx(50.0)      # 100% against a 50% league


def test_polar_split_files_a_corner_three_by_shot_type_not_radius():
    """22 ft in the corner is inside the arc's radius but is still a three."""
    corner = _shots([(230, 20, 22.0, 1, "3PT")])
    league = _shots([(230, 20, 22.0, 0, "3PT")] * 50)
    split = sm.polar_split(corner, league).set_index("key")
    assert split.loc["3PT-4", "fga"] == 1
    assert split.loc["3-2", "fga"] == 0            # not the 12-16 ft right cell


# --- distance ladder -------------------------------------------------------
def _ring(dist, made, kind="2PT", n=1, x=0):
    return [(x, dist * 10, dist, made, kind)] * n


def _corner(dist, made, n=1):
    """Attempts out beyond the corner line, where only threes exist."""
    return [(230, 40, dist, made, "3PT")] * n


def test_points_counts_the_extra_point_beyond_the_arc():
    df = _shots(_ring(25.0, 1, "3PT") + _ring(5.0, 1) + _ring(5.0, 0))
    assert list(sm._points(df)) == [3.0, 2.0, 0.0]


def test_distance_ladder_covers_the_range_once():
    lad = sm.distance_ladder(_shots(_ring(5.0, 1)))
    assert len(lad) == int(sm.LADDER_MAX_FT / sm.LADDER_STEP_FT)
    assert lad.lo.iloc[0] == 0.0 and lad.hi.iloc[-1] == pytest.approx(sm.LADDER_MAX_FT)
    assert lad.fga.sum() == 1


def test_distance_ladder_pps_beats_fg_for_comparing_across_the_arc():
    """A 35% three and a 52.5% two are the same 1.05 points per shot.

    This is the reason the chart encodes PPS: on FG% the three looks far worse,
    and the whole 'is this shot worth taking' question gets the wrong answer.
    """
    threes = _shots(_ring(25.0, 1, "3PT", 35) + _ring(25.0, 0, "3PT", 65))
    twos = _shots(_ring(5.0, 1, "2PT", 525) + _ring(5.0, 0, "2PT", 475))
    lad_3 = sm.distance_ladder(threes).set_index("lo").loc[24.0]
    lad_2 = sm.distance_ladder(twos).set_index("lo").loc[4.0]
    assert lad_3.pps == pytest.approx(lad_2.pps, abs=0.01)
    assert lad_3.fg < lad_2.fg - 0.15


def test_distance_ladder_flags_thin_rings():
    lad = sm.distance_ladder(_shots(_ring(5.0, 1, "2PT", sm.MIN_RING_FGA - 1)))
    assert not lad.set_index("lo").loc[4.0, "rated"]


def test_distance_ladder_rates_a_ring_that_clears_the_floor():
    lad = sm.distance_ladder(_shots(_ring(5.0, 1, "2PT", sm.MIN_RING_FGA)))
    assert lad.set_index("lo").loc[4.0, "rated"]


def test_distance_ladder_measures_each_ring_against_the_same_ring():
    """The league baseline must be distance-matched, not a single global number."""
    team = _shots(_ring(5.0, 1, "2PT", 50) + _ring(5.0, 0, "2PT", 50))
    league = _shots(_ring(5.0, 1, "2PT", 40) + _ring(5.0, 0, "2PT", 60)
                    + _ring(25.0, 1, "3PT", 90))
    row = sm.distance_ladder(team, league).set_index("lo").loc[4.0]
    assert row.fg == pytest.approx(0.50)
    assert row.lg_fg == pytest.approx(0.40)       # the 5 ft ring, not all shots
    assert row.fg_rel == pytest.approx(10.0)


def test_distance_ladder_counts_twos_inside_the_split_and_threes_outside():
    """The split is the whole method, and mixing the two destroys the finding.

    At 22-23 ft a corner three and a long two sit at the same radius but are
    worth wildly different amounts. Binning by distance alone lets the threes
    drag that ring up toward ~1.15 points per shot, so the value curve rises
    smoothly into the arc and the cliff the chart exists to show disappears.
    """
    mixed = _shots(_ring(22.4, 1, "3PT", 90) + _ring(22.4, 0, "2PT", 30))
    lad = sm.distance_ladder(mixed).set_index("lo")
    assert lad.loc[22.0, "fga"] == 30            # the long twos only
    assert lad.loc[22.0, "pps"] == 0.0           # every one of which missed
    assert not lad.loc[22.0, "three"]


def test_distance_ladder_rings_beyond_the_split_hold_threes_only():
    beyond = _shots(_ring(25.5, 1, "3PT", 40) + _ring(25.5, 1, "2PT", 5))
    row = sm.distance_ladder(beyond).set_index("lo").loc[24.0]
    assert row.fga == 40 and row.three
    assert row.pps == pytest.approx(3.0)


def test_ladder_coverage_keeps_corner_threes_rather_than_dropping_them():
    """Corner threes belong to the pocket, not to the excluded pile.

    The reference card drops them, which costs it 22% of all threes and paints
    the corner with the above-the-break value. Carving the pocket out keeps
    them, and coverage should show it.
    """
    shots = _shots(_corner(22.4, 1, 22) + _ring(26.0, 1, "3PT", 78)
                   + _ring(5.0, 1, "2PT", 100))
    cover = sm.ladder_coverage(shots)
    assert cover["corner_threes"] == 22
    assert cover["stray_threes"] == 0
    assert cover["excluded"] == 0


def test_ladder_coverage_flags_shots_past_the_outer_edge():
    cover = sm.ladder_coverage(_shots(_ring(34.0, 0, "3PT", 3)
                                      + _ring(26.0, 1, "3PT", 97)))
    assert cover["beyond_range"] == 3


def test_corner_pocket_is_carved_out_of_the_two_point_rings():
    """A corner three must never be counted as a long two at the same radius."""
    shots = _shots(_corner(22.4, 1, 40) + _ring(22.4, 0, "2PT", 10, x=100))
    lad = sm.distance_ladder(shots).set_index("lo")
    assert lad.loc[22.0, "fga"] == 10          # only the true long twos
    corner = sm.corner_split(shots)
    assert corner["fga"] == 40
    assert corner["pps"] == pytest.approx(3.0)


def test_corner_split_measures_against_the_leagues_own_corner():
    league = _shots(_corner(22.5, 1, 40) + _corner(22.5, 0, 60))
    team = _shots(_corner(22.5, 1, 50) + _corner(22.5, 0, 50))
    row = sm.corner_split(team, league)
    assert row["fg"] == pytest.approx(0.50)
    assert row["lg_fg"] == pytest.approx(0.40)
    assert row["fg_rel"] == pytest.approx(10.0)
    assert row["pps_rel"] == pytest.approx(0.30)


def test_corner_mask_ignores_threes_inside_the_corner_line():
    """An above-the-break three is not a corner three however short it reads."""
    above = _shots(_ring(23.8, 1, "3PT", 5, x=100))
    assert not sm.corner_mask(above).any()


def test_distance_ladder_leaves_an_empty_ring_blank_not_zero():
    """An unshot ring must not read as 0.00 points per shot."""
    row = sm.distance_ladder(_shots(_ring(5.0, 1))).set_index("lo").loc[18.0]
    assert row.fga == 0
    assert np.isnan(row.pps) and np.isnan(row.fg)


def test_ladder_edges_never_overshoot_the_outer_limit():
    """The outer edge is a hard limit, not a rounding target.

    At 2 ft wide a naive range would run 30-32 ft and silently readmit the
    heaves the limit exists to exclude, while the coverage line kept claiming
    they were shown.
    """
    for step in (1.0, 2.0, 4.0):
        edges = sm.ladder_edges(step, max_ft=30.0)
        assert edges[0] == 0.0
        assert edges[-1] <= 30.0
        assert np.allclose(np.diff(edges), step)


def test_ladder_edges_snap_down_when_the_width_does_not_divide():
    edges = sm.ladder_edges(4.0, max_ft=30.0)
    assert edges[-1] == 28.0


def test_default_bands_are_two_feet_and_split_cleanly_at_the_arc():
    """2 ft must divide both the outer limit and the 2PT/3PT split radius.

    If it did not, a band would straddle the split and hold twos and threes at
    once -- the exact mixing the split exists to prevent.
    """
    assert sm.LADDER_STEP_FT == 2.0
    assert sm.LADDER_MAX_FT % sm.LADDER_STEP_FT == 0
    assert sm.LADDER_TWO_MAX_FT % sm.LADDER_STEP_FT == 0
    lad = sm.distance_ladder(_shots(_ring(5.0, 1, "2PT", 50)))
    assert sm.LADDER_TWO_MAX_FT in set(lad.lo)      # a band starts exactly at the split
