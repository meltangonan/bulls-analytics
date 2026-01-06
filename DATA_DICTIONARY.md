# Data Dictionary - NBA API Stats

> Reference for all available statistics from the NBA API.  
> Last Updated: January 2026

---

## Data Sources

| Endpoint | Description | Use Case |
|----------|-------------|----------|
| `teams.get_teams()` | All 30 NBA teams | Look up team IDs |
| `LeagueGameFinder` | Game schedules & results | Get list of Bulls games |
| `BoxScoreTraditionalV3` | Basic player stats | Core stats for any game |
| `BoxScoreAdvancedV3` | Advanced metrics | Efficiency, usage stats |
| `BoxScoreMiscV3` | Miscellaneous stats | Paint points, fast break |
| `BoxScoreScoringV3` | Scoring breakdown | Shot distribution |

---

## Key IDs

| Entity | ID | Notes |
|--------|-----|-------|
| Chicago Bulls | `1610612741` | Used in all API calls |
| Season format | `'2025-26'` | Year season starts - year it ends |
| Game ID format | `'0022500503'` | Unique identifier per game |

---

## Traditional Stats (BoxScoreTraditionalV3)

| Column | Description | Example |
|--------|-------------|---------|
| `personId` | Unique player ID | `203897` |
| `firstName` | Player first name | `Zach` |
| `familyName` | Player last name | `LaVine` |
| `minutes` | Minutes played | `PT32M15S` (32:15) |
| `points` | Points scored | `28` |
| `reboundsTotal` | Total rebounds | `5` |
| `reboundsOffensive` | Offensive rebounds | `1` |
| `reboundsDefensive` | Defensive rebounds | `4` |
| `assists` | Assists | `6` |
| `steals` | Steals | `2` |
| `blocks` | Blocks | `0` |
| `turnovers` | Turnovers | `3` |
| `foulsPersonal` | Personal fouls | `2` |
| `plusMinusPoints` | Plus/minus | `+12` |
| `fieldGoalsMade` | FG made | `10` |
| `fieldGoalsAttempted` | FG attempted | `18` |
| `fieldGoalsPercentage` | FG % | `0.556` |
| `threePointersMade` | 3PT made | `4` |
| `threePointersAttempted` | 3PT attempted | `8` |
| `threePointersPercentage` | 3PT % | `0.500` |
| `freeThrowsMade` | FT made | `4` |
| `freeThrowsAttempted` | FT attempted | `5` |
| `freeThrowsPercentage` | FT % | `0.800` |

---

## Advanced Stats (BoxScoreAdvancedV3)

| Column | Description | What It Means |
|--------|-------------|---------------|
| `offensiveRating` | Points per 100 possessions (offense) | Higher = more efficient scorer |
| `defensiveRating` | Points allowed per 100 possessions | Lower = better defender |
| `netRating` | ORtg - DRtg | Positive = team better with player on court |
| `usagePercentage` | % of team plays used by player | Higher = more involved in offense |
| `trueShootingPercentage` | Shooting efficiency (includes FT) | Better than raw FG% |
| `effectiveFieldGoalPercentage` | FG% adjusted for 3PT value | Accounts for 3s being worth more |
| `assistPercentage` | % of teammate FGs player assisted | Measures playmaking |
| `assistToTurnover` | Assists / Turnovers | Higher = takes care of ball |
| `reboundPercentage` | % of available rebounds grabbed | Measures rebounding impact |
| `PIE` | Player Impact Estimate | Overall game impact metric |

---

## Misc Stats (BoxScoreMiscV3)

| Column | Description | Content Ideas |
|--------|-------------|---------------|
| `pointsPaint` | Points scored in the paint | "Dominated inside" storylines |
| `pointsFastBreak` | Fast break points | Transition offense |
| `pointsSecondChance` | Points after offensive rebounds | Hustle plays |
| `pointsOffTurnovers` | Points off opponent turnovers | Defense → offense |
| `foulsDrawn` | Fouls drawn by player | Getting to the line |
| `blocksAgainst` | Times player was blocked | Shot difficulty |

---

## Scoring Breakdown (BoxScoreScoringV3)

| Column | Description | Content Ideas |
|--------|-------------|---------------|
| `percentagePointsPaint` | % of points from paint | Inside vs outside scorer |
| `percentagePoints3pt` | % of points from 3PT | Perimeter threat |
| `percentagePointsFreeThrow` | % of points from FT | Getting to the line |
| `percentageAssistedFGM` | % of FGs that were assisted | Creating own shot vs. assisted |
| `percentageUnassistedFGM` | % of FGs unassisted | Self-creation ability |
| `percentageAssisted2pt` | % of 2PT FGs assisted | Inside finishing |
| `percentageAssisted3pt` | % of 3PT FGs assisted | Catch-and-shoot vs pull-up |

---

## Interesting Stats for Content Ideas

### "Story" Stats (unique angles)
- **Usage Rate** - "Coby White used 28% of possessions - highest on team"
- **True Shooting %** - Better measure of efficiency than raw FG%
- **Points in Paint %** - Shows player's scoring style
- **Unassisted FG %** - "Created his own shot on 65% of makes"
- **Net Rating** - "Bulls were +15 with LaVine on the court"

### Comparison Ideas
- Player's game vs. their season average
- Player vs. opponent's best player
- Team stats vs. league average
- This game vs. last 5 games

---

## Notes

- V3 endpoints use **camelCase** (e.g., `teamId`, `firstName`)
- V2 endpoints (deprecated) used **SCREAMING_SNAKE_CASE** (e.g., `TEAM_ID`)
- Always add `time.sleep(0.6)` between API calls to avoid rate limiting
- Season type options: `'Regular Season'`, `'Playoffs'`, `'Pre Season'`, `'All Star'`

