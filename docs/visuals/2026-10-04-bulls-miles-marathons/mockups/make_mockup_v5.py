"""Throwaway HTML mockup: approved runner faces plus polish (covered shading, markers, shadows). Numbers come from data/top10.csv."""
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
top = pd.read_csv(HERE.parent / 'data/top10.csv')
NAMES = {'Jimmy Butler III': 'Jimmy Butler'}
MAX = top.marathons.max()
CHECKER = 'repeating-conic-gradient(#242424 0 25%,#fff 0 50%) 0 0/20px 20px'


def seasons(r):
    return f"{r.first_season[:4]}-{str(int(r.last_season[:4]) + 1)[2:]}"


MARKS = ''.join(f'<div class="mark" style="left:{m / MAX * 100}%"></div>' for m in (10, 20, 30, 40))
SCALE = ''.join(f'<span style="left:{m / MAX * 100}%">{m}</span>' for m in (10, 20, 30, 40))
rows = ''.join(f'''
<div class="who"><span class="rk">{r['rank']}</span><div><b>{NAMES.get(r.player, r.player).split()[-1]}</b><small>{seasons(r)}</small></div></div>
<div class="track"><div class="covered" style="width:{r.marathons / MAX * 100}%"></div>{MARKS}<div class="trail" style="width:{r.marathons / MAX * 100}%"></div>
  <div class="runner" style="left:{r.marathons / MAX * 100}%"><div class="face"><img src="../data/portraits/{r.PLAYER_ID}.png" alt=""></div>
    <div class="bib"><em>{r.marathons:.1f}</em><small>marathons</small></div></div></div>
<div class="st3"><b>{r.miles:,.0f} miles</b><span>{r.games} games</span><span>{r.avg_mph:.2f} MPH</span></div>'''
               for _, r in top.iterrows())

html = f'''<!doctype html><html><head><meta charset="utf-8"><title>Stacked stats</title><style>
*{{box-sizing:border-box;margin:0}}
body{{width:1080px;height:1440px;background:#E9E5E1;font-family:Helvetica,Arial,sans-serif;color:#242424;
  padding:60px 44px;position:relative;overflow:hidden;font-variant-numeric:tabular-nums}}
.kicker{{font-size:22px;font-weight:700;color:#CE1141;letter-spacing:3px;margin-bottom:12px}}
h1{{font-size:60px;line-height:1.02;letter-spacing:-1.5px;font-weight:800}}
.sub{{font-size:22px;color:#5F5B57;margin-top:14px;line-height:1.3}}
.foot{{position:absolute;left:44px;right:44px;bottom:44px;font-size:18px;color:#7A736C;line-height:1.45}}
.grid{{display:grid;grid-template-columns:186px 1fr 142px;align-items:center}}
.top{{margin-top:110px;height:36px}}
.h{{font-size:17px;font-weight:700;color:#242424;text-transform:uppercase;letter-spacing:.5px;text-align:center}}
.who{{display:flex;align-items:center;gap:10px}}.rk{{width:34px;text-align:right;font-size:32px;font-weight:800;color:#CE1141}}
.who b{{font-size:27px;display:block;white-space:nowrap}}.who small{{display:block;font-size:20px;color:#5F5B57;margin-top:3px}}
.track{{position:relative;height:88px;background:#EBA9B8;margin:0 22px 0 14px;border-bottom:3px solid #fff}}
.grid > .track:nth-child(2){{border-top:3px solid #fff}}
.lanes{{position:relative}}.finish{{position:absolute;top:0;bottom:0;right:{142 + 2}px;width:20px;background:{CHECKER}}}
.covered{{position:absolute;left:0;top:0;bottom:0;background:#CE1141}}
.mark{{position:absolute;top:0;bottom:0;border-left:2px dashed rgba(255,255,255,.55)}}
.scale{{position:relative;height:100%;margin:0 22px 0 14px}}.scale span{{position:absolute;top:6px;transform:translateX(-50%);font-size:15px;font-weight:700;color:#7A736C}}
.trail{{position:absolute;left:0;top:50%;border-top:3px dotted rgba(255,255,255,.8)}}
.runner{{position:absolute;top:0;bottom:0;transform:translateX(-100%);display:flex;align-items:center}}
.face{{align-self:flex-end;width:98px;height:98px;overflow:hidden;position:relative;margin-right:-26px;margin-bottom:3px;z-index:1}}.face img{{filter:drop-shadow(0 3px 4px rgba(0,0,0,.35));position:absolute;height:132px;width:auto;left:50%;top:0;transform:translateX(-50%)}}
.bib{{box-shadow:0 3px 7px rgba(0,0,0,.25);position:relative;z-index:0;background:#fff;border-radius:5px;padding:7px 12px 6px 22px;white-space:nowrap;text-align:center;font-weight:700}}
.bib:before,.bib:after{{content:"";position:absolute;top:5px;width:5px;height:5px;border-radius:50%;background:#242424}}
.bib:before{{left:15px}}.bib:after{{right:5px}}
.bib em{{display:block;font-style:normal;font-weight:800;font-size:30px;line-height:1}}.bib small{{display:block;font-size:14px;margin-top:2px}}
.st3{{padding-left:12px;display:flex;flex-direction:column;line-height:1.12;font-size:20px;color:#242424}}.st3 b{{font-size:24px}}.st3 span{{color:#242424}}
</style></head><body>
<div class="kicker">CHICAGO MARATHON WEEK</div><h1>Most marathons run as a Bull</h1>
<p class="sub">Career miles run in games since tracking began in 2013-14, in marathons (26.2 miles)</p>
<div class="grid top"></div>
<div class="grid lanes">{rows}<div class="finish"></div></div>
<div class="grid" style="height:30px"><div></div><div class="scale">{SCALE}</div></div>
<p class="foot">MPH is average speed while on the court. Includes playoffs and play-in.<br>
Source: NBA.com player tracking &middot; @chicagobullsdata</p>
</body></html>'''

out = HERE / 'v5-stacked-stats.html'
out.write_text(html)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1080, 'height': 1440})
    page.goto(out.resolve().as_uri())
    page.wait_for_timeout(200)
    page.screenshot(path=str(HERE / 'v5-stacked-stats.png'))
    # Report any runner that starts left of its lane (would cross the start line).
    print(page.evaluate('''[...document.querySelectorAll('.track')].map(t => {
        const r = t.querySelector('.runner').getBoundingClientRect(), tr = t.getBoundingClientRect();
        return Math.round(r.left - tr.left); })'''))
    browser.close()
