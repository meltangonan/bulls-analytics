"""Fetch Bulls data from NBA API."""
import time
import json
import requests
from typing import Optional, List, Dict
import pandas as pd

from nba_api.stats.endpoints import (
    leaguegamefinder,
    boxscoretraditionalv3,
    shotchartdetail,
)

from bulls.config import (
    BULLS_TEAM_ID,
    CURRENT_SEASON,
    LAST_SEASON,
    API_DELAY,
    NBA_TEAMS,
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
    except (AttributeError, KeyError, IndexError, requests.RequestException, json.JSONDecodeError, ValueError) as e:
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
                    'ft_made': int(p.get('freeThrowsMade', 0) or 0),
                    'ft_attempted': int(p.get('freeThrowsAttempted', 0) or 0),
                    'turnovers': int(p.get('turnovers', 0) or 0),
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
        df['ft_pct'] = (df['ft_made'] / df['ft_attempted'].replace(0, 1) * 100).round(1)

    return df


def get_player_shots(
    player_id: int,
    team_id: int = BULLS_TEAM_ID,
    season: str = CURRENT_SEASON,
    last_n_games: Optional[int] = None,
) -> pd.DataFrame:
    """
    Get shot chart data for a player.

    Args:
        player_id: NBA player ID (e.g., 1629632 for Coby White)
        team_id: NBA team ID (default: Bulls)
        season: NBA season string (default: current season)
        last_n_games: Limit to last N games (optional)

    Returns:
        DataFrame with shot data including:
        - loc_x, loc_y: Court coordinates
        - shot_made: Boolean (True = made, False = missed)
        - shot_type: "2PT" or "3PT"
        - shot_zone: Zone description
        - shot_distance: Distance in feet

    Example:
        >>> shots = get_player_shots(1629632)  # Coby White
        >>> makes = shots[shots['shot_made']]
        >>> print(f"FG%: {len(makes) / len(shots) * 100:.1f}%")
    """
    time.sleep(API_DELAY)

    try:
        last_n = str(last_n_games) if last_n_games else '0'

        shot_chart = shotchartdetail.ShotChartDetail(
            team_id=team_id,
            player_id=player_id,
            season_nullable=season,
            season_type_all_star='Regular Season',
            last_n_games=last_n,
            context_measure_simple='FGA',
        )

        shots = shot_chart.get_data_frames()[0]

        if shots.empty:
            return pd.DataFrame()

        # Create clean DataFrame with relevant columns
        result = pd.DataFrame({
            'loc_x': shots['LOC_X'],
            'loc_y': shots['LOC_Y'],
            'shot_made': shots['SHOT_MADE_FLAG'] == 1,
            'shot_type': shots['SHOT_TYPE'].apply(lambda x: '3PT' if '3PT' in str(x) else '2PT'),
            'shot_zone': shots['SHOT_ZONE_BASIC'],
            'shot_distance': shots['SHOT_DISTANCE'],
            'game_id': shots['GAME_ID'],
            'game_date': shots['GAME_DATE'] if 'GAME_DATE' in shots.columns else None,
        })

        return result

    except (AttributeError, KeyError, IndexError, requests.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching shot chart for player {player_id}: {e}")
        return pd.DataFrame()


def get_team_shots(
    team_id: int = BULLS_TEAM_ID,
    season: str = CURRENT_SEASON,
    last_n_games: Optional[int] = None,
) -> pd.DataFrame:
    """
    Get shot chart data for a team (all players combined).

    Args:
        team_id: NBA team ID (default: Bulls)
        season: NBA season string (default: current season)
        last_n_games: Limit to last N games (optional)

    Returns:
        DataFrame with shot data including:
        - loc_x, loc_y: Court coordinates
        - shot_made: Boolean (True = made, False = missed)
        - shot_type: "2PT" or "3PT"
        - shot_zone: Zone description
        - shot_distance: Distance in feet
        - player_id: Player who took the shot
        - player_name: Player name (if available)

    Example:
        >>> shots = get_team_shots()
        >>> makes = shots[shots['shot_made']]
        >>> print(f"Team FG%: {len(makes) / len(shots) * 100:.1f}%")
    """
    time.sleep(API_DELAY)

    try:
        last_n = str(last_n_games) if last_n_games else '0'

        # Use player_id=0 to get all team shots
        shot_chart = shotchartdetail.ShotChartDetail(
            team_id=team_id,
            player_id=0,  # 0 means all players on the team
            season_nullable=season,
            season_type_all_star='Regular Season',
            last_n_games=last_n,
            context_measure_simple='FGA',
        )

        shots = shot_chart.get_data_frames()[0]

        if shots.empty:
            return pd.DataFrame()

        # Create clean DataFrame with relevant columns
        result = pd.DataFrame({
            'loc_x': shots['LOC_X'],
            'loc_y': shots['LOC_Y'],
            'shot_made': shots['SHOT_MADE_FLAG'] == 1,
            'shot_type': shots['SHOT_TYPE'].apply(lambda x: '3PT' if '3PT' in str(x) else '2PT'),
            'shot_zone': shots['SHOT_ZONE_BASIC'],
            'shot_distance': shots['SHOT_DISTANCE'],
            'game_id': shots['GAME_ID'],
            'game_date': shots['GAME_DATE'] if 'GAME_DATE' in shots.columns else None,
        })

        # Add player info if available
        if 'PLAYER_ID' in shots.columns:
            result['player_id'] = shots['PLAYER_ID']
        if 'PLAYER_NAME' in shots.columns:
            result['player_name'] = shots['PLAYER_NAME']

        return result

    except (AttributeError, KeyError, IndexError, requests.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching shot chart for team {team_id}: {e}")
        return pd.DataFrame()


def get_league_shots(
    season: str = LAST_SEASON,
    teams: Optional[list] = None,
) -> pd.DataFrame:
    """
    Get shot chart data for all NBA teams (or specified teams).

    Args:
        season: NBA season string (default: last season)
        teams: List of team abbreviations to fetch (default: all 30 teams)
               e.g., ["CHI", "BOS", "LAL"]

    Returns:
        DataFrame with shot data for all teams including:
        - loc_x, loc_y: Court coordinates
        - shot_made: Boolean (True = made, False = missed)
        - shot_type: "2PT" or "3PT"
        - shot_zone: Zone description
        - shot_distance: Distance in feet
        - team_id: Team ID
        - team_abbr: Team abbreviation

    Example:
        >>> league_shots = get_league_shots(season="2024-25")
        >>> print(f"Total shots: {len(league_shots):,}")
    """
    if teams is None:
        teams = list(NBA_TEAMS.keys())

    all_shots = []
    total_teams = len(teams)

    for i, abbr in enumerate(teams, 1):
        if abbr not in NBA_TEAMS:
            print(f"Warning: Unknown team abbreviation '{abbr}', skipping")
            continue

        team_info = NBA_TEAMS[abbr]
        team_id = team_info["id"]
        team_name = team_info["name"]

        print(f"[{i}/{total_teams}] Fetching {team_name}...")

        try:
            shots = get_team_shots(team_id=team_id, season=season)

            if not shots.empty:
                shots["team_id"] = team_id
                shots["team_abbr"] = abbr
                shots["team_name"] = team_name
                all_shots.append(shots)
                print(f"    -> {len(shots):,} shots")
            else:
                print(f"    -> No shots found")

        except Exception as e:
            print(f"    -> Error: {e}")
            continue

    if not all_shots:
        return pd.DataFrame()

    result = pd.concat(all_shots, ignore_index=True)
    print(f"\nTotal: {len(result):,} shots from {len(all_shots)} teams")
    return result


def get_roster_efficiency(
    last_n_games: int = 10,
    min_fga: float = 5.0,
    season: str = CURRENT_SEASON,
) -> List[Dict]:
    """
    Get efficiency and volume data for all Bulls players.

    Args:
        last_n_games: Number of recent games to analyze
        min_fga: Minimum FGA per game threshold to include player
        season: NBA season string (default: current season)

    Returns:
        List of dicts with: player_id, name, ts_pct, fga_per_game, games

    Example:
        >>> roster = get_roster_efficiency(last_n_games=10, min_fga=5.0)
        >>> for p in roster:
        ...     print(f"{p['name']}: {p['ts_pct']:.1f}% TS on {p['fga_per_game']:.1f} FGA/G")
    """
    # Get team shots to identify players and their shot attempts
    team_shots = get_team_shots(
        team_id=BULLS_TEAM_ID,
        season=season,
        last_n_games=last_n_games,
    )

    if team_shots.empty or 'player_id' not in team_shots.columns:
        return []

    # Get unique game IDs to fetch box scores
    game_ids = team_shots['game_id'].unique().tolist()

    # Aggregate player stats from box scores
    player_stats = {}

    for game_id in game_ids:
        box = get_box_score(game_id)
        if box.empty:
            continue

        for _, row in box.iterrows():
            player_id = row.get('personId') or row.get('playerId')
            if player_id is None:
                continue

            player_id = int(player_id)
            name = row.get('name', f"{row.get('firstName', '')} {row.get('familyName', '')}".strip())

            if player_id not in player_stats:
                player_stats[player_id] = {
                    'player_id': player_id,
                    'name': name,
                    'games': 0,
                    'points': 0,
                    'fga': 0,
                    'fta': 0,
                }

            player_stats[player_id]['games'] += 1
            player_stats[player_id]['points'] += int(row.get('points', 0) or 0)
            player_stats[player_id]['fga'] += int(row.get('fieldGoalsAttempted', 0) or 0)
            player_stats[player_id]['fta'] += int(row.get('freeThrowsAttempted', 0) or 0)

    # Calculate efficiency metrics and filter
    result = []
    for pid, stats in player_stats.items():
        if stats['games'] == 0:
            continue

        fga_per_game = stats['fga'] / stats['games']

        # Skip players below minimum FGA threshold
        if fga_per_game < min_fga:
            continue

        # Calculate True Shooting %
        # TS% = PTS / (2 * (FGA + 0.44 * FTA))
        tsa = stats['fga'] + 0.44 * stats['fta']
        ts_pct = (stats['points'] / (2 * tsa) * 100) if tsa > 0 else 0

        result.append({
            'player_id': pid,
            'name': stats['name'],
            'ts_pct': round(ts_pct, 1),
            'fga_per_game': round(fga_per_game, 1),
            'games': stats['games'],
        })

    # Sort by volume (FGA per game) descending
    result.sort(key=lambda x: x['fga_per_game'], reverse=True)

    return result
