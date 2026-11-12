from pathlib import Path
import sys,re
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'viewer'))
from make_viewer import generate
s=(R/'viewer'/'viewer_template_v64.html').read_text('utf8')
s=s.replace('BNBU v64','BNBU v75')
s=s.replace('v64：在 v63 完整校园上约束平滑四组原有山体（仅 Z ±0.35 模型米，XY 不变）。',
  'v75：完整保留 v64 四处山体与全部既有可靠建筑；修复 37 处原有不透明楼层边带的顶面-侧面拓扑，纳入 v71 两处未测绘的 LRC 小铺装连接并修正其法向；隔离无证据 CTV 小屋，未新增窗格。')
s=s.replace('v53–54 · CTV/CC401 小房子与接入（位置推定）','CTV 小房子已隔离，不在主模型')
s=s.replace('<div class="switch"><label for="showV53CTV">CTV 小房子已隔离，不在主模型</label><input type="checkbox" id="showV53CTV" checked/></div>','')
s=s.replace('showV53CTV=true,','')
s=s.replace("if(!showV53CTV&&(m.name.startsWith('V53_CTV_')||m.name.startsWith('V54_CTV_')))return false;",'')
s=s.replace("$('showV53CTV').onchange=e=>{showV53CTV=e.target.checked;requestRender()};",'')
s=re.sub(r"const ct=document.createElement\('button'\);ct.textContent='CTV 旁小房';.*?\$\('focusList'\)\.appendChild\(ct\);",'',s,flags=re.S)
# Dedicated controls for source-matched but not geodetically verified geometry.
s=s.replace('<div class="switch"><label for="showV63Story">',
 '<div class="switch"><label for="showV75Story">v75 · 37 处旧楼层不透明边饰网格封闭（不新增窗格）</label><input type="checkbox" id="showV75Story" checked/></div><div class="switch"><label for="showV71Joint">v71 · LRC 两处小铺装拼接（模型推定，默认隐藏）</label><input type="checkbox" id="showV71Joint"/></div><div class="switch"><label for="showV63Story">')
s=s.replace('showV63Story=true,','showV63Story=true,showV75Story=true,showV71Joint=false,')
s=s.replace('function isShown(m){','function isShown(m){if(!showV75Story&&m.name.startsWith("V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_"))return false;if(!showV71Joint&&m.name.startsWith("V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_"))return false;')
s=s.replace("$('showV63Story').onchange=e=>{showV63Story=e.target.checked;requestRender()};",
 "$('showV75Story').onchange=e=>{showV75Story=e.target.checked;requestRender()};$('showV71Joint').onchange=e=>{showV71Joint=e.target.checked;requestRender()};$('showV63Story').onchange=e=>{showV63Story=e.target.checked;requestRender()};")
s=s.replace("const v63=document.createElement('button');", "const v75=document.createElement('button');v75.textContent='一期 37 处原楼层饰带 · v75';v75.title='原模型仅 0.5 毫米数学奇点修复，非测量';v75.onclick=()=>{const ms=current.items.filter(m=>m.name.startsWith('V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_'));if(ms.length){showV75Story=true;$('showV75Story').checked=true;focusBounds(boundsFor(ms),1.4)}requestRender()};$('focusList').appendChild(v75);const joint=document.createElement('button');joint.textContent='LRC 两处来源拼接 · v71';joint.title='v71 沿旧模型同高拼接，未测绘，不可导航';joint.onclick=()=>{const ms=current.items.filter(m=>m.name.startsWith('V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_'));if(ms.length){showV71Joint=true;$('showV71Joint').checked=true;focusBounds(boundsFor(ms),7)}requestRender()};$('focusList').appendChild(joint);const v63=document.createElement('button');")
s=s.replace("if(n.startsWith('V64_CONSTRAINED_RELIEF_'))return 'landscape';","if(n.startsWith('V64_CONSTRAINED_RELIEF_'))return 'landscape';")
s=s.replace("if(u.startsWith('V64_CONSTRAINED_RELIEF_PHASEII_'))return 'II';","if(u.startsWith('V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_')||u.startsWith('V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_'))return 'I';if(u.startsWith('V64_CONSTRAINED_RELIEF_PHASEII_'))return 'II';")
s=s.replace("if(/ROOF|DOME|PARAPET|SOFFIT|FLOOR_EDGE|CROSSRIB|CEILING|COLUMN|PILLAR|MULLION|FRAME|PORTICO|BRACE|RIB_/.test(n))return 'roof';", "if(/V75_CLOSED_OPAQUE_EXISTING_STORYTRIM_/.test(n))return 'roof';if(/V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_/.test(n))return 'pavement';if(/ROOF|DOME|PARAPET|SOFFIT|FLOOR_EDGE|CROSSRIB|CEILING|COLUMN|PILLAR|MULLION|FRAME|PORTICO|BRACE|RIB_/.test(n))return 'roof';")
s=s.replace("'v63 对照基线'","'v64 对照基线'")
s=s.replace("'返回 v64 主模型'","'返回 v75 主模型'")
s=s.replace('查看 v56 对照基线','查看 v64 基线')
s=s.replace('title="查看 v51 基线模型"','title="v64 原始三维模型基线"')
assert s.count('showV75Story')>=5 and s.count('showV71Joint')>=5
(R/'viewer'/'viewer_template_v75.html').write_text(s,'utf8')
generate(R/'model'/'BNBU_v75_FULL_EDITABLE.glb',R/'BNBU_Campus_3D_Viewer_v75.html','v75',R/'viewer'/'viewer_template_v75.html',strict=R/'input'/'BNBU_v64_FULL_EDITABLE.glb')