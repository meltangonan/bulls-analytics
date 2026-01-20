"""Statistical analysis functions."""
import pandas as pd
import numpy as np
from typing import Optional, List


def season_averages(player_games: pd.DataFrame) -> dict:
    """
    Calculate a player's averages from their game log.
    
    Args:
        player_games: DataFrame from get_player_games()
    
    Returns:
        Dict with average stats (points, rebounds, assists, fg_pct, etc.)
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=20)
        >>> avgs = season_averages(coby)
        >>> print(f"Coby averages {avgs['points']:.1f} PPG")
    """
    if player_games.empty:
        return {}
    
    return {
        'games': len(player_games),
        'points': player_games['points'].mean(),
        'rebounds': player_games['rebounds'].mean(),
        'assists': player_games['assists'].mean(),
        'steals': player_games['steals'].mean(),
        'blocks': player_games['blocks'].mean(),
        'fg_pct': player_games['fg_pct'].mean(),
        'fg3_pct': player_games['fg3_pct'].mean(),
    }


def vs_average(
    game_stats: dict,
    averages: dict
) -> dict:
    """
    Compare a single game to season averages.
    
    Args:
        game_stats: Dict with game stats (points, rebounds, etc.)
        averages: Dict from season_averages()
    
    Returns:
        Dict with differences (positive = above average)
    
    Example:
        >>> avgs = season_averages(coby_games)
        >>> last_game = {'points': 28, 'rebounds': 5, 'assists': 7}
        >>> diff = vs_average(last_game, avgs)
        >>> print(f"Points vs avg: {diff['points']:+.1f}")
    """
    return {
        'points': game_stats.get('points', 0) - averages.get('points', 0),
        'rebounds': game_stats.get('rebounds', 0) - averages.get('rebounds', 0),
        'assists': game_stats.get('assists', 0) - averages.get('assists', 0),
    }


def scoring_trend(
    player_games: pd.DataFrame,
    metric: str = 'points'
) -> dict:
    """
    Analyze scoring trend over recent games.
    
    Args:
        player_games: DataFrame from get_player_games()
        metric: Which stat to analyze ('points', 'assists', etc.)
    
    Returns:
        Dict with trend info (direction, streak, high, low)
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=10)
        >>> trend = scoring_trend(coby)
        >>> print(f"Trending: {trend['direction']}")
    """
    if player_games.empty or metric not in player_games.columns:
        return {}
    
    values = player_games[metric].tolist()
    avg = sum(values) / len(values)
    
    # Recent trend (last 5 vs previous 5)
    recent = values[:5] if len(values) >= 5 else values
    previous = values[5:10] if len(values) >= 10 else values[len(recent):]
    
    recent_avg = sum(recent) / len(recent) if recent else 0
    previous_avg = sum(previous) / len(previous) if previous else recent_avg
    
    if recent_avg > previous_avg * 1.1:
        direction = "up"
    elif recent_avg < previous_avg * 0.9:
        direction = "down"
    else:
        direction = "stable"
    
    return {
        'direction': direction,
        'average': avg,
        'recent_avg': recent_avg,
        'high': max(values),
        'low': min(values),
        'last_game': values[0] if values else 0,
    }


def top_performers(box_score: pd.DataFrame) -> list:
    """
    Rank players by performance in a game.
    
    Args:
        box_score: DataFrame from get_box_score()
    
    Returns:
        List of dicts with player info, sorted by points (desc)
    
    Example:
        >>> box = get_box_score(game_id)
        >>> top = top_performers(box)
        >>> print(f"Top scorer: {top[0]['name']} with {top[0]['points']} pts")
    """
    if box_score.empty:
        return []
    
    performers = []
    
    for _, row in box_score.iterrows():
        performers.append({
            'player_id': row.get('personId', 0),
            'name': row.get('name', 'Unknown'),
            'first_name': row.get('firstName', ''),
            'last_name': row.get('familyName', ''),
            'points': int(row.get('points', 0) or 0),
            'rebounds': int(row.get('reboundsTotal', 0) or 0),
            'assists': int(row.get('assists', 0) or 0),
            'steals': int(row.get('steals', 0) or 0),
            'blocks': int(row.get('blocks', 0) or 0),
            'fg_made': int(row.get('fieldGoalsMade', 0) or 0),
            'fg_attempted': int(row.get('fieldGoalsAttempted', 0) or 0),
        })
    
    # Sort by points, then assists, then rebounds
    performers.sort(key=lambda x: (x['points'], x['assists'], x['rebounds']), reverse=True)

    return performers


def efficiency_metrics(player_games: pd.DataFrame) -> dict:
    """
    Calculate advanced efficiency metrics for a player.

    Args:
        player_games: DataFrame from get_player_games()

    Returns:
        Dict with efficiency metrics:
        - ts_pct: True Shooting % (accounts for FTs and 3s)
        - efg_pct: Effective FG % (weights 3-pointers)
        - games: Number of games analyzed

    Example:
        >>> coby = get_player_games("Coby White", last_n=20)
        >>> eff = efficiency_metrics(coby)
        >>> print(f"TS%: {eff['ts_pct']:.1f}%")
    """
    if player_games.empty:
        return {}

    total_pts = player_games['points'].sum()
    total_fga = player_games['fg_attempted'].sum()
    total_fta = player_games.get('ft_attempted', pd.Series([0])).sum()
    total_fgm = player_games['fg_made'].sum()
    total_fg3m = player_games['fg3_made'].sum()

    # True Shooting %: pts / (2 * (fga + 0.44 * fta)) * 100
    tsa = total_fga + 0.44 * total_fta
    ts_pct = (total_pts / (2 * tsa) * 100) if tsa > 0 else 0.0

    # Effective FG %: (fgm + 0.5 * fg3m) / fga * 100
    efg_pct = ((total_fgm + 0.5 * total_fg3m) / total_fga * 100) if total_fga > 0 else 0.0

    return {
        'ts_pct': round(ts_pct, 1),
        'efg_pct': round(efg_pct, 1),
        'games': len(player_games),
    }


def game_efficiency(player_games: pd.DataFrame) -> pd.DataFrame:
    """
    Add per-game efficiency columns to player games DataFrame.

    Args:
        player_games: DataFrame from get_player_games()

    Returns:
        DataFrame with added columns:
        - ts_pct: Per-game True Shooting %
        - efg_pct: Per-game Effective FG %

    Example:
        >>> coby = get_player_games("Coby White", last_n=10)
        >>> coby_eff = game_efficiency(coby)
        >>> coby_eff[['date', 'points', 'ts_pct', 'efg_pct']]
    """
    if player_games.empty:
        return player_games.copy()

    df = player_games.copy()

    # Get FT attempted, default to 0 if column doesn't exist
    fta = df['ft_attempted'] if 'ft_attempted' in df.columns else 0

    # True Shooting %: pts / (2 * (fga + 0.44 * fta)) * 100
    tsa = df['fg_attempted'] + 0.44 * fta
    df['ts_pct'] = (df['points'] / (2 * tsa.replace(0, 1)) * 100).round(1)

    # Effective FG %: (fgm + 0.5 * fg3m) / fga * 100
    df['efg_pct'] = ((df['fg_made'] + 0.5 * df['fg3_made']) / df['fg_attempted'].replace(0, 1) * 100).round(1)

    return df


def rolling_averages(
    player_games: pd.DataFrame,
    metrics: Optional[List[str]] = None,
    windows: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Calculate rolling averages for specified metrics.

    Args:
        player_games: DataFrame from get_player_games()
        metrics: List of column names to calculate rolling averages for
                 (default: ['points', 'rebounds', 'assists'])
        windows: List of window sizes (default: [3, 5, 10])

    Returns:
        DataFrame with added rolling average columns.
        Column naming: {metric}_roll_{window}

    Example:
        >>> coby = get_player_games("Coby White", last_n=15)
        >>> coby_roll = rolling_averages(coby, metrics=['points'], windows=[3, 5])
        >>> coby_roll[['date', 'points', 'points_roll_3', 'points_roll_5']]
    """
    if player_games.empty:
        return player_games.copy()

    if metrics is None:
        metrics = ['points', 'rebounds', 'assists']
    if windows is None:
        windows = [3, 5, 10]

    df = player_games.copy()

    # Data is most recent first, so we reverse for rolling calculation
    # then reverse back to maintain original order
    df_reversed = df.iloc[::-1].copy()

    for metric in metrics:
        if metric not in df.columns:
            continue
        for window in windows:
            col_name = f'{metric}_roll_{window}'
            df_reversed[col_name] = df_reversed[metric].rolling(window=window, min_periods=1).mean().round(1)

    # Reverse back to original order (most recent first)
    result = df_reversed.iloc[::-1].reset_index(drop=True)

    return result


def consistency_score(
    player_games: pd.DataFrame,
    metrics: Optional[List[str]] = None,
) -> dict:
    """
    Analyze a player's consistency across metrics.

    Uses coefficient of variation (CV = std/mean) to categorize consistency:
    - very_consistent: CV < 20%
    - consistent: CV 20-35%
    - moderate: CV 35-50%
    - volatile: CV > 50%

    Args:
        player_games: DataFrame from get_player_games()
        metrics: List of metrics to analyze
                 (default: ['points', 'rebounds', 'assists'])

    Returns:
        Dict with consistency analysis for each metric:
        - mean: Average value
        - std: Standard deviation
        - cv: Coefficient of variation (%)
        - category: Consistency category
        - high: Maximum value
        - low: Minimum value

    Example:
        >>> coby = get_player_games("Coby White", last_n=20)
        >>> cons = consistency_score(coby)
        >>> print(f"Scoring consistency: {cons['points']['category']}")
    """
    if player_games.empty:
        return {}

    if metrics is None:
        metrics = ['points', 'rebounds', 'assists']

    result = {}

    for metric in metrics:
        if metric not in player_games.columns:
            continue

        values = player_games[metric]
        mean_val = values.mean()
        std_val = values.std()

        # Coefficient of variation (as percentage)
        cv = (std_val / mean_val * 100) if mean_val > 0 else 0.0

        # Categorize consistency
        if cv < 20:
            category = 'very_consistent'
        elif cv < 35:
            category = 'consistent'
        elif cv < 50:
            category = 'moderate'
        else:
            category = 'volatile'

        result[metric] = {
            'mean': round(mean_val, 1),
            'std': round(std_val, 1),
            'cv': round(cv, 1),
            'category': category,
            'high': int(values.max()),
            'low': int(values.min()),
        }

    return result


def points_per_shot(
    team_shots: pd.DataFrame,
    by_zone: bool = False,
    exclude_backcourt: bool = True
) -> dict:
    """
    Calculate points per shot (PPS) - average point value per shot taken.

    Args:
        team_shots: DataFrame from get_team_shots() with shot data
        by_zone: If True, include breakdown by shot zone
        exclude_backcourt: If True (default), exclude Backcourt shots from calculations

    Returns:
        Dict with PPS stats. If by_zone=False:
        {
            'pps': float,
            'total_points': int,
            'total_shots': int,
            'fg_pct': float
        }

        If by_zone=True, adds 'by_zone' dict with same structure per zone.

    Example:
        >>> shots = data.get_team_shots()
        >>> pps = points_per_shot(shots)
        >>> print(f"Season PPS: {pps['pps']:.3f}")
        >>>
        >>> pps_zones = points_per_shot(shots, by_zone=True)
        >>> for zone, stats in pps_zones['by_zone'].items():
        ...     print(f"{zone}: {stats['pps']:.3f}")
    """
    if team_shots.empty:
        return {}

    # Check required columns
    required_cols = ['shot_made', 'shot_type']
    if by_zone:
        required_cols.append('shot_zone')
    missing_cols = [col for col in required_cols if col not in team_shots.columns]
    if missing_cols:
        return {}

    # Filter out Backcourt shots if requested
    shots_data = team_shots.copy()
    if exclude_backcourt and 'shot_zone' in shots_data.columns:
        shots_data = shots_data[shots_data['shot_zone'] != 'Backcourt']

    def calc_stats(shots_df: pd.DataFrame) -> dict:
        """Calculate PPS stats for a group of shots."""
        total_shots = len(shots_df)
        if total_shots == 0:
            return {'pps': 0.0, 'total_points': 0, 'total_shots': 0, 'fg_pct': 0.0}

        # Calculate points: 3 for made 3PT, 2 for made 2PT, 0 for misses
        points = shots_df.apply(
            lambda row: 3 if row['shot_made'] and row['shot_type'] == '3PT'
                       else 2 if row['shot_made'] else 0,
            axis=1
        ).sum()

        made_shots = shots_df['shot_made'].sum()
        fg_pct = (made_shots / total_shots) * 100

        return {
            'pps': round(points / total_shots, 3),
            'total_points': int(points),
            'total_shots': total_shots,
            'fg_pct': round(fg_pct, 1)
        }

    # Calculate overall stats
    overall = calc_stats(shots_data)

    if not by_zone:
        return overall

    # Calculate per-zone stats
    zone_stats = {}
    for zone in shots_data['shot_zone'].dropna().unique():
        zone_shots = shots_data[shots_data['shot_zone'] == zone]
        zone_stats[zone] = calc_stats(zone_shots)

    return {
        'overall': overall,
        'by_zone': zone_stats
    }


def zone_leaders(
    team_shots: pd.DataFrame,
    min_shots: int = 5,
    exclude_backcourt: bool = True
) -> dict:
    """
    Calculate which player leads in points per game for each shot zone.

    Args:
        team_shots: DataFrame from get_team_shots() with shot data
        min_shots: Minimum number of shots required in a zone to qualify (default: 5)
        exclude_backcourt: If True (default), exclude Backcourt shots from calculations

    Returns:
        Dict mapping zone names to leader info:
        {
            'zone_name': {
                'player_id': int,
                'player_name': str,
                'ppg': float,
                'total_points': int,
                'total_shots': int,
                'games': int
            }
        }

    Example:
        >>> shots = data.get_team_shots()
        >>> leaders = zone_leaders(shots, min_shots=5)
        >>> print(f"Left Corner 3 leader: {leaders['Left Corner 3']['player_name']}")
    """
    if team_shots.empty:
        return {}

    # Check required columns
    required_cols = ['player_id', 'player_name', 'shot_zone', 'shot_made', 'shot_type', 'game_id']
    missing_cols = [col for col in required_cols if col not in team_shots.columns]
    if missing_cols:
        print(f"Warning: Missing required columns: {missing_cols}")
        return {}

    # Filter out Backcourt shots if requested
    if exclude_backcourt:
        team_shots = team_shots[team_shots['shot_zone'] != 'Backcourt']
    
    # Calculate points per shot (2 for 2PT made, 3 for 3PT made, 0 for misses)
    def calculate_points(row):
        if row['shot_made']:
            return 3 if row['shot_type'] == '3PT' else 2
        return 0
    
    team_shots = team_shots.copy()
    team_shots['points'] = team_shots.apply(calculate_points, axis=1)
    
    # Group by player, zone, and game to get points per game
    # Then aggregate to get total points and unique games
    player_zone_stats = []
    
    for (player_id, player_name, zone), group in team_shots.groupby(['player_id', 'player_name', 'shot_zone']):
        if pd.isna(player_id) or pd.isna(zone):
            continue
        
        total_shots = len(group)
        if total_shots < min_shots:
            continue
        
        total_points = group['points'].sum()
        unique_games = group['game_id'].nunique()
        
        if unique_games == 0:
            continue
        
        ppg = total_points / unique_games
        
        player_zone_stats.append({
            'player_id': int(player_id),
            'player_name': str(player_name),
            'zone': str(zone),
            'ppg': ppg,
            'total_points': int(total_points),
            'total_shots': total_shots,
            'games': unique_games
        })
    
    if not player_zone_stats:
        return {}
    
    # Convert to DataFrame for easier processing
    stats_df = pd.DataFrame(player_zone_stats)
    
    # Find leader for each zone (highest PPG)
    leaders = {}
    for zone in stats_df['zone'].unique():
        zone_stats = stats_df[stats_df['zone'] == zone]
        leader = zone_stats.loc[zone_stats['ppg'].idxmax()]
        
        leaders[zone] = {
            'player_id': leader['player_id'],
            'player_name': leader['player_name'],
            'ppg': round(leader['ppg'], 2),
            'total_points': leader['total_points'],
            'total_shots': leader['total_shots'],
            'games': leader['games']
        }

    return leaders


def league_pps_by_zone(
    league_shots: pd.DataFrame,
    exclude_backcourt: bool = True
) -> dict:
    """
    Calculate league-wide points per shot by zone across all teams.

    Args:
        league_shots: DataFrame from get_league_shots() with shot data for all teams
        exclude_backcourt: If True (default), exclude Backcourt shots from calculations

    Returns:
        Dict with league-wide PPS analysis:
        {
            'league_overall': {'pps': float, 'total_points': int, 'total_shots': int, 'fg_pct': float},
            'by_zone': {
                'zone_name': {
                    'pps': float, 'total_points': int, 'total_shots': int, 'fg_pct': float,
                    'rank': int, 'pct_of_shots': float
                }
            },
            'by_team': {
                'team_abbr': {
                    'overall': {...},
                    'by_zone': {...}
                }
            }
        }

    Example:
        >>> league_shots = data.get_league_shots(season="2024-25")
        >>> league_pps = league_pps_by_zone(league_shots)
        >>> print(f"League PPS: {league_pps['league_overall']['pps']:.3f}")
    """
    if league_shots.empty:
        return {}

    required_cols = ['shot_made', 'shot_type', 'shot_zone']
    missing_cols = [col for col in required_cols if col not in league_shots.columns]
    if missing_cols:
        return {}

    # Filter out Backcourt shots if requested
    if exclude_backcourt:
        league_shots = league_shots[league_shots['shot_zone'] != 'Backcourt']

    def calc_stats(shots_df: pd.DataFrame) -> dict:
        """Calculate PPS stats for a group of shots."""
        total_shots = len(shots_df)
        if total_shots == 0:
            return {'pps': 0.0, 'total_points': 0, 'total_shots': 0, 'fg_pct': 0.0}

        points = shots_df.apply(
            lambda row: 3 if row['shot_made'] and row['shot_type'] == '3PT'
                       else 2 if row['shot_made'] else 0,
            axis=1
        ).sum()

        made_shots = shots_df['shot_made'].sum()
        fg_pct = (made_shots / total_shots) * 100

        return {
            'pps': round(points / total_shots, 3),
            'total_points': int(points),
            'total_shots': total_shots,
            'fg_pct': round(fg_pct, 1)
        }

    # Calculate league-wide overall stats
    league_overall = calc_stats(league_shots)

    # Calculate league-wide by zone
    zone_stats = {}
    total_league_shots = len(league_shots)

    for zone in league_shots['shot_zone'].dropna().unique():
        zone_shots = league_shots[league_shots['shot_zone'] == zone]
        stats = calc_stats(zone_shots)
        stats['pct_of_shots'] = round(len(zone_shots) / total_league_shots * 100, 1)
        zone_stats[zone] = stats

    # Rank zones by PPS
    sorted_zones = sorted(zone_stats.items(), key=lambda x: x[1]['pps'], reverse=True)
    for rank, (zone, _) in enumerate(sorted_zones, 1):
        zone_stats[zone]['rank'] = rank

    # Calculate per-team stats
    team_stats = {}
    if 'team_abbr' in league_shots.columns:
        for team_abbr in league_shots['team_abbr'].dropna().unique():
            team_shots = league_shots[league_shots['team_abbr'] == team_abbr]
            team_overall = calc_stats(team_shots)

            team_zones = {}
            for zone in team_shots['shot_zone'].dropna().unique():
                zone_shots = team_shots[team_shots['shot_zone'] == zone]
                team_zones[zone] = calc_stats(zone_shots)

            team_stats[team_abbr] = {
                'overall': team_overall,
                'by_zone': team_zones
            }

    return {
        'league_overall': league_overall,
        'by_zone': zone_stats,
        'by_team': team_stats
    }


def high_value_zone_usage(
    league_shots: pd.DataFrame,
    high_value_zones: Optional[List[str]] = None,
    exclude_backcourt: bool = True
) -> pd.DataFrame:
    """
    Calculate % of shots from high-value zones for each team.

    High-value zones are areas with the best expected point value per shot,
    based on league-wide PPS data. By default, these are:
    - Restricted Area (highest PPS at ~1.33)
    - All 3-point zones (Corner 3s and Above the Break 3)

    Args:
        league_shots: DataFrame from get_league_shots() with shot data for all teams
        high_value_zones: List of zone names to consider "high value"
                         (default: Restricted Area + all 3-point zones)
        exclude_backcourt: If True (default), exclude Backcourt shots from calculations

    Returns:
        DataFrame sorted by high-value usage % (best first):
        - team_abbr: Team abbreviation
        - high_value_pct: % of shots from high-value zones
        - restricted_area_pct: % from Restricted Area
        - three_point_pct: % from all 3-point zones combined
        - low_value_pct: % from low-value zones (Mid-Range + Paint Non-RA)
        - total_shots: Total shots taken
        - rank: Ranking (1 = highest high-value usage)

    Example:
        >>> league_shots = data.get_league_shots(season="2024-25")
        >>> usage = high_value_zone_usage(league_shots)
        >>> print(usage.head())
        >>> # Find Bulls ranking
        >>> bulls_rank = usage[usage['team_abbr'] == 'CHI']['rank'].values[0]
    """
    if league_shots.empty:
        return pd.DataFrame()

    required_cols = ['shot_zone', 'team_abbr']
    missing_cols = [col for col in required_cols if col not in league_shots.columns]
    if missing_cols:
        return pd.DataFrame()

    # Filter out Backcourt shots if requested
    shots_data = league_shots.copy()
    if exclude_backcourt:
        shots_data = shots_data[shots_data['shot_zone'] != 'Backcourt']

    # Default high-value zones: Restricted Area + all 3-point zones
    if high_value_zones is None:
        high_value_zones = [
            'Restricted Area',
            'Right Corner 3',
            'Left Corner 3',
            'Above the Break 3',
        ]

    # Define 3-point zones for separate tracking
    three_point_zones = ['Right Corner 3', 'Left Corner 3', 'Above the Break 3']

    # Calculate per-team stats
    team_stats = []
    for team_abbr in shots_data['team_abbr'].dropna().unique():
        team_shots = shots_data[shots_data['team_abbr'] == team_abbr]
        total_shots = len(team_shots)

        if total_shots == 0:
            continue

        # Calculate zone usage percentages
        high_value_shots = team_shots[team_shots['shot_zone'].isin(high_value_zones)]
        restricted_area_shots = team_shots[team_shots['shot_zone'] == 'Restricted Area']
        three_point_shots = team_shots[team_shots['shot_zone'].isin(three_point_zones)]

        # Low-value zones: everything not high-value (Mid-Range, In The Paint Non-RA)
        low_value_shots = team_shots[~team_shots['shot_zone'].isin(high_value_zones)]

        team_stats.append({
            'team_abbr': team_abbr,
            'high_value_pct': round(len(high_value_shots) / total_shots * 100, 1),
            'restricted_area_pct': round(len(restricted_area_shots) / total_shots * 100, 1),
            'three_point_pct': round(len(three_point_shots) / total_shots * 100, 1),
            'low_value_pct': round(len(low_value_shots) / total_shots * 100, 1),
            'total_shots': total_shots,
        })

    if not team_stats:
        return pd.DataFrame()

    # Create DataFrame and rank by high-value usage
    df = pd.DataFrame(team_stats)
    df = df.sort_values('high_value_pct', ascending=False).reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)

    return df


def zone_value_ranking(
    league_pps: dict,
    exclude_backcourt: bool = True
) -> pd.DataFrame:
    """
    Create a ranked DataFrame of shot zones by value (PPS).

    Args:
        league_pps: Dict from league_pps_by_zone()
        exclude_backcourt: If True (default), exclude Backcourt zone from rankings

    Returns:
        DataFrame with zones ranked by PPS, including volume and efficiency metrics.

    Example:
        >>> league_pps = league_pps_by_zone(league_shots)
        >>> rankings = zone_value_ranking(league_pps)
        >>> print(rankings)
    """
    if not league_pps or 'by_zone' not in league_pps:
        return pd.DataFrame()

    zones = []
    for zone, stats in league_pps['by_zone'].items():
        if exclude_backcourt and zone == 'Backcourt':
            continue
        zones.append({
            'Zone': zone,
            'PPS': stats['pps'],
            'FG%': stats['fg_pct'],
            'Points': stats['total_points'],
            'Shots': stats['total_shots'],
            'Volume%': stats['pct_of_shots'],
            'Rank': stats['rank']
        })

    df = pd.DataFrame(zones).sort_values('Rank')
    return df.reset_index(drop=True)


def team_zone_comparison(league_pps: dict, zones: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Create a DataFrame comparing team PPS across zones.

    Args:
        league_pps: Dict from league_pps_by_zone()
        zones: List of zones to include (default: all zones)

    Returns:
        DataFrame with teams as rows and zones as columns, values are PPS.

    Example:
        >>> league_pps = league_pps_by_zone(league_shots)
        >>> comparison = team_zone_comparison(league_pps)
        >>> print(comparison.head())
    """
    if not league_pps or 'by_team' not in league_pps:
        return pd.DataFrame()

    if zones is None:
        zones = list(league_pps['by_zone'].keys())

    rows = []
    for team_abbr, team_data in league_pps['by_team'].items():
        row = {'Team': team_abbr, 'Overall': team_data['overall']['pps']}
        for zone in zones:
            if zone in team_data['by_zone']:
                row[zone] = team_data['by_zone'][zone]['pps']
            else:
                row[zone] = np.nan
        rows.append(row)

    df = pd.DataFrame(rows).sort_values('Overall', ascending=False)
    return df.reset_index(drop=True)
