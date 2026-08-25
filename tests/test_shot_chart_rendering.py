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


def _Cell(cell: dict):
    """``polar_cells`` returns dicts; the renderers take itertuples rows."""
    from types import SimpleNamespace

    return SimpleNamespace(**cell)


def _viewer_side(px: float, hoop_px: float, tol: float = 1e-6) -> str:
    """Which side of the hoop something sits on, with a centred case.

    The middle sector straddles the hoop line exactly, so a bare ``>`` would let
    floating-point noise decide its side and the comparison would be meaningless.
    """
    delta = px - hoop_px
    if abs(delta) <= tol:
        return "centre"
    return "right" if delta > 0 else "left"


def test_every_polar_cell_is_drawn_on_the_side_its_own_shots_map_to():
    """The cells chart must agree with the shared coordinate mirror.

    The wedges and the dot/fill layers are drawn by different code paths, so
    nothing but a test stops one of them from being mirrored and the other not.
    That happened once already: NBA's Left Corner appeared on the viewer's left
    here while the zone chart put it on the viewer's right, which meant one
    player had two contradictory charts. Each cell is checked by taking a shot
    that genuinely falls inside it and asking whether the pixel it maps to sits
    on the same side of the hoop as the wedge that is supposed to contain it.
    """
    from bulls.analysis import shot_maps as sm
    from bulls.graphics.court import nba_to_basket_bottom_px

    s = 1.0
    hoop_px, _ = nba_to_basket_bottom_px(0.0, 0.0, s, 0.0, 0.0)

    for cell in (c for c in sm.polar_cells() if c["n_sectors"] > 1):
        step = 180.0 / cell["n_sectors"]
        # A point on the sector's own midline, at a radius inside the cell.
        source_angle = np.radians(180.0 - (cell["sector"] + 0.5) * step)
        radius = (cell["r_in"] + cell["r_out"]) / 2 * 10
        loc_x, loc_y = radius * np.cos(source_angle), radius * np.sin(source_angle)
        assert sm.sector_index(loc_x, loc_y, cell["n_sectors"]) == cell["sector"]

        px, _ = nba_to_basket_bottom_px(0.0, 0.0, s, loc_x, loc_y)
        t1, t2 = msc._cell_angles(_Cell(cell))
        wedge_x = np.cos(np.radians((max(t1, -90.0) + min(t2, 270.0)) / 2))

        assert _viewer_side(px, hoop_px) == _viewer_side(wedge_x, 0.0), cell["name"]


def test_polar_cell_labels_sit_inside_their_own_wedge():
    """A number printed opposite its wedge is worse than no number at all."""
    from bulls.graphics.court import nba_to_basket_bottom_px
    from bulls.analysis import shot_maps as sm

    s, hx, hy = 1.0, 0.0, 0.0
    for cell in (c for c in sm.polar_cells() if c["n_sectors"] > 1):
        c = _Cell(cell)
        t1, t2 = msc._cell_angles(c)
        wedge_x = np.cos(np.radians((max(t1, -90.0) + min(t2, 270.0)) / 2))
        label_x, _ = msc._label_anchor(c, hx, hy, s)
        assert _viewer_side(label_x, hx) == _viewer_side(wedge_x, 0.0), cell["name"]


def test_nba_left_corner_lands_on_the_viewer_right_in_the_cells_chart():
    """The concrete case the audit turned up, pinned by name."""
    from bulls.analysis import shot_maps as sm

    left_corner = next(c for c in sm.polar_cells() if c["name"] == "LEFT CORNER 3")
    t1, t2 = msc._cell_angles(_Cell(left_corner))
    assert np.cos(np.radians((max(t1, -90.0) + min(t2, 270.0)) / 2)) > 0
    assert msc._label_anchor(_Cell(left_corner), 0.0, 0.0, 1.0)[0] > 0
