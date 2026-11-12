from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];h=(R/'BNBU_v75_Changes_3D_Viewer.html').read_text('utf8')
o={'test':'offline 42 mesh v75 delta scene controls','pass':False,'page_errors':[]}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu','--enable-unsafe-swiftshader','--use-gl=angle','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1440,'height':840})
 page.on('pageerror',lambda e:o['page_errors'].append(str(e)))
 try:
  page.set_content(h,wait_until='domcontentloaded',timeout=40000)
  page.wait_for_function('window.__BNBU_TEST__?.loaded && window.__BNBU_TEST__.meshes===42',timeout=45000)
  o['mesh_count']=page.locator('#meshCount').inner_text()
  before=page.evaluate('window.__BNBU_TEST__.getVisible()')
  page.locator('#showV75Story').uncheck()
  after=page.evaluate('window.__BNBU_TEST__.getVisible()')
  o['visibility_repair_reduction']=before-after
  page.locator('#showV75Story').check()
  page.locator('#showV71Joint').check()
  o['visibility_source_patch_increase']=page.evaluate('window.__BNBU_TEST__.getVisible()')-before
  page.screenshot(path=str(R/'figures/BNBU_v75_42mesh_browser.png'))
  o['screenshot_size']=(R/'figures/BNBU_v75_42mesh_browser.png').stat().st_size
  o['pass']=o['mesh_count']=='42' and o['visibility_repair_reduction']==37 and o['visibility_source_patch_increase']==2 and not o['page_errors']
 except Exception as e:o['error']=str(e)[:900]
 finally:b.close()
(R/'qa/v75_delta_browser.json').write_text(json.dumps(o,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(o,ensure_ascii=False,indent=2))