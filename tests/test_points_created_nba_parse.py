"""Checks for attribution mistakes that can leave the overall assist sum intact."""

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes.points_created_nba_parse import parse_game


def shot(action, scorer, name, assister, ordinal, value=2, team=1):
    return {"gameId": "0021000001", "actionNumber": action, "teamId": team,
            "personId": scorer, "playerName": name, "playerNameI": name,
            "description": f"{name} makes shot ({assister} {ordinal} AST)",
            "shotResult": "Made", "isFieldGoal": 1, "shotValue": value}


def roster(rows):
    return pd.DataFrame(rows, columns=["PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "AST"])


def test_same_surname_opponents_are_separated_and_scoring_is_weighted():
    logs = roster([(1, "John Smith", 1, 1), (2, "Alex Brown", 1, 0),
                   (3, "James Smith", 2, 1), (4, "Max Green", 2, 0)])
    frame = pd.DataFrame([shot(1, 2, "Brown", "Smith", 1, 2, 1),
                          shot(2, 4, "Green", "Smith", 1, 3, 2)])
    events, issues = parse_game(frame, logs)
    assert not issues
    assert events.assister_id.tolist() == [1, 3]
    assert events.groupby("assister_id").shot_value.sum().to_dict() == {1: 2, 3: 3}


def test_suffix_exact_match_and_roster_only_assister():
    logs = roster([(1, "Carlik Jones", 1, 1), (2, "Derrick Jones Jr.", 1, 1),
                   (3, "Nikola Vučević", 1, 1), (4, "Coby White", 1, 0)])
    frame = pd.DataFrame([shot(1, 4, "White", "Jones", 1),
                          shot(2, 4, "White", "Jones Jr.", 1),
                          shot(3, 4, "White", "Vucevic", 1)])
    events, issues = parse_game(frame, logs)
    assert not issues
    assert events.assister_id.tolist() == [1, 2, 3]


def test_shared_surname_cannot_self_assist():
    logs = roster([(1, "John Smith", 1, 1), (2, "James Smith", 1, 0)])
    events, issues = parse_game(pd.DataFrame([shot(1, 2, "Smith", "Smith", 1)]), logs)
    assert not issues
    assert events.assister_id.tolist() == [1]


def test_ambiguous_surname_is_reported_without_guessing():
    logs = roster([(1, "John Smith", 1, 1), (2, "James Smith", 1, 0),
                   (3, "Joe Brown", 1, 0)])
    events, issues = parse_game(pd.DataFrame([shot(1, 3, "Brown", "Smith", 1)]), logs)
    assert events.empty
    assert any(i["kind"] == "unresolved_assister" for i in issues)


def test_four_letter_prefix_resolves_literal_match():
    logs = roster([(1, "Shelden Williams", 1, 1), (2, "Shawne Williams", 1, 1),
                   (3, "Joe Brown", 1, 0)])
    frame = pd.DataFrame([shot(1, 3, "Brown", "Shel. Williams", 1),
                          shot(2, 3, "Brown", "Shaw. Williams", 1)])
    events, issues = parse_game(frame, logs)
    assert not issues
    assert events.assister_id.tolist() == [1, 2]


def test_long_prefix_collision_stays_unresolved():
    logs = roster([(1, "Shelden Williams", 1, 1), (2, "Shelton Williams", 1, 0),
                   (3, "Joe Brown", 1, 0)])
    events, issues = parse_game(pd.DataFrame([shot(1, 3, "Brown", "Shel. Williams", 1)]), logs)
    assert events.empty
    unresolved = [i for i in issues if i["kind"] == "unresolved_assister"]
    assert len(unresolved) == 1
    assert unresolved[0]["candidates"] == [1, 2]


def test_shot_value_discrepancy_is_rejected_despite_matching_assists():
    logs = roster([(1, "John Smith", 1, 1), (2, "Joe Brown", 1, 0)])
    logs["FGM"] = [0, 1]
    logs["FG3M"] = [0, 1]
    events, issues = parse_game(pd.DataFrame([shot(1, 2, "Brown", "Smith", 1, 2)]), logs)
    assert len(events) == 1
    assert [(i["kind"], i.get("stat")) for i in issues] == [
        ("field_goal_count_mismatch", "FG3M")]


def test_cached_both_teams_official_game():
    root = Path(__file__).resolve().parents[1]
    data = root / "docs/visuals/2026-09-21-points-created/data/nba-league"
    pbp_path = data / "sample-pbp-0021000001.json"
    logs_path = data / "player-game-logs-2010-11.json"
    if not pbp_path.exists() or not logs_path.exists():
        pytest.skip("Optional captured NBA audit fixtures are not present")
    game = json.loads(pbp_path.read_text())["game"]
    frame = pd.DataFrame(game["actions"])
    frame["gameId"] = game["gameId"]
    source = json.loads(logs_path.read_text())["resultSets"][0]
    logs = pd.DataFrame(source["rowSet"], columns=source["headers"])
    logs = logs[logs.GAME_ID == game["gameId"]]
    events, issues = parse_game(frame, logs)
    assert not [i for i in issues if i["severity"] == "error"]
    assert len(events) == logs.AST.sum()
    assert events.team_id.nunique() == 2
