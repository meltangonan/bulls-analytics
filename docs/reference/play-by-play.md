# Play-by-play and lineups

## Assist attribution

`PlayByPlayV3` may name the assister only inside a description such as `(Butler 3 AST)` without
an assister ID. Reuse `assist_duos_fetch.surname_key` and `_name_variants`: fold diacritics, strip
generational suffixes and allow disambiguating first-name prefixes (`J.`, `Ty.`, `Ti.`).
Resolve within game then season, after collecting the season: an assister may have no other event.
The missing `III` normalization once dropped 417 Jimmy Butler assists; aggregate plausibility
is insufficient.

Reconcile extracted assists against official team *and player* box totals. Report gaps rather than
adjusting counts to hide them. The saved assist-duos audit reconciled 48,316 team assists across
26 seasons. Fetch play-by-play serially; concurrent calls are throttled. Post-specific season
extracts belong in the post's tracked `data/`, not disposable cache.

Two-man lineup minutes are unavailable before 2007-08 (`leaguedashlineups` returns no rows), so
since-2000 duo comparisons use games played together. Choose denominators against the oldest
season in the coverage window.

## pbpstats and five-man units

pbpstats parses NBA feeds; it is not an independent data provider. Use it for possession boundaries,
corrected events, on-court units and passer-to-scorer structure when that saves work. Keep NBA's
structured endpoint when it answers the question. Cache required pbpstats responses in the post's
tracked data because the public API can timeout or return 500/503.

API: https://api.pbpstats.com/docs ; parser: https://github.com/dblackrun/pbpstats . Inspect the current
endpoint shape before fetching across many seasons.

The rating boards qualify exact five-player units at 500 relevant possessions: `rORTG = ORTG −
LeagueORTG`; `rDRTG = LeagueDRTG − DRTG`. Positive means better in either board. The 3PT board has
two floors, 100 offensive possessions and 50 three-point attempts, because possessions alone can
qualify a 4-for-6 shooter. These are existing-post contracts, not defaults for every new analysis.

The public lineup response can cap a season at 500 rows sorted by time played. Retain a completeness
check proving the tail cannot hide a qualifier. Count nulls may mean zero in this specific feed;
missing identity, time or possession data still raises. Reconcile the actual schema before adopting
that rule elsewhere. Display order from PG to C is authored role metadata, not a provider field.
Keep calculations independent of the portrait/display ordering.
