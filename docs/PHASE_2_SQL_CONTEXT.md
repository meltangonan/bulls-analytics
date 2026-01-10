# Phase 2 Context: Database & Data Pipeline

> **Purpose:** Detailed context for learning SQL and building a real data pipeline.
> **Philosophy:** Learn tools by using them together on real problems, not in isolation.
> **Last Updated:** January 9, 2026

---

## Current Environment Status ✅

| Component | Status | Details |
|-----------|--------|---------|
| **PostgreSQL** | ✅ Running | Postgres.app v18.1 |
| **psql CLI** | ✅ Working | Added to PATH |
| **Python packages** | ✅ Installed | sqlalchemy, psycopg2-binary |
| **Database** | ⏳ Needs creation | `bulls_analytics` database |

**Connection details:**
- Host: `localhost`
- Port: `5432`
- User: `postgres`
- Database: `bulls_analytics` (create this first!)

---

## Apply These Perspectives in Phase 2

**🎯 Product Manager Lens:**
- Why PostgreSQL? → Because it's what jobs require (career value)
- Why Postgres.app? → Native Mac app, same PostgreSQL, simpler setup
- Schema design = product decisions (what data matters?)
- Every query should answer: "What story does this tell for fans?"

**📊 Data Analyst Lens:**
- Validate data at every step (row counts, spot checks)
- Document data lineage (where did this number come from?)
- Question outliers—bug or real?
- Think about data freshness (when was this pulled?)

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

## Tools We're Using

| Tool | What It Is | Why We're Using It |
|------|------------|-------------------|
| **PostgreSQL** | Industry-standard database | What you'll use at most jobs |
| **Postgres.app** | Native Mac app for PostgreSQL | Simple setup, same PostgreSQL |
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
2. Postgres.app gives us real PostgreSQL with simple setup
3. Skills transfer directly to work
4. Same SQL syntax works everywhere

### Why Postgres.app instead of Docker?

Docker had compatibility issues on this machine. Postgres.app provides:
- ✅ Same PostgreSQL (production-grade)
- ✅ Native macOS app (no compatibility issues)
- ✅ One-click start/stop
- ✅ Same learning outcomes

**No learning is lost** — SQL is SQL, and SQLAlchemy connects the same way.

---

## The 6-Step Framework

This is your repeatable workflow for ANY data project:

### Step 1: Acquire Data
- Source: NBA API (already connected!)
- What: Game results, player stats

### Step 2: Local Database Setup
- Run PostgreSQL locally (Postgres.app)
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

1. **Explain** what PostgreSQL is and why it's industry-standard
2. **Run** a PostgreSQL database locally (Postgres.app)
3. **Design** a database schema with proper relationships
4. **Write** Python ETL scripts that load data into PostgreSQL
5. **Query** the database with increasingly complex SQL
6. **Connect** Jupyter notebooks to the database for analysis

---

## Recommended Order of Work

### Part A: Environment Setup ✅ COMPLETE
1. ~~Install Docker Desktop~~ → Using Postgres.app instead
2. ~~Run PostgreSQL container~~ → Postgres.app running (🐘 in menu bar)
3. ✅ Connect to database (verified: `psql -U postgres` works)
4. ✅ Install Python packages (sqlalchemy, psycopg2-binary installed)

**Remaining:** Create `bulls_analytics` database

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

1. What is PostgreSQL and why is it industry-standard?
2. What makes a good database schema?
3. What is ETL and how does each step work?
4. How do foreign keys maintain data integrity?
5. When do you use SQL vs Python for data work?

---

## QA Checkpoints for Phase 2

**After Part A (Environment Setup):**
- [x] Is Postgres.app running? (🐘 in menu bar)
- [x] Can you run `psql -U postgres` and connect?
- [ ] Is `bulls_analytics` database created?
- [ ] Can you connect to the database from Python?
- [ ] Are connection details documented (not hardcoded)?

**After Part B (Database Design):**
- [ ] Do table relationships make sense? (draw it out)
- [ ] Are foreign keys correctly defined?
- [ ] Can you explain the schema to someone else?

**After Part C (ETL Pipeline):**
- [ ] Does the pipeline handle missing data gracefully?
- [ ] Are API rate limits respected?
- [ ] Can you re-run the pipeline without duplicating data?

**After Part D (SQL Mastery):**
- [ ] Do queries return expected results? (spot-check against source)
- [ ] Are complex queries documented/commented?
- [ ] Can you rebuild views if needed?

**End of Phase 2:**
- [ ] Update PROGRESS.md with learnings
- [ ] Update PRD.md with any scope changes
- [ ] Verify all file references in docs are still accurate
- [ ] Commit everything to GitHub with meaningful message

---

## Start Prompt for Phase 2

```
I'm continuing Phase 2 of my Bulls Analytics project.

Please read these files for context:
1. docs/QUICK_START.md (my working style + who I am)
2. AGENT_CONTEXT.md (full project context, interaction protocol)
3. docs/PHASE_2_SQL_CONTEXT.md (this phase's details)
4. DATA_DICTIONARY.md (available NBA data)

Current status:
- Phase 1 ✅ complete (API connection, data exploration)
- Part A ✅ mostly complete:
  - Postgres.app installed and running (🐘 in menu bar)
  - psql CLI works (`psql -U postgres`)
  - Python packages installed (sqlalchemy, psycopg2-binary)
  - ⏳ NEED TO: Create `bulls_analytics` database (forgot semicolon last time!)

I'm a Modern AI PM—non-technical background, AI-first. I want to:
- Learn the real workflow: PostgreSQL, SQLAlchemy, ETL
- Understand end-to-end data pipeline
- Build something portfolio-ready

Let's:
1. Create the bulls_analytics database
2. Then move to Part B: Database Design (schema, tables, relationships)

Remember: teach me step-by-step, I run commands myself, challenge me constructively.
```
