# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bulls Analytics is a Python data analysis workspace for exploring Chicago Bulls basketball data and creating visualizations. It uses the NBA API to fetch data and matplotlib for charts.

## Commands

### Running Tests

**Critical: Always use the virtual environment's Python. System Python will hang.**

```bash
# Recommended
./run_tests.sh

# Or directly
venv/bin/python -m pytest tests/ -v

# Single test file
venv/bin/python -m pytest tests/test_data.py -v

# Single test function
venv/bin/python -m pytest tests/test_analysis.py::TestScoringTrend::test_calculates_trend_direction -v

# Tests matching pattern
venv/bin/python -m pytest tests/ -k "scatter" -v
```

### Setup Verification

```bash
python test_setup.py
```

### Interactive Exploration

```bash
source venv/bin/activate && jupyter notebook notebooks/explore.ipynb
```

## Architecture

Three-layer architecture with clear data flow:

```
DATA LAYER (bulls/data/fetch.py)
    ↓ Returns DataFrames/dicts
ANALYSIS LAYER (bulls/analysis/stats.py)
    ↓ Returns analysis dicts
VISUALIZATION LAYER (bulls/viz/charts.py)
    → Returns matplotlib Figures
```

### Data Layer (`bulls.data`)
- `get_games(last_n, season)` - Team games DataFrame
- `get_latest_game()` - Most recent game dict
- `get_box_score(game_id)` - Player stats DataFrame
- `get_player_games(player_name, last_n)` - Player's game log DataFrame
- `get_player_headshot(player_id)` - PIL Image

### Analysis Layer (`bulls.analysis`)
- `season_averages(player_games)` - Mean stats dict
- `vs_average(game_stats, averages)` - Comparison dict
- `scoring_trend(player_games)` - Trend direction dict
- `top_performers(box_score)` - Ranked player list

### Visualization Layer (`bulls.viz`)
- `bar_chart()`, `line_chart()`, `scatter_plot()`, `comparison_chart()`, `win_loss_chart()`
- All charts use Bulls branding (red: #CE1141, black)

### Configuration (`bulls/config.py`)
- `BULLS_TEAM_ID = 1610612741`
- `CURRENT_SEASON = "2025-26"`
- `API_DELAY = 0.6` seconds between API calls

## Testing

Tests use mocked NBA API calls (defined in `tests/conftest.py`) to avoid network dependencies. Test suite has 67 tests across 4 modules:
- `test_config.py` - Config constants
- `test_data.py` - Data fetching with mocks
- `test_analysis.py` - Statistical analysis
- `test_viz.py` - Chart creation

When adding new data functions, use the `mock_nba_api` fixture from conftest.py.

## Usage Pattern

```python
from bulls import data, analysis, viz

# Fetch
games = data.get_games(last_n=10)
player_games = data.get_player_games("Coby White", last_n=15)

# Analyze
avgs = analysis.season_averages(player_games)
trend = analysis.scoring_trend(player_games)

# Visualize
fig = viz.bar_chart(player_games, x='date', y='points', title="Scoring")
```
