# Product Requirements Document: Bulls Analytics Workspace

> **Document Owner:** User  
> **Last Updated:** January 11, 2026  
> **Status:** v0.1 - Initial Direction  
> **Document Type:** Living document - will evolve with the project

---

## 1. What This Is

### Vision
A **collaborative analysis workspace** for exploring Chicago Bulls data and creating unique, insightful visualizations - with AI as a thought partner.

### One-Liner
"Explore Bulls data with AI, find interesting stories, craft visualizations together."

### What It's NOT
- ❌ An auto-generation tool that spits out graphics
- ❌ A fire-and-forget CLI command
- ❌ Just reformatting box scores into pretty pictures

### The Key Insight
The **process** of exploring data and finding insights is as valuable as the **output** (visualizations). The visualization emerges from collaborative exploration, not automation.

---

## 2. Why This Exists

### Goals

| Goal | Description |
|------|-------------|
| **Portfolio Piece** | Demonstrate skills in data analysis, visualization, product management, and software engineering - from a PM/AI-builder perspective |
| **Create Content** | Produce unique Bulls analytics content and visualizations |
| **Explore Interests** | Figure out what I enjoy by doing it - data, basketball, creating, building software |
| **Learn Software Engineering** | Understand foundational concepts and first principles of how software actually works - not every line of code, but the concepts that make it tick |
| **Learn Best Practices** | Experience the end-to-end lifecycle of building real-world software: planning, building, testing, iterating, shipping |
| **Prove AI-Driven Building Works** | Demonstrate that a non-technical PM can successfully leverage AI to build and ship real, functional software |

### The AI-Driven Builder Approach

This project is explicitly about **building with AI**, not despite it:

| Principle | What It Means |
|-----------|---------------|
| **AI as Collaborator** | AI (Cursor) isn't just a tool - it's a thought partner in both coding and analysis |
| **Concepts Over Syntax** | Focus on understanding *why* code works, not memorizing *how* to write every line |
| **Ship Real Software** | The goal isn't to "learn to code" - it's to build something real that works |
| **PM-Led Development** | Drive the product vision, requirements, and decisions; AI handles implementation details |
| **Always Be Testing** | Good engineers test their code - this is a core practice, not an afterthought |

### Skills Demonstrated

**Software Engineering & Development:**
- Understanding software architecture and how systems fit together
- Writing and maintaining tested, working code (with AI assistance)
- Following the software development lifecycle end-to-end
- Applying engineering best practices: version control, testing, documentation

**Data & Analytics:**
- Fetching, cleaning, analyzing NBA data
- Creating compelling, branded visualizations
- Finding insights and telling stories with data

**Product Management:**
- Defining problems and writing clear requirements (PRD, SPEC)
- Scoping solutions and making tradeoffs
- Iterating based on what's learned
- Shipping - actually getting things done

**AI-Augmented Development:**
- Effectively prompting and collaborating with AI coding assistants
- Knowing when to trust AI output vs. when to dig deeper
- Building real software without being a traditional "developer"

### Audience

| Who | Role |
|-----|------|
| **Me** | Primary user - exploring data, creating content, learning software engineering |
| **Bulls Fans** | Audience for the analytics content I create |
| **AI (Cursor)** | Collaborator - thought partner for both coding and analysis |
| **Future Employers/Portfolio Viewers** | See evidence of PM who can ship real software with AI |

---

## 3. How It Works

### The Workflow

This is **not** a tool you run and get output. It's a **collaborative process**:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. EXPLORE                                                     │
│     "What happened in last night's Bulls game?"                 │
│     "How has Coby White been shooting lately?"                  │
│     "Are the Bulls better at home or away?"                     │
│                                                                 │
│                          ↓                                      │
│                                                                 │
│  2. DISCUSS                                                     │
│     AI fetches data, surfaces interesting patterns              │
│     You ask follow-up questions                                 │
│     Together, you find a unique angle                           │
│                                                                 │
│                          ↓                                      │
│                                                                 │
│  3. VISUALIZE                                                   │
│     "Can we see that as a chart?"                               │
│     "What if we compared it to league average?"                 │
│     "Let's highlight the outliers"                              │
│     Iterate together until it looks right                       │
│                                                                 │
│                          ↓                                      │
│                                                                 │
│  4. POLISH (when ready)                                         │
│     "Create a polished visualization"                            │
│     Add Bulls branding, proper dimensions                       │
│     Export final graphic                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Example Session

```
You: "Pull up last night's Bulls game"

AI:  "Bulls beat the Heat 118-105 at home.
      
      Top performers:
      - Coby White: 28 PTS, 5 REB, 7 AST
      - Nikola Vučević: 22 PTS, 12 REB
      - Matas Buzelis: 15 PTS, 4 STL
      
      Want me to dig deeper into anything?"

You: "Anything interesting beyond the basic stats?"

AI:  "A few things stand out:
      
      1. Coby had 18 of his 28 points in the 4th quarter
      2. Bulls shot 48% from three (season avg is 35%)
      3. Buzelis had a career-high 4 steals
      4. This was the Bulls' 5th straight home win"

You: "The Coby 4th quarter thing is interesting. What's his 
      clutch scoring been like this season?"

AI:  [fetches data]
      "Over the last 15 games, Coby averages 8.3 points in Q4.
       Last night's 18 was his season high.
       
       He's scored 10+ in Q4 only 4 times this season.
       Bulls are 4-0 in those games."

You: "That's a great stat. Can we visualize his Q4 scoring 
      over the last 15 games? Bar chart maybe?"

AI:  [creates chart]
      "Here's a bar chart showing Q4 points per game.
       Last night clearly stands out."

You: "Can we add a line showing his Q4 average?"

AI:  [updates chart]

You: "Nice. Let's also show the win/loss for each game - 
      maybe color the bars green for wins, red for losses?"

AI:  [updates chart]

You: "This is great. When I'm ready, can you make this 
      polished with Bulls colors and proper sizing?"

AI:  "Sure, just let me know. I can add:
       - Bulls red/black color scheme
       - Player headshot
       - Title and caption
       - Proper dimensions for sharing
       - Your handle for attribution"

You: "Let's do it."

AI:  [generates final graphic]
      "Saved to output/coby_clutch_q4.png"
```

### Two Interaction Modes

| Mode | Best For |
|------|----------|
| **Chat (Cursor)** | Quick exploration, brainstorming, generating visualizations |
| **Notebook (Jupyter)** | Deep analysis, experimenting with data, iterating on visuals |

Both use the same underlying codebase.

---

## 4. What We're Building

### The Codebase

A Python library that makes Bulls data accessible and visualizable:

```python
from bulls import data, analysis, viz

# Easy data access
game = data.get_latest_game()
games = data.get_games(last_n=20)
player = data.get_player_stats("Coby White", last_n=15)

# Analysis helpers
trends = analysis.scoring_trend(player)
comparison = analysis.vs_season_average(player, game)
quarters = analysis.quarter_breakdown(player)

# Visualization
viz.bar_chart(data, x="date", y="points")
viz.trend_line(data, metric="fg_pct")
viz.bar_chart(data, x="date", y="points")
```

### What the Codebase Provides

| Component | Purpose |
|-----------|---------|
| `bulls.data` | Fetch games, players, box scores from NBA API |
| `bulls.analysis` | Common calculations - averages, trends, comparisons |
| `bulls.viz` | Create charts and visualizations |

### What the Codebase Does NOT Do

- ❌ Automatically decide what's interesting
- ❌ Generate graphics without your input
- ❌ Replace your judgment about what makes good content

**You drive the exploration. The codebase supports you. AI helps along the way.**

---

## 5. Output: Visualizations

When you've found an interesting insight and are ready to share it, the end product is a visualization.

### Specifications

| Property | Value |
|----------|-------|
| Dimensions | 1080 x 1350 px (portrait) or 1080 x 1080 px (square) |
| Format | PNG |
| Style | Bulls branded - red (#CE1141), black (#000000), clean typography |

### Design Inspiration

These accounts create the kind of unique, analytical content we're aiming for:

| Account | Style |
|---------|-------|
| **@kirkgoldsberry** | Bold typography, player headshots, spatial analysis |
| **@bballuniversity** | Clean data tables, color-coded stats, multi-dimensional charts |
| **@datakabas** | Team logos, annotation callouts, league-wide comparisons |

### What Makes Good Content

- **Unique angle** - Not just "Coby scored 28" but "Coby's Q4 dominance"
- **Data-backed** - Real stats, properly sourced
- **Visual clarity** - Understandable in 3 seconds
- **Fan-relevant** - Something Bulls fans would care about
- **Fresh perspective** - The "data nerd" take that casual fans don't see

---

## 6. Iterative Approach

### Philosophy

We don't know exactly what this will become. That's okay.

| Principle | What It Means |
|-----------|---------------|
| **Start small** | Get something working, then evolve |
| **Learn by doing** | Preferences will become clearer through use |
| **Expect change** | What we want in week 1 ≠ week 4 |
| **Don't over-build** | Add capabilities as needed, not upfront |

### Phases

**Phase 0: Foundation**
- Get Bulls data flowing
- Basic exploration works
- *Then use it. See what's missing.*

**Phase 1: Analysis**
- Add analysis helpers as questions arise
- Trends, comparisons, breakdowns
- *Then use it. See what questions are hard to answer.*

**Phase 2: Visualization**
- Build viz capabilities as you have things to visualize
- Start simple, add polish over time
- *Then use it. Iterate on the visual style.*

**Ongoing: Evolve**
- The codebase grows with your needs
- Remove what doesn't work
- This document updates as we learn

---

## 7. Decisions Log

Track decisions so we can revisit them:

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2026-01-11 | Collaborative workspace, not auto-generation | Want to be involved in the creative process |
| 2026-01-11 | Start with data layer, add viz later | Need to explore before we know what to visualize |
| 2026-01-11 | Use Pillow for graphics (can revisit) | Simple, Python-native, good enough for v0.1 |
| 2026-01-11 | No database, NBA API is source of truth | Keeps it simple, data is always fresh |
| 2026-01-11 | Include testing from the start | Testing is what good engineers do - not optional |
| 2026-01-11 | Focus on concepts over syntax | Goal is understanding how software works, not memorizing code |
| 2026-01-11 | Frame as AI-driven PM building | Proves non-technical folks can ship real software with AI |

---

## 8. Open Questions

Things we'll figure out as we go:

| Question | Status |
|----------|--------|
| What types of analysis are most interesting? | Will discover through use |
| What visual style works best? | Will iterate |
| How much polish do visualizations need? | Will experiment |
| What's the right balance of chat vs notebook? | Will find out |
| What level of code understanding is "enough"? | Will learn through building |
| How much testing is practical vs overkill? | Will find balance |
| What software concepts are most valuable to learn? | Will discover through doing |

---

## 9. Success Criteria

### For v0.1 (Foundation)
- [ ] Can fetch Bulls game data through simple function calls
- [ ] Can have a conversation with AI about Bulls stats
- [ ] Can create a basic chart from the data
- [ ] Tests exist and pass for core functionality

### For v0.2 (Analysis)
- [ ] Can easily answer "how has player X performed lately?"
- [ ] Can compare player/team stats to averages
- [ ] Can identify interesting patterns in the data
- [ ] Analysis functions are tested with known inputs/outputs

### For v0.3 (Visualization)
- [ ] Can create Bulls-branded charts
- [ ] Can generate polished visualizations
- [ ] Have created at least 3 graphics I'm proud of

### Software Engineering Goals
- [ ] Understand how modules, imports, and packages work together
- [ ] Understand how tests verify code works correctly
- [ ] Can explain what each major function does (concepts, not syntax)
- [ ] Experience the full build → test → iterate → ship cycle
- [ ] Feel confident using AI to build real software

### Ongoing
- [ ] Actually enjoy using this
- [ ] Create content I want to post
- [ ] Learn something about data/basketball/creating/building software
- [ ] Prove that AI-assisted building works for non-traditional developers

---

## 10. Technical Notes

For implementation details, see **SPEC.md**.

Quick reference:

| Item | Value |
|------|-------|
| Language | Python 3.10+ |
| Data Source | NBA API (via `nba_api` library) |
| Visualization | Pillow, matplotlib (may evolve) |
| Key Libraries | nba_api, pandas, Pillow, requests |
| Testing | pytest |
| Bulls Team ID | 1610612741 |
| Season | 2025-26 |

### Software Engineering Stack

| Concept | Tool/Practice |
|---------|---------------|
| Version Control | Git |
| Testing | pytest |
| Documentation | PRD + SPEC + inline comments |
| Development Environment | Virtual environment (venv) |
| AI Collaboration | Cursor |
