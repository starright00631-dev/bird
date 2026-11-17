#!/usr/bin/env python3
"""Fully offline interactive 3D source-face clip inspection; Canvas fallback needs no WebGL."""
from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]
DATA=json.loads((R/'viewer/v79_canvas_geometry_data.json').read_text())
assert len(DATA)==65
head='''<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>BNBU v79 source-face 3D connector inspector</title>
<style>body{margin:0;background:#0c1727;color:#eaf1fa;font:14px system-ui,sans-serif}
header{padding:18px 24px;background:#142b43;border-bottom:1px solid #39506a}
h1{font-size:21px;margin:0 0 8px}p{margin:6px 0;line-height:1.55;color:#b5cddd}
main{display:grid;grid-template-columns:minmax(430px,1fr) 340px;gap:14px;padding:15px}
canvas{display:block;width:100%;height:690px;background:#0a1220;border:1px solid #375371;border-radius:8px;touch-action:none}
aside{background:#132238;padding:18px;border:1px solid #2c455f;border-radius:8px}
select,button{background:#203e56;border:1px solid #63819a;color:#fff;border-radius:4px;padding:10px;width:100%;margin:8px 0}
pre{white-space:pre-wrap;word-break:break-word;line-height:1.6;font-size:13px;color:#d1e3f0}
.legend{display:flex;gap:15px;margin:9px 0}.tag{display:inline-block;width:13px;height:13px;border-radius:3px;margin-right:5px}
@media(max-width:850px){main{grid-template-columns:1fr}canvas{height:480px}}</style></head><body>
<header><h1>BNBU v79 | Actual source triangles around 65 connection diagnostics</h1>
<p>47 inherited hotspots, six V52 bridge systems (12 ends), 12 Phase II dorm/radial/ring pairs. Source: reconciled v78 GLB. Colored surfaces are existing copied triangles, not new roads or glass.</p>
<p><b>Critical:</b> D1-D6 rooftop surfaces at model Z=32 are not ground doors. Their Z=0 faces point DOWN and are not evidence of navigable entrances. Coordinates/hill/water are unsurveyed proxies.</p></header>
<main><section><canvas id="canvas" width="1200" height="790"></canvas><p>Drag to orbit, wheel to zoom. Dashed joining segment is a MEASUREMENT ONLY (not a road, bridge, or 3D asset). Independent local Z model, not survey.</p></section>
<aside><label for="case">Inspect source 3D triangle pair</label><select id="case"></select>
<button id="reset">Reset view</button><div class="legend"><div><i class="tag" style="background:#2da3d2"></i>A source facets</div><div><i class="tag" style="background:#f19335"></i>B source facets</div></div><pre id="stats"></pre>
<p>GLB main geometry unchanged: 1,380 meshes. Diagnostic GLB: 130 newly exported source-face subsets; exactly the same vertices as originals. No claim of verified walkability.</p></aside></main>
<script>const DATA=__JSON__;
let idx=Math.max(0,DATA.findIndex(x=>x.id==='DR_D1')),yaw=-.52,pitch=.65,zoom=1,drag=false,last=null;
const el=document.getElementById('case'),c=document.getElementById('canvas'),ctx=c.getContext('2d');
for(let i=0;i<DATA.length;i++){let a=document.createElement('option');a.value=i;a.textContent=DATA[i].id+' / '+DATA[i].kind;el.appendChild(a)}el.value=idx;
function project(v,scale){let x=v[0]*Math.cos(yaw)-v[1]*Math.sin(yaw),y=v[0]*Math.sin(yaw)+v[1]*Math.cos(yaw);return [c.width/2+x*scale,c.height*.55+(y*Math.sin(pitch)-v[2]*Math.cos(pitch))*scale,y*Math.cos(pitch)+v[2]*Math.sin(pitch)]}
function draw(){let d=DATA[idx],ss=[d.a,d.b],all=[];ss.forEach(s=>s.faces.forEach(f=>all.push(...f)));
let ext=Math.max(12,...all.map(a=>Math.max(Math.abs(a[0]),Math.abs(a[1]),Math.abs(a[2])*1.5)));let scale=Math.min(c.width*.43,c.height*.4)/ext*zoom;
ctx.clearRect(0,0,c.width,c.height);ctx.strokeStyle='#24415f';ctx.lineWidth=1;
for(let k=-5;k<=5;k++){let v=5*k,aa=project([v,-30,0],scale),bb=project([v,30,0],scale);ctx.beginPath();ctx.moveTo(...aa);ctx.lineTo(...bb);ctx.stroke();aa=project([-30,v,0],scale);bb=project([30,v,0],scale);ctx.beginPath();ctx.moveTo(...aa);ctx.lineTo(...bb);ctx.stroke()}
const faces=[];ss.forEach((s,j)=>s.faces.forEach(f=>{let pp=f.map(v=>project(v,scale));faces.push({pp,j,depth:pp.reduce((z,x)=>z+x[2],0)/3})}));faces.sort((a,b)=>b.depth-a.depth);
for(let z of faces){let pp=z.pp;let v1=[pp[1][0]-pp[0][0],pp[1][1]-pp[0][1]],v2=[pp[2][0]-pp[0][0],pp[2][1]-pp[0][1]];let turn=v1[0]*v2[1]-v1[1]*v2[0];ctx.beginPath();ctx.moveTo(pp[0][0],pp[0][1]);ctx.lineTo(pp[1][0],pp[1][1]);ctx.lineTo(pp[2][0],pp[2][1]);ctx.closePath();ctx.fillStyle=z.j===0?(turn>0?'rgba(45,163,210,.55)':'rgba(71,186,236,.82)'):(turn>0?'rgba(241,147,53,.55)':'rgba(255,194,90,.84)');ctx.fill();ctx.strokeStyle=z.j===0?'rgba(169,232,255,.6)':'rgba(255,221,157,.6)';ctx.stroke()}
const a=project(d.a.anchor,scale),b=project(d.b.anchor,scale);ctx.setLineDash([8,7]);ctx.lineWidth=2;ctx.strokeStyle='#f26568';ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.setLineDash([]);
for(let [p,j] of [[a,0],[b,1]]){ctx.fillStyle=j===0?'#36d3ff':'#ffa23b';ctx.beginPath();ctx.arc(p[0],p[1],6,0,Math.PI*2);ctx.fill();ctx.font='18px system-ui';ctx.fillText(j===0?'A':'B',p[0]+10,p[1]-10)}
ctx.fillStyle='#adc7db';ctx.font='16px system-ui';ctx.fillText('LOCAL XY/Z | REAL MESH FACES, NOT PASSABLE NETWORK',20,30)
}
function update(){idx=Number(el.value);const d=DATA[idx];let labels=[`Case: ${d.id} (${d.kind})`,`Plan gap: ${d.plan_gap.toFixed(3)} model m`,`Z difference: ${d.z_gap.toFixed(3)} model m`,`A source: ${d.a.source_mesh}`,`A Z=${d.a.z} / normal=${d.a.normal.join(', ')}`,`A crossing heights=${d.a.candidate_heights.join(', ')}`,`B source: ${d.b.source_mesh}`,`B Z=${d.b.z} / normal=${d.b.normal.join(', ')}`,`B crossing heights=${d.b.candidate_heights.join(', ')}`];if(d.kind==='dorm_ground_to_radial')labels.push('WARNING: A ground-facing underside is not a door. Roof sample is a false height match. No path created.');document.getElementById('stats').textContent=labels.join('\\n');draw()}
el.addEventListener('change',()=>{yaw=-.52;pitch=.65;zoom=1;update()});document.getElementById('reset').onclick=()=>{yaw=-.52;pitch=.65;zoom=1;draw()};
c.onpointerdown=e=>{drag=true;last=[e.clientX,e.clientY];c.setPointerCapture(e.pointerId)};
c.onpointermove=e=>{if(!drag)return;yaw+=(e.clientX-last[0])*.007;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-last[1])*.006));last=[e.clientX,e.clientY];draw()};c.onpointerup=()=>drag=false;
c.onwheel=e=>{e.preventDefault();zoom=Math.max(.12,Math.min(12,zoom*Math.exp(-e.deltaY*.001)));draw()};
window.__BNBU_V79_READY__=true;window.__BNBU_V79__={count:DATA.length,selected:()=>DATA[idx].id,change:i=>{el.value=i;update()},data:DATA};update();</script></body></html>'''
(R/'viewer/BNBU_v79_Interactive_3D_Connector_Inspector.html').write_text(head.replace('__JSON__',json.dumps(DATA,separators=(',',':'))),'utf8')
print(len(DATA))