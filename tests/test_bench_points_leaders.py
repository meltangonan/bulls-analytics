"""Tests for the Bulls bench-points season leaderboard prototype.

The guards here protect the decisions that are invisible in the rendered PNG:
the 1996-97 coverage floor NBA.com enforces by returning nothing rather than an
error, the bench + starters = season reconciliation, the qualification rule that
keeps the board from becoming a Ben Gordon list, the surname spellings NBA.com
strips, and the fit check that stopped a games line from running off the canvas.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from PIL import Image

from scripts.prototypes.bench_points_leaders import _first_row_y as module_first_row_y
from scripts.prototypes.bench_points_leaders import (
    CHART_WIDTH,
    CLAIM_DEPTH,
    DEFAULT_TOP_N,
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    MIN_BENCH_GAME_SHARE,
    NAME_OVERRIDES,
    chart_height,
    _reconcile,
    _row_y,
    build_leaders,
    canva_copy_block,
    last_name,
    render_chart,
    season_label,
    validate,
)


def _split(rows: list[tuple[int, str, int, int]]) -> pd.DataFrame:
    """Build a minimal LeagueDashPlayerStats-shaped frame."""
    return pd.DataFrame(rows, columns=["PLAYER_ID", "PLAYER_NAME", "GP", "PTS"])


def _table(rows: list[dict]) -> pd.DataFrame:
    """Build a bench player-season table spanning the full covered window.

    Every season needs a row or `validate` rejects the window, so the filler
    seasons carry one unremarkable bench player each and the rows under test are
    appended on top.
    """
    filler = [
        {
            "season": season_label(year),
            "season_end_year": year,
            "player_id": 900 + year,
            "player_name": f"Filler {year}",
            "bench_games": 40,
            "total_games": 40,
            "bench_game_share": 1.0,
            "bench_minutes": 400.0,
            "bench_points": 100,
            "bench_points_per_game": 2.5,
            "bench_minutes_per_game": 10.0,
            "total_points": 100,
            "qualified": True,
        }
        for year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1)
    ]
    return pd.DataFrame(filler + rows)


# The real 2026-09-03 leaderboard. Fixtures use it rather than round numbers
# because two guards depend on the actual shape of the distribution: the headline
# margin check compares first-to-second against second-to-tenth, and the games
# line has to fit inside the tenth bar.
REAL_POINTS = [1209, 915, 906, 839, 807, 749, 734, 718, 683, 681]
# The next five qualified seasons, for the fifteen-row version.
REAL_POINTS_15 = REAL_POINTS + [673, 662, 658, 567, 550]


def _leader_rows(points: list[int]) -> list[dict]:
    """Return qualified bench seasons scoring the given point totals."""
    return [
        {
            "season": "2004-05",
            "season_end_year": 2005,
            "player_id": 100 + index,
            "player_name": f"Player {index}",
            "bench_games": 70,
            "total_games": 72,
            "bench_game_share": 70 / 72,
            "bench_minutes": 1700.0,
            "bench_points": value,
            "bench_points_per_game": value / 70,
            "bench_minutes_per_game": 1700.0 / 70,
            "total_points": value + 10,
            "qualified": True,
        }
        for index, value in enumerate(points)
    ]


class TestCoverageWindow:
    def test_window_starts_where_nba_com_has_data(self):
        """1996-97 is the floor of the play-by-play-derived split, not a choice."""
        assert FIRST_SEASON_END_YEAR == 1997
        assert season_label(FIRST_SEASON_END_YEAR) == "1996-97"

    def test_empty_bench_frame_is_an_error_not_an_absence(self):
        """NBA.com returns no rows before 1996-97 and raises nothing itself."""
        with pytest.raises(ValueError, match="no bench rows"):
            _reconcile(
                1991,
                _split([]),
                _split([(1, "A", 50, 500)]),
                _split([(1, "A", 50, 500)]),
            )

    def test_missing_season_fails_validation(self):
        table = _table(_leader_rows(REAL_POINTS))
        short = table[table["season_end_year"] != 2010]
        with pytest.raises(ValueError, match="seasons of bench data"):
            validate(short, build_leaders(short))


class TestReconciliation:
    def test_split_halves_must_sum_to_the_season(self):
        with pytest.raises(ValueError, match="does not equal the season total"):
            _reconcile(
                2005,
                _split([(1, "A", 40, 400)]),
                _split([(1, "A", 40, 400)]),
                _split([(1, "A", 82, 900)]),  # 80 games and 800 points, not 82/900
            )

    def test_a_player_absent_from_one_split_still_reconciles(self):
        """A pure reserve has no starter row at all; that is not a mismatch."""
        _reconcile(
            2005,
            _split([(1, "A", 82, 800)]),
            _split([(2, "B", 82, 1600)]),
            _split([(1, "A", 82, 800), (2, "B", 82, 1600)]),
        )

    def test_bench_games_cannot_exceed_games_played(self):
        rows = _leader_rows(REAL_POINTS)
        rows[0]["bench_games"] = 99
        table = _table(rows)
        with pytest.raises(ValueError, match="more bench games than games played"):
            validate(table, build_leaders(table))


class TestQualification:
    def test_below_the_bar_is_excluded(self):
        """A half-season of bench work does not make a sixth-man season."""
        rows = _leader_rows(REAL_POINTS)
        rows.append(
            {
                **rows[0],
                "player_id": 999,
                "player_name": "Part-time Starter",
                "bench_points": 5000,
                "bench_games": 30,
                "total_games": 82,
                "bench_game_share": 30 / 82,
                "qualified": False,
            }
        )
        leaders = build_leaders(_table(rows))
        assert "Part-time Starter" not in set(leaders["player_name"])
        assert leaders["bench_game_share"].min() >= MIN_BENCH_GAME_SHARE

    def test_leaderboard_is_ranked_and_the_right_length(self):
        table = _table(_leader_rows(REAL_POINTS))
        leaders = build_leaders(table)
        assert len(leaders) == DEFAULT_TOP_N
        assert list(leaders["rank"]) == list(range(1, DEFAULT_TOP_N + 1))
        assert list(leaders["bench_points"]) == sorted(
            leaders["bench_points"], reverse=True
        )


class TestHeadlineClaim:
    def test_the_margin_is_judged_against_the_top_ten_at_any_depth(self):
        """A deeper board widens the tail; the caption's claim is about the ten."""
        ten = _table(_leader_rows(REAL_POINTS))
        fifteen = _table(_leader_rows(REAL_POINTS_15))
        assert (
            validate(ten, build_leaders(ten))["tail_gap"]
            == validate(fifteen, build_leaders(fifteen, 15))["tail_gap"]
        )

    def test_a_board_shallower_than_the_claim_is_refused(self):
        table = _table(_leader_rows(REAL_POINTS))
        with pytest.raises(ValueError, match="at least"):
            build_leaders(table, CLAIM_DEPTH - 1)

    def test_a_shrinking_margin_fails_rather_than_shipping(self):
        """The caption claims the leader's gap beats the rest of the board's spread."""
        table = _table(_leader_rows([900, 880, 860, 840, 820, 800, 780, 760, 740, 720]))
        with pytest.raises(ValueError, match="no longer exceeds"):
            validate(table, build_leaders(table))

    def test_canva_copy_carries_the_window_and_the_threshold(self):
        table = _table(_leader_rows(REAL_POINTS))
        leaders = build_leaders(table)
        block = canva_copy_block(validate(table, leaders))
        assert "1996-97" in block
        assert f"{MIN_BENCH_GAME_SHARE:.0%}" in block
        assert "nba.com" in block


class TestNames:
    def test_generational_suffix_is_dropped(self):
        assert last_name("Bobby Portis Jr.") == "Portis"

    def test_internal_capitals_survive(self):
        assert last_name("Zach LaVine") == "LaVine"

    def test_nba_com_spelling_is_corrected(self):
        """NBA.com stores no diacritics; the graphic is where that becomes wrong."""
        assert NAME_OVERRIDES[202703] == "Nikola Mirotić"
        table = _table(
            [
                {
                    **_leader_rows([REAL_POINTS[0]])[0],
                    "player_id": 202703,
                    "player_name": "Nikola Mirotic",
                }
            ]
            + _leader_rows(REAL_POINTS[1:])
        )
        leaders = build_leaders(table)
        assert leaders.iloc[0]["last_name"] == "Mirotić"


class TestRender:
    def test_chart_is_exported_at_the_declared_size_and_transparent(self, tmp_path, monkeypatch):
        import scripts.prototypes.bench_points_leaders as module

        monkeypatch.setattr(module, "OUT", tmp_path)
        table = _table(_leader_rows(REAL_POINTS))
        path = render_chart(build_leaders(table), "2026-09-03")
        with Image.open(path) as image:
            assert image.size == (CHART_WIDTH, chart_height(DEFAULT_TOP_N))
            assert image.mode == "RGBA"
            assert image.getpixel((2, 2))[3] == 0

    def test_rows_descend_the_page(self):
        height = chart_height(DEFAULT_TOP_N)
        first = module_first_row_y(DEFAULT_TOP_N, height)
        assert _row_y(0, first) > _row_y(DEFAULT_TOP_N - 1, first)
        assert _row_y(DEFAULT_TOP_N - 1, first) > 0

    def test_every_export_height_divides_cleanly_by_the_draft_dpi(self):
        """Matplotlib sizes figures in inches; a ragged height exports short."""
        from bulls.graphics.house import DRAFT_DPI

        for rows in range(CLAIM_DEPTH, 21):
            assert chart_height(rows) % DRAFT_DPI == 0

    def test_the_fifteen_row_version_exports_taller(self, tmp_path, monkeypatch):
        import scripts.prototypes.bench_points_leaders as module

        monkeypatch.setattr(module, "OUT", tmp_path)
        table = _table(_leader_rows(REAL_POINTS_15))
        path = render_chart(build_leaders(table, 15), "2026-09-03")
        assert "top15" in path.name, "The two versions must not overwrite each other."
        with Image.open(path) as image:
            assert image.size == (CHART_WIDTH, chart_height(15))
        assert chart_height(15) > chart_height(DEFAULT_TOP_N)

    def test_a_name_column_that_reaches_the_bars_fails(self, tmp_path, monkeypatch):
        """The name column is set from the data, so its width has to be checked."""
        import scripts.prototypes.bench_points_leaders as module

        monkeypatch.setattr(module, "OUT", tmp_path)
        rows = _leader_rows(REAL_POINTS)
        rows[0]["player_name"] = "Constantin Alexandrescu-Papadopoulos III"
        with pytest.raises(ValueError, match="runs into the bar column"):
            render_chart(build_leaders(_table(rows)), "2026-09-03")

    def test_a_missing_portrait_does_not_break_the_build(self, tmp_path, monkeypatch):
        """Fixture players have no cached portrait; they draw as placeholders."""
        import scripts.prototypes.bench_points_leaders as module

        monkeypatch.setattr(module, "OUT", tmp_path)
        table = _table(_leader_rows(REAL_POINTS))
        assert render_chart(build_leaders(table), "2026-09-03").is_file()

    def test_the_post_carries_the_portraits_it_renders(self):
        """NBA's CDN serves only a silhouette for these two (DESIGN.md §5)."""
        import scripts.prototypes.bench_points_leaders as module

        for player_id, who in ((101126, "Nate Robinson"), (2033, "Marcus Fizer")):
            local = module.PORTRAITS / f"{player_id}.png"
            assert local.is_file(), f"{who}'s hand-sourced portrait is missing."
            assert module.portrait_path(player_id) == local
            assert local.stat().st_size > 50_000, "This looks like the grey silhouette."
        assert (module.PORTRAITS / "README.md").is_file(), (
            "Hand-sourced portraits must carry their provenance."
        )

    def test_a_wide_portrait_is_not_clipped_to_a_square(self):
        """Coby White's hair is wider than the square window would allow."""
        import scripts.prototypes.bench_points_leaders as module

        image = plt.imread(module.portrait_path(1629632))
        band = image[: int(image.shape[0] * module.HEADSHOT_CROP_FRACTION)]
        columns = np.where(band[..., 3].max(axis=0) > 0.04)[0]
        content = int(columns.max() - columns.min())
        square = int(image.shape[0] * module.HEADSHOT_CROP_FRACTION)
        assert content > square, (
            "This test only means something while his content overflows the square."
        )
