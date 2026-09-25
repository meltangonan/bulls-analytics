# Bulls career deep threes — review package

**Editorial question:** Who made the most deep threes as a Bull? This post is a career leaderboard. Average shot distance is reserved for a separate future post.

**Chart:** 15 Bulls players, ranked by made official regular-season **and playoff** 3PT field goals from a recorded whole-foot distance of 27–39 feet, 1996–97 through 2025–26. Shot location must be before midcourt (`LOC_Y < 417.5`). The 40-foot cutoff also removes 227 Bulls frontcourt attempts, including eight makes; their intent cannot be established from the shot log. Chicago attempts only; players' other teams are excluded. Equal makes share a rank; attempts break display order only.

The transparent table uses made threes as the bar, then attempts (ATT), deep attempts per Bulls game (ATT/G), and player deep 3P%. A second line under 3P% shows the player-minus-NBA difference as `(+4.3 vs. NBA)`, matching the contested-jumpers table's relative-percentage format. The underlying NBA rate covers **the same 27–39-foot, before-midcourt shots** in the same season and phase (regular season or playoffs), weighted by the player's attempts in each. This is a shot-range comparison, not ordinary league 3P%; the displayed number is a percentage-point difference computed before rounding.

The renderer is 2,900 × 3,355 design units, exported at 5,800 × 6,710 pixels. At a 1,030-pixel width on a 1,080 × 1,440 Canva page, it occupies about 1,191 pixels of height. The makes-bar span is 870 design units, down from 1,050 in the regular-season draft; the LaVine–White difference still spans about 97 design units. Taller rows and a smaller bottom pad reduce the blank area below the table while keeping 25-pixel page margins.

## Data and methods

| Displayed value | Source | Calculation |
| --- | --- | --- |
| Makes / ATT | NBA [ShotChartDetail](https://stats.nba.com/stats/shotchartdetail), one row per Bulls field-goal attempt | Filter `SHOT_TYPE = 3PT Field Goal`, `SHOT_DISTANCE` from 27 through 39 inclusive, `LOC_Y < 417.5`; sum `SHOT_MADE_FLAG` / count rows by `PLAYER_ID` |
| ATT/G | NBA [LeagueDashPlayerStats](https://stats.nba.com/stats/leaguedashplayerstats), official Bulls player-season `GP` | Career eligible ATT divided by summed Bulls regular-season and playoff GP, including games with zero deep attempts |
| 3P% | Selected ShotChartDetail rows | Made / attempts × 100 |
| NBA 3P% | NBA ShotChartDetail all-team regular-season cache and saved league-wide playoff shot responses | Eligible league makes / attempts by season **and phase**; average those rates using the player's eligible attempts in each as weights |
| ± pp | Calculated | Player 3P% minus player-weighted NBA 3P% |

ShotChartDetail regular-season Bulls parameters: `team_id=1610612741`, `player_id=0`, `season_nullable=<season>`, `season_type_all_star=Regular Season`, `context_measure_simple=FGA`, `last_n_games=0` (captured 2026-09-23 UTC). For playoffs, `team_id=0`, `player_id=0`, `season_nullable=<season>`, `season_type_all_star=Playoffs`, `context_measure_simple=FGA` returns one league-wide shot row per attempt; Chicago rows are selected by `TEAM_ID=1610612741` (captured 2026-09-25 UTC). Bulls official [LeagueDashPlayerStats](https://stats.nba.com/stats/leaguedashplayerstats) uses `season=<season>`, `season_type_all_star=Regular Season` or `Playoffs`, `team_id_nullable=1610612741`, `per_mode_detailed=Totals`, `measure_type_detailed_defense=Base`. Playoff league shots reconcile to official [LeagueDashTeamStats](https://stats.nba.com/stats/leaguedashteamstats) with `season_type_all_star=Playoffs`, `per_mode_detailed=Totals`, `measure_type_detailed_defense=Base` (all teams). A saved [LeagueGameFinder](https://stats.nba.com/stats/leaguegamefinder) response with `team_id_nullable=1610612741`, `season_type_nullable=Playoffs` verifies the 14 Bulls playoff seasons between 1996–97 and 2025–26 (136 team-game rows). The shared regular-season league cache was produced by `bulls.data.shots.league_shots`, which requests ShotChartDetail for each NBA team and season. Regular-season inputs span 1996–97 to 2025–26; league shot data cover 2003–04 to 2025–26. All top-15 regular-season selected attempts fall within those 23 league seasons.

The NBA shot log's `SHOT_DISTANCE` is a reported whole number of feet. `LOC_Y` is in tenths of a foot from the basket toward halfcourt; 417.5 is the halfcourt coordinate in those units. For example, Zach LaVine's made attempt in game `0021700704` is recorded at 27 feet, `LOC_X=-111`, `LOC_Y=247`, `SHOT_MADE_FLAG=1` in `raw/bulls-shots/2017-18.csv.gz`. It contributes one make and one attempt. His 2017–18 regular-season selected rows total 3-for-8, while his 2021–22 playoff rows add 2-for-9 in four games. Across all Chicago games he is 234-for-622 in 420 games: 1.48 ATT/G and 37.62%. Same-season, same-phase league rates imply 207.414 makes on his attempt mix, so the comparison is 207.414 / 622 = 33.35%, or +4.27 percentage points.

All 30 Bulls regular-season and 14 Bulls playoff shot logs reconcile exactly to official Bulls player 3PA and 3PM (52,603 attempts and 18,740 makes combined). All 14 league-wide playoff shot logs reconcile to official league team 3PA and 3PM. Nine regular-season three-point attempts have no shot distance, including two makes in 2001–02, so they cannot be classified into this range. Neither 2001–02 shooter reaches this top 15; no playoff three has missing distance. NBA's reported distance and coordinates may contain scorer or tracking error; the eligibility rule is reproducible from the supplied fields. The definition excludes 40+ foot shots even when their coordinates are before midcourt; it cannot identify every period-ending heave from shorter distances.

## Files and status

- `data/raw/bulls-shots/` and `data/raw/bulls-player-totals/`: 30 regular-season team shot responses and official player totals.
- `data/raw/bulls-playoff-games.csv.gz`: 136 Bulls playoff team-game rows confirming the 14 eligible postseason years.
- `data/raw/league-playoff-shots/`, `data/raw/bulls-playoff-totals/`, `data/raw/league-playoff-team-totals/`: 14 league-wide playoff shot responses, Bulls player totals, and official all-team totals, captured 2026-09-25 UTC.
- `data/source_manifest.csv`: endpoint, season, phase, file, and source-file modified time for the source snapshots.
- `data/league_27_39_by_season.csv` and `data/league_27_39_playoffs_by_season.csv`: selected league counts, source paths, and source-file modified times. Full regular-season all-team shot rows remain in the project's shared ignored `cache/shot_charts/`.
- `data/season_audit.csv`: per-season/phase reconciliation, missing-distance counts, selected counts, and 40+ foot exclusion counts, including frontcourt attempts and makes. `data/season_audit_regular_only.csv` and `data/top15_regular_only.csv` preserve the earlier scope decision.
- `data/player_seasons.csv`, `data/top15.csv`, `data/generation.json`: calculation trail, displayed values, and generation time.
- `scripts/prototypes/deep_threes_career_fetch_playoffs.py` fetches and caches playoff sources; `scripts/prototypes/deep_threes_career_data.py` regenerates data from snapshots; `scripts/prototypes/deep_threes_career_table.py --final` renders the table from `top15.csv`.

The chart is placed at 1,030 pixels wide on page 2 of the linked Canva design. Its downloaded 1,080 × 1,440 PNG was inspected at feed size with all 15 rows readable and no cropping. Canva copy and cover approval are tracked in the Notion post record. The post has not been published.
