#!/usr/bin/env python3
"""Build Matas Buzelis's two Bulls season zone charts and his tenure total.

Every player row is a regular-season field-goal attempt taken for Chicago.
Buzelis has played only for the Bulls, so his Chicago stint is his whole career;
the Chicago filter is kept anyway so the selecting total and the chart stay tied
to the same stint if he is ever traded.

Season pages use that season's NBA attempts as the comparison. The tenure page
pools the same two NBA seasons, so both player and baseline are attempt-weighted
across the identical window. The tenure colour floor scales with the pooled
window for the same reason it does elsewhere in this family: a zone that clears
20 attempts once should not read as equally well established when two seasons
were pooled to get there.

Usage:
    ../bulls-analytics/venv/bin/python \
        scripts/prototypes/matas_buzelis_bulls_zone_charts.py --refresh --final
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.config import BULLS_TEAM_ID
from bulls.data import fetch
from bulls.data import shots as shot_data
from scripts import make_shot_chart as shot_chart


PLAYER_ID = 1641824
PLAYER_NAME = "Matas Buzelis"
SEASONS = ("2024-25", "2025-26")
SEASON_MIN_ZONE_FGA = sm.MIN_ZONE12_FGA_PLAYER
TENURE_MIN_ZONE_FGA = SEASON_MIN_ZONE_FGA * len(SEASONS)
PROJECT = "matas-buzelis-bulls-zone-charts"
START_DATE = "2026-09-07"
SLUG = f"{START_DATE}-{PROJECT}"
LEADERBOARD_COLUMNS = (
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN",
    "FGM", "FGA", "FG_PCT", "PTS",
)


def fetch_bulls_totals(season: str) -> pd.Series:
    """Return Buzelis's official Chicago regular-season totals."""
    table = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=BULLS_TEAM_ID,
        per_mode_detailed="Totals",
        timeout=60,
        headers=fetch._NBA_HEADERS,
    ).get_data_frames()[0]
    missing = set(LEADERBOARD_COLUMNS) - set(table.columns)
    if missing:
        raise ValueError(f"{season} totals missing: " + ", ".join(sorted(missing)))
    player = table[table.PLAYER_ID.astype(int).eq(PLAYER_ID)]
    if len(player) != 1:
        raise ValueError(f"expected one {PLAYER_NAME} row for {season}, found {len(player)}")
    return player.loc[:, LEADERBOARD_COLUMNS].iloc[0]


def load_bulls_totals(season: str, data_dir: Path,
                      refresh: bool = False) -> pd.Series:
    path = data_dir / f"{season}-matas-buzelis-bulls-totals.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path).iloc[0]
    player = fetch_bulls_totals(season)
    out = player.to_frame().T
    out.insert(0, "season", season)
    out.to_csv(path, index=False)
    return out.iloc[0]


def load_bulls_shots(season: str, totals: pd.Series, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    path = data_dir / f"{season}-matas-buzelis-bulls-shots.csv"
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
    expected, actual = int(totals.FGA), len(shots)
    if actual != expected:
        raise ValueError(f"{season}: shot rows {actual} != Bulls FGA {expected}")


def league_zone_baseline(label: str, league: pd.DataFrame) -> pd.DataFrame:
    working = league.copy()
    working["zone"] = sm.zone12_of_shots(working)
    grouped = working.groupby("zone", as_index=False)["shot_made"].agg(
        fga="size", fgm="sum"
    )
    grouped.insert(0, "window", label)
    grouped["fg_pct"] = grouped.fgm / grouped.fga * 100
    grouped["fga_share_pct"] = grouped.fga / len(working) * 100
    return grouped


def summary_row(label: str, totals: pd.Series, shots: pd.DataFrame,
                zones: pd.DataFrame, min_zone_fga: int,
                included_seasons: str) -> dict[str, object]:
    overall = shot_chart._zone12_overall_metrics(shots)
    rated = zones[zones.rated]
    return {
        "window": label,
        "player_id": PLAYER_ID,
        "player": PLAYER_NAME,
        "included_seasons": included_seasons,
        "games": int(totals.GP),
        "minutes": round(float(totals.MIN), 1),
        "points": int(totals.PTS),
        "ppg": round(float(totals.PTS) / int(totals.GP), 1),
        "bulls_fga": int(totals.FGA),
        "shot_rows": len(shots),
        "fgm": int(shots.shot_made.sum()),
        "fg_pct": round(shots.shot_made.mean() * 100, 1),
        "efg_pct": round(overall["efg_pct"], 1),
        "three_pct": round(overall["three_pct"], 1),
        "zones_rated": len(rated),
        "zones_grey": len(zones) - len(rated),
        "rated_fga_share_pct": round(rated.fga.sum() / len(shots) * 100, 1),
        "mapped_zone_fga": int(zones.fga.sum()),
        "excluded_backcourt_fga": int(zones.subject_excluded_fga.iloc[0]),
        "source_zone_value_conflicts": int(
            zones.subject_source_conflict_fga.iloc[0]
        ),
        "league_zone_value_conflicts": int(
            zones.league_source_conflict_fga.iloc[0]
        ),
        "min_zone_fga": min_zone_fga,
        "scope": "Chicago attempts only",
    }


def tenure_totals(season_totals: list[pd.Series]) -> pd.Series:
    """Add counting fields; each game belongs to exactly one Bulls season."""
    return pd.Series({
        "GP": sum(int(row.GP) for row in season_totals),
        "MIN": sum(float(row.MIN) for row in season_totals),
        "PTS": sum(int(row.PTS) for row in season_totals),
        "FGA": sum(int(row.FGA) for row in season_totals),
    })


def render(label: str, shots: pd.DataFrame, league: pd.DataFrame,
           min_zone_fga: int, output_dir: Path, final: bool,
           merge_mid: bool = False, ppg: float | None = None) -> Path:
    suffix = label.lower().replace("–", "-").replace(" ", "-")
    variant = "-merged-mid" if merge_mid else ""
    out = output_dir / (
        f"{date.today().isoformat()}-zone-matas-buzelis-{suffix}{variant}.png"
    )
    shot_chart.render_zones(
        {
            "player": shots,
            "league": league,
            "name": PLAYER_NAME,
            "season": label,
            "min_fga": min_zone_fga,
            "pill": "large",
            "summary_metrics": True,
            "summary_ppg": ppg,
            "merge_mid": merge_mid,
        },
        out,
        final,
    )
    return out


def print_canva_copy(summary: pd.DataFrame, merge_mid: bool = False) -> None:
    # The cover states the zone count, so it has to follow the variant actually
    # rendered rather than the family's usual twelve.
    zone_count = "eight" if merge_mid else "twelve"
    print("\nCANVA COPY / 4-SLIDE CAROUSEL")
    print("PAGE 1 / COVER")
    print("Title: Matas Buzelis, season by season")
    print(f"Subtitle: Two Bulls seasons in the same {zone_count} court zones")
    for page, row in enumerate(summary.itertuples(index=False), start=2):
        tenure = row.window == "Bulls tenure"
        print(f"\nPAGE {page} / {row.window}")
        print(f"Title: {'Two-year Bulls tenure' if tenure else row.window}")
        print(f"Subtitle: {row.ppg:.1f} PPG · {row.bulls_fga:,} Bulls FGA · "
              f"{row.games} games")
        print("Key: Colour = FG% vs the NBA in that zone")
        print("Reading it: vs LA = percentage-point gap to the matching league baseline")
        print(
            "Qualifier: Chicago attempts only · Grey zones are under "
            f"{row.min_zone_fga} FGA"
            + (" · The five mid-range regions are shown pooled as one zone"
               if merge_mid else "")
        )
        if row.excluded_backcourt_fga:
            print(
                "Coverage: "
                f"{row.excluded_backcourt_fga} backcourt FGA excluded from the half-court zones"
            )
        print("Source: NBA.com/stats")


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    summaries: list[dict[str, object]] = []
    zone_tables: list[pd.DataFrame] = []
    baseline_tables: list[pd.DataFrame] = []
    all_shots: list[pd.DataFrame] = []
    all_league: list[pd.DataFrame] = []
    all_totals: list[pd.Series] = []

    for season in SEASONS:
        print(f"\n{'=' * 72}\n{season}")
        totals = load_bulls_totals(season, args.data_dir, args.refresh)
        shots = load_bulls_shots(season, totals, args.data_dir, args.refresh)
        league = shot_data.league_shots(season, args.refresh_league)
        if league.empty:
            raise ValueError(f"NBA.com returned no league shots for {season}")
        zones = sm.zone12_split(shots, league, min_fga=SEASON_MIN_ZONE_FGA,
                                merge_mid=args.merge_mid)
        audit = zones.copy()
        audit.insert(0, "window", season)
        zone_tables.append(audit)
        baseline_tables.append(league_zone_baseline(season, league))
        summaries.append(summary_row(
            season, totals, shots, zones, SEASON_MIN_ZONE_FGA, season
        ))
        outputs.append(render(
            season, shots, league, SEASON_MIN_ZONE_FGA, args.output_dir,
            args.final, args.merge_mid, float(totals.PTS) / int(totals.GP)
        ))
        all_shots.append(shots.assign(source_season=season))
        all_league.append(league.assign(source_season=season))
        all_totals.append(totals)

    pooled_shots = pd.concat(all_shots, ignore_index=True)
    pooled_league = pd.concat(all_league, ignore_index=True)
    pooled_zones = sm.zone12_split(
        pooled_shots, pooled_league, min_fga=TENURE_MIN_ZONE_FGA,
        merge_mid=args.merge_mid
    )
    pooled_audit = pooled_zones.copy()
    pooled_audit.insert(0, "window", "Bulls tenure")
    zone_tables.append(pooled_audit)
    baseline_tables.append(league_zone_baseline("Bulls tenure", pooled_league))
    totals = tenure_totals(all_totals)
    summaries.append(summary_row(
        "Bulls tenure", totals, pooled_shots, pooled_zones,
        TENURE_MIN_ZONE_FGA, ", ".join(SEASONS)
    ))
    outputs.append(render(
        "Bulls tenure", pooled_shots, pooled_league, TENURE_MIN_ZONE_FGA,
        args.output_dir, args.final, args.merge_mid,
        float(totals.PTS) / int(totals.GP)
    ))

    stem = "merged-mid-" if args.merge_mid else ""
    summary = pd.DataFrame(summaries)
    summary.to_csv(args.data_dir / f"{stem}zone-chart-summary.csv", index=False)
    pd.concat(zone_tables, ignore_index=True).to_csv(
        args.data_dir / f"{stem}zone-splits.csv", index=False, float_format="%.4f"
    )
    pd.concat(baseline_tables, ignore_index=True).to_csv(
        args.data_dir / "league-zone-baselines.csv", index=False,
        float_format="%.4f"
    )
    print("\nBUZELIS BULLS ZONE SUMMARY")
    print(summary.to_string(index=False))
    print_canva_copy(summary, args.merge_mid)
    print(f"\nData: {args.data_dir}")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Matas Buzelis Bulls-tenure twelve-zone charts"
    )
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-league", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--merge-mid", action="store_true",
                        help="pool the five mid-range regions into one zone")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "output" / PROJECT)
    parser.add_argument("--data-dir", type=Path,
                        default=ROOT / "docs" / "visuals" / SLUG / "data")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
