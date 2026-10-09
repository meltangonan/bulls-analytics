"""Draft page, not in the recap yet: who set up whom, from the play-by-play's assist credits.

    venv/bin/python postgame-recaps/pipeline/pbp_page_draft.py 0022500248

Reads the game folder's pbp.csv and players.csv (already pulled by pull_game.py) and writes
output/postgame-recap/<id>/draft-assist-network.html and .png. PlayByPlayV3 names the passer only in a made
shot's text, "(Giddey 3 AST)", by last name without accents; it is matched to the Bulls player with that
family name. Every Bulls assist must be matched, and the total must equal the box score's assists.
"""
import math
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_mockup import portrait  # noqa: E402  house face crop as a data URI

HERE = Path(__file__).resolve().parent
from paths import OUTPUT, PORTRAITS, game_dir  # noqa: E402
BULLS = 1610612741
BG, K, R, FT, LR, RU = "#E9E5E1", "#242424", "#CE1141", "#7A736C", "#D8D2CA", "#B8B0A8"


def plain(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def assists(game_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    g = game_dir(game_id)
    pbp, players = pd.read_csv(g / "pbp.csv"), pd.read_csv(g / "players.csv")
    chi = players[players.teamId == BULLS]
    by_name = {plain(r.familyName): r.personId for r in chi.itertuples()}
    made = pbp[(pbp.teamId == BULLS) & (pbp.shotResult == "Made")].copy()
    made["passer_name"] = made.description.str.extract(r"\(([^()]+?) \d+ AST\)")[0]
    a = made.dropna(subset=["passer_name"])
    a = a.assign(passer=a.passer_name.map(lambda n: by_name.get(plain(n))))
    unmatched = a[a.passer.isna()].passer_name.unique().tolist()
    if unmatched:
        raise SystemExit(f"unmatched passers: {unmatched}")
    box = int(chi.assists.sum())
    if len(a) != box:
        raise SystemExit(f"play-by-play has {len(a)} Bulls assists, the box score {box}")
    pairs = (a.groupby(["passer", "personId"]).agg(n=("shotValue", "size"), pts=("shotValue", "sum"))
             .reset_index().rename(columns={"personId": "scorer"}))
    return pairs, chi


def t(x, y, s, txt, f=K, w=400, a="start", ff=None):
    fam = f' font-family="{ff}"' if ff else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{s}" fill="{f}" font-weight="{w}" text-anchor="{a}"{fam}>{txt}</text>'


def page(game_id: str) -> str:
    pairs, chi = assists(game_id)
    name = {r.personId: r.familyName for r in chi.itertuples()}
    involved = pd.concat([pairs.passer, pairs.scorer]).unique()
    given = pairs.groupby("passer").n.sum()
    got = pairs.groupby("scorer").n.sum()
    order = sorted(involved, key=lambda i: (-given.get(i, 0), -got.get(i, 0)))
    cx, cy, rad, nr = 540, 612, 292, 46
    pos = {pid: (cx + rad * math.sin(2 * math.pi * k / len(order)), cy - rad * math.cos(2 * math.pi * k / len(order)))
           for k, pid in enumerate(order)}
    heads = {pid: portrait(PORTRAITS / f"{pid}.png") for pid in order if (PORTRAITS / f"{pid}.png").exists()}
    s = [f'<rect width="1080" height="1440" fill="{BG}"/>',
         '<rect y="0" width="1080" height="4" fill="#C12744"/><rect y="4" width="1080" height="4" fill="#EFEEF1"/><rect y="8" width="1080" height="5" fill="#151F1B"/>',
         t(25, 104, 86, "Bulls assist network", w=900, ff="RecapSerif, 'Source Serif 4', Georgia, serif")]
    # Section title in the page's boxed style.
    s.append(f'<rect x="25" y="150" width="{len("Who set up whom") * 15.5 + 24:.0f}" height="41" fill="none" stroke="{K}" stroke-width="2.5"/>'
             + t(37, 181, 28, "Who set up whom", w=600))
    s.append(t(1055, 181, 20, f"Arrow from passer to scorer · {int(pairs.n.sum())} assists", f=FT, a="end"))
    # Edges first, so the portraits sit on top. Each curve bends toward the centre; width grows with assists.
    for r in pairs.sort_values("n").itertuples():
        (x1, y1), (x2, y2) = pos[r.passer], pos[r.scorer]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        qx, qy = mx + (cx - mx) * 0.35, my + (cy - my) * 0.35
        # Stop short of the scorer's circle for the arrowhead.
        d = math.hypot(x2 - qx, y2 - qy); ex, ey = x2 - (x2 - qx) / d * (nr + 8), y2 - (y2 - qy) / d * (nr + 8)
        sw = 2 + 3 * (r.n - 1)
        ang = math.atan2(ey - qy, ex - qx); ah = 10 + sw
        tip = f"{ex:.1f},{ey:.1f} {ex - ah * math.cos(ang - 0.45):.1f},{ey - ah * math.sin(ang - 0.45):.1f} {ex - ah * math.cos(ang + 0.45):.1f},{ey - ah * math.sin(ang + 0.45):.1f}"
        op = 0.25 + 0.25 * min(r.n, 3)
        s.append(f'<path d="M{x1:.1f},{y1:.1f} Q{qx:.1f},{qy:.1f} {ex:.1f},{ey:.1f}" fill="none" stroke="{R}" stroke-width="{sw}" stroke-opacity="{op:.2f}" stroke-linecap="round"/>'
                 f'<polygon points="{tip}" fill="{R}" fill-opacity="{op:.2f}"/>')
        if r.n >= 2:
            lx, ly = 0.25 * x1 + 0.5 * qx + 0.25 * ex, 0.25 * y1 + 0.5 * qy + 0.25 * ey
            s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="15" fill="{BG}" stroke="{R}" stroke-width="2"/>' + t(lx, ly + 7, 19, r.n, f=R, w=600, a="middle"))
    for pid, (x, y) in pos.items():
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{nr}" fill="{LR}"/>')
        if pid in heads:
            s.append(f'<image href="{heads[pid]}" x="{x - 44:.1f}" y="{y + nr * 0.92 - 88:.1f}" width="88" height="88"/>')
        out = (x - cx, y - cy); L = math.hypot(*out) or 1
        lx, ly = x + out[0] / L * (nr + 18), y + out[1] / L * (nr + 18)
        anchor = "middle" if abs(out[0]) < 60 else ("start" if out[0] > 0 else "end")
        ly += 30 if out[1] > 40 else (-26 if out[1] < -40 else 8)
        s.append(t(lx, ly, 21, name[pid], w=600, a=anchor)
                 + t(lx, ly + 22, 17, f"{int(given.get(pid, 0))} ast · {int(got.get(pid, 0))} assisted", f=FT, a=anchor))
    # Top connections: the three duos with the most assists, ties broken by points.
    s.append(f'<rect x="25" y="1052" width="{len("Top connections") * 15.5 + 24:.0f}" height="41" fill="none" stroke="{K}" stroke-width="2.5"/>'
             + t(37, 1083, 28, "Top connections", w=600) + f'<line x1="25" y1="1093" x2="1055" y2="1093" stroke="{K}" stroke-width="2.5"/>')
    top = pairs.sort_values(["n", "pts"], ascending=False).head(3)
    for k, r in enumerate(top.itertuples()):
        x0 = 25 + k * 352
        for j, pid in enumerate((r.passer, r.scorer)):
            hx = x0 + 44 + j * 104
            s.append(f'<circle cx="{hx}" cy="1170" r="40" fill="{LR}"/>')
            if pid in heads:
                s.append(f'<image href="{heads[pid]}" x="{hx - 39}" y="{1170 + 37 - 78}" width="78" height="78"/>')
        s.append(f'<path d="M{x0 + 88},1170 L{x0 + 100},1170" stroke="{R}" stroke-width="4"/><polygon points="{x0 + 106},1170 {x0 + 96},1163 {x0 + 96},1177" fill="{R}"/>')
        s.append(t(x0 + 96, 1244, 22, f"{name[r.passer]} to {name[r.scorer]}", w=600, a="middle")
                 + t(x0 + 96, 1272, 19, f"{r.n} assists, {r.pts} points", f=FT, a="middle"))
    s.append(t(25, 1424, 16, "Data via NBA.com play-by-play | Draft page, not in the recap yet", f=FT)
             + f'<text x="1055" y="1424" font-size="16" font-weight="600" text-anchor="end"><tspan fill="{R}">chicago_bulls</tspan><tspan fill="{K}">[data]</tspan></text>')
    return ("<!doctype html><html><head><meta charset='utf-8'><style>"
            "@font-face{font-family:RecapSans;font-weight:400;src:local('Geist-Regular')}"
            "@font-face{font-family:RecapSans;font-weight:600;src:local('Geist-SemiBold')}"
            "@font-face{font-family:RecapSerif;font-weight:900;src:local('GeorgiaProCondensed-Bold'),local('Georgia Pro Condensed Bold')}"
            "body{margin:0}svg{display:block;font-family:RecapSans,Geist,Arial,sans-serif;font-variant-numeric:tabular-nums}</style></head><body>"
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 1080 1440">{"".join(s)}</svg></body></html>')


def main(game_id: str) -> None:
    out = OUTPUT / game_id
    out.mkdir(parents=True, exist_ok=True)
    html = out / "draft-assist-network.html"
    html.write_text(page(game_id))
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page(viewport={"width": 1080, "height": 1440})
        p.goto(html.resolve().as_uri()); p.evaluate("document.fonts.ready"); p.wait_for_timeout(300)
        p.locator("svg").screenshot(path=str(out / "draft-assist-network.png")); b.close()
    print("wrote", out / "draft-assist-network.png")


if __name__ == "__main__":
    main(sys.argv[1])
