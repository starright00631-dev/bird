from pathlib import Path
from playwright.sync_api import sync_playwright
import json
R=Path(__file__).resolve().parents[1];P=R/'viewer/BNBU_v81_Boardwalk_Source_Triangles_Inspector.html'
r={'source':P.name,'loaded':False,'errors':[],'visible_states':[],'full_viewer_webgl_test':'blocked by runtime policy (file/http navigation)'}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1240,'height':760})
 page.on('pageerror',lambda err:r['errors'].append(str(err)))
 page.set_content(P.read_text('utf8'),wait_until='load',timeout=30000)
 page.wait_for_function('window.__BNBU_V81_READY__ === true',timeout=12000)
 for l in [None,'showSupports','showRamp']:
  if l:page.locator('#'+l).check()
  r['visible_states'].append({'state':l or 'deck_only','meshes':page.evaluate('window.__BNBU_V81_GROUP_COUNT__'),'faces':page.evaluate('window.__BNBU_V81_TRIANGLES_VISIBLE__')})
 assert r['visible_states'][0]['meshes']==1
 assert r['visible_states'][1]['meshes']==27
 assert r['visible_states'][2]['meshes']==28
 page.locator('#showSupports').uncheck();page.locator('#showRamp').uncheck()
 page.locator('#zExaggeration').check()
 page.screenshot(path=str(R/'figures/v81_boardwalk_3D_inspector_browser.png'),animations='disabled')
 r['loaded']=True;r['canvas_size']=page.locator('canvas').bounding_box()
 browser.close()
assert not r['errors']
(R/'qa/v81_browser_inspector.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(r,ensure_ascii=False,indent=2))