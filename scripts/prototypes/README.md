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
| `assist_age_ladder.py` | Assist counterpart to `scoring_age_ladder.py` | `tests/test_assist_age_ladder.py` |
| `assist_duos.py` | Bulls assist duos | `tests/test_assist_duos.py` |
| `assist_duos_fetch.py` | Bulls assist duos | `tests/test_assist_duos.py` |
| `assisted_buckets.py` | Assisted vs. unassisted buckets | `tests/test_assisted_buckets.py` |
| `bench_points_leaders.py` | Bulls' biggest bench-scoring seasons since 1996-97 | `tests/test_bench_points_leaders.py` |
| `bulls_lineup_3pt.py` | Bulls' best three-point shooting five-man lineups since 2000-01 | Use the consuming family checks |
| `bulls_lineup_rdrtg.py` | Bulls' best five-man defensive lineups since 2000-01 | `tests/test_bulls_lineup_rdrtg.py` |
| `bulls_lineup_rortg.py` | Bulls' best five-man offensive lineups since 2000-01 | `tests/test_bulls_lineup_rortg.py` |
| `bulls_national_tv_history.py` | Bulls national TV games by season | `tests/test_bulls_national_tv_history.py` |
| `bulls_nba_2k27_rating_cards.py` | Full Bulls NBA 2K27 launch roster | `tests/test_bulls_nba_2k27_rating_cards.py` |
| `bulls_on_court_landscape.py` | 2025-26 on-court performance landscape | Use the consuming family checks |
| `bulls_opponent_win_percentage.py` | Bulls regular-season win percentage against every current NBA opponent since 2000-01 | `tests/test_bulls_opponent_win_percentage.py` |
| `bulls_rookie_chronological_table.py` | Bulls rookie seasons since 2000 | `tests/test_databallr_snapshot.py`, `tests/test_bulls_rookie_chronological_table.py` |
| `bulls_rookie_composite_table.py` | Top Bulls rookie seasons by an equal-weight six-category rank (PTS, REB, AST, STL+BLK, TS%, Win Shares) across r… | `tests/test_bulls_rookie_composite_table.py` |
| `bulls_rookie_landscape_scatter.py` | Every Bulls rookie season since 2000 as production against quality | `tests/test_bulls_rookie_landscape_scatter.py` |
| `bulls_rookie_leaderboard.py` | Which Bulls rookies did the most | `tests/test_bulls_rookie_leaderboard.py` |
| `bulls_rookie_metric_analysis.py` | Bulls rookie seasons since 2000 | `tests/test_databallr_snapshot.py`, `tests/test_bulls_rookie_metric_analysis.py` |
| `bulls_season_zone_charts.py` | One Bulls season through zone shot charts | `tests/test_2010_11_mvp_rose_zone_charts.py`, `tests/test_bulls_season_zone_charts.py` |
| `clutch_seasons_table.py` | The most clutch Bulls seasons since 2000 | `tests/test_clutch_seasons_table.py` |
| `clutch_table.py` | Current Bulls in the clutch | `tests/test_clutch_table.py`, `tests/test_scoring_age_ladder.py` |
| `current_roster_darko_landscape.py` | Current Bulls DARKO landscape | `tests/test_current_roster_darko_landscape.py` |
| `current_roster_hex_charts.py` | Current-roster player hex batch | `tests/test_current_roster_hex_charts.py` |
| `current_roster_hot_spots.py` | Roster hot-spot shot charts as small multiples. Faithful port of Owen Phillips' F5 method: smooth shot-location … | `tests/test_current_roster_hot_spots.py` |
| `current_roster_jam_cards.py` | NBA Jam-style player cards for the current roster. Six bars per card, each the player's league percentile in a p… | `tests/test_current_roster_jam_cards.py` |
| `current_roster_scoring_landscape.py` | Current roster scoring landscape | `tests/test_current_roster_scoring_landscape.py` |
| `current_roster_zone_charts.py` | Current-roster twelve-zone batch | Use the consuming family checks |
| `demar_derozan_bulls_zone_charts.py` | DeMar DeRozan's three Bulls regular seasons plus an attempt-weighted Chicago-tenure total | `tests/test_demar_derozan_bulls_zone_charts.py` |
| `derrick_rose_bulls_zone_charts.py` | Derrick Rose's seven played Bulls regular seasons plus an attempt-weighted Chicago-tenure total | `tests/test_derrick_rose_bulls_zone_charts.py`, `tests/test_player_season_totals.py` |
| `f5_lineup_table.py` | Bulls Lineup Table | `tests/test_f5_lineup_table.py` |
| `fga_leader_zone_charts.py` | Bulls FGA leaders of the 2020s | `tests/test_fga_leader_zone_charts.py` |
| `game_score_by_height.py` | Best Bulls game at every listed height since 2000 | `tests/test_game_score_by_height.py` |
| `height_ladder_cards.py` | Bulls' highest PPG at each listed height | Use the consuming family checks |
| `height_ladder_fetch.py` | Bulls' highest PPG at each listed height | Use the consuming family checks |
| `height_ladder_portraits.py` | Bulls' highest PPG at each listed height | Use the consuming family checks |
| `height_ladder_prep.py` | Bulls' highest PPG at each listed height | Use the consuming family checks |
| `height_ladder_threshold.py` | Bulls' highest PPG at each listed height | Use the consuming family checks |
| `hinrich_bulls_zone_charts.py` | Kirk Hinrich's eleven Bulls regular seasons plus a pooled Chicago-tenure total and a small-multiples cover | `tests/test_hinrich_bulls_zone_charts.py`, `tests/test_player_season_totals.py` |
| `impactful_bulls_bpm.py` | Most impactful Bull per season | `tests/test_impactful_bulls_bpm.py` |
| `impactful_bulls_bpm_columns.py` | The same BPM analysis as a stacked column chart | Use the consuming family checks |
| `jimmy_butler_bulls_zone_charts.py` | Jimmy Butler's Bulls regular seasons with 300+ Chicago FGA plus an attempt-weighted six-season tenure total | `tests/test_jimmy_butler_bulls_zone_charts.py`, `tests/test_player_season_totals.py` |
| `mock_post_demo.py` | A design-preview harness, not a post idea. Renders a full fake post (fictional roster, no network/cache needed) … | Use the consuming family checks |
| `opponent_elite_performance.py` | Which opponents the most elite Bulls player-games came against. Reuses `top_game_performances.py`'s validated lo… | `tests/test_opponent_elite_performance.py` |
| `payroll_vs_wins.py` | Build the Bulls payroll-share vs win-percentage chart asset for Canva. | `tests/test_payroll_vs_wins.py` |
| `rebounds_age_ladder.py` | Rebound counterpart to `stocks_age_ladder.py` | `tests/test_rebounds_age_ladder.py` |
| `rebounds_age_ladder_merger.py` | Same rebound age ladder from the 1976-77 merger onward. NBA.com's LeagueDashPlayerStats endpoint begins in 1996-… | `tests/test_rebounds_age_ladder_merger.py` |
| `regular_season_gamebook.py` | Four independent regular-season postgame experiments | `tests/test_regular_season_gamebook.py` |
| `rim_vs_three_pps_landscape.py` | Rim vs. Three points per shot | `tests/test_rim_vs_three_pps_landscape.py` |
| `scoring_age_ladder.py` | Highest-scoring Bulls season at every age since 2000. NBA.com's season-age field as listed, regular-season Chica… | `tests/test_stocks_age_ladder.py`, `tests/test_scoring_age_ladder.py`, `tests/test_assist_age_ladder.py` |
| `scoring_by_location.py` | Scoring by location | `tests/test_scoring_by_location.py` |
| `scoring_leaps.py` | Bulls' biggest year-over-year scoring leaps since 2000 | `tests/test_scoring_leaps.py` |
| `season_opener_performances.py` | Best Bulls season-opener performances since 2000 | `tests/test_season_opener_performances.py` |
| `season_shape_post.py` | The Shape of the Season | Use the consuming family checks |
| `stocks_age_ladder.py` | Defensive counterpart | `tests/test_stocks_age_ladder.py` |
| `summer_league_report.py` | Summer League Report v1 + v2 | `tests/test_summer_league_report.py` |
| `summer_league_sticky_stats.py` | 2026 Summer League sticky shot-profile prototype | `tests/test_summer_league_sticky_stats.py` |
| `three_point_leaders.py` | Bulls' most accurate three-point shooter every season since 2010-11 | `tests/test_three_point_leaders.py` |
| `top_game_performances.py` | Top Bulls game performances by decade | `tests/test_bulls_rookie_leaderboard.py`, `tests/test_top_game_performances.py` |
| `zone_deep_dive.py` | Volume *and* efficiency inside a single shot zone | Use the consuming family checks |
