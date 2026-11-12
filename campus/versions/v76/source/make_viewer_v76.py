from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'viewer'))
from make_viewer import generate
s=(R/'viewer/viewer_template_v75.html').read_text('utf8')
s=s.replace('BNBU v75','BNBU v76')
s=s.replace('v75：完整保留 v64 四处山体与全部既有可靠建筑；修复 37 处原有不透明楼层边带的顶面-侧面拓扑，纳入 v71 两处未测绘的 LRC 小铺装连接并修正其法向；隔离无证据 CTV 小屋，未新增窗格。',
 'v76：继承 v75 全校园，在 LRC 已有圆形屋顶洞口及拱肋上补齐一张连续玻璃天窗曲面；曲率依据既有模型拱肋插值，不是摄影测绘；无随机窗格，无玻璃面积定量资格。')
s=s.replace('<div class="switch"><label for="showV75Story">',
 '<div class="switch"><label for="showV76Skylight">v76 · LRC 既有圆形天窗玻璃连续曲面（模型推定，非实测）</label><input type="checkbox" id="showV76Skylight" checked/></div><div class="switch"><label for="showV75Story">')
s=s.replace('showV75Story=true,','showV75Story=true,showV76Skylight=true,')
s=s.replace('function isShown(m){','function isShown(m){if(!showV76Skylight&&m.name.startsWith("V76_LRC_EXISTING_SKYLIGHT_"))return false;')
s=s.replace("$('showV75Story').onchange=e=>{showV75Story=e.target.checked;requestRender()};", "$('showV76Skylight').onchange=e=>{showV76Skylight=e.target.checked;requestRender()};$('showV75Story').onchange=e=>{showV75Story=e.target.checked;requestRender()};")
s=s.replace("const v75=document.createElement('button');", "const v76=document.createElement('button');v76.textContent='LRC 圆形玻璃天窗 · v76';v76.title='既有洞口+拱肋约束的连续玻璃曲面；不代表实测玻璃面积';v76.onclick=()=>{const ms=current.items.filter(m=>m.name.startsWith('V76_LRC_EXISTING_SKYLIGHT_'));if(ms.length){showV76Skylight=true;$('showV76Skylight').checked=true;focusBounds(boundsFor(ms),3.6)}requestRender()};$('focusList').appendChild(v76);const v75=document.createElement('button');")
s=s.replace("'返回 v75 主模型'", "'返回 v76 主模型'")
s=s.replace('查看 v63 对照基线','查看 v75 对照基线')
s=s.replace("parseGLB(bufferFromBase64(STRICT_GLB_BASE64),'v64 对照基线')", "parseGLB(bufferFromBase64(STRICT_GLB_BASE64),'v75 对照基线')")
s=s.replace("'v64 对照基线'", "'v75 对照基线'")
# User-facing trust messaging; no scientifically invalid glass area computation.
s=s.replace('已有玻璃幕墙（仍需摄影配准）','已有幕墙 / LRC 天窗代理（不适于风险面积定量）')
assert s.count('showV76Skylight')>=5, s.count('showV76Skylight')
assert 'v76 · LRC 既有圆形天窗' in s
assert '__MODEL_BASE64__' in s
(R/'viewer/viewer_template_v76.html').write_text(s,'utf8')
generate(R/'model/BNBU_v76_FULL_EDITABLE.glb',R/'BNBU_Campus_3D_Viewer_v76.html','v76',R/'viewer/viewer_template_v76.html',strict=R/'input/BNBU_v75_FULL_EDITABLE.glb')