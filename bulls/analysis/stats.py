"""Statistical analysis functions."""
import pandas as pd
from typing import Optional


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
