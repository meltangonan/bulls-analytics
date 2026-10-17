# Postgame recaps

A carousel of 1080x1440 pages after every Bulls game, built from NBA.com data, checked, and delivered to the
phone for posting on @chicagobullsdata (or posted by Claude when the user says yes for that game; the
`run-postgame-recap` skill, step 5). Live since the 2026-27 preseason opener (2026-10-07). Notion's "Game
recaps" page owns the format decisions, open work and lessons; each game's record (result, timing, post link,
notes, Status) is its own pre-made page in the posts database, written by the skill's step 6 and listed on the
"Game recaps" sub-page "Game log" (since 2026-10-15). This file owns the method.

```text
postgame-recaps/
  pipeline/                 the code; paths.py says where everything lives
  baselines/league-2025-26/ league averages the game breakdown is measured against
  seasons/<season>/<id>/    each Bulls game's NBA.com feeds, sources.json, and as-posted/ (what the slides used)
  stress-tests/<id>/        saved test games: 2025-26 Bulls games and dry runs featuring other teams
  logos/, portraits/        NBA.com images (portraits are downloaded again when missing or 12 hours old, never committed)
  assets/                   decision-bearing slide versions from the format's design (Oct 3 to 14, 2026; v14 is the Oct 9 template; v19 is the Oct 10 template, with v15 and v17 its rejected options; v20 is the Oct 14 cover)
output/postgame-recap/<id>/ recap.json, zones.png, slides/, layout.json, caption.txt (scratch, not committed)
```

## Running a recap

One command, from the repo root (a worktree uses the primary checkout's venv); the `run-postgame-recap` skill
wraps it with Claude's updates, Claude's review of every slide, the delivery and the Notion log:

```bash
PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/postgame_recap.py --today
```

Beside it, the skill runs `pipeline/watch_build.py <build output file>` under Claude's Monitor tool: it turns
the log into one line per change (period, Final, the feeds still unpublished, a failing check, each build step),
a heartbeat every 3 minutes after Final and a warning if the build logs nothing for 10 minutes (it logs every
poll, so that means stuck), so Claude can update the user without reading every poll. Once the box score is on
disk, `pipeline/early_look.py <game_id>` gives Claude the result, whether the player rows add up to the team
totals, the leaders and what changes the layout (overtime, players used, longest name), so the updates during
the wait say something.

`--today` finds tonight's Bulls game in NBA.com's schedule (or pass a game ID) and exits quietly on days
without one (before 6 am, last night's game). It checks every 90 seconds until the game is Final, the box
score is filled and the play-by-play ends on the final score, holding the Mac awake (`caffeinate`) meanwhile;
then it pulls every feed and computes every number, and while either step exits NOT_READY (75) it logs the
reason, waits 90 seconds (5 minutes from an hour after Final, so a long wait does not hammer stats.nba.com)
and pulls again. Any other failure three times in a row stops the run; once or twice, it pulls again, because
a half-published feed can crash a step. Then, one build at a time (a lock), it draws the shot chart (linking the shared cache when run from a
worktree, removing only the link), builds the pages, exports and measures the PNGs, writes `caption.txt` and
stops: its last line, `review:`, prints the delivery command. Nothing reaches the phone until Claude has
looked at every page beside its reference and fixed what needed fixing (Oct 10: the user wants judgment before
anything ships, not only the script's checks). The measurement (`layout.json` and one `layout:` line per page)
reports text overlapping text or past the margins (FIX) and an unusually tall empty band or a page crowding
its footer (LOOK); the thresholds are set so all 16 saved test games read "ok". The references are the v19
pages in `assets/` (`2026-10-10-v19-gsw-*`, the cover since 2026-10-14 `2026-10-14-v20-gsw-01-cover`, with three notables and overtime, plus the final-score page with
none, `-det-`, and one, `-mia-`).

Early pages (since 2026-10-12): NBA.com publishes in two waves. The box score, play-by-play, line score and summary
come first; four factors, misc and the Bulls shot feed can follow minutes or half an hour later. Once only that
second wave is missing, `postgame_recap.py` runs the build once with `RECAP_EARLY=1`: every first-wave check
(score, play-by-play, game logs, game flow against NBA.com) and the pages they complete (cover, final score, box
score, season pages), drawn in `output/postgame-recap/early/<id>/` with their final carousel numbers, and logs
an `early:` line. Team stats, shot chart and game breakdown stay pending; the cover's contents still list them.
Claude reviews the early pages and sends them to the user while the rest publish. They are never delivered: the
final build draws every page again, and only it reaches the phone.

The user's calls while watching go in `seasons/<season>/<id>/picks.json` (optional; added 2026-10-11), which
`recap_data.py` reads on every build:

```json
{"mvp": 1631159, "drop_awards": ["#closer"],
 "moments": [{"action": 376, "label": "Wilson buzzer-beater"}, {"action": 466, "label": "DEN: Johnson go-ahead 3"}]}
```

`mvp` is a personId and replaces the Game Score pick; `drop_awards` leaves out awards that qualified (a weak one,
or a player showing up too often); each moment names a scoring play by its play-by-play `actionNumber`, so the dot's
time and margin come from NBA.com and only the label is typed. The template places a moment's label on its own
team's side of zero, clear of the margin line and the other labels. `notables` names callouts from
`PICKED_NOTABLES` in `recap_data.py` (`"assist_rate"`: "Bulls: x assists on y field goals" from the Bulls box score;
`"dunks"`: "Bulls: x team dunks, led by " and the top three dunkers, from the play-by-play's made dunks); they
lead the final-score page's notables, three at most; a pick that also qualifies (Notables, below) takes the qualifier's
wording. These are calls, not numbers.

Then Claude delivers (`PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/deliver.py <game_id>`):
- the slides are copied to iCloud Drive › Bulls recaps › `<date> <matchup>` (replacing an earlier copy);
- every slide keeps image data only, so Instagram has nothing to read as AI-made (the user's rule: its AI
  label must never appear); anything else is removed and logged;
- the slides go into the Photos album "Bulls recaps", which iCloud Photos syncs to the phone, where
  Instagram picks images; the stored originals are exported back and compared byte for byte;
- Claude's push notification is the alert (the `run-postgame-recap` skill). An iMessage to the user's own number
  with the slides was tried and dropped on 2026-10-08: a text to oneself never alerts on the iPhone, and the
  attachments would pile up in Messages;
- the feeds, play-by-play, `sources.json` and `recap.json` are kept in the game's `as-posted/` (written once
  per game, at the first delivery, so it holds what was posted and a later rebuild cannot move the baseline
  `recheck.py` compares against).
A failed Photos import is logged and delivery carries on: the slides are already in iCloud Drive. The build gives up
five hours after tip-off (three hours after Final once a notice has restarted it). `--check` only reports
whether the game is final. `FOCUS_TEAM_ID` dry-runs another
team's game (saved under `stress-tests/`); `RECAP_ALBUM` sends a test run's slides to another album.

Notices, so a long wait is heard about instead of sat through in silence (added 2026-10-09): at fixed minutes
after Final (`MARKS`: at Final, then 20, 30, 45, 60, 90 and 120 minutes while NBA.com has not published every
slide feed, because the post should be out within 30 minutes of the buzzer; from 10 minutes when every feed is
in but a check keeps failing) the script prints what it is waiting on,
the step's own reason line and a restart command carrying the game ID and the time Final was first seen, then
exits STILL_WAITING (76). The `run-postgame-recap` skill posts the notice, pushes it to the phone (every notice;
the user wants to hear from the run), and restarts the command; every feed is already on disk, so a restart costs seconds and the timing line and
deadline carry on. Each mark is raised once, because a restarted process begins after the mark it reported
(no state file). The two kinds of wait are different problems: "not published yet: four factors" is NBA.com
being slow and needs patience; "every slide feed is published but a check is failing" means a scrambled feed
(DEN at UTA, 2026-10-06, never corrected) or our own check, and the user decides whether to keep waiting.

The steps it runs, for debugging (from the primary checkout, where `cache/` is the shared cache):

```bash
PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/pull_game.py <game_id>
PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/recap_data.py <game_id>
PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/espn_check.py <game_id>
PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/zones_share.py postgame-recaps/seasons/<season>/<game_id> output/postgame-recap/<game_id>/zones.png 13 11 33
venv/bin/python postgame-recaps/pipeline/build_mockup.py <game_id> [more ids]
venv/bin/python postgame-recaps/pipeline/export_slides.py <game_id>
```

`build_mockup.py` writes `output/postgame-recap/mockup.html`, all the given games with a switcher (the phone
preview is built from it); `export_slides.py` saves each page through headless Chromium (Playwright).

To review the whole format, including pages not yet in the live carousel, build the full mockup:
`venv/bin/python postgame-recaps/pipeline/build_mockup.py --full` recomputes one saved test game where every
page qualifies (`FULL_GAME`) and writes `output/postgame-recap/mockup-full.html` with every page and the team ranks mock.
When a new page or option is added behind a condition, make sure the full mockup still shows it.

The deadline (user, 2026-10-10: "we have to post"): 45 minutes after Final (`FALLBACK`), `postgame_recap.py`
sets `RECAP_FALLBACK`, and a feed NBA.com has left incomplete is replaced by what can be computed exactly or its
page is left out; each change is a `repaired:` line in the log and in `recap.json` (`repairs`), and the delivery
message names it. MIN at MIA showed why: NBA.com published the box score, play-by-play and summary for the full
game, but four factors, misc and shots stopped at 203 of 240 team-minutes and stayed so. Past the deadline:
- four factors covering fewer minutes than the game: eFG% and FT rate from the box score (within 0.05 points of
  NBA.com on 36 complete team-games), TOV% and OREB% a hyphen (box-score versions were 2 to 4 points off
  typically, up to 11: NBA.com uses team turnovers, team rebounds and its own possessions), with a page note;
- an incomplete shot feed: the shots come from the play-by-play (`shots_from_pbp`), which held every attempt
  on all 13 saved games and matched the shot feed's location, result, 2 or 3 points and shot type on all 1,220
  matched shots; it lacks NBA.com's zone labels, so the zones chart places those shots by coordinates (1,217 of
  1,220 in the same zone), and the page says so. Only if the play-by-play's count also differs from the box
  score is the shot chart left out (the contents renumber).
Paint, fast-break, second-chance and points-off-turnover counts always come from the game summary (full game,
144 of 144 equal to the misc feed on the saved complete games), so a partial misc feed no longer reaches a slide.

What makes a build "not ready" (`pull_game.py` and `recap_data.py`, exit 75):
- a feed a published slide uses is not published yet (`pull_game.REQUIRED`, logged by plain name, for example
  "four factors"); feeds used only by back-pocket pages (advanced, scoring, matchups, tracking, opponent shots)
  are optional; a timeout or dropped connection to NBA.com also waits and retries;
- the play-by-play does not yet reach the box score's final score (the two are separately cached requests);
- the play-by-play does not match NBA.com's quarter scores, or any made shot or free throw does not add exactly
  its points to the scoring team's total (`score_steps`; every saved game passes except the scrambled DEN at UTA
  feed). When the plays do reach every quarter score and only a printed running score is wrong, the running
  score is recomputed from the plays (`repair_scores`, 2026-10-10, MIN at MIA: a re-entered and-one), and the
  result must still pass the score steps and NBA.com's game-flow counts below;
- the Bulls shot feed holds fewer attempts than the box score (MIN at MIA: 72 of 87; every saved Bulls game
  matches);
- the game logs (LeagueGameLog players and teams), which carry a game while it is live, do not yet show tonight
  exactly as the final box score does (`logs_match`: PTS, REB, AST, STL, BLK and 3PM for both team rows and every
  Bulls player who played);
- the box-score tables disagree with each other (`feeds_agree`): player rows must add up to the team totals, and
  NBA.com's eFG% and FT rate must match the box score's makes and attempts (all 15 saved games agree); the hold
  names how many minutes NBA.com's four factors cover when they stopped early;
- lead changes, ties, biggest leads or longest runs differ from NBA.com's own Summary V3 counts. One exception
  (`compare_flow`, 2026-10-09): a winner led by at least its final margin, so an NBA.com biggest lead below it is
  impossible and is skipped, provided ours passes that test (HOU 135-117 at DAL, Oct 9: NBA.com listed both teams'
  biggest lead as 0 nine hours after Final). The recap.json `flow.nba_note` records it.
Box-score feeds are requested first exactly as NBA.com's game page requests them (LeagueID=00, EndRange=28800,
RangeType=0, which makes NBA.com ignore the range, so overtime is kept: checked on an OT and a 2OT game), then
with `nba_api`'s defaults: stats.nba.com caches each exact request, and on 2026-10-07 the website's request
had four factors, advanced and misc filled two to five minutes sooner.

Once every check passes, `pipeline/espn_check.py <game_id>` compares the saved feeds with ESPN's copy of the
game (its unofficial site API, `site.api.espn.com`, no key): the final and quarter scores, every player's box line
(minutes to the minute, who started and who played), the team box, the summary counts the slides use, every
shot in NBA.com's shot feeds matched to ESPN's play-by-play, and each team's running score. ESPN gets the same
official scorekeeping through its own pipeline, so it catches a feed NBA.com served incomplete (MIN at MIA: every
missing shot and the broken running score) and our own bugs, never a scorekeeper's error. NBA.com stays the
source (user, 2026-10-11): each `espn differs:` line is flagged for Claude's review, which makes the judgment
call; the build never waits or stops on it, and an unreachable ESPN reads "could not run", never "agree". ESPN's
summary is saved as `espn_summary.json` in the game folder. Two conventions differ by design and are handled:
ESPN files points off turnovers under the team that turned the ball over, and leaves some counts blank (a note,
not a zero). In preseason NBA.com's box score often marks one or two bench centers as extra starters (6 of 8
saved 2026-27 preseason games, no regular-season game); `recap_data.starters()` keeps the five on the floor at the
opening tip (the play-by-play), which ESPN's five match, and stops the build when it cannot settle five. The
ESPN check compares that five.

`recap_data.py` computes every number into `output/postgame-recap/<id>/recap.json`; the template only draws,
plus the arithmetic on rows it prints: TS% and the box-score subtotals and team row (which sums the players'
turnovers; the head-to-head turnover count is NBA.com's total with team turnovers, so slides 3 and 6 can
differ by design).
Scores come only from made-shot and free-throw rows: a period-start row can carry a later score, which once hid
five minutes of baskets (first live run, below). Game margins come from the two teams' points in LeagueGameLog;
LeagueGameFinder is no longer pulled, because after an overnight stat correction (2026-10-08) it showed the
Bulls' Oct 7 win as +0 while both teams' points were still right.

Stat corrections: NBA.com corrects box scores after games. Game 1 was corrected overnight (a missed shot, a block
and an offensive rebound added, an assist moved), which changed eleven numbers on the posted slides (Bulls FG
42-83 to 42-84, eFG% 57.8 to 57.1, OREB% 32.6 to 34.1, FT rate 38.6 to 38.1, rebounds 35 to 36, fast break points
12 to 14, Suns blocks 2 to 3, Caleb Wilson's line, two shot types, two breakdown bars). `pipeline/recheck.py <game_id>`
compares the feeds saved for the post (the game folder's `as-posted/` when present) with NBA.com now and lists each
changed number in plain words (box score with minutes, line score, four factors, misc points, game-flow counts,
and the featured team's shots by zone and shot type); it reads only. `postgame_recap.py` copies those feeds, the play-by-play, `sources.json` and
`recap.json` into `as-posted/` after the first export only, so neither a re-pull nor a rebuild can move the baseline. The as-posted Game 1 feeds and
recap.json are kept in `seasons/2026-27/0012600030/as-posted/`; the game folder itself holds the corrected pull.
The next-morning QA of four dry runs (2026-10-09) found only fast break points revised, in two of them; fast break
points also changed for Game 1, so they are the stat to expect to move. Readers are told: every slide footer
reads "Data via NBA.com as of <time> CT" (the box score's capture time from `sources.json`, with the date when the
capture was not on game day), and the caption carries "Stats via NBA.com as of game night. The NBA can revise
official stats after a game."

Before posting, check by eye: the score, line score and slide 2's tiles against the NBA.com game page; a margin
line with no long flat stretch (minutes with no score logged); the box-score lines of the top three Bulls scorers.

## Pages in the mockup

Drawn in the Canva Brand Template's page style (`EAHW6UQqJFQ`, page 2): warm `#E9E5E1` canvas, red, white and
black trim (brand `#CE1141`, `#FFFFFF`, `#000000`), heavy serif title, no subtitle, black text, 25 px side margins, and a "Data via NBA.com |
CHI @DEN, Nov 17, 2025" footer with the handle. The serif (titles, scores, big
numbers) is Georgia Pro Condensed Bold and Bold Italic (licensed desktop fonts, installed in ~/Library/Fonts
on 2026-10-07) when present on the Mac that exports; otherwise Source Serif 4 Black. All other text is Geist SemiBold
and Regular, from `~/Library/Fonts` or else Google Fonts. `export_slides.py` prints which faces it used. Font files never enter the repo (it is
public), and the phone preview cannot load them, so it shows Source Serif 4. Section titles are light text on a solid black block. The account mark
(`assets/brand/chicagobullsdata-mark.svg`) sits top right of every page but the cover. Labels are sentence case; column headers keep
capitals. The cover comes first (always posted since 2026-10-12), on the same
background with graph paper (36 px grid): the game's margin line as art, a score card (black header with "Final", any overtime, and Home or Away; one row per team with logo, serif name, record and serif score, the Bulls row banded and red, a pointer on the winning score; no W or L, which waits for page 2), the date, and across the top the series label in a black block and the swipe call to action as a red block with an arrow.
Under the series label, a contents box lists every page that follows with its carousel number ("[03] Team stats"),
on a solid offset shadow; every page's footer ends with the same number. Numbers are counted from the pages actually
drawn, so a skipped page (season leaders before game 5) drops out and the rest renumber. The opponent's side of
every comparison (head-to-head bars, the margin chart and the cover's margin art) takes a tint of the team's color,
red, green, black and silver teams staying gray (`DESIGN.md`, "The opponent in a tint").

1. Final score: big scoreboard (Final, any overtime, then W in green or L in red), line score, step-line scoring margin (every score, unsmoothed), then biggest lead, lead
   changes, tied, longest run (four band tiles, each label in a black block), and up to three notables.
2. Team stats: game leaders for both teams with headshots, 13 head-to-head rows (offensive rebounds after
   rebounds, steals and blocks after assists; the shooting rows' bars and bold side follow makes, not percentage,
   since 2026-10-12), up to four Bulls game awards.
3. Shot chart (real Python render): mid-range pooled and painted as one shape, 5-attempt color floor, square pills show
   makes/attempts and share of FGA, square summary cards; shot-type strip below, then "Assisted makes": one square
   per made field goal, red when assisted (since 2026-10-15).
4. Game breakdown: four factors table and points above average, the margin bars (each factor keeps one color chip on its column and its bar), "How to read it" (below).
5. Box score: starters and bench by points, subtotals and team total; MIN PTS REB AST FG 3PT FT TS% STL
   BLK TO +/-; one fixed gap between every column.
6. Season so far: record and tonight's place in the conference (places moved: a green up or black down arrow), then game margins (empty slots for games
   to play) and games over .500 after each game, on one game axis.
7. Season leaders: one grid of every qualified Bulls player's per-game points, rebounds, assists, steals,
   blocks and 3PM, then FG% (and games played), sorted by points; each stat's leader, every tied player included, in a solid red
   cell, the rest shaded by how close they are to the leader (from game 5; preseason from game 1, since
   2026-10-09, when the top-three cards were replaced so ties are never cut).

Team ranks (designed 2026-10-10, regular season only, not yet in the live carousel): "Where the Bulls rank", twelve
NBA.com team stats with league ranks in three groups (overall; style; the four factors with their color chips), each
a strip of all 30 teams by value with the Bulls as a red square. Only a mockup exists: `build_mockup.py --full` (or `<game_id> --ranks-mock
postgame-recaps/team-ranks-mock/ranks.json`) draws it from the 2025-26 NBA.com snapshot in that folder (its
`pull_team_ranks.py` rebuilds ranks.json; ranks are NBA.com's own, 1 being the best or the most,
except 3-point attempt share, which NBA.com does not list: the script ranks 3PA/FGA, ties sharing the best rank). The live page still needs season-to-date team stats pulled with each
game and a start rule (around game 5 to 10).

Preseason is its own season: its own record, .500 line, slots (from the schedule) and leaders; the
regular season starts at 0-0. Game breakdown (option B, chosen 2026-10-07; the bars-only page with awards was retired): the four factors per team as
rates (eFG% with 2PT | 3PT, TOV%, OREB%, FT rate; the better rate boxed) and as "points above average"
(points, not per possession, against an average team on that team's possessions) (shooting split 2PT | 3PT, using the league's own 2PT and 3PT baselines),
no total, then the Bulls-minus-opponent bars (other only when nonzero, extra possession) to the margin,
then "How to read it": why these four factors (every way a possession ends), then three short paragraphs with tonight's own worked shooting math (per-play values at
three decimals, so the equation is marked ≈).
Team stats then drops its four factors section and ends with up to four Bulls game awards as cards
(award, headshot, name, the stat that earned it). Technical, flagrant and clear-path free throws now
count under free throws, so other holds only possessions cut off by the end of a period and cut-short trips.

Back pocket, out of the carousel for now: on-court ratings scatter, who
guarded whom, player tracking, how they scored (`pipeline/backpocket_pages.js`; data still computed).

## Decisions

- Not building our own Net Points. ESPN's numbers sit behind access-controlled S3 files; do not work around it.
- Four factors use NBA.com's official per-game values (turnover % counts team turnovers) for the
  printed value, so they match what fans see on NBA.com.
- Awards omit ESPN-style negative awards (LVP, Dead Weight) for a Bulls fan account.
- Play types are season-only on NBA.com and cannot appear per game.
- No DRE and no DARKO in the recap (decided 2026-10-06). The parked DARKO script and data were removed on
  2026-10-08.
- Not committed (`.gitignore`): `portraits/` (NBA.com headshots that `pull_game.py` downloads again when
  missing; the repo keeps third-party portraits out of git). The generated page lives in `output/`.
- East place ranks the conference by winning percentage after tonight's games (league game log);
  teams level on winning percentage share a place, shown as T-9th, and NBA tiebreakers are not applied.
  Preseason ranks preseason games only.
- Scores logged at the same clock time are spread two seconds apart on the margin line, so every labeled
  moment is a real point on it.
- The margin line is drawn exactly, unsmoothed (2026-10-09; it was simplified and drawn as a monotone curve
  before): a step line that holds the margin flat until the next score and then jumps, through every scoring
  event. `STEP` in the template switches it to straight segments between scores.
- Zones always pool mid-range: a game's five mid-range sectors hold 0 to 4 attempts each, so split they
  would all be gray; pooled, the 13 saved Bulls games had 1 to 10. The color floor is 5 attempts (was 8 until
  2026-10-09): at 8, 3.2 of 8 zones per game were gray and mid-range in 11 of 13 games; at 5, 1.2 zones and 5
  of 13. One shot moves a 5-attempt zone's FG% by 20 points, so the color describes tonight, not a skill;
  the pill prints makes and attempts. A split mid-range belongs on a season-to-date chart, not a game.
- Notables (final-score page): up to three exact, positive callouts in one column, most notable first: tonight's team
  stat ranked top three among every NBA team game this season (once 150 exist), a Bulls season high
  (after 10 games; biggest win, fewest points allowed included), then player season highs over a floor
  (15 PTS, 8 REB, 6 AST, 3 3PM, 3 STL, 3 BLK; after 5 games, counting his games for other teams). Ties say
  "tied". Regular season only; `player_games.csv` keeps Bulls players' games on every team for this.
  Since 2026-10-15 two kinds also run in preseason. Qualifiers (`QUALIFIERS`; the user's table is Notion's "Notable
  qualifiers"): a Bulls team stat in the top 5% of the 2,460 team games of 2025-26 (`baselines/`; bottom 5% for
  turnovers and opponent FG%), worded "top 2% of NBA games last season", rarest first, one per family (assist rate,
  threes), never a family a season notable already covers. Tonight's line comes from the game log, the baseline's own
  table, and every count it reads must equal the box score (turnovers: the summary's total with team turnovers), or
  no qualifier runs. Then the top assist connection ("Giddey to Vučević: 6 assists") when one passer-to-scorer pair
  alone has 5 or more (3 of the 16 saved Bulls games). Assists come from the play-by-play's text, which must match
  the box score's makes and assists, or the connection and the shot chart's assisted row are left out (a `repairs` line).
- Season leaders qualify at half of the Bulls' games so far, shown in the footer. The NBA's 70% rule
  was tried first and left out Giddey (34 of 50) and White (28 of 50) at the midseason test game.
- Season leaders' FG% comes from summed makes and attempts and needs 5 field-goal attempts per game played;
  below that it is a hyphen (user, 2026-10-12: plain FG%, chosen over eFG% and TS% after comparing all three).
- Season leader values are rounded to the one decimal printed, so players tied on the page share the red cell.
  The saved games qualify 9 to 16 players; the grid fits 16 at full row height.

## Game breakdown method (`pipeline/accounting.py`)

Every possession starts worth V, the 2025-26 league points per possession (1.148). Each shot, rebound,
turnover and free-throw trip moves that value and books the change to one factor; a missed shot drops it
to P×V, where P is the official offensive-rebound rate (0.302). Factors are centred on the league average
and taken Bulls minus opponent; an extra-possession term covers unequal possession counts. Because every
point and possession passes through one booked event, the factors sum to the final margin exactly.
`pipeline/validate_accounting_season.py` checks this on all 82 Bulls games of 2025-26 (both overtime games
included): play-by-play points match every official score and the error is zero
(`stress-tests/accounting-season-2025-26.csv`). Two rare events needed handling: clear-path free throws, and a
lane violation that cancelled a trip's last free throw. A production run must reconcile before rendering.
The total is exact; the split between factors depends on V and P.

Worked example, Bulls at Denver (2025-11-17), traced play by play. Constants from 2025-26 NBA.com totals:
V = 284,395 PTS / 247,827 POSS = 1.1476; P = 0.3023 (official OREB%, team rebounds included, weighted by possessions), so a miss
leaves P x V = 0.347. Each made 2 books 2 - 1.148 = +0.852 to shooting; each made 3 +1.852; each miss
0.347 - 1.148 = -0.801. Bulls shooting raw: 29 x 0.852 + 19 x 1.852 - 54 x 0.801 = +16.68; the league's
raw shooting per possession is (2 x FGM + 3PM - FGA x V + misses x P x V) / POSS = +0.1125, so 103
possessions expect +11.59 and the Bulls are +5.09. Denver: +12.38 raw, +11.48 expected on 102, +0.90.
Shooting bar = 5.09 - 0.90 = +4.2. Turnovers book minus the possession's value (9 x 1.148), rebounds
+0.801 for an offensive board and -0.347 when the opponent rebounds a miss, free-throw trips minus the
possession value at the trip's start plus 1 per make. `other` holds technical/flagrant/clear-path free
throws and possessions cut off by the end of a period. Play-by-play counts team rebounds, so the Bulls show
16 offensive rebounds where the box score shows 13.

ESPN Analytics' "4 Factors Accounting" (Dean Oliver's net points, summed by factor) was compared on two
games. Its team total equals PTS - 1.1563 x ESPN's possession count in all four team rows; 1.1563 is not
NBA.com's league average for 2023-24 (1.145), 2024-25 (1.137) or 2025-26 to date (1.145-1.146) or in full
(1.148), so its source is unpublished. Its turnover row is close to -1.16 per turnover. Its per-shot,
rebound and foul credits are not published; our raw ledger with its constant lands within about 1 point
per factor.

## Stress test (2026-10-03)

Five games: the Denver win, a 24-point comeback (vs. PHI, Nov 4), a 43-point loss (at MIA, Feb 1), a
double-overtime loss (at UTA, Nov 16) and a preseason game (at DEN, Oct 14, 2025). Flow counts matched
NBA's in all five and every accounting reconciled. Fixes it forced: OT label and periods on the cover,
margin legend moved out of the plot, opponent's deciding basket labeled with its team, breakdown bars
scaled to fixed label and value columns, clutch free throws double-counted, awards capped at two per
player and only ever given to the leader.

Preseason: shots need `season_type=Pre Season`; matchups are not published; tracking tables come back as
all zeros, which `BoxScoreSummaryV3` flags with `ptAvailable = 0`, so the tracking page is skipped.
Hustle and scoring returned real rows.

Second stress test (2026-10-07), seven more games chosen to break the format: the opener vs DET (game 1),
the finale at DAL (game 82), a one-OT win at GSW with only 8 Bulls used, the +31 win at WAS, a 1-point win
at POR (long name), a -35 loss vs MIN with 13 Bulls used, and a 1-point loss at MEM decided by the opponent.
All twelve reconcile and match NBA's flow counts. An in-browser check of every text element on all 95 pages
(off the 25 px margins, or overlapping another text) finds none. Fixes it forced: chart labels at the edge go
beside their dot, season-chart labels are placed by trying spots around their bar or point, nearest first, and taking the first that touches no bar, line or edge (a short leader joins any label that had to move), season leaders wait until game 5
(game 3 in preseason, game 1 since 2026-10-09), the cover lines leave room for the record, and notables rank players by size and give
each player one line.

Awards (2026-10-07; shown as hashtags since 2026-10-09, the mapping is drafted on the Notion "Game recaps"
page): Top Performer (#mvp; highest Game Score, not printed; a triple-double shows as its three stats, unlabeled)
is always first. The rest are leader-only, at most two per player, and ranked by how far the winner cleared
the floor (value / floor): Triple-double (by anyone else), Hot Hand (#efficient; 70%+ FG on 10+ shots), Sharpshooter
(5+ threes since 2026-10-12, was 6), Pickpocket (4+ steals), Block Party (4+), Glass Cleaner (15+ rebounds), Board Crasher (5+
offensive), Facilitator (8+ assists; 12 until 2026-10-09, 10 until 2026-10-12), Spark Plug (bench Game Score 15+, raised from 10 on 2026-10-09; not the Top Performer),
Closer (5+ clutch points), Slam Dunk (#highflyer; 5+ dunks, raised from 4 on 2026-10-09). Workhorse (40+ minutes) and Soft Touch
(3+ floaters) were dropped on 2026-10-09; the hashtag for each award is in the Notion "Game recaps" table.
Floors tightened 2026-10-07 so each box-score award fires in about 5-20% of 2025-26 Bulls games (Hot Hand had
fired in 82%, Facilitator 63%). Team stats shows the first four. The hustle awards (Charge Taker, Loose Ball,
Screen Setter) were removed on 2026-10-08: hustle stats publish late and speed matters more. The Top Performer
line shows points with shooting, then up to two other standout stats (rebounds, assists, steals, blocks, threes),
so the line shows why Game Score picked the player.

## Baseline for current-season games

`recap_data.BASELINE_SEASON` sets one completed regular season for points per possession, the
offensive-rebound rate, the scatter reference line and the zones league FG%. Policy, in force since the first preseason game: the previous completed regular season for the whole season,
said on the page. It exists from the first preseason game, and it keeps all 82 posts on one scale. League ORtg moved
only between 113.7 and 114.8 over 2022-23 to 2025-26; moving the baseline across that range, or the
rebound rate by two points, changed the Denver breakdown bars by at most 0.1 point, because both teams
are measured against the same baseline and the error cancels in the Bulls-minus-opponent edge.

## Inputs

Tests: `./run_tests.sh tests/test_postgame_recap.py -q` runs the saved feeds through every check that makes
a build wait (score steps, a lagging play-by-play, box tables that disagree, game logs, the deciding-basket
label) and pins Game 1's NBA.com-verified numbers and caption.

- `seasons/<season>/<id>/` and `stress-tests/<id>/`: NBA.com snapshots per game (traditional, summary V3, four factors, play-by-play,
  advanced, misc, matchups, tracking, scoring, shots with and without ACTION_TYPE, roster (hustle and
  LeagueGameFinder's team games were dropped on 2026-10-08; older folders still hold them); for regular-season games also `player_games.csv`, the Bulls' player game
  logs and `league_games.csv`, every team's games, both from `LeagueGameLog` (preseason too), and
  `schedule.csv` from `ScheduleLeagueV2`, added 2026-10-06),
  fetched by `pipeline/pull_game.py` (the first five games on 2026-10-03, the rest on 2026-10-07 and 08);
  `missing.txt` lists empty feeds. 16 folders: the games named under Stress test and Second stress test, the
  2026-27 dry runs (0012600010 LAL at GSW; 0012600027 DEN at UTA, kept for its scrambled play-by-play;
  0012600012 HOU at DAL, whose impossible NBA.com biggest leads made `compare_flow`; 0012600036 SAC at LAL, a
  clean loss) and the preseason DEN game (0012500059).
- `logos/`: both teams' primary logos (SVG) from NBA.com's CDN (`cdn.nba.com/logos/nba/<team id>/primary/L/logo.svg`),
  fetched by `pull_logos`; there is no separate dark-background version, so the cover uses the same file.
- `baselines/league-2025-26/`: league team-game logs, official four factors and advanced (possessions, ratings).
- `stress-tests/bulls-games-2025-26.csv`: last season's Bulls game list. `portraits/`: NBA CDN headshots.
- `assets/2026-10-03-v01-zones-share.png`: `pipeline/zones_share.py` (patches the zones pill in place).

## Known gaps before production

- Jersey numbers: the box score feed leaves `jerseyNum` blank, so numbers come from `CommonTeamRoster`.
  The 2026-27 camp roster lists four shared numbers (8, 9, 11, 15). `recap_data.JERSEY_FIX` holds numbers the
  user confirmed (Buddy Hield 7) and wins over the roster; when two players who both played share a number,
  every unconfirmed holder prints none (Game 1: Miller and Boston at 11).
  Pulled the night of a game it is current; the 2025-26 test games were pulled later, so players traded
  since (Vučević, Huerter, Dosunmu, Carter, Terry, Phillips, White) show no number rather than a guess.
  NBA's live box score feed (which carries jersey numbers) returned HTTP 403.

- `bulls.data.fetch.get_game_shots` still hardcodes the regular season; `pull_game.py` avoids it.
- `BoxScoreSummaryV2` returned empty line scores; `BoxScoreSummaryV3` supplies date, arena, records and
  quarter scores (records and arena are now taken from it). NBA's CDN live-data feed returned HTTP 403.
- Positions were dropped from the box score; if they return, take them from the roster as of the game.
- Tracking counts 100 of the Bulls' 102 shots; matchup possessions are partial-possession estimates.
- Feed timing, measured 2026-10-06 on preseason LAL at GSW (polled each minute): marked Final 23:41, play-by-play
  23:51, box score 23:52, misc and shots 23:56, four factors 23:57, so every core feed within 16 minutes.
  Mid-game, the box scores return nothing, but LeagueGameLog already includes the live game with partial
  stats: build only after the summary says Final and the box score is filled. The same night, DEN at UTA's
  play-by-play was out of order (scores and periods scrambled) over an hour after the final and stayed so on
  a re-pull; the quarter-by-quarter check against the official line score catches it (`pbp_ok`), and a post
  should wait for a clean feed (now enforced: the build waits).
  `FOCUS_TEAM_ID` lets the pipeline dry-run on any team's game.
- Dry runs on two 2026-27 preseason games (2026-10-07): LAL at GSW (Warriors featured) passes every cross-check
  against a second NBA source (score, records, quarters, flow counts, box totals, minutes, head to head, shots,
  leaders, awards, headshots, logos). DEN at UTA fails only the play-by-play checks: its feed was still
  scrambled the next morning, and PlayByPlayV2 (the older feed) is retired, so there is no clean source; such
  a post waits. Jersey numbers come from the roster (the box score's jerseyNum is blank for current games too)
  and are read as text so "3.0" and lost "00" cannot appear. Minutes totals add exact minutes and round once.
  A "Did not play" list too long for the footer moves to its own line above it.
- First live run (2026-10-07, PHX at CHI, 0012600030; full write-up on the Notion "Game recaps" page).
  Final about 21:51 CT, every feed ready to `postgame_recap.py` 22:08, slides 22:10. Open: (1) stats.nba.com
  caches by exact URL, and `nba_api`'s request (EndRange=0, no LeagueID) lagged the website's
  (LeagueID=00, EndRange=28800) by two to five minutes on four factors, advanced, misc and scoring;
  (2) readiness checks four factors and shots but not scoring, advanced or misc, so the first build pulled
  an empty scoring feed and `recap_data.py` stopped (re-run fixed it); (3) `nba_api` raises
  AttributeError on an empty derived feed, so the readiness log reads "request failed" for "not published";
  (4) hustle stats were still unpublished at pull time. Fixed on 2026-10-07: the run and third-quarter margin
  line, which the period-start score had corrupted. Fixed on 2026-10-08: (1) website-style requests first, (2)
  readiness covers every required feed and the build retries on NOT_READY, (3) unpublished feeds are logged by
  name, (4) hustle removed from the recap; plus the score-step, game-log and game-flow checks above.
- Independent review (2026-10-08): a separate agent re-fetched NBA.com and matched every Game 1 slide number
  (post-correction) and two overtime games (0022500943 OT, 0022500240 2OT), overtime periods included. It found
  and the same day fixed: a play-by-play lagging the box score stopped the run instead of waiting; one NBA.com
  timeout ended the night; the deciding-basket label could name a missed and-1 free throw at the same clock;
  team game-log rows were checked on points only; a triple-double with steals or blocks printed "PTS, REB,
  AST". Not yet verified: a preseason game against a non-NBA club (LeagueGameLog may have no opponent row,
  which would make the build wait until the deadline), and whether NBA.com ever lists an and-1 free throw
  before its basket or keeps an overturned basket (either would fail `score_steps` on a good feed).
- The box score's 12 columns force 24px numbers at full-name size; dropping STL/BLK would allow 26px.
