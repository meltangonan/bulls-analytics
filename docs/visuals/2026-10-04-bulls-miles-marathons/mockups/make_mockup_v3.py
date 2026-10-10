"""Throwaway HTML mockup: runner faces, round 2. Numbers come from data/top10.csv."""
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


rows = ''.join(f'''
<div class="who"><span class="rk">{r['rank']}</span><div><b>{NAMES.get(r.player, r.player)}</b><small>{seasons(r)}</small></div></div>
<div class="track"><div class="trail" style="width:{r.marathons / MAX * 100}%"></div>
  <div class="runner" style="left:{r.marathons / MAX * 100}%"><div class="face"><img src="../data/portraits/{r.PLAYER_ID}.png" alt=""></div>
    <div class="bib"><em>{r.marathons:.1f}</em><small>marathons</small></div></div></div>
<div class="st">{r.miles:,.0f}</div><div class="st">{r.games}</div><div class="st b">{r.avg_mph:.2f}</div>'''
               for _, r in top.iterrows())

html = f'''<!doctype html><html><head><meta charset="utf-8"><title>Runner faces v3</title><style>
*{{box-sizing:border-box;margin:0}}
body{{width:1080px;height:1440px;background:#E9E5E1;font-family:Helvetica,Arial,sans-serif;color:#242424;
  padding:60px 44px;position:relative;overflow:hidden;font-variant-numeric:tabular-nums}}
.kicker{{font-size:22px;font-weight:700;color:#CE1141;letter-spacing:3px;margin-bottom:12px}}
h1{{font-size:60px;line-height:1.02;letter-spacing:-1.5px;font-weight:800}}
.sub{{font-size:22px;color:#5F5B57;margin-top:14px;line-height:1.3}}
.foot{{position:absolute;left:44px;right:44px;bottom:44px;font-size:18px;color:#7A736C;line-height:1.45}}
.grid{{display:grid;grid-template-columns:258px 1fr 84px 76px 66px;align-items:center}}
.top{{margin-top:110px;height:36px}}
.h{{font-size:17px;font-weight:700;color:#5F5B57;text-transform:uppercase;letter-spacing:.5px;text-align:right}}
.who{{display:flex;align-items:center;gap:10px}}.rk{{width:34px;text-align:right;font-size:32px;font-weight:800;color:#CE1141}}
.who b{{font-size:27px;display:block;white-space:nowrap}}.who small{{display:block;font-size:20px;color:#5F5B57;margin-top:3px}}
.track{{position:relative;height:88px;background:#CE1141;margin:0 22px 0 14px;border-bottom:3px solid #fff}}
.grid > .track:nth-child(2){{border-top:3px solid #fff}}
.track:after{{content:"";position:absolute;top:-3px;bottom:-3px;right:-20px;width:20px;background:{CHECKER}}}
.trail{{position:absolute;left:0;top:50%;border-top:3px dotted rgba(255,255,255,.8)}}
.runner{{position:absolute;top:0;bottom:0;transform:translateX(-100%);display:flex;align-items:center}}
.face{{align-self:flex-end;width:98px;height:98px;overflow:hidden;position:relative;margin-right:-26px;margin-bottom:3px;z-index:1}}.face img{{position:absolute;height:132px;width:auto;left:50%;top:0;transform:translateX(-50%)}}
.bib{{position:relative;z-index:0;background:#fff;border-radius:5px;padding:7px 12px 6px 22px;white-space:nowrap;text-align:center;font-weight:700}}
.bib:before,.bib:after{{content:"";position:absolute;top:5px;width:5px;height:5px;border-radius:50%;background:#242424}}
.bib:before{{left:15px}}.bib:after{{right:5px}}
.bib em{{display:block;font-style:normal;font-weight:800;font-size:30px;line-height:1}}.bib small{{display:block;font-size:14px;margin-top:2px}}
.st{{text-align:right;font-size:27px}}.st.b{{font-weight:700}}
</style></head><body>
<div class="kicker">CHICAGO MARATHON WEEK</div><h1>Most marathons run as a Bull</h1>
<p class="sub">Career miles run in games since tracking began in 2013-14, in marathons (26.2 miles)</p>
<div class="grid top"><div></div><div></div><div class="h">Miles</div><div class="h">Games</div><div class="h">MPH</div></div>
<div class="grid">{rows}</div>
<p class="foot">MPH is average speed while on the court. Includes playoffs and play-in.<br>
Source: NBA.com player tracking &middot; @chicagobullsdata</p>
</body></html>'''

out = HERE / 'v3-runner-faces.html'
out.write_text(html)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1080, 'height': 1440})
    page.goto(out.resolve().as_uri())
    page.wait_for_timeout(200)
    page.screenshot(path=str(HERE / 'v3-runner-faces.png'))
    # Report any runner that starts left of its lane (would cross the start line).
    print(page.evaluate('''[...document.querySelectorAll('.track')].map(t => {
        const r = t.querySelector('.runner').getBoundingClientRect(), tr = t.getBoundingClientRect();
        return Math.round(r.left - tr.left); })'''))
    browser.close()
