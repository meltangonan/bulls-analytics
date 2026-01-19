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
        'freeThrowsMade': 3,
        'freeThrowsAttempted': 4,
        'turnovers': 2,
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
        'freeThrowsMade': 4,
        'freeThrowsAttempted': 5,
        'turnovers': 3,
        'minutes': '35:42',
    },
])


# Sample shot chart data
MOCK_SHOT_CHART_DATA = pd.DataFrame([
    {
        'LOC_X': 0,
        'LOC_Y': 50,
        'SHOT_MADE_FLAG': 1,
        'SHOT_TYPE': '2PT Field Goal',
        'SHOT_ZONE_BASIC': 'Restricted Area',
        'SHOT_DISTANCE': 2,
        'GAME_ID': '0022500503',
    },
    {
        'LOC_X': 150,
        'LOC_Y': 200,
        'SHOT_MADE_FLAG': 0,
        'SHOT_TYPE': '3PT Field Goal',
        'SHOT_ZONE_BASIC': 'Right Corner 3',
        'SHOT_DISTANCE': 24,
        'GAME_ID': '0022500503',
    },
    {
        'LOC_X': -100,
        'LOC_Y': 100,
        'SHOT_MADE_FLAG': 1,
        'SHOT_TYPE': '2PT Field Goal',
        'SHOT_ZONE_BASIC': 'Mid-Range',
        'SHOT_DISTANCE': 12,
        'GAME_ID': '0022500489',
    },
    {
        'LOC_X': 0,
        'LOC_Y': 250,
        'SHOT_MADE_FLAG': 1,
        'SHOT_TYPE': '3PT Field Goal',
        'SHOT_ZONE_BASIC': 'Above the Break 3',
        'SHOT_DISTANCE': 26,
        'GAME_ID': '0022500489',
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


@pytest.fixture
def mock_shot_chart_api():
    """Mock the NBA API ShotChartDetail to return sample data."""
    with patch('bulls.data.fetch.shotchartdetail.ShotChartDetail') as mock_shot:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [MOCK_SHOT_CHART_DATA.copy()]
        mock_shot.return_value = mock_instance
        yield mock_shot


@pytest.fixture
def mock_empty_shot_chart_api():
    """Mock the NBA API ShotChartDetail to return empty data."""
    with patch('bulls.data.fetch.shotchartdetail.ShotChartDetail') as mock_shot:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [pd.DataFrame()]
        mock_shot.return_value = mock_instance
        yield mock_shot


@pytest.fixture
def sample_player_games():
    """Sample player games DataFrame for analysis tests."""
    return pd.DataFrame({
        'game_id': ['001', '002', '003', '004', '005'],
        'date': ['2026-01-10', '2026-01-08', '2026-01-06', '2026-01-04', '2026-01-02'],
        'matchup': ['CHI vs. MIA', 'CHI @ BOS', 'CHI vs. NYK', 'CHI @ LAL', 'CHI vs. GSW'],
        'result': ['W', 'L', 'W', 'L', 'W'],
        'points': [25, 18, 30, 22, 28],
        'rebounds': [5, 4, 6, 3, 7],
        'assists': [6, 4, 8, 5, 7],
        'steals': [2, 1, 2, 1, 3],
        'blocks': [0, 1, 0, 1, 1],
        'fg_made': [10, 7, 12, 9, 11],
        'fg_attempted': [20, 18, 22, 20, 21],
        'fg3_made': [3, 2, 4, 2, 4],
        'fg3_attempted': [8, 7, 9, 8, 10],
        'ft_made': [2, 2, 2, 2, 2],
        'ft_attempted': [3, 2, 3, 3, 2],
        'turnovers': [2, 3, 1, 4, 2],
        'fg_pct': [50.0, 38.9, 54.5, 45.0, 52.4],
        'fg3_pct': [37.5, 28.6, 44.4, 25.0, 40.0],
        'ft_pct': [66.7, 100.0, 66.7, 66.7, 100.0],
    })
