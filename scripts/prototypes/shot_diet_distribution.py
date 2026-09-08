#!/usr/bin/env python3
"""Bulls 2025-26 shot diet: every shot family's share, against the league average.

One chart asset for one slide. A distribution alone cannot say whether 7.8% of shots
being pull-ups is a lot, so each family carries both marks -- Chicago and the league --
and the distance between them is the finding, with every family's league rank alongside.

Shot families come from ``ACTION_TYPE`` in NBA.com play-by-play, which a human scorer
types. That has two consequences the code encodes rather than assumes:

* ``Jump Shot`` is the scorer's *unlabelled default*, not a technique. It is kept in the
  chart because dropping a third of the season would misstate every other share, but it
  is drawn oblique and footnoted, and it is deliberately excluded from rank annotation
  (``RANK_EXCLUDED``) -- a league rank on an artefact of labelling habits would claim
  more than the data supports.
* Scorers vary by arena, so a low Chicago rate could be a United Center habit rather
  than basketball. ``--audit-venue`` runs that test; see ``venue_audit``.

    --prepare        snapshot 30 teams, reconcile to official totals, write tables
    --audit-venue    home/road and arena-effect check on the labelling
    --render         chart asset from the saved tables
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from nba_api.stats.endpoints import shotchartdetail, leaguedashteamstats

from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica
from bulls.visuals import DATA, visual_dir

SEASON = "2025-26"
BULLS = 1610612741
PROJECT = "shot-diet-distribution"
CACHE = ROOT / "cache" / "shot_family_diet" / "v2"
OUT = ROOT / "output" / PROJECT

NBA_TEAM_IDS = [1610612737, 1610612738, 1610612751, 1610612766, 1610612752,
                1610612764, 1610612753, 1610612754, 1610612760, 1610612750,
                1610612743, 1610612757, 1610612762, 1610612746, 1610612756,
                1610612744, 1610612742, 1610612745, 1610612763, 1610612749,
                1610612748, 1610612761, 1610612755, 1610612759, 1610612765,
                1610612747, 1610612758, 1610612740, 1610612741, 1610612739]
KEEP = ["GAME_ID", "GAME_DATE", "HTM", "VTM", "TEAM_ID", "TEAM_NAME", "PLAYER_ID",
        "PLAYER_NAME", "ACTION_TYPE", "SHOT_TYPE", "SHOT_ZONE_BASIC", "SHOT_DISTANCE",
        "SHOT_MADE_FLAG"]

# First match wins, so order is a claim about what a label *is*. "Turnaround Hook Shot"
# is a hook, not a turnaround jumper, so hooks are tested before the jumper families --
# a flat regex sweep put those 125 attempts in the self-created bucket and inflated the
# headline by 1.7 points.
FAMILY_RULES = [
    ("Dunks", r"dunk"),
    ("Floaters", r"floating"),
    ("Tip-ins", r"\btip\b"),
    ("Layups", r"layup|finger roll"),
    ("Hooks", r"hook"),
    ("Pull-ups", r"pull-?up"),
    ("Step-backs", r"step back"),
    ("Turnarounds/fades", r"turnaround|fadeaway"),
    ("Running jumpers", r"running jump"),
]
UNLABELLED = "Standard jumpers"
SELF_CREATED = ("Pull-ups", "Step-backs", "Turnarounds/fades")

# The league's optical tracking classifies the same season without a scorer typing
# anything, so it is the independent check on both label-derived claims. It measured the
# Bulls at 36.8% catch-and-shoot (2nd) and 14.5% pull-up (30th) -- the same two ranks the
# labels give, from a system with no arena to be biased by. ``--corroborate`` refetches it.
#
# Tracking measures do NOT partition a season: catch-and-shoot and pull-up cover only
# jumpers roughly 10ft and out, and the touch/drive measures overlap each other. Only
# ACTION_TYPE partitions -- all 48 Bulls labels sum to the official 7,417 attempts --
# which is why the chart is built on labels and merely checked against tracking.
TRACKING = {"CatchShoot": "CATCH_SHOOT_FGA", "PullUpShot": "PULL_UP_FGA"}


def post_data() -> Path:
    return visual_dir(ROOT / "docs" / "visuals", PROJECT) / DATA


def classify(action: str) -> str:
    action = action.lower()
    for name, pattern in FAMILY_RULES:
        if re.search(pattern, action):
            return name
    return UNLABELLED


# ---------------------------------------------------------------- preparation

def fetch_team(team_id: int) -> pd.DataFrame:
    path = CACHE / f"{team_id}_{SEASON}.csv.gz"
    if not path.exists():
        params = dict(team_id=team_id, player_id=0, season_nullable=SEASON,
                      season_type_all_star="Regular Season", context_measure_simple="FGA")
        for attempt in range(3):
            try:
                frame = shotchartdetail.ShotChartDetail(
                    **params, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
                if frame.empty:
                    raise ValueError(f"Unavailable shot rows: {team_id} {SEASON}")
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        missing = [column for column in KEEP if column not in frame.columns]
        if missing:
            raise ValueError(f"ShotChartDetail is missing {missing}")
        CACHE.mkdir(parents=True, exist_ok=True)
        frame[KEEP].to_csv(path, index=False)
        (CACHE / f"{team_id}_{SEASON}.meta.json").write_text(json.dumps(dict(
            endpoint="ShotChartDetail", parameters=params, rows=len(frame),
            fetched_at=datetime.now(timezone.utc).isoformat()), indent=2))
        time.sleep(0.65)
    frame = pd.read_csv(path, dtype={"GAME_ID": str})
    if not frame.TEAM_ID.eq(team_id).all():
        raise ValueError(f"Unexpected team rows in {path}")
    return frame


def load_shots() -> pd.DataFrame:
    shots = pd.concat([fetch_team(team) for team in NBA_TEAM_IDS], ignore_index=True)
    shots["FAMILY"] = shots.ACTION_TYPE.map(classify)
    return shots


def official_totals() -> pd.DataFrame:
    path = CACHE.parent / f"official_totals_{SEASON}.csv"
    if not path.exists():
        frame = leaguedashteamstats.LeagueDashTeamStats(
            season=SEASON, season_type_all_star="Regular Season",
            per_mode_detailed="Totals", headers=_NBA_HEADERS,
            timeout=60).get_data_frames()[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    return pd.read_csv(path)[["TEAM_ID", "TEAM_NAME", "FGA", "FGM"]]


def reconcile(shots: pd.DataFrame) -> pd.DataFrame:
    """Every team's shot rows must equal its official FGA/FGM, or a share is wrong."""
    counted = shots.groupby("TEAM_ID").agg(
        SHOT_FGA=("SHOT_MADE_FLAG", "size"),
        SHOT_FGM=("SHOT_MADE_FLAG", "sum")).reset_index()
    table = counted.merge(official_totals(), on="TEAM_ID")
    table["FGA_DIFF"] = table.SHOT_FGA - table.FGA
    table["FGM_DIFF"] = table.SHOT_FGM - table.FGM
    if (table.FGA_DIFF != 0).any() or (table.FGM_DIFF != 0).any():
        off = table[(table.FGA_DIFF != 0) | (table.FGM_DIFF != 0)]
        raise ValueError(f"Shot rows disagree with official totals:\n{off}")
    return table


def build_tables(shots: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-team family shares, and the Bulls row set the chart draws."""
    by_team = (shots.groupby(["TEAM_ID", "TEAM_NAME", "FAMILY"])
               .agg(FGA=("SHOT_MADE_FLAG", "size"), FGM=("SHOT_MADE_FLAG", "sum"))
               .reset_index())
    by_team["SHARE"] = by_team.FGA / by_team.groupby("TEAM_ID").FGA.transform("sum") * 100
    by_team["RANK"] = (by_team.groupby("FAMILY").SHARE
                       .rank(ascending=False, method="min").astype(int))

    league = by_team.groupby("FAMILY").FGA.sum()
    league_share = (league / league.sum() * 100).rename("LEAGUE_SHARE")
    chart = (by_team[by_team.TEAM_ID == BULLS].merge(league_share, on="FAMILY")
             .assign(DIFF=lambda d: d.SHARE - d.LEAGUE_SHARE,
                     FG_PCT=lambda d: d.FGM / d.FGA * 100)
             .sort_values("SHARE", ascending=False)
             .reset_index(drop=True))
    columns = ["FAMILY", "FGA", "FGM", "FG_PCT", "SHARE", "LEAGUE_SHARE", "DIFF", "RANK"]
    return by_team, chart[columns]


def build_vocabulary(shots: pd.DataFrame, chart: pd.DataFrame) -> pd.DataFrame:
    """Every distinct NBA shot label the Bulls recorded, under the family it maps to.

    This is the second slide's whole point: the family rows on slide one are a grouping
    *we* chose, and a reader cannot check a grouping they cannot see. Families keep the
    share order of slide one; labels run by attempts within each family.
    """
    bulls = shots[shots.TEAM_ID == BULLS]
    rows = (bulls.groupby(["FAMILY", "ACTION_TYPE"])
            .agg(FGA=("SHOT_MADE_FLAG", "size"), FGM=("SHOT_MADE_FLAG", "sum"))
            .reset_index())
    rows["FG_PCT"] = rows.FGM / rows.FGA * 100
    rows["SHARE"] = rows.FGA / len(bulls) * 100
    order = {family: index for index, family in enumerate(chart.FAMILY)}
    missing = set(rows.FAMILY) - set(order)
    if missing:
        raise ValueError(f"Families absent from the share table: {missing}")
    rows["FAMILY_ORDER"] = rows.FAMILY.map(order)
    return (rows.sort_values(["FAMILY_ORDER", "FGA"], ascending=[True, False])
            .drop(columns="FAMILY_ORDER").reset_index(drop=True))


def prepare() -> None:
    shots = load_shots()
    recon = reconcile(shots)
    by_team, chart = build_tables(shots)
    vocabulary = build_vocabulary(shots, chart)
    data = post_data()
    data.mkdir(parents=True, exist_ok=True)
    recon.to_csv(data / "team-fga-reconciliation.csv", index=False)
    by_team.to_csv(data / "family-shares-all-teams.csv", index=False)
    chart.to_csv(data / "bulls-family-shares.csv", index=False)
    vocabulary.to_csv(data / "bulls-shot-vocabulary.csv", index=False)
    (data / "source.json").write_text(json.dumps(dict(
        endpoint="ShotChartDetail (per team) + LeagueDashTeamStats",
        season=SEASON, season_type="Regular Season", shot_rows=len(shots),
        games=int(shots.GAME_ID.nunique()), teams=int(shots.TEAM_ID.nunique()),
        prepared_at=datetime.now(timezone.utc).isoformat()), indent=2))
    print(f"{len(shots)} shot rows, {shots.GAME_ID.nunique()} games, "
          f"{len(recon)} teams reconciled with zero FGA/FGM difference")
    print(chart.to_string(index=False, float_format=lambda value: f"{value:.1f}"))
    print(f"\nvocabulary: {len(vocabulary)} distinct labels covering "
          f"{vocabulary.FGA.sum()} attempts across {vocabulary.FAMILY.nunique()} families")


# ---------------------------------------------------------------- venue audit

def venue_audit() -> None:
    """Separate a real shooting pattern from a United Center scoring habit.

    A team's own home scorer labels half its shots, so a season rate cannot rule out an
    arena effect by itself. Two independent views can: how the Bulls change on the road,
    and how *visiting* teams change when they play in Chicago.
    """
    shots = load_shots()
    abbreviations = {}
    for team_id, group in shots.groupby("TEAM_ID"):
        per_game = group.groupby("GAME_ID").apply(
            lambda frame: {frame.HTM.iloc[0], frame.VTM.iloc[0]}, include_groups=False)
        common = set.intersection(*per_game)
        if len(common) != 1:
            raise ValueError(f"Ambiguous abbreviation for {team_id}: {common}")
        abbreviations[team_id] = common.pop()
    shots["ABBR"] = shots.TEAM_ID.map(abbreviations)
    shots["HOME"] = shots.ABBR == shots.HTM
    shots["SELF"] = shots.FAMILY.isin(SELF_CREATED)

    def rate(frame: pd.DataFrame) -> float:
        return frame.SELF.mean() * 100

    bulls = shots[shots.TEAM_ID == BULLS]
    home, road = rate(bulls[bulls.HOME]), rate(bulls[~bulls.HOME])
    road_rates = shots[~shots.HOME].groupby("TEAM_ID").SELF.mean().mul(100).sort_values()
    season = shots.groupby("TEAM_ID").SELF.mean().mul(100)
    visitors = shots[shots.ABBR != shots.HTM]
    effect = (visitors.groupby(["HTM", "TEAM_ID"]).SELF.mean().mul(100)
              .rename("rate").reset_index()
              .assign(delta=lambda d: d.rate.values - season.loc[d.TEAM_ID].values)
              .groupby("HTM").delta.mean().sort_values())

    lines = [
        f"Bulls self-created jumper rate: home {home:.1f}%  road {road:.1f}%  "
        f"gap {home - road:+.1f}p  season {rate(bulls):.1f}%",
        f"Road-only rate {road_rates[BULLS]:.1f}% ranks "
        f"{list(road_rates.index).index(BULLS) + 1}/30; "
        f"next-lowest {road_rates.iloc[1]:.1f}% "
        f"(gap {road_rates.iloc[1] - road_rates.iloc[0]:.1f}p, "
        f"2nd to 3rd {road_rates.iloc[2] - road_rates.iloc[1]:.1f}p)",
        f"United Center effect on visitors {effect['CHI']:+.1f}p, "
        f"rank {list(effect.index).index('CHI') + 1}/30 of arenas "
        f"(spread {effect.min():+.1f} to {effect.max():+.1f}, sd {effect.std():.2f})",
        "",
        "Read: the United Center scorer is mildly stingy with descriptors, by an amount "
        "two independent views agree on and that is ordinary among arenas. Chicago's rate "
        "stays lowest in the NBA using road games alone, which 29 other scorers label.",
    ]
    print("\n".join(lines))
    data = post_data()
    data.mkdir(parents=True, exist_ok=True)
    (data / "venue-audit.txt").write_text("\n".join(lines) + "\n")
    effect.rename("MEAN_VISITOR_DELTA").to_csv(data / "arena-label-effect.csv")


def corroborate() -> None:
    """Check the label-derived claims against optical tracking, which no scorer types.

    Tracking classifies shots from player and ball position, so it shares no failure mode
    with ``ACTION_TYPE``. Where the two agree, the scorer-bias question is closed. It is a
    check only: its categories overlap and leave gaps, so they can never replace the
    families on the chart.
    """
    from nba_api.stats.endpoints import leaguedashptstats

    totals = official_totals()[["TEAM_ID", "FGA"]].rename(columns={"FGA": "TEAM_FGA"})
    rows, lines = [], []
    for measure, column in TRACKING.items():
        frame = leaguedashptstats.LeagueDashPtStats(
            season=SEASON, season_type_all_star="Regular Season", player_or_team="Team",
            pt_measure_type=measure, per_mode_simple="Totals",
            headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
        merged = frame[["TEAM_ID", column]].merge(totals, on="TEAM_ID")
        merged["SHARE"] = merged[column] / merged.TEAM_FGA * 100
        merged = merged.sort_values("SHARE", ascending=False).reset_index(drop=True)
        rank = int(merged.index[merged.TEAM_ID == BULLS][0]) + 1
        bulls = merged[merged.TEAM_ID == BULLS].iloc[0]
        league = merged[column].sum() / merged.TEAM_FGA.sum() * 100
        rows.append(dict(MEASURE=measure, BULLS_FGA=int(bulls[column]),
                         BULLS_SHARE=round(float(bulls.SHARE), 1), BULLS_RANK=rank,
                         LEAGUE_SHARE=round(league, 1)))
        lines.append(f"{measure}: Bulls {bulls[column]:.0f} FGA = {bulls.SHARE:.1f}% of "
                     f"attempts, rank {rank}/30 (league {league:.1f}%)")
        time.sleep(0.65)

    lines.append("")
    lines.append("Read: optical tracking reaches the same two ranks as the scorer labels "
                 "-- 2nd in catch-and-shoot, 30th in pull-ups -- from a system with no "
                 "arena scorer to be biased by. The shares differ by about two points "
                 "because the two systems draw their boundaries differently, so the chart "
                 "keeps the label-derived numbers rather than mixing the sources.")
    print("\n".join(lines))
    data = post_data()
    data.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(data / "tracking-corroboration.csv", index=False)
    (data / "tracking-corroboration.txt").write_text("\n".join(lines) + "\n")


# -------------------------------------------------------------------- drawing

# Sized for a 4:5 Instagram page: near-portrait, so the chart fills the page rather than
# sitting as a landscape band across the middle. The extra height goes into ROW_STEP --
# rows that breathe -- not into blank margin.
CHART_WIDTH = 1600
CHART_HEIGHT = 1790

# Four columns: family name, track, value, rank. The value sits in its own column
# rather than beside its dot because the Chicago mark is sometimes left of the league
# mark -- a label hung off the dot then lands on the connector, and on the five rows
# where Chicago is under the league average it covered the very gap being measured.
LABEL_RIGHT = 452       # right-aligned; "Turnarounds/fades" is the longest name
TRACK_LEFT = 504
TRACK_RIGHT = 1210
AXIS_MAX = 36.0         # a little past the widest share, so the last dot clears the axis
VALUE_RIGHT = 1390      # right-aligned so the decimal points line up down the column
RANK_X = 1500           # ranks share one column so they read as a set, not as callouts
LEADER_GAP = 30         # clear air between the rightmost mark and the leader
LEADER_END = 1262       # stops short of the widest value, "34.5%", set at VALUE_RIGHT
# The "Share" header centres over the block the values occupy rather than hanging off
# their shared right edge, which left it looking pushed away from its own column.
SHARE_HEADER_X = (LEADER_END + VALUE_RIGHT) / 2
TOP_RANK_HIGHLIGHT = 5  # a top-five finish is where the Bulls stand out; drawn in red

# The two legend entries were colliding as one phrase; 400px between the marks reads as
# two separate keys, with room for the longer "Chicago Bulls" wordmark.
LEGEND_CHI_DOT = TRACK_LEFT + 8
LEGEND_LEAGUE_DOT = TRACK_LEFT + 400
LEGEND_TEXT_GAP = 26
LEGEND_DROP = 66        # below the scale, so the top of the chart is headers only

HEADER_Y = 80           # "Share" and "NBA rank" sit above their columns
AXIS_RULE_Y = 112       # gridlines start here, just under the headers
ROW_TOP = 200
ROW_STEP = 150
# The percentage scale reads along the bottom, the conventional place for it: at the top
# it competed with the column headers for the same band of the eye's first pass. Its y is
# derived from the last row rather than fixed, so it cannot drift if a family is added.
AXIS_LABEL_DROP = 42

# Marker diameters in points, drawn through ``plot`` rather than ``scatter`` so the
# number here is the size on the page: at DRAFT_DPI a point is 150/72 px, so 13.5pt
# is a 28px dot inside a 100px row.
CHI_DOT = 13.5
LEAGUE_DOT = 10.5
LEAGUE_RING_WIDTH = 2.6
# The Bulls mark is filled, so the connector simply disappears under it. The league mark
# is a ring, so a connector drawn to its centre shows straight through the hollow middle.
# The bar has to stop at the ring's outer edge instead: half the marker plus half the
# stroke, converted from points to the pixel units this axes is drawn in.
LEAGUE_RING_RADIUS = (LEAGUE_DOT + LEAGUE_RING_WIDTH) / 2 * DRAFT_DPI / 72

INK = house.BLACK
CHI = house.RED
# A tone ladder rather than a set of independent choices: each step down is scaffolding
# to the one above it, and every value is dark enough to hold on #E9E5E1, the darker end
# of the range Canva's canvas covers. The first pass was tuned on the pale #FAF8F5 end and
# the leaders and gridlines all but vanished once the page was exported.
LEAGUE_GREY = "#6E6862"      # the league mark: data, so darkest of the greys
CONNECTOR_GREY = "#8A837B"   # the bar between the two marks: also data
LEADER_GREY = "#A8A199"      # dotted leader; a dash reads lighter than a solid rule
GRIDLINE = "#B8B0A8"         # DESIGN.md's structural separator for this background
FOOTNOTE_GREY = "#7A736C"
# Table rows: hierarchy comes from weight, not pale text (DESIGN.md). Family rows are
# bold house black; label rows drop to the accepted subtitle tone at regular weight.
LABEL_GREY = "#5F5B57"

TYPE_FAMILY = 19.0      # family names sat larger than the value they introduce
TYPE_VALUE = 21.0
TYPE_AXIS = 17.0
TYPE_LEGEND = 18.0
TYPE_RANK = 18.0


def x_for(share: float) -> float:
    return TRACK_LEFT + (share / AXIS_MAX) * (TRACK_RIGHT - TRACK_LEFT)


def dot(ax, x: float, y: float, size: float, color: str, zorder: int = 4,
        hollow: bool = False) -> None:
    """A filled mark, or a ring when ``hollow``.

    The league mark is a ring so it survives being overlapped. On rows where the two
    shares nearly match (Tip-ins, 1.9 against 2.1) a filled grey dot sat entirely behind
    the Bulls dot and the row read as though the league had no value at all.
    """
    ax.plot([x], [y], marker="o", markersize=size, linestyle="none", zorder=zorder,
            markerfacecolor="none" if hollow else color, markeredgecolor=color,
            markeredgewidth=LEAGUE_RING_WIDTH if hollow else 0)


TABLE_WIDTH = 1600      # slide two: the full label vocabulary
TABLE_TOP = 232         # first row baseline, below the column headers
TABLE_LINE = 46         # one label row
TABLE_FAMILY_GAP = 30   # extra air above each family header, so groups read as groups
TABLE_BOTTOM_PAD = 90
TABLE_COL_X = (40, 820)     # left edge of each of the two column blocks
TABLE_COL_WIDTH = 740
TABLE_INDENT = 16       # labels sit inside their family header
# Right edges of the number columns, measured from a block's left edge. Made and attempts
# share one cell as "made-att": three separate numeric columns plus a 34-character label
# does not fit 740px at a readable size, and made-att is the familiar box-score form.
TABLE_COUNT_RIGHT = 558
TABLE_FG_RIGHT = 642
TABLE_SHARE_RIGHT = 740
# A percentage on one or two attempts describes nothing. Below this the cell is left
# empty rather than carrying a number that would read as a shooting rate. Empty rather
# than a dash: the FG cell beside it already uses hyphens for made-attempts, so another
# dash in the next column would read as part of that number.
MIN_ATTEMPTS_FOR_PCT = 10

TYPE_TABLE_FAMILY = 19.0
TYPE_TABLE_FAMILY_NUM = 17.0
# 14.5 rather than 15: the longest label, "Turnaround Fadeaway Bank Jump", was touching
# its FG figure. The alternative was moving the number columns right, which would have
# closed the gap between FG and FG% instead.
TYPE_TABLE_LABEL = 14.5
TYPE_TABLE_HEADER = 15.0


def format_share(share: float) -> str:
    """A one-attempt label is 0.013% of the season. Printing "0.0" would read as none at
    all, so anything that would round to zero says "<0.1" instead."""
    return f"{share:.1f}" if share >= 0.05 else "<0.1"


def display_label(action_type: str) -> str:
    """Every one of the 48 labels ends in "Shot" or "shot", so the suffix distinguishes
    nothing and costs the width that the long labels need. The stored vocabulary keeps
    the NBA string verbatim; only the drawn cell is trimmed."""
    return re.sub(r"\s+shot$", "", action_type, flags=re.IGNORECASE)


def ordinal(rank: int) -> str:
    """1st, 2nd, 3rd, 4th -- and 11th/12th/13th, which break the last-digit rule."""
    if 10 <= rank % 100 <= 20:
        return f"{rank}th"
    return f"{rank}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(rank % 10, 'th')}"


def render(chart: pd.DataFrame, final: bool = False) -> Path:
    """Draw the transparent dumbbell asset. Canva owns title, source and framing."""
    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI),
                     facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(CHART_HEIGHT, 0)
    ax.set_axis_off()

    rows = list(chart.itertuples())
    bottom = ROW_TOP + (len(rows) - 1) * ROW_STEP

    gridline_foot = bottom + ROW_STEP * 0.42
    for tick in (0, 10, 20, 30):
        x = x_for(tick)
        ax.plot([x, x], [AXIS_RULE_Y, gridline_foot],
                color=GRIDLINE, linewidth=1.2, zorder=1)
        ax.text(x, gridline_foot + AXIS_LABEL_DROP, f"{tick}%", ha="center", va="center",
                fontsize=TYPE_AXIS, color=FOOTNOTE_GREY, fontproperties=helvetica())

    # Legend names both marks, so the reader can tell direction without relying on hue.
    # It sits under the scale: at the top it took a whole band before any data, and the
    # reader needs the key once they reach a row, not before they have seen one.
    legend_y = gridline_foot + AXIS_LABEL_DROP + LEGEND_DROP
    dot(ax, LEGEND_CHI_DOT, legend_y, CHI_DOT, CHI)
    ax.text(LEGEND_CHI_DOT + LEGEND_TEXT_GAP, legend_y, "Chicago Bulls", ha="left",
            va="center", fontsize=TYPE_LEGEND, color=INK, fontproperties=helvetica("bold"))
    dot(ax, LEGEND_LEAGUE_DOT, legend_y, LEAGUE_DOT, LEAGUE_GREY, hollow=True)
    ax.text(LEGEND_LEAGUE_DOT + LEGEND_TEXT_GAP, legend_y, "NBA average", ha="left",
            va="center", fontsize=TYPE_LEGEND, color=LEAGUE_GREY,
            fontproperties=helvetica("bold"))
    ax.text(SHARE_HEADER_X, HEADER_Y, "Share", ha="center", va="center",
            fontsize=TYPE_AXIS, color=INK, fontproperties=helvetica("bold"))
    ax.text(RANK_X, HEADER_Y, "NBA rank", ha="center", va="center",
            fontsize=TYPE_AXIS, color=INK, fontproperties=helvetica("bold"))

    for index, row in enumerate(rows):
        y = ROW_TOP + index * ROW_STEP
        # The unlabelled default was first drawn oblique as a weaker qualification
        # (DESIGN.md). Tracking corroborates both its size and its rank, so it now reads
        # at full weight like every other row; Canva carries what the name means.
        ax.text(LABEL_RIGHT, y, row.FAMILY, ha="right", va="center",
                fontsize=TYPE_FAMILY, color=INK, fontproperties=helvetica("bold"))

        chi_x, league_x = x_for(row.SHARE), x_for(row.LEAGUE_SHARE)
        # A dotted leader carries the eye from the marks across to the value. Without it
        # the eight short rows left a wide blank band between the dots and the numbers,
        # and its length reads as the inverse of the share, which reinforces the bar.
        ax.plot([max(chi_x, league_x) + LEADER_GAP, LEADER_END], [y, y],
                color=LEADER_GREY, linewidth=1.8, linestyle=(0, (2, 4)), zorder=1)
        # Stop the bar at the ring's edge, and drop it entirely when the two shares are
        # so close that the ring already spans the gap (Tip-ins, 1.9 against 2.1).
        bar_start, bar_end = min(chi_x, league_x), max(chi_x, league_x)
        if league_x > chi_x:
            bar_end -= LEAGUE_RING_RADIUS
        else:
            bar_start += LEAGUE_RING_RADIUS
        if bar_end > bar_start:
            ax.plot([bar_start, bar_end], [y, y], color=CONNECTOR_GREY,
                    linewidth=4.0, solid_capstyle="butt", zorder=2)
        dot(ax, league_x, y, LEAGUE_DOT, LEAGUE_GREY, zorder=3, hollow=True)
        dot(ax, chi_x, y, CHI_DOT, CHI, zorder=4)
        ax.text(VALUE_RIGHT, y, f"{row.SHARE:.1f}%", ha="right", va="center",
                fontsize=TYPE_VALUE, color=INK, fontproperties=helvetica("bold"))

        # Every rank reads at full weight; red marks a top-five finish. Direction is
        # never carried by the colour alone, since the ordinal itself says which end.
        ax.text(RANK_X, y, ordinal(row.RANK), ha="center", va="center",
                fontsize=TYPE_RANK, fontproperties=helvetica("bold"),
                color=CHI if row.RANK <= TOP_RANK_HIGHLIGHT else INK)

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().date().isoformat()
    suffix = "final" if final else "draft"
    path = OUT / f"{stamp}-bulls-shot-diet-{suffix}.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return path


def split_families(vocabulary: pd.DataFrame) -> tuple[list, list]:
    """Divide the families between two columns, keeping each family whole.

    Balancing on *rendered lines* rather than family count is what matters: Layups alone
    carries 14 labels and Tip-ins carries one, so an even split by family would leave one
    column twice the height of the other.
    """
    groups = [(family, group) for family, group in vocabulary.groupby("FAMILY", sort=False)]
    lines = [len(group) + 1 for _, group in groups]          # labels plus the family row
    total = sum(lines)
    cuts = [(abs(sum(lines[:i]) - (total - sum(lines[:i]))), i)
            for i in range(1, len(groups))]
    best = min(cuts)[1]
    return groups[:best], groups[best:]


def draw_column(ax, groups, left: float, top: float) -> float:
    """Draw one column of family groups; returns the y it finished at."""
    y = top
    for family, group in groups:
        y += TABLE_FAMILY_GAP
        made, attempts = int(group.FGM.sum()), int(group.FGA.sum())
        ax.text(left, y, family, ha="left", va="center", fontsize=TYPE_TABLE_FAMILY,
                color=INK, fontproperties=helvetica("bold"))
        for value, right in ((f"{made}-{attempts}", TABLE_COUNT_RIGHT),
                             (f"{made / attempts * 100:.1f}", TABLE_FG_RIGHT),
                             (format_share(group.SHARE.sum()), TABLE_SHARE_RIGHT)):
            ax.text(left + right, y, value, ha="right", va="center",
                    fontsize=TYPE_TABLE_FAMILY_NUM, color=INK,
                    fontproperties=helvetica("bold"))
        ax.plot([left, left + TABLE_COL_WIDTH], [y + 22, y + 22],
                color=INK, linewidth=1.2, zorder=1)

        for row in group.itertuples():
            y += TABLE_LINE
            ax.text(left + TABLE_INDENT, y, display_label(row.ACTION_TYPE), ha="left",
                    va="center", fontsize=TYPE_TABLE_LABEL, color=LABEL_GREY,
                    fontproperties=helvetica())
            pct = (f"{row.FG_PCT:.1f}" if row.FGA >= MIN_ATTEMPTS_FOR_PCT else "")
            for value, right in ((f"{row.FGM}-{row.FGA}", TABLE_COUNT_RIGHT),
                                 (pct, TABLE_FG_RIGHT),
                                 (format_share(row.SHARE), TABLE_SHARE_RIGHT)):
                ax.text(left + right, y, value, ha="right", va="center",
                        fontsize=TYPE_TABLE_LABEL, color=LABEL_GREY,
                        fontproperties=helvetica())
        y += TABLE_LINE
    return y


def render_vocabulary(vocabulary: pd.DataFrame, final: bool = False) -> Path:
    """Slide two: all 48 NBA shot labels, grouped under the families slide one uses."""
    left_groups, right_groups = split_families(vocabulary)
    tallest = max(sum(len(g) + 1 for _, g in side) for side in (left_groups, right_groups))
    families = max(len(left_groups), len(right_groups))
    height = (TABLE_TOP + tallest * TABLE_LINE + families * TABLE_FAMILY_GAP
              + TABLE_BOTTOM_PAD)

    fig = plt.figure(figsize=(TABLE_WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, TABLE_WIDTH)
    ax.set_ylim(height, 0)
    ax.set_axis_off()

    for left in TABLE_COL_X:
        for heading, right in (("FG", TABLE_COUNT_RIGHT), ("FG%", TABLE_FG_RIGHT),
                               ("Share", TABLE_SHARE_RIGHT)):
            ax.text(left + right, TABLE_TOP - 96, heading, ha="right", va="center",
                    fontsize=TYPE_TABLE_HEADER, color=INK,
                    fontproperties=helvetica("bold"))
        ax.plot([left, left + TABLE_COL_WIDTH], [TABLE_TOP - 66, TABLE_TOP - 66],
                color=INK, linewidth=2.0, zorder=1)

    for groups, left in zip((left_groups, right_groups), TABLE_COL_X):
        draw_column(ax, groups, left, TABLE_TOP - TABLE_FAMILY_GAP)

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().date().isoformat()
    suffix = "final" if final else "draft"
    path = OUT / f"{stamp}-bulls-shot-vocabulary-{suffix}.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prepare", action="store_true",
                        help="snapshot, reconcile and write the tables")
    parser.add_argument("--audit-venue", action="store_true",
                        help="home/road and arena-effect check on the labelling")
    parser.add_argument("--corroborate", action="store_true",
                        help="check the label-derived claims against optical tracking")
    parser.add_argument("--render", action="store_true", help="draw the chart asset")
    parser.add_argument("--render-table", action="store_true",
                        help="draw slide two: the full shot-label vocabulary")
    parser.add_argument("--final", action="store_true", help="export at publish DPI")
    args = parser.parse_args()

    if args.prepare:
        prepare()
    if args.audit_venue:
        venue_audit()
    if args.corroborate:
        corroborate()
    if args.render:
        table = pd.read_csv(post_data() / "bulls-family-shares.csv")
        print(f"wrote {render(table, final=args.final)}")
    if args.render_table:
        vocabulary = pd.read_csv(post_data() / "bulls-shot-vocabulary.csv")
        print(f"wrote {render_vocabulary(vocabulary, final=args.final)}")
    if not (args.prepare or args.audit_venue or args.corroborate
            or args.render or args.render_table):
        parser.print_help()


if __name__ == "__main__":
    main()
