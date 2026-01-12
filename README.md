# Bulls Analytics Workspace

A collaborative analysis workspace for exploring Chicago Bulls basketball data and creating unique, insightful visualizations for Instagram.

## Quick Start

### 1. Set Up Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Setup

```bash
python test_setup.py
# Expected: ✅ Setup complete! Bulls ID: 1610612741
```

### 3. Run Tests

**Important:** Always use the virtual environment's Python to run tests. The tests use mocks to avoid real API calls.

```bash
# Option 1: Use the helper script (recommended)
./run_tests.sh

# Option 2: Use venv Python directly
venv/bin/python -m pytest tests/ -v

# Option 3: Activate venv first, then run
source venv/bin/activate
pytest tests/ -v
```

**⚠️ Do NOT use `python -m pytest`** - this uses system Python and will hang or fail!

### 4. Start Exploring

```python
from bulls import data

# Get latest game
game = data.get_latest_game()
print(f"{game['matchup']} - {game['result']}")

# Get recent games
games = data.get_games(last_n=10)
print(games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])
```

## Project Structure

```
bulls-analytics/
├── bulls/              # Core library
│   ├── config.py      # Constants (team ID, colors, etc.)
│   ├── data/          # Data fetching from NBA API
│   ├── analysis/      # Analysis helpers (Phase 2)
│   └── viz/           # Visualization (Phase 3)
├── tests/             # Test suite
├── notebooks/         # Exploration notebooks
├── output/            # Generated graphics
└── requirements.txt   # Dependencies
```

## Current Status: Phase 0 Complete ✅

- ✅ Project structure created
- ✅ Configuration module (`bulls/config.py`)
- ✅ Data fetching module (`bulls/data/fetch.py`)
  - `get_games()` - Get Bulls games for a season
  - `get_latest_game()` - Get most recent game
  - `get_box_score()` - Get box score for a game
  - `get_player_games()` - Get player's game-by-game stats
  - `get_player_headshot()` - Fetch player headshot
- ✅ Tests written for config and data modules
- ✅ Package structure with proper `__init__.py` files

## Next Steps

1. **Install dependencies** (see Quick Start above)
2. **Run tests** to verify everything works
3. **Start exploring** Bulls data together!

## Documentation

- **PRD.md** - Product requirements and vision
- **SPEC.md** - Technical specification and implementation details
- **AGENT_PROMPT.md** - Context for AI collaborators

## Development

This project follows software engineering best practices:
- **Testing**: pytest for all functionality
- **Modular design**: Clear separation of concerns
- **Documentation**: PRD + SPEC + code comments
- **Iterative building**: Start simple, evolve as needed
