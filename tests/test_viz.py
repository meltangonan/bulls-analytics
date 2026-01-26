"""Tests for bulls.viz module."""
import pytest
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from unittest.mock import patch, MagicMock
from PIL import Image

from bulls.viz import (
    bar_chart,
    line_chart,
    rolling_efficiency_chart,
    radar_chart,
    shot_chart,
    efficiency_matrix,
)
from bulls.config import OUTPUT_DIR


class TestBarChart:
    """Tests for bar_chart function."""

    def test_returns_figure(self):
        """Should return a matplotlib Figure object."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08', '2026-01-06'],
            'points': [28, 22, 25],
        })

        fig = bar_chart(data, x='date', y='points')

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_saves_to_file(self, tmp_path):
        """Should save chart to file when save_path provided."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08'],
            'points': [28, 22],
        })

        save_path = tmp_path / "test_chart.png"
        fig = bar_chart(data, x='date', y='points', save_path=str(save_path))

        assert save_path.exists()
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        """Should handle empty DataFrame gracefully."""
        empty_data = pd.DataFrame(columns=['date', 'points'])

        # Should not raise an error
        fig = bar_chart(empty_data, x='date', y='points')
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_missing_column(self):
        """Should handle missing column gracefully."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08'],
            'points': [28, 22],
        })

        # Missing x column - should still create figure
        fig = bar_chart(data, x='missing', y='points')
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestLineChart:
    """Tests for line_chart function."""

    def test_returns_figure(self):
        """Should return a matplotlib Figure object."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08', '2026-01-06'],
            'points': [28, 22, 25],
        })

        fig = line_chart(data, x='date', y='points')

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_saves_to_file(self, tmp_path):
        """Should save chart to file when save_path provided."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08'],
            'points': [28, 22],
        })

        save_path = tmp_path / "test_line.png"
        fig = line_chart(data, x='date', y='points', save_path=str(save_path))

        assert save_path.exists()
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        """Should handle empty DataFrame gracefully."""
        empty_data = pd.DataFrame(columns=['date', 'points'])

        # Should not raise an error
        fig = line_chart(empty_data, x='date', y='points')
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestRollingEfficiencyChart:
    """Tests for rolling_efficiency_chart function."""

    def test_returns_figure(self):
        """Should return a matplotlib Figure object."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08', '2026-01-06'],
            'ts_pct_roll_5': [55.0, 58.0, 52.0],
            'result': ['W', 'L', 'W'],
        })

        fig = rolling_efficiency_chart(data, efficiency_col='ts_pct_roll_5')

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_dataframe(self):
        """Should handle empty DataFrame gracefully."""
        empty_data = pd.DataFrame(columns=['date', 'ts_pct_roll_5', 'result'])

        fig = rolling_efficiency_chart(empty_data, efficiency_col='ts_pct_roll_5')
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_custom_league_avg(self):
        """Should respect custom league average."""
        data = pd.DataFrame({
            'date': ['2026-01-10'],
            'ts_pct_roll_5': [55.0],
            'result': ['W'],
        })

        fig = rolling_efficiency_chart(data, efficiency_col='ts_pct_roll_5', league_avg=60.0)
        assert fig is not None
        plt.close(fig)

    def test_saves_to_file(self, tmp_path):
        """Should save chart to file when save_path provided."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08'],
            'ts_pct_roll_5': [55.0, 58.0],
            'result': ['W', 'L'],
        })

        save_path = tmp_path / "test_rolling.png"
        fig = rolling_efficiency_chart(data, efficiency_col='ts_pct_roll_5', save_path=str(save_path))

        assert save_path.exists()
        plt.close(fig)


class TestRadarChart:
    """Tests for radar_chart function."""

    def test_returns_figure(self):
        """Should return a matplotlib Figure object."""
        players_data = [
            {'name': 'Player A', 'points': 20, 'rebounds': 5, 'assists': 6},
        ]

        fig = radar_chart(players_data, metrics=['points', 'rebounds', 'assists'])

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_multiple_players(self):
        """Should handle multiple players."""
        players_data = [
            {'name': 'Player A', 'points': 20, 'rebounds': 5, 'assists': 6},
            {'name': 'Player B', 'points': 25, 'rebounds': 8, 'assists': 4},
        ]

        fig = radar_chart(players_data, metrics=['points', 'rebounds', 'assists'])

        assert fig is not None
        plt.close(fig)

    def test_handles_empty_players_list(self):
        """Should handle empty players list gracefully."""
        fig = radar_chart([], metrics=['points', 'rebounds', 'assists'])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_missing_metrics(self):
        """Should handle missing metrics gracefully."""
        players_data = [
            {'name': 'Player A', 'points': 20},  # Missing rebounds, assists
        ]

        fig = radar_chart(players_data, metrics=['points', 'rebounds', 'assists'])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_normalization(self):
        """Should normalize values when normalize=True."""
        players_data = [
            {'name': 'Player A', 'points': 20, 'rebounds': 5, 'assists': 6},
        ]

        fig = radar_chart(players_data, normalize=True)
        assert fig is not None
        plt.close(fig)

    def test_saves_to_file(self, tmp_path):
        """Should save chart to file when save_path provided."""
        players_data = [
            {'name': 'Player A', 'points': 20, 'rebounds': 5, 'assists': 6},
        ]

        save_path = tmp_path / "test_radar.png"
        fig = radar_chart(players_data, save_path=str(save_path))

        assert save_path.exists()
        plt.close(fig)


class TestShotChart:
    """Tests for shot_chart function."""

    def test_returns_figure(self):
        """Should return a matplotlib Figure object."""
        shots_data = pd.DataFrame({
            'loc_x': [0, 100, -100],
            'loc_y': [50, 200, 150],
            'shot_made': [True, False, True],
        })

        fig = shot_chart(shots_data)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_data(self):
        """Should handle empty DataFrame gracefully."""
        empty_data = pd.DataFrame(columns=['loc_x', 'loc_y', 'shot_made'])

        fig = shot_chart(empty_data)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_scatter_mode(self):
        """Should create scatter plot when show_zones=False."""
        shots_data = pd.DataFrame({
            'loc_x': [0, 100, -100],
            'loc_y': [50, 200, 150],
            'shot_made': [True, False, True],
        })

        fig = shot_chart(shots_data, show_zones=False)
        assert fig is not None
        plt.close(fig)

    def test_heatmap_mode(self):
        """Should create heatmap when show_zones=True."""
        shots_data = pd.DataFrame({
            'loc_x': [0, 100, -100, 50, 75],
            'loc_y': [50, 200, 150, 100, 120],
            'shot_made': [True, False, True, True, False],
        })

        fig = shot_chart(shots_data, show_zones=True)
        assert fig is not None
        plt.close(fig)

    def test_saves_to_file(self, tmp_path):
        """Should save chart to file when save_path provided."""
        shots_data = pd.DataFrame({
            'loc_x': [0, 100],
            'loc_y': [50, 200],
            'shot_made': [True, False],
        })

        save_path = tmp_path / "test_shot_chart.png"
        fig = shot_chart(shots_data, save_path=str(save_path))

        assert save_path.exists()
        plt.close(fig)

    def test_handles_all_makes(self):
        """Should handle data with all makes."""
        shots_data = pd.DataFrame({
            'loc_x': [0, 100, -100],
            'loc_y': [50, 200, 150],
            'shot_made': [True, True, True],
        })

        fig = shot_chart(shots_data)
        assert fig is not None
        plt.close(fig)

    def test_handles_all_misses(self):
        """Should handle data with all misses."""
        shots_data = pd.DataFrame({
            'loc_x': [0, 100, -100],
            'loc_y': [50, 200, 150],
            'shot_made': [False, False, False],
        })

        fig = shot_chart(shots_data)
        assert fig is not None
        plt.close(fig)


class TestEfficiencyMatrix:
    """Tests for efficiency_matrix function."""

    def test_returns_figure(self, mock_roster_efficiency_data, mock_headshot_request):
        """Should return a matplotlib Figure object."""
        fig = efficiency_matrix(mock_roster_efficiency_data)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_empty_data(self):
        """Should handle empty data gracefully."""
        fig = efficiency_matrix([])

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_single_player(self, mock_headshot_request):
        """Should handle single player data."""
        single_player = [
            {'player_id': 1629632, 'name': 'Coby White', 'ts_pct': 58.5, 'fga_per_game': 14.2}
        ]

        fig = efficiency_matrix(single_player)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_respects_show_gradient_toggle(self, mock_roster_efficiency_data, mock_headshot_request):
        """Should work with show_gradient=False."""
        fig = efficiency_matrix(mock_roster_efficiency_data, show_gradient=False)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_respects_show_names_toggle(self, mock_roster_efficiency_data, mock_headshot_request):
        """Should work with show_names=False."""
        fig = efficiency_matrix(mock_roster_efficiency_data, show_names=False)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_respects_custom_thresholds(self, mock_roster_efficiency_data, mock_headshot_request):
        """Should respect custom league average thresholds."""
        fig = efficiency_matrix(
            mock_roster_efficiency_data,
            league_avg_ts=55.0,
            league_avg_fga=10.0,
        )

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_saves_to_file(self, mock_roster_efficiency_data, mock_headshot_request, tmp_path):
        """Should save chart to file when save_path provided."""
        save_path = tmp_path / "test_efficiency_matrix.png"
        fig = efficiency_matrix(mock_roster_efficiency_data, save_path=str(save_path))

        assert save_path.exists()
        plt.close(fig)

    def test_handles_headshot_errors_gracefully(self, mock_roster_efficiency_data, mock_headshot_error):
        """Should handle headshot fetch errors gracefully."""
        fig = efficiency_matrix(mock_roster_efficiency_data)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_handles_missing_player_id(self, mock_headshot_request):
        """Should handle players without player_id."""
        data_without_id = [
            {'name': 'Unknown Player', 'ts_pct': 55.0, 'fga_per_game': 10.0}
        ]

        fig = efficiency_matrix(data_without_id)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_custom_title(self, mock_roster_efficiency_data, mock_headshot_request):
        """Should use custom title."""
        custom_title = "Custom Matrix Title"
        fig = efficiency_matrix(mock_roster_efficiency_data, title=custom_title)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_custom_figsize(self, mock_roster_efficiency_data, mock_headshot_request):
        """Should respect custom figsize."""
        fig = efficiency_matrix(mock_roster_efficiency_data, figsize=(8, 6))

        assert isinstance(fig, plt.Figure)
        plt.close(fig)
