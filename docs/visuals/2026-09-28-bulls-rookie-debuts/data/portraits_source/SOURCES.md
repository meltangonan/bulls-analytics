# Portrait sources

The NBA CDN serves a silhouette for six ranked players. Four reuse portraits framed for
earlier posts (`FRAMED_PORTRAITS` in `scripts/prototypes/bulls_rookie_debuts.py`); Jay Williams
reuses the rookie Game Score post's cut-out (`2026-09-18-rookie-game-scores/data/portraits/2398.png`).

Scott May (77490): headshot from his Ohio Basketball Hall of Fame 2007 inductee page,
https://ohiobasketballhalloffame.com/hall-of-fame/inductees/2007/scott-may.html
(image https://cdn.firespring.com/images/d28743f0-40c1-4bb8-bd8c-c4afd61db89a.jpeg, 233x241),
captured 2026-09-28; original in `originals/`. Background removed with macOS Vision
`VNGenerateForegroundInstanceMaskRequest` (largest subject, cropped to its extent) to give
`Scott May.png`, which `house.cut_out_flat_background` frames like an NBA headshot.
