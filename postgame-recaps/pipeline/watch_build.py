"""Turn a running postgame_recap.py log into short status lines for the person waiting on the recap.

    python3 postgame-recaps/pipeline/watch_build.py <the build's output file> [--resume]

Claude's Monitor tool runs this beside the build: each line it prints wakes Claude to post an update. It
prints when the run's state changes (the period, Final, which feeds NBA.com has still not published, a
failing check, each build step, done or stopped) and, after Final, a heartbeat whenever five minutes pass
without an update. Repeated "still waiting" polls print nothing. It exits when the build exits or prints
its restart command, so a restarted build needs a new watcher on its new output file. --resume (a watcher
re-armed on the same build) reads what is already logged without printing it, then prints what follows.
"""
import re
import sys
import time
from datetime import datetime, timedelta

HEARTBEAT = 5 * 60  # seconds after Final without an update before a heartbeat
STAMP = re.compile(r"^(\d\d:\d\d):\d\d (.*)$")
STATUS = re.compile(r"^(not final yet|final|summary not published)")  # final() in postgame_recap.py
FIRST_SEEN = re.compile(r"Final first seen (\d\d:\d\d)")
STEPS = [  # build lines worth an update: (pattern, plain text, or None to pass the line through)
    (re.compile(r"^game \d+"), None),
    (re.compile(r"^(FINAL SEEN|STILL WAITING)"), None),
    (re.compile(r"^pulled \d+"), "every slide feed is published; running the checks"),
    (re.compile(r"^\d{10}: "), None),  # recap_data.py's summary: score, flow check, awards, skipped pages
    (re.compile(r"^Saved .*zones\.png"), "checks passed; shot chart drawn"),
    (re.compile(r"^wrote .*mockup\.html"), "slides laid out; exporting"),
    (re.compile(r"^copied to "), "slides exported and copied to iCloud Drive"),
    (re.compile(r"^(done|timing|delivery|a step failed|gave up|stopped|no Bulls game today)"), None),
    (re.compile(r"Traceback"), "a step crashed (Traceback in the log)"),
]
END = re.compile(r"^(restart: |gave up|stopped|no Bulls game today)|^\[exited with code")


class Watcher:
    def __init__(self):
        self.status = self.waiting = self.previous = None
        self.final_at = None  # wall-clock time Final was first seen, for "N min after Final"
        self.last_update = time.time()
        self.ended = False

    def minutes(self, now: float) -> int:
        return round((now - self.final_at) / 60)

    def feed(self, raw: str, now: float) -> list[str]:
        """The updates one log line earns."""
        line = raw.rstrip()
        stamp, text = (STAMP.match(line).groups() if STAMP.match(line) else (None, line))
        at = self.clock(stamp, now) if stamp else now  # the log's own time, so a replay reads the same
        out = []
        if FIRST_SEEN.search(text):
            self.final_at = self.clock(FIRST_SEEN.search(text).group(1), now)
        if STATUS.match(text):
            if text.startswith("final") and self.final_at is None:
                self.final_at = at
            if text != self.status:
                out.append(text)
            self.status = text
        elif text.startswith("not ready, pulling again"):
            reason = self.previous or "unknown"  # the line before names what is missing or failing
            if reason != self.waiting:
                out.append(f"{self.minutes(at)} min after Final; waiting on: {reason}")
            self.waiting = reason
        else:
            for pattern, plain in STEPS:
                if pattern.search(text):
                    out.append(plain or text)
                    break
        if text and not text.startswith("missing or empty"):
            self.previous = text
        if END.search(text):
            self.ended = True
        if out:
            self.last_update = now
        return out

    def tick(self, now: float) -> list[str]:
        """A heartbeat when Final has passed and five minutes went by without an update."""
        if self.final_at is None or now - self.last_update < HEARTBEAT:
            return []
        self.last_update = now
        return [f"{self.minutes(now)} min after Final; still waiting on: {self.waiting or 'NBA.com'}"]

    @staticmethod
    def clock(hhmm: str, now: float) -> float:
        """Today's (or, past midnight, yesterday's) time for an HH:MM log stamp."""
        today = datetime.fromtimestamp(now)
        at = datetime.combine(today.date(), datetime.strptime(hhmm, "%H:%M").time())
        return (at - timedelta(days=1) if at > today + timedelta(minutes=1) else at).timestamp()


def main(path: str, resume: bool = False) -> None:
    w, partial = Watcher(), ""
    with open(path) as log:
        if resume:
            for line in log.readlines():
                w.feed(line, time.time())
            w.last_update = time.time()
        while not w.ended:
            partial += log.readline()
            line, complete = partial, partial.endswith("\n")  # a line still being written waits for its end
            if complete:
                partial = ""
            for update in (w.feed(line, time.time()) if complete else w.tick(time.time())):
                print(update, flush=True)
            if not complete:
                time.sleep(1)


if __name__ == "__main__":
    main(sys.argv[1], resume="--resume" in sys.argv)
