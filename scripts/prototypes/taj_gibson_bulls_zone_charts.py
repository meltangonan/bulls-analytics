#!/usr/bin/env python3
"""Build Taj Gibson's Bulls tenure zone chart and his career shot diet.

    ../bulls-analytics/venv/bin/python \
        scripts/prototypes/taj_gibson_bulls_zone_charts.py --final

The fifth in the tenure family, after Rose, DeRozan, Butler, Hinrich and
Buzelis, and deliberately identical to them in method: same twelve zones, same
per-season reconciliation against official totals, same pooled baseline.

Two differences from the others, both deliberate:

**Only the tenure page is rendered.** The retirement post has room for one shot
slide, not eight. The per-season shots are still fetched and reconciled, because
the tenure pool is built from them and a season that fails its check must fail
loudly rather than be quietly averaged into the total.

**A shot diet travels with it.** ``shot-diet.csv`` is the career family split
from ``bulls.analysis.shot_families``. Note what that module warns about:
``Jump Shot`` is the scorer's unlabelled default rather than a measured
technique, so the largest family is a residual bucket. It is kept because
dropping it would misstate every other share, and the rendered slide has to say
what it is instead of implying a technique nobody recorded.

His eight Bulls seasons are contiguous, so unlike Hinrich there is no gap to
explain; his last season is split by the February 2017 trade to Oklahoma City,
which the Chicago team filter handles.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats, shotchartdetail

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.analysis import shot_families as sf
from bulls.analysis import shot_maps as sm
from bulls.config import BULLS_TEAM_ID
from bulls.data import fetch
from bulls.data import shots as shot_data
from scripts import make_shot_chart as shot_chart

PLAYER_ID = 201959
PLAYER_NAME = "Taj Gibson"
SEASONS = (
    "2009-10", "2010-11", "2011-12", "2012-13",
    "2013-14", "2014-15", "2015-16", "2016-17",
)
SEASON_MIN_ZONE_FGA = sm.MIN_ZONE12_FGA_PLAYER
# The floor scales with the pooled window for the same reason it does elsewhere
# in this family: a zone that clears the season threshold once should not read
# as equally well established when eight seasons were pooled to reach it.
TENURE_MIN_ZONE_FGA = SEASON_MIN_ZONE_FGA * len(SEASONS)

PROJECT = "taj-gibson-retirement"
SLUG = "2026-09-15-taj-gibson-retirement"
DEFAULT_DATA = _REPO / "docs/visuals" / SLUG / "data"
DEFAULT_OUTPUT = _REPO / "output" / PROJECT

# Verified against FranchisePlayers on 2026-09-15.
EXPECTED_TENURE_FGA = 4408


def fetch_bulls_totals(season: str) -> pd.Series:
    """Taj's official Chicago regular-season totals for one season."""
    table = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=BULLS_TEAM_ID,
        headers=fetch._NBA_HEADERS,
        timeout=60,
    ).get_data_frames()[0]
    row = table[table["PLAYER_ID"] == PLAYER_ID]
    if row.empty:
        raise ValueError(f"{PLAYER_NAME} has no Chicago {season} row.")
    return row.iloc[0]


def load_bulls_totals(season: str, data_dir: Path, refresh: bool = False) -> pd.Series:
    path = data_dir / f"{season}-taj-gibson-bulls-totals.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path).iloc[0]
    totals = fetch_bulls_totals(season)
    totals.to_frame().T.to_csv(path, index=False)
    return totals


def load_bulls_shots(season: str, totals: pd.Series, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    path = data_dir / f"{season}-taj-gibson-bulls-shots.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch.get_player_shots(
            PLAYER_ID, team_id=BULLS_TEAM_ID, season=season
        )
        if shots.empty:
            raise ValueError(f"NBA.com returned no {PLAYER_NAME} shots for {season}")
        shots.to_csv(path, index=False)
    reconcile_shot_count(season, totals, shots)
    return shots


def reconcile_shot_count(season: str, totals: pd.Series,
                         shots: pd.DataFrame) -> None:
    """Every shot row must be an attempt the official totals also counted."""
    expected, actual = int(totals.FGA), len(shots)
    if actual != expected:
        raise ValueError(f"{season}: shot rows {actual} != Bulls FGA {expected}")


def drop_unlabelled_league_rows(league: pd.DataFrame, season: str) -> pd.DataFrame:
    """Remove baseline rows NBA.com never assigned a shot zone.

    Older seasons carry a handful of shots with no ``shot_zone``: tens of rows
    per season against roughly 200,000, and none at all from 2024-25 onward,
    which is why the rest of this family never meets them. ``zone12_of_shots``
    refuses the whole frame rather than guess, and that is the right default.

    They are dropped from the *baseline* rather than placed by coordinate,
    because a zone NBA.com declined to assign is unavailable, not derivable.
    Every one of Taj's own 4,408 attempts is labelled, so nothing of his is
    lost; this only very slightly thins the league average he is measured
    against. The count is printed so the exclusion is never silent.
    """
    if "shot_zone" not in league.columns:
        return league
    missing = int(league["shot_zone"].isna().sum())
    if missing:
        share = missing / len(league) * 100
        print(f"  {season}: dropped {missing} unlabelled league rows ({share:.3f}%)")
        return league[league["shot_zone"].notna()].copy()
    return league


def tenure_totals(season_totals: list[pd.Series]) -> pd.Series:
    """Add counting fields; each game belongs to exactly one Bulls season."""
    return pd.Series({
        "GP": sum(int(row.GP) for row in season_totals),
        "MIN": sum(float(row.MIN) for row in season_totals),
        "PTS": sum(int(row.PTS) for row in season_totals),
        "FGA": sum(int(row.FGA) for row in season_totals),
    })


def load_labelled_shots(season: str, totals: pd.Series, data_dir: Path,
                        refresh: bool = False) -> pd.DataFrame:
    """One season of shots keeping ``ACTION_TYPE``, for the family split.

    ``bulls.data.shots`` trims to the geometry columns the zone charts need,
    which drops the label the shot diet is built from, so this takes the same
    route the shot-family posts do and reconciles the same way.
    """
    path = data_dir / f"{season}-taj-gibson-bulls-shot-families.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        frame = shotchartdetail.ShotChartDetail(
            team_id=BULLS_TEAM_ID, player_id=PLAYER_ID, season_nullable=season,
            season_type_all_star="Regular Season", last_n_games=0,
            context_measure_simple="FGA", timeout=60, headers=fetch._NBA_HEADERS,
        ).get_data_frames()[0]
        keep = ["GAME_ID", "GAME_DATE", "ACTION_TYPE", "SHOT_TYPE",
                "SHOT_ZONE_BASIC", "SHOT_DISTANCE", "SHOT_MADE_FLAG"]
        shots = frame.loc[:, keep].copy()
        shots.insert(0, "season", season)
        shots.to_csv(path, index=False)
    reconcile_shot_count(season, totals, shots)
    return shots


def shot_diet(shots: pd.DataFrame) -> pd.DataFrame:
    """Career family split, ordered by attempts, zeros kept.

    ``family_shares`` returns every family including ones he never used, which
    for a shot diet is itself the finding: a big man with no step-backs is a
    fact about him, not a row to drop.
    """
    diet = sf.family_shares(shots.ACTION_TYPE, shots.SHOT_MADE_FLAG)
    return diet.sort_values("fga", ascending=False).reset_index(drop=True)


def render_tenure(shots: pd.DataFrame, league: pd.DataFrame, output_dir: Path,
                  final: bool, ppg: float) -> Path:
    out = output_dir / f"{date.today().isoformat()}-zone-taj-gibson-bulls-tenure.png"
    shot_chart.render_zones(
        {
            "player": shots,
            "league": league,
            "name": PLAYER_NAME,
            "season": "Bulls tenure",
            "min_fga": TENURE_MIN_ZONE_FGA,
            "pill": "large",
            "summary_metrics": True,
            "summary_ppg": ppg,
        },
        out,
        final,
    )
    return out


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)

    all_shots, all_league, all_totals, all_labelled = [], [], [], []
    for season in SEASONS:
        print(f"{season} ...", flush=True)
        totals = load_bulls_totals(season, args.data_dir, args.refresh)
        shots = load_bulls_shots(season, totals, args.data_dir, args.refresh)
        league = shot_data.league_shots(season, args.refresh_league)
        if league.empty:
            raise ValueError(f"NBA.com returned no league shots for {season}")
        league = drop_unlabelled_league_rows(league, season)
        all_labelled.append(load_labelled_shots(
            season, totals, args.data_dir, args.refresh
        ))
        all_shots.append(shots.assign(source_season=season))
        all_league.append(league.assign(source_season=season))
        all_totals.append(totals)

    pooled_shots = pd.concat(all_shots, ignore_index=True)
    pooled_league = pd.concat(all_league, ignore_index=True)
    totals = tenure_totals(all_totals)
    if int(totals.FGA) != EXPECTED_TENURE_FGA:
        raise ValueError(
            f"Tenure FGA {int(totals.FGA)} != franchise record {EXPECTED_TENURE_FGA}"
        )

    zones = sm.zone12_split(pooled_shots, pooled_league, min_fga=TENURE_MIN_ZONE_FGA)
    audit = zones.copy()
    audit.insert(0, "window", "Bulls tenure")
    audit.to_csv(args.data_dir / "zone-splits.csv", index=False, float_format="%.4f")

    labelled = pd.concat(all_labelled, ignore_index=True)
    if len(labelled) != EXPECTED_TENURE_FGA:
        raise ValueError(
            f"Labelled rows {len(labelled)} != franchise FGA {EXPECTED_TENURE_FGA}"
        )
    diet = shot_diet(labelled)
    diet.to_csv(args.data_dir / "shot-diet.csv", index=False, float_format="%.4f")

    outputs = [render_tenure(
        pooled_shots, pooled_league, args.output_dir, args.final,
        float(totals.PTS) / int(totals.GP),
    )]

    print("\nTAJ GIBSON BULLS SHOT DIET")
    print(diet[["family", "fga", "share_pct", "fg_pct", "rated"]].round(1).to_string(index=False))
    print(f"\nPooled: {int(totals.FGA)} FGA over {int(totals.GP)} games")
    print(f"Data: {args.data_dir}")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh", action="store_true",
                        help="refetch his shots and totals")
    parser.add_argument("--refresh-league", action="store_true",
                        help="refetch the league baseline (about 30 requests per season)")
    parser.add_argument("--final", action="store_true")
    return parser.parse_args()


def main() -> None:
    for path in build(parse_args()):
        print(path)


if __name__ == "__main__":
    main()
