"""Shot families from NBA.com's ``ACTION_TYPE``, and what that label can support.

``ACTION_TYPE`` is typed by a human scorer at each arena, not measured. Two
consequences travel with every number derived from it, and both belong to the
label rather than to any one post:

* ``Jump Shot`` is the scorer's *unlabelled default*, not a technique. It is the
  largest family for most subjects. Keep it -- dropping a third of a season
  would misstate every other share -- but never rename it "catch-and-shoot".
  Tracking measures a genuine catch-and-shoot rate, and the two figures differ;
  a tracking name on a label-derived number does not survive being checked.
* Scorers vary by arena, so a rate can carry a venue habit as well as
  basketball. The team-level audit in the shot-diet post found the United Center
  7th of 30 on that effect and the finding intact on road games alone. A single
  player's home/road split is smaller and noisier, so that audit does not
  transfer: at player scope, prefer comparing a subject with himself, where both
  windows carry the same labelling regime.

The rules are ordered. ``floating`` must be tested before ``layup`` because NBA
writes "Floating Jump Shot" and "Driving Floating Bank Jump Shot"; a later
``jump`` rule would otherwise absorb them.
"""
from __future__ import annotations

import re

import pandas as pd

FAMILY_RULES: tuple[tuple[str, str], ...] = (
    ("Dunks", r"dunk"),
    ("Floaters", r"floating"),
    ("Tip-ins", r"\btip\b"),
    ("Layups", r"layup|finger roll"),
    ("Hooks", r"hook"),
    ("Pull-ups", r"pull-?up"),
    ("Step-backs", r"step back"),
    ("Turnarounds/fades", r"turnaround|fadeaway"),
    ("Running jumpers", r"running jump"),
)

UNLABELLED = "Standard jumpers"

FAMILIES: tuple[str, ...] = tuple(name for name, _ in FAMILY_RULES) + (UNLABELLED,)

# A shot the player made for himself off the dribble, as the labels describe it.
# This is the shot-diet post's definition, unchanged, so the two posts cannot
# quietly disagree about what "self-created" counts.
SELF_CREATED: tuple[str, ...] = ("Pull-ups", "Step-backs", "Turnarounds/fades")


def classify(action: str) -> str:
    """One ``ACTION_TYPE`` string to one family name."""
    lowered = str(action).lower()
    for name, pattern in FAMILY_RULES:
        if re.search(pattern, lowered):
            return name
    return UNLABELLED


def classify_series(actions: pd.Series) -> pd.Series:
    return actions.map(classify)


def family_shares(actions: pd.Series, made: pd.Series | None = None,
                  min_fga: int = 20) -> pd.DataFrame:
    """Every family's attempts and share, in a stable order, zeros included.

    A family the subject never used is returned as a zero row rather than
    dropped: an absent row silently redraws the chart with a hole in it, and for
    a shot diet an untaken shot type is itself the finding.

    ``rated`` marks whether a family holds enough attempts to stand behind a
    made-rate. Shares are counts and need no such guard; a rate does.
    """
    families = classify_series(actions)
    total = len(families)
    frame = pd.DataFrame({"family": families})
    if made is not None:
        frame["made"] = pd.Series(made).astype(int).to_numpy()
    rows = []
    for name in FAMILIES:
        block = frame[frame.family.eq(name)]
        fga = len(block)
        fgm = int(block.made.sum()) if made is not None and fga else 0
        rows.append({
            "family": name,
            "fga": fga,
            "fgm": fgm,
            "share_pct": fga / total * 100 if total else 0.0,
            "fg_pct": fgm / fga * 100 if (made is not None and fga) else float("nan"),
            "self_created": name in SELF_CREATED,
            "unlabelled_default": name == UNLABELLED,
            "rated": bool(fga >= min_fga),
        })
    return pd.DataFrame(rows)
