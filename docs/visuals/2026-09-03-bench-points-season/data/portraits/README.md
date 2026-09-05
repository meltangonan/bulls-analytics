# Hand-sourced portraits

The NBA CDN serves a grey silhouette for these two players rather than a
headshot, so the post carries its own copies. `bench_points_leaders.portrait_path`
prefers this folder over the shared `cache/headshots`.

Both were verified against the CDN on 2026-09-03: a request to
`https://cdn.nba.com/headshots/nba/latest/1040x760/<id>.png` returns HTTP 200
with a ~12 KB body, which is the silhouette placeholder, not a real portrait
(`DESIGN.md` §5 — a real headshot is 50–200 KB).

| File | Player | Source |
| --- | --- | --- |
| `101126.png` | Nate Robinson | Hand-sourced for the 2026-08-20 height ladder; copied here unchanged from `docs/visuals/2026-09-01-three-point-leaders/data/portraits/`. |
| `2033.png` | Marcus Fizer | Built 2026-09-03 from `2033-source.png`, supplied by the user — see below. |

## Marcus Fizer

No portrait file for Fizer (`PLAYER_ID` 2033) survives anywhere: not in the
shared `cache/headshots`, not in any worktree's cache, not in any post's
`portraits/` or `portraits_source/` folder, and not in git history. Both CDN
sizes return the silhouette. The 2026-08-14 rookie-landscape post drew a real
face for him because it fetched one into the gitignored shared cache in August;
that cache entry is gone and the CDN no longer serves it.

`2033-source.png` is the original the user supplied on 2026-09-03: a 416x440
NBA-style headshot on the blue studio backdrop, in a Bulls uniform. It is kept
next to the built file so the chain from source to render stays auditable. It is
not an NBA CDN download — check licensing before reusing it elsewhere
(`DESIGN.md` §5).

`2033.png` is built from it in two steps:

1. **The blue backdrop is keyed out.** Every other portrait here is a transparent
   PNG, so a solid background would have drawn as a blue rectangle sitting on the
   page. The key is a soft ramp on distance from the backdrop colour
   `(78, 106, 166)` — full transparency below 42, full opacity above 96 — so
   edges stay smooth rather than jagged. Only backdrop *connected to the border*
   is removed, so a dark or blue-ish pixel inside the subject can never be
   punched out.
2. **It is framed to match a real portrait.** Scaled and pasted so his content
   runs from row 40 to row 485 of the 486-row drawn band, with the band's bottom
   edge landing just below his chin (source row 315).

   **Both numbers are load-bearing.** Row 40 sits him among the real portraits,
   whose content begins at rows 11 (Korver), 33 (Gibson) and 53 (Gordon), so his
   row overlaps the row above it like every other. Ending the band at his chin
   rather than his shoulders keeps the jersey out, which is the rule the shared
   `HEADSHOT_CROP_FRACTION` enforces for everyone else.

An earlier attempt reconstructed him from the rookie post's rendered PNG — 93x96
px of real detail upscaled ~4.5x. That is superseded and should not be revived;
the supplied source is sharp.
