"""Fetch Bulls data from NBA API."""
import time
import json
from pathlib import Path
import requests
from typing import Optional, List, Dict
import pandas as pd

from nba_api.stats.endpoints import (
    leaguegamefinder,
    boxscoretraditionalv3,
    shotchartdetail,
    commonteamroster,
    leaguedashlineups,
    leaguedashplayerstats,
    leaguedashteamstats,
)

from bulls.config import (
    BULLS_TEAM_ID,
    CURRENT_SEASON,
    LAST_SEASON,
    API_DELAY,
    NBA_TEAMS,
)

# Custom headers needed for reliable NBA Stats API access
_NBA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.nba.com/',
    'Accept': 'application/json',
}


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
            timeout=60,
            headers=_NBA_HEADERS,
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
            timeout=60,
            headers=_NBA_HEADERS,
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

        # Add zone area for granular zone breakdowns
        if 'SHOT_ZONE_AREA' in shots.columns:
            result['shot_zone_area'] = shots['SHOT_ZONE_AREA']

        # Add player info if available
        if 'PLAYER_ID' in shots.columns:
            result['player_id'] = shots['PLAYER_ID']
        if 'PLAYER_NAME' in shots.columns:
            result['player_name'] = shots['PLAYER_NAME']

        return result

    except (AttributeError, KeyError, IndexError, requests.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching shot chart for team {team_id}: {e}")
        return pd.DataFrame()


def league_for_game(game_id: str) -> str:
    """
    Derive the NBA league ID from a game ID.

    The first two digits of every game ID encode the league: '00' NBA,
    '15' Summer League, '20' G League. ShotChartDetail filters by league
    server-side and defaults to the NBA, so it silently returns zero rows
    for a Summer League game unless this is passed along.
    """
    return str(game_id)[:2]


def get_game_shots(
    game_id: str,
    team_id: int = BULLS_TEAM_ID,
) -> pd.DataFrame:
    """
    Get shot chart data for one team in one game, any league.

    Unlike the season-scoped shot fetchers above, this works for Summer
    League games because it derives league_id from the game ID.

    Args:
        game_id: NBA.com game ID (e.g. '1522500033' for a Summer League game)
        team_id: NBA team ID (default: Bulls)

    Returns:
        DataFrame with the same columns as get_team_shots:
        - loc_x, loc_y: Court coordinates (tenths of feet, hoop at origin)
        - shot_made: Boolean (True = made, False = missed)
        - shot_type: "2PT" or "3PT"
        - shot_zone: NBA zone label (SHOT_ZONE_BASIC)
        - shot_distance: Distance in feet
        - player_id, player_name: Who took the shot

    Example:
        >>> shots = get_game_shots('1522500033')
        >>> shots[shots['player_name'] == 'Matas Buzelis']['shot_zone'].value_counts()
    """
    time.sleep(API_DELAY)

    try:
        shot_chart = shotchartdetail.ShotChartDetail(
            league_id=league_for_game(game_id),
            team_id=team_id,
            player_id=0,  # 0 means all players on the team
            game_id_nullable=game_id,
            season_type_all_star='Regular Season',
            context_measure_simple='FGA',
            timeout=60,
            headers=_NBA_HEADERS,
        )

        shots = shot_chart.get_data_frames()[0]

        if shots.empty:
            return pd.DataFrame()

        result = pd.DataFrame({
            'loc_x': shots['LOC_X'],
            'loc_y': shots['LOC_Y'],
            'shot_made': shots['SHOT_MADE_FLAG'] == 1,
            'shot_type': shots['SHOT_TYPE'].apply(lambda x: '3PT' if '3PT' in str(x) else '2PT'),
            'shot_zone': shots['SHOT_ZONE_BASIC'],
            'shot_distance': shots['SHOT_DISTANCE'],
            'game_id': shots['GAME_ID'],
            'player_id': shots['PLAYER_ID'],
            'player_name': shots['PLAYER_NAME'],
        })

        if 'SHOT_ZONE_AREA' in shots.columns:
            result['shot_zone_area'] = shots['SHOT_ZONE_AREA']

        return result

    except (AttributeError, KeyError, IndexError, requests.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching shot chart for game {game_id}: {e}")
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


def get_roster(
    team_id: int = BULLS_TEAM_ID,
    season: str = CURRENT_SEASON,
) -> pd.DataFrame:
    """
    Get the current roster for a team.

    Args:
        team_id: NBA team ID (default: Bulls)
        season: NBA season string (default: current season)

    Returns:
        DataFrame with player_id and player_name columns.

    Example:
        >>> roster = get_roster()
        >>> roster[['player_name', 'player_id']]
    """
    time.sleep(API_DELAY)

    try:
        roster = commonteamroster.CommonTeamRoster(
            team_id=team_id,
            season=season,
            timeout=60,
            headers=_NBA_HEADERS,
        )
        df = roster.common_team_roster.get_data_frame()

        if df.empty:
            return pd.DataFrame(columns=['player_id', 'player_name'])

        return pd.DataFrame({
            'player_id': df['PLAYER_ID'],
            'player_name': df['PLAYER'],
        })

    except (AttributeError, KeyError, IndexError, requests.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching roster for team {team_id}: {e}")
        return pd.DataFrame(columns=['player_id', 'player_name'])


# Columns consumed from the lineup response (Advanced measure type)
_LINEUP_COLUMNS = ['GROUP_ID', 'GROUP_NAME', 'GP', 'MIN',
                   'OFF_RATING', 'DEF_RATING', 'NET_RATING']

_TEAM_PLAYER_ADVANCED_COLUMNS = [
    'PLAYER_ID', 'PLAYER_NAME', 'GP', 'MIN',
    'OFF_RATING', 'DEF_RATING', 'NET_RATING', 'POSS',
]

_TEAM_ADVANCED_COLUMNS = [
    'TEAM_ID', 'TEAM_NAME', 'GP', 'MIN',
    'OFF_RATING', 'DEF_RATING', 'NET_RATING', 'PACE', 'POSS',
]


def get_team_advanced_stats(
    team_id: int = BULLS_TEAM_ID,
    season: str = CURRENT_SEASON,
) -> pd.DataFrame:
    """Get a team's regular-season advanced ratings from NBA.com."""
    time.sleep(API_DELAY)

    try:
        teams = leaguedashteamstats.LeagueDashTeamStats(
            team_id_nullable=team_id,
            season=season,
            season_type_all_star='Regular Season',
            per_mode_detailed='Totals',
            measure_type_detailed_defense='Advanced',
            timeout=60,
            headers=_NBA_HEADERS,
        ).get_data_frames()[0]

        if teams.empty:
            return pd.DataFrame(columns=_TEAM_ADVANCED_COLUMNS)

        return teams[_TEAM_ADVANCED_COLUMNS].copy().reset_index(drop=True)

    except (AttributeError, KeyError, IndexError, requests.RequestException,
            json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching advanced stats for team {team_id}: {e}")
        return pd.DataFrame(columns=_TEAM_ADVANCED_COLUMNS)


def get_team_player_advanced_stats(
    team_id: int = BULLS_TEAM_ID,
    season: str = CURRENT_SEASON,
) -> pd.DataFrame:
    """Get team-stint player minutes and on-court advanced ratings.

    NBA.com's player Advanced response reports ``MIN`` as minutes per game,
    even with ``PerMode=Totals``. The player Traditional response does return
    total minutes. Both requests use the same team filter, and this function
    joins total minutes from Traditional to the on-court ratings from
    Advanced so traded players retain only the selected team's stint.

    Returns:
        DataFrame with ``PLAYER_ID``, ``PLAYER_NAME``, ``GP``, total ``MIN``,
        ``OFF_RATING``, ``DEF_RATING``, ``NET_RATING``, and ``POSS``.
    """
    try:
        request_kwargs = {
            'team_id_nullable': team_id,
            'season': season,
            'season_type_all_star': 'Regular Season',
            'per_mode_detailed': 'Totals',
            'timeout': 60,
            'headers': _NBA_HEADERS,
        }

        time.sleep(API_DELAY)
        traditional = leaguedashplayerstats.LeagueDashPlayerStats(
            measure_type_detailed_defense='Base',
            **request_kwargs,
        ).get_data_frames()[0]

        time.sleep(API_DELAY)
        advanced = leaguedashplayerstats.LeagueDashPlayerStats(
            measure_type_detailed_defense='Advanced',
            **request_kwargs,
        ).get_data_frames()[0]

        if traditional.empty or advanced.empty:
            return pd.DataFrame(columns=_TEAM_PLAYER_ADVANCED_COLUMNS)

        minutes = traditional[['PLAYER_ID', 'PLAYER_NAME', 'GP', 'MIN']].copy()
        ratings = advanced[
            ['PLAYER_ID', 'OFF_RATING', 'DEF_RATING', 'NET_RATING', 'POSS']
        ].copy()
        result = minutes.merge(ratings, on='PLAYER_ID', how='inner', validate='one_to_one')
        return result[_TEAM_PLAYER_ADVANCED_COLUMNS].sort_values(
            'MIN', ascending=False
        ).reset_index(drop=True)

    except (AttributeError, KeyError, IndexError, requests.RequestException,
            json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching player advanced stats for team {team_id}: {e}")
        return pd.DataFrame(columns=_TEAM_PLAYER_ADVANCED_COLUMNS)


def get_lineup_stats(
    min_minutes: float = 0,
    team_id: int = BULLS_TEAM_ID,
    season: str = CURRENT_SEASON,
) -> pd.DataFrame:
    """
    Get 2-man lineup stats for a team.

    Uses the Advanced measure type because the default Base measure
    does not include OFF_RATING/DEF_RATING/NET_RATING columns.

    Args:
        min_minutes: Drop lineups with total MIN below this threshold
        team_id: NBA team ID (default: Bulls)
        season: NBA season string (default: current season)

    Returns:
        DataFrame with columns:
        - GROUP_ID: Dash-separated player IDs in the lineup
        - GROUP_NAME: Lineup label (e.g., "C. White - J. Giddey")
        - GP: Games played together
        - MIN: Total minutes together
        - OFF_RATING, DEF_RATING, NET_RATING: Advanced ratings

    Example:
        >>> lineups = get_lineup_stats(min_minutes=100)
        >>> lineups.sort_values('NET_RATING', ascending=False).head()
    """
    time.sleep(API_DELAY)

    try:
        lineups = leaguedashlineups.LeagueDashLineups(
            group_quantity=2,
            team_id_nullable=team_id,
            season=season,
            per_mode_detailed='Totals',
            measure_type_detailed_defense='Advanced',
            timeout=60,
            headers=_NBA_HEADERS,
        )

        df = lineups.get_data_frames()[0]

        if df.empty:
            return pd.DataFrame(columns=_LINEUP_COLUMNS)

        result = df[_LINEUP_COLUMNS].copy()

        if min_minutes > 0:
            result = result[result['MIN'] >= min_minutes].reset_index(drop=True)

        return result

    except (AttributeError, KeyError, IndexError, requests.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching lineup stats for team {team_id}: {e}")
        return pd.DataFrame(columns=_LINEUP_COLUMNS)


def get_player_headshot(
    player_id: int,
    cache_dir: str = "cache/headshots",
) -> Optional[Path]:
    """
    Download and cache a player headshot from the NBA CDN.

    Args:
        player_id: NBA player ID
        cache_dir: Local directory to cache headshot PNGs

    Returns:
        Path to cached headshot PNG, or None if download fails.
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    file_path = cache_path / f"{player_id}.png"
    if file_path.exists():
        return file_path

    url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)
        return file_path
    except requests.RequestException:
        return None
