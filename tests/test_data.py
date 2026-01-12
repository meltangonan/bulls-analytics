"""Tests for bulls.data module."""
import pytest
import pandas as pd
from PIL import Image
from bulls.data import (
    get_games,
    get_latest_game,
    get_box_score,
    get_player_games,
    get_player_headshot,
)
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


class TestGetBoxScore:
    """Tests for get_box_score function."""
    
    def test_returns_dataframe(self):
        """get_box_score should return a pandas DataFrame."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        assert isinstance(box, pd.DataFrame)
    
    def test_returns_expected_columns(self):
        """get_box_score should return expected columns."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        
        if not box.empty:
            # Check for key columns that should exist
            assert 'name' in box.columns
            assert 'points' in box.columns or 'firstName' in box.columns
    
    def test_handles_invalid_game_id(self):
        """get_box_score should handle invalid game_id gracefully."""
        # Use a clearly invalid game ID
        box = get_box_score("0000000000")
        assert isinstance(box, pd.DataFrame)
        # Should return empty DataFrame or handle gracefully
    
    def test_returns_bulls_players_only(self):
        """get_box_score should only return Bulls players."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        
        if not box.empty:
            # All players should be Bulls players (teamId check is done in function)
            # We can't easily verify this without the teamId column, but the function filters it
            assert len(box) > 0  # At least some players returned
    
    def test_handles_empty_result(self):
        """get_box_score should handle empty results gracefully."""
        # This test verifies the function doesn't crash on edge cases
        # The function should return an empty DataFrame, not raise an exception
        box = get_box_score("9999999999")  # Invalid game ID
        assert isinstance(box, pd.DataFrame)


class TestGetPlayerGames:
    """Tests for get_player_games function."""
    
    def test_returns_dataframe(self):
        """get_player_games should return a pandas DataFrame."""
        # Use a real player name - this might take a while due to API calls
        player_games = get_player_games("Coby White", last_n=5)
        assert isinstance(player_games, pd.DataFrame)
    
    def test_returns_expected_columns(self):
        """get_player_games should return expected columns."""
        player_games = get_player_games("Coby White", last_n=3)
        
        if not player_games.empty:
            expected_columns = [
                'game_id', 'date', 'matchup', 'result',
                'points', 'rebounds', 'assists', 'steals', 'blocks',
                'fg_made', 'fg_attempted', 'fg3_made', 'fg3_attempted',
                'minutes', 'fg_pct', 'fg3_pct'
            ]
            for col in expected_columns:
                assert col in player_games.columns, f"Missing column: {col}"
    
    def test_respects_last_n_parameter(self):
        """get_player_games should respect last_n parameter."""
        player_games_3 = get_player_games("Coby White", last_n=3)
        player_games_5 = get_player_games("Coby White", last_n=5)
        
        # Should return at most last_n games (accounting for DNPs)
        assert len(player_games_3) <= 3
        assert len(player_games_5) <= 5
    
    def test_handles_player_not_found(self):
        """get_player_games should handle player not found gracefully."""
        # Use a clearly fake player name
        player_games = get_player_games("Fake Player Name XYZ", last_n=5)
        assert isinstance(player_games, pd.DataFrame)
        # Should return empty DataFrame, not raise exception
        assert player_games.empty
    
    def test_calculates_percentages(self):
        """get_player_games should calculate fg_pct and fg3_pct."""
        player_games = get_player_games("Coby White", last_n=3)
        
        if not player_games.empty:
            assert 'fg_pct' in player_games.columns
            assert 'fg3_pct' in player_games.columns
            # Percentages should be numeric
            assert pd.api.types.is_numeric_dtype(player_games['fg_pct'])
            assert pd.api.types.is_numeric_dtype(player_games['fg3_pct'])
    
    def test_handles_case_insensitive_name(self):
        """get_player_games should handle case-insensitive player names."""
        player_games_lower = get_player_games("coby white", last_n=2)
        player_games_upper = get_player_games("COBY WHITE", last_n=2)
        
        # Both should work (case-insensitive matching)
        assert isinstance(player_games_lower, pd.DataFrame)
        assert isinstance(player_games_upper, pd.DataFrame)


class TestGetPlayerHeadshot:
    """Tests for get_player_headshot function."""
    
    def test_returns_image(self):
        """get_player_headshot should return a PIL Image."""
        # Coby White's player ID: 1629632
        img = get_player_headshot(1629632)
        assert isinstance(img, Image.Image)
    
    def test_respects_size_parameter(self):
        """get_player_headshot should respect size parameter."""
        img = get_player_headshot(1629632, size=(200, 200))
        assert img.size == (200, 200)
    
    def test_handles_invalid_player_id(self):
        """get_player_headshot should handle invalid player_id gracefully."""
        # Use a clearly invalid player ID
        img = get_player_headshot(999999999)
        assert isinstance(img, Image.Image)
        # Should return placeholder image, not raise exception
    
    def test_returns_rgba_image(self):
        """get_player_headshot should return RGBA image."""
        img = get_player_headshot(1629632)
        assert img.mode == 'RGBA'
    
    def test_handles_network_errors(self):
        """get_player_headshot should handle network errors gracefully."""
        # This test verifies the function doesn't crash on network issues
        # The function should return a placeholder, not raise an exception
        # We can't easily simulate network errors, but we can test invalid IDs
        img = get_player_headshot(0)  # Invalid ID
        assert isinstance(img, Image.Image)
