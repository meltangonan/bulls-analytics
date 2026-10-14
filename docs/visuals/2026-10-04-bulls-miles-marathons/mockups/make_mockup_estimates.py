"""Throwaway HTML mockup: estimated all-time slide plus a method slide. Not production code.

Numbers come from data/estimates-top15.csv and estimates-all.csv (bulls_miles_marathons_estimates.py).
Canva's serif title face is approximated with Georgia here.
"""
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
POST = HERE.parent
top = pd.read_csv(POST / 'data/estimates-top15.csv')
NAMES = {'Toni Kukoc': 'Toni Kukoč'}
MAX = top.marathons.max()
CHECKER = 'repeating-conic-gradient(#242424 0 25%,#fff 0 50%) 0 0/20px 20px'
STRIPES = 'repeating-linear-gradient(135deg,#CE1141 0 7px,#DD5A78 7px 12px)'
ERA_RATE = 0.0703


def years(r):
    end = r.last_season + 1
    return f"{r.first_season}-{str(end)[2:] if str(end)[:2] == str(r.first_season)[:2] else end}"


def pct(v):
    return v / MAX * 100


MARKS = ''.join(f'<div class="mark" style="--p:{m / MAX}"></div>' for m in (25, 50, 75, 100))
SCALE = ''.join(f'<span style="--p:{m / MAX}">{m}</span>' for m in (25, 50, 75, 100))


def row(r):
    measured = r.measured_miles / 26.2
    est_only = r.measured_share < 0.999
    bib = f'{r.marathons_lo:.0f}-{r.marathons_hi:.0f}' if est_only else f'{r.marathons:.1f}'
    stat3 = f'{r.measured_mph:.2f} MPH' if not est_only else '- MPH'
    tilde = '~' if est_only else ''
    return f'''
<div class="who"><span class="rk">{r['rank']}</span><div><b>{NAMES.get(r.player, r.player).split()[-1]}</b><small>{years(r)}</small></div></div>
<div class="track"><div class="est" style="--p:{r.marathons / MAX}"></div><div class="covered" style="--p:{measured / MAX}"></div>{MARKS}
  <div class="runner" style="--p:{r.marathons / MAX}"><div class="face"><img src="../data/portraits/{r.PLAYER_ID}.png" alt=""></div>
    <div class="bib"><em>{bib}</em><small>marathons</small></div></div></div>
<div class="st3"><b>{tilde}{r.miles:,.0f} miles</b><span>{r.minutes:,.0f} min</span><span>{stat3}</span></div>'''


BASE = '''
*{box-sizing:border-box;margin:0}
body{width:1080px;height:1440px;background:#E9E5E1;font-family:Helvetica,Arial,sans-serif;color:#242424;
  position:relative;overflow:hidden;font-variant-numeric:tabular-nums}
.trim{position:absolute;left:0;right:0;top:0;height:13px;background:linear-gradient(#CE1141 0 4px,#fff 4px 8px,#242424 8px 13px)}
h1{position:absolute;left:25px;top:48px;font-family:Georgia,serif;font-weight:700;font-size:62px;letter-spacing:-1.5px}
.sub{position:absolute;left:25px;top:118px;font-family:Georgia,serif;font-weight:700;font-style:italic;font-size:30px;color:#CE1141;letter-spacing:-.5px}
.foot{position:absolute;left:25px;right:25px;top:1409px;font-size:14.7px;color:#7A736C;display:flex;justify-content:space-between}
.foot b{font-weight:700}.handle{font-weight:700;font-size:16px;color:#CE1141}.handle i{font-style:normal;color:#242424}
'''

CHART_CSS = '''
.chart{position:absolute;left:25px;width:1030px;top:178px}
.grid{display:grid;grid-template-columns:max-content 1fr 168px;align-items:center}
.who{display:flex;align-items:center;gap:10px}.rk{width:34px;text-align:right;font-size:28px;font-weight:800;color:#CE1141}
.who b{font-size:27px;display:block;white-space:nowrap}.who small{display:block;font-size:20px;color:#5F5B57;margin-top:3px}
.track{position:relative;height:75px;background:#EBA9B8;margin:0 22px 0 12px;border-bottom:3px solid #fff}
.grid > .track:nth-child(2){border-top:3px solid #fff}
.lanes{position:relative}.finish{position:absolute;top:0;bottom:24px;right:170px;width:20px;background:CHECKER}
:root{--r:150px}.covered{position:absolute;left:0;top:0;bottom:0;width:calc((100% - var(--r)) * var(--p));background:#CE1141}
.est{position:absolute;left:0;top:0;bottom:0;width:calc((100% - var(--r)) * var(--p));background:STRIPES}
.mark{position:absolute;top:0;bottom:0;left:calc((100% - var(--r)) * var(--p));border-left:2px dashed rgba(255,255,255,.55)}
.range{position:absolute;bottom:7px;height:8px;border:2.5px solid #fff;border-top:none;z-index:2}
.scale{position:relative;height:24px;margin:0 22px 0 12px}.scale span{position:absolute;top:5px;left:calc((100% - var(--r)) * var(--p));transform:translateX(-50%);font-size:15px;font-weight:700;color:#7A736C}
.runner{position:absolute;top:0;bottom:0;left:calc((100% - var(--r)) * var(--p));transform:translateX(-40px);display:flex;align-items:center;z-index:3}
.face{align-self:flex-end;width:80px;height:80px;overflow:hidden;position:relative;margin-right:-21px;margin-bottom:3px;z-index:1}.face img{filter:drop-shadow(0 3px 4px rgba(0,0,0,.35));position:absolute;height:108px;width:auto;left:50%;top:0;transform:translateX(-50%)}
.bib{box-shadow:0 3px 7px rgba(0,0,0,.25);position:relative;z-index:0;background:#fff;border-radius:5px;padding:5px 10px 4px 23px;white-space:nowrap;text-align:center;font-weight:700}
.bib:before,.bib:after{content:"";position:absolute;top:5px;width:5px;height:5px;border-radius:50%;background:#242424}
.bib:before{left:15px}.bib:after{right:5px}
.bib em{display:block;font-style:normal;font-weight:800;font-size:26px;line-height:1}.bib small{display:block;font-size:12px;margin-top:1px}
.st3{padding-left:12px;display:flex;flex-direction:column;line-height:1;font-size:16px}.st3 b{font-size:20px;white-space:nowrap}.st3 span{margin-top:2px}.st3 span+span{margin-top:4px}
.key{display:flex;gap:26px;align-items:center;font-size:16px;font-weight:700;color:#242424;margin:0 0 12px 2px}
.key span{display:flex;align-items:center;gap:8px}.key i{display:inline-block;width:30px;height:16px}
.key .r{width:30px;height:9px;border:2.5px solid #242424;border-top:none}
'''.replace('CHECKER', CHECKER).replace('STRIPES', STRIPES)

FOOT = ('<div class="foot"><span>Data via NBA.com tracking and box scores | <b>1976-77 to 2025-26, regular season '
        'and playoffs | Estimates, method on next slide</b></span><span class="handle">chicago_bulls<i>[data]</i></span></div>')

chart_page = f'''<!doctype html><html><head><meta charset="utf-8"><style>{BASE}{CHART_CSS}</style></head><body>
<div class="trim"></div>
<h1>Estimated Bulls marathon leaders</h1>
<p class="sub">Career miles in games since 1976-77, estimated from minutes</p>
<div class="chart">
<div class="key"><span><i style="background:#CE1141"></i>Measured (2013-14 on)</span>
<span><i style="background:{STRIPES}"></i>Estimated from minutes</span></div>
<div class="grid lanes">{''.join(row(r) for _, r in top.iterrows())}<div></div><div class="scale">{SCALE}</div><div></div><div class="finish"></div></div>
</div>{FOOT}</body></html>'''

jordan = top.set_index('player').loc['Michael Jordan']
METHOD_CSS = '''
.sec{position:absolute;left:25px;right:25px}
.sec h2{display:flex;align-items:center;gap:16px;font-family:Georgia,serif;font-size:32px;padding-bottom:10px;border-bottom:2px solid #7A736C;margin-bottom:16px}
.sec h2 b{background:#CE1141;color:#fff;font-family:Helvetica,Arial,sans-serif;font-size:24px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;border-radius:4px}
.sec p{font-size:22px;line-height:1.42;margin:0 0 12px 56px;max-width:900px}
.sec p.f{font-weight:700}.sec p .red{color:#CE1141}
.ex{margin:6px 0 0 56px;background:#F6F3F0;border-radius:10px;padding:18px 22px;font-size:21px;line-height:1.5;box-shadow:0 2px 6px rgba(0,0,0,.08)}
.note{position:absolute;left:25px;right:25px;top:1180px;font-size:17px;font-style:italic;font-weight:700;color:#242424}
'''
method_page = f'''<!doctype html><html><head><meta charset="utf-8"><style>{BASE}{METHOD_CSS}</style></head><body>
<div class="trim"></div>
<h1>How we estimated the miles</h1>
<p class="sub">Measured since 2013-14, estimated from minutes before that</p>
<div class="sec" style="top:210px"><h2><b>1</b>What is measured</h2>
<p>Since 2013-14, cameras in every NBA arena track how far each player moves during games. Those miles are real
measurements: Zach LaVine's 1,093 miles as a Bull are counted, not estimated.</p></div>
<div class="sec" style="top:440px"><h2><b>2</b>How we estimated earlier seasons</h2>
<p>Before tracking, we only know minutes. Miles follow minutes closely, so for each Bulls season before 2013-14:</p>
<p class="f"><span class="red">Estimated miles</span> = minutes played &times; miles per minute</p>
<p>Players with enough tracked Bulls minutes (Hinrich, Noah, Rose) use their own measured pace. Everyone else uses
the Bulls average from 2013-14 to 2016-17: {ERA_RATE:.3f} miles per minute, about 3.4 miles per 48-minute game.</p>
<div class="ex"><b>Example: Michael Jordan</b><br>{jordan.minutes:,.0f} Bulls minutes, regular season and playoffs<br>
{jordan.minutes:,.0f} &times; {ERA_RATE:.4f} = {jordan.miles:,.0f} miles &divide; 26.2 = <b>{jordan.marathons:.0f} marathons</b></div></div>
<div class="sec" style="top:935px"><h2><b>3</b>How sure we are</h2>
<p>Minutes predict miles well: using a player's own pace, a tracked season lands within about 2% of the measured
miles. The ranges show a slower and a faster pace, and they can't capture how the speed of play changed between eras.</p></div>
<p class="note">*Estimates rank the order well, since minutes are exact; treat individual totals as approximate.</p>
<div class="foot"><span>Data via NBA.com player tracking and box scores</span><span class="handle">chicago_bulls<i>[data]</i></span></div>
</body></html>'''

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1080, 'height': 1440})
    for name, html in (('estimates-chart', chart_page), ('estimates-method', method_page)):
        path = HERE / f'{name}.html'
        path.write_text(html)
        page.goto(path.resolve().as_uri())
        page.wait_for_timeout(300)
        page.evaluate('''(() => {
            const rs = [...document.querySelectorAll('.runner')];
            if (!rs.length) return;
            const need = Math.max(...rs.map(r => { const f = r.querySelector('.face').getBoundingClientRect();
                return r.querySelector('.bib').getBoundingClientRect().right - (f.left + f.width / 2); }));
            document.documentElement.style.setProperty('--r', Math.ceil(need) + 4 + 'px'); })()''')
        page.screenshot(path=str(HERE / f'{name}.png'))
        print(HERE / f'{name}.png')
    browser.close()
