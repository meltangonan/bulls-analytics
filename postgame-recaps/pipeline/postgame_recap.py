"""Postgame recap: wait until NBA.com has published and settled every feed for a finished game, then build the recap.

    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/postgame_recap.py --today
    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/postgame_recap.py 0012600037
    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/postgame_recap.py 0012600037 1760059860   (a restart)

Run from the repo root (a worktree uses the primary checkout's venv). --today finds tonight's Bulls game in
NBA.com's schedule (before 6 am, last night's) and exits quietly when there is none; a game ID runs that game.
--check reports once whether the game is final and builds nothing. The second number is the time NBA.com
first showed Final, printed by a notice (below); a restart passes it so the timing line and the deadline carry on.

1. Every 90 seconds it checks that the game is Final, the box score is filled and the play-by-play ends on the
   final score. It holds the Mac awake (caffeinate) while it runs.
2. Then it pulls every feed (pull_game.py) and computes every number (recap_data.py). Either one exits
   NOT_READY (75) while a feed the slides use is unpublished, or while the play-by-play, the game logs or the
   game-flow counts disagree with NBA.com; it logs the reason, waits 90 seconds (5 minutes from an hour after
   Final) and pulls again. Any other failure three times in a row stops the run; once or twice, it pulls again
   (a half-published feed can crash a step).
3. Notices: at fixed minutes after Final (MARKS) it prints what it is waiting on and a restart command, then
   exits STILL_WAITING (76). The run-postgame-recap skill posts the notice, pushes it to the phone when it matters,
   and restarts the command; nothing is lost, because every feed is on disk. Each mark is raised once: a
   restarted process begins after the mark it reported. It gives up three hours after Final.
4. It draws the shot chart (linking the shared cache, then removing only the link), builds the pages, exports
   the PNGs, copies them to iCloud Drive, writes caption.txt and keeps an as-posted/ copy of the feeds and
   recap.json, written once per game. One build runs at a time (a lock), because the cache link and the page
   file are shared.
5. It delivers the slides (deliver.py): image data only, added to the Photos album iCloud Photos syncs.
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import boxscoresummaryv3, boxscoretraditionalv3, playbyplayv3, scheduleleaguev2

from bulls.data.fetch import _NBA_HEADERS

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from deliver import deliver  # noqa: E402
from paths import OUTPUT, REPO, game_dir, shared_cache  # noqa: E402

PY = sys.executable
BULLS = 1610612741
POLL = 90  # seconds between checks for the first hour after Final
SLOW_POLL = 300  # after that: NBA.com is late anyway, and stats.nba.com throttles busy clients
NOT_READY = 75
STILL_WAITING = 76  # not a failure: the skill posts the notice and restarts the printed command
STRIKES = 3  # consecutive failures other than NOT_READY before the run stops
# Minutes after Final at which a notice is due: at Final itself (so the user knows the wait has begun), then
# often, because the post should be out within 30 minutes of the buzzer (user, 2026-10-09); sooner still when
# every feed is in but a check keeps failing (a scrambled feed, as DEN at UTA on 2026-10-06, or our own check).
MARKS = {"publishing": (0, 20, 30, 45, 60, 90, 120), "check": (0, 10, 20, 30, 45, 60, 90, 120)}
HASHTAGS = "#chicagobulls #bullsnation #nbadata #nbastats #basketballanalytics"
# NBA.com revises official stats after games (fast break points changed overnight in three of the first five).
REVISION_NOTE = "Stats via NBA.com as of game night. The NBA can revise official stats after a game."
# What recheck.py compares the next day, plus the play-by-play (margin line, runs, breakdown, Closer award)
# and the capture record; recap.json, the numbers the slides drew, is copied from output/.
SNAPSHOT = ["teams.csv", "players.csv", "ff_team.csv", "misc_teams.csv", "summary_stats.csv", "summary_linescore.csv",
            "shots_raw_chi.csv", "pbp.csv", "sources.json"]


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def game_day(now: datetime):
    """The dates to look for a Bulls game on, nearest first: before 6 am, last night's game comes first
    (a 9 pm CT tip-off ends after midnight)."""
    today = now.date()
    return [today - timedelta(days=1), today] if now.hour < 6 else [today]


def tonight() -> tuple[str, datetime, str] | None:
    """Today's Bulls game ID, tip-off (UTC) and matchup from NBA.com's schedule, or None on a day without one."""
    now = datetime.now()
    season = f"{now.year}-{(now.year + 1) % 100:02d}" if now.month >= 8 else f"{now.year - 1}-{now.year % 100:02d}"
    s = scheduleleaguev2.ScheduleLeagueV2(season=season, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
    s = s[(s.homeTeam_teamId == BULLS) | (s.awayTeam_teamId == BULLS)]
    dates = pd.to_datetime(s.gameDate).dt.date
    day = next((d for day in game_day(now) if not (d := s[dates == day]).empty), None)
    if day is None:
        return None
    r = day.iloc[0]
    home = r.homeTeam_teamId == BULLS
    matchup = f"{'vs' if home else 'at'} {r.awayTeam_teamCity if home else r.homeTeam_teamCity} {r.awayTeam_teamName if home else r.homeTeam_teamName}"
    return r.gameId, datetime.fromisoformat(str(r.gameDateTimeUTC).replace("Z", "+00:00")), matchup


def final(game_id: str) -> tuple[bool, str, bool]:
    """Cheap check: the game is Final, the box score is filled and the play-by-play ends on the final score.
    Returns (ready, what the log says, whether NBA.com shows Final). Each feed is asked separately, so a box
    score that is not up yet is named as such and does not hide that the game is already Final (Oct 8: NBA.com
    showed Final 33 minutes before it published the box score, and the timing line counted from the box score)."""
    kw = dict(game_id=game_id, headers=_NBA_HEADERS, timeout=30)

    def fetch(cls, pick):  # an unpublished feed comes back without its tables, which nba_api turns into an error
        try:
            return pick(cls(**kw).get_data_frames())
        except Exception:
            return pd.DataFrame()

    game = fetch(boxscoresummaryv3.BoxScoreSummaryV3, lambda fs: next(f for f in fs if "gameStatus" in f))
    if game.empty:
        return False, "summary not published yet", False
    if int(game.gameStatus.iloc[0]) != 3:
        return False, f"not final yet ({game.gameStatusText.iloc[0].strip()})", False
    teams = fetch(boxscoretraditionalv3.BoxScoreTraditionalV3, lambda fs: fs[2])
    if teams.empty or teams.points.fillna(0).sum() == 0:
        return False, "final; box score not published yet", True
    pbp = fetch(playbyplayv3.PlayByPlayV3, lambda fs: fs[0])
    pbp = pbp.dropna(subset=["scoreHome"]) if not pbp.empty else pbp
    if pbp.empty:
        return False, "final; play-by-play not published yet", True
    if sorted([int(pbp.scoreHome.iloc[-1]), int(pbp.scoreAway.iloc[-1])]) != sorted(teams.points.astype(int)):
        return False, "final; play-by-play not at the final score yet", True
    return True, f"final: {int(pbp.scoreAway.iloc[-1])}-{int(pbp.scoreHome.iloc[-1])} (away-home)", True


def run(*args: str) -> tuple[int, str]:
    """Run one pipeline step: its output goes to the log; returns the exit code and the line that says why it
    stopped (the last line it printed, or the error when it crashed)."""
    done = subprocess.run(args, env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True)
    for text in (done.stdout, done.stderr):
        if text.strip():
            print(text.rstrip(), flush=True)
    lines = [l for l in (done.stdout if done.returncode in (0, NOT_READY) else done.stderr + done.stdout).splitlines() if l.strip()]
    return done.returncode, lines[-1] if lines else ""


def due(started: float, final_at: float, now: float, stage: str) -> int | None:
    """The notice mark (minutes after Final) this process should raise now: the first mark that fell between
    this process's start and now. A restarted process begins after the mark it reported, so each mark is
    raised once without a state file."""
    for mark in MARKS[stage]:
        if started < final_at + mark * 60 <= now:
            return mark
    return None


def notice(text: str, game_id: str, final_at: float) -> None:
    """Print what the run is waiting on and the command that resumes it, then exit STILL_WAITING."""
    log(text)
    log(f"restart: PYTHONPATH=. {PY} postgame-recaps/pipeline/postgame_recap.py {game_id} {int(final_at)}")
    sys.exit(STILL_WAITING)


def caption(r: dict) -> str:
    """The post caption from the verified numbers: the result line, then the standing hashtags."""
    us, them = r["chi"], r["opp"]
    hi, lo = max(us["score"], them["score"]), min(us["score"], them["score"])
    verb = "beat" if us["score"] > them["score"] else "fell to"
    where = "the United Center" if r.get("arena") == "United Center" else r.get("arena") or them["city"]
    return (f"The Chicago Bulls {verb} the {them['city']} {them['team']} {hi}-{lo} at {where}.\n\n"
            f"{REVISION_NOTE}\n\n{HASHTAGS}\n")


def draw(game_id: str, data: Path, out: Path) -> int:
    """Shot chart, pages and PNG export for one game; returns the first failing exit code, or 0."""
    # The shot chart reads league shots from <repo>/cache/shot_charts/. In the primary checkout that is the shared
    # cache itself; in a worktree, link the shared cache, or only its shot_charts when tests have already made a
    # real cache/ there (seen 2026-10-08), and remove only the link afterwards.
    shared, local = shared_cache(), REPO / "cache"
    link = local if not local.is_dir() or local.is_symlink() else local / "shot_charts"
    target = shared if link.name == "cache" else shared / "shot_charts"
    if link.is_symlink() and not link.exists():
        link.unlink()  # a dangling link left by an interrupted run
    made = not link.exists() and target != link  # in the primary checkout the link would point at itself
    if made:
        link.symlink_to(target)
    try:
        code, _ = run(PY, str(HERE / "zones_share.py"), str(data), str(out / "zones.png"), "13", "11", "33")
    finally:
        if made and link.is_symlink():
            link.unlink()  # the link only, never the shared cache
    for step in ([] if code else [[str(HERE / "build_mockup.py"), game_id], [str(HERE / "export_slides.py"), game_id, "--icloud"]]):
        code = code or run(PY, *step)[0]
    return code


def snapshot(data: Path, out: Path) -> str:
    """Keep the feeds these slides were built from, and the numbers they drew, in <game>/as-posted/, once:
    recheck.py compares them with NBA.com later, so a rebuild must not move them. Returns the log line."""
    posted = data / "as-posted"
    if posted.exists():
        return f"as-posted/ kept from the first build; this build's feeds are in {data.name}/ only"
    posted.mkdir()
    kept = [name for name in SNAPSHOT if (data / name).exists()]
    for name in kept:
        shutil.copy2(data / name, posted / name)
    shutil.copy2(out / "recap.json", posted / "recap.json")
    return f"as-posted/ written: {', '.join(kept)}, recap.json"


def main(arg: str, check: bool = False, since: float | None = None) -> None:
    try:  # hold the Mac awake for as long as this process lives (idle sleep, and system sleep on power)
        subprocess.Popen(["caffeinate", "-is", "-w", str(os.getpid())])
    except OSError:
        pass
    if arg == "--today":
        game = tonight()
        if game is None:
            log("no Bulls game today")
            return
        game_id, tip, matchup = game
    else:
        game_id, tip, matchup = arg, None, ""
    started = time.time()
    deadline = since + 3 * 3600 if since else (tip.timestamp() if tip else started) + 5 * 3600
    log(f"game {game_id}" + (f" ({matchup}), tip-off {tip.astimezone():%-I:%M %p}" if tip else "")
        + (f"; restarted, Final first seen {time.strftime('%H:%M', time.localtime(since))}" if since else ""))

    final_at = since  # the first poll on which NBA.com showed Final, which the timing line counts from
    while True:  # 1. wait for the final
        ok, why, shown_final = final(game_id)
        log(why)
        if check:
            sys.exit(0 if ok else 1)
        if shown_final and final_at is None:
            final_at = time.time()
        if ok:
            break
        if time.time() > deadline:
            sys.exit("gave up: the game was not final five hours after tip-off")
        time.sleep(POLL)
    if final_at - started > POLL / 2 and due(started, final_at, time.time(), "publishing") == 0:
        # Seen go Final while watching: say so. A run started after the buzzer skips this, the user knows.
        notice(f"FINAL SEEN: {why}; waiting for NBA.com to publish every feed (12 to 35 minutes so far this season)",
               game_id, final_at)

    strikes = 0
    while True:  # 2. pull and compute until every feed is published and every check passes
        code, why = run(PY, str(HERE / "pull_game.py"), game_id)
        stage = "publishing"  # what the wait is: NBA.com publishing, or a check on published feeds
        if code == 0:
            code, why = run(PY, str(HERE / "recap_data.py"), game_id)
            stage = "check"
        if code == 0:
            break
        if code == NOT_READY:
            strikes = 0
        else:
            strikes += 1
            if strikes >= STRIKES:
                sys.exit(f"stopped: a pipeline step failed {STRIKES} times in a row (exit {code}); see the log above")
            log(f"a step failed (exit {code}), {strikes} of {STRIKES} strikes; pulling again")
        if time.time() > deadline:
            sys.exit("gave up: data still not complete and consistent three hours after Final")
        minutes = (time.time() - final_at) / 60
        if due(started, final_at, time.time(), stage) is not None:
            what = ("NBA.com has not published every slide feed" if stage == "publishing"
                    else "every slide feed is published but a check is failing (NBA.com's feed, or our check)")
            notice(f"STILL WAITING: {minutes:.0f} min after Final; {what}: {why}", game_id, final_at)
        wait = POLL if minutes < 60 else SLOW_POLL
        log(f"not ready, pulling again in {wait} s")
        time.sleep(wait)
    ready_at = time.time()

    data = game_dir(game_id)  # 3. draw, build, export
    out = OUTPUT / game_id
    with open(out.parent / ".build.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # one build at a time: the cache link and the page file are shared
        code = draw(game_id, data, out)
    if code:
        sys.exit(f"stopped: drawing or export failed (exit {code})")
    recap = json.loads((out / "recap.json").read_text())
    (out / "caption.txt").write_text(caption(recap))
    log(snapshot(data, out))
    slides = sorted((out / "slides").glob("*.png"))
    log(f"done: {recap['chi']['tri']} {recap['chi']['score']}, {recap['opp']['tri']} {recap['opp']['score']}; "
        f"{len(slides)} slides; game flow vs NBA.com: {recap['flow'].get('nba_check')}")
    log(f"timing: NBA.com showed Final at {time.strftime('%H:%M', time.localtime(final_at))}; data ready "
        f"{(ready_at - final_at) / 60:.1f} min later, slides {(time.time() - final_at) / 60:.1f} min later "
        "(up to 1.5 min more, the polling interval)")
    log("optional feeds missing (back-pocket pages only): " + ("; ".join(recap["missing"]) or "none"))
    log(f"caption: {out / 'caption.txt'}")
    for line in deliver(slides):  # 4. onto the phone
        log(f"delivery: {line}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--check"]
    main(args[0], check="--check" in sys.argv, since=float(args[1]) if len(args) > 1 else None)
