# Technical Specification: Bulls Analytics Workspace

> **Purpose:** Technical guide for building the Bulls Analytics workspace.  
> **Audience:** Developer, AI agent, or future self implementing this project.  
> **Last Updated:** January 11, 2026  
> **Status:** v0.1 - Foundation  
> **Document Type:** Living document - will evolve with the project

---

## 0. Start Here: Environment Setup

This section assumes you're starting from scratch - no Python, no project folder, nothing.

### 0.1 System Requirements

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| macOS / Linux / Windows | Any modern version | - |
| Python | 3.10+ (3.11 recommended) | `python3 --version` |
| pip | Latest | `pip3 --version` |
| Internet | Required for NBA API | - |

### 0.2 Install Python (if needed)

**macOS:**
```bash
brew install python@3.11
python3 --version
```

**Windows:**
Download from https://www.python.org/downloads/, check "Add to PATH"

**Linux:**
```bash
sudo apt install python3.11 python3.11-venv python3-pip
```

### 0.3 Create Project

```bash
# Create project folder
mkdir bulls-analytics
cd bulls-analytics

# Initialize git
git init

# Create virtual environment
python3 -m venv venv

# Activate it (do this every session)
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

### 0.4 Install Dependencies

Create `requirements.txt`:
```
nba_api>=1.4
pandas>=2.0.0
Pillow>=10.0.0
matplotlib>=3.7.0
requests>=2.28.0
pytest>=7.0.0
```

Install:
```bash
pip install -r requirements.txt
```

### 0.5 Create Directory Structure

```bash
# Create package structure
mkdir -p bulls/{data,analysis,viz}
mkdir -p notebooks
mkdir -p output
mkdir -p assets/fonts
mkdir -p tests

# Create __init__.py files
touch bulls/__init__.py
touch bulls/data/__init__.py
touch bulls/analysis/__init__.py
touch bulls/viz/__init__.py
touch tests/__init__.py
```

### 0.6 Download Fonts (Optional - for polished graphics)

Download and place in `assets/fonts/`:
- **Bebas Neue**: https://fonts.google.com/specimen/Bebas+Neue
- **Inter**: https://fonts.google.com/specimen/Inter

### 0.7 Verify Setup

```python
# test_setup.py
from nba_api.stats.static import teams

bulls = [t for t in teams.get_teams() if t['abbreviation'] == 'CHI'][0]
print(f"✅ Setup complete! Bulls ID: {bulls['id']}")
```

```bash
python test_setup.py
# Expected: ✅ Setup complete! Bulls ID: 1610612741
```

---

## 1. Architecture Overview

### Design Principles

| Principle | What It Means |
|-----------|---------------|
| **Simple** | Easy to understand, easy to modify |
| **Modular** | Each part does one thing well |
| **AI-Friendly** | Functions are easy for AI to discover and use |
| **Iterative** | Built to evolve, not to be perfect upfront |
| **Tested** | Code should have tests - this isn't optional, it's what good engineers do |
| **Documented** | Code explains itself; PRD/SPEC capture the "why" |

### Software Engineering Practices

This project follows real-world software engineering practices:

| Practice | How We Apply It |
|----------|-----------------|
| **Version Control** | Git for tracking changes, commits tell a story |
| **Testing** | Write tests alongside features, not as an afterthought |
| **Documentation** | PRD (what/why) + SPEC (how) + code comments |
| **Separation of Concerns** | Data fetching, analysis, and visualization are separate modules |
| **Single Responsibility** | Each function does one thing well |
| **DRY (Don't Repeat Yourself)** | Shared config, reusable functions |
| **Readable Over Clever** | Code should be obvious, not impressive |

### Understanding the Concepts

You don't need to memorize every line of code. Focus on understanding:

| Concept | What to Understand |
|---------|-------------------|
| **Modules & Imports** | How code is organized into files and packages |
| **Functions** | Inputs, outputs, and what happens in between |
| **Data Structures** | DataFrames, dictionaries, lists - how data is shaped |
| **APIs** | How we talk to external services (NBA API) |
| **Dependencies** | External packages that do heavy lifting for us |
| **Testing** | How we verify code works correctly |

### Structure

```
bulls-analytics/
├── bulls/                    # Core library
│   ├── __init__.py          # Package exports
│   ├── config.py            # Constants (team ID, colors, etc.)
│   ├── data/                # Data fetching
│   │   ├── __init__.py
│   │   └── fetch.py         # NBA API functions
│   ├── analysis/            # Analysis helpers
│   │   ├── __init__.py
│   │   └── stats.py         # Calculations, comparisons
│   └── viz/                 # Visualization
│       ├── __init__.py
│       ├── charts.py        # Basic charts
│       └── instagram.py     # Instagram-ready graphics
│
├── tests/                   # Test suite (yes, we test!)
│   ├── __init__.py
│   ├── test_data.py         # Tests for data module
│   ├── test_analysis.py     # Tests for analysis module
│   └── test_viz.py          # Tests for viz module
│
├── notebooks/               # Exploration notebooks
│   └── explore.ipynb        # Interactive analysis
│
├── output/                  # Generated graphics
├── assets/                  # Fonts, logos
├── requirements.txt
├── SPEC.md                  # This file
└── PRD.md                   # Product requirements
```

### How It's Used

```
┌─────────────────────────────────────────────────────────────┐
│                     YOU + AI (Cursor)                       │
│                                                             │
│   "Get me the last Bulls game"                              │
│   "Show me Coby's scoring trend"                            │
│   "Create a bar chart of this"                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     bulls library                           │
│                                                             │
│   bulls.data    →  Fetch from NBA API                       │
│   bulls.analysis →  Calculate trends, averages              │
│   bulls.viz     →  Create charts and graphics               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Outputs                               │
│                                                             │
│   - Data displayed in chat/notebook                         │
│   - Charts for exploration                                  │
│   - Instagram graphics (when ready)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Module: bulls.config

Constants and configuration. Single source of truth.

### File: `bulls/config.py`

```python
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

# Instagram dimensions
INSTAGRAM_PORTRAIT = (1080, 1350)
INSTAGRAM_SQUARE = (1080, 1080)

# NBA API
NBA_HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
API_DELAY = 0.6  # Seconds between API calls (rate limiting)

# Paths
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
```

---

## 3. Module: bulls.data

Fetching data from NBA API. The foundation of everything.

### File: `bulls/data/__init__.py`

```python
"""Data fetching for Bulls Analytics."""
from bulls.data.fetch import (
    get_latest_game,
    get_games,
    get_box_score,
    get_player_games,
    get_player_headshot,
)
```

### File: `bulls/data/fetch.py`

```python
"""Fetch Bulls data from NBA API."""
import time
import requests
from io import BytesIO
from datetime import datetime
from typing import Optional
import pandas as pd
from PIL import Image

from nba_api.stats.endpoints import (
    leaguegamefinder,
    boxscoretraditionalv3,
)

from bulls.config import (
    BULLS_TEAM_ID,
    CURRENT_SEASON,
    API_DELAY,
    NBA_HEADSHOT_URL,
)


def get_games(
    last_n: Optional[int] = None,
    season: str = CURRENT_SEASON
) -> pd.DataFrame:
    """
    Get Bulls games for a season.
    
    Args:
        last_n: Return only the last N games (most recent first)
        season: NBA season string (default: current season)
    
    Returns:
        DataFrame with game info (date, opponent, score, result, etc.)
    
    Example:
        >>> games = get_games(last_n=10)
        >>> games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']]
    """
    finder = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=BULLS_TEAM_ID,
        season_nullable=season,
        season_type_nullable='Regular Season'
    )
    games = finder.get_data_frames()[0]
    games = games.sort_values('GAME_DATE', ascending=False)
    
    if last_n:
        games = games.head(last_n)
    
    return games


def get_latest_game() -> dict:
    """
    Get the most recent Bulls game.
    
    Returns:
        Dict with game info including:
        - game_id, date, matchup, result (W/L)
        - bulls_score, opponent_score
        - opponent name
    
    Example:
        >>> game = get_latest_game()
        >>> print(f"{game['matchup']} - {game['result']}")
    """
    games = get_games(last_n=1)
    row = games.iloc[0]
    
    matchup = row['MATCHUP']
    is_home = 'vs.' in matchup
    
    if is_home:
        opponent = matchup.split('vs.')[-1].strip()
    else:
        opponent = matchup.split('@')[-1].strip()
    
    return {
        'game_id': row['GAME_ID'],
        'date': row['GAME_DATE'],
        'matchup': matchup,
        'is_home': is_home,
        'result': row['WL'],
        'bulls_score': int(row['PTS']),
        'opponent': opponent,
        'plus_minus': int(row['PLUS_MINUS']),
    }


def get_box_score(game_id: str) -> pd.DataFrame:
    """
    Get box score for a specific game.
    
    Args:
        game_id: NBA game ID (e.g., "0022500503")
    
    Returns:
        DataFrame with player stats for Bulls players only.
        Columns include: player name, points, rebounds, assists, etc.
    
    Example:
        >>> game = get_latest_game()
        >>> box = get_box_score(game['game_id'])
        >>> box[['firstName', 'familyName', 'points', 'rebounds', 'assists']]
    """
    time.sleep(API_DELAY)
    
    box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
    players = box.player_stats.get_data_frame()
    
    # Filter to Bulls players only
    bulls_players = players[players['teamId'] == BULLS_TEAM_ID].copy()
    
    # Add full name column for convenience
    bulls_players['name'] = bulls_players['firstName'] + ' ' + bulls_players['familyName']
    
    return bulls_players


def get_player_games(
    player_name: str,
    last_n: int = 20,
    season: str = CURRENT_SEASON
) -> pd.DataFrame:
    """
    Get a player's game-by-game stats.
    
    Args:
        player_name: Player's name (e.g., "Coby White")
        last_n: Number of recent games
        season: NBA season
    
    Returns:
        DataFrame with the player's stats for each game.
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=10)
        >>> coby[['date', 'points', 'assists', 'fg_pct']]
    """
    games = get_games(last_n=last_n * 2, season=season)  # Fetch extra to account for DNPs
    
    player_stats = []
    
    for _, game in games.iterrows():
        time.sleep(API_DELAY)
        
        try:
            box = get_box_score(game['GAME_ID'])
            
            # Find player in box score (case-insensitive match)
            player_row = box[box['name'].str.lower() == player_name.lower()]
            
            if not player_row.empty:
                p = player_row.iloc[0]
                player_stats.append({
                    'game_id': game['GAME_ID'],
                    'date': game['GAME_DATE'],
                    'matchup': game['MATCHUP'],
                    'result': game['WL'],
                    'points': int(p.get('points', 0) or 0),
                    'rebounds': int(p.get('reboundsTotal', 0) or 0),
                    'assists': int(p.get('assists', 0) or 0),
                    'steals': int(p.get('steals', 0) or 0),
                    'blocks': int(p.get('blocks', 0) or 0),
                    'fg_made': int(p.get('fieldGoalsMade', 0) or 0),
                    'fg_attempted': int(p.get('fieldGoalsAttempted', 0) or 0),
                    'fg3_made': int(p.get('threePointersMade', 0) or 0),
                    'fg3_attempted': int(p.get('threePointersAttempted', 0) or 0),
                    'minutes': p.get('minutes', '0'),
                })
                
                if len(player_stats) >= last_n:
                    break
                    
        except Exception as e:
            print(f"Warning: Could not fetch {game['GAME_ID']}: {e}")
            continue
    
    df = pd.DataFrame(player_stats)
    
    # Calculate percentages
    if not df.empty:
        df['fg_pct'] = (df['fg_made'] / df['fg_attempted'].replace(0, 1) * 100).round(1)
        df['fg3_pct'] = (df['fg3_made'] / df['fg3_attempted'].replace(0, 1) * 100).round(1)
    
    return df


def get_player_headshot(
    player_id: int,
    size: tuple = (300, 300)
) -> Image.Image:
    """
    Fetch player headshot from NBA CDN.
    
    Args:
        player_id: NBA player ID
        size: Resize to (width, height)
    
    Returns:
        PIL Image object
    
    Example:
        >>> # Get Coby White's headshot (ID: 1629632)
        >>> img = get_player_headshot(1629632)
        >>> img.save("coby.png")
    """
    url = NBA_HEADSHOT_URL.format(player_id=player_id)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        img = img.convert('RGBA')
        img = img.resize(size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"Could not fetch headshot for {player_id}: {e}")
        # Return placeholder
        return Image.new('RGBA', size, (100, 100, 100, 255))
```

---

## 4. Module: bulls.analysis

Calculations, comparisons, and finding interesting things.

### File: `bulls/analysis/__init__.py`

```python
"""Analysis helpers for Bulls Analytics."""
from bulls.analysis.stats import (
    season_averages,
    vs_average,
    scoring_trend,
    top_performers,
)
```

### File: `bulls/analysis/stats.py`

```python
"""Statistical analysis functions."""
import pandas as pd
from typing import Optional


def season_averages(player_games: pd.DataFrame) -> dict:
    """
    Calculate a player's averages from their game log.
    
    Args:
        player_games: DataFrame from get_player_games()
    
    Returns:
        Dict with average stats (points, rebounds, assists, fg_pct, etc.)
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=20)
        >>> avgs = season_averages(coby)
        >>> print(f"Coby averages {avgs['points']:.1f} PPG")
    """
    if player_games.empty:
        return {}
    
    return {
        'games': len(player_games),
        'points': player_games['points'].mean(),
        'rebounds': player_games['rebounds'].mean(),
        'assists': player_games['assists'].mean(),
        'steals': player_games['steals'].mean(),
        'blocks': player_games['blocks'].mean(),
        'fg_pct': player_games['fg_pct'].mean(),
        'fg3_pct': player_games['fg3_pct'].mean(),
    }


def vs_average(
    game_stats: dict,
    averages: dict
) -> dict:
    """
    Compare a single game to season averages.
    
    Args:
        game_stats: Dict with game stats (points, rebounds, etc.)
        averages: Dict from season_averages()
    
    Returns:
        Dict with differences (positive = above average)
    
    Example:
        >>> avgs = season_averages(coby_games)
        >>> last_game = {'points': 28, 'rebounds': 5, 'assists': 7}
        >>> diff = vs_average(last_game, avgs)
        >>> print(f"Points vs avg: {diff['points']:+.1f}")
    """
    return {
        'points': game_stats.get('points', 0) - averages.get('points', 0),
        'rebounds': game_stats.get('rebounds', 0) - averages.get('rebounds', 0),
        'assists': game_stats.get('assists', 0) - averages.get('assists', 0),
    }


def scoring_trend(
    player_games: pd.DataFrame,
    metric: str = 'points'
) -> dict:
    """
    Analyze scoring trend over recent games.
    
    Args:
        player_games: DataFrame from get_player_games()
        metric: Which stat to analyze ('points', 'assists', etc.)
    
    Returns:
        Dict with trend info (direction, streak, high, low)
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=10)
        >>> trend = scoring_trend(coby)
        >>> print(f"Trending: {trend['direction']}")
    """
    if player_games.empty or metric not in player_games.columns:
        return {}
    
    values = player_games[metric].tolist()
    avg = sum(values) / len(values)
    
    # Recent trend (last 5 vs previous 5)
    recent = values[:5] if len(values) >= 5 else values
    previous = values[5:10] if len(values) >= 10 else values[len(recent):]
    
    recent_avg = sum(recent) / len(recent) if recent else 0
    previous_avg = sum(previous) / len(previous) if previous else recent_avg
    
    if recent_avg > previous_avg * 1.1:
        direction = "up"
    elif recent_avg < previous_avg * 0.9:
        direction = "down"
    else:
        direction = "stable"
    
    return {
        'direction': direction,
        'average': avg,
        'recent_avg': recent_avg,
        'high': max(values),
        'low': min(values),
        'last_game': values[0] if values else 0,
    }


def top_performers(box_score: pd.DataFrame) -> list:
    """
    Rank players by performance in a game.
    
    Args:
        box_score: DataFrame from get_box_score()
    
    Returns:
        List of dicts with player info, sorted by points (desc)
    
    Example:
        >>> box = get_box_score(game_id)
        >>> top = top_performers(box)
        >>> print(f"Top scorer: {top[0]['name']} with {top[0]['points']} pts")
    """
    performers = []
    
    for _, row in box_score.iterrows():
        performers.append({
            'player_id': row['personId'],
            'name': row['name'],
            'first_name': row['firstName'],
            'last_name': row['familyName'],
            'points': int(row.get('points', 0) or 0),
            'rebounds': int(row.get('reboundsTotal', 0) or 0),
            'assists': int(row.get('assists', 0) or 0),
            'steals': int(row.get('steals', 0) or 0),
            'blocks': int(row.get('blocks', 0) or 0),
            'fg_made': int(row.get('fieldGoalsMade', 0) or 0),
            'fg_attempted': int(row.get('fieldGoalsAttempted', 0) or 0),
        })
    
    # Sort by points, then assists, then rebounds
    performers.sort(key=lambda x: (x['points'], x['assists'], x['rebounds']), reverse=True)
    
    return performers
```

---

## 5. Module: bulls.viz

Visualization - charts and Instagram graphics.

### File: `bulls/viz/__init__.py`

```python
"""Visualization for Bulls Analytics."""
from bulls.viz.charts import (
    bar_chart,
    line_chart,
)
from bulls.viz.instagram import (
    create_graphic,
)
```

### File: `bulls/viz/charts.py`

```python
"""Basic chart functions using matplotlib."""
import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional, List
from pathlib import Path

from bulls.config import BULLS_RED, BULLS_BLACK, WHITE, OUTPUT_DIR


def bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    highlight_last: bool = True,
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Create a bar chart.
    
    Args:
        data: DataFrame with the data
        x: Column name for x-axis
        y: Column name for y-axis (bar heights)
        title: Chart title
        color: Bar color (RGB tuple)
        highlight_last: Highlight the most recent bar
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=10)
        >>> bar_chart(coby, x='date', y='points', title="Coby's Scoring")
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Reverse data so oldest is first (left to right chronologically)
    plot_data = data.iloc[::-1].copy()
    
    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()
    
    # Color bars
    colors = [tuple(c/255 for c in color)] * len(y_vals)
    if highlight_last and len(colors) > 0:
        colors[-1] = tuple(c/255 for c in BULLS_RED)  # Highlight most recent
    
    ax.bar(x_vals, y_vals, color=colors, edgecolor='black', linewidth=0.5)
    
    # Styling
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_ylabel(y.capitalize())
    
    # X-axis labels
    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        # Shorten date labels if needed
        if 'date' in x.lower():
            labels = [str(l)[5:10] if len(str(l)) > 5 else l for l in labels]
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45, ha='right')
    
    # Add average line
    avg = sum(y_vals) / len(y_vals)
    ax.axhline(y=avg, color='gray', linestyle='--', alpha=0.7, label=f'Avg: {avg:.1f}')
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig


def line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Create a line chart showing trend over time.
    
    Args:
        data: DataFrame with the data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Line color (RGB tuple)
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Reverse for chronological order
    plot_data = data.iloc[::-1].copy()
    
    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()
    
    ax.plot(x_vals, y_vals, color=tuple(c/255 for c in color), linewidth=2, marker='o')
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_ylabel(y.capitalize())
    
    # X-axis labels
    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        if 'date' in x.lower():
            labels = [str(l)[5:10] if len(str(l)) > 5 else l for l in labels]
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig
```

### File: `bulls/viz/instagram.py`

```python
"""Instagram-ready graphics using Pillow."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Optional

from bulls.config import (
    BULLS_RED, BULLS_BLACK, WHITE, DARK_BG, GRAY,
    INSTAGRAM_PORTRAIT, OUTPUT_DIR, FONTS_DIR
)


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font, with fallback to default."""
    font_paths = [
        FONTS_DIR / f"{name}.ttf",
        FONTS_DIR / f"{name}-Regular.ttf",
    ]
    
    for path in font_paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    
    # Fallback
    return ImageFont.load_default()


def create_graphic(
    title: str,
    subtitle: str = "",
    stats: dict = None,
    player_name: str = "",
    player_image: Optional[Image.Image] = None,
    footer: str = "@bullsanalytics",
    size: tuple = INSTAGRAM_PORTRAIT,
    save_path: Optional[str] = None,
) -> Image.Image:
    """
    Create an Instagram-ready graphic.
    
    This is a flexible template - customize as needed.
    
    Args:
        title: Main headline
        subtitle: Secondary text
        stats: Dict of stats to display (e.g., {'PTS': 28, 'REB': 5})
        player_name: Player's name to display
        player_image: PIL Image of player headshot
        footer: Attribution text
        size: Image dimensions
        save_path: Path to save (optional)
    
    Returns:
        PIL Image object
    
    Example:
        >>> img = create_graphic(
        ...     title="CLUTCH PERFORMANCE",
        ...     subtitle="Bulls vs Heat • Jan 10, 2026",
        ...     stats={'PTS': 28, 'REB': 5, 'AST': 7},
        ...     player_name="COBY WHITE",
        ...     save_path="output/coby_clutch.png"
        ... )
    """
    # Create canvas
    img = Image.new('RGB', size, DARK_BG)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    font_title = load_font("BebasNeue", 72)
    font_subtitle = load_font("Inter", 28)
    font_name = load_font("BebasNeue", 56)
    font_stat_value = load_font("BebasNeue", 64)
    font_stat_label = load_font("Inter", 20)
    font_footer = load_font("Inter", 18)
    
    width, height = size
    y_cursor = 80
    
    # Title
    bbox = draw.textbbox((0, 0), title, font=font_title)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_cursor), title, font=font_title, fill=WHITE)
    y_cursor += 90
    
    # Subtitle
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, y_cursor), subtitle, font=font_subtitle, fill=GRAY)
        y_cursor += 60
    
    # Player section
    if player_image or player_name:
        y_cursor += 40
        
        # Player image (if provided)
        if player_image:
            # Resize and paste
            img_size = 250
            player_image = player_image.resize((img_size, img_size), Image.Resampling.LANCZOS)
            paste_x = (width - img_size) // 2
            
            # Create circular mask
            mask = Image.new('L', (img_size, img_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, img_size, img_size), fill=255)
            
            img.paste(player_image, (paste_x, y_cursor), mask)
            y_cursor += img_size + 30
        
        # Player name
        if player_name:
            bbox = draw.textbbox((0, 0), player_name, font=font_name)
            text_width = bbox[2] - bbox[0]
            draw.text(((width - text_width) // 2, y_cursor), player_name, font=font_name, fill=WHITE)
            y_cursor += 70
    
    # Stats
    if stats:
        y_cursor += 30
        stat_spacing = width // (len(stats) + 1)
        
        for i, (label, value) in enumerate(stats.items()):
            x = stat_spacing * (i + 1)
            
            # Value
            value_text = str(value)
            bbox = draw.textbbox((0, 0), value_text, font=font_stat_value)
            text_width = bbox[2] - bbox[0]
            draw.text((x - text_width // 2, y_cursor), value_text, font=font_stat_value, fill=BULLS_RED)
            
            # Label
            bbox = draw.textbbox((0, 0), label, font=font_stat_label)
            text_width = bbox[2] - bbox[0]
            draw.text((x - text_width // 2, y_cursor + 65), label, font=font_stat_label, fill=GRAY)
    
    # Footer
    bbox = draw.textbbox((0, 0), footer, font=font_footer)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, height - 50), footer, font=font_footer, fill=GRAY)
    
    # Save if path provided
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        save_path = Path(save_path)
        img.save(save_path, "PNG")
        print(f"Saved to {save_path}")
    
    return img
```

---

## 6. Package Exports

### File: `bulls/__init__.py`

```python
"""
Bulls Analytics - Collaborative analysis workspace for Chicago Bulls data.

Usage:
    from bulls import data, analysis, viz
    
    # Get recent games
    games = data.get_games(last_n=10)
    
    # Get player stats
    coby = data.get_player_games("Coby White", last_n=15)
    
    # Analyze
    avgs = analysis.season_averages(coby)
    trend = analysis.scoring_trend(coby)
    
    # Visualize
    viz.bar_chart(coby, x='date', y='points', title="Coby's Scoring")
    viz.create_graphic(title="...", stats={...})
"""

from bulls import data
from bulls import analysis
from bulls import viz
from bulls.config import BULLS_TEAM_ID, CURRENT_SEASON

__version__ = "0.1.0"
```

---

## 7. Example Notebook

### File: `notebooks/explore.ipynb`

Create a Jupyter notebook with these starter cells:

**Cell 1: Setup**
```python
# Setup
import sys
sys.path.insert(0, '..')  # Add parent directory to path

from bulls import data, analysis, viz
import pandas as pd

print("✅ Bulls Analytics loaded")
print(f"Season: {from bulls.config import CURRENT_SEASON; CURRENT_SEASON}")
```

**Cell 2: Get Recent Games**
```python
# Get last 10 Bulls games
games = data.get_games(last_n=10)
games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'PLUS_MINUS']]
```

**Cell 3: Latest Game Box Score**
```python
# Get last game
game = data.get_latest_game()
print(f"{game['matchup']} - {game['result']}")
print(f"Bulls: {game['bulls_score']}")

# Box score
box = data.get_box_score(game['game_id'])
box[['name', 'points', 'rebounds', 'assists']].sort_values('points', ascending=False)
```

**Cell 4: Player Analysis**
```python
# Coby White's recent games
coby = data.get_player_games("Coby White", last_n=15)
coby[['date', 'matchup', 'points', 'assists', 'fg_pct']]
```

**Cell 5: Averages**
```python
# Calculate averages
avgs = analysis.season_averages(coby)
print(f"Coby's averages over {avgs['games']} games:")
print(f"  Points: {avgs['points']:.1f}")
print(f"  Assists: {avgs['assists']:.1f}")
print(f"  FG%: {avgs['fg_pct']:.1f}%")
```

**Cell 6: Visualization**
```python
# Bar chart of scoring
viz.bar_chart(
    coby, 
    x='date', 
    y='points', 
    title="Coby White - Points Per Game (Last 15)"
)
```

---

## 8. Testing

Testing isn't optional - it's what good engineers do. Even as a PM using AI to build, you should understand *why* we test and ensure code is tested.

### Why We Test

| Reason | Explanation |
|--------|-------------|
| **Confidence** | Know that code works before shipping |
| **Catch Regressions** | Changes don't break existing functionality |
| **Documentation** | Tests show how code is *supposed* to work |
| **Refactoring Safety** | Can improve code without fear |
| **Professional Practice** | This is non-negotiable in real software |

### Testing Strategy

| Test Type | What It Tests | When to Run |
|-----------|---------------|-------------|
| **Unit Tests** | Individual functions in isolation | During development |
| **Integration Tests** | Multiple components working together | Before committing |
| **Smoke Tests** | Quick check that core features work | After changes |

### Directory Structure for Tests

```
bulls-analytics/
├── bulls/              # Source code
├── tests/              # Test files
│   ├── __init__.py
│   ├── test_data.py    # Tests for data module
│   ├── test_analysis.py # Tests for analysis module
│   └── test_viz.py     # Tests for viz module
```

### Running Tests

```bash
# Install pytest (add to requirements.txt)
pip install pytest

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_data.py
```

### Quick Smoke Test

After implementing, verify everything works:

```python
from bulls import data, analysis, viz

# Test data fetching
game = data.get_latest_game()
print(f"✅ Latest game: {game['matchup']}")

box = data.get_box_score(game['game_id'])
print(f"✅ Box score: {len(box)} players")

# Test analysis
top = analysis.top_performers(box)
print(f"✅ Top scorer: {top[0]['name']} ({top[0]['points']} pts)")

# Test viz
fig = viz.bar_chart(
    data.get_player_games(top[0]['name'], last_n=5),
    x='date', y='points',
    title=f"{top[0]['name']} Recent Scoring"
)
print("✅ Chart created")
```

### Example Test File

**File: `tests/test_analysis.py`**
```python
"""Tests for bulls.analysis module."""
import pytest
import pandas as pd
from bulls.analysis import season_averages, scoring_trend

class TestSeasonAverages:
    """Tests for season_averages function."""
    
    def test_returns_correct_keys(self):
        """Should return dict with expected stat keys."""
        fake_games = pd.DataFrame({
            'points': [20, 25, 30],
            'rebounds': [5, 6, 7],
            'assists': [3, 4, 5],
            'steals': [1, 2, 1],
            'blocks': [0, 1, 0],
            'fg_pct': [45.0, 50.0, 55.0],
            'fg3_pct': [35.0, 40.0, 45.0],
        })
        
        result = season_averages(fake_games)
        
        assert 'points' in result
        assert 'rebounds' in result
        assert 'assists' in result
    
    def test_calculates_correct_average(self):
        """Should calculate correct averages."""
        fake_games = pd.DataFrame({
            'points': [10, 20, 30],
            'rebounds': [5, 5, 5],
            'assists': [3, 3, 3],
            'steals': [1, 1, 1],
            'blocks': [0, 0, 0],
            'fg_pct': [50.0, 50.0, 50.0],
            'fg3_pct': [40.0, 40.0, 40.0],
        })
        
        result = season_averages(fake_games)
        
        assert result['points'] == 20.0
        assert result['rebounds'] == 5.0
    
    def test_handles_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty_df = pd.DataFrame()
        result = season_averages(empty_df)
        assert result == {}
```

---

## 9. Implementation Order

Build in this order. Each phase includes testing - this is how real software gets built:

### Phase 0: Foundation
1. Create directory structure (including `tests/` folder)
2. Create `bulls/config.py`
3. Create `bulls/data/fetch.py` with `get_games()` and `get_latest_game()`
4. **Write tests:** Basic tests for config constants, test API calls return expected structure
5. **Verify:** `pytest` passes, can fetch and print Bulls games

### Phase 1: Data Layer Complete
1. Add `get_box_score()`
2. Add `get_player_games()`
3. Add `get_player_headshot()`
4. **Write tests:** Test each function handles edge cases (empty results, missing data)
5. **Verify:** `pytest` passes, can get a player's recent stats

### Phase 2: Analysis
1. Create `bulls/analysis/stats.py`
2. Add `season_averages()`, `vs_average()`
3. Add `scoring_trend()`, `top_performers()`
4. **Write tests:** Test calculations with known inputs, test empty dataframe handling
5. **Verify:** `pytest` passes, can analyze a player's performance

### Phase 3: Visualization
1. Create `bulls/viz/charts.py` with `bar_chart()`
2. Create `bulls/viz/instagram.py` with `create_graphic()`
3. **Write tests:** Test that functions return expected types, test file saving
4. **Verify:** `pytest` passes, can create a chart and save it

### Phase 4: Polish & Ship
1. Create exploration notebook
2. Add more chart types as needed
3. Refine Instagram graphic template
4. **Full test suite:** Run all tests, fix any issues
5. **Use it!** See what's missing, iterate

### The Testing Mindset

| Phase | Write Code | Write Tests | Run Tests |
|-------|-----------|-------------|-----------|
| Every phase | ✅ | ✅ | ✅ |

This isn't "extra work" - it's how professional software gets built. Tests give you confidence to ship.

---

## 10. Future Additions (As Needed)

Add these when you need them, not before:

| Feature | When to Add |
|---------|-------------|
| Quarter-by-quarter breakdown | When analyzing clutch performances |
| Team comparison | When comparing Bulls to opponents/league |
| Shot chart data | When analyzing shooting locations |
| Season trends | When looking at longer-term patterns |
| More graphic templates | When you know what styles work |

---

## 11. Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: bulls` | Make sure you're in project root, venv activated |
| NBA API timeout | Add longer delays, try again later |
| Font not found | Download fonts to `assets/fonts/` or use fallback |
| Rate limiting | Increase `API_DELAY` in config.py |

---

## 12. Decisions Log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2026-01-11 | Compute averages from game logs | Simpler than PlayerDashboard API |
| 2026-01-11 | Matplotlib for charts | Good enough, familiar, can upgrade later |
| 2026-01-11 | Pillow for Instagram graphics | Python-native, simple, flexible |
| 2026-01-11 | No CLI tool | Focus on exploration workflow |
| 2026-01-11 | pytest for testing | Industry standard, simple, well-documented |
| 2026-01-11 | Tests in separate `tests/` folder | Clean separation, standard Python convention |
| 2026-01-11 | Test each phase before moving on | Build confidence incrementally |