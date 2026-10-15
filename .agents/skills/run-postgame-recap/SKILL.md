---
name: run-postgame-recap
description: Build, check and deliver tonight's Bulls postgame recap carousel ("run postgame recap"); waits for NBA.com, reviews every slide before it ships; posts to Instagram only when the user says yes for that game.
---

# Run Postgame Recap

The user starts this with a message, from the desktop app or from the phone through Remote Control, in a
session opened on the `bulls-analytics` folder, usually as the game is about to end. Run every command from
the repo root. The script waits, checks and draws; **you are the reviewer**: nothing reaches the phone until
you have looked at every slide and are satisfied (the user's choice, Oct 10: judgment before anything ships,
not only the script's checks). The run ends when reviewed slides are in the Photos album and iCloud Drive, and
the user has a notification (your push is the only alert), the caption and what you checked. Post to
Instagram only through step 5, when the user has said yes for this game; never schedule, draft or touch X;
never commit or push: the game's new folder in `postgame-recaps/seasons/`
stays uncommitted until the user approves a batch commit. Method and failure reasons:
`postgame-recaps/README.md`, "Running a recap".

Your review is the most important part of this run, in the user's words the reason an agent is in the
workflow. On the first dry run (MIN at MIA, Oct 10) every check passed while NBA.com's shot feed held 72 of 87
attempts and the shot chart showed a partial game; only the review caught it. Be ready for anything: look at
every number with fresh eyes, cross-check it against the box score, fix or hold it, and say what you found.

The user wants to hear from the run often and wants each update to say something new: what landed, what you
checked, what you found. "Still waiting" with nothing else is the update to avoid.

**The user's picks.** Notes sent while watching ("Miller should be MVP", "no closer award tonight", "label the
buzzer-beater") go into `postgame-recaps/seasons/<season>/<id>/picks.json` (format: `postgame-recaps/README.md`, "Running a recap"). Write
it once NBA.com's play-by-play is on disk: find each moment's own row and use its `actionNumber`, confirm the
description matches what the user saw (scorer, period, clock, score), and keep labels short. A note
recalled from the couch can be off (Oct 14: "3 or 9 threes in a row" was 9 straight Bulls points, three
threes): count it in the play-by-play, say what you found, and label what the data shows. A notable the user
asks for goes in `notables` when `PICKED_NOTABLES` has it; otherwise say so rather than typing a figure. The build reads it on
every pull; after delivery, rerun `postgame-recaps/pipeline/recap_data.py`, `postgame-recaps/pipeline/build_mockup.py` and `postgame-recaps/pipeline/export_slides.py` to apply a late pick.

1. **Recheck the previous game.** If a `postgame-recaps/seasons/*/*/as-posted/` folder exists for an earlier
   game, run `postgame-recaps/pipeline/recheck.py` on the most recent one. Exit 1 lists numbers NBA.com
   corrected since posting: report them; do not rebuild or change the post. A traceback (a network error)
   is not a correction: say the recheck could not run, and continue.
   ```
   PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/recheck.py <game_id>
   ```
   If that game's page in the posts database is not Posted yet, look for the post on the @chicagobullsdata
   profile (read-only); when it is live, set Posted and add its link (step 6).
   Then read tonight's game page in the posts database (step 6 says how to find it): notes left there for this
   run (things to watch, picks decided ahead) are part of tonight's job; act on them and report on each.
2. **Build, and watch it.** Start the script with Bash `run_in_background` (use the game ID instead of
   `--today` if the user gave one). You are re-invoked when it exits; don't poll. It waits for Final, then
   pulls again every 90 s until every check passes (12 to 35 minutes after Final so far), exports and
   measures the slides and writes `output/postgame-recap/<id>/caption.txt`. It does not deliver. "no Bulls
   game today" ends the run.
   ```
   PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/postgame_recap.py --today
   ```
   In your first message after starting the build, ask once: "Want me to post it on Instagram when it's
   reviewed? If so, send your caption (or I use the build's) and any collaborator." Asked early, the answer is
   in before delivery even if the user leaves at the buzzer. No answer, or no, means deliver only.

   Right after starting each build (the first one and every restart), start a Monitor on that build's output
   file with the maximum timeout; if it expires while the build runs, re-arm it with `--resume` added, which
   skips the lines already reported:
   ```
   python3 postgame-recaps/pipeline/watch_build.py <the build's output file>
   ```
   It prints a line when the period changes, at Final, when the list of unpublished feeds changes, when a
   check fails, at each build step and at the end, a heartbeat every 3 minutes after Final without one, and
   a warning when the build has logged nothing for 10 minutes. It exits when its build exits or restarts; if
   one is still running when the build has exited, stop it with TaskStop.

   **Turn each watcher line into a real update.** Post it to chat as one or two plain lines and send it as a
   PushNotification too (the user's choice, Oct 9: a buzz on every update while the series is new):
   - **Box score in.** At the first "waiting on" or "every slide feed is published" line after Final (the
     build has pulled by then; on a restarted build, at once), run the early look and report the result, that the box score adds up (or
     that it does not: the build will hold on it too), the Bulls leaders and anything that changes the
     layout: overtime, more players than usual, a long name. Example: "Final 110-102. Box score in and adds
     up. Buzelis 24, Giddey 11 ast. Waiting on four factors and shots (normal, 12 to 35 min so far)."
     ```
     PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/early_look.py <game_id>
     ```
   - **Early pages.** An `early:` line means the first wave of feeds is in and the pages it completes (cover,
     final score, box score, season pages; numbered as in the final set) are drawn in
     `output/postgame-recap/early/<id>/slides/`, while team stats, shot chart and game breakdown wait on the
     second wave. Review them now exactly as in step 3 (numbers, references, by eye), fix what needs fixing
     (a template fix: rerun the three scripts named under "The user.s picks" with `RECAP_EARLY=1`), then
     send them with SendUserFile and a push ("Bulls recap: early pages ready, still waiting on <feeds>") so the
     user reviews them too and can add picks. Early pages are never delivered; the final build draws every page
     again. In step 3, the early pages need only a check that they match what was reviewed; give the rest the
     full review.
   - **Heartbeats and feed changes.** Say what has landed since the last update, what is still missing and
     whether the wait is normal: minutes after Final against the 12 to 35 seen so far. When the watcher
     line alone is thin, read the last 15 lines of the build output for more.
   - **Stall warning.** Read the last 15 lines of the build output and check that the background task is
     still running. A build stuck in a step (no new line, still running) is stopped with TaskStop and
     started again with the last `restart:` command it printed, or with the game ID alone if it printed
     none (its timing line then counts from the restart); every feed is on disk, so nothing is lost. Tell
     the user what you saw and did.

   The script exits in four ways:
   - A `FINAL SEEN` or `STILL WAITING` line followed by `restart: ...` (exit 76) is a notice, not a failure.
     Post the notice and push it (every notice: the post should be out within 30 minutes of the buzzer),
     then start the printed restart command in the background at once (it carries the game ID and the time
     Final was first seen; every feed is on disk, so nothing is lost). Pushes read like "Bulls recap still
     waiting, 21 min after Final: NBA.com has not published: four factors, misc". Notices come at Final,
     then 20, 30, 45, 60, 90 and 120 minutes after it (from 10 minutes when a check is failing).
     When a check is failing, quote the reason line (it names the feed and the row), look at that feed on
     disk yourself and say which it looks like: a feed NBA.com never corrects (DEN at UTA, Oct 6) or our
     own check. The user can reply "stop": end the background task with TaskStop, report what it was
     waiting on, and do not restart it.
   - A "stopped" or "gave up" line means no slides: report it in one sentence, keep all data, and stop.
   - A `review:` line: the slides are exported and nothing is on the phone yet. Continue with step 3.

   If the user asks how the run is going between updates, read the last 15 lines of the build output and
   answer in one line: the phase, minutes since Final, and either "waiting for NBA.com to publish X
   (normal)" or "a check is failing: <reason>".
3. **Review every slide before it ships.** Tell the user in one line that the slides are built and you are
   reviewing them. Then:
   - **Read the build log's checks.** The `serif:` line names Georgia Pro Condensed Bold (otherwise say so,
     and continue). Each `repaired:` line (45 minutes after Final, the build replaces what NBA.com left
     incomplete or leaves the page out; README, "Running a recap") goes into the delivery message. Each `layout:` line (also in `output/postgame-recap/<id>/layout.json`) is "ok", "LOOK"
     (unusual for the format: an empty band taller than any saved game's, or a page crowding its footer;
     judge it by eye) or "FIX" (text overlapping text, or past the margins: never ship it).
   - **Weigh the ESPN check.** The `espn check:` line says how many values matched ESPN's copy of the game;
     each `espn differs:` line above it is one disagreement. NBA.com stays the source (the user's rule, Oct 11),
     so a difference is a flag for your judgment, not an automatic fix. For each one that reaches a slide, look
     at both sides and the feeds on disk: NBA.com incomplete or behind (missing shots, a broken running score)
     is a hold, as below; a convention or a scorer's call ESPN reads differently ships with NBA.com's number and
     a line in the delivery message. "could not run" means ESPN had nothing usable: say so, and run
     `postgame-recaps/pipeline/espn_check.py <game_id>` again before delivering if there is time.
   - **Check the numbers.** The score, line score and slide 2's four tiles match
     `output/postgame-recap/<id>/recap.json`, which the script has checked against NBA.com. Awards, leaders
     and notables hold no surprise; if a pick looks wrong, check its Game Score in that recap.json. No long
     flat stretch in the step margin line (minutes with no score logged), no red play-by-play warning.
     Every count a page draws from a feed other than the box score, play-by-play and summary must match the
     box score (MIN at MIA, Oct 10: NBA.com's shot feed held 72 of 87 attempts and the shot chart printed a
     partial game; the checks now catch that one, the review is there for the next). A stat printed on two
     pages agrees, or you know why not (Oct 14: 22 turnovers on team stats, 21 on the box score; NBA.com's
     total adds a team turnover). Anything that will look surprising to a fan (a big minus with a big scoring night, a quiet star),
     verify yourself against the feeds on disk (players.csv and teams.csv in the game's folder) and keep a
     one-line explanation for the delivery message: the user should not have to wonder whether a number is
     right.
   - **Look at every page beside its reference.** Read each PNG in `output/postgame-recap/<id>/slides/` and
     the reference page with the same name in `postgame-recaps/assets/` (`2026-10-10-v19-gsw-<page>.png`, the cover `2026-10-14-v20-gsw-01-cover.png`;
     for the final-score page, the reference with the same number of notables: `-det-` none, `-mia-` one,
     `-gsw-` three). Judge it as a designer would: spacing even and consistent with the reference, nothing
     touching, clipped or crowding the footer, no empty hole the reference does not have, labels clear of
     lines and dots, headshots and logos present, and the page reading as the same series.
   - **Decide:** ship as is, fix the layout (below), or hold a number (below).

   **Fixing the layout.** You may fix it yourself; you need no approval. Make the smallest change in
   `postgame-recaps/pipeline/recap_template.html` that makes this page right and stays right for other
   games: a rule ("when there are notables, ...") rather than a nudge for tonight's numbers. Then rebuild
   without pulling again:
   ```
   PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/build_mockup.py <game_id>
   PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/export_slides.py <game_id>
   ```
   and review the changed pages again (their `layout:` lines and by eye). Leave the template change
   uncommitted: it is checked against the saved test games the next day and then kept as the template or
   reverted, so the series does not drift one game at a time. If a fix is not working within about ten
   minutes, ship without it only when the problem is cosmetic, and say so in the delivery message; never
   ship text that hides a number.

   **Holding a number.** Never type or edit a number in the template or on a slide: every published figure
   comes from `postgame-recaps/pipeline/recap_data.py`, traceable to NBA.com. Push the user at once
   ("Bulls recap held: <what looks wrong>; investigating"), then find the cause:
   - NBA.com is still revising the feed: start the build again with the game ID (step 2's command with
     `<game_id>` for `--today`; it pulls, checks and draws everything again in a few minutes), then review
     again;
   - NBA.com published something wrong and has not corrected it: keep holding and tell the user what is
     wrong and where; they decide whether to post without the page or wait;
   - our own code is wrong: fix it in `postgame-recaps/pipeline/recap_data.py`, run
     `./run_tests.sh tests/test_postgame_recap.py -q`, start the build again with the game ID, check the
     number against the feed by hand, and tell the user what was wrong. The code change stays uncommitted
     for review, like a template fix.
4. **Deliver**, once you are satisfied:
   ```
   PYTHONPATH=. /Users/meltangonan/projects/bulls-analytics/venv/bin/python postgame-recaps/pipeline/deliver.py <game_id>
   ```
   The `delivery:` lines say the slides went to iCloud Drive, hold image data only, and that Photos stored
   them unchanged, and that `as-posted/` was written; report anything else. Send a PushNotification ("Bulls
   recap ready: <score>. <n> slides in Photos, Bulls recaps"), then the slides with SendUserFile (proactive)
   and a short message:
   - the caption from `output/postgame-recap/<id>/caption.txt` in full (add any line the user asked for; no
     em dashes);
   - **what you checked**, in three or four short lines: the box score adds up and the score and line score
     match NBA.com; the ESPN check (all agree, or each difference and what you decided); the game-flow check; the layout ("all pages ok" or what you fixed and why); any number
     that looks surprising, with its explanation;
   - corrections from step 1, and, when the user posts it themselves, the reminder: choose the 3:4
     "Original" crop.

   If you must deliver again after a fix, iCloud Drive's copy is replaced, but the Photos album keeps the
   earlier slides too: tell the user which to delete.
5. **Post, only if the user said yes for this game** (the user's choice, Oct 14: an option, never the
   default). Their yes covers this one post, including the Share click; anything new after it (a changed
   slide, a different caption, a held number) needs their yes again. Posting adds no review of its own:
   step 3 is the gate, and you post the exact files you delivered. While NBA.com is still publishing, get
   Claude in Chrome ready: open instagram.com in a new tab and confirm it is signed in as `chicagobullsdata`.
   Then:
   - Create › Post; `find` the hidden file input in the dialog and `file_upload` every PNG in
     `output/postgame-recap/<id>/slides/` in one call, in page order (about 1.6 MB, under the 10 MB limit).
   - Crop: the bottom-left button › **Original** (3:4; the default 1:1 cuts the page). Next; filter
     **Original**. Next.
   - Caption: the user's text exactly, or `output/postgame-recap/<game_id>/caption.txt`. Before typing, check its numbers against
     recap.json and that it has no em dashes. Read it back from the field and compare its length with yours.
   - Collaborator: search the exact handle and pick the row whose handle matches character for character
     (lookalikes such as `chicagobulls_central` sit just below), then Done.
   - **Add AI label stays off** and Schedule stays off. Share, wait for "Your post has been shared".
   - Verify the live post: the profile grid (it lands after the pinned posts), the caption text, `?img_index=<n>`
     shows the last slide, the collaborator line. Push "Bulls recap posted: <score>, <link>", close your tab.
   If anything in the dialog looks off, stop before Share and tell the user; never retry a Share.
6. **Log it** on tonight's game page in the posts database (https://app.notion.com/p/3a6e1c13abe6809ab16bfe33edb233cf;
   one pre-made page per game, Tags `recap`, found by its Date), in the same shape as the earlier game pages: game
   and game ID, result, minutes from Final to ready data (the script's `timing:` line, counted from when NBA.com
   first showed Final), slides and delivery, posted (the link when you posted it), then notes: what you fixed or
   held, or "review clean". Set Status to Posted only when the post is live: at once when you posted it; when the
   user posts it, once they say so or when step 1 of the next run finds it on the profile (read-only), adding the
   link then. A template or code fix made tonight goes under open work on the Notion page "Game recaps"
   (https://app.notion.com/p/3a7e1c13abe680629bb0df2d6f77f623) as a follow-up: check it against the saved test
   games, then keep or revert. Edit only those two pages.
