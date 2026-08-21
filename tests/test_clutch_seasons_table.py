"""Post-specific tests for the most-clutch-Bulls-seasons leaderboard.

The behaviour worth pinning here is the team filter's stint semantics, which
is the trap that produces silently wrong Bulls totals, and the era-relative
colour scale, which is what keeps a 2000s season and a 2020s season on the
same terms.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bulls.graphics.house import HEAT_MID
from matplotlib.colors import to_rgb

from scripts.prototypes.clutch_seasons_table import (
    CALIBRATION_MIN_TSA,
    COLUMN_SCALES,
    FIRST_SEASON,
    LAST_SEASON,
    LAST_SEASON,
    SHADED_METRICS,
    HERO_GAP,
    HERO_METRIC,
    STAT_COLUMNS,
    TABLE_ROWS,
    add_rates,
    assert_whole_season_bulls,
    calibration_population,
    cell_label,
    column_bounds,
    league_baselines,
    prepare_table,
    reconcile_team_filter,
    season_marker,
    shaded_value,
    validate,
)


def _row(season, player_id, name, team, gp, w, pts, fgm, fga, fta, minutes):
    return {
        "SEASON": season,
        "PLAYER_ID": player_id,
        "PLAYER_NAME": name,
        "TEAM_ABBREVIATION": team,
        "GP": gp,
        "W": w,
        "L": gp - w,
        "MIN": minutes,
        "PTS": pts,
        "FGM": fgm,
        "FGA": fga,
        "FG3M": 0,
        "FG3A": 0,
        "FTM": fta,
        "FTA": fta,
    }


def _league() -> pd.DataFrame:
    """Two seasons whose league clutch efficiency differs sharply."""
    rows = [
        # 2000-01: pooled league TS% lands near .500.
        _row("2000-01", 10, "Old Bull", "CHI", 40, 20, 100, 40, 100, 0, 150.0),
        _row("2000-01", 11, "Old Filler", "BOS", 40, 20, 100, 40, 100, 0, 150.0),
        # 2025-26: the same raw shooting is now below average.
        _row("2025-26", 20, "New Bull", "CHI", 40, 20, 130, 52, 100, 0, 150.0),
        _row("2025-26", 21, "New Filler", "BOS", 40, 20, 130, 52, 100, 0, 150.0),
    ]
    return pd.DataFrame(rows)


def test_league_baselines_are_pooled_not_averaged():
    """A season's baseline comes from its totals, not a mean of player rates."""
    league = pd.DataFrame(
        [
            _row("2000-01", 1, "Volume", "CHI", 40, 20, 200, 80, 200, 0, 150.0),
            _row("2000-01", 2, "Sliver", "BOS", 5, 2, 4, 2, 2, 0, 5.0),
        ]
    )
    baseline = league_baselines(league).iloc[0]
    # Pooled: 204 points on 2 x 202 attempts. A mean of the two player rates
    # would have returned .750, dragged there by a two-shot bench season.
    assert baseline["league_ts_pct"] == pytest.approx(204 / (2 * 202))


def test_league_baseline_rejects_an_impossible_season():
    league = pd.DataFrame([_row("2000-01", 1, "Nobody", "CHI", 1, 0, 0, 0, 1, 0, 1.0)])
    with pytest.raises(ValueError, match="plausible range"):
        league_baselines(league)


def test_team_filter_stint_is_kept_even_when_stamped_with_another_team():
    """The trap: TEAM_ABBREVIATION names the player's last team, not the stint.

    Ron Mercer's real 2001-02 rows: 19 Bulls clutch games stamped IND, plus 4
    Indiana clutch games, against 23 in his unfiltered season row. Filtering
    the Bulls response down to CHI would delete the Bulls stint entirely.
    """
    bulls = pd.DataFrame(
        [_row("2001-02", 1500, "Ron Mercer", "IND", 19, 6, 46, 17, 34, 14, 61.7)]
    )
    league = pd.DataFrame(
        [_row("2001-02", 1500, "Ron Mercer", "IND", 23, 8, 46, 17, 36, 14, 70.4)]
    )
    merged = reconcile_team_filter(bulls, league)
    assert len(merged) == 1
    assert merged.iloc[0]["GP"] == 19
    assert merged.iloc[0]["season_gp"] == 23


def test_a_stint_larger_than_its_own_season_is_rejected():
    bulls = pd.DataFrame(
        [_row("2001-02", 1500, "Ron Mercer", "IND", 25, 6, 46, 17, 34, 14, 61.7)]
    )
    league = pd.DataFrame(
        [_row("2001-02", 1500, "Ron Mercer", "IND", 23, 8, 46, 17, 36, 14, 70.4)]
    )
    with pytest.raises(ValueError, match="exceeds the player's own season"):
        reconcile_team_filter(bulls, league)


def test_a_bulls_stint_with_no_league_row_is_rejected():
    bulls = pd.DataFrame([_row("2001-02", 999, "Ghost", "CHI", 5, 2, 10, 4, 8, 2, 12.0)])
    league = pd.DataFrame([_row("2001-02", 1, "Someone", "CHI", 5, 2, 10, 4, 8, 2, 12.0)])
    with pytest.raises(ValueError, match="no league row"):
        reconcile_team_filter(bulls, league)


def test_a_partial_bulls_season_is_refused_a_place_in_the_table():
    """A half-season beside fourteen whole ones has to be declared, not printed."""
    table = pd.DataFrame(
        [
            {
                "PLAYER_NAME": "Traded Bull",
                "SEASON": "2003-04",
                "GP": 30,
                "season_gp": 60,
                "PTS": 90,
                "season_pts": 180,
            }
        ]
    )
    with pytest.raises(ValueError, match="only part of the player's clutch year"):
        assert_whole_season_bulls(table)


def test_true_shooting_colour_is_judged_against_its_own_season():
    """Identical raw TS% in 2000-01 and 2025-26 must not take the same colour.

    This is the whole reason the column is era-relative: league clutch true
    shooting climbed more than five points across the window, so a fixed scale
    would have ranked eras instead of players.
    """
    league = _league()
    baselines = league_baselines(league).set_index("SEASON")["league_ts_pct"]
    assert baselines["2025-26"] > baselines["2000-01"]

    same_raw = pd.DataFrame(
        [
            _row("2000-01", 10, "Old Bull", "CHI", 40, 20, 115, 46, 100, 0, 150.0),
            _row("2025-26", 20, "New Bull", "CHI", 40, 20, 115, 46, 100, 0, 150.0),
        ]
    )
    rated = add_rates(same_raw).merge(
        league_baselines(league), on="SEASON", validate="many_to_one"
    )
    rated["ts_pct_relative"] = (rated["ts_pct"] - rated["league_ts_pct"]) * 100
    assert rated.iloc[0]["ts_pct"] == pytest.approx(rated.iloc[1]["ts_pct"])
    # Identical raw shooting, different achievement — and now the CELL says so
    # rather than only its colour.
    assert (
        shaded_value(rated.iloc[0], "ts_pct_relative")
        > shaded_value(rated.iloc[1], "ts_pct_relative")
    )
    assert cell_label(rated.iloc[0], "ts_pct_relative").startswith("+")
    assert cell_label(rated.iloc[1], "ts_pct_relative").startswith("\N{MINUS SIGN}")


def test_the_neutral_band_leaves_an_ordinary_season_uncoloured():
    """A cell that says nothing remarkable disappears into the page."""
    from bulls.graphics.house import heat_fill

    red_at, low, high, green_at = COLUMN_SCALES["ts_pct_relative"]
    middle = (low + high) / 2
    assert heat_fill(middle, red_at, low, high, green_at) == to_rgb(HEAT_MID)
    assert heat_fill(green_at, red_at, low, high, green_at) != to_rgb(HEAT_MID)


def test_plus_minus_pivots_on_zero_but_its_ends_need_not_match():
    """The BAND is centred on breaking even; the ENDS follow the population.

    Zero is the value clutch plus-minus means something at, so the dead band
    straddles it symmetrically. The ends are a different question: the
    distribution's median is +12, not 0, because the players who take 100+
    clutch shots are mostly on winning teams. Anchoring each end at the same
    percentile of that lopsided field is what keeps a poor season from being
    graded against a spread the population does not actually have.
    """
    red_at, low, high, green_at = COLUMN_SCALES["PLUS_MINUS"]
    assert low < 0 < high
    assert -low == pytest.approx(high), "the dead band must straddle zero evenly"
    assert red_at < low and green_at > high
    # Asymmetric by design — assert the direction so a future 'tidy-up' that
    # symmetrises them has to argue with this instead of looking like a fix.
    assert abs(red_at) < abs(green_at)


def test_the_scoring_rate_is_kept_in_the_data_but_off_the_chart():
    """P/36 is reconciled every run and is deliberately not a column.

    The table was held to the metrics it already carried rather than gaining
    another. Keeping the rate in the working CSV costs nothing and leaves the
    counterweight to a totals ranking available to anyone reading the data.
    """
    assert "pts_per_36" not in [metric for metric, _, _ in STAT_COLUMNS]
    assert "pts_per_36" not in SHADED_METRICS
    assert "pts_per_36" not in COLUMN_SCALES
    frame = pd.DataFrame(
        [_row("2023-24", 1, "Leader", "CHI", 40, 24, 182, 55, 113, 74, 191.8)]
    )
    rated = add_rates(frame).iloc[0]
    assert rated["pts_per_36"] == pytest.approx(182 / 191.8 * 36)


def test_points_per_shooting_attempt_would_have_duplicated_true_shooting():
    """Documents why PTS/TSA is not a column: it is exactly two times TS%."""
    frame = pd.DataFrame(
        [_row("2023-24", 1, "Leader", "CHI", 40, 24, 182, 55, 113, 74, 191.8)]
    )
    rated = add_rates(frame).iloc[0]
    assert rated["PTS"] / rated["tsa"] == pytest.approx(2 * rated["ts_pct"])


def _every_season(extra: list[dict]) -> pd.DataFrame:
    """Pad a fixture out to the full window `prepare_table` insists on."""
    # Distinct point totals, so the 15-row cut never lands inside a tie the
    # way an all-identical filler block would.
    filler = [
        _row(f"{year}-{str(year + 1)[-2:]}", 900 + year, "Filler", "CHI",
             10, 5, 100 - (year - 2000), (100 - (year - 2000)) // 2,
             100 - (year - 2000), 0, 20.0)
        for year in range(FIRST_SEASON, LAST_SEASON + 1)
    ]
    return pd.DataFrame(filler + extra)


def test_ranking_breaks_a_tie_toward_the_shorter_stint():
    """Equal clutch points rank by who needed fewer clutch minutes."""
    bulls = _every_season(
        [
            _row("2020-21", 1, "Efficient", "CHI", 30, 15, 150, 50, 100, 20, 100.0),
            _row("2010-11", 2, "Grinder", "CHI", 30, 15, 150, 50, 100, 20, 200.0),
        ]
    )
    league = bulls.copy()
    table = prepare_table(bulls, league_baselines(league), league)
    assert list(table["PLAYER_NAME"])[:2] == ["Efficient", "Grinder"]


def test_a_snapshot_missing_seasons_is_rejected():
    bulls = pd.DataFrame(
        [_row("2020-21", 1, "Only One", "CHI", 30, 15, 150, 50, 100, 20, 100.0)]
    )
    with pytest.raises(ValueError, match="does not cover every season"):
        prepare_table(bulls, league_baselines(bulls), bulls)


def test_validate_catches_a_win_percentage_that_stopped_reconciling():
    league = _league()
    bulls = league.loc[league["TEAM_ABBREVIATION"].eq("CHI")].copy()
    rated = add_rates(bulls).merge(
        league_baselines(league), on="SEASON", validate="many_to_one"
    )
    rated["ts_pct_relative"] = (rated["ts_pct"] - rated["league_ts_pct"]) * 100
    rated["win_pct"] = 0.9  # No longer W / GP.
    population = calibration_population(league, league_baselines(league))
    with pytest.raises(ValueError):
        validate(rated, population)


def test_the_colour_scale_is_calibrated_above_the_volume_it_describes():
    """No displayed row may sit below the population the scale was built on."""
    assert CALIBRATION_MIN_TSA > 0
    table = pd.DataFrame(
        {
            "PTS": [200, 100],
            "GP": [40, 40],
            "W": [20, 20],
            "L": [20, 20],
            "MIN": [150.0, 150.0],
            "FGM": [70, 35],
            "FGA": [140, 70],
            "tsa": [140.0, 10.0],  # The second row is far below the floor.
            "ts_pct": [200 / 280, 100 / 20],
            "fg_pct": [0.5, 0.5],
            "win_pct": [0.5, 0.5],
            "ts_pct_relative": [5.0, 5.0],
        }
    )
    population = pd.DataFrame({"tsa": [100.0] * 400})
    with pytest.raises(ValueError):
        validate(table, population)


def test_the_shooting_line_prints_the_sample_not_a_percentage():
    """FG stays makes-attempts so the reader can see how thin the sample is."""
    row = pd.Series({"FGM": 55, "FGA": 113, "FTM": 65, "FTA": 74, "ts_pct": 0.625,
                     "win_pct": 0.6, "MIN": 191.8, "PTS": 182, "GP": 40,
                     "pts_per_36": 182 / 191.8 * 36})
    assert cell_label(row, "fg_line") == "55\N{EN DASH}113"
    # Free throws are half of what makes a clutch scorer: DeRozan's 2023-24
    # leader has 65 of his 182 points at the line.
    assert cell_label(row, "ft_line") == "65\N{EN DASH}74"
    assert cell_label(row, "MIN") == "192"


def test_relative_true_shooting_is_signed_and_never_a_signed_zero():
    """The cell prints the comparison itself, not the raw percentage.

    A raw 62.5% meant two different things in 2004-05 and 2023-24; this column
    prints the difference so the reader does not have to know the era.
    """
    assert cell_label(pd.Series({"ts_pct_relative": 12.04}), "ts_pct_relative") == "+12.0"
    assert cell_label(pd.Series({"ts_pct_relative": -6.26}), "ts_pct_relative") == "\N{MINUS SIGN}6.3"
    # Python rounds exact halves to even, so -6.25 gives -6.2 rather than -6.3.
    # Left alone deliberately: a tenth either way on a figure this noisy is not
    # worth a custom rounder, and pinning it here stops it reading as a bug.
    assert cell_label(pd.Series({"ts_pct_relative": -6.25}), "ts_pct_relative") == "\N{MINUS SIGN}6.2"
    # Sign decided after rounding, so a -0.04 never prints as "-0.0".
    assert cell_label(pd.Series({"ts_pct_relative": -0.04}), "ts_pct_relative") == "0.0"


def test_the_raw_percentage_stays_in_the_data_but_off_the_chart():
    """`ts_pct` is still computed and reconciled; it is just not a column."""
    assert "ts_pct" not in [metric for metric, _, _ in STAT_COLUMNS]
    assert "ts_pct" not in COLUMN_SCALES
    frame = pd.DataFrame(
        [_row("2023-24", 1, "Leader", "CHI", 40, 24, 182, 55, 113, 74, 191.8)]
    )
    assert add_rates(frame).iloc[0]["ts_pct"] == pytest.approx(182 / (2 * (113 + 0.44 * 74)))


def test_plus_minus_prints_a_true_minus_and_never_a_signed_zero():
    assert cell_label(pd.Series({"PLUS_MINUS": 94}), "PLUS_MINUS") == "+94"
    assert cell_label(pd.Series({"PLUS_MINUS": -25}), "PLUS_MINUS") == "\N{MINUS SIGN}25"
    # Decided after rounding, so a -0.4 never prints as a minus beside a zero.
    assert cell_label(pd.Series({"PLUS_MINUS": -0.4}), "PLUS_MINUS") == "0"


def test_season_marker_compacts_to_two_digit_years():
    assert season_marker("2023-24") == "23\N{EN DASH}24"


def test_columns_are_ordered_and_sized_by_their_widest_string():
    """FG holds "55-113" and G holds "40", so they cannot share a width."""
    bounds = column_bounds(400.0)
    assert list(bounds) == [metric for metric, _, _ in STAT_COLUMNS]
    fg_width = bounds["fg_line"][1] - bounds["fg_line"][0]
    games_width = bounds["GP"][1] - bounds["GP"][0]
    assert fg_width > games_width
    # The columns tile the space without overlaps, and the only gap in the run
    # is the deliberate margin that keeps the first ordinary column off the
    # ranking card.
    order = [metric for metric, _, _ in STAT_COLUMNS]
    for before, after in zip(order, order[1:]):
        gap = bounds[after][0] - bounds[before][1]
        assert gap == pytest.approx(HERO_GAP if before == HERO_METRIC else 0.0)


def test_the_table_is_exactly_the_agreed_depth():
    assert TABLE_ROWS == 15


def test_the_window_starts_where_the_headline_says():
    """2000-01 is a choice; the source floor is 1996-97 (DEVELOPMENT.md).

    A wider window was built and rejected on 2026-08-21. This pins the shipped
    window so a future refresh cannot quietly widen it while the page, the
    caption and the Notion provenance all still say "since 2000".
    """
    assert FIRST_SEASON == 2000
    assert LAST_SEASON == 2025
