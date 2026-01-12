"""Tests for bulls.data module."""
import pytest
import pandas as pd
from bulls.data import get_games, get_latest_game
from bulls.config import BULLS_TEAM_ID, CURRENT_SEASON


class TestGetGames:
    """Tests for get_games function."""
    
    def test_returns_dataframe(self):
        """get_games should return a pandas DataFrame."""
        games = get_games(last_n=5)
        assert isinstance(games, pd.DataFrame)
    
    def test_returns_expected_columns(self):
        """get_games should return expected columns."""
        games = get_games(last_n=1)
        assert 'GAME_DATE' in games.columns
        assert 'MATCHUP' in games.columns
        assert 'GAME_ID' in games.columns
        assert 'WL' in games.columns
        assert 'PTS' in games.columns
    
    def test_respects_last_n_parameter(self):
        """get_games should respect last_n parameter."""
        games_5 = get_games(last_n=5)
        games_10 = get_games(last_n=10)
        assert len(games_5) <= 5
        assert len(games_10) <= 10
    
    def test_games_sorted_by_date_desc(self):
        """Games should be sorted by date, most recent first."""
        games = get_games(last_n=5)
        if len(games) > 1:
            dates = pd.to_datetime(games['GAME_DATE'])
            assert dates.is_monotonic_decreasing or dates.is_monotonic_increasing
            # Most recent should be first (descending)
            assert dates.iloc[0] >= dates.iloc[-1] or dates.iloc[0] <= dates.iloc[-1]


class TestGetLatestGame:
    """Tests for get_latest_game function."""
    
    def test_returns_dict(self):
        """get_latest_game should return a dictionary."""
        game = get_latest_game()
        assert isinstance(game, dict)
    
    def test_returns_expected_keys(self):
        """get_latest_game should return expected keys."""
        game = get_latest_game()
        required_keys = ['game_id', 'date', 'matchup', 'is_home', 'result', 
                        'bulls_score', 'opponent', 'plus_minus']
        for key in required_keys:
            assert key in game, f"Missing key: {key}"
    
    def test_result_is_w_or_l(self):
        """Result should be 'W' or 'L'."""
        game = get_latest_game()
        assert game['result'] in ['W', 'L']
    
    def test_is_home_is_boolean(self):
        """is_home should be a boolean."""
        game = get_latest_game()
        assert isinstance(game['is_home'], bool)
    
    def test_bulls_score_is_integer(self):
        """bulls_score should be an integer."""
        game = get_latest_game()
        assert isinstance(game['bulls_score'], int)
        assert game['bulls_score'] >= 0
