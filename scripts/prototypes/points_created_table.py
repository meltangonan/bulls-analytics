"""Top Bulls points-created seasons: scored/assisted bar and context columns."""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bulls.graphics import house

PROJECT = ROOT / 'docs/visuals/2026-09-21-points-created'
WIDTH, ROW, PAD = 3500, 254, 190
NAME_X, BAR_LEFT, BAR_SPAN = 300, 1020, 1120
TOTAL_LEFT, TOTAL_RIGHT = 2225, 2475
SUPPORT = (2680, 3010, 3340)
INK, RED = house.BLACK, house.RED
ASSIST = '#77716B'
TOP_TEN_GREEN = '#218347'  # Existing dark conditional green for readable table text.
QUIET, RULE = '#625D58', '#B8B0A8'
PRIMARY_HEADSHOTS = Path('/Users/meltangonan/projects/bulls-analytics/cache/headshots')

def ordinal(value):
    n=int(value)
    return str(n)+('th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th'))

def rate(total, games):
    return str((Decimal(int(total))/Decimal(int(games))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))

def load_data():
    frame=pd.read_csv(PROJECT/'data/nba-top15.csv').sort_values('created',ascending=False).reset_index(drop=True)
    if not frame.nba_rank_source.eq('NBA.com').all():
        raise ValueError('Graphic requires the completed NBA-only rank audit')
    votes=pd.read_csv(PROJECT/'data/mvp-voting.csv')
    votes=votes.drop(columns=['PLAYER_NAME'],errors='ignore')
    frame=frame.merge(votes, on=['PLAYER_ID','season'], how='left',validate='one_to_one',indicator=True)
    if not frame['_merge'].eq('both').all():
        raise ValueError('Every displayed row must have a completed MVP voting audit')
    if len(frame)!=15 or not frame.created.eq(frame.PTS+frame.assist_pts).all():
        raise ValueError('Expected 15 verified scoring-plus-assist totals')
    frame['PLAYER_NAME']=frame.PLAYER_NAME.replace({'Jimmy Butler III':'Jimmy Butler'})
    return frame

def render(output:Path, final=False):
    frame=load_data()
    height=2*PAD+ROW*len(frame)
    fig=plt.figure(figsize=(WIDTH/house.DRAFT_DPI,height/house.DRAFT_DPI),facecolor='none')
    ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,WIDTH);ax.set_ylim(0,height);ax.axis('off')
    def text(x,y,label,size=32,color=INK,align='center',weight='bold',z=5):
        return ax.text(x,y,label,fontsize=size,fontproperties=house.helvetica(weight),color=color,ha=align,va='center',zorder=z)
    first=height-PAD-ROW/2
    hy=height-PAD+94
    text(NAME_X,hy,'PLAYER / SEASON',27,align='left')
    for x,color,label in [(BAR_LEFT,INK,'Points scored'),(BAR_LEFT+475,ASSIST,'Assist points')]:
        ax.add_patch(Rectangle((x,hy-18),36,36,facecolor=color,edgecolor='none'))
        text(x+56,hy,label,27,align='left')
    text((TOTAL_LEFT+TOTAL_RIGHT)/2,hy,'TOTAL PTS\nCREATED',26,color=RED)
    for x,label in zip(SUPPORT,['NBA\nRANK','% TEAM\nPOINTS','CREATED\nPER GAME']):
        text(x,hy,label,26)
    card=house.draw_accent_card(ax,TOTAL_LEFT,TOTAL_RIGHT,first,len(frame),ROW,overlap_y=25)
    for lo,hi in [(0,card[0]),(card[1],WIDTH)]:
        ax.plot([lo,hi],[height-PAD+15]*2,color=INK,linewidth=2,zorder=3)
    scale=BAR_SPAN/frame.created.max()
    for i,r in frame.iterrows():
        y=first-i*ROW
        if i%2==0:ax.axhspan(y-ROW/2,y+ROW/2,color=RULE,alpha=.12,zorder=0)
        if i:ax.plot([0,WIDTH],[y+ROW/2]*2,color=RULE,lw=1,zorder=0)
        portrait=PRIMARY_HEADSHOTS/f'{int(r.PLAYER_ID)}.png'
        if not portrait.exists():
            house.ensure_headshots([int(r.PLAYER_ID)]);portrait=house.HEADSHOT_CACHE/f'{int(r.PLAYER_ID)}.png'
        house.top_anchored_headshot_label(ax,portrait,140,y+4,118,crop_fraction=.64,preserve_width=True,zorder=2)
        name=text(NAME_X,y+24,r.PLAYER_NAME,36,align='left')
        if NAME_X+house.rendered_width(ax,name)>BAR_LEFT-35:raise ValueError(f'Name too wide: {r.PLAYER_NAME}')
        season=str(r.season)
        # Keep awards beside the season, on the identity line rather than a numeric column.
        season_text=text(NAME_X,y-47,season,23,color=QUIET,align='left',weight='bold_oblique')
        if pd.notna(r.mvp_rank):
            award=str(r.mvp_label)
            x=NAME_X+house.rendered_width(ax,season_text)+20
            artist=text(x,y-47,'('+award+')',22,color=RED,align='left',weight='bold')
            if x+house.rendered_width(ax,artist)>BAR_LEFT-25:raise ValueError(f'Award annotation too wide: {r.PLAYER_NAME}')
        end=BAR_LEFT+r.created*scale;split=BAR_LEFT+r.PTS*scale;bh=109
        clip=FancyBboxPatch((BAR_LEFT,y-bh/2),end-BAR_LEFT,bh,boxstyle='round,pad=0,rounding_size=9',facecolor='none',edgecolor='none')
        ax.add_patch(clip)
        for lo,hi,color,value in [(BAR_LEFT,split,INK,r.PTS),(split,end,ASSIST,r.assist_pts)]:
            patch=ax.add_patch(Rectangle((lo,y-bh/2),hi-lo,bh,facecolor=color,edgecolor='none',zorder=2));patch.set_clip_path(clip)
            label=text((lo+hi)/2,y,f'{int(value):,}',28,color='white')
            if house.rendered_width(ax,label)>hi-lo-24:raise ValueError(f'Bar label too wide: {r.PLAYER_NAME}')
        text((TOTAL_LEFT+TOTAL_RIGHT)/2,y,f'{int(r.created):,}',34,color='white',z=6)
        text(SUPPORT[0],y,ordinal(r.nba_rank),32,color=TOP_TEN_GREEN if int(r.nba_rank)<=10 else INK)
        text(SUPPORT[1],y,f'{r.team_pct:.1f}%',32)
        text(SUPPORT[2],y,rate(r.created,r.GP),32)
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,dpi=house.export_dpi(final),transparent=True,pad_inches=0)
    plt.close(fig)
    # Keep a small transparent breathing margin, not a page-sized empty footer.
    with Image.open(output) as image:
        bounds=image.getbbox()
        margin=round(20*house.export_dpi(final)/house.DRAFT_DPI)
        image.crop((0,max(0,bounds[1]-margin),image.width,min(image.height,bounds[3]+margin))).save(output,dpi=(house.export_dpi(final),)*2)
    frame.to_csv(PROJECT/'data/top15.csv',index=False)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'output/points-created/table.png')
    args=parser.parse_args();print(render(args.output,args.final))
