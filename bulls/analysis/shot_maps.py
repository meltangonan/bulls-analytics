"""Shot-location analysis shared by the shot-chart family.

Two independent methods live here, and they answer different questions:

* **Density** (``density`` / ``signed_diff``) -- the F5 hot-spot method. Smooths
  shot locations into a distribution, normalises it, and subtracts the league's.
  Answers *where does he shoot from, relative to everyone else*. Frequency only;
  it says nothing about whether the shots went in.

* **Zones** (``zone_split``) -- the RIM / SHORT MID / LONG MID / THREE taxonomy,
  with per-75 volume and FG% measured against the league in the same band.
  Answers *how often and how well, compared with everyone else*.

* **Polar cells** (``polar_split``) -- the same efficiency question at high
  resolution: 4 ft distance bands crossed with angular sectors, 18 cells rather
  than 4. Answers *which spots specifically*, at the cost of a sample thin enough
  that each cell carries a ``rated`` flag saying whether its FG% is worth reading.

Normalisation is the load-bearing idea in both. A player takes ~1,000 shots and
the league takes ~219,000, so raw counts can never be compared; converting each
to a share (or a per-possession rate) is what makes a 262-attempt player and a
963-attempt player legible on the same axis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

# --- Density grid, in raw NBA coordinates (tenths of a foot) ----------------
GRID_X = (-250.0, 250.0)
GRID_Y = (-50.0, 300.0)     # baseline at -47.5, out to ~30 ft
CELL = 5.0                  # half-foot cells
BLUR_FT = 3.8               # Gaussian bandwidth, feet
BASELINE_Y = -47.5
MAX_DIST_FT = 35            # drop half-court heaves, matching the F5 filter

# --- Zone taxonomy ---------------------------------------------------------
# Distance bands reverse-engineered from a published player card by grid-search
# against BOTH its FG% and its per-75 volume. The joint best fit is rim <=3 ft and
# short mid 3-13 ft, which reproduces the card to 0.02 attempts per 75 and 0.4
# FG points. The 13 ft cut is not arbitrary: the free-throw line sits 13.75 ft
# from the hoop, so short mid is effectively "inside the free-throw line" and long
# mid is "the free-throw line out to the arc".
RIM_MAX_FT = 3.0
SHORT_MID_MAX_FT = 13.0
ZONE_ORDER = ("RIM", "SHORT MID", "LONG MID", "THREE")


# --- Polar cell grid, the fine spatial partition ---------------------------
# Distance bands every 4 ft, each cut into angular sectors from the hoop. The
# sector count changes at the three-point line and nowhere else, which is the
# whole reason this grid is drawable. NBA's own SHOT_ZONE_AREA steps from three
# sectors to five at 16 ft, and DEVELOPMENT.md records that drawing that real
# geometry reads as a rendering fault, because the floor has no line at 16 ft
# for the step to sit on. Moving the step to the arc keeps NBA's angular cuts --
# 60/120 inside, 36/72/108/144 outside -- while putting the change where the
# court already has a painted line to justify it.
POLAR_BANDS = (0.0, 4.0, 8.0, 12.0, 16.0, 23.75)
INNER_SECTORS = 3          # 60 degrees each, matching NBA's 8-16 ft scheme
THREE_SECTORS = 5          # 36 degrees each, matching NBA's beyond-16 ft scheme
# The innermost band is one cell, not three. At 0-4 ft the sectors would be a
# couple of feet of arc wide, and angle stops describing anything a defence
# actually defends.
MIN_CELL_FGA = 15          # below this a cell's FG% is not worth colouring
# The outer edge is a counting rule and a drawing rule at once, deliberately:
# the drawn region and the counted region must be the same object or the chart
# can show one set of cells while totalling another. 30 ft drops only heaves.
THREE_MAX_FT = 30.0

SECTOR_NAMES = {
    3: ("LEFT", "MIDDLE", "RIGHT"),
    5: ("LEFT CORNER", "LEFT WING", "TOP", "RIGHT WING", "RIGHT CORNER"),
}


def sector_index(loc_x, loc_y, n_sectors: int) -> np.ndarray:
    """Which angular sector a shot falls in, 0 = the viewer's left.

    Angle is measured at the hoop, so a sector is a wedge rather than a vertical
    slab -- which is how a defence is arranged and how NBA's own zones work.
    """
    ang = np.degrees(np.arctan2(np.maximum(np.asarray(loc_y, dtype=float), 0.0),
                                np.asarray(loc_x, dtype=float)))
    return np.clip(((180.0 - ang) // (180.0 / n_sectors)).astype(int),
                   0, n_sectors - 1)


def polar_cells() -> list[dict]:
    """Every cell in the grid, as geometry plus the label it carries.

    Returned outermost-first so a renderer can paint straight down the list and
    have nearer bands land on top of farther ones.
    """
    # ``draw_in`` exists only because a corner three is not defined by radius.
    # A baseline shot at 23 ft with |x| > 220 is a three, so an annulus starting
    # at the arc would leave the corner pocket unpainted. The three-point cells
    # therefore draw from the hoop outward and the two-point cells, clipped to
    # the corner line, paint over the middle -- the same trick ``rings`` uses.
    cells: list[dict] = []
    for i in range(THREE_SECTORS):
        cells.append({"key": f"3PT-{i}", "three": True, "sector": i,
                      "n_sectors": THREE_SECTORS, "r_in": POLAR_BANDS[-1],
                      "r_out": THREE_MAX_FT, "draw_in": 0.0, "band": "3PT",
                      "name": f"{SECTOR_NAMES[THREE_SECTORS][i]} 3"})
    for b in range(len(POLAR_BANDS) - 2, -1, -1):
        r_in, r_out = POLAR_BANDS[b], POLAR_BANDS[b + 1]
        n = 1 if b == 0 else INNER_SECTORS
        band = f"{r_in:.0f}-{r_out:.0f} FT"
        for i in range(n):
            cells.append({"key": f"{b}-{i}", "three": False, "sector": i,
                          "n_sectors": n, "r_in": r_in, "r_out": r_out,
                          "draw_in": r_in, "band": band,
                          "name": band if n == 1 else f"{SECTOR_NAMES[n][i]} {band}"})
    return cells


def _cell_mask(df: pd.DataFrame, cell: dict) -> pd.Series:
    """Rows falling in one cell. The 2PT/3PT split follows NBA's own flag.

    Using ``shot_type`` rather than radius is what keeps the corner pocket
    honest: a 22 ft baseline shot is a three even though it sits inside the
    arc's radius, and the drawn geometry stops the two-point wedges at the
    corner line to match.
    """
    is_three = df["shot_type"] == "3PT"
    if cell["three"]:
        mask = is_three & (df["shot_distance"] <= THREE_MAX_FT)
    else:
        d = df["shot_distance"]
        mask = ~is_three & (d >= cell["r_in"]) & (d < cell["r_out"])
    if cell["n_sectors"] == 1:
        return mask
    sec = sector_index(df["loc_x"], df["loc_y"], cell["n_sectors"])
    return mask & (sec == cell["sector"])


def polar_split(player: pd.DataFrame, league: pd.DataFrame,
                min_fga: int = MIN_CELL_FGA) -> pd.DataFrame:
    """Per-cell shooting, measured against the league from the same cell.

    ``rated`` is the honesty flag. One player-season spread over 18 cells leaves
    several holding a dozen shots, where a shooting percentage swings 20 points
    on chance alone; the renderer greys those out rather than colouring a number
    it cannot stand behind.
    """
    rows = []
    for cell in polar_cells():
        shots, lg = player[_cell_mask(player, cell)], league[_cell_mask(league, cell)]
        fg = float(shots["shot_made"].mean()) if len(shots) else np.nan
        lg_fg = float(lg["shot_made"].mean()) if len(lg) else np.nan
        rows.append({**cell, "fga": len(shots),
                     "fgm": int(shots["shot_made"].sum()) if len(shots) else 0,
                     "fg": fg, "lg_fg": lg_fg,
                     "fg_rel": (fg - lg_fg) * 100 if len(shots) and len(lg) else np.nan,
                     "share": len(shots) / len(player) * 100 if len(player) else 0.0,
                     "rated": bool(len(shots) >= min_fga and len(lg))})
    return pd.DataFrame(rows)


# --- Distance ladder, the "Midrange Is Dead" partition ---------------------
# Concentric distance bands and nothing else -- no angle, no zone taxonomy. The
# point of this one is that shot value is very nearly a pure function of
# distance, and the discontinuity at the arc is the only place that breaks.
# Reading it outward, points per shot falls from ~1.5 at the rim to its floor
# just INSIDE the three-point line, then jumps a third of a point the moment a
# shot crosses it. That cliff is the whole argument, and only a fine, uniform
# ladder shows it; a four-zone chart averages straight across it.
# 2 ft bands, not 1 ft. Two independent reasons point the same way.
#
# Statistically, 1 ft oversamples: across the league's own ladder, 21 of 29
# neighbouring 1 ft bands are statistically indistinguishable from each other,
# so most of that resolution is rendering noise as detail. Pooling pairs turns
# the league's mid-range from a jittery walk into a clean monotonic decline.
#
# Physically, a foot is finer than the thing being measured. A shooter and his
# defender occupy roughly two feet of floor, so a 14 ft shot and a 15 ft shot
# are not different basketball situations -- they are the same shot measured
# twice. Bands should be no finer than the resolution at which the phenomenon
# actually varies.
#
# It also halves the number of bands too thin to rate on a single team season,
# from 12 to 2, which is what makes a team chart readable at all.
LADDER_STEP_FT = 2.0
# Divides evenly by both 1 and 2 ft, so the outer edge is the same wherever the
# band width lands. Attempts past it are excluded and reported, not absorbed
# into a catch-all band -- a band with no outer edge is not a distance band.
LADDER_MAX_FT = 30.0
# Inside this radius a ring counts TWO-point attempts only; outside it, THREES
# only. This is the load-bearing choice, and it is what the reference card does.
#
# Binning purely by distance destroys the chart's entire finding. The 22-24 ft
# rings would then be ~95% corner threes, so they read ~1.15 points per shot and
# the value curve rises smoothly into the arc. Splitting by shot type instead
# exposes the real shape: a two-point attempt from 23-24 ft is worth 0.61
# points, the worst shot in basketball, and stepping back over the line doubles
# it. Verified against the published card.
#
# That card pays a heavy price for the split and we do not. It drops every three
# inside the radius -- 22% of all NBA threes -- and then paints their pocket
# with the above-the-break value from 24-25 ft. Corner threes are the second
# most efficient shot in basketball, 1.15 points per attempt against 1.05 above
# the break, so the corner reads as a merely-good area when it is a great one.
# ``corner_mask`` carves the pocket out and gives it its own value instead.
LADDER_TWO_MAX_FT = 24.0
# Below this a ring's rate is not worth colouring. 40 rather than 25: a 1 ft
# band holding 30 attempts carries a points-per-shot swing of roughly +/-0.2,
# which is the entire width of the relative charts' colour scale -- it would
# render as confident dark green or dark red on nothing but chance. Costs the
# season) and costs the league chart nothing: every league band clears 40 with
# room to spare. Paired with 2 ft bands it leaves the Bulls chart 2 bands grey.
MIN_RING_FGA = 40


CORNER_LINE_X = 220.0      # the corner three-point line, in NBA units (22 ft)


def corner_mask(df: pd.DataFrame, two_max: float = LADDER_TWO_MAX_FT) -> pd.Series:
    """The corner-three pocket: outside the corner line, inside the split radius.

    This region is exactly one shot type. Verified on 219,160 league attempts:
    **zero** two-pointers fall beyond the corner line inside 24 ft, because
    beyond that line there is no such thing as a two. So carving the pocket out
    of the radial ladder costs nothing in purity and buys back every corner
    three the ladder would otherwise have to drop.
    """
    return ((df["shot_type"] == "3PT") & (df["loc_x"].abs() >= CORNER_LINE_X)
            & (df["shot_distance"] < two_max))


def _ladder_ring_mask(df: pd.DataFrame, lo: float, hi: float,
                      two_max: float) -> pd.Series:
    """Which attempts belong to the ring spanning ``lo``-``hi`` feet.

    Inside the split radius a ring holds two-pointers and stops at the corner
    line, so the pocket beyond it belongs to ``corner_mask`` instead. Outside
    the split radius a ring holds threes and runs the full width.
    """
    band = (df["shot_distance"] >= lo) & (df["shot_distance"] < hi)
    is_three = df["shot_type"] == "3PT"
    if lo >= two_max:
        return band & is_three
    return band & ~is_three & (df["loc_x"].abs() < CORNER_LINE_X)


def corner_split(shots: pd.DataFrame, league: pd.DataFrame | None = None,
                 two_max: float = LADDER_TWO_MAX_FT,
                 min_fga: int = MIN_RING_FGA) -> dict:
    """The corner pocket as a single cell, measured like any ring.

    Kept whole rather than cut into bands: the pocket spans barely two feet
    of radius, and splitting it would put a few hundred attempts in each slice
    for no gain -- distance is not what makes a corner three good.
    """
    pocket = shots[corner_mask(shots, two_max)]
    row = {"fga": len(pocket), "fg": np.nan, "pps": np.nan, "lg_fg": np.nan,
           "lg_pps": np.nan, "fg_rel": np.nan, "pps_rel": np.nan,
           "rated": bool(len(pocket) >= min_fga)}
    if len(pocket):
        row["fg"] = float(pocket["shot_made"].mean())
        row["pps"] = float(_points(pocket).mean())
    if league is not None:
        lg = league[corner_mask(league, two_max)]
        if len(lg):
            row["lg_fg"] = float(lg["shot_made"].mean())
            row["lg_pps"] = float(_points(lg).mean())
            if len(pocket):
                row["fg_rel"] = (row["fg"] - row["lg_fg"]) * 100
                row["pps_rel"] = row["pps"] - row["lg_pps"]
    return row


def ladder_coverage(shots: pd.DataFrame, two_max: float = LADDER_TWO_MAX_FT,
                    max_ft: float = LADDER_MAX_FT) -> dict:
    """What the ladder leaves out, so the omission can be stated on the graphic.

    With the corner pocket carved out, almost nothing is left out: only heaves
    past ``max_ft`` and a tiny sliver of above-the-break threes that register
    just under the split radius (~190 in a league season, 0.2% of all threes),
    which the arc's own geometry makes unavoidable at 1 ft resolution.
    """
    is_three = shots["shot_type"] == "3PT"
    in_range = shots["shot_distance"] < max_ft
    stray_threes = int((is_three & (shots["shot_distance"] < two_max) & in_range
                        & (shots["loc_x"].abs() < CORNER_LINE_X)).sum())
    long_twos = int((~is_three & (shots["shot_distance"] >= two_max)
                     & in_range).sum())
    deep = int((~in_range).sum())
    excluded = stray_threes + long_twos + deep
    n_three = int(is_three.sum())
    return {"total": len(shots), "corner_threes": int(corner_mask(shots, two_max).sum()),
            "stray_threes": stray_threes, "long_twos": long_twos,
            "beyond_range": deep, "excluded": excluded,
            "excluded_share": excluded / len(shots) if len(shots) else 0.0,
            "three_share_excluded": stray_threes / n_three if n_three else 0.0}


def ladder_edges(step: float = LADDER_STEP_FT,
                 max_ft: float = LADDER_MAX_FT) -> np.ndarray:
    """Band edges that stop at or below ``max_ft`` -- never past it.

    Snapping down matters once band width is a choice: at 2 ft wide a naive
    range would run 30-32 ft and silently readmit the heaves ``max_ft`` exists
    to exclude. The last edge returned is the chart's true outer limit, and
    ``ladder_coverage`` must be given the same figure or the "% shown" line
    will disagree with the picture.
    """
    n = int(max_ft / step + 1e-9)
    return np.arange(n + 1) * step


def distance_ladder(shots: pd.DataFrame, league: pd.DataFrame | None = None,
                    step: float = LADDER_STEP_FT, max_ft: float = LADDER_MAX_FT,
                    two_max: float = LADDER_TWO_MAX_FT,
                    min_fga: int = MIN_RING_FGA) -> pd.DataFrame:
    """Points per shot and FG% for every distance band, optionally vs the league.

    Points per shot -- not FG% -- is what makes distance comparable across the
    arc. A 35% three and a 52.5% two are the same 1.05 points, so PPS is the
    only scale on which "is this shot worth taking" has one answer everywhere on
    the floor. FG% is still returned because it answers the other question,
    *how well did they shoot it*, which is what a league comparison needs.
    """
    edges_ft = ladder_edges(step, max_ft)
    rows = []
    for lo, hi in zip(edges_ft[:-1], edges_ft[1:]):
        ring = shots[_ladder_ring_mask(shots, lo, hi, two_max)]
        row = {"lo": lo, "hi": hi, "three": bool(lo >= two_max), "fga": len(ring),
               "fgm": 0, "pps": np.nan, "fg": np.nan, "lg_pps": np.nan,
               "lg_fg": np.nan, "fg_rel": np.nan, "pps_rel": np.nan,
               "rated": False}
        if len(ring):
            row["fgm"] = int(ring["shot_made"].sum())
            row["fg"] = float(ring["shot_made"].mean())
            row["pps"] = float(_points(ring).mean())
        if league is not None:
            lg = league[_ladder_ring_mask(league, lo, hi, two_max)]
            if len(lg):
                row["lg_fg"] = float(lg["shot_made"].mean())
                row["lg_pps"] = float(_points(lg).mean())
                if len(ring):
                    row["fg_rel"] = (row["fg"] - row["lg_fg"]) * 100
                    row["pps_rel"] = row["pps"] - row["lg_pps"]
        row["rated"] = bool(len(ring) >= min_fga)
        rows.append(row)
    return pd.DataFrame(rows)


def _points(df: pd.DataFrame) -> pd.Series:
    """Points scored by each attempt, honouring the extra point beyond the arc."""
    return df["shot_made"].astype(float) * np.where(df["shot_type"] == "3PT", 3, 2)


def edges() -> tuple[np.ndarray, np.ndarray]:
    """Shared grid edges, so player and league maps always align cell-for-cell."""
    return (np.arange(GRID_X[0], GRID_X[1] + CELL, CELL),
            np.arange(GRID_Y[0], GRID_Y[1] + CELL, CELL))


def within_range(df: pd.DataFrame, max_dist_ft: float = MAX_DIST_FT) -> pd.DataFrame:
    return df[df["shot_distance"] <= max_dist_ft]


def density(df: pd.DataFrame, blur_ft: float = BLUR_FT) -> np.ndarray:
    """Smoothed, normalised shot-location density, shaped ``(nx, ny)``.

    A 2D histogram plus a Gaussian blur is the same kernel-density idea as the
    F5 tutorial's ``MASS::kde2d``, but it scales to the league's ~219k shots.
    Normalising to sum 1 turns counts into "share of this shooter's diet", which
    is what makes players of different volume comparable.
    """
    xe, ye = edges()
    counts, _, _ = np.histogram2d(df["loc_x"], df["loc_y"], bins=[xe, ye])
    smooth = gaussian_filter(counts, sigma=blur_ft * 10.0 / CELL, mode="constant")
    total = smooth.sum()
    return smooth / total if total else smooth


def signed_diff(player_pdf: np.ndarray, league_pdf: np.ndarray) -> np.ndarray:
    """Player density minus league density, with off-court cells zeroed.

    Positive where he shoots MORE than a league-average shot would come from;
    negative where he shoots less. Cells at or below the baseline are cleared so
    heat never bleeds off the bottom of the court.
    """
    diff = player_pdf - league_pdf
    _, ye = edges()
    centres = (ye[:-1] + ye[1:]) / 2.0
    diff[:, centres <= BASELINE_Y] = 0.0
    return diff


def zone_masks(df: pd.DataFrame, rim_max: float = RIM_MAX_FT,
               short_mid_max: float = SHORT_MID_MAX_FT) -> dict[str, pd.Series]:
    """Boolean masks for the four concentric zones."""
    two = df["shot_type"] != "3PT"
    d = df["shot_distance"]
    return {
        "RIM": two & (d <= rim_max),
        "SHORT MID": two & (d > rim_max) & (d <= short_mid_max),
        "LONG MID": two & (d > short_mid_max),
        "THREE": ~two,
    }


def zone_split(player: pd.DataFrame, league: pd.DataFrame, player_poss: float,
               league_poss: float, rim_max: float = RIM_MAX_FT,
               short_mid_max: float = SHORT_MID_MAX_FT) -> pd.DataFrame:
    """Per-zone volume and efficiency, each measured against the league.

    Returns one row per zone with attempts, FG%, the league's FG% from the same
    band, per-75 rates for both, and the two relative figures the charts encode.
    """
    lz = zone_masks(league, rim_max, short_mid_max)
    rows = []
    for zone, mask in zone_masks(player, rim_max, short_mid_max).items():
        shots, lg_shots = player[mask], league[lz[zone]]
        if shots.empty or lg_shots.empty:
            continue
        fg, lg_fg = shots["shot_made"].mean(), lg_shots["shot_made"].mean()
        per75 = len(shots) / player_poss * 75
        lg_per75 = len(lg_shots) / league_poss * 75
        rows.append({
            "zone": zone, "fga": len(shots), "fgm": int(shots["shot_made"].sum()),
            "fg": fg, "lg_fg": lg_fg, "fg_rel": (fg - lg_fg) * 100,
            "per75": per75, "lg_per75": lg_per75,
            "vol_rel": (per75 / lg_per75 - 1) * 100 if lg_per75 else 0.0,
            "pps": fg * (3 if zone == "THREE" else 2),
        })
    order = {z: i for i, z in enumerate(ZONE_ORDER)}
    return pd.DataFrame(rows).sort_values("zone", key=lambda c: c.map(order),
                                          ignore_index=True)


def separable(made: int, attempts: int, league_rate: float,
              z: float = 1.96) -> bool:
    """Whether a player's rate is distinguishable from the league's.

    A single player-season splits thin fast: sub-regions of a zone routinely hold
    30-40 attempts, where a shooting percentage carries a swing of +/-15 points.
    This is the guard against publishing noise as a finding.
    """
    if attempts <= 0:
        return False
    p = made / attempts
    se = np.sqrt(p * (1 - p) / attempts)
    return bool(p - z * se > league_rate or p + z * se < league_rate)
