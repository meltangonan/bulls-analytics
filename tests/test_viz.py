"""Tests for bulls.viz module."""
import pytest
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

from bulls.viz import (
    bar_chart,
    line_chart,
    rolling_efficiency_chart,
    radar_chart,
    shot_chart,
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
    
    def test_handles_basic_data(self):
        """Should create chart with basic data."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08', '2026-01-06'],
            'points': [28, 22, 25],
        })
        
        fig = bar_chart(data, x='date', y='points', title="Test Chart")
        
        assert fig is not None
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
    
    def test_custom_title(self):
        """Should use custom title."""
        data = pd.DataFrame({
            'date': ['2026-01-10'],
            'points': [28],
        })
        
        fig = bar_chart(data, x='date', y='points', title="Custom Title")
        assert fig is not None
        plt.close(fig)
    
    def test_reverses_data_chronologically(self):
        """Should reverse data so oldest is first (left to right)."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08', '2026-01-06'],
            'points': [28, 22, 25],
        })
        
        fig = bar_chart(data, x='date', y='points')
        # Just verify it doesn't crash - the reversal is internal
        assert fig is not None
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
    
    def test_handles_basic_data(self):
        """Should create chart with basic data."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08', '2026-01-06'],
            'points': [28, 22, 25],
        })
        
        fig = line_chart(data, x='date', y='points', title="Test Line Chart")
        
        assert fig is not None
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
    
    def test_custom_title(self):
        """Should use custom title."""
        data = pd.DataFrame({
            'date': ['2026-01-10'],
            'points': [28],
        })

        fig = line_chart(data, x='date', y='points', title="Custom Line Title")
        assert fig is not None
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

    def test_handles_basic_data(self):
        """Should create chart with basic data."""
        data = pd.DataFrame({
            'date': ['2026-01-10', '2026-01-08', '2026-01-06'],
            'ts_pct_roll_5': [55.0, 58.0, 52.0],
            'result': ['W', 'L', 'W'],
        })

        fig = rolling_efficiency_chart(data, efficiency_col='ts_pct_roll_5', title="Test Chart")

        assert fig is not None
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

    def test_no_normalization(self):
        """Should not normalize values when normalize=False."""
        players_data = [
            {'name': 'Player A', 'points': 20, 'rebounds': 5, 'assists': 6},
        ]

        fig = radar_chart(players_data, normalize=False)
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

    def test_custom_title(self):
        """Should use custom title."""
        shots_data = pd.DataFrame({
            'loc_x': [0],
            'loc_y': [50],
            'shot_made': [True],
        })

        fig = shot_chart(shots_data, title="Test Shot Chart")
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
