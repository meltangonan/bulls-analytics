#!/usr/bin/env python3
"""Build Kirk Hinrich's Bulls season zone charts, tenure chart, and cover.

    venv/bin/python scripts/prototypes/hinrich_bulls_zone_charts.py --final

The fourth in the tenure family, after Rose, DeRozan and Butler, and deliberately
identical to them in method so the four can sit side by side: same twelve zones,
same reconciliation, same grey floor rule, same audit files. What is new is the
cover -- ``shot_chart.render_zonegrid`` puts every charted season on one page as
bare coloured courts, which is a question no single-season slide can ask.

**Eleven seasons are pulled; ten are drawn.** ``CHART_MIN_SEASON_FGA`` keeps a
season off the slides and off the cover grid unless he took 300 Chicago shots in
it. All eleven still reconcile, still pool into the tenure chart and still land
in the audit files -- the floor governs what is shown, not what is counted.

Two things about Hinrich's tenure that the earlier three did not have to handle:

**It is split by two seasons somewhere else.** He was a Bull from 2003-04 to
2009-10, spent 2010-11 in Washington and Atlanta and 2011-12 in Atlanta, and came
back from 2012-13 to 2015-16. The missing pair are not gaps in the data.

**His last season is split by a trade.** He played 35 games for Chicago in
2015-16 and 11 for Atlanta after being dealt in February. Every pull here is
scoped to ``team_id=BULLS_TEAM_ID``, which is what keeps those 11 games out --
and because a wrongly-scoped shot pull returns an empty frame rather than an
error, the reconciliation against his official Chicago totals is what makes the
narrow pull trustworthy rather than merely narrow.
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
from bulls.config import BULLS_TEAM_ID
from bulls.data import fetch
from bulls.data import shots as shot_data
from scripts import make_shot_chart as shot_chart


PLAYER_ID = 2550
PLAYER_NAME = "Kirk Hinrich"
SEASONS = (
    "2003-04", "2004-05", "2005-06", "2006-07", "2007-08", "2008-09", "2009-10",
    "2012-13", "2013-14", "2014-15", "2015-16",
)
AWAY_SEASONS = ("2010-11", "2011-12")
CHART_MIN_SEASON_FGA = 300
GRID_ROW_PLAN = (3, 3, 3, 1)
SEASON_MIN_ZONE_FGA = sm.MIN_ZONE12_FGA_PLAYER
# Twenty attempts per pooled season. The pool is all eleven Chicago seasons,
# including the thin 2015-16 half that gets no chart of its own, so the
# denominator stays at eleven.
TENURE_MIN_ZONE_FGA = SEASON_MIN_ZONE_FGA * len(SEASONS)
PROJECT = "hinrich-bulls-zone-charts"
START_DATE = "2026-09-03"
SLUG = f"{START_DATE}-{PROJECT}"
TENURE_LABEL = "Bulls tenure"
TOTAL_COLUMNS = (
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN",
    "PTS", "FGM", "FGA", "FG_PCT",
)
LOCATION_COLUMNS = ["loc_x", "loc_y", "shot_distance", "shot_zone",
                    "shot_zone_area"]


def fetch_bulls_totals(season: str) -> pd.Series:
    return fetch.get_player_season_totals(
        PLAYER_ID, season, team_id=BULLS_TEAM_ID,
        columns=TOTAL_COLUMNS, player_name=PLAYER_NAME,
    )


def load_bulls_totals(season: str, data_dir: Path,
                      refresh: bool = False) -> pd.Series:
    path = data_dir / f"{season}-kirk-hinrich-bulls-totals.csv"
    if path.exists() and not refresh:
        row = pd.read_csv(path).iloc[0]
        if set(TOTAL_COLUMNS).issubset(row.index):
            if int(row.PLAYER_ID) != PLAYER_ID:
                raise ValueError(f"{season}: saved totals are not {PLAYER_NAME}")
            return row
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


def located_shots(label: str, shots: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop only attempts with no location fields at all, and count them.

    Historical ShotChartDetail occasionally returns a valid make/miss and shot
    value with no x/y, distance, or NBA zone. Such a row belongs in scoring
    totals but cannot honestly contribute to a location chart. A row missing
    only SOME of those fields is a different thing -- a shape change in the feed
    rather than a known gap -- so it raises rather than being quietly dropped.

    Hinrich has two, both missed threes: one in 2008-09 and one in 2009-10.
    """
    unlocated = shots[LOCATION_COLUMNS].isna().all(axis=1)
    partial = shots[LOCATION_COLUMNS].isna().any(axis=1) & ~unlocated
    if partial.any():
        raise ValueError(
            f"{label}: {int(partial.sum())} rows have partially missing "
            "location data"
        )
    return shots.loc[~unlocated].copy(), int(unlocated.sum())


def load_bulls_shots(season: str, totals: pd.Series, data_dir: Path,
                     refresh: bool = False) -> pd.DataFrame:
    path = data_dir / f"{season}-kirk-hinrich-bulls-shots.csv"
    if path.exists() and not refresh:
        shots = pd.read_csv(path)
    else:
        shots = fetch.get_player_shots(
            PLAYER_ID, team_id=BULLS_TEAM_ID, season=season
        )
        if shots.empty:
            raise ValueError(
                f"NBA.com returned no {PLAYER_NAME} shots for {season}")
        shots.to_csv(path, index=False)
    reconcile_shots(season, totals, shots)
    return shots


def load_league_shots(season: str, refresh: bool = False) -> pd.DataFrame:
    league = shot_data.league_shots(season, refresh)
    if league.empty:
        raise ValueError(f"NBA.com returned no league shots for {season}")
    return league


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
        raise ValueError(
            f"{season}: custom zones crossed an NBA broad-zone family")


def summary_row(label: str, totals: pd.Series, shots: pd.DataFrame,
                zones: pd.DataFrame, min_zone_fga: int,
                unlocated_fga: int, league_unlocated_fga: int,
                charted: bool = True) -> dict[str, object]:
    overall = shot_chart._zone12_overall_metrics(shots)
    rated = zones[zones.rated]
    return {
        "window": label,
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
        "unlocated_fga": unlocated_fga,
        "source_zone_value_conflicts": int(
            zones.subject_source_conflict_fga.iloc[0]
        ),
        "league_zone_value_conflicts": int(
            zones.league_source_conflict_fga.iloc[0]
        ),
        "league_unlocated_fga": league_unlocated_fga,
        "min_zone_fga": min_zone_fga,
        "charted": charted,
        "scope": "Chicago attempts only",
    }


def pooled_totals(rows: list[pd.Series]) -> pd.Series:
    return pd.Series({
        "GP": sum(int(row.GP) for row in rows),
        "MIN": sum(float(row.MIN) for row in rows),
        "PTS": sum(int(row.PTS) for row in rows),
        "FGA": sum(int(row.FGA) for row in rows),
        "FGM": sum(int(row.FGM) for row in rows),
    })


def render(label: str, shots: pd.DataFrame, league: pd.DataFrame,
           min_zone_fga: int, output_dir: Path, final: bool,
           ppg: float) -> Path:
    suffix = label.lower().replace("–", "-").replace(" ", "-")
    out = output_dir / f"{date.today().isoformat()}-zone-kirk-hinrich-{suffix}.png"
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
                        min_zone_fga: int, output_dir: Path,
                        final: bool) -> Path:
    label = TENURE_LABEL
    suffix = label.lower().replace("\u2013", "-").replace(" ", "-")
    out = output_dir / f"{date.today().isoformat()}-zone-kirk-hinrich-{suffix}-cover.png"
    shot_chart.render_zones(
        {
            "player": shots,
            "league": league,
            "name": PLAYER_NAME,
            "season": label,
            "min_fga": min_zone_fga,
            "show_details": False,
            "summary_metrics": False,
        },
        out,
        final,
    )
    return out


def render_cover(by_season: dict[str, dict[str, pd.DataFrame]],
                 output_dir: Path, final: bool) -> Path:
    out = output_dir / f"{date.today().isoformat()}-zonegrid-kirk-hinrich-tenure.png"
    shot_chart.render_zonegrid(
        {
            "by_season": by_season,
            "min_fga": SEASON_MIN_ZONE_FGA,
            "row_plan": GRID_ROW_PLAN,
            "align": "left",
        },
        out,
        final,
    )
    return out


def build(args: argparse.Namespace) -> list[Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    outputs, summaries, splits = [], [], []
    all_shots, all_league, all_totals = [], [], []
    by_season: dict[str, dict[str, pd.DataFrame]] = {}

    for season in SEASONS:
        print(f"\n{'=' * 72}\n{season}")
        totals = load_bulls_totals(season, args.data_dir, args.refresh)
        raw_shots = load_bulls_shots(season, totals, args.data_dir, args.refresh)
        shots, unlocated = located_shots(season, raw_shots)
        raw_league = load_league_shots(season, args.refresh_league)
        league, league_unlocated = located_shots(f"{season} league", raw_league)
        assert_source_family_reconciliation(season, shots)
        zones = sm.zone12_split(shots, league, min_fga=SEASON_MIN_ZONE_FGA)
        audit = zones.copy()
        audit.insert(0, "window", season)
        splits.append(audit)
        charted = int(totals.FGA) >= CHART_MIN_SEASON_FGA
        summaries.append(summary_row(
            season, totals, shots, zones, SEASON_MIN_ZONE_FGA,
            unlocated, league_unlocated, charted,
        ))
        if charted:
            outputs.append(render(
                season, shots, league, SEASON_MIN_ZONE_FGA,
                args.output_dir, args.final,
                float(totals.PTS) / int(totals.GP),
            ))
            by_season[season] = {"subject": shots, "league": league}
        else:
            print(f"{season}: {int(totals.FGA)} Chicago FGA, under "
                  f"{CHART_MIN_SEASON_FGA} -- no chart, pooled into the tenure")
        all_shots.append(shots.assign(source_season=season))
        all_league.append(league.assign(source_season=season))
        all_totals.append(totals)

    tenure_shots = pd.concat(all_shots, ignore_index=True)
    tenure_league = pd.concat(all_league, ignore_index=True)
    tenure_zones = sm.zone12_split(
        tenure_shots, tenure_league, min_fga=TENURE_MIN_ZONE_FGA
    )
    audit = tenure_zones.copy()
    audit.insert(0, "window", TENURE_LABEL)
    splits.append(audit)
    totals = pooled_totals(all_totals)
    summaries.append(summary_row(
        TENURE_LABEL, totals, tenure_shots, tenure_zones, TENURE_MIN_ZONE_FGA,
        sum(int(row["unlocated_fga"]) for row in summaries),
        sum(int(row["league_unlocated_fga"]) for row in summaries),
    ))
    outputs.append(render(
        TENURE_LABEL, tenure_shots, tenure_league, TENURE_MIN_ZONE_FGA,
        args.output_dir, args.final,
        float(totals.PTS) / int(totals.GP),
    ))
    outputs.append(render_tenure_cover(tenure_shots, tenure_league,
                                       TENURE_MIN_ZONE_FGA, args.output_dir,
                                       args.final))
    outputs.append(render_cover(by_season, args.output_dir, args.final))

    summary = pd.DataFrame(summaries)
    summary.to_csv(args.data_dir / "zone-chart-summary.csv", index=False)
    pd.concat(splits, ignore_index=True).to_csv(
        args.data_dir / "zone-splits.csv", index=False, float_format="%.4f"
    )
    print("\nKIRK HINRICH BULLS ZONE SUMMARY")
    print(summary.to_string(index=False))
    print("\nCANVA COPY")
    charted = [row["window"] for row in summaries[:-1] if row["charted"]]
    print("Title: Kirk Hinrich as a Bull, season by season")
    print(f"Coverage: Eleven Chicago regular seasons · "
          f"{' and '.join(AWAY_SEASONS)} omitted (not a Bull)")
    print(f"Charted seasons: {len(charted)} of {len(SEASONS)} · "
          f"{CHART_MIN_SEASON_FGA}+ Chicago FGA "
          f"({', '.join(s for s in SEASONS if s not in charted)} omitted)")
    print("Season qualifier: Grey zones are under 20 FGA")
    print(f"Tenure qualifier: Grey zones are under {TENURE_MIN_ZONE_FGA} FGA "
          f"(20 × {len(SEASONS)} seasons)")
    print("2015-16 note: Chicago half only (118 FGA) — too thin for its own "
          "chart, still inside the pooled tenure")
    print("Source: NBA.com/stats · Chicago attempts only")
    return outputs


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
