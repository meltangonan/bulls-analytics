"""Quick smoke test to verify setup works."""
from nba_api.stats.static import teams

bulls = [t for t in teams.get_teams() if t['abbreviation'] == 'CHI'][0]
print(f"✅ Setup complete! Bulls ID: {bulls['id']}")
