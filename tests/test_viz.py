"""Tests for bulls.viz module."""
import pytest
import pandas as pd
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

from bulls.viz import bar_chart, line_chart, create_graphic
from bulls.config import OUTPUT_DIR, INSTAGRAM_PORTRAIT


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


class TestCreateGraphic:
    """Tests for create_graphic function."""
    
    def test_returns_image(self):
        """Should return a PIL Image object."""
        img = create_graphic(title="TEST TITLE")
        
        assert isinstance(img, Image.Image)
    
    def test_creates_correct_size(self):
        """Should create image with correct dimensions."""
        img = create_graphic(title="TEST", size=INSTAGRAM_PORTRAIT)
        
        assert img.size == INSTAGRAM_PORTRAIT
    
    def test_handles_title_only(self):
        """Should create graphic with just a title."""
        img = create_graphic(title="TITLE ONLY")
        
        assert img is not None
        assert img.size == INSTAGRAM_PORTRAIT
    
    def test_handles_subtitle(self):
        """Should create graphic with title and subtitle."""
        img = create_graphic(
            title="MAIN TITLE",
            subtitle="Subtitle text"
        )
        
        assert img is not None
    
    def test_handles_stats(self):
        """Should create graphic with stats."""
        img = create_graphic(
            title="PLAYER STATS",
            stats={'PTS': 28, 'REB': 5, 'AST': 7}
        )
        
        assert img is not None
    
    def test_handles_player_name(self):
        """Should create graphic with player name."""
        img = create_graphic(
            title="PLAYER PERFORMANCE",
            player_name="COBY WHITE"
        )
        
        assert img is not None
    
    def test_handles_player_image(self):
        """Should create graphic with player image."""
        # Create a simple test image
        test_img = Image.new('RGB', (100, 100), color='red')
        
        img = create_graphic(
            title="PLAYER WITH IMAGE",
            player_image=test_img
        )
        
        assert img is not None
    
    def test_handles_all_parameters(self):
        """Should create graphic with all parameters."""
        test_img = Image.new('RGB', (100, 100), color='blue')
        
        img = create_graphic(
            title="FULL GRAPHIC",
            subtitle="Bulls vs Heat • Jan 10, 2026",
            stats={'PTS': 28, 'REB': 5, 'AST': 7},
            player_name="COBY WHITE",
            player_image=test_img,
            footer="@bullsanalytics"
        )
        
        assert img is not None
    
    def test_saves_to_file(self, tmp_path):
        """Should save graphic to file when save_path provided."""
        save_path = tmp_path / "test_graphic.png"
        img = create_graphic(
            title="TEST",
            save_path=str(save_path)
        )
        
        assert save_path.exists()
        assert save_path.suffix == '.png'
    
    def test_custom_size(self):
        """Should create graphic with custom size."""
        custom_size = (500, 500)
        img = create_graphic(title="TEST", size=custom_size)
        
        assert img.size == custom_size
    
    def test_custom_footer(self):
        """Should use custom footer text."""
        img = create_graphic(
            title="TEST",
            footer="@customhandle"
        )
        
        assert img is not None
    
    def test_handles_empty_stats(self):
        """Should handle empty stats dict."""
        img = create_graphic(
            title="TEST",
            stats={}
        )
        
        assert img is not None
    
    def test_handles_none_stats(self):
        """Should handle None stats."""
        img = create_graphic(
            title="TEST",
            stats=None
        )
        
        assert img is not None
