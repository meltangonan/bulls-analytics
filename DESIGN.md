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
  breathing room; a chart asset does not need to fill the page.
- For a full-width chart on a 1080×1440 Canva page, start around **1030 px placed width**
  (roughly 25 px side margins), usually aligned with the footer. This is a flexible default, not
  a minimum. Fit height to the actual subtitle-to-footer space; adjust row height or padding
  before crowding columns, and preserve proportions when placing the asset.
- Charts carry axes, names, values, references, and data annotations. Canva carries titles,
  subtitles, editorial framing, sources, coverage, qualification, and authorship. A chart's own
  qualification legend stays with its marks when needed to interpret them.
- Generate data-bound Canva copy from the same calculation as the chart. Optional verified summary
  cards may carry those numbers inside the asset; never copy a number by eye.
- Use `house.helvetica()` with `regular`, `bold`, `oblique`, or `bold_oblique`. It loads the actual
  face; requesting bold or italic by family name can silently return regular on macOS. The helper
  caches extracted licensed fonts locally. Elsewhere it prefers installed Nimbus Sans,
  then Arial or DejaVu Sans. Cloud uses Nimbus Sans from the `fonts-urw-base35` package;
  the Mac continues to use its system Helvetica. The fonts are visually close, not identical.
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
including a darker warm background such as `#E9E5E1`. Use `#B8B0A8` for structural table separators
on that background; reserve `#D8D2CA` for decorative or nonessential rules. `#E6E2DB` disappears.
Prefer size and weight to increasingly pale text. Aim near 4.5:1 for small
source/qualification text; the user's accepted `#E9E5E1` treatment uses subtitle `#5F5B57` and footer
`#7A736C`, with the quieter footer an intentional exception.

## Composition and review

Use one clear payoff. Reference lines need short labels; dashed lines and weight distinguish them
without relying on color. Callouts should explain the pattern, with a usual budget of three or four.
Quadrant labels describe roles, not unsupported judgments; leave enough axis headroom that a label
cannot hide an outlier. A whole oblique row can signal a weaker qualification, explained on the page.

When the user supplies a visual reference, retain its structure and proportions while adapting the
palette and chart typeface. Any larger departure should be deliberate.

While a new format is still taking shape, a quick mockup of the composed page can settle the design
before renderer code is written. Use whatever is fastest; a self-contained HTML page often helps,
since it can show whole pages or a carousel with real data at phone width. Keep the numbers coming
from Python. The usual next step ports the settled design to Python chart assets and Canva. HTML pages
exported as 1080×1440 PNGs are also an option for final assets: the postgame recap uses them (see its
package README), and other formats may follow. This path is still being evaluated, so choose it per
format with the user rather than by default.

HTML pages get the house serif from licensed desktop fonts on the user's Mac: Georgia Pro Condensed
Bold and Bold Italic, installed in `~/Library/Fonts` (bought 2026-10-07). Reference them by local name
only, `local('GeorgiaProCondensed-Bold')` and `local('GeorgiaProCondensed-BoldItalic')`, with Source
Serif 4 from Google Fonts as the fallback, and have the export report which face rendered. Never
commit, upload or embed the font files (base64 in a published artifact counts). Phone previews and
cloud runs therefore show the fallback, so export final PNGs on the Mac. Georgia Pro Condensed is also
in Canva's library; Canva posts still use the Brand Kit's Clarendon Narrow unless the user changes it.

Judge the **downloaded Canva export at feed size** (1080×1440 or 1080×1350). Check readable type, unclipped
marks, spacing, contrast, and visible source/coverage/qualification/authorship on each data-bearing
page. Reuse an established chart family before inventing another layout. Update this guide or its
specific reference together with the owning helper when a shared visual rule changes. Build,
archiving, and approval steps live in [POSTING_WORKFLOW.md](POSTING_WORKFLOW.md).
