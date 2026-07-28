"""Scoring by location — the leading Bull in each of the 12 shot zones.

One half court, twelve zones outlined, and a face in each. Two slides off the same
court: EFFICIENCY crowns the best points per shot among a zone's real users, VOLUME
crowns whoever shoots it most. Chart assets only — Canva supplies the title,
subtitle, qualifier, and source line.

Zones are classified from shot coordinates by ``zone_of``, the same function that
draws the outlines, so the chart cannot count one set of regions while drawing
another. That is a deliberate departure from NBA's own labels, which change how
many side sectors exist at 16 ft and so draw each baseline/mid-range border as a
stepped "tent" rather than a straight ray. The cost is measured and reported on
every run: 34 of 5,855 roster shots move (0.6%), and ``main`` prints the live
agreement rate. See DEVELOPMENT.md for why this is an exception, not the rule.

Usage:
    python scripts/prototypes/scoring_by_location.py            # both slides
    python scripts/prototypes/scoring_by_location.py --mode volume --final
    python scripts/prototypes/scoring_by_location.py --refresh  # re-fetch shots
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Wedge
from scipy.ndimage import gaussian_filter

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bulls import data
from bulls.analysis.stats import detailed_zones
from bulls.config import CURRENT_SEASON
from bulls.graphics import house
from bulls.graphics.house import helvetica

CACHE = REPO_ROOT / "cache" / "scoring_by_location"
OUTPUT = REPO_ROOT / "output" / "feed"

# Official 2026-27 roster, snapshot 2026-07-23 (docs/handoffs), matching
# current_roster_hot_spots. The four 2026 rookies (Awaka, Sellers, Swain,
# C. Wilson) have no 2025-26 NBA shots and are disclosed in the caption.
ROSTER = [
    (1641824, "Matas Buzelis", "BUZELIS"),
    (1626181, "Norman Powell", "POWELL"),      # 2025-26 with Miami
    (1630581, "Josh Giddey", "GIDDEY"),
    (1630200, "Tre Jones", "JONES"),
    (1629651, "Nicolas Claxton", "CLAXTON"),   # 2025-26 with Brooklyn
    (1630172, "Patrick Williams", "WILLIAMS"),
    (1630171, "Isaac Okoro", "OKORO"),
    (1642265, "Rob Dillingham", "DILLINGHAM"),
    (1630188, "Jalen Smith", "SMITH"),
    (1631159, "Leonard Miller", "MILLER"),
    (1628380, "Zach Collins", "COLLINS"),
    (1642855, "Noa Essengue", "ESSENGUE"),
]

# Qualification: a share of the team's work in that zone. Zone volume spans two
# orders of magnitude (2,226 roster attempts at the rim against 29 from right
# mid-range), so neither a fixed attempt floor nor a rank works. A floor hands the
# rim to a 28-attempt reserve over the man who took 351; a rank ignores volume
# entirely, so "third most attempts" means 324 shots at the rim and 8 on the right
# baseline. A share scales itself: 15% is 334 shots at the rim and 9 on the right
# baseline. If a zone is so evenly split that nobody clears it, the attempts leader
# stands in, so every zone always has a leader.
MIN_ZONE_SHARE = 0.15

# Two slides off one court. EFFICIENCY crowns the best points per shot among a
# zone's real users; VOLUME crowns whoever simply shoots it most. Volume needs no
# qualification at all — the attempts leader is, by definition, the best-sampled
# player in the zone — which is why the share gate applies only to efficiency.
MODES = ("efficiency", "volume")
# Below this, the zone leader is drawn muted — shown, but not asserted.
MIN_FGA_CONFIDENT = 10

# NBA zone geometry, in raw API units (tenths of a foot, hoop at the origin).
RA_R = 40.0             # restricted area, 4 ft
PAINT_HALF = 80.0       # key half-width, 8 ft
FT_Y = 142.5            # free-throw line
ARC_R = 237.5           # three-point arc, 23.75 ft
CORNER_X = 220.0        # corner-3 sideline, 22 ft
CORNER_Y = float(np.sqrt(ARC_R ** 2 - CORNER_X ** 2))   # arc/corner break, ~89.5
BASELINE_Y = -47.5
BACKBOARD_Y = -7.5      # where the restricted-area sides close onto the board
BAND_R = 160.0          # 16 ft, where NBA's own scheme changes sector count.
                        # Ours does not; kept as the landmark the tests probe around.
COURT_DEPTH = 344.0     # how much of the half court is drawn; past this is empty floor

# Display order, and where each zone's chip sits (raw court units).
ZONE_ORDER = [
    "Restricted Area", "In The Paint (Non-RA)",
    "Left Baseline", "Left Mid-Range", "Center Mid-Range",
    "Right Mid-Range", "Right Baseline",
    "Left Corner 3", "Left Wing 3", "Top of Key 3",
    "Right Wing 3", "Right Corner 3",
]

SHORT_LABEL = {
    "Restricted Area": "AT THE RIM",
    "In The Paint (Non-RA)": "PAINT",
    "Left Baseline": "LEFT BASELINE",
    "Left Mid-Range": "LEFT MID",
    "Center Mid-Range": "CENTER MID",
    "Right Mid-Range": "RIGHT MID",
    "Right Baseline": "RIGHT BASELINE",
    "Left Corner 3": "LEFT CORNER",
    "Left Wing 3": "LEFT WING",
    "Top of Key 3": "TOP OF KEY",
    "Right Wing 3": "RIGHT WING",
    "Right Corner 3": "RIGHT CORNER",
}

# Where each chip sits, in court coordinates (hoop at the origin); the renderer
# flips y so the hoop is at the top. On-court anchors sit in the zone they report.
# Three zones cannot hold a chip: the rim, and the two corner-3 strips, which are
# only 3 ft wide. All three sit hard against their own zone instead, close enough
# that no leader line is needed — the corners just outside their sideline, the rim
# directly above the basket with its figures between the backboard and the baseline.
CHIP_LAYOUT = {
    "Restricted Area":       ((0, -52), None),
    "Left Corner 3":         ((-254, 16), None),
    "Right Corner 3":        ((254, 16), None),
    "Left Baseline":         ((-150, 35), None),
    "Right Baseline":        ((150, 35), None),
    "In The Paint (Non-RA)": ((0, 95), None),
    "Left Mid-Range":        ((-120, 150), None),
    "Right Mid-Range":       ((120, 150), None),
    "Center Mid-Range":      ((0, 203), None),
    "Left Wing 3":           ((-200, 213), None),
    "Right Wing 3":          ((200, 213), None),
    "Top of Key 3":          ((0, 278), None),
}

# Half-width of a corner chip's widest figure line, measured from the rendered
# text at the sizes below. The corner chips deliberately straddle the sideline, so
# this is what keeps them from creeping onto the corner-3 line itself.
CORNER_TEXT_HALF = 30.0

# Chips that cannot stand in their own zone, so a positional test must skip them.
OFF_COURT_ZONES = {"Restricted Area", "Left Corner 3", "Right Corner 3"}


# The mid-range band is shallow between the paint and the arc, so its three chips
# are drawn smaller rather than sitting on top of the borders either side.
COMPACT_ZONES = {"Left Mid-Range", "Right Mid-Range", "Center Mid-Range"}
COMPACT_SCALE = 0.76

# A chip is a face over two lines; this recentres that stack on its anchor.
CHIP_RISE = 21.0

# Screen-space window (y already flipped): baseline at the top, half court below.
VIEW_X = (-306, 306)
VIEW_Y = (-356, 142)

# A red floor with black lines, following the reference graphic. The two deeper
# tints give the paint and the rim their own presence, the way a painted key does.
COURT_FILL = "#F6DCE1"
PAINT_FILL = "#EFC6D0"
RIM_FILL = "#E5A9B8"
COURT_LINE = "#1A1A1A"
ZONE_LINE = "#1A1A1A"

# Centre-to-centre between a chip's two figures, in court units.
LINE_GAP = 12.0

HEAD_HALF = 23.0

# Zone-outline tracing: sample step and blur radius, both in court units.
ZONE_TRACE_STEP = 0.5
ZONE_TRACE_BLUR = 1.0


# ---------------------------------------------------------------------------
# Zone geometry — the single source of truth for BOTH the outlines and the numbers,
# so the chart cannot draw one set of regions while counting another.
# ---------------------------------------------------------------------------
def _angle(x, y):
    """Degrees from the +x axis, wrapped so the left side below the hoop stays > 90."""
    a = np.degrees(np.arctan2(y, x))
    return np.where(a < -90, a + 360, a)


def zone_of(x, y):
    """Zone name for court coordinates: five side sectors at every distance.

    NBA's own labelling changes how many sectors exist with distance — three inside
    16 ft, five outside — which makes the baseline/mid-range divider a stepped
    "tent" rather than a straight line, and reads as a drawing error. We use the
    five-sector split (36/72/108/144 degrees) at every distance instead, so each
    divider is one clean ray from the hoop, matching how these charts are usually
    drawn. Above the break keeps three sectors because the corners take the outer
    two, exactly as NBA does.

    The cost is measured, not assumed: against NBA's own labels this moves 34 of
    5,855 roster shots (0.6%), almost all of them long twos near the 16 ft line,
    and changes one of the twelve zone leaders. ``main`` prints the live agreement
    rate on every run so the divergence can never drift unnoticed.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    r = np.hypot(x, y)
    a = _angle(x, y)

    out = np.full(x.shape, "", dtype=object)

    corner = (np.abs(x) >= CORNER_X) & (y <= CORNER_Y)
    beyond_arc = (r >= ARC_R) & ~corner
    paint = (np.abs(x) <= PAINT_HALF) & (y <= FT_Y) & (r > RA_R)

    out[corner & (x < 0)] = "Left Corner 3"
    out[corner & (x > 0)] = "Right Corner 3"
    out[beyond_arc & (a < 72)] = "Right Wing 3"
    out[beyond_arc & (a >= 72) & (a < 108)] = "Top of Key 3"
    out[beyond_arc & (a >= 108)] = "Left Wing 3"

    mid = (out == "") & (r > RA_R) & ~paint
    out[mid & (a < 36)] = "Right Baseline"
    out[mid & (a >= 36) & (a < 72)] = "Right Mid-Range"
    out[mid & (a >= 72) & (a < 108)] = "Center Mid-Range"
    out[mid & (a >= 108) & (a < 144)] = "Left Mid-Range"
    out[mid & (a >= 144)] = "Left Baseline"

    out[paint] = "In The Paint (Non-RA)"
    out[r <= RA_R] = "Restricted Area"
    return out


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_shots(pid: int, refresh: bool) -> pd.DataFrame:
    path = CACHE / f"player_{pid}_{CURRENT_SEASON}.csv"
    # Coordinates drive the zone; NBA's own labels ride along so every run can
    # report how far our geometry diverges from theirs.
    cols = ["loc_x", "loc_y", "shot_made", "shot_type", "shot_zone", "shot_zone_area"]
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = data.get_player_shots(pid, team_id=0, season=CURRENT_SEASON)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df[[c for c in cols if c in df.columns]] if not df.empty else pd.DataFrame(columns=cols)
    df.to_csv(path, index=False)
    return df


@dataclass
class ZoneLeader:
    zone: str
    name: str
    short: str
    nba_id: int
    fga: int
    pps: float
    confident: bool
    team_fga: int          # every roster attempt in the zone, for the copy block
    qualified: int         # how many players cleared the top-N gate


def roster_shots(refresh: bool) -> pd.DataFrame:
    """Every roster shot, zoned by our own geometry and carrying NBA's label too."""
    frames = []
    for pid, name, short in ROSTER:
        df = load_shots(pid, refresh)
        if df.empty:
            print(f"  no {CURRENT_SEASON} shots: {name}")
            continue
        missing = {"loc_x", "loc_y", "shot_zone_area"} - set(df.columns)
        if missing:
            raise SystemExit(f"{name}: cached shots are missing {sorted(missing)}; rerun --refresh")
        df = detailed_zones(df)                      # NBA's own 12-zone label
        df = df.rename(columns={"shot_zone": "nba_zone"})
        df["nba_id"], df["name"], df["short"] = pid, name, short
        frames.append(df)

    shots = pd.concat(frames, ignore_index=True)
    # NBA's label is the reliable way to drop half-court heaves, which our own
    # geometry would otherwise happily score against Top of Key.
    shots = shots[shots["nba_zone"] != "Backcourt"]
    shots["shot_zone"] = zone_of(shots["loc_x"].values, shots["loc_y"].values)
    # Points per shot: a made three is 3, a made two is 2, a miss is 0.
    shots["points"] = np.where(
        shots["shot_made"] & (shots["shot_type"] == "3PT"), 3,
        np.where(shots["shot_made"], 2, 0),
    )
    return shots


def zone_agreement(shots: pd.DataFrame) -> tuple[int, int]:
    """How many shots our geometry places exactly where NBA's own labels do."""
    same = int((shots["shot_zone"] == shots["nba_zone"]).sum())
    return same, len(shots)


def zone_table(shots: pd.DataFrame) -> pd.DataFrame:
    """Every roster player's attempts and points per shot in each of the 12 zones."""
    table = (
        shots.groupby(["shot_zone", "nba_id", "name", "short"])
        .agg(fga=("shot_made", "size"), points=("points", "sum"))
        .reset_index()
    )
    table["pps"] = table["points"] / table["fga"]
    return table


def select_leaders(table: pd.DataFrame, mode: str = "efficiency") -> list[ZoneLeader]:
    """Crown one player per zone: best points per shot among that zone's real users.

    Gating on a share of attempts *within the zone* rather than on season totals is
    what keeps the claim honest — the metric is zone-specific, so the sample that
    earns a place on the graphic has to be too.
    """
    leaders: list[ZoneLeader] = []
    for zone in ZONE_ORDER:
        z = table[table["shot_zone"] == zone]
        if z.empty:
            raise SystemExit(f"no shots at all in {zone}")
        if mode == "volume":
            # No gate: "took the most shots here" is a fact, not an estimate.
            pool = z
            best = pool.sort_values(["fga", "pps"], ascending=[False, False]).iloc[0]
        else:
            pool = z[z["fga"] >= MIN_ZONE_SHARE * z["fga"].sum()]
            if pool.empty:
                # Nobody owns this zone; the man who shoots it most speaks for it.
                pool = z.nlargest(1, "fga", keep="all")
            best = pool.sort_values(["pps", "fga"], ascending=[False, False]).iloc[0]
        leaders.append(ZoneLeader(
            zone=zone,
            name=best["name"],
            short=best["short"],
            nba_id=int(best["nba_id"]),
            fga=int(best["fga"]),
            pps=float(best["pps"]),
            confident=mode == "volume" or int(best["fga"]) >= MIN_FGA_CONFIDENT,
            team_fga=int(z["fga"].sum()),
            qualified=len(pool),
        ))
    return leaders



# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def flip(y):
    """Court y -> screen y. Negating puts the hoop at the top, as in the reference."""
    return -np.asarray(y, dtype=float) if isinstance(y, np.ndarray) else -float(y)


def _arc(ax, cx, cy, diameter, theta1, theta2, **kw):
    """An Arc placed in flipped space; mirroring y reverses and negates the sweep."""
    ax.add_patch(Arc((cx, flip(cy)), diameter, diameter,
                     theta1=-theta2, theta2=-theta1, **kw))


def draw_floor(ax):
    """Fill the half court, then the paint and the rim, before anything is drawn on top."""
    ax.add_patch(FancyBboxPatch(
        (-250, flip(COURT_DEPTH)), 500, COURT_DEPTH - BASELINE_Y,
        boxstyle="square,pad=0", facecolor=COURT_FILL, edgecolor="none", zorder=0))
    ax.add_patch(FancyBboxPatch(
        (-PAINT_HALF, flip(FT_Y)), 2 * PAINT_HALF, FT_Y - BASELINE_Y,
        boxstyle="square,pad=0", facecolor=PAINT_FILL, edgecolor="none", zorder=1))
    # The restricted area is painted as a D — a semicircle closing onto the
    # backboard — not a full disc. NBA still *classifies* it as the whole 4 ft
    # circle, so the sliver behind the board (26 of 2,226 roster shots, 1.2%,
    # reverse layups) counts toward the zone without being shaded.
    ax.add_patch(Wedge((0, 0), RA_R, 180, 360, facecolor=RIM_FILL,
                       edgecolor="none", zorder=1))
    ax.add_patch(FancyBboxPatch((-RA_R, 0), 2 * RA_R, flip(BACKBOARD_Y),
                                boxstyle="square,pad=0", facecolor=RIM_FILL,
                                edgecolor="none", zorder=1))


def draw_zone_outlines(ax):
    """Trace each zone boundary from the classifier so the lines match the labels.

    Contouring a 0/1 mask straight off the grid leaves the radial dividers visibly
    stair-stepped, because a diagonal boundary can only follow cell edges. Sampling
    finer and softening the mask first turns each step into a sub-pixel wobble, and
    at half a unit of blur the traced line stays within an inch of true.
    """
    step = ZONE_TRACE_STEP
    xs = np.arange(-250.0, 250.0 + step, step)
    ys = np.arange(BASELINE_Y, COURT_DEPTH + step, step)
    gx, gy = np.meshgrid(xs, ys)
    zones = zone_of(gx, gy)

    for zone in ZONE_ORDER:
        if zone == "Restricted Area":
            # Its painted D already bounds it; a traced circle would double the line.
            continue
        mask = zones == zone
        if zone == "In The Paint (Non-RA)":
            # The paint is a ring around the restricted area, so tracing it alone
            # would draw the rim's full 4 ft circle as an inner edge — the very
            # shape the painted D replaces. Fill that hole before tracing.
            mask = mask | (zones == "Restricted Area")
        mask = mask.astype(float)
        if mask.max() == 0:
            continue
        smooth = gaussian_filter(mask, sigma=ZONE_TRACE_BLUR / step, mode="nearest")
        ax.contour(gx, flip(gy), smooth, levels=[0.5], colors=[ZONE_LINE],
                   linewidths=1.35, zorder=3)


def draw_court(ax):
    """The painted geometry a fan recognises, over the zone dividers."""
    line = dict(color=COURT_LINE, lw=1.9, zorder=4, solid_capstyle="butt")
    ax.plot([-250, 250], [flip(BASELINE_Y)] * 2, **line)
    ax.plot([-250, 250], [flip(COURT_DEPTH)] * 2, **line)
    for side in (-250, 250):
        # Drawn unbroken even where the corner chips straddle it. Glyphs are opaque
        # and sit above (zorder 10), so the line disappears under the strokes and
        # shows through the gaps between them — the label reads as sitting on the
        # boundary, which is what a court line should do.
        ax.plot([side, side], [flip(BASELINE_Y), flip(COURT_DEPTH)], **line)

    ax.add_patch(FancyBboxPatch(
        (-PAINT_HALF, flip(FT_Y)), 2 * PAINT_HALF, FT_Y - BASELINE_Y,
        boxstyle="square,pad=0", facecolor="none", edgecolor=COURT_LINE, lw=1.9, zorder=4))
    ax.add_patch(Circle((0, 0), 7.5, facecolor="none", edgecolor=COURT_LINE, lw=1.9, zorder=5))
    ax.plot([-30, 30], [flip(BACKBOARD_Y)] * 2, **line)             # backboard
    _arc(ax, 0, 0, 2 * RA_R, 0, 180, color=COURT_LINE, lw=1.9, zorder=5)
    for side in (-RA_R, RA_R):                                      # close the D
        ax.plot([side, side], [0, flip(BACKBOARD_Y)], **line)
    _arc(ax, 0, FT_Y, 120, 0, 180, color=COURT_LINE, lw=1.9, zorder=4)
    _arc(ax, 0, FT_Y, 120, 180, 360, color=COURT_LINE, lw=1.6,
         linestyle=(0, (5, 4)), zorder=4)

    for side in (-CORNER_X, CORNER_X):
        ax.plot([side, side], [flip(BASELINE_Y), flip(CORNER_Y)], **line)
    theta = float(np.degrees(np.arcsin(CORNER_Y / ARC_R)))
    _arc(ax, 0, 0, 2 * ARC_R, theta, 180 - theta, color=COURT_LINE, lw=1.9, zorder=4)


def draw_chip(ax, leader: ZoneLeader, anchor, target, mode="efficiency"):
    """A face over two lines: the points-per-shot figure and the attempts behind it.

    No name and no zone caption — the face and the position on the court carry both,
    and twelve of each was more label than the graphic could hold.
    """
    cx = anchor[0]
    k = COMPACT_SCALE if leader.zone in COMPACT_ZONES else 1.0
    head = HEAD_HALF * k
    cy = flip(anchor[1]) - CHIP_RISE * k   # centres the face-over-figures stack on the anchor
    strong = leader.confident
    ink = house.BULLS_BLACK if strong else "#8A8A8A"
    sub = "#5C5C5C" if strong else "#9A9A9A"

    if target is not None:
        ax.annotate("", xy=(target[0], flip(target[1])), xytext=(cx, cy - 22),
                    arrowprops=dict(arrowstyle="-", color=house.BULLS_BLACK, lw=1.0,
                                    shrinkA=4, shrinkB=2), zorder=6)
        ax.plot([target[0]], [flip(target[1])], marker="o", markersize=2.6,
                color=house.BULLS_BLACK, zorder=6)

    art = house.square_headshot_label(ax, house.HEADSHOT_CACHE / f"{leader.nba_id}.png",
                                      cx, cy + head + 13 * k, head, zorder=9)
    if not strong and hasattr(art, "set_alpha"):
        art.set_alpha(0.45)

    if mode == "volume":
        headline, footnote = f"{leader.fga} FGA", f"{leader.pps:.2f} PPS"
    else:
        headline, footnote = f"{leader.pps:.2f} PPS", f"{leader.fga} FGA"
    ax.text(cx + 1, cy + 1, headline, ha="center", va="center",
            fontproperties=helvetica("bold"), fontsize=11.5 * k, color=ink,
            zorder=10, clip_on=False)
    ax.text(cx + 1, cy - LINE_GAP * k, footnote, ha="center", va="center",
            fontproperties=helvetica("regular"), fontsize=8 * k, color=sub,
            zorder=10, clip_on=False)



def render(leaders: list[ZoneLeader], out_path: Path, final: bool,
           mode: str = "efficiency") -> Path:
    fig, ax = plt.subplots(figsize=(9.6, 7.3))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    ax.set_xlim(*VIEW_X)
    ax.set_ylim(*VIEW_Y)
    ax.set_aspect("equal")
    ax.axis("off")

    draw_floor(ax)
    draw_zone_outlines(ax)
    draw_court(ax)

    house.ensure_headshots([lead.nba_id for lead in leaders])
    for leader in leaders:
        anchor, target = CHIP_LAYOUT[leader.zone]
        draw_chip(ax, leader, anchor, target, mode)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=house.export_dpi(final), transparent=True,
                bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    return out_path


def canva_block(leaders: list[ZoneLeader], mode: str = "efficiency") -> str:
    """Exact strings for the Canva page, so page and chart come from one run."""
    thin = [lead for lead in leaders if not lead.confident]
    if mode == "volume":
        slide = ["SUBTITLE:  Who takes the shots from each zone,",
                 f"           {CURRENT_SEASON} regular season",
                 "QUALIFIER: Most attempts in that zone — no minimum, the count is the sample"]
    else:
        slide = ["SUBTITLE:  The most efficient Bull per shot in each zone,",
                 f"           {CURRENT_SEASON} regular season",
                 f"QUALIFIER: Among Bulls with {MIN_ZONE_SHARE:.0%}+ of the team's attempts in that zone"]
    lines = [
        "--- CANVA COPY BLOCK ---",
        f"SLIDE {'2 (volume)' if mode == 'volume' else '1 (efficiency)'}",
        "TITLE:     Scoring By Location",
        *slide,
        "ROSTER:    2026-27 roster; 2025-26 stats, including games with prior teams",
        "SOURCE:    Source: NBA.com/stats  |  @chicagobullsdata",
        "",
        "PER-ZONE (chart already carries these — do not retype):",
    ]
    for lead in leaders:
        flag = "" if lead.confident else "   <-- MUTED, low sample"
        lines.append(f"  {SHORT_LABEL[lead.zone]:<15} {lead.name:<18} "
                     f"{lead.pps:.2f} PPS on {lead.fga} FGA "
                     f"({lead.fga / lead.team_fga:.0%} of the zone's {lead.team_fga}){flag}")
    if thin:
        names = ", ".join(SHORT_LABEL[t.zone].title() for t in thin)
        lines += ["", f"NOTE: {names} shown muted — leader under {MIN_FGA_CONFIDENT} attempts."]
    lines.append("--- END ---")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-fetch shots from the API")
    parser.add_argument("--final", action="store_true", help="export at final DPI")
    parser.add_argument("--mode", choices=(*MODES, "both"), default="both",
                        help="efficiency slide, volume slide, or both")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    shots = roster_shots(args.refresh)
    table = zone_table(shots)
    same, total = zone_agreement(shots)
    print(f"zone check: {same}/{total} shots ({same / total * 100:.1f}%) land in the same "
          f"zone NBA's own labels give them; the rest are long twos near the 16 ft line.\n")

    modes = MODES if args.mode == "both" else (args.mode,)
    for mode in modes:
        leaders = select_leaders(table, mode)
        slide = 1 if mode == "efficiency" else 2
        out = args.out or OUTPUT / f"2026-07-27-zone-{mode}-scoring-by-location.png"
        path = render(leaders, out, args.final, mode)
        print(canva_block(leaders, mode))
        print(f"\nwrote slide {slide} ({mode}): {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
