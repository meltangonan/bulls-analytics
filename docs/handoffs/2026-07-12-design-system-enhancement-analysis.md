# Design System Page — Enhancement Analysis

**Scope:** `design-system.html` (v2, rebuilt 2026-07-12) — the rendered companion to
`DESIGN.md`. This document is the working brief for the enhancement/polish pass: ten
detailed opportunities plus the results of a formal `/impeccable critique` run. It supports
the handoff at `docs/handoffs/2026-07-12-design-system-enhancement.md`.

**What this is NOT about:** the Instagram graphics themselves. Every change here is doc
chrome. The graphics spec (tokens, Archivo, white canvas) is fixed; spec demos must keep
rendering on white canvas cards regardless of theme. That two-layer rule is the page's core
architecture — any enhancement that blurs it is wrong by definition.

**Overall read going in:** the page is clean, correct, and complete, but it is still
*well-behaved* — a spec that documents a design system rather than one that performs it.
The strongest available moves are self-referential: make the page practice its own rules.

---

## Tier 1 — High-impact ("oh nice" moments)

### 1. Fitted masthead title

**What:** DESIGN.md §5 / page §04 requires post titles to auto-fit so the string fills the
measure exactly (W−120 on the graphics). The page's own masthead should obey its own rule:
"DESIGN SYSTEM" in Academic M54 scaled by JS so it fills the content column edge-to-edge at
any window size.

**Why:** the single most ownable touch available — the document demonstrating its own
header rule. Also fixes the current slightly arbitrary `clamp()` size.

**How:** measure the title's natural width at a base size, compute
`scale = containerWidth / naturalWidth`, apply `font-size` accordingly (or
`transform: scale()` on a single-line element with `transform-origin: left`). Re-run on
`resize` (throttled) and after the Academic M54 `@font-face` resolves
(`document.fonts.ready`). Keep the one-red-accent-word rule. Fallback: current `clamp()`
when JS is off.

**Watch out:** `text-wrap: balance` must come off the h1 (single line now); test very
narrow viewports — below ~360px allow wrapping back to two lines instead of microscopic
type.

### 2. Anatomy pin ↔ legend coupling

**What:** in §09, hovering (or focusing) a numbered legend row highlights the matching pin
on the real render — pin scales up ~1.3×, gets a stronger ring; sibling pins dim to ~40%.
Hovering a pin highlights its legend row in return.

**Why:** turns the anatomies from an illustration into an instrument; cheapest
delight-per-line-of-code on the page.

**How:** pure CSS is possible if each anatomy card gets `data-pin` attributes and
`:has()` selectors (fine in 2026 Chrome); otherwise ~15 lines of JS toggling a class on the
card (`.hl-1` … `.hl-5`). Include `:focus-within` so keyboard users get the same coupling.
Respect `prefers-reduced-motion`: swap the scale animation for an instant color change.

### 3. Jersey-trim band

**What:** the flat 10px top band becomes a jersey-collar trim: the theme's band color with
two thin contrast pinstripes (e.g. Jersey: red band, hairline white + black stripes;
Blackout: black with red piping; Newsprint: ink band with paper hairline; Hardwood: black
band with cream piping).

**Why:** a motif borrowed from the actual physical object (the uniform) rather than from
other websites — exactly what the brand register asks for. Small, permanent, ownable.

**How:** band becomes a 14–16px element with two 1.5px inset lines
(`background: linear-gradient` stack or `border-top`/`border-bottom` on a pseudo-element).
Define per-theme via the existing custom-property block; no new structure.

### 4. Recompose the color section (kill the swatch card grid)

**What:** replace the 9-identical-swatch card grid with one composed "palette board":
a single wide strip on a white canvas card where each color's width is proportional to its
actual role on a graphic — white dominant (~70%), grays as thin scaffolding slices, RED hot
and narrow (~8%), BULLS_BLACK solid (~15%) — with token name + hex labeling each slice
(popover or below-strip legend for the thin slices). The four panel tints and two colormaps
stay as compact secondary rows.

**Why:** identical card grids are the recognized template smell, and this is the page's
most generic-looking section. A proportional strip *shows* the "red/black are the only
meaningful colors; a thumbnail reads red+black+white" rule instead of listing it.

**How:** flex row of slices with `flex-grow` weights; each slice is a `<button>` for
click-to-copy (see #5). Keep a small definition list under the strip for the roles, since
thin slices can't hold their own description text. Accessibility: every slice needs an
accessible name (`aria-label="RED #CE1141 — Bulls red, accent"`).

**Watch out:** don't lose information the grid carried (each token's role description);
the legend list keeps it. The proportions are illustrative, not a new spec value — label
the strip "illustrative share of a typical post" so it can't be misread as a rule.

---

## Tier 2 — Craft details

### 5. Click-to-copy hex on every swatch

**What:** clicking any color slice/swatch copies its hex; a small inline "copied ✓"
confirmation appears for ~1.2s (no toast library, no global toast).

**How:** `navigator.clipboard.writeText()`; confirmation as a transient span swap inside
the swatch label. Keyboard: works on Enter/Space since slices are buttons. This is the main
practical payoff of the page for day-to-day work.

### 6. Scrollspy navigation

**What:** the page is ~10,000px tall and the toc chips scroll away. Make the section nav
sticky (a slim horizontal bar that condenses from the chip grid once the masthead scrolls
off), with the current section highlighted via IntersectionObserver.

**How:** `position: sticky` wrapper; a condensed variant of the existing `.toc` (numbers
only + label on hover at narrow widths); IntersectionObserver with `rootMargin` tuned so
the active state flips near the top third. Keep the theme switcher clear of it (switcher is
fixed top-right; sticky bar should reserve right padding or sit below it at narrow
widths — currently the switcher already overlaps chip rows around 800px wide; this item
should fix that collision properly).

### 7. Interactive gradient bar

**What:** a small slider under the `gradient_bar` demo driving `frac` continuously: bar
width and fill sample the real MAGNITUDE_CMAP live, with the outlined-value treatment
(white bold, ink stroke) riding the bar tip — inside the tip when width > threshold,
outside when not, demonstrating the §08 outlined-value rule at the same time.

**How:** `<input type="range">` + ~20 lines of JS interpolating the three cmap stops in
sRGB (piecewise-linear is fine for a demo; note it approximates matplotlib's colormap).
Label the slider with the current frac value. This makes the two co-encodings (width +
fill) tangible.

### 8. One orchestrated load moment

**What:** a single restrained entrance on first paint: the band draws in from the left
(~300ms), the masthead title settles from 98% scale/0 opacity (~250ms, ease-out-quint),
nothing else animates. No scroll-triggered reveals anywhere.

**How:** CSS animations on `.band` and `.masthead h1` only, declared as
enhancement-on-top-of-visible (elements are fully visible without the animation class —
never gate visibility on animation). Full `prefers-reduced-motion: reduce` opt-out already
exists globally; verify it kills these.

---

## Tier 3 — De-slop insurance

### 9. Vary the card rhythm

**What:** `spec-item`, `comp`, and note rows are uniformly structured bordered boxes; the
page reads as "every block is the same box." Break the cadence deliberately:
- let selected demos go full-bleed inside their `comp` card (shot map, table) instead of
  sitting in a second nested canvas card — **nested-box-in-box is the main offender**;
- render NOTE/RULE annotations as margin notes (small, hanging in the left gutter on wide
  viewports) instead of stacked label+text rows;
- let §11 grid rules lose their boxes entirely — five numbered lines with generous spacing
  read stronger than five identical bordered rows.

**Why:** rhythm variance is what separates "designed" from "generated" at a glance; the
content doesn't change at all.

**Watch out:** the white canvas card is load-bearing where it marks "this is the graphics
spec surface" — keep it there (header demo, footer demo, faces, chips, player row). Only
remove *decorative* box nesting, never the semantic white canvas.

### 10. Favicon + tab polish

**What:** an inline SVG favicon (data URI): simplest ownable mark is a basketball-seams
circle in RED on white, or a red square with the white "one-idea" canvas rectangle. Keeps
the tab from rendering the default globe next to the page title.

**How:** `<link rel="icon" href="data:image/svg+xml,...">`, one line, no asset file.
Note: this is a *page* favicon, not the parked account logo decision (DESIGN.md §1) — do
not accidentally ship a logo; keep it abstract.

---

## Critique results (`/impeccable critique design-system.html`, 2026-07-12)

Method: dual-agent (independent design-director review + deterministic detector run).
Score: **34/40** (Good band). Full report archived at
`.impeccable/critique/2026-07-12T21-39-12Z__design-system-html.md` — `/impeccable polish`
reads that snapshot as its backlog automatically. First critique run for this target.

**Verdict:** not AI slop; reads hand-made. The two-layer architecture, real-render
anatomies, and production-scar warn boxes carry it. The weaknesses are rhythm (the §08
valley of seven near-identical cards) and a handful of concrete defects below.

### Confirmed defects (fix before or alongside the ten opportunities)

| Pri | Defect | Fix |
|---|---|---|
| P1 | §09 anatomy pin 1 sits on the first letter of every mock's title (all four anatomies) | Move pins into whitespace per render, or switch to outlined ring markers / side-gutter callout lines (Goldsberry-style). Overlaps opportunity #2. |
| P1 | Horizontal overflow at ~390px: long mono tokens (`summer_league_report._player_table_image()`) clip masthead meta, TOC, `.src` labels; switcher partly offscreen | `overflow-wrap:anywhere` on `code`, `.src`, `.sig`, `.comp-src`; re-test at 390px |
| P2 | §-cross-references ("§04", "§06") are plain text on a ~13,500px page; no back-to-top | Wrap in `<a href="#sNN">`; opportunity #6 (scrollspy) covers the nav half |
| P2 | Mobile theme buttons lose accessible names (`.sw-name` display:none removes text; four unnamed near-twin dots) | `aria-label` on each `.sw-btn` |
| P3 | Swatch color chips have no border: BULLS_BLACK/INK merge into Blackout panel, RED into Hardwood card | 1px inset hairline on `.chip` (colormap `.strip` already does this) |
| P3 | §09 pin numbers are bare `<span>`s; screen readers hear stray "1 2 3 4 5" before the image | `aria-hidden="true"` on overlay pins (legend list carries the numbers) |
| P3 | Hardwood muted `#F4D9CC` on `#BE0E3B` ≈ 4.7:1 — passes AA with no headroom; weakest at `.tag.parked` .62rem mono | Nudge Hardwood muted lighter or bump smallest mono sizes |

### Judgment findings worth folding into the tiers

- **Numbering collision:** page §04 (Header) ≠ DESIGN.md §5 (Header); inline refs never say
  which numbering they use. Cheapest fix: make § refs links (they then self-disambiguate)
  and keep the `DESIGN.md §n` source pointers as the only DESIGN.md-numbered references.
- **§08 is quietly becoming the real spec:** chip 118×52 r10, rail 280×88 r12,
  `PLAYER_ROW_HEIGHT=173`, and the court-line color trio exist nowhere in DESIGN.md.
  Decide: DESIGN.md absorbs them, or formally delegates component-level values to this
  page. (Owner decision — flag, don't resolve unilaterally.)
- **§01 diverging colormap shows no colorblind caveat** although PRODUCT.md records the
  red→green risk and the SIGN RULE mitigation sits far away in §08. One line beside the
  swatch shows the system knows its own weakness.
- **Type specimens are a missed brand beat:** replace "Aa 0123" with Bulls lines
  ("CALEB WILSON · 35 PTS") so even §02 feels like the account.
- **Emphasis grammar stated three times** (§08 ×2, §10) — consolidate to one canonical
  statement plus short pointers.
- **TOC wraps unbalanced** (9+4 at 1280px); the sticky-nav work (#6) should rebalance it.
- Repo hygiene (outside the page): `docs/mocks/` contains two mis-dated
  `2025-07-14-summer-league-report-*` files next to the 2026-07-10 set — confirm and
  rename/remove with the user.

### Detector + mechanical facts (Assessment B)

Detector: 1 file-level warning (`em-dash-overuse`, count inflated by the five intentional
"—" spec glyphs — classified false positive; the last genuine prose em dash was fixed this
run). `numbered-section-markers` suppressed by config. Mechanical a11y: 0 missing alts,
working `aria-pressed`, clean heading order, `:focus-visible` present,
`prefers-reduced-motion` present.

### Open questions from the critique (for the owner, not the implementing agent)

1. Do four doc themes earn their QA surface, or would one impeccable Jersey theme be more
   on-message? (Three themes shipped with the contrast nits above.)
2. Should DESIGN.md absorb §08's component values, or delegate component truth to this page?
3. Pins vs. side-gutter callout lines for the anatomies?

---

## Constraints for the implementing agent

1. **The two-layer rule is inviolable:** doc chrome themes; graphic spec constants
   (`--g-*`) and white canvas cards do not theme.
2. **Fidelity to DESIGN.md:** the page documents the system; never change a documented
   value while polishing. If a spec value looks wrong, flag it, don't fix it silently.
3. **Fonts:** Academic M54 + Archivo load from `assets/fonts/` (relative paths); theme
   faces (Barlow Semi Condensed, Libre Franklin, IBM Plex Sans) come from Google Fonts with
   system fallbacks. Academic M54 has no "&" or "-" glyphs — the `.amp` span pattern
   handles ampersands in headings.
4. **No new dependencies, no build step.** Single hand-authored file, vanilla JS only.
5. **Reduced motion:** every animation added needs to die under
   `prefers-reduced-motion: reduce` (a global kill rule exists; verify per addition).
6. **Detector hygiene:** `numbered-section-markers` is suppressed by config (user-confirmed
   convention). Em dashes in prose were deliberately removed 2026-07-12 — don't reintroduce
   them (the "—" data glyphs in swatch names and table-missing values are spec content and
   stay). Reflex-reject fonts (Space Grotesk was already removed) must not come back.
7. **Verify in all four themes and at mobile width** after each tier; the earlier
   switcher-overlaps-toc collision (~800px) is a known issue item #6 should resolve.
