"""Throwaway HTML mockup for the finish-line format. Numbers come from data/top10.csv."""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
top = pd.read_csv(HERE.parent / 'data/top10.csv')
ON_ROSTER = {'Patrick Williams'}
NAMES = {'Jimmy Butler III': 'Jimmy Butler'}
MAX = top.marathons.max()

def name(r): return NAMES.get(r.player, r.player)
def seasons(r):
    a, b = r.first_season[:4], str(int(r.last_season[:4]) + 1)
    return f"{a}-{b[2:]}" if a != b else a
def pace(mph):
    m = 60 / mph; return f"{int(m)}:{round((m % 1) * 60):02d}"

# ---------- A: track lanes, runner bibs, finish line ----------
lanes = []
for i, r in top.iterrows():
    pct = r.marathons / MAX * 100
    tag = '<span class="tag">On roster</span>' if r.player in ON_ROSTER else ''
    lanes.append(f'''
    <div class="lane">
      <div class="who"><span class="rk">{r['rank']}</span><div><b>{name(r)}</b><small>{seasons(r)}{tag}</small></div></div>
      <div class="track"><div class="trail" style="width:{pct}%"></div>
        <div class="bib" style="left:{pct}%"><em>{r.marathons:.1f}</em></div></div>
      <div class="st">{r.games:,}</div><div class="st">{r.minutes:,.0f}</div><div class="st">{r.miles:,.0f}</div><div class="st b">{r.avg_mph:.2f}</div>
    </div>''')
ticks = ''.join(f'<div class="tick" style="left:{m / MAX * 100}%"><span>{m}</span></div>' for m in (10, 20, 30, 40))
page_a = f'''
<div class="page a">
  <div class="kicker">CHICAGO MARATHON WEEK</div>
  <h1>The Bulls who ran the most marathons</h1>
  <p class="sub">Career miles run in games as a Bull since tracking began in 2013-14, counted in marathons (26.2 miles)</p>
  <div class="head"><div class="who"></div><div class="track-h">{ticks}<b class="startl">START</b><b class="finl">FINISH</b></div>
    <div class="st h">Games</div><div class="st h">Min</div><div class="st h">Miles</div><div class="st h">MPH</div></div>
  <div class="lanes">{''.join(lanes)}<div class="finish"></div><div class="start"></div></div>
  <p class="foot">Marathons on the bib. MPH is average speed while on the court. Includes playoffs and play-in.<br>Source: NBA.com player tracking &middot; @chicagobullsdata</p>
</div>'''

# ---------- B: race results board with finish banner ----------
rows = ''.join(f'''
  <div class="res{' gold' if r['rank']==1 else ''}"><span class="pl">{r['rank']}</span>
    <span class="nm"><b>{name(r)}</b>{'<span class="tag">On roster</span>' if r.player in ON_ROSTER else ''}<small>{seasons(r)} &middot; {r.games} games &middot; {r.minutes:,.0f} min</small></span>
    <span class="mar">{r.marathons:.1f}</span><span class="mi">{r.miles:,.0f}</span><span class="pc">{r.avg_mph:.2f}<small>{pace(r.avg_mph)}/mi</small></span></div>''' for _, r in top.iterrows())
page_b = f'''
<div class="page b">
  <div class="banner"><div class="checker"></div><div class="bt">FINISH</div><div class="checker"></div></div>
  <h1>Most marathons run as a Bull</h1>
  <p class="sub">Career miles run in games since tracking began in 2013-14. One marathon = 26.2 miles</p>
  <div class="res h"><span class="pl">Place</span><span class="nm">Runner</span><span class="mar">Marathons</span><span class="mi">Miles</span><span class="pc">MPH<small>pace</small></span></div>
  {rows}
  <p class="foot">MPH is average speed while on the court, standing time included. Includes playoffs and play-in.<br>Source: NBA.com player tracking &middot; @chicagobullsdata</p>
</div>'''

css = '''
*{box-sizing:border-box;margin:0}body{background:#bdb7b0;font-family:Helvetica,Arial,sans-serif;color:#242424;padding:24px}
.wrap{display:flex;gap:28px;flex-wrap:wrap;justify-content:center}.cap{font:600 14px Helvetica;margin:0 0 8px;color:#242424}
.scale{width:540px;height:720px;overflow:hidden}.page{width:1080px;height:1440px;transform:scale(.5);transform-origin:0 0;background:#E9E5E1;padding:64px 56px;position:relative}
h1{font-size:62px;line-height:1.02;letter-spacing:-1.5px;font-weight:800}.sub{font-size:25px;color:#5F5B57;margin:16px 0 0;line-height:1.3}
.foot{position:absolute;left:56px;right:56px;bottom:48px;font-size:19px;color:#7A736C;line-height:1.45}
.kicker{font-size:22px;font-weight:700;color:#CE1141;letter-spacing:3px;margin-bottom:14px}
.tag{display:inline-block;background:#242424;color:#fff;font-size:14px;font-weight:700;padding:3px 8px;border-radius:4px;margin-left:10px;vertical-align:4px;letter-spacing:.5px}
/* A */
.a .head,.a .lane{display:grid;grid-template-columns:250px 1fr 70px 82px 70px 64px;align-items:center}
.a .head{margin-top:80px;height:56px}.st{text-align:right;font-size:23px;font-variant-numeric:tabular-nums}.st.b{font-weight:700}.st.h{font-size:16px;font-weight:700;color:#5F5B57;text-transform:uppercase;letter-spacing:.5px;align-self:end;padding-bottom:6px}
.track-h{position:relative;height:100%;margin:0 34px 0 4px}.tick{position:absolute;top:22px;bottom:0;border-left:2px dashed #7A736C}.tick span{position:absolute;top:-24px;left:-12px;font-size:17px;font-weight:700;color:#5F5B57}
.startl,.finl{position:absolute;top:-34px;font-size:15px;letter-spacing:2px}.startl{left:-4px;color:#5F5B57}.finl{right:-58px;color:#242424}
.lanes{position:relative}.lane{height:88px}.who{display:flex;align-items:center;gap:14px;font-size:24px}.who small{display:block;font-size:16px;color:#5F5B57;margin-top:3px}
.rk{width:36px;font-size:30px;font-weight:800;color:#CE1141;text-align:right}
.track{position:relative;height:100%;background:#CE1141;margin:0 34px 0 4px;border-bottom:3px solid #fff}.lane:first-child .track{border-top:3px solid #fff}
.trail{position:absolute;left:0;top:50%;height:0;border-top:3px dotted rgba(255,255,255,.75)}
.bib{position:absolute;top:50%;transform:translate(-100%,-50%);background:#fff;border:2px solid #242424;border-radius:5px;padding:6px 10px 5px;min-width:74px;text-align:center}
.bib:before,.bib:after{content:"";position:absolute;top:5px;width:6px;height:6px;border-radius:50%;background:#242424}.bib:before{left:5px}.bib:after{right:5px}
.bib em{font-style:normal;font-weight:800;font-size:28px;font-variant-numeric:tabular-nums}
.finish{position:absolute;top:0;bottom:0;left:calc(250px + (100% - 250px - 286px) - 34px);width:22px;background:repeating-conic-gradient(#242424 0 25%,#fff 0 50%) 0 0/22px 22px}
.start{position:absolute;top:0;bottom:0;left:254px;width:4px;background:#fff}
/* B */
.banner{display:flex;align-items:center;gap:20px;margin:-64px -56px 44px;background:#242424;padding:18px 0}.checker{flex:1;height:44px;background:repeating-conic-gradient(#242424 0 25%,#fff 0 50%) 0 0/22px 22px}
.bt{color:#fff;font-weight:800;font-size:40px;letter-spacing:10px}
.res{display:grid;grid-template-columns:76px 1fr 150px 110px 120px;align-items:center;border-bottom:2px solid #B8B0A8;height:94px;font-variant-numeric:tabular-nums}
.res.h{height:48px;margin-top:36px;border-bottom:3px solid #242424}.res.h span{font-size:16px;font-weight:700;color:#5F5B57;text-transform:uppercase;letter-spacing:.5px}
.pl{font-size:34px;font-weight:800;color:#CE1141}.nm b{font-size:28px}.nm small{display:block;font-size:17px;color:#5F5B57;margin-top:4px}
.mar{text-align:right;font-size:42px;font-weight:800}.mi{text-align:right;font-size:24px}.pc{text-align:right;font-size:24px;font-weight:700}.pc small{display:block;font-size:15px;font-weight:400;color:#5F5B57}
.res.h .mar,.res.h .mi,.res.h .pc{text-align:right}.res.gold{background:#fff;margin:0 -14px;padding:0 14px;border-bottom-color:#242424}
'''
html = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marathon mockups</title><style>{css}</style></head><body><div class="wrap">
<div><p class="cap">A. Running track</p><div class="scale">{page_a}</div></div>
<div><p class="cap">B. Race results board</p><div class="scale">{page_b}</div></div>
</div></body></html>'''
(HERE / 'mockup.html').write_text(html)
print(HERE / 'mockup.html')
