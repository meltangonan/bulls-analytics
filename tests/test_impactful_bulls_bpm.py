"""Post-specific tests for the most-impactful-Bull BPM carousel."""

from __future__ import annotations

import pandas as pd
import pytest

from bulls.data.basketball_reference import parse_advanced_table
from scripts.prototypes.impactful_bulls_bpm import (
    COLUMN_SCALES,
    SCALE_PERCENTILES,
    SCALE_POPULATION,
    SCALE_SAMPLE_SIZE,
    BPM_TIERS,
    DECADE_LAYOUT,
    DECADES,
    FIRST_SEASON_END,
    HEAT_GREEN,
    HEAT_RED,
    LAST_SEASON_END,
    MIN_MINUTES_PER_GAME,
    MIN_TEAM_GAMES_SHARE,
    _norm,
    attach_player_ids,
    canva_copy_block,
    heat_fill,
    heat_text_color,
    ONE_SLIDE_LAYOUT,
    build_working_table,
    select_leaders,
    TWO_SLIDE_LAYOUT,
    half_groups,
    decade_groups,
    slide_height,
    uniform_row_count,
    validate_working_table,
)

PAGE = """
<div id="all_advanced">
<table>
<tr><th scope="col" data-stat="name_display">Player</th>
    <th scope="col" data-stat="games">G</th>
    <th scope="col" data-stat="mp">MP</th></tr>
<tr><td data-stat="name_display"><a href="/x.html">Joakim Noah</a></td>
    <td data-stat="games">80</td><td data-stat="mp">2820</td>
    <td data-stat="obpm">1.7</td><td data-stat="dbpm">3.6</td>
    <td data-stat="bpm">5.3</td><td data-stat="vorp">5.2</td></tr>
<tr><td data-stat="name_display">Nikola Vu&#269;evi&#263;</td>
    <td data-stat="games">82</td><td data-stat="mp">2746</td>
    <td data-stat="obpm">1.9</td><td data-stat="dbpm">0.7</td>
    <td data-stat="bpm">2.7</td><td data-stat="vorp">3.2</td></tr>
<tr><td data-stat="name_display">Bench Guy</td>
    <td data-stat="games">20</td><td data-stat="mp">300</td>
    <td data-stat="obpm">0.1</td><td data-stat="dbpm">0.1</td>
    <td data-stat="bpm">9.9</td><td data-stat="vorp">0.2</td></tr>
<tr><td data-stat="name_display">Team Totals</td>
    <td data-stat="games">82</td><td data-stat="mp">19755</td>
    <td data-stat="obpm"></td><td data-stat="dbpm"></td>
    <td data-stat="bpm"></td><td data-stat="vorp"></td></tr>
</table>
</div>
"""


def _table() -> pd.DataFrame:
    """Two seasons: one with a clear leader, one with a genuine BPM tie."""
    rows = [
        # 2014 -- clear leader, plus an unqualified higher-BPM reserve.
        ("Joakim Noah", 2014, 80, 2820.0, 1.7, 3.6, 5.3, 5.2),
        ("Taj Gibson", 2014, 82, 1500.0, 0.4, 1.2, 1.6, 1.4),
        ("Bench Guy", 2014, 20, 300.0, 0.1, 0.1, 9.9, 0.2),
        # 2009 -- Gordon and Noah both at +1.1; VORP breaks it.
        ("Ben Gordon", 2009, 82, 2999.0, 2.4, -1.3, 1.1, 2.3),
        ("Joakim Noah", 2009, 80, 1938.0, 0.1, 1.1, 1.1, 1.5),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "player_name",
            "season",
            "games",
            "mp",
            "obpm",
            "dbpm",
            "bpm",
            "vorp",
        ],
    )
    frame["season_label"] = frame["season"].map(
        lambda end: f"{end - 1}-{str(end)[2:]}"
    )
    team_games = (frame.groupby("season")["mp"].transform("sum") / 240).round()
    frame["minutes_per_game"] = frame["mp"] / frame["games"]
    frame["games_share"] = frame["games"] / team_games
    frame["qualified"] = (
        (frame["minutes_per_game"] >= MIN_MINUTES_PER_GAME)
        & (frame["games_share"] >= MIN_TEAM_GAMES_SHARE)
    )
    return frame


class TestParseAdvancedTable:
    def test_skips_header_and_team_totals(self):
        rows = parse_advanced_table(PAGE, 2014)
        assert [r["player_name"] for r in rows] == [
            "Joakim Noah",
            "Nikola Vučević",
            "Bench Guy",
        ]

    def test_parses_numeric_fields(self):
        noah = parse_advanced_table(PAGE, 2014)[0]
        assert noah["bpm"] == 5.3
        assert noah["obpm"] == 1.7
        assert noah["dbpm"] == 3.6
        assert noah["vorp"] == 5.2
        assert noah["mp"] == 2820.0
        assert noah["season"] == 2014

    def test_unescapes_html_entities_in_names(self):
        names = [r["player_name"] for r in parse_advanced_table(PAGE, 2023)]
        assert "Nikola Vučević" in names

    def test_raises_when_table_missing(self):
        with pytest.raises(ValueError, match="No Advanced table"):
            parse_advanced_table("<html><body>nothing</body></html>", 2014)


class TestSelectLeaders:
    def test_picks_highest_bpm_among_qualified(self):
        leaders = select_leaders(_table())
        pick = leaders[leaders["season"] == 2014].iloc[0]
        assert pick["player_name"] == "Joakim Noah"

    def test_minutes_gate_excludes_high_bpm_reserve(self):
        """The +9.9 bench guy has the best BPM but only 300 minutes."""
        leaders = select_leaders(_table())
        assert "Bench Guy" not in set(leaders["player_name"])

    def test_bpm_tie_breaks_on_vorp(self):
        pick = select_leaders(_table()).query("season == 2009").iloc[0]
        assert pick["player_name"] == "Ben Gordon"
        assert pick["vorp"] == 2.3

    def test_returns_newest_season_first(self):
        assert list(select_leaders(_table())["season"]) == [2014, 2009]


class TestValidation:
    def test_reports_the_tie_and_who_was_passed_over(self):
        table = _table()
        report = validate_working_table(table, attach_player_ids(select_leaders(table)))
        tie = next(t for t in report["tied_seasons"] if t["season"] == "2008-09")
        assert tie["selected"] == "Ben Gordon"
        assert tie["passed_over"][0]["player"] == "Joakim Noah"
        assert tie["resolved_by"] == "VORP"

    def test_flags_seasons_absent_from_the_selection(self):
        table = _table()
        report = validate_working_table(table, attach_player_ids(select_leaders(table)))
        # The fixture only covers two of the 17 expected seasons.
        assert 2011 in report["missing_seasons"]
        assert 2014 not in report["missing_seasons"]

    def test_resolves_every_player_id(self):
        table = _table()
        leaders = attach_player_ids(select_leaders(table))
        report = validate_working_table(table, leaders)
        assert report["unresolved_player_ids"] == []


class TestHeatFill:
    def test_range_ends_are_the_scale_ends(self):
        from matplotlib.colors import to_rgb

        assert heat_fill(0.8, 0.8, 7.3) == pytest.approx(to_rgb(HEAT_RED))
        assert heat_fill(7.3, 0.8, 7.3) == pytest.approx(to_rgb(HEAT_GREEN))

    def test_midpoint_is_the_yellow_stop(self):
        low, high = 0.0, 10.0
        red, green, blue = heat_fill(5.0, low, high)
        assert red > 0.85 and green > 0.75 and blue < 0.55, "midpoint reads yellow"

    def test_higher_values_move_toward_green(self):
        low, high = 0.8, 7.3
        weak, strong = heat_fill(1.5, low, high), heat_fill(6.5, low, high)
        assert strong[1] - strong[0] > weak[1] - weak[0]

    def test_values_outside_the_range_clamp(self):
        assert heat_fill(-99.0, 0.8, 7.3) == heat_fill(0.8, 0.8, 7.3)
        assert heat_fill(99.0, 0.8, 7.3) == heat_fill(7.3, 0.8, 7.3)

    def test_zero_span_does_not_divide_by_zero(self):
        assert heat_fill(3.0, 3.0, 3.0) is not None

    def test_text_flips_to_white_on_the_dark_red_end(self):
        assert heat_text_color(heat_fill(0.8, 0.8, 7.3)) == "#FFFFFF"
        assert heat_text_color(heat_fill(4.0, 0.8, 7.3)) != "#FFFFFF"


class TestSlideHeight:
    def test_height_grows_one_row_at_a_time(self):
        seven = slide_height(7, DECADE_LAYOUT)
        ten = slide_height(10, DECADE_LAYOUT)
        assert ten - seven == pytest.approx(3 * DECADE_LAYOUT.row_height)

    def test_last_row_clears_the_bottom_edge(self):
        for count in (7, 10):
            height = slide_height(count, DECADE_LAYOUT)
            first_row_y = height - DECADE_LAYOUT.first_row_from_top
            last_bottom = (
                first_row_y
                - (count - 1) * DECADE_LAYOUT.row_height
                - DECADE_LAYOUT.row_height / 2
            )
            assert last_bottom == pytest.approx(DECADE_LAYOUT.bottom_pad)


class TestNormalize:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Nikola Vučević", "nikola vucevic"),
            ("Jimmy Butler III", "jimmy butler"),
            ("Bobby Portis Jr.", "bobby portis"),
            ("P.J. Brown", "pj brown"),
        ],
    )
    def test_normalizes_for_cross_source_joins(self, raw, expected):
        assert _norm(raw) == expected


class TestDecades:
    def test_decades_cover_every_expected_season_exactly_once(self):
        covered = [
            season
            for _, low, high in DECADES
            for season in range(low, high + 1)
        ]
        assert sorted(covered) == list(range(FIRST_SEASON_END, LAST_SEASON_END + 1))
        assert len(covered) == len(set(covered))


class TestCanvaCopyBlock:
    def test_names_the_peak_and_floor_from_the_same_run(self):
        table = _table()
        leaders = attach_player_ids(select_leaders(table))
        report = validate_working_table(table, leaders)
        block = canva_copy_block(leaders, report, "2026-08-05")
        assert "Joakim Noah 2013-14 (+5.3 BPM)" in block
        assert "minutes per game" in block
        assert "Basketball Reference" in block


class TestSeasonLabels:
    def test_graphic_spells_the_first_year_in_full_with_an_en_dash(self):
        """Matches top_game_performances.display_season_label: "2025-26"."""
        table = build_working_table()
        row = table[table["season"] == 2026].iloc[0]
        assert row["season_short"] == "2025\u201326"
        assert "\u2013" in row["season_short"], "graphic label uses an en dash"

    def test_working_table_keeps_the_plain_hyphenated_label(self):
        """Filenames and other surfaces stay ASCII."""
        table = build_working_table()
        row = table[table["season"] == 2026].iloc[0]
        assert row["season_label"] == "2025-26"

    def test_the_first_season_in_range_is_2000_01(self):
        """"Since 2000" is the 2000-01 season, not 1999-00."""
        table = build_working_table()
        assert table["season"].min() == FIRST_SEASON_END == 2001
        row = table[table["season"] == 2001].iloc[0]
        assert row["season_short"] == "2000\u201301"


class TestDecadeSlideLayout:
    def test_the_largest_decade_fits_a_1080x1350_page(self):
        groups = decade_groups(_leaders_fixture())
        assert uniform_row_count(groups) == 10
        assert slide_height(uniform_row_count(groups), DECADE_LAYOUT) <= 1350

    def test_every_slide_renders_at_the_same_canvas_height(self):
        """A 6-row slide must paste at the same size as a 10-row one."""
        groups = decade_groups(_leaders_fixture())
        capacity = uniform_row_count(groups)
        heights = {slide_height(capacity, DECADE_LAYOUT) for _ in groups}
        assert len(heights) == 1

    def test_halves_are_even_and_cover_every_season(self):
        table = _leaders_fixture()
        groups = half_groups(table)
        assert len(groups) == 2
        assert len({len(rows) for _, rows in groups}) == 1, "both halves equal"
        covered = sorted(s for _, rows in groups for s in rows["season"])
        assert covered == sorted(table["season"])

    def test_halves_run_newest_first_within_and_across_slides(self):
        groups = half_groups(_leaders_fixture())
        first, second = (rows for _, rows in groups)
        assert first["season"].is_monotonic_decreasing
        assert second["season"].is_monotonic_decreasing
        assert first["season"].min() > second["season"].max()

    def test_thirteen_rows_fit_a_page_at_the_halves_pitch(self):
        assert slide_height(13, TWO_SLIDE_LAYOUT) <= 1350
        assert slide_height(13, DECADE_LAYOUT) > 1350, "why the pitch shrank"

    def test_both_split_modes_size_every_slide_the_same(self):
        table = _leaders_fixture()
        for groups in (half_groups(table), decade_groups(table)):
            capacity = uniform_row_count(groups)
            assert capacity == max(len(rows) for _, rows in groups)

    def test_the_headline_stat_is_body_size_and_carries_weight_by_bold(self):
        """Matches top_game_performances: gmsc_font_size == value_font_size."""
        assert DECADE_LAYOUT.bpm_font_size == DECADE_LAYOUT.value_font_size == 16

    def test_faces_are_taller_than_their_row_in_both_layouts(self):
        """The overlap is deliberate -- it buys a bigger face."""
        for layout in (ONE_SLIDE_LAYOUT, DECADE_LAYOUT):
            assert 2 * layout.headshot_half_size > layout.row_height


class TestHeaderRule:
    def test_the_rule_sits_between_the_labels_and_the_first_row(self):
        for layout in (ONE_SLIDE_LAYOUT, DECADE_LAYOUT):
            first_row_top = layout.first_row_from_top - layout.row_height / 2
            assert layout.header_from_top < layout.header_rule_from_top
            assert layout.header_rule_from_top <= first_row_top


class TestPercentileCalibratedScales:
    """Scales come from the league distribution, not from tier labels."""

    # Percentiles measured over 3,036 qualified player-seasons, 2009-10 to
    # 2025-26. Used here to assert the scale ends match what was measured.
    P05 = {"bpm": -3.0, "obpm": -2.5, "dbpm": -1.7}
    P99 = {"bpm": 9.2, "obpm": 7.6, "dbpm": 3.0}

    def test_each_column_spans_its_own_measured_percentiles(self):
        for column, (low, high) in COLUMN_SCALES.items():
            assert low == self.P05[column]
            assert high == self.P99[column]

    def test_the_floor_sits_below_replacement_level(self):
        """10% of qualified players are below -2.30 BPM, so -2.0 clamped them."""
        assert COLUMN_SCALES["bpm"][0] < -2.0

    def test_a_bottom_quartile_season_is_not_painted_as_the_worst(self):
        """-1.1 BPM is the 25th percentile; it must not read as near-floor."""
        quartile = heat_fill(-1.1, *COLUMN_SCALES["bpm"])
        floor = heat_fill(COLUMN_SCALES["bpm"][0], *COLUMN_SCALES["bpm"])
        assert quartile != floor
        assert quartile[1] > floor[1], "it should have moved toward yellow"

    def test_the_median_qualified_season_reads_mid_scale(self):
        """+0.4 BPM is the median; it should not read as good or bad."""
        red, green, _ = heat_fill(0.4, *COLUMN_SCALES["bpm"])
        assert red > 0.7 and green > 0.4, "median lands in the warm middle"

    def test_dbpm_stays_the_narrowest_column(self):
        widths = {c: hi - lo for c, (lo, hi) in COLUMN_SCALES.items()}
        assert widths["dbpm"] < widths["obpm"] < widths["bpm"]

    def test_the_ceiling_keeps_great_and_historic_seasons_apart(self):
        """Butler +7.3, Rose +6.8 and Noah +5.3 must not all clamp to green."""
        fills = {v: heat_fill(v, *COLUMN_SCALES["bpm"]) for v in (5.3, 6.8, 7.3)}
        assert len(set(fills.values())) == 3

    def test_the_calibration_is_documented_for_the_footnote(self):
        assert "1,500+ minutes" in SCALE_POPULATION
        assert SCALE_PERCENTILES == (5, 99)
        assert SCALE_SAMPLE_SIZE > 3000

    def test_reference_tiers_are_retained_for_the_explainer(self):
        assert (0.0, "league average") in BPM_TIERS
        assert (-2.0, "replacement level") in BPM_TIERS


def _leaders_fixture() -> pd.DataFrame:
    """One synthetic leader per season across the full window."""
    seasons = list(range(FIRST_SEASON_END, LAST_SEASON_END + 1))
    frame = pd.DataFrame({"season": seasons})
    frame["season_label"] = frame["season"].map(
        lambda end: f"{end - 1}-{str(end)[2:]}"
    )
    return frame.sort_values("season", ascending=False).reset_index(drop=True)


class TestQualificationGate:
    """A rotation-sized role, held for most of the season."""

    def test_the_gate_has_both_a_rate_and_an_availability_condition(self):
        assert MIN_MINUTES_PER_GAME == 20.0
        assert MIN_TEAM_GAMES_SHARE == 0.50

    def test_a_flat_minutes_floor_would_tighten_in_a_shortened_season(self):
        """1,500 minutes asks 18.3 mpg over 82 games but 23.1 over 65."""
        assert 1500 / 82 == pytest.approx(18.3, abs=0.1)
        assert 1500 / 65 == pytest.approx(23.1, abs=0.1)

    def test_a_lockout_starter_qualifies(self):
        """Rose 2011-12: 39 of 66 games at 35.3 mpg, cut by a flat floor."""
        assert 1375 / 39 >= MIN_MINUTES_PER_GAME
        assert 39 / 66 >= MIN_TEAM_GAMES_SHARE

    def test_a_traded_starter_qualifies(self):
        """Brad Miller 2001-02: 48 of 82 games at 29.0 mpg."""
        assert 1391 / 48 >= MIN_MINUTES_PER_GAME
        assert 48 / 82 >= MIN_TEAM_GAMES_SHARE

    def test_a_short_cameo_is_excluded_on_availability(self):
        """Metta World Peace 2001-02: 30.5 mpg but only 27 of 82 games."""
        assert 823 / 27 >= MIN_MINUTES_PER_GAME, "the rate alone would pass"
        assert 27 / 82 < MIN_TEAM_GAMES_SHARE, "availability is what stops him"

    def test_a_low_minute_regular_is_excluded_on_rate(self):
        """Shaquille Harrison 2019-20: 43 of 65 games but 11.3 mpg.

        Games alone would have handed him the 2019-20 row.
        """
        assert 43 / 65 >= MIN_TEAM_GAMES_SHARE, "availability alone would pass"
        assert 484 / 43 < MIN_MINUTES_PER_GAME, "the rate is what stops him"

    def test_a_four_game_cameo_is_excluded(self):
        """JaKarr Sampson 2018-19: 127 minutes in 4 games.

        Minutes-per-game alone would have handed him the 2018-19 row.
        """
        assert 4 / 81 < MIN_TEAM_GAMES_SHARE
