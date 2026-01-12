# Bulls Analytics — Exploration Question Bank & Visualization Ideas

**Purpose:** A MECE set of questions and chart ideas to guide exploration in the Bulls Analytics Workspace, with a bias toward insights that translate well into Instagram-ready posts.

---

## 0) How to use this document (repeatable workflow)

1. **Pick a scope:** *Team*, *player*, or *single-game story*
2. **Pick a time window:** *last game*, *last 5 / 10 / 15*, *season-to-date*
3. **Choose a “so-what” lens:** trend, split, outlier, comparison, or driver
4. **Define a baseline:** season average, last-10 average, or “in wins vs losses”
5. **Choose a chart:** bar / line / scatter / win-loss bar (supported today), then iterate

This mirrors a clean analytics loop: **question → data → chart → insight → post**.

---

## 1) What you can answer with the current workspace (v0.1)

### Team game logs
- Game-by-game team stats for the Bulls season  
- Fields typically include: date, matchup, W/L, points, plus/minus, and standard team box score stats

### Single-game Bulls box score
- Player-level box score for one game  
- Points, rebounds, assists, shooting (FG / 3P), minutes, etc.

### Player game-by-game time series
- Player’s last N games with points, rebounds, assists
- Shooting volume and efficiency (FG%, 3P%)

### Built-in analysis capabilities
- Season averages
- Vs-average deltas
- Basic trend detection
- Top performer identification

### Built-in visualization types
- Bar charts
- Line charts
- Scatter plots
- Comparison charts (grouped data)
- Win / loss bar charts

---

## 2) Question Bank (MECE)

### A) Team performance (macro)

#### A1. Results & trajectory — *what’s happening*
- What is the Bulls’ win rate over the last 5 / 10 / 15 games vs season-to-date?
- How is point differential (plus/minus) trending over time?
- Are recent results driven by blowouts or close games?
- Do the Bulls show momentum (streaks) or volatility (alternating W/L)?

**Good charts**
- Win/loss bar chart of points by game
- Line chart of plus/minus over last N games

---

#### A2. Offensive profile — *how they score*
- In wins vs losses, what changes most: points, FG%, 3P%, 3PA?
- Are the Bulls becoming more three-point-dependent over time?
- How strong is the relationship between 3P% and plus/minus?
- Do they have a consistent scoring floor?

**Good charts**
- Scatter: 3P% vs plus/minus
- Bar: points per game with average line

---

#### A3. Defense & “stops” (proxy metrics)
- In wins, do the Bulls generate more steals or blocks?
- Are defensive stats more predictive than shooting on certain nights?
- Are losses often associated with low defensive activity?

**Good charts**
- Comparison bars: steals / blocks in wins vs losses

---

#### A4. Rebounding & possession battle
- Do the Bulls win more often when they rebound better?
- Are losses correlated with low offensive rebounding?
- Are there “second-chance identity” games?

**Good charts**
- Scatter: rebounds vs plus/minus
- Split bars: average rebounds in wins vs losses

---

### B) Player performance (micro)

#### B1. Form & trend — *is a player heating up or cooling off?*
- Is the player trending up, down, or stable in points?
- Is the trend driven by minutes (role) or efficiency?
- How consistent is the player game-to-game?
- What are the best and worst multi-game stretches?

**Good charts**
- Bar: points by game with average line
- Line: FG% or 3P% over time

---

#### B2. Volume vs efficiency
- When scoring spikes, is it volume (shots) or efficiency?
- Does higher 3PA lead to higher points or just more variance?
- Are hot games driven by threes or overall FG%?

**Good charts**
- Scatter: points vs FGA (size by 3PA)
- Scatter: points vs 3PA

---

#### B3. Playmaking & role balance
- When scoring increases, do assists drop or rise?
- Which games show a balanced stat line (PTS + AST + REB)?
- Are there “connector games” with low scoring but high assists?

**Good charts**
- Scatter: points vs assists
- Bar: assists by game

---

#### B4. Outlier & story games
- What are the top games above a player’s recent average?
- What are the biggest efficiency outliers?
- Which games show unusually high workload (minutes)?
- What are the best all-around box score performances?

**Good charts**
- Ranked bars: top games by points above average
- Delta bars: game vs recent average

---

### C) Single-game deep dives (post-game content)

#### C1. “What won the game?”
- Who were the top 3 contributors?
- Was it a star-driven win or balanced scoring?
- Did defense or rebounding compensate for poor shooting?

**Good charts**
- Bar: points by player (top rotation)
- Scatter: points vs minutes

---

#### C2. Above / below average framing
- Who exceeded expectations the most?
- Who underperformed but still contributed to a win?

**Good charts**
- Side-by-side bars: last game vs average

---

### D) Comparisons & splits

#### D1. Player-to-player
- Who leads the team over the last 10 games in:
  - points, assists, rebounds
  - 3P makes, 3P%
  - minutes (workload)
- Are there clear role groupings?

**Good charts**
- Grouped bar charts
- Top-N leaderboards

---

#### D2. Contextual splits
- Home vs away
- Wins vs losses
- Close games vs non-close games

**Good charts**
- Two-bar split comparisons

---

### E) Drivers & “why” questions

#### E1. What correlates with winning?
- Which stats most strongly correlate with plus/minus?
- Are there threshold effects (e.g., shooting above X%)?
- Is shooting variance the primary swing factor?

**Good charts**
- Scatter with trend line
- Win% above vs below threshold

---

#### E2. Variance & stability
- Are the Bulls highly volatile in shooting?
- Are outcomes more consistent than performance?

**Good charts**
- Rolling standard deviation lines
- Distribution summaries (future)

---

## 3) Visualization menu

### A) Production-ready now
- Last N games scoring bars (team or player)
- Player trend lines (points, FG%, 3P%)
- Scatter relationships (points vs assists, 3P% vs plus/minus)
- Win vs loss split comparisons

---

### B) High-value next (small extensions)
- Rolling averages
- Outlier annotations
- Diverging bars (above/below average)
- Small multiples (same chart for multiple players)

---

### C) Advanced roadmap (future data)
- Shot charts / heatmaps
- Clutch performance
- Lineup on/off impact
- Opponent-adjusted metrics

---

## 4) Repeatable content series ideas

1. **Stat of the Night** — one chart + why it mattered
2. **Trend Watch** — weekly player trends
3. **What Drives Bulls Wins?** — one driver per post
4. **Role Watch** — minutes vs production
5. **Boom / Bust Meter** — consistency and variance

---

## 5) Low-friction first post ideas

### Option 1 — Team
- Question: Are recent Bulls wins offense-driven?
- Chart: win/loss bar of points (last 10 games)
- Insight: avg points in wins vs losses

### Option 2 — Player
- Question: Is Player X heating up due to volume or efficiency?
- Charts: points bar, FG% line, points vs FGA scatter

### Option 3 — Single game
- Question: Who actually won the game?
- Chart: points by player + one key supporting stat

---

## 6) Optional prioritization questions

1. Team-focused or player-focused early content?
2. Post-game cadence or weekly insights?
3. Clean single-metric visuals or richer multi-metric charts?
