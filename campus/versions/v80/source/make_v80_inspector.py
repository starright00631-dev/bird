#!/usr/bin/env python3
"""Create a small, entirely offline 3D canvas inspector from real GLB triangles."""
from pathlib import Path
import trimesh, numpy as np, json, collections
R=Path(__file__).resolve().parent
S=trimesh.load(R/'input/BNBU_v79_FULL_EDITABLE.glb',force='scene',process=False)
objects=[]
for n in S.graph.nodes_geometry:
 group=None
 if n.startswith('PHASEII_DORM_D') and len(n)==len('PHASEII_DORM_D1'):group='dorm'
 elif n.startswith('V49_PHASEII_D') and n.endswith('INFERRED_NOT_BRIDGE'):group='candidate'
 elif n.startswith('PHASEII_V12_PAVING_phaseII_radial_D') and n.endswith('_surface'):group='radial'
 elif n=='PHASEII_V12_PAVING_phaseII_inner_college_ring_surface':group='ring'
 elif n=='V15_D1_D6_CENTRAL_COURT_PAVING':group='court'
 if group is None:continue
 tf,k=S.graph[n];m=S.geometry[k]
 v=trimesh.transform_points(m.vertices,tf); f=m.faces
 normals=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
 areas=np.linalg.norm(normals,axis=1);z=np.divide(normals[:,2],areas,out=np.zeros(len(f)),where=areas>1e-8)
 if group in ('dorm','court','ring','radial'):
  valid=(z>.4)
  if group=='dorm':
   # Include a bounded sample of existing vertical source triangles, not made-up walls.
   idx=np.where(abs(z)<.13)[0]
   valid[idx[::12]]=True
  f=f[valid]
 tris=np.round(v[f],3)
 objects.append({'name':n,'group':group,'triangles':tris.tolist(),'faces':len(tris)})
print('included groups',collections.Counter({g:sum(x['faces'] for x in objects if x['group']==g) for g in ['dorm','radial','ring','court','candidate']}))
jsondata=json.dumps(objects,separators=(',',':'))
html='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>BNBU v80 · D1–D6 实际GLB候选路径三维检查</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}html,body{margin:0;background:#091521;color:#e9f2fa;font:14px/1.4 system-ui,"Microsoft YaHei",sans-serif}header{padding:12px 18px;background:#152a3b;border-bottom:1px solid #334b5e}header strong{font-size:17px}header small{display:block;color:#b6cdd7;margin-top:4px}main{display:grid;grid-template-columns:minmax(0,1fr) 290px;height:calc(100dvh - 86px)}#view{height:100%;width:100%;display:block;cursor:grab;touch-action:none}aside{padding:16px;background:#102132;border-left:1px solid #304b64;overflow:auto}h3{font-size:14px;margin:10px 0}label{display:block;padding:7px 0}select,button{background:#193249;color:#f2f4f8;border:1px solid #4a687b;padding:8px 10px;border-radius:5px;cursor:pointer}button{margin:5px 3px 0 0}input{accent-color:#61b7a2}p{color:#b7cbd6}strong.warn{color:#ffc37e}footer{font-size:12px;color:#9fb4c4;border-top:1px solid #375; padding-top:10px;margin-top:15px}@media(max-width:780px){main{display:block;height:auto}#view{height:56vh}aside{border:0;border-top:1px solid #304b64}}
</style></head><body><header><strong>BNBU v80 · 二期 D1–D6 真实三角面结构</strong><small>GLB 原始顶点采样的独立离线 3D 检查器 · 拖动旋转，滚轮缩放，橙色仅为未经测绘的历史推断道路</small></header><main><canvas id="view"></canvas><aside><h3>三维场景控制</h3>
<label><input type="checkbox" id="candidates"> 显示 6 条 V49 不可导航候选连接（默认关闭）</label>
<label><input type="checkbox" id="facades" checked> 显示原建筑/屋顶/环路三角面</label>
<label>观察中心 <select id="focus"><option value="all">D1–D6 整体</option><option>D1</option><option>D2</option><option>D3</option><option>D4</option><option>D5</option><option>D6</option></select></label>
<button id="oblique">倾斜视角</button><button id="top">正上方</button><button id="reset">重置视野</button>
<h3>结构信息</h3><p id="stats">加载中</p><p><strong class="warn">未验证通行路径。</strong> 六条历史候选源自旧 v48/v49 形态推断，2022 年官方施工航拍仅支持六栋宿舍围绕公共中心的整体布局，不提供道路的测绘中心线。不能自动连路或用于鸟撞暴露面积。</p>
<footer>实际模型：EPSG:32649 减 (758940,2474080)，Z 为模型相对值，不是 DEM。三角面全部来自 v79 源 GLB；本视图为选取的原始面片，非新增建筑。v80 主 GLB 已排除 V49 候选。</footer></aside></main><script>
const GROUPS=__DATA__;
const canv=document.querySelector('#view'),ctx=canv.getContext('2d');let yaw=0.65,pitch=0.87,scale=2.05,cx=-365,cy=874,showCand=false,showExisting=true,moving=false,px=0,py=0,drag=0;
const colors={dorm:'#c9d7d5',radial:'#70aaa5',ring:'#427d82',court:'#7f9c8c',candidate:'#ffaa48'};
const $=id=>document.querySelector('#'+id);
function resize(){const b=canv.getBoundingClientRect();canv.width=Math.round(b.width*devicePixelRatio);canv.height=Math.round(b.height*devicePixelRatio);draw()}
function proj(p){let a=p[0]-cx,b=p[1]-cy,z=p[2];let C=Math.cos(yaw),S=Math.sin(yaw),x=a*C-b*S,d=a*S+b*C;return [x, -d*Math.sin(pitch)-z*Math.cos(pitch),d*Math.cos(pitch)+z*Math.sin(pitch)]}
function draw(){const W=canv.width,H=canv.height;ctx.fillStyle='#0b1d2d';ctx.fillRect(0,0,W,H);const sc=scale*devicePixelRatio;
let polys=[];for(const o of GROUPS){if(o.group==='candidate'&&!showCand)continue;if(o.group!=='candidate'&&!showExisting)continue;for(const tri of o.triangles){const p=tri.map(proj);polys.push([p,(p[0][2]+p[1][2]+p[2][2])/3,o.group])}}
polys.sort((a,b)=>b[1]-a[1]);let cnt=0;for(const [a,d,g] of polys){ctx.beginPath();ctx.moveTo(W/2+a[0][0]*sc,H/2+a[0][1]*sc);ctx.lineTo(W/2+a[1][0]*sc,H/2+a[1][1]*sc);ctx.lineTo(W/2+a[2][0]*sc,H/2+a[2][1]*sc);ctx.closePath();ctx.fillStyle=colors[g];ctx.globalAlpha=g==='candidate'?.97:.80;ctx.fill();ctx.globalAlpha=1;ctx.strokeStyle=g==='candidate'?'#5c371a':'#213749';ctx.lineWidth=.40;ctx.stroke();cnt++}
ctx.fillStyle='#e8eff9';ctx.font=`${12*devicePixelRatio}px sans-serif`;ctx.fillText(`原始三角面 ${cnt} · 模型 XY/Z 非实测`,16*devicePixelRatio,23*devicePixelRatio);
$('stats').textContent='显示三角面 '+cnt+'；待证候选路径 6 组 / 448 三角面。v80 主场景保留 1,374 网格；历史候选 6 网格单独归档。';}
$('candidates').addEventListener('change',e=>{showCand=e.target.checked;draw()});$('facades').addEventListener('change',e=>{showExisting=e.target.checked;draw()});
$('focus').addEventListener('change',e=>{if(e.target.value==='all'){cx=-365;cy=874;scale=2.05}else{const group=GROUPS.find(o=>o.name==='PHASEII_DORM_'+e.target.value);let p=group.triangles.flat();cx=p.reduce((a,x)=>a+x[0],0)/p.length;cy=p.reduce((a,x)=>a+x[1],0)/p.length;scale=4.4}draw()});
$('oblique').onclick=()=>{yaw=.65;pitch=.87;draw()};$('top').onclick=()=>{yaw=0;pitch=Math.PI/2;draw()};$('reset').onclick=()=>{cx=-365;cy=874;scale=2.05;yaw=.65;pitch=.87;$('focus').value='all';draw()};
canv.addEventListener('pointerdown',e=>{moving=true;px=e.clientX;py=e.clientY;canv.setPointerCapture(e.pointerId)});canv.addEventListener('pointerup',()=>moving=false);canv.addEventListener('pointermove',e=>{if(!moving)return;let dx=e.clientX-px,dy=e.clientY-py;px=e.clientX;py=e.clientY;yaw+=dx*.009;pitch=Math.max(.14,Math.min(1.56,pitch+dy*.007));draw()});canv.addEventListener('wheel',e=>{e.preventDefault();scale=Math.min(16,Math.max(.2,scale*Math.exp(-e.deltaY*.001)));draw()},{passive:false});
new ResizeObserver(resize).observe(canv);window.__BNBU_V80_READY__=true;resize();
</script></body></html>'''.replace('__DATA__',jsondata)
(R/'viewer/BNBU_v80_3D_Quarantine_Inspector.html').write_text(html,encoding='utf8')
print('HTML bytes',len(html.encode()))