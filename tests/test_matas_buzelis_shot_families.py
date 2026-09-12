"""Classifier, reconciliation and self-creation checks for the Buzelis slides."""
from pathlib import Path

import pandas as pd
import pytest

from bulls.analysis import shot_families as sf
from scripts.prototypes import matas_buzelis_shot_families as slides


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / slides.SLUG / "data"


# --- The classifier ---------------------------------------------------------
def test_floaters_are_matched_before_layups_and_jumpers():
    """NBA writes "Driving Floating Bank Jump Shot"; rule order is what saves it."""
    assert sf.classify("Driving Floating Bank Jump Shot") == "Floaters"
    assert sf.classify("Floating Jump Shot") == "Floaters"
    assert sf.classify("Driving Floating Jump Shot") == "Floaters"


@pytest.mark.parametrize("action,family", [
    ("Cutting Layup Shot", "Layups"),
    ("Driving Finger Roll Layup Shot", "Layups"),
    ("Running Alley Oop Dunk Shot", "Dunks"),
    ("Step Back Jump shot", "Step-backs"),
    ("Pullup Jump shot", "Pull-ups"),
    ("Turnaround Fadeaway shot", "Turnarounds/fades"),
    ("Running Jump Shot", "Running jumpers"),
    ("Hook Shot", "Hooks"),
    ("Tip Layup Shot", "Tip-ins"),
])
def test_representative_action_types_land_in_their_family(action, family):
    assert sf.classify(action) == family


def test_the_bare_jump_shot_is_the_unlabelled_default_not_a_technique():
    """Naming this one wrongly is the post's biggest available error."""
    assert sf.classify("Jump Shot") == sf.UNLABELLED
    assert sf.UNLABELLED == "Standard jumpers"
    assert "catch" not in sf.UNLABELLED.lower()


def test_self_created_is_the_shot_diet_posts_definition():
    """Two posts must not quietly disagree about what self-created counts."""
    assert sf.SELF_CREATED == ("Pull-ups", "Step-backs", "Turnarounds/fades")
    assert set(sf.SELF_CREATED) < set(sf.FAMILIES)


def test_every_family_appears_even_when_the_subject_never_used_it():
    """A dropped row silently redraws the chart with a hole in it."""
    table = sf.family_shares(pd.Series(["Jump Shot", "Cutting Layup Shot"]),
                             pd.Series([1, 0]))
    assert list(table.family) == list(sf.FAMILIES)
    assert int(table[table.family.eq("Hooks")].fga.iloc[0]) == 0
    assert table.share_pct.sum() == pytest.approx(100.0)


def test_a_thin_family_keeps_its_share_and_loses_only_its_rate():
    table = sf.family_shares(pd.Series(["Hook Shot"] * 3 + ["Jump Shot"] * 97),
                             pd.Series([1] * 3 + [0] * 97))
    hooks = table[table.family.eq("Hooks")].iloc[0]
    assert hooks.fga == 3 and hooks.share_pct == pytest.approx(3.0)
    assert not hooks.rated
    assert table[table.family.eq(sf.UNLABELLED)].iloc[0].rated


# --- The post's saved data --------------------------------------------------
def test_labelled_logs_reconcile_to_the_same_totals_as_the_zone_slides():
    """Both halves of the post must describe identically sized seasons."""
    assert slides.OFFICIAL_FGA == {"2024-25": 555, "2025-26": 963}
    for season, expected in slides.OFFICIAL_FGA.items():
        shots = pd.read_csv(
            DATA / f"{season}-matas-buzelis-bulls-shot-families.csv")
        assert len(shots) == expected, season
        slides.reconcile(season, shots)


def test_reconciliation_raises_rather_than_warning():
    with pytest.raises(ValueError, match="labelled rows 2 != Bulls FGA 555"):
        slides.reconcile("2024-25", pd.DataFrame({"x": [1, 2]}))


def test_saved_shares_cover_every_family_and_sum_to_one_hundred():
    shares = pd.read_csv(DATA / "shot-family-shares.csv")
    for season, group in shares.groupby("season"):
        assert list(group.family) == list(sf.FAMILIES), season
        assert group.share_pct.sum() == pytest.approx(100.0, abs=1e-3), season
        assert int(group.fga.sum()) == slides.OFFICIAL_FGA[season], season


def test_the_self_created_share_doubled_between_the_two_seasons():
    """The slide 5 claim, pinned to the saved data."""
    shares = pd.read_csv(DATA / "shot-family-shares.csv")
    totals = {}
    for season, group in shares.groupby("season"):
        sc = group[group.self_created]
        assert set(sc.family) == set(sf.SELF_CREATED), season
        totals[season] = (int(sc.fga.sum()), float(sc.share_pct.sum()))
    assert totals["2024-25"] == (35, pytest.approx(6.3, abs=0.05))
    assert totals["2025-26"] == (124, pytest.approx(12.9, abs=0.05))


def test_the_unlabelled_default_is_the_largest_family_in_both_seasons():
    """It is why the slide cannot be captioned as a breakdown of technique."""
    shares = pd.read_csv(DATA / "shot-family-shares.csv")
    for season, group in shares.groupby("season"):
        top = group.sort_values("fga", ascending=False).iloc[0]
        assert top.family == sf.UNLABELLED, season
        assert bool(top.unlabelled_default)


def test_action_type_audit_lets_a_reader_see_inside_each_bucket():
    """"Standard jumpers" is many raw strings; the post ships which ones."""
    actions = pd.read_csv(DATA / "shot-family-action-types.csv")
    for season, group in actions.groupby("season"):
        assert int(group.fga.sum()) == slides.OFFICIAL_FGA[season], season
    # Every saved row re-derives its own family, so the audit table and the
    # chart cannot drift apart if the rules are ever edited.
    rebuilt = actions.assign(check=actions.ACTION_TYPE.map(sf.classify))
    assert (rebuilt.check == rebuilt.family).all()
    assert actions.ACTION_TYPE.nunique() > 20


# --- The shared rules and the published post that also uses them -------------
def test_the_shared_rules_match_the_published_shot_diet_posts_copy():
    """Two posts classifying the same labels must not drift apart.

    The shot-diet post shipped its own copy of these rules before this module
    existed. Migrating a published renderer is not this post's business, so the
    guard is a test rather than an edit: if either copy changes, this fails and
    whoever changed it has to reconcile both.

    Order is part of the contract, not an implementation detail. That post's
    commit records a flat regex sweep putting "Turnaround Hook Shot" in the
    self-created bucket and inflating its headline by 1.7 points, so hooks,
    floaters and tips must stay ahead of the jumper families.
    """
    from scripts.prototypes import shot_diet_distribution as diet

    assert list(sf.FAMILY_RULES) == [tuple(rule) for rule in diet.FAMILY_RULES]
    assert sf.UNLABELLED == diet.UNLABELLED
    assert sf.SELF_CREATED == diet.SELF_CREATED


def test_a_turnaround_hook_is_a_hook_not_a_self_created_jumper():
    """The exact regression the published post's rule order was fixed for."""
    assert sf.classify("Turnaround Hook Shot") == "Hooks"
    assert sf.classify("Driving Hook Shot") == "Hooks"
    assert "Hooks" not in sf.SELF_CREATED


# --- Tracking corroboration -------------------------------------------------
def test_tracking_corroborates_the_self_created_claim_in_both_seasons():
    """Two systems sharing no failure mode, moving together.

    Tracking reads player and ball position; the families are typed by a scorer.
    They are not required to agree exactly and their boundaries differ, so the
    check is that the gap stays small, not that the counts are identical.
    """
    table = pd.read_csv(DATA / "tracking-corroboration.csv").set_index("season")
    for season in slides.SEASONS:
        row = table.loc[season]
        assert abs(row.gap_points) < 1.0, season
        assert row.total_fga == slides.OFFICIAL_FGA[season]
    # Both measures roughly double, which is the claim the slide makes.
    assert table.loc["2025-26", "tracked_pullup_share_pct"] > \
        1.8 * table.loc["2024-25", "tracked_pullup_share_pct"]
    assert table.loc["2025-26", "label_self_created_share_pct"] > \
        1.8 * table.loc["2024-25", "label_self_created_share_pct"]


def test_tracking_cannot_replace_the_families_because_it_leaves_gaps():
    """Guards against a future pass swapping the chart onto tracked categories.

    Catch-and-shoot plus pull-up cover only about half his attempts. A slide
    built on them alone would silently drop the other half.
    """
    table = pd.read_csv(DATA / "tracking-corroboration.csv")
    assert table.tracked_covered_share_pct.max() < 60.0
    assert table.tracked_covered_share_pct.min() > 40.0


# --- The shared dumbbell grammar --------------------------------------------
def test_the_dumbbell_helper_matches_the_published_shot_diet_chart():
    """One form across the account, not two that merely resemble each other.

    These slides and the published shot-diet slide are the same picture with a
    different comparison, so every value carrying the look is asserted equal to
    that post's. If either side is retuned, this fails and both get retuned.
    """
    from bulls.graphics import dumbbell as db
    from scripts.prototypes import shot_diet_distribution as diet

    assert (db.INK, db.SUBJECT) == (diet.INK, diet.CHI)
    assert db.REFERENCE_GREY == diet.LEAGUE_GREY
    assert db.CONNECTOR_GREY == diet.CONNECTOR_GREY
    assert db.LEADER_GREY == diet.LEADER_GREY
    assert db.GRIDLINE == diet.GRIDLINE
    assert db.FOOTNOTE_GREY == diet.FOOTNOTE_GREY
    assert (db.SUBJECT_DOT, db.REFERENCE_DOT) == (diet.CHI_DOT, diet.LEAGUE_DOT)
    assert db.REFERENCE_RING_WIDTH == diet.LEAGUE_RING_WIDTH
    assert db.REFERENCE_RING_RADIUS == diet.LEAGUE_RING_RADIUS
    assert (db.TYPE_LABEL, db.TYPE_VALUE) == (diet.TYPE_FAMILY, diet.TYPE_VALUE)
    assert (db.TYPE_AXIS, db.TYPE_LEGEND) == (diet.TYPE_AXIS, diet.TYPE_LEGEND)
    assert db.LEADER_GAP == diet.LEADER_GAP
    assert (db.LEGEND_TEXT_GAP, db.LEGEND_DROP) == (diet.LEGEND_TEXT_GAP,
                                                    diet.LEGEND_DROP)
    assert db.AXIS_LABEL_DROP == diet.AXIS_LABEL_DROP


def test_these_slides_share_the_published_charts_row_geometry():
    from scripts.prototypes import shot_diet_distribution as diet

    # Canvas width deliberately differs: these slides carry one extra column for
    # the legend. Every position inside the chart body is the published one.
    assert slides.LABEL_RIGHT == diet.LABEL_RIGHT
    assert (slides.TRACK_LEFT, slides.TRACK_RIGHT) == (diet.TRACK_LEFT, diet.TRACK_RIGHT)
    assert (slides.VALUE_RIGHT, slides.LEADER_END) == (diet.VALUE_RIGHT, diet.LEADER_END)
    assert (slides.ROW_TOP, slides.ROW_STEP) == (diet.ROW_TOP, diet.ROW_STEP)
    assert (slides.HEADER_Y, slides.AXIS_RULE_Y) == (diet.HEADER_Y, diet.AXIS_RULE_Y)
    assert slides.VALUE_HEADER_X == diet.SHARE_HEADER_X


def test_the_connector_stops_at_the_ring_and_vanishes_when_marks_overlap():
    """A stub of bar poking out of a ring reads as a drawing error."""
    from bulls.graphics import dumbbell as db

    drawn = []

    class FakeAx:
        def plot(self, xs, ys, **kw):
            drawn.append(xs)

    ax = FakeAx()
    db.connector(ax, 100.0, 400.0, 0.0)          # reference well to the right
    assert len(drawn) == 1
    assert drawn[0][1] == pytest.approx(400.0 - db.REFERENCE_RING_RADIUS)

    drawn.clear()
    db.connector(ax, 100.0, 100.0 + db.REFERENCE_RING_RADIUS / 2, 0.0)
    assert drawn == []                            # ring already spans the gap


def test_the_axis_clears_the_widest_mark_on_both_slides():
    """A dot sitting on the axis end reads as clipped."""
    shares = pd.read_csv(DATA / "shot-family-shares.csv")
    assert shares.share_pct.max() < slides.FAMILY_AXIS_MAX
    counts = pd.read_csv(DATA / "creation-counts.csv")
    assert counts.fgm.max() < slides.CREATION_AXIS_MAX


# --- Assisted vs unassisted -------------------------------------------------
def test_assisted_and_unassisted_are_a_partition_that_closes():
    table = pd.read_csv(DATA / "assisted-unassisted.csv")
    assert sorted(table.season) == sorted(slides.SEASONS)
    for row in table.itertuples(index=False):
        assert row.pct_unast_fgm + row.pct_ast_fgm == pytest.approx(100.0, abs=0.2)


def test_the_unassisted_share_rose_on_every_shot_type():
    """Slide 5's claim: he created more of his own scoring, twos and threes alike."""
    table = pd.read_csv(DATA / "assisted-unassisted.csv").set_index("season")
    for column in ("pct_unast_fgm", "pct_unast_2pm", "pct_unast_3pm"):
        assert table.loc["2025-26", column] > table.loc["2024-25", column], column
    assert table.loc["2024-25", "pct_unast_fgm"] == pytest.approx(19.4, abs=0.05)
    assert table.loc["2025-26", "pct_unast_fgm"] == pytest.approx(30.3, abs=0.05)


def test_a_broken_partition_raises_rather_than_publishing():
    """Guards the endpoint changing shape under us."""
    slides.assert_partition("2025-26", 30.3, 69.7)
    slides.assert_partition("2025-26", 30.3, 69.8)          # inside tolerance
    with pytest.raises(ValueError, match="not 100"):
        slides.assert_partition("2025-26", 40.0, 30.0)


# --- Recovering the count NBA does not publish ------------------------------
def test_the_unassisted_count_is_recovered_not_estimated():
    """The published share pins exactly one integer, and that is checked."""
    assert slides.recover_unassisted_count(252, 0.194) == 49
    assert slides.recover_unassisted_count(446, 0.303) == 135


def test_recovery_refuses_when_the_share_does_not_pin_one_integer():
    """A coarser share or a larger denominator leaves several candidates.

    Without this guard the arithmetic silently degrades from a recovered figure
    into a guess, which is the failure worth catching: the number would still
    look exact on the page.
    """
    with pytest.raises(ValueError, match="not uniquely determined"):
        slides.recover_unassisted_count(4000, 0.300)
    with pytest.raises(ValueError, match="not uniquely determined"):
        slides.recover_unassisted_count(252, 0.19, places=2)


def test_saved_creation_counts_partition_the_made_field_goals():
    counts = pd.read_csv(DATA / "creation-counts.csv").set_index("season")
    for season in slides.SEASONS:
        row = counts.loc[season]
        assert row.unassisted_fgm + row.assisted_fgm == row.fgm, season
        assert row.unassisted_pct == pytest.approx(
            row.unassisted_fgm / row.fgm * 100, abs=0.05), season


def test_creation_counts_agree_with_the_official_shares_and_the_zone_slides():
    """Slide 5 must describe the same seasons as slides 1 to 4."""
    counts = pd.read_csv(DATA / "creation-counts.csv").set_index("season")
    shares = pd.read_csv(DATA / "assisted-unassisted.csv").set_index("season")
    zones = pd.read_csv(DATA / "zone-chart-summary.csv").set_index("window")
    for season in slides.SEASONS:
        assert counts.loc[season, "fgm"] == zones.loc[season, "fgm"], season
        assert counts.loc[season, "unassisted_pct"] == pytest.approx(
            shares.loc[season, "pct_unast_fgm"], abs=0.1), season


def test_the_unassisted_slice_grew_faster_than_the_whole():
    """Slide 5's reason to exist: the rate rose while the pie also grew."""
    counts = pd.read_csv(DATA / "creation-counts.csv").set_index("season")
    early, late = counts.loc["2024-25"], counts.loc["2025-26"]
    made_growth = late.fgm / early.fgm
    unassisted_growth = late.unassisted_fgm / early.unassisted_fgm
    assert made_growth > 1.7
    assert unassisted_growth > 2.5
    assert unassisted_growth > made_growth


def test_bar_ink_is_chosen_for_the_fill_it_sits_on():
    """White holds on the red; on the pale grey it does not."""
    assert slides.UNASSISTED_INK == "#FFFFFF"
    assert slides.ASSISTED_INK == slides.db.INK
    assert slides.ASSISTED_FILL == slides.db.LEADER_GREY


# --- The legend column ------------------------------------------------------
def test_the_legend_is_a_right_hand_column_not_a_band_of_its_own():
    """Two of these charts stack on one page, so a legend row costs real height."""
    for rows in (2, 10):
        bottom = slides.ROW_TOP + (rows - 1) * slides.ROW_STEP
        foot = bottom + slides.ROW_STEP * slides.db.GRIDLINE_FOOT_FACTOR
        assert slides._canvas_height(rows) == foot + slides.db.AXIS_LABEL_DROP + 46
        # Strictly less than the old layout, which added a legend band below.
        assert slides._canvas_height(rows) < (
            foot + slides.db.AXIS_LABEL_DROP + slides.db.LEGEND_DROP + 70)


def test_the_legend_column_sits_clear_of_the_value_columns():
    assert slides.LEGEND_COL_X > slides.CHANGE_X
    assert slides.LEGEND_COL_X < slides.WIDTH


def test_the_extra_width_is_the_legend_column_and_nothing_else():
    """Widening rather than compressing is what preserved the matched geometry.

    Every x that the published shot-diet chart also defines must be unchanged;
    only the canvas is wider, by one column.
    """
    from scripts.prototypes import shot_diet_distribution as diet

    assert slides.WIDTH > diet.CHART_WIDTH
    assert slides.LEGEND_COL_X >= diet.CHART_WIDTH
    for ours, theirs in ((slides.LABEL_RIGHT, diet.LABEL_RIGHT),
                         (slides.TRACK_LEFT, diet.TRACK_LEFT),
                         (slides.TRACK_RIGHT, diet.TRACK_RIGHT),
                         (slides.VALUE_RIGHT, diet.VALUE_RIGHT),
                         (slides.LEADER_END, diet.LEADER_END)):
        assert ours == theirs


def test_the_legend_is_centred_against_the_rows():
    """It reads as belonging to the chart rather than floating beside it."""
    for rows in (2, 10):
        entries = [("A", lambda a, x, y: None, 22.0),
                   ("B", lambda a, x, y: None, 22.0)]
        first = (slides.ROW_TOP
                 + (slides.ROW_TOP + (rows - 1) * slides.ROW_STEP)) / 2 \
            - slides.LEGEND_LINE_STEP / 2
        middle = first + slides.LEGEND_LINE_STEP / 2
        assert middle == pytest.approx(
            (slides.ROW_TOP + slides.ROW_TOP + (rows - 1) * slides.ROW_STEP) / 2)
        assert len(entries) == 2


def test_a_legend_label_that_overflows_the_canvas_fails_the_render():
    """The column is last on the canvas, so overflow clips silently otherwise."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = slides._canvas(400)
    long_label = "Unassisted" * 6
    with pytest.raises(ValueError, match="past the"):
        slides._legend_column(fig, ax, [(long_label, lambda a, x, y: None, 22.0)], 2)
    # The real labels fit.
    slides._legend_column(fig, ax, [("Unassisted", lambda a, x, y: None, 22.0),
                                    ("Assisted", lambda a, x, y: None, 22.0)], 2)
    plt.close(fig)
