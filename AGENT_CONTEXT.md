# Agent Context - Bulls Analytics Project

> **Purpose:** Paste this into a new AI chat to quickly onboard a new agent on this project.
> **Last Updated:** January 7, 2026

---

## Context File System

We have a tiered context system for onboarding new agents:

| File | Use When |
|------|----------|
| `docs/QUICK_START.md` | New chat, need fast context (~30 lines) |
| `AGENT_CONTEXT.md` | Full project understanding (this file) |
| `docs/PHASE_X_CONTEXT.md` | Starting a specific phase |

**Recommended workflow for new chats:**
1. Paste `QUICK_START.md` first
2. If agent needs more, paste `AGENT_CONTEXT.md`
3. For phase-specific work, include that phase's context file

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

7. **QA mindset always** - Check work from multiple lenses (see below).

---

## Quality Standards (Apply Throughout)

**Always think from multiple perspectives:**

| Lens | Key Questions |
|------|---------------|
| **PM** | Does this serve the user? Is scope clear? What's the "so what"? |
| **Data Analyst** | Is the data accurate? Are sources documented? Any edge cases? |
| **Engineer** | Is it reproducible? Are file references correct? Will it work on another machine? |
| **Professor** | Is the learning progression logical? Are concepts explained before used? |
| **Future Self** | Will I understand this in 3 months? Is context preserved? |

**Before finishing any session:**
- [ ] Are all file references accurate? (no broken links)
- [ ] Is the tech stack consistent across docs?
- [ ] Are dates updated where needed?
- [ ] Does PROGRESS.md reflect what was learned?
- [ ] Would a new agent understand the current state?

**When making changes:**
- Update related docs (PRD, PROGRESS, etc.) in the same session
- Verify code examples still work after API/library changes
- Check that "Questions Already Answered" stays current

---

## Tech Stack

| Tool | Purpose | Notes |
|------|---------|-------|
| Python 3.11+ | Core language | Using venv for isolation |
| nba_api | NBA stats API | Use V3 endpoints (V2 deprecated) |
| pandas | Data manipulation | |
| **Docker** | Container runtime | Runs PostgreSQL locally |
| **PostgreSQL** | Database | Industry standard (Phase 2) |
| **SQLAlchemy** | Python ORM | Connects Python ↔ Database |
| **psycopg2** | PostgreSQL adapter | PostgreSQL driver for Python |
| matplotlib/seaborn | Visualization | Phase 3 |
| Jupyter notebooks | Exploration | Using .ipynb in Cursor |
| Git/GitHub | Version control | Already set up |

### Why This Stack?
We're building a **production-grade data pipeline**, not just a learning exercise:
- PostgreSQL over SQLite = what real jobs use
- Docker = industry-standard for local development
- SQLAlchemy = how Python talks to databases professionally
- ETL pattern = Extract → Transform → Load (core data engineering)

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
├── AGENT_CONTEXT.md       # This file (full context)
├── README.md              # GitHub intro
├── test_viz.ipynb         # Data exploration notebook
├── requirements.txt       # Python dependencies
├── .gitignore
├── docs/                  # Context files for new agents
│   ├── QUICK_START.md     # Fast onboarding (~30 lines)
│   └── PHASE_X_CONTEXT.md # Phase-specific deep dives
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

**Phase 2: Database & Data Pipeline** ⏳ UP NEXT
*Expanded scope: Production-grade workflow*
- Part A: Docker + PostgreSQL setup
- Part B: Database design (schema, relationships)
- Part C: ETL pipeline (Python scripts)
- Part D: SQL mastery (queries, joins, views)
- See `docs/PHASE_2_SQL_CONTEXT.md` for full details

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

Q: Why PostgreSQL over SQLite?
A: PostgreSQL is what real companies use. Running it in Docker gives production-grade experience.

Q: How do we get NBA data?
A: nba_api Python package connects to NBA's official stats API.

---

## How to Continue

1. Read `PRD.md` for product context
2. Read `PROGRESS.md` to see what was learned
3. Check `DATA_DICTIONARY.md` for available stats
4. Open `test_viz.ipynb` to see working code
5. Start Phase 2: Docker + PostgreSQL setup

---

## When to Start a New Chat/Agent

**Start a new chat when:**
- Starting a new phase (Phase 2, 3, 4)
- Context is above ~70% (things start getting forgotten)
- Switching focus (e.g., debugging vs. learning)
- Working on a different computer

**Keep current chat when:**
- Wrapping up current phase
- Quick follow-up questions
- Still have context room

## Prompt to Start New Session

**Quick version:**
```
[Paste docs/QUICK_START.md]
Continuing from Phase X. Let's go!
```

**Full version:**
```
I'm continuing work on my Bulls Analytics project. Please read these files for context:
1. docs/QUICK_START.md (working style)
2. AGENT_CONTEXT.md (full project context)
3. docs/PHASE_2_SQL_CONTEXT.md (current phase)

Remember: I prefer learning step-by-step, with explanations, and I want to be hands-on (run commands myself).
```

