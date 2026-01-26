# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation Requirements
Changes to this project MUST include **relevant** updates to these files. However, be selective with the updates, not everything might be necessary to include:

1. **`CLAUDE.md`**
2. **`README.md`**

## Notebook Requirements
**Every new analysis or visualization MUST include a Jupyter notebook** in the `notebooks/` directory that demonstrates its usage. This allows for interactive testing and serves as living documentation.

Notebook naming convention: `feature_name.ipynb` (e.g., `efficiency_matrix.ipynb`, `shot_selection_analysis.ipynb`)

**Required setup cell:** Every notebook MUST start with this setup code to enable imports from the `bulls` package:

```python
import sys
from pathlib import Path

# Add parent directory to path so we can import bulls
sys.path.insert(0, str(Path().absolute().parent))

from bulls import data, analysis, viz
import matplotlib.pyplot as plt

%matplotlib inline
```

## Project Overview

Bulls Analytics is a Python data analysis workspace for exploring Chicago Bulls basketball data and creating visualizations. It uses the NBA API to fetch data and matplotlib for charts.

**Python Version:** Python 3.11+ is recommended. If the system Python is older, install Python 3.11 via Homebrew:
```bash
brew install python@3.11
```

Then create the venv with: `python3.11 -m venv venv`

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
source venv/bin/activate && jupyter notebook notebooks/
```

### Available Notebooks

- `efficiency_matrix.ipynb` - Instagram-style efficiency vs volume quadrant chart
- `points_per_shot.ipynb` - Points per shot analysis
- `postgame_shot_charts.ipynb` - Post-game shot chart visualizations
- `shot_selection_analysis.ipynb` - Shot selection breakdown
- `zone_leaders.ipynb` - Zone-by-zone scoring leaders

## Architecture

Three-layer architecture with clear data flow:

```
DATA LAYER (bulls/data/fetch.py)
    | Returns DataFrames/dicts
ANALYSIS LAYER (bulls/analysis/stats.py)
    | Returns analysis dicts
VISUALIZATION LAYER (bulls/viz/charts.py)
    -> Returns matplotlib Figures
```

### Data Layer (`bulls.data`)
- `get_games(last_n, season)` -> DataFrame with GAME_DATE, MATCHUP, WL, PTS, PLUS_MINUS, GAME_ID
  - Returns empty DataFrame if no games found
- `get_latest_game()` -> dict with game_id, date, matchup, is_home, result, bulls_score, opponent, plus_minus
  - Raises ValueError if no games found
- `get_box_score(game_id)` -> DataFrame with name, points, reboundsTotal, assists, steals, blocks, minutes
  - Only returns Bulls players
- `get_player_games(player_name, last_n)` -> DataFrame with game_id, date, matchup, result, points, rebounds, assists, fg_pct
  - Makes multiple API calls (slow). Returns empty DataFrame if player not found.
- `get_player_headshot(player_id)` -> PIL.Image
  - Returns gray placeholder on network error
- `get_player_shots(player_id, team_id, season, last_n_games)` -> DataFrame with loc_x, loc_y, shot_made, shot_type, shot_zone, shot_distance
- `get_roster_efficiency(last_n_games, min_fga, season)` -> List of dicts with player_id, name, ts_pct, fga_per_game, games
  - Aggregates efficiency and volume data for all Bulls players

### Analysis Layer (`bulls.analysis`)
- `season_averages(player_games)` -> dict with games, points, rebounds, assists, steals, blocks, fg_pct, fg3_pct
  - Returns empty dict if input empty
- `vs_average(game_stats, averages)` -> dict with points, rebounds, assists differences
  - Positive values = above average
- `scoring_trend(player_games)` -> dict with direction (up/down/stable), average, recent_avg, high, low, last_game
  - Compares last 5 games to previous 5
- `top_performers(box_score)` -> list of dicts sorted by points, each with player_id, name, points, rebounds, assists
- `efficiency_metrics(player_games)` -> dict with ts_pct, efg_pct, games
- `game_efficiency(player_games)` -> DataFrame with ts_pct and efg_pct columns added
- `rolling_averages(player_games, metrics, windows)` -> DataFrame with {metric}_roll_{window} columns
- `consistency_score(player_games, metrics)` -> dict per metric with mean, std, cv, category (very_consistent/consistent/moderate/volatile)

### Visualization Layer (`bulls.viz`)
All return matplotlib.Figure. All support `save_path` parameter.
- `bar_chart(data, x, y, title, highlight_last)` - Highlights most recent bar
- `line_chart(data, x, y, title)` - Trend over time
- `scatter_plot(data, x, y, title, size)` - size can be column name for variable sizing
- `comparison_chart(data, x, y, group_by, title)` - Grouped bars
- `win_loss_chart(data, x, y, result_col, title)` - Green=win, red=loss
- `rolling_efficiency_chart(data, efficiency_col, result_col, league_avg)` - Line with win/loss markers
- `radar_chart(players_data, metrics, normalize)` - Spider chart, players_data is list of dicts with 'name' key
- `shot_chart(shots_data, show_zones)` - show_zones=True for heatmap, False for scatter
- `efficiency_matrix(players_data, title, league_avg_ts, league_avg_fga, show_gradient, show_names)` - Instagram-style quadrant chart with player headshots positioned by efficiency (TS%) and volume (FGA/game)

### Configuration (`bulls/config.py`)
- `BULLS_TEAM_ID = 1610612741`
- `CURRENT_SEASON = "2025-26"`
- `LAST_SEASON = "2024-25"`
- `API_DELAY = 0.6` seconds between API calls

## Testing

Tests use mocked NBA API calls (defined in `tests/conftest.py`) to avoid network dependencies. Test suite has 124 tests across 4 modules:
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
- `mock_roster_efficiency_data` - Sample roster efficiency data for `efficiency_matrix` tests
- `mock_roster_efficiency_api` - Mocks shot chart and box score APIs for `get_roster_efficiency` tests

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

# Efficiency Matrix (Instagram-style visualization)
roster = data.get_roster_efficiency(last_n_games=10, min_fga=5.0)
fig = viz.efficiency_matrix(roster, title="Bulls Efficiency Matrix")
```

## Gotchas

- Never use system Python for tests - always use `venv/bin/python` or `./run_tests.sh`
- API calls have a 0.6s delay built in to respect rate limits
- `get_player_games()` makes multiple API calls (one per game) so it can be slow
- Shot chart coordinates use NBA court coordinate system (origin at basket)
- Always check for empty DataFrames before passing to analysis functions: `if not df.empty:`
- Notebooks must include `sys.path.insert(0, str(Path().absolute().parent))` to import `bulls` - see Notebook Requirements
