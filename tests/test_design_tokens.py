"""Keep the active chart palette and legacy config colors consistent."""
import re
from pathlib import Path

import pytest

from bulls import config
from bulls.graphics import house

DESIGN_MD = (Path(__file__).resolve().parents[1] / "DESIGN.md").read_text()


@pytest.mark.parametrize("name", ["BLACK", "RED"])
def test_active_design_palette_matches_house(name):
    row = re.search(rf"\|\s*`{name}`\s*\|\s*`(#[0-9A-Fa-f]{{6}})`", DESIGN_MD)
    assert row, f"DESIGN.md has no color row for {name}."
    assert row.group(1).upper() == getattr(house, name).upper()


def test_config_rgb_tuples_match_house():
    def rgb(value):
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))

    assert config.BULLS_RED == rgb(house.RED)
    assert config.BULLS_BLACK == rgb(house.BULLS_BLACK)
