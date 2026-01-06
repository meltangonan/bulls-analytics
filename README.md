# Bulls Analytics 🏀

A data-driven Instagram content project for Chicago Bulls fans.

> "Making Bulls stats accessible and visual for fans who love the team but don't dive deep into numbers."

## What This Is

This is a passion project combining:
- **Data Analysis** - Pulling and analyzing NBA stats
- **SQL** - Learning database queries through basketball data
- **Visualization** - Creating Instagram-ready graphics
- **Product Thinking** - Building something people actually want

## Project Status

**Current Phase:** Phase 1 Complete ✅ → Starting Phase 2

See [PRD.md](PRD.md) for full product requirements and roadmap.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/meltangonan/bulls-analytics.git
cd bulls-analytics

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Open the exploration notebook
# (In VS Code/Cursor, just open explore.ipynb)
```

## Project Structure

```
bulls-analytics/
├── PRD.md                 # Product Requirements Document
├── DATA_DICTIONARY.md     # Reference for all NBA stats
├── explore.ipynb          # Data exploration notebook
├── requirements.txt       # Python dependencies
├── data/                  # SQLite database (Phase 2)
├── scripts/               # Data fetching scripts (Phase 2)
├── queries/               # SQL query templates (Phase 2)
├── visualizations/        # Chart generation code (Phase 3)
└── output/                # Generated images for Instagram (Phase 3)
```

## Documentation

- [PRD.md](PRD.md) - Product vision, goals, and roadmap
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) - All available NBA stats explained
- [PROGRESS.md](PROGRESS.md) - Learning journey and session notes

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| nba_api | Fetch NBA statistics |
| pandas | Data manipulation |
| SQLite | Local database (learning SQL) |
| matplotlib/seaborn | Visualizations |
| Jupyter Notebooks | Exploration & analysis |

## Data Sources

All data comes from the official NBA API via the `nba_api` Python package:
- Game schedules and results
- Player box scores (traditional stats)
- Advanced metrics (usage rate, true shooting, etc.)
- Scoring breakdowns (paint points, assisted %, etc.)

---

*Built with [Cursor](https://cursor.sh) and a lot of curiosity about basketball data.*

