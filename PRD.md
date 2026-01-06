# Product Requirements Document: Bulls Analytics Instagram

> **Last Updated:** January 6, 2026
> **Status:** Phase 1 Complete ✅ - Ready for Phase 2

## Overview

**Product:** An Instagram page delivering data-driven analysis and visualizations for the Chicago Bulls.

**One-liner:** "Making Bulls stats accessible and visual for fans who love the team but don't dive deep into numbers."

---

## Problem Statement

### The Gap
Bulls fans consume content through traditional sports media and fan pages, but:
- Most fan pages focus on highlights and memes, not data
- Stats exist (ESPN, Basketball Reference) but aren't visual or engaging
- Raw numbers lack context—fans don't know if "18 points" is good or bad for that player
- Post-game analysis isn't timely or tailored to casual fans

### The Opportunity
Create timely, visual, contextual data content that helps casual fans understand what's actually happening with their team—without needing to be a stats nerd.

---

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
| Metric | Target |
|--------|--------|
| Technical | Complete end-to-end pipeline (API → visualization) |
| Content | Create 5+ post-game recap graphics |
| Learning | Write 10+ SQL queries from scratch |
| Habit | Post after at least 10 Bulls games |

---

## MVP Scope: Post-Game Recaps

### What's In (v1)
The MVP focuses on ONE content type done well: **Post-Game Recaps**

A post-game recap answers: *"What happened in last night's game, told through data?"*

**Core components:**
1. Final score and win/loss
2. Top performer(s) with key stats
3. One "story" stat (e.g., "LaVine scored 30 for the 5th time this month")
4. Player performance vs. their season average
5. Clean, minimal visual design with Bulls branding

**Example post concept:**
> **BULLS 118, HEAT 105**
> Coby White: 28 PTS | 5 AST | 6/10 3PT
> [Bar chart showing Coby vs his season average]
> "Coby's 3rd game with 25+ points this month"

### What's Out (for now)
- Matchup previews (future)
- Season-long trend analysis (future)
- Shot charts / play-by-play (future)
- Advanced metrics (future)
- Video content
- Other teams

---

## Non-Goals

Explicitly NOT doing:
| Non-Goal | Reason |
|----------|--------|
| Breaking news | Not competing with reporters; analysis, not scoops |
| Video highlights | Other pages do this; data viz is the differentiator |
| Hot takes/opinions | Data-driven means showing what happened, not arguing |
| Full NBA coverage | Bulls only keeps scope manageable and builds niche |
| Monetization | Learning is the ROI; no sponsors, no pressure |

---

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
```
After each Bulls game:
1. Run script to fetch new game data
2. Data saves to SQLite database
3. Write/run SQL query to find the story
4. Generate visualization
5. Export and post to Instagram
```

---

## Timeline & Phases

### Phase 1: Foundation (Week 1) ✅ COMPLETE
- [x] Set up project structure
- [x] Create virtual environment
- [x] Install dependencies
- [x] Connect to NBA API
- [x] Pull first data
- [x] Explore available stats (traditional, advanced, misc, scoring)

### Phase 2: Data Pipeline (Week 2) ← CURRENT
- [ ] Create SQLite database
- [ ] Design tables
- [ ] Automate game data fetching
- [ ] Write core SQL queries

### Phase 3: Visualization (Week 3)
- [ ] Create post-game template
- [ ] Establish visual style
- [ ] Generate first graphic

### Phase 4: Launch Prep (Week 4)
- [ ] Create Instagram account
- [ ] Build 3-5 sample posts
- [ ] Refine workflow
- [ ] First real post!

---

## Open Questions (To Decide Later)

1. **Instagram handle** - What should the page be called?
2. **Posting time** - Morning after games? Same night?
3. **Caption style** - Stats only? Add commentary?
4. **Stories vs Posts** - Which format for which content?

---

## Learnings & Discoveries

### Phase 1 Learnings
- NBA API has 4 box score endpoints with different stat types (traditional, advanced, misc, scoring)
- V2 endpoints deprecated for 2025-26 season - must use V3
- V3 uses camelCase column names (e.g., `teamId` not `TEAM_ID`)
- Bulls Team ID: `1610612741`
- Rich advanced stats available: usage rate, true shooting %, net rating, etc.
- See `DATA_DICTIONARY.md` for full reference

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-06 | Phase 1 complete, added DATA_DICTIONARY.md |
| 2026-01-05 | Initial PRD created |

