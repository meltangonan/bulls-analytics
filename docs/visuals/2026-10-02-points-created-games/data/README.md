# Single-game points created — source and verification

Scope: every Chicago Bulls regular-season player-game from 1996–97 through 2025–26. Repeat players are allowed. Points created means **the player's official points scored + the exact 2 or 3 points scored on each field goal he officially assisted**. It includes overtime. This does not estimate assisted points as AST × 2.5, include playoff games, credit free throws resulting from passes, or measure possession value.

| Displayed value | NBA source | Calculation |
| --- | --- | --- |
| Player, date, opponent, result, points scored | `https://stats.nba.com/stats/playergamelogs` | NBA game box-score fields; normalized names in saved CSVs |
| Points from assists | `https://stats.nba.com/stats/playbyplayv3` | Sum each assisted made field goal's `shotValue` (2 or 3) for its attributed assister |
| Total points created | The two sources above | `PTS + assist_pts` |
| % of team points | `https://stats.nba.com/stats/leaguegamefinder` supplies official Chicago game points | `100 × created / team_pts` |
| Overtime label | PlayByPlayV3 `period`; otherwise official player-game `MIN` | Maximum period minus four; otherwise verify total Chicago minutes = 240 + 25 × number of overtime periods |
| Rank | Calculated across the full Chicago player-game population | Competition rank: 1 + count of games with greater points created; all cutoff ties retained |

Inputs are reused saved NBA responses/extracts; **no new NBA requests were needed for the Bulls selection**. Box-score inputs were archived from the September 25 season-opener post; assisted baskets/actions were archived from the August 8 assist-duos and September 21 season points-created posts. Original capture timestamps are unavailable for some reused normalized CSVs; the manifest explicitly marks these unknown. Raw PlayByPlayV3 snapshots retain their original `retrieved_at` where available. `verification-summary.json` records October 2, 2026 generation time, source paths and SHA-256 hashes; this is the archive/calculation date, not a new NBA capture date.

Effective endpoint scope parameters: `PlayerGameLogs` used `Season=1996-97` through `2025-26`, `SeasonType=Regular Season`, `TeamID=1610612741`; `LeagueGameFinder` used the same season/type/team parameters. `PlayByPlayV3` used each candidate's 10-digit `GameID` and its ordinary all-period/all-action defaults. Complete PlayByPlayV3 response parameters remain in original raw snapshots where preserved. Historical normalized extracts do not retain the complete transport parameter object; nothing was inferred as a fresh fetch.

## Complete selection proof

`coverage.csv` proves coverage of all 30 seasons: **2,385 team games and 24,660 player-game rows**. Expected games are 82 per season except 1998–99 (50), 2011–12 (66), 2019–20 (65), and 2020–21 (72). Team and player game-ID populations match exactly, player-game identities are unique, required box fields are present, and summed player points reconcile to official Chicago game points in every game.

For each unresolved player-game, teammates' total made field goals and made threes provide bounds. Let `A=AST`, `T3=teammates' FG3M`, and `T2=teammates' FGM−FG3M`, explicitly excluding the player's own shots:

- Minimum assisted points = `2A + max(0, A−T2)`.
- Maximum assisted points = `2A + min(A,T3)`.
- Add official PTS to obtain minimum/maximum points-created bounds.

Resolve the largest remaining upper bound while it can meet the current selection cutoff. **35 potentially relevant games were resolved exactly**. Every player's extracted assist count in each resolved Chicago game matches his official box-score AST, including players outside the final display. Both input branches verify same-team scorer/assister membership, reject self-assists, and require each scorer’s assisted twos/threes not to exceed his official made twos/threes. Raw-action parses additionally reconcile player FGM and FG3M and reject duplicate action numbers. Older normalized basket extracts lack action IDs, so distinct repeated baskets to the same scorer cannot be independently distinguished using their schema. No audit errors or warnings remain (`issues.json` is empty). Some other games were not parsed, because the official upper bound alone proves they cannot qualify.

The final cutoff is **61 points created**, while **every unexamined player-game has an upper bound of at most 60**. `selection-proof.csv.gz` saves all 24,660 rows, exact values where resolved, conservative bounds elsewhere, and each row's disposition. There are four performances tied at rank 13, so **Top 15 + ties contains 16 rows**. The selection does not discard a tied game. The first rank column compares Chicago games. The added NBA season rank compares every NBA regular-season player-game in that game’s season; see `nba-game-ranks/README.md` for sources and exact comparison proofs.

## Worked published example

DeMar DeRozan, December 11, 2023 at Milwaukee, `GameID=0022300300`, `PLAYER_ID=201942`: NBA box score supplies **41 PTS and 11 AST**. The saved NBA assisted baskets contain **four 2-point baskets and seven 3-point baskets** credited to DeRozan: `4×2 + 7×3 = 29` assisted points. Thus `41 + 29 = 70` points created, the highest Chicago game in this window. Chicago scored 129, so `100×70/129 = 54.2636%`, displayed as 54.3%. This was one overtime, verified from the saved game actions.

The raw first assist appears at action 9: DeRozan assists Nikola Vučević's made three; the next appears at action 29 and is a made two. The raw game snapshot is `raw/2023-24_0022300300.json.gz`; the official player/team boxes are `raw/CHI-players-regular-season-2024.csv` and `raw/CHI-team-regular-season-2024.csv`. Saved attributable baskets are in `candidate-assisted-baskets.csv.gz`; final display values are in `top15.csv`. Despite the historical filename, `top15.csv` intentionally contains all 16 cutoff qualifiers.

Reproduce with `python scripts/prototypes/points_created_games_data.py`; verification checks are `tests/test_points_created_games_data.py` plus the reused NBA attribution/bounds tests. Inputs under `raw/` include all box extracts, original compressed game actions where available, and game-specific saved basket extracts otherwise. Saved basket extracts preserve the source's identities and actual shot values; where original actions are unavailable they cannot independently reconstruct every non-assisted event. Official-assist reconciliation is preserved without inventing missing action details.
