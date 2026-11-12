#!/usr/bin/env python3
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
res={'test':'full offline v76 embedded GLB and skylight layer toggle', 'pass':False,'page_errors':[]}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu','--enable-unsafe-swiftshader','--use-gl=angle','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1450,'height':900})
 page.on('pageerror',lambda e:res['page_errors'].append(str(e)))
 try:
  page.set_content((R/'BNBU_Campus_3D_Viewer_v76.html').read_text('utf8'),wait_until='domcontentloaded',timeout=150000)
  page.wait_for_function('window.__BNBU_TEST__ && window.__BNBU_TEST__.loaded===true && window.__BNBU_TEST__.meshes===1380',timeout=150000)
  res['reported_meshes']=page.locator('#meshCount').inner_text()
  res['skylight_toggle_initial']=page.locator('#showV76Skylight').is_checked()
  res['uncertain_LRC_join_default_hidden']=not page.locator('#showV71Joint').is_checked()
  before=page.evaluate('window.__BNBU_TEST__.getVisible()')
  page.locator('#showV76Skylight').uncheck()
  after=page.evaluate('window.__BNBU_TEST__.getVisible()')
  res['skylight_toggle_visible_mesh_delta']=before-after
  page.locator('#showV76Skylight').check()
  page.locator('#focusList button').filter(has_text='LRC 圆形玻璃天窗').click()
  page.wait_for_timeout(1000)
  (R/'figures').mkdir(exist_ok=True)
  page.screenshot(path=str(R/'figures/BNBU_v76_viewer_chromium.png'),full_page=True)
  res['screenshot_bytes']=(R/'figures/BNBU_v76_viewer_chromium.png').stat().st_size
  res['pass']=all([res['reported_meshes']=='1,380',res['skylight_toggle_initial'],res['uncertain_LRC_join_default_hidden'],res['skylight_toggle_visible_mesh_delta']==1,res['screenshot_bytes']>5000,not res['page_errors']])
 except Exception as e:res['error']=str(e)[:700]
 finally:b.close()
(R/'qa/v76_browser.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(res,ensure_ascii=False,indent=2))