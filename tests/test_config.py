"""Tests for bulls.config module."""
import pytest
from bulls.config import (
    BULLS_TEAM_ID,
    CURRENT_SEASON,
)


class TestConfig:
    """Tests for configuration constants."""

    def test_bulls_team_id(self):
        """BULLS_TEAM_ID should be correct."""
        assert BULLS_TEAM_ID == 1610612741

    def test_current_season(self):
        """CURRENT_SEASON should be set."""
        assert CURRENT_SEASON == "2025-26"
