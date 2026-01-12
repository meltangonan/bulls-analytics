# Bulls Analytics Workspace - Complete Usage Guide

> **A comprehensive guide to using the Bulls Analytics workspace for exploring Chicago Bulls data, analyzing player performance, and creating visualizations.**

---

## Table of Contents

1. [What Is This Workspace?](#what-is-this-workspace)
2. [Prerequisites & Setup](#prerequisites--setup)
3. [Two Ways to Use This Workspace](#two-ways-to-use-this-workspace)
4. [Complete Function Reference](#complete-function-reference)
5. [Common Workflows](#common-workflows)
6. [Tips & Best Practices](#tips--best-practices)
7. [Troubleshooting](#troubleshooting)

---

## What Is This Workspace?

The Bulls Analytics workspace is a Python library designed to help you:

- **Fetch** Chicago Bulls game data and player statistics from the NBA API
- **Analyze** player performance, trends, and patterns
- **Visualize** data with charts and create visualizations

It's built as a collaborative tool - you explore data, find insights, and create visualizations. The workspace provides the tools; you provide the questions and creativity.

### Key Concepts

- **Data Layer** (`bulls.data`): Fetches data from the NBA API
- **Analysis Layer** (`bulls.analysis`): Calculates averages, trends, comparisons
- **Visualization Layer** (`bulls.viz`): Creates charts and visualizations

All three layers work together, but you can use them independently based on what you need.

---

## Prerequisites & Setup

### Requirements

- Python 3.8 or higher (3.10+ recommended)
- Internet connection (for NBA API access)
- Virtual environment (already set up in this project)

### Initial Setup

1. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate     # Windows
   ```

2. **Verify setup:**
   ```bash
   python test_setup.py
   # Should output: ✅ Setup complete! Bulls ID: 1610612741
   ```

3. **Run tests to confirm everything works:**
   ```bash
   ./run_tests.sh
   # or
   venv/bin/python -m pytest tests/ -v
   ```

If all tests pass, you're ready to go!

### Installing Additional Dependencies

If you want to use Jupyter notebooks:
```bash
pip install jupyter
```

---

## Two Ways to Use This Workspace

### Option 1: Jupyter Notebook (Recommended for Exploration)

**Best for:** Interactive exploration, experimenting with data, iterating on visualizations

1. **Start Jupyter:**
   ```bash
   source venv/bin/activate
   jupyter notebook
   ```

2. **Open the exploration notebook:**
   - Navigate to `notebooks/explore.ipynb`
   - This notebook has starter cells for common tasks

3. **Run cells and explore:**
   - Each cell is self-contained
   - Modify variables (like `PLAYER_NAME`) to explore different data
   - Add new cells as needed

**Why use notebooks?**
- See data and charts inline
- Easy to iterate and experiment
- Keep your exploration organized
- Great for learning and discovery

### Option 2: Python Scripts or Cursor Chat

**Best for:** Quick queries, automation, asking AI for help

1. **In a Python script:**
   ```python
   from bulls import data, analysis, viz
   
   # Your code here
   ```

2. **In Cursor chat:**
   - Just ask questions like "What happened in the last Bulls game?"
   - I'll use the workspace functions to answer

**Why use scripts/chat?**
- Fast for quick questions
- Good for automation
- Can integrate with other tools
- AI can help you use the functions

---

## Complete Function Reference

### Module: `bulls.data`

Functions for fetching data from the NBA API.

#### `get_games(last_n=None, season='2025-26')`

Get Bulls games for a season.

**Parameters:**
- `last_n` (int, optional): Return only the last N games. If `None`, returns all games.
- `season` (str): NBA season string (default: current season from config)

**Returns:** `pandas.DataFrame` with columns:
- `GAME_DATE`: Date of the game
- `MATCHUP`: Opponent (e.g., "CHI vs. MIA" or "CHI @ BOS")
- `WL`: Win ('W') or Loss ('L')
- `PTS`: Points scored
- `PLUS_MINUS`: Point differential
- `GAME_ID`: Unique game identifier
- And many more stats...

**Example:**
```python
from bulls import data

# Get last 10 games
games = data.get_games(last_n=10)
print(games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])

# Get all games from a specific season
games_2024 = data.get_games(season='2024-25')
```

**Notes:**
- Games are sorted by date (most recent first)
- If `last_n` is provided, returns the N most recent games
- Returns empty DataFrame if no games found

---

#### `get_latest_game()`

Get the most recent Bulls game.

**Returns:** `dict` with keys:
- `game_id`: NBA game ID (string)
- `date`: Game date (string)
- `matchup`: Full matchup string (e.g., "CHI vs. MIA")
- `is_home`: Boolean (True if home game)
- `result`: 'W' or 'L'
- `bulls_score`: Bulls points (int)
- `opponent`: Opponent name (string)
- `plus_minus`: Point differential (int)

**Example:**
```python
from bulls import data

game = data.get_latest_game()
print(f"{game['matchup']} - {game['result']}")
print(f"Score: Bulls {game['bulls_score']}")
```

**Notes:**
- Raises `ValueError` if no games found
- Always returns the most recent completed game

---

#### `get_box_score(game_id)`

Get detailed box score for a specific game.

**Parameters:**
- `game_id` (str): NBA game ID (e.g., "0022500503")

**Returns:** `pandas.DataFrame` with player stats. Columns include:
- `name`: Full player name
- `firstName`, `familyName`: Player name parts
- `points`: Points scored
- `reboundsTotal`: Total rebounds
- `assists`: Assists
- `steals`: Steals
- `blocks`: Blocks
- `fieldGoalsMade`, `fieldGoalsAttempted`: Shooting stats
- `threePointersMade`, `threePointersAttempted`: 3PT stats
- `minutes`: Minutes played
- And more...

**Example:**
```python
from bulls import data

# Get latest game ID
game = data.get_latest_game()
box = data.get_box_score(game['game_id'])

# Show top scorers
print(box[['name', 'points', 'reboundsTotal', 'assists']].sort_values('points', ascending=False))
```

**Notes:**
- Only returns Bulls players (filters by team ID)
- Includes a `name` column for convenience (combines firstName + familyName)
- Has a built-in delay to respect NBA API rate limits

---

#### `get_player_games(player_name, last_n=20, season='2025-26')`

Get a player's game-by-game stats.

**Parameters:**
- `player_name` (str): Player's name (e.g., "Coby White")
- `last_n` (int): Number of recent games to fetch (default: 20)
- `season` (str): NBA season string

**Returns:** `pandas.DataFrame` with one row per game. Columns:
- `game_id`: Game identifier
- `date`: Game date
- `matchup`: Opponent
- `result`: 'W' or 'L'
- `points`: Points scored
- `rebounds`: Total rebounds
- `assists`: Assists
- `steals`: Steals
- `blocks`: Blocks
- `fg_made`, `fg_attempted`: Field goal stats
- `fg3_made`, `fg3_attempted`: 3-point stats
- `fg_pct`: Field goal percentage (calculated)
- `fg3_pct`: 3-point percentage (calculated)
- `minutes`: Minutes played

**Example:**
```python
from bulls import data

# Get Coby White's last 15 games
coby = data.get_player_games("Coby White", last_n=15)
print(coby[['date', 'points', 'assists', 'fg_pct']])
```

**Notes:**
- Name matching is case-insensitive
- Fetches extra games to account for DNPs (Did Not Play)
- Returns empty DataFrame if player not found
- Calculates shooting percentages automatically
- This function makes multiple API calls (one per game), so it may take a while

---

#### `get_player_headshot(player_id, size=(300, 300))`

Fetch a player's headshot image from NBA CDN.

**Parameters:**
- `player_id` (int): NBA player ID
- `size` (tuple): Resize dimensions (width, height)

**Returns:** `PIL.Image` object

**Example:**
```python
from bulls import data

# Coby White's player ID is 1629632
img = data.get_player_headshot(1629632, size=(400, 400))
img.save("coby_headshot.png")
```

**Notes:**
- Returns a placeholder gray image if fetch fails
- Image is automatically resized and converted to RGBA format
- You need to know the player ID (can find it in box score data)

---

### Module: `bulls.analysis`

Functions for analyzing data and finding insights.

#### `season_averages(player_games)`

Calculate a player's averages from their game log.

**Parameters:**
- `player_games` (DataFrame): DataFrame from `get_player_games()`

**Returns:** `dict` with keys:
- `games`: Number of games
- `points`: Average points per game
- `rebounds`: Average rebounds per game
- `assists`: Average assists per game
- `steals`: Average steals per game
- `blocks`: Average blocks per game
- `fg_pct`: Average field goal percentage
- `fg3_pct`: Average 3-point percentage

**Example:**
```python
from bulls import data, analysis

coby = data.get_player_games("Coby White", last_n=20)
avgs = analysis.season_averages(coby)

print(f"Coby averages {avgs['points']:.1f} PPG")
print(f"Over {avgs['games']} games")
```

**Notes:**
- Returns empty dict if input DataFrame is empty
- All averages are floating-point numbers

---

#### `vs_average(game_stats, averages)`

Compare a single game's stats to season averages.

**Parameters:**
- `game_stats` (dict): Dict with game stats (e.g., `{'points': 28, 'rebounds': 5}`)
- `averages` (dict): Dict from `season_averages()`

**Returns:** `dict` with differences:
- `points`: Points vs average (positive = above average)
- `rebounds`: Rebounds vs average
- `assists`: Assists vs average

**Example:**
```python
from bulls import data, analysis

# Get player averages
coby = data.get_player_games("Coby White", last_n=20)
avgs = analysis.season_averages(coby)

# Compare last game
last_game = coby.iloc[0]
game_stats = {
    'points': last_game['points'],
    'rebounds': last_game['rebounds'],
    'assists': last_game['assists']
}

diff = analysis.vs_average(game_stats, avgs)
print(f"Points vs avg: {diff['points']:+.1f}")
```

**Notes:**
- Positive values mean above average
- Negative values mean below average
- Only compares points, rebounds, and assists

---

#### `scoring_trend(player_games, metric='points')`

Analyze trend over recent games.

**Parameters:**
- `player_games` (DataFrame): DataFrame from `get_player_games()`
- `metric` (str): Which stat to analyze (default: 'points')

**Returns:** `dict` with keys:
- `direction`: 'up', 'down', or 'stable'
- `average`: Overall average
- `recent_avg`: Average of last 5 games
- `high`: Highest value
- `low`: Lowest value
- `last_game`: Most recent game value

**Example:**
```python
from bulls import data, analysis

coby = data.get_player_games("Coby White", last_n=15)
trend = analysis.scoring_trend(coby)

print(f"Trend: {trend['direction']}")
print(f"Recent avg: {trend['recent_avg']:.1f} PPG")
print(f"Overall avg: {trend['average']:.1f} PPG")
```

**Notes:**
- Direction is determined by comparing last 5 games to previous 5
- "Up" means recent avg > 110% of previous avg
- "Down" means recent avg < 90% of previous avg
- Otherwise "stable"
- Can analyze any numeric column (points, assists, rebounds, etc.)

---

#### `top_performers(box_score)`

Rank players by performance in a game.

**Parameters:**
- `box_score` (DataFrame): DataFrame from `get_box_score()`

**Returns:** `list` of dicts, sorted by points (descending). Each dict contains:
- `player_id`: NBA player ID
- `name`: Full name
- `first_name`, `last_name`: Name parts
- `points`: Points scored
- `rebounds`: Total rebounds
- `assists`: Assists
- `steals`: Steals
- `blocks`: Blocks
- `fg_made`, `fg_attempted`: Shooting stats

**Example:**
```python
from bulls import data, analysis

game = data.get_latest_game()
box = data.get_box_score(game['game_id'])
top = analysis.top_performers(box)

print("Top 3 performers:")
for i, player in enumerate(top[:3], 1):
    print(f"{i}. {player['name']}: {player['points']} PTS")
```

**Notes:**
- Sorted by points, then assists, then rebounds
- Returns all players from the box score

---

### Module: `bulls.viz`

Functions for creating charts and visualizations.

#### `bar_chart(data, x, y, title='', color=None, highlight_last=True, save_path=None, figsize=(10, 6))`

Create a bar chart.

**Parameters:**
- `data` (DataFrame): Data to plot
- `x` (str): Column name for x-axis labels
- `y` (str): Column name for bar heights
- `title` (str): Chart title
- `color` (tuple): RGB color tuple (default: Bulls red)
- `highlight_last` (bool): Highlight the most recent bar (default: True)
- `save_path` (str, optional): Path to save image
- `figsize` (tuple): Figure size (width, height)

**Returns:** `matplotlib.Figure` object

**Example:**
```python
from bulls import data, viz

coby = data.get_player_games("Coby White", last_n=10)
viz.bar_chart(
    coby,
    x='date',
    y='points',
    title="Coby's Scoring (Last 10 Games)",
    save_path="output/coby_scoring.png"
)
```

**Notes:**
- Data is automatically reversed so oldest is on the left
- Includes an average line
- Most recent bar is highlighted in Bulls red
- Saves to `output/` directory if `save_path` provided

---

#### `line_chart(data, x, y, title='', color=None, save_path=None, figsize=(10, 6))`

Create a line chart showing trends over time.

**Parameters:**
- `data` (DataFrame): Data to plot
- `x` (str): Column name for x-axis labels
- `y` (str): Column name for y-axis values
- `title` (str): Chart title
- `color` (tuple): RGB color tuple (default: Bulls red)
- `save_path` (str, optional): Path to save image
- `figsize` (tuple): Figure size

**Returns:** `matplotlib.Figure` object

**Example:**
```python
from bulls import data, viz

coby = data.get_player_games("Coby White", last_n=15)
viz.line_chart(
    coby,
    x='date',
    y='points',
    title="Coby's Scoring Trend"
)
```

**Notes:**
- Shows trend over time with markers
- Data is automatically reversed for chronological order
- Good for seeing patterns and trends

---

#### `scatter_plot(data, x, y, title='', color=None, size=None, save_path=None, figsize=(10, 6))`

Create a scatter plot comparing two metrics.

**Parameters:**
- `data` (DataFrame): Data to plot
- `x` (str): Column name for x-axis
- `y` (str): Column name for y-axis
- `title` (str): Chart title
- `color` (tuple): RGB color tuple (default: Bulls red)
- `size` (int or str, optional): Point size, or column name for variable sizing
- `save_path` (str, optional): Path to save image
- `figsize` (tuple): Figure size

**Returns:** `matplotlib.Figure` object

**Example:**
```python
from bulls import data, viz

coby = data.get_player_games("Coby White", last_n=15)
viz.scatter_plot(
    coby,
    x='points',
    y='assists',
    title="Points vs Assists"
)
```

**Notes:**
- Great for finding correlations
- Can use a column name for `size` to show a third dimension
- Includes grid for easier reading

---

#### `comparison_chart(data, x, y, group_by, title='', save_path=None, figsize=(10, 6))`

Create a comparison chart showing multiple groups side by side.

**Parameters:**
- `data` (DataFrame): Data to plot
- `x` (str): Column name for x-axis (categories)
- `y` (str): Column name for y-axis (values)
- `group_by` (str): Column name to group by (creates multiple series)
- `title` (str): Chart title
- `save_path` (str, optional): Path to save image
- `figsize` (tuple): Figure size

**Returns:** `matplotlib.Figure` object

**Example:**
```python
from bulls import data, viz
import pandas as pd

# Compare multiple players (requires combining data first)
# This is a more advanced use case
```

**Notes:**
- Useful for comparing multiple players or categories
- Creates grouped bars
- Requires data to be structured with a grouping column

---

#### `win_loss_chart(data, x, y, result_col='result', title='', save_path=None, figsize=(10, 6))`

Create a bar chart with different colors for wins and losses.

**Parameters:**
- `data` (DataFrame): Data to plot
- `x` (str): Column name for x-axis
- `y` (str): Column name for y-axis (bar heights)
- `result_col` (str): Column name containing 'W' or 'L' (default: 'result')
- `title` (str): Chart title
- `save_path` (str, optional): Path to save image
- `figsize` (tuple): Figure size

**Returns:** `matplotlib.Figure` object

**Example:**
```python
from bulls import data, viz

games = data.get_games(last_n=10)
viz.win_loss_chart(
    games,
    x='GAME_DATE',
    y='PTS',
    result_col='WL',
    title="Bulls Scoring by Game (Last 10)"
)
```

**Notes:**
- Green bars = wins, Red bars = losses
- Includes legend
- Great for seeing team performance patterns

---

---

## Common Workflows

### Workflow 1: Check Last Night's Game

**Goal:** Get a quick summary of the most recent Bulls game.

```python
from bulls import data, analysis

# Get latest game
game = data.get_latest_game()
print(f"🏀 {game['matchup']}")
print(f"📅 {game['date']}")
print(f"🏆 Result: {game['result']}")
print(f"📊 Score: Bulls {game['bulls_score']}")

# Get box score
box = data.get_box_score(game['game_id'])

# Find top performers
top = analysis.top_performers(box)
print(f"\n⭐ Top Scorer: {top[0]['name']} with {top[0]['points']} points")
```

**When to use:** After a game, quick check-ins, starting an analysis session.

---

### Workflow 2: Analyze a Player's Recent Performance

**Goal:** Understand how a player has been performing lately.

```python
from bulls import data, analysis, viz

# Step 1: Get player data
PLAYER_NAME = "Coby White"
player = data.get_player_games(PLAYER_NAME, last_n=15)

# Step 2: Calculate averages
avgs = analysis.season_averages(player)
print(f"{PLAYER_NAME} - Averages over {avgs['games']} games:")
print(f"  Points: {avgs['points']:.1f} PPG")
print(f"  Rebounds: {avgs['rebounds']:.1f} RPG")
print(f"  Assists: {avgs['assists']:.1f} APG")
print(f"  FG%: {avgs['fg_pct']:.1f}%")

# Step 3: Check trend
trend = analysis.scoring_trend(player)
print(f"\n📈 Trend: {trend['direction'].upper()}")
print(f"  Recent avg: {trend['recent_avg']:.1f} PPG")
print(f"  Overall avg: {trend['average']:.1f} PPG")

# Step 4: Visualize
viz.bar_chart(
    player,
    x='date',
    y='points',
    title=f"{PLAYER_NAME} - Points Per Game"
)
```

**When to use:** Player analysis, finding trends, preparing for content creation.

---

### Workflow 3: Compare Last Game to Season Average

**Goal:** See if a player's last game was above or below their average.

```python
from bulls import data, analysis

# Get player's recent games
player = data.get_player_games("Coby White", last_n=20)
avgs = analysis.season_averages(player)

# Get last game stats
last_game = player.iloc[0]
game_stats = {
    'points': last_game['points'],
    'rebounds': last_game['rebounds'],
    'assists': last_game['assists']
}

# Compare
diff = analysis.vs_average(game_stats, avgs)

print(f"Last game vs season average:")
print(f"  Points: {diff['points']:+.1f}")
print(f"  Rebounds: {diff['rebounds']:+.1f}")
print(f"  Assists: {diff['assists']:+.1f}")
```

**When to use:** Post-game analysis, identifying standout performances.

---

### Workflow 4: Create Multiple Visualizations

**Goal:** Create different types of charts to explore data from multiple angles.

```python
from bulls import data, viz

# Get player data
player = data.get_player_games("Coby White", last_n=15)

# Create different visualizations
viz.bar_chart(player, x='date', y='points', title="Points Per Game")
viz.line_chart(player, x='date', y='points', title="Scoring Trend")
viz.scatter_plot(player, x='points', y='assists', title="Points vs Assists")
```

**When to use:** When you want to explore data from different perspectives.

---

### Workflow 5: Explore Team Performance Trends

**Goal:** See how the team has been performing recently.

```python
from bulls import data, viz

# Get recent games
games = data.get_games(last_n=10)

# Win/loss chart
viz.win_loss_chart(
    games,
    x='GAME_DATE',
    y='PTS',
    result_col='WL',
    title="Bulls Scoring by Game (Last 10)"
)

# Calculate win rate
wins = (games['WL'] == 'W').sum()
losses = (games['WL'] == 'L').sum()
print(f"Last 10 games: {wins}W - {losses}L")
print(f"Average points: {games['PTS'].mean():.1f}")
```

**When to use:** Team analysis, understanding recent form.

---

### Workflow 6: Find Interesting Patterns

**Goal:** Discover unique insights in the data.

```python
from bulls import data, analysis, viz

# Get player data
player = data.get_player_games("Coby White", last_n=20)

# Look for correlations
viz.scatter_plot(
    player,
    x='points',
    y='assists',
    title="Points vs Assists"
)

# Check home vs away (if you add that analysis)
# Look for outliers
# Compare to league averages
# Find clutch performances
```

**When to use:** Deep exploration, finding content ideas, data discovery.

---

## Tips & Best Practices

### 1. Start with the Notebook

The `notebooks/explore.ipynb` file is your best starting point. It has:
- Pre-written cells for common tasks
- Examples you can modify
- A logical workflow from data → analysis → visualization

### 2. Understand the Data Flow

```
NBA API → bulls.data → pandas DataFrame
                ↓
         bulls.analysis → dict/DataFrame
                ↓
         bulls.viz → charts/graphics
```

- **Data functions** return DataFrames or dicts
- **Analysis functions** take DataFrames, return dicts or DataFrames
- **Viz functions** take DataFrames, create visualizations

### 3. Use Meaningful Variable Names

```python
# Good
coby_games = data.get_player_games("Coby White", last_n=15)
coby_avgs = analysis.season_averages(coby_games)

# Less clear
df = data.get_player_games("Coby White", last_n=15)
a = analysis.season_averages(df)
```

### 4. Check for Empty Data

Some functions may return empty DataFrames. Always check:

```python
player = data.get_player_games("Player Name", last_n=10)

if not player.empty:
    avgs = analysis.season_averages(player)
    print(avgs)
else:
    print("No games found for this player")
```

### 5. Save Your Work

When creating visualizations, save them:

```python
viz.bar_chart(
    data,
    x='date',
    y='points',
    title="My Chart",
    save_path="output/my_chart.png"  # Always save!
)
```

### 6. Combine Functions for Power

Chain functions together:

```python
# Get data
game = data.get_latest_game()
box = data.get_box_score(game['game_id'])

# Analyze
top = analysis.top_performers(box)

# Visualize
player = data.get_player_games(top[0]['name'], last_n=10)
viz.bar_chart(player, x='date', y='points')
```

### 7. Experiment and Iterate

- Try different players
- Change `last_n` values
- Modify chart titles and colors
- Combine different analyses

### 8. Ask Questions

The workspace is designed for exploration. Ask:
- "How has player X been performing?"
- "What's the trend?"
- "Can I see that as a chart?"
- "What's interesting about this data?"

### 9. Use the Right Tool for the Job

- **Quick questions:** Use Python scripts or chat
- **Deep exploration:** Use Jupyter notebook
- **Automation:** Use Python scripts
- **Learning:** Use notebook with examples

### 10. Respect API Rate Limits

The NBA API has rate limits. The workspace includes delays, but:
- Don't make excessive rapid calls
- Be patient with `get_player_games()` (it makes many API calls)
- If you get timeouts, wait and try again

---

## Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'bulls'`

**Solution:**
- Make sure you're in the project root directory
- Activate the virtual environment: `source venv/bin/activate`
- If using a notebook, make sure the first cell adds the parent directory to the path

### Problem: API calls are timing out

**Solution:**
- The NBA API may be temporarily unavailable
- Wait a few minutes and try again
- Check your internet connection
- The workspace includes delays between calls - this is intentional

### Problem: Empty DataFrame returned

**Solution:**
- Check if the season is correct (default is 2025-26)
- Verify player name spelling (case-insensitive, but spelling must be correct)
- Some players may not have played in recent games
- Check if games exist for the specified season

### Problem: Charts not displaying in notebook

**Solution:**
- Make sure you have `%matplotlib inline` in your notebook
- For Jupyter: `%matplotlib inline`
- For JupyterLab: `%matplotlib widget` or `%matplotlib inline`
- Try `plt.show()` after creating the chart


### Problem: Tests are failing

**Solution:**
- Make sure virtual environment is activated
- Run: `pip install -r requirements.txt`
- Use the venv's Python: `venv/bin/python -m pytest tests/ -v`
- Don't use system Python for tests

### Problem: Player not found

**Solution:**
- Check spelling of player name
- Use full name (e.g., "Coby White" not "Coby")
- Some players may have different name formats in the API
- Try searching box scores to find the exact name format

### Problem: Can't save files

**Solution:**
- Make sure `output/` directory exists (it should be created automatically)
- Check file permissions
- Use relative paths like `"output/my_file.png"` or absolute paths

### Problem: Import errors in notebook

**Solution:**
- Make sure the first cell in your notebook includes:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path().absolute().parent))
  ```
- This adds the parent directory to Python's path so it can find the `bulls` module

---

## Next Steps

Now that you understand how to use the workspace:

1. **Start exploring:** Open `notebooks/explore.ipynb` and run the cells
2. **Try different players:** Change `PLAYER_NAME` and see different data
3. **Experiment with visualizations:** Modify chart parameters, try different chart types
4. **Find insights:** Look for interesting patterns, trends, and stories
5. **Create visualizations:** When you find something interesting, create charts to visualize it
6. **Iterate:** Use the workspace regularly and add features as needed

Remember: This is a collaborative tool. You explore, ask questions, and create. The workspace provides the tools to make it easy.

---

## Additional Resources

- **README.md**: Quick start and project overview
- **docs/PRD.md**: Product requirements and vision
- **docs/SPEC.md**: Technical specification and implementation details
- **notebooks/explore.ipynb**: Interactive exploration notebook
- **tests/**: Example usage in test files

---

**Happy exploring! 🏀📊**
