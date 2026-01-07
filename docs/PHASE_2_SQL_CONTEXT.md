# Phase 2 Context: Database & SQL

> **Purpose:** Detailed context for the SQL/Database phase. Paste to new agent when starting Phase 2.

---

## Phase 2 Goals

Learn SQL fundamentals while building a real database for Bulls analytics:
1. Create SQLite database
2. Design proper table schema
3. Write useful queries
4. Automate data fetching

---

## What We Have From Phase 1

### Data Available (via NBA API)
- Game metadata (date, opponent, score, W/L)
- Player box scores (traditional, advanced, misc, scoring)
- All columns documented in `DATA_DICTIONARY.md`

### Working Code
- `explore.ipynb` has working API calls
- Can fetch game list with `leaguegamefinder`
- Can fetch player stats with `boxscoretraditionalv3` etc.

---

## Planned Database Schema

```sql
-- Games table
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    game_date DATE,
    opponent TEXT,
    is_home BOOLEAN,
    bulls_score INTEGER,
    opponent_score INTEGER,
    result TEXT  -- 'W' or 'L'
);

-- Player game stats
CREATE TABLE player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT,
    player_id INTEGER,
    player_name TEXT,
    minutes INTEGER,
    points INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    -- ... more columns
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);
```

---

## SQL Concepts to Learn

| Concept | Use Case |
|---------|----------|
| SELECT, WHERE | Filter specific games/players |
| JOIN | Connect games table to player stats |
| GROUP BY | Aggregate stats (averages, totals) |
| ORDER BY | Rank players, sort by date |
| Aggregate functions | AVG(), SUM(), MAX(), COUNT() |
| Subqueries | Compare to league averages |

---

## Key Questions for This Phase

1. How do we design tables that work well together?
2. What's a foreign key and why does it matter?
3. How do we turn raw API data into structured database rows?
4. What queries will power our post-game recaps?

---

## Expected Outputs

- `data/bulls.db` - SQLite database file
- `scripts/fetch_games.py` - Fetch and store game data
- `scripts/fetch_player_stats.py` - Fetch and store player stats
- `queries/` - SQL query templates for analysis

---

## Start Prompt for Phase 2

```
I'm starting Phase 2 (Database & SQL) of my Bulls Analytics project.

Please read:
1. docs/QUICK_START.md (working style)
2. docs/PHASE_2_SQL_CONTEXT.md (this phase details)
3. DATA_DICTIONARY.md (available data)

I'm new to SQL. Please teach me step-by-step, explain concepts as we go, and let me run commands myself.

Let's start by creating the SQLite database and designing the tables.
```

