# Independent leaderboard replay

The 2010-11 top three ranks and 2023-24 top ten player-games were independently rebuilt from original NBA league player-game logs and raw NBA play-by-play. Previously computed points-created totals were not reused. Full league coverage was revalidated against official season scoring, assists, made field goals, made threes and games played for every player. Each replayed game reconciles every player's assisted baskets and made field goals to official boxes.

Competition rank counts every player-game, including repeat games by the same player. The leaderboards include every game tied at the cutoff. Points created equals PTS plus the actual two- or three-point values of assisted field goals.

- **2010-11:** 25,153 player-games / 1,230 games. Twenty-six PBP games replayed. Leaderboard cutoff 66; five rows occupy the top three ranks. LeBron James leads at 70, followed by Monta Ellis at 68. Derrick Rose, another Ellis game and Deron Williams tie third at 66. Rose's published T-3rd rank and three-game tie count are confirmed. Maximum uninspected box bound is 62.
- **2023-24:** 26,401 player-games / 1,230 games. Seventy-six PBP games replayed. Top-ten cutoff 76. DeMar DeRozan's 70-point-created game has 21 games strictly above it and six other games equal to it, confirming T-22nd and seven tied games. Maximum uninspected box bound is 69.

Both replays have zero source errors, zero ordinal warnings, zero unresolved comparisons, and no changes to the published sixteen ranks. Raw replies are referenced by exact path/hash in `sources-*.json`; newly required replies are saved under the parent `raw/` directory. `population-proof-*.csv.gz` preserves every league player-game, `target-recheck-proof-*.csv.gz` preserves every target comparison, and `assisted-baskets-*.csv.gz` preserves every extracted basket. Verification summaries include source counts, coverage and output hashes.

Reproduce with:

```bash
venv/bin/python scripts/prototypes/points_created_games_nba_leaderboards.py
```

This script writes only supplementary leaderboard/proof outputs, leaving the canonical table and its sixteen published rank values unchanged. NBA PBP requests remain serial.
