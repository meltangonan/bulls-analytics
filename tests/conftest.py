"""Pytest fixtures for Bulls Analytics tests."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


# Sample game data matching NBA API response format
MOCK_GAMES_DATA = pd.DataFrame([
    {
        'GAME_ID': '0022500503',
        'GAME_DATE': '2026-01-10',
        'MATCHUP': 'CHI vs. MIA',
        'WL': 'W',
        'PTS': 112,
        'PLUS_MINUS': 8,
        'MIN': 240,
        'FGM': 42,
        'FGA': 88,
        'FG_PCT': 0.477,
    },
    {
        'GAME_ID': '0022500489',
        'GAME_DATE': '2026-01-08',
        'MATCHUP': 'CHI @ BOS',
        'WL': 'L',
        'PTS': 98,
        'PLUS_MINUS': -12,
        'MIN': 240,
        'FGM': 36,
        'FGA': 85,
        'FG_PCT': 0.424,
    },
    {
        'GAME_ID': '0022500475',
        'GAME_DATE': '2026-01-06',
        'MATCHUP': 'CHI vs. NYK',
        'WL': 'W',
        'PTS': 105,
        'PLUS_MINUS': 3,
        'MIN': 240,
        'FGM': 40,
        'FGA': 90,
        'FG_PCT': 0.444,
    },
])


@pytest.fixture
def mock_nba_api():
    """Mock the NBA API LeagueGameFinder to return sample data."""
    with patch('bulls.data.fetch.leaguegamefinder.LeagueGameFinder') as mock_finder:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [MOCK_GAMES_DATA.copy()]
        mock_finder.return_value = mock_instance
        yield mock_finder


@pytest.fixture
def mock_empty_api():
    """Mock the NBA API to return empty data."""
    with patch('bulls.data.fetch.leaguegamefinder.LeagueGameFinder') as mock_finder:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [pd.DataFrame()]
        mock_finder.return_value = mock_instance
        yield mock_finder
