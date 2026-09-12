#!/usr/bin/env python3
"""Slides 4 and 5 of the Buzelis post: how he got his shots, and who made them.

The zone charts answer *where* he shot and whether it went in. They cannot say
how the shot came to exist. These two assets do, from NBA.com's ``ACTION_TYPE``
labels, and they carry that source's limits (``bulls.analysis.shot_families``).

    slide 4  every family's share, 2024-25 against 2025-26
    slide 5  the self-created share, and what it is made of

Both compare Buzelis with himself rather than with the league. That is not a
shortcut around fetching a baseline -- it is the honest scope. Shot labels carry
a per-arena scorer habit, and a single player's home/road split is too small to
audit it the way the team-level shot-diet post could. Two seasons of the same
player share the same labelling regime, so the movement between them is the
claim the source can actually support.

    venv/bin/python scripts/prototypes/matas_buzelis_shot_families.py --prepare
    venv/bin/python scripts/prototypes/matas_buzelis_shot_families.py --final
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from nba_api.stats.endpoints import shotchartdetail

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_families as sf
from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import dumbbell as db
from bulls.graphics.house import DRAFT_DPI, export_dpi, helvetica

PLAYER_ID = 1641824
PLAYER_NAME = "Matas Buzelis"
SEASONS = ("2024-25", "2025-26")
PROJECT = "matas-buzelis-bulls-zone-charts"
SLUG = f"2026-09-07-{PROJECT}"
# Official Chicago regular-season FGA. The zone slides already reconcile to
# these; the family logs must land on the same totals or the two halves of the
# post would describe differently sized seasons.
OFFICIAL_FGA = {"2024-25": 555, "2025-26": 963}
MIN_FAMILY_FGA = 20

# Optical tracking (Second Spectrum) classifies the same seasons from player and ball
# position, with no scorer typing anything, so it shares no failure mode with
# ACTION_TYPE. Where the two agree the scorer-bias question is closed for this subject.
# It is a check only. Tracking's categories overlap and leave gaps -- catch-and-shoot
# and pull-up together cover roughly half his attempts, the rest being drives, putbacks
# and post-ups -- so they can never replace the families on the chart.
TRACKING_RANGES = ("Catch and Shoot", "Pullups")


# ---------------------------------------------------------------- preparation
def fetch_labelled_shots(season: str) -> pd.DataFrame:
    frame = shotchartdetail.ShotChartDetail(
        team_id=BULLS_TEAM_ID, player_id=PLAYER_ID, season_nullable=season,
        season_type_all_star="Regular Season", last_n_games=0,
        context_measure_simple="FGA", timeout=60, headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    keep = ["GAME_ID", "GAME_DATE", "ACTION_TYPE", "SHOT_TYPE", "SHOT_ZONE_BASIC",
            "SHOT_DISTANCE", "SHOT_MADE_FLAG"]
    out = frame.loc[:, keep].copy()
    out.insert(0, "season", season)
    out["family"] = sf.classify_series(out.ACTION_TYPE)
    return out


def reconcile(season: str, shots: pd.DataFrame) -> None:
    expected, actual = OFFICIAL_FGA[season], len(shots)
    if actual != expected:
        raise ValueError(f"{season}: labelled rows {actual} != Bulls FGA {expected}")


def load_shots(season: str, data_dir: Path, refresh: bool) -> pd.DataFrame:
    path = data_dir / f"{season}-matas-buzelis-bulls-shot-families.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch_labelled_shots(season)
        data_dir.mkdir(parents=True, exist_ok=True)
        shots.to_csv(path, index=False)
    reconcile(season, shots)
    return shots


def build_tables(data_dir: Path, refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    shares, actions = [], []
    for season in SEASONS:
        shots = load_shots(season, data_dir, refresh)
        table = sf.family_shares(shots.ACTION_TYPE, shots.SHOT_MADE_FLAG,
                                 MIN_FAMILY_FGA)
        table.insert(0, "season", season)
        shares.append(table)
        # The raw label counts travel with the post: "Standard jumpers" is a
        # bucket of many strings, and a reader checking the claim needs to see
        # which ones landed in it.
        counts = (shots.groupby(["ACTION_TYPE", "family"]).size()
                  .reset_index(name="fga"))
        counts.insert(0, "season", season)
        actions.append(counts)
    return (pd.concat(shares, ignore_index=True),
            pd.concat(actions, ignore_index=True))


def fetch_unassisted(season: str) -> dict[str, float]:
    """Official assisted/unassisted splits, as a share of MADE field goals.

    NBA's Scoring measure derives these from whether a basket was credited with
    an assist, so the denominator is baskets, not attempts. A shot a player
    created for himself and missed is invisible here. That is a real limit and
    the page has to state it, but it buys an official measure in place of a
    grouping this repo invented.
    """
    from nba_api.stats.endpoints import leaguedashplayerstats

    frame = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season, season_type_all_star="Regular Season",
        team_id_nullable=BULLS_TEAM_ID, per_mode_detailed="Totals",
        measure_type_detailed_defense="Scoring", headers=_NBA_HEADERS,
        timeout=60).get_data_frames()[0]
    player = frame[frame.PLAYER_ID.eq(PLAYER_ID)]
    if len(player) != 1:
        raise ValueError(f"{season}: expected one {PLAYER_NAME} scoring row, "
                         f"found {len(player)}")
    row = player.iloc[0]
    out = {
        "season": season,
        "pct_unast_fgm": round(float(row.PCT_UAST_FGM) * 100, 1),
        "pct_ast_fgm": round(float(row.PCT_AST_FGM) * 100, 1),
        "pct_unast_2pm": round(float(row.PCT_UAST_2PM) * 100, 1),
        "pct_unast_3pm": round(float(row.PCT_UAST_3PM) * 100, 1),
    }
    assert_partition(season, out["pct_unast_fgm"], out["pct_ast_fgm"])
    return out


def assert_partition(season: str, unassisted: float, assisted: float) -> None:
    """The two halves must close. Drift here means the endpoint changed shape."""
    total = unassisted + assisted
    if abs(total - 100.0) > 0.2:
        raise ValueError(f"{season}: assisted + unassisted = {total}, not 100")


def load_unassisted(data_dir: Path, refresh: bool) -> pd.DataFrame:
    path = data_dir / "assisted-unassisted.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    rows = []
    for season in SEASONS:
        rows.append(fetch_unassisted(season))
        time.sleep(0.65)
    frame = pd.DataFrame(rows)
    data_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def recover_unassisted_count(fgm: int, pct: float, places: int = 3) -> int:
    """The count NBA does not publish, pinned by the share it does.

    The Scoring endpoint gives the unassisted share to three decimals and never
    the count. With FGM known, the rounding interval around that share usually
    admits exactly one integer, which makes the count recovered rather than
    estimated. It is only safe while that integer is unique, so this raises when
    it is not: a larger denominator or coarser rounding leaves several
    candidates, and the arithmetic would quietly become a guess.
    """
    half = 0.5 * 10 ** -places
    low, high = (pct - half) * fgm, (pct + half) * fgm
    candidates = [n for n in range(fgm + 1) if low <= n <= high]
    if len(candidates) != 1:
        raise ValueError(
            f"unassisted count not uniquely determined by {pct} of {fgm} FGM: "
            f"candidates {candidates}")
    return candidates[0]


def creation_counts(unassisted: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """Made field goals split into unassisted and assisted, as counts."""
    shares = unassisted.set_index("season")
    rows = []
    for season in SEASONS:
        totals = pd.read_csv(
            data_dir / f"{season}-matas-buzelis-bulls-totals.csv").iloc[0]
        fgm = int(totals.FGM)
        pct = float(shares.loc[season, "pct_unast_fgm"]) / 100
        unast = recover_unassisted_count(fgm, pct)
        rows.append({"season": season, "fgm": fgm, "unassisted_fgm": unast,
                     "assisted_fgm": fgm - unast,
                     "unassisted_pct": round(unast / fgm * 100, 1)})
    frame = pd.DataFrame(rows)
    frame.to_csv(data_dir / "creation-counts.csv", index=False)
    return frame


def corroborate(shares: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """Check the label-derived self-created share against tracked pull-up rate.

    The two measure the same idea by different means: our grouping counts three
    scorer-typed families, tracking counts any shot taken off the dribble. They
    are not required to match exactly and their boundaries differ. What matters
    is whether they move together, because only one of them can be a labelling
    artefact.
    """
    from nba_api.stats.endpoints import leaguedashplayerptshot

    rows, lines = [], []
    for season in SEASONS:
        tracked = {}
        for shot_range in TRACKING_RANGES:
            frame = leaguedashplayerptshot.LeagueDashPlayerPtShot(
                season=season, season_type_all_star="Regular Season",
                team_id_nullable=BULLS_TEAM_ID, general_range_nullable=shot_range,
                headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
            player = frame[frame.PLAYER_ID.eq(PLAYER_ID)]
            if len(player) != 1:
                raise ValueError(f"{season} {shot_range}: expected one row, "
                                 f"found {len(player)}")
            tracked[shot_range] = int(player.iloc[0].FGA)
            time.sleep(0.65)

        total = OFFICIAL_FGA[season]
        table = shares[shares.season.eq(season)]
        label_fga = int(table[table.self_created].fga.sum())
        label_share = float(table[table.self_created].share_pct.sum())
        tracked_share = tracked["Pullups"] / total * 100
        rows.append({
            "season": season,
            "total_fga": total,
            "label_self_created_fga": label_fga,
            "label_self_created_share_pct": round(label_share, 1),
            "tracked_pullup_fga": tracked["Pullups"],
            "tracked_pullup_share_pct": round(tracked_share, 1),
            "gap_points": round(tracked_share - label_share, 1),
            "tracked_catch_shoot_fga": tracked["Catch and Shoot"],
            "tracked_covered_share_pct": round(
                sum(tracked.values()) / total * 100, 1),
        })
        lines.append(
            f"{season}: labels {label_fga} self-created = {label_share:.1f}% of "
            f"{total} attempts; tracking {tracked['Pullups']} pull-ups = "
            f"{tracked_share:.1f}%. Gap {tracked_share - label_share:+.1f} points.")

    lines.append("")
    lines.append("Tracking is an independent check, not the chart's source. Its "
                 "catch-and-shoot and pull-up categories together cover "
                 + ", ".join(f"{r['tracked_covered_share_pct']:.1f}% ({r['season']})"
                             for r in rows)
                 + " of his attempts; the remainder is drives, putbacks and "
                   "post-ups that tracking classifies elsewhere. The chart keeps "
                   "the label-derived families rather than mixing sources.")
    out = pd.DataFrame(rows)
    out.to_csv(data_dir / "tracking-corroboration.csv", index=False)
    (data_dir / "tracking-corroboration.txt").write_text("\n".join(lines) + "\n")
    print("\nTRACKING CORROBORATION")
    for line in lines:
        print(f"  {line}" if line else "")
    return out


# ---------------------------------------------------------------- shared type
# The dumbbell grammar is the shot-diet post's, promoted to bulls/graphics/dumbbell.py
# so both posts draw one form rather than two that merely resemble each other. Only the
# comparison differs: there Chicago against the NBA, here a player against himself. The
# subject is the later season, so it takes the filled mark; the earlier season is the
# reference and takes the ring.
# The canvas is wider than the published shot-diet chart by exactly one column,
# and every other x below is that chart's, untouched. Widening rather than
# compressing is what lets the legend sit right of the value columns without
# retuning a single matched position -- and placed to the same page width, the
# wider asset scales down, so it costs less page height rather than more.
WIDTH = 1860
LEGEND_COL_X = 1620
LEGEND_LINE_STEP = 52.0
LABEL_RIGHT = 452
TRACK_LEFT = 504
TRACK_RIGHT = 1210
VALUE_RIGHT = 1390
CHANGE_X = 1500
LEADER_END = 1262
VALUE_HEADER_X = (LEADER_END + VALUE_RIGHT) / 2
HEADER_Y = 80
AXIS_RULE_Y = 112
ROW_TOP = 200
ROW_STEP = 150


def _canvas(height: float):
    fig = plt.figure(figsize=(WIDTH / DRAFT_DPI, height / DRAFT_DPI), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(height, 0)
    ax.set_axis_off()
    return fig, ax


def _save(fig, out: Path, final: bool) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=export_dpi(final), transparent=True, pad_inches=0)
    plt.close(fig)
    print(f"Saved {out}")
    return out


def _signed(value: float) -> str:
    """Sign decided after rounding, so a change printing 0.0 carries no direction."""
    rounded = round(value, 1)
    sign = "+" if rounded > 0 else ("\u2212" if rounded < 0 else "")
    return f"{sign}{abs(rounded):.1f}"


def fig_of(ax):
    return ax.get_figure()


def _dumbbell_rows(ax, rows, axis_max: float, ticks, value_header: str,
                   change_header: str, legend_labels: tuple[str, str]):
    """Draw the shared chart body: gridlines, scale, legend, and one row each.

    ``rows`` are ``(label, reference_value, subject_value)``. Returns the y of the
    legend so a caller can size its canvas from the content rather than guess.
    """
    def x_for(value: float) -> float:
        return TRACK_LEFT + (value / axis_max) * (TRACK_RIGHT - TRACK_LEFT)

    bottom = ROW_TOP + (len(rows) - 1) * ROW_STEP
    foot = bottom + ROW_STEP * db.GRIDLINE_FOOT_FACTOR
    for tick in ticks:
        x = x_for(tick)
        ax.plot([x, x], [AXIS_RULE_Y, foot], color=db.GRIDLINE,
                linewidth=db.GRIDLINE_WIDTH, zorder=1)
        ax.text(x, foot + db.AXIS_LABEL_DROP, f"{tick}%", ha="center", va="center",
                fontsize=db.TYPE_AXIS, color=db.FOOTNOTE_GREY,
                fontproperties=helvetica())

    ax.text(VALUE_HEADER_X, HEADER_Y, value_header, ha="center", va="center",
            fontsize=db.TYPE_AXIS, color=db.INK, fontproperties=helvetica("bold"))
    ax.text(CHANGE_X, HEADER_Y, change_header, ha="center", va="center",
            fontsize=db.TYPE_AXIS, color=db.INK, fontproperties=helvetica("bold"))

    for index, (label, reference, subject) in enumerate(rows):
        y = ROW_TOP + index * ROW_STEP
        ax.text(LABEL_RIGHT, y, label, ha="right", va="center", fontsize=db.TYPE_LABEL,
                color=db.INK, fontproperties=helvetica("bold"))
        ref_x, sub_x = x_for(reference), x_for(subject)
        db.leader(ax, max(ref_x, sub_x), LEADER_END, y)
        db.connector(ax, sub_x, ref_x, y)
        db.dot(ax, ref_x, y, db.REFERENCE_DOT, db.REFERENCE_GREY, zorder=3, hollow=True)
        db.dot(ax, sub_x, y, db.SUBJECT_DOT, db.SUBJECT, zorder=4)
        ax.text(VALUE_RIGHT, y, f"{subject:.1f}%", ha="right", va="center",
                fontsize=db.TYPE_VALUE, color=db.INK, fontproperties=helvetica("bold"))
        ax.text(CHANGE_X, y, _signed(subject - reference), ha="center", va="center",
                fontsize=db.TYPE_VALUE, color=db.INK, fontproperties=helvetica("bold"))

    return _legend_column(fig_of(ax), ax, [
        (legend_labels[1],
         lambda a, x, y: db.dot(a, x + 11, y, db.SUBJECT_DOT, db.SUBJECT), 22.0),
        (legend_labels[0],
         lambda a, x, y: db.dot(a, x + 11, y, db.REFERENCE_DOT, db.REFERENCE_GREY,
                                hollow=True), 22.0),
    ], len(rows))


LEGEND_MARK_GAP = 16.0        # mark to its own label


def _text_width(fig, ax, text: str, size: float) -> float:
    """Measured, not estimated, so the column can be checked for overflow."""
    artist = ax.text(0, 0, text, fontsize=size, fontproperties=helvetica("bold"))
    fig.canvas.draw()
    width = artist.get_window_extent(fig.canvas.get_renderer()).width
    artist.remove()
    return width * (WIDTH / fig.get_size_inches()[0] / fig.dpi)


def _legend_column(fig, ax, entries, row_count: int) -> float:
    """Legend as a column right of the values, centred against the rows.

    Stacked rather than laid out in a line because a line of entries needs a band
    of its own, and two of these charts share one page. As a column it occupies
    space the chart was not using at all, and the page keeps the height.

    Entries read top to bottom in the order the reader meets them in the data:
    the subject season first, then what it is measured against.
    """
    top = ROW_TOP
    bottom = ROW_TOP + (row_count - 1) * ROW_STEP
    first = (top + bottom) / 2 - LEGEND_LINE_STEP * (len(entries) - 1) / 2
    for index, (label, draw_mark, mark_width) in enumerate(entries):
        y = first + index * LEGEND_LINE_STEP
        draw_mark(ax, LEGEND_COL_X, y)
        ax.text(LEGEND_COL_X + mark_width + LEGEND_MARK_GAP, y, label, ha="left",
                va="center", fontsize=db.TYPE_LEGEND, color=db.INK,
                fontproperties=helvetica("bold"))
        right = (LEGEND_COL_X + mark_width + LEGEND_MARK_GAP
                 + _text_width(fig, ax, label, db.TYPE_LEGEND))
        # The column is the last thing on the canvas, so overflow is silent
        # clipping rather than a visible collision. Fail the render instead.
        if right > WIDTH:
            raise ValueError(f"legend entry {label!r} reaches {right:.0f}, "
                             f"past the {WIDTH}px canvas")
    return first


def _canvas_height(row_count: int) -> float:
    """Content depth plus the legend's own breathing room, never padded beyond it."""
    bottom = ROW_TOP + (row_count - 1) * ROW_STEP
    foot = bottom + ROW_STEP * db.GRIDLINE_FOOT_FACTOR
    return foot + db.AXIS_LABEL_DROP + 46


# ------------------------------------------------------- slide 4: the families
FAMILY_AXIS_MAX = 44.0
FAMILY_TICKS = (0, 10, 20, 30, 40)


def render_families(shares: pd.DataFrame, out: Path, final: bool) -> Path:
    """One row per family, sorted by the later season, so it reads as a diet."""
    later = shares[shares.season.eq(SEASONS[1])].set_index("family")
    earlier = shares[shares.season.eq(SEASONS[0])].set_index("family")
    order = later.sort_values("fga", ascending=False).index.tolist()
    rows = [(family, float(earlier.loc[family, "share_pct"]),
             float(later.loc[family, "share_pct"])) for family in order]

    fig, ax = _canvas(_canvas_height(len(rows)))
    _dumbbell_rows(ax, rows, FAMILY_AXIS_MAX, FAMILY_TICKS, "Share", "Change",
                   SEASONS)
    return _save(fig, out, final)


# ------------------------------------------- slide 5: who created the makes
# Counts, not a rate. The rate alone (19.4% to 30.3%) hides that the whole pie
# grew underneath it: his makes nearly doubled in the same window, so the
# unassisted slice nearly tripled. Width carries volume, colour carries creation.
CREATION_AXIS_MAX = 470.0
CREATION_TICKS = (0, 100, 200, 300, 400)
CREATION_BAR_H = 86.0
# Ink is chosen per fill rather than per chart: DESIGN.md computes contrast where
# the text actually sits. White holds on the red; on the pale grey it does not.
ASSISTED_FILL = db.LEADER_GREY
ASSISTED_INK = db.INK
UNASSISTED_INK = "#FFFFFF"


def render_creation(counts: pd.DataFrame, out: Path, final: bool) -> Path:
    """Two seasons of made field goals, split by who created them."""
    rows = list(counts.itertuples(index=False))

    def x_for(value: float) -> float:
        return TRACK_LEFT + (value / CREATION_AXIS_MAX) * (TRACK_RIGHT - TRACK_LEFT)

    fig, ax = _canvas(_canvas_height(len(rows)))
    bottom = ROW_TOP + (len(rows) - 1) * ROW_STEP
    foot = bottom + ROW_STEP * db.GRIDLINE_FOOT_FACTOR
    for tick in CREATION_TICKS:
        x = x_for(tick)
        ax.plot([x, x], [AXIS_RULE_Y, foot], color=db.GRIDLINE,
                linewidth=db.GRIDLINE_WIDTH, zorder=1)
        ax.text(x, foot + db.AXIS_LABEL_DROP, f"{tick}", ha="center", va="center",
                fontsize=db.TYPE_AXIS, color=db.FOOTNOTE_GREY,
                fontproperties=helvetica())
    ax.text(VALUE_HEADER_X, HEADER_Y, "Made", ha="center", va="center",
            fontsize=db.TYPE_AXIS, color=db.INK, fontproperties=helvetica("bold"))
    ax.text(CHANGE_X, HEADER_Y, "Unassisted", ha="center", va="center",
            fontsize=db.TYPE_AXIS, color=db.INK, fontproperties=helvetica("bold"))

    for index, row in enumerate(rows):
        y = ROW_TOP + index * ROW_STEP
        ax.text(LABEL_RIGHT, y, row.season, ha="right", va="center",
                fontsize=db.TYPE_LABEL, color=db.INK, fontproperties=helvetica("bold"))
        top = y - CREATION_BAR_H / 2
        left = x_for(0)
        for value, fill, ink in ((row.unassisted_fgm, db.SUBJECT, UNASSISTED_INK),
                                 (row.assisted_fgm, ASSISTED_FILL, ASSISTED_INK)):
            width = x_for(value) - x_for(0)
            ax.add_patch(plt.Rectangle((left, top), width, CREATION_BAR_H,
                                       facecolor=fill, edgecolor="none", zorder=2))
            ax.text(left + width / 2, y, f"{value}", ha="center", va="center",
                    fontsize=db.TYPE_VALUE, color=ink, zorder=3,
                    fontproperties=helvetica("bold"))
            left += width
        db.leader(ax, left, LEADER_END, y)
        ax.text(VALUE_RIGHT, y, f"{row.fgm}", ha="right", va="center",
                fontsize=db.TYPE_VALUE, color=db.INK, fontproperties=helvetica("bold"))
        ax.text(CHANGE_X, y, f"{row.unassisted_pct:.1f}%", ha="center", va="center",
                fontsize=db.TYPE_VALUE, color=db.INK, fontproperties=helvetica("bold"))

    def swatch(fill):
        def draw(a, x, y):
            a.add_patch(plt.Rectangle((x, y - 11), 22, 22, facecolor=fill,
                                      edgecolor="none"))
        return draw

    _legend_column(fig, ax, [("Unassisted", swatch(db.SUBJECT), 22.0),
                             ("Assisted", swatch(ASSISTED_FILL), 22.0)],
                   len(rows))
    return _save(fig, out, final)


# ----------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description="Buzelis shot-family slides")
    ap.add_argument("--prepare", action="store_true", help="refetch the labelled logs")
    ap.add_argument("--corroborate", action="store_true",
                    help="check the label-derived claim against optical tracking")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "output" / PROJECT)
    ap.add_argument("--data-dir", type=Path,
                    default=ROOT / "docs" / "visuals" / SLUG / "data")
    args = ap.parse_args()

    shares, actions = build_tables(args.data_dir, args.prepare)
    shares.to_csv(args.data_dir / "shot-family-shares.csv", index=False,
                  float_format="%.4f")
    actions.to_csv(args.data_dir / "shot-family-action-types.csv", index=False)

    for season in SEASONS:
        table = shares[shares.season.eq(season)]
        sc = table[table.self_created]
        print(f"\n{season}: {int(table.fga.sum())} FGA")
        for row in table.sort_values("fga", ascending=False).itertuples():
            flag = "" if row.rated else "   (under 20, share only, no rate)"
            print(f"  {row.family:<20}{row.fga:>4} FGA  {row.share_pct:5.1f}%{flag}")
        print(f"  SELF-CREATED       {int(sc.fga.sum()):>4} FGA  "
              f"{sc.share_pct.sum():5.1f}%")

    if args.corroborate:
        corroborate(shares, args.data_dir)

    unassisted = load_unassisted(args.data_dir, args.prepare)
    counts = creation_counts(unassisted, args.data_dir)
    print("\nWHO CREATED HIS MADE FIELD GOALS")
    for row in counts.itertuples(index=False):
        print(f"  {row.season}: {row.fgm} made = {row.unassisted_fgm} unassisted "
              f"({row.unassisted_pct:.1f}%) + {row.assisted_fgm} assisted")

    stamp = date.today().isoformat()
    render_families(shares, args.output_dir /
                    f"{stamp}-buzelis-shot-families.png", args.final)
    render_creation(counts, args.output_dir /
                    f"{stamp}-buzelis-shot-creation.png", args.final)
    print(f"\nData: {args.data_dir}")


if __name__ == "__main__":
    main()
