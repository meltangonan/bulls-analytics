"""Pytest fixtures for Bulls Analytics tests."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from PIL import Image


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


# Sample box score data
MOCK_BOX_SCORE_DATA = pd.DataFrame([
    {
        'personId': 1629632,
        'firstName': 'Coby',
        'familyName': 'White',
        'teamId': 1610612741,  # Bulls
        'points': 28,
        'reboundsTotal': 5,
        'assists': 7,
        'steals': 2,
        'blocks': 0,
        'fieldGoalsMade': 10,
        'fieldGoalsAttempted': 18,
        'threePointersMade': 4,
        'threePointersAttempted': 8,
        'minutes': '35:23',
    },
    {
        'personId': 1629629,
        'firstName': 'Nikola',
        'familyName': 'Vučević',
        'teamId': 1610612741,  # Bulls
        'points': 22,
        'reboundsTotal': 12,
        'assists': 3,
        'steals': 1,
        'blocks': 1,
        'fieldGoalsMade': 9,
        'fieldGoalsAttempted': 15,
        'threePointersMade': 2,
        'threePointersAttempted': 4,
        'minutes': '32:15',
    },
    {
        'personId': 1234567,
        'firstName': 'Opponent',
        'familyName': 'Player',
        'teamId': 1610612748,  # Not Bulls
        'points': 20,
        'reboundsTotal': 8,
        'assists': 5,
        'steals': 0,
        'blocks': 0,
        'fieldGoalsMade': 8,
        'fieldGoalsAttempted': 16,
        'threePointersMade': 2,
        'threePointersAttempted': 5,
        'minutes': '28:00',
    },
])


@pytest.fixture
def mock_box_score():
    """Mock the NBA API BoxScoreTraditionalV3 to return sample data."""
    with patch('bulls.data.fetch.boxscoretraditionalv3.BoxScoreTraditionalV3') as mock_box:
        mock_instance = MagicMock()
        mock_instance.player_stats.get_data_frame.return_value = MOCK_BOX_SCORE_DATA.copy()
        mock_box.return_value = mock_instance
        yield mock_box


@pytest.fixture
def mock_empty_box_score():
    """Mock the NBA API BoxScoreTraditionalV3 to return empty data."""
    with patch('bulls.data.fetch.boxscoretraditionalv3.BoxScoreTraditionalV3') as mock_box:
        mock_instance = MagicMock()
        mock_instance.player_stats.get_data_frame.return_value = pd.DataFrame()
        mock_box.return_value = mock_instance
        yield mock_box


@pytest.fixture
def mock_player_headshot():
    """Mock requests.get to return a sample player headshot image."""
    mock_img = Image.new('RGBA', (300, 300), (100, 100, 100, 255))
    with patch('bulls.data.fetch.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.content = b'fake_image_data'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Mock Image.open to return our test image when called with BytesIO
        with patch('bulls.data.fetch.Image.open', return_value=mock_img):
            yield mock_get


@pytest.fixture
def mock_failed_headshot():
    """Mock requests.get to fail when fetching headshot."""
    with patch('bulls.data.fetch.requests.get') as mock_get:
        import requests
        mock_get.side_effect = requests.RequestException("Failed to fetch")
        yield mock_get
