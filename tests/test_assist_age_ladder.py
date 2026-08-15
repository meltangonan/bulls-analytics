"""Tests for the Bulls assist age ladder prototype."""

from __future__ import annotations

import pandas as pd
import pytest

from scripts.prototypes.assist_age_ladder import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    SEASON_LEADERS_LAYOUT,
    age_winners,
    build_working_table,
    canva_copy_block,
    display_season_label,
    player_source_url,
    season_canva_copy_block,
    season_chronological_canva_copy_block,
    season_winners,
    season_winners_by_year,
    validate_season_winners,
    validate_working_table,
)
from scripts.prototypes.scoring_age_ladder import (
    CHART_HEIGHT,
    METRIC_FILL_ROUNDED_BAND,
    METRIC_FILL_SQUARE_CELLS,
    ONE_SLIDE_LAYOUT,
    PPG_LEFT,
    PPG_RIGHT,
    PPG_SCALE_RED,
    ppg_fill,
    render_chart,
)


def _source_rows() -> pd.DataFrame:
    records = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        team_games = {2012: 66, 2020: 65, 2021: 72}.get(end_year, 82)
        for player_id, player, age, games, assists in (
            (1000 + end_year, "Prime Creator", 25, team_games, 8 * team_games),
            (2000 + end_year, "Young Creator", 20, team_games, 5 * team_games),
        ):
            records.append(
                {
                    "season_end_year": end_year,
                    "season": display_season_label(end_year),
                    "player_id": player_id,
                    "player": player,
                    "age": age,
                    "games": games,
                    "assists": assists,
                    "assists_per_game": assists / games,
                    "team_games": team_games,
                    "team_assists": 13 * team_games,
                    "player_source_url": player_source_url(end_year),
                    "team_source_url": "https://example.test/team",
                }
            )
    return pd.DataFrame(records)


def test_source_url_keeps_requested_bulls_season():
    url = player_source_url(2026)
    assert "Season=2025-26" in url
    assert "TeamID=1610612741" in url


def test_shortened_seasons_use_half_of_that_seasons_schedule():
    rows = _source_rows()
    rows.loc[
        (rows["season_end_year"] == 2012) & (rows["player"] == "Prime Creator"),
        "games",
    ] = 32
    rows.loc[
        (rows["season_end_year"] == 2021) & (rows["player"] == "Prime Creator"),
        "games",
    ] = 36

    table = build_working_table(rows)

    short = table.loc[
        table["season_end_year"].isin([2012, 2021])
        & (table["player"] == "Prime Creator")
    ]
    assert short["minimum_games"].tolist() == [33, 36]
    assert short["qualified"].tolist() == [False, True]


def test_winner_is_apg_then_total_assists_then_games():
    rows = _source_rows()
    season = FIRST_SEASON_END_YEAR
    rows.loc[
        rows["player_id"] == 1000 + season,
        ["age", "assists_per_game", "assists", "games"],
    ] = [30, 10.0, 500, 50]
    challenger = rows.loc[rows["player_id"] == 2000 + season].copy()
    challenger["player_id"] = 999999
    challenger["player"] = "Assist Tie"
    challenger[["age", "assists_per_game", "assists", "games"]] = [30, 10.0, 510, 51]
    rows = pd.concat([rows, challenger], ignore_index=True)
    rows.loc[rows["season_end_year"] == season, "team_assists"] = rows.loc[
        rows["season_end_year"] == season, "assists"
    ].sum()

    winners = age_winners(build_working_table(rows))

    age_30 = winners.loc[winners["age"] == 30].iloc[0]
    assert age_30["player"] == "Assist Tie"
    assert age_30["assists"] == 510


def test_validation_covers_all_seasons_and_reconciles_assists():
    table = build_working_table(_source_rows())

    report = validate_working_table(table)

    assert report["season_count"] == 26
    assert report["age_count"] == 2
    assert report["youngest_age"] == 20
    assert report["oldest_age"] == 25


def test_validation_rejects_team_assist_mismatch():
    table = build_working_table(_source_rows())
    table.loc[table["season_end_year"] == FIRST_SEASON_END_YEAR, "team_assists"] += 1

    try:
        validate_working_table(table)
    except ValueError as error:
        assert str(error) == "Player assists do not reconcile to Bulls team assists."
    else:
        raise AssertionError("Expected assist reconciliation to fail.")


def test_season_winners_select_one_leader_per_season_and_sort_apg_descending():
    rows = _source_rows()
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        mask = (rows["season_end_year"] == end_year) & (rows["player"] == "Prime Creator")
        apg = 6.0 + (end_year - FIRST_SEASON_END_YEAR) / 10
        games = int(rows.loc[mask, "games"].iloc[0])
        assists = round(apg * games)
        rows.loc[mask, ["assists", "assists_per_game"]] = [assists, assists / games]
        season_mask = rows["season_end_year"] == end_year
        rows.loc[season_mask, "team_assists"] = rows.loc[season_mask, "assists"].sum()

    winners = season_winners(build_working_table(rows))
    report = validate_season_winners(build_working_table(rows))

    assert len(winners) == 26
    assert winners["season_end_year"].nunique() == 26
    assert winners["player"].eq("Prime Creator").all()
    assert winners["assists_per_game"].is_monotonic_decreasing
    assert report["season_count"] == 26


def test_season_winner_tie_breaks_on_total_assists_then_games():
    rows = _source_rows()
    season = FIRST_SEASON_END_YEAR
    leader_mask = (rows["season_end_year"] == season) & (rows["player"] == "Prime Creator")
    rows.loc[leader_mask, ["assists_per_game", "assists", "games"]] = [10.0, 500, 50]
    challenger = rows.loc[
        (rows["season_end_year"] == season) & (rows["player"] == "Young Creator")
    ].copy()
    challenger["player_id"] = 999999
    challenger["player"] = "Season Tie"
    challenger[["assists_per_game", "assists", "games"]] = [10.0, 510, 51]
    rows = pd.concat([rows, challenger], ignore_index=True)
    season_mask = rows["season_end_year"] == season
    rows.loc[season_mask, "team_assists"] = rows.loc[season_mask, "assists"].sum()

    winner = season_winners(build_working_table(rows)).loc[
        lambda frame: frame["season_end_year"] == season
    ].iloc[0]

    assert winner["player"] == "Season Tie"
    assert winner["assists"] == 510


def test_season_winners_by_year_run_newest_to_oldest():
    winners = season_winners_by_year(build_working_table(_source_rows()))

    assert winners["season_end_year"].tolist() == list(
        range(LAST_SEASON_END_YEAR, FIRST_SEASON_END_YEAR - 1, -1)
    )


def test_canva_copy_matches_assist_metric_and_scoring_timeframe():
    copy = canva_copy_block(
        {
            "age_count": 20,
            "youngest_age": 19,
            "oldest_age": 38,
            "qualified_count": 275,
            "season_count": 26,
        }
    )

    assert "Bulls assist leaders by age" in copy
    assert "Highest assists per game at every age since 2000" in copy
    assert "2000\u201301 to 2025\u201326" in copy
    assert "Min. 50% team games played" in copy


def test_season_canva_copy_describes_one_leader_per_season():
    copy = season_canva_copy_block(
        {"season_count": 26, "lowest_apg": 4.2, "highest_apg": 9.1}
    )

    assert "Bulls assist leaders by season" in copy
    assert "Highest assists per game by a Bull each season since 2000" in copy
    assert "One qualifying leader per season" in copy
    assert "4.2\u20139.1" in copy


def test_chronological_canva_copy_explains_the_newest_to_oldest_order():
    copy = season_chronological_canva_copy_block(
        {"season_count": 26, "lowest_apg": 4.2, "highest_apg": 9.1}
    )

    assert "newest to oldest" in copy
    assert "One qualifying leader per season" in copy


def test_season_layout_fits_all_26_rows_in_the_same_asset_height():
    bottom = (
        SEASON_LEADERS_LAYOUT.first_row_y
        - 25 * SEASON_LEADERS_LAYOUT.row_height
        - SEASON_LEADERS_LAYOUT.row_height / 2
    )

    assert bottom >= 0
    assert SEASON_LEADERS_LAYOUT.headshot_half_size * 2 > SEASON_LEADERS_LAYOUT.row_height


def test_red_scale_is_a_smooth_linear_gradient():
    low = ppg_fill(4.0, 4.0, 10.0, PPG_SCALE_RED)
    middle = ppg_fill(7.0, 4.0, 10.0, PPG_SCALE_RED)
    high = ppg_fill(10.0, 4.0, 10.0, PPG_SCALE_RED)

    for low_channel, middle_channel, high_channel in zip(low, middle, high):
        assert middle_channel == pytest.approx((low_channel + high_channel) / 2)


def test_shared_renderer_labels_metric_apg_and_uses_assist_output_name(tmp_path, monkeypatch):
    from PIL import Image
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(build_working_table(_source_rows()))
    path = render_chart(
        winners,
        "2026-08-05",
        layout=ONE_SLIDE_LAYOUT,
        metric_column="assists_per_game",
        metric_header="APG",
        output_stem="bulls-assist-age-ladder",
    )

    image = Image.open(path)
    assert path.name == "2026-08-05-bulls-assist-age-ladder-one-slide-draft.png"
    assert image.mode == "RGBA"
    assert image.size == (1080, 1110)
    assert image.getpixel((0, 0))[3] == 0


def test_shared_renderer_supports_season_sorted_table_without_age_column(tmp_path, monkeypatch):
    from PIL import Image
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = season_winners(build_working_table(_source_rows()))
    path = render_chart(
        winners,
        "2026-08-05",
        layout=SEASON_LEADERS_LAYOUT,
        color_scale=PPG_SCALE_RED,
        metric_column="assists_per_game",
        metric_header="APG",
        output_stem="bulls-assist-season-leaders",
        show_age=False,
        headshot_x=120,
        name_x=175,
        row_rule_left=80,
        sort_by=["assists_per_game", "assists", "games", "season_end_year"],
        sort_ascending=[False, False, False, True],
        metric_fill_style=METRIC_FILL_ROUNDED_BAND,
    )

    image = Image.open(path)
    assert path.name == "2026-08-05-bulls-assist-season-leaders-one-slide-draft.png"
    assert image.mode == "RGBA"
    assert image.size == (1080, 1110)

    metric_center = round((PPG_LEFT + PPG_RIGHT) / 2)
    first_divider_y = round(
        CHART_HEIGHT
        - (SEASON_LEADERS_LAYOUT.first_row_y - SEASON_LEADERS_LAYOUT.row_height / 2)
    )
    assert image.getpixel((metric_center, first_divider_y))[3] > 0

    band_top_y = round(
        CHART_HEIGHT
        - (SEASON_LEADERS_LAYOUT.first_row_y + SEASON_LEADERS_LAYOUT.row_height / 2)
    )
    # The shared table renderer now carries the full-width ruler under headers,
    # so the top edge of the heat band is intentionally occupied by that rule.
    assert image.getpixel((round(PPG_LEFT), band_top_y))[3] > 0
    assert image.getpixel((metric_center, band_top_y + 2))[3] > 0


def test_square_metric_cells_keep_square_outer_corners(tmp_path, monkeypatch):
    from PIL import Image
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = season_winners_by_year(build_working_table(_source_rows()))
    path = render_chart(
        winners,
        "2026-08-05",
        layout=SEASON_LEADERS_LAYOUT,
        color_scale=PPG_SCALE_RED,
        metric_column="assists_per_game",
        metric_header="APG",
        output_stem="bulls-assist-season-leaders-chronological",
        show_age=False,
        headshot_x=120,
        name_x=175,
        row_rule_left=80,
        sort_by=["season_end_year"],
        sort_ascending=[False],
        metric_fill_style=METRIC_FILL_SQUARE_CELLS,
    )

    image = Image.open(path)
    band_top_y = round(
        CHART_HEIGHT
        - (SEASON_LEADERS_LAYOUT.first_row_y + SEASON_LEADERS_LAYOUT.row_height / 2)
    )
    assert image.getpixel((round(PPG_LEFT + 2), band_top_y + 1))[3] > 0
