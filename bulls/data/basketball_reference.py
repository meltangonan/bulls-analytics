"""Season-level Advanced tables from Basketball Reference.

Basketball Reference publishes Box Plus/Minus, which NBA.com does not, and has
no public API. This module scrapes the team season pages, parses the Advanced
table, and caches the parsed result as a CSV the caller owns.

**The CSV belongs in the consuming post's ``data/`` folder, not in ``cache/``.**
Basketball Reference rate-limits scrapers, so a refetch is slow, and published
numbers rest on these values; ``cache/`` is gitignored and does not survive
worktree cleanup (``AGENTS.md``, ``bulls/visuals.py``). Callers pass the path.

Only the parsed table is kept. The raw pages are ~2 MB each and carry nothing
the CSV does not.
"""

from __future__ import annotations

import html
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

TEAM_URL = "https://www.basketball-reference.com/teams/{team}/{year}.html"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
REQUEST_DELAY_SECONDS = 3.5

# `data-stat` keys on the Advanced table. `name_display` is the player.
ADVANCED_FIELDS = (
    "games",
    "mp",
    "per",
    "ts_pct",
    "usg_pct",
    "ws",
    "obpm",
    "dbpm",
    "bpm",
    "vorp",
)
_NON_PLAYER_ROWS = ("", "Player", "Team Totals", "League Average")


def parse_advanced_table(page: str, year: int) -> list[dict]:
    """Parse one season's Advanced rows out of a team page.

    The table ships inside an HTML comment, so it is matched from its
    container rather than by walking a parsed DOM. Values are read by
    ``data-stat`` name, never by column position, so a Basketball Reference
    column reorder cannot silently shift them into the wrong field.
    """
    block = re.search(r'id="(?:all_)?advanced".*?(<table.*?</table>)', page, re.S)
    if not block:
        raise ValueError(f"No Advanced table found for {year}")

    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", block.group(1), re.S):
        if 'scope="col"' in row_html:  # the table's own header row
            continue
        cells = dict(
            re.findall(r'data-stat="([a-z_0-9]+)"[^>]*>(.*?)</t[dh]>', row_html, re.S)
        )
        name = html.unescape(
            re.sub(r"<[^>]+>", "", cells.get("name_display", ""))
        ).strip()
        if name in _NON_PLAYER_ROWS:
            continue
        record = {"season": year, "player_name": name}
        for field in ADVANCED_FIELDS:
            raw = re.sub(r"<[^>]+>", "", cells.get(field, "")).strip()
            record[field] = float(raw) if raw else None
        rows.append(record)
    if not rows:
        raise ValueError(f"Advanced table for {year} parsed to zero players")
    return rows


def fetch_season(team: str, year: int) -> list[dict]:
    """Fetch and parse one team-season, pausing to stay a polite scraper."""
    request = urllib.request.Request(
        TEAM_URL.format(team=team, year=year), headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        page = response.read().decode("utf-8", "replace")
    time.sleep(REQUEST_DELAY_SECONDS)
    return parse_advanced_table(page, year)


def load_or_fetch_advanced(
    csv_path: Path,
    years: range,
    team: str = "CHI",
    refresh: bool = False,
) -> pd.DataFrame:
    """Return the Advanced table for ``years``, reading ``csv_path`` if present.

    Pass ``refresh`` only when a season is live and its numbers have moved.
    """
    if csv_path.exists() and not refresh:
        frame = pd.read_csv(csv_path)
        missing = sorted(set(years) - set(frame["season"]))
        if not missing:
            return frame

    records = []
    for year in years:
        records.extend(fetch_season(team, year))
    frame = pd.DataFrame(records)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)
    return frame
