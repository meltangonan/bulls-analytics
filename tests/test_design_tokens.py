"""Drift alarm for design tokens.

bulls/graphics/house.py is the canonical palette. DESIGN.md, design-system.html,
and bulls/config.py each restate its values by hand; these tests fail the suite
the moment any copy diverges, so the docs can stay hand-authored without
silently going stale.
"""
import re
from pathlib import Path

import pytest
from matplotlib.colors import to_hex

from bulls import config
from bulls.graphics import craft, house

REPO = Path(__file__).resolve().parents[1]
DESIGN_MD = (REPO / "DESIGN.md").read_text()
DESIGN_HTML = (REPO / "design-system.html").read_text()

HOUSE_TOKENS = {
    "RED": house.RED,
    "BULLS_BLACK": house.BULLS_BLACK,
    "INK": house.INK,
    "MUTED": house.MUTED,
    "FAINT": house.FAINT,
    "RULE": house.RULE,
    "SUBTITLE_RULE": house.SUBTITLE_RULE,
    "GRIDLINE": house.GRIDLINE,
    "WHITE": house.WHITE,
}

# design-system.html graphic-spec CSS constants (--g-*) mirror house.py.
HTML_VAR_TO_HOUSE = {
    "--g-red": house.RED,
    "--g-black": house.BULLS_BLACK,
    "--g-ink": house.INK,
    "--g-muted": house.MUTED,
    "--g-faint": house.FAINT,
    "--g-rule": house.RULE,
    "--g-tick": house.SUBTITLE_RULE,
    "--g-grid": house.GRIDLINE,
    "--g-canvas": house.WHITE,
}

# Tokens documented by name in the DESIGN.md §2 table.
NAMED_IN_DESIGN_MD = ["RED", "BULLS_BLACK", "INK", "MUTED", "FAINT", "RULE"]


def _hex_to_rgb(hex_value: str) -> tuple:
    return tuple(int(hex_value[i:i + 2], 16) for i in (1, 3, 5))


@pytest.mark.parametrize("name", sorted(HOUSE_TOKENS))
def test_design_md_mentions_every_house_hex(name):
    hex_value = HOUSE_TOKENS[name].upper()
    assert hex_value in DESIGN_MD.upper(), (
        f"house.{name} = {hex_value} does not appear in DESIGN.md — "
        "update the §2 color table (or house.py) so they agree."
    )


@pytest.mark.parametrize("name", NAMED_IN_DESIGN_MD)
def test_design_md_table_rows_match_house(name):
    row = re.search(rf"\|\s*`{name}`\s*\|\s*`(#[0-9A-Fa-f]{{6}})`", DESIGN_MD)
    assert row, f"DESIGN.md §2 table has no row for `{name}`."
    assert row.group(1).upper() == HOUSE_TOKENS[name].upper(), (
        f"DESIGN.md documents {name} as {row.group(1)} but house.py says "
        f"{HOUSE_TOKENS[name]}."
    )


@pytest.mark.parametrize("var", sorted(HTML_VAR_TO_HOUSE))
def test_design_system_html_spec_constants_match_house(var):
    match = re.search(rf"{var}:\s*(#[0-9A-Fa-f]{{6}})", DESIGN_HTML)
    assert match, f"design-system.html no longer defines {var}."
    assert match.group(1).upper() == HTML_VAR_TO_HOUSE[var].upper(), (
        f"design-system.html sets {var} to {match.group(1)} but house.py says "
        f"{HTML_VAR_TO_HOUSE[var]}."
    )


# Theme dataclass fields that hold a color, in declaration order.
THEME_COLOR_FIELDS = [
    "canvas", "ink", "muted", "faint", "rule", "tick",
    "grid", "accent", "contrast", "band", "trim_a", "trim_b",
]


@pytest.mark.parametrize(
    "theme_name,field",
    [(t, f) for t in sorted(house.THEMES) for f in THEME_COLOR_FIELDS],
)
def test_theme_tokens_match_design_system_html(theme_name, field):
    var = f"--gt-{theme_name}-{field.replace('_', '-')}"
    expected = getattr(house.THEMES[theme_name], field)
    match = re.search(rf"{var}:\s*(#[0-9A-Fa-f]{{6}})", DESIGN_HTML)
    assert match, f"design-system.html no longer defines {var}."
    assert match.group(1).upper() == expected.upper(), (
        f"design-system.html sets {var} to {match.group(1)} but house.py says {expected}."
    )


@pytest.mark.parametrize(
    "theme_name,field",
    [(t, f) for t in sorted(house.THEMES) for f in THEME_COLOR_FIELDS],
)
def test_theme_tokens_documented_in_design_md(theme_name, field):
    expected = getattr(house.THEMES[theme_name], field).upper()
    assert expected in DESIGN_MD.upper(), (
        f"house.THEMES['{theme_name}'].{field} = {expected} does not appear in "
        "DESIGN.md — update the §2 Canvas themes table (or house.py) so they agree."
    )


def test_white_theme_matches_module_constants():
    white = house.THEMES["white"]
    assert white.canvas == house.WHITE
    assert white.ink == house.INK
    assert white.muted == house.MUTED
    assert white.faint == house.FAINT
    assert white.rule == house.RULE
    assert white.tick == house.SUBTITLE_RULE
    assert white.grid == house.GRIDLINE
    assert white.accent == house.RED
    assert white.contrast == house.BULLS_BLACK


def test_default_theme_is_jersey():
    assert house.DEFAULT_THEME is house.THEMES["jersey"]


def test_config_rgb_tuples_match_house():
    assert config.BULLS_RED == _hex_to_rgb(house.RED)
    assert config.BULLS_BLACK == _hex_to_rgb(house.BULLS_BLACK)


def test_magnitude_cmap_endpoints_documented():
    for endpoint in (0.0, 1.0):
        hex_value = to_hex(craft.MAGNITUDE_CMAP(endpoint)).upper()
        assert hex_value in DESIGN_MD.upper(), (
            f"MAGNITUDE_CMAP endpoint {hex_value} is not documented in DESIGN.md §2."
        )
