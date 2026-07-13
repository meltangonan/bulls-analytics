"""Tests for the regular-season Gamebook concept calculations."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prototypes" / "regular_season_gamebook.py"
SPEC = spec_from_file_location("regular_season_gamebook", SCRIPT)
gamebook = module_from_spec(SPEC)
sys.modules[SPEC.name] = gamebook
SPEC.loader.exec_module(gamebook)


def test_four_factors_identify_two_edges_for_each_team():
    factors = gamebook.prepare_factors(gamebook.CHI, gamebook.MEM)

    assert [factor.label for factor in factors] == [
        "SHOT MAKING",
        "BALL SECURITY",
        "SECOND CHANCES",
        "FREE THROWS",
    ]
    assert [factor.bulls_wins for factor in factors] == [True, True, False, False]
    assert factors[0].bulls == pytest.approx(53.623, abs=0.001)
    assert factors[2].opponent == pytest.approx(33.333, abs=0.001)


def test_fingerprint_exposes_the_assisted_field_goal_outlier():
    metrics = gamebook.prepare_fingerprint(gamebook.CHI)
    assisted = next(metric for metric in metrics if metric.label == "ASSISTED-FG RATE")

    assert assisted.value == pytest.approx(46.667, abs=0.001)
    assert assisted.baseline == pytest.approx(67.17)
    assert assisted.percentile == 0.0


def test_shot_quality_separates_location_expectation_from_results():
    zones = gamebook.prepare_quality_zones()

    assert sum(zone.actual_points for zone in zones) == 74
    assert sum(zone.expected_points for zone in zones) == pytest.approx(78.0, abs=0.1)
    assert next(zone for zone in zones if zone.label == "RIM").delta == pytest.approx(-8.2, abs=0.1)
    assert next(zone for zone in zones if zone.label == "ABOVE-BREAK THREES").delta == pytest.approx(3.9, abs=0.1)


def test_contribution_board_applies_minutes_threshold_and_finds_distinct_leaders():
    rows = gamebook.prepare_contributions(gamebook.PLAYERS, gamebook.CHI)

    assert len(rows) == 8
    assert all(row.minutes >= 10 for row in rows)
    assert max(rows, key=lambda row: row.scoring).name == "Caleb Wilson"
    assert max(rows, key=lambda row: row.creation).name == "Kennedy Chandler"
    assert max(rows, key=lambda row: row.rebounding).name == "Malik Williams"
