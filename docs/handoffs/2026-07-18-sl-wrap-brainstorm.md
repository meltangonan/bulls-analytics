# Summer League Wrap Post Handoff

**Status: ACTIVE — next session opens with a brainstorm, not a scoped brief**

## Objective

Create the Summer League wrap post: the cumulative "SL so far/wrap" piece that has been the
planned home for the **rotating spotlight module** format twist (held since the Lakers
installment; see DESIGN.md's decision log and the Lakers catalog card). Summer League is over:
the Bulls finished **1-4** (Jul 10 @MEM L 96-97, Jul 13 @UTA L, Jul 14 vs WAS W 99-87,
Jul 16 vs LAL L 82-105, Jul 17 @CLE L 91-100).

## How the User Wants to Start

The user explicitly wants to **open with a brainstorm** (use the `brainstorming` skill), not the
create-bulls-post clarification gate. Do not pre-scope the post, pick a format, or draft
anything before that conversation happens. Treat the material below as brainstorm fuel, not
decisions.

## Context Completed Before This Handoff

- All four per-game SL reports are Posted (account at 8 posts / 29 followers as of 2026-07-18).
  Full evidence, captions, and per-game analysis live on the `idea-catalog.html` cards.
- The per-game format stays unchanged as a serial; the wrap is where format experimentation was
  deliberately deferred.
- Commits through `a74ecf9` cover the Cavs finale package, a shot-zone data fix, the hashtag
  block rule, and skill updates.

## Brainstorm Fuel: Community Narratives (Scanned 2026-07-18)

Best-effort snapshot from the user's IG favorites and X; verify anything before it reaches a
graphic or caption:

- **Atwell 2-way speculation** is the hottest thread: everythingbullss's own comment
  ("last 2-way spot 👀", 21 likes), a 2.5K-like Texas Tech "give him a contract" post, and the
  official @chicagobulls account amplifying his 3Q (13 pts, 5-5 FG). The user's own Cavs-finale
  caption leaned into this. Atwell and Sellers were UDFA signings — the "front office found
  shooters for free" angle circulates too.
- **Grade discourse**: fan pages are posting letter grades (Caleb A, Sellers C, Awaka C+,
  Noa D-, Swain F) and "worst Bulls SL team in franchise history" takes. A data-grounded wrap
  is a natural above-the-fray answer.
- **Patience counter-narrative for Noa/Dailyn**: Noa grew three inches, had shoulder surgery,
  and is younger than Caleb/Dailyn; Dailyn played out of position. Both sat the finale for
  precautionary soreness (K.C. Johnson, Bulls PR). The bulls-content-playbook fairness
  guardrails matter here.
- **Caleb's final SL line circulating**: 23.5 PPG / 7.3 RPG / 2.5 BPG on 50/42 splits in
  4 games (fan-posted; recompute from NBA.com before use).
- Verified in-session nuggets: Awaka made 7 straight FGs over the last two games (13 of his
  last 15 over three; he did miss twice in the opener), and the team's 3PT swung from 9.1%
  (LAL) to 36.4% (CLE).

## Open Questions for the Brainstorm

- What is the wrap's single thesis — player-centric (spotlight module), team-trend, or a
  grades-answer? One post idea at a time still applies.
- Does the spotlight twist survive contact with the actual best story, or was it a
  format-first idea?
- Five games is a tiny sample; which claims clear the fairness bar?

## Durable Pointers

- `idea-catalog.html` — four Posted SL cards with captions and evidence.
- `scripts/prototypes/summer_league_report.py` — fetch/prep helpers reusable for cumulative
  stats (per-game only today; a wrap needs cross-game aggregation).
- `bulls-content-playbook.html` — editorial lanes and fairness guardrails.
- `STRATEGY.md` — casual-fan-first decision rule; shares/sends as the metric.
- `AGENTS.md` — Instagram and X access (@chicagobullsdata, @bullsdata) for the optional
  narrative re-scan in `promote-bulls-post`.
