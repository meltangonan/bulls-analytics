# Product

## Register

brand

## Platform

web

## Users

The everyday Bulls fan who would never call themselves a stats person. They meet the work
inside the Instagram feed, mid-scroll, and are hiring the account to show them a Bulls stat
they didn't know, as a chart clean enough to get in two seconds and pretty enough to stop
the scroll ("huh, didn't know that"). Secondary, as a bonus rather than a design target:
data-literate hoops nerds and the "top guys" of NBA data viz, whose reposts and respect are
gravy. Decision rule: when a detail would help a nerd but confuse a casual fan, the casual
fan wins.

## Product Purpose

@chicagobullsdata makes league-quality data storytelling specifically about the Chicago
Bulls — a corner that is empty for every NBA team. The deliverables are 1080×1350 Instagram
pages built either as complete Python renders or as Canva compositions from verified Python
chart/data assets; this repo is the studio and editor of record for the analysis, final downloads,
design system, and editorial playbook. Success is measured by
shares/sends per post, engagement rate, and community recognition from other Bulls pages
and the top viz accounts — belonging over raw follower count.

## Positioning

Chicago Bulls, charted. Basketball-University-quality data viz pointed entirely at the
Bulls, made legible and fun for any fan — not just stats people.

## Conversion & proof

- Primary CTA: follow the account. Secondary: send the post to a friend or group chat —
  the share is the engine that puts posts in front of non-followers.
- The line a visitor remembers after 10 seconds: "Chicago Bulls, charted."
- Belief ladder: this is about *my* team → I understood it instantly → that was genuinely
  new to me → they do this all the time → follow.
- Proof on hand: the live grid, the posted evidence in `idea-catalog.html`, and community
  recognition as it accrues; tracked qualitatively in `STRATEGY.md` rather than duplicated here.

## Brand Personality

Craft-proud and instantly legible. Every post should look like it belongs next to the best
NBA viz accounts (Basketball University, Kirk Goldsberry, Owen Phillips / The F5) while
staying readable to a normal fan in two seconds; clarity always beats cleverness. The
on-graphic voice is the settled "fan in the stands": first-person, wry, a notch above
meme-page — while captions speak as a knowledgeable Bulls watcher, simple and direct, with
no manufactured hooks or engagement bait.

## Anti-references

- Bulls fan/meme pages: ugly stat-dumps, hot takes, template meme content.
- Beautiful-but-inscrutable analytics charts that only stats people can decode.
- League-wide coverage — single-team focus is the whole point.
- Social-media-persona copy: manufactured hooks, slang, rhetorical questions, bait.
- The official Bulls brand itself: never trace, recolor, or imitate the team's trademark;
  riffing on red/black as a fan account is fine, the logo is team IP.

## Design Principles

1. Pretty AND instantly legible — the two-second bar rules out both stat-dumps and
   inscrutable beauty; if a casual fan can't get it fast, it doesn't ship.
2. The template is the brand — the shared canvas (header pattern, red/black/white
   thumbnail read, footer pair) is the identity; consistency compounds recognition.
3. One idea per post — the title states it; if the title needs "and," it's two posts.
4. Take the structure, not the look — adopt formats from the best accounts (F5 patterns,
   Basketball University boards) but always in the house visual system.
5. Analytical honesty is visible — verified facts only, qualification thresholds and
   sources printed on the graphic, signs always shown on net ratings.

## Accessibility & Inclusion

Legibility-first, tuned for the Instagram feed: Python full layouts export at 300 DPI; Canva pages
are checked from the downloaded 1080×1350 final. Both paths use generous type sizes and
high-contrast red/black/white as the meaningful palette. Known caveat: the table diverging
colormap (NET_CMAP) runs red-to-green, a
colorblind-unsafe pair — mitigated by always printing the sign on values (force_sign);
revisit the pair if a table post ever leans on color alone.
