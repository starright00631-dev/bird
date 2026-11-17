from pathlib import Path
from playwright.sync_api import sync_playwright
import json
R=Path(__file__).resolve().parent
h=(R/'viewer/BNBU_v80_3D_Quarantine_Inspector.html').read_text('utf8')
report={}
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 p=b.new_page(viewport={'width':1450,'height':950},device_scale_factor=1)
 report['js_errors']=[];p.on('pageerror',lambda e:report['js_errors'].append(str(e)))
 p.set_content(h,wait_until='domcontentloaded',timeout=60000)
 p.wait_for_function('window.__BNBU_V80_READY__===true',timeout=15000)
 report['initial_off']=not p.locator('#candidates').is_checked()
 report['initial_canvas']=p.locator('canvas').count()==1
 report['initial_triangles']=p.locator('#stats').inner_text()
 p.screenshot(path=str(R/'qa/BNBU_v80_3D_Inspector_Chromium.png'))
 p.locator('#candidates').check()
 report['toggle_on']=p.locator('#candidates').is_checked()
 p.screenshot(path=str(R/'qa/BNBU_v80_3D_Inspector_Chromium_Candidates_ON.png'))
 report['with_candidates_triangles']=p.locator('#stats').inner_text()
 p.locator('#focus').select_option('D2')
 report['D2_select']=p.locator('#focus').input_value()=='D2'
 report['pass']=not report['js_errors'] and report['initial_off'] and report['toggle_on'] and report['D2_select']
 b.close()
(R/'qa/v80_small_viewer_browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))