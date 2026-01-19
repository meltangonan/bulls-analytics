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
    get_player_shots,
)
from bulls.config import BULLS_TEAM_ID, CURRENT_SEASON


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
        games_3 = get_games(last_n=3)
        assert len(games_1) == 1
        assert len(games_3) == 3

    def test_games_sorted_by_date_desc(self, mock_nba_api):
        """Games should be sorted by date, most recent first."""
        games = get_games(last_n=5)
        if len(games) > 1:
            dates = pd.to_datetime(games['GAME_DATE'])
            assert dates.is_monotonic_decreasing

    def test_returns_empty_dataframe_when_no_data(self, mock_empty_api):
        """get_games should return empty DataFrame when no data."""
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

    def test_parses_home_game(self, mock_nba_api):
        """get_latest_game should correctly identify home games."""
        game = get_latest_game()
        # Mock data has 'CHI vs. MIA' as most recent - that's a home game
        assert game['is_home'] is True
        assert game['opponent'] == 'MIA'


class TestGetBoxScore:
    """Tests for get_box_score function."""

    def test_returns_dataframe(self, mock_box_score_api):
        """get_box_score should return a pandas DataFrame."""
        box = get_box_score('0022500503')
        assert isinstance(box, pd.DataFrame)

    def test_returns_expected_columns(self, mock_box_score_api):
        """get_box_score should return expected columns."""
        box = get_box_score('0022500503')

        if not box.empty:
            assert 'name' in box.columns
            assert 'points' in box.columns or 'firstName' in box.columns

    def test_handles_invalid_game_id(self, mock_empty_box_score_api):
        """get_box_score should handle invalid game_id gracefully."""
        box = get_box_score("0000000000")
        assert isinstance(box, pd.DataFrame)

    def test_returns_bulls_players_only(self, mock_box_score_api):
        """get_box_score should only return Bulls players."""
        box = get_box_score('0022500503')

        if not box.empty:
            assert len(box) > 0
            # Verify all returned players have Bulls team ID
            assert all(box['teamId'] == BULLS_TEAM_ID)

    def test_handles_empty_result(self, mock_empty_box_score_api):
        """get_box_score should handle empty results gracefully."""
        box = get_box_score("9999999999")
        assert isinstance(box, pd.DataFrame)
        assert box.empty


class TestGetPlayerGames:
    """Tests for get_player_games function."""

    def test_returns_dataframe(self, mock_nba_api, mock_box_score_api):
        """get_player_games should return a pandas DataFrame."""
        player_games = get_player_games("Coby White", last_n=5)
        assert isinstance(player_games, pd.DataFrame)

    def test_returns_expected_columns(self, mock_nba_api, mock_box_score_api):
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

    def test_respects_last_n_parameter(self, mock_nba_api, mock_box_score_api):
        """get_player_games should respect last_n parameter."""
        player_games = get_player_games("Coby White", last_n=2)
        # Should return at most last_n games
        assert len(player_games) <= 2

    def test_handles_player_not_found(self, mock_nba_api, mock_box_score_api):
        """get_player_games should handle player not found gracefully."""
        player_games = get_player_games("Fake Player Name XYZ", last_n=5)
        assert isinstance(player_games, pd.DataFrame)
        assert player_games.empty

    def test_calculates_percentages(self, mock_nba_api, mock_box_score_api):
        """get_player_games should calculate fg_pct and fg3_pct."""
        player_games = get_player_games("Coby White", last_n=3)

        if not player_games.empty:
            assert 'fg_pct' in player_games.columns
            assert 'fg3_pct' in player_games.columns
            assert pd.api.types.is_numeric_dtype(player_games['fg_pct'])
            assert pd.api.types.is_numeric_dtype(player_games['fg3_pct'])

    def test_handles_case_insensitive_name(self, mock_nba_api, mock_box_score_api):
        """get_player_games should handle case-insensitive player names."""
        player_games_lower = get_player_games("coby white", last_n=2)
        player_games_upper = get_player_games("COBY WHITE", last_n=2)

        assert isinstance(player_games_lower, pd.DataFrame)
        assert isinstance(player_games_upper, pd.DataFrame)
        # Both should find the same player
        assert len(player_games_lower) == len(player_games_upper)


class TestGetPlayerHeadshot:
    """Tests for get_player_headshot function."""

    def test_returns_image(self, mock_headshot_request):
        """get_player_headshot should return a PIL Image."""
        img = get_player_headshot(1629632)
        assert isinstance(img, Image.Image)

    def test_respects_size_parameter(self, mock_headshot_request):
        """get_player_headshot should respect size parameter."""
        img = get_player_headshot(1629632, size=(200, 200))
        assert img.size == (200, 200)

    def test_handles_invalid_player_id(self, mock_headshot_error):
        """get_player_headshot should handle invalid player_id gracefully."""
        img = get_player_headshot(999999999)
        assert isinstance(img, Image.Image)
        # Should return placeholder image (gray)

    def test_returns_rgba_image(self, mock_headshot_request):
        """get_player_headshot should return RGBA image."""
        img = get_player_headshot(1629632)
        assert img.mode == 'RGBA'

    def test_handles_network_errors(self, mock_headshot_error):
        """get_player_headshot should handle network errors gracefully."""
        img = get_player_headshot(0)
        assert isinstance(img, Image.Image)
        # Should return placeholder image
        assert img.size == (300, 300)  # Default size


class TestGetPlayerShots:
    """Tests for get_player_shots function."""

    def test_returns_dataframe(self, mock_shot_chart_api):
        """get_player_shots should return a pandas DataFrame."""
        shots = get_player_shots(1629632)
        assert isinstance(shots, pd.DataFrame)

    def test_returns_expected_columns(self, mock_shot_chart_api):
        """get_player_shots should return expected columns."""
        shots = get_player_shots(1629632)

        if not shots.empty:
            expected_columns = [
                'loc_x', 'loc_y', 'shot_made', 'shot_type',
                'shot_zone', 'shot_distance', 'game_id'
            ]
            for col in expected_columns:
                assert col in shots.columns, f"Missing column: {col}"

    def test_shot_made_is_boolean(self, mock_shot_chart_api):
        """shot_made column should be boolean."""
        shots = get_player_shots(1629632)

        if not shots.empty:
            assert shots['shot_made'].dtype == bool

    def test_shot_type_values(self, mock_shot_chart_api):
        """shot_type should be '2PT' or '3PT'."""
        shots = get_player_shots(1629632)

        if not shots.empty:
            assert all(shots['shot_type'].isin(['2PT', '3PT']))

    def test_handles_empty_result(self, mock_empty_shot_chart_api):
        """get_player_shots should handle empty results gracefully."""
        shots = get_player_shots(1629632)
        assert isinstance(shots, pd.DataFrame)
        assert shots.empty

    def test_respects_team_id_parameter(self, mock_shot_chart_api):
        """get_player_shots should accept team_id parameter."""
        shots = get_player_shots(1629632, team_id=BULLS_TEAM_ID)
        assert isinstance(shots, pd.DataFrame)

    def test_respects_season_parameter(self, mock_shot_chart_api):
        """get_player_shots should accept season parameter."""
        shots = get_player_shots(1629632, season="2025-26")
        assert isinstance(shots, pd.DataFrame)

    def test_respects_last_n_games_parameter(self, mock_shot_chart_api):
        """get_player_shots should accept last_n_games parameter."""
        shots = get_player_shots(1629632, last_n_games=5)
        assert isinstance(shots, pd.DataFrame)
