"""Browser smoke test for the ACTUAL GitHub Pages file layout and legacy URLs."""
from __future__ import annotations
import functools
import http.server
import json
import threading
import urllib.request
from playwright.sync_api import sync_playwright
from build_pages_site import build,PAGES

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def check():
    report=build()
    handler=functools.partial(QuietHandler,directory=str(PAGES))
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
    thr=threading.Thread(target=server.serve_forever,daemon=True)
    thr.start()
    url=f"http://127.0.0.1:{server.server_address[1]}"
    try:
        data=json.loads(urllib.request.urlopen(url+"/site-status.json").read().decode())
        assert data["source_offline_html_sha256"]==report["site_index_html_sha256"]
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
            page=browser.new_page(viewport={"width":1200,"height":820})
            errors=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            response=page.goto(url+"/index.html",wait_until="domcontentloaded",timeout=110000)
            assert response.status==200
            page.wait_for_function("window.__BNBU_READY__ === true",timeout=130000)
            page.wait_for_function("window.__BNBU_DEBUG__.v76BuildingCount()===30",timeout=60000)
            assert page.evaluate("window.__BNBU_VERSION__")== "v76"
            assert page.evaluate("window.__BNBU_DEBUG__.meshCount()")==1379
            assert page.locator("#architecture-v76-select option").count()==30
            assert not errors,errors
            # This is exactly the path the older README exposed. It must not
            # load the stale CDN-dependent v66 viewer.
            page.goto(url+"/campus/viewer.html",wait_until="domcontentloaded",timeout=110000)
            page.wait_for_url(url+"/index.html",timeout=30000)
            page.wait_for_function("window.__BNBU_READY__ === true",timeout=130000)
            assert page.evaluate("window.__BNBU_VERSION__")=="v76"
            assert not errors,errors
            browser.close()
        print("GitHub Pages layout + /campus/viewer.html redirect passed, v76 and 1379 meshes")
    finally:
        server.shutdown()
        server.server_close()

if __name__=="__main__":check()
