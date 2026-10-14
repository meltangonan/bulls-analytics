"""Throwaway HTML mockups: four variations on the running-track format.

Numbers come from data/top10.csv. Each variation is a 1080x1440 page, screenshotted to PNG.
"""
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
top = pd.read_csv(HERE.parent / 'data/top10.csv')
ON_ROSTER = {'Patrick Williams'}
NAMES = {'Jimmy Butler III': 'Jimmy Butler'}
MAX = top.marathons.max()
CHECKER = 'repeating-conic-gradient(#242424 0 25%,#fff 0 50%) 0 0/22px 22px'


def name(r):
    return NAMES.get(r.player, r.player)


def last(r):
    return name(r).split()[-1]


def seasons(r):
    return f"{r.first_season[:4]}-{str(int(r.last_season[:4]) + 1)[2:]}"


def tag(r):
    return '<span class="tag">On roster</span>' if r.player in ON_ROSTER else ''


def pct(r, room=1.0):
    return r.marathons / MAX * 100 * room


BASE = f'''
*{{box-sizing:border-box;margin:0}}
body{{width:1080px;height:1440px;background:#E9E5E1;font-family:Helvetica,Arial,sans-serif;color:#242424;
  padding:60px 56px;position:relative;overflow:hidden;font-variant-numeric:tabular-nums}}
.kicker{{font-size:22px;font-weight:700;color:#CE1141;letter-spacing:3px;margin-bottom:12px}}
h1{{font-size:60px;line-height:1.02;letter-spacing:-1.5px;font-weight:800}}
.sub{{font-size:24px;color:#5F5B57;margin-top:14px;line-height:1.3}}
.foot{{position:absolute;left:56px;right:56px;bottom:44px;font-size:18px;color:#7A736C;line-height:1.45}}
.tag{{display:inline-block;background:#242424;color:#fff;font-size:13px;font-weight:700;padding:3px 7px;
  border-radius:4px;margin-left:8px;vertical-align:2px;letter-spacing:.5px}}
.bib{{background:#fff;border:2px solid #242424;border-radius:5px;padding:6px 10px 5px;text-align:center;position:relative}}
.bib:before,.bib:after{{content:"";position:absolute;top:5px;width:6px;height:6px;border-radius:50%;background:#242424}}
.bib:before{{left:5px}}.bib:after{{right:5px}}
.bib em{{font-style:normal;font-weight:800;font-size:28px;display:block;line-height:1}}
.bib small{{display:block;font-size:13px;color:#5F5B57;margin-top:2px}}
.h{{font-size:15px;font-weight:700;color:#5F5B57;text-transform:uppercase;letter-spacing:.5px}}
.st{{text-align:right;font-size:23px}}.st.b{{font-weight:700}}
.who b{{font-size:24px;display:block}}.who small{{display:block;font-size:16px;color:#5F5B57;margin-top:3px}}
.checker{{background:{CHECKER}}}
'''
HEAD = '''<div class="kicker">CHICAGO MARATHON WEEK</div><h1>Most marathons run as a Bull</h1>
<p class="sub">Career miles run in games since tracking began in 2013-14, counted in marathons (26.2 miles)</p>'''
FOOT = ('<p class="foot">{note} MPH is average speed while on the court. Includes playoffs and play-in.'
        '<br>Source: NBA.com player tracking &middot; @chicagobullsdata</p>')


def page(title, css, body):
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>'
            f'<style>{BASE}{css}</style></head><body>{HEAD}{body}</body></html>')


def painted():
    lanes = ''.join(f'''<div class="lane"><div class="who"><b>{name(r)}</b><small>{seasons(r)}{tag(r)}</small></div>
      <div class="track"><span class="paint">{r['rank']}</span><div class="trail" style="width:{pct(r)}%"></div>
        <div class="bib" style="left:{pct(r)}%"><em>{r.marathons:.1f}</em><small>{r.miles:,.0f} mi</small></div></div>
      <div class="st">{r.games}</div><div class="st">{r.minutes:,.0f}</div><div class="st b">{r.avg_mph:.2f}</div></div>'''
                    for _, r in top.iterrows())
    ticks = ''.join(f'<div class="tick" style="left:{m / MAX * 100}%"><span>{m}</span></div>' for m in (10, 20, 30, 40))
    css = '''
.grid{display:grid;grid-template-columns:230px 1fr 64px 92px 72px;align-items:center}
.top{margin-top:70px;height:56px}.top .h{align-self:end;padding-bottom:6px;text-align:right}
.scale{position:relative;height:100%;margin-right:30px}
.tick{position:absolute;top:24px;bottom:0;border-left:2px dashed #7A736C}.tick span{position:absolute;top:-24px;left:-11px;font-size:17px;font-weight:700;color:#5F5B57}
.fin{position:absolute;right:-50px;top:-30px;font-size:15px;font-weight:700;letter-spacing:2px}
.lanes{position:relative}.lane{display:contents}
.track{position:relative;height:92px;background:#CE1141;margin-right:30px;border-bottom:3px solid #fff}
.lane:first-child .track{border-top:3px solid #fff}
.paint{position:absolute;left:12px;top:50%;transform:translateY(-50%);font-size:46px;font-weight:800;color:rgba(255,255,255,.35)}
.trail{position:absolute;left:0;top:50%;border-top:3px dotted rgba(255,255,255,.8)}
.track .bib{position:absolute;top:50%;transform:translate(-100%,-50%);min-width:82px}
.finish{position:absolute;top:0;bottom:0;right:8px;width:22px}
'''
    body = f'''<div class="grid top"><div></div><div class="scale">{ticks}<b class="fin">FINISH</b></div>
      <div class="h" style="text-align:right">Games</div><div class="h" style="text-align:right">Min</div><div class="h" style="text-align:right">MPH</div></div>
      <div class="grid lanes">{lanes}</div>{FOOT.format(note="Lane = rank. Marathons on the bib.")}'''
    body = body.replace('<div class="grid lanes">', '<div class="grid lanes" style="position:relative">')
    return page('Painted lanes', css + '.track:after{content:"";position:absolute;top:-3px;bottom:-3px;right:-22px;width:22px;background:' + CHECKER + '}', body)


def faces():
    lanes = ''.join(f'''<div class="who"><span class="rk">{r['rank']}</span><div><b>{name(r)}</b><small>{seasons(r)}{tag(r)}</small></div></div>
      <div class="track"><div class="trail" style="width:{pct(r)}%"></div>
        <div class="runner" style="left:{pct(r)}%"><img src="../data/portraits/{r.PLAYER_ID}.png"><div class="bib"><em>{r.marathons:.1f}</em></div></div></div>
      <div class="st">{r.games}</div><div class="st">{r.minutes:,.0f}</div><div class="st b">{r.avg_mph:.2f}</div>'''
                    for _, r in top.iterrows())
    css = '''
.grid{display:grid;grid-template-columns:250px 1fr 64px 92px 72px;align-items:center}
.top{margin-top:44px;height:40px}.top .h{text-align:right}
.who{display:flex;align-items:center;gap:12px}.rk{width:34px;text-align:right;font-size:30px;font-weight:800;color:#CE1141}
.track{position:relative;height:92px;background:#CE1141;margin-right:30px;border-bottom:3px solid #fff}
.track:after{content:"";position:absolute;top:-3px;bottom:-3px;right:-22px;width:22px;background:''' + CHECKER + '''}
.trail{position:absolute;left:0;top:50%;border-top:3px dotted rgba(255,255,255,.8)}
.runner{position:absolute;top:2px;bottom:2px;transform:translateX(-100%);display:flex;align-items:center}
.runner img{width:78px;height:78px;border-radius:50%;object-fit:cover;object-position:50% 0;background:#E9E5E1;border:3px solid #fff;margin-right:-10px;position:relative;z-index:1}
.runner .bib{padding:6px 9px 5px 14px;min-width:76px}
.fin{font-size:15px;font-weight:700;letter-spacing:2px;text-align:right;padding-right:0}
'''
    body = f'''<div class="grid top"><div></div><div class="fin" style="margin-right:-48px;position:relative;top:-22px">FINISH</div>
      <div class="h">Games</div><div class="h">Min</div><div class="h">MPH</div></div>
      <div class="grid">{lanes}</div>{FOOT.format(note="Marathons on the bib.")}'''
    return page('Runner faces', css, body)


def vertical():
    cols = ''.join(f'''<div class="col"><div class="vtrack"><div class="vtrail" style="height:{pct(r, .92)}%"></div>
        <div class="bib" style="bottom:{pct(r, .92)}%"><em>{r.marathons:.1f}</em></div><span class="paint">{r['rank']}</span></div>
      <b class="nm">{last(r)}</b><div class="s">{r.games}</div><div class="s">{r.minutes:,.0f}</div><div class="s b">{r.avg_mph:.2f}</div></div>'''
                   for _, r in top.iterrows())
    css = '''
.race{position:absolute;left:56px;right:56px;top:300px;display:flex}
.labels{width:84px;padding-top:740px}.labels div{height:34px;font-size:14px;font-weight:700;color:#5F5B57;text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center}
.labels .gap{height:44px}
.banner{position:absolute;left:84px;right:0;top:-46px;height:44px;display:flex;align-items:center;justify-content:center}
.banner span{background:#242424;color:#fff;font-weight:800;font-size:22px;letter-spacing:8px;padding:6px 14px}
.col{flex:1;text-align:center}
.vtrack{position:relative;height:720px;background:#CE1141;border-right:3px solid #fff;margin-bottom:20px}
.col:first-of-type .vtrack{border-left:3px solid #fff}
.vtrail{position:absolute;bottom:0;left:50%;border-left:3px dotted rgba(255,255,255,.8)}
.vtrack .bib{position:absolute;left:50%;transform:translate(-50%,50%);padding:6px 4px 5px;min-width:70px}
.vtrack .bib em{font-size:24px}
.paint{position:absolute;bottom:10px;left:0;right:0;font-size:40px;font-weight:800;color:rgba(255,255,255,.4)}
.nm{display:block;font-size:17px;height:24px;margin-bottom:20px}
.s{height:34px;font-size:19px;display:flex;align-items:center;justify-content:center}.s.b{font-weight:700}
.tick{position:absolute;left:84px;right:0;border-top:2px dashed rgba(255,255,255,.55)}
.tick span{position:absolute;left:-40px;top:-11px;font-size:16px;font-weight:700;color:#5F5B57}
'''
    ticks = ''.join(f'<div class="tick" style="bottom:{720 - 720 * .92 * m / MAX}px;top:{720 - 720 * .92 * m / MAX}px;height:0"><span>{m}</span></div>'
                    for m in (10, 20, 30, 40))
    body = f'''<div class="race"><div class="banner checker"><span>FINISH</span></div>
      <div class="labels"><div class="gap"></div><div>Games</div><div>Min</div><div>MPH</div></div>{cols}{ticks}</div>
      {FOOT.format(note="Marathons on the bib; dashed lines every 10 marathons.")}'''
    return page('Vertical sprint', css, body)


def medals():
    def row(r):
        full, part = int(r.marathons), r.marathons % 1
        m = '<i></i>' * full + (f'<i class="p" style="--p:{part * 100:.0f}%"></i>' if part > 0.05 else '')
        return f'''<div class="who"><span class="rk">{r['rank']}</span><div><b>{name(r)}</b><small>{seasons(r)}{tag(r)}</small></div></div>
          <div class="track"><div class="medals">{m}</div><b class="n">{r.marathons:.1f}</b></div>
          <div class="st">{r.games}</div><div class="st">{r.minutes:,.0f}</div><div class="st b">{r.avg_mph:.2f}</div>'''
    css = '''
.grid{display:grid;grid-template-columns:250px 1fr 64px 92px 72px;align-items:center}
.top{margin-top:44px;height:40px}.top .h{text-align:right}
.who{display:flex;align-items:center;gap:12px}.rk{width:34px;text-align:right;font-size:30px;font-weight:800;color:#CE1141}
.track{position:relative;height:92px;background:#CE1141;margin-right:30px;border-bottom:3px solid #fff;display:flex;align-items:center;padding:0 10px}
.grid > .track:nth-child(2){border-top:3px solid #fff}
.track:after{content:"";position:absolute;top:-3px;bottom:-3px;right:-22px;width:22px;background:''' + CHECKER + '''}
.medals{display:grid;grid-template-columns:repeat(21,15px);gap:3px 2px;width:357px}
.medals i{width:15px;height:15px;border-radius:50%;background:#F2C14E;border:2px solid #fff}
.medals i.p{background:linear-gradient(90deg,#F2C14E var(--p),rgba(255,255,255,.25) var(--p))}
.n{position:absolute;right:10px;color:#fff;font-size:28px;font-weight:800}
.key{display:flex;align-items:center;gap:8px;font-size:17px;color:#5F5B57;margin-top:18px}
.key i{width:17px;height:17px;border-radius:50%;background:#F2C14E;border:2px solid #242424;display:inline-block}
.fin{font-size:15px;font-weight:700;letter-spacing:2px;text-align:right}
'''
    body = f'''<div class="key"><i></i> = one marathon finished (26.2 miles)</div>
      <div class="grid top"><div></div><div class="fin" style="margin-right:-48px;position:relative;top:-22px">FINISH</div>
      <div class="h">Games</div><div class="h">Min</div><div class="h">MPH</div></div>
      <div class="grid">{''.join(row(r) for _, r in top.iterrows())}</div>{FOOT.format(note="")}'''
    return page('Finisher medals', css, body)


VARIANTS = {'v2-1-painted-lanes': painted, 'v2-2-runner-faces': faces,
            'v2-3-vertical-sprint': vertical, 'v2-4-finisher-medals': medals}

with sync_playwright() as p:
    browser = p.chromium.launch()
    shot = browser.new_page(viewport={'width': 1080, 'height': 1440})
    for slug, build in VARIANTS.items():
        html = HERE / f'{slug}.html'
        html.write_text(build())
        shot.goto(html.resolve().as_uri())
        shot.wait_for_timeout(200)
        shot.screenshot(path=str(HERE / f'{slug}.png'))
        print(HERE / f'{slug}.png')
    browser.close()
