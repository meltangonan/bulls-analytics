---
name: run-postgame-recap
description: Build, check and deliver tonight's Bulls postgame recap carousel ("run postgame recap"); waits for NBA.com, never posts.
---

# Run Postgame Recap

The user starts this with a message, from the desktop app or from the phone through Remote Control, in a
session opened on the `bulls-analytics` folder. Run every command from the repo root. The run ends when
checked slides are in the Photos album and iCloud Drive, and the user has a notification (your push is the
only alert) and the caption. Never post, schedule or draft on Instagram or X; never commit or push: the game's new folder in
`postgame-recaps/seasons/` stays uncommitted until the user approves a batch commit. Method and failure
reasons: `postgame-recaps/README.md`, "Running a recap".

1. **Recheck the previous game.** If a `postgame-recaps/seasons/*/*/as-posted/` folder exists for an earlier
   game, run `postgame-recaps/pipeline/recheck.py` on the most recent one. Exit 1 lists numbers NBA.com
   corrected since posting: report them; do not rebuild or change the post. A traceback (a network error)
   is not a correction: say the recheck could not run, and continue.
   ```
   PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/recheck.py <game_id>
   ```
2. **Build.** Start the script with Bash `run_in_background` (use the game ID instead of `--today` if the user
   gave one). You are re-invoked when it exits; don't poll. It waits for Final, then pulls again every 90 s
   until every check passes (12 to 35 minutes after Final so far), exports the slides, copies them to iCloud
   Drive › Bulls recaps, writes `output/postgame-recap/<id>/caption.txt`, keeps an `as-posted/` copy of the
   feeds and adds the slides to the Photos album (it sends no text message). "no Bulls game today" ends the
   run.
   ```
   PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/postgame_recap.py --today
   ```
   **Watch it.** Right after starting each build (the first one and every restart), start a Monitor on that
   build's output file with the maximum timeout; if it expires while the build runs, re-arm it with `--resume`
   added, which skips the lines already reported:
   ```
   python3 postgame-recaps/pipeline/watch_build.py <the build's output file>
   ```
   It prints a line when the period changes, at Final, when the list of unpublished feeds changes, when a
   check fails, at each build step and at done, plus a heartbeat every 5 minutes after Final without one.
   Post each line to chat as a one-line update in plain words (the user wants frequent updates); no
   PushNotification for these, only for the notices below. It exits when its build exits or restarts; if one
   is still running when the build has exited, stop it with TaskStop.
   The script exits in three ways:
   - A `FINAL SEEN` or `STILL WAITING` line followed by `restart: ...` (exit 76) is a notice, not a failure.
     Post the notice in one chat line and send it as a PushNotification (every notice: the user wants to
     hear from the run, and the post should be out within 30 minutes of the buzzer), then start the printed
     restart command in the background at once (it carries the game ID and the time Final was first seen;
     every feed is on disk, so nothing is lost). Pushes read like "Bulls game final, 110-102; waiting for
     NBA.com to publish (12 to 35 min so far)" and "Bulls recap still waiting, 21 min after Final: NBA.com has
     not published: four factors, misc". Notices come at Final, then 20, 30, 45, 60, 90 and 120 minutes
     after it (from 10 minutes when a check is failing).
     When a check is failing, quote the reason line (it names the feed and the row). A feed NBA.com never
     corrects (DEN at UTA, Oct 6) looks the same as a wrong check, so say which it looks like and that the
     user can reply "stop". If the user says stop, end the background task with TaskStop and report what
     it was waiting on; do not restart it.
   - A "stopped" or "gave up" line means no slides: report it in one sentence, keep all data, and stop.
   - A "done:" line: continue with step 3.
   If the user asks how the run is going between updates, read the last 15 lines of the background task's output and answer
   in one line: the phase, minutes since Final, and either "waiting for NBA.com to publish X (normal)" or
   "a check is failing: <reason>".
3. **Check every slide** (`output/postgame-recap/<id>/slides/`, Read each PNG):
   - the export's `serif:` line names Georgia Pro Condensed Bold (otherwise say so, and continue);
   - the `delivery:` lines say the slides hold image data only and Photos stored them unchanged; report
     anything else;
   - the score, line score and slide 2's four tiles match `output/postgame-recap/<id>/recap.json`,
     which the script has checked against NBA.com;
   - no long flat stretch in the step margin line (minutes with no score logged), no red play-by-play warning;
   - no text overlaps or runs off a page; headshots and logos present;
   - awards and leaders hold no surprise; if a pick looks wrong, check its Game Score in that recap.json.
4. **Deliver.** Send a PushNotification ("Bulls recap ready: <score>. <n> slides in Photos, Bulls recaps"),
   then the slides with SendUserFile (proactive) and a short message: the caption from
   `output/postgame-recap/<id>/caption.txt` in full (add any line the user asked for; no em dashes),
   anything that looked off or "all checks passed", corrections from step 1, and the reminders: slide 1
   (cover) is optional; choose the 3:4 "Original" crop.
5. **Log it** as one row in the Game log on the Notion page "Game recaps"
   (https://app.notion.com/p/3a7e1c13abe680629bb0df2d6f77f623): result, minutes from Final to ready data
   (the script's `timing:` line, counted from when NBA.com first showed Final), delivery, Posted left blank,
   and anything that went wrong. Edit only that page.
