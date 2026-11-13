#!/usr/bin/env python3
"""Chromium tests for the self-contained v86 baseline/candidate comparison viewer."""
from pathlib import Path
import json, re, subprocess, asyncio
from playwright.async_api import async_playwright
R=Path(__file__).resolve().parents[1]
html=(R/'viewer/BNBU_v86_T1_T3_OSM_Registration_Comparison.html').read_text('utf-8')
assert '<script src=' not in html and '<link rel=' not in html
scripts=re.findall(r'<script[^>]*>(.*?)</script>',html,re.S|re.I)
assert len(scripts)==1
node=subprocess.run(['node','--check'],input=scripts[0],text=True,capture_output=True)
assert node.returncode==0,node.stderr
report={'node_check':'PASS','self_contained':True,'browser':'Chromium set_content','success':False}
async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader'])
        page=await browser.new_page(viewport={'width':1440,'height':900})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        await page.set_content(html,wait_until='domcontentloaded',timeout=60000)
        await page.wait_for_function('window.__BNBU_V86__?.ready',timeout=30000)
        baseline=await page.evaluate('window.__BNBU_V86__')
        assert baseline['meshCount']==173 and baseline['sourceTriangles']==10700 and baseline['renderedFaces']==10700,baseline
        await page.locator('#mode').select_option('candidate')
        candidate=await page.evaluate('window.__BNBU_V86__')
        assert candidate['mode']=='candidate' and candidate['renderedFaces']==10700,candidate
        await page.locator('#mode').select_option('overlay')
        overlay=await page.evaluate('window.__BNBU_V86__')
        assert overlay['mode']=='overlay' and overlay['renderedFaces']==21400,overlay
        focus=[]
        for f in ['T1','T2','T3','V52_04','V52_05']:
            await page.locator('#focus').select_option(f)
            d=await page.evaluate('window.__BNBU_V86__')
            assert d['meshCount']>0 and d['sourceTriangles']>0 and d['renderedFaces']==2*d['sourceTriangles'],d
            focus.append({'focus':f,'meshCount':d['meshCount'],'sourceTriangles':d['sourceTriangles']})
        await page.locator('#focus').select_option('ALL')
        await page.mouse.move(700,400);await page.mouse.down();await page.mouse.move(760,430);await page.mouse.up()
        await page.mouse.wheel(0,-200)
        await page.locator('#reset').click()
        await page.screenshot(path=str(R/'figures/BNBU_v86_registration_overlay_Chromium.png'))
        assert not errors,errors
        report.update({'success':True,'baseline':baseline,'candidate':candidate,'overlay':overlay,'focus_tests':focus,'page_errors':errors})
        await browser.close()
asyncio.run(main())
(R/'qa/v86_browser_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(report,ensure_ascii=False))