#!/usr/bin/env python3
"""Create genuinely interactive no-WebGL offline 3D viewport from REAL v82 GLB triangles.
LOD is viewer ONLY and does not replace original geometry or make source more accurate.
No network resources or fabricated GIS geometry. Local JS has orbit/zoom/pan and mesh selection.
"""
from pathlib import Path
import trimesh,numpy as np,json,gzip,base64,collections,html
R=Path(__file__).resolve().parents[1]
s=trimesh.load(R/'model/BNBU_v82_FULL_EDITABLE.glb',force='scene',process=False)
def kind(name):
 n=name.upper()
 if 'LAKE' in n or 'SHORE' in n or 'WATER' in n or 'WETLAND' in n:return 'water'
 if 'TERRAIN' in n or 'HILL' in n or 'RIDGE' in n or 'SLOPE' in n:return 'terrain'
 if 'ROAD' in n or 'WALK' in n or 'BRIDGE' in n or 'DECK' in n or 'RAMP' in n or 'PATH' in n or 'PAV' in n or 'STAIR' in n:return 'road'
 if 'LRC' in n or 'LIBRARY' in n:return 'lrc'
 if n.startswith('D') and len(n)>1 and n[1].isdigit() or 'DORM' in n or n.startswith('V2') or n.startswith('V1'):return 'dorm'
 return 'building'
sc=[];nodes=[];catcnt=collections.Counter();source_faces=0
for n in s.graph.nodes_geometry:
 tf,k=s.graph[n];m=s.geometry[k];f=m.faces;source_faces+=len(f)
 cat=kind(n)
 budget = {'terrain':900,'water':500,'road':95,'lrc':90,'dorm':95,'building':85}[cat]
 # high-detail roof/circular glass, for visual-only reproduction of true original mesh
 if cat=='lrc':budget=len(f) # LRC: preserve every original face in CPU viewport
 if 'SHORE' in n and len(f)>10000:budget=900
 if len(f)<=budget:sel=np.arange(len(f))
 else: sel=np.round(np.linspace(0,len(f)-1,budget)).astype(int)
 verts=trimesh.transform_points(m.vertices,tf)
 mid=len(nodes)
 bounds=np.stack([verts.min(axis=0),verts.max(axis=0)]).round(4).tolist()
 # Keep selected triangles as *existing* face triples. No interpolation or invented surface.
 faces=f[sel]
 xyz=verts[faces]
 # Material medians are visual only; do not assign material/uncertainty to GIS.
 try:
  if m.visual.kind=='vertex':
   c=np.median(m.visual.vertex_colors[:,:3],axis=0)
  elif m.visual.kind=='face':c=np.median(m.visual.face_colors[:,:3],axis=0)
  elif hasattr(m.visual,'material') and hasattr(m.visual.material,'baseColorFactor'):
   c=np.array(m.visual.material.baseColorFactor[:3])*255
  else:c=np.array([174,185,178])
 except Exception:c=np.array([173,190,184])
 c=np.clip(c.astype(int),0,255)
 # Brighten very dark materials for CPU preview
 c=np.clip(c*.82+34,25,237).astype(int).tolist()
 nodes.append({'name':n,'cat':cat,'bounds':bounds,'src_faces':len(f),'lod_faces':len(faces),'rgb':c})
 catcnt[cat]+=1
 for sid,coord in zip(sel,xyz):
  # retain source model triangle IDs; rounded only for display payload (source GLB exact)
  if not np.isfinite(coord).all():continue
  sc.append([mid,int(sid),*[round(float(z),3) for z in coord.flatten()]])
payload={'model_version':'v82','crs':'EPSG:32649 - (758940,2474080), model Z relative','source_faces':source_faces,'nodes':nodes,'faces':sc}
packed=base64.b64encode(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),compresslevel=8)).decode()
(R/'qa'/'v82_cpu_viewer_data.json').write_text(json.dumps({'source_meshes':len(nodes),'source_faces':source_faces,'original_source_face_refs':len(sc),'per_category':catcnt,'rounded_display_coordinates_3_decimal_places':True,'payload_gzip_bytes':len(base64.b64decode(packed)),'no_new_geometry':True},indent=2),'utf8')
TEMPLATE=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BNBU v82 · 完整校园原始三角面 3D CPU 查看器</title><style>
:root{font-family:system-ui,"Microsoft YaHei",sans-serif;background:#101c2a;color:#e0ecf4}*{box-sizing:border-box}body{margin:0;overflow:hidden}header{height:61px;display:flex;align-items:center;gap:18px;padding:0 16px;background:#0d1b2b;border-bottom:1px solid #304257}h1{font-size:17px;margin:0}small{color:#9fb4c8}header span{font-size:12px;color:#b4cad8}section{display:grid;grid-template-columns:minmax(0,1fr) 310px;height:calc(100vh - 61px)}main{position:relative;min-width:0;background:linear-gradient(#bdd6e2,#f0f3eb)}#view{display:block;width:100%;height:100%;cursor:grab;touch-action:none}#view:active{cursor:grabbing}aside{padding:16px 15px;overflow-y:auto;background:#112131;border-left:1px solid #304257}label{display:block;margin:11px 0;color:#ccddeb;font-size:13px}input[type=checkbox]{accent-color:#64c8c4}input[type=range]{width:100%}button{padding:7px 10px;border-radius:7px;border:1px solid #486784;background:#1d394f;color:#e3f4fa;cursor:pointer;margin:4px 5px 4px 0}button:hover{background:#2b5062}#info{white-space:pre-wrap;font-size:11px;color:#b6cbd7;overflow-wrap:anywhere;border-top:1px solid #34495c;margin-top:13px;padding-top:9px}#status{position:absolute;left:14px;bottom:14px;padding:10px 12px;border-radius:9px;background:#102131ed;color:white;font:12px/1.5 system-ui;max-width:min(530px,80%)}#hint{position:absolute;top:13px;left:14px;padding:9px 11px;border-radius:9px;background:#0b2537d9;color:white;font:12px system-ui}a{color:#8bd5e7}#error{display:none;background:#7b2424;padding:10px}</style></head>
<body><header><div><h1>BNBU 珠海校园 · v82</h1><small>可交互的真实源三角面 3D 视图 · WebGL 无依赖</small></div><span>1347 个主模型网格 / 2 个 LRC 连接面法线纠错 / 仅展示用 LOD</span></header><section><main><canvas id="view"></canvas><div id="hint">左键旋转 · 右键拖动平移 · 滚轮缩放 · 点击三角面检查构件</div><div id="status">加载中…</div><div id="error"></div></main><aside>
<b>源模型层级</b><div id="category-controls"></div><hr><b>定位</b><div><button data-focus="all">全校园</button><button data-focus="lrc">LRC</button><button data-focus="dorm">宿舍</button><button data-focus="road">道路/桥</button><button data-focus="terrain">山体</button></div>
<label>轨道放大 <input id="zoom" type="range" min="0.4" max="4" step="0.05" value="1"/></label><label>垂直视角 <input id="pitch" type="range" min="0.2" max="1.48" step="0.02" value="0.86"/></label><button id="reset">重置视角</button><hr>
<b>构件信息</b><div id="info">点击源三角面选中并查看网格名、三角面 ID 与局部 Z。</div>
<hr><small>显示为抽样源三角面：绝不补点插值、随机生成实体。完整 691,907 原始三角面在 ZIP 的 GLB 中；视图保留源网格原始三角形的同一三顶点，屏显坐标四舍五入至 0.001 模型单位，仅用来交互预览。地图不是正射测绘，模型 Z 非绝对高程。新增玻璃/道路/树木/岸线 = 0。</small>
</aside></section><script id="lod-data" type="application/octet-stream">__DATA__</script><script>
'use strict';const $=id=>document.getElementById(id),cv=$('view'),ctx=cv.getContext('2d',{alpha:false});let DATA,faces=[],nodes=[],last=[],center=[0,0,0],yaw=-.85,pitch=.86,zoom=1,selected=-1,drag=null,scheduled=false,payloadReady=false;let visible={terrain:true,water:true,road:true,lrc:true,dorm:true,building:true};
const cats=[['building','建筑实体'],['dorm','宿舍建筑'],['lrc','LRC / 图书馆'],['road','道路、步道、连桥'],['water','湖岸、水体'],['terrain','山体、地形']];
for(const [key,title] of cats){let lab=document.createElement('label'),inp=document.createElement('input');inp.type='checkbox';inp.checked=true;inp.dataset.group=key;inp.onchange=()=>{visible[key]=inp.checked;schedule()};lab.append(inp,document.createTextNode(' '+title));$('category-controls').append(lab)}
function resize(){const r=cv.getBoundingClientRect();cv.width=Math.max(350,Math.round(r.width));cv.height=Math.max(280,Math.round(r.height));schedule()}
const clamp=(v,a,b)=>Math.max(a,Math.min(v,b));function schedule(){if(!scheduled&&payloadReady){scheduled=true;requestAnimationFrame(()=>{scheduled=false;draw()})}}
function viewBasis(){const cp=Math.cos(pitch),sp=Math.sin(pitch),cy=Math.cos(yaw),sy=Math.sin(yaw);return {right:[-sy,cy,0],up:[-sp*cy,-sp*sy,cp],dir:[cy*cp,sy*cp,sp]}}
function projPoint(x,y,z,b,s){let a=x-center[0],c=y-center[1],d=z-center[2];return [cv.width*.5+(a*b.right[0]+c*b.right[1]+d*b.right[2])*s,cv.height*.52-(a*b.up[0]+c*b.up[1]+d*b.up[2])*s,a*b.dir[0]+c*b.dir[1]+d*b.dir[2]]}
function draw(){const t0=performance.now(),w=cv.width,h=cv.height;ctx.fillStyle='#dce8ec';ctx.fillRect(0,0,w,h);let b=viewBasis(),scale=Math.min(w/1120,h/850)*zoom;let work=[];
 for(let fi=0;fi<faces.length;fi++){let f=faces[fi],node=nodes[f[0]];if(!visible[node.cat])continue;
  let p=projPoint(f[2],f[3],f[4],b,scale),q=projPoint(f[5],f[6],f[7],b,scale),r=projPoint(f[8],f[9],f[10],b,scale);
  if(Math.max(p[0],q[0],r[0])<0||Math.min(p[0],q[0],r[0])>w||Math.max(p[1],q[1],r[1])<0||Math.min(p[1],q[1],r[1])>h)continue;
  if(Math.abs((q[0]-p[0])*(r[1]-p[1])-(r[0]-p[0])*(q[1]-p[1]))<.08)continue;
  work.push([((p[2]+q[2]+r[2])/3),f[0],fi,p,q,r]);}
 work.sort((a,b)=>a[0]-b[0]);
 // Original painted depth: far triangles first, no invented geometry.
 const rgb=nodes.map(n=>n.rgb);for(const f of work){const [depth,mi,fi,p,q,r]=f;let c=rgb[mi];ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1]);ctx.lineTo(r[0],r[1]);ctx.closePath();ctx.fillStyle='rgb('+c.join(',')+')';ctx.fill();}
 last=work;
 if(selected>=0){for(const f of work){if(f[1]!==selected)continue;const p=f[3],q=f[4],r=f[5];ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1]);ctx.lineTo(r[0],r[1]);ctx.closePath();ctx.strokeStyle='#f36d32';ctx.lineWidth=1.3;ctx.stroke();}}
 ctx.fillStyle='#283e48';ctx.font='12px system-ui';ctx.fillText('N ↑ 仅模型坐标：E +X / N +Y / relative Z',15,cv.height-12);
 $('status').textContent='v82 实源模型：'+nodes.length+' 网格，'+DATA.source_faces.toLocaleString()+' 原始三角面；CPU 显示 '+work.length.toLocaleString()+' 个抽样源三角面。实际渲染 '+Math.round(performance.now()-t0)+' ms · 不代表测绘或可通行证据。';
 window.__BNBU_V82__={ready:true,mode:'cpu-3d',sourceMeshCount:nodes.length,sourceTriangles:DATA.source_faces,visibleFaces:work.length,selectedNode:selected>=0?nodes[selected].name:null};}
function focus(group){for(const key of Object.keys(visible)){visible[key]=(group==='all'||key===group);}for(const cb of document.querySelectorAll('input[data-group]'))cb.checked=visible[cb.dataset.group];let matching=nodes.filter(n=>group==='all'||n.cat===group);if(!matching.length)return;let mins=[Infinity,Infinity,Infinity],maxs=[-Infinity,-Infinity,-Infinity];for(const n of matching){for(let d=0;d<3;d++){mins[d]=Math.min(mins[d],n.bounds[0][d]);maxs[d]=Math.max(maxs[d],n.bounds[1][d]);}}center=mins.map((x,i)=>(x+maxs[i])/2);let extent=Math.max(maxs[0]-mins[0],(maxs[1]-mins[1])*.82,(maxs[2]-mins[2])*3,8);zoom=clamp(1120/extent*.70,.4,8);$('zoom').value=clamp(zoom,.4,4);selected=-1;schedule()}
for(const btn of document.querySelectorAll('[data-focus]'))btn.onclick=()=>focus(btn.dataset.focus);
$('zoom').oninput=e=>{zoom=+e.target.value;schedule()};$('pitch').oninput=e=>{pitch=+e.target.value;schedule()};$('reset').onclick=()=>{yaw=-.85;pitch=.86;$('pitch').value=pitch;focus('all')};
cv.addEventListener('contextmenu',e=>e.preventDefault());cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);drag={x:e.clientX,y:e.clientY,button:e.button,moved:false};});cv.addEventListener('pointermove',e=>{if(!drag)return;let dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;if(Math.abs(dx)+Math.abs(dy)>.5)drag.moved=true;if(drag.button===2||e.shiftKey){let b=viewBasis(),k=1/(Math.min(cv.width/1120,cv.height/850)*zoom);center[0]-=(dx*b.right[0]-dy*b.up[0])*k;center[1]-=(dx*b.right[1]-dy*b.up[1])*k;center[2]-=(dx*b.right[2]-dy*b.up[2])*k}else{yaw-=dx*.006;pitch=clamp(pitch+dy*.004,.15,1.48);$('pitch').value=pitch;}schedule();});
cv.addEventListener('pointerup',e=>{if(!drag)return;if(!drag.moved){let x=e.offsetX,y=e.offsetY;for(let i=last.length-1;i>=0;i--){let f=last[i],p=f[3],q=f[4],r=f[5];let den=(q[1]-r[1])*(p[0]-r[0])+(r[0]-q[0])*(p[1]-r[1]);if(!den)continue;let a=((q[1]-r[1])*(x-r[0])+(r[0]-q[0])*(y-r[1]))/den,c=((r[1]-p[1])*(x-r[0])+(p[0]-r[0])*(y-r[1]))/den;if(a>=0&&c>=0&&a+c<=1){selected=f[1];const n=nodes[selected],src=faces[f[2]];$('info').textContent=n.name+'\n类型: '+n.cat+'\n源三角面 ID: '+src[1]+'\n源网格三角面: '+n.src_faces+'\n局部 Z: '+src[4]+', '+src[7]+', '+src[10]+'\n坐标未经实测配准；仅模型几何。';schedule();break;}}}drag=null;});
cv.addEventListener('wheel',e=>{e.preventDefault();zoom=clamp(zoom*Math.exp(-e.deltaY*.0012),.2,12);$('zoom').value=clamp(zoom,.4,4);schedule()},{passive:false});
async function init(){try{let raw=atob($('lod-data').textContent.trim()),blob=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)blob[i]=raw.charCodeAt(i);let stream=new Blob([blob]).stream().pipeThrough(new DecompressionStream('gzip'));DATA=JSON.parse(await new Response(stream).text());nodes=DATA.nodes;faces=DATA.faces;payloadReady=true;resize();window.addEventListener('resize',resize);focus('all');}catch(e){$('error').style.display='block';$('error').textContent='无法加载 CPU 源三角面数据：'+e.message;window.__BNBU_V82__={ready:false,error:String(e)}}}init();
</script></body></html>'''
s=TEMPLATE.replace('__DATA__',packed)
(R/'viewer'/'BNBU_Campus_3D_CPU_v82.html').write_text(s,'utf8')
print('SOURCE mesh',len(nodes),'original faces',source_faces,'viewer source-triangle references',len(sc),'HTML_MB',round(len(s)/1e6,2),'kinds',catcnt)