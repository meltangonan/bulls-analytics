// Back-pocket recap pages, not in the carousel (2026-10-06): on-court ratings scatter, who guarded whom,
// player tracking, how they scored. recap_data.py still computes their data (scatter, matchups, tracking,
// scoring). They were drawn with the pre-house-style helpers below (page, section, splitRows); port them to
// the current helpers in recap_template.html before bringing one back.

// Split bars: Bulls left, opponent right; the better value is bold.
function splitRows(rows,y0,step,opts={}){let s='';rows.forEach(([lab,l,r,va,vb,hi],i)=>{const y=y0+i*step,better=va==vb?0:((va>vb)==!!hi?1:-1);
s+=t(60,y,opts.size||25,l,{w:better==1?700:400,f:better==1?R:K})+t(1020,y,opts.size||25,r,{a:'end',w:better==-1?700:400})+t(540,y,opts.lsize||21,lab,{a:'middle',f:MU});
const sh=(va+vb)?va/(va+vb):0.5,mid=60+960*sh;s+=rect(60,y+12,mid-64,8,R,4)+rect(mid+4,y+12,1020-mid-4,8,GR,4);});return s;}

function scatterPage(){const SC=D.scatter;const vals=SC.flatMap(d=>[d[2],d[3]]);const lo=Math.floor((Math.min(...vals)-4)/10)*10,hi=Math.ceil((Math.max(...vals)+4)/10)*10;
const px0=150,px1=1010,py0=200,py1=1140,X=v=>px0+(v-lo)/(hi-lo)*(px1-px0),Y=v=>py0+(v-lo)/(hi-lo)*(py1-py0);let s='';
const stp=(hi-lo)>80?20:10;for(let v=lo;v<=hi;v+=stp){s+=ln(px0,Y(v),px1,Y(v),LR,1.2)+t(px0-14,Y(v)+8,21,v,{a:'end',f:MU})+ln(X(v),py0,X(v),py1,LR,1.2)+t(X(v),py1+34,21,v,{a:'middle',f:MU});}
const lg=D.league_rating;s+=ln(X(lg),py0,X(lg),py1,K,1.8,'9 8')+ln(px0,Y(lg),px1,Y(lg),K,1.8,'9 8')+t(X(lg)+10,py1-12,18,`NBA avg ${lg}`,{f:MU,w:700});
s+=t(px1-10,py0+30,21,'Better offense',{a:'end',f:MU,w:700})+t(px1-10,py0+55,21,'and defense',{a:'end',f:MU,w:700});
s+=t((px0+px1)/2,py1+76,20,'OFFENSIVE RATING  (higher is better)',{a:'middle',f:MU,w:700,ls:1})+`<text transform="translate(62 ${(py0+py1)/2}) rotate(-90)" font-size="20" fill="${MU}" font-weight="700" text-anchor="middle" letter-spacing="1">DEFENSIVE RATING  (lower is better, so up)</text>`;
SC.filter(d=>d[1]!=='CHI').forEach(d=>s+=`<circle cx="${X(d[2])}" cy="${Y(d[3])}" r="12" fill="${GR}" opacity="0.85"/>`);
SC.filter(d=>d[1]==='CHI').forEach(d=>s+=`<circle cx="${X(d[2])}" cy="${Y(d[3])}" r="14" fill="${R}"/>`);
// Labels go right, left, above or below their dot, whichever touches nothing already placed.
const boxes=SC.map(d=>({x:X(d[2])-14,y:Y(d[3])-14,w:28,h:28}));const hit=b=>boxes.some(o=>b.x<o.x+o.w&&b.x+b.w>o.x&&b.y<o.y+o.h&&b.y+b.h>o.y)||b.x<px0||b.x+b.w>px1||b.y<py0||b.y+b.h>py1;
[...SC].sort((a,b)=>(a[1]==='CHI'?0:1)-(b[1]==='CHI'?0:1)).forEach(d=>{const x=X(d[2]),y=Y(d[3]),w=tw(d[0],21,700),opts=[[x+18,y+7,'start',x+18,y-12],[x-18,y+7,'end',x-18-w,y-12],[x,y-22,'middle',x-w/2,y-40],[x,y+36,'middle',x-w/2,y+18]];
for(const [lx,ly,an,bx,by] of opts){const b={x:bx,y:by,w,h:24};if(!hit(b)){boxes.push(b);s+=t(lx,ly,21,d[0],{a:an,w:d[1]==='CHI'?700:500,f:d[1]==='CHI'?K:MU});break;}}});
s+=`<circle cx="72" cy="1290" r="13" fill="${R}"/>`+t(94,1298,22,'Bulls',{w:700})+`<circle cx="200" cy="1290" r="11" fill="${GR}"/>`+t(220,1298,22,D.opp.team,{f:MU,w:700});
return page('ON-COURT RATINGS',s,'Team points per 100 possessions scored and allowed with each player on the floor. Players with 20+ possessions.');}

function matchupPage(){if(!D.matchups)return null;let s=section(222,'POSSESSIONS GUARDED','POINTS ALLOWED');let y=248;const mx=Math.max(...D.matchups.flatMap(m=>m[2].map(r=>r[1]))),bx0=400,bsc=300/mx;
D.matchups.forEach(([star,pts,rows])=>{s+=ln(60,y,1020,y,K,2.5)+t(60,y+40,28,star,{w:700})+t(1020,y+40,28,`${pts} PTS`,{a:'end',w:700});y+=58;
rows.forEach(([d,poss,p,fm,fa,id])=>{const c=y+25,other=d==='Others';if(!other)s+=head(id,58,y-2,52);
s+=t(124,c+9,24,d,{w:other?400:700,f:other?MU:K})+rect(bx0,c-11,poss*bsc,22,other?LR:R,4)+t(bx0+poss*bsc+10,c+8,20,poss.toFixed(1),{f:MU,w:700})+t(880,c+8,21,`${fm}-${fa} FG`,{a:'end',f:MU})+t(1020,c+9,24,`${p} PTS`,{a:'end',w:700});y+=50;});y+=12;});
return page('WHO GUARDED WHOM',s,`Bulls defenders on the ${D.opp.team}' top three scorers. Partial possessions; Others includes switches.`);}

function trackingPage(){const T=D.tracking;if(!T)return null;let s=t(60,222,22,'BULLS',{w:700,f:R,ls:1.5})+t(1020,222,22,D.opp.name,{w:700,a:'end',ls:1.5});
s+=splitRows(T.rows,270,50,{size:24,lsize:20});const ty=270+T.rows.length*50+26;
const TH=['TOUCHES','PASSES','UNCONT. FG','CONT. FG','OPP. AT RIM','MILES'],tx=[400,505,625,750,870,1020];
s+=section(ty,'BULLS PLAYERS');TH.forEach((h,j)=>s+=t(tx[j],ty,16,h,{a:j==5?'end':'middle',w:700}));s+=ln(40,ty+14,1046,ty+14,K,2.5);
const rh=Math.min(44,(1320-ty-30)/T.players.length);T.players.forEach((r,i)=>{const y=ty+44+i*rh;if(i%2==0)s+=rect(40,y-rh+12,1006,rh,ALT,0);
s+=t(60,y,23,r[0],{w:700});[r[1],r[2],r[3],r[4],r[5],r[6].toFixed(2)].forEach((v,j)=>s+=t(tx[j],y,23,v,{a:j==5?'end':'middle'}));});
return page('PLAYER TRACKING',s,`NBA.com tracking cameras; they logged ${T.tracked_fga} of the Bulls' ${D.shooting.fga} shots. Opp. at rim: shots at the rim this player defended.`);}

function scoringPage(){const S=D.scoring;if(!S)return null;let s=section(222,'SHARE OF POINTS');const SEG=[['Paint',R],['Mid-range','#E28A9B'],['3PT',K],['Free throws',GR]];
[['BULLS',S.shares[0]],[D.opp.name,S.shares[1]]].forEach(([n,v],j)=>{const y=246+j*86;s+=t(60,y+42,25,n,{w:700,f:j==0?R:K});let x=250;
v.forEach((p,k)=>{const w=p/100*770;s+=rect(x,y+8,w-3,54,SEG[k][1],2);if(w>66)s+=t(x+w/2,y+43,21,p.toFixed(1)+'%',{a:'middle',w:700,f:k==1||k==3?K:'#FFFFFF'});x+=w;});});
let lx=250;SEG.forEach(([n,c])=>{s+=rect(lx,432,18,18,c,3)+t(lx+26,448,20,n,{f:MU,w:700});lx+=tw(n,20,700)+64;});
s+=t(60,500,20,`Fast break: Bulls ${S.fastbreak[0]}% of points, ${D.opp.team} ${S.fastbreak[1]}%  ·  Off turnovers: ${S.off_to[0]}% vs. ${S.off_to[1]}%`,{f:MU});
s+=section(574,'ASSISTED MAKES');S.assisted.forEach(([lab,a,b],i)=>{const y=600+i*78;s+=t(60,y+28,24,lab);[[a,R],[b,GR]].forEach(([v,c],k)=>{const yy=y+k*28;s+=rect(330,yy+6,v/100*560,22,c,4)+t(330+v/100*560+10,yy+24,20,`${v.toFixed(0)}%`,{w:700});});});
const U=S.unassisted.slice(0,9),uy=868;s+=section(uy,'WHO CREATED THEIR OWN SHOT','BULLS MADE FIELD GOALS');const mxf=Math.max(...U.map(u=>u[1])),bw=Math.min(40,560/mxf-5);
U.forEach(([n,f,u],i)=>{const y=uy+26+i*42;s+=t(60,y+24,22,n,{w:700});for(let k=0;k<f;k++)s+=rect(230+k*(bw+5),y+5,bw,26,k<u?R:LR,4);s+=t(230+f*(bw+5)+8,y+24,19,`${u} of ${f} unassisted`,{f:MU});});
s+=rect(60,1300,18,18,R,3)+t(86,1316,20,'Unassisted',{f:MU,w:700})+rect(220,1300,18,18,LR,3)+t(246,1316,20,'Assisted',{f:MU,w:700});
return page('HOW THEY SCORED',s);}

