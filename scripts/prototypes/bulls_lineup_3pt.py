"""Rank the best three-point shooting Bulls five-man lineups since 2000-01.

pbpstats supplies exact five-player lineup three-point makes and attempts along
with offensive possessions, so both halves of the qualification rule come from
one source.

Two thresholds are applied together, and the second one is the point of this
post. A possession minimum qualifies a per-possession rate; three-point
percentage is a per-attempt rate, and a 100-possession lineup can contain very
few three-point attempts — the 2001-02 median was 15. Ranking 100-possession
lineups by three-point percentage therefore puts 4-for-6 samples on top. The
attempts floor is what makes the ranking mean what it says.

Players are shown in functional lineup order from point guard through center;
that display order is editorial metadata, not a field supplied by pbpstats.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    export_dpi,
    helvetica,
    square_headshot_label,
)
from scripts.prototypes import bulls_lineup_rortg as rortg
from scripts.prototypes import bulls_lineup_rdrtg as rdrtg


PROJECT = "bulls-lineup-3pt-since-2000"
POST_DATE = "2026-08-31"
FIRST_SEASON = 2000
LAST_SEASON = 2025
TEAM_ID = "1610612741"
MIN_POSSESSIONS = 100
MIN_ATTEMPTS = 50
TOP_N = 10
API_ROOT = rortg.API_ROOT

OUT = _REPO / "output" / f"{POST_DATE}-{PROJECT}"
DATA = _REPO / "docs" / "visuals" / f"{POST_DATE}-{PROJECT}" / "data"
LINEUP_SOURCE = DATA / "pbpstats-bulls-lineup-3pt-2000-01-to-2025-26.csv"
FETCH_AUDIT = DATA / "pbpstats-lineup-fetch-audit.csv"
TOP_TEN = DATA / "bulls-lineup-3pt-top-10.csv"
SEASON_SNAPSHOTS = DATA / "season-lineup-source"

CHART_WIDTH = 1080
ROW_HEIGHT = 125
CHART_HEIGHT = 1350
POSITION_COLUMNS = ("PG", "SG", "SF", "PF", "C")

# Fields kept from the pbpstats lineup payload. FG3M/FG3A carry the ranking;
# the corner and above-the-break splits are retained so the heave question can
# be re-checked from the saved snapshot without refetching.
#
# pbpstats omits a zero rather than sending it: a lineup that went 0-for-1 from
# the corner reports Corner3FGA = 1 and Corner3FGM = null. So a missing count is
# a real zero and is coalesced, while a missing identity, time or possession
# field is a genuine gap and still raises.
IDENTITY_FIELDS = (
    "EntityId",
    "Name",
    "TeamAbbreviation",
    "GamesPlayed",
    "SecondsPlayed",
    "OffPoss",
)
COUNT_FIELDS = (
    "FG3M",
    "FG3A",
    "Corner3FGM",
    "Corner3FGA",
    "Arc3FGM",
    "Arc3FGA",
    "NonHeaveArc3FGM",
    "NonHeaveArc3FGA",
)
KEEP_FIELDS = (*IDENTITY_FIELDS, *COUNT_FIELDS)

LINEUP_REQUIRED = {"Season", *KEEP_FIELDS}

# The ten functional orders in the three-point result. pbpstats exposes lineup
# identities but not PG-to-C role slots, so this map is explicit and checked
# against both the source names and entity IDs before rendering.
POSITION_ORDER = {
    ("2005-06", "2199-2550-2732-2736-970"): (
        "Kirk Hinrich",
        "Ben Gordon",
        "Luol Deng",
        "Othella Harrington",
        "Tyson Chandler",
    ),
    ("2021-22", "1628366-1629750-201942-202696-203897"): (
        "Lonzo Ball",
        "Zach LaVine",
        "Javonte Green",
        "DeMar DeRozan",
        "Nikola Vucevic",
    ),
    ("2021-22", "1627936-1628366-1628396-201942-203897"): (
        "Lonzo Ball",
        "Alex Caruso",
        "Zach LaVine",
        "DeMar DeRozan",
        "Tony Bradley",
    ),
    ("2022-23", "1629632-1630172-201942-202696-203897"): (
        "Coby White",
        "Zach LaVine",
        "Patrick Williams",
        "DeMar DeRozan",
        "Nikola Vucevic",
    ),
    ("2017-18", "1626166-1626245-1628021-1628374-203200"): (
        "Cameron Payne",
        "Justin Holiday",
        "David Nwaba",
        "Lauri Markkanen",
        "Cristiano Felicio",
    ),
    ("2016-17", "1627835-200765-201577-202703-202710"): (
        "Rajon Rondo",
        "Jimmy Butler",
        "Paul Zipser",
        "Nikola Mirotic",
        "Robin Lopez",
    ),
    ("2005-06", "2199-2550-2732-2736-2804"): (
        "Kirk Hinrich",
        "Ben Gordon",
        "Luol Deng",
        "Andres Nocioni",
        "Tyson Chandler",
    ),
    ("2022-23", "1629632-1630172-1630245-201942-203083"): (
        "Coby White",
        "Ayo Dosunmu",
        "Patrick Williams",
        "DeMar DeRozan",
        "Andre Drummond",
    ),
    ("2024-25", "1628366-1630172-1630581-202696-203897"): (
        "Josh Giddey",
        "Lonzo Ball",
        "Zach LaVine",
        "Patrick Williams",
        "Nikola Vučević",
    ),
    ("2021-22", "1629632-1629750-201942-202696-203897"): (
        "Coby White",
        "Zach LaVine",
        "Javonte Green",
        "DeMar DeRozan",
        "Nikola Vucevic",
    ),
}


# Othella Harrington retired in 2008, before the NBA CDN portrait archive and
# before ESPN's headshot range, so both serve a silhouette. This Wikimedia
# portrait is a post-career photograph, not a playing-days headshot — the same
# compromise the rDRTG post made for Antonio Davis.
PROJECT_HEADSHOT_OVERRIDES = {
    970: DATA.parent / "assets" / "othella-harrington-cutout.png",
}
MIN_USABLE_HEADSHOT_BYTES = 20_000


HARRINGTON_SOURCE_URL = (
    "https://commons.wikimedia.org/wiki/Special:FilePath/"
    "Othella Harrington (51910110377) (cropped).jpg"
)
# Head and a little shoulder, in the source photograph's own pixels. A looser
# crop carries enough torso that the face lands small beside the NBA portraits,
# which are almost entirely head inside the same 0.72 face crop.
HARRINGTON_HEAD_BOX = (155, 0, 395, 285)
# Arena seating is far darker than either skin or the red polo, so the subject
# separates on brightness alone. Harrington is bald here, which is why this
# works: dark hair against dark seats would need a real matting tool.
HARRINGTON_BACKGROUND_MAX = 95


def build_harrington_cutout(destination: Path) -> Path:
    """Derive the Harrington portrait from its Wikimedia source, reproducibly."""
    from collections import deque
    from io import BytesIO

    import requests
    from PIL import Image, ImageFilter

    from bulls.graphics.house import NBA_PORTRAIT_SIZE, PORTRAIT_CROP_FRACTION

    response = requests.get(
        HARRINGTON_SOURCE_URL,
        headers={"User-Agent": "@chicagobullsdata analytics archive"},
        timeout=30,
    )
    response.raise_for_status()
    with Image.open(BytesIO(response.content)) as opened:
        source = opened.convert("RGBA").crop(HARRINGTON_HEAD_BOX)

    pixels = np.array(source)
    height, width = pixels.shape[:2]
    dark = pixels[:, :, :3].astype(int).max(axis=2) <= HARRINGTON_BACKGROUND_MAX

    background = np.zeros((height, width), dtype=bool)
    queue: deque = deque()
    for x in range(width):
        for y in (0, height - 1):
            if dark[y, x] and not background[y, x]:
                background[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if dark[y, x] and not background[y, x]:
                background[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and dark[ny, nx] and not background[ny, nx]:
                background[ny, nx] = True
                queue.append((ny, nx))

    # Keep only the largest connected subject region: unlit seat highlights that
    # never touch an edge survive the flood fill and would render as speckle.
    subject = ~background
    labels = np.zeros((height, width), dtype=int)
    current = 0
    largest = (0, 0)
    for sy in range(height):
        for sx in range(width):
            if subject[sy, sx] and labels[sy, sx] == 0:
                current += 1
                size = 0
                blob: deque = deque([(sy, sx)])
                labels[sy, sx] = current
                while blob:
                    y, x = blob.popleft()
                    size += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if (
                            0 <= ny < height
                            and 0 <= nx < width
                            and subject[ny, nx]
                            and labels[ny, nx] == 0
                        ):
                            labels[ny, nx] = current
                            blob.append((ny, nx))
                if size > largest[1]:
                    largest = (current, size)

    pixels[:, :, 3] = np.where(labels == largest[0], 255, 0)
    cut_out = Image.fromarray(pixels)
    cut_out.putalpha(cut_out.getchannel("A").filter(ImageFilter.GaussianBlur(0.8)))

    canvas_w, canvas_h = NBA_PORTRAIT_SIZE
    crop_side = int(canvas_h * PORTRAIT_CROP_FRACTION)
    scale = min(crop_side / cut_out.width, crop_side / cut_out.height)
    resized = cut_out.resize(
        (max(1, int(cut_out.width * scale)), max(1, int(cut_out.height * scale))), Image.LANCZOS
    )
    canvas = Image.new("RGBA", NBA_PORTRAIT_SIZE, (0, 0, 0, 0))
    canvas.paste(
        resized, ((canvas_w - resized.width) // 2, max(0, crop_side - resized.height)), resized
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)
    return destination


def headshot_path(player_id: int) -> Path:
    """Return a project-specific portrait when one is part of this post."""
    return PROJECT_HEADSHOT_OVERRIDES.get(int(player_id), HEADSHOT_CACHE / f"{int(player_id)}.png")


def ensure_post_headshots(player_ids: list[int]) -> None:
    """Cache NBA portraits and refuse to render a silhouette."""
    from bulls.graphics.house import ensure_headshots

    wanted = {int(value) for value in player_ids}
    ensure_headshots(sorted(wanted - set(PROJECT_HEADSHOT_OVERRIDES)))
    harrington = PROJECT_HEADSHOT_OVERRIDES[970]
    if 970 in wanted and not harrington.is_file():
        build_harrington_cutout(harrington)
    silhouettes = [
        player_id
        for player_id in wanted
        if not headshot_path(player_id).is_file()
        or headshot_path(player_id).stat().st_size < MIN_USABLE_HEADSHOT_BYTES
    ]
    if silhouettes:
        raise ValueError(f"No usable portrait for player IDs {sorted(silhouettes)}")


def season_label(start_year: int) -> str:
    return f"{start_year:04d}-{(start_year + 1) % 100:02d}"


def _lineup_params(season: str) -> dict[str, str]:
    return {"Season": season, "SeasonType": "Regular Season", "Type": "Lineup", "TeamId": TEAM_ID}


def _validated_lineup_response(payload: dict, season: str) -> tuple[list[dict], dict]:
    rows = payload.get("multi_row_table_data")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"pbpstats returned no lineup rows for {season}")
    missing = set(KEEP_FIELDS) - set(rows[0])
    if missing:
        raise ValueError(f"pbpstats lineup rows for {season} are missing: {sorted(missing)}")
    if {str(row.get("TeamAbbreviation")) for row in rows} != {"CHI"}:
        raise ValueError(f"pbpstats returned a non-Bulls lineup for {season}")
    seconds = pd.Series([float(row.get("SecondsPlayed") or 0) for row in rows])
    if not seconds.is_monotonic_decreasing:
        raise ValueError(f"pbpstats lineup rows are not minutes-sorted for {season}")

    # The endpoint caps a season at 500 rows, sorted by time played. That drops
    # only the smallest lineups, so the audit records the floor: a truncated
    # season is safe for this post exactly while its smallest retained lineup
    # sits far below the possession threshold.
    floor_poss = int(min(float(row.get("OffPoss") or 0) for row in rows))
    audit = {
        "Season": season,
        "RowsReturned": len(rows),
        "Truncated": len(rows) >= 500,
        "SmallestRetainedOffPoss": floor_poss,
        "LineupSecondsPlayed": int(seconds.sum()),
        "QualifyingLineups": sum(
            float(row.get("OffPoss") or 0) >= MIN_POSSESSIONS
            and float(row.get("FG3A") or 0) >= MIN_ATTEMPTS
            for row in rows
        ),
    }
    if audit["Truncated"] and floor_poss >= MIN_POSSESSIONS:
        raise ValueError(
            f"{season} was truncated at a lineup still above the {MIN_POSSESSIONS}-possession "
            f"threshold (floor {floor_poss}); qualifying lineups may be missing"
        )
    return rows, audit


def fetch_source_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch and save lineup rows plus a per-season completeness audit."""
    DATA.mkdir(parents=True, exist_ok=True)
    SEASON_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    lineup_rows: list[dict] = []
    audit_rows: list[dict] = []

    for start_year in range(FIRST_SEASON, LAST_SEASON + 1):
        season = season_label(start_year)
        snapshot_path = SEASON_SNAPSHOTS / f"{season}.json"
        if snapshot_path.is_file():
            snapshot = json.loads(snapshot_path.read_text())
            season_rows = snapshot["rows"]
            audit = snapshot["audit"]
            print(f"Loaded cached {season}")
        else:
            payload = rortg.get_json("/get-totals/nba", _lineup_params(season))
            rows, audit = _validated_lineup_response(payload, season)
            season_rows = []
            for row in rows:
                off_poss = int(row.get("OffPoss") or 0)
                if off_poss <= 0:
                    continue
                absent = [field for field in IDENTITY_FIELDS if row.get(field) is None]
                if absent:
                    if off_poss >= MIN_POSSESSIONS:
                        raise ValueError(
                            f"A qualifying {season} lineup is missing {absent}: {row.get('EntityId')}"
                        )
                    continue
                record = {"Season": season}
                record.update({field: row[field] for field in IDENTITY_FIELDS})
                record.update({field: int(row.get(field) or 0) for field in COUNT_FIELDS})
                season_rows.append(record)
            snapshot_path.write_text(
                json.dumps(
                    {
                        "source": f"{API_ROOT}/get-totals/nba",
                        "parameters": _lineup_params(season),
                        "audit": audit,
                        "rows": season_rows,
                    },
                    indent=2,
                )
                + "\n"
            )
            print(f"Fetched and saved {season}")
        lineup_rows.extend(season_rows)
        audit_rows.append(audit)

    lineups = pd.DataFrame(lineup_rows).sort_values(
        ["Season", "SecondsPlayed"], ascending=[True, False], kind="stable"
    )
    audit = pd.DataFrame(audit_rows).sort_values("Season", kind="stable")
    lineups.to_csv(LINEUP_SOURCE, index=False)
    audit.to_csv(FETCH_AUDIT, index=False)
    return lineups, audit


def load_source_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = [path for path in (LINEUP_SOURCE, FETCH_AUDIT) if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing source snapshots; run with --refresh: "
            + ", ".join(str(path) for path in missing)
        )
    return pd.read_csv(LINEUP_SOURCE, dtype={"EntityId": str}), pd.read_csv(FETCH_AUDIT)


def prepare_ranking(
    lineups: pd.DataFrame,
    *,
    min_possessions: int = MIN_POSSESSIONS,
    min_attempts: int = MIN_ATTEMPTS,
    top_n: int = TOP_N,
) -> pd.DataFrame:
    missing = LINEUP_REQUIRED - set(lineups)
    if missing:
        raise ValueError(f"Lineup source is missing columns: {sorted(missing)}")
    if lineups.duplicated(["Season", "EntityId"]).any():
        raise ValueError("Duplicate season-lineup rows in pbpstats source")

    frame = lineups.copy()
    numeric = ["OffPoss", "FG3M", "FG3A", "SecondsPlayed", "GamesPlayed"]
    if frame[numeric].isna().any().any():
        raise ValueError("A lineup is missing possessions, three-point totals or time")
    if (frame["OffPoss"] <= 0).any():
        raise ValueError("Offensive possessions must be positive")
    if (frame["FG3M"] > frame["FG3A"]).any():
        raise ValueError("A lineup has more three-point makes than attempts")

    frame["Fg3Pct"] = 100 * frame["FG3M"] / frame["FG3A"].replace(0, np.nan)
    frame["Minutes"] = frame["SecondsPlayed"] / 60

    eligible = frame.loc[
        (frame["OffPoss"] >= min_possessions) & (frame["FG3A"] >= min_attempts)
    ].copy()
    if len(eligible) < top_n:
        raise ValueError(
            f"Only {len(eligible)} lineups reached {min_possessions} possessions and "
            f"{min_attempts} attempts; {top_n} are required."
        )
    rows = (
        eligible.sort_values(
            ["Fg3Pct", "FG3A", "Season", "Name"],
            ascending=[False, False, True, True],
            kind="stable",
        )
        .head(top_n)
        .reset_index(drop=True)
    )
    rows.insert(0, "Rank", np.arange(1, len(rows) + 1))

    for index, row in rows.iterrows():
        key = (str(row["Season"]), str(row["EntityId"]))
        order = POSITION_ORDER.get(key)
        if order is None:
            raise ValueError(f"No PG-to-C display order recorded for {key}")
        if set(order) != rdrtg._source_names(row["Name"]):
            raise ValueError(f"Position order does not match source names for {key}")
        source_pairs = dict(
            zip(
                [part.strip() for part in str(row["Name"]).split(",")],
                str(row["EntityId"]).split("-"),
            )
        )
        for position, player in zip(POSITION_COLUMNS, order):
            rows.loc[index, position] = player
            rows.loc[index, f"{position}_LABEL"] = rdrtg._surname(player)
            rows.loc[index, f"{position}_ID"] = int(source_pairs[player])

    if not rows["Fg3Pct"].is_monotonic_decreasing:
        raise ValueError("Selected lineups are not ordered by three-point percentage")
    return rows


def write_top_ten(rows: pd.DataFrame) -> Path:
    columns = [
        "Rank",
        "Season",
        "EntityId",
        *POSITION_COLUMNS,
        "GamesPlayed",
        "Minutes",
        "OffPoss",
        "FG3M",
        "FG3A",
        "Fg3Pct",
    ]
    table = rows[columns].copy()
    for column in ["Minutes", "Fg3Pct"]:
        table[column] = table[column].round(3)
    TOP_TEN.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(TOP_TEN, index=False)
    return TOP_TEN


def _pct_label(value: float) -> str:
    return f"{round(float(value), 1):.1f}%"


def render_chart(rows: pd.DataFrame, *, final: bool = False) -> Path:
    theme = DEFAULT_THEME
    player_ids = [
        int(row[f"{position}_ID"]) for _, row in rows.iterrows() for position in POSITION_COLUMNS
    ]
    ensure_post_headshots(player_ids)
    fig = plt.figure(figsize=(CHART_WIDTH / DRAFT_DPI, CHART_HEIGHT / DRAFT_DPI))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, CHART_HEIGHT)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    first_row_y = CHART_HEIGHT - 76
    position_x = {"PG": 180, "SG": 334, "SF": 488, "PF": 642, "C": 796}
    x_metric = 960
    for index, row in rows.iterrows():
        y = first_row_y - index * ROW_HEIGHT
        ax.plot([145, 903], [y, y], color=theme.accent, lw=1.2, solid_capstyle="round", zorder=1)
        ax.text(
            125,
            y + 32,
            str(row["Season"]),
            ha="right",
            va="center",
            fontsize=11,
            color=theme.muted,
            fontproperties=helvetica("bold_oblique"),
        )
        for position in POSITION_COLUMNS:
            x = position_x[position]
            player_id = int(row[f"{position}_ID"])
            square_headshot_label(
                ax,
                headshot_path(player_id),
                x,
                y + 11,
                49,
                zorder=3,
                face_fraction=0.72,
            )
            ax.text(
                x,
                y - 56,
                row[f"{position}_LABEL"],
                ha="center",
                va="center",
                fontsize=7.4,
                color=theme.ink,
                fontproperties=helvetica("bold"),
                zorder=5,
            )
        # Makes/attempts and possessions sit on their own lines: the single-line
        # form overflowed the pill on the widest row (52/103 · 314 POSS) and was
        # clipped at the chart edge.
        ax.add_patch(
            FancyBboxPatch(
                (x_metric - 57, y - 42),
                114,
                84,
                boxstyle="round,pad=0,rounding_size=13",
                facecolor="#B5123C",
                edgecolor="none",
                zorder=3,
            )
        )
        ax.text(
            x_metric,
            y + 18,
            _pct_label(row["Fg3Pct"]),
            ha="center",
            va="center",
            fontsize=16,
            color="#FFFFFF",
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        ax.text(
            x_metric,
            y - 8,
            f"{int(row['FG3M'])}/{int(row['FG3A'])}",
            ha="center",
            va="center",
            fontsize=8.4,
            color="#FFFFFF",
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        ax.text(
            x_metric,
            y - 26,
            f"{int(row['OffPoss'])} POSS",
            ha="center",
            va="center",
            fontsize=7.2,
            color="#FFFFFF",
            fontproperties=helvetica("oblique"),
            zorder=4,
        )

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{POST_DATE}-bulls-lineup-3pt-top-10.png"
    fig.savefig(path, dpi=export_dpi(final), transparent=True)
    plt.close(fig)
    return path


def canva_copy_block(rows: pd.DataFrame) -> str:
    leader = rows.iloc[0]
    leader_names = " / ".join(str(leader[pos]) for pos in POSITION_COLUMNS)
    return "\n".join(
        [
            "=== CANVA COPY (DATA-BOUND) ===",
            "",
            "TITLE: THE BULLS’ BEST THREE-POINT SHOOTING LINEUPS SINCE 2000",
            "",
            "SUBTITLE: Chicago’s top five-man units by three-point percentage",
            "",
            f"LEAD NOTE: {leader_names} ranked first at "
            f"{_pct_label(leader['Fg3Pct'])} on {int(leader['FG3M'])}-of-{int(leader['FG3A'])}.",
            "",
            f"QUALIFICATION: 2000-01 through 2025-26 regular seasons · Minimum "
            f"{MIN_POSSESSIONS} offensive possessions and {MIN_ATTEMPTS} three-point attempts",
            "",
            "METHOD: Three-point percentage is makes divided by attempts for the exact five players "
            "on the floor. The attempts minimum is separate from the possession minimum because a "
            "possession need not contain a three-point attempt. Players are ordered PG to C by "
            "functional lineup role.",
            "",
            "SOURCE: pbpstats.com · Derived from NBA play-by-play",
            "",
            "HANDLE: @chicagobullsdata",
            "",
            "=== END CANVA COPY ===",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank Bulls five-man lineup three-point shooting since 2000-01."
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Fetch and replace the tracked pbpstats snapshots."
    )
    parser.add_argument(
        "--final", action="store_true", help="Export the chart asset at publish resolution."
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help=f"Accepted for CLI consistency; the post folder remains dated {POST_DATE}.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lineups, audit = fetch_source_tables() if args.refresh else load_source_tables()
    if len(audit) != LAST_SEASON - FIRST_SEASON + 1:
        raise ValueError("Fetch audit does not contain all 26 seasons")
    rows = prepare_ranking(lineups)
    table_path = write_top_ten(rows)
    chart_path = render_chart(rows, final=args.final)
    print(
        rows[["Rank", "Season", *POSITION_COLUMNS, "OffPoss", "FG3M", "FG3A", "Fg3Pct"]].to_string(
            index=False
        )
    )
    print(
        f"\nSource lineups: {LINEUP_SOURCE}\nFetch audit: {FETCH_AUDIT}\n"
        f"Top-ten table: {table_path}\nChart asset: {chart_path}"
    )
    scale = 2 if args.final else 1
    print(f"Chart export: {CHART_WIDTH * scale}×{CHART_HEIGHT * scale} px\n")
    print(canva_copy_block(rows))


if __name__ == "__main__":
    main()
