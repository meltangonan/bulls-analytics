"""
Bulls Analytics - Collaborative analysis workspace for Chicago Bulls data.

Usage:
    from bulls import data, analysis, graphics

    # Get recent games
    games = data.get_games(last_n=10)

    # Get player stats
    coby = data.get_player_games("Coby White", last_n=15)

    # Analyze
    avgs = analysis.season_averages(coby)
    trend = analysis.scoring_trend(coby)

    # Shared graphics helpers live in bulls.graphics; post-specific renderers
    # start in scripts/prototypes.
"""

from bulls import data
from bulls import analysis
from bulls import graphics
from bulls.config import BULLS_TEAM_ID, CURRENT_SEASON

__version__ = "0.1.0"
