---
target: Python design primitives and representative rendered graphics
total_score: 21
p0_count: 0
p1_count: 4
timestamp: 2026-07-12T22-44-59Z
slug: bulls-graphics
---
## Design Health Score

The standard Impeccable usability heuristics are translated here to the experience of reading a static Instagram graphic. A score of 4 means the output consistently works at feed size, not merely when opened full-screen.

| # | Static-graphic heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of the story | 2/4 | Season Shape states an immediate story; Summer League mostly presents evidence and leaves the conclusion to the viewer. |
| 2 | Match to everyday-fan language | 2/4 | Basic box-score terms work, but TS%, USG%, NETRTG, and qualifications assume expertise. |
| 3 | Viewer orientation and reading path | 2/4 | Grouping is orderly, but the recurring series title often outranks the actual basketball point. |
| 4 | Consistency and standards | 3/4 | The current renders look cohesive, but that cohesion is manually repeated across scripts rather than safely centralized. |
| 5 | Prevention of misreading | 2/4 | Redundant visual encodings help; missing benchmarks and fixed emphasis can suggest unsupported importance. |
| 6 | Recognition rather than recall | 2/4 | Legends help, but the viewer must know whether a metric is good and remember context across slides. |
| 7 | Comprehension efficiency | 2/4 | Season Shape rewards a glance; the overview and player profiles demand synthesis across many numbers. |
| 8 | Aesthetic and minimalist design | 3/4 | Clean, spacious, and recognizably Bulls; repeated cards and low-volume shot maps sometimes feel auto-filled. |
| 9 | Ambiguity diagnosis and recovery | 1/4 | When the takeaway is unclear, there is no declarative claim or benchmark to resolve it. |
| 10 | Source and context help | 2/4 | Provenance is consistently attempted but required microcopy does not survive feed-size reduction. |
| **Total** |  | **21/40** | **Acceptable foundation; significant comprehension and system-hardening work remains.** |

## Anti-Patterns Verdict

**LLM assessment:** The work passes the AI-slop test. Season Shape feels authored: its .500 baseline, red/black area grammar, annotations, and final -20 shape make the data itself the composition. The current header, palette, player imagery, and provenance are specific enough to feel like @chicagobullsdata rather than a generic sports template.

The Summer League family has a narrower problem: a dashboard-template smell. Repeated rounded stat tiles, a fixed six-card rail, and a fixed red TS% hero can make the template more assertive than the finding. This is not a wholesale style failure; it is a hierarchy failure. The series reports data cleanly but does not always tell the viewer what is interesting about it.

**Deterministic scan:** The Impeccable detector returned exit 0 and `[]`. This is a false clean signal, not validation: the detector scans HTML/CSS/JS-family files and the resolved target contains Python. The technical assessment therefore used source tracing, render metadata, browser and native PNG inspection, targeted tests, the full test suite, and synthetic edge cases.

**Visual overlays:** No reliable detector overlay exists. The target is a direct raster document rather than an HTML scene, and mutable injection was unavailable. Representative PNGs were successfully inspected over localhost in a fresh Chrome tab and through original-resolution image viewing; the local server and audit tabs were cleaned up afterward.

## Overall Impression

The repo already has the beginnings of a strong graphics product, not merely a style guide. The clearest proof is Season Shape: its visual form and its analytical claim are the same thing. The Summer League work demonstrates a repeatable production format, but repeatability currently comes at the cost of interpretive hierarchy and is implemented through duplicated script-local drawing logic.

The single biggest opportunity is to separate two responsibilities more cleanly:

1. A small, dependable house frame should guarantee identity, legibility, attribution, and export behavior.
2. Each format should remain free to let the basketball finding determine the composition and emphasis.

That distinction avoids both extremes: hand-rebuilding the brand on every post and forcing every story through one generic template.

## What's Working

1. **Season Shape demonstrates the intended two-second standard.** The overall season arc is understood before the annotations are read. Its fitted title and redundant red-above/black-below encoding also hold up technically and visually.

2. **The current identity survives thumbnail scale.** Academic M54, the red terminal title word, generous white field, and footer placement create recognizable authorship. The current system is meaningfully more distinctive than the older serif-led experiments.

3. **The best shared abstractions are appropriately small.** `gradient_bar` clamps values safely, and `headshot_label` degrades to a placeholder. Both are focused and tested. Summer League also has strong data-quality gates that prevent in-progress or falsely complete data from becoming a post.

## Priority Issues

### [P1] The Summer League format presents evidence before it states the claim

**What:** “TEAM SNAPSHOT,” “SHOT PROFILE,” and “ALL 21 FIELD-GOAL ATTEMPTS” identify content types, while the viewer must assemble the basketball conclusion from a court, a stat rail, and advanced metrics. The front page compounds this with four team tiles, a shot cloud, three shooting splits, and a 12-column player table.

**Why it matters:** At feed size, most of the table collapses into texture. A casual fan is asked to perform analysis before knowing why to care, while a knowledgeable fan receives many numbers without a benchmark or clear thesis.

**Fix:** Make each slide lead with one declarative, everyday-language finding. Use two or three measures as evidence. Reduce the front page to one game-level takeaway and three or four supporting facts; move full box-score detail to a later details slide or caption. Keep “Summer League Report” as a smaller recognition device.

**Code owner and blast radius:** This is primarily local to `scripts/prototypes/summer_league_report.py`, not a reason to redesign `craft.py`.

**Suggested command:** `$impeccable distill`

### [P1] The house frame is duplicated, while the nominally shared layer still leaks legacy typography

**What:** Season Shape and Summer League independently rebuild the current canvas, fitted segmented title, subtitle ticks, fonts, colors, and footer. Meanwhile `craft.py` imports private DM Sans and circular-headshot helpers from legacy `feed.py`, so `stacked_label` and `threshold_footer` can emit the font the design system labels legacy-only.

**Why it matters:** Current outputs look consistent because two scripts happen to repeat the same decisions. A future color, font, margin, or footer change can diverge silently, and a caller can use a “shared” helper while unknowingly stepping back into the old system.

**Fix:** Promote only the repeated house frame: explicit Academic M54/Archivo loaders, fixed canvas, fitted segmented title, tick-separated subtitle, optional kicker, source, watermark, and draft/final save contract. Remove the dependency from current helpers back into private legacy typography. Keep chart geometry and story-specific composition local.

**Code owner and blast radius:** `bulls/graphics/craft.py` or one small sibling house module, then active scripts as adopters. Do not migrate archival prototypes wholesale.

**Suggested command:** `$impeccable typeset`

### [P1] Real content edges can overflow or crash

**What:** Synthetic diagnostics reproduced three failures: a long F5 title/subtitle rendered beyond the canvas, `impact_board.py` crashed on a long one-word player name, and `f5_lineup_table.py` crashed on an empty valid frame. Long lineup combinations are also unmeasured, and no prototype test checks rendered bounds.

**Why it matters:** These are the graphics equivalent of broken responsive states. A repeatable format is not repeatable if normal variation in copy, names, or query results can produce clipped or failed output.

**Fix:** Reuse one measured-text/name helper, add explicit empty states before table construction, and test long titles, surnames, one-word names, empty frames, and maximum-density frames. Add a post-render bounds check for intentional artists.

**Code owner and blast radius:** Active legacy-derived formats first: `f5_leaderboard.py`, `f5_lineup_table.py`, and `impact_board.py`. The helper can be shared; format-specific empty states should remain local.

**Suggested command:** `$impeccable harden`

### [P1] Final export quality is a convention rather than an enforced contract

**What:** All committed mocks have the correct 4:5 aspect ratio, but they split evenly between 1080x1350 draft-sized output and 2160x2700 final output. Season Shape and Summer League expose a final-render path; F5 hard-codes 300 DPI; Impact silently saves through the 150-DPI default. Existing save tests assert only that a PNG exists.

**Why it matters:** A visually approved post can still be copied to the catalog at draft resolution. That risk is easy to miss because both files look correct on a desktop.

**Fix:** Preserve the fast 150-DPI draft workflow, give every active generator the same explicit final path, and assert draft/final pixel dimensions and DPI in tests before approved outputs are copied into `docs/mocks`.

**Code owner and blast radius:** `save_feed_post` contract plus active prototype entry points; no heavy export pipeline is needed.

**Suggested command:** `$impeccable harden`

### [P2] Required context is present but functionally too quiet

**What:** Sources, qualifications, court lines, table headers, miss outlines, and some annotations are readable full-size but nearly disappear around 288x360. The technical audit confirms `FAINT=#AAAAAA` on white is roughly 2.3:1 contrast. The Summer League table path also lacks bottom-bound validation and a robust missing-headshot path.

**Why it matters:** Provenance and fairness rules should survive the actual medium. Merely including them in the file is not enough if Instagram-scale viewing makes them unusable.

**Fix:** Establish a feed-tested minimum size and darker contrast floor for information required to interpret or trust the graphic. Shorten qualifications instead of shrinking them. Thicken court/miss marks, and validate embedded-table bounds and placeholder behavior.

**Code owner and blast radius:** Shared footer/text tokens for the minimum standard; Summer League-specific table compositing locally.

**Suggested command:** `$impeccable adapt`

## Persona Red Flags

**Distracted casual Bulls fan:** Season Shape works immediately. Summer League requires deciding which of ten-plus numbers matters and already knowing what TS% means. The largest phrase often describes the series rather than the interesting basketball fact.

**Data-literate hoops fan:** Shot locations, usage, efficiency, attempt counts, and provenance are useful, but the slides lack benchmarks. One-game NETRTG and plus/minus are visible enough to invite interpretation without communicating their instability. The overview reads closer to an archive box score than an analysis.

**Low-vision or color-deficient viewer:** The core red/black encodings usually have shape or position redundancy, which is good. Pale-gray sources, court geometry, table headers, miss circles, and qualifications are too delicate. The overview's density makes zoom reduction especially punishing.

## Minor Observations

- The current render family is stronger than the legacy F5/zone family; archival PNGs do not need retroactive migration. Adopt the current recognition layer if those formats return.
- Player image treatment varies across the Summer League sequence: circular portrait, cutout, and silhouette. Some variation is data availability, but the fallback should feel intentional.
- The fixed red TS% hero makes low-volume player slides feel auto-filled. Emphasis should move to the metric supporting that slide's claim.
- `feed.py` contains an empty `_draw_zone_borders` stub that callers invoke, making the apparent contract misleading.
- The Great Tables front-page path is not fully self-contained: the dependency is not declared, missing image paths can become the string `None`, and an intermediate PNG is left behind.

## Questions to Consider

1. Is the Summer League carousel primarily an interpretive story or a compact game archive? The current front page tries to do both.
2. Should the next implementation pass focus first on what fans see—the claim and density—or on the shared foundation that makes future posts safer?
3. Should active legacy-derived formats be migrated now, or only when the next real post needs one?
4. Is TS% always the red hero because it is the finding, or because the existing template requires a hero?
