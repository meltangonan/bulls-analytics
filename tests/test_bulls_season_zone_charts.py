"""Selection, coverage, and reconciliation checks for the 2021-22 season carousel."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes import bulls_season_zone_charts as charts


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "visuals" / charts.SLUG / "data"


def test_default_carousel_is_cover_plus_nine_pages():
    assert charts.SEASON == "2021-22"
    assert charts.MIN_PLAYER_FGA == 250
    assert charts.MAX_PLAYER_PAGES == 9


def test_selection_is_descending_and_deterministic():
    table = pd.DataFrame([
        {"PLAYER_ID": 30, "PLAYER_NAME": "Lower", "FGA": 249, "MIN": 1900},
        {"PLAYER_ID": 20, "PLAYER_NAME": "Tie B", "FGA": 300, "MIN": 2000},
        {"PLAYER_ID": 10, "PLAYER_NAME": "Tie A", "FGA": 300, "MIN": 2000},
    ])
    selected = charts.select_players(table, minimum=250, limit=2)
    assert list(selected.PLAYER_NAME) == ["Tie A", "Tie B"]


def test_selection_rejects_a_carousel_without_nine_qualified_players():
    table = pd.DataFrame([
        {"PLAYER_ID": i, "PLAYER_NAME": str(i), "FGA": 300, "MIN": 1}
        for i in range(8)
    ])
    with pytest.raises(ValueError, match="need 9"):
        charts.select_players(table)


def test_raw_shots_must_reconstruct_the_selecting_bulls_fga():
    player = pd.Series({"PLAYER_NAME": "Player", "FGA": 3})
    shots = pd.DataFrame({"shot_made": [True, False, True]})
    charts.reconcile_shot_count("2021-22", player, shots)

    with pytest.raises(ValueError, match="shot rows 2 != Bulls FGA 3"):
        charts.reconcile_shot_count("2021-22", player, shots.iloc[:2])


def test_saved_selection_and_shot_logs_reconstruct_the_carousel():
    leaderboard = pd.read_csv(DATA / "bulls-season-fga-leaderboard-2021-22.csv")
    selected = charts.select_players(leaderboard)
    summary = pd.read_csv(DATA / "zone-chart-summary-2021-22.csv")

    assert len(selected) == 9
    assert list(summary.player) == list(selected.PLAYER_NAME)
    assert summary.bulls_fga.tolist() == selected.FGA.astype(int).tolist()
    assert summary.shot_rows.tolist() == summary.bulls_fga.tolist()
    assert summary.zones_rated.between(0, 12).all()
    assert summary.rated_fga_share_pct.between(0, 100).all()

    for player in selected.itertuples(index=False):
        path = DATA / f"2021-22-{charts.player_slug(player.PLAYER_NAME)}-bulls-shots.csv"
        shots = pd.read_csv(path)
        charts.reconcile_shot_count("2021-22", pd.Series(player._asdict()), shots)


def test_saved_zone_tables_cover_all_players_and_share_a_common_baseline():
    splits = pd.read_csv(DATA / "zone-splits-2021-22.csv")
    baselines = pd.read_csv(DATA / "league-zone-baseline-2021-22.csv")

    assert splits.player.nunique() == 9
    assert all(len(group) == 12 for _, group in splits.groupby("player"))
    for _, group in splits.groupby("player"):
        assert group.fga_share_pct.sum() == pytest.approx(100.0, abs=0.001)
    assert len(baselines) == 12
    assert baselines.fga_share_pct.sum() == pytest.approx(100.0, abs=0.001)
