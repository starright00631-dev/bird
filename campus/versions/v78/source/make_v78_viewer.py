"""Main viewer v76.1 + compatible v78 source GLB, with seams strictly opt-in.

Preserves main v74/v75/v76 research UI and asset URLs, does not claim Pages live.
"""
from pathlib import Path
import re,json,base64,shutil
ROOT=Path(__file__).resolve().parent
src=ROOT/'input/main_viewer';dst=ROOT/'viewer'
dst.mkdir(exist_ok=True)
for name in ['index.html','viewer.js','viewer.css','serve.py','README_打开方式.md']:
 shutil.copy2(src/name,dst/name)
shutil.copytree(src/'generated',dst/'generated',dirs_exist_ok=True)
model=ROOT/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb'
seams=ROOT/'model/BNBU_v78_PAVING_SEAMS_DISPLAY_ONLY.glb'
shutil.copy2(model,dst/'generated/BNBU_v78_RECONCILED_MAIN.glb')
shutil.copy2(seams,dst/'generated/BNBU_v78_PAVING_SEAMS_DISPLAY_ONLY.glb')

# Reconcile each building's source-component name (37 already present, NOT 37 new windows).
archfile=dst/'generated/BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json'
arch=json.loads(archfile.read_text());oldarch=json.dumps(arch,ensure_ascii=False)
compat=json.loads((ROOT/'qa/v78_geometry_compatibility.json').read_text())
rename=compat['source_main_name_to_branch_replacements']
for r in arch['building_records']:
 r['existing_component_names']=[rename.get(n,n) for n in r['existing_component_names']]
 if r.get('source_anchor_node') in rename:r['source_anchor_node']=rename[r['source_anchor_node']]
arch['v78_reconciliation']={'only_existing_opaque_trims_renamed':len(rename),'active_scene_mesh_count':1380,
 'source_main_baseline_mesh_count':1379,'source_main_baseline_sha256':compat['source_main_sha256'],
 'actual_integrated_glb_sha256':compat['active_output_sha256'],
 'roof_paving_seams':'display-only opt-in; never counted as real paths',
 'skylight':'unsurveyed continuous rim-guided surface, exclude measured glass denominators'}
archfile.write_text(json.dumps(arch,ensure_ascii=False,indent=2),'utf8')

html=(dst/'index.html').read_text()
html=html.replace('BNBU 校园 v76','BNBU 校园 v78 · 已验证主场景与 LRC 天窗')
html=html.replace('3D / GIS evidence viewer · v76','3D / GIS model viewer · v78 reconciled')
attach='''\n      <div id="v78-geometry-controls" style="padding:10px;border:1px solid #4f7782;border-radius:8px;background:#102c38;margin:9px 0">
        <strong style="color:#a9e6e6">v78 · 主模型实质几何合并（绝对坐标未测绘）</strong>
        <label style="display:block;font-size:11px;margin:7px 0"><input type="checkbox" id="show-v78-skylight" checked> LRC 连续弧面天窗（已有洞口与拱肋约束，可关闭，非实测玻璃面积）</label>
        <label style="display:block;font-size:11px;margin:7px 0"><input type="checkbox" id="show-v78-seams"> 二期中心圆厅不透明屋顶铺装缝（未配准，仅示意，默认隐藏）</label>
        <span id="v78-control-status" role="status" style="color:#b3c9cd;font-size:10px">主场景有 37 处旧楼层饰边封闭重建及 LRC 天窗；屋顶铺装缝独立展示不计实际几何。</span>
      </div>'''
html=html.replace('      <p id="architecture-v76-status"',attach+'\n      <p id="architecture-v76-status"')
assert 'show-v78-skylight' in html
html=html.replace('v76 建筑身份与连接细部','v78 继承 30 栋身份与连接细部')
html=html.replace('<div class="disclaimer">','<div class="disclaimer"><strong>v78：主 GLB 基于 main v71，37 处不透明饰边替换、1 个 LRC 低可信天窗和 1 处既有屋顶盖板接触修复；不采用缺测的屋面缝和地形平滑作为实际几何。</strong>')
(dst/'index.html').write_text(html)

js=(dst/'viewer.js').read_text()
assert js.count('generated/BNBU_v71_CONNECTED_LAKEFRONT.glb')==1
js=js.replace('generated/BNBU_v71_CONNECTED_LAKEFRONT.glb','generated/BNBU_v78_RECONCILED_MAIN.glb')
assert js.count('it.length!==1379')==1
js=js.replace('it.length!==1379','it.length!==1380')
newfunc='''
// v78 compatibility-gated integration. Branch-only paving seams are opt-in display-only.
let v78SeamGroup=null;
const V78_SKY='V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED';
function v78SkyToggle(){let n=ut?.getObjectByName(V78_SKY);if(n){n.visible=K('show-v78-skylight').checked;st();}}
async function v78LoadSeams(){
  const root=ut?.getObjectByName('world');
  if(!root)throw Error('v78 world root missing');
  let g=(await Ko('v78-seams','generated/BNBU_v78_PAVING_SEAMS_DISPLAY_ONLY.glb')).scene;
  let names=[];g.traverse(e=>{if(e.isMesh){names.push(e.name);e.userData.displayOnly=true;e.userData.metricBirdstrikeEligible=false;e.userData.isSurveyed=false;}});
  if(names.length!==2 || names.some(n=>!n.startsWith('V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_')))throw Error('v78 unregistered roof sidecar mismatch');
  root.add(g);v78SeamGroup=g;g.visible=K('show-v78-seams').checked;st();
}
K('show-v78-skylight').addEventListener('change',v78SkyToggle);
K('show-v78-seams').addEventListener('change',()=>{if(v78SeamGroup){v78SeamGroup.visible=K('show-v78-seams').checked;st();}});
'''
assert js.count('async function ey(){')==1
js=js.replace('async function ey(){',newfunc+'async function ey(){')
assert js.count('Ex(),Tx(),wx(),ut.visible=')==1
js=js.replace('Ex(),Tx(),wx(),ut.visible=','Ex(),Tx(),wx(),v78SkyToggle(),v78LoadSeams().catch(i=>{K("v78-control-status").textContent="v78 未配准屋面缝加载失败："+i.message;console.warn(i)}),ut.visible=')
js=js.replace('window.__BNBU_VERSION__="v76"','window.__BNBU_VERSION__="v78-main-reconciled"')
js=js.replace('meshCount:()=>it.length,','meshCount:()=>it.length,v78SkylightVisible:()=>ut?.getObjectByName(V78_SKY)?.visible??false,v78SeamVisible:()=>v78SeamGroup?.visible??false,v78SeamLoaded:()=>!!v78SeamGroup,')
(dst/'viewer.js').write_text(js)

# Fully standalone packaging: base64 for both actual full model and sidecar, no fetch required.
original=(src/'双击查看_校园3D.html').read_text()
modified=original.replace('BNBU 校园 v76','BNBU 校园 v78 · 已验证主场景与 LRC 天窗')
modified=modified.replace('3D / GIS evidence viewer · v76','3D / GIS model viewer · v78 reconciled')
modified=modified.replace('v76 建筑身份与连接细部','v78 继承 30 栋身份与连接细部')
modified=modified.replace('      <p id="architecture-v76-status"',attach+'\n      <p id="architecture-v76-status"')
modified=modified.replace('<div class="disclaimer">','<div class="disclaimer"><strong>v78： main v71 → 37 处不透明饰边替换、LRC 天窗及屋顶盖板接触校正，屋面缝只作为非测绘视觉对照。</strong>')
pattern=re.compile(r'(<script id="embedded-v71" type="application/octet-stream">)([^<]+)(</script>)')
modified,num=pattern.subn(lambda m:m.group(1)+base64.b64encode(model.read_bytes()).decode()+m.group(3),modified)
assert num==1
pattern2=re.compile(r'(<script id="embedded-v76-architecture" type="application/json">)(.*?)(</script>)',re.S)
modified,num=pattern2.subn(lambda m:m.group(1)+json.dumps(arch,ensure_ascii=False)+m.group(3),modified)
assert num==1
modified=modified.replace('<script id="embedded-v76-edges"', '<script id="embedded-v78-seams" type="application/octet-stream">'+base64.b64encode(seams.read_bytes()).decode()+'</script>\n<script id="embedded-v76-edges"',1)
modified=modified.replace('generated/BNBU_v71_CONNECTED_LAKEFRONT.glb','generated/BNBU_v78_RECONCILED_MAIN.glb',1)
assert modified.count('it.length!==1379')==1
modified=modified.replace('it.length!==1379','it.length!==1380')
assert modified.count('async function ey(){')==1
modified=modified.replace('async function ey(){',newfunc+'async function ey(){')
modified=modified.replace('Ex(),Tx(),wx(),ut.visible=','Ex(),Tx(),wx(),v78SkyToggle(),v78LoadSeams().catch(i=>{K("v78-control-status").textContent="v78 未配准屋面缝加载失败："+i.message;console.warn(i)}),ut.visible=')
modified=modified.replace('window.__BNBU_VERSION__="v76"','window.__BNBU_VERSION__="v78-main-reconciled"')
modified=modified.replace('meshCount:()=>it.length,','meshCount:()=>it.length,v78SkylightVisible:()=>ut?.getObjectByName(V78_SKY)?.visible??false,v78SeamVisible:()=>v78SeamGroup?.visible??false,v78SeamLoaded:()=>!!v78SeamGroup,')
(dst/'BNBU_Campus_3D_Offline_v78.html').write_text(modified)
print('viewer generated',len(js),len(modified),'atlas names patched',len(rename))