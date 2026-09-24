"""Eligibility checks for the last distance-band slide."""

import pandas as pd

from scripts.prototypes.distance_band_fgm import HALFCOURT_Y, build_30_to_halfcourt


def test_30_plus_slide_stops_at_the_straight_halfcourt_line():
    assert HALFCOURT_Y == 417.5
    shots = pd.DataFrame([
        # Two equal-FGM seasons: higher PPS wins after the midcourt exclusion.
        (1, "Player A", "2024-25", 30, 1, "3PT Field Goal", 0, 417),
        (1, "Player A", "2024-25", 31, 0, "3PT Field Goal", 0, 300),
        (2, "Player B", "2024-25", 30, 1, "3PT Field Goal", 0, 416),
        (2, "Player B", "2024-25", 31, 1, "3PT Field Goal", 0, 418),
        (2, "Player B", "2024-25", 29, 1, "3PT Field Goal", 0, 400),
    ], columns=[
        "PLAYER_ID", "PLAYER_NAME", "season", "SHOT_DISTANCE", "SHOT_MADE_FLAG",
        "SHOT_TYPE", "LOC_X", "LOC_Y",
    ])

    grouped, winner, audit = build_30_to_halfcourt(shots)

    assert len(grouped) == 2
    assert winner.iloc[0].PLAYER_NAME == "Player B"
    assert winner.iloc[0].FGM == 1
    assert winner.iloc[0].FGA == 1
    assert winner.iloc[0].PPS == 3.0
    assert audit.iloc[0].inside_halfcourt_fga == 3
    assert audit.iloc[0].beyond_halfcourt_fga == 1
