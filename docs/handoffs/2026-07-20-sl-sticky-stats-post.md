# Summer League Sticky-Stats Post Handoff

**Status: ACTIVE — scope finalized in a 2026-07-20 brainstorm; next step is `create-bulls-post`**

## Objective

Build a new @chicagobullsdata post: profile **Caleb Wilson** (lead subject) — and optionally other
Bulls Summer League roster players — on the six **"sticky stats"**: the Summer League statistics
that published research shows actually predict rookie-season play. Frame: *ignore the box-score
noise from Vegas; these are the six numbers history says you can trust, and here is where Caleb
landed on them.*

This is a **separate post** from the SL-wrap post
(`docs/handoffs/2026-07-18-sl-wrap-brainstorm.md`, still ACTIVE). Sequencing between the two is
undecided; work one post at a time.

## Finalized Scope Decisions (user-confirmed)

1. **The six sticky stats** (user picked these; every one clears R² ≥ 0.55 in its source study):

   | Stat | R² | Source |
   | --- | --- | --- |
   | Dunk Rate | 0.74 | Lee |
   | 3PT Attempt Rate | 0.70 | Phillips |
   | Rim Rate | 0.65 | Lee |
   | AST per 36 | 0.58 | Phillips |
   | BLK per 36 | 0.56 | Phillips |
   | TRB per 36 | 0.55 | Phillips |

   Deliberate exclusions: 3PA per 36 (0.68, near-duplicate of 3PT attempt rate) and
   ORB per 36 (0.51, subsumed by TRB at 0.55).

2. **Cite, don't rebuild.** Present the R² values as the sources' findings with attribution on
   the graphic. Do not recompute historical SL-to-rookie correlations. (A self-computed rebuild
   was discussed and shelved as a possible offseason follow-up.)

3. **Comp-based outlook is shelved.** Nearest-neighbor rookie comps ("past rookies with Wilson's
   SL profile and the range of their rookie seasons") was explored in depth and deliberately cut:
   it requires a historical multi-year SL play-by-play/shot-location pool (hundreds of API calls,
   thinning coverage before ~2017). Keep out of scope unless the user re-opens it.

4. **Context device: this year's SL class.** A raw stat value is illegible alone. Show Wilson's
   values with percentiles (or equivalent context) within the 2026 Summer League class. The
   Egor Dëmin treatment in Phillips' article (one player, one sticky stat, historical anchor —
   "only three NBA players had a 3PA rate that high") is the editorial template.

5. **Lead with Caleb; others are context.** Dailyn Swain (user's named second subject — note
   spelling per existing repo docs) and other roster players may appear, but the predictive
   framing belongs to rookies: both studies measured **rookies only**. Any non-rookie shown gets
   descriptive framing, not "history says this predicts."

## Verified Source Details (read directly from the articles this session)

### Phillips (The F5) — primary citation for box-score stats

- Owen Phillips, "Summer League Stats You Can Trust," *The F5*, Jul 18, 2025.
  https://thef5.substack.com/p/summer-league-stats-you-can-trust — **paywalled**; the user is a
  logged-in subscriber in Chrome. All needed values are captured below.
- Method: 25 stats, 485 rookies, SL 2008–2024 (no 2020-21 season — no SL that year), per-36 and
  rate stats, **min 50 SL minutes & 250 rookie-season minutes**. "Summer League" includes Vegas,
  California Classic, and Salt Lake City. Chart title: "Summer League Stats vs. Rookie Season
  Stats."
- Full R² ladder (read off the chart, verified by zoom): 3PT Attempt Rate 0.70 · 3PA/36 0.68 ·
  AST/36 0.58 · BLK/36 0.56 · TRB/36 0.55 · ORB/36 0.51 · DRB/36 0.37 · PF/36 0.36 ·
  FGA/36 0.35 · Fantasy Pts/36 0.28 · TOV/36 0.26 · FT Attempt Rate 0.25 · AST/TO 0.24 ·
  FTA/36 0.24 · PTS/36 0.23 · STL/36 0.19 · FT% 0.14 · Game Score/36 0.13 · DRE/36 0.12 ·
  eFG% 0.12 · 2P% 0.10 · TS% 0.09 · MPG 0.03 · 3P% 0.03 · +/- per 36 0.02.
- Useful caption fodder: the icky-stat story (3P%, TS%, plus-minus ≈ noise) is the hook that
  makes the sticky six meaningful.
- Phillips also has a paid 2021 code tutorial (RealGM scrape + per-36 + lm in R) at
  https://thef5.substack.com/p/how-to-summer-league — only relevant if a rebuild is ever done.

### Lee (The Hardwood Collective) — primary citation for rim/dunk rate

- David Lee, Summer League article, *The Hardwood Collective*,
  https://thehardwoodcollective.com/articles/summer-league (published ~Jul 9, 2026; announced via
  https://x.com/dlee4three/status/2075285660752306507 — the X post and article are the same work,
  an explicit expansion of Phillips' study).
- Method: SL play-by-play, **SL 2017–2025 (no 2020), min 50 SL minutes & 250 rookie minutes**
  (mirrors Phillips' thresholds). Chart title: "Summer League Advanced Stats vs. Rookie Season."
- R² values (read off the chart, verified by zoom): Dunk Rate 0.74 · Rim Rate 0.65 ·
  AST/USG 0.51 · OREB Pts Added/100 0.50 · Unassisted 2P Creation% 0.47 · Unassisted% 0.44 ·
  Moreyball% 0.40 · Offensive Load 0.38 · Rim AST/100 0.34 · Non-Rim:Rim Rate 0.33 ·
  STOP% 0.30 · Box Creation 0.29 · STOP% (est) 0.26 · FT Pts Added/100 0.20 ·
  TOV Pts Added/100 0.14 · Rim Pts Added/100 0.12.
- **Build task: confirm Lee's exact rim-rate and dunk-rate definitions** (presumed share of FGA
  at rim / share of FGA that are dunk attempts) from his article before computing, so our numbers
  are apples-to-apples with the cited R².

## Requirements

### Analytical

- 2026 Bulls SL facts: team went 1-4 across 5 games (Jul 10 @MEM through Jul 17 @CLE; details in
  the SL-wrap handoff). **Caleb Wilson played 4 of 5 games** — recompute his stats from NBA.com
  data, not the fan-circulated line.
- Compute for Wilson (and any roster players shown): 3PA rate (3PA/FGA), AST/36, BLK/36, TRB/36
  from box scores; rim rate and dunk rate from shot detail per Lee's definitions.
- Percentile pool: 2026 SL players with a minutes floor (≥50 SL minutes mirrors both studies —
  keeps the qualification threshold citable). **Open decision:** pool = rookies only (matches the
  research) vs. all SL players (bigger, more intuitive pool). Surface to the user at the
  clarification gate.

### Functional (graphic/post)

- Six-stat profile card for Wilson with class context per stat; sources, R² values, minutes
  floors, and "4 games / X minutes" visible on the graphic (house rule: thresholds and sources
  on-graphic).
- Both citations on the graphic: "R²: Phillips, The F5 (2008–24 rookies)" and "Lee, The Hardwood
  Collective (2017–25)," or equivalent compact form.
- Fairness guardrail (bulls-content-playbook): sticky stats describe *what kind of player*, not
  *how good* — Phillips' own closing point. Keep the caption on that side of the line,
  especially with grade-discourse swirling (see SL-wrap handoff).
- Follow `POSTING_WORKFLOW.md` (incl. hashtag block rule) and `DESIGN.md`.

### Technical

- Reuse `bulls/data/fetch.py`: `get_box_score`, `get_player_shots`, `get_league_shots`,
  `league_for_game` are SL-aware. `scripts/prototypes/summer_league_report.py` has the SL
  fetch/prep patterns from the four posted reports (per-game; this post needs cross-game
  aggregation).
- **First build step / main risk:** recon that stats.nba.com has complete league-wide 2026 SL
  box + shot-detail data for the percentile pool. Cheap to verify before committing to design.
- Rim-zone definition should stay consistent with the repo's existing shot-zone handling (see
  the shot-zone data fix that shipped with the Cavs report, commit range through `a74ecf9`).
- New analysis belongs in a prototype script per `DEVELOPMENT.md`; no promoted CLI unless the
  format repeats.

## Next Action

Run `create-bulls-post` when the user is ready. Open the clarification gate with the small set of
open decisions above (percentile pool, whether Swain/others appear, sequencing vs. the SL-wrap
post), then start with the data-coverage recon. Add the idea-catalog card as part of that flow.
