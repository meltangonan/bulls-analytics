# Bulls single-game points created

Top 15 + ties (16 rows), Chicago regular seasons 1996-97 through 2025-26.

Current chart: `assets/2026-10-02-v08-table-300dpi.png`, 7000×8098 at 300 DPI. Adds the requested, exactly verified NBA season rank to the approved v05 design without reducing the approved identity or stat sizes.

Prepare saved inputs: `venv/bin/python scripts/prototypes/points_created_games_data.py`.
Enrich NBA ranks: `venv/bin/python scripts/prototypes/points_created_games_nba_ranks.py` (run after selection preparation).
Render: `venv/bin/python scripts/prototypes/points_created_games_table.py --final --output output/points-created-games/table-300dpi.png`.
Checks: `tests/test_points_created_games_data.py`, `tests/test_points_created_games_nba_ranks.py`; reused NBA parser and bounds checks.

Source trail: `data/README.md`, `data/verification-summary.json`, `data/selection-proof.csv.gz`.
NBA ranks: `data/nba-game-ranks/README.md`, full league population/comparison proofs and verified ranks. Each game compares every NBA regular-season player-game in its own season, including other games by the same player. Exact competition ranks preserve ties; zero unresolved comparisons.
Canva assembly and copy: `data/canva-layout.json`. Notion owns the live brief, status, approval and publication history.

The saved two-page Canva copy preserves the recent season post's page design. User added a DeMar DeRozan cover photograph; both current page previews inspected for promotion QA. Typography, gradient overlays, trim and handle preserved. Both tool previews (450×600) checked. The user signed off QA and confirmed development complete; only Instagram publication remains. The connected previews were 450×600, and no full-size composed export was available. Promotion copy and distribution recommendations are recorded in Notion; no publication recorded.

Independent replay of Rose and DeRozan ranks and exact comparison leaderboards: `data/nba-game-ranks/leaderboards/`; reproducer `scripts/prototypes/points_created_games_nba_leaderboards.py`.
