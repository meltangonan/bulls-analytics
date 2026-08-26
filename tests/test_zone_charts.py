"""The twelve-zone chart: geometry, shot diet, and what it refuses to claim.

Three things can go wrong here and none of them look wrong in the output:

* the classifier and the drawn fills could disagree, so the chart counts one set
  of regions and paints another;
* a zone's attempts could be divided by the wrong total, so its printed share
  no longer participates in one shot diet that sums to 100%;
* a zone holding two attempts could print "0.0%", which reads as a cold streak
  rather than as nothing known.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm


def _shots(rows) -> pd.DataFrame:
    """(x, y, made) triples as a shot frame, with shot_type derived from geometry."""
    df = pd.DataFrame(rows, columns=["loc_x", "loc_y", "shot_made"])
    zone = sm.zone_of(df.loc_x, df.loc_y)
    df["shot_type"] = np.where(pd.Series(zone).isin(sm.THREE_ZONES), "3PT", "2PT")
    df["shot_distance"] = np.hypot(df.loc_x, df.loc_y) / 10.0
    return df


# --- Geometry --------------------------------------------------------------
def test_every_point_on_the_drawn_court_belongs_to_exactly_one_zone():
    """No gaps and no overlaps, or a fill would leave bare court or paint twice.

    The fills are traced from this same classification, so an unclassified point
    is a hole in the chart rather than a rounding detail.
    """
    xs = np.arange(-249.0, 250.0, 3.0)
    ys = np.arange(-47.0, 310.0, 3.0)
    gx, gy = np.meshgrid(xs, ys)
    zones = sm.zone_of(gx, gy)
    assert (zones != "").all(), "some court coordinates fall in no zone"
    assert set(np.unique(zones)) <= set(sm.ZONE12_ORDER)


@pytest.mark.parametrize("x, y, expected", [
    (0, 0, "Restricted Area"),            # the hoop itself
    (0, 39, "Restricted Area"),           # just inside the 4 ft arc
    (0, 41, "In The Paint (Non-RA)"),     # just outside it
    (0, 137, "In The Paint (Non-RA)"),    # just inside the free-throw line
    (0, 138, "Center Mid-Range"),         # just beyond its 137.5 coordinate
    (-230, 0, "Left Corner 3"),           # past the corner line, level with hoop
    (230, 0, "Right Corner 3"),
    (-210, 0, "Left Baseline"),           # inside the corner line is still a two
    (0, 240, "Top of Key 3"),             # straight on, past the arc
])
def test_named_landmarks_land_in_the_zone_a_fan_would_name(x, y, expected):
    assert sm.zone_of(np.array([x]), np.array([y]))[0] == expected


def test_nba_basic_zone_owns_physical_region_while_custom_angles_own_sector():
    """A source-labeled mid-range shot must not leak back into geometric paint."""
    shots = pd.DataFrame({
        "loc_x": [0, 0, -100, 100],
        "loc_y": [142, 142, 180, 180],
        "shot_zone": [
            "Mid-Range", "In The Paint (Non-RA)",
            "Mid-Range", "Mid-Range",
        ],
    })

    zones = sm.zone12_of_shots(shots)
    assert zones.tolist() == [
        "Center Mid-Range", "In The Paint (Non-RA)",
        "Left Mid-Range", "Right Mid-Range",
    ]


def test_backcourt_is_explicitly_excluded_from_the_twelve_court_zones():
    shots = pd.DataFrame({
        "loc_x": [0], "loc_y": [450], "shot_zone": ["Backcourt"]
    })
    assert sm.zone12_of_shots(shots).tolist() == ["Backcourt"]


def test_a_shot_inside_the_arc_radius_but_past_the_corner_line_is_a_three():
    """The corner three is the one place distance alone gives the wrong answer.

    At 22 ft from the hoop and level with it, a shot is closer than the 23.75 ft
    arc and still worth three, because the corner line cuts in. A radius-only
    rule would score these as long twos and quietly move ~500 team attempts a
    season into the wrong zone.
    """
    zone = sm.zone_of(np.array([225.0]), np.array([20.0]))[0]
    assert zone in sm.THREE_ZONES
    assert np.hypot(225.0, 20.0) < sm.ARC_R


# --- The split -------------------------------------------------------------
def test_every_zone_appears_even_when_the_subject_never_shot_there():
    """A zone he avoids entirely is a finding; dropping the row hides it."""
    subject = _shots([(0, 0, 1), (0, 0, 1), (0, 0, 0)])
    league = _shots([(0, 0, 1), (0, 200, 1), (-230, 0, 0), (0, 100, 1)])
    table = sm.zone12_split(subject, league)
    assert list(table.zone) == list(sm.ZONE12_ORDER)
    empty = table[table.zone == "Top of Key 3"].iloc[0]
    assert empty.fga == 0 and np.isnan(empty.fg)


def test_a_thin_zone_keeps_its_shot_share_and_loses_only_its_rating():
    """Shot share is counted, so a small sample does not erase the shot diet."""
    subject = _shots([(-210, 0, 0), (-210, 0, 0)])
    league = _shots([(-210, 0, 1), (-210, 0, 0)] * 50)
    row = sm.zone12_split(subject, league)
    baseline = row[row.zone == "Left Baseline"].iloc[0]
    assert baseline.fga == 2
    assert not baseline.rated
    assert baseline.fga_share_pct == pytest.approx(100.0)
    assert baseline.lg_fga_share_pct == pytest.approx(100.0)


# --- The colour floor ------------------------------------------------------
def test_both_floors_are_solved_rather_than_chosen():
    """Each answers "what must not be able to recolour this zone", at the
    strength that subject's sample can support.

    A floor nobody can re-derive is a floor that drifts to whatever looked good
    on the day, which is how this one reached 45 and stayed there through four
    rounds of the chart no longer needing it.
    """
    # team: one standard error must not move it a band
    assert sm.colour_floor(2.5) == 400
    assert sm.MIN_ZONE12_FGA_TEAM == sm.colour_floor(sm.SIGMA_TEAM_POINTS)
    # player: one SHOT must not move it farther than the full neutral span
    assert sm.single_shot_floor(5.0) == 20
    assert sm.MIN_ZONE12_FGA_PLAYER == sm.single_shot_floor()


def test_a_wider_band_needs_fewer_shots_to_hold_its_colour():
    """One shot moves a percentage by 100/n points, so the floor falls as the
    band widens. Halving the band doubles the shots needed."""
    assert sm.single_shot_floor(10.0) == 10
    assert sm.single_shot_floor(2.5) == 40
    assert sm.single_shot_floor(sm.BAND_WIDTH_POINTS) == sm.MIN_ZONE12_FGA_PLAYER


def test_at_the_player_floor_one_shot_moves_exactly_the_neutral_span():
    """The rule stated as arithmetic the reader could check."""
    n = sm.MIN_ZONE12_FGA_PLAYER
    assert 100.0 / n == pytest.approx(sm.BAND_WIDTH_POINTS)
    assert 100.0 / (n - 1) > sm.BAND_WIDTH_POINTS   # one fewer and it overshoots


def test_zone_outer_bands_begin_at_five_points_but_hex_stays_at_seven_and_a_half():
    """Named zones and smoothed hex cells deliberately use different outer cuts."""
    from scripts import make_shot_chart as shot_chart

    assert shot_chart.ZONE12_CUTS == (-0.05, -0.025, 0.025, 0.05)
    assert shot_chart.HEX_CUTS == (-0.075, -0.025, 0.025, 0.075)
    assert shot_chart._zone12_band_color(0.049, "rdylgn") == \
        shot_chart.ZONE12_PALETTES["rdylgn"][3]
    assert shot_chart._zone12_band_color(0.05, "rdylgn") == \
        shot_chart.ZONE12_PALETTES["rdylgn"][4]
    assert shot_chart._zone12_band_color(-0.05, "rdylgn") == \
        shot_chart.ZONE12_PALETTES["rdylgn"][0]


def test_a_tighter_precision_demands_more_attempts():
    """Halving the tolerated error quadruples the sample, because the error
    falls with the square root of n. This is why 2.5 points costs 400 shots and
    not 120, and why no player-season zone can reach it."""
    assert sm.colour_floor(2.5) == 4 * sm.colour_floor(5.0)


def test_the_worst_case_variance_never_understates_the_sample_needed():
    """p(1-p) peaks at p = 0.5, so 0.25 is the assumption-free choice. A rim
    zone shoots ~65% and a three-point zone ~36%; both need fewer attempts than
    the team floor demands, never more."""
    for p in (0.36, 0.45, 0.65):
        needed = p * (1 - p) / (sm.SIGMA_TEAM_POINTS / 100) ** 2
        assert needed <= sm.MIN_ZONE12_FGA_TEAM


def test_a_zone_clears_the_floor_at_the_threshold_exactly():
    n = sm.MIN_ZONE12_FGA
    subject = _shots([(0, 0, 1)] * n)
    league = _shots([(0, 0, 1), (0, 0, 0)] * 50)
    rim = sm.zone12_split(subject, league)
    assert rim[rim.zone == "Restricted Area"].iloc[0].rated

    fewer = _shots([(0, 0, 1)] * (n - 1))
    rim = sm.zone12_split(fewer, league)
    assert not rim[rim.zone == "Restricted Area"].iloc[0].rated


def test_points_per_shot_carries_the_right_point_value_per_zone():
    """A three-point zone is worth 3 and a two-point zone 2, or PPS is nonsense."""
    subject = _shots([(0, 0, 1)] * 30 + [(0, 240, 1)] * 30)
    league = _shots([(0, 0, 1), (0, 240, 0)] * 50)
    table = sm.zone12_split(subject, league).set_index("zone")
    assert table.loc["Restricted Area", "pps"] == pytest.approx(2.0)
    assert table.loc["Top of Key 3", "pps"] == pytest.approx(3.0)


def test_nba_zone_value_conflict_is_reported_and_points_follow_scoreboard_value():
    """NBA zone labels can round across the arc; do not turn an official two into three points."""
    subject = pd.DataFrame({
        "loc_x": [0, 0], "loc_y": [238, 238], "shot_made": [1, 0],
        "shot_type": ["2PT", "2PT"], "shot_zone": ["Above the Break 3"] * 2,
    })
    league = subject.copy()
    table = sm.zone12_split(subject, league).set_index("zone")

    assert sm.source_zone_value_conflicts(subject).sum() == 2
    assert table.loc["Top of Key 3", "subject_source_conflict_fga"] == 2
    assert table.loc["Top of Key 3", "pps"] == pytest.approx(1.0)


def test_relative_fg_and_relative_pps_rank_identically_inside_one_zone():
    """The reason the chart prints FG% and shot share rather than PPS too.

    Within a zone the point value is a constant, so PPS is FG% times that
    constant and the two "vs league" figures carry exactly the same ordering.
    Printing both would be a third column repeating the first.
    """
    subject = _shots([(0, 240, 1)] * 40 + [(0, 240, 0)] * 60)
    league = _shots([(0, 240, 1)] * 35 + [(0, 240, 0)] * 65)
    row = sm.zone12_split(subject, league)
    three = row[row.zone == "Top of Key 3"].iloc[0]
    assert three.fg_rel > 0
    assert (three.pps - three.lg_pps) > 0
    assert (three.pps - three.lg_pps) == pytest.approx(three.fg_rel / 100 * 3)


def test_shot_shares_sum_to_100_and_use_one_league_baseline():
    """A shot diet tiles all attempts and needs no possession denominator."""
    subject = _shots([(0, 0, 1)] * 30)
    league = _shots([(0, 0, 1), (0, 0, 0)] * 50)
    table = sm.zone12_split(subject, league)
    assert table.fga_share_pct.sum() == pytest.approx(100.0)
    assert table.lg_fga_share_pct.sum() == pytest.approx(100.0)




# --- The label layer -------------------------------------------------------
def _rendered(zone: str, table: pd.DataFrame, fill: str = "#F1CC5B",
              pill: str = "full"):
    """Draw one zone's pill on a real axes and report what landed on it.

    A real axes rather than a mock, because the pill measures its own type off
    the renderer to size itself; a mock returns mocks from that measurement and
    the layout never runs.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    row = next(r for r in table.itertuples() if r.zone == zone)
    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1080)
    ax.set_ylim(0, 1350)
    shot_chart._zone12_block(ax, lambda x, y: (540.0, 600.0), row, fill,
                             shot_chart.house.get_theme("jersey"), pill)
    texts = [artist.get_text() for artist in ax.texts]
    colours = [artist.get_color() for artist in ax.texts]
    pills = len(ax.patches)
    plt.close(fig)
    return row, texts, colours, pills


def test_the_large_pill_keeps_four_lines_and_enlarges_only_the_figures():
    import scripts.make_shot_chart as shot_chart

    table = sm.zone12_split(_shots([(0, 240, 1)] * 60 + [(0, 240, 0)] * 40),
                            _shots([(0, 240, 1)] * 50 + [(0, 240, 0)] * 50))
    _, texts, _, pills = _rendered("Top of Key 3", table, pill="large")

    assert pills == 1
    assert len(texts) == 4
    assert texts[0] == "60/100 FG (60.0%)"
    assert texts[1].endswith("vs LA")
    assert texts[2] == "100.0% of FGA"
    assert texts[3].endswith("vs LA")
    assert shot_chart.ZONE12_LARGE_FIGURE_SIZE > shot_chart.ZONE12_FIGURE_SIZE
    assert shot_chart.ZONE12_LARGE_DELTA_SIZE == shot_chart.ZONE12_DELTA_SIZE + 1


def test_a_zone_below_the_floor_keeps_every_figure():
    """Same pill, same four figures, same order as a rated zone.

    The chart says "not evidence" once, in the grey fill, and does not repeat
    itself in the label. Dropping the figures was tried and reversed: a reader
    looking at a zone wants to know what happened there even when the sample is
    thin, and the grey is what tells them how much to trust it.
    """
    thin = sm.zone12_split(_shots([(-210, 0, 0), (-210, 0, 1)] * 6),
                           _shots([(-210, 0, 1), (-210, 0, 0)] * 50))
    row, texts, _, pills = _rendered("Left Baseline", thin, fill="#D8D2CA")
    assert not row.rated
    assert len(texts) == 4 and pills == 1
    assert "FG (" in texts[0] and "% of FGA" in texts[2]


def test_a_thin_pill_is_set_apart_from_a_rated_one():
    """Muted type on a faded card. It carries the figures without carrying the
    weight, so the eye ranks it below the zones the chart can stand behind."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    def draw(table, zone, fill):
        row = next(r for r in table.itertuples() if r.zone == zone)
        fig = plt.figure(figsize=(7.2, 9))
        ax = fig.add_axes([0, 0, 1, 1])
        shot_chart._zone12_block(ax, lambda x, y: (540.0, 600.0), row, fill,
                                 shot_chart.house.get_theme("jersey"))
        out = (ax.texts[0].get_color(), ax.patches[0].get_alpha())
        plt.close(fig)
        return out

    league = _shots([(-210, 0, 1), (-210, 0, 0)] * 300)
    thin = sm.zone12_split(_shots([(-210, 0, 1)] * 6), league)
    fat = sm.zone12_split(_shots([(-210, 0, 1)] * 300), league)

    thin_ink, thin_alpha = draw(thin, "Left Baseline", "#D8D2CA")
    rated_ink, rated_alpha = draw(fat, "Left Baseline", "#F1CC5B")
    assert thin_ink == shot_chart.ZONE12_THIN_INK
    assert rated_ink == shot_chart.ZONE12_PILL_INK
    assert thin_alpha == shot_chart.ZONE12_THIN_PILL_ALPHA
    assert rated_alpha in (None, 1.0)


# --- When a gap is worth a colour ------------------------------------------
def test_a_shooting_gap_inside_the_average_band_is_grey_not_green():
    """+0.2 points is not a direction, and printing it in green claims one.

    The threshold is the fill scale's own neutral band, so a zone painted "about
    average" never carries a coloured gap underneath it. Colour cannot
    contradict colour.
    """
    import scripts.make_shot_chart as shot_chart

    assert shot_chart._zone12_delta_ink(0.2, False) == shot_chart.ZONE12_NEUTRAL_GAP
    assert shot_chart._zone12_delta_ink(0.0, False) == shot_chart.ZONE12_NEUTRAL_GAP
    assert shot_chart._zone12_delta_ink(-0.2, False) == shot_chart.ZONE12_NEUTRAL_GAP
    assert shot_chart.ZONE12_FG_NEUTRAL_POINTS == 2.5, \
        "the neutral band must match the fill scale's own average band"


def test_a_zone_with_no_attempts_says_so():
    """Grey now means one thing only — he never shot here — so it can say it.

    A silent gap left the reader to work out whether the zone was unmeasured or
    simply unused; "0 FGA" settles it in three characters.
    """
    empty = sm.zone12_split(_shots([(0, 0, 1)] * 60),
                            _shots([(0, 0, 1), (0, 240, 0)] * 60))
    _, texts, _, pills = _rendered("Top of Key 3", empty)
    assert texts == ["0 FGA"] and pills == 1


def test_a_rated_zone_prints_shooting_first_then_shot_share():
    """Shooting leads because the fill is shooting.

    The zone's colour is its FG% against the league, so the first line of the
    pill has to be the figure that colour is about. With volume on top the
    reader had to hunt past it for the number the region was already shouting.
    """
    import scripts.make_shot_chart as shot_chart

    table = sm.zone12_split(_shots([(0, 0, 1)] * 40 + [(0, 0, 0)] * 20),
                            _shots([(0, 0, 1), (0, 0, 0)] * 200))
    _, texts, colours, pills = _rendered("Restricted Area", table)
    assert pills == 1
    assert len(texts) == 4
    # The shooting figure names itself. "66.7%" alone was ambiguous next to a
    # neighbouring "+5% vs LA" -- both are percentages of different things.
    assert "FG (" in texts[0], f"shooting must come first, got {texts}"
    assert texts[0].startswith("40/60"), "makes and attempts lead the line"
    assert texts[2] == "100.0% of FGA", f"shot share must come second, got {texts}"
    assert texts[3] == "0.0 vs LA", f"shot share must use the comparison grammar, got {texts}"
    assert colours[3] == shot_chart.ZONE12_NEUTRAL_GAP


def test_shooting_and_share_use_the_same_coloured_comparison_grammar():
    """Both questions show the subject figure, then its signed gap to LA."""
    import scripts.make_shot_chart as shot_chart

    table = sm.zone12_split(_shots([(0, 240, 1)] * 60 + [(0, 240, 0)] * 40),
                            _shots([(0, 240, 1)] * 30 + [(0, 240, 0)] * 70
                                   + [(0, 0, 1)] * 100))
    _, texts, colours, _ = _rendered("Top of Key 3", table)
    assert sum("vs LA" in text for text in texts) == 2
    assert texts[2] == "100.0% of FGA"
    assert texts[3] == "+50.0 vs LA"
    assert colours[1] == shot_chart.ZONE12_UP_ON_LIGHT
    assert colours[3] == shot_chart.ZONE12_UP_ON_LIGHT


def test_no_pill_prints_its_zone_name():
    """The court already says which zone this is."""
    import scripts.make_shot_chart as shot_chart

    table = sm.zone12_split(_shots([(0, 0, 1)] * 60),
                            _shots([(0, 0, 1), (0, 0, 0)] * 200))
    _, texts, _, _ = _rendered("Restricted Area", table)
    assert not any(name in texts for name in shot_chart.ZONE12_SHORT.values())


def test_every_pill_sits_inside_the_zone_it_reports():
    """Position is the only attribution left once the zone names are gone.

    No exceptions now. The rim pill used to drop into the apron under the basket
    because a full-size pill would not fit an 8 ft disc; it fits once the pill
    is allowed to shrink, and a label inside its own region needs no explaining.
    """
    import scripts.make_shot_chart as shot_chart

    for zone, (x, y) in shot_chart.ZONE12_ANCHORS.items():
        landed = sm.zone_of(np.array([float(x)]), np.array([float(y)]))[0]
        assert landed == zone, f"the {zone} pill sits in {landed}"


def test_left_and_right_zone_pills_follow_basket_bottom_orientation():
    """Regression: source Left renders right; source Right renders left."""
    import scripts.make_shot_chart as shot_chart
    from bulls.graphics.court import nba_to_basket_bottom_px

    def display_x(zone):
        x, y = shot_chart.ZONE12_ANCHORS[zone]
        return nba_to_basket_bottom_px(0.0, 0.0, 1.0, x, y)[0]

    for pair in ("Corner 3", "Baseline", "Mid-Range", "Wing 3"):
        assert display_x(f"Left {pair}") > 250.0
        assert display_x(f"Right {pair}") < 250.0


def test_the_rim_uses_the_same_type_scale_as_every_other_zone():
    """Readability wins over trapping the whole cream card inside the RA."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    table = sm.zone12_split(_shots([(0, 0, 1)] * 40 + [(0, 0, 0)] * 20),
                            _shots([(0, 0, 1), (0, 0, 0)] * 200))
    row = next(r for r in table.itertuples() if r.zone == "Restricted Area")
    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    shot_chart._zone12_block(ax, lambda x, y: (540.0, 600.0), row, "#F1CC5B",
                             shot_chart.house.get_theme("jersey"))
    sizes = [text.get_fontsize() for text in ax.texts]
    plt.close(fig)
    assert sizes == [shot_chart.ZONE12_FIGURE_SIZE,
                     shot_chart.ZONE12_DELTA_SIZE,
                     shot_chart.ZONE12_FIGURE_SIZE,
                     shot_chart.ZONE12_DELTA_SIZE]
    assert shot_chart.ZONE12_PILL_PAD_X < 10
    assert shot_chart.ZONE12_PILL_PAD_Y < 8


def test_gap_colour_carries_direction_and_nothing_else():
    """One ink and one green-red-grey set, because every pill is cream. An
    earlier draft recoloured type per fill, and the same figure changing colour
    zone to zone read as though the colour meant something it did not."""
    import scripts.make_shot_chart as shot_chart

    assert shot_chart._zone12_delta_ink(4.0, True) == shot_chart.ZONE12_UP_ON_LIGHT
    assert shot_chart._zone12_delta_ink(-4.0, True) == shot_chart.ZONE12_DOWN_ON_LIGHT
    assert shot_chart._zone12_delta_ink(4.0, False) == shot_chart.ZONE12_NEUTRAL_GAP


def test_every_zone_has_an_anchor_and_a_short_label():
    """A zone with no anchor would silently vanish from the page."""
    import scripts.make_shot_chart as shot_chart

    assert set(shot_chart.ZONE12_ANCHORS) == set(sm.ZONE12_ORDER)
    assert set(shot_chart.ZONE12_SHORT) == set(sm.ZONE12_ORDER)


# --- Signs -----------------------------------------------------------------
def test_a_gap_that_rounds_to_zero_carries_no_sign():
    """"-0%" claims a direction the printed number contradicts.

    The sign has to follow the value the reader can see, so it is decided after
    rounding rather than before. A gap of -0.4 prints as "0%", not "-0%".
    """
    import scripts.make_shot_chart as shot_chart

    assert shot_chart._signed(-0.4, 0) == "0"
    assert shot_chart._signed(0.4, 0) == "0"
    assert shot_chart._signed(0.0, 0) == "0"
    assert shot_chart._signed(-0.04, 1) == "0.0"
    assert shot_chart._signed(0.04, 1) == "0.0"


def test_a_negative_gap_uses_a_true_minus_not_a_hyphen():
    """A hyphen sits too high and too short beside figures, and next to a
    full-width plus the pair reads as misaligned."""
    import scripts.make_shot_chart as shot_chart

    assert shot_chart._signed(-4.2, 1) == "−4.2"
    assert "-" not in shot_chart._signed(-4.2, 1)
    assert shot_chart._signed(5.0, 0) == "+5"


def test_the_rendered_gaps_use_the_same_signs():
    """The rule has to survive the trip through the row builder."""
    import scripts.make_shot_chart as shot_chart

    worse = sm.zone12_split(_shots([(0, 240, 1)] * 20 + [(0, 240, 0)] * 80),
                            _shots([(0, 240, 1)] * 40 + [(0, 240, 0)] * 60))
    _, texts, _, _ = _rendered("Top of Key 3", worse)
    assert any(text.startswith("−") for text in texts), texts
    assert not any(text.startswith("-") for text in texts), texts


def test_the_legend_is_one_row_of_swatches_and_no_prose():
    """The scale, plus the grey that sits outside it, and nothing else.

    Asserted on what the legend actually draws rather than on its source text —
    an earlier version of this test searched the source for a literal string,
    and went on passing after the string moved into a constant.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1080)
    ax.set_ylim(0, 1350)
    shot_chart._zone12_legend(ax, shot_chart.house.get_theme("jersey"), "rdylgn",
                              sm.MIN_ZONE12_FGA_TEAM)
    texts = [artist.get_text() for artist in ax.texts]
    swatches = [tuple(patch.get_facecolor()) for patch in ax.patches]
    plt.close(fig)

    assert texts == ["Below", "FG% vs. NBA avg", "Above",
                     shot_chart._zone12_thin_key(sm.MIN_ZONE12_FGA_TEAM)]
    assert not any(len(text.split()) > 4 for text in texts), \
        f"the legend grew a sentence: {texts}"
    # Five bands plus the grey, which is a sixth state of the same encoding.
    assert len(swatches) == len(shot_chart.ZONE12_PALETTES["rdylgn"]) + 1


def test_the_legend_can_omit_the_thin_key_when_every_zone_is_rated():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1080)
    ax.set_ylim(0, 1350)
    shot_chart._zone12_legend(
        ax, shot_chart.house.get_theme("jersey"), "rdylgn", 1,
        show_thin=False,
    )
    texts = [artist.get_text() for artist in ax.texts]
    swatches = [tuple(patch.get_facecolor()) for patch in ax.patches]
    plt.close(fig)

    assert texts == ["Below", "FG% vs. NBA avg", "Above"]
    assert len(swatches) == len(shot_chart.ZONE12_PALETTES["rdylgn"])


def test_the_thin_key_is_a_plain_neutral_swatch():
    """The key must match the plain grey used for every below-floor zone."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    shot_chart._zone12_legend(ax, shot_chart.house.get_theme("jersey"), "rdylgn",
                              sm.MIN_ZONE12_FGA_PLAYER)
    neutral = ax.patches[-1]
    face = matplotlib.colors.to_hex(neutral.get_facecolor()).upper()
    plt.close(fig)
    assert not neutral.get_hatch()
    assert face == shot_chart.ZONE12_GREY.upper()
    assert face not in {c.upper() for c in shot_chart.ZONE12_PALETTES["rdylgn"]}


def test_the_grey_key_states_the_threshold_rather_than_a_verdict():
    """"TOO FEW TO RATE" hides the rule; a number can be checked against the
    attempt counts printed in the grey pills themselves."""
    import scripts.make_shot_chart as shot_chart

    assert shot_chart._zone12_thin_key(400) == "Under 400 FGA"
    assert shot_chart._zone12_thin_key(20) == "Under 20 FGA"


def test_the_threshold_in_the_key_matches_the_floor_the_chart_used():
    """A key quoting one floor while the fills use another is worse than no key.

    This is the check that catches the team and player floors being wired up
    separately and drifting apart.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    for floor in (sm.MIN_ZONE12_FGA_TEAM, sm.MIN_ZONE12_FGA_PLAYER):
        fig = plt.figure(figsize=(7.2, 9))
        ax = fig.add_axes([0, 0, 1, 1])
        shot_chart._zone12_legend(ax, shot_chart.house.get_theme("jersey"),
                                  "rdylgn", floor)
        printed = [t.get_text() for t in ax.texts]
        plt.close(fig)
        assert str(floor) in " ".join(printed)


def test_the_threshold_is_muted_not_accent_red():
    """Red on this chart means "below league average". A red figure in the key
    would read as the bad end of the scale rather than as a caveat."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    theme = shot_chart.house.get_theme("jersey")
    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    shot_chart._zone12_legend(ax, theme, "rdylgn", 400)
    thin = next(t for t in ax.texts if t.get_text().startswith("Under "))
    plt.close(fig)
    assert thin.get_color() == theme.muted
    assert thin.get_color() != theme.accent


# --- Below-floor fill ------------------------------------------------------
def test_a_thin_zone_is_plain_grey():
    """The full pill preserves the finding; the ground declines to rate it."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    gx, gy = np.meshgrid(np.linspace(0, 100, 40), np.linspace(0, 100, 40))
    mask = gx < 50
    shot_chart._zone12_fill(ax, gx, gy, mask, shot_chart.ZONE12_GREY, 2.0)
    fills = [c for c in ax.collections if len(c.get_facecolor())]
    faces = [matplotlib.colors.to_hex(c.get_facecolor()[0]).upper() for c in fills]
    plt.close(fig)
    assert faces == [shot_chart.ZONE12_GREY.upper()]
    assert not any(getattr(c, "hatches", [None])[0] for c in fills)


def test_a_rated_zone_keeps_its_solid_band_colour():
    """Changing the caveat must not mute a zone that clears the floor."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    gx, gy = np.meshgrid(np.linspace(0, 100, 40), np.linspace(0, 100, 40))
    shot_chart._zone12_fill(ax, gx, gy, gx < 50, "#8CBF63", 2.0)
    fills = [c for c in ax.collections if len(c.get_facecolor())]
    faces = [matplotlib.colors.to_hex(c.get_facecolor()[0]).upper() for c in fills]
    assert faces == ["#8CBF63"]
    assert not any(getattr(c, "hatches", [None])[0] for c in ax.collections)
    plt.close(fig)


def test_blank_zone_cover_has_no_data_layer_or_legend(tmp_path):
    """The cover teases the exact geometry without pretending to show results."""
    import inspect
    from scripts import make_shot_chart as shot_chart

    blank = inspect.getsource(shot_chart.render_blank_zones)
    assert "_zone12_block" not in blank
    assert "_zone12_legend" not in blank
    assert "_zone12_summary_cards" not in blank
    helper = inspect.getsource(shot_chart._render_cover_zones)
    assert 'court_ink = "#242424"' in helper

    out = tmp_path / "blank.png"
    shot_chart.render_blank_zones(out, final=False)
    assert out.exists()


def test_color_preview_cover_is_solid_reproducible_and_data_free(tmp_path):
    """The colorful teaser previews the grammar without inventing results."""
    import inspect
    from scripts import make_shot_chart as shot_chart

    preview = inspect.getsource(shot_chart.render_preview_zones)
    assert "_zone12_block" not in preview
    assert "_zone12_legend" not in preview
    assert "_zone12_summary_cards" not in preview
    assert "band_by_zone" in preview
    assert "1.0" in preview
    assert "(4, 3, 1, 0, 4, 2, 1, 0, 1, 3, 0, 3)" in preview

    out = tmp_path / "preview.png"
    shot_chart.render_preview_zones(out, final=False)
    assert out.exists()


def test_randomized_cover_is_reproducible_and_separates_adjacent_shades(tmp_path):
    from scripts import make_shot_chart as shot_chart

    first = shot_chart.randomized_cover_fills(201011)
    second = shot_chart.randomized_cover_fills(201011)

    assert first == second
    assert set(first) == set(sm.ZONE12_ORDER)
    assert set(first.values()) == set(
        shot_chart.ZONE12_PALETTES[shot_chart.ZONE12_DEFAULT_PALETTE]
    )
    colors = shot_chart.ZONE12_PALETTES[shot_chart.ZONE12_DEFAULT_PALETTE]
    assert [list(first.values()).count(color) for color in colors] == [2, 2, 2, 3, 3]
    for left, right in shot_chart.ZONE12_COVER_ADJACENCY:
        assert first[left] != first[right]

    out = tmp_path / "randomized-cover.png"
    shot_chart.render_randomized_cover_zones(out, final=False, seed=201011)
    assert out.exists()


def test_solid_cover_variants_use_canonical_reusable_red_tokens(tmp_path):
    """Solid covers remain player-neutral and use settled Bulls-family reds."""
    from scripts import make_shot_chart as shot_chart

    assert shot_chart.ZONE12_BULLS_RED == "#CE1141"
    assert shot_chart.ZONE12_BULLS_RED_LIGHT == "#E67C96"
    for name, fill in (
        ("red", shot_chart.ZONE12_BULLS_RED),
        ("light-red", shot_chart.ZONE12_BULLS_RED_LIGHT),
    ):
        out = tmp_path / f"zone-cover-{name}.png"
        shot_chart.render_solid_cover_zones(out, final=False, fill=fill)
        assert out.exists()


def test_zone_renderer_can_hide_all_detail_overlays_for_a_data_cover():
    """Real zone colors can stand alone without pills, legend, or summaries."""
    import inspect
    from scripts import make_shot_chart as shot_chart

    source = inspect.getsource(shot_chart.render_zones)
    assert 'show_details = bool(ctx.get("show_details", True))' in source
    assert "if show_details:" in source
    detail_branch = source.split("if show_details:", 1)[1]
    assert "_zone12_block" in detail_branch
    assert "_zone12_legend" in detail_branch
    assert "_zone12_summary_cards" in detail_branch


def test_the_above_the_break_dividers_are_the_mid_range_rays_continued():
    """One unbroken ray from the paint to the top of the chart.

    Written out twice as literals they drift apart, and the kink lands exactly
    where the line crosses the most recognisable arc on the floor.
    """
    assert sm.ATB_CUTS == sm.MID_SECTOR_CUTS[1:3]

    just_inside = sm.zone_of(np.array([0.0]), np.array([sm.ARC_R - 6]))[0]
    just_outside = sm.zone_of(np.array([0.0]), np.array([sm.ARC_R + 6]))[0]
    assert just_inside == "Center Mid-Range" and just_outside == "Top of Key 3"


def test_the_three_central_sectors_are_equal_width():
    """Even thirds of what the baseline cuts leave. NBA's 72/108 measured worse
    on both zone area and league shot volume — the paint pushes the middle
    sector's inner edge out to the free-throw line, so equal rays do not buy
    equal regions and the middle needs the extra width."""
    cuts = sm.MID_SECTOR_CUTS
    widths = [cuts[i + 1] - cuts[i] for i in range(3)]
    assert all(abs(w - widths[0]) < 1e-9 for w in widths)
    assert cuts[0] == pytest.approx(sm.CORNER_BREAK_DEG)
    assert cuts[3] == pytest.approx(180 - sm.CORNER_BREAK_DEG)


def test_overall_cards_compute_efg_and_three_point_percentage_from_attempts():
    import scripts.make_shot_chart as shot_chart

    shots = pd.DataFrame({
        "shot_type": ["2PT Field Goal", "2PT Field Goal",
                      "3PT Field Goal", "3PT Field Goal"],
        "shot_made": [1, 0, 1, 0],
    })
    metrics = shot_chart._zone12_overall_metrics(shots)

    assert metrics["fga"] == 4
    assert metrics["efg_pct"] == pytest.approx(62.5)
    assert metrics["three_pa"] == 2
    assert metrics["three_pct"] == pytest.approx(50.0)


def test_overall_cards_replace_low_sample_three_pct_with_attempt_count():
    import scripts.make_shot_chart as shot_chart

    assert shot_chart._zone12_three_label(
        {"three_pa": 0, "three_pct": float("nan")}
    ) == "0 3PA"
    assert shot_chart._zone12_three_label(
        {"three_pa": 19, "three_pct": 100.0}
    ) == "19 3PA"
    assert shot_chart._zone12_three_label(
        {"three_pa": 20, "three_pct": 35.0}
    ) == "35.0% 3PT"


def test_overall_cards_default_to_three_red_gradient_pills_without_league_deltas():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import scripts.make_shot_chart as shot_chart

    shots = pd.DataFrame({
        "shot_type": ["2PT Field Goal", "2PT Field Goal",
                      "3PT Field Goal", "3PT Field Goal"],
        "shot_made": [1, 0, 1, 0],
    })
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1080)
    ax.set_ylim(0, 1350)
    shot_chart._zone12_summary_cards(
        ax, shots, shots, shot_chart.house.get_theme("jersey")
    )
    labels = [text.get_text() for text in ax.texts]
    colors = [text.get_color() for text in ax.texts]
    plt.close(fig)

    assert labels == ["4 FGA", "62.5% eFG", "2 3PA"]
    assert not any("LA" in label for label in labels)
    assert colors == ["#FFFFFF"] * 3
    assert len(ax.images) == 3


def test_overall_cards_put_supplied_ppg_immediately_before_fga():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import scripts.make_shot_chart as shot_chart

    shots = pd.DataFrame({
        "shot_type": ["2PT Field Goal", "2PT Field Goal",
                      "3PT Field Goal", "3PT Field Goal"],
        "shot_made": [1, 0, 1, 0],
    })
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1080)
    ax.set_ylim(0, 1350)
    shot_chart._zone12_summary_cards(
        ax, shots, shots, shot_chart.house.get_theme("jersey"), ppg=25.012
    )
    labels = [text.get_text() for text in ax.texts]
    plt.close(fig)

    assert labels == ["25.0 PPG", "4 FGA", "62.5% eFG", "2 3PA"]
    assert len(ax.images) == 4


def test_the_filled_zone_court_has_a_closed_horizontal_top_edge():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import scripts.make_shot_chart as shot_chart

    fig, ax = plt.subplots()
    theme = shot_chart.house.get_theme("jersey")
    shot_chart._zone12_close_top(ax, lambda x, y: (x, y), theme)
    line = ax.lines[-1]
    plt.close(fig)

    assert tuple(line.get_xdata()) == (-250, 250)
    assert tuple(line.get_ydata()) == (shot_chart.ZONE12_TOP,) * 2
    assert line.get_color() == theme.ink


# --- Which side is which ---------------------------------------------------
# The family totals cannot catch a left/right swap: mid-range still sums to the
# same number with its wings exchanged, and the pill anchors still sit on the
# correct sides of the court. What would move is the pair of numbers printed in
# them. These pin the whole chain instead -- NBA's sign, our zone name, and the
# pixel the fill lands on -- because it is only wrong at the ends.
def _nba_row(loc_x, loc_y, shot_zone):
    return pd.DataFrame({"loc_x": [loc_x], "loc_y": [loc_y],
                         "shot_zone": [shot_zone], "shot_made": [1]})


# Sectors are wedges measured at the hoop, so a baseline zone is reached by a
# shot close to the baseline -- not by one far out to the side.
@pytest.mark.parametrize("loc_x,loc_y,shot_zone,expected", [
    (-120.0, 120.0, "Mid-Range", "Left Mid-Range"),
    (120.0, 120.0, "Mid-Range", "Right Mid-Range"),
    (-200.0, 40.0, "Mid-Range", "Left Baseline"),
    (200.0, 40.0, "Mid-Range", "Right Baseline"),
    (-150.0, 220.0, "Above the Break 3", "Left Wing 3"),
    (150.0, 220.0, "Above the Break 3", "Right Wing 3"),
])
def test_a_zone_named_left_holds_the_shots_nba_calls_left(loc_x, loc_y, shot_zone,
                                                          expected):
    """Negative ``loc_x`` is NBA's Left Side; our zone names must agree with it.

    Verified against NBA's own ``shot_zone_area`` on DeRozan's 4,193 Bulls
    attempts: no shot NBA labels Left Side or Left Side Center falls in one of
    our Right zones, or the reverse. Only neighbouring sectors disagree, which
    is expected -- our rays sit at different angles than NBA's on purpose.
    """
    assert sm.zone12_of_shots(_nba_row(loc_x, loc_y, shot_zone))[0] == expected


def test_each_zone_fill_is_painted_on_the_side_its_own_shots_map_to():
    """The fills, not just the pills. A pill can be right while the fill is not."""
    import scripts.make_shot_chart as shot_chart
    from bulls.graphics.court import nba_to_basket_bottom_px

    gx, gy, grid = shot_chart._zone12_grid()
    gx_px, _ = nba_to_basket_bottom_px(0.0, 0.0, 1.0, gx, gy)
    hoop_px, _ = nba_to_basket_bottom_px(0.0, 0.0, 1.0, 0.0, 0.0)

    for zone in sm.ZONE12_ORDER:
        mask = grid == zone
        assert mask.any(), zone
        # Where the region's own shots sit in NBA coordinates, and where it is
        # painted. A basket-bottom court must put those on opposite signs.
        source_x = gx[mask].mean()
        drawn_offset = gx_px[mask].mean() - hoop_px
        if abs(source_x) < 15.0:
            assert abs(drawn_offset) < 8.0, zone
        else:
            assert np.sign(drawn_offset) == -np.sign(source_x), zone
