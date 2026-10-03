# NBA season rank certificates

`verified-ranks.csv` adds the NBA season context for each of the 16 selected Bulls player-games. Rank is competition rank: **1 + the number of NBA player-games in that season with strictly more points created**. Repeated games by the same player count separately. `nba_season_tie_count` includes the target game; `T-` appears only when at least two games have exactly that total. The population includes the NBA regular season and overtime, with every team, rather than Bulls games or one best game per player.

The completed audit covers **296,616 NBA player-games across 14,117 games in 12 seasons**, with **401,484 target comparisons**. It inspected 883 games of NBA play-by-play: 127 reused from the prior season post and 756 fetched for this post. All 16 ranks and exact tie counts are certified, with zero unresolved comparisons, zero source errors and zero excluded team-games. Fifteen assist-ordinal warnings still reconcile to official player counts; 66 recorded name-normalization actions resolve source spelling/name differences. Five league-log seasons were reused from the prior post and seven were fetched for this audit.

Points created is official PTS plus the actual value (two or three) of each assisted field goal. Official `PlayerGameLogs` are reconciled to `LeagueDashPlayerStats` totals for every player in each season: PTS, AST, FGM, FG3M and GP must all match. Every logged game must contain two teams. This verifies source coverage, including the shortened and bubble seasons.

For each player-game, the uninspected assist contribution has conservative bounds from official assists and teammates' made two- and three-point field goals. Every interval containing a selected total is resolved using saved or newly fetched NBA `PlayByPlayV3` actions. Intervals entirely above or below the total provide conclusive proofs without needing their exact totals. An interval touching the target total remains unresolved unless its endpoints are identical. No assist value, missing source or tied-game count is estimated.

Assisted baskets are resolved within the official same-team roster and reconciled to every player's AST, FGM and FG3M. A team-game with a source error retains its conservative box interval. Certification requires **zero unresolved comparisons**, so such an error can never silently affect a published rank or tied-game count. Ordinal gaps that still reconcile to official counts remain recorded warnings. Deterministic source-name normalizations are recorded per action in `sources-*.json`: literal first-name prefixes with missing punctuation; the comma before a generational suffix; and historical surnames only when NBA personal actions independently link the surname to the exact person ID. Original raw replies are unchanged.

- `player-game-logs-*.json` and `league-summary-*.json`: complete official box populations and independent season coverage inputs.
- `*.meta.json`: source path/hash or retrieval metadata; endpoint and parameters where available.
- `raw/*.json.gz`: NBA PBP snapshots, including original response where newly fetched.
- `assisted-baskets-*.csv.gz`: basket-level identity and shot values, with validated-team flags.
- `population-proof-*.csv.gz`: every NBA player-game and its exact value or conclusive interval.
- `rank-proof-*.csv.gz`: every comparison for each selected target, including that target and other games by the same player.
- `issues-*.json` and `sources-*.json`: reconciliation outcomes and normalization evidence.
- `verification-summary.json`: final coverage, proof/source counts, errors/warnings, freshness/reuse counts and proof hashes.

Endpoints are `https://stats.nba.com/stats/playergamelogs`, `https://stats.nba.com/stats/leaguedashplayerstats`, and `https://stats.nba.com/stats/playbyplayv3`. Each request uses the target season and **Regular Season**; full request parameters are preserved in the snapshots/metadata. NBA PBP requests are serial.

Reproduce the Bulls selection first, then enrich it with NBA ranks, because the selection script writes `top15.csv`:

```bash
venv/bin/python scripts/prototypes/points_created_games_data.py
venv/bin/python scripts/prototypes/points_created_games_nba_ranks.py
./run_tests.sh tests/test_points_created_games_nba_ranks.py -q
```

The rank certifier reuses verified per-season certificates, then independently recomputes them from saved complete population proofs before enriching the canonical CSV. It preserves the original selected rows, order and Bulls scoring/assist values. To explicitly recalculate one season's raw-action audit, remove only that season's `verified-ranks-<season>.csv` and `population-proof-<season>.csv.gz`, then run with `--season <season>`; saved source replies are reused.
