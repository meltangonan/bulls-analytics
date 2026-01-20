"""Tests for bulls.analysis module."""
import pytest
import pandas as pd
from bulls.analysis import (
    season_averages,
    vs_average,
    scoring_trend,
    top_performers,
    efficiency_metrics,
    game_efficiency,
    rolling_averages,
    consistency_score,
    points_per_shot,
    high_value_zone_usage,
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
        fake_games = pd.DataFrame({
            'points': [30, 28, 26, 24, 22, 18, 16, 14, 12, 10],
        })

        result = scoring_trend(fake_games)

        assert result['direction'] == 'up'
        assert result['recent_avg'] > result['average']

    def test_detects_downward_trend(self):
        """Should detect downward trend when recent avg < previous avg * 0.9."""
        fake_games = pd.DataFrame({
            'points': [10, 12, 14, 16, 18, 22, 24, 26, 28, 30],
        })

        result = scoring_trend(fake_games)

        assert result['direction'] == 'down'
        assert result['recent_avg'] < result['average']

    def test_detects_stable_trend(self):
        """Should detect stable trend when change is within 10%."""
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


class TestEfficiencyMetrics:
    """Tests for efficiency_metrics function."""

    def test_returns_expected_keys(self, sample_player_games):
        """Should return dict with expected keys."""
        result = efficiency_metrics(sample_player_games)

        assert 'ts_pct' in result
        assert 'efg_pct' in result
        assert 'games' in result

    def test_calculates_ts_pct_correctly(self):
        """Should calculate true shooting % correctly."""
        # 30 pts / (2 * (20 + 0.44 * 4)) = 30 / (2 * 21.76) = 30 / 43.52 = 68.93%
        fake_games = pd.DataFrame({
            'points': [30],
            'fg_attempted': [20],
            'ft_attempted': [4],
            'fg_made': [12],
            'fg3_made': [2],
        })

        result = efficiency_metrics(fake_games)

        expected_ts = 30 / (2 * (20 + 0.44 * 4)) * 100
        assert result['ts_pct'] == pytest.approx(expected_ts, rel=0.01)

    def test_calculates_efg_pct_correctly(self):
        """Should calculate effective FG % correctly."""
        # (12 + 0.5 * 2) / 20 * 100 = 13 / 20 * 100 = 65%
        fake_games = pd.DataFrame({
            'points': [30],
            'fg_attempted': [20],
            'ft_attempted': [4],
            'fg_made': [12],
            'fg3_made': [2],
        })

        result = efficiency_metrics(fake_games)

        expected_efg = (12 + 0.5 * 2) / 20 * 100
        assert result['efg_pct'] == pytest.approx(expected_efg, rel=0.01)

    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = efficiency_metrics(empty_df)
        assert result == {}

    def test_handles_zero_attempts(self):
        """Should handle zero attempts gracefully."""
        fake_games = pd.DataFrame({
            'points': [0],
            'fg_attempted': [0],
            'ft_attempted': [0],
            'fg_made': [0],
            'fg3_made': [0],
        })

        result = efficiency_metrics(fake_games)

        assert result['ts_pct'] == 0.0
        assert result['efg_pct'] == 0.0


class TestGameEfficiency:
    """Tests for game_efficiency function."""

    def test_adds_ts_pct_column(self, sample_player_games):
        """Should add ts_pct column to DataFrame."""
        result = game_efficiency(sample_player_games)
        assert 'ts_pct' in result.columns

    def test_adds_efg_pct_column(self, sample_player_games):
        """Should add efg_pct column to DataFrame."""
        result = game_efficiency(sample_player_games)
        assert 'efg_pct' in result.columns

    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = game_efficiency(empty_df)
        assert result.empty

    def test_per_game_ts_calculation(self):
        """Should calculate per-game TS% correctly."""
        fake_games = pd.DataFrame({
            'points': [20, 30],
            'fg_attempted': [15, 20],
            'ft_attempted': [4, 5],
            'fg_made': [8, 12],
            'fg3_made': [2, 3],
        })

        result = game_efficiency(fake_games)

        # Game 1: 20 / (2 * (15 + 0.44 * 4)) = 20 / 33.52 = 59.7%
        expected_ts_1 = 20 / (2 * (15 + 0.44 * 4)) * 100
        assert result.iloc[0]['ts_pct'] == pytest.approx(expected_ts_1, rel=0.01)

    def test_handles_missing_ft_attempted(self):
        """Should handle missing ft_attempted column."""
        fake_games = pd.DataFrame({
            'points': [20],
            'fg_attempted': [15],
            'fg_made': [8],
            'fg3_made': [2],
        })

        result = game_efficiency(fake_games)

        assert 'ts_pct' in result.columns
        assert 'efg_pct' in result.columns


class TestRollingAverages:
    """Tests for rolling_averages function."""

    def test_adds_rolling_columns(self, sample_player_games):
        """Should add rolling average columns."""
        result = rolling_averages(sample_player_games, metrics=['points'], windows=[3])

        assert 'points_roll_3' in result.columns

    def test_default_metrics_and_windows(self, sample_player_games):
        """Should use default metrics and windows."""
        result = rolling_averages(sample_player_games)

        # Default metrics: points, rebounds, assists
        # Default windows: 3, 5, 10
        assert 'points_roll_3' in result.columns
        assert 'points_roll_5' in result.columns
        assert 'rebounds_roll_3' in result.columns
        assert 'assists_roll_3' in result.columns

    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = rolling_averages(empty_df)
        assert result.empty

    def test_rolling_calculation_correctness(self):
        """Should calculate rolling averages correctly."""
        # Data is most recent first
        fake_games = pd.DataFrame({
            'points': [30, 20, 10],  # Most recent first
        })

        result = rolling_averages(fake_games, metrics=['points'], windows=[2])

        # After reversal (oldest first): [10, 20, 30]
        # Roll 2: [10, 15, 25] (min_periods=1)
        # After re-reversal (most recent first): [25, 15, 10]
        assert result.iloc[0]['points_roll_2'] == 25.0  # avg of 30, 20
        assert result.iloc[1]['points_roll_2'] == 15.0  # avg of 20, 10
        assert result.iloc[2]['points_roll_2'] == 10.0  # just 10

    def test_skips_missing_metric(self):
        """Should skip metrics not in DataFrame."""
        fake_games = pd.DataFrame({
            'points': [20, 25, 30],
        })

        result = rolling_averages(fake_games, metrics=['points', 'nonexistent'], windows=[3])

        assert 'points_roll_3' in result.columns
        assert 'nonexistent_roll_3' not in result.columns


class TestConsistencyScore:
    """Tests for consistency_score function."""

    def test_returns_expected_keys(self, sample_player_games):
        """Should return dict with expected structure."""
        result = consistency_score(sample_player_games)

        assert 'points' in result
        assert 'rebounds' in result
        assert 'assists' in result

        assert 'mean' in result['points']
        assert 'std' in result['points']
        assert 'cv' in result['points']
        assert 'category' in result['points']
        assert 'high' in result['points']
        assert 'low' in result['points']

    def test_categorizes_very_consistent(self):
        """Should categorize CV < 20% as very_consistent."""
        fake_games = pd.DataFrame({
            'points': [20, 21, 20, 19, 20],  # Low variation
        })

        result = consistency_score(fake_games, metrics=['points'])

        assert result['points']['category'] == 'very_consistent'

    def test_categorizes_volatile(self):
        """Should categorize CV > 50% as volatile."""
        fake_games = pd.DataFrame({
            'points': [5, 40, 8, 35, 10],  # High variation
        })

        result = consistency_score(fake_games, metrics=['points'])

        assert result['points']['category'] == 'volatile'

    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = consistency_score(empty_df)
        assert result == {}

    def test_skips_missing_metric(self):
        """Should skip metrics not in DataFrame."""
        fake_games = pd.DataFrame({
            'points': [20, 25, 30],
        })

        result = consistency_score(fake_games, metrics=['points', 'nonexistent'])

        assert 'points' in result
        assert 'nonexistent' not in result

    def test_handles_zero_mean(self):
        """Should handle zero mean gracefully."""
        fake_games = pd.DataFrame({
            'blocks': [0, 0, 0, 0, 0],
        })

        result = consistency_score(fake_games, metrics=['blocks'])

        assert result['blocks']['cv'] == 0.0


class TestPointsPerShot:
    """Tests for points_per_shot function."""

    def test_returns_expected_keys(self):
        """Should return dict with expected keys."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, False, True],
            'shot_type': ['2PT', '3PT', '3PT'],
            'shot_zone': ['Restricted Area', 'Above the Break 3', 'Above the Break 3'],
        })

        result = points_per_shot(fake_shots)

        assert 'pps' in result
        assert 'total_points' in result
        assert 'total_shots' in result
        assert 'fg_pct' in result

    def test_calculates_pps_correctly(self):
        """Should calculate points per shot correctly."""
        # 1 made 2PT (2 pts) + 1 made 3PT (3 pts) + 1 miss (0 pts) = 5 pts / 3 shots = 1.667
        fake_shots = pd.DataFrame({
            'shot_made': [True, True, False],
            'shot_type': ['2PT', '3PT', '2PT'],
        })

        result = points_per_shot(fake_shots)

        assert result['pps'] == pytest.approx(5 / 3, rel=0.01)
        assert result['total_points'] == 5
        assert result['total_shots'] == 3

    def test_calculates_fg_pct_correctly(self):
        """Should calculate field goal percentage correctly."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, True, False, False],
            'shot_type': ['2PT', '3PT', '2PT', '3PT'],
        })

        result = points_per_shot(fake_shots)

        assert result['fg_pct'] == 50.0  # 2/4 = 50%

    def test_by_zone_returns_zone_breakdown(self):
        """Should return zone breakdown when by_zone=True."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, True, False, True],
            'shot_type': ['2PT', '3PT', '3PT', '2PT'],
            'shot_zone': ['Restricted Area', 'Above the Break 3', 'Above the Break 3', 'Mid-Range'],
        })

        result = points_per_shot(fake_shots, by_zone=True)

        assert 'overall' in result
        assert 'by_zone' in result
        assert 'Restricted Area' in result['by_zone']
        assert 'Above the Break 3' in result['by_zone']
        assert 'Mid-Range' in result['by_zone']

    def test_by_zone_calculates_per_zone_pps(self):
        """Should calculate PPS correctly per zone."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, True, False],
            'shot_type': ['2PT', '3PT', '3PT'],
            'shot_zone': ['Restricted Area', 'Above the Break 3', 'Above the Break 3'],
        })

        result = points_per_shot(fake_shots, by_zone=True)

        # Restricted Area: 1 made 2PT = 2 pts / 1 shot = 2.0 PPS
        assert result['by_zone']['Restricted Area']['pps'] == 2.0
        assert result['by_zone']['Restricted Area']['total_points'] == 2
        assert result['by_zone']['Restricted Area']['total_shots'] == 1

        # Above the Break 3: 1 made 3PT + 1 miss = 3 pts / 2 shots = 1.5 PPS
        assert result['by_zone']['Above the Break 3']['pps'] == 1.5
        assert result['by_zone']['Above the Break 3']['total_points'] == 3
        assert result['by_zone']['Above the Break 3']['total_shots'] == 2

    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = points_per_shot(empty_df)
        assert result == {}

    def test_handles_missing_columns(self):
        """Should return empty dict if required columns missing."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, False],
            # Missing 'shot_type'
        })

        result = points_per_shot(fake_shots)
        assert result == {}

    def test_handles_missing_zone_column_with_by_zone(self):
        """Should return empty dict if shot_zone missing when by_zone=True."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, False],
            'shot_type': ['2PT', '3PT'],
            # Missing 'shot_zone'
        })

        result = points_per_shot(fake_shots, by_zone=True)
        assert result == {}

    def test_excludes_backcourt_by_default(self):
        """Should exclude Backcourt zone by default."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, True, False],
            'shot_type': ['2PT', '3PT', '3PT'],
            'shot_zone': ['Restricted Area', 'Above the Break 3', 'Backcourt'],
        })

        result = points_per_shot(fake_shots, by_zone=True)

        # Backcourt should not be in the results
        assert 'Backcourt' not in result['by_zone']
        # Other zones should be present
        assert 'Restricted Area' in result['by_zone']
        assert 'Above the Break 3' in result['by_zone']
        # Overall stats should exclude Backcourt shot
        assert result['overall']['total_shots'] == 2

    def test_includes_backcourt_when_disabled(self):
        """Should include Backcourt zone when exclude_backcourt=False."""
        fake_shots = pd.DataFrame({
            'shot_made': [True, True, True],
            'shot_type': ['2PT', '3PT', '3PT'],
            'shot_zone': ['Restricted Area', 'Above the Break 3', 'Backcourt'],
        })

        result = points_per_shot(fake_shots, by_zone=True, exclude_backcourt=False)

        # Backcourt should be in the results
        assert 'Backcourt' in result['by_zone']
        assert result['by_zone']['Backcourt']['pps'] == 3.0  # Made 3PT = 3 pts / 1 shot
        # Overall stats should include all 3 shots
        assert result['overall']['total_shots'] == 3


class TestHighValueZoneUsage:
    """Tests for high_value_zone_usage function."""

    def test_returns_expected_columns(self):
        """Should return DataFrame with expected columns."""
        fake_shots = pd.DataFrame({
            'team_abbr': ['CHI', 'CHI', 'LAL', 'LAL', 'BOS', 'BOS'],
            'shot_zone': ['Restricted Area', 'Mid-Range', 'Above the Break 3', 'Mid-Range', 'Left Corner 3', 'Restricted Area'],
        })

        result = high_value_zone_usage(fake_shots)

        expected_cols = ['team_abbr', 'high_value_pct', 'restricted_area_pct', 'three_point_pct', 'low_value_pct', 'total_shots', 'rank']
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_calculates_percentages_correctly(self):
        """Should calculate zone usage percentages correctly."""
        # Team with 4 shots: 2 high-value (Restricted Area + Corner 3), 2 low-value (Mid-Range)
        fake_shots = pd.DataFrame({
            'team_abbr': ['CHI', 'CHI', 'CHI', 'CHI'],
            'shot_zone': ['Restricted Area', 'Right Corner 3', 'Mid-Range', 'Mid-Range'],
        })

        result = high_value_zone_usage(fake_shots)

        chi_row = result[result['team_abbr'] == 'CHI'].iloc[0]
        assert chi_row['high_value_pct'] == 50.0  # 2/4 = 50%
        assert chi_row['restricted_area_pct'] == 25.0  # 1/4 = 25%
        assert chi_row['three_point_pct'] == 25.0  # 1/4 = 25%
        assert chi_row['low_value_pct'] == 50.0  # 2/4 = 50%
        assert chi_row['total_shots'] == 4

    def test_ranks_teams_correctly(self):
        """Should rank teams by high-value usage (highest first)."""
        fake_shots = pd.DataFrame({
            'team_abbr': ['CHI', 'CHI', 'LAL', 'LAL', 'LAL', 'LAL', 'BOS', 'BOS', 'BOS', 'BOS'],
            'shot_zone': [
                'Restricted Area', 'Mid-Range',  # CHI: 1 high, 1 low = 50%
                'Restricted Area', 'Above the Break 3', 'Left Corner 3', 'Right Corner 3',  # LAL: 4 high, 0 low = 100%
                'Mid-Range', 'In The Paint (Non-RA)', 'Mid-Range', 'Mid-Range',  # BOS: 0 high, 4 low = 0%
            ],
        })

        result = high_value_zone_usage(fake_shots)

        # LAL should be rank 1 (100%), CHI rank 2 (50%), BOS rank 3 (0%)
        assert result.iloc[0]['team_abbr'] == 'LAL'
        assert result.iloc[0]['rank'] == 1
        assert result.iloc[0]['high_value_pct'] == 100.0

        chi_row = result[result['team_abbr'] == 'CHI'].iloc[0]
        assert chi_row['rank'] == 2

        bos_row = result[result['team_abbr'] == 'BOS'].iloc[0]
        assert bos_row['rank'] == 3
        assert bos_row['high_value_pct'] == 0.0

    def test_handles_empty_dataframe(self):
        """Should return empty DataFrame for empty input."""
        empty_df = pd.DataFrame()
        result = high_value_zone_usage(empty_df)
        assert result.empty

    def test_handles_missing_columns(self):
        """Should return empty DataFrame if required columns missing."""
        fake_shots = pd.DataFrame({
            'shot_zone': ['Restricted Area', 'Mid-Range'],
            # Missing 'team_abbr'
        })

        result = high_value_zone_usage(fake_shots)
        assert result.empty

    def test_custom_high_value_zones(self):
        """Should use custom high-value zones when provided."""
        fake_shots = pd.DataFrame({
            'team_abbr': ['CHI', 'CHI', 'CHI', 'CHI'],
            'shot_zone': ['Restricted Area', 'Mid-Range', 'Mid-Range', 'Mid-Range'],
        })

        # Custom: only Mid-Range is high value
        result = high_value_zone_usage(fake_shots, high_value_zones=['Mid-Range'])

        chi_row = result[result['team_abbr'] == 'CHI'].iloc[0]
        assert chi_row['high_value_pct'] == 75.0  # 3/4 = 75%
        assert chi_row['low_value_pct'] == 25.0  # 1/4 = 25%

    def test_excludes_backcourt_by_default(self):
        """Should exclude Backcourt shots by default."""
        fake_shots = pd.DataFrame({
            'team_abbr': ['CHI', 'CHI', 'CHI'],
            'shot_zone': ['Restricted Area', 'Mid-Range', 'Backcourt'],
        })

        result = high_value_zone_usage(fake_shots)

        chi_row = result[result['team_abbr'] == 'CHI'].iloc[0]
        assert chi_row['total_shots'] == 2  # Backcourt excluded
        assert chi_row['high_value_pct'] == 50.0  # 1 Restricted / 2 total

    def test_includes_backcourt_when_disabled(self):
        """Should include Backcourt when exclude_backcourt=False."""
        fake_shots = pd.DataFrame({
            'team_abbr': ['CHI', 'CHI', 'CHI'],
            'shot_zone': ['Restricted Area', 'Mid-Range', 'Backcourt'],
        })

        result = high_value_zone_usage(fake_shots, exclude_backcourt=False)

        chi_row = result[result['team_abbr'] == 'CHI'].iloc[0]
        assert chi_row['total_shots'] == 3  # Backcourt included
