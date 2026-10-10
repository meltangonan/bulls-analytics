"""Render the Bulls career-marathons charts (runner-faces track design).

The design was settled as an HTML mockup and approved; this script renders that same HTML with
Chromium rather than porting it to matplotlib, so the assets match the approved design. Outputs, in
``output/bulls-miles-marathons/``, are transparent charts at 7x, placed 1030px wide on Canva chart
pages that carry the title, subtitle and footer:

* ``chart.png``            measured top 15 since 2013-14 (``data/top15.csv``)
* ``chart-estimates.png``  estimated top 15 since 1976-77 (``data/estimates-top15.csv``); solid red
  is measured distance, striped red is estimated, and the bib shows the estimate's range

The center of each face marks the player's value. The build fails if a face starts left of its
lane's start line, if a bib crosses the finish line, or if any stat block sits within 4px of its
lane's top or bottom edge.
"""
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
POST = ROOT / 'docs/visuals/2026-10-04-bulls-miles-marathons'
OUT = ROOT / 'output/bulls-miles-marathons'
NAMES = {'Jimmy Butler III': 'Jimmy Butler', 'Nikola Mirotic': 'Nikola Mirotić', 'Toni Kukoc': 'Toni Kukoč'}
CHECKER = 'repeating-conic-gradient(#242424 0 25%,#fff 0 50%) 0 0/20px 20px'
STRIPES = 'repeating-linear-gradient(135deg,#CE1141 0 7px,#DD5A78 7px 12px)'
MARATHON_MILES = 26.2

CSS = f'''
*{{box-sizing:border-box;margin:0}}
body{{width:1080px;background:transparent;font-family:Helvetica,Arial,sans-serif;color:#242424;
  padding:60px 44px;position:relative;font-variant-numeric:tabular-nums}}
.grid{{display:grid;grid-template-columns:max-content 1fr 162px;align-items:center}}
.top{{height:36px}}
.key{{display:flex;gap:26px;align-items:center;font-size:16px;font-weight:700;padding-left:2px}}
.key span{{display:flex;align-items:center;gap:8px}}.key i{{display:inline-block;width:30px;height:16px}}
.who{{display:flex;align-items:center;gap:10px}}.rk{{width:34px;text-align:right;font-size:28px;font-weight:800;color:#CE1141}}
.who b{{font-size:27px;display:block;white-space:nowrap}}.who small{{display:block;font-size:20px;color:#5F5B57;margin-top:3px}}
.track{{position:relative;height:74px;background:#EBA9B8;margin:0 22px 0 12px;border-bottom:3px solid #fff}}
.grid > .track:nth-child(2){{border-top:3px solid #fff}}
.lanes{{position:relative}}.finish{{position:absolute;top:0;bottom:24px;right:{162 + 2}px;width:20px;background:{CHECKER}}}
:root{{--r:120px}}
.covered,.est{{position:absolute;left:0;top:0;bottom:0;width:calc((100% - var(--r)) * var(--p))}}
.covered{{background:#CE1141}}.est{{background:{STRIPES}}}
.mark{{position:absolute;top:0;bottom:0;left:calc((100% - var(--r)) * var(--p));border-left:2px dashed rgba(255,255,255,.55)}}
.scale{{position:relative;height:24px;margin:0 22px 0 12px}}.scale span{{position:absolute;top:5px;left:calc((100% - var(--r)) * var(--p));transform:translateX(-50%);font-size:15px;font-weight:700;color:#7A736C}}
.trail{{position:absolute;left:0;top:50%;width:calc((100% - var(--r)) * var(--p));border-top:3px dotted rgba(255,255,255,.8)}}
.runner{{position:absolute;top:0;bottom:0;left:calc((100% - var(--r)) * var(--p));transform:translateX(-39px);display:flex;align-items:center}}
.face{{align-self:flex-end;width:78px;height:78px;overflow:hidden;position:relative;margin-right:-21px;margin-bottom:3px;z-index:1}}.face img{{filter:drop-shadow(0 3px 4px rgba(0,0,0,.35));position:absolute;height:105px;width:auto;left:50%;top:0;transform:translateX(-50%)}}
.bib{{box-shadow:0 3px 7px rgba(0,0,0,.25);position:relative;z-index:0;background:#fff;border-radius:5px;padding:5px 10px 4px 23px;white-space:nowrap;text-align:center;font-weight:700}}
.bib:before,.bib:after{{content:"";position:absolute;top:5px;width:5px;height:5px;border-radius:50%;background:#242424}}
.bib:before{{left:15px}}.bib:after{{right:5px}}
.bib em{{display:block;font-style:normal;font-weight:800;font-size:26px;line-height:1}}.bib small{{display:block;font-size:12px;margin-top:1px}}
.st3{{padding-left:12px;display:flex;flex-direction:column;line-height:1;font-size:16px}}.st3 b{{font-size:20px;white-space:nowrap}}.st3 span{{margin-top:2px}}.st3 span+span{{margin-top:4px}}
'''


def _portrait(player_id) -> str:
    return (POST / 'data/portraits' / f'{int(player_id)}.png').as_uri()


def _last(player: str) -> str:
    return NAMES.get(player, player).split()[-1]


def _lane(rank, name, years, fill, value, bib, stats) -> str:
    return f'''
<div class="who"><span class="rk">{rank}</span><div><b>{name}</b><small>{years}</small></div></div>
<div class="track">{fill}<div class="runner" style="--p:{value}">
  <div class="face"><img src="{bib[0]}" alt=""></div><div class="bib"><em>{bib[1]}</em><small>marathons</small></div></div></div>
<div class="st3"><b>{stats[0]}</b><span>{stats[1]}</span><span>{stats[2]}</span></div>'''


def _page(top_band: str, lanes: str, ticks, axis_max: float) -> str:
    marks = ''.join(f'<div class="mark" style="--p:{m / axis_max}"></div>' for m in ticks)
    scale = ''.join(f'<span style="--p:{m / axis_max}">{m}</span>' for m in ticks)
    lanes = lanes.replace('{MARKS}', marks)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f'<div class="grid top">{top_band}</div><div class="grid lanes">{lanes}<div></div>'
            f'<div class="scale">{scale}</div><div></div><div class="finish"></div></div></body></html>')


def measured_html() -> str:
    top = pd.read_csv(POST / 'data/top15.csv')
    axis_max = top.marathons.max()
    lanes = ''.join(_lane(
        r['rank'], _last(r.player), f"{r.first_season[:4]}-{str(int(r.last_season[:4]) + 1)[2:]}",
        f'<div class="covered" style="--p:{r.marathons / axis_max}"></div>{{MARKS}}'
        f'<div class="trail" style="--p:{r.marathons / axis_max}"></div>',
        r.marathons / axis_max, (_portrait(r.PLAYER_ID), f'{r.marathons:.1f}'),
        (f'{r.miles:,.0f} miles', f'{r.games} games', f'{r.avg_mph:.2f} MPH'))
        for _, r in top.iterrows())
    return _page('', lanes, (10, 20, 30, 40), axis_max)


def estimates_html() -> str:
    top = pd.read_csv(POST / 'data/estimates-top15.csv')
    axis_max = top.marathons.max()

    def years(r):
        end = r.last_season + 1
        return f"{r.first_season}-{str(end)[2:] if str(end)[:2] == str(r.first_season)[:2] else end}"

    lanes = []
    for _, r in top.iterrows():
        measured_only = r.measured_share >= 0.999
        # The bib shows the range; the face's position marks the single estimate.
        bib = f'{r.marathons:.1f}' if measured_only else f'{r.marathons_lo:.0f}-{r.marathons_hi:.0f}'
        lanes.append(_lane(
            r['rank'], _last(r.player), years(r),
            f'<div class="est" style="--p:{r.marathons / axis_max}"></div>'
            f'<div class="covered" style="--p:{r.measured_miles / MARATHON_MILES / axis_max}"></div>{{MARKS}}',
            r.marathons / axis_max, (_portrait(r.PLAYER_ID), bib),
            (f'{"" if measured_only else "~"}{r.miles:,.0f} miles', f'{r.minutes:,.0f} min',
             f'{r.measured_mph:.2f} MPH' if measured_only else '-')))
    key = (f'<div></div><div class="key"><span><i style="background:#CE1141"></i>Measured (2013-14 on)</span>'
           f'<span><i style="background:{STRIPES}"></i>Estimated from minutes</span></div><div></div>')
    return _page(key, ''.join(lanes), (25, 50, 75, 100), axis_max)


def render(page, html: str, name: str) -> None:
    html_path = OUT / f'{name}.html'
    html_path.write_text(html)
    page.goto(html_path.as_uri())
    page.wait_for_load_state('networkidle')
    # The face's center marks the value. Reserve just enough axis space after the leader for the
    # widest bib, so no bib crosses the finish line.
    page.evaluate('''(() => {
        const need = Math.max(...[...document.querySelectorAll('.runner')].map(r => {
            const f = r.querySelector('.face').getBoundingClientRect();
            return r.querySelector('.bib').getBoundingClientRect().right - (f.left + f.width / 2); }));
        document.documentElement.style.setProperty('--r', Math.ceil(need) + 4 + 'px'); })()''')
    starts = page.evaluate('''[...document.querySelectorAll('.track')].map(t =>
        t.querySelector('.face').getBoundingClientRect().left - t.getBoundingClientRect().left)''')
    overrun = page.evaluate('''Math.max(...[...document.querySelectorAll('.track')].map(t =>
        t.querySelector('.bib').getBoundingClientRect().right - t.getBoundingClientRect().right))''')
    stat_gaps = page.evaluate('''[...document.querySelectorAll('.track')].map(t => {
        const s = t.nextElementSibling.getBoundingClientRect(), r = t.getBoundingClientRect();
        return Math.min(s.top - r.top, r.bottom - s.bottom); })''')
    if min(starts) < 0:
        raise ValueError(f'{name}: a runner crosses its start line: {starts}')
    if overrun > 0:
        raise ValueError(f'{name}: a bib crosses the finish line by {overrun:.1f}px')
    if min(stat_gaps) < 4:
        raise ValueError(f'{name}: a stat block crowds its lane edge: {stat_gaps}')
    box = page.evaluate('''(() => {
        const els = [...document.querySelectorAll('.grid, .face, .bib')].map(e => e.getBoundingClientRect());
        const x0 = Math.min(...els.map(r => r.left)), y0 = Math.min(...els.map(r => r.top));
        const x1 = Math.max(...els.map(r => r.right)), y1 = Math.max(...els.map(r => r.bottom));
        return {x: Math.floor(x0) - 2, y: Math.floor(y0) - 2,
                width: Math.ceil(x1 - x0) + 4, height: Math.ceil(y1 - y0) + 4}; })()''')
    page.screenshot(path=str(OUT / f'{name}.png'), clip=box, omit_background=True)
    print(OUT / f'{name}.png', 'runner clearance', [round(x) for x in starts],
          'stat clearance', [round(x, 1) for x in stat_gaps])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1080, 'height': 2000}, device_scale_factor=7)
        render(page, measured_html(), 'chart')
        render(page, estimates_html(), 'chart-estimates')
        browser.close()


if __name__ == '__main__':
    main()
