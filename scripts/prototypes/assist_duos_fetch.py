"""Cache every assisted Bulls field goal since 2000-01 from NBA.com play-by-play.

One row per assisted Bulls basket: who passed, who scored, and what the shot was worth.
That is the only source with player-to-player assist detail this far back — the tracking
passing dashboard (``PlayerDashPtPass``) starts in 2013-14 — and it is the only source at
any point in time that carries the shot value, so assists and the points they produced
come from one reconciled record.

Written as a separate module from the renderer because the fetch is a long, resumable job:
about 2,100 games, one request each. **NBA.com throttles concurrent play-by-play requests
hard** — a brief 4-worker test was enough to make even single serial requests time out for
several minutes — so this stays strictly serial with backoff. Each season is checkpointed
to its own CSV, so an interrupted run resumes at the season it stopped on.

## Identity matching

Play-by-play names the assister only inside the event description (``"... (Giddey 4 AST)"``)
with no player id. Two resolutions are needed and both are load-bearing:

- **Fold diacritics.** Descriptions are ASCII (``Vucevic``) while the ``playerName`` column
  keeps accents (``Vučević``). A literal comparison silently drops those rows — 182 of them
  in 2025-26 alone, with no error.
- **Resolve the surname against Bulls players in that game first.** The candidate set is
  smallest there, so two players sharing a surname (the 2025-26 roster carried both Leonard
  and Emanuel Miller) only collide if both appeared in the same game. The season-wide map is
  the fallback for an assister whose only appearance in a game is the assist itself, which
  produces no event row of his own.

Anything still unresolved is counted and reported, never silently dropped.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, playbyplayv3, playergamelogs
from nba_api.stats.static import players as static_players

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS

FIRST_SEASON_END_YEAR = 2001
LAST_SEASON_END_YEAR = 2026

CACHE = _REPO / "cache" / "assist-duos"
REQUEST_DELAY_SECONDS = 1.0
REQUEST_ATTEMPTS = 5
BACKOFF_SECONDS = (5, 20, 60, 120)

ASSIST_RE = re.compile(r"\(([^()]+?)\s+\d+\s+AST\)")


def season_label(end_year: int) -> str:
    """2001 -> '2000-01', matching NBA.com's season parameter."""
    return f"{end_year - 1}-{str(end_year)[-2:]}"


GENERATIONAL_SUFFIXES = {"JR", "JR.", "SR", "SR.", "II", "III", "IV", "V"}


def fold(name: str) -> str:
    """Strip diacritics and upper-case, so 'Vučević' and 'Vucevic' compare equal."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(name)) if not unicodedata.combining(c)
    ).upper()


def surname_key(name: str) -> str:
    """Fold a name and drop any trailing generational suffix.

    The two sides of the match disagree about suffixes. NBA.com's ``playerName`` column
    carries them ("Butler III") while the event description does not ("(Butler 3 AST)"),
    so a fold-only comparison dropped **every assist Jimmy Butler made as a Bull** — 417
    in 2016-17 alone, over a fifth of the season, with no error raised.

    Stripping the suffix cannot cause a misattribution: a genuine father/son collision
    still leaves two ids under one key, and the caller rejects any key that is not unique.
    """
    folded = fold(name).strip()
    parts = folded.split()
    while len(parts) > 1 and parts[-1] in GENERATIONAL_SUFFIXES:
        parts.pop()
    return " ".join(parts)


def _request(factory, label: str):
    """Run one NBA.com request with backoff. Raises if every attempt fails."""
    last_error: Exception | None = None
    for attempt in range(REQUEST_ATTEMPTS):
        try:
            frame = factory().get_data_frames()[0]
            time.sleep(REQUEST_DELAY_SECONDS)
            return frame
        except Exception as error:  # noqa: BLE001 - retry any transport or parse failure
            last_error = error
            if attempt < len(BACKOFF_SECONDS):
                time.sleep(BACKOFF_SECONDS[attempt])
    raise RuntimeError(f"{label} failed after {REQUEST_ATTEMPTS} attempts: {last_error}")


def bulls_game_log(end_year: int) -> pd.DataFrame:
    """Bulls regular-season team-game rows for one season, cached.

    Carries the official ``AST`` per game, which is what every extracted assisted basket
    is reconciled against.
    """
    path = CACHE / f"game-log-{season_label(end_year)}.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"GAME_ID": str})
    season = season_label(end_year)
    games = _request(
        lambda: leaguegamefinder.LeagueGameFinder(
            season_nullable=season,
            season_type_nullable="Regular Season",
            league_id_nullable="00",
            team_id_nullable=BULLS_TEAM_ID,
            timeout=60,
            headers=_NBA_HEADERS,
        ),
        f"game finder {season}",
    )
    games = games.drop_duplicates("GAME_ID").sort_values("GAME_ID")
    CACHE.mkdir(parents=True, exist_ok=True)
    games.to_csv(path, index=False)
    return games


def bulls_game_ids(end_year: int) -> list[str]:
    """Every Bulls regular-season game id for one season, oldest first."""
    return sorted(bulls_game_log(end_year).GAME_ID.astype(str).unique())


def bulls_player_game_logs(end_year: int) -> pd.DataFrame:
    """Every Bulls player-game for one season, cached: player id, game id, minutes.

    One request per season covers the whole roster, which is what makes "games these two
    played together" affordable across 26 seasons. Rows exist only for games a player
    actually appeared in, so an intersection of game ids is the shared-availability count.
    """
    path = CACHE / f"player-game-logs-{season_label(end_year)}.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"GAME_ID": str})
    logs = _request(
        lambda: playergamelogs.PlayerGameLogs(
            season_nullable=season_label(end_year),
            season_type_nullable="Regular Season",
            team_id_nullable=BULLS_TEAM_ID,
            timeout=60,
            headers=_NBA_HEADERS,
        ),
        f"player game logs {season_label(end_year)}",
    )
    logs = logs[["PLAYER_ID", "PLAYER_NAME", "GAME_ID", "MIN"]].copy()
    logs["season_end_year"] = end_year
    CACHE.mkdir(parents=True, exist_ok=True)
    logs.to_csv(path, index=False)
    return logs


def load_player_game_logs(
    first: int = FIRST_SEASON_END_YEAR, last: int = LAST_SEASON_END_YEAR
) -> pd.DataFrame:
    """Player game logs for every season in the range."""
    return pd.concat(
        [bulls_player_game_logs(year) for year in range(first, last + 1)],
        ignore_index=True,
    )


def reconcile_season(end_year: int) -> dict[str, object]:
    """Compare extracted assisted baskets with the official box-score assist total.

    Play-by-play is the official scorer's record, so these should agree almost exactly.
    A gap is reported rather than forced away — the realistic causes are an assister
    surname that could not be resolved to one player, or an NBA.com scoring correction
    applied to the box score but not to the event feed.
    """
    events = fetch_season(end_year)
    official = int(bulls_game_log(end_year).AST.sum())
    extracted = len(events)
    return {
        "season": season_label(end_year),
        "official_assists": official,
        "extracted_assists": extracted,
        "difference": extracted - official,
        "coverage": extracted / official if official else float("nan"),
    }


@lru_cache(maxsize=1)
def _static_full_names() -> dict[int, str]:
    """Player id -> full name, from nba_api's offline table. No request."""
    return {int(p["id"]): p["full_name"] for p in static_players.get_players()}


def _name_variants(full_name: str) -> set[str]:
    """Every disambiguation form NBA.com might use for one player.

    When a roster carries two players with the same surname, the event description
    disambiguates with a *prefix of the first name*, and the length of that prefix is
    whatever it takes to be unique — one letter for "(J. Sampson 2 AST)", two for the
    2008-09 Bulls' Tyrus and Tim Thomas ("Ty. Thomas", "Ti. Thomas"). Neither
    ``playerName`` nor ``playerNameI`` carries the two-letter form, so it is generated
    here. Ambiguous keys are still rejected by the caller, so over-generating is safe.
    """
    parts = str(full_name).split()
    if len(parts) < 2:
        return {surname_key(full_name)}
    first, surname = parts[0], " ".join(parts[1:])
    variants = {surname_key(surname), surname_key(full_name)}
    for prefix_length in (1, 2, 3):
        if len(first) >= prefix_length:
            variants.add(surname_key(f"{first[:prefix_length]}. {surname}"))
    return variants


def _index_names(bulls: pd.DataFrame) -> dict[str, set[int]]:
    """Map every way a Bulls player is named in this frame to his player id.

    Indexes the frame's own two name columns plus the generated variants above.
    ``playerName`` is the bare surname; ``playerNameI`` adds the single-initial form.
    """
    index: dict[str, set[int]] = {}
    for column in ("playerName", "playerNameI"):
        if column not in bulls.columns:
            continue
        for person_id, name in zip(bulls.personId, bulls[column]):
            if person_id and isinstance(name, str) and name.strip():
                index.setdefault(surname_key(name), set()).add(int(person_id))

    full_names = _static_full_names()
    for person_id in {int(p) for p in bulls.personId if p}:
        full_name = full_names.get(person_id)
        if not full_name:
            continue
        for variant in _name_variants(full_name):
            index.setdefault(variant, set()).add(person_id)
    return index


def assisted_baskets_for_game(game_id: str) -> tuple[list[dict], dict[str, set[int]]]:
    """Return this game's assisted baskets (assister unresolved) and its name index."""
    pbp = _request(
        lambda: playbyplayv3.PlayByPlayV3(game_id=game_id, timeout=60, headers=_NBA_HEADERS),
        f"play-by-play {game_id}",
    )
    bulls = pbp[pbp.teamId == BULLS_TEAM_ID]
    made = bulls[(bulls.actionType == "Made Shot") & (bulls.isFieldGoal == 1)]

    rows = []
    for event in made.itertuples():
        match = ASSIST_RE.search(event.description or "")
        if not match:
            continue
        rows.append(
            {
                "game_id": game_id,
                "assister_key": surname_key(match.group(1)),
                "scorer_id": int(event.personId),
                "scorer_name": event.playerName,
                "shot_value": int(event.shotValue),
            }
        )
    return rows, _index_names(bulls)


def fetch_season(end_year: int, *, refresh: bool = False) -> pd.DataFrame:
    """Fetch and cache one season. Returns the cached frame if it already exists."""
    path = CACHE / f"assisted-baskets-{season_label(end_year)}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path, dtype={"game_id": str})

    game_ids = bulls_game_ids(end_year)
    pending: list[dict] = []
    game_indexes: dict[str, dict[str, set[int]]] = {}

    # Phase one: collect every assisted basket and every game's name index. Resolution
    # waits until the whole season is in hand, because a player whose *only* appearance
    # in a game is the assist itself produces no event row of his own — Trentyn Flowers
    # and Cristiano Felício each lost an assist to a single-pass version that could only
    # consult the games it had already walked.
    for index, game_id in enumerate(game_ids, 1):
        game_rows, name_index = assisted_baskets_for_game(game_id)
        pending.extend(game_rows)
        game_indexes[game_id] = name_index
        if index % 20 == 0:
            print(
                f"  {season_label(end_year)}  {index}/{len(game_ids)} games, "
                f"{len(pending)} assisted baskets",
                flush=True,
            )

    season_index: dict[str, set[int]] = {}
    for name_index in game_indexes.values():
        for key, ids in name_index.items():
            season_index.setdefault(key, set()).update(ids)

    # Phase two: resolve against that game's roster first — the smallest candidate set,
    # so two players sharing a surname only collide if both played — then the season.
    rows: list[dict] = []
    unresolved: list[tuple] = []
    for row in pending:
        key = row["assister_key"]
        ids = game_indexes[row["game_id"]].get(key) or season_index.get(key)
        if not ids or len(ids) != 1:
            unresolved.append((row["game_id"], key, sorted(ids) if ids else None))
            continue
        rows.append(
            {
                "game_id": row["game_id"],
                "assister_id": next(iter(ids)),
                "scorer_id": row["scorer_id"],
                "scorer_name": row["scorer_name"],
                "shot_value": row["shot_value"],
            }
        )

    frame = pd.DataFrame(rows)
    frame["season_end_year"] = end_year
    frame["season"] = season_label(end_year)
    CACHE.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    print(
        f"{season_label(end_year)}: {len(game_ids)} games, {len(frame)} assisted baskets, "
        f"{len(unresolved)} unresolved",
        flush=True,
    )
    if unresolved:
        # Report by surname with counts. The first-five-rows view hid the Butler bug for
        # a full run: five identical lines look like a rounding error, "BUTLER x417"
        # does not.
        counts: dict[str, int] = {}
        for _, surname, _ids in unresolved:
            counts[surname] = counts.get(surname, 0) + 1
        summary = ", ".join(
            f"{name} x{count}"
            for name, count in sorted(counts.items(), key=lambda kv: -kv[1])
        )
        print(f"    UNRESOLVED SURNAMES: {summary}", flush=True)
    return frame


def load_history(
    first: int = FIRST_SEASON_END_YEAR,
    last: int = LAST_SEASON_END_YEAR,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Every cached season, fetching any that are missing."""
    frames = [fetch_season(year, refresh=refresh) for year in range(first, last + 1)]
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=int, default=FIRST_SEASON_END_YEAR)
    parser.add_argument("--last", type=int, default=LAST_SEASON_END_YEAR)
    parser.add_argument("--refresh", action="store_true", help="refetch cached seasons")
    parser.add_argument(
        "--reconcile", action="store_true", help="check each season against official assists"
    )
    args = parser.parse_args()

    history = load_history(args.first, args.last, refresh=args.refresh)
    print(f"\ntotal: {len(history)} assisted baskets across {history.season.nunique()} seasons")

    if args.reconcile:
        report = pd.DataFrame(
            reconcile_season(year) for year in range(args.first, args.last + 1)
        )
        print("\n" + report.to_string(index=False))
        print(
            f"\noverall: {report.extracted_assists.sum()} extracted vs "
            f"{report.official_assists.sum()} official "
            f"({report.extracted_assists.sum() / report.official_assists.sum():.4%})"
        )


if __name__ == "__main__":
    main()
