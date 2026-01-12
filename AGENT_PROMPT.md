# Bulls Analytics Workspace - New Project

## What I'm Building

A **collaborative analysis workspace** for exploring Chicago Bulls basketball data and creating unique, insightful visualizations for Instagram. 

This is NOT an auto-generation tool. It's a workspace where I explore data WITH AI assistance, find interesting stories, and craft visualizations together.

## Why I'm Building This

| Goal | What It Means |
|------|---------------|
| **Portfolio Piece** | Demonstrate data analysis, visualization, PM skills, and software engineering |
| **Learn Software Engineering** | Understand foundational concepts - how software actually works, not every line of code |
| **Prove AI-Driven Building Works** | Show that a PM can use AI to build and ship real, functional software |
| **Create Content** | Produce unique Bulls analytics content for Instagram |

This project is explicitly about **building with AI**. I'm a PM, not a traditional developer. I want to understand the *concepts* of how software works, drive the product vision, and let AI handle implementation details.

## The Vision

```
Me: "What was interesting about last night's Bulls game?"

AI: [fetches data, analyzes]
    "Coby White scored 28 points, but here's what stands out:
     - 18 of those points came in the 4th quarter
     - Bulls are 4-0 when he scores 10+ in Q4 this season"

Me: "That's interesting. Can we visualize his Q4 scoring over the last 15 games?"

AI: [creates chart, shows me]

Me: "Nice. Let's highlight last night's game in Bulls red."

AI: [updates chart]

Me: "Perfect. When I'm ready, make it Instagram-ready."

AI: [generates polished 1080x1350 graphic]
```

The key insight: The **process** of exploring and finding insights is as important as the output. I want to be involved, not just push a button.

## What I Want From You

You are my collaborator. Help me:
1. **Explore** Bulls data - fetch stats, find patterns
2. **Discuss** what's interesting - surface unique angles
3. **Visualize** insights together - iterate on charts
4. **Polish** when ready - create Instagram-ready graphics

## Key Documents

I have two documents that define everything:

### PRD.md
Product requirements including:
- Why this exists (portfolio piece, learning, content creation)
- How the workflow should feel
- What makes good content
- Success criteria

### SPEC.md  
Technical specification including:
- Complete environment setup from scratch
- Directory structure
- File-by-file code implementation
- NBA API reference
- Implementation phases

**Please read both documents fully before starting.**

## Technical Summary

| Item | Value |
|------|-------|
| Language | Python 3.10+ |
| Data Source | NBA API (nba_api library) |
| Key Libraries | nba_api, pandas, matplotlib, Pillow |
| Testing | pytest |
| Package Name | `bulls` (import as `from bulls import data, analysis, viz`) |
| Bulls Team ID | 1610612741 |
| Season | 2025-26 |

## How I Want to Work

1. **Build iteratively** - Start with data layer, make sure it works, then add analysis, then visualization
2. **Always test** - Write actual tests (pytest), not just manual verification. Testing is what good engineers do.
3. **Keep it simple** - Don't over-build. Add features when we need them, not before
4. **Concepts over syntax** - Help me understand *why* code works, not just *how* to write it
5. **This will evolve** - My preferences will become clearer as I use it. Expect change.

## Start Here

1. **Read PRD.md and SPEC.md** completely
2. **Set up the project** following SPEC.md Section 0 (environment setup)
3. **Build Phase 0** - Get Bulls data flowing (SPEC.md Section 9)
4. **Write tests** - Add pytest tests for the functionality we build
5. **Verify** - Run tests, make sure everything works
6. **Then we'll explore together** - I'll start asking questions about Bulls games

## What NOT to Do

- ❌ Don't build an auto-generation CLI tool
- ❌ Don't make decisions about what's "interesting" without me
- ❌ Don't generate graphics without my input on what to visualize
- ❌ Don't over-engineer - we're starting simple
- ❌ Don't skip tests - they're part of the process, not an afterthought

## Ready?

Read the docs, then let's set up the project and get data flowing. Once that works, we'll start exploring Bulls data together.
