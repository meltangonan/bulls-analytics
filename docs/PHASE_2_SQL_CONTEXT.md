# Phase 2 Context: Database & Data Pipeline

> **Purpose:** Detailed context for learning SQL and building a real data pipeline.
> **Philosophy:** Learn tools by using them together on real problems, not in isolation.

---

## Phase 2 Vision

We're not just "learning SQL"—we're building a **real-world data pipeline** like you'd use at an actual job:

```
┌──────────┐    ┌───────────┐    ┌──────────────┐    ┌─────────┐    ┌─────────────┐
│  NBA API │ →  │  Python   │ →  │  PostgreSQL  │ →  │   SQL   │ →  │  Analysis   │
│  (Source)│    │  (ETL)    │    │  (Database)  │    │ (Query) │    │  (Jupyter)  │
└──────────┘    └───────────┘    └──────────────┘    └─────────┘    └─────────────┘
```

This is the **exact workflow** data analysts and engineers use every day.

---

## Tools We're Adding

| Tool | What It Is | Why We're Using It |
|------|------------|-------------------|
| **PostgreSQL** | Industry-standard database | What you'll use at most jobs |
| **Docker** | Container to run Postgres locally | Clean, reproducible setup |
| **SQLAlchemy** | Python library to talk to databases | Industry standard ORM |
| **psycopg2** | PostgreSQL adapter for Python | Connects Python ↔ Postgres |

### Why PostgreSQL over SQLite?

| SQLite | PostgreSQL |
|--------|------------|
| Good for learning basics | What companies actually use |
| File-based, no setup | Client-server architecture |
| Limited features | Full-featured (joins, indexes, etc.) |
| Can't handle concurrency | Production-ready |

**We're using PostgreSQL** because:
1. It's what you'll see on job descriptions
2. It runs in Docker (clean local setup)
3. Skills transfer directly to work
4. Same SQL syntax works everywhere

---

## The 6-Step Framework

This is your repeatable workflow for ANY data project:

### Step 1: Acquire Data
- Source: NBA API (already connected!)
- What: Game results, player stats

### Step 2: Local Database Setup
- Spin up PostgreSQL in Docker
- Create database and tables
- Design proper schema (relationships, keys)

### Step 3: Ingest Data (ETL)
- **E**xtract: Pull from NBA API
- **T**ransform: Clean, format, validate
- **L**oad: Insert into PostgreSQL

### Step 4: Transform & Model
- Write SQL queries to reshape data
- Calculate aggregations, averages, trends
- Create views for common analyses

### Step 5: Analyze & Visualize
- Query database from Jupyter
- Use pandas + matplotlib for insights
- Build toward post-game graphics

### Step 6: Document & Version Control
- Git commits with meaningful messages
- README explaining the project
- Update PROGRESS.md each session

---

## What We Have From Phase 1

### Data Available (via NBA API)
- Game metadata (date, opponent, score, W/L)
- Player box scores (traditional, advanced, misc, scoring)
- All columns documented in `DATA_DICTIONARY.md`

### Working Code
- `explore.ipynb` has working API calls (note: may have been renamed to test_viz.ipynb)
- Can fetch game list with `leaguegamefinder`
- Can fetch player stats with `boxscoretraditionalv3` etc.

### Key Technical Decisions
- Bulls Team ID: `1610612741`
- Season format: `'2025-26'`
- Use V3 API endpoints (V2 deprecated)
- Column names are camelCase in V3

---

## Database Schema (Planned)

```sql
-- Teams reference table
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY,
    full_name TEXT,
    abbreviation TEXT,
    city TEXT
);

-- Games table
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    game_date DATE,
    home_team_id INTEGER REFERENCES teams(team_id),
    away_team_id INTEGER REFERENCES teams(team_id),
    home_score INTEGER,
    away_score INTEGER,
    season TEXT
);

-- Player game stats (normalized)
CREATE TABLE player_game_stats (
    id SERIAL PRIMARY KEY,
    game_id TEXT REFERENCES games(game_id),
    player_id INTEGER,
    player_name TEXT,
    team_id INTEGER REFERENCES teams(team_id),
    -- Traditional stats
    minutes INTEGER,
    points INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    -- Shooting
    fgm INTEGER,
    fga INTEGER,
    fg3m INTEGER,
    fg3a INTEGER,
    ftm INTEGER,
    fta INTEGER,
    -- Advanced
    plus_minus INTEGER,
    offensive_rating REAL,
    defensive_rating REAL,
    usage_pct REAL,
    true_shooting_pct REAL
);

-- Indexes for common queries
CREATE INDEX idx_player_stats_game ON player_game_stats(game_id);
CREATE INDEX idx_player_stats_player ON player_game_stats(player_id);
CREATE INDEX idx_games_date ON games(game_date);
```

---

## SQL Concepts to Learn (In Order)

| Concept | What It Does | Example Use |
|---------|--------------|-------------|
| SELECT, WHERE | Filter data | "Show me Coby White's stats" |
| ORDER BY, LIMIT | Sort and cap results | "Top 5 scoring games" |
| Aggregate (AVG, SUM, COUNT) | Summarize data | "Average points this season" |
| GROUP BY | Aggregate by category | "Points per game by player" |
| JOIN | Connect tables | "Games + player stats together" |
| Subqueries | Queries inside queries | "Compare to season average" |
| Window functions | Advanced analytics | "Running totals, rankings" |
| Views | Saved queries | "player_season_averages view" |

---

## Learning Goals for Phase 2

By the end of Phase 2, you should be able to:

1. **Explain** what Docker is and why it's useful
2. **Run** a PostgreSQL database locally via Docker
3. **Design** a database schema with proper relationships
4. **Write** Python ETL scripts that load data into PostgreSQL
5. **Query** the database with increasingly complex SQL
6. **Connect** Jupyter notebooks to the database for analysis

---

## Recommended Order of Work

### Part A: Environment Setup
1. Install Docker Desktop
2. Run PostgreSQL container
3. Connect to database (verify it works)
4. Install Python packages (SQLAlchemy, psycopg2)

### Part B: Database Design
5. Create database schema (tables, keys)
6. Understand relationships (foreign keys)
7. Learn about indexes

### Part C: ETL Pipeline
8. Write script to fetch games from API
9. Write script to transform data
10. Write script to load into PostgreSQL
11. Test end-to-end pipeline

### Part D: SQL Mastery
12. Basic SELECT queries
13. Aggregations and GROUP BY
14. JOINs across tables
15. Complex queries for post-game recaps
16. Create views for common analyses

---

## Key Questions for This Phase

1. What is Docker and why do data engineers use it?
2. What makes a good database schema?
3. What is ETL and how does each step work?
4. How do foreign keys maintain data integrity?
5. When do you use SQL vs Python for data work?

---

## Start Prompt for Phase 2

```
I'm starting Phase 2 of my Bulls Analytics project.

Please read these files for context:
1. docs/QUICK_START.md (my working style)
2. docs/PHASE_2_SQL_CONTEXT.md (this phase's details)
3. DATA_DICTIONARY.md (available NBA data)

Key context:
- Phase 1 complete (API connection, data exploration)
- I want to learn the REAL workflow: Docker, PostgreSQL, SQLAlchemy, ETL
- Not just "learn SQL"—I want end-to-end data pipeline experience
- I'm new to these tools. Teach me step-by-step.
- I run commands myself—guide me, don't do everything for me.

Let's start with Part A: setting up Docker and PostgreSQL locally.
```
