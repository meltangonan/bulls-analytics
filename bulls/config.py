"""Configuration constants for Bulls Analytics."""

# Chicago Bulls
BULLS_TEAM_ID = 1610612741
BULLS_ABBR = "CHI"
CURRENT_SEASON = "2025-26"

# Colors (RGB tuples for Pillow, hex for reference)
BULLS_RED = (206, 17, 65)      # #CE1141
BULLS_BLACK = (0, 0, 0)        # #000000
WHITE = (255, 255, 255)        # #FFFFFF
DARK_BG = (10, 10, 10)         # #0a0a0a
GRAY = (102, 102, 102)         # #666666
GREEN = (34, 197, 94)          # #22c55e (positive)
RED = (239, 68, 68)            # #ef4444 (negative)

# NBA API
NBA_HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
API_DELAY = 0.6  # Seconds between API calls (rate limiting)

# Paths
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
