"""Post-specific tests for the Bulls assist-connections tables."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.assist_duos import (
    DECADES,
    attach_games_together,
    best_per_season,
    build_pairs,
    display_name,
    display_season,
    render_table,
    slide_height,
    top_by_decade,
    top_overall,
)
from scripts.prototypes.assist_duos_fetch import (
    ASSIST_RE,
    _resolve_assister,
    fold,
    season_label,
    surname_key,
)

GIDDEY, VUCEVIC, BUZELIS, JONES = 1630581, 202696, 1641824, 1630200
ARTEST = 1897
NAMES = {
    GIDDEY: "Josh Giddey",
    VUCEVIC: "Nikola Vučević",
    BUZELIS: "Matas Buzelis",
    JONES: "Tre Jones",
    ARTEST: "Metta World Peace",
}


def _events(rows, season_end_year: int = 2026) -> pd.DataFrame:
    """Expand (assister, scorer, count, shot_value) tuples into one row per basket."""
    records = []
    for assister, scorer, count, value in rows:
        records.extend(
            [
                {
                    "assister_id": assister,
                    "scorer_id": scorer,
                    "shot_value": value,
                    "season_end_year": season_end_year,
                    "season": season_label(season_end_year),
                }
            ]
            * count
        )
    return pd.DataFrame(records)


class TestSeasonLabel:
    def test_maps_end_year_to_nba_season(self):
        assert season_label(2001) == "2000-01"
        assert season_label(2026) == "2025-26"

    def test_display_uses_an_en_dash(self):
        assert display_season("2015-16") == "2015–16"


class TestFold:
    def test_strips_diacritics(self):
        # Descriptions are ASCII while the player-name column keeps accents.
        assert fold("Vučević") == fold("Vucevic") == "VUCEVIC"

    def test_leaves_plain_names_alone(self):
        assert fold("Giddey") == "GIDDEY"


class TestSurnameKey:
    def test_suffix_in_the_name_column_matches_the_bare_description_name(self):
        # The bug this exists for: NBA.com's playerName is "Butler III" while the event
        # description says "(Butler 3 AST)". A fold-only match dropped every assist
        # Jimmy Butler made as a Bull — 417 in 2016-17 — without raising anything.
        assert surname_key("Butler III") == surname_key("Butler") == "BUTLER"

    @pytest.mark.parametrize(
        "name", ["Oubre Jr.", "Oubre Jr", "Oubre Sr.", "Oubre II", "Oubre IV"]
    )
    def test_every_generational_suffix_is_stripped(self, name):
        assert surname_key(name) == "OUBRE"

    def test_diacritics_are_still_folded(self):
        assert surname_key("Vučević") == surname_key("Vucevic") == "VUCEVIC"

    def test_a_hyphenated_surname_survives_intact(self):
        assert surname_key("El-Amin") == "EL-AMIN"

    def test_a_multi_word_surname_survives_intact(self):
        assert surname_key("World Peace") == "WORLD PEACE"

    def test_a_suffix_only_name_is_not_stripped_to_nothing(self):
        assert surname_key("III") == "III"


class TestAssistPattern:
    def test_captures_the_assister_surname(self):
        text = "Buzelis 25' 3PT Jump Shot (12 PTS) (Giddey 4 AST)"
        assert ASSIST_RE.search(text).group(1) == "Giddey"

    def test_captures_a_two_word_surname(self):
        text = "Jones 2' Layup (4 PTS) (El-Amin 3 AST)"
        assert ASSIST_RE.search(text).group(1) == "El-Amin"

    def test_unassisted_basket_has_no_match(self):
        assert ASSIST_RE.search("Giddey 26' 3PT Jump Shot (3 PTS)") is None

    def test_missed_shot_has_no_match(self):
        assert ASSIST_RE.search("MISS Buzelis 25' 3PT Jump Shot") is None


class TestDisplayName:
    def test_uses_the_era_name_before_the_change(self):
        assert display_name("Metta World Peace", ARTEST, 2001) == "Ron Artest"

    def test_uses_the_current_name_after_the_change(self):
        assert display_name("Metta World Peace", ARTEST, 2013) == "Metta World Peace"

    def test_leaves_other_players_untouched(self):
        assert display_name("Josh Giddey", GIDDEY, 2026) == "Josh Giddey"


class TestBuildPairs:
    def test_combines_both_directions(self):
        pairs = build_pairs(
            _events([(GIDDEY, BUZELIS, 10, 2), (BUZELIS, GIDDEY, 4, 3)]), NAMES
        )
        assert len(pairs) == 1
        assert pairs.iloc[0].combined_ast == 14
        assert pairs.iloc[0].combined_pts == 10 * 2 + 4 * 3

    def test_orients_high_volume_passer_first(self):
        pairs = build_pairs(
            _events([(BUZELIS, GIDDEY, 4, 2), (GIDDEY, BUZELIS, 10, 2)]), NAMES
        )
        row = pairs.iloc[0]
        assert (row.high_id, row.high_ast) == (GIDDEY, 10)
        assert (row.low_id, row.low_ast) == (BUZELIS, 4)

    def test_one_way_pair_keeps_a_zero_direction(self):
        row = build_pairs(_events([(GIDDEY, BUZELIS, 6, 2)]), NAMES).iloc[0]
        assert row.low_ast == 0 and row.low_pts == 0 and row.share_high == 1.0

    def test_pairs_never_merge_across_seasons(self):
        # The post ranks single seasons; a duo's 2024-25 and 2025-26 work must stay apart.
        events = pd.concat(
            [
                _events([(GIDDEY, BUZELIS, 10, 2)], season_end_year=2025),
                _events([(GIDDEY, BUZELIS, 7, 2)], season_end_year=2026),
            ]
        )
        pairs = build_pairs(events, NAMES)
        assert len(pairs) == 2
        assert sorted(pairs.combined_ast) == [7, 10]
        assert set(pairs.season) == {"2024-25", "2025-26"}

    def test_ranks_by_combined_assists_across_seasons(self):
        events = pd.concat(
            [
                _events([(GIDDEY, BUZELIS, 5, 2)], season_end_year=2024),
                _events([(JONES, VUCEVIC, 9, 2)], season_end_year=2011),
                _events([(GIDDEY, VUCEVIC, 7, 2)], season_end_year=2026),
            ]
        )
        assert list(build_pairs(events, NAMES).combined_ast) == [9, 7, 5]

    def test_points_break_an_assist_tie(self):
        pairs = build_pairs(
            _events([(GIDDEY, BUZELIS, 5, 2), (JONES, VUCEVIC, 5, 3)]), NAMES
        )
        assert list(pairs.combined_pts) == [15, 10]
        assert pairs.iloc[0].high_id == JONES

    def test_directions_always_sum_to_the_displayed_totals(self):
        pairs = build_pairs(
            _events(
                [(GIDDEY, VUCEVIC, 12, 2), (VUCEVIC, GIDDEY, 5, 3), (JONES, BUZELIS, 8, 2)]
            ),
            NAMES,
        )
        assert (pairs.high_ast + pairs.low_ast == pairs.combined_ast).all()
        assert (pairs.high_pts + pairs.low_pts == pairs.combined_pts).all()

    def test_shot_values_drive_points_not_assist_counts(self):
        row = build_pairs(_events([(GIDDEY, BUZELIS, 10, 3)]), NAMES).iloc[0]
        assert (row.combined_ast, row.combined_pts) == (10, 30)

    def test_a_pair_appears_once_regardless_of_id_order(self):
        pairs = build_pairs(
            _events([(VUCEVIC, GIDDEY, 3, 2), (GIDDEY, VUCEVIC, 3, 2)]), NAMES
        )
        assert len(pairs) == 1

    def test_unknown_player_id_falls_back_to_the_id(self):
        pairs = build_pairs(_events([(GIDDEY, 999, 2, 2)]), {GIDDEY: "Josh Giddey"})
        assert pairs.iloc[0].low_name == "999"

    def test_self_assist_raises_instead_of_doubling_the_total(self):
        with pytest.raises(ValueError):
            build_pairs(_events([(GIDDEY, GIDDEY, 3, 2)]), NAMES)

    def test_missing_season_columns_raise(self):
        bare = pd.DataFrame(
            [{"assister_id": GIDDEY, "scorer_id": BUZELIS, "shot_value": 2}]
        )
        with pytest.raises(ValueError):
            build_pairs(bare, NAMES)


def _multi_season_pairs() -> pd.DataFrame:
    """One connection per season across all three decades, with a decoy in 2006-07."""
    blocks = [
        _events([(GIDDEY, BUZELIS, 12, 2)], season_end_year=2003),
        _events([(JONES, VUCEVIC, 18, 2)], season_end_year=2007),
        _events([(GIDDEY, VUCEVIC, 9, 2)], season_end_year=2007),   # same season, lower
        _events([(GIDDEY, JONES, 15, 2)], season_end_year=2011),
        _events([(VUCEVIC, BUZELIS, 20, 2)], season_end_year=2020),
        _events([(JONES, BUZELIS, 7, 2)], season_end_year=2026),
    ]
    return build_pairs(pd.concat(blocks), NAMES)


class TestDecadeSplit:
    def test_every_decade_gets_a_slide(self):
        slides = top_by_decade(_multi_season_pairs())
        assert tuple(slides) == DECADES

    def test_rows_land_in_the_decade_of_their_season(self):
        slides = top_by_decade(_multi_season_pairs())
        assert set(slides["2000s"].season) == {"2002-03", "2006-07"}
        assert set(slides["2010s"].season) == {"2010-11", "2019-20"}
        assert set(slides["2020s"].season) == {"2025-26"}

    def test_2019_20_belongs_to_the_2010s_not_the_2020s(self):
        # Decade boundaries follow the season *end* year, matching the game-score
        # carousel: 2010-11 through 2019-20 is the 2010s.
        slides = top_by_decade(_multi_season_pairs())
        assert "2019-20" in set(slides["2010s"].season)
        assert "2019-20" not in set(slides["2020s"].season)

    def test_decade_slide_is_capped_at_top_n(self):
        slides = top_by_decade(_multi_season_pairs(), top_n=1)
        assert len(slides["2000s"]) == 1
        assert slides["2000s"].iloc[0].combined_ast == 18

    def test_decade_slide_is_ranked_by_combined_assists(self):
        rows = top_by_decade(_multi_season_pairs())["2000s"]
        assert list(rows.combined_ast) == sorted(rows.combined_ast, reverse=True)


class TestTopOverall:
    def test_ranks_across_every_decade_at_once(self):
        rows = top_overall(_multi_season_pairs(), top_n=3)
        # 2019-20's 20 beats 2006-07's 18 beats 2010-11's 15, decade irrelevant.
        assert list(rows.season) == ["2019-20", "2006-07", "2010-11"]

    def test_caps_at_top_n(self):
        assert len(top_overall(_multi_season_pairs(), top_n=2)) == 2

    def test_asking_for_more_rows_than_exist_returns_what_there_is(self):
        pairs = _multi_season_pairs()
        assert len(top_overall(pairs, top_n=999)) == len(pairs)

    def test_keeps_two_rows_from_one_season_when_both_qualify(self):
        # Unlike best_per_season, an all-time board has no one-row-per-season rule.
        rows = top_overall(_multi_season_pairs(), top_n=6)
        assert list(rows.season).count("2006-07") == 2

    def test_rows_are_renumbered_from_zero(self):
        assert list(top_overall(_multi_season_pairs(), top_n=3).index) == [0, 1, 2]


class TestBestPerSeason:
    def test_keeps_exactly_one_row_per_season(self):
        slides = best_per_season(_multi_season_pairs())
        seasons = [s for rows in slides.values() for s in rows.season]
        assert len(seasons) == len(set(seasons))
        assert set(seasons) == {"2002-03", "2006-07", "2010-11", "2019-20", "2025-26"}

    def test_keeps_the_best_connection_of_a_season(self):
        rows = best_per_season(_multi_season_pairs())["2000s"]
        row = rows[rows.season == "2006-07"].iloc[0]
        assert row.combined_ast == 18

    def test_orders_a_slide_chronologically(self):
        rows = best_per_season(_multi_season_pairs())["2000s"]
        assert list(rows.season) == ["2002-03", "2006-07"]


class TestSlideHeight:
    def test_grows_by_one_row_height_per_row(self):
        assert slide_height(10) - slide_height(9) == pytest.approx(116)

    def test_eight_and_ten_row_slides_differ(self):
        assert slide_height(10) > slide_height(8)


def _logs(rows, season_end_year: int = 2026) -> pd.DataFrame:
    """Build player game logs from (player_id, [game numbers]) pairs."""
    records = [
        {
            "PLAYER_ID": player_id,
            "GAME_ID": f"00{season_end_year}{game:04d}",
            "MIN": 20.0,
            "season_end_year": season_end_year,
        }
        for player_id, games in rows
        for game in games
    ]
    return pd.DataFrame(records)


class TestGamesTogether:
    def test_counts_only_games_both_players_appeared_in(self):
        pairs = build_pairs(_events([(GIDDEY, BUZELIS, 10, 2)]), NAMES)
        logs = _logs([(GIDDEY, [1, 2, 3, 4]), (BUZELIS, [3, 4, 5])])
        assert attach_games_together(pairs, logs).iloc[0].games_together == 2

    def test_a_did_not_play_game_contributes_nothing(self):
        pairs = build_pairs(_events([(GIDDEY, BUZELIS, 10, 2)]), NAMES)
        logs = _logs([(GIDDEY, [1, 2]), (BUZELIS, [3, 4])])
        assert attach_games_together(pairs, logs).iloc[0].games_together == 0

    def test_zero_minute_appearances_do_not_count(self):
        pairs = build_pairs(_events([(GIDDEY, BUZELIS, 10, 2)]), NAMES)
        logs = _logs([(GIDDEY, [1, 2]), (BUZELIS, [1, 2])])
        logs.loc[logs.PLAYER_ID == BUZELIS, "MIN"] = 0.0
        assert attach_games_together(pairs, logs).iloc[0].games_together == 0

    def test_games_are_matched_within_a_season_not_across(self):
        # Shared game *numbers* in different seasons are different games.
        events = pd.concat(
            [
                _events([(GIDDEY, BUZELIS, 4, 2)], season_end_year=2025),
                _events([(GIDDEY, BUZELIS, 6, 2)], season_end_year=2026),
            ]
        )
        logs = pd.concat(
            [
                _logs([(GIDDEY, [1, 2, 3]), (BUZELIS, [1, 2, 3])], season_end_year=2025),
                _logs([(GIDDEY, [1, 2]), (BUZELIS, [1])], season_end_year=2026),
            ]
        )
        result = attach_games_together(build_pairs(events, NAMES), logs)
        by_season = dict(zip(result.season, result.games_together))
        assert by_season == {"2024-25": 3, "2025-26": 1}

    def test_per_game_rate_divides_the_combined_total(self):
        pairs = build_pairs(_events([(GIDDEY, BUZELIS, 10, 2)]), NAMES)
        logs = _logs([(GIDDEY, [1, 2, 3, 4, 5]), (BUZELIS, [1, 2, 3, 4, 5])])
        assert attach_games_together(pairs, logs).iloc[0].ast_per_game == pytest.approx(2.0)

    def test_no_shared_games_gives_no_rate_instead_of_dividing_by_zero(self):
        pairs = build_pairs(_events([(GIDDEY, BUZELIS, 10, 2)]), NAMES)
        logs = _logs([(GIDDEY, [1]), (BUZELIS, [2])])
        assert pd.isna(attach_games_together(pairs, logs).iloc[0].ast_per_game)


class TestSeasonOrdering:
    def test_ascending_is_the_default(self):
        rows = best_per_season(_multi_season_pairs())["2000s"]
        assert list(rows.season) == ["2002-03", "2006-07"]

    def test_descending_reverses_within_each_slide(self):
        rows = best_per_season(_multi_season_pairs(), descending=True)["2000s"]
        assert list(rows.season) == ["2006-07", "2002-03"]

    def test_descending_keeps_the_same_rows(self):
        up = best_per_season(_multi_season_pairs())
        down = best_per_season(_multi_season_pairs(), descending=True)
        for decade in DECADES:
            assert set(up[decade].season) == set(down[decade].season)


class TestRenderSmoke:
    def test_a_slide_renders_end_to_end_with_every_required_column(self, tmp_path):
        pairs = attach_games_together(
            build_pairs(
                _events([(GIDDEY, BUZELIS, 10, 2), (JONES, VUCEVIC, 6, 3)]), NAMES
            ),
            _logs([(GIDDEY, [1, 2]), (BUZELIS, [1, 2]), (JONES, [1]), (VUCEVIC, [1])]),
        )
        out = render_table(pairs, tmp_path / "slide.png", show_season=True)
        assert out.exists() and out.stat().st_size > 5_000

    def test_a_row_without_games_together_is_rejected_before_drawing(self, tmp_path):
        pairs = build_pairs(_events([(GIDDEY, BUZELIS, 10, 2)]), NAMES)
        with pytest.raises((AttributeError, KeyError, ValueError)):
            render_table(pairs, tmp_path / "slide.png", show_season=False)


class TestUniformSlideSize:
    def test_a_short_slide_can_be_padded_to_a_taller_canvas(self):
        assert slide_height(6) < slide_height(10)

    def test_canvas_rows_never_shrinks_a_slide_below_its_own_rows(self, tmp_path):
        # Guards the Canva framing rule: a carousel passes one canvas_rows to every
        # slide, and a slide with more rows than that must not be cropped.
        pairs = attach_games_together(
            build_pairs(
                _events(
                    [(GIDDEY, BUZELIS, 10, 2), (JONES, VUCEVIC, 6, 2),
                     (GIDDEY, VUCEVIC, 4, 2)]
                ),
                NAMES,
            ),
            _logs([(GIDDEY, [1]), (BUZELIS, [1]), (JONES, [1]), (VUCEVIC, [1])]),
        )
        tall = render_table(pairs, tmp_path / "tall.png", show_season=False, canvas_rows=1)
        from PIL import Image

        with Image.open(tall) as image:
            assert image.height >= slide_height(len(pairs))

    def test_every_slide_of_a_carousel_shares_one_height(self, tmp_path):
        from PIL import Image

        pairs = attach_games_together(
            build_pairs(
                pd.concat(
                    [
                        _events([(GIDDEY, BUZELIS, 9, 2)], season_end_year=2003),
                        _events([(JONES, VUCEVIC, 7, 2)], season_end_year=2005),
                        _events([(GIDDEY, JONES, 5, 2)], season_end_year=2026),
                    ]
                ),
                NAMES,
            ),
            pd.concat(
                [
                    _logs([(GIDDEY, [1]), (BUZELIS, [1])], season_end_year=2003),
                    _logs([(JONES, [1]), (VUCEVIC, [1])], season_end_year=2005),
                    _logs([(GIDDEY, [1]), (JONES, [1])], season_end_year=2026),
                ]
            ),
        )
        slides = best_per_season(pairs)
        populated = [rows for rows in slides.values() if len(rows)]
        canvas_rows = max(len(rows) for rows in populated)
        heights = set()
        for name, rows in slides.items():
            if rows.empty:
                continue
            path = render_table(
                rows, tmp_path / f"{name}.png", show_season=True, canvas_rows=canvas_rows
            )
            with Image.open(path) as image:
                heights.add(image.size)
        assert len(heights) == 1


class TestSharedBarScale:
    def test_a_slide_maximum_below_its_own_rows_is_rejected(self, tmp_path):
        # Guards the carousel case: passing a ceiling from the wrong slide set would
        # silently draw bars past the end of the column.
        rows = build_pairs(_events([(GIDDEY, BUZELIS, 40, 2)]), NAMES)
        with pytest.raises(ValueError):
            render_table(
                rows, tmp_path / "slide.png", show_season=False, scale_max=10
            )

    def test_carousel_ceiling_is_the_maximum_across_all_slides(self):
        slides = top_by_decade(_multi_season_pairs())
        ceiling = max(int(r.combined_ast.max()) for r in slides.values() if len(r))
        assert ceiling == 20
        assert ceiling >= max(int(r.combined_ast.max()) for r in slides.values() if len(r))


class TestAssistOrdinal:
    def test_the_running_assist_count_is_captured(self):
        m = ASSIST_RE.search("Deng 18' Jump Shot (12 PTS) (Rose 7 AST)")
        assert (m.group(1), m.group(2)) == ("Rose", "7")

    def test_a_tie_is_broken_by_whose_tally_is_one_short(self):
        row = {"game_id": "g", "assist_ordinal": 3}
        assert _resolve_assister({1, 2}, row, {("g", 1): 2, ("g", 2): 5}) == {1}

    def test_an_unbreakable_tie_is_left_ambiguous(self):
        # Both on zero and it is the first assist: nothing to tell them apart.
        row = {"game_id": "g", "assist_ordinal": 1}
        assert _resolve_assister({1, 2}, row, {}) == {1, 2}

    def test_an_already_unique_candidate_is_untouched(self):
        row = {"game_id": "g", "assist_ordinal": 1}
        assert _resolve_assister({7}, row, {}) == {7}

    def test_tallies_do_not_leak_between_games(self):
        row = {"game_id": "g2", "assist_ordinal": 3}
        assert _resolve_assister({1, 2}, row, {("g1", 1): 2}) == {1, 2}


class TestExactBeforeLoose:
    def test_a_suffix_distinguishes_two_teammates_of_one_surname(self):
        # 2022-23 carried Carlik Jones ("Jones") and Derrick Jones Jr. ("Jones Jr.").
        # NBA.com disambiguates them by suffix, so the folded exact forms must differ.
        assert fold("Jones") != fold("Jones Jr.")

    def test_suffix_stripping_would_collapse_them(self):
        # Which is why the loose index alone cannot resolve a bare "(Jones 1 AST)".
        assert surname_key("Jones") == surname_key("Jones Jr.") == "JONES"

    def test_the_butler_case_still_needs_the_loose_form(self):
        # The opposite direction: the description drops a suffix the column carries.
        assert fold("Butler") != fold("Butler III")
        assert surname_key("Butler") == surname_key("Butler III") == "BUTLER"


class TestDataIsTracked:
    def test_season_data_is_not_written_to_the_ignored_cache(self):
        """The regression that cost fifty minutes of fetching.

        cache/ is gitignored, so a season cache written there is destroyed by routine
        worktree cleanup. These CSVs must land in the post's tracked data/ folder.
        """
        from scripts.prototypes.assist_duos_fetch import CACHE

        parts = CACHE.parts
        assert "cache" not in parts, f"season data is under an ignored cache/: {CACHE}"
        assert "visuals" in parts and "data" in parts, CACHE

    def test_analysis_tables_are_not_written_to_scratch(self):
        """output/ is gitignored; the numbers behind a chart must outlive it."""
        from scripts.prototypes.assist_duos import ALL_TIME_PROJECT, data_dir

        folder = data_dir(ALL_TIME_PROJECT)
        assert "output" not in folder.parts, folder
        assert folder.parts[-1] == "data" and "visuals" in folder.parts, folder
