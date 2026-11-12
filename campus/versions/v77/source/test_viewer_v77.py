#!/usr/bin/env python3
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
res={'test':'Full offline v77 GLB browser, visibility and focus control','pass':False,'page_errors':[]}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu','--enable-unsafe-swiftshader','--use-gl=angle','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1450,'height':900})
 page.on('pageerror',lambda e:res['page_errors'].append(str(e)))
 try:
  page.set_content((R/'BNBU_Campus_3D_Viewer_v77.html').read_text('utf8'),wait_until='domcontentloaded',timeout=150000)
  page.wait_for_function('window.__BNBU_TEST__ && window.__BNBU_TEST__.loaded===true && window.__BNBU_TEST__.meshes===1382',timeout=150000)
  res['reported_meshes']=page.locator('#meshCount').inner_text()
  res['paver_toggle_initial']=page.locator('#showV77Pavers').is_checked()
  res['unverified_LRC_joint_hidden']=not page.locator('#showV71Joint').is_checked()
  before=page.evaluate('window.__BNBU_TEST__.getVisible()')
  page.locator('#showV77Pavers').uncheck()
  after=page.evaluate('window.__BNBU_TEST__.getVisible()')
  res['pavers_toggle_visible_mesh_delta']=before-after
  page.locator('#showV77Pavers').check()
  page.locator('#focusList button').filter(has_text='二期圆形建筑屋顶铺装').click()
  page.wait_for_timeout(1100)
  R.joinpath('figures').mkdir(exist_ok=True)
  page.screenshot(path=str(R/'figures/BNBU_v77_Viewer_Chromium.png'),full_page=True)
  res['screenshot_bytes']=(R/'figures/BNBU_v77_Viewer_Chromium.png').stat().st_size
  res['pass']=all([res['reported_meshes']=='1,382',res['paver_toggle_initial'],res['unverified_LRC_joint_hidden'],res['pavers_toggle_visible_mesh_delta']==2,res['screenshot_bytes']>5000,not res['page_errors']])
 except Exception as e:res['error']=str(e)[:700]
 finally:b.close()
R.joinpath('qa/v77_browser.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(res,ensure_ascii=False,indent=2))