"""Fetch Bulls data from NBA API."""
import time
import requests
from io import BytesIO
from typing import Optional
import pandas as pd
from PIL import Image

from nba_api.stats.endpoints import (
    leaguegamefinder,
    boxscoretraditionalv3,
)

from bulls.config import (
    BULLS_TEAM_ID,
    CURRENT_SEASON,
    API_DELAY,
    NBA_HEADSHOT_URL,
)


def get_games(
    last_n: Optional[int] = None,
    season: str = CURRENT_SEASON
) -> pd.DataFrame:
    """
    Get Bulls games for a season.
    
    Args:
        last_n: Return only the last N games (most recent first)
        season: NBA season string (default: current season)
    
    Returns:
        DataFrame with game info (date, opponent, score, result, etc.)
    
    Example:
        >>> games = get_games(last_n=10)
        >>> games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']]
    """
    finder = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=BULLS_TEAM_ID,
        season_nullable=season,
        season_type_nullable='Regular Season'
    )
    data_frames = finder.get_data_frames()
    
    if not data_frames or len(data_frames) == 0:
        return pd.DataFrame()  # Return empty DataFrame if no data
    
    games = data_frames[0]
    
    if games.empty:
        return pd.DataFrame()
    
    games = games.sort_values('GAME_DATE', ascending=False)
    
    if last_n:
        games = games.head(last_n)
    
    return games


def get_latest_game() -> dict:
    """
    Get the most recent Bulls game.
    
    Returns:
        Dict with game info including:
        - game_id, date, matchup, result (W/L)
        - bulls_score, opponent_score
        - opponent name
    
    Example:
        >>> game = get_latest_game()
        >>> print(f"{game['matchup']} - {game['result']}")
    """
    games = get_games(last_n=1)
    
    if games.empty:
        raise ValueError("No games found for the current season")
    
    row = games.iloc[0]
    
    matchup = row['MATCHUP']
    is_home = 'vs.' in matchup
    
    if is_home:
        opponent = matchup.split('vs.')[-1].strip()
    else:
        opponent = matchup.split('@')[-1].strip()
    
    return {
        'game_id': row['GAME_ID'],
        'date': row['GAME_DATE'],
        'matchup': matchup,
        'is_home': is_home,
        'result': row['WL'],
        'bulls_score': int(row['PTS']),
        'opponent': opponent,
        'plus_minus': int(row['PLUS_MINUS']),
    }


def get_box_score(game_id: str) -> pd.DataFrame:
    """
    Get box score for a specific game.
    
    Args:
        game_id: NBA game ID (e.g., "0022500503")
    
    Returns:
        DataFrame with player stats for Bulls players only.
        Columns include: player name, points, rebounds, assists, etc.
    
    Example:
        >>> game = get_latest_game()
        >>> box = get_box_score(game['game_id'])
        >>> box[['firstName', 'familyName', 'points', 'rebounds', 'assists']]
    """
    time.sleep(API_DELAY)
    
    try:
        box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
        players = box.player_stats.get_data_frame()
        
        if players.empty:
            return pd.DataFrame()
        
        # Filter to Bulls players only
        bulls_players = players[players['teamId'] == BULLS_TEAM_ID].copy()
        
        if bulls_players.empty:
            return pd.DataFrame()
        
        # Add full name column for convenience
        bulls_players['name'] = bulls_players['firstName'] + ' ' + bulls_players['familyName']
        
        return bulls_players
    except (AttributeError, KeyError, IndexError, requests.RequestException) as e:
        print(f"Error fetching box score for game {game_id}: {e}")
        return pd.DataFrame()


def get_player_games(
    player_name: str,
    last_n: int = 20,
    season: str = CURRENT_SEASON
) -> pd.DataFrame:
    """
    Get a player's game-by-game stats.
    
    Args:
        player_name: Player's name (e.g., "Coby White")
        last_n: Number of recent games
        season: NBA season
    
    Returns:
        DataFrame with the player's stats for each game.
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=10)
        >>> coby[['date', 'points', 'assists', 'fg_pct']]
    """
    games = get_games(last_n=last_n * 2, season=season)  # Fetch extra to account for DNPs
    
    player_stats = []
    
    for _, game in games.iterrows():
        time.sleep(API_DELAY)
        
        try:
            box = get_box_score(game['GAME_ID'])
            
            if box.empty:
                continue
            
            # Find player in box score (case-insensitive match)
            player_row = box[box['name'].str.lower() == player_name.lower()]
            
            if not player_row.empty:
                p = player_row.iloc[0]
                player_stats.append({
                    'game_id': game['GAME_ID'],
                    'date': game['GAME_DATE'],
                    'matchup': game['MATCHUP'],
                    'result': game['WL'],
                    'points': int(p.get('points', 0) or 0),
                    'rebounds': int(p.get('reboundsTotal', 0) or 0),
                    'assists': int(p.get('assists', 0) or 0),
                    'steals': int(p.get('steals', 0) or 0),
                    'blocks': int(p.get('blocks', 0) or 0),
                    'fg_made': int(p.get('fieldGoalsMade', 0) or 0),
                    'fg_attempted': int(p.get('fieldGoalsAttempted', 0) or 0),
                    'fg3_made': int(p.get('threePointersMade', 0) or 0),
                    'fg3_attempted': int(p.get('threePointersAttempted', 0) or 0),
                    'minutes': p.get('minutes', '0'),
                })
                
                if len(player_stats) >= last_n:
                    break
                    
        except (KeyError, ValueError, AttributeError, requests.RequestException) as e:
            print(f"Warning: Could not fetch {game['GAME_ID']}: {e}")
            continue
    
    df = pd.DataFrame(player_stats)
    
    # Calculate percentages
    if not df.empty:
        df['fg_pct'] = (df['fg_made'] / df['fg_attempted'].replace(0, 1) * 100).round(1)
        df['fg3_pct'] = (df['fg3_made'] / df['fg3_attempted'].replace(0, 1) * 100).round(1)
    
    return df


def get_player_headshot(
    player_id: int,
    size: tuple = (300, 300)
) -> Image.Image:
    """
    Fetch player headshot from NBA CDN.
    
    Args:
        player_id: NBA player ID
        size: Resize to (width, height)
    
    Returns:
        PIL Image object
    
    Example:
        >>> # Get Coby White's headshot (ID: 1629632)
        >>> img = get_player_headshot(1629632)
        >>> img.save("coby.png")
    """
    url = NBA_HEADSHOT_URL.format(player_id=player_id)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        img = img.convert('RGBA')
        img = img.resize(size, Image.Resampling.LANCZOS)
        return img
    except (requests.RequestException, OSError, ValueError) as e:
        print(f"Could not fetch headshot for {player_id}: {e}")
        # Return placeholder
        return Image.new('RGBA', size, (100, 100, 100, 255))
