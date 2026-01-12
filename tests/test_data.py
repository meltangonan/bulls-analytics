"""Tests for bulls.data module."""
import pytest
import pandas as pd
from PIL import Image
from bulls.data import (
    get_games, 
    get_latest_game, 
    get_box_score, 
    get_player_games, 
    get_player_headshot
)
from bulls.config import BULLS_TEAM_ID


class TestGetGames:
    """Tests for get_games function."""
    
    def test_returns_dataframe(self, mock_nba_api):
        """get_games should return a pandas DataFrame."""
        games = get_games(last_n=5)
        assert isinstance(games, pd.DataFrame)
    
    def test_returns_expected_columns(self, mock_nba_api):
        """get_games should return expected columns."""
        games = get_games(last_n=1)
        assert 'GAME_DATE' in games.columns
        assert 'MATCHUP' in games.columns
        assert 'GAME_ID' in games.columns
        assert 'WL' in games.columns
        assert 'PTS' in games.columns
    
    def test_respects_last_n_parameter(self, mock_nba_api):
        """get_games should respect last_n parameter."""
        games_1 = get_games(last_n=1)
        games_2 = get_games(last_n=2)
        assert len(games_1) == 1
        assert len(games_2) == 2
    
    def test_games_sorted_by_date_desc(self, mock_nba_api):
        """Games should be sorted by date, most recent first."""
        games = get_games(last_n=3)
        dates = pd.to_datetime(games['GAME_DATE'])
        # Most recent should be first (descending order)
        assert dates.iloc[0] >= dates.iloc[-1]
    
    def test_returns_empty_dataframe_when_no_data(self, mock_empty_api):
        """get_games should return empty DataFrame when no games found."""
        games = get_games(last_n=5)
        assert isinstance(games, pd.DataFrame)
        assert games.empty


class TestGetLatestGame:
    """Tests for get_latest_game function."""
    
    def test_returns_dict(self, mock_nba_api):
        """get_latest_game should return a dictionary."""
        game = get_latest_game()
        assert isinstance(game, dict)
    
    def test_returns_expected_keys(self, mock_nba_api):
        """get_latest_game should return expected keys."""
        game = get_latest_game()
        required_keys = ['game_id', 'date', 'matchup', 'is_home', 'result', 
                        'bulls_score', 'opponent', 'plus_minus']
        for key in required_keys:
            assert key in game, f"Missing key: {key}"
    
    def test_result_is_w_or_l(self, mock_nba_api):
        """Result should be 'W' or 'L'."""
        game = get_latest_game()
        assert game['result'] in ['W', 'L']
    
    def test_is_home_is_boolean(self, mock_nba_api):
        """is_home should be a boolean."""
        game = get_latest_game()
        assert isinstance(game['is_home'], bool)
    
    def test_bulls_score_is_integer(self, mock_nba_api):
        """bulls_score should be an integer."""
        game = get_latest_game()
        assert isinstance(game['bulls_score'], int)
        assert game['bulls_score'] >= 0
    
    def test_home_game_detection(self, mock_nba_api):
        """Home games should be detected by 'vs.' in matchup."""
        game = get_latest_game()
        # First mock game is 'CHI vs. MIA' (home game)
        assert game['is_home'] is True
        assert game['opponent'] == 'MIA'
    
    def test_raises_when_no_games(self, mock_empty_api):
        """get_latest_game should raise ValueError when no games found."""
        with pytest.raises(ValueError, match="No games found"):
            get_latest_game()


class TestGetBoxScore:
    """Tests for get_box_score function."""
    
    def test_returns_dataframe(self, mock_nba_api, mock_box_score):
        """get_box_score should return a pandas DataFrame."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        assert isinstance(box, pd.DataFrame)
    
    def test_returns_bulls_players_only(self, mock_nba_api, mock_box_score):
        """get_box_score should only return Bulls players."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        
        if not box.empty:
            # All players should be Bulls
            assert all(box['teamId'] == BULLS_TEAM_ID)
    
    def test_has_name_column(self, mock_nba_api, mock_box_score):
        """Box score should have a 'name' column with full names."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        
        if not box.empty:
            assert 'name' in box.columns
            # Names should be strings
            assert all(isinstance(name, str) for name in box['name'])
    
    def test_has_expected_stat_columns(self, mock_nba_api, mock_box_score):
        """Box score should have expected stat columns."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        
        if not box.empty:
            expected_cols = ['points', 'reboundsTotal', 'assists', 'steals', 'blocks']
            for col in expected_cols:
                assert col in box.columns, f"Missing column: {col}"
    
    def test_handles_empty_box_score(self, mock_nba_api, mock_empty_box_score):
        """get_box_score should handle empty box scores gracefully."""
        game = get_latest_game()
        box = get_box_score(game['game_id'])
        assert isinstance(box, pd.DataFrame)
        assert box.empty


class TestGetPlayerGames:
    """Tests for get_player_games function."""
    
    def test_returns_dataframe(self, mock_nba_api, mock_box_score):
        """get_player_games should return a pandas DataFrame."""
        player_games = get_player_games("Coby White", last_n=3)
        assert isinstance(player_games, pd.DataFrame)
    
    def test_has_expected_columns(self, mock_nba_api, mock_box_score):
        """get_player_games should return expected columns."""
        player_games = get_player_games("Coby White", last_n=3)
        
        if not player_games.empty:
            expected_cols = [
                'game_id', 'date', 'matchup', 'result', 
                'points', 'rebounds', 'assists', 
                'fg_pct', 'fg3_pct'
            ]
            for col in expected_cols:
                assert col in player_games.columns, f"Missing column: {col}"
    
    def test_calculates_percentages(self, mock_nba_api, mock_box_score):
        """get_player_games should calculate fg_pct and fg3_pct."""
        player_games = get_player_games("Coby White", last_n=3)
        
        if not player_games.empty:
            assert 'fg_pct' in player_games.columns
            assert 'fg3_pct' in player_games.columns
            # Percentages should be between 0 and 100 (or NaN for no attempts)
            valid_fg = player_games['fg_pct'].dropna()
            if len(valid_fg) > 0:
                assert all((valid_fg >= 0) & (valid_fg <= 100))
    
    def test_respects_last_n_parameter(self, mock_nba_api, mock_box_score):
        """get_player_games should respect last_n parameter."""
        games_2 = get_player_games("Coby White", last_n=2)
        games_3 = get_player_games("Coby White", last_n=3)
        
        # Should return at most last_n games (may be less if player didn't play)
        assert len(games_2) <= 2
        assert len(games_3) <= 3
    
    def test_handles_player_not_found(self, mock_nba_api, mock_box_score):
        """get_player_games should handle non-existent player gracefully."""
        # Use a clearly fake player name
        player_games = get_player_games("Fake Player Name XYZ", last_n=5)
        assert isinstance(player_games, pd.DataFrame)
        # Should return empty DataFrame
        assert player_games.empty
    
    def test_result_is_w_or_l(self, mock_nba_api, mock_box_score):
        """Result column should contain 'W' or 'L'."""
        player_games = get_player_games("Coby White", last_n=3)
        
        if not player_games.empty:
            assert all(player_games['result'].isin(['W', 'L']))
    
    def test_stats_are_numeric(self, mock_nba_api, mock_box_score):
        """Stats columns should be numeric."""
        player_games = get_player_games("Coby White", last_n=3)
        
        if not player_games.empty:
            numeric_cols = ['points', 'rebounds', 'assists', 'steals', 'blocks']
            for col in numeric_cols:
                if col in player_games.columns:
                    # Should be numeric (int or float)
                    assert pd.api.types.is_numeric_dtype(player_games[col])


class TestGetPlayerHeadshot:
    """Tests for get_player_headshot function."""
    
    def test_returns_image(self, mock_player_headshot):
        """get_player_headshot should return a PIL Image."""
        # Coby White's player ID: 1629632
        img = get_player_headshot(1629632)
        assert isinstance(img, Image.Image)
    
    def test_returns_correct_size(self, mock_player_headshot):
        """get_player_headshot should return image of specified size."""
        size = (200, 200)
        img = get_player_headshot(1629632, size=size)
        assert img.size == size
    
    def test_handles_failed_request(self, mock_failed_headshot):
        """get_player_headshot should handle failed requests gracefully."""
        # Use a clearly invalid player ID
        img = get_player_headshot(999999999, size=(100, 100))
        assert isinstance(img, Image.Image)
        # Should return placeholder image
        assert img.size == (100, 100)
    
    def test_image_is_rgba(self, mock_player_headshot):
        """get_player_headshot should return RGBA image."""
        img = get_player_headshot(1629632)
        assert img.mode == 'RGBA'
