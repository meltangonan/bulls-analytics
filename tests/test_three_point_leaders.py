"""Tests for the Bulls season three-point-percentage leader prototype.

The guards here protect the decisions that are invisible in the rendered PNG:
the qualification rule, the percentile benchmark, the constant portrait scale
behind a per-player crop override, and the newest-season-first row order that
once pushed a series label onto the bottom portrait.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from scripts.prototypes.three_point_leaders import (
    AXIS_STEP,
    BENCHMARK_PERCENTILE,
    CHART_HEIGHT,
    CHART_WIDTH,
    FIRST_SEASON_END_YEAR,
    HEADSHOT_CROP_FRACTION,
    HEADSHOT_HALF,
    INK,
    LAST_SEASON_END_YEAR,
    MIN_THREE_POINT_ATTEMPTS,
    PLOT_LEFT,
    PLOT_RIGHT,
    SEASON_LABEL_X,
    SERIES_LABEL_DROP,
    _row_y,
    _x,
    axis_bounds,
    build_leaders,
    canva_copy_block,
    display_season,
    last_name,
    portrait_path,
    render_chart,
    season_label,
    top_anchored_headshot,
    validate,
)


def _season_rows(end_year: int, players: list[tuple[int, str, int, int]]) -> list[dict]:
    """Build synthetic Bulls player-seasons from (id, name, 3PM, 3PA)."""
    return [
        {
            "season": season_label(end_year),
            "season_end_year": end_year,
            "player_id": pid,
            "player_name": name,
            "games_played": 70,
            "team_games": 82,
            "three_pm": made,
            "three_pa": att,
            "three_pct": (made / att * 100) if att else float("nan"),
            "qualified": att >= MIN_THREE_POINT_ATTEMPTS,
        }
        for pid, name, made, att in players
    ]


def _league_row(end_year: int, benchmark: float = 41.0) -> dict:
    return {
        "season": season_label(end_year),
        "season_end_year": end_year,
        "team_games": 82,
        "league_three_pm": 30000,
        "league_three_pa": 83000,
        "league_three_pct": 36.1,
        "league_three_pa_per_team_game": 34.2,
        "benchmark_three_pct": benchmark,
        "qualified_shooters": 200,
        "bulls_three_pct": 36.0,
        "bulls_three_pa_per_game": 34.0,
        "bulls_attempt_rank": 12,
    }


def _sixteen_seasons() -> pd.DataFrame:
    rows = []
    for offset, end_year in enumerate(range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1)):
        made = 80 + offset
        rows += _season_rows(end_year, [(offset + 1, f"Player{offset}", made, 200)])
    seasons = pd.DataFrame(rows)
    league = pd.DataFrame(
        [_league_row(e) for e in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1)]
    )
    return build_leaders(seasons, league)


# --- naming ------------------------------------------------------------------


@pytest.mark.parametrize(
    "full,expected",
    [
        ("Zach LaVine", "LaVine"),          # internal capital survives
        ("Doug McDermott", "McDermott"),
        ("D.J. Augustin", "Augustin"),
        ("Jimmy Butler III", "Butler"),     # generational suffix dropped
        ("Otto Porter Jr.", "Porter"),
        ("Nikola Vucevic", "Vucevic"),
    ],
)
def test_last_name_strips_suffixes_and_keeps_capitals(full, expected):
    assert last_name(full) == expected


def test_season_labels():
    assert season_label(2026) == "2025-26"
    assert display_season(2026) == "2025-26"


# --- qualification and leader selection --------------------------------------


def test_leader_is_the_most_accurate_qualifier_not_the_most_accurate_player():
    """A 6-for-10 shooter must not outrank a qualified 40% season."""
    seasons = pd.DataFrame(
        _season_rows(
            2026,
            [
                (1, "Hot Hand", 6, 10),        # 60% on 10 attempts
                (2, "Real Shooter", 80, 200),  # 40% on 200
                (3, "Cold Shooter", 50, 160),
            ],
        )
    )
    leaders = build_leaders(seasons, pd.DataFrame([_league_row(2026)]))
    assert list(leaders["player_name"]) == ["Real Shooter"]
    assert leaders.iloc[0]["qualifiers"] == 2


def test_attempts_exactly_at_the_threshold_qualify():
    seasons = pd.DataFrame(
        _season_rows(2026, [(1, "Edge Case", 56, MIN_THREE_POINT_ATTEMPTS)])
    )
    leaders = build_leaders(seasons, pd.DataFrame([_league_row(2026)]))
    assert leaders.iloc[0]["three_pa"] == MIN_THREE_POINT_ATTEMPTS


def test_no_qualifier_raises_rather_than_dropping_the_season():
    seasons = pd.DataFrame(_season_rows(2026, [(1, "Low Volume", 40, 100)]))
    with pytest.raises(ValueError, match="no Bull reached"):
        build_leaders(seasons, pd.DataFrame([_league_row(2026)]))


def test_exact_tie_raises_rather_than_letting_sort_order_pick():
    seasons = pd.DataFrame(
        _season_rows(2026, [(1, "First", 80, 200), (2, "Second", 80, 200)])
    )
    with pytest.raises(ValueError, match="tie"):
        build_leaders(seasons, pd.DataFrame([_league_row(2026)]))


def test_benchmark_comparison_drives_beat_flag_and_edge():
    seasons = pd.DataFrame(
        _season_rows(2026, [(1, "Above", 88, 200)])  # 44.0%
    )
    leaders = build_leaders(seasons, pd.DataFrame([_league_row(2026, benchmark=41.0)]))
    row = leaders.iloc[0]
    assert bool(row["beat_benchmark"]) is True
    assert row["edge"] == pytest.approx(3.0)

    seasons = pd.DataFrame(_season_rows(2026, [(1, "Below", 76, 200)]))  # 38.0%
    leaders = build_leaders(seasons, pd.DataFrame([_league_row(2026, benchmark=41.0)]))
    assert bool(leaders.iloc[0]["beat_benchmark"]) is False
    assert leaders.iloc[0]["edge"] == pytest.approx(-3.0)


def test_validate_rejects_a_short_season_table():
    seasons = pd.DataFrame(_season_rows(2026, [(1, "Only One", 80, 200)]))
    leaders = build_leaders(seasons, pd.DataFrame([_league_row(2026)]))
    with pytest.raises(ValueError, match="Expected 16 seasons"):
        validate(leaders)


def test_validate_rejects_an_implausible_percentage():
    leaders = _sixteen_seasons()
    leaders.loc[0, "three_pct"] = 95.0
    with pytest.raises(ValueError, match="not a plausible"):
        validate(leaders)


# --- axis ---------------------------------------------------------------------


def test_axis_snaps_outward_and_contains_every_value():
    low, high, ticks = axis_bounds([37.3, 45.1, 40.2])
    assert low <= 37.3 and high >= 45.1
    assert low % AXIS_STEP == 0 and high % AXIS_STEP == 0
    assert ticks[0] == low and ticks[-1] == high
    assert all(round(b - a, 6) == AXIS_STEP for a, b in zip(ticks, ticks[1:]))


def test_axis_widens_when_the_league_average_is_included():
    without = axis_bounds([37.3, 45.1])[0]
    with_league = axis_bounds([34.9, 37.3, 45.1])[0]
    assert with_league < without


def test_x_maps_the_axis_onto_the_plot():
    low, high, _ = axis_bounds([36.0, 46.0])
    assert _x(low, low, high) == pytest.approx(PLOT_LEFT)
    assert _x(high, low, high) == pytest.approx(PLOT_RIGHT)


# --- row order ----------------------------------------------------------------


def test_rows_run_down_the_page():
    assert _row_y(0) > _row_y(1) > _row_y(15)


def test_series_labels_clear_the_last_portrait():
    """The drop must stay derived from the portrait.

    With the newest season on top the bottom row is 2010-11, whose leader sits
    within 0.2 points of the benchmark — so a fixed drop put the benchmark label
    on top of Korver's face the moment the order flipped.
    """
    assert SERIES_LABEL_DROP > HEADSHOT_HALF


# --- portraits ----------------------------------------------------------------


def test_portrait_path_prefers_the_post_copy(tmp_path, monkeypatch):
    import scripts.prototypes.three_point_leaders as mod

    local = tmp_path / "portraits"
    local.mkdir()
    (local / "999.png").write_bytes(b"x")
    monkeypatch.setattr(mod, "PORTRAITS", local)
    assert portrait_path(999) == local / "999.png"
    assert portrait_path(1000) == mod.HEADSHOT_CACHE / "1000.png"


def test_crop_override_holds_the_drawn_scale_constant(tmp_path):
    """A wider crop must be drawn proportionally bigger, not shrunk.

    Dunleavy needs a taller window than the standard 0.68 to clear his chin. If
    that window were drawn into the same square his head would render smaller
    than every other face, so source pixels per drawn pixel is the invariant.
    """
    import matplotlib.pyplot as plt

    portrait = tmp_path / "p.png"
    Image.new("RGBA", (1040, 760), (10, 20, 30, 255)).save(portrait)

    fig, ax = plt.subplots()
    standard = top_anchored_headshot(ax, portrait, 0, 0, HEADSHOT_HALF)
    widened = top_anchored_headshot(
        ax, portrait, 0, 0, HEADSHOT_HALF, crop=HEADSHOT_CROP_FRACTION * 1.1
    )

    def scale(artist, crop):
        x0, x1, _, _ = artist.get_extent()
        source_side = round(min(1040, 760) * crop)
        return (x1 - x0) / source_side

    # The crop side is an integer count of source pixels, so the invariant holds
    # up to that rounding rather than exactly.
    assert scale(standard, HEADSHOT_CROP_FRACTION) == pytest.approx(
        scale(widened, HEADSHOT_CROP_FRACTION * 1.1), rel=5e-3
    )
    plt.close(fig)


def test_missing_portrait_becomes_a_placeholder_not_a_crash(tmp_path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    artist = top_anchored_headshot(ax, tmp_path / "absent.png", 0, 0, HEADSHOT_HALF)
    assert artist is not None
    plt.close(fig)


# --- palette ------------------------------------------------------------------


def test_chart_uses_the_account_black_not_pure_black():
    """DESIGN.md (Color and hierarchy): nothing in a graphic is pure or near-pure black."""
    assert INK == "#242424"


# --- render -------------------------------------------------------------------


def test_render_produces_a_transparent_asset_at_the_declared_size(tmp_path, monkeypatch):
    import scripts.prototypes.three_point_leaders as mod

    monkeypatch.setattr(mod, "OUT", tmp_path)
    path = render_chart(_sixteen_seasons(), "2026-09-01")
    image = Image.open(path)
    assert image.size == (CHART_WIDTH, CHART_HEIGHT)
    assert image.mode == "RGBA"
    assert np.array(image)[:, :, 3].min() == 0, "the chart carries no background"


def test_render_refuses_a_label_that_would_run_off_the_chart(tmp_path, monkeypatch):
    import scripts.prototypes.three_point_leaders as mod

    monkeypatch.setattr(mod, "OUT", tmp_path)
    leaders = _sixteen_seasons()
    leaders.loc[0, "last_name"] = "Vandeweghe-Papagiannis-Antetokounmpo"
    with pytest.raises(ValueError, match="runs off the chart|season column"):
        render_chart(leaders, "2026-09-01")


def test_canva_copy_states_the_threshold_and_the_benchmark():
    leaders = _sixteen_seasons()
    block = canva_copy_block(validate(leaders), leaders)
    assert str(MIN_THREE_POINT_ATTEMPTS) in block
    assert str(BENCHMARK_PERCENTILE) in block
    assert "Chicago-only" in block
    assert "nba.com" in block.lower()
