"""Find the Bulls player-season with the most made field goals in each of the twelve zones.

Bulls shot rows are the reconciled 1997-98 to 2025-26 ShotChartDetail snapshot saved
with the distance-band post. Each leader's zone tag compares that player-season with
every located NBA attempt from the same season, as on the regular zone charts.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.analysis import shot_maps as sm
from bulls.data import shots as shot_data


SLUG = "2026-10-07-zone-fgm-leaders"
DATA = ROOT / "docs/visuals" / SLUG / "data"
BULLS_SOURCE = ROOT / "docs/visuals/2026-09-23-distance-band-fgm/data"
SEASONS = [f"{year}-{(year + 1) % 100:02d}" for year in range(1997, 2026)]
TEAM_ID = 1610612741
SHOT_TYPES = {"2PT Field Goal": "2PT", "3PT Field Goal": "3PT"}


def load_bulls() -> pd.DataFrame:
    frames = []
    for season in SEASONS:
        raw = pd.read_csv(BULLS_SOURCE / "shotchartdetail" / f"{season}.csv.gz")
        if not raw.TEAM_ID.eq(TEAM_ID).all():
            raise ValueError(f"{season}: non-Bulls shots found")
        if not raw.SHOT_MADE_FLAG.isin([0, 1]).all():
            raise ValueError(f"{season}: invalid make flags")
        frames.append(pd.DataFrame({
            "season": season,
            "player_id": raw.PLAYER_ID,
            "player_name": raw.PLAYER_NAME,
            "loc_x": raw.LOC_X,
            "loc_y": raw.LOC_Y,
            "shot_distance": raw.SHOT_DISTANCE,
            "shot_made": raw.SHOT_MADE_FLAG.eq(1),
            "shot_type": raw.SHOT_TYPE.map(SHOT_TYPES),
            "shot_zone": raw.SHOT_ZONE_BASIC,
            "shot_zone_area": raw.SHOT_ZONE_AREA,
        }))
    shots = pd.concat(frames, ignore_index=True)
    if shots.shot_type.isna().any():
        raise ValueError("unknown SHOT_TYPE value")
    return shots


def reconcile_bulls(shots: pd.DataFrame) -> pd.DataFrame:
    """Every season's shot rows must equal official Chicago FGA, FGM, 3PA and 3PM."""
    official = pd.read_csv(BULLS_SOURCE / "official-team-totals.csv")
    three = shots.shot_type.eq("3PT")
    observed = shots.assign(three=three, three_made=three & shots.shot_made).groupby(
        "season", as_index=False).agg(
        FGA=("shot_made", "size"), FGM=("shot_made", "sum"),
        FG3A=("three", "sum"), FG3M=("three_made", "sum"))
    out = observed.merge(official, on="season", suffixes=("_shots", "_official"))
    if len(out) != len(SEASONS):
        raise ValueError("official comparison is missing a season")
    for stat in ("FGA", "FGM", "FG3A", "FG3M"):
        bad = out.loc[out[f"{stat}_shots"].ne(out[f"{stat}_official"]), "season"]
        if len(bad):
            raise ValueError(f"{stat} differs from official totals: {bad.tolist()}")
    return out


def classify(shots: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign twelve zones; count rows that cannot enter one, by season."""
    unlocated = shots[["loc_x", "loc_y", "shot_zone"]].isna().any(axis=1)
    located = shots.loc[~unlocated].copy()
    located["zone"] = sm.zone12_of_shots(located)
    backcourt = located.zone.eq("Backcourt")
    exclusions = shots.assign(
        unlocated=unlocated, unlocated_made=unlocated & shots.shot_made,
    ).groupby("season", as_index=False).agg(
        unlocated_fga=("unlocated", "sum"), unlocated_fgm=("unlocated_made", "sum"))
    bc = located.assign(bc=backcourt, bc_made=backcourt & located.shot_made).groupby(
        "season", as_index=False).agg(backcourt_fga=("bc", "sum"),
                                      backcourt_fgm=("bc_made", "sum"))
    exclusions = exclusions.merge(bc, on="season", how="left")
    zoned = located.loc[~backcourt].copy()
    if not zoned.zone.isin(sm.ZONE12_ORDER).all():
        raise ValueError("a located half-court shot has no twelve-zone label")
    assert_family_and_side(zoned)
    return zoned, exclusions


def assert_family_and_side(zoned: pd.DataFrame) -> None:
    """Custom subdivisions stay inside NBA's broad family and on NBA's side label."""
    family = zoned.zone.replace({
        **{z: "Mid-Range" for z in sm.MID_ZONES},
        "Left Wing 3": "Above the Break 3", "Top of Key 3": "Above the Break 3",
        "Right Wing 3": "Above the Break 3",
    })
    if not family.eq(zoned.shot_zone).all():
        raise ValueError("custom zones crossed an NBA broad-zone family")
    for side, area in (("Left", "Left Side"), ("Right", "Right Side")):
        rows = zoned.loc[zoned.zone.isin([f"{side} Baseline", f"{side} Corner 3"])]
        if not rows.shot_zone_area.str.startswith(area).all():
            raise ValueError(f"{side} baseline/corner shots disagree with NBA's side label")


def rank(zoned: pd.DataFrame, tenure: bool = False
         ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Most FGM wins; a tie goes to the higher FG% (fewer attempts for the same makes).

    ``tenure`` pools every Chicago season a player has in the window instead of
    ranking single player-seasons.
    """
    keys = ["zone", "player_id", "player_name"] + ([] if tenure else ["season"])
    table = zoned.groupby(keys, as_index=False).agg(
        FGM=("shot_made", "sum"), FGA=("shot_made", "size"),
        seasons=("season", "nunique"), first_season=("season", "min"),
        last_season=("season", "max"))
    if tenure:
        table["season"] = table.first_season + " to " + table.last_season
    table["FG_PCT"] = table.FGM / table.FGA
    table["zone_order"] = table.zone.map(sm.ZONE12_ORDER.index)
    table = table.sort_values(["zone_order", "FGM", "FGA", "season"],
                              ascending=[True, False, True, True])
    table["rank"] = table.groupby("zone").FGM.rank(method="min", ascending=False).astype(int)
    ties = table.loc[table["rank"].eq(1)]
    leaders = ties.drop_duplicates("zone").copy()
    if len(leaders) != 12:
        raise ValueError("a zone has no leader")
    return table, leaders, ties


def league_for(season: str, cache: Path) -> tuple[pd.DataFrame, dict]:
    """Saved post copy first; otherwise copy the local league cache into the post."""
    saved = DATA / "league-shots" / f"{season}.csv.gz"
    if not saved.exists():
        source = cache / f"league_{season}.csv"
        league = pd.read_csv(source)[shot_data.SHOT_COLUMNS]
        saved.parent.mkdir(parents=True, exist_ok=True)
        league.to_csv(saved, index=False, compression={"method": "gzip", "mtime": 0})
    league = pd.read_csv(saved)
    required = ["loc_x", "loc_y", "shot_distance", "shot_zone", "shot_zone_area"]
    unlocated = league[required].isna().all(axis=1)
    if (league[required].isna().any(axis=1) & ~unlocated).any():
        raise ValueError(f"{season}: league rows with partial location data")
    manifest = {
        "season": season, "file": f"league-shots/{season}.csv.gz",
        "rows": len(league), "unlocated_rows": int(unlocated.sum()),
        "sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
    }
    return league.loc[~unlocated].copy(), manifest


def official_league_totals(seasons: list[str]) -> pd.DataFrame:
    """Official league FGA/FGM per season, summed over LeagueDashTeamStats team rows.

    Saved with the post; only seasons missing from the saved file are fetched.
    """
    path = DATA / "league-official-totals.csv"
    saved = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["season"])
    rows = []
    for season in sorted(set(seasons) - set(saved.season)):
        from nba_api.stats.endpoints import leaguedashteamstats
        from bulls.data import fetch
        teams = leaguedashteamstats.LeagueDashTeamStats(
            season=season, season_type_all_star="Regular Season",
            per_mode_detailed="Totals", timeout=60, headers=fetch._NBA_HEADERS,
        ).get_data_frames()[0]
        rows.append({
            "season": season, "teams": len(teams),
            "FGA": int(teams.FGA.sum()), "FGM": int(teams.FGM.sum()),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    if rows:
        saved = pd.concat([saved, pd.DataFrame(rows)], ignore_index=True).sort_values("season")
    saved = saved.astype({"teams": int, "FGA": int, "FGM": int})
    saved.to_csv(path, index=False)
    return saved


def reconcile_league(manifest: pd.DataFrame) -> pd.DataFrame:
    """Every saved league season's shot rows equal official league FGA and FGM."""
    official = official_league_totals(manifest.season.tolist())
    out = []
    for season in manifest.season:
        league = pd.read_csv(DATA / "league-shots" / f"{season}.csv.gz")
        out.append({"season": season, "shot_rows": len(league),
                    "shot_makes": int(league.shot_made.sum())})
    out = pd.DataFrame(out).merge(official, on="season", how="left")
    bad = out.loc[out.shot_rows.ne(out.FGA) | out.shot_makes.ne(out.FGM), "season"]
    if len(bad):
        raise ValueError(f"league shot rows differ from official totals: {bad.tolist()}")
    return out


def leader_tags(leaders: pd.DataFrame, located: pd.DataFrame, cache: Path,
                tenure: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tags, splits, manifest = [], [], []
    leagues: dict[str, pd.DataFrame] = {}
    for row in leaders.itertuples():
        mine = located.loc[located.player_id.eq(row.player_id)]
        seasons = sorted(mine.season.unique()) if tenure else [row.season]
        for season in seasons:
            if season not in leagues:
                leagues[season], info = league_for(season, cache)
                manifest.append(info)
        # Share of FGA uses every Chicago attempt in the window, backcourt included,
        # matching the denominator on the regular zone charts. A tenure pools the
        # league from the same seasons, attempt-weighted, as on the tenure charts.
        subject = mine.loc[mine.season.isin(seasons)]
        league = pd.concat([leagues[season] for season in seasons], ignore_index=True)
        split = sm.zone12_split(subject, league, min_fga=sm.MIN_ZONE12_FGA_PLAYER)
        split.insert(0, "leader_zone", row.zone)
        split.insert(1, "player_name", row.player_name)
        split.insert(2, "season", row.season)
        splits.append(split)
        z = split.set_index("zone").loc[row.zone]
        if int(z.fgm) != row.FGM or int(z.fga) != row.FGA:
            raise ValueError(f"{row.zone}: split disagrees with ranking table")
        tags.append({
            "zone": row.zone, "player_id": row.player_id,
            "player_name": row.player_name, "season": row.season,
            "FGM": row.FGM, "FGA": row.FGA, "FG_PCT": z.fg * 100,
            "league_FG_PCT": z.lg_fg * 100, "FG_PCT_vs_NBA": z.fg_rel,
            "share_of_FGA": z.fga_share_pct, "league_share_of_FGA": z.lg_fga_share_pct,
            "share_vs_NBA": z.fga_share_pct - z.lg_fga_share_pct,
            "player_window_FGA": len(subject), "seasons": len(seasons),
        })
    return pd.DataFrame(tags), pd.concat(splits, ignore_index=True), pd.DataFrame(manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-cache", type=Path, default=shot_data.CACHE,
                        help="folder of league_<season>.csv files, used only when "
                             "the post has no saved copy")
    parser.add_argument("--scope", choices=("season", "tenure"), default="season",
                        help="rank single player-seasons or pooled Bulls tenures")
    args = parser.parse_args()
    tenure = args.scope == "tenure"
    prefix = "tenure-" if tenure else ""
    DATA.mkdir(parents=True, exist_ok=True)

    shots = load_bulls()
    reconciliation = reconcile_bulls(shots)
    zoned, exclusions = classify(shots)
    table, leaders, ties = rank(zoned, tenure)
    located = shots.loc[shots[["loc_x", "loc_y", "shot_zone"]].notna().all(axis=1)]
    tags, splits, manifest = leader_tags(leaders, located, args.league_cache, tenure)
    manifest["copied_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    reconciliation.to_csv(DATA / "bulls-source-reconciliation.csv", index=False)
    exclusions.to_csv(DATA / "zone-exclusions.csv", index=False)
    table.drop(columns="zone_order").to_csv(
        DATA / f"{prefix}all-player-{args.scope}s.csv", index=False, float_format="%.4f")
    table.loc[table["rank"].le(5)].drop(columns="zone_order").to_csv(
        DATA / f"{prefix}zone-top5.csv", index=False, float_format="%.4f")
    ties.drop(columns="zone_order").to_csv(DATA / f"{prefix}zone-fgm-ties.csv", index=False)
    splits.to_csv(DATA / f"{prefix}leader-zone-splits.csv", index=False, float_format="%.4f")
    tags.to_csv(DATA / f"{prefix}carousel-values.csv", index=False, float_format="%.4f")
    manifest_path = DATA / "league-source-manifest.csv"
    if manifest_path.exists():
        # Keep the original copy time for files already saved with the post.
        old = pd.read_csv(manifest_path)
        manifest = pd.concat([old, manifest.loc[~manifest.season.isin(old.season)]])
    manifest = manifest.sort_values("season")
    manifest.to_csv(manifest_path, index=False)
    league_check = reconcile_league(manifest)
    league_check.to_csv(DATA / "league-source-reconciliation.csv", index=False)

    print(f"Bulls rows reconcile in all {len(reconciliation)} seasons; "
          f"{int(exclusions.unlocated_fga.sum())} unlocated and "
          f"{int(exclusions.backcourt_fga.sum())} backcourt attempts excluded; "
          f"league rows reconcile in all {len(league_check)} saved seasons")
    if len(ties) > 12:
        print("TIES:\n" + ties.to_string(index=False))
    print(tags.drop(columns="player_id").to_string(
        index=False, float_format=lambda v: f"{v:.1f}"))
    print("\nRunner-up margins:")
    for zone, group in table.groupby("zone", sort=False):
        top = group.head(2)
        print(f"  {zone:<22} {top.iloc[0].player_name} {top.iloc[0].FGM} vs "
              f"{top.iloc[1].player_name} {top.iloc[1].season} {top.iloc[1].FGM}")


if __name__ == "__main__":
    main()
