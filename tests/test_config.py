import pytest
from bulls.config import (
    BULLS_TEAM_ID,
    CURRENT_SEASON,
)


class TestConfig:
    def test_bulls_team_id(self):
        assert BULLS_TEAM_ID == 1610612741

    def test_current_season(self):
        assert CURRENT_SEASON == "2025-26"
