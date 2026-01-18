"""Pytest fixtures for Bulls Analytics tests."""
import pytest
import pandas as pd
from io import BytesIO
from PIL import Image
from unittest.mock import MagicMock, patch

from bulls.config import BULLS_TEAM_ID


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


# Sample box score data matching NBA API response format
MOCK_BOX_SCORE_DATA = pd.DataFrame([
    {
        'teamId': BULLS_TEAM_ID,
        'firstName': 'Coby',
        'familyName': 'White',
        'points': 22,
        'reboundsTotal': 4,
        'assists': 5,
        'steals': 1,
        'blocks': 0,
        'fieldGoalsMade': 8,
        'fieldGoalsAttempted': 16,
        'threePointersMade': 3,
        'threePointersAttempted': 7,
        'minutes': '32:15',
    },
    {
        'teamId': BULLS_TEAM_ID,
        'firstName': 'Zach',
        'familyName': 'LaVine',
        'points': 28,
        'reboundsTotal': 6,
        'assists': 4,
        'steals': 2,
        'blocks': 1,
        'fieldGoalsMade': 10,
        'fieldGoalsAttempted': 20,
        'threePointersMade': 4,
        'threePointersAttempted': 9,
        'minutes': '35:42',
    },
])


@pytest.fixture
def mock_box_score_api():
    """Mock the NBA API BoxScoreTraditionalV3 to return sample data."""
    with patch('bulls.data.fetch.boxscoretraditionalv3.BoxScoreTraditionalV3') as mock_box:
        mock_instance = MagicMock()
        mock_df = MOCK_BOX_SCORE_DATA.copy()
        mock_instance.player_stats.get_data_frame.return_value = mock_df
        mock_box.return_value = mock_instance
        yield mock_box


@pytest.fixture
def mock_empty_box_score_api():
    """Mock the NBA API BoxScoreTraditionalV3 to return empty data."""
    with patch('bulls.data.fetch.boxscoretraditionalv3.BoxScoreTraditionalV3') as mock_box:
        mock_instance = MagicMock()
        mock_instance.player_stats.get_data_frame.return_value = pd.DataFrame()
        mock_box.return_value = mock_instance
        yield mock_box


@pytest.fixture
def mock_headshot_request():
    """Mock requests.get for player headshot URLs."""
    with patch('bulls.data.fetch.requests.get') as mock_get:
        # Create a simple test image
        img = Image.new('RGBA', (260, 190), (255, 0, 0, 255))
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        mock_response = MagicMock()
        mock_response.content = img_bytes.read()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_headshot_error():
    """Mock requests.get to simulate a network error."""
    import requests
    with patch('bulls.data.fetch.requests.get') as mock_get:
        mock_get.side_effect = requests.RequestException("Network error")
        yield mock_get
