"""Compare qualification thresholds for the most-PPG-at-each-height ladder.

Every rung must be won by a real NBA season or the graphic looks broken. This
script shows what each candidate threshold does to the winner at each listed
height, so the cutoff is chosen against the actual roster rather than a guess.
"""
from pathlib import Path

import pandas as pd

DATA = Path("docs/visuals/2026-08-20-most-ppg-at-each-height/data")

# (label, min games played, min minutes per game)
THRESHOLDS = [
    ("none", 0, 0.0),
    ("20 GP", 20, 0.0),
    ("41 GP", 41, 0.0),
    ("41 GP + 15 MPG", 41, 15.0),
    ("41 GP + 20 MPG", 41, 20.0),
    ("58 GP + 20 MPG", 58, 20.0),
]


def winners(df: pd.DataFrame, min_gp: int, min_mpg: float) -> pd.DataFrame:
    q = df[(df["GP"] >= min_gp) & (df["MPG"] >= min_mpg)]
    return (
        q.sort_values("PPG", ascending=False)
        .drop_duplicates("HEIGHT_IN")
        .sort_values("HEIGHT_IN")
        .set_index("HEIGHT_IN")
    )


def main() -> None:
    df = pd.read_csv(DATA / "bulls_player_seasons.csv")
    df = df[df["GP"] > 0]

    print(f"{len(df)} Bulls player-seasons, "
          f"{df['PLAYER_ID'].nunique()} players, "
          f"{df['HEIGHT_IN'].nunique()} distinct listed heights\n")

    table = {}
    for label, gp, mpg in THRESHOLDS:
        w = winners(df, gp, mpg)
        table[label] = w.apply(
            lambda r: f"{r.PLAYER_NAME} {r.PPG:.1f} ({r.SEASON_ID}, {int(r.GP)}g {r.MPG:.0f}m)",
            axis=1,
        )
        print(f"{label}: {len(w)} rungs filled")

    print()
    heights = df[["HEIGHT_IN", "HEIGHT"]].drop_duplicates().set_index("HEIGHT_IN")["HEIGHT"]
    out = pd.DataFrame(table)
    out.insert(0, "HEIGHT", heights)
    pd.set_option("display.width", 400, "display.max_colwidth", 46)
    print(out.to_string())

    # Depth per rung drives how fragile a rung is, independent of threshold.
    print("\nQualifying seasons per rung at 41 GP + 20 MPG:")
    q = df[(df["GP"] >= 41) & (df["MPG"] >= 20)]
    depth = q.groupby(["HEIGHT_IN", "HEIGHT"]).agg(
        seasons=("PPG", "size"), players=("PLAYER_ID", "nunique")
    )
    print(depth.to_string())


if __name__ == "__main__":
    main()
