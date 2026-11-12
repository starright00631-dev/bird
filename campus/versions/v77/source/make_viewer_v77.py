#!/usr/bin/env python3
"""Embedded v77 3D GLB browser with v76 comparison and hypothesis layer toggle."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'viewer'))
from make_viewer import generate
s=(R/'viewer/viewer_template_v76.html').read_text('utf8')
s=s.replace('BNBU v76','BNBU v77')
s=s.replace('BNBU v77 博雅苑 V15–V29 不透明楼层饰带实体重建（原轮廓、非玻璃）','BNBU v77 二期圆形建筑屋顶接触修复及照片支持的铺装缝线（尺寸非实测）')
s=s.replace('v76：继承 v75 全校园，在 LRC 已有圆形屋顶洞口及拱肋上补齐一张连续玻璃天窗曲面；曲率依据既有模型拱肋插值，不是摄影测绘；无随机窗格，无玻璃面积定量资格。','v77：继承 v76 全校园，修复二期圆形建筑原中心屋顶盘与方形铺装的微小埋入冲突；用官方照片证实的铺装类型补充两组不透明缝线，但数量和间距不是测绘数据。')
s=s.replace('<div class="switch"><label for="showV76Skylight">','<div class="switch"><label for="showV77Pavers">v77 · 二期圆形建筑屋顶铺装缝线（照片类型支持，数量和间距为推定）</label><input type="checkbox" id="showV77Pavers" checked/></div><div class="switch"><label for="showV76Skylight">')
s=s.replace('showV76Skylight=true,','showV76Skylight=true,showV77Pavers=true,')
s=s.replace('function isShown(m){','function isShown(m){if(!showV77Pavers&&m.name.startsWith("V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_"))return false;')
s=s.replace("$('showV76Skylight').onchange=e=>{showV76Skylight=e.target.checked;requestRender()};", "$('showV77Pavers').onchange=e=>{showV77Pavers=e.target.checked;requestRender()};$('showV76Skylight').onchange=e=>{showV76Skylight=e.target.checked;requestRender()};")
s=s.replace("const v76=document.createElement('button');","const v77=document.createElement('button');v77.textContent='二期圆形建筑屋顶铺装 · v77';v77.title='来源：校方建筑照片；位置、缝距及高差未经测绘';v77.onclick=()=>{const ms=current.items.filter(m=>m.name.startsWith('V77_P2_COMMONS_ROOF_PHOTO_PAVING_SEAMS_'));if(ms.length){showV77Pavers=true;$('showV77Pavers').checked=true;focusBounds(boundsFor(ms),2.4)}requestRender()};$('focusList').appendChild(v77);const v76=document.createElement('button');")
s=s.replace('返回 v76 主模型','返回 v77 主模型')
s=s.replace('查看 v75 对照基线','查看 v76 对照基线')
s=s.replace("parseGLB(bufferFromBase64(STRICT_GLB_BASE64),'v75 对照基线')","parseGLB(bufferFromBase64(STRICT_GLB_BASE64),'v76 对照基线')")
assert s.count('showV77Pavers')>=5
(R/'viewer/viewer_template_v77.html').write_text(s,'utf8')
generate(R/'model/BNBU_v77_FULL_EDITABLE.glb',R/'BNBU_Campus_3D_Viewer_v77.html','v77',R/'viewer/viewer_template_v77.html',strict=R/'input/BNBU_v76_FULL_EDITABLE.glb')