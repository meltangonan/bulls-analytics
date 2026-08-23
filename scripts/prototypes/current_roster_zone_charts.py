#!/usr/bin/env python3
"""Build twelve-zone shot charts for the Bulls and for qualified current players.

The follow-up to the hex carousel, asking a different question of the same data.
A hex chart draws where the shots came from and leaves most of the court empty;
this one partitions the whole half court into NBA's twelve named regions and
fills every one, so the reader gets a shot profile rather than a scatter.

Each zone carries two figures, weighted equally: how well he shoots there against
the league, and the share of his attempts that came from there against the NBA's
share. The colour encodes the first. Neither is derivable from the other, which
is the reason both are printed -- a player can be excellent in a zone he almost
never visits.

Points per shot is deliberately absent. Inside one zone the point value is fixed,
so PPS is FG% times a constant and "his PPS vs the league's" ranks identically to
"his FG% vs the league's". It earned its place on the scoring-by-location post
because that chart compared ACROSS zones; here it would be a third column saying
what the first already said.

Roster membership is live. Shot data is each player's complete 2025-26 regular
season across all teams, so a traded player's season stays intact.

Usage:
    venv/bin/python scripts/prototypes/current_roster_zone_charts.py
    venv/bin/python scripts/prototypes/current_roster_zone_charts.py --refresh
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.config import BULLS_TEAM_ID, CURRENT_SEASON
from bulls.data import shots as shot_data
from bulls.data.fetch import get_current_roster
from scripts import make_shot_chart as shot_chart


# The same floor the hex carousel used, so the two posts cover the same ten
# players and a reader meeting both sees one roster rather than two.
MIN_PLAYER_FGA = 250
PROJECT = "bulls-zone-charts"
SLUG = "2026-08-10-bulls-zone-charts"


def player_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "")


def qualifies_player(fga: int, minimum: int = MIN_PLAYER_FGA) -> bool:
    """Twelve zones split a season thin; below this too many go unrated to read."""
    return fga >= minimum


def summarise(subject: str, scope: str, shots: pd.DataFrame,
              zones: pd.DataFrame, min_fga: int) -> dict[str, object]:
    """One row per chart: what it claims, and how much of it is standing on air."""
    fga = len(shots)
    made = int(shots.shot_made.sum())
    threes = shots.shot_type.eq("3PT")
    rated = zones[zones.rated]
    return {
        "subject": subject,
        "scope": scope,
        "fga": fga,
        "fg_pct": round(made / fga * 100, 1) if fga else float("nan"),
        "efg_pct": round((made + 0.5 * int(shots.loc[threes, "shot_made"].sum()))
                         / fga * 100, 1) if fga else float("nan"),
        "zones_rated": int(len(rated)),
        "zones_grey": int(len(zones) - len(rated)),
        # The share of his attempts that sit in a coloured zone. A chart where
        # this is high is mostly assertion; where it is low, mostly grey.
        "rated_fga_share_pct": round(rated.fga.sum() / fga * 100, 1) if fga else 0.0,
        "min_zone_fga": min_fga,
    }


def build(args: argparse.Namespace) -> list[Path]:
    league = shot_data.league_shots(args.season, args.refresh)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    summary_rows: list[dict[str, object]] = []
    zone_tables: list[pd.DataFrame] = []
    stamp = date.today().isoformat()

    def render(subject: str, slug: str, shots: pd.DataFrame,
               scope: str, min_fga: int) -> None:
        ctx = {"player": shots, "league": league, "name": subject,
               "season": args.season, "min_fga": min_fga}
        out = args.output_dir / f"{stamp}-zones-{slug}.png"
        print(f"\n{subject}: {len(shots):,} FGA")
        shot_chart.render_zones(ctx, out, args.final)
        outputs.append(out)

        zones = sm.zone12_split(shots, league, min_fga=min_fga)
        summary_rows.append(summarise(subject, scope, shots, zones, min_fga))
        table = zones.copy()
        table.insert(0, "subject", subject)
        table.insert(1, "scope", scope)
        zone_tables.append(table)
        # The fetched rows behind the table travel with it. cache/shot_charts is
        # ignored, and a published number whose inputs live only there is one
        # worktree cleanup away from being unauditable.
        shots.to_csv(args.data_dir / f"{slug}-shots-{args.season}.csv", index=False)

    # The team first because it is the carousel's opener; team and player shot
    # shares now use the same all-attempts denominator logic.
    render("Chicago Bulls", "bulls",
           shot_data.team_shots(BULLS_TEAM_ID, args.season, args.refresh),
           "Chicago attempts", sm.MIN_ZONE12_FGA_TEAM)

    roster = get_current_roster()
    prepared = []
    excluded = []
    for player in roster.itertuples(index=False):
        shots = shot_data.player_shots(int(player.nba_id), args.season, args.refresh)
        if qualifies_player(len(shots), args.min_fga):
            prepared.append((str(player.official_roster_name), shots))
        else:
            excluded.append((str(player.official_roster_name), len(shots)))

    for name, shots in sorted(prepared, key=lambda item: (-len(item[1]), item[0])):
        render(name, player_slug(name), shots, "Full season, all teams",
               sm.MIN_ZONE12_FGA_PLAYER)

    zones_path = args.data_dir / f"zone-splits-{args.season}.csv"
    pd.concat(zone_tables, ignore_index=True).to_csv(
        zones_path, index=False, float_format="%.4f")
    summary_path = args.data_dir / f"zone-chart-summary-{args.season}.csv"
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(summary_path, index=False, float_format="%.1f")
    print("\nROSTER ZONE SUMMARY")
    print(f"Roster as of: {stamp}")
    print(f"Qualifier: {args.min_fga}+ FGA in the {args.season} NBA regular season")
    print(f"Colour floor: {sm.MIN_ZONE12_FGA_TEAM} attempts for the team chart, "
          f"{sm.MIN_ZONE12_FGA_PLAYER} for a player — both solved from the "
          f"colour scale, not chosen")
    print(summary.to_string(index=False))
    if excluded:
        print("Excluded: " + ", ".join(f"{n} ({f} FGA)" for n, f in excluded))
    print(f"Zone splits: {zones_path}")
    print(f"Summary: {summary_path}")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Bulls team and current-roster twelve-zone shot charts")
    parser.add_argument("--season", default=CURRENT_SEASON)
    parser.add_argument("--min-fga", type=int, default=MIN_PLAYER_FGA)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "output" / PROJECT)
    parser.add_argument("--data-dir", type=Path,
                        default=ROOT / "docs" / "visuals" / SLUG / "data")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
