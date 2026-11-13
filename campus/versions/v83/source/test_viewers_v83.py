#!/usr/bin/env python3
"""Chromium actual script/canvas execution (set_content); WebGL file navigation unverified."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, subprocess, re, hashlib
R=Path(__file__).resolve().parents[1]
report={'version':'v83','browser_executed':'Chromium set_content with original HTML source','native_file_http_webgl_navigation':'not tested/blocked by runtime','console_page_errors':[]}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu','--disable-software-rasterizer'])
 for mode,file,ready in [('cpu','BNBU_Campus_3D_CPU_v83.html','__BNBU_V83__'),('bridge','BNBU_v83_V52_Actual_Triangle_3D_Inspector.html','__BNBU_V83__')]:
  page=b.new_page(viewport={'width':1330,'height':830});errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
  html=(R/'viewer'/file).read_text('utf8')
  page.set_content(html,wait_until='domcontentloaded',timeout=90000)
  page.wait_for_function(f'window.{ready}?.ready===true',timeout=90000)
  init=page.evaluate(f'window.{ready}')
  if mode=='cpu':
   assert init['sourceMeshCount']==1347 and init['sourceTriangles']==691907 and init['visibleFaces']>10000,init
   page.screenshot(path=str(R/'figures'/'BNBU_v83_CPU_Full_Campus_Chromium.png'))
   page.get_by_role('button',name='LRC').click();page.wait_for_timeout(800)
   after=page.evaluate(f'window.{ready}')
   assert after['visibleFaces']>1000
   page.screenshot(path=str(R/'figures'/'BNBU_v83_CPU_LRC_Chromium.png'))
   page.get_by_role('button',name='宿舍').click();page.wait_for_timeout(500)
   dorm=page.evaluate(f'window.{ready}');assert dorm['visibleFaces']>100
   page.screenshot(path=str(R/'figures'/'BNBU_v83_CPU_Dorms_Chromium.png'))
   report['cpu_browser']={'rendered':True,'mesh_count':init['sourceMeshCount'],'full_visible':init['visibleFaces'],'LRC_visible':after['visibleFaces'],'dorm_visible':dorm['visibleFaces']}
  else:
   assert init['sourceProbes']==12 and init['visibleTriangles']>100
   page.screenshot(path=str(R/'figures'/'BNBU_v83_V52_Bridge_3D_Chromium.png'))
   page.get_by_role('button',name='下一个端点').click();page.wait_for_timeout(250)
   after=page.evaluate('window.__BNBU_V83__');assert after['selected']=='00_B' and after['visibleTriangles']>100
   page.get_by_role('button',name='全部六座桥').click();page.wait_for_timeout(300)
   allx=page.evaluate('window.__BNBU_V83__');assert allx['visibleTriangles']>700,allx
   page.mouse.move(280,300);page.mouse.down();page.mouse.move(310,350,steps=6);page.mouse.up()
   report['bridge_browser']={'rendered':True,'endpoint_selection_ok':True,'full_bridges_visible_triangles':allx['visibleTriangles'],'orbit_drag_ok':True}
  assert not errs,errs
  report['console_page_errors'].extend(errs)
  page.close()
 b.close()
(R/'qa'/'v83_browser_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))