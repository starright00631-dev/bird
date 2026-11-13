#!/usr/bin/env python3
import argparse, asyncio, json, re, subprocess, tempfile, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT
HTML=MASTER/'双击查看_校园3D.html'
INDEX=MASTER/'index.html'
OUT=ROOT/'release_qa'/'v88_browser_validation.json'

def node_check(path):
    s=path.read_text('utf-8')
    scripts=re.findall(r'<script(?![^>]*type="(?:application/json|application/octet-stream)")[^>]*>(.*?)</script>',s,re.S|re.I)
    for i,script in enumerate(scripts):
        p=subprocess.run(['node','--check'],input=script,text=True,capture_output=True)
        if p.returncode: raise AssertionError(f'{path.name} inline script {i}: {p.stderr}')
    p=subprocess.run(['node','--check'],input=(MASTER/'viewer.js').read_text('utf-8'),text=True,capture_output=True)
    if p.returncode: raise AssertionError(p.stderr)
    return len(scripts)

async def exercise(page,label,errors):
    page.on('pageerror',lambda e:errors.append(f'{label}: {e}'))
    await page.wait_for_function("window.__BNBU_DEBUG__ && window.__BNBU_DEBUG__.meshCount()===1378 && window.__BNBU_DEBUG__.v88MappedAssetCount()===38",timeout=240000)
    debug=await page.evaluate("({version:window.__BNBU_VERSION__,meshCount:window.__BNBU_DEBUG__.meshCount(),core:window.__BNBU_DEBUG__.v76BuildingCount(),mapped:window.__BNBU_DEBUG__.v88MappedAssetCount(),bridges:window.__BNBU_DEBUG__.v75BridgeCount(),junctions:window.__BNBU_DEBUG__.junctionCount(),phaseIIGaps:window.__BNBU_DEBUG__.v76PhaseIIGapSegments()})")
    assert debug['version']=='v88',debug
    assert debug['meshCount']==1378 and debug['core']==30 and debug['mapped']==38,debug
    select=page.locator('#architecture-v76-select')
    assert await select.count()==1
    options=await select.locator('option').evaluate_all('(els)=>els.map(e=>e.value)')
    required=['T29','ADMIN','HALL','SPORT','THEATRE','CC','YUZHAN','P2_CIRCULAR_COMMONS']
    missing=[x for x in required if x not in options]
    assert not missing,missing
    focus=[]
    for asset in required:
        await select.select_option(asset)
        await page.wait_for_timeout(120)
        detail=await page.locator('#architecture-v76-detail').inner_text()
        assert asset in detail,(asset,detail)
        focus.append(asset)
    # Confirm original whole-campus controls remain functional.
    await page.locator('#architecture-v76-select').select_option('T1')
    await page.wait_for_timeout(120)
    return {'entry':label,'debug':debug,'extended_asset_focus':focus,'options_count':len(options)}

async def main():
    ap=argparse.ArgumentParser();ap.add_argument('--set-content-only',action='store_true');args=ap.parse_args()
    report={'version':'v88','node_script_count':node_check(HTML),'file_navigation':'NOT_RUN','http_navigation':'NOT_RUN','tests':[]}
    errors=[]
    async with async_playwright() as p:
        launch={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
        if Path('/usr/bin/chromium').exists(): launch['executable_path']='/usr/bin/chromium'
        browser=await p.chromium.launch(**launch)
        if args.set_content_only:
            page=await browser.new_page(viewport={'width':1365,'height':900})
            await page.set_content(HTML.read_text('utf-8'),wait_until='domcontentloaded',timeout=240000)
            report['tests'].append(await exercise(page,'Chromium set_content',errors))
            report['set_content']='PASS';report['file_navigation']='BLOCKED_BY_EXECUTION_ENVIRONMENT';report['http_navigation']='BLOCKED_BY_EXECUTION_ENVIRONMENT'
        else:
            page=await browser.new_page(viewport={'width':1365,'height':900})
            await page.goto(HTML.resolve().as_uri(),wait_until='domcontentloaded',timeout=240000)
            report['tests'].append(await exercise(page,'Chromium file://',errors));report['file_navigation']='PASS'
            with tempfile.TemporaryDirectory() as td:
                # Serve the entire campus package, not only the HTML, so relative GLB/GIS paths are available.
                class Handler(SimpleHTTPRequestHandler):
                    def __init__(self,*a,**kw):super().__init__(*a,directory=str(MASTER),**kw)
                    def log_message(self,*a):pass
                server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    page2=await browser.new_page(viewport={'width':1365,'height':900})
                    await page2.goto(f'http://127.0.0.1:{server.server_port}/index.html',wait_until='domcontentloaded',timeout=240000)
                    report['tests'].append(await exercise(page2,'Chromium localhost HTTP',errors));report['http_navigation']='PASS'
                finally:server.shutdown();thread.join(timeout=5);server.server_close()
        await browser.close()
    report['page_errors']=errors;report['success']=len(errors)==0 and len(report['tests'])>0
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if not report['success']:raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())