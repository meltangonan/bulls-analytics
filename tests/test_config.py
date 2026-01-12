"""Tests for bulls.config module."""
import pytest
from bulls.config import (
    BULLS_TEAM_ID,
    BULLS_ABBR,
    CURRENT_SEASON,
    BULLS_RED,
    BULLS_BLACK,
    OUTPUT_DIR,
)


class TestConfig:
    """Tests for configuration constants."""
    
    def test_bulls_team_id(self):
        """BULLS_TEAM_ID should be correct."""
        assert BULLS_TEAM_ID == 1610612741
    
    def test_bulls_abbr(self):
        """BULLS_ABBR should be 'CHI'."""
        assert BULLS_ABBR == "CHI"
    
    def test_current_season(self):
        """CURRENT_SEASON should be set."""
        assert CURRENT_SEASON == "2025-26"
    
    def test_colors_are_tuples(self):
        """Color constants should be RGB tuples."""
        assert isinstance(BULLS_RED, tuple)
        assert isinstance(BULLS_BLACK, tuple)
        assert len(BULLS_RED) == 3
        assert len(BULLS_BLACK) == 3
    
    def test_output_dir_exists(self):
        """OUTPUT_DIR should be a Path object."""
        assert OUTPUT_DIR.exists() or OUTPUT_DIR.parent.exists()
