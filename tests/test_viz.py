"""Tests for bulls.viz module."""

import matplotlib.pyplot as plt
import pandas as pd

from bulls.viz import (
    bar_chart,
    efficiency_matrix,
    line_chart,
    radar_chart,
    rolling_efficiency_chart,
    shot_chart,
    zone_leaders_chart,
)


class TestBarChart:
    """Tests for bar_chart."""

    def test_returns_figure(self):
        data = pd.DataFrame({"date": ["2026-01-10", "2026-01-08"], "points": [28, 22]})
        fig = bar_chart(data, x="date", y="points")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        fig = bar_chart(pd.DataFrame(columns=["date", "points"]), x="date", y="points")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_missing_x_column(self):
        data = pd.DataFrame({"date": ["2026-01-10", "2026-01-08"], "points": [28, 22]})
        fig = bar_chart(data, x="missing", y="points")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestLineChart:
    """Tests for line_chart."""

    def test_returns_figure(self):
        data = pd.DataFrame({"date": ["2026-01-10", "2026-01-08"], "points": [28, 22]})
        fig = line_chart(data, x="date", y="points")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        fig = line_chart(pd.DataFrame(columns=["date", "points"]), x="date", y="points")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestRollingEfficiencyChart:
    """Tests for rolling_efficiency_chart."""

    def test_returns_figure(self):
        data = pd.DataFrame(
            {
                "date": ["2026-01-10", "2026-01-08", "2026-01-06"],
                "ts_pct_roll_5": [55.0, 58.0, 52.0],
                "result": ["W", "L", "W"],
            }
        )
        fig = rolling_efficiency_chart(data, efficiency_col="ts_pct_roll_5")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        fig = rolling_efficiency_chart(
            pd.DataFrame(columns=["date", "ts_pct_roll_5", "result"]),
            efficiency_col="ts_pct_roll_5",
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_respects_custom_league_avg(self):
        data = pd.DataFrame({"date": ["2026-01-10"], "ts_pct_roll_5": [55.0], "result": ["W"]})
        fig = rolling_efficiency_chart(data, efficiency_col="ts_pct_roll_5", league_avg=60.0)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestRadarChart:
    """Tests for radar_chart."""

    def test_returns_figure(self):
        fig = radar_chart([{"name": "Player A", "points": 20, "rebounds": 5, "assists": 6}])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_multiple_players(self):
        players = [
            {"name": "Player A", "points": 20, "rebounds": 5, "assists": 6},
            {"name": "Player B", "points": 25, "rebounds": 8, "assists": 4},
        ]
        fig = radar_chart(players)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_players(self):
        fig = radar_chart([])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_missing_metrics(self):
        fig = radar_chart([{"name": "Player A", "points": 20}], metrics=["points", "rebounds", "assists"])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestShotChart:
    """Tests for shot_chart."""

    def test_returns_figure(self):
        shots = pd.DataFrame({"loc_x": [0, 100, -100], "loc_y": [50, 200, 150], "shot_made": [True, False, True]})
        fig = shot_chart(shots)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_heatmap_mode(self):
        shots = pd.DataFrame(
            {
                "loc_x": [0, 100, -100, 50],
                "loc_y": [50, 200, 150, 120],
                "shot_made": [True, False, True, True],
            }
        )
        fig = shot_chart(shots, show_zones=True)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty(self):
        fig = shot_chart(pd.DataFrame(columns=["loc_x", "loc_y", "shot_made"]))
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestZoneLeadersChart:
    """Tests for zone_leaders_chart."""

    def test_returns_figure(self):
        leaders = {
            "Restricted Area": {"player_name": "Coby White", "ppg": 6.1},
            "Above the Break 3": {"player_name": "Zach LaVine", "ppg": 5.8},
        }
        fig = zone_leaders_chart(leaders)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty(self):
        fig = zone_leaders_chart({})
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestEfficiencyMatrix:
    """Tests for efficiency_matrix."""

    def test_returns_figure(self, mock_roster_efficiency_data):
        fig = efficiency_matrix(mock_roster_efficiency_data)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_data(self):
        fig = efficiency_matrix([])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_single_player(self):
        fig = efficiency_matrix([{"player_id": 1, "name": "Player A", "ts_pct": 58.5, "fga_per_game": 14.2}])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_respects_toggles(self, mock_roster_efficiency_data):
        fig = efficiency_matrix(mock_roster_efficiency_data, show_gradient=False, show_names=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_missing_columns(self):
        fig = efficiency_matrix([{"name": "Unknown"}])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
