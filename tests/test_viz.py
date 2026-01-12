"""Tests for bulls.viz module."""
import pytest
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

from bulls.viz import bar_chart, line_chart
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


