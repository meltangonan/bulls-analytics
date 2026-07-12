---
target: design-system.html
total_score: 34
p0_count: 0
p1_count: 2
timestamp: 2026-07-12T21-39-12Z
slug: design-system-html
---
Method: dual-agent (A: design review sub-agent · B: detector sub-agent)

# Critique: design-system.html (v2, 2026-07-12)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Switcher state clear (aria-pressed, persisted); no current-section indicator on a ~13,500px page |
| 2 | Match System / Real World | 4 | Real pt/px values, real renders, plain-language rationale throughout |
| 3 | User Control and Freedom | 3 | Theme reversible; no back-to-top or persistent way back to the TOC |
| 4 | Consistency and Standards | 4 | White canvas-card convention rigorously held across all four themes |
| 5 | Error Prevention | 4 | License warning, matplotlib gotcha, fact rule, silhouette-size heuristic: the page's superpower |
| 6 | Recognition Rather Than Recall | 2 | §-cross-references are plain text, not links; no sticky nav |
| 7 | Flexibility and Efficiency | 3 | Anchored TOC + themes; § refs not clickable, no persistent nav |
| 8 | Aesthetic and Minimalist Design | 3 | §08 is ~4,500px of near-identical gray cards; emphasis rule stated three times |
| 9 | Error Recovery | 4 | Near-n/a for a static doc; degradation handled well (fallback stacks, try/catch, placeholder philosophy) |
| 10 | Help and Documentation | 4 | "How to use this file" up front; source pointers on every section head |
| **Total** | | **34/40** | **Good — solid foundation, address weak areas** |

## Anti-Patterns Verdict

**LLM assessment: not AI slop — reads hand-made, confidently so.** The two-layer color
architecture, the amp-glyph workaround, production scars in the warn boxes, and four
genuinely distinct themes are the opposite of template output. The one slop-adjacent tell:
mid-page rhythm — §08's seven near-identical bordered cards narrow the page's compositional
vocabulary below its voice.

**Deterministic scan: effectively clean.** 1 file-level warning (`em-dash-overuse`, count 7)
whose count is inflated by quoted spec glyphs (the "—" swatch placeholders and the
missing-value glyph rule are documented graphics content, confirmed intentional); the last
genuine prose em dash was fixed during this run. `numbered-section-markers` is suppressed by
config (user-confirmed convention). Mechanical a11y facts all green: 0 missing alts, working
aria-pressed, clean heading order, :focus-visible, prefers-reduced-motion.

**Browser overlays:** not run — no browser tool exposed to the detector sub-agent.

**Where they diverge:** the detector had nothing on the real issues (pin occlusion, mobile
overflow, unnamed mobile buttons, invisible swatch chips on dark themes) — all
judgment-layer findings.

## Overall Impression

A correct, complete, self-aware spec whose opening 1,000px and §09 real-render anatomies are
genuinely impressive, but whose middle flatlines into uniform gray cards, and whose showcase
section (the anatomies) is the one place where overlays damage the work. Biggest single
opportunity: make the page perform its system, not just document it.

## What's Working

1. The two-layer color system is executed, not just claimed: verified across all four
   themes, every spec demo stays on a white canvas card with true --g-* tokens.
2. §09 closes the spec-to-output loop with actual docs/mocks/ renders, pinned callouts, and
   honest caveats ("this render predates the fitted-title rule").
3. Production scars as documentation (silhouette ~12KB heuristic, force_sign,
   never-guess-a-date) give it authority no generic design-system page has.

## Priority Issues

- **[P1] §09 pins occlude the artwork.** Pin 1 sits on the first letter of every mock's
  title in all four anatomies. Fix: move pins into whitespace, or replace solid discs with
  outlined ring markers / side-gutter callout lines. Suggested: /impeccable polish
- **[P1] Horizontal overflow at ~390px.** Long unbreakable mono tokens
  (`summer_league_report._player_table_image()`) clip masthead meta, TOC, .src labels;
  switcher partially offscreen. Fix: overflow-wrap:anywhere on code/.src/.sig; re-test 390px.
  Suggested: /impeccable adapt
- **[P2] § cross-references aren't links** on a 13,500px page; no back-to-top. Fix: wrap
  §NN refs in anchors; slim sticky section indicator. Suggested: /impeccable polish
- **[P2] Mobile switcher buttons lose accessible names** (.sw-name display:none removes
  text from the a11y tree; four unnamed near-identical dots). Fix: aria-label per button.
  Suggested: /impeccable audit
- **[P3] Swatch chips vanish on dark/red themes** (no border on .chip; BULLS_BLACK merges
  into Blackout panel, RED into Hardwood card). Fix: 1px inset hairline like the colormap
  .strip already has. Suggested: /impeccable polish

## Persona Red Flags

**Jordan (first-time coding agent):** page §04 ≠ DESIGN.md §5 numbering collision (inline
refs never say which numbering); §08 quietly holds normative values that exist nowhere in
DESIGN.md (chip 118×52 r10, rail 280×88 r12, PLAYER_ROW_HEIGHT=173, court-line trio) with
no statement of which doc wins; unlinked § refs are the biggest first-visit friction.

**Sam (keyboard/screen reader/contrast):** no skip link; fixed switcher is first tab stop;
§09 pin numbers are bare spans a screen reader reads as stray digits (aria-hidden them);
Hardwood muted #F4D9CC on #BE0E3B ≈ 4.7:1 — passes AA with no headroom at .92rem; weakest:
.tag.parked mono at .62rem in Hardwood. Positives: :focus-visible, reduced-motion,
role="img" + alts, real aria-pressed.

**The account owner:** the pin-over-title flaw is exactly what a Goldsberry-tier eye
catches in the proof-of-craft section; §01's red→green diverging ramp shows no colorblind
caveat although PRODUCT.md records it (the SIGN RULE mitigation is buried in §08); the
Archivo "Aa 0123" specimens are a missed brand beat — a Bulls line ("CALEB WILSON · 35
PTS") would make even the type section feel like the account.

## Minor Observations

- Masthead uses "·" separators while §04 bans "·" glyphs on graphics — doc chrome,
  technically fine, wink-worthy in a page this self-aware.
- Emphasis grammar stated three times (§08 ×2, §10) — consolidation candidate.
- Google Fonts dependency: offline agents see fallback chrome fonts (spec faces load
  locally — correct).
- "1350" rotated dimension label sits close to the card edge at narrow widths.
- TOC's 13 pills wrap unbalanced (9+4) at 1280px.
- Repo hygiene: docs/mocks/ has two mis-dated `2025-07-14-summer-league-report-*` files
  next to the 2026-07-10 set.

## Questions to Consider

1. If "the template is the brand," why does the brand's reference page default to a theme
   the graphics can never use? Do four decorative themes earn their QA surface, or would
   one impeccable Jersey theme be more on-message?
2. §08 is becoming the real spec (values live only there). Is "DESIGN.md stays canonical"
   still true — should DESIGN.md absorb those values or formally delegate component-level
   truth to this page?
3. Who is the pinned-anatomy section for? If it's the proof-of-craft centerpiece, would
   side-gutter callout lines (Goldsberry-style figure annotation) beat floating pins?
