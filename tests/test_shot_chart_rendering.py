"""Small contracts for shot-chart visual encodings."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "make_shot_chart", ROOT / "scripts" / "make_shot_chart.py")
msc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(msc)


def test_hex_area_is_proportional_to_attempt_volume():
    small = msc._hex_radius_fraction(10, 160)
    middle = msc._hex_radius_fraction(40, 160)
    high = msc._hex_radius_fraction(160, 160)

    assert small < middle < high
    assert middle ** 2 / small ** 2 == pytest.approx(4.0)
    assert high ** 2 / middle ** 2 == pytest.approx(4.0)


def test_hex_radius_caps_extreme_cells_and_handles_empty_input():
    assert msc._hex_radius_fraction(200, 100) == 1.0
    assert msc._hex_radius_fraction(0, 100) == 0.0
    assert msc._hex_radius_fraction(10, 0) == 0.0


def test_hex_table_accepts_a_shared_absolute_volume_cap():
    player = pd.DataFrame({
        "loc_x": [0] * 10,
        "loc_y": [0] * 10,
        "shot_made": [True] * 5 + [False] * 5,
        "shot_type": ["2PT"] * 10,
    })
    league = player.copy()

    _, table = msc.prepare_hex_table({
        "player": player,
        "league": league,
        "hex_size_cap": 40,
    })

    assert table.size_cap_fga.unique().tolist() == [40.0]
    largest = table.loc[table.exact_fga.idxmax()]
    assert largest.radius_fraction == pytest.approx((10 / 40) ** 0.5)


def test_hex_radius_uses_the_larger_scale_at_the_low_volume_end():
    assert msc._hex_radius_fraction(3, 127) == msc.HEX_MIN_RADIUS_FRACTION
    assert msc._hex_radius_fraction(7, 127) == msc.HEX_MIN_RADIUS_FRACTION
    assert msc._hex_radius_fraction(8, 127) > msc.HEX_MIN_RADIUS_FRACTION


def test_full_volume_hexes_deliberately_overlap_on_the_actual_lattice():
    centres = np.array([
        [0.0, 0.0],
        [13.88888892, 17.5],
        [-13.88888892, 17.5],
    ])
    nearest = np.linalg.norm(centres[1] - centres[0])
    radius = msc._hex_base_radius()

    assert 2 * radius > nearest
    assert radius == pytest.approx(15.396, abs=0.001)


def test_hex_extent_keeps_long_shots_that_still_fit_the_drawn_court():
    shots = pd.DataFrame({
        "loc_x": [0, 240, 0],
        "loc_y": [20, 250, 340],
        "shot_distance": [2, 34, 34],
    })
    shown = msc._within_hex_extent(shots)

    assert shown.index.tolist() == [0, 1]
    assert shown.shot_distance.tolist() == [2, 34]


def test_hex_asset_uses_a_tight_vertical_crop():
    assert msc.HEX_CROP_TOP - msc.HEX_CROP_BOTTOM == 895
    assert msc.HEX_CROP_TOP < msc.house.CANVAS_HEIGHT
    assert msc.HEX_CROP_BOTTOM > 0


def test_hex_legend_is_lowered_from_the_near_baseline_placement():
    assert msc.HEX_LEGEND_DY == 110


def test_hex_legend_icons_are_grouped_tightly():
    (small_x, small_r), (large_x, large_r) = msc.HEX_VOLUME_MARKS
    assert large_x - small_x - small_r - large_r == 3
    assert np.diff(msc.HEX_COLOR_CENTERS).tolist() == [28, 28, 28, 28]


def test_hex_color_qualification_is_subject_specific():
    # The chart's calculations have always been subject-specific; the generated
    # Canva note must not call every player's attempts "Bulls attempts."
    source = Path(msc.__file__).read_text()
    assert "{MIN_SMOOTH} {ctx['name']} attempts nearby" in source


def test_hex_requires_three_attempts_in_the_exact_cell():
    """One- and two-shot locations are visual dust, not a repeated shot area."""
    assert msc.MIN_ATT == 3


def test_hex_can_show_one_and_two_shot_cells_as_gray_context():
    attempts = pd.Series([0, 1, 2, 3, 8])

    assert msc._hex_display_mask(attempts, False).tolist() == [False, False, False, True, True]
    assert msc._hex_display_mask(attempts, True).tolist() == [False, True, True, True, True]


def test_hex_uses_five_discrete_symmetric_efficiency_bands():
    colors = [msc._hex_color(diff) for diff in (-0.10, -0.05, 0.0, 0.05, 0.10)]
    assert colors == list(msc.HEX_COLORS)
    assert msc._hex_color(-0.075) == msc.HEX_COLORS[1]
    assert msc._hex_color(0.075) == msc.HEX_COLORS[4]


@pytest.mark.parametrize("draw", [msc._ring_court, msc._ladder_court])
def test_specialized_courts_reuse_the_shared_smooth_restricted_area(draw):
    fig, ax = plt.subplots()
    clip = Rectangle((-500, -500), 1000, 1000)
    draw(ax, 0, 0, 1.0, clip)

    smooth_ds = [patch for patch in ax.patches
                 if isinstance(patch, PathPatch) and patch.get_snap() is False]
    assert len(smooth_ds) == 1
    plt.close(fig)
