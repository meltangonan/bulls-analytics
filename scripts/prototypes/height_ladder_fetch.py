"""Fetch every Bulls player-season since the 1976-77 merger, with listed height.

Two passes, both against the NBA Stats API:

1. `commonteamroster` for each season 1976-77..2025-26 gives the Bulls roster for
   that year, including each player's listed HEIGHT. Height is stored per player,
   not per season, so a player who appears in several rosters carries one height.
2. `playercareerstats` for each distinct player gives their per-season regular
   season line. We keep only rows whose TEAM_ID is the Bulls, which drops the
   rest of a journeyman's career and correctly splits a mid-season trade.

Output is a single tidy CSV: one row per Bulls player-season.

Pass `--rebuild` to regenerate the tidy CSV from the saved raw responses without
refetching anything.
"""
import sys
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import commonteamroster, playercareerstats

from bulls.config import BULLS_TEAM_ID

FIRST_SEASON = 1976  # first post-merger season, 1976-77
LAST_SEASON = 2025   # 2025-26
DELAY = 0.6
OUT = Path("docs/visuals/2026-08-20-most-ppg-at-each-height/data")


def season_str(start_year: int) -> str:
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def height_to_inches(height: str) -> float:
    """'6-6' -> 78.0. Blank or malformed -> NaN."""
    if not isinstance(height, str) or "-" not in height:
        return float("nan")
    feet, _, inches = height.partition("-")
    try:
        return int(feet) * 12 + int(inches)
    except ValueError:
        return float("nan")


def fetch_rosters() -> pd.DataFrame:
    frames = []
    for year in range(FIRST_SEASON, LAST_SEASON + 1):
        season = season_str(year)
        try:
            df = commonteamroster.CommonTeamRoster(
                team_id=BULLS_TEAM_ID, season=season
            ).get_data_frames()[0]
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  roster {season}: FAILED {exc}", file=sys.stderr)
            time.sleep(DELAY * 3)
            continue
        df["SEASON"] = season
        frames.append(df)
        print(f"  roster {season}: {len(df)} players")
        time.sleep(DELAY)
    return pd.concat(frames, ignore_index=True)


def fetch_careers(player_ids: list[int]) -> pd.DataFrame:
    frames = []
    for i, pid in enumerate(player_ids, 1):
        try:
            df = playercareerstats.PlayerCareerStats(
                player_id=pid, per_mode36="Totals"
            ).get_data_frames()[0]
        except Exception as exc:  # noqa: BLE001
            print(f"  career {pid}: FAILED {exc}", file=sys.stderr)
            time.sleep(DELAY * 3)
            continue
        frames.append(df)
        if i % 25 == 0:
            print(f"  careers: {i}/{len(player_ids)}")
        time.sleep(DELAY)
    return pd.concat(frames, ignore_index=True)


def player_heights(rosters: pd.DataFrame) -> pd.DataFrame:
    """One height per player: the endpoint stores a current value, not a yearly one."""
    heights = (
        rosters[["PLAYER_ID", "PLAYER", "HEIGHT", "POSITION"]]
        .drop_duplicates(subset="PLAYER_ID", keep="last")
        .rename(columns={"PLAYER": "PLAYER_NAME"})
    )
    heights["HEIGHT_IN"] = heights["HEIGHT"].map(height_to_inches)
    return heights


def tidy_from_raw(rosters: pd.DataFrame, careers: pd.DataFrame) -> pd.DataFrame:
    """Join rosters to careers and keep the Bulls rows. Pure; no network."""
    heights = player_heights(rosters)

    bulls = careers[careers["TEAM_ID"] == BULLS_TEAM_ID].copy()
    bulls = bulls[bulls["SEASON_ID"] >= season_str(FIRST_SEASON)]

    tidy = bulls.merge(heights, on="PLAYER_ID", how="left")

    # ⚠️ Do not round here. The renderer prints one decimal, and rounding to two
    # first rounds twice: 26.9538 -> 26.95 -> "26.9" when the correct single
    # rounding is 27.0. Three of twenty published MPG figures were wrong by 0.1
    # this way before it was caught. Store full precision; round once, at display.
    tidy["PPG"] = tidy["PTS"] / tidy["GP"]
    tidy["MPG"] = tidy["MIN"] / tidy["GP"]

    return tidy[[
        "PLAYER_ID", "PLAYER_NAME", "HEIGHT", "HEIGHT_IN", "POSITION",
        "SEASON_ID", "GP", "MIN", "MPG", "PTS", "PPG",
    ]].sort_values(["HEIGHT_IN", "PPG"], ascending=[True, False])


def rebuild() -> None:
    """Regenerate the tidy CSV from saved raw responses, without refetching."""
    rosters = pd.read_csv(OUT / "raw_rosters.csv")
    careers = pd.read_csv(OUT / "raw_careers.csv")
    tidy = tidy_from_raw(rosters, careers)
    tidy.to_csv(OUT / "bulls_player_seasons.csv", index=False)
    print(f"Rebuilt {len(tidy)} Bulls player-seasons from saved raw responses")


def main() -> None:
    if "--rebuild" in sys.argv:
        rebuild()
        return

    OUT.mkdir(parents=True, exist_ok=True)

    print("Pass 1: season rosters")
    rosters = fetch_rosters()
    rosters.to_csv(OUT / "raw_rosters.csv", index=False)

    heights = player_heights(rosters)
    print(f"\nPass 2: careers for {len(heights)} distinct players")
    careers = fetch_careers(heights["PLAYER_ID"].tolist())
    careers.to_csv(OUT / "raw_careers.csv", index=False)

    tidy = tidy_from_raw(rosters, careers)
    tidy.to_csv(OUT / "bulls_player_seasons.csv", index=False)
    print(f"\nWrote {len(tidy)} Bulls player-seasons to {OUT}")


if __name__ == "__main__":
    main()
