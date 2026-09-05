"""Rank the biggest Bulls bench-scoring seasons since 1996-97 for Canva.

Every Bulls player-season is split into the games the player started and the
games he came off the bench, and the bench half is ranked by points. Ben Gordon's
2004-05 rookie year tops it by a margin larger than the gap between second and
tenth, which is the whole reason the post is a bar chart rather than a table.

**The coverage window is a wall, not a choice.** NBA.com's starter/bench split is
derived from the play-by-play archive, so it begins in 1996-97 and returns an
EMPTY frame -- not an error -- for anything earlier. Verified 2026-09-03: 1985-86,
1990-91 and 1995-96 each came back with 0 rows and nothing raised, while 1996-97
returned 12. `validate` asserts a non-zero bench row count for every season so a
silently truncated window fails here rather than shipping under an "all time"
headline. It also rules out framing the post as "since Jordan left": 1996-97 and
1997-98 are dynasty seasons and Steve Kerr and Toni Kukoc are in the data.

**The split counts appearances, not roles.** A player who started 40 games and
came off the bench 42 contributes only the 42 bench games, and his GP in the
bench response reads 42. That is the honest construction, but it lets a starter
who lost his job in February onto a sixth-man leaderboard on a half-season of
bench work. `MIN_BENCH_GAME_SHARE` requires 70% of a player's games to have been
bench games. It changes almost nothing in the top ten and does one useful thing:
without it Ben Gordon holds three of the top ten places on the strength of two
seasons he spent mostly starting, and the leaderboard stops being about the Bulls.

**No era adjustment, deliberately.** Raw totals across a 30-season window usually
measure league pace as much as the player, so this was checked rather than
assumed: the leader is from 2004-05, and 1996-97 and 2001-02 both reach the top
fifteen. The distribution is not sorted by recency, so the number stays literal.

Bench and starter halves are reconciled against the unsplit season row for every
player in every season, which is what catches a mis-scoped response. Team
attribution is never read off `TEAM_ABBREVIATION`: a team-filtered `LeagueDash*`
row carries the player's *last* team of the season, so filtering on it would
silently delete traded players whose stint is already correctly scoped
(DEVELOPMENT.md, Data Guardrails).

The renderer produces a transparent chart asset; Canva owns the title, subtitle,
source line, and page framing.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from matplotlib.patches import FancyBboxPatch

from bulls.config import API_DELAY, BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica, rendered_width
from bulls.visuals import visual_dir
from nba_api.stats.endpoints import leaguedashplayerstats

FIRST_SEASON_END_YEAR = 1997  # NBA.com's starter/bench split starts here. See module docstring.
LAST_SEASON_END_YEAR = 2026
MIN_BENCH_GAME_SHARE = 0.70
DEFAULT_TOP_N = 10
# The headline margin is always judged against the top ten, whatever the chart
# draws. On a fifteen-row board the second-to-last gap widens to 365 and the
# claim "his margin beats the rest of the board" would read as false -- but the
# claim the caption makes is about the top ten, and it stays true there.
CLAIM_DEPTH = 10
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 4
SNAPSHOT_TZ = ZoneInfo("America/Chicago")
PROJECT = "bench-points-season"

OUT = _REPO / "output" / "feed"
# Single-consumer data lives with its post from the first run, not in the ignored
# cache -- see AGENTS.md and tests/test_data_locations.py.
POST_DATA = visual_dir(_REPO / "docs" / "visuals", PROJECT) / "data"
RAW = POST_DATA / "raw"
# NBA's CDN serves no portrait for Nate Robinson, only the grey silhouette
# (DESIGN.md §5). This copy was hand-sourced for the 2026-08-20 height ladder;
# portraits here win over the shared cache so the post carries the image it
# actually renders.
PORTRAITS = POST_DATA / "portraits"

NBA_SPLIT_URL = (
    "https://www.nba.com/stats/players/traditional"
    "?PerMode=Totals&Season={season}&SeasonType=Regular%20Season"
    f"&TeamID={BULLS_TEAM_ID}&StarterBench={{split}}"
)

# Horizontal bars: the finding is a length comparison, and a 294-point gap is
# read instantly as length and slowly as a number. Ten rows at 1800 px wide give
# every surname a full row, so nothing is abbreviated or angled.
CHART_WIDTH = 2550
# The height is derived from the row count so the ten- and fifteen-row versions
# share one layout instead of two sets of hand-tuned constants. `chart_height`
# rounds up to a whole multiple of DRAFT_DPI, because matplotlib sizes figures in
# inches and a height that does not divide cleanly exports a pixel short.
MIN_VERTICAL_MARGIN = 60

# Row anatomy follows the ranked player-season grammar the account already uses
# on the scoring-leaps chart and the rookie leaderboard: portrait, then the name
# with the season raised beside it, then a quieter support line, then the mark.
# A reader who has seen either post can read this one without learning anything.
#
# No rank column. On a bar chart the ordering is already the longest thing on the
# page, so a numeral restates it -- and the rookie table's numbers earn their
# place only because a table has no length to read.
HEADSHOT_X = 158
# Portraits are drawn taller than the row pitch, so consecutive faces overlap
# slightly. NBA portraits carry a transparent background, so the overlap reads as
# a stack of players rather than as clipping -- and the size is the point: the
# face is the highest-stopping-power object on the chart (DESIGN.md §5). Upper
# rows take the higher z-order so no face is cut off by the one below it.
HEADSHOT_HALF = 112
# Top-anchored, not centred: the NBA CDN serves each player's *current* portrait,
# so a chart spanning 1996 to 2026 arrives with Gibson and White in Hornets teal
# and Portis in Heat white. Cropping to the head keeps the wrong jersey small
# (DESIGN.md §5).
#
# 0.64 is tuned against this layout, where the portrait's bottom edge lands on
# the row rule and the cut is visible. The cut has to clear the jersey entirely:
# at 0.78 a sliver of collar survived on most rows, and at 0.86 three rows became
# blocks of the wrong team's colour. 0.64 cuts at the beard or the jaw, above
# every collar, on all fifteen portraits. The flat edge is the deliberate cost of
# that -- a soft alpha fade removes it but was rejected (2026-09-03).
HEADSHOT_CROP_FRACTION = 0.64

NAME_X = 330            # left edge of the name / support column
BAR_LEFT = 1100
BAR_MAX_RIGHT = 2280    # the longest bar; the total sits to the right of it
VALUE_GAP = 26          # bar end to the points figure

ROW_HEIGHT = 195
# The bar is nearly the full row pitch, so the bars themselves become the page's
# banding and the reader gets weight as well as length. The remaining gutter is
# what keeps ten stacked bars from reading as one block.
BAR_HEIGHT = 108
BAR_RADIUS = 8

NAME_COLUMN_GAP = 30    # clearance the name column keeps off the bars
SEASON_GAP = 14         # name to the raised season label
NAME_RISE = 26          # name above the row centre, support line below it
SEASON_RISE = 42        # the season rides high beside the name, not under it
SUPPORT_DROP = 46

# This chart takes no theme. The page canvas changes from post to post, the asset
# is always transparent, and the only meaningful colours are Bulls red and the
# house near-black (DESIGN.md §2).
#
# #242424 is the account's black: nothing in a graphic is pure or near-pure black.
INK = "#242424"
# Every bar is Bulls red. The leader needs no second encoding: at 1,209 against
# 915 his bar is a third longer than anything else on the page, so colouring one
# bar differently would restate the ranking the length already states.
SUPPORT_GREY = "#5F5B57"   # games and per-game, subordinate to the name
SEASON_GREY = "#6E6963"
# Chart greys must read across the canvas range Canva owns (#FAF8F5 through at
# least #E9E5E1), so the row rule is set well above the lightest of them. It is
# the table grammar's one structural line: it groups a portrait, a name and a bar
# into a row without drawing a box around each, which at ten rows would read as a
# grid competing with the bars.
ROW_RULE = "#DCD6CE"
ROW_RULE_WIDTH = 1.1

NAME_SUFFIXES = {"jr.", "jr", "sr.", "sr", "ii", "iii", "iv", "v"}

# NBA.com stores names without diacritics, so the name it returns is a
# misspelling once it is set in 30 pt on a graphic. Keyed by player id rather
# than by string, because the string is exactly the thing being corrected.
NAME_OVERRIDES = {202703: "Nikola Mirotić", 389: "Toni Kukoč"}

# NBA portraits are not framed identically, so one crop fraction does not clear
# every collar. Nate Robinson sits high and small in his frame: at the shared
# 0.64 his Nuggets yellow still showed, and 0.52 cropped him visibly tighter than
# his neighbours. 0.56 clears the jersey and matches them. The drawn size scales
# by the same ratio as the crop, which keeps his head the same size as every
# other face -- a tighter crop at a fixed drawn size would magnify him instead.
CROP_FRACTIONS = {101126: 0.56}  # Nate Robinson

# Clear space kept either side of a portrait's content, in source pixels.
PORTRAIT_SIDE_PADDING = 18

SPLITS = {"bench": "Bench", "starter": "Starters", "total": None}

SEASON_COLUMNS = [
    "season",
    "season_end_year",
    "player_id",
    "player_name",
    "bench_games",
    "total_games",
    "bench_game_share",
    "bench_minutes",
    "bench_points",
    "bench_points_per_game",
    "bench_minutes_per_game",
    "total_points",
    "qualified",
]


@dataclass(frozen=True)
class ChartType:
    """Type sizing for the bench-points leaderboard at 2550 wide."""

    name: float = 34.0
    season: float = 20.0
    value: float = 36.0
    support: float = 23.0


CHART_TYPE = ChartType()


def season_label(end_year: int) -> str:
    """Return an NBA end year as an NBA.com season string."""
    return f"{end_year - 1}-{str(end_year)[-2:]}"


def display_season(end_year: int) -> str:
    """Return the season as it is printed on the chart."""
    return season_label(end_year)


def last_name(full_name: str) -> str:
    """Return the surname a Bulls fan would recognise on a crowded row.

    Generational suffixes are dropped and internal capitals preserved, so
    "Bobby Portis Jr." becomes Portis and "Zach LaVine" stays LaVine.
    """
    parts = [p for p in re.split(r"\s+", full_name.strip()) if p]
    while len(parts) > 1 and parts[-1].lower().strip(".") in NAME_SUFFIXES:
        parts.pop()
    return parts[-1] if parts else full_name


def portrait_label(ax, image_path, x, y, half_size, *, crop, zorder=5):
    """Draw a top-anchored portrait, widened when the player does not fit a square.

    `house.square_headshot_label` takes a square window centred on the image, and
    that clips anyone wider than tall in the drawn band: Coby White's hair loses
    43 px on the left and 107 px on the right, because his content is 636 px wide
    against a 486 px window and he sits right of the frame's centre.

    So the window's height is still the crop fraction -- that is what fixes how
    large the head is drawn -- but its width is taken from the portrait's own
    alpha bounding box, and it is centred on that content rather than on the
    image. Horizontal and vertical scale stay equal, so nothing is stretched; a
    wide player simply occupies a wider box and may overlap the name column,
    which he is drawn behind.

    Everyone whose content already fits the square is unaffected, so this needs
    no per-player table to maintain.

    A missing or unreadable file becomes a neutral placeholder square, so the
    builder never breaks on one absent portrait.
    """
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            FancyBboxPatch(
                (x - half_size, y - half_size), 2 * half_size, 2 * half_size,
                boxstyle="square,pad=0", facecolor="#DDD8D1", edgecolor="none",
                zorder=zorder,
            )
        )

    height, width = image.shape[:2]
    side = min(int(height * crop), width)
    band = image[:side]

    if band.shape[2] == 4:
        columns = np.where(band[..., 3].max(axis=0) > 0.04)[0]
    else:  # no alpha to measure; fall back to the plain square window
        columns = np.array([], dtype=int)

    if columns.size:
        centre = (int(columns.min()) + int(columns.max())) / 2
        wanted = int(columns.max() - columns.min()) + 2 * PORTRAIT_SIDE_PADDING
    else:
        centre, wanted = width / 2, side
    window = min(max(side, wanted), width)
    left = int(round(min(max(centre - window / 2, 0), width - window)))

    square = band[:, left:left + window]
    half_width = half_size * window / side
    if x - half_width < 0:
        raise ValueError(f"{Path(image_path).name} runs off the left edge of the chart.")

    return ax.imshow(
        square,
        extent=[x - half_width, x + half_width, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=zorder,
    )


def portrait_path(player_id: int) -> Path:
    """Return the portrait to draw, preferring this post's own hand-sourced copy."""
    local = PORTRAITS / f"{player_id}.png"
    return local if local.is_file() else house.HEADSHOT_CACHE / f"{player_id}.png"


def _fetch_frame(endpoint, **kwargs) -> pd.DataFrame:
    """Call one NBA.com endpoint, retrying the timeouts it hands out freely."""
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        time.sleep(API_DELAY * (1 + attempt * RETRY_BACKOFF))
        try:
            return endpoint(timeout=60, headers=_NBA_HEADERS, **kwargs).get_data_frames()[0]
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            print(f"  NBA.com timed out; retry {attempt + 1} of {RETRY_ATTEMPTS - 1}")
    raise RuntimeError(f"NBA.com did not respond after {RETRY_ATTEMPTS} attempts.") from last_error


def _cached_frame(path: Path, fetch) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    frame = fetch()
    RAW.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def fetch_split(end_year: int, split: str, *, refresh: bool = False) -> pd.DataFrame:
    """Return one season of Chicago-only totals for one starter/bench split.

    `team_id_nullable` is the only way NBA.com splits a traded player into
    stints, and it is applied to all three splits so bench, starter and total
    describe the same Bulls-only body of work and can be reconciled against each
    other.
    """
    path = RAW / f"chi-{split}-{end_year}.csv"
    if refresh:
        path.unlink(missing_ok=True)
    return _cached_frame(
        path,
        lambda: _fetch_frame(
            leaguedashplayerstats.LeagueDashPlayerStats,
            season=season_label(end_year),
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            team_id_nullable=BULLS_TEAM_ID,
            starter_bench_nullable=SPLITS[split],
        ),
    )


def build_table(refresh: bool = False) -> pd.DataFrame:
    """Return every Bulls bench player-season in the covered window."""
    rows = []
    for end_year in range(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR + 1):
        bench = fetch_split(end_year, "bench", refresh=refresh)
        starter = fetch_split(end_year, "starter", refresh=refresh)
        total = fetch_split(end_year, "total", refresh=refresh)
        _reconcile(end_year, bench, starter, total)

        frame = bench[["PLAYER_ID", "PLAYER_NAME", "GP", "MIN", "PTS"]].copy()
        frame.columns = ["player_id", "player_name", "bench_games", "bench_minutes", "bench_points"]
        totals = total[["PLAYER_ID", "GP", "PTS"]].copy()
        totals.columns = ["player_id", "total_games", "total_points"]
        frame = frame.merge(totals, on="player_id", how="left")
        if frame["total_games"].isna().any():
            missing = frame.loc[frame["total_games"].isna(), "player_name"].tolist()
            raise ValueError(f"{season_label(end_year)}: no unsplit season row for {missing}.")

        frame.insert(0, "season", season_label(end_year))
        frame.insert(1, "season_end_year", end_year)
        rows.append(frame)
        print(f"  {season_label(end_year)}: {len(frame)} bench player-seasons", flush=True)

    table = pd.concat(rows, ignore_index=True)
    table["bench_game_share"] = table["bench_games"] / table["total_games"]
    table["bench_points_per_game"] = table["bench_points"] / table["bench_games"]
    table["bench_minutes_per_game"] = table["bench_minutes"] / table["bench_games"]
    table["qualified"] = table["bench_game_share"] >= MIN_BENCH_GAME_SHARE
    return table[SEASON_COLUMNS]


def _reconcile(
    end_year: int, bench: pd.DataFrame, starter: pd.DataFrame, total: pd.DataFrame
) -> None:
    """Fail when a season's splits do not add back up to its unsplit totals.

    Two different failures are caught here. An empty bench frame means the season
    predates the play-by-play archive the split is derived from -- NBA.com returns
    no rows rather than an error, so nothing else would notice. A split that does
    not sum to the season total means the response was scoped differently from
    what the parameters claim, which is the failure mode that ships wrong numbers
    quietly. Neither is checkable from the bench response alone.
    """
    season = season_label(end_year)
    if bench.empty:
        raise ValueError(
            f"{season}: NBA.com returned no bench rows. The starter/bench split "
            f"begins in {season_label(FIRST_SEASON_END_YEAR)} and returns an empty "
            "frame rather than an error before it."
        )
    if total.empty:
        raise ValueError(f"{season}: NBA.com returned no unsplit season rows.")

    parts = (
        bench[["PLAYER_ID", "GP", "PTS"]]
        .rename(columns={"GP": "bench_gp", "PTS": "bench_pts"})
        .merge(
            starter[["PLAYER_ID", "GP", "PTS"]].rename(
                columns={"GP": "starter_gp", "PTS": "starter_pts"}
            ),
            on="PLAYER_ID",
            how="outer",
        )
        .merge(
            total[["PLAYER_ID", "PLAYER_NAME", "GP", "PTS"]].rename(
                columns={"GP": "total_gp", "PTS": "total_pts"}
            ),
            on="PLAYER_ID",
            how="outer",
        )
        .fillna({"bench_gp": 0, "bench_pts": 0, "starter_gp": 0, "starter_pts": 0})
    )
    broken = parts[
        (parts["bench_gp"] + parts["starter_gp"] != parts["total_gp"])
        | (parts["bench_pts"] + parts["starter_pts"] != parts["total_pts"])
    ]
    if not broken.empty:
        names = broken["PLAYER_NAME"].tolist()
        raise ValueError(
            f"{season}: bench + starters does not equal the season total for {names}."
        )


def build_leaders(table: pd.DataFrame, top_n: int = DEFAULT_TOP_N) -> pd.DataFrame:
    """Return the top qualified bench-scoring seasons, ranked."""
    if top_n < CLAIM_DEPTH:
        raise ValueError(f"The chart needs at least {CLAIM_DEPTH} rows, not {top_n}.")
    leaders = (
        table[table["qualified"]]
        .sort_values("bench_points", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    leaders["rank"] = leaders.index + 1
    leaders["display_name"] = [
        NAME_OVERRIDES.get(int(pid), name)
        for pid, name in zip(leaders["player_id"], leaders["player_name"])
    ]
    leaders["last_name"] = leaders["display_name"].map(last_name)
    return leaders


def validate(table: pd.DataFrame, leaders: pd.DataFrame) -> dict[str, object]:
    """Check the window, the qualification, and the claim the chart will make."""
    expected = LAST_SEASON_END_YEAR - FIRST_SEASON_END_YEAR + 1
    seasons = table["season_end_year"].nunique()
    if seasons != expected:
        raise ValueError(f"Expected {expected} seasons of bench data, found {seasons}.")
    empty = table.groupby("season_end_year")["bench_points"].count()
    if (empty == 0).any():
        raise ValueError(f"Seasons with no bench rows: {empty[empty == 0].index.tolist()}")
    if (table["bench_games"] > table["total_games"]).any():
        raise ValueError("A player recorded more bench games than games played.")
    if (table["bench_points"] > table["total_points"]).any():
        raise ValueError("A player scored more bench points than season points.")
    if len(leaders) < CLAIM_DEPTH:
        raise ValueError(f"Expected at least {CLAIM_DEPTH} qualified leaders, found {len(leaders)}.")
    if leaders["bench_game_share"].min() < MIN_BENCH_GAME_SHARE:
        raise ValueError("An unqualified season reached the leaderboard.")

    top, second = leaders.iloc[0], leaders.iloc[1]
    gap = int(top["bench_points"] - second["bench_points"])
    tail_gap = int(second["bench_points"] - leaders.iloc[CLAIM_DEPTH - 1]["bench_points"])
    # The post's claim, asserted rather than eyeballed: the leader's margin is
    # bigger than the whole rest of the board's spread. If a future season breaks
    # that, the chart is still correct but the caption is not.
    if gap <= tail_gap:
        raise ValueError(
            f"The leader's margin ({gap}) no longer exceeds the second-to-last "
            f"spread ({tail_gap}); the headline claim needs rewriting."
        )
    # The highest season the qualification rule threw out, so the audit line can
    # say what the threshold cost. There is no guarantee it exists -- a window
    # where every bench season clears the bar is unlikely but not impossible, and
    # assuming it did crashed the audit rather than the analysis.
    unqualified = table[~table["qualified"]].nlargest(1, "bench_points")
    cut = (
        {
            "cut_name": unqualified.iloc[0]["player_name"],
            "cut_season": unqualified.iloc[0]["season"],
            "cut_points": int(unqualified.iloc[0]["bench_points"]),
            "cut_share": float(unqualified.iloc[0]["bench_game_share"]),
        }
        if not unqualified.empty
        else {}
    )
    return {
        **cut,
        "seasons": seasons,
        "first_season": table["season"].min(),
        "last_season": table["season"].max(),
        "player_seasons": len(table),
        "qualified": int(table["qualified"].sum()),
        "leader_name": top["player_name"],
        "leader_season": top["season"],
        "leader_points": int(top["bench_points"]),
        "leader_games": int(top["bench_games"]),
        "leader_ppg": float(top["bench_points_per_game"]),
        "second_name": second["player_name"],
        "second_points": int(second["bench_points"]),
        "gap": gap,
        "tail_gap": tail_gap,
        "rows": len(leaders),
    }


def _content_above() -> float:
    """How far the tallest object in a row reaches above the row centre."""
    return 2 * HEADSHOT_HALF - ROW_HEIGHT / 2


def chart_height(rows: int) -> int:
    """Return the export height for a chart of this many rows."""
    span = (rows - 1) * ROW_HEIGHT
    needed = span + _content_above() + ROW_HEIGHT / 2 + 2 * MIN_VERTICAL_MARGIN
    return int(math.ceil(needed / DRAFT_DPI) * DRAFT_DPI)


def _first_row_y(rows: int, height: int) -> float:
    """Centre the rows in the export, absorbing the rounding into the margins."""
    content = (rows - 1) * ROW_HEIGHT + _content_above() + ROW_HEIGHT / 2
    return height - (height - content) / 2 - _content_above()


def _row_y(index: int, first_row_y: float) -> float:
    return first_row_y - index * ROW_HEIGHT


def render_chart(leaders: pd.DataFrame, date: str, *, final: bool = False) -> Path:
    """Render the transparent bench-points leaderboard for Canva."""
    rows = len(leaders)
    height = chart_height(rows)
    first_row_y = _first_row_y(rows, height)
    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none"
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")

    # No value axis. Every bar carries its own figure, so an axis would be a
    # second reading of the same numbers -- and the comparison the post makes is
    # between bars, not against a scale.
    longest = float(leaders["bench_points"].max())
    scale = (BAR_MAX_RIGHT - BAR_LEFT) / longest

    for index, row in leaders.iterrows():
        y = _row_y(index, first_row_y)

        # One rule above each row after the first. A rule under the last row
        # would close the list like a table footer, which is a claim the chart
        # does not make: this is the top ten of a longer field.
        if index:
            ax.plot(
                [0, CHART_WIDTH], [y + ROW_HEIGHT / 2, y + ROW_HEIGHT / 2],
                color=ROW_RULE, linewidth=ROW_RULE_WIDTH, zorder=0,
            )

        # The portrait's *bottom* sits on the row's bottom edge, so it can only
        # ever grow upward into the row above -- never down into the row below.
        # Anchoring on the row centre instead let a tall portrait break out of
        # both ends of its row, which reads as a misaligned image rather than a
        # deliberate overlap.
        crop = CROP_FRACTIONS.get(int(row["player_id"]), HEADSHOT_CROP_FRACTION)
        half = HEADSHOT_HALF * crop / HEADSHOT_CROP_FRACTION
        portrait_label(
            ax,
            portrait_path(int(row["player_id"])),
            HEADSHOT_X,
            y - ROW_HEIGHT / 2 + half,
            half,
            crop=crop,
            # Lower rows draw in front, so each face covers the shoulders of the
            # one above it. All of them sit *under* the text, so a portrait wide
            # enough to reach the name column runs behind the name.
            zorder=2.4 + index * 0.01,
        )

        # Full name rather than surname: with a portrait beside it the row has
        # the width for it, and "Coby White 2019-20" beside "Coby White 2022-23"
        # is the pair a reader most needs to tell apart.
        name = ax.text(
            NAME_X, y + NAME_RISE, row["display_name"], ha="left", va="center",
            fontsize=CHART_TYPE.name, color=INK,
            fontproperties=helvetica("bold"), zorder=3,
        )
        # The season rides high and italic beside the name, as it does on the
        # scoring-leaps chart and the rookie leaderboard: it identifies the row
        # without competing with the player for the reader's first glance.
        # It is also what sets the name column's width -- the longest name plus a
        # season is wider than any stat line -- so the bars start where this
        # label ends, not where the stat line ends.
        season = ax.text(
            NAME_X + rendered_width(ax, name) + SEASON_GAP, y + SEASON_RISE,
            display_season(int(row["season_end_year"])), ha="left", va="center",
            fontsize=CHART_TYPE.season, color=SEASON_GREY,
            fontproperties=helvetica("oblique"), zorder=3,
        )
        # Games and per-game: they stop 1,209 being read without knowing how many
        # bench appearances it took, and they make a short bar with a high
        # per-game figure legible as fewer chances rather than a worse season --
        # Augustin's 749 in 52 games against McDermott's 718 in 77. "Off the
        # bench" is not repeated; every row on the chart is a bench row.
        support = ax.text(
            NAME_X, y - SUPPORT_DROP,
            f"{int(row['bench_games'])} G, {row['bench_points_per_game']:.1f} PTS/G",
            ha="left", va="center",
            fontsize=CHART_TYPE.support, color=SUPPORT_GREY,
            fontproperties=helvetica("bold"), zorder=3,
        )
        # The name column is set from the data, so it has to be checked against
        # the bar rather than eyeballed once: a longer name next season silently
        # runs a label under a bar instead of failing.
        for artist, label in (
            (name, "name"), (season, "season label"), (support, "stat line"),
        ):
            right = artist.get_position()[0] + rendered_width(ax, artist)
            if right > BAR_LEFT - NAME_COLUMN_GAP:
                raise ValueError(
                    f"The {label} for {row['player_name']} runs into the bar column."
                )

        width = float(row["bench_points"]) * scale
        # Rounded ends rather than square: at 150 px tall a square bar reads as a
        # slab, and the radius is small enough not to distort length.
        ax.add_patch(
            FancyBboxPatch(
                (BAR_LEFT, y - BAR_HEIGHT / 2),
                width,
                BAR_HEIGHT,
                boxstyle=f"round,pad=0,rounding_size={BAR_RADIUS}",
                linewidth=0,
                facecolor=house.RED,
                zorder=2,
            )
        )

        # The totals stay near-black against the red bars: a red numeral beside a
        # red bar loses the contrast the figure needs to be read at feed size.
        value = ax.text(
            BAR_LEFT + width + VALUE_GAP, y,
            f"{int(row['bench_points']):,}", ha="left", va="center",
            fontsize=CHART_TYPE.value, color=INK,
            fontproperties=helvetica("bold"), zorder=3,
        )
        if BAR_LEFT + width + VALUE_GAP + rendered_width(ax, value) > CHART_WIDTH - 20:
            raise ValueError(f"The value label for {row['player_name']} runs off the chart.")

    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    variant = "" if rows == DEFAULT_TOP_N else f"-top{rows}"
    path = OUT / f"{date}-bulls-bench-points-leaders{variant}-{suffix}.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return path


def write_working_tables(table: pd.DataFrame, leaders: pd.DataFrame) -> tuple[Path, Path]:
    """Write every bench player-season and the ranked leaderboard."""
    POST_DATA.mkdir(parents=True, exist_ok=True)
    table_path = POST_DATA / "bulls-bench-player-seasons.csv"
    leaders_path = POST_DATA / "bench-points-leaders.csv"
    table.to_csv(table_path, index=False)
    leaders.to_csv(leaders_path, index=False)
    return table_path, leaders_path


def canva_copy_block(report: dict[str, object]) -> str:
    """Return the exact data-bound framing to paste around the chart asset."""
    audit = (
        f"AUDIT: {report['qualified']} of {report['player_seasons']} Bulls bench "
        f"player-seasons across {report['seasons']} seasons clear the "
        f"{MIN_BENCH_GAME_SHARE:.0%} bar; this chart shows the top {report['rows']}. "
        f"Leader line: {report['leader_points']:,} points in "
        f"{report['leader_games']} bench games ({report['leader_ppg']:.1f} per game)."
    )
    if "cut_name" in report:
        audit += (
            f" Highest excluded season: {report['cut_name']} {report['cut_season']}, "
            f"{report['cut_points']:,} points on {report['cut_share']:.0%} bench games."
        )
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: THE BEST BENCH SEASONS IN BULLS HISTORY",
            f"SUBTITLE: Points scored off the bench, {report['first_season']} to "
            f"{report['last_season']} — and one rookie who is still not close to being caught",
            "FOOTER: Data via nba.com | "
            f"{report['first_season']} to {report['last_season']} regular seasons | "
            f"Bench games only; min. {MIN_BENCH_GAME_SHARE:.0%} of games played off the bench | "
            "NBA.com's starter/bench split does not exist before 1996-97",
            f"NOTE: {report['leader_name']} scored {report['leader_points']:,} points off the "
            f"bench in {report['leader_season']} — {report['gap']} more than "
            f"{report['second_name']}, and a bigger margin than the {report['tail_gap']} points "
            f"separating 2nd from {CLAIM_DEPTH}th.",
            audit,
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Bulls bench-points season leaderboard chart asset."
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Refetch every cached NBA.com season response."
    )
    parser.add_argument(
        "--final", action="store_true", help="Export at final resolution after the draft is approved."
    )
    parser.add_argument(
        "--top", type=int, default=DEFAULT_TOP_N,
        help=f"How many seasons to rank (at least {CLAIM_DEPTH}). 10 and 15 are the built versions.",
    )
    args = parser.parse_args()

    snapshot = datetime.now(SNAPSHOT_TZ)
    table = build_table(refresh=args.refresh)
    leaders = build_leaders(table, args.top)
    report = validate(table, leaders)
    table_path, leaders_path = write_working_tables(table, leaders)
    house.ensure_headshots(leaders["player_id"].tolist())
    chart_path = render_chart(leaders, snapshot.date().isoformat(), final=args.final)

    print(f"Player seasons: {table_path}")
    print(f"Leaders:        {leaders_path}")
    print(f"Chart:          {chart_path}")
    print()
    print(f"{'#':>2} {'PLAYER':18} {'SEASON':8} {'PTS':>6} {'G':>4} {'PPG':>6} {'BENCH G%':>9}")
    for _, row in leaders.iterrows():
        print(
            f"{int(row['rank']):2d} {row['player_name'][:18]:18} {row['season']:8} "
            f"{int(row['bench_points']):6,d} {int(row['bench_games']):4d} "
            f"{row['bench_points_per_game']:6.1f} {row['bench_game_share']:8.0%}"
        )
    print()
    print(canva_copy_block(report))


if __name__ == "__main__":
    main()
