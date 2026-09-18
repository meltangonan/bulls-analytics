"""The and-1 counting rule, and the published rows it produced."""
import pandas as pd
import pytest
from scripts.prototypes import and_one_leaders_data as post

BULLS = post.BULLS
OTHER = 1610612758


def event(**fields):
    row = dict(teamId=BULLS, personId=1, playerName="Player", period=4, clock="PT06M39.00S",
               isFieldGoal=0, shotResult="", shotValue=0, actionType="", subType="",
               description="")
    row.update(fields)
    return row


def made_shot(value=2, **fields):
    return event(isFieldGoal=1, shotResult="Made", shotValue=value,
                 actionType="Made Shot", subType="Jump Shot", **fields)


def shooting_foul(**fields):
    return event(teamId=OTHER, personId=99, actionType="Foul", subType="Shooting", **fields)


def free_throw(subType="Free Throw 1 of 1", **fields):
    return event(actionType="Free Throw", subType=subType,
                 description=fields.pop("description", "Player Free Throw 1 of 1 (3 PTS)"),
                 **fields)


def count(rows):
    counted = post.count_game(pd.DataFrame(rows))
    return counted[0] if counted else None


def test_made_shot_with_shooting_foul_and_one_free_throw_counts():
    row = count([made_shot(), shooting_foul(), free_throw()])
    assert row["and1s"] == 1
    assert row["and1s_3pt"] == 0 and row["and1s_flagrant"] == 0 and row["and1s_made_ft"] == 1


def test_missed_free_throw_still_counts_but_is_recorded():
    row = count([made_shot(), shooting_foul(),
                 free_throw(description="MISS Player Free Throw 1 of 1")])
    assert row["and1s"] == 1 and row["and1s_made_ft"] == 0


def test_three_point_and_flagrant_forms_are_tallied():
    row = count([made_shot(value=3), shooting_foul(),
                 free_throw(subType="Free Throw Flagrant 1 of 1")])
    assert row["and1s"] == 1 and row["and1s_3pt"] == 1 and row["and1s_flagrant"] == 1


def test_technical_free_throw_after_a_basket_is_not_an_and_one():
    assert count([made_shot(), event(teamId=OTHER, personId=99, actionType="Foul",
                                     subType="Technical"),
                  free_throw(subType="Free Throw Technical")]) is None


def test_away_from_play_foul_shot_by_a_team_mate_is_not_an_and_one():
    """The shooter keeps his basket; a different player takes the free throw."""
    rows = [made_shot(), event(teamId=OTHER, personId=99, actionType="Foul",
                               subType="Away From Play"),
            free_throw(personId=2, playerName="Team-mate")]
    assert count(rows) is None


def test_one_shot_trip_without_a_made_basket_is_not_an_and_one():
    assert count([shooting_foul(), free_throw()]) is None


def test_free_throw_without_an_opponent_foul_at_that_moment_is_not_an_and_one():
    assert count([made_shot(), free_throw()]) is None


def test_a_later_free_throw_does_not_attach_to_an_earlier_basket():
    rows = [made_shot(), shooting_foul(), free_throw(clock="PT02M00.00S")]
    assert count(rows) is None


def test_published_rows_match_the_saved_selection():
    top = pd.read_csv(post.DATA / "top15.csv")
    assert len(top) == post.TOP_N
    assert top["and1s"].is_monotonic_decreasing
    assert top.loc[0, "player_name"] == "DeMar DeRozan" and top.loc[0, "and1s"] == 79
    jordan = top[top["player_name"] == "Michael Jordan"]
    assert jordan["season"].tolist() == ["1997-98", "1996-97"]
    assert jordan["and1s"].tolist() == [70, 45]
    # The cutoff tie is broken on per 100, not on the season.
    tail = top.tail(1).iloc[0]
    assert tail["player_name"] == "Luol Deng" and tail["and1s"] == 39
    everyone = pd.read_csv(post.DATA / "all_player_seasons.csv")
    rose = everyone[(everyone["player_name"] == "Jalen Rose") & (everyone["season"] == "2002-03")]
    assert rose["and1s"].iloc[0] == 39
    assert float(rose["per_100"].iloc[0]) < float(tail["per_100"])


def test_every_published_row_is_bounded_by_both_providers():
    """Neither provider may disagree with a published count by more than one."""
    top = pd.read_csv(post.DATA / "selection_audit.csv")
    for column in ("bbr_and1s", "pbpstats_and1s"):
        gap = (top["and1s"] - top[column]).abs()
        assert gap.max() <= 5  # pbpstats misses five of Jordan's 1996-97 and-1s
    assert (top["and1s"] - top["bbr_and1s"]).abs().max() <= 1


def test_counted_seasons_and_games_are_complete():
    games = pd.read_csv(post.DATA / "games_counted.csv")
    assert games["season"].tolist() == post.SEASONS
    assert games.loc[games["season"] == "1998-99", "games"].iloc[0] == 50  # lockout
    assert games["games"].sum() == 2385


@pytest.mark.parametrize("season", ["1995-96", "1996-97"])
def test_window_starts_where_play_by_play_starts(season):
    assert (season in post.SEASONS) == (season == "1996-97")
