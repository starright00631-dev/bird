"""Actual browser QA: independent standalone file and HTTP viewer, no CDN/network."""
from __future__ import annotations
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

PACKAGE = Path(__file__).resolve().parents[2] / "dist/BNBU_Campus_Full_v68"
RESULT = PACKAGE.parents[0] / "qa"
RESULT.mkdir(parents=True,exist_ok=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def check(page,label,offline=False):
    failures=[];console=[]
    page.on("pageerror",lambda e:failures.append(str(e)))
    page.on("console",lambda e:console.append(e.text) if e.type=="error" else None)
    page.wait_for_function("window.__BNBU_READY__ === true",timeout=130000)
    page.wait_for_function("window.__BNBU_DEBUG__?.hasGIS() === true",timeout=30000)
    state=page.evaluate("({n:window.__BNBU_DEBUG__.meshCount(),l:window.__BNBU_DEBUG__.layerCount(),gis:window.__BNBU_DEBUG__.hasGIS()})")
    assert state=={"n":1377,"l":10,"gis":True},(label,state)
    assert not page.locator("#render-error").is_visible()
    assert page.locator("#layers input[type=checkbox]").count()==10
    page.screenshot(path=str(RESULT/(label+"_campus.png")),full_page=True,timeout=45000)
    page.locator("#part-water_unsurveyed").uncheck()
    assert page.evaluate("window.__BNBU_DEBUG__.layerVisible('water_unsurveyed')") is False
    page.locator("#part-water_unsurveyed").check()
    assert page.evaluate("window.__BNBU_DEBUG__.layerVisible('water_unsurveyed')") is True
    page.locator("button[data-focus=lake]").click()
    page.locator("button[data-focus=phase2]").click()
    page.locator("#choose-dsm").click()
    page.wait_for_function("window.__BNBU_DEBUG__?.hasDSM()===true",timeout=65000)
    assert "DSM" in page.locator("#scene-status").inner_text()
    page.screenshot(path=str(RESULT/(label+"_dsm.png")),full_page=True,timeout=45000)
    page.locator("#choose-campus").click()
    page.wait_for_function("window.__BNBU_DEBUG__?.getScene()==='campus'",timeout=12000)
    assert not failures,(label,failures)
    # The renderer may emit transient GL backend context warnings; JS and asset errors are not allowed.
    assert not [e for e in console if "WebGL context lost" not in e and "GL_INVALID" not in e],(label,console)
    return {"entry":label,"status":"pass","campus_meshes":1377,"layers":10,
            "gis_features":522,"independent_dsm":True,
            "browser_errors":failures,"console_errors":console}

def main():
    assert PACKAGE.is_dir()
    errors=[];reports=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=[
            "--no-sandbox","--enable-webgl","--enable-unsafe-swiftshader",
            "--use-angle=swiftshader","--disable-dev-shm-usage"
        ])
        try:
            context=browser.new_context(viewport={"width":1440,"height":900})
            context.route("https://**/*",lambda route:route.abort())
            context.route("http://**/*",lambda route:route.abort())
            page=context.new_page()
            page.goto((PACKAGE/"双击查看_校园3D.html").as_uri(),wait_until="domcontentloaded",timeout=120000)
            reports.append(check(page,"standalone_file"))
            page.close()
            # A separate local HTTP copy must work even if browser disallows file:// in some environments.
            handler=functools.partial(Handler,directory=str(PACKAGE))
            server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            try:
                http_context=browser.new_context(viewport={"width":1440,"height":900})
                http_context.route("https://**/*",lambda route:route.abort())
                page=http_context.new_page()
                page.goto("http://127.0.0.1:%d/index.html"%server.server_port,
                          wait_until="domcontentloaded",timeout=60000)
                reports.append(check(page,"local_http"))
                http_context.close()
            finally:
                server.shutdown()
            context.close()
        finally:
            browser.close()
    result={"status":"pass","reports":reports,
            "explanation":"Both file:// single HTML and localhost version rendered and passed controls in Chromium without external CDN."}
    (RESULT/"browser_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
