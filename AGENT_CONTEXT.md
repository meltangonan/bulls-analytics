# Agent Context - Bulls Analytics Project

> **Purpose:** Paste this into a new AI chat to quickly onboard a new agent on this project.
> **Last Updated:** January 6, 2026

---

## How to Use This File

When starting a new chat (on a new computer or new session), paste this entire file to give the agent context about:
1. What this project is
2. How we work together
3. Where we left off
4. Key decisions already made

---

## Project Overview

**What:** An Instagram page for data-driven Chicago Bulls analysis and visualizations.

**Goal:** Build a portfolio piece while learning SQL, Python, data analysis, and visualization.

**Target Audience:** Casual Bulls fans who want to understand the team better through data.

**MVP:** Post-game recaps with clean, minimal visualizations.

---

## Working Style & Preferences

The human on this project prefers:

1. **Learning, not just building** - Explain concepts before implementing. Don't just write code—teach why.

2. **Step-by-step pace** - Not too slow (boring), not too fast (overwhelming). A few steps at a time is good.

3. **Hands-on** - They want to run commands themselves, not have everything done automatically. Guide, don't do everything.

4. **PM perspective** - They think like a product manager. Always tie technical work back to "so what?" and user value.

5. **Ask before assuming** - Check in on decisions rather than making them unilaterally.

6. **Document everything** - Keep PRD, PROGRESS.md, and other docs updated as we go.

---

## Tech Stack

| Tool | Purpose | Notes |
|------|---------|-------|
| Python 3.11+ | Core language | Using venv for isolation |
| nba_api | NBA stats API | Use V3 endpoints (V2 deprecated) |
| pandas | Data manipulation | |
| SQLite | Database | Phase 2 |
| matplotlib/seaborn | Visualization | Phase 3 |
| Jupyter notebooks | Exploration | Using .ipynb in Cursor |

---

## Key Technical Decisions Made

1. **NBA API V3** - Must use V3 endpoints (boxscoretraditionalv3, etc.) for 2025-26 season. V2 is deprecated.

2. **Column naming** - V3 uses camelCase (e.g., `teamId`, `firstName`), not SCREAMING_SNAKE_CASE.

3. **Bulls Team ID** - `1610612741`

4. **Season format** - `'2025-26'` (year start - year end)

5. **Season type filter** - Use `season_type_nullable='Regular Season'` to exclude preseason.

6. **4 box score endpoints** available:
   - `boxscoretraditionalv3` - basic stats
   - `boxscoreadvancedv3` - efficiency metrics (usage rate, true shooting, etc.)
   - `boxscoremiscv3` - paint points, fast break points, etc.
   - `boxscorescoringv3` - shot distribution, assisted %

---

## Project Structure

```
bulls-analytics/
├── PRD.md                 # Product requirements (READ THIS FIRST)
├── DATA_DICTIONARY.md     # All NBA stats explained
├── PROGRESS.md            # Learning journal (update each session)
├── AGENT_CONTEXT.md       # This file
├── README.md              # GitHub intro
├── explore.ipynb          # Data exploration notebook
├── requirements.txt       # Python dependencies
├── .gitignore
├── data/                  # Database files (Phase 2)
├── scripts/               # Automation scripts (Phase 2)
├── queries/               # SQL templates (Phase 2)
├── visualizations/        # Chart code (Phase 3)
└── output/                # Generated images (Phase 3)
```

---

## Current Status

**Phase 1: Foundation** ✅ COMPLETE
- Project structure set up
- Virtual environment configured
- NBA API connected
- Data exploration done
- Documentation complete
- Pushed to GitHub

**Phase 2: Database & SQL** ⏳ UP NEXT
- Create SQLite database
- Design tables
- Write SQL queries
- Learn JOINs, GROUP BY, aggregations

**Phase 3: Visualization** 🔜 FUTURE
- Create post-game visualization template
- Establish Bulls brand style
- Generate first real graphic

**Phase 4: Launch** 🔜 FUTURE
- Create Instagram account
- First real post

---

## Questions Already Answered

Q: Why virtual environments?
A: Isolates project dependencies. Each project has its own "kitchen" with its own ingredients.

Q: Why not just use Excel?
A: Databases scale better, can be queried with SQL, and are reproducible.

Q: Why SQLite specifically?
A: Simple (file-based), no server needed, perfect for learning SQL.

Q: How do we get NBA data?
A: nba_api Python package connects to NBA's official stats API.

---

## How to Continue

1. Read `PRD.md` for product context
2. Read `PROGRESS.md` to see what was learned
3. Check `DATA_DICTIONARY.md` for available stats
4. Open `explore.ipynb` to see working code
5. Start where Phase 2 begins: creating the SQLite database

---

## Prompt to Start New Session

Copy and paste this to quickly continue:

```
I'm continuing work on my Bulls Analytics project. I've attached AGENT_CONTEXT.md which has all the background.

Current status: Phase 1 complete, starting Phase 2 (Database & SQL).

Please read the context file and let's continue where we left off. Remember: I prefer learning step-by-step, with explanations, and I want to be hands-on (run commands myself, not have you do everything).
```

