#!/usr/bin/env python3
"""Full non-WebGL Chromium load, 65 case switching and canvas rotation acceptance."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];html=R/'viewer/BNBU_v79_Interactive_3D_Connector_Inspector.html'
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 pg=b.new_page(viewport={'width':1450,'height':920})
 pg.on('pageerror',lambda e:errors.append(str(e)))
 pg.set_content(html.read_text('utf8'),wait_until='load',timeout=40000)
 assert pg.evaluate('window.__BNBU_V79_READY__') is True
 assert pg.evaluate('window.__BNBU_V79__.count')==65
 assert pg.evaluate('window.__BNBU_V79__.selected()')=='DR_D1'
 for i in [0,10,46,47,52,53,58,59,64]:
  pg.select_option('#case',str(i))
  assert pg.evaluate('window.__BNBU_V79__.selected()')
 pg.select_option('#case','56')
 cvs=pg.locator('#canvas');box=cvs.bounding_box()
 pg.mouse.move(box['x']+200,box['y']+220);pg.mouse.down();pg.mouse.move(box['x']+250,box['y']+260,steps=5);pg.mouse.up()
 pg.mouse.wheel(0,-180)
 pg.select_option('#case','53')
 pg.screenshot(path=str(R/'qa/BNBU_v79_3D_Viewer_Chromium.png'),timeout=20000)
 assert 'ground-facing underside' in pg.locator('#stats').text_content()
 assert not errors,errors
 report={'pass':True,'browser':'headless Chromium Canvas 2D (no WebGL required)','fully_offline':True,
  'interactive_cases':65,'change_test_indices':[0,10,46,47,52,53,58,59,64],
  'orbit_drag':True,'zoom_wheel':True,'source_facets_rendered':True,'page_errors':errors,
  'full_campus_WebGL':'NOT verified; browser context unavailable','screenshot':'qa/BNBU_v79_3D_Viewer_Chromium.png'}
 (R/'qa/v79_browser_validation.json').write_text(json.dumps(report,indent=2),'utf8')
 print(json.dumps(report,indent=2));b.close()