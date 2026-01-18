# Bulls Analytics Workspace

A collaborative analysis workspace for exploring Chicago Bulls basketball data and creating unique, insightful visualizations.

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

**📖 For detailed usage instructions, see [USAGE_GUIDE.md](USAGE_GUIDE.md)**

Quick example:
```python
from bulls import data, analysis, viz

# Get latest game
game = data.get_latest_game()
print(f"{game['matchup']} - {game['result']}")

# Get recent games
games = data.get_games(last_n=10)
print(games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])

# Analyze player performance
coby = data.get_player_games("Coby White", last_n=15)
avgs = analysis.season_averages(coby)
print(f"Coby averages {avgs['points']:.1f} PPG")

# Check scoring trend
trend = analysis.scoring_trend(coby)
print(f"Trending: {trend['direction']}")

# Create visualizations
viz.bar_chart(coby, x='date', y='points', title="Coby's Scoring")
viz.line_chart(coby, x='date', y='points', title="Coby's Scoring Trend")
viz.scatter_plot(coby, x='points', y='assists', title="Points vs Assists")
viz.win_loss_chart(games, x='GAME_DATE', y='PTS', result_col='WL', title="Bulls Scoring by Game")
# Note: comparison_chart requires data with a group_by column
# Example: Compare multiple players' scoring over time
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

## Current Status: Phase 4 Complete ✅

### Phase 0: Foundation ✅
- ✅ Project structure created
- ✅ Configuration module (`bulls/config.py`)
- ✅ Data fetching module (`bulls/data/fetch.py`)
  - `get_games()` - Get Bulls games for a season
  - `get_latest_game()` - Get most recent game
  - `get_box_score()` - Get box score for a game
  - `get_player_games()` - Get player's game-by-game stats
  - `get_player_headshot()` - Fetch player headshot
- ✅ Tests written for config and data modules (30 tests: 5 config + 25 data)

### Phase 2: Analysis ✅
- ✅ Analysis module (`bulls/analysis/stats.py`)
  - `season_averages()` - Calculate player averages from game log
  - `vs_average()` - Compare game stats to season averages
  - `scoring_trend()` - Analyze trend over recent games (up/down/stable)
  - `top_performers()` - Rank players by performance in a game
- ✅ Comprehensive tests for analysis module (25 tests)

### Phase 3: Visualization ✅
- ✅ Charts module (`bulls/viz/charts.py`)
  - `bar_chart()` - Create bar charts with Bulls branding
  - `line_chart()` - Create line charts showing trends over time
- ✅ Additional chart types
  - `scatter_plot()` - Compare two metrics (e.g., points vs assists)
  - `comparison_chart()` - Compare multiple groups side by side
  - `win_loss_chart()` - Bar chart with win/loss color coding
- ✅ Comprehensive tests for visualization module (12 tests)
- ✅ All 69 tests passing

### Phase 4: Polish & Ship ✅
- ✅ Exploration notebook (`notebooks/explore.ipynb`)
  - Starter cells for data exploration, analysis, and visualization
  - Examples for getting games, analyzing players, creating charts
  - Examples for creating various chart types
- ✅ Additional chart types
  - `scatter_plot()` - Compare two metrics (e.g., points vs assists)
  - `comparison_chart()` - Compare multiple groups side by side
  - `win_loss_chart()` - Bar chart with win/loss color coding
- ✅ Enhanced chart styling
  - Bulls branding and colors
  - Multiple chart types for different use cases
  - Customizable styling options
- ✅ All 69 tests passing

## Next Steps

1. **Install dependencies** (see Quick Start above)
2. **Run tests** to verify everything works
3. **Start exploring** Bulls data together!

## Documentation

- **docs/USAGE_GUIDE.md** - Complete guide on how to use this workspace (start here!)
- **docs/PRD.md** - Product requirements and vision
- **docs/SPEC.md** - Technical specification and implementation details

## Development

This project follows software engineering best practices:
- **Testing**: pytest for all functionality
- **Modular design**: Clear separation of concerns
- **Documentation**: PRD + SPEC + code comments
- **Iterative building**: Start simple, evolve as needed
