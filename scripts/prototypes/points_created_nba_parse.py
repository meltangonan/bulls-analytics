"""Attribute NBA PlayByPlayV3 assisted baskets and audit official game assists.

No network access. Player-game box rows supply the same-team roster and official AST;
play-by-play supplies the basket's value. Issues are returned, never silently repaired.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

from scripts.prototypes.assist_duos_fetch import (
    ASSIST_RE, _index_names, _name_variants, fold, surname_key,
)

EVENT_COLUMNS = [
    "game_id", "team_id", "action_number", "assister_id", "scorer_id",
    "shot_value", "assist_ordinal", "assister_raw",
]


def parse_game(frame: pd.DataFrame, logs: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Return assisted-basket rows and unresolved/box-count audit issues.

    ``logs`` contains PLAYER_ID, PLAYER_NAME, TEAM_ID, AST for a single game.
    If GAME_ID is supplied, it is checked against the play-by-play game ID.
    An empty issue list requires every player's extracted assist count to match
    the official box count; that check cannot independently prove shot values.
    """
    required = {"PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "AST"}
    if missing := required - set(logs.columns):
        raise ValueError(f"Player-game logs missing columns: {sorted(missing)}")
    if frame.empty or logs.empty:
        raise ValueError("Play-by-play and player-game logs must both be nonempty")
    games = frame.gameId.astype(str).str.zfill(10).unique()
    if len(games) != 1:
        raise ValueError("parse_game requires exactly one play-by-play game")
    game_id = games[0]
    if "GAME_ID" in logs and set(logs.GAME_ID.astype(str).str.zfill(10)) != {game_id}:
        raise ValueError("Player-game logs and play-by-play game IDs differ")
    if logs.duplicated(["TEAM_ID", "PLAYER_ID"]).any():
        raise ValueError("Duplicate player-game log rows")
    if logs[list(required)].isna().any().any():
        raise ValueError("Player-game logs contain missing roster or assist values")

    issues: list[dict] = []
    indexes = {}
    official = {}
    for team_id, team_logs in logs.groupby("TEAM_ID"):
        team_id = int(team_id)
        roster = set(team_logs.PLAYER_ID.astype(int))
        team_events = frame[(frame.teamId == team_id) & frame.personId.isin(roster)]
        index = _index_names(team_events)
        # Box rosters also name players with no personal event in the play-by-play.
        for player in team_logs.itertuples():
            player_id = int(player.PLAYER_ID)
            name = str(player.PLAYER_NAME)
            official[(team_id, player_id)] = int(player.AST)
            for variant in _name_variants(name):
                index["loose"].setdefault(variant, set()).add(player_id)
            parts = name.split()
            # NBA also uses four or more characters (Shel. Williams, Shaw.
            # Williams). Enumerate literal prefixes, retaining all collisions.
            if len(parts) > 1:
                for length in range(1, len(parts[0]) + 1):
                    variant = surname_key(f"{parts[0][:length]}. {' '.join(parts[1:])}")
                    index["loose"].setdefault(variant, set()).add(player_id)
            literal_forms = {name, " ".join(parts[1:])}
            if len(parts) > 1:
                literal_forms.add(f"{parts[0][0]}. {' '.join(parts[1:])}")
            for variant in literal_forms:
                if variant:
                    index["exact"].setdefault(fold(variant).strip(), set()).add(player_id)
        indexes[team_id] = index

    tally: Counter = Counter()
    rows = []
    ordered = frame.sort_values("actionNumber", kind="stable")
    for event in ordered.itertuples():
        description = event.description if isinstance(event.description, str) else ""
        match = ASSIST_RE.search(description)
        if not match:
            continue
        base = {"game_id": game_id, "action_number": int(event.actionNumber),
                "team_id": int(event.teamId), "description": description}
        if not (event.isFieldGoal == 1 and event.shotResult == "Made"
                and event.shotValue in (2, 3)):
            issues.append({**base, "severity": "error", "kind": "assist_on_invalid_field_goal"})
            continue
        raw, ordinal = fold(match.group(1)).strip(), int(match.group(2))
        index = indexes.get(int(event.teamId))
        ids = set() if index is None else set(
            index["exact"].get(raw) or index["loose"].get(surname_key(raw)) or []
        )
        # A player cannot assist his own basket. For shared surnames, use the
        # running ordinal only when it uniquely identifies one roster candidate.
        ids.discard(int(event.personId))
        if len(ids) > 1:
            ordinal_matches = {pid for pid in ids
                               if tally[(int(event.teamId), pid)] == ordinal - 1}
            if len(ordinal_matches) == 1:
                ids = ordinal_matches
        if len(ids) != 1:
            issues.append({**base, "severity": "error", "kind": "unresolved_assister", "assister_raw": raw,
                           "assist_ordinal": ordinal, "candidates": sorted(ids)})
            continue
        player_id = next(iter(ids))
        key = (int(event.teamId), player_id)
        if tally[key] + 1 != ordinal:
            issues.append({**base, "severity": "warning", "kind": "assist_ordinal_gap", "player_id": player_id,
                           "expected": tally[key] + 1, "observed": ordinal})
        tally[key] += 1
        rows.append({"game_id": game_id, "team_id": int(event.teamId),
                     "action_number": int(event.actionNumber), "assister_id": player_id,
                     "scorer_id": int(event.personId), "shot_value": int(event.shotValue),
                     "assist_ordinal": ordinal, "assister_raw": raw})

    for key in sorted(set(official) | set(tally)):
        expected, observed = official.get(key, 0), tally[key]
        if expected != observed:
            issues.append({"game_id": game_id, "team_id": key[0], "player_id": key[1],
                           "severity": "error", "kind": "assist_count_mismatch", "official_ast": expected,
                           "pbp_ast": observed, "difference": observed - expected})
    if {"FGM", "FG3M"}.issubset(logs.columns):
        made = frame[(frame.isFieldGoal == 1) & (frame.shotResult == "Made")]
        field_goals = made.groupby(["teamId", "personId"]).size()
        threes = made[made.shotValue == 3].groupby(["teamId", "personId"]).size()
        for player in logs.itertuples():
            key = (int(player.TEAM_ID), int(player.PLAYER_ID))
            for stat, observed in (("FGM", int(field_goals.get(key, 0))),
                                   ("FG3M", int(threes.get(key, 0)))):
                expected = int(getattr(player, stat))
                if expected != observed:
                    issues.append({"game_id": game_id, "team_id": key[0],
                                   "player_id": key[1], "severity": "error",
                                   "kind": "field_goal_count_mismatch", "stat": stat,
                                   "official": expected, "pbp": observed,
                                   "difference": observed - expected})
    return pd.DataFrame(rows, columns=EVENT_COLUMNS), issues
