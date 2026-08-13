"""Tests for the Bulls scoring age ladder prototype."""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from scripts.prototypes.scoring_age_ladder import (
    FIRST_SEASON_END_YEAR,
    GP_LEFT,
    GP_RIGHT,
    LAST_SEASON_END_YEAR,
    ONE_SLIDE_LAYOUT,
    PPG_LEFT,
    PPG_RIGHT,
    PPG_SCALE_RED,
    PPG_SCALE_RED_YELLOW_GREEN,
    TWO_SLIDE_LAYOUT,
    _ppg_cells,
    age_winners,
    build_working_table,
    display_season_label,
    header_rule_segments,
    historical_headshot_url,
    ppg_fill,
    ppg_text_color,
    player_source_url,
    render_chart,
    row_rule_segments,
    season_label,
    season_marker,
    split_carousel_pages,
    validate_working_table,
)


def _source_rows() -> pd.DataFrame:
    records = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        team_games = {2012: 66, 2020: 65, 2021: 72}.get(end_year, 82)
        for player_id, player, age, games, points in (
            (1000 + end_year, "Prime Leader", 25, team_games, 20 * team_games),
            (2000 + end_year, "Young Runner", 20, team_games, 15 * team_games),
        ):
            records.append(
                {
                    "season_end_year": end_year,
                    "season": display_season_label(end_year),
                    "player_id": player_id,
                    "player": player,
                    "age": age,
                    "games": games,
                    "points": points,
                    "points_per_game": points / games,
                    "team_games": team_games,
                    "team_points": 35 * team_games,
                    "player_source_url": player_source_url(end_year),
                    "team_source_url": "https://example.test/team",
                }
            )
    return pd.DataFrame(records)


def test_season_labels_have_machine_and_display_forms():
    assert season_label(2001) == "2000-01"
    assert display_season_label(2001) == "2000\u201301"


def test_source_url_keeps_the_requested_bulls_season():
    url = player_source_url(2026)
    assert "Season=2025-26" in url
    assert "TeamID=1610612741" in url


def test_shortened_seasons_use_half_of_that_seasons_schedule():
    rows = _source_rows()
    rows.loc[(rows["season_end_year"] == 2012) & (rows["player"] == "Prime Leader"), "games"] = 32
    rows.loc[(rows["season_end_year"] == 2021) & (rows["player"] == "Prime Leader"), "games"] = 36

    table = build_working_table(rows)

    short = table.loc[table["season_end_year"].isin([2012, 2021]) & (table["player"] == "Prime Leader")]
    assert short["minimum_games"].tolist() == [33, 36]
    assert short["qualified"].tolist() == [False, True]


def test_winner_is_ppg_then_total_points_then_games():
    rows = _source_rows()
    rows.loc[rows["player_id"] == 1000 + FIRST_SEASON_END_YEAR, ["age", "points_per_game", "points", "games"]] = [30, 25.0, 1000, 50]
    challenger = rows.loc[rows["player_id"] == 2000 + FIRST_SEASON_END_YEAR].copy()
    challenger["player_id"] = 999999
    challenger["player"] = "Points Tie"
    challenger[["age", "points_per_game", "points", "games"]] = [30, 25.0, 1001, 50]
    challenger["team_points"] += 1001
    rows = pd.concat([rows, challenger], ignore_index=True)
    # Keep the mocked team total reconciled after adding the synthetic row.
    season = FIRST_SEASON_END_YEAR
    rows.loc[rows["season_end_year"] == season, "team_points"] = rows.loc[rows["season_end_year"] == season, "points"].sum()

    winners = age_winners(build_working_table(rows))

    age_30 = winners.loc[winners["age"] == 30].iloc[0]
    assert age_30["player"] == "Points Tie"
    assert age_30["points"] == 1001


def test_validation_covers_every_season_since_2000_and_one_winner_per_age():
    table = build_working_table(_source_rows())

    report = validate_working_table(table)

    assert report["season_count"] == 26
    assert report["age_count"] == 2
    assert report["youngest_age"] == 20
    assert report["oldest_age"] == 25


def test_season_marker_uses_compact_unstarred_label():
    assert season_marker("2000\u201301") == "00\u201301"
    assert season_marker("2025\u201326") == "25\u201326"


def test_retired_players_with_nba_silhouettes_have_explicit_fallbacks():
    assert historical_headshot_url(1724) is None
    assert historical_headshot_url(2430).endswith("/1703.png")
    assert historical_headshot_url(703).endswith("/846.png")
    assert historical_headshot_url(999999) is None


def test_carousel_split_is_two_consecutive_ten_age_pages():
    source = _source_rows().iloc[[0]]
    winners = pd.concat(
        [
            source.assign(age=age, player_id=10_000 + age)
            for age in range(19, 39)
        ],
        ignore_index=True,
    )

    first_page, second_page = split_carousel_pages(winners)

    assert first_page["age"].tolist() == list(range(19, 29))
    assert second_page["age"].tolist() == list(range(29, 39))


def test_ppg_cells_match_clutch_points_color_and_contrast_rules():
    from scripts.prototypes.clutch_table import points_fill, text_color

    for value in (4.1, 16.8, 27.9):
        scoring_fill = ppg_fill(value, 4.1, 27.9, PPG_SCALE_RED)
        clutch_fill = points_fill(value, 4.1, 27.9)
        assert scoring_fill == clutch_fill
        assert ppg_text_color(scoring_fill) == text_color(clutch_fill)


def test_ppg_precedes_gp_in_compact_reference_width_columns():
    assert PPG_LEFT < PPG_RIGHT
    assert PPG_RIGHT == GP_LEFT
    assert GP_LEFT < GP_RIGHT
    assert PPG_RIGHT - PPG_LEFT == 120
    assert GP_RIGHT - GP_LEFT == 120


def test_red_yellow_green_scale_uses_distinct_low_mid_and_high_colors():
    from matplotlib.colors import to_rgb

    minimum = 4.1
    maximum = 27.9
    midpoint = (minimum + maximum) / 2

    np.testing.assert_allclose(
        ppg_fill(minimum, minimum, maximum, PPG_SCALE_RED_YELLOW_GREEN),
        to_rgb("#D64545"),
    )
    np.testing.assert_allclose(
        ppg_fill(midpoint, minimum, maximum, PPG_SCALE_RED_YELLOW_GREEN),
        to_rgb("#F2D46B"),
    )
    np.testing.assert_allclose(
        ppg_fill(maximum, minimum, maximum, PPG_SCALE_RED_YELLOW_GREEN),
        to_rgb("#3FAE63"),
    )


def test_red_yellow_green_scale_separates_4_1_from_9_2_more_than_red_scale():
    low = np.array(ppg_fill(4.1, 4.1, 27.9, PPG_SCALE_RED))
    nine = np.array(ppg_fill(9.2, 4.1, 27.9, PPG_SCALE_RED))
    heat_low = np.array(ppg_fill(4.1, 4.1, 27.9, PPG_SCALE_RED_YELLOW_GREEN))
    heat_nine = np.array(ppg_fill(9.2, 4.1, 27.9, PPG_SCALE_RED_YELLOW_GREEN))

    assert np.linalg.norm(heat_nine - heat_low) > np.linalg.norm(nine - low)


def test_approved_default_ppg_scale_is_red_yellow_green():
    assert ppg_fill(4.1, 4.1, 27.9) == ppg_fill(
        4.1,
        4.1,
        27.9,
        PPG_SCALE_RED_YELLOW_GREEN,
    )


def test_ppg_fill_covers_each_full_square_edged_cell():
    import matplotlib.pyplot as plt

    players = pd.DataFrame({"points_per_game": [10.0, 20.0]})
    fig, ax = plt.subplots()
    _ppg_cells(ax, players, TWO_SLIDE_LAYOUT, 10.0, 20.0)

    assert len(ax.patches) == 2
    for index, patch in enumerate(ax.patches):
        expected_y = (
            TWO_SLIDE_LAYOUT.first_row_y
            - index * TWO_SLIDE_LAYOUT.row_height
            - TWO_SLIDE_LAYOUT.row_height / 2
        )
        assert type(patch) is Rectangle
        assert patch.get_x() == PPG_LEFT
        assert patch.get_y() == expected_y
        assert patch.get_width() == PPG_RIGHT - PPG_LEFT
        assert patch.get_height() == TWO_SLIDE_LAYOUT.row_height
        assert patch.get_clip_path() is None
    first_cell = ax.patches[0]
    assert first_cell.get_y() + first_cell.get_height() == TWO_SLIDE_LAYOUT.header_rule_y
    plt.close(fig)


def test_both_layouts_start_the_first_cell_at_the_table_top():
    for layout in (ONE_SLIDE_LAYOUT, TWO_SLIDE_LAYOUT):
        assert layout.first_row_y + layout.row_height / 2 == layout.header_rule_y


def test_headshots_deliberately_overlap_adjacent_rows():
    for layout in (ONE_SLIDE_LAYOUT, TWO_SLIDE_LAYOUT):
        assert layout.headshot_half_size * 2 > layout.row_height
        assert layout.headshot_rise > 0


def test_heavy_header_rule_is_omitted():
    assert header_rule_segments() == ()


def test_light_row_rules_skip_ppg_but_extend_through_gp():
    assert row_rule_segments() == ((100, 211), (279, PPG_LEFT), (GP_LEFT, GP_RIGHT))



def test_chart_export_is_transparent(tmp_path, monkeypatch):
    from PIL import Image
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(build_working_table(_source_rows()))
    path = render_chart(winners, "2026-08-04", final=False)

    image = Image.open(path)
    assert image.mode == "RGBA"
    assert image.size == (1080, 1110)
    assert image.getpixel((0, 0))[3] == 0
