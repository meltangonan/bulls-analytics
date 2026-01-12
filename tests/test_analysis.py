"""Tests for bulls.analysis module."""
import pytest
import pandas as pd
from bulls.analysis import (
    season_averages,
    vs_average,
    scoring_trend,
    top_performers,
)


class TestSeasonAverages:
    """Tests for season_averages function."""
    
    def test_returns_correct_keys(self):
        """Should return dict with expected stat keys."""
        fake_games = pd.DataFrame({
            'points': [20, 25, 30],
            'rebounds': [5, 6, 7],
            'assists': [3, 4, 5],
            'steals': [1, 2, 1],
            'blocks': [0, 1, 0],
            'fg_pct': [45.0, 50.0, 55.0],
            'fg3_pct': [35.0, 40.0, 45.0],
        })
        
        result = season_averages(fake_games)
        
        assert 'points' in result
        assert 'rebounds' in result
        assert 'assists' in result
        assert 'steals' in result
        assert 'blocks' in result
        assert 'fg_pct' in result
        assert 'fg3_pct' in result
        assert 'games' in result
    
    def test_calculates_correct_average(self):
        """Should calculate correct averages."""
        fake_games = pd.DataFrame({
            'points': [10, 20, 30],
            'rebounds': [5, 5, 5],
            'assists': [3, 3, 3],
            'steals': [1, 1, 1],
            'blocks': [0, 0, 0],
            'fg_pct': [50.0, 50.0, 50.0],
            'fg3_pct': [40.0, 40.0, 40.0],
        })
        
        result = season_averages(fake_games)
        
        assert result['points'] == 20.0
        assert result['rebounds'] == 5.0
        assert result['assists'] == 3.0
        assert result['fg_pct'] == 50.0
        assert result['games'] == 3
    
    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = season_averages(empty_df)
        assert result == {}
    
    def test_calculates_games_count(self):
        """Should correctly count number of games."""
        fake_games = pd.DataFrame({
            'points': [10, 20, 30, 25, 15],
            'rebounds': [5, 5, 5, 5, 5],
            'assists': [3, 3, 3, 3, 3],
            'steals': [1, 1, 1, 1, 1],
            'blocks': [0, 0, 0, 0, 0],
            'fg_pct': [50.0, 50.0, 50.0, 50.0, 50.0],
            'fg3_pct': [40.0, 40.0, 40.0, 40.0, 40.0],
        })
        
        result = season_averages(fake_games)
        assert result['games'] == 5


class TestVsAverage:
    """Tests for vs_average function."""
    
    def test_returns_differences(self):
        """Should return differences between game stats and averages."""
        game_stats = {'points': 28, 'rebounds': 5, 'assists': 7}
        averages = {'points': 20.0, 'rebounds': 5.0, 'assists': 5.0}
        
        result = vs_average(game_stats, averages)
        
        assert result['points'] == 8.0  # 28 - 20
        assert result['rebounds'] == 0.0  # 5 - 5
        assert result['assists'] == 2.0  # 7 - 5
    
    def test_handles_missing_keys(self):
        """Should handle missing keys gracefully."""
        game_stats = {'points': 20}
        averages = {'points': 15.0, 'rebounds': 5.0, 'assists': 3.0}
        
        result = vs_average(game_stats, averages)
        
        assert result['points'] == 5.0
        assert result['rebounds'] == -5.0  # 0 - 5
        assert result['assists'] == -3.0  # 0 - 3
    
    def test_handles_negative_differences(self):
        """Should correctly calculate negative differences."""
        game_stats = {'points': 10, 'rebounds': 3, 'assists': 2}
        averages = {'points': 20.0, 'rebounds': 5.0, 'assists': 5.0}
        
        result = vs_average(game_stats, averages)
        
        assert result['points'] == -10.0
        assert result['rebounds'] == -2.0
        assert result['assists'] == -3.0


class TestScoringTrend:
    """Tests for scoring_trend function."""
    
    def test_returns_expected_keys(self):
        """Should return dict with expected trend keys."""
        fake_games = pd.DataFrame({
            'points': [20, 22, 24, 26, 28, 18, 20, 22, 24, 26],
        })
        
        result = scoring_trend(fake_games)
        
        assert 'direction' in result
        assert 'average' in result
        assert 'recent_avg' in result
        assert 'high' in result
        assert 'low' in result
        assert 'last_game' in result
    
    def test_detects_upward_trend(self):
        """Should detect upward trend when recent avg > previous avg * 1.1."""
        # Recent 5: [28, 26, 24, 22, 20] = 24 avg
        # Previous 5: [18, 20, 22, 24, 26] = 22 avg
        # 24 > 22 * 1.1 = 24.2? No, but let's make it clearer
        # Recent 5: [30, 28, 26, 24, 22] = 26 avg
        # Previous 5: [10, 12, 14, 16, 18] = 14 avg
        # 26 > 14 * 1.1 = 15.4? Yes!
        fake_games = pd.DataFrame({
            'points': [30, 28, 26, 24, 22, 18, 16, 14, 12, 10],
        })
        
        result = scoring_trend(fake_games)
        
        assert result['direction'] == 'up'
        assert result['recent_avg'] > result['average']
    
    def test_detects_downward_trend(self):
        """Should detect downward trend when recent avg < previous avg * 0.9."""
        # Recent 5: [10, 12, 14, 16, 18] = 14 avg
        # Previous 5: [30, 28, 26, 24, 22] = 26 avg
        # 14 < 26 * 0.9 = 23.4? Yes!
        fake_games = pd.DataFrame({
            'points': [10, 12, 14, 16, 18, 22, 24, 26, 28, 30],
        })
        
        result = scoring_trend(fake_games)
        
        assert result['direction'] == 'down'
        assert result['recent_avg'] < result['average']
    
    def test_detects_stable_trend(self):
        """Should detect stable trend when change is within 10%."""
        # All values around 20, so recent and previous should be similar
        fake_games = pd.DataFrame({
            'points': [20, 21, 19, 20, 21, 20, 19, 21, 20, 19],
        })
        
        result = scoring_trend(fake_games)
        
        assert result['direction'] == 'stable'
    
    def test_handles_less_than_5_games(self):
        """Should handle cases with fewer than 5 games."""
        fake_games = pd.DataFrame({
            'points': [20, 22, 24],
        })
        
        result = scoring_trend(fake_games)
        
        assert 'direction' in result
        assert result['average'] == 22.0
        assert result['last_game'] == 20  # First in list (most recent)
    
    def test_handles_less_than_10_games(self):
        """Should handle cases with 5-9 games."""
        fake_games = pd.DataFrame({
            'points': [20, 22, 24, 26, 28, 18, 20],
        })
        
        result = scoring_trend(fake_games)
        
        assert 'direction' in result
        assert result['average'] == pytest.approx(22.57, rel=0.1)
    
    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = scoring_trend(empty_df)
        assert result == {}
    
    def test_handles_missing_metric_column(self):
        """Should handle missing metric column gracefully."""
        fake_games = pd.DataFrame({
            'points': [20, 22, 24],
        })
        
        result = scoring_trend(fake_games, metric='nonexistent')
        assert result == {}
    
    def test_calculates_high_and_low(self):
        """Should correctly identify high and low values."""
        fake_games = pd.DataFrame({
            'points': [10, 15, 20, 25, 30],
        })
        
        result = scoring_trend(fake_games)
        
        assert result['high'] == 30
        assert result['low'] == 10
    
    def test_works_with_different_metrics(self):
        """Should work with metrics other than points."""
        fake_games = pd.DataFrame({
            'assists': [5, 6, 7, 8, 9, 3, 4, 5, 6, 7],
        })
        
        result = scoring_trend(fake_games, metric='assists')
        
        assert 'direction' in result
        assert result['average'] == pytest.approx(6.0, rel=0.1)


class TestTopPerformers:
    """Tests for top_performers function."""
    
    def test_returns_list(self):
        """Should return a list."""
        fake_box = pd.DataFrame({
            'personId': [1, 2, 3],
            'name': ['Player A', 'Player B', 'Player C'],
            'firstName': ['Player', 'Player', 'Player'],
            'familyName': ['A', 'B', 'C'],
            'points': [20, 15, 10],
            'reboundsTotal': [5, 6, 7],
            'assists': [3, 4, 5],
            'steals': [1, 2, 1],
            'blocks': [0, 1, 0],
            'fieldGoalsMade': [8, 6, 4],
            'fieldGoalsAttempted': [15, 12, 10],
        })
        
        result = top_performers(fake_box)
        
        assert isinstance(result, list)
        assert len(result) == 3
    
    def test_sorts_by_points_descending(self):
        """Should sort players by points, highest first."""
        fake_box = pd.DataFrame({
            'personId': [1, 2, 3],
            'name': ['Player A', 'Player B', 'Player C'],
            'firstName': ['Player', 'Player', 'Player'],
            'familyName': ['A', 'B', 'C'],
            'points': [10, 30, 20],
            'reboundsTotal': [5, 5, 5],
            'assists': [3, 3, 3],
            'steals': [1, 1, 1],
            'blocks': [0, 0, 0],
            'fieldGoalsMade': [4, 12, 8],
            'fieldGoalsAttempted': [10, 20, 15],
        })
        
        result = top_performers(fake_box)
        
        assert result[0]['points'] == 30
        assert result[1]['points'] == 20
        assert result[2]['points'] == 10
        assert result[0]['name'] == 'Player B'
    
    def test_sorts_by_assists_when_points_tied(self):
        """Should sort by assists when points are tied."""
        fake_box = pd.DataFrame({
            'personId': [1, 2, 3],
            'name': ['Player A', 'Player B', 'Player C'],
            'firstName': ['Player', 'Player', 'Player'],
            'familyName': ['A', 'B', 'C'],
            'points': [20, 20, 20],
            'reboundsTotal': [5, 5, 5],
            'assists': [3, 5, 4],
            'steals': [1, 1, 1],
            'blocks': [0, 0, 0],
            'fieldGoalsMade': [8, 8, 8],
            'fieldGoalsAttempted': [15, 15, 15],
        })
        
        result = top_performers(fake_box)
        
        assert result[0]['assists'] == 5
        assert result[1]['assists'] == 4
        assert result[2]['assists'] == 3
    
    def test_sorts_by_rebounds_when_points_and_assists_tied(self):
        """Should sort by rebounds when points and assists are tied."""
        fake_box = pd.DataFrame({
            'personId': [1, 2, 3],
            'name': ['Player A', 'Player B', 'Player C'],
            'firstName': ['Player', 'Player', 'Player'],
            'familyName': ['A', 'B', 'C'],
            'points': [20, 20, 20],
            'reboundsTotal': [5, 7, 6],
            'assists': [3, 3, 3],
            'steals': [1, 1, 1],
            'blocks': [0, 0, 0],
            'fieldGoalsMade': [8, 8, 8],
            'fieldGoalsAttempted': [15, 15, 15],
        })
        
        result = top_performers(fake_box)
        
        assert result[0]['rebounds'] == 7
        assert result[1]['rebounds'] == 6
        assert result[2]['rebounds'] == 5
    
    def test_returns_expected_keys(self):
        """Should return dicts with expected keys."""
        fake_box = pd.DataFrame({
            'personId': [1],
            'name': ['Player A'],
            'firstName': ['Player'],
            'familyName': ['A'],
            'points': [20],
            'reboundsTotal': [5],
            'assists': [3],
            'steals': [1],
            'blocks': [0],
            'fieldGoalsMade': [8],
            'fieldGoalsAttempted': [15],
        })
        
        result = top_performers(fake_box)
        
        assert len(result) == 1
        player = result[0]
        
        expected_keys = [
            'player_id', 'name', 'first_name', 'last_name',
            'points', 'rebounds', 'assists', 'steals', 'blocks',
            'fg_made', 'fg_attempted'
        ]
        for key in expected_keys:
            assert key in player, f"Missing key: {key}"
    
    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = top_performers(empty_df)
        assert result == []
    
    def test_handles_missing_columns_gracefully(self):
        """Should handle missing columns with default values."""
        fake_box = pd.DataFrame({
            'personId': [1],
            'name': ['Player A'],
            # Missing some columns
        })
        
        result = top_performers(fake_box)
        
        assert len(result) == 1
        # Should use defaults for missing values
        assert result[0]['points'] == 0
        assert result[0]['rebounds'] == 0
        assert result[0]['assists'] == 0
    
    def test_converts_values_to_integers(self):
        """Should convert stat values to integers."""
        fake_box = pd.DataFrame({
            'personId': [1],
            'name': ['Player A'],
            'firstName': ['Player'],
            'familyName': ['A'],
            'points': [20.5],  # Float value
            'reboundsTotal': [5.7],
            'assists': [3.2],
            'steals': [1.0],
            'blocks': [0.0],
            'fieldGoalsMade': [8],
            'fieldGoalsAttempted': [15],
        })
        
        result = top_performers(fake_box)
        
        assert isinstance(result[0]['points'], int)
        assert isinstance(result[0]['rebounds'], int)
        assert isinstance(result[0]['assists'], int)
