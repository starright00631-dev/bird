#!/usr/bin/env python3
"""Actual Chromium renderer, selections, canvas visible triangles, offline HTML self-sufficiency."""
from pathlib import Path
import json,re,subprocess,asyncio
from playwright.async_api import async_playwright
R=Path(__file__).resolve().parents[1]
html=(R/'viewer/BNBU_v85_V52_V60_Actual_SourceTriangle_3D_Inspector.html').read_text('utf-8')
assert '<script src=' not in html and '<link rel=' not in html
js=re.findall(r'<script[^>]*>(.*?)</script>',html,re.S|re.I)
assert len(js)==1
p=subprocess.run(['node','--check'],input=js[0],text=True,capture_output=True)
assert p.returncode==0,p.stderr
report={'node_check':'PASS','browser':'Chromium set_content (local file/http navigation blocked by environment policy)','success':False}
async def test():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=await browser.new_page(viewport={'width':1280,'height':760});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.set_content(html,wait_until='domcontentloaded',timeout=50000)
  await page.wait_for_function('window.__BNBU_V85__?.ready',timeout=20000)
  first=await page.evaluate('window.__BNBU_V85__')
  assert first['sourceProbes']==14 and first['visibleTriangles']>0,first
  options=await page.locator('#pick option').count()
  assert options==14
  choices=[]
  for i in (12,13,0):
   await page.locator('#pick').select_option(str(i))
   await page.wait_for_timeout(100)
   d=await page.evaluate('({state:window.__BNBU_V85__,detail:document.querySelector("#info").textContent})')
   assert d['state']['visibleTriangles']>0,d
   choices.append({'index':i,'selected':d['state']['selected'],'visibleTriangles':d['state']['visibleTriangles'],'mentions_exact_mesh':('V60_P1' in d['detail'] if i in (12,13) else 'V52_' in d['detail'])})
   assert choices[-1]['mentions_exact_mesh']
  await page.locator('#all').click()
  await page.wait_for_timeout(150)
  allstate=await page.evaluate('window.__BNBU_V85__')
  assert allstate['visibleTriangles']>0
  await page.locator('#pick').select_option('13')
  await page.screenshot(path=str(R/'figures/BNBU_v85_V60_E_source_Chromium.png'))
  assert not errors,errors
  report.update({'success':True,'first_state':first,'selections':choices,'all_visibleTriangles':allstate['visibleTriangles'],'page_errors':errors})
  await browser.close()
asyncio.run(test())
(R/'qa/v85_browser_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(report,ensure_ascii=False))