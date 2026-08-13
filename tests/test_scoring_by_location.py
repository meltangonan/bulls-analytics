"""Post-specific tests for the scoring-by-location zone graphic.

Two things carry the analytical claim and are worth pinning: the qualification
rule (best points per shot among a zone's attempt leaders, not best overall) and
the drawn zone geometry, which has to agree with the NBA labels the numbers are
grouped by — otherwise a face would sit in a zone it did not lead.

The NBA fetch path is not exercised here, and the layout is judged visually.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.prototypes.scoring_by_location import (
    ARC_R,
    BAND_R,
    BASELINE_Y,
    CORNER_X,
    CORNER_Y,
    FT_Y,
    MIN_FGA_CONFIDENT,
    PAINT_HALF,
    RA_R,
    MIN_ZONE_SHARE,
    ZONE_ORDER,
    CHIP_LAYOUT,
    COMPACT_ZONES,
    CORNER_TEXT_HALF,
    OFF_COURT_ZONES,
    SHORT_LABEL,
    select_leaders,
    zone_of,
)


def _row(zone, nba_id, name, fga, pps):
    return {
        "shot_zone": zone, "nba_id": nba_id, "name": name,
        "short": name.upper(), "fga": fga, "points": round(fga * pps),
        "pps": pps,
    }


def _table(rows_for_first_zone):
    """One populated zone plus a filler row for every other zone."""
    rows = list(rows_for_first_zone)
    for zone in ZONE_ORDER[1:]:
        rows.append(_row(zone, 99, "Filler", 50, 1.0))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Qualification rule
# ---------------------------------------------------------------------------
def test_leader_is_best_pps_among_players_who_clear_the_share():
    zone = ZONE_ORDER[0]
    table = _table([
        _row(zone, 1, "Volume", 300, 1.10),
        _row(zone, 2, "Efficient", 200, 1.40),   # 28% of the zone, best PPS
        _row(zone, 3, "Third", 200, 1.20),
    ])
    leader = next(x for x in select_leaders(table) if x.zone == zone)
    assert leader.name == "Efficient"
    assert leader.pps == pytest.approx(1.40)


def test_small_sample_below_the_share_cannot_win_a_zone():
    """The whole point of the gate: 2-for-2 does not beat a season of volume."""
    zone = ZONE_ORDER[0]
    table = _table([
        _row(zone, 1, "Volume", 300, 1.10),
        _row(zone, 2, "Second", 200, 1.05),
        _row(zone, 3, "Fluke", 2, 2.00),         # far below the share, so excluded
    ])
    leader = next(x for x in select_leaders(table) if x.zone == zone)
    assert leader.name == "Volume"


def test_the_share_scales_with_how_much_the_zone_is_used():
    """Ten attempts fails in a busy zone and passes in a quiet one — the point of
    using a share rather than a fixed floor or a rank."""
    busy = _table([
        _row(ZONE_ORDER[0], 1, "Heavy", 990, 1.00),
        _row(ZONE_ORDER[0], 2, "Light", 10, 2.00),
    ])
    assert next(x for x in select_leaders(busy) if x.zone == ZONE_ORDER[0]).name == "Heavy"

    quiet = _table([
        _row(ZONE_ORDER[0], 1, "Heavy", 30, 1.00),
        _row(ZONE_ORDER[0], 2, "Light", 10, 2.00),   # 25% of a thin zone, so it counts
    ])
    assert next(x for x in select_leaders(quiet) if x.zone == ZONE_ORDER[0]).name == "Light"


def test_a_rank_gate_would_have_admitted_what_the_share_rejects():
    """Guards the reason we moved off top-N: rank ignores how busy a zone is."""
    zone = ZONE_ORDER[0]
    table = _table([
        _row(zone, 1, "First", 26, 0.90),
        _row(zone, 2, "Second", 20, 0.95),
        _row(zone, 3, "ThirdByRank", 8, 1.50),   # top 3 by attempts, but only 13%
    ])
    leader = next(x for x in select_leaders(table) if x.zone == zone)
    assert leader.name != "ThirdByRank"
    assert leader.name == "Second"


def test_evenly_split_zone_falls_back_to_the_attempts_leader():
    """With ten equal shooters nobody clears 15%, and the zone still needs a face."""
    zone = ZONE_ORDER[0]
    rows = [_row(zone, i, f"P{i}", 10, 1.0 + i / 100) for i in range(1, 11)]
    rows.append(_row(zone, 99, "Most", 12, 0.5))
    leader = next(x for x in select_leaders(_table(rows)) if x.zone == zone)
    assert leader.name == "Most"
    assert leader.fga == 12


def test_share_threshold_is_a_fraction_not_a_count():
    assert 0 < MIN_ZONE_SHARE < 1


def test_pps_tie_breaks_toward_the_larger_sample():
    zone = ZONE_ORDER[0]
    table = _table([
        _row(zone, 1, "Bigger", 200, 1.25),
        _row(zone, 2, "Smaller", 60, 1.25),
        _row(zone, 3, "Third", 40, 1.00),
    ])
    leader = next(x for x in select_leaders(table) if x.zone == zone)
    assert leader.name == "Bigger"


def test_thin_leader_is_flagged_not_dropped():
    """A muted zone is still shown — the attempt count does the disclosure."""
    zone = ZONE_ORDER[0]
    table = _table([
        _row(zone, 1, "Thin", 4, 1.50),
        _row(zone, 2, "Thinner", 3, 1.00),
    ])
    leader = next(x for x in select_leaders(table) if x.zone == zone)
    assert leader.name == "Thin"
    assert leader.confident is False
    assert leader.fga < MIN_FGA_CONFIDENT


def test_team_total_counts_every_player_not_only_the_qualified():
    zone = ZONE_ORDER[0]
    table = _table([
        _row(zone, 1, "A", 100, 1.0),
        _row(zone, 2, "B", 50, 1.0),
        _row(zone, 3, "C", 30, 1.0),
        _row(zone, 4, "D", 20, 1.0),   # below the share, still team volume
    ])
    leader = next(x for x in select_leaders(table) if x.zone == zone)
    assert leader.team_fga == 200


def test_every_zone_gets_a_leader():
    table = _table([_row(ZONE_ORDER[0], 1, "A", 10, 1.0)])
    assert {x.zone for x in select_leaders(table)} == set(ZONE_ORDER)


# ---------------------------------------------------------------------------
# Drawn zone geometry, which must agree with NBA's labelling
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("x, y, expected", [
    (0, 0, "Restricted Area"),                       # the rim itself
    (0, RA_R - 1, "Restricted Area"),
    (0, RA_R + 1, "In The Paint (Non-RA)"),          # just past the restricted arc
    (PAINT_HALF - 1, FT_Y - 1, "In The Paint (Non-RA)"),
    (0, FT_Y + 10, "Center Mid-Range"),              # above the free-throw line
    (-CORNER_X - 10, 0, "Left Corner 3"),
    (CORNER_X + 10, 0, "Right Corner 3"),
    (0, ARC_R + 10, "Top of Key 3"),
])
def test_zone_of_known_landmarks(x, y, expected):
    assert zone_of(np.array([x]), np.array([y]))[0] == expected


def test_left_means_negative_x_on_screen():
    """NBA's 'Left' is screen-left in these coordinates; a flip would mislabel faces."""
    assert zone_of(np.array([-240.0]), np.array([10.0]))[0] == "Left Corner 3"
    assert zone_of(np.array([-200.0]), np.array([220.0]))[0] == "Left Wing 3"


def test_a_bearing_keeps_its_zone_at_every_distance():
    """The whole point of the five-sector split: no stepped border.

    NBA's own scheme changes sector count at 16 ft, so one bearing would land in
    Left Baseline inside and Left Mid-Range outside, drawing a tent. Ours must not.
    """
    bearing = np.radians(126.0)
    # From just clear of the key out to the arc — inside that, it is paint.
    for radius in (BAND_R - 15, BAND_R - 1, BAND_R + 1, BAND_R + 40, ARC_R - 5):
        zone = zone_of(np.array([radius * np.cos(bearing)]),
                       np.array([radius * np.sin(bearing)]))[0]
        assert zone == "Left Mid-Range", (radius, zone)


def test_every_mid_range_border_is_a_single_ray():
    """Walk each divider bearing outward; the zone either side must never swap.

    None of the four sit where NBA puts them. The baseline cuts run from the hoop
    through the corner break, where the arc meets the straight corner line, so
    each continues a mark the floor already carries. The two central cuts split
    what is left evenly, which measured flatter than NBA's 72/108 on both zone
    area and league shot volume. The same two rays continue past the arc as the
    above-the-break dividers, so every divider is one unbroken line.
    """
    from bulls.analysis.shot_maps import MID_SECTOR_CUTS

    lower, mid_low, mid_high, upper = MID_SECTOR_CUTS
    for cut, inner_zone, outer_zone in [
        (lower, "Right Baseline", "Right Mid-Range"),
        (mid_low, "Right Mid-Range", "Center Mid-Range"),
        (mid_high, "Center Mid-Range", "Left Mid-Range"),
        (upper, "Left Mid-Range", "Left Baseline"),
    ]:
        for radius in np.arange(PAINT_HALF + 25, ARC_R - 5, 10.0):
            below = np.radians(cut - 4)
            above = np.radians(cut + 4)
            a = zone_of(np.array([radius * np.cos(below)]), np.array([radius * np.sin(below)]))[0]
            b = zone_of(np.array([radius * np.cos(above)]), np.array([radius * np.sin(above)]))[0]
            if a in (inner_zone, outer_zone):
                assert a == inner_zone, (cut, radius, a)
            if b in (inner_zone, outer_zone):
                assert b == outer_zone, (cut, radius, b)


def test_baseline_zone_reaches_the_corner_three_line():
    """A baseline zone shares its outer edge with its corner-3 strip, as drawn."""
    just_inside = zone_of(np.array([CORNER_X - 4.0]), np.array([20.0]))[0]
    just_outside = zone_of(np.array([CORNER_X + 4.0]), np.array([20.0]))[0]
    assert just_inside == "Right Baseline"
    assert just_outside == "Right Corner 3"


def test_corner_three_becomes_a_wing_above_the_break():
    """Above the corner/arc break the same sideline strip is no longer a corner 3."""
    assert zone_of(np.array([-235.0]), np.array([CORNER_Y - 5]))[0] == "Left Corner 3"
    assert zone_of(np.array([-235.0]), np.array([CORNER_Y + 60]))[0] == "Left Wing 3"


def test_classifier_covers_the_whole_half_court():
    """No point on the drawn court may fall through to an empty label."""
    xs = np.arange(-249.0, 250.0, 3.0)
    ys = np.arange(-47.0, 290.0, 3.0)
    gx, gy = np.meshgrid(xs, ys)
    zones = zone_of(gx, gy)
    assert (zones != "").all()
    assert set(np.unique(zones)) <= set(ZONE_ORDER)


def test_all_twelve_zones_appear_on_the_court():
    xs = np.arange(-249.0, 250.0, 2.0)
    ys = np.arange(-47.0, 290.0, 2.0)
    gx, gy = np.meshgrid(xs, ys)
    assert set(np.unique(zone_of(gx, gy))) == set(ZONE_ORDER)


# ---------------------------------------------------------------------------
# Layout wiring
# ---------------------------------------------------------------------------
def test_every_zone_has_a_chip_position_and_a_label():
    assert set(CHIP_LAYOUT) == set(ZONE_ORDER)
    assert set(SHORT_LABEL) == set(ZONE_ORDER)


def test_on_court_chips_sit_inside_the_zone_they_report():
    """A chip standing on the floor has to stand in its own zone, or it lies."""
    for zone, (anchor, _target) in CHIP_LAYOUT.items():
        if zone in OFF_COURT_ZONES:
            continue
        x, y = anchor
        assert zone_of(np.array([float(x)]), np.array([float(y)]))[0] == zone, zone


def test_off_court_chip_leaders_land_in_their_own_zone():
    """Only the rim uses a leader; wherever one exists it must reach its own zone."""
    for zone, (_anchor, target) in CHIP_LAYOUT.items():
        if target is None:
            continue
        x, y = target
        assert zone_of(np.array([float(x)]), np.array([float(y)]))[0] == zone, zone


def test_off_court_chips_are_the_zones_too_narrow_to_hold_one():
    """Only the rim and the two 3-ft corner strips may sit off the drawn floor."""
    assert OFF_COURT_ZONES == {"Restricted Area", "Left Corner 3", "Right Corner 3"}
    for zone in OFF_COURT_ZONES:
        x, y = CHIP_LAYOUT[zone][0]
        assert y < BASELINE_Y or abs(x) > 250, zone


def test_no_chip_carries_a_leader_line():
    """Every chip now sits in or hard against its own zone, so none needs one."""
    for zone, (_anchor, target) in CHIP_LAYOUT.items():
        assert target is None, zone


def test_any_leader_that_is_ever_added_must_point_into_its_own_zone():
    """Guards the layout table if a future zone does need a line."""
    for zone, (_anchor, target) in CHIP_LAYOUT.items():
        if target is None:
            continue
        x, y = target
        assert zone_of(np.array([float(x)]), np.array([float(y)]))[0] == zone, zone


def test_the_rim_chip_sits_between_the_backboard_and_the_baseline():
    """It cannot stand in a 4 ft circle, so proximity has to do the pointing:
    centred over the basket, figures tucked inside the court without touching
    either the backboard below them or the baseline above them."""
    from scripts.prototypes.scoring_by_location import (
        BACKBOARD_Y, CHIP_RISE, HEAD_HALF, flip,
    )
    anchor = CHIP_LAYOUT["Restricted Area"][0]
    assert anchor[0] == 0, "must be centred over the basket"

    cy = flip(anchor[1]) - CHIP_RISE
    fga_bottom, pps_top = cy - 18.4, cy + 6.6      # measured text extents
    assert fga_bottom > flip(BACKBOARD_Y) + 2, "figures would sit on the backboard"
    assert pps_top < flip(BASELINE_Y) - 2, "figures would sit on the baseline"
    # and the face reaches up across the baseline, tying the chip to the court
    assert cy + 13 + 2 * HEAD_HALF > flip(BASELINE_Y)


def test_corner_chips_straddle_the_sideline_without_reaching_the_corner_three_line():
    """They sit half on the floor by design; the guard is the corner-3 line itself."""
    for zone in ("Left Corner 3", "Right Corner 3"):
        x = abs(CHIP_LAYOUT[zone][0][0])
        assert x - CORNER_TEXT_HALF < 250, zone      # part of the chip is on the floor
        assert x + CORNER_TEXT_HALF > 250, zone      # and part of it hangs off
        assert x - CORNER_TEXT_HALF > CORNER_X, zone  # but never onto the corner-3 line


def test_compact_zones_are_the_shallow_mid_range_band():
    assert COMPACT_ZONES == {"Left Mid-Range", "Right Mid-Range", "Center Mid-Range"}
    assert COMPACT_ZONES <= set(ZONE_ORDER)
