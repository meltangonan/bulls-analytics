"""The twelve-zone chart: geometry, denominators, and what it refuses to claim.

Three things can go wrong here and none of them look wrong in the output:

* the classifier and the drawn fills could disagree, so the chart counts one set
  of regions and paints another;
* a team rate could be measured against a player-possession baseline, which
  reads about five times too high and still looks like a plausible number;
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
    (0, 141, "In The Paint (Non-RA)"),    # just inside the free-throw line
    (0, 144, "Center Mid-Range"),         # just beyond it
    (-230, 0, "Left Corner 3"),           # past the corner line, level with hoop
    (230, 0, "Right Corner 3"),
    (-210, 0, "Left Baseline"),           # inside the corner line is still a two
    (0, 240, "Top of Key 3"),             # straight on, past the arc
])
def test_named_landmarks_land_in_the_zone_a_fan_would_name(x, y, expected):
    assert sm.zone_of(np.array([x]), np.array([y]))[0] == expected


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
    table = sm.zone12_split(subject, league, 100.0, 1000.0)
    assert list(table.zone) == list(sm.ZONE12_ORDER)
    empty = table[table.zone == "Top of Key 3"].iloc[0]
    assert empty.fga == 0 and np.isnan(empty.fg)


def test_a_thin_zone_keeps_its_volume_and_loses_only_its_rating():
    """Volume is counted, not estimated, so a small sample does not damage it."""
    subject = _shots([(-210, 0, 0), (-210, 0, 0)])
    league = _shots([(-210, 0, 1), (-210, 0, 0)] * 50)
    row = sm.zone12_split(subject, league, 100.0, 1000.0)
    baseline = row[row.zone == "Left Baseline"].iloc[0]
    assert baseline.fga == 2
    assert not baseline.rated
    assert baseline.per75 == pytest.approx(2 / 100.0 * 75)


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
    # player: one SHOT must not move it a band
    assert sm.single_shot_floor(5.0) == 20
    assert sm.MIN_ZONE12_FGA_PLAYER == sm.single_shot_floor()


def test_a_wider_band_needs_fewer_shots_to_hold_its_colour():
    """One shot moves a percentage by 100/n points, so the floor falls as the
    band widens. Halving the band doubles the shots needed."""
    assert sm.single_shot_floor(10.0) == 10
    assert sm.single_shot_floor(2.5) == 40
    assert sm.single_shot_floor(sm.BAND_WIDTH_POINTS) == sm.MIN_ZONE12_FGA_PLAYER


def test_at_the_player_floor_one_shot_moves_exactly_one_band():
    """The rule stated as arithmetic the reader could check."""
    n = sm.MIN_ZONE12_FGA_PLAYER
    assert 100.0 / n == pytest.approx(sm.BAND_WIDTH_POINTS)
    assert 100.0 / (n - 1) > sm.BAND_WIDTH_POINTS   # one fewer and it overshoots


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
    rim = sm.zone12_split(subject, league, 100.0, 1000.0)
    assert rim[rim.zone == "Restricted Area"].iloc[0].rated

    fewer = _shots([(0, 0, 1)] * (n - 1))
    rim = sm.zone12_split(fewer, league, 100.0, 1000.0)
    assert not rim[rim.zone == "Restricted Area"].iloc[0].rated


def test_points_per_shot_carries_the_right_point_value_per_zone():
    """A three-point zone is worth 3 and a two-point zone 2, or PPS is nonsense."""
    subject = _shots([(0, 0, 1)] * 30 + [(0, 240, 1)] * 30)
    league = _shots([(0, 0, 1), (0, 240, 0)] * 50)
    table = sm.zone12_split(subject, league, 100.0, 1000.0).set_index("zone")
    assert table.loc["Restricted Area", "pps"] == pytest.approx(2.0)
    assert table.loc["Top of Key 3", "pps"] == pytest.approx(3.0)


def test_relative_fg_and_relative_pps_rank_identically_inside_one_zone():
    """The reason the chart prints FG% and volume rather than PPS and volume.

    Within a zone the point value is a constant, so PPS is FG% times that
    constant and the two "vs league" figures carry exactly the same ordering.
    Printing both would be a third column repeating the first.
    """
    subject = _shots([(0, 240, 1)] * 40 + [(0, 240, 0)] * 60)
    league = _shots([(0, 240, 1)] * 35 + [(0, 240, 0)] * 65)
    row = sm.zone12_split(subject, league, 100.0, 1000.0)
    three = row[row.zone == "Top of Key 3"].iloc[0]
    assert three.fg_rel > 0
    assert (three.pps - three.lg_pps) > 0
    assert (three.pps - three.lg_pps) == pytest.approx(three.fg_rel / 100 * 3)


def test_per75_scales_with_the_possession_denominator_it_is_given():
    """Halving the denominator doubles the rate — the check that catches a team
    rate measured against a player-possession baseline."""
    subject = _shots([(0, 0, 1)] * 30)
    league = _shots([(0, 0, 1), (0, 0, 0)] * 50)
    wide = sm.zone12_split(subject, league, 1000.0, 10_000.0)
    narrow = sm.zone12_split(subject, league, 500.0, 10_000.0)
    wide_rim = wide[wide.zone == "Restricted Area"].iloc[0]
    narrow_rim = narrow[narrow.zone == "Restricted Area"].iloc[0]
    assert narrow_rim.per75 == pytest.approx(wide_rim.per75 * 2)
    assert narrow_rim.lg_per75 == pytest.approx(wide_rim.lg_per75)




# --- The label layer -------------------------------------------------------
def _rendered(zone: str, table: pd.DataFrame, fill: str = "#F1CC5B"):
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
                             shot_chart.house.get_theme("jersey"))
    texts = [artist.get_text() for artist in ax.texts]
    colours = [artist.get_color() for artist in ax.texts]
    pills = len(ax.patches)
    plt.close(fig)
    return row, texts, colours, pills


def test_a_zone_below_the_floor_keeps_every_figure():
    """Same pill, same four figures, same order as a rated zone.

    The chart says "not evidence" once, in the grey fill, and does not repeat
    itself in the label. Dropping the figures was tried and reversed: a reader
    looking at a zone wants to know what happened there even when the sample is
    thin, and the grey is what tells them how much to trust it.
    """
    thin = sm.zone12_split(_shots([(-210, 0, 0), (-210, 0, 1)] * 6),
                           _shots([(-210, 0, 1), (-210, 0, 0)] * 50),
                           100.0, 1000.0)
    row, texts, _, pills = _rendered("Left Baseline", thin, fill="#D8D2CA")
    assert not row.rated
    assert len(texts) == 4 and pills == 1
    assert "FG (" in texts[0] and "FGA / 75" in texts[2]


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
    thin = sm.zone12_split(_shots([(-210, 0, 1)] * 6), league, 100.0, 1000.0)
    fat = sm.zone12_split(_shots([(-210, 0, 1)] * 300), league, 100.0, 1000.0)

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


def test_a_volume_gap_is_measured_against_the_noise_in_its_own_count():
    """A season's attempts in a zone is a count, so its standard error is the
    square root of itself and the relative noise is 1/sqrt(n). That makes the
    threshold scale with the zone rather than being picked: about 5% at 400
    attempts, about 15% at 45."""
    import scripts.make_shot_chart as shot_chart

    assert not shot_chart._volume_gap_is_real(4.0, 400)    # inside 5% noise
    assert shot_chart._volume_gap_is_real(6.0, 400)
    assert not shot_chart._volume_gap_is_real(12.0, 45)    # inside 15% noise
    assert shot_chart._volume_gap_is_real(20.0, 45)
    assert not shot_chart._volume_gap_is_real(50.0, 0)


def test_a_zone_with_no_attempts_says_so():
    """Grey now means one thing only — he never shot here — so it can say it.

    A silent gap left the reader to work out whether the zone was unmeasured or
    simply unused; "0 FGA" settles it in three characters.
    """
    empty = sm.zone12_split(_shots([(0, 0, 1)] * 60),
                            _shots([(0, 0, 1), (0, 240, 0)] * 60),
                            100.0, 1000.0)
    _, texts, _, pills = _rendered("Top of Key 3", empty)
    assert texts == ["0 FGA"] and pills == 1


def test_a_rated_zone_prints_shooting_first_then_attempts():
    """Shooting leads because the fill is shooting.

    The zone's colour is its FG% against the league, so the first line of the
    pill has to be the figure that colour is about. With volume on top the
    reader had to hunt past it for the number the region was already shouting.
    """
    table = sm.zone12_split(_shots([(0, 0, 1)] * 40 + [(0, 0, 0)] * 20),
                            _shots([(0, 0, 1), (0, 0, 0)] * 200),
                            100.0, 1000.0)
    _, texts, _, pills = _rendered("Restricted Area", table)
    assert pills == 1
    assert len(texts) == 4
    # The shooting figure names itself. "66.7%" alone was ambiguous next to a
    # neighbouring "+5% vs LA" -- both are percentages of different things.
    assert "FG (" in texts[0], f"shooting must come first, got {texts}"
    assert texts[0].startswith("40 / 60"), "makes and attempts lead the line"
    assert "FGA / 75" in texts[2], f"volume must come second, got {texts}"


def test_both_gaps_say_what_they_are_a_gap_to_and_carry_direction():
    """"+0.8" alone does not say what it is measured against, and a gap that
    never changes colour makes the reader do the sign arithmetic."""
    import scripts.make_shot_chart as shot_chart

    table = sm.zone12_split(_shots([(0, 240, 1)] * 60 + [(0, 240, 0)] * 40),
                            _shots([(0, 240, 1)] * 30 + [(0, 240, 0)] * 70),
                            100.0, 1000.0)
    _, texts, colours, _ = _rendered("Top of Key 3", table)
    gaps = [text for text in texts if "vs LA" in text]
    assert len(gaps) == 2, f"expected one gap per figure, got {texts}"
    assert all("vs LA" in text for text in gaps)
    assert shot_chart.ZONE12_UP_ON_LIGHT in colours, "an above-average gap is green"


def test_no_pill_prints_its_zone_name():
    """The court already says which zone this is."""
    import scripts.make_shot_chart as shot_chart

    table = sm.zone12_split(_shots([(0, 0, 1)] * 60),
                            _shots([(0, 0, 1), (0, 0, 0)] * 200), 100.0, 1000.0)
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


def test_the_rim_pill_is_shrunk_to_fit_inside_the_restricted_area():
    """Solved on every render, not tuned once.

    The disc is 8 ft across and the pill is nearly that wide, so the margin is
    thin enough that a longer figure on some other player's chart would burst it
    if the size were fixed. What is checked is the pill's farthest point from its
    own centre, which the rounded corners pull in well short of the rectangle's
    diagonal -- that rounding is most of why it fits at all.
    """
    import scripts.make_shot_chart as shot_chart

    court_scale = shot_chart.ZONE12_SCALE

    def to_px(x, y):
        return (540.0 + x * court_scale, 600.0 + y * court_scale)

    half_w, half_h = 62.0, 42.0
    scale = shot_chart._zone12_rim_fit("Restricted Area", half_w, half_h, to_px)
    radius = shot_chart.ZONE12_PILL_ROUND * scale
    reach = np.hypot(max(half_w * scale - radius, 0),
                     max(half_h * scale - radius, 0)) + radius
    assert reach <= sm.RA_R * court_scale, "the rim pill escapes its own zone"
    assert scale <= 1.0

    # A wider pill shrinks further; every other zone is left alone.
    assert shot_chart._zone12_rim_fit("Restricted Area", 90.0, 42.0, to_px) < scale
    assert shot_chart._zone12_rim_fit("In The Paint (Non-RA)", 200.0, 90.0,
                                      to_px) == 1.0


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
                            _shots([(0, 240, 1)] * 40 + [(0, 240, 0)] * 60),
                            100.0, 1000.0)
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

    assert texts == ["BELOW", "FG% VS. NBA AVG", "ABOVE",
                     shot_chart._zone12_thin_key(sm.MIN_ZONE12_FGA_TEAM)]
    assert not any(len(text.split()) > 4 for text in texts), \
        f"the legend grew a sentence: {texts}"
    # Five bands plus the grey, which is a sixth state of the same encoding.
    assert len(swatches) == len(shot_chart.ZONE12_PALETTES["rdylgn"]) + 1


def test_the_thin_key_is_a_hatch_on_a_neutral_swatch():
    """Hatched, because that is what a thin zone now looks like on the court.

    The swatch sits on neutral grey rather than a band colour: the hatch can
    fall on any of the five, and a yellow swatch suggested it belonged to yellow.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    shot_chart._zone12_legend(ax, shot_chart.house.get_theme("jersey"), "rdylgn",
                              sm.MIN_ZONE12_FGA_PLAYER)
    hatched = [p for p in ax.patches if p.get_hatch()]
    faces = {matplotlib.colors.to_hex(p.get_facecolor()).upper() for p in hatched}
    plt.close(fig)
    assert len(hatched) == 1, "one hatched swatch, on the end of the scale"
    assert faces == {shot_chart.ZONE12_HATCH_KEY.upper()}
    assert faces.isdisjoint({c.upper() for c in shot_chart.ZONE12_PALETTES["rdylgn"]})


def test_the_grey_key_states_the_threshold_rather_than_a_verdict():
    """"TOO FEW TO RATE" hides the rule; a number can be checked against the
    attempt counts printed in the grey pills themselves."""
    import scripts.make_shot_chart as shot_chart

    assert shot_chart._zone12_thin_key(400) == "UNDER 400 SHOTS"
    assert shot_chart._zone12_thin_key(45) == "UNDER 45 SHOTS"


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
    thin = next(t for t in ax.texts if "UNDER" in t.get_text())
    plt.close(fig)
    assert thin.get_color() == theme.muted
    assert thin.get_color() != theme.accent


# --- Hatching --------------------------------------------------------------
def test_a_thin_zone_is_hatched_in_its_own_colour_not_greyed():
    """The finding survives the caveat.

    Greying a thin zone threw its colour away to signal the doubt. Hatching says
    the same thing the way a footnote does — read this, but not as hard — and
    texture is a weaker visual channel than colour by design, which is the right
    ranking for a caveat against the thing it qualifies.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    gx, gy = np.meshgrid(np.linspace(0, 100, 40), np.linspace(0, 100, 40))
    mask = gx < 50
    shot_chart._zone12_fill(ax, gx, gy, mask, "#8CBF63", 2.0, hatched=True)
    # A filled contour keeps its hatch on `.hatches`; get_hatch() reports None
    # for a QuadContourSet even when it renders the pattern.
    hatched = [c for c in ax.collections if getattr(c, "hatches", [None])[0]]
    faces = [matplotlib.colors.to_hex(c.get_facecolor()[0]).upper()
             for c in hatched]
    plt.close(fig)
    assert hatched, "a thin zone must carry a hatch"
    assert faces == ["#8CBF63"], "and must keep its own band colour"


def test_only_a_zone_below_the_floor_is_hatched():
    """Above the floor the fill is solid; grey is reserved for no attempts."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import scripts.make_shot_chart as shot_chart

    fig = plt.figure(figsize=(7.2, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    gx, gy = np.meshgrid(np.linspace(0, 100, 40), np.linspace(0, 100, 40))
    shot_chart._zone12_fill(ax, gx, gy, gx < 50, "#8CBF63", 2.0, hatched=False)
    assert not any(getattr(c, "hatches", [None])[0] for c in ax.collections)
    plt.close(fig)


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
