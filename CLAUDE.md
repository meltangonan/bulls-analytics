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
- `get_player_games(player_name, last_n)` - Player's game log DataFrame (includes FT data)
- `get_player_headshot(player_id)` - PIL Image
- `get_player_shots(player_id, team_id, season, last_n_games)` - Shot chart DataFrame

### Analysis Layer (`bulls.analysis`)
- `season_averages(player_games)` - Mean stats dict
- `vs_average(game_stats, averages)` - Comparison dict
- `scoring_trend(player_games)` - Trend direction dict
- `top_performers(box_score)` - Ranked player list
- `efficiency_metrics(player_games)` - TS% and eFG% dict
- `game_efficiency(player_games)` - DataFrame with per-game TS%/eFG%
- `rolling_averages(player_games, metrics, windows)` - DataFrame with rolling columns
- `consistency_score(player_games, metrics)` - CV-based consistency analysis dict

### Visualization Layer (`bulls.viz`)
- `bar_chart()`, `line_chart()`, `scatter_plot()`, `comparison_chart()`, `win_loss_chart()`
- `rolling_efficiency_chart()` - Efficiency trend with win/loss markers
- `radar_chart()` - Spider chart for player comparison
- `shot_chart()` - Court visualization (scatter or heatmap mode)
- All charts use Bulls branding (red: #CE1141, black)

### Configuration (`bulls/config.py`)
- `BULLS_TEAM_ID = 1610612741`
- `CURRENT_SEASON = "2025-26"`
- `API_DELAY = 0.6` seconds between API calls

## Testing

Tests use mocked NBA API calls (defined in `tests/conftest.py`) to avoid network dependencies. Test suite has 121 tests across 4 modules:
- `test_config.py` - Config constants
- `test_data.py` - Data fetching with mocks
- `test_analysis.py` - Statistical analysis
- `test_viz.py` - Chart creation

### Available Mock Fixtures

When adding new data functions, use these fixtures from `tests/conftest.py`:

- `mock_nba_api` - Mocks `LeagueGameFinder` with sample game data
- `mock_empty_api` - Mocks `LeagueGameFinder` returning empty data
- `mock_box_score_api` - Mocks `BoxScoreTraditionalV3` with sample player stats (includes FT fields)
- `mock_empty_box_score_api` - Mocks `BoxScoreTraditionalV3` returning empty data
- `mock_headshot_request` - Mocks `requests.get` for player headshot URLs
- `mock_headshot_error` - Mocks `requests.get` to simulate network errors
- `mock_shot_chart_api` - Mocks `ShotChartDetail` with sample shot data
- `mock_empty_shot_chart_api` - Mocks `ShotChartDetail` returning empty data
- `sample_player_games` - Sample player games DataFrame for analysis tests

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
