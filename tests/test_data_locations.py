"""Repo-wide convention test: expensive data must not land in the ignored cache.

`cache/` is gitignored, so anything written there is destroyed by routine worktree
cleanup. That already cost this project 2,132 rate-limited play-by-play requests — about
fifty minutes — *after* the post built on them had shipped, because the images were saved
under the tracked `docs/visuals/` tree and the data behind them was not.

The rule is in `AGENTS.md` and `bulls/visuals.py`, but a rule nobody is reminded of is a
rule that gets broken by the next post. This test is the reminder: every `cache/` location
in the codebase is listed below with the reason it is allowed to be there, and adding a new
one fails until it is either justified here or moved to the post's tracked
`docs/visuals/<slug>/data/` folder.

Failing this test is not automatically a bug. It is a question: *if this folder were
deleted tonight, what would it cost to rebuild?* Cheap, licensed, or third-party content
belongs in `cache/`. Anything a published number rests on does not.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCHED = ("bulls", "scripts")

# Path expressions like `_REPO / "cache" / "headshots"` or `"cache/headshots"`.
CACHE_PATH = re.compile(r'/\s*"cache"\s*/\s*"([\w.\-]+)"|"cache/([\w.\-]+)')
CACHE_TOKEN = re.compile(r'/\s*"cache"')

# folder -> why it is allowed to live in an ignored cache.
ALLOWED = {
    "headshots": "third-party NBA portrait images, re-downloadable one request each",
    "fonts": "extraction of the licensed system Helvetica — DESIGN.md forbids committing it",
    "shot_charts": "league shot baseline, ~30 requests to rebuild",
    "hot_spots": "per-player zone splits, cheap to refetch",
    "scoring_by_location": "one league request to rebuild",
    "sl_sticky_stats_2026": "Summer League box scores, one tournament, cheap",
    "nba.com": "season game logs, one request per season",
}

# Modules that legitimately reference the cache root itself rather than a subfolder.
ALLOWED_BARE_CACHE = {"scripts/prototypes/season_shape_post.py"}


def _code_lines(path: Path):
    """Source lines with comments and docstring prose stripped out.

    The rule is discussed in prose in several modules; only real path construction
    should trip the check.
    """
    for number, line in enumerate(path.read_text().splitlines(), 1):
        code = line.split("#", 1)[0]
        if code.strip():
            yield number, code


def _python_files():
    for folder in SEARCHED:
        for path in sorted((ROOT / folder).rglob("*.py")):
            if "__pycache__" not in path.parts:
                yield path


def test_no_new_cache_locations_without_a_documented_reason():
    offenders = []
    for path in _python_files():
        for number, code in _code_lines(path):
            for match in CACHE_PATH.finditer(code):
                folder = match.group(1) or match.group(2)
                if folder not in ALLOWED:
                    rel = path.relative_to(ROOT)
                    offenders.append(f"{rel}:{number} writes to cache/{folder}")

    assert not offenders, (
        "New ignored-cache location(s):\n  "
        + "\n  ".join(offenders)
        + "\n\ncache/ is gitignored and is destroyed by worktree cleanup. If this data is "
          "slow or rate-limited to rebuild, or a published number rests on it, write it to "
          "docs/visuals/<slug>/data/ instead (see bulls/visuals.py). If it really is cheap, "
          "licensed, or third-party, add it to ALLOWED in this test with the reason."
    )


def _uses_bare_cache_root(code: str) -> bool:
    """True when `/ "cache"` is not followed by a subfolder.

    Written as a scan rather than a lookahead regex: an earlier lookahead version
    backtracked over the whitespace and flagged every subfolder use as a bare one.
    """
    for match in CACHE_TOKEN.finditer(code):
        if not code[match.end():].lstrip().startswith("/"):
            return True
    return False


def test_cache_root_is_not_written_to_directly():
    offenders = []
    for path in _python_files():
        rel = str(path.relative_to(ROOT))
        if rel in ALLOWED_BARE_CACHE:
            continue
        for number, code in _code_lines(path):
            if _uses_bare_cache_root(code):
                offenders.append(f"{rel}:{number}")
    assert not offenders, (
        "Writing to the cache root scatters files with no owner: " + ", ".join(offenders)
    )


def test_the_assist_duos_season_data_is_tracked():
    """The specific regression this whole rule came from."""
    data = ROOT / "docs" / "visuals" / "2026-08-08-assist-duos" / "data" / "seasons"
    assert data.is_dir(), f"season data missing from the tracked tree: {data}"
    seasons = list(data.glob("assisted-baskets-*.csv"))
    assert len(seasons) == 26, f"expected 26 cached seasons, found {len(seasons)}"


def test_every_allowed_cache_folder_states_a_reason():
    """An allowlist without reasons decays into a list of whatever was there."""
    for folder, reason in ALLOWED.items():
        assert len(reason) > 20, f"{folder} needs a real justification, not '{reason}'"
