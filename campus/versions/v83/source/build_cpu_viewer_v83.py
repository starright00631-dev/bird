#!/usr/bin/env python3
"""Correct semantic classification of ALL GLB meshes in evidence-preserving offline CPU viewer.
Avoid confusing V21/V26 revision tags with actual V21/V26 residential building IDs.
Inherit exact v82-source triangles; never invent preview geometry.
"""
from pathlib import Path
import re
R=Path(__file__).resolve().parents[1]
src=(R/'reference'/'build_cpu_viewer_v82.py').read_text('utf8')
start=src.index('def kind(name):');end=src.index('\nsc=[];',start)
replacement='''def kind(name):
 n=name.upper()
 if 'LAKE' in n or 'SHORE' in n or 'WATER' in n or 'WETLAND' in n:return 'water'
 if 'TERRAIN' in n or 'HILL' in n or 'RIDGE' in n or 'SLOPE' in n or 'LAWN' in n:return 'terrain'
 if any(t in n for t in ('ROAD','WALK','BRIDGE','DECK','RAMP','PATH','PAV','STAIR')) and not any(t in n for t in ('ROOF_DECK','MAIN_','_ROOF_')):return 'road'
 if 'LRC' in n or 'LIBRARY' in n:return 'lrc'
 # Revision tags such as V26_ or V34_MODULE_V26_ are NOT dormitory identities.
 base=re.sub(r'^V\\d{1,3}_','',n)
 base=re.sub(r'^(MODULE_V\\d{1,3}_|P[12]_V\\d{1,3}_)','',base)
 if re.search(r'(?<![A-Z0-9])(?:D[1-6]|V(?:1[5-9]|2[0-9]))(?![0-9])',base):return 'dorm'
 return 'building'
'''
src=src[:start]+replacement+src[end:]
src=src.replace("import trimesh,numpy as np,json,gzip,base64,collections,html", "import trimesh,numpy as np,json,gzip,base64,collections,html,re")
# replace only precise template strings and paths
src=src.replace("BNBU_v82_FULL_EDITABLE.glb","BNBU_v83_FULL_EDITABLE.glb").replace("/model/BNBU_v82", "/model/BNBU_v83")
src=src.replace('v82_cpu_viewer_data.json','v83_cpu_viewer_data.json').replace('BNBU_Campus_3D_CPU_v82.html','BNBU_Campus_3D_CPU_v83.html')
src=src.replace('v82', 'v83').replace('V82','V83')
src=src.replace('2 个 LRC 连接面法线纠错','V52 十二处真实源三角面端点定位')
src=src.replace('v83 实源模型：', 'v83 实源模型（修正宿舍/版本号分类）：')
(R/'source'/'_cpu_builder_generated_v83.py').write_text(src,'utf8')
exec(compile(src,str(R/'source'/'_cpu_builder_generated_v83.py'),'exec'),{'__file__':str(R/'source'/'_cpu_builder_generated_v83.py'),'__name__':'__main__'})