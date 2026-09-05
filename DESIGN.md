# Chart design

Python produces verified chart assets; Canva assembles the post. **Notion owns editorial direction
and the live post brief.** Canva's Brand Kit and the user's current design own page typography,
background, and composition. This file owns the reusable chart contract, alongside
[`house.py`](bulls/graphics/house.py) and [`craft.py`](bulls/graphics/craft.py).

Read only the reference for the chart being changed:

| Working on | Reference |
|---|---|
| Tables, ranking cards, stat boxes, portraits | [Tables and cards](docs/design/tables-cards.md) |
| Courts, hex maps, twelve-zone charts | [Shot charts](docs/design/shot-charts.md) |
| Maintaining an older Python-composed page | [Legacy page system](docs/design/legacy.md) |

## Current chart contract

- Export a **transparent** asset, large enough for its placed size. Use 300 DPI for publish assets;
  pixel dimensions, not DPI metadata alone, determine sharpness. Crop to the content and needed
  breathing room; a chart asset does not need to fill a 4:5 page.
- Charts carry axes, names, values, references, and data annotations. Canva carries titles,
  subtitles, editorial framing, sources, coverage, qualification, and authorship. A chart's own
  qualification legend stays with its marks when needed to interpret them.
- Generate data-bound Canva copy from the same calculation as the chart. Optional verified summary
  cards may carry those numbers inside the asset; never copy a number by eye.
- Use `house.helvetica()` with `regular`, `bold`, `oblique`, or `bold_oblique`. It loads the actual
  face; requesting bold or italic by family name can silently return regular on macOS. The helper
  caches extracted licensed fonts locally and falls back to installed sans-serif elsewhere.
- Helvetica lacks arrow glyphs. Write “to” or draw a real arrow. Use a true minus (−) for negative
  comparisons and remove the sign when the displayed number rounds to zero.

## Color and hierarchy

| Token in `house.py` | Hex | Use |
|---|---|---|
| `BLACK` | `#242424` | All black chart text, marks, and rules |
| `RED` | `#CE1141` | Bulls red; deliberate emphasis |

**New charts take no theme.** Use these tokens and a few named local colors for scaffolding or a
specified data scale. Legacy `INK`, `BULLS_BLACK`, and `THEMES` exist for compatibility only.
Red and black establish the graphic's identity; the documented shot and table scales may use other
colors when they encode data. Direction must also be readable from labels or signed values.

Canva's light, low-saturation canvas varies. Check quiet lines and labels against the actual page,
including a darker warm background such as `#E9E5E1`. `#D8D2CA` is a proven quiet rule there;
`#E6E2DB` disappears. Prefer size and weight to increasingly pale text. Aim near 4.5:1 for small
source/qualification text; the user's accepted `#E9E5E1` treatment uses subtitle `#5F5B57` and footer
`#7A736C`, with the quieter footer an intentional exception.

## Composition and review

Use one clear payoff. Reference lines need short labels; dashed lines and weight distinguish them
without relying on color. Callouts should explain the pattern, with a usual budget of three or four.
Quadrant labels describe roles, not unsupported judgments; leave enough axis headroom that a label
cannot hide an outlier. A whole oblique row can signal a weaker qualification, explained on the page.

When the user supplies a visual reference, retain its structure and proportions while adapting the
palette and chart typeface. Any larger departure should be deliberate.

Judge the **downloaded Canva export at feed size**, usually 1080×1350. Check readable type, unclipped
marks, spacing, contrast, and visible source/coverage/qualification/authorship on each data-bearing
page. Reuse an established chart family before inventing another layout. Update this guide or its
specific reference together with the owning helper when a shared visual rule changes. Build,
archiving, and approval steps live in [POSTING_WORKFLOW.md](POSTING_WORKFLOW.md).
