"""Selection and reconciliation checks for the 2020s FGA-leader carousel."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes import fga_leader_zone_charts as charts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"


def test_the_coverage_is_six_completed_seasons_since_2020_21():
    assert charts.SEASONS == (
        "2020-21",
        "2021-22",
        "2022-23",
        "2023-24",
        "2024-25",
        "2025-26",
    )


def test_total_fga_selects_the_leader_with_deterministic_ties():
    table = pd.DataFrame([
        {"PLAYER_ID": 30, "PLAYER_NAME": "Lower", "FGA": 700, "MIN": 1900},
        {"PLAYER_ID": 20, "PLAYER_NAME": "Tie B", "FGA": 800, "MIN": 2000},
        {"PLAYER_ID": 10, "PLAYER_NAME": "Tie A", "FGA": 800, "MIN": 2000},
    ])
    leader = charts.select_fga_leader(table)
    assert leader.PLAYER_NAME == "Tie A"
    assert leader.FGA == 800


def test_selection_does_not_trust_the_returned_team_abbreviation():
    """A team-filtered stint may be labelled with the player's later team."""
    table = pd.DataFrame([
        {"PLAYER_ID": 1, "PLAYER_NAME": "Traded", "TEAM_ABBREVIATION": "IND",
         "FGA": 900, "MIN": 2100},
        {"PLAYER_ID": 2, "PLAYER_NAME": "Stayed", "TEAM_ABBREVIATION": "CHI",
         "FGA": 850, "MIN": 2200},
    ])
    assert charts.select_fga_leader(table).PLAYER_NAME == "Traded"


def test_2022_23_bonus_rule_selects_demar_as_the_close_runner_up():
    table = pd.read_csv(DATA / "bulls-fga-leaderboard-2022-23.csv")
    leader, runner_up = charts.select_bonus_runner_up(table)
    assert leader.PLAYER_NAME == "Zach LaVine"
    assert int(leader.FGA) == 1388
    assert runner_up.PLAYER_NAME == "DeMar DeRozan"
    assert int(runner_up.FGA) == 1303
    assert int(leader.FGA - runner_up.FGA) == 85


@pytest.mark.parametrize(
    "leader_fga, runner_fga",
    [(1400, 1299), (1400, 1300)],
)
def test_bonus_rule_rejects_low_volume_or_a_100_fga_gap(
    leader_fga, runner_fga
):
    table = pd.DataFrame([
        {"PLAYER_ID": 1, "PLAYER_NAME": "Leader", "FGA": leader_fga, "MIN": 1},
        {"PLAYER_ID": 2, "PLAYER_NAME": "Runner", "FGA": runner_fga, "MIN": 1},
    ])
    with pytest.raises(ValueError, match="no qualifying runner-up"):
        charts.select_bonus_runner_up(table)


def test_raw_chicago_shots_must_reconstruct_the_selecting_fga_total():
    leader = pd.Series({"PLAYER_NAME": "Player", "FGA": 3})
    shots = pd.DataFrame({"shot_made": [True, False, True]})
    charts.reconcile_shot_count("2025-26", leader, shots)

    with pytest.raises(ValueError, match="shot rows 2 != box FGA 3"):
        charts.reconcile_shot_count("2025-26", leader, shots.iloc[:2])


def test_league_baseline_preserves_attempt_and_make_counts():
    league = pd.DataFrame({
        "loc_x": [0, 0, 0, 230],
        "loc_y": [0, 0, 240, 0],
        "shot_made": [True, False, True, False],
    })
    table = charts.league_zone_baseline("2025-26", league).set_index("zone")
    assert table.fga.sum() == 4
    assert table.fgm.sum() == 2
    assert table.fga_share_pct.sum() == pytest.approx(100.0)
    assert table.loc["Restricted Area", "fg_pct"] == pytest.approx(50.0)


def test_saved_post_data_reconstructs_every_selection_and_chart_input():
    summary = pd.read_csv(DATA / "fga-leader-zone-summary.csv").set_index("season")
    baselines = pd.read_csv(DATA / "league-zone-baselines.csv")

    assert tuple(summary.index) == charts.SEASONS
    for season in charts.SEASONS:
        leaderboard = pd.read_csv(DATA / f"bulls-fga-leaderboard-{season}.csv")
        leader = charts.select_fga_leader(leaderboard)
        saved = summary.loc[season]
        assert int(leader.PLAYER_ID) == int(saved.player_id)
        assert int(leader.FGA) == int(saved.box_fga)

        slug = charts.player_slug(str(leader.PLAYER_NAME))
        shots = pd.read_csv(DATA / f"{season}-{slug}-bulls-shots.csv")
        charts.reconcile_shot_count(season, leader, shots)
        assert int(shots.shot_made.sum()) == int(saved.fgm)

        league = baselines[baselines.season == season]
        assert len(league) == 12
        assert league.fga_share_pct.sum() == pytest.approx(100.0, abs=0.001)


def test_large_four_line_pills_stay_separate_and_inside_the_asset():
    """Measure the actual rendered cards for all six saved season layouts."""
    from itertools import combinations
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scripts import make_shot_chart as shot_chart
    from bulls.graphics.court import nba_to_basket_bottom_px

    splits = pd.read_csv(DATA / "fga-leader-zone-splits.csv")
    assert tuple(splits.season.drop_duplicates()) == charts.SEASONS

    for season, table in splits.groupby("season", sort=False):
        fig = plt.figure(figsize=(7.2, 9))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1080)
        ax.set_ylim(0, 1350)
        x0 = (1080 - 500 * shot_chart.ZONE12_SCALE) / 2
        y0 = 400

        def to_px(x, y):
            return nba_to_basket_bottom_px(
                x0, y0, shot_chart.ZONE12_SCALE, x, y
            )

        for row in table.itertuples():
            shot_chart._zone12_block(
                ax, to_px, row, "#F1CC5B",
                shot_chart.house.get_theme("jersey"), "large"
            )
        boxes = [patch.get_bbox() for patch in ax.patches]
        plt.close(fig)

        assert len(boxes) == 12
        assert all(box.x0 >= 0 and box.x1 <= 1080 for box in boxes), season
        assert not any(a.overlaps(b) for a, b in combinations(boxes, 2)), season
