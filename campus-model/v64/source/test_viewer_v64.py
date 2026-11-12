#!/usr/bin/env python3
"""Render actual complete v64 GLB and verify hill toggling in headless Chrome."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];html=(R/'BNBU_Campus_3D_Viewer_v64.html').read_text('utf8')
out={'test':'full v64 offline embedded GLB and four refined hill meshes','pass':False,'page_errors':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--disable-gpu','--enable-unsafe-swiftshader','--use-gl=angle','--disable-dev-shm-usage','--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
 page.on('pageerror',lambda err:out['page_errors'].append(str(err)))
 try:
  page.set_content(html,wait_until='domcontentloaded',timeout=150000)
  page.wait_for_function('window.__BNBU_TEST__?.loaded && window.__BNBU_TEST__.meshes===1381',timeout=150000)
  out['reported_meshes']=page.locator('#meshCount').inner_text()
  out['hill_switch_default_on']=page.locator('#showV53Terrain').is_checked()
  page.get_by_text('Four hills - display',exact=True).count()
  btn=page.locator('#focusList button').filter(has_text='四片山体')
  if btn.count():btn.click()
  page.wait_for_timeout(1600)
  page.screenshot(path=str(R/'figures/BNBU_v64_Viewer_Chromium.png'))
  before=page.evaluate('window.__BNBU_TEST__.getVisible()')
  page.locator('#showV53Terrain').uncheck()
  after=page.evaluate('window.__BNBU_TEST__.getVisible()')
  out['visible_mesh_delta']=before-after
  page.locator('#showV53Terrain').check()
  out['toggle_roundtrip']=page.locator('#showV53Terrain').is_checked()
  out['baseline_button_present']=page.locator('#strictBtn').count()==1
  out['pass']=out['reported_meshes']=='1,381' and out['visible_mesh_delta']==4 and out['toggle_roundtrip'] and out['hill_switch_default_on'] and not out['page_errors']
 except Exception as e:out['error']=str(e)[:800]
 finally:browser.close()
(R/'qa/v64_browser.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(out,ensure_ascii=False,indent=2))