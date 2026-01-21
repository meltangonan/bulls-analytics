# Bulls Analytics

Python workspace for exploring Chicago Bulls basketball data. Fetches data from the NBA API and creates visualizations with matplotlib.

## Requirements

- Python 3.11+ (3.11 recommended)
- Virtual environment
- Internet connection for NBA API access

## Setup

### Installing Python 3.11 on macOS

If your system Python is older than 3.11, install Python 3.11 via Homebrew:

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11
```

### Quickstart

```bash
# Create and activate virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Verify setup
python test_setup.py
# Expected: Setup complete! Bulls ID: 1610612741
```

**Note:** If you don't have Python 3.11 installed, replace `python3.11` with `python3` (but Python 3.11+ is recommended).

## Running Tests

Always use the virtual environment's Python. System Python will hang.

```bash
# Recommended
./run_tests.sh

# Or directly
venv/bin/python -m pytest tests/ -v
```

## Usage

```python
from bulls import data, analysis, viz

# Fetch data
games = data.get_games(last_n=10)
player_games = data.get_player_games("Coby White", last_n=15)

# Analyze
avgs = analysis.season_averages(player_games)
trend = analysis.scoring_trend(player_games)

# Visualize
viz.bar_chart(player_games, x='date', y='points', title="Scoring")
viz.line_chart(player_games, x='date', y='points', title="Trend")
```

## Project Layout

```
bulls-analytics/
├── bulls/              # Core library
│   ├── config.py       # Constants (team ID, colors, seasons)
│   ├── data/           # Data fetching from NBA API
│   ├── analysis/       # Statistical analysis functions
│   └── viz/            # Chart creation (matplotlib)
├── tests/              # Test suite (97 tests, mocked API calls)
├── notebooks/          # Jupyter notebooks for exploration
├── output/             # Generated graphics
└── docs/               # Documentation
```

## Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `BULLS_TEAM_ID` | `1610612741` | Chicago Bulls team ID |
| `CURRENT_SEASON` | `"2025-26"` | Current NBA season |
| `LAST_SEASON` | `"2024-25"` | Previous season |
| `API_DELAY` | `0.6` | Seconds between API calls |

These are defined in `bulls/config.py`.

## Troubleshooting

**Tests hang or fail with system Python**
- Always use `venv/bin/python -m pytest` or `./run_tests.sh`
- Never use bare `python -m pytest`

**API timeouts**
- NBA API has rate limits; the workspace includes delays
- Wait and retry if you get timeouts

**Empty DataFrame returned**
- Check player name spelling (case-insensitive but must be exact)
- Verify the season string format (e.g., "2025-26")

**ModuleNotFoundError: No module named 'bulls'**
- Run from project root directory
- Activate virtual environment: `source venv/bin/activate`
