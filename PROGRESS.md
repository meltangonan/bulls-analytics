# Progress Log

A record of what I've learned and built on this project.

---

## Session 1 - January 6, 2026

### What I Did
- Created the PRD (Product Requirements Document)
- Set up project structure and folders
- Created Python virtual environment
- Installed packages (nba_api, pandas, matplotlib, seaborn)
- Connected to NBA API
- Explored 4 different box score endpoints
- Created data dictionary documenting all available stats
- Pushed to GitHub

### What I Learned

**Product/PM Skills:**
- How to write a PRD with problem statement, target audience, goals, and scope
- Importance of defining what's NOT in scope (non-goals)
- MVP thinking - focus on one thing first (post-game recaps)

**Technical Skills:**
- Virtual environments isolate project dependencies
- `requirements.txt` makes projects reproducible
- APIs are like waiters - you request data, they bring it back
- NBA API has multiple endpoints for different stat types:
  - `boxscoretraditionalv3` - basic stats
  - `boxscoreadvancedv3` - efficiency metrics
  - `boxscoremiscv3` - paint points, fast break, etc.
  - `boxscorescoringv3` - shot distribution
- API versions matter - V2 was deprecated, had to use V3
- Column naming conventions differ between API versions (camelCase vs SCREAMING_SNAKE_CASE)
- `.gitignore` keeps large/generated files out of GitHub

**Data Skills:**
- Always question your data (found 41 games when expected 36 - included preseason!)
- Filtering is important (season_type_nullable parameter)
- Combining data from multiple sources enriches analysis

### Key Files Created
- `PRD.md` - Product requirements
- `DATA_DICTIONARY.md` - Stats reference
- `test_viz.ipynb` - Exploration notebook (originally explore.ipynb)
- `requirements.txt` - Dependencies
- `.gitignore` - Git ignore rules

### Questions for Next Time
- How do I design database tables for this data?
- What SQL queries will I need for post-game recaps?
- How do I automate data fetching after each game?

### Next Steps (Phase 2 - Expanded Scope!)
**Upgraded from "learn SQL" to "build production-grade data pipeline"**

Part A: Environment Setup
- [ ] Install Docker Desktop
- [ ] Run PostgreSQL in Docker container
- [ ] Install SQLAlchemy + psycopg2

Part B: Database Design
- [ ] Create database schema (tables, foreign keys)
- [ ] Understand relationships and indexes

Part C: ETL Pipeline
- [ ] Write Python scripts: Extract → Transform → Load
- [ ] Automate game data fetching

Part D: SQL Mastery
- [ ] Basic queries → Aggregations → JOINs
- [ ] Create views for post-game analysis

---

## Template for Future Sessions

```markdown
## Session X - [Date]

### What I Did
- 

### What I Learned
- 

### Key Files Created/Modified
- 

### Questions/Blockers
- 

### Next Steps
- 

### End-of-Session QA ✓
- [ ] PROGRESS.md updated
- [ ] File references accurate across docs
- [ ] Changes committed to GitHub
- [ ] PRD updated if scope changed
```

---

## QA Lenses (Apply Every Session)

| Lens | Ask Yourself |
|------|--------------|
| **PM** | Does this serve the end goal (Instagram posts)? |
| **Data** | Is the data accurate? Did I validate it? |
| **Engineer** | Would this work on a fresh machine? |
| **Learner** | Did I document what I learned, not just what I did? |
| **Future Self** | Will I understand this in 3 months? |

