from pathlib import Path
import trimesh,numpy as np,json,html
R=Path(__file__).resolve().parents[1]
base=R/'input/BNBU_v80_FULL_EDITABLE.glb'
s=trimesh.load(base,force='scene',process=False)
DNAME='V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE'
entries=[]
for n in s.graph.nodes_geometry:
 if n==DNAME: group='deck'
 elif n.startswith('V60_P1_EASTLAKE_BOARDWALK_'):group='supports'
 elif n=='V54_LAKE00_EAST_WATER_CROSSING_SHORE_RAMP_INFERRED_ENDPOINT_MATCH':group='ramp'
 else:continue
 tf,k=s.graph[n];m=s.geometry[k];v=trimesh.transform_points(m.vertices,tf)
 entries.append({'name':n,'group':group,'tris':np.round(v[m.faces],4).tolist(),'triangles':len(m.faces)})
assert len(entries)==28
payload=json.dumps(entries,separators=(',',':'))
htmltext='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>BNBU v81 · 东湖实源网格观察器</title><style>
*{box-sizing:border-box}body{margin:0;background:#081624;color:#ecf3ff;font:14px/1.5 system-ui,sans-serif}header{padding:12px 20px;border-bottom:1px solid #26445b}header b{font-size:18px}main{display:flex;height:calc(100vh - 100px)}aside{width:300px;background:#102436;padding:18px;overflow:auto}label{display:block;margin:15px 0}canvas{flex:1;display:block;min-width:0;touch-action:none;background:linear-gradient(#153c52,#081827)}.muted{color:#acc2d5;font-size:12px}.value{font-family:monospace;font-weight:650}input{accent-color:#76cae6}a{color:#a6daff} @media(max-width:850px){main{flex-direction:column}aside{width:100%;height:auto}canvas{min-height:55vh}} </style></head>
<body><header><b>BNBU v81 · 东湖板桥 / 原三角面检查器</b><div class="muted">GLB 坐标：EPSG:32649 减 (758940,2474080)；Z 为未测绘的模型相对值。拖动旋转，滚轮缩放。</div></header>
<main><aside><label><input type="checkbox" id="showSupports"> 显示 13 组桥墩 + 13 道横梁（推定，默认关闭）</label>
<label><input type="checkbox" id="showRamp"> 显示 V54 推定岸坡连接（默认关闭）</label>
<label><input type="checkbox" id="zExaggeration"> 高度夸大 ×8（仅显示，不改原三角面）</label>
<label><input type="checkbox" id="wire"> 网格边线</label>
<div id="counter" class="value"></div><p class="muted">蓝灰色为既有桥面；橙色与紫色仅为未定位的历史演示层，不是测绘结果或已证实通道。照片仅支持栈道/支撑的类型，不支持13组数量与间距。</p>
<p class="muted">本检查器使用来自 v80 GLB 的真实三角面顶点，不生成新道路或玻璃。主 GLB 中已排除推定构件；切换仅改变显示。</p></aside><canvas id="c"></canvas></main>
<script>
const entries=PAYLOAD;
const $=id=>document.getElementById(id);const c=$('c'),ctx=c.getContext('2d');
let yaw=-.22,pitch=.28,zoom=1.0,drag=false,last=[0,0],hScale=1;
const cols={deck:'#8dc8d3',supports:'#efa95a',ramp:'#c5a0e6'};
let base=[265,-91,0.2];
function projection(v,w,h){let x=v[0]-base[0],y=v[1]-base[1],z=(v[2]-base[2])*hScale;
const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
let X= x*cy-y*sy;let Y=x*sy+y*cy;let yy=Y*cp-z*sp, zz=Y*sp+z*cp;
let f=zoom*Math.min(w/175,h/110);return [w/2+X*f,h/2-yy*f,zz]}
function render(){const w=c.clientWidth,h=c.clientHeight,dpr=window.devicePixelRatio||1;if(c.width!==Math.round(w*dpr)||c.height!==Math.round(h*dpr)){c.width=w*dpr;c.height=h*dpr;}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
const chosen=entries.filter(e=>e.group==='deck'||e.group==='supports'&&$('showSupports').checked||e.group==='ramp'&&$('showRamp').checked);
let triangles=[];for(const e of chosen){for(const tri of e.tris){const p=tri.map(x=>projection(x,w,h));triangles.push({p,d:(p[0][2]+p[1][2]+p[2][2])/3,col:cols[e.group]})}}
triangles.sort((a,b)=>a.d-b.d);ctx.lineWidth=.6;for(const t of triangles){let p=t.p;ctx.beginPath();ctx.moveTo(p[0][0],p[0][1]);ctx.lineTo(p[1][0],p[1][1]);ctx.lineTo(p[2][0],p[2][1]);ctx.closePath();ctx.fillStyle=t.col;ctx.fill();if($('wire').checked){ctx.strokeStyle='#16405c';ctx.stroke()}}
$('counter').textContent=`显示源网格 ${chosen.length} 个 / 三角面 ${triangles.length.toLocaleString()} | Z ×${hScale}`;
window.__BNBU_V81_TRIANGLES_VISIBLE__=triangles.length;window.__BNBU_V81_GROUP_COUNT__=chosen.length;}
window.addEventListener('resize',render);for(const id of ['showSupports','showRamp','zExaggeration','wire']) $(id).addEventListener('change',()=>{hScale=$('zExaggeration').checked?8:1;render()});
c.addEventListener('pointerdown',e=>{drag=true;last=[e.clientX,e.clientY];c.setPointerCapture(e.pointerId)});
c.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-last[0])*.006;pitch=Math.max(-1.3,Math.min(1.3,pitch+(e.clientY-last[1])*.006));last=[e.clientX,e.clientY];render()});
c.addEventListener('pointerup',()=>drag=false);c.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.15,Math.min(10,zoom*Math.exp(-e.deltaY*.001)));render()},{passive:false});
render();window.__BNBU_V81_READY__=true;
</script></body></html>'''.replace('PAYLOAD',payload)
path=R/'viewer/BNBU_v81_Boardwalk_Source_Triangles_Inspector.html';path.write_text(htmltext,'utf8')
print(path,len(htmltext))