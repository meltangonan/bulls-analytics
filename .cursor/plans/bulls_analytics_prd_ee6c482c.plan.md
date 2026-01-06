---
name: Bulls Analytics PRD
overview: Product Requirements Document for a data-driven Chicago Bulls Instagram page targeting casual fans, with post-game recap content as the MVP.
todos:
  - id: phase1-setup
    content: "Phase 1: Set up project structure, virtual environment, and install dependencies"
    status: completed
  - id: phase1-api
    content: "Phase 1: Connect to NBA API and pull first Bulls game data"
    status: completed
    dependencies:
      - phase1-setup
  - id: phase2-database
    content: "Phase 2: Create SQLite database and design tables"
    status: pending
    dependencies:
      - phase1-api
  - id: phase2-sql
    content: "Phase 2: Write core SQL queries for post-game stats"
    status: pending
    dependencies:
      - phase2-database
  - id: phase3-viz
    content: "Phase 3: Create post-game visualization template"
    status: pending
    dependencies:
      - phase2-sql
  - id: phase4-launch
    content: "Phase 4: Create Instagram account and first real post"
    status: pending
    dependencies:
      - phase3-viz
---

# Product Requirements Document: Bulls Analytics Instagram

## Overview

**Product:** An Instagram page delivering data-driven analysis and visualizations for the Chicago Bulls.**One-liner:** "Making Bulls stats accessible and visual for fans who love the team but don't dive deep into numbers."---

## Problem Statement

### The Gap

Bulls fans consume content through traditional sports media and fan pages, but:

- Most fan pages focus on highlights and memes, not data
- Stats exist (ESPN, Basketball Reference) but aren't visual or engaging
- Raw numbers lack context—fans don't know if "18 points" is good or bad for that player
- Post-game analysis isn't timely or tailored to casual fans

### The Opportunity

Create timely, visual, contextual data content that helps casual fans understand what's actually happening with their team—without needing to be a stats nerd.---

## Target Audience

**Primary:** Casual Bulls fans

- Watch games regularly but don't track advanced stats
- Follow Bulls on social media
- Want to understand the team better without doing homework
- Appreciate visuals over walls of text

**Not targeting (for now):**

- Hardcore analytics people (they have their own sources)
- Fantasy-focused content consumers
- General NBA fans (Bulls-specific only)

---

## Goals & Success Metrics

### Primary Goal

**Build a portfolio piece** that demonstrates data analysis, SQL, Python, and visualization skills for career development.

### Secondary Goals

- Learn SQL through practical application
- Understand the end-to-end data pipeline
- Build a consistent content creation habit

### Success Metrics (1-month checkpoint)

| Metric | Target ||--------|--------|| Technical | Complete end-to-end pipeline (API to visualization) || Content | Create 5+ post-game recap graphics || Learning | Write 10+ SQL queries from scratch || Habit | Post after at least 10 Bulls games |---

## MVP Scope: Post-Game Recaps

### What's In (v1)

The MVP focuses on ONE content type done well: **Post-Game Recaps**A post-game recap answers: *"What happened in last night's game, told through data?"***Core components:**

1. Final score and win/loss
2. Top performer(s) with key stats
3. One "story" stat (e.g., "LaVine scored 30 for the 5th time this month")
4. Player performance vs. their season average
5. Clean, minimal visual design with Bulls branding

**Example post concept:**> **BULLS 118, HEAT 105**> Coby White: 28 PTS | 5 AST | 6/10 3PT> [Bar chart showing Coby vs his season average]> "Coby's 3rd game with 25+ points this month"

### What's Out (for now)

- Matchup previews (future)
- Season-long trend analysis (future)
- Shot charts / play-by-play (future)
- Advanced metrics (future)
- Video content
- Other teams

---

## Non-Goals

Explicitly NOT doing:| Non-Goal | Reason ||----------|--------|| Breaking news | Not competing with reporters; analysis, not scoops || Video highlights | Other pages do this; data viz is the differentiator || Hot takes/opinions | Data-driven means showing what happened, not arguing || Full NBA coverage | Bulls only keeps scope manageable and builds niche || Monetization | Learning is the ROI; no sponsors, no pressure |---

## Technical Approach (High Level)

### Data Source

- **NBA API** (via `nba_api` Python library)
- Free, comprehensive, includes box scores and player stats

### Storage

- **SQLite database**
- Simple, file-based, perfect for learning SQL
- Tables: games, player stats, team stats

### Analysis

- **SQL** for querying and aggregations
- **Python** for data manipulation when needed

### Visualization

- **matplotlib/seaborn** for chart generation
- Clean, minimal style
- Bulls red (#CE1141) and black (#000000) palette

### Workflow

```javascript
After each Bulls game:
1. Run script to fetch new game data
2. Data saves to SQLite database
3. Write/run SQL query to find the story
4. Generate visualization
5. Export and post to Instagram
```

---

## Timeline & Phases

### Phase 1: Foundation (Week 1)

- Set up project structure
- Create database
- Connect to NBA API
- Pull first data

### Phase 2: Data Pipeline (Week 2)

- Automate game data fetching
- Write core SQL queries
- Understand the data model

### Phase 3: Visualization (Week 3)

- Create post-game template
- Establish visual style
- Generate first graphic

### Phase 4: Launch Prep (Week 4)

- Create Instagram account
- Build 3-5 sample posts
- Refine workflow
- First real post!

---

## Open Questions (To Decide Later)

1. **Instagram handle** - What should the page be called?
2. **Posting time** - Morning after games? Same night?
3. **Caption style** - Stats only? Add commentary?