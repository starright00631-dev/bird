#!/usr/bin/env python3
"""Chromium runtime checks: CPU 3D and actual standalone full-HTML embedded CPU fallback."""
from pathlib import Path
import asyncio,json,subprocess,re
from playwright.async_api import async_playwright
R=Path(__file__).resolve().parents[1]
assets=[R/'viewer/BNBU_Campus_3D_CPU_v84.html',R/'viewer/BNBU_Campus_3D_Offline_v84.html',R/'viewer/BNBU_v84_V52_Actual_Triangle_3D_Inspector.html']
js_checks=[]
for f in assets:
 text=f.read_text('utf8')
 for i,m in enumerate(re.finditer(r'<script(?:\s+[^>]*)?>(.*?)</script>',text,re.S|re.I)):
  # no script data types in structural validation
  tag=text[m.start():m.start(1)]
  if 'application/json' in tag or 'application/octet-stream' in tag:continue
  src=m.group(1)
  if not src.strip():continue
  path=R/'qa'/f'_tmp_js_{f.stem}_{i}.js';path.write_text(src,'utf8')
  cp=subprocess.run(['node','--check',str(path)],capture_output=True,text=True)
  js_checks.append([f.name,i,cp.returncode,cp.stderr[:100]])
  path.unlink()
assert all(x[2]==0 for x in js_checks),js_checks
report={'node_JS_syntax':js_checks,'browser_full_webgl_runtime_status':'not tested','cpu_standalone':{},'full_document_embedded_cpu_fallback':{},'console_page_errors':[]}
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=await browser.new_page(viewport={'width':1280,'height':760},device_scale_factor=1)
  errs=[];page.on('pageerror',lambda e: errs.append(str(e)))
  html=assets[0].read_text('utf8')
  await page.set_content(html,wait_until='domcontentloaded',timeout=50000)
  await page.wait_for_function('window.__BNBU_V84__ && window.__BNBU_V84__.ready === true',timeout=45000)
  default=await page.evaluate('window.__BNBU_V84__')
  await page.locator('[data-focus="road"]').click()
  await page.wait_for_timeout(1200)
  road=await page.evaluate('window.__BNBU_V84__')
  assert default['sourceMeshCount']==1346 and default['sourceTriangles']==691593
  assert road['visibleFaces']>0 and road['visibleFaces']!=default['visibleFaces']
  await page.screenshot(path=str(R/'figures/BNBU_v84_CPU_Chromium.png'))
  report['cpu_standalone']={'ready':True,'source_meshes':default['sourceMeshCount'],'source_triangles':default['sourceTriangles'],'default_visible_faces':default['visibleFaces'],'road_visible_faces':road['visibleFaces']}
  # Run full, self-contained HTML in the same browser without file:/http: navigation.
  page2=await browser.new_page(viewport={'width':1280,'height':760})
  page2.on('pageerror',lambda e:errs.append('full: '+str(e)))
  try:
   await page2.set_content(assets[1].read_text('utf8'),wait_until='domcontentloaded',timeout=65000)
   # If WebGL is unavailable, the single-file viewer should auto-switch to CPU.
   # In a GPU-capable browser, manual click must still work.
   try:
    await page2.wait_for_function('window.__BNBU_V84__ && window.__BNBU_V84__.ready === true',timeout=12000)
    mode='automatic_after_WebGL_context_error'
   except Exception:
    await page2.locator('#bn-cpu-fallback').click(timeout=8000)
    await page2.wait_for_function('window.__BNBU_V84__ && window.__BNBU_V84__.ready === true',timeout=45000)
    mode='user_click_fallback'
   full=await page2.evaluate('window.__BNBU_V84__')
   assert full['sourceMeshCount']==1346 and full['sourceTriangles']==691593
   report['full_document_embedded_cpu_fallback']={'success':True,'mode':mode,'loaded_meshes':full['sourceMeshCount'],'loaded_faces':full['sourceTriangles']}
   await page2.screenshot(path=str(R/'figures/BNBU_v84_Embedded_Fallback_Chromium.png'))
  except Exception as e:
   report['full_document_embedded_cpu_fallback']={'click_success':False,'error':str(e)[:400]}
  report['console_page_errors']=errs
  await browser.close()
asyncio.run(main())
(R/'qa/v84_browser_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))