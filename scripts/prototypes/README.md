# Post renderers

Find a related entry point here; read its module docstring and arguments before running it.
Notion owns post status and history. This index maps code, not publication state.
The scripts include live post renderers, shared preparation scripts, and older experiments;
check imports before retiring one. Reuse shared elements in `bulls/graphics` for new work.

Run selected checks with `./run_tests.sh <test paths> -q`. Use the primary checkout's Python in
linked worktrees. Rendering can fetch data unless the entry point explicitly supports saved inputs;
inspect its arguments first. `--final` on supported renderers means publish DPI.

| Entry point | Purpose/family | Focused checks (paths from repo root) |
| --- | --- | --- |
| `shot_family_leaders.py` | Any shot family's single-season FGM ranking from one registry (`--family dunks/hooks/layups/floaters`); derives the rankable window from the label audit, `--from-season` narrows it | `tests/test_shot_family_leaders.py` |
| `shot_diet_distribution.py` | Bulls shot-family shares vs the league average, one dumbbell row per family; `--prepare` snapshots 30 teams and reconciles, `--audit-venue` tests arena scorer bias, `--corroborate` checks the claims against tracking, `--render` draws the family dumbbell and `--render-table` the 48-label vocabulary, both from saved tables | `tests/test_shot_diet_distribution.py` |
| `floater_season_leaders.py` | Bulls single-season floater FGM ranking since 2015–16, the first season carrying all three floating labels; same flags as `layup_season_leaders.py` | `tests/test_floater_season_leaders.py` |
| `layup_season_leaders.py` | Bulls single-season layup FGM ranking since 2000–01; `--prepare` snapshots/audits, `--render` saved data | `tests/test_layup_season_leaders.py` |
| `assist_age_ladder.py` | Assist counterpart to `scoring_age_ladder.py` | `tests/test_assist_age_ladder.py` |
| `and_one_leaders_data.py` | Bulls and-1 season leaders since 1996-97; counts and-1s from NBA.com play-by-play. | `tests/test_and_one_leaders_data.py` |
| `and_one_leaders_table.py` | Table-bar chart for the and-1 season leaders. | `tests/test_and_one_leaders_data.py` |
| `rim_protection_data.py` | Bulls rim defence since 2013-14; reconciles tracking totals, rebuilds 2024-25 from date halves, prepares per-100 and top-15 views | `tests/test_rim_protection.py` |
| `rim_protection_landscape.py` | Tipoff-style scatter of rim attempts defended against rim points saved, both per 100 possessions; qualified league seasons are grey, the Bulls seasons saving over a point per 100 are headshots on their point | `tests/test_rim_protection.py` |
| `rim_protection_table.py` | Top-15 Bulls seasons by rim points saved as a table-bar hybrid; measures its own column widths for equal gaps and sizes rows to fill the Canva page (`--page 3:4` or `4:5`) | `tests/test_rim_protection.py` |
| `block_leaders_data.py` / `block_leaders_table.py` | Prepares and renders the top Bulls single-season block totals since 2000-01. Blocks are the bar; NBA rank and BLK/G are support columns. The 104-block cutoff tie is resolved by BLK/G | `tests/test_block_leaders.py` |
| `points_created_table.py` | Top 15 Bulls points-created seasons since 1996-97; scored/assisted split bar, total card, NBA rank, team share, per-game rate and MVP voting. `points_created_nba_ranks.py` certifies ranks with NBA data; `points_created_nba_parse.py` attributes and reconciles baskets | `tests/test_points_created_nba_*.py`, saved rank proofs and renderer geometry checks |
| `assist_duos.py` | Bulls assist duos | `tests/test_assist_duos.py` |
| `assist_duos_fetch.py` | Bulls assist duos | `tests/test_assist_duos.py` |
| `scoring_duo_games_data.py` | Bulls top-15 combined-scoring duo games since 2000-01; duo selection, tie handling and overtime labels over `top_game_performances` source rows | `tests/test_scoring_duo_games.py` |
| `scoring_duo_games_table.py` | Renders `scoring_duo_games_data.py` top15.csv as a split-bar duo table | `tests/test_scoring_duo_games.py` |
| `taj_gibson_retirement_data.py` | Taj Gibson's Bulls season splits, best Game Scores, career highs and franchise ranks; reconciles career totals and records rank populations | `tests/test_taj_gibson_retirement.py` |
| `taj_gibson_bulls_zone_charts.py` | Pooled Bulls-tenure zones and career shot diet; reconciles season FGA and excludes unlabelled league rows | `tests/test_taj_gibson_retirement.py` |
| `taj_gibson_retirement_tables.py` | Retirement CSVs as tables/cards; `--slide` selects the asset, `top-games-table` reuses `house.draw_accent_card`; checks text overflow | `tests/test_taj_gibson_retirement.py` |
| `assisted_buckets.py` | Assisted vs. unassisted buckets | `tests/test_assisted_buckets.py` |
| `bench_points_leaders.py` | Bulls' biggest bench-scoring seasons since 1996-97 | `tests/test_bench_points_leaders.py` |
| `catch_and_shoot_points_data.py` | Bulls top-15 catch-and-shoot points and three-point points seasons; renders with `pull_up_points_bars.py --volume-comparisons` | `tests/test_catch_and_shoot_points_data.py` |
| `pull_up_points_data.py` | Bulls top-15 pull-up points seasons, 2013–14 onward; shared inputs for `pull_up_points_boxed.py`, `pull_up_points_bars.py`, and `pull_up_points_table.py` | `tests/test_pull_up_points_data.py` |
| `drive_leaders_data.py` | Bulls top-15 drive volume, drive-points, and drive-assist seasons since 2013–14; retains point-accounting and player/team audits | `tests/test_drive_leaders.py` |
| `drive_leaders_table.py` | Three matching table assets for the drive leaders carousel (`--mode drives/points/assists`) | `tests/test_drive_leaders.py` |
| `bulls_lineup_3pt.py` | Bulls' best three-point shooting five-man lineups since 2000-01 | No dedicated tests |
| `bulls_lineup_rdrtg.py` | Bulls' best five-man defensive lineups since 2000-01 | `tests/test_bulls_lineup_rdrtg.py` |
| `bulls_lineup_rortg.py` | Bulls' best five-man offensive lineups since 2000-01 | `tests/test_bulls_lineup_rortg.py` |
| `bulls_national_tv_history.py` | Bulls national TV games by season | `tests/test_bulls_national_tv_history.py` |
| `bulls_nba_2k27_rating_cards.py` | Full Bulls NBA 2K27 launch roster | `tests/test_bulls_nba_2k27_rating_cards.py` |
| `bulls_on_court_landscape.py` | 2025-26 on-court performance landscape | No dedicated tests |
| `bulls_opponent_win_percentage.py` | Bulls regular-season win percentage against every current NBA opponent since 2000-01 | `tests/test_bulls_opponent_win_percentage.py` |
| `bulls_rookie_chronological_table.py` | Bulls rookie seasons since 2000 | `tests/test_databallr_snapshot.py`, `tests/test_bulls_rookie_chronological_table.py` |
| `bulls_rookie_composite_table.py` | Rookie seasons since 2000-01, 1,000+ minutes; equal-weight ranks in PTS, REB, AST, STL+BLK, TS% and Win Shares | `tests/test_bulls_rookie_composite_table.py` |
| `bulls_rookie_landscape_scatter.py` | Every Bulls rookie season since 2000 as production against quality | `tests/test_bulls_rookie_landscape_scatter.py` |
| `bulls_rookie_leaderboard.py` | Which Bulls rookies did the most | `tests/test_bulls_rookie_leaderboard.py` |
| `bulls_rookie_metric_analysis.py` | Bulls rookie seasons since 2000 | `tests/test_databallr_snapshot.py`, `tests/test_bulls_rookie_metric_analysis.py` |
| `bulls_season_zone_charts.py` | One Bulls season through zone shot charts | `tests/test_2010_11_mvp_rose_zone_charts.py`, `tests/test_bulls_season_zone_charts.py` |
| `clutch_seasons_table.py` | The most clutch Bulls seasons since 2000 | `tests/test_clutch_seasons_table.py` |
| `clutch_scoring_age_ladder.py` | Bulls clutch scoring leaders by age since 2000 | `tests/test_clutch_scoring_age_ladder.py` |
| `clutch_table.py` | Current Bulls in the clutch | `tests/test_clutch_table.py`, `tests/test_scoring_age_ladder.py` |
| `current_roster_darko_landscape.py` | Current Bulls DARKO landscape | `tests/test_current_roster_darko_landscape.py` |
| `current_roster_hex_charts.py` | Current-roster player hex batch | `tests/test_current_roster_hex_charts.py` |
| `current_roster_hot_spots.py` | Roster shot-location density vs league, as small multiples; frequency, not accuracy; `--cold` adds below-average locations | `tests/test_current_roster_hot_spots.py` |
| `current_roster_jam_cards.py` | NBA Jam-style roster cards; six league-percentile bars using per-75-possession production | `tests/test_current_roster_jam_cards.py` |
| `current_roster_scoring_landscape.py` | Current roster scoring landscape | `tests/test_current_roster_scoring_landscape.py` |
| `current_roster_zone_charts.py` | Current-roster twelve-zone batch | Shared renderer: `tests/test_zone_charts.py`; no dedicated batch tests |
| `demar_derozan_bulls_zone_charts.py` | DeMar DeRozan's three Bulls regular seasons plus an attempt-weighted Chicago-tenure total | `tests/test_demar_derozan_bulls_zone_charts.py` |
| `derrick_rose_bulls_zone_charts.py` | Derrick Rose's seven played Bulls regular seasons plus an attempt-weighted Chicago-tenure total | `tests/test_derrick_rose_bulls_zone_charts.py`, `tests/test_player_season_totals.py` |
| `dunks_since_2010.py` | Top-ten Bulls dunk seasons since 2010–11, split by type (total, driving, running, alley-oop, putback) | `tests/test_dunks_since_2010.py` |
| `f5_lineup_table.py` | Bulls Lineup Table | `tests/test_f5_lineup_table.py` |
| `fga_leader_zone_charts.py` | Bulls FGA leaders of the 2020s | `tests/test_fga_leader_zone_charts.py` |
| `game_score_by_height.py` | Best Bulls game at every listed height since 2000 | `tests/test_game_score_by_height.py` |
| `height_ladder_cards.py` | Highest-PPG-at-each-height ladder as bordered portrait cards | No dedicated tests |
| `height_ladder_fetch.py` | Bulls player-seasons and heights since 1976-77; `--rebuild` reuses saved responses | No dedicated tests |
| `height_ladder_portraits.py` | Processes manually sourced height-ladder portraits; originals cannot be refetched | No dedicated tests |
| `height_ladder_prep.py` | Height winners with 41 GP/20 MPG floors, plus an alternate fallback for empty heights | No dedicated tests |
| `height_ladder_threshold.py` | Compares qualification thresholds for height-ladder winners | No dedicated tests |
| `hinrich_bulls_zone_charts.py` | Kirk Hinrich's eleven Bulls regular seasons plus a pooled Chicago-tenure total and a small-multiples cover | `tests/test_hinrich_bulls_zone_charts.py`, `tests/test_player_season_totals.py` |
| `impactful_bulls_bpm.py` | Most impactful Bull per season | `tests/test_impactful_bulls_bpm.py` |
| `impactful_bulls_bpm_columns.py` | The same BPM analysis as a stacked column chart | Shared analysis: `tests/test_impactful_bulls_bpm.py`; no dedicated renderer tests |
| `jimmy_butler_bulls_zone_charts.py` | Jimmy Butler's Bulls regular seasons with 300+ Chicago FGA plus an attempt-weighted six-season tenure total | `tests/test_jimmy_butler_bulls_zone_charts.py`, `tests/test_player_season_totals.py` |
| `matas_buzelis_shot_families.py` | Buzelis's shot families and self-created share across his two Bulls seasons, from NBA.com ACTION_TYPE labels | `tests/test_matas_buzelis_shot_families.py` |
| `matas_buzelis_bulls_zone_charts.py` | Matas Buzelis's two Bulls regular seasons plus a pooled two-season tenure total | `tests/test_matas_buzelis_bulls_zone_charts.py` |
| `mock_post_demo.py` | Design preview with a fictional roster; no network or cache needed | No dedicated tests |
| `opponent_elite_performance.py` | Opponent counts/rates for Game Score 30+ and 30+ point games; reuses `top_game_performances.py` loaders | `tests/test_opponent_elite_performance.py` |
| `payroll_vs_wins.py` | Build the Bulls payroll-share vs win-percentage chart asset for Canva. | `tests/test_payroll_vs_wins.py` |
| `rebounds_age_ladder.py` | Rebound counterpart to `stocks_age_ladder.py` | `tests/test_rebounds_age_ladder.py` |
| `rebounds_age_ladder_merger.py` | Rebound age ladder since 1976-77; uses saved PlayerCareerStats for coverage before LeagueDashPlayerStats begins | `tests/test_rebounds_age_ladder_merger.py` |
| `regular_season_gamebook.py` | Four independent regular-season postgame experiments | `tests/test_regular_season_gamebook.py` |
| `rim_vs_three_pps_landscape.py` | Rim vs. Three points per shot | `tests/test_rim_vs_three_pps_landscape.py` |
| `scoring_age_ladder.py` | Highest PPG by NBA-listed season age since 2000-01; Chicago regular-season stints, minimum half the team's games | `tests/test_stocks_age_ladder.py`, `tests/test_scoring_age_ladder.py`, `tests/test_assist_age_ladder.py` |
| `scoring_by_location.py` | Scoring by location | `tests/test_scoring_by_location.py` |
| `scoring_leaps.py` | Bulls' biggest year-over-year scoring leaps since 2000 | `tests/test_scoring_leaps.py` |
| `season_opener_performances.py` | Best Bulls season-opener performances since 2000 | `tests/test_season_opener_performances.py` |
| `season_shape_post.py` | The Shape of the Season | Shared record calculation: `tests/test_analysis.py`; no dedicated renderer tests |
| `stocks_age_ladder.py` | Defensive counterpart | `tests/test_stocks_age_ladder.py` |
| `summer_league_report.py` | Summer League Report v1 + v2 | `tests/test_summer_league_report.py` |
| `summer_league_sticky_stats.py` | 2026 Summer League sticky shot-profile prototype | `tests/test_summer_league_sticky_stats.py` |
| `three_point_leaders.py` | Bulls' most accurate three-point shooter every season since 2010-11 | `tests/test_three_point_leaders.py` |
| `rookie_game_scores.py` | Top fifteen Bulls rookie games since 2000–01 by Game Score, regular season plus that season's playoffs (repeats eligible, points tiebreak); NBA.com Rookie filter defines rookies, CommonAllPlayers audits it; renders the Game Score table without FT and a boxed card version from `game_score_by_height.py` | `tests/test_rookie_game_scores.py` |
| `season_game_performances.py` | Top fifteen Bulls player-games in the 2025–26 regular season; reuses the Game Score table. | `tests/test_season_game_performances.py` |
| `top_game_performances.py` | Top Bulls game performances by decade | `tests/test_bulls_rookie_leaderboard.py`, `tests/test_top_game_performances.py` |
| `zone_deep_dive.py` | Volume *and* efficiency inside a single shot zone | No dedicated tests |
