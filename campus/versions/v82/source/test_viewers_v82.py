"""Test real Chromium CPU rendering through page.set_content because navigation is restricted.
Do not misrepresent this as successful full WebGL/full file:// navigation test.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess,hashlib,base64,re,json
R=Path(__file__).resolve().parents[1]
old=(R/'viewer/BNBU_Campus_3D_Offline_v82.html').read_text('utf8')
embedded=base64.b64decode(re.search(r'<script id="embedded-v71" type="application/octet-stream">(.*?)</script>',old,re.S).group(1))
assert embedded==(R/'model/BNBU_v82_FULL_EDITABLE.glb').read_bytes()
jschecks=[]
for j,m in enumerate(re.finditer(r'<script\b([^>]*)>(.*?)</script>',old,re.S|re.I)):
 attr=m.group(1);code=m.group(2)
 if 'type="module"' not in attr and 'type="text/javascript"' not in attr:continue
 tmp=R/'qa'/f'v82_webgl_js_{j}.mjs'
 tmp.write_text(code,'utf8')
 res=subprocess.run(['node','--check',str(tmp)],capture_output=True,text=True)
 jschecks.append({'script':j,'syntax_ok':res.returncode==0,'error':res.stderr[-250:]})
 assert res.returncode==0,res.stderr
report={'full_glb_embedded_sha256':hashlib.sha256(embedded).hexdigest(),'full_webgl_js_syntax':jschecks,
 'full_webgl_browser_navigation_test':'not validated: restricted in this runtime',
 'no_webgl_cpu_browser_test':False}
html=(R/'viewer/BNBU_Campus_3D_CPU_v82.html').read_text('utf8')
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu','--disable-software-rasterizer'])
 page=b.new_page(viewport={'width':1320,'height':810});errs=[]
 page.on('pageerror',lambda e:errs.append(str(e)))
 # No navigation bypass: test executed document's actual script and canvas renderer.
 page.set_content(html,wait_until='domcontentloaded',timeout=60000)
 page.wait_for_function('window.__BNBU_V82__?.ready===true',timeout=60000)
 s=page.evaluate('window.__BNBU_V82__')
 assert s['sourceMeshCount']==1347 and s['sourceTriangles']==691907 and s['visibleFaces']>10000
 page.screenshot(path=str(R/'figures/BNBU_v82_CPU_full_campus_Chromium.png'))
 page.get_by_role('button',name='LRC').click();page.wait_for_timeout(1100)
 a=page.evaluate('window.__BNBU_V82__');assert a['visibleFaces']>1000 and a['sourceMeshCount']==1347
 page.screenshot(path=str(R/'figures/BNBU_v82_CPU_LRC_Chromium.png'))
 page.get_by_role('button',name='全校园').click();page.wait_for_timeout(500)
 page.locator('input[data-group="terrain"]').uncheck();page.wait_for_timeout(500)
 c=page.evaluate('window.__BNBU_V82__');assert c['visibleFaces']>0
 page.mouse.move(330,310);page.mouse.down();page.mouse.move(395,350,steps=6);page.mouse.up();page.wait_for_timeout(1000)
 d=page.evaluate('window.__BNBU_V82__');assert d['ready']
 assert not errs,errs
 report.update({'no_webgl_cpu_browser_test':True,'browser_test_mode':'chromium set_content (no file navigation)','initial_drawn_source_faces':s['visibleFaces'],
 'lrc_focus_drawn_source_faces':a['visibleFaces'],'after_terrain_toggle_drawn_faces':c['visibleFaces'],'orbit_drag_pass':True,
 'javascript_page_errors':errs,'cpu_viewer_html_sha256':hashlib.sha256(html.encode()).hexdigest()})
 b.close()
(R/'qa/v82_browser_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in report.items() if k!='full_webgl_js_syntax'},ensure_ascii=False,indent=2))