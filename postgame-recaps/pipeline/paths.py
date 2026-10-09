"""Where the postgame recap keeps things. Every pipeline script takes its folders from here.

    postgame-recaps/
      pipeline/                 this code
      baselines/league-2025-26/ league averages the game breakdown is measured against
      seasons/<season>/<id>/    each Bulls game's NBA.com feeds; as-posted/ holds what the slides used
      stress-tests/<id>/        saved test games (2025-26 Bulls games, dry runs on other teams)
      logos/, portraits/        NBA.com images (portraits are not committed)
    output/postgame-recap/<id>/ recap.json, zones.png, slides/, caption.txt (scratch, not committed)
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
BASELINES = ROOT / "baselines"
LOGOS = ROOT / "logos"
PORTRAITS = ROOT / "portraits"
STRESS = ROOT / "stress-tests"
OUTPUT = REPO / "output" / "postgame-recap"
BULLS = 1610612741


def season_of(game_id: str) -> str:
    """NBA game IDs carry the season's start year in digits 4 and 5: 0012600030 is 2026-27."""
    year = 2000 + int(game_id[3:5])
    return f"{year}-{(year + 1) % 100:02d}"


def game_dir(game_id: str) -> Path:
    """A saved test game stays in stress-tests/; a dry run featuring another team goes there too;
    every Bulls game goes to its season folder."""
    test = STRESS / game_id
    other_team = int(os.environ.get("FOCUS_TEAM_ID", BULLS)) != BULLS
    return test if test.exists() or other_team else ROOT / "seasons" / season_of(game_id) / game_id


def shared_cache() -> Path:
    """The primary checkout's cache/ (league shot tables), found the same way from a worktree or main."""
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()
    return Path(common).parent / "cache"
