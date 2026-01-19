"""Statistical analysis functions."""
import pandas as pd
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


def zone_leaders(
    team_shots: pd.DataFrame,
    min_shots: int = 5
) -> dict:
    """
    Calculate which player leads in points per game for each shot zone.
    
    Args:
        team_shots: DataFrame from get_team_shots() with shot data
        min_shots: Minimum number of shots required in a zone to qualify (default: 5)
    
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
