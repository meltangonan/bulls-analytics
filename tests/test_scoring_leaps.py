"""Tests for the Bulls year-over-year scoring leaps prototype."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from scripts.prototypes.scoring_leaps import (
    AXIS_MAX,
    AXIS_MIN,
    CHART_TYPE,
    CHART_HEIGHT,
    CHART_WIDTH,
    DISPLAY_NAMES,
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    MIN_ENDING_POINTS_PER_36,
    MIN_MINUTES_PER_GAME,
    PLOT_LEFT,
    PLOT_RIGHT,
    TOP_N,
    _x_position,
    build_leap_table,
    build_season_table,
    chart_pages,
    display_name,
    display_season_label,
    gain_label,
    minutes_label,
    rate_label,
    top_anchored_headshot_label,
    minutes_correlations,
    player_source_url,
    render_chart,
    season_label,
    season_marker,
    top_leaps,
    validate_tables,
)


SHORTENED_SEASONS = {2012: 66, 2020: 65, 2021: 72}


def _row(
    end_year: int,
    player_id: int,
    player: str,
    games: int,
    minutes_per_game: float,
    points_per_game: float,
) -> dict:
    """Build one synthetic Bulls player-season from display-level rates."""
    return {
        "season_end_year": end_year,
        "season": display_season_label(end_year),
        "player_id": player_id,
        "player": player,
        "games": games,
        "minutes": round(minutes_per_game * games, 1),
        "points": round(points_per_game * games),
        "team_games": SHORTENED_SEASONS.get(end_year, 82),
        "player_source_url": player_source_url(end_year),
        "team_source_url": "https://example.test/team",
    }


def _source_rows() -> pd.DataFrame:
    """Cover every season with a flat starter, a mover, and a benched player.

    The mover's minutes swing far more than its per-36 rate, which is what makes
    a per-game gain track playing time more closely than a per-36 gain.
    """
    records: list[dict] = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        index = end_year - FIRST_SEASON_END_YEAR
        team_games = SHORTENED_SEASONS.get(end_year, 82)
        mover_minutes = 20.0 + (index % 6) * 2.0
        mover_per_36 = 14.0 + (index % 3) * 0.5
        records.extend(
            [
                _row(end_year, 1001, "Steady Star", team_games, 32.0, 16.0),
                _row(
                    end_year,
                    2002,
                    "Big Mover",
                    team_games,
                    mover_minutes,
                    mover_per_36 * mover_minutes / 36,
                ),
                _row(end_year, 3003, "Bench Guy", 30, 12.0, 4.0),
            ]
        )
    frame = pd.DataFrame(records)
    team_points = frame.groupby("season_end_year")["points"].transform("sum")
    frame["team_points"] = team_points
    return frame


def _tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    season_table = build_season_table(_source_rows())
    return season_table, build_leap_table(season_table)


def test_season_labels_have_machine_and_display_forms():
    assert season_label(2015) == "2014-15"
    assert display_season_label(2015) == "2014–15"


def test_source_url_keeps_the_requested_bulls_season():
    assert "Season=2014-15" in player_source_url(2015)


def test_rates_come_from_season_totals_not_reported_averages():
    table = build_season_table(_source_rows())
    star = table.loc[(table["player_id"] == 1001) & (table["season_end_year"] == 2015)].iloc[0]
    assert star["minutes_per_game"] == pytest.approx(32.0)
    assert star["points_per_game"] == pytest.approx(16.0)
    # 16 points in 32 minutes scales to 18 points per 36 minutes.
    assert star["points_per_36"] == pytest.approx(18.0)


def test_qualification_needs_both_games_and_minutes():
    rows = pd.DataFrame(
        [
            _row(2015, 11, "Exactly At Gate", 41, MIN_MINUTES_PER_GAME, 10.0),
            _row(2015, 12, "Enough Games Few Minutes", 70, MIN_MINUTES_PER_GAME - 0.5, 6.0),
            _row(2015, 13, "Enough Minutes Few Games", 40, 30.0, 12.0),
        ]
    )
    rows["team_points"] = rows["points"].sum()
    table = build_season_table(rows).set_index("player_id")
    assert bool(table.loc[11, "qualified"]) is True
    assert bool(table.loc[12, "qualified"]) is False
    assert bool(table.loc[13, "qualified"]) is False


def test_games_gate_scales_with_a_shortened_season():
    rows = pd.DataFrame(
        [
            _row(2012, 11, "Half The Lockout", 33, 20.0, 10.0),
            _row(2012, 12, "Under Half Lockout", 32, 20.0, 10.0),
        ]
    )
    rows["team_points"] = rows["points"].sum()
    table = build_season_table(rows).set_index("player_id")
    assert bool(table.loc[11, "qualified"]) is True
    assert bool(table.loc[12, "qualified"]) is False


def test_a_season_with_no_games_is_rejected_rather_than_divided_by():
    rows = pd.DataFrame([_row(2015, 11, "Never Played", 0, 0.0, 0.0)])
    rows["team_points"] = 0
    with pytest.raises(ValueError, match="no games played"):
        build_season_table(rows)


def test_leaps_pair_only_consecutive_seasons_that_both_qualify():
    rows = pd.DataFrame(
        [
            _row(2014, 11, "Gapped", 70, 30.0, 10.0),
            # The middle season falls under the minutes gate, so it can neither
            # end the first pair nor start the second.
            _row(2015, 11, "Gapped", 70, 12.0, 5.0),
            _row(2016, 11, "Gapped", 70, 30.0, 18.0),
            _row(2014, 22, "Linked", 70, 30.0, 10.0),
            _row(2015, 22, "Linked", 70, 30.0, 14.0),
        ]
    )
    rows["team_points"] = rows.groupby("season_end_year")["points"].transform("sum")
    leaps = build_leap_table(build_season_table(rows))
    assert set(zip(leaps["player_id"], leaps["season_end_year_cur"])) == {(22, 2015)}


def test_gain_is_the_change_in_points_per_36():
    rows = pd.DataFrame(
        [
            _row(2014, 11, "Riser", 70, 30.0, 10.0),
            _row(2015, 11, "Riser", 70, 30.0, 15.0),
        ]
    )
    rows["team_points"] = rows.groupby("season_end_year")["points"].transform("sum")
    leap = build_leap_table(build_season_table(rows)).iloc[0]
    assert leap["points_per_36_prev"] == pytest.approx(12.0)
    assert leap["points_per_36_cur"] == pytest.approx(18.0)
    assert leap["gain_per_36"] == pytest.approx(6.0)
    assert leap["gain_per_game"] == pytest.approx(5.0)
    assert leap["percentage_increase"] == pytest.approx(50.0)


def test_pair_must_finish_at_the_scoring_rate_floor():
    rows = pd.DataFrame(
        [
            _row(2014, 11, "Low Finish", 70, 36.0, 5.0),
            _row(2015, 11, "Low Finish", 70, 36.0, MIN_ENDING_POINTS_PER_36 - 0.1),
            _row(2014, 22, "At Floor", 70, 36.0, 5.0),
            _row(2015, 22, "At Floor", 70, 36.0, MIN_ENDING_POINTS_PER_36),
        ]
    )
    rows["team_points"] = rows.groupby("season_end_year")["points"].transform("sum")
    leaps = build_leap_table(build_season_table(rows))
    assert leaps["player_id"].tolist() == [22]


def test_ties_break_on_the_higher_finishing_rate_so_order_is_stable():
    rows = pd.DataFrame(
        [
            # Both gain exactly 4.0 per 36; the higher finishing rate ranks first.
            _row(2014, 11, "Lower Finish", 70, 36.0, 8.0),
            _row(2015, 11, "Lower Finish", 70, 36.0, 12.0),
            _row(2014, 22, "Higher Finish", 70, 36.0, 15.0),
            _row(2015, 22, "Higher Finish", 70, 36.0, 19.0),
        ]
    )
    rows["team_points"] = rows.groupby("season_end_year")["points"].transform("sum")
    leaps = build_leap_table(build_season_table(rows))
    assert leaps["gain_per_36"].tolist() == pytest.approx([4.0, 4.0])
    assert leaps["player_cur"].tolist() == ["Higher Finish", "Lower Finish"]
    assert leaps["rank"].tolist() == [1, 2]


def test_ranked_metric_tracks_minutes_less_closely_than_points_per_game():
    _, leap_table = _tables()
    correlations = minutes_correlations(leap_table)
    assert correlations["per_36"] < correlations["per_game"]


def test_validation_reports_coverage_and_the_leader():
    season_table, leap_table = _tables()
    report = validate_tables(season_table, leap_table)
    assert report["season_count"] == LAST_SEASON_END_YEAR - FIRST_SEASON_END_YEAR + 1
    assert report["leap_count"] == len(leap_table)
    # "Bench Guy" clears neither gate in any season, so he never pairs.
    assert report["leap_player_count"] == 2
    assert report["leader"] == leap_table.iloc[0]["player_cur"]


def test_validation_rejects_a_missing_season():
    season_table, _ = _tables()
    trimmed = season_table.loc[season_table["season_end_year"] != 2015].reset_index(drop=True)
    with pytest.raises(ValueError, match="Season coverage"):
        validate_tables(trimmed, build_leap_table(trimmed))


def test_validation_rejects_player_points_that_do_not_reconcile_to_the_team():
    season_table, leap_table = _tables()
    broken = season_table.copy()
    broken.loc[0, "points"] = int(broken.loc[0, "points"]) + 25
    with pytest.raises(ValueError, match="reconcile"):
        validate_tables(broken, leap_table)


def test_validation_rejects_a_pair_of_non_consecutive_seasons():
    season_table, leap_table = _tables()
    broken = leap_table.copy()
    broken.loc[0, "season_end_year_prev"] = int(broken.loc[0, "season_end_year_prev"]) - 1
    with pytest.raises(ValueError, match="not consecutive"):
        validate_tables(season_table, broken)


def test_validation_rejects_a_gate_flag_that_stopped_matching_its_rule():
    season_table, leap_table = _tables()
    broken = season_table.copy()
    broken.loc[broken.index[0], "qualified"] = not bool(broken.loc[broken.index[0], "qualified"])
    with pytest.raises(ValueError, match="qualification is inconsistent"):
        validate_tables(broken, leap_table)


def test_validation_rejects_a_metric_that_stopped_controlling_for_role():
    season_table, leap_table = _tables()
    broken = leap_table.copy()
    # Make the ranked metric track minutes perfectly and the per-game metric not
    # at all -- the exact inversion the guard exists to catch.
    broken["gain_per_36"] = broken["gain_minutes_per_game"]
    broken["gain_per_game"] = -broken["gain_minutes_per_game"]
    broken = broken.sort_values("gain_per_36", ascending=False).reset_index(drop=True)
    with pytest.raises(ValueError, match="stopped controlling for role"):
        validate_tables(season_table, broken)


def test_top_leaps_rejects_a_field_shorter_than_the_chart_needs():
    rows = pd.DataFrame(
        [
            _row(2014, 11, "Only Pair", 70, 30.0, 10.0),
            _row(2015, 11, "Only Pair", 70, 30.0, 14.0),
        ]
    )
    rows["team_points"] = rows.groupby("season_end_year")["points"].transform("sum")
    leaps = build_leap_table(build_season_table(rows))
    with pytest.raises(ValueError, match="qualifying leaps exist"):
        top_leaps(leaps, TOP_N)


def test_display_name_corrects_the_nba_name_field():
    leap = pd.Series({"player_id": 202710, "player_cur": "Jimmy Butler III"})
    assert display_name(leap) == "Jimmy Butler"
    untouched = pd.Series({"player_id": 1629632, "player_cur": "Coby White"})
    assert display_name(untouched) == "Coby White"
    assert DISPLAY_NAMES[2804] == "Andrés Nocioni"


def test_season_marker_includes_the_start_and_end_seasons():
    assert season_marker("2013–14", "2014–15") == "13–14 to 14–15"
    assert season_marker("2004–05", "2005–06") == "04–05 to 05–06"



def test_gain_label_always_carries_its_sign():
    assert gain_label(
        pd.Series({"gain_per_36": 6.44, "percentage_increase": 53.21})
    ) == "+6.4 (+53.2%)"


def test_rate_label_prints_the_exact_per_36_transition():
    leap = pd.Series(
        {
            "points_per_36_prev": 12.16,
            "points_per_36_cur": 18.63,
            "percentage_increase": 53.21,
        }
    )
    assert rate_label(leap) == "12.2 to 18.6 PTS/36"


def test_minutes_label_prints_the_exact_mpg_transition():
    leap = pd.Series({"minutes_per_game_prev": 18.89, "minutes_per_game_cur": 29.20})
    assert minutes_label(leap) == "18.9 to 29.2 MPG"


def test_stat_lines_are_optically_balanced_above_the_season():
    assert CHART_TYPE.rate == CHART_TYPE.minutes + 0.5
    assert CHART_TYPE.rate == CHART_TYPE.season + 1


def test_top_fifteen_stays_on_one_slide():
    _, leap_table = _tables()
    pages = chart_pages(top_leaps(leap_table))
    assert [len(page) for page in pages] == [15]
    assert pages[0].iloc[0]["rank"] == 1
    assert pages[0].iloc[-1]["rank"] == 15


def test_axis_bounds_map_to_the_plot_edges():
    assert _x_position(AXIS_MIN) == pytest.approx(PLOT_LEFT)
    assert _x_position(AXIS_MAX) == pytest.approx(PLOT_RIGHT)
    assert _x_position((AXIS_MIN + AXIS_MAX) / 2) == pytest.approx((PLOT_LEFT + PLOT_RIGHT) / 2)


def test_five_point_axis_interval_has_room_to_read():
    assert _x_position(15.0) - _x_position(10.0) >= 160


def test_render_rejects_a_leap_that_runs_past_the_axis(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.prototypes.scoring_leaps.OUT", tmp_path)
    _, leap_table = _tables()
    leaders = chart_pages(top_leaps(leap_table))[0].copy()
    leaders.loc[0, "points_per_36_cur"] = AXIS_MAX + 1.0
    with pytest.raises(ValueError, match="above the chart's axis maximum"):
        render_chart(leaders, "2026-08-05")


def test_render_rejects_an_empty_field(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.prototypes.scoring_leaps.OUT", tmp_path)
    _, leap_table = _tables()
    with pytest.raises(ValueError, match="empty leap chart"):
        render_chart(leap_table.head(0), "2026-08-05")




def test_headshot_crop_is_anchored_to_the_top_of_the_frame(tmp_path):
    # A tall portrait: white above, black below. A top-anchored square keeps
    # mostly the white half; a centred one would land near an even split.
    source = np.zeros((100, 60, 3), dtype=float)
    source[:50] = 1.0
    path = tmp_path / "portrait.png"
    plt.imsave(path, source)

    figure, ax = plt.subplots()
    artist = top_anchored_headshot_label(ax, path, 0.0, 0.0, 10.0)
    drawn = np.asarray(artist.get_array(), dtype=float)
    plt.close(figure)

    assert drawn.shape[0] == drawn.shape[1] == 41
    assert drawn[:, :, 0].mean() == pytest.approx(1.0)


def test_a_missing_portrait_becomes_a_placeholder_rather_than_a_crash(tmp_path):
    figure, ax = plt.subplots()
    artist = top_anchored_headshot_label(ax, tmp_path / "absent.png", 0.0, 0.0, 10.0)
    plt.close(figure)
    assert artist in ax.patches


def test_chart_export_is_transparent(tmp_path, monkeypatch):
    from PIL import Image

    monkeypatch.setattr("scripts.prototypes.scoring_leaps.OUT", tmp_path)
    _, leap_table = _tables()
    path = render_chart(chart_pages(top_leaps(leap_table))[0], "2026-08-05")
    assert path.exists()
    with Image.open(path) as image:
        assert image.mode == "RGBA"
        assert image.getpixel((2, 2))[3] == 0


def test_final_export_doubles_draft_pixel_dimensions(tmp_path, monkeypatch):
    from PIL import Image

    monkeypatch.setattr("scripts.prototypes.scoring_leaps.OUT", tmp_path)
    _, leap_table = _tables()
    path = render_chart(
        chart_pages(top_leaps(leap_table))[0], "2026-08-05", final=True
    )
    with Image.open(path) as image:
        assert image.size == (CHART_WIDTH * 2, CHART_HEIGHT * 2)
