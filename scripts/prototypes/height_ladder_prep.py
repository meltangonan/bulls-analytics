"""Pick the ladder winner at each listed Bulls height, two ways.

STRICT   - a season must clear 41 GP and 20 MPG. Heights where no Bull ever
           did that are simply absent from the ladder.
FALLBACK - the same floor, but a height emptied by it falls back to the best
           season any Bull that height ever played. The fallback can only fire
           where no qualifying season exists, so a fallback row is itself the
           finding: nobody that tall or that short ever held a rotation spot.
"""
from pathlib import Path

import pandas as pd

DATA = Path("docs/visuals/2026-08-20-most-ppg-at-each-height/data")
MIN_GP = 41
MIN_MPG = 20.0


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA / "bulls_player_seasons.csv")
    return df[df["GP"] > 0].copy()


def best_per_height(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values("PPG", ascending=False)
        .drop_duplicates("HEIGHT_IN")
        .sort_values("HEIGHT_IN")
    )


def build(df: pd.DataFrame, fallback: bool) -> pd.DataFrame:
    qualified = df[(df["GP"] >= MIN_GP) & (df["MPG"] >= MIN_MPG)]
    ladder = best_per_height(qualified)
    ladder["QUALIFIED"] = True

    if fallback:
        missing = sorted(set(df["HEIGHT_IN"]) - set(ladder["HEIGHT_IN"]))
        extra = best_per_height(df[df["HEIGHT_IN"].isin(missing)])
        extra["QUALIFIED"] = False
        ladder = pd.concat([ladder, extra]).sort_values("HEIGHT_IN")

    return ladder.reset_index(drop=True)


def main() -> None:
    df = load()
    for name, fb in (("strict", False), ("fallback", True)):
        ladder = build(df, fallback=fb)
        out = DATA / f"ladder_{name}.csv"
        ladder.to_csv(out, index=False)
        print(f"\n{name.upper()} — {len(ladder)} rungs -> {out.name}")
        for row in ladder.itertuples():
            mark = "" if row.QUALIFIED else "   <- fallback"
            print(
                f"  {row.HEIGHT:>4}  {row.PLAYER_NAME:<22} {row.PPG:5.1f}  "
                f"{row.SEASON_ID}  {int(row.GP):>2}g {row.MPG:>4.1f}m{mark}"
            )


if __name__ == "__main__":
    main()
