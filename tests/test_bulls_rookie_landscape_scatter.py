"""Tests for the Bulls rookie production-versus-quality scatter."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.prototypes.bulls_rookie_landscape_scatter import (
    FACE_CROP_FRACTION,
    MAX_MARK_RADIUS,
    MIN_FACE_RADIUS,
    MIN_MARK_RADIUS,
    Y_AXES,
    label_choices,
    mark_radii,
    quadrant_split,
)


def test_mark_area_not_radius_scales_with_minutes():
    """A circle twice as wide reads four times as big, so area carries minutes."""
    radii = mark_radii(pd.Series([300.0, 1650.0, 3000.0]))
    assert radii[0] == pytest.approx(MIN_MARK_RADIUS)
    assert radii[-1] == pytest.approx(MAX_MARK_RADIUS)
    midpoint_area = (MIN_MARK_RADIUS ** 2 + MAX_MARK_RADIUS ** 2) / 2
    assert radii[1] ** 2 == pytest.approx(midpoint_area)


def test_mark_radius_survives_a_pool_where_every_rookie_played_the_same_minutes():
    assert np.all(mark_radii(pd.Series([500.0, 500.0])) == MIN_MARK_RADIUS)


def test_a_face_is_never_drawn_below_the_size_it_stays_recognisable_at():
    assert MIN_MARK_RADIUS < MIN_FACE_RADIUS < MAX_MARK_RADIUS
    assert 0.5 < FACE_CROP_FRACTION < 1.0


def test_quadrant_split_uses_the_pool_median():
    assert quadrant_split(pd.Series([1.0, 2.0, 9.0])) == 2.0


def test_label_choices_names_the_extremes_and_never_repeats_a_rookie():
    pool = pd.DataFrame(
        {
            "pra_per_75": np.linspace(10, 30, 20),
            "bpm": np.linspace(-8, 3, 20),
            "minutes": np.linspace(300, 3000, 20),
        }
    )
    picks = label_choices(pool, "pra_per_75", "bpm", count=8)
    assert len(picks) == len(set(picks)) == 8
    assert 19 in picks  # the highest production and BPM season
    assert 0 in picks  # the lowest BPM season


def test_every_offered_y_axis_names_a_real_column_and_a_label():
    for column, label, fmt in Y_AXES.values():
        assert column and label == label.upper()
        assert fmt.startswith("{")


def test_net_rating_on_off_is_not_offered_as_an_axis():
    """It only exists from 2007-08 and tracks minutes, not rookie quality."""
    assert not any("net" in key for key in Y_AXES)
