# Maintaining legacy Python pages

Read only when maintaining a renderer that composes an entire page in Python. New posts follow
[DESIGN.md](../../DESIGN.md): transparent Python chart, Canva page.

[`house.py`](../../bulls/graphics/house.py) still provides `new_canvas`, `draw_header`,
`draw_fitted_title`, `draw_subtitle`, `draw_jersey_stripe`, `draw_footer`, and `save_post`. Their theme
and font APIs remain for old callers. Use [season_shape_post.py](../../scripts/prototypes/season_shape_post.py)
as a full-page example. `THEMES` and the palette values in code are the compatibility reference;
do not duplicate their complete table in current guidance or add theme switches to new posts.

Existing page geometry is 1080×1350 with 60-pixel side margins and full-bleed axes; previews use
150 DPI and final exports 300 DPI. The 16-pixel jersey band has 4/2/4/2/4-pixel colored segments.
Titles fit within width minus 120, with 7-point red outline and 3.5-point white gap. The subtitle
baseline is height minus 168, kicker height minus 206, footer baseline 40. Footer data source sits
left and authorship at x=1020. Compatibility font helpers now resolve to Helvetica.

Keep prototype-specific measurements with that prototype. Avoid converting all historical renderers
as a prerequisite for a new post. Remove an old shared API only after checking its actual callers
and verifying affected existing renders.

The old HTML design-system companion is retired. HTML/CSS/SVG page composition was tried and
rejected; this does not prohibit the existing Great Tables → `nokap.from_html` → PNG path for tables.
Historical draft treatments remain in version history rather than in mandatory design instructions.
