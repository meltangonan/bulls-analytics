"""Selection, tie-handling and overtime checks for the scoring-duo games post."""
import pandas as pd
import pytest

from scripts.prototypes import scoring_duo_games_data as post


DATA = post.DEFAULT_DATA_DIR


def frame(rows):
    """A minimal player-game table with the columns select_duos reads."""
    return pd.DataFrame(rows, columns=[
        "game_id", "season_end_year", "season", "game_date", "matchup", "opponent",
        "result", "team_points", "player_id", "player", "points", "minutes",
    ])


def test_duo_is_the_two_leading_scorers_not_an_arbitrary_pair():
    table = frame([
        ("1", 2023, "2022–23", "2023-01-01", "CHI vs. MIN", "MIN", "W", 120, 10, "A", 40, 38),
        ("1", 2023, "2022–23", "2023-01-01", "CHI vs. MIN", "MIN", "W", 120, 11, "B", 30, 36),
        ("1", 2023, "2022–23", "2023-01-01", "CHI vs. MIN", "MIN", "W", 120, 12, "C", 20, 30),
    ] + [("1", 2023, "2022–23", "2023-01-01", "CHI vs. MIN", "MIN", "W", 120, 13, "D", 10, 136)])
    duo = post.select_duos(table).iloc[0]
    assert (duo.player_1, duo.player_2) == ("A", "B")
    assert duo.combined_points == 70
    assert duo.point_gap == 10
    # The two leading scorers also maximise the lower half of any pair, which is
    # why the post needs no separate both-players qualifier.
    assert duo.player_2_points == 30


def test_second_scorer_tie_is_resolved_on_minutes_and_counted():
    table = frame([
        ("1", 2019, "2018–19", "2019-03-01", "CHI @ ATL", "ATL", "W", 168, 10, "LaVine", 47, 55.5),
        ("1", 2019, "2018–19", "2019-03-01", "CHI @ ATL", "ATL", "W", 168, 11, "Porter", 31, 54.5),
        ("1", 2019, "2018–19", "2019-03-01", "CHI @ ATL", "ATL", "W", 168, 12, "Markkanen", 31, 53.8),
    ] + [("1", 2019, "2018–19", "2019-03-01", "CHI @ ATL", "ATL", "W", 168, 13, "Dunn", 14, 176.2)])
    duo = post.select_duos(table).iloc[0]
    assert duo.player_2 == "Porter"       # more minutes than the equal scorer
    assert duo.second_tied_with == 1      # and the graphic's audit records the other claim


def test_overtime_comes_from_the_team_minute_budget():
    def game(gid, total_minutes):
        each = total_minutes / 4
        return [(gid, 2023, "2022–23", "2023-01-01", "CHI vs. MIN", "MIN", "W", 120,
                 i, f"P{i}", 20 - i, each) for i in range(4)]

    table = frame(game("reg", 240) + game("ot", 265) + game("four", 340))
    periods = post.overtime_periods(table)
    assert periods["reg"] == 0
    assert periods["ot"] == 1
    assert periods["four"] == 4


def test_source_rounding_is_absorbed_but_a_real_mismatch_raises():
    def game(gid, total_minutes):
        each = total_minutes / 4
        return [(gid, 2003, "2002–03", "2003-01-31", "CHI @ POR", "POR", "L", 94,
                 i, f"P{i}", 20 - i, each) for i in range(4)]

    # The 2002-03 game at Portland logs 236.9 team minutes; it is still regulation.
    assert post.overtime_periods(frame(game("short", 236.92)))["short"] == 0
    with pytest.raises(ValueError, match="do not match"):
        post.overtime_periods(frame(game("broken", 252)))


def test_saved_top15_matches_its_own_printed_numbers():
    top = pd.read_csv(DATA / "top15.csv")
    assert len(top) == 15
    assert top["rank"].tolist() == list(range(1, 16))
    assert (top.player_1_points + top.player_2_points).equals(top.combined_points)
    assert top.combined_points.is_monotonic_decreasing
    assert (top.player_1_points >= top.player_2_points).all()
    assert top.iloc[0].combined_points == 88
    assert (top.iloc[0].player_1_points, top.iloc[0].player_2_points) == (49, 39)
    # Share is the duo's points over the official team score, not a sum of players.
    assert top.team_share_pct.round(1).equals(
        (top.combined_points / top.team_points * 100).round(1)
    )


def test_saved_selection_covers_every_season_and_reports_overtime():
    audit = pd.read_csv(DATA / "selection_audit.csv", index_col=0)["value"]
    assert int(audit["games_considered"]) == 2089
    assert int(audit["seasons_covered"]) == 26
    assert int(audit["overtime_games_in_top"]) == 8
    # Overtime is rare overall, which is exactly why the graphic labels it.
    assert float(audit["overtime_share_all_games_pct"]) < 10
    # No balance qualifier is applied, so the audit has to show the worst case.
    assert int(audit["lowest_second_scorer_in_top"]) == 22


def test_cutoff_tie_prefers_the_more_balanced_game():
    top = pd.read_csv(DATA / "top15.csv")
    every = pd.read_csv(DATA / "all_duo_games.csv")
    cutoff = top.combined_points.min()
    tied = every[every.combined_points == cutoff]
    assert len(tied) == 2
    kept = top[top.combined_points == cutoff].iloc[0]
    dropped = tied[~tied.game_id.isin(top.game_id)].iloc[0]
    assert kept.player_2_points > dropped.player_2_points
