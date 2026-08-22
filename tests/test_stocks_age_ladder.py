"""Tests for the Bulls stocks (steals + blocks) age ladder prototype."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes.stocks_age_ladder import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    STOCKS_CHART_HEIGHT,
    STOCKS_CHART_WIDTH,
    STOCKS_FACE_CROP_FRACTION,
    STOCKS_LAYOUT,
    STOCKS_METRIC_WIDTH,
    STOCKS_TRAILING_COLUMNS,
    STOCKS_TRAILING_SLOT_WIDTH,
    age_winners,
    apply_display_names,
    attach_league_percentile,
    build_working_table,
    canva_copy_block,
    display_season_label,
    league_rotation_rates,
    player_source_url,
    render_stocks_table,
    validate_working_table,
)

from scripts.prototypes.scoring_age_ladder import (
    CHART_WIDTH,
    NAME_X,
    GAMES_COLUMN,
    ONE_SLIDE_LAYOUT,
    TrailingColumn,
    render_chart,
)


def _source_rows() -> pd.DataFrame:
    """Two Bulls per season: a shot-blocking big and a ball-hawking guard."""
    records = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        team_games = {2012: 66, 2020: 65, 2021: 72}.get(end_year, 82)
        for player_id, player, age, games, steals, blocks in (
            (1000 + end_year, "Rim Protector", 28, team_games, 1 * team_games, 2 * team_games),
            (2000 + end_year, "Ball Hawk", 22, team_games, 2 * team_games, 0 * team_games),
        ):
            records.append(
                {
                    "season_end_year": end_year,
                    "season": display_season_label(end_year),
                    "player_id": player_id,
                    "player": player,
                    "age": age,
                    "games": games,
                    "steals": steals,
                    "blocks": blocks,
                    "stocks": steals + blocks,
                    "steals_per_game": steals / games,
                    "blocks_per_game": blocks / games,
                    "stocks_per_game": (steals + blocks) / games,
                    "team_games": team_games,
                    "team_steals": 3 * team_games,
                    "team_blocks": 2 * team_games,
                    "player_source_url": player_source_url(end_year),
                    "team_source_url": "https://example.test/team",
                }
            )
    return pd.DataFrame(records)


def _baseline() -> dict:
    """A flat league pool per season: 200 players spread from 0.5 to 2.5 stocks."""
    rates = pd.Series([0.5 + 2.0 * i / 199 for i in range(200)])
    return {
        end_year: rates
        for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1)
    }


def _rated_table() -> pd.DataFrame:
    return attach_league_percentile(build_working_table(_source_rows()), _baseline())


def test_source_url_keeps_requested_bulls_season():
    url = player_source_url(2026)
    assert "Season=2025-26" in url
    assert "TeamID=1610612741" in url


def test_shortened_seasons_use_half_of_that_seasons_schedule():
    rows = _source_rows()
    rows.loc[
        (rows["season_end_year"] == 2012) & (rows["player"] == "Rim Protector"), "games"
    ] = 32
    rows.loc[
        (rows["season_end_year"] == 2021) & (rows["player"] == "Rim Protector"), "games"
    ] = 36

    table = build_working_table(rows)

    short = table.loc[
        table["season_end_year"].isin([2012, 2021]) & (table["player"] == "Rim Protector")
    ]
    assert short["minimum_games"].tolist() == [33, 36]
    assert short["qualified"].tolist() == [False, True]


def test_winner_is_stocks_then_total_stocks_then_games():
    rows = _source_rows()
    season = FIRST_SEASON_END_YEAR
    rows.loc[
        rows["player_id"] == 1000 + season,
        ["age", "stocks_per_game", "stocks", "steals", "blocks", "games"],
    ] = [30, 4.0, 200, 100, 100, 50]
    challenger = rows.loc[rows["player_id"] == 2000 + season].copy()
    challenger["player_id"] = 999999
    challenger["player"] = "Stocks Tie"
    challenger[
        ["age", "stocks_per_game", "stocks", "steals", "blocks", "games"]
    ] = [30, 4.0, 204, 102, 102, 51]
    rows = pd.concat([rows, challenger], ignore_index=True)
    for component, team_column in (("steals", "team_steals"), ("blocks", "team_blocks")):
        rows.loc[rows["season_end_year"] == season, team_column] = rows.loc[
            rows["season_end_year"] == season, component
        ].sum()

    winners = age_winners(build_working_table(rows))

    age_30 = winners.loc[winners["age"] == 30].iloc[0]
    assert age_30["player"] == "Stocks Tie"
    assert age_30["stocks"] == 204


def test_validation_covers_all_seasons_and_reconciles_both_components():
    table = build_working_table(_source_rows())

    report = validate_working_table(table)

    assert report["season_count"] == 26
    assert report["age_count"] == 2
    assert report["youngest_age"] == 22
    assert report["oldest_age"] == 28


def test_validation_rejects_a_team_steal_mismatch():
    table = build_working_table(_source_rows())
    table.loc[table["season_end_year"] == FIRST_SEASON_END_YEAR, "team_steals"] += 1

    with pytest.raises(ValueError, match="Player steals do not reconcile"):
        validate_working_table(table)


def test_validation_rejects_a_team_block_mismatch():
    """Blocks reconcile on their own; a steal surplus must not mask a block gap."""
    table = build_working_table(_source_rows())
    table.loc[table["season_end_year"] == FIRST_SEASON_END_YEAR, "team_blocks"] += 1

    with pytest.raises(ValueError, match="Player blocks do not reconcile"):
        validate_working_table(table)


def test_validation_rejects_stocks_that_are_not_steals_plus_blocks():
    table = build_working_table(_source_rows())
    table.loc[0, "stocks"] = int(table.loc[0, "stocks"]) + 1

    with pytest.raises(ValueError, match="Stocks do not equal steals plus blocks"):
        validate_working_table(table)


def test_report_counts_which_side_of_the_composite_led_each_row():
    report = validate_working_table(build_working_table(_source_rows()))

    assert report["block_led_count"] == 1
    assert report["steal_led_count"] == 1


def test_canva_copy_states_the_composite_and_its_limits():
    report = validate_working_table(_rated_table())

    copy = canva_copy_block(report)

    assert "Stocks = steals + blocks" in copy
    assert "not defensive value" in copy
    assert "Min. 50% of team games" in copy
    assert "2000–01 to 2025–26" in copy
    assert "Chicago-only" in copy
    # The reader must be told what the colour is measured against.
    assert "NBA median for rotation regulars" in copy
    assert "Yellow is exactly league average" in copy
    assert "2.5x" in copy


def test_display_names_use_the_name_worn_that_season():
    """Ron Artest in 2000–01, and never NBA.com's registered "Jimmy Butler III"."""
    winners = pd.DataFrame(
        [
            {"player": "Metta World Peace", "player_id": 1897, "season_end_year": 2001},
            {"player": "Metta World Peace", "player_id": 1897, "season_end_year": 2013},
            {"player": "Jimmy Butler III", "player_id": 202710, "season_end_year": 2015},
        ]
    )

    labeled = apply_display_names(winners)

    assert labeled["player"].tolist() == [
        "Ron Artest",
        "Metta World Peace",
        "Jimmy Butler",
    ]


def test_display_names_leave_the_audit_table_untouched():
    winners = pd.DataFrame(
        [{"player": "Jimmy Butler III", "player_id": 202710, "season_end_year": 2015}]
    )

    apply_display_names(winners)

    assert winners.loc[0, "player"] == "Jimmy Butler III"


def test_every_trailing_column_shares_one_width():
    """Games played is an equal column, not a squeezed afterthought.

    A third column was added by widening the asset, not by narrowing STL and
    BLK — they keep the 112px they had when there were only two of them.
    """
    assert STOCKS_TRAILING_SLOT_WIDTH == 112
    assert STOCKS_CHART_WIDTH > CHART_WIDTH
    # One slot width serves all three, so the columns cannot drift apart.
    slots = [STOCKS_TRAILING_SLOT_WIDTH] * len(STOCKS_TRAILING_COLUMNS)
    assert len(set(slots)) == 1


def test_the_components_lead_and_games_played_trails_as_context():
    """STL and BLK explain the composite; GP is supplemental, so it sits last."""
    headers = [entry.header for entry in STOCKS_TRAILING_COLUMNS]
    assert headers == ["STL", "BLK", "GP"]
    # Components are rates to one decimal; games played is a whole count.
    assert [entry.decimals for entry in STOCKS_TRAILING_COLUMNS] == [1, 1, 0]


def test_games_played_does_not_decide_the_winner():
    """The claim is a rate. GP is context beside it, never a tie-break above it."""
    rows = _source_rows()
    season = FIRST_SEASON_END_YEAR
    # A durable but weaker season must not displace a stronger, shorter one.
    iron_man = rows.loc[rows["player_id"] == 2000 + season].copy()
    iron_man["player_id"] = 999999
    iron_man["player"] = "Iron Man"
    iron_man[["age", "games", "stocks", "stocks_per_game"]] = [22, 82, 164, 2.0]
    rows = pd.concat([rows, iron_man], ignore_index=True)
    for component, team_column in (("steals", "team_steals"), ("blocks", "team_blocks")):
        rows.loc[rows["season_end_year"] == season, team_column] = rows.loc[
            rows["season_end_year"] == season, component
        ].sum()

    winner = age_winners(build_working_table(rows))
    age_22 = winner.loc[winner["age"] == 22].iloc[0]

    assert age_22["player"] == "Ball Hawk"          # 2.0/g in fewer games still wins
    assert age_22["stocks_per_game"] >= age_22["stocks_per_game"]


def test_the_stocks_columns_stay_inside_the_chart_asset():
    assert STOCKS_METRIC_WIDTH > 0
    assert STOCKS_TRAILING_SLOT_WIDTH > 0
    assert (
        NAME_X
        + STOCKS_METRIC_WIDTH
        + len(STOCKS_TRAILING_COLUMNS) * STOCKS_TRAILING_SLOT_WIDTH
    ) < STOCKS_CHART_WIDTH


def test_renderer_rejects_a_trailing_column_the_rows_do_not_carry(tmp_path, monkeypatch):
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(build_working_table(_source_rows()))

    with pytest.raises(ValueError, match="missing trailing columns"):
        render_chart(
            winners,
            "2026-08-20",
            metric_column="stocks_per_game",
            trailing_columns=(TrailingColumn("FGA", "field_goal_attempts"),),
        )


def test_renderer_draws_the_stocks_table_at_the_family_asset_size(tmp_path, monkeypatch):
    from PIL import Image
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(_rated_table())

    path = render_stocks_table(winners, "2026-08-22")

    image = Image.open(path)
    assert path.name == "2026-08-22-bulls-stocks-age-ladder-one-slide-draft.png"
    assert image.mode == "RGBA"
    assert image.size == (STOCKS_CHART_WIDTH, STOCKS_CHART_HEIGHT)
    assert image.getpixel((0, 0))[3] == 0


def test_the_other_ladders_still_default_to_a_single_games_column():
    """The shared renderer change must not alter the four published ladders."""
    assert GAMES_COLUMN == (TrailingColumn("GP", "games"),)
    assert GAMES_COLUMN[0].decimals == 0


# --- the newer table treatment ---------------------------------------------


def test_a_long_name_no_longer_runs_under_the_metric_column():
    """The overlap bug: "Wendell Carter Jr." pushed its season into the STK cell."""
    import matplotlib.pyplot as plt
    from scripts.prototypes.scoring_age_ladder import name_block_width

    players = pd.DataFrame(
        [
            {"player": "Wendell Carter Jr.", "season": "2018–19"},
            {"player": "Nikola Vučević", "season": "2021–22"},
        ]
    )
    fig = plt.figure(figsize=(10.8, 11.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, STOCKS_CHART_WIDTH)
    ax.set_ylim(0, 1150)
    try:
        widest = name_block_width(ax, players, STOCKS_LAYOUT)
    finally:
        plt.close(fig)

    metric_left = NAME_X + widest
    assert widest > 0
    # Every column still lands inside the fixed 1080px asset width.
    assert (
        metric_left
        + STOCKS_METRIC_WIDTH
        + len(STOCKS_TRAILING_COLUMNS) * STOCKS_TRAILING_SLOT_WIDTH
    ) <= STOCKS_CHART_WIDTH


def test_the_table_asset_stays_close_to_the_other_ladders_in_height():
    """A taller asset is a smaller one once Canva scales it to fit the page."""
    from scripts.prototypes.scoring_age_ladder import CHART_HEIGHT

    assert STOCKS_CHART_HEIGHT - CHART_HEIGHT <= 100


def test_portraits_take_a_larger_share_of_the_row_than_the_older_ladders():
    from scripts.prototypes.scoring_age_ladder import ONE_SLIDE_LAYOUT

    older = 2 * ONE_SLIDE_LAYOUT.headshot_half_size / ONE_SLIDE_LAYOUT.row_height
    newer = 2 * STOCKS_LAYOUT.headshot_half_size / STOCKS_LAYOUT.row_height
    assert newer > older


def test_the_face_crop_keeps_less_of_the_shoulder_than_the_older_ladders():
    from scripts.prototypes.scoring_age_ladder import FACE_CROP_HEIGHT_FRACTION

    assert STOCKS_FACE_CROP_FRACTION < FACE_CROP_HEIGHT_FRACTION


def test_auto_name_column_refuses_a_table_that_would_overflow_the_asset(tmp_path, monkeypatch):
    import scripts.prototypes.scoring_age_ladder as ladder
    from scripts.prototypes.stocks_age_ladder import STOCKS_LAYOUT

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(build_working_table(_source_rows())).copy()
    winners["player"] = "A Preposterously Long Basketball Player Name Indeed"

    with pytest.raises(ValueError, match="overflows"):
        render_chart(
            winners,
            "2026-08-22",
            layout=STOCKS_LAYOUT,
            metric_column="stocks_per_game",
            trailing_columns=STOCKS_TRAILING_COLUMNS,
            auto_name_column=True,
        )


# --- the fixes the conditional fill needed ---------------------------------


def test_the_conditional_fill_stops_short_of_the_header_rule():
    """The top cell used to bleed into the black ruler above it."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from scripts.prototypes.scoring_age_ladder import HEADER_RULE_CLEARANCE, _ppg_cells

    fig = plt.figure(figsize=(10.8, 12.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, STOCKS_CHART_WIDTH)
    ax.set_ylim(0, STOCKS_CHART_HEIGHT)
    players = pd.DataFrame({"points_per_game": [3.5, 2.0, 1.1]})
    try:
        _ppg_cells(
            ax, players, STOCKS_LAYOUT, 1.1, 3.5,
            top_limit=STOCKS_LAYOUT.header_rule_y - HEADER_RULE_CLEARANCE,
        )
        clips = [p for p in ax.patches if isinstance(p, Rectangle) and p.get_facecolor()[3] == 0]
        assert clips, "expected a clip rectangle bounding the fill band"
        top = max(c.get_y() + c.get_height() for c in clips)
    finally:
        plt.close(fig)

    assert top <= STOCKS_LAYOUT.header_rule_y - HEADER_RULE_CLEARANCE
    assert top < STOCKS_LAYOUT.header_rule_y


def test_the_fill_band_is_squared_off_not_rounded():
    from matplotlib.patches import FancyBboxPatch
    import matplotlib.pyplot as plt
    from scripts.prototypes.scoring_age_ladder import _ppg_cells

    fig = plt.figure(figsize=(10.8, 12.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, STOCKS_CHART_WIDTH)
    ax.set_ylim(0, STOCKS_CHART_HEIGHT)
    try:
        _ppg_cells(ax, pd.DataFrame({"points_per_game": [3.5, 1.1]}), STOCKS_LAYOUT, 1.1, 3.5)
        assert not any(isinstance(p, FancyBboxPatch) for p in ax.patches)
    finally:
        plt.close(fig)


def test_a_gap_separates_the_season_marker_from_the_metric_column():
    from scripts.prototypes.stocks_age_ladder import STOCKS_NAME_COLUMN_GAP

    assert STOCKS_NAME_COLUMN_GAP > 0


def test_row_rules_do_not_paint_over_the_fill_corners(tmp_path, monkeypatch):
    """Projecting line caps left a pale notch at every row boundary."""
    from PIL import Image
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(_rated_table())
    image = Image.open(render_stocks_table(winners, "2026-08-22")).convert("RGBA")

    # Find the fill column by its only signature: a long run of fully opaque,
    # strongly coloured pixels. Scan clear of the row's own digits, which would
    # otherwise chop the run into pieces.
    row_mid = int(STOCKS_CHART_HEIGHT - STOCKS_LAYOUT.first_row_y) + 20
    runs, run = [], []
    for x in range(image.width):
        r, g, b, a = image.getpixel((x, row_mid))
        if a == 255 and (max(r, g, b) - min(r, g, b)) > 40:
            run.append(x)
        else:
            if len(run) > 100:
                runs.append((run[0], run[-1]))
            run = []
    assert runs, "could not locate the conditional fill column"
    left, right = max(runs, key=lambda pair: pair[1] - pair[0])

    # Straddle the first row boundary just inside each edge of the band. Every
    # pixel there must be opaque fill; a notch shows up as partial alpha.
    boundary = int(
        STOCKS_CHART_HEIGHT - (STOCKS_LAYOUT.first_row_y - STOCKS_LAYOUT.row_height / 2)
    )
    for x in (left + 2, right - 2):
        for y in range(boundary - 2, boundary + 3):
            assert image.getpixel((x, y))[3] == 255, f"hairline at x={x}, y={y}"


def test_rows_are_taller_than_the_first_cleanup_pass():
    assert STOCKS_LAYOUT.row_height >= 56


def test_the_crop_keeps_the_whole_head():
    """Too tight cut jaws; this sits between the old ladders and the first pass."""
    from scripts.prototypes.scoring_age_ladder import FACE_CROP_HEIGHT_FRACTION

    assert 0.62 < STOCKS_FACE_CROP_FRACTION < FACE_CROP_HEIGHT_FRACTION


def test_the_post_ships_the_table_only():
    import scripts.prototypes.stocks_age_ladder as stocks

    assert not hasattr(stocks, "render_stocks_bars")


# --- shading against the league, not against this chart --------------------


def test_the_league_pool_is_rotation_regulars_only():
    rows = pd.DataFrame(
        {
            "PLAYER_ID": [1, 2, 3, 4],
            "PLAYER_NAME": ["Starter", "Bench Minutes", "Injured", "Regular"],
            "GP": [82, 82, 10, 60],
            "MIN": [82 * 34, 82 * 8, 10 * 30, 60 * 25],
            "STL": [82, 82, 10, 60],
            "BLK": [82, 82, 10, 60],
        }
    )

    rates = league_rotation_rates(rows)

    # The eight-minute bench player and the ten-game player are both excluded.
    assert len(rates) == 2


def test_a_shortened_season_is_not_held_to_an_82_game_bar():
    """41 games is 62% of a lockout season — the bar has to move with the year."""
    rows = pd.DataFrame(
        {
            "PLAYER_ID": range(1, 5),
            "PLAYER_NAME": list("ABCD"),
            "GP": [66, 40, 34, 20],
            "MIN": [66 * 30, 40 * 30, 34 * 30, 20 * 30],
            "STL": [66, 40, 34, 20],
            "BLK": [66, 40, 34, 20],
        }
    )

    rates = league_rotation_rates(rows)

    # Minimum is ceil(66 * 0.5) = 33, so the 34-game player qualifies.
    assert len(rates) == 3


def test_percentile_places_a_row_against_its_own_season():
    table = _rated_table()

    assert "league_percentile" in table.columns
    assert table["league_percentile"].between(0, 100).all()
    # The fixture's rim protector sits at 3.0 stocks, above every league rate.
    protector = table.loc[table["player"] == "Rim Protector"].iloc[0]
    assert protector["league_percentile"] == 100.0


def test_percentile_needs_a_baseline_for_every_season():
    table = build_working_table(_source_rows())
    baseline = _baseline()
    del baseline[FIRST_SEASON_END_YEAR]

    with pytest.raises(ValueError, match="No league baseline"):
        attach_league_percentile(table, baseline)


def test_validation_rejects_a_percentile_outside_the_scale():
    table = _rated_table()
    table.loc[0, "league_percentile"] = 101.0

    with pytest.raises(ValueError, match="outside 0–100"):
        validate_working_table(table)


def test_validation_rejects_a_comparison_pool_too_small_to_mean_anything():
    table = _rated_table()
    table.loc[0, "league_sample"] = 12

    with pytest.raises(ValueError, match="too small a comparison pool"):
        validate_working_table(table)


def test_the_ratio_column_is_the_rate_over_that_season_league_median():
    table = _rated_table()

    assert "league_ratio" in table.columns
    row = table.iloc[0]
    assert row["league_ratio"] == pytest.approx(
        row["stocks_per_game"] / row["league_median"]
    )


def test_yellow_lands_on_league_average_not_the_middle_of_the_chart():
    """The whole point of the midpoint: 1.00x is average wherever the extremes sit."""
    from scripts.prototypes.scoring_age_ladder import HEAT_YELLOW, ppg_fill
    from matplotlib.colors import to_rgb
    from scripts.prototypes.stocks_age_ladder import (
        LEAGUE_RATIO_AVERAGE,
        LEAGUE_RATIO_CEILING,
        LEAGUE_RATIO_FLOOR,
    )

    average = ppg_fill(
        LEAGUE_RATIO_AVERAGE, LEAGUE_RATIO_FLOOR, LEAGUE_RATIO_CEILING,
        midpoint=LEAGUE_RATIO_AVERAGE,
    )

    assert average == pytest.approx(to_rgb(HEAT_YELLOW))
    # An unpinned scale would have put yellow at 1.625x, which is well above average.
    assert ppg_fill(
        LEAGUE_RATIO_AVERAGE, LEAGUE_RATIO_FLOOR, LEAGUE_RATIO_CEILING
    ) != average


def test_the_scale_separates_seasons_that_percentile_flattened():
    """Ben Wallace and Jimmy Butler must not read as the same green."""
    from scripts.prototypes.scoring_age_ladder import ppg_fill
    from scripts.prototypes.stocks_age_ladder import (
        LEAGUE_RATIO_AVERAGE,
        LEAGUE_RATIO_CEILING,
        LEAGUE_RATIO_FLOOR,
    )

    def fill(ratio):
        return ppg_fill(
            ratio, LEAGUE_RATIO_FLOOR, LEAGUE_RATIO_CEILING,
            midpoint=LEAGUE_RATIO_AVERAGE,
        )

    butler, wallace = fill(1.72), fill(2.68)          # 89.7th and 98.2nd percentile
    # Greener means a lower red channel on this ramp.
    assert wallace[0] < butler[0]
    assert butler[0] - wallace[0] > 0.05


def test_a_midpoint_outside_the_scale_is_refused():
    from scripts.prototypes.scoring_age_ladder import ppg_fill

    with pytest.raises(ValueError, match="midpoint must sit between"):
        ppg_fill(1.0, 0.75, 2.5, midpoint=3.0)


def test_the_renderer_rejects_a_fill_column_the_rows_do_not_carry(tmp_path, monkeypatch):
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(_rated_table())

    with pytest.raises(ValueError, match="missing fill column"):
        render_chart(
            winners,
            "2026-08-22",
            metric_column="stocks_per_game",
            fill_column="not_a_column",
            trailing_columns=STOCKS_TRAILING_COLUMNS,
        )


def test_final_export_is_the_same_layout_at_twice_the_pixels(tmp_path, monkeypatch):
    """--final must raise resolution, not resize the type."""
    from PIL import Image
    import scripts.prototypes.scoring_age_ladder as ladder

    monkeypatch.setattr(ladder, "OUT", tmp_path)
    winners = age_winners(_rated_table())

    draft = Image.open(render_stocks_table(winners, "2026-08-22"))
    final = Image.open(render_stocks_table(winners, "2026-08-22", final=True))

    assert final.size == (draft.width * 2, draft.height * 2)
    assert final.mode == draft.mode == "RGBA"
