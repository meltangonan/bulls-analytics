"""Shot-location analysis shared by the shot-chart family.

Two independent methods live here, and they answer different questions:

* **Density** (``density`` / ``signed_diff``) -- the F5 hot-spot method. Smooths
  shot locations into a distribution, normalises it, and subtracts the league's.
  Answers *where does he shoot from, relative to everyone else*. Frequency only;
  it says nothing about whether the shots went in.

* **Zones** (``zone_split``) -- the RIM / SHORT MID / LONG MID / THREE taxonomy,
  with per-75 volume and FG% measured against the league in the same band.
  Answers *how often and how well, compared with everyone else*.

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
