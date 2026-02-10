"""Tests for bulls.data module."""
import pytest
import pandas as pd
from bulls.data import (
    get_games,
    get_latest_game,
    get_box_score,
    get_player_games,
    get_player_shots,
    get_roster_efficiency,
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

    def test_handles_empty_result(self, mock_empty_shot_chart_api):
        """get_player_shots should handle empty results gracefully."""
        shots = get_player_shots(1629632)
        assert isinstance(shots, pd.DataFrame)
        assert shots.empty

    def test_respects_last_n_games_parameter(self, mock_shot_chart_api):
        """get_player_shots should accept last_n_games parameter."""
        shots = get_player_shots(1629632, last_n_games=5)
        assert isinstance(shots, pd.DataFrame)


class TestGetRosterEfficiency:
    """Tests for get_roster_efficiency function."""

    def test_returns_list(self, mock_roster_efficiency_api):
        """get_roster_efficiency should return a list."""
        result = get_roster_efficiency(last_n_games=5)
        assert isinstance(result, list)

    def test_returns_expected_keys(self, mock_roster_efficiency_api):
        """get_roster_efficiency should return dicts with expected keys."""
        result = get_roster_efficiency(last_n_games=5)

        if result:
            expected_keys = ['player_id', 'name', 'ts_pct', 'fga_per_game', 'games']
            for player in result:
                for key in expected_keys:
                    assert key in player, f"Missing key: {key}"

    def test_filters_by_min_fga(self, mock_roster_efficiency_api):
        """get_roster_efficiency should filter players by min_fga."""
        # With high min_fga threshold, should filter out low-volume players
        result = get_roster_efficiency(last_n_games=5, min_fga=100.0)
        assert isinstance(result, list)
        # May be empty if no players meet threshold

    def test_handles_empty_shots(self, mock_empty_shot_chart_api):
        """get_roster_efficiency should handle empty shot data gracefully."""
        result = get_roster_efficiency(last_n_games=5)
        assert isinstance(result, list)
        assert result == []

    def test_sorted_by_volume(self, mock_roster_efficiency_api):
        """get_roster_efficiency should return players sorted by FGA desc."""
        result = get_roster_efficiency(last_n_games=5, min_fga=0.0)

        if len(result) > 1:
            fga_values = [p['fga_per_game'] for p in result]
            assert fga_values == sorted(fga_values, reverse=True)

    def test_calculates_ts_pct(self, mock_roster_efficiency_api):
        """get_roster_efficiency should calculate TS% for players."""
        result = get_roster_efficiency(last_n_games=5, min_fga=0.0)

        if result:
            for player in result:
                assert 'ts_pct' in player
                assert isinstance(player['ts_pct'], (int, float))
                # TS% should be reasonable (0-100 range)
                assert 0 <= player['ts_pct'] <= 100
