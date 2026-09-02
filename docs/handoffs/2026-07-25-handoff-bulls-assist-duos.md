# ACTIVE — Bulls assist-duos posts

Which Bulls pairs created the most baskets for one another. One analysis, **two separate visual
projects**, each with its own folder under `docs/visuals/` and its own Notion page when it ships.

| Project | Slug | Slides |
| --- | --- | --- |
| The post being taken forward | `assist-duos` | Best connection of every season, one slide per decade (10 / 10 / 6 rows), plus a 2025-26 top-eight slide |
| Parked, liked, not scheduled | `assist-duos-by-decade` | Top ten connections within each decade (10 / 10 / 10) |

Both render from `scripts/prototypes/assist_duos.py`; `--mode both` writes both projects.

## Settled direction

- Rank unordered pairs by **combined assists between the two players** (`A→B + B→A`), ties broken on
  the points those baskets were worth.
- Preserve the directional split — it is the point of the post. It ranges from 87% one-way
  (Giddey→Buzelis, 2025-26) to a dead-even 35-34 (Vučević↔Buzelis). The split bar carries both facts
  in one mark: length is the total, the colour break is the boundary between directions.
- Second column is **games played together**, not points. Points ran at ~2.3 per assist for every
  duo, restating the total; shared games explain *why* a total is what it is. Giddey-Vučević fell
  from 175 to 106 mostly because they shared 33 games instead of 63.
- Volume post: "most productive connections", not "best chemistry".
- Decade boundaries come from `top_game_performances.decade_for_end_year`, so the two carousels cut
  seasons identically. 2019-20 is the 2010s.
- One bar scale and one canvas height across a carousel — readers compare slides directly, and every
  slide must drop into the same Canva frame. All slides export 1500×1320.
- Chart assets only. Canva owns the title, subtitle, coverage line, and handle.

## Data

`scripts/prototypes/assist_duos_fetch.py` caches every assisted Bulls basket since 2000-01 from
`PlayByPlayV3`, one CSV per season under the post's tracked
`docs/visuals/2026-08-08-assist-duos/data/seasons/` (not ignored `cache/`, which lost one full fetch
to worktree cleanup). ~2,100 games at roughly two minutes per season, strictly serial: **NBA.com
throttles concurrent play-by-play hard** — a four-worker test made even single serial requests time
out for minutes afterwards.

Play-by-play rather than the tracking passing dashboard because only it carries `shotValue`, and
because it *is* the official record: tracking undercounts (2,312 vs 2,335 official in 2025-26).

**Every season reconciles exactly: 48,316 extracted vs 48,316 official.** Run
`--reconcile` after any refetch. The identity-matching traps that got there are in `DEVELOPMENT.md`
under Data Guardrails — read them before touching the resolver.

Games played together comes from `PlayerGameLogs`, one request per season.

**Shared minutes are not available.** `leaguedashlineups` returns zero rows before 2007-08, which
would blank the two best rows on the board (2006-07 Hinrich/Deng, 2003-04 Hinrich/Crawford). Games
is the coarser but complete denominator. Revisit only for a 2010s-onward post.

## Findings

- **Derrick Rose → Luol Deng, 2010-11: 233 combined (182 one way)** — far clear of everything since
  2000; the next best is Hinrich→Deng at 184.
- Every 2000s leader beats the 2025-26 best of 106. The modern number only means something beside
  the Hinrich era.
- The decade view is repetitive by nature — Hinrich in four 2000s rows, Vučević in nine of ten 2020s
  rows. That is why the yearly view was chosen for the post.

## Open

- **Jay Williams (2398) has no portrait** on the NBA CDN or ESPN; he is row 8 of the decade-2000s
  slide only, so he does not affect the chosen post. Greg Anthony (21) is the same case on the
  yearly-2000s slide and currently renders as the CDN silhouette, at the user's direction. A Getty
  comp was offered and declined — licensed sources only. Wikimedia has CC-licensed photos of both,
  but they are present-day candids that clash with studio headshots and carry attribution and
  share-alike obligations.
- **Newest season first** is settled. The CLI now renders only `yearly-desc`; ascending is still
  reachable via `best_per_season(descending=False)` and its v01 renders are kept in the archive.
- Canva assembly, QA off a full export, and the caption are the user's next session.

## State

Both Notion pages are written, with the full data provenance section on the per-season page and a
pointer to it from the decade page. Status: `Mocked` for the post, `Parked` for the decade board.
The `Canva` property on both is still empty — it gets the design's edit link at assembly.

`docs/visuals/2026-08-08-assist-duos/assets/` and `.../2026-08-08-assist-duos-by-decade/assets/`
hold v01 of each project. Test suite 484 passing, 59 of them for this post.

The superseded first-session worktree `claude-assist-duos` has been removed; nothing on it was
unique to it.
