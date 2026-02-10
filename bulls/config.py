"""Configuration constants for Bulls Analytics."""

# Chicago Bulls
BULLS_TEAM_ID = 1610612741
BULLS_ABBR = "CHI"
CURRENT_SEASON = "2025-26"
LAST_SEASON = "2024-25"

# All NBA Team IDs
NBA_TEAMS = {
    "ATL": {"id": 1610612737, "name": "Atlanta Hawks"},
    "BOS": {"id": 1610612738, "name": "Boston Celtics"},
    "BKN": {"id": 1610612751, "name": "Brooklyn Nets"},
    "CHA": {"id": 1610612766, "name": "Charlotte Hornets"},
    "CHI": {"id": 1610612741, "name": "Chicago Bulls"},
    "CLE": {"id": 1610612739, "name": "Cleveland Cavaliers"},
    "DAL": {"id": 1610612742, "name": "Dallas Mavericks"},
    "DEN": {"id": 1610612743, "name": "Denver Nuggets"},
    "DET": {"id": 1610612765, "name": "Detroit Pistons"},
    "GSW": {"id": 1610612744, "name": "Golden State Warriors"},
    "HOU": {"id": 1610612745, "name": "Houston Rockets"},
    "IND": {"id": 1610612754, "name": "Indiana Pacers"},
    "LAC": {"id": 1610612746, "name": "LA Clippers"},
    "LAL": {"id": 1610612747, "name": "Los Angeles Lakers"},
    "MEM": {"id": 1610612763, "name": "Memphis Grizzlies"},
    "MIA": {"id": 1610612748, "name": "Miami Heat"},
    "MIL": {"id": 1610612749, "name": "Milwaukee Bucks"},
    "MIN": {"id": 1610612750, "name": "Minnesota Timberwolves"},
    "NOP": {"id": 1610612740, "name": "New Orleans Pelicans"},
    "NYK": {"id": 1610612752, "name": "New York Knicks"},
    "OKC": {"id": 1610612760, "name": "Oklahoma City Thunder"},
    "ORL": {"id": 1610612753, "name": "Orlando Magic"},
    "PHI": {"id": 1610612755, "name": "Philadelphia 76ers"},
    "PHX": {"id": 1610612756, "name": "Phoenix Suns"},
    "POR": {"id": 1610612757, "name": "Portland Trail Blazers"},
    "SAC": {"id": 1610612758, "name": "Sacramento Kings"},
    "SAS": {"id": 1610612759, "name": "San Antonio Spurs"},
    "TOR": {"id": 1610612761, "name": "Toronto Raptors"},
    "UTA": {"id": 1610612762, "name": "Utah Jazz"},
    "WAS": {"id": 1610612764, "name": "Washington Wizards"},
}

# Colors (RGB tuples)
BULLS_RED = (206, 17, 65)      # #CE1141
BULLS_BLACK = (0, 0, 0)        # #000000
GREEN = (34, 197, 94)          # #22c55e (positive)
RED = (239, 68, 68)            # #ef4444 (negative)

# NBA API
API_DELAY = 0.6  # Seconds between API calls (rate limiting)
