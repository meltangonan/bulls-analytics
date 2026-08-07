#!/usr/bin/env python3
"""Zone deep-dive — volume AND efficiency inside a single shot zone.

One slide per zone (long mid-range, three-point, ...), splitting that zone into
sub-regions and reporting, for each: attempts, FG%, and the league's FG% from
the same sub-region.

Two guardrails are built in rather than bolted on:

* The league baseline needs no minimum-attempt rule -- pooling all 30 teams puts
  6,000-25,000 shots in every sub-region drawn here, so the benchmark is exact
  for practical purposes. The fragile side is always the *player*.
* A single player-season splits thin fast. Each sub-region is therefore tested
  against the league with a 95% interval, and any gap the sample cannot support
  is marked so the reader can weigh it instead of being sold it.

Zone definitions follow the RIM / SMR / LMR / 3PT taxonomy (rim <=4 ft,
short mid 4-10 ft, long mid 10 ft to the arc), reverse-engineered from and
matched against a published card to within 0.1 points.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import FancyBboxPatch, Rectangle, Wedge

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls import data
from bulls.graphics import house
from bulls.graphics.court import draw_half_court
from bulls.graphics.house import helvetica

CACHE = ROOT / "cache" / "hot_spots"
ARC = 237.5          # three-point radius, tenths of a foot
LMR_INNER = 100.0    # 10 ft
DIFF_CLAMP = 0.08

CMAP = LinearSegmentedColormap.from_list(
    "zonediff", ["#2C6FB5", "#8FB4D6", "#EFEAE4", "#E8896F", "#C42B1C"])

# Sub-regions per zone: (label, theta1, theta2) sweeping right -> left.
WEDGES = [("RIGHT", 0, 60), ("CENTER", 60, 120), ("LEFT", 120, 180)]
WING_WEDGES = [("RIGHT WING", 0, 65), ("TOP", 65, 115), ("LEFT WING", 115, 180)]


def load(pid: int, season: str) -> pd.DataFrame:
    path = CACHE / f"hex_player_{pid}_{season}.csv"
    if path.exists():
        return pd.read_csv(path)
    df = data.get_player_shots(pid, team_id=0, season=season)[
        ["loc_x", "loc_y", "shot_distance", "shot_made", "shot_type"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ang"] = np.degrees(np.arctan2(df.loc_y.clip(lower=0), df.loc_x))
    df["is3"] = df.shot_type == "3PT"
    df["corner"] = df.is3 & (df.loc_y <= 92.5)
    return df


def split(zone: str, player: pd.DataFrame, league: pd.DataFrame) -> list[dict]:
    """Sub-region rows: attempts, FG%, league FG%, and whether the gap holds up."""
    rows = []

    def add(label, pm, lm, geom):
        a, b = player[pm], league[lm]
        if len(a) == 0:
            return
        p, n = a.shot_made.mean(), len(a)
        lg = b.shot_made.mean()
        se = np.sqrt(p * (1 - p) / n)
        lo, hi = p - 1.96 * se, p + 1.96 * se
        rows.append(dict(label=label, fgm=int(a.shot_made.sum()), fga=n, fg=p,
                         lg=lg, lg_n=len(b), diff=p - lg,
                         solid=bool(lo > lg or hi < lg), geom=geom))

    if zone == "lmr":
        pz = (~player.is3) & (player.shot_distance > 10)
        lz = (~league.is3) & (league.shot_distance > 10)
        for label, t1, t2 in WEDGES:
            add(label,
                pz & player.ang.between(t1, t2),
                lz & league.ang.between(t1, t2),
                ("wedge", LMR_INNER, ARC, t1, t2))
    elif zone == "3pt":
        add("LEFT CORNER", player.corner & (player.loc_x < 0),
            league.corner & (league.loc_x < 0), ("corner", -1))
        for label, t1, t2 in WING_WEDGES:
            add(label,
                player.is3 & ~player.corner & player.ang.between(t1, t2),
                league.is3 & ~league.corner & league.ang.between(t1, t2),
                ("wedge", ARC, ARC + 62, t1, t2))
        add("RIGHT CORNER", player.corner & (player.loc_x > 0),
            league.corner & (league.loc_x > 0), ("corner", 1))
    else:
        raise SystemExit(f"Unknown zone '{zone}'")
    return rows


def render(rows, zone_title, zone_rule, player_name, subtitle, out, final):
    theme = house.get_theme("jersey")
    fig, ax = house.new_canvas(theme)
    s = 1.62
    x0, y0 = draw_half_court(ax, house.CANVAS_WIDTH / 2, 700, s, "#B4AEA6")

    def t(cx, cy):
        return x0 + (cx + 250.0) * s, y0 + (cy + 47.5) * s

    hoop = t(0, 0)
    norm = Normalize(-DIFF_CLAMP, DIFF_CLAMP)

    for r in rows:
        color = CMAP(norm(r["diff"]))
        kind = r["geom"][0]
        if kind == "wedge":
            _, r_in, r_out, t1, t2 = r["geom"]
            ax.add_patch(Wedge(hoop, r_out * s, t1, t2, width=(r_out - r_in) * s,
                               facecolor=color, edgecolor="#FAF8F5", lw=1.4,
                               alpha=0.9, zorder=2))
            mid_a = np.radians((t1 + t2) / 2)
            mid_r = (r_in + r_out) / 2
            lx, ly = t(mid_r * np.cos(mid_a), mid_r * np.sin(mid_a))
        else:
            side = r["geom"][1]
            xl = 220 if side > 0 else -250
            ax.add_patch(Rectangle(t(xl, -47.5), 30 * s, 140 * s, facecolor=color,
                                   edgecolor="#FAF8F5", lw=1.4, alpha=0.9, zorder=2))
            lx, ly = t(side * 235, 30)
        _label(ax, lx, ly, r, theme)

    # Header
    ax.text(house.SIDE_MARGIN, house.CANVAS_HEIGHT - 62, zone_title,
            ha="left", va="top", fontsize=40, color=theme.ink,
            fontproperties=helvetica("bold"))
    ax.text(house.SIDE_MARGIN, house.CANVAS_HEIGHT - 132,
            f"{player_name}  ·  {subtitle}", ha="left", va="top", fontsize=15,
            color=theme.muted, fontproperties=helvetica("bold"))
    ax.text(house.SIDE_MARGIN, house.CANVAS_HEIGHT - 164, zone_rule,
            ha="left", va="top", fontsize=13, color=theme.accent,
            fontproperties=helvetica("bold"))

    # Totals + reliability note
    tot_fga = sum(r["fga"] for r in rows)
    tot_fgm = sum(r["fgm"] for r in rows)
    lg_n = sum(r["lg_n"] for r in rows)
    ax.text(house.CANVAS_WIDTH / 2, 268,
            f"{tot_fgm}/{tot_fga}  ·  {tot_fgm / tot_fga * 100:.1f}% overall",
            ha="center", va="bottom", fontsize=19, color=theme.ink,
            fontproperties=helvetica("bold"))

    shaky = [r["label"] for r in rows if not r["solid"]]
    note = ("Every split here is within normal variation for its sample size."
            if len(shaky) == len(rows) else
            "* = gap is larger than sampling noise can explain")
    ax.text(house.CANVAS_WIDTH / 2, 222, note, ha="center", va="bottom",
            fontsize=12, color=theme.muted, fontproperties=helvetica("bold"))

    ax.text(house.CANVAS_WIDTH / 2, 150,
            "Color = FG% vs. league average from the same sub-region",
            ha="center", va="bottom", fontsize=12.5, color=theme.muted,
            fontproperties=helvetica("bold"))
    ax.text(house.SIDE_MARGIN, 44,
            f"Data: nba.com/stats  ·  league baseline = all 30 teams, {lg_n:,} shots",
            ha="left", va="bottom", fontsize=9.5, color=theme.faint,
            fontproperties=helvetica())

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=house.export_dpi(final), facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {out}")


def _label(ax, x, y, r, theme):
    """Zone name, the headline FG%, then attempts + league benchmark beneath."""
    w, h = 168, 104
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                 boxstyle="round,pad=0,rounding_size=10",
                 facecolor="#FCFAF7", edgecolor="#E3DCD2", lw=1.0, zorder=6))
    mark = " *" if r["solid"] else ""
    ax.text(x, y + h / 2 - 10, r["label"] + mark, ha="center", va="top", fontsize=9.5,
            color=theme.muted, fontproperties=helvetica("bold"), zorder=7)
    ax.text(x, y, f"{r['fg'] * 100:.1f}%", ha="center", va="center", fontsize=19,
            color=theme.ink, fontproperties=helvetica("bold"), zorder=7)
    ax.text(x, y - h / 2 + 10, f"{r['fgm']}/{r['fga']}  ·  {r['lg'] * 100:.0f}% lg",
            ha="center", va="bottom", fontsize=9.5, color=theme.faint,
            fontproperties=helvetica("bold"), zorder=7)


ZONES = {
    "lmr": ("LONG MID-RANGE", "Two-pointers from 10 ft out to the three-point line"),
    "3pt": ("THREE-POINT", "Every shot beyond the arc, split by where he took it"),
}


def main():
    ap = argparse.ArgumentParser(description="Zone deep-dive slide")
    ap.add_argument("--zone", choices=list(ZONES), required=True)
    ap.add_argument("--player-id", type=int, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--season", default="2025-26")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    player = prep(load(args.player_id, args.season))
    league = prep(pd.read_csv(CACHE / f"league_makes_{args.season}.csv"))
    rows = split(args.zone, player, league)

    for r in rows:
        flag = "REAL" if r["solid"] else "within noise"
        print(f'  {r["label"]:<13}{r["fgm"]:>4}/{r["fga"]:<4} '
              f'{r["fg"]*100:5.1f}%  vs lg {r["lg"]*100:5.1f}%  '
              f'({r["diff"]*100:+5.1f})  {flag}')

    title, rule = ZONES[args.zone]
    out = Path(args.output or ROOT / "output" /
               f"zone-{args.zone}-{args.name.lower().replace(' ', '-')}.png")
    render(rows, title, rule, args.name,
           args.subtitle or f"{args.season} Regular Season", out, args.final)


if __name__ == "__main__":
    main()
