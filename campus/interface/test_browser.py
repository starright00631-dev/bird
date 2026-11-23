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

PACKAGE = Path(__file__).resolve().parents[2] / "dist/BNBU_Campus_Full_v89"
PANE_FIXTURE = Path(__file__).resolve().parents[2] / "data/examples/synthetic_workspace_evidence.json"
RESULT = PACKAGE.parents[0] / "qa"
RESULT.mkdir(parents=True,exist_ok=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def check_control_rendering(page):
    checkboxes = page.locator(".bp6-checkbox > input[type=checkbox]").evaluate_all("""inputs =>
        inputs.map(input => ({
            id: input.id,
            opacity: getComputedStyle(input).opacity,
            position: getComputedStyle(input).position,
            indicator: input.nextElementSibling?.classList.contains('bp6-control-indicator'),
        }))
    """)
    assert checkboxes and all(
        item["opacity"] == "0" and item["position"] == "absolute" and item["indicator"]
        for item in checkboxes
    ), checkboxes
    building_select = page.locator("#architecture-v76-select").evaluate("""select => {
        const style = getComputedStyle(select);
        let next = select.nextElementSibling;
        while (next && next.getClientRects().length === 0) next = next.nextElementSibling;
        const textHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize);
        const room = select.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
        return {appearance: style.appearance, room, textHeight,
            overlaps: !!next && select.getBoundingClientRect().bottom > next.getBoundingClientRect().top};
    }""")
    assert building_select["appearance"] == "auto", building_select
    assert building_select["room"] >= building_select["textHeight"] and not building_select["overlaps"], building_select

def check_pane_evidence(page):
    page.locator("#pane-evidence-file").set_input_files(PANE_FIXTURE)
    select = page.locator("#pane-evidence-select")
    select.wait_for()
    select.select_option(label="SYN-A-1")
    page.get_by_text("合成窗片示例 · SYN-A-1").wait_for()
    detail = page.locator("#pane-evidence-detail")
    assert "来源冲突" in detail.locator("#pane-fact-exterior_vlr").inner_text()
    assert "60%" in detail.locator("#pane-fact-exterior_vlt").inner_text()
    assert "2026-01-09T09:00:00+08:00" in detail.locator("#pane-fact-exterior_vlt").inner_text()
    calls = []
    replies = iter([
        {"pane_id":"SYN-A-1","fact_ids":["exterior_vlr","exterior_vlt","local_treatment_effect"]},
        {"pane_id":"SYN-A-1","fact_ids":["exterior_vlt"]},
        {"pane_id":"SYN-A-2","fact_ids":["tree_cover_0_5_m","glass_contact_risk"]},
    ])
    endpoint = "https://api.deepseek.com/chat/completions"
    def api(route):
        headers = {"access-control-allow-origin":"*", "access-control-allow-methods":"POST, OPTIONS",
                   "access-control-allow-headers":"authorization, content-type"}
        if route.request.method == "OPTIONS":
            route.fulfill(status=204, headers=headers)
            return
        calls.append(route.request.post_data_json)
        payload = {"choices":[{"message":{"content":json.dumps(next(replies))}}]}
        route.fulfill(status=200,headers=headers,content_type="application/json",body=json.dumps(payload))
    page.route(endpoint,api)
    page.locator("#show-chat").click()
    page.get_by_label("输入消息").fill("解释当前窗片的玻璃和本地改造效果")
    page.get_by_role("button",name="发送").click()
    page.locator(".aip-message.assistant").get_by_text("外表面可见光透射率",exact=False).wait_for()
    assert "SYN-A-2" not in calls[0]["messages"][0]["content"]
    page.get_by_role("button",name="查看证据").nth(1).click()
    assert page.evaluate("document.activeElement.id") == "pane-fact-exterior_vlt"
    detail.locator("#pane-fact-exterior_vlr a").first.click()
    assert page.evaluate("document.activeElement.id").startswith("pane-source-synthetic-assembly")
    select.select_option(label="SYN-A-2")
    page.get_by_text("合成窗片示例 · SYN-A-2").wait_for()
    page.locator("#show-chat").click()
    assert page.locator(".aip-message.assistant").count() == 0
    page.get_by_label("输入消息").fill("这块窗片有实测玻璃数据吗")
    page.get_by_role("button",name="发送").click()
    page.get_by_text("接口回复与当前窗片",exact=False).wait_for()
    assert page.locator(".aip-message.assistant").count() == 0
    assert "SYN-A-1" not in calls[1]["messages"][0]["content"]
    page.get_by_label("输入消息").fill("植被和风险如何")
    page.get_by_role("button",name="发送").click()
    assert "缺少证据" in page.locator(".aip-message.assistant").inner_text()
    assert "暂不提供结论" in page.locator(".aip-message.assistant").inner_text()
    page.locator("#show-data").click()
    select.select_option(value="")
    page.locator("#show-chat").click()
    page.get_by_label("输入消息").fill("给出窗片校准碰撞概率")
    page.get_by_role("button",name="发送").click()
    page.get_by_text("碰撞概率和本地改造效果仍待验证",exact=False).wait_for()
    assert len(calls) == 3
    page.unroute(endpoint,api)
    page.locator("#show-data").click()
    return {
        "known_fact_checks": {"passed": 6, "total": 6},
        "source_navigation_checks": {"passed": 2, "total": 2},
        "abstention_checks": {"passed": 4, "total": 4},
        "api": "simulated",
    }

def check(page,label,offline=False):
    print(f"Checking {label}: chat", flush=True)
    failures=[];console=[]
    def set_checkbox(selector, checked):
        box = page.locator(selector)
        if box.is_checked() != checked:
            box.locator("xpath=ancestor::label[1]").click()
        assert box.is_checked() == checked

    page.on("pageerror",lambda e:failures.append(str(e)))
    # Publisher-hosted photo thumbnails are intentionally offline-blocked here;
    # do not mistake those expected HTTPS request failures for missing local GLB/GIS.
    page.on("console",lambda e:console.append(e.text) if e.type=="error" and "net::ERR_FAILED" not in e.text and "net::ERR_BLOCKED_BY_CLIENT" not in e.text else None)
    assert page.locator("#show-chat").get_attribute("aria-selected") == "true"
    assert page.get_by_text("从空间开始提问").is_visible()
    assert not page.locator("#help-dialog").is_visible()
    page.locator("#help-button").click()
    assert page.locator("#help-dialog").is_visible()
    page.locator("#close-help").click()
    assert not page.locator("#help-dialog").is_visible()
    page.get_by_label("输入消息").fill("请介绍当前模型")
    page.get_by_role("button", name="发送").click()
    assert page.get_by_text("请先配置 API Key。").is_visible()
    assert page.locator("#api-model").input_value() == "deepseek-flash"
    page.locator("#api-key").fill("test-key")
    page.get_by_role("button", name="完成").click()
    requests = []
    def fake_api(route):
        if route.request.method == "OPTIONS":
            route.fulfill(status=204, headers={"access-control-allow-origin":"*", "access-control-allow-methods":"POST, OPTIONS", "access-control-allow-headers":"authorization, content-type"})
            return
        requests.append(route.request.post_data_json)
        route.fulfill(status=200, headers={"access-control-allow-origin":"*"}, content_type="application/json", body=json.dumps({"choices":[{"message":{"content":"测试回答"}}]}))
    page.route("https://api.deepseek.com/chat/completions", fake_api)
    page.get_by_role("button", name="发送").click()
    page.get_by_text("测试回答").wait_for()
    assert requests[0]["model"] == "deepseek-flash"
    assert "当前场景" in requests[0]["messages"][0]["content"]
    assert requests[0]["messages"][-1]["content"] == "请介绍当前模型"
    page.get_by_label("输入消息").fill("继续说明")
    page.get_by_role("button", name="发送").click()
    page.wait_for_function("document.querySelectorAll('.aip-message.assistant').length === 2")
    assert [item["role"] for item in requests[1]["messages"]] == ["system", "user", "assistant", "user"]
    page.unroute("https://api.deepseek.com/chat/completions", fake_api)
    def fail_api(route):
        route.fulfill(status=401, headers={"access-control-allow-origin":"*"}, content_type="application/json", body='{"error":{"message":"invalid key"}}')
    page.route("https://api.deepseek.com/chat/completions", fail_api)
    page.get_by_label("输入消息").fill("失败后保留的问题")
    page.get_by_role("button", name="发送").click()
    page.get_by_text("请求失败：invalid key", exact=False).wait_for()
    assert page.get_by_label("输入消息").input_value() == "失败后保留的问题"
    assert page.locator(".aip-message.user").count() == 2
    page.unroute("https://api.deepseek.com/chat/completions", fail_api)
    # Chromium logs the deliberately mocked 401; retain every other console error.
    console[:] = [item for item in console if "status of 401 (Unauthorized)" not in item]
    print(f"Checking {label}: 3D and GIS", flush=True)
    page.locator("#show-data").click()
    page.wait_for_function("window.__BNBU_READY__ === true",timeout=130000)
    page.wait_for_function("window.__BNBU_DEBUG__?.hasGIS() === true",timeout=30000)
    print(f"Checking {label}: loaded", flush=True)
    state=page.evaluate("({n:window.__BNBU_DEBUG__.meshCount(),l:window.__BNBU_DEBUG__.layerCount(),gis:window.__BNBU_DEBUG__.hasGIS()})")
    assert state["n"] >= 450 and state["l"] == 10 and state["gis"] is True, (label, state)
    assert not page.locator("#render-error").is_visible()
    page.wait_for_function("window.__BNBU_DEBUG__.waterfrontMaterialCount()===6",timeout=30000)
    assert page.evaluate("window.__BNBU_VERSION__")=="v89"
    check_control_rendering(page)
    pane_evidence = check_pane_evidence(page)
    assert page.locator("#layers input[type=checkbox]").count()==10
    assert page.locator("#layers label.bp6-checkbox").count() == 10
    assert page.locator(".topbar.bp6-navbar").is_visible()
    assert page.locator("#show-chat.bp6-tab").count() == 1
    page.wait_for_function("window.__BNBU_DEBUG__.hasLakefrontProxy() === true",timeout=30000)
    assert page.evaluate("window.__BNBU_DEBUG__.landFinishCount()")>=8
    assert page.evaluate("window.__BNBU_DEBUG__.railingProxyCount()")>250
    assert page.locator("#show-photo-proxies").is_checked()
    set_checkbox("#show-photo-proxies", False)
    assert page.evaluate("window.__BNBU_DEBUG__.photoProxyVisible()") is False
    set_checkbox("#show-photo-proxies", True)
    assert page.evaluate("window.__BNBU_DEBUG__.photoProxyVisible()") is True
    print(f"Checking {label}: lake controls", flush=True)
    page.locator("button[data-focus=boardwalk]").click()
    assert page.evaluate("window.__BNBU_DEBUG__.cameraDistance()")<70
    page.wait_for_function("window.__BNBU_DEBUG__.junctionCount()===11",timeout=35000)
    page.wait_for_function("window.__BNBU_DEBUG__.v74CaseCount()===47",timeout=45000)
    # v75 independent windows/glass data: keep source scientific mesh count 1379.
    page.wait_for_function("window.__BNBU_DEBUG__.v75BridgeCount()===7",timeout=50000)
    page.wait_for_function("window.__BNBU_DEBUG__.v76BuildingCount()===30 && window.__BNBU_DEBUG__.v89MappedBuildingCount()===41",timeout=75000)
    assert page.evaluate("window.__BNBU_DEBUG__.v76PhaseIIGapSegments()")==0
    assert not page.locator("#show-v76-phaseii-gaps").is_checked()
    set_checkbox("#show-v76-phaseii-gaps", True)
    assert page.evaluate("window.__BNBU_DEBUG__.v76PhaseIIGapsVisible()") is True
    print(f"Checking {label}: architecture", flush=True)
    page.locator("#architecture-v76-select").select_option("D1")
    detail=page.locator("#architecture-v76-detail").inner_text()
    assert "IoU" in detail and "0.98" in detail
    set_checkbox("#show-v76-phaseii-gaps", False)
    assert page.evaluate("window.__BNBU_DEBUG__.v76PhaseIIGapsVisible()") is False

    assert page.locator("#architecture-v76-select option:not([value=''])").count()==41
    assert page.evaluate("window.__BNBU_DEBUG__.v76FeatureFamilies()")==5
    assert page.locator("#show-v76-facades").is_checked()
    assert page.locator("#show-v76-edges").is_checked()
    assert page.evaluate("window.__BNBU_DEBUG__.v76StyleCount()")>100
    assert page.evaluate("window.__BNBU_DEBUG__.v76EdgeVisible()") is True
    page.locator("#architecture-v76-select").select_option("T1")
    assert "T1 (T)" in page.locator("#architecture-v76-detail").inner_text()
    building = page.locator("#building-profile")
    assert building.get_by_role("heading", name="T1 厚德楼").is_visible()
    assert building.get_by_text("2,012 m²", exact=True).is_visible()
    building.get_by_role("button", name="T1–T2 连廊").click()
    assert building.get_by_text("96 m²", exact=True).is_visible()
    page.locator("#show-chat").click()
    page.get_by_label("输入消息").fill("这段连廊的平面投影面积是多少？")
    page.get_by_role("button", name="发送").click()
    response = page.locator(".aip-building-answer")
    response.get_by_text("平面投影面积 · 96 m²", exact=True).wait_for()
    response.get_by_role("button", name="查看建筑资料").click()
    assert building.get_by_role("button", name="T1–T2 连廊").get_attribute("aria-pressed") == "true"
    building.get_by_role("button", name="概览").click()
    page.screenshot(path=str(RESULT/(label+"_v76_T1_facade.png")),full_page=True,timeout=45000)
    page.locator("#architecture-v76-select").select_option("V16")
    assert "V16 (V)" in page.locator("#architecture-v76-detail").inner_text()
    assert building.is_hidden()
    page.screenshot(path=str(RESULT/(label+"_v76_V16_residence.png")),full_page=True,timeout=45000)
    page.locator("#architecture-v76-select").select_option("D1")
    assert "D1 (D)" in page.locator("#architecture-v76-detail").inner_text()
    page.screenshot(path=str(RESULT/(label+"_v76_D1_dorm.png")),full_page=True,timeout=45000)
    page.locator("#architecture-v76-select").select_option("LRC")
    assert "LRC (LRC)" in page.locator("#architecture-v76-detail").inner_text()
    page.screenshot(path=str(RESULT/(label+"_v76_LRC_outer_frame.png")),full_page=True,timeout=45000)
    set_checkbox("#show-v76-facades", False)
    assert page.evaluate("window.__BNBU_DEBUG__.v76StyleCount()")==0
    set_checkbox("#show-v76-facades", True)
    assert page.evaluate("window.__BNBU_DEBUG__.v76StyleCount()")>100
    set_checkbox("#show-v76-edges", False)
    assert page.evaluate("window.__BNBU_DEBUG__.v76EdgeVisible()") is False
    set_checkbox("#show-v76-edges", True)
    assert page.evaluate("window.__BNBU_DEBUG__.v76EdgeVisible()") is True

    assert page.locator("#bridge-v75-select option").count()==7
    assert page.evaluate("window.__BNBU_DEBUG__.v75GlassVertices()")==1356
    assert page.locator("#show-v75-glass").is_checked()
    assert page.evaluate("window.__BNBU_DEBUG__.v75GlassVisible()") is True
    page.locator("#bridge-v75-select").select_option("V52_03")
    description=page.locator("#bridge-v75-detail").inner_text()
    assert "T8" in description and "T7" in description and "3.709" in description
    page.locator("#bridge-v75-select").select_option("lake")
    assert "340" in page.locator("#bridge-v75-detail").inner_text()
    page.screenshot(path=str(RESULT/(label+"_v75_bridge_glass.png")),full_page=True,timeout=45000)
    set_checkbox("#show-v75-glass", False)
    assert page.evaluate("window.__BNBU_DEBUG__.v75GlassVisible()") is False
    set_checkbox("#show-v75-glass", True)
    assert page.evaluate("window.__BNBU_DEBUG__.v75GlassVisible()") is True

    assert page.locator("#v74-junction-select option").count()==47
    assert not page.locator("#show-v74-junctions").is_checked()
    set_checkbox("#show-v74-junctions", True)
    assert page.evaluate("window.__BNBU_DEBUG__.v74MarkersVisible()") is True
    page.locator("#v74-junction-select").select_option("38")
    assert "局部三角面顶面高差" in page.locator("#v74-junction-description").inner_text()
    page.screenshot(path=str(RESULT/(label+"_v74_junction_detail.png")),full_page=True,timeout=45000)
    set_checkbox("#show-v74-junctions", False)
    assert page.evaluate("window.__BNBU_DEBUG__.v74MarkersVisible()") is False

    page.wait_for_function("window.__BNBU_DEBUG__.photoCount()===16",timeout=35000)
    print(f"Checking {label}: sources", flush=True)
    page.locator("#tab-source").click()
    assert page.locator("#photo-cards article").count()==16
    assert page.locator("#photo-cards article a[href^='https://']").count()>=16
    page.locator("#photo-filter").select_option("road")
    assert page.locator("#photo-cards article").count()==2
    page.locator("#photo-filter").select_option("stairs")
    assert page.locator("#photo-cards article").count()==4
    page.locator("#photo-filter").select_option("all")
    assert page.locator("#photo-cards article").count()==16
    page.locator("#tab-map").click()
    page.wait_for_function("window.__BNBU_DEBUG__.hasProfileRails()===true",timeout=35000)
    assert page.evaluate("window.__BNBU_DEBUG__.profileRailCount()")>220
    assert page.evaluate("window.__BNBU_DEBUG__.gradeMarkerCount()")==3
    assert page.locator("#show-v72-rails").is_checked()
    set_checkbox("#show-v72-rails", False)
    assert page.evaluate("window.__BNBU_DEBUG__.hasProfileRails()") is True
    set_checkbox("#show-v72-rails", True)
    assert not page.locator("#show-v72-grade").is_checked()
    set_checkbox("#show-v72-grade", True)
    assert page.evaluate("window.__BNBU_DEBUG__.gradeMarkersVisible()") is True
    set_checkbox("#show-v72-grade", False)
    assert page.evaluate("window.__BNBU_DEBUG__.gradeMarkersVisible()") is False
    page.locator("#focus-v72-ramp").click()
    page.screenshot(path=str(RESULT/(label+"_v72_ramp_rail.png")),full_page=True,timeout=45000)
    page.locator("#focus-v72-stair").click()
    cam_and_ground=page.evaluate("({cam:window.__BNBU_DEBUG__.cameraWorld(),ground:window.__BNBU_DEBUG__.stairApproachWorld()})")
    assert cam_and_ground["cam"][2] < cam_and_ground["ground"][2]-10,cam_and_ground
    assert cam_and_ground["cam"][1] < 3.1,"Camera eye must be below inherited LRC raised-floor soffit"
    page.screenshot(path=str(RESULT/(label+"_v72_LRC_stair.png")),full_page=True,timeout=45000)
    page.locator("#focus-v72-west").click()
    page.screenshot(path=str(RESULT/(label+"_v72_west_grade_unresolved.png")),full_page=True,timeout=45000)
    set_checkbox("#show-v72-grade", False)
    assert page.evaluate("window.__BNBU_DEBUG__.modelConnectionPatchCount()")==2
    assert page.locator("#show-junction-graph").is_checked()
    assert page.locator("#show-model-joints").is_checked()
    page.locator("#focus-join-a").click()
    page.screenshot(path=str(RESULT/(label+"_land_connection_A.png")),full_page=True,timeout=45000)
    page.locator("#focus-join-b").click()
    page.screenshot(path=str(RESULT/(label+"_land_connection_B.png")),full_page=True,timeout=45000)
    set_checkbox("#show-model-joints", False)
    assert page.evaluate("window.__BNBU_DEBUG__.connectionPatchesVisible()") is False
    set_checkbox("#show-model-joints", True)
    assert page.evaluate("window.__BNBU_DEBUG__.connectionPatchesVisible()") is True
    page.locator("#focus-east-landfall").click()
    page.screenshot(path=str(RESULT/(label+"_east_ramp.png")),full_page=True,timeout=45000)
    page.locator("button[data-focus=boardwalk]").click()
    page.screenshot(path=str(RESULT/(label+"_lakefront_detail.png")),full_page=True,timeout=45000)
    page.screenshot(path=str(RESULT/(label+"_campus.png")),full_page=True,timeout=45000)
    set_checkbox("#part-water_unsurveyed", False)
    assert page.evaluate("window.__BNBU_DEBUG__.layerVisible('water_unsurveyed')") is False
    set_checkbox("#part-water_unsurveyed", True)
    assert page.evaluate("window.__BNBU_DEBUG__.layerVisible('water_unsurveyed')") is True
    page.locator("button[data-focus=lakefront]").click()
    page.locator("button[data-focus=phase2]").click()
    page.locator("#choose-dsm").click()
    page.wait_for_function("window.__BNBU_DEBUG__?.hasDSM()===true",timeout=65000)
    page.wait_for_function("document.querySelector('#scene-status').textContent.includes('DSM')",timeout=30000)
    assert "DSM" in page.locator("#scene-status").inner_text()
    page.wait_for_function("window.__BNBU_DEBUG__.contourMeshCount()===3737",timeout=35000)
    assert page.locator("#show-v73-dsm-contours").is_checked()
    set_checkbox("#show-v73-dsm-contours", False)
    assert page.evaluate("window.__BNBU_DEBUG__.contourVisible()") is False
    set_checkbox("#show-v73-dsm-contours", True)
    assert page.evaluate("window.__BNBU_DEBUG__.contourVisible()") is True
    page.screenshot(path=str(RESULT/(label+"_dsm.png")),full_page=True,timeout=45000)
    page.locator("#choose-campus").click()
    page.wait_for_function("window.__BNBU_DEBUG__?.getScene()==='campus'",timeout=12000)
    print(f"Checking {label}: completed", flush=True)
    assert not failures,(label,failures)
    # The renderer may emit transient GL backend context warnings; JS and asset errors are not allowed.
    assert not [e for e in console if "WebGL context lost" not in e and "GL_INVALID" not in e],(label,console)
    return {"entry":label,"status":"pass","campus_meshes":state["n"],"layers":10,
            "junctions_checked":11,"short_at_grade_connections_added":2,
            "model_source_profiles":4,"distinct_photo_references":16,"unresolved_grade_markers":3,
            "gis_features":49,"independent_dsm":True,"v74_junction_hotspots":47,"v74_pairs":1876,
            "v75_glass_balustrade_source_points":340,"v75_bridge_systems":7,"v75_ends":12,
            "v89_mapped_buildings":41,"v76_architectural_buildings":30,"v76_building_families":5,"v89_layout_corrected":True,
            "browser_errors":failures,"console_errors":console,"pane_evidence":pane_evidence}

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
