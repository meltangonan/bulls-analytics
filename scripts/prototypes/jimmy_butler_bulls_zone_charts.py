#!/usr/bin/env python3
"""Build Jimmy Butler's qualifying Bulls season charts and full-tenure chart."""
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
from bulls.config import BULLS_TEAM_ID
from bulls.data import fetch
from bulls.data import shots as shot_data
from scripts import make_shot_chart as shot_chart


PLAYER_ID = 202710
PLAYER_NAME = "Jimmy Butler"
ALL_BULLS_SEASONS = (
    "2011-12", "2012-13", "2013-14", "2014-15", "2015-16", "2016-17",
)
MIN_SEASON_FGA = 300
SEASON_MIN_ZONE_FGA = sm.MIN_ZONE12_FGA_PLAYER
TENURE_MIN_ZONE_FGA = SEASON_MIN_ZONE_FGA * len(ALL_BULLS_SEASONS)
PROJECT = "jimmy-butler-bulls-zone-charts"
START_DATE = "2026-08-26"
SLUG = f"{START_DATE}-{PROJECT}"
TOTAL_COLUMNS = (
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN",
    "PTS", "FGM", "FGA", "FG_PCT",
)


def fetch_bulls_totals(season: str) -> pd.Series:
    """Fetch the independent Chicago totals used to reconcile this post's shots."""
    return fetch.get_player_season_totals(
        PLAYER_ID, season, team_id=BULLS_TEAM_ID,
        columns=TOTAL_COLUMNS, player_name=PLAYER_NAME,
    )


def load_bulls_totals(season: str, data_dir: Path,
                      refresh: bool = False) -> pd.Series:
    path = data_dir / f"{season}-jimmy-butler-bulls-totals.csv"
    if path.exists() and not refresh:
        row = pd.read_csv(path).iloc[0]
        if "PTS" not in row.index:
            row = fetch_bulls_totals(season)
            out = row.to_frame().T
            out.insert(0, "season", season)
            out.to_csv(path, index=False)
            row = out.iloc[0]
    else:
        row = fetch_bulls_totals(season)
        out = row.to_frame().T
        out.insert(0, "season", season)
        out.to_csv(path, index=False)
        row = out.iloc[0]
    if int(row.PLAYER_ID) != PLAYER_ID:
        raise ValueError(f"{season}: saved totals are not {PLAYER_NAME}")
    return row


def reconcile_shots(season: str, totals: pd.Series,
                    shots: pd.DataFrame) -> None:
    if len(shots) != int(totals.FGA):
        raise ValueError(
            f"{season}: shot rows {len(shots)} != Bulls FGA {int(totals.FGA)}"
        )
    makes = int(shots.shot_made.sum())
    if makes != int(totals.FGM):
        raise ValueError(
            f"{season}: shot makes {makes} != Bulls FGM {int(totals.FGM)}"
        )


def load_bulls_shots(season: str, totals: pd.Series, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    path = data_dir / f"{season}-jimmy-butler-bulls-shots.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch.get_player_shots(
            PLAYER_ID, team_id=BULLS_TEAM_ID, season=season
        )
        if shots.empty:
            raise ValueError(f"NBA.com returned no {PLAYER_NAME} shots for {season}")
        shots.to_csv(path, index=False)
    reconcile_shots(season, totals, shots)
    return shots


def load_league_shots(season: str, data_dir: Path,
                      refresh: bool = False) -> pd.DataFrame:
    path = data_dir / f"{season}-nba-shots.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    league = shot_data.league_shots(season, refresh)
    if league.empty:
        raise ValueError(f"NBA.com returned no league shots for {season}")
    league.to_csv(path, index=False)
    return league


def located_league_shots(season: str, league: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    required = ["loc_x", "loc_y", "shot_distance", "shot_zone", "shot_zone_area"]
    unlocated = league[required].isna().all(axis=1)
    partial = league[required].isna().any(axis=1) & ~unlocated
    if partial.any():
        raise ValueError(
            f"{season}: {int(partial.sum())} league rows have partially missing location data"
        )
    return league.loc[~unlocated].copy(), int(unlocated.sum())


def collapse_to_source_family(zones: pd.Series) -> pd.Series:
    return zones.replace({
        "Left Baseline": "Mid-Range",
        "Left Mid-Range": "Mid-Range",
        "Center Mid-Range": "Mid-Range",
        "Right Mid-Range": "Mid-Range",
        "Right Baseline": "Mid-Range",
        "Left Wing 3": "Above the Break 3",
        "Top of Key 3": "Above the Break 3",
        "Right Wing 3": "Above the Break 3",
    })


def assert_source_family_reconciliation(season: str,
                                        shots: pd.DataFrame) -> None:
    custom = pd.Series(sm.zone12_of_shots(shots), index=shots.index)
    actual = collapse_to_source_family(custom).value_counts().sort_index()
    expected = shots.shot_zone.value_counts().sort_index()
    if actual.to_dict() != expected.to_dict():
        raise ValueError(f"{season}: custom zones crossed an NBA broad-zone family")


def summary_row(label: str, totals: pd.Series, shots: pd.DataFrame,
                zones: pd.DataFrame, min_zone_fga: int,
                league_unlocated_fga: int, rendered: bool) -> dict[str, object]:
    overall = shot_chart._zone12_overall_metrics(shots)
    rated = zones[zones.rated]
    return {
        "window": label,
        "rendered_detail_page": rendered,
        "games": int(totals.GP),
        "minutes": round(float(totals.MIN), 1),
        "points": int(totals.PTS),
        "ppg": round(float(totals.PTS) / int(totals.GP), 1),
        "bulls_fga": int(totals.FGA),
        "shot_rows": len(shots),
        "fgm": int(shots.shot_made.sum()),
        "efg_pct": round(overall["efg_pct"], 1),
        "three_pct": round(overall["three_pct"], 1),
        "zones_rated": len(rated),
        "zones_grey": len(zones) - len(rated),
        "rated_fga_share_pct": round(rated.fga.sum() / len(shots) * 100, 1),
        "mapped_zone_fga": int(zones.fga.sum()),
        "excluded_backcourt_fga": int(zones.subject_excluded_fga.iloc[0]),
        "source_zone_value_conflicts": int(zones.subject_source_conflict_fga.iloc[0]),
        "league_zone_value_conflicts": int(zones.league_source_conflict_fga.iloc[0]),
        "league_unlocated_fga": league_unlocated_fga,
        "min_zone_fga": min_zone_fga,
        "scope": "Chicago attempts only",
    }


def pooled_totals(rows: list[pd.Series]) -> pd.Series:
    return pd.Series({
        "GP": sum(int(row.GP) for row in rows),
        "MIN": sum(float(row.MIN) for row in rows),
        "PTS": sum(int(row.PTS) for row in rows),
        "FGA": sum(int(row.FGA) for row in rows),
    })


def render(label: str, shots: pd.DataFrame, league: pd.DataFrame,
           min_zone_fga: int, ppg: float, output_dir: Path, final: bool) -> Path:
    suffix = label.lower().replace("–", "-").replace(" ", "-")
    out = output_dir / f"{date.today().isoformat()}-zone-jimmy-butler-{suffix}.png"
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
        },
        out,
        final,
    )
    return out


def render_tenure_cover(shots: pd.DataFrame, league: pd.DataFrame,
                        output_dir: Path, final: bool) -> Path:
    out = output_dir / f"{date.today().isoformat()}-zone-jimmy-butler-bulls-tenure-cover.png"
    shot_chart.render_zones(
        {
            "player": shots,
            "league": league,
            "name": PLAYER_NAME,
            "season": "Bulls tenure",
            "min_fga": TENURE_MIN_ZONE_FGA,
            "show_details": False,
            "summary_metrics": False,
            "court_ink": "#242424",
        },
        out,
        final,
    )
    return out


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    season_outputs, summaries, splits = [], [], []
    all_shots, all_league, all_totals = [], [], []

    for season in ALL_BULLS_SEASONS:
        print(f"\n{'=' * 72}\n{season}")
        totals = load_bulls_totals(season, args.data_dir, args.refresh)
        shots = load_bulls_shots(season, totals, args.data_dir, args.refresh)
        raw_league = load_league_shots(season, args.data_dir, args.refresh_league)
        league, league_unlocated = located_league_shots(season, raw_league)
        assert_source_family_reconciliation(season, shots)
        zones = sm.zone12_split(shots, league, min_fga=SEASON_MIN_ZONE_FGA)
        rendered = int(totals.FGA) >= MIN_SEASON_FGA
        audit = zones.copy()
        audit.insert(0, "window", season)
        splits.append(audit)
        summaries.append(summary_row(
            season, totals, shots, zones, SEASON_MIN_ZONE_FGA,
            league_unlocated, rendered,
        ))
        if rendered:
            season_outputs.append(render(
                season, shots, league, SEASON_MIN_ZONE_FGA,
                float(totals.PTS) / int(totals.GP),
                args.output_dir, args.final,
            ))
        all_shots.append(shots.assign(source_season=season))
        all_league.append(league.assign(source_season=season))
        all_totals.append(totals)

    tenure_shots = pd.concat(all_shots, ignore_index=True)
    tenure_league = pd.concat(all_league, ignore_index=True)
    tenure_zones = sm.zone12_split(
        tenure_shots, tenure_league, min_fga=TENURE_MIN_ZONE_FGA
    )
    audit = tenure_zones.copy()
    audit.insert(0, "window", "Bulls tenure")
    splits.append(audit)
    totals = pooled_totals(all_totals)
    summaries.append(summary_row(
        "Bulls tenure", totals, tenure_shots, tenure_zones,
        TENURE_MIN_ZONE_FGA,
        sum(int(row["league_unlocated_fga"]) for row in summaries), True,
    ))
    tenure_output = render(
        "Bulls tenure", tenure_shots, tenure_league, TENURE_MIN_ZONE_FGA,
        float(totals.PTS) / int(totals.GP),
        args.output_dir, args.final,
    )
    cover = render_tenure_cover(
        tenure_shots, tenure_league, args.output_dir, args.final
    )

    summary = pd.DataFrame(summaries)
    summary.to_csv(args.data_dir / "zone-chart-summary.csv", index=False)
    pd.concat(splits, ignore_index=True).to_csv(
        args.data_dir / "zone-splits.csv", index=False, float_format="%.4f"
    )
    print("\nJIMMY BUTLER BULLS ZONE SUMMARY")
    print(summary.to_string(index=False))
    qualifying = summary[
        summary.rendered_detail_page & summary.window.ne("Bulls tenure")
    ]
    print("\nCANVA COPY")
    print("Title: Jimmy Butler as a Bull, season by season")
    print(f"Coverage: {len(ALL_BULLS_SEASONS)} regular seasons · all Bulls FGA in tenure total")
    print(f"Season pages: {', '.join(qualifying.window)} (minimum {MIN_SEASON_FGA} FGA)")
    print("Season qualifier: Grey zones are under 20 FGA")
    print(f"Tenure qualifier: Grey zones are under {TENURE_MIN_ZONE_FGA} FGA "
          f"(20 × {len(ALL_BULLS_SEASONS)} seasons)")
    print("Source: NBA.com/stats · Chicago attempts only")
    return [cover, *season_outputs, tenure_output]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-league", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "output" / PROJECT
    )
    parser.add_argument(
        "--data-dir", type=Path,
        default=ROOT / "docs" / "visuals" / SLUG / "data",
    )
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
