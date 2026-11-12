"""Publish the VERIFIED self-contained offline campus viewer as a GitHub Pages site.

No CDN, no remote GLB fetch, no external build output dependencies.
The source of truth is the exact HTML that passed offline Chromium QA.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"dist"/"BNBU_Campus_Full_v76"
OFFLINE=BUNDLE/"双击查看_校园3D.html"
PAGES=ROOT/"dist"/"pages-site"
PROJECT_URL="https://starright00631-dev.github.io/bird/"

def _redirect(target,source):
    # Relative targets work beneath a GitHub project base path (/bird/),
    # as well as for local preview and any future custom domain.
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="0; url={target}">
<title>BNBU Campus Viewer — moved to current version</title>
<link rel="canonical" href="{PROJECT_URL}">
<script>location.replace({json.dumps(target)});</script>
</head><body><main>
<h1>BNBU Campus 3D viewer has moved</h1>
<p>The {source} file is a legacy path. The new viewer is standalone and includes all model assets.</p>
<p><a href="{target}">Open current BNBU 3D viewer</a></p>
</main></body></html>
"""

def build():
    assert OFFLINE.is_file(),f"First run campus/interface/build_package.py: missing {OFFLINE}"
    source=OFFLINE.read_bytes()
    assert len(source)>1_000_000 and b'id="embedded-v71"' in source
    for key in ["v76-architecture","v76-edges","v75-glass","v74-hotspots","gis","dsm"]:
        assert ('id="embedded-'+key+'"').encode() in source,key
    assert b'cdn.jsdelivr' not in source and b'unpkg.com' not in source
    assert b'window.__BNBU_VERSION__' in source
    PAGES.mkdir(parents=True,exist_ok=True)
    (PAGES/"index.html").write_bytes(source)
    (PAGES/"campus").mkdir(parents=True,exist_ok=True)
    for path,target in [
        ("campus/viewer.html","../index.html"),
        ("campus/index.html","../index.html"),
        ("viewer.html","./index.html")]:
        (PAGES/path).write_text(_redirect(target,path),encoding="utf-8")
    (PAGES/"404.html").write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><title>BNBU Viewer</title>'
        f'</head><body><h1>Page not found</h1>'
        f'<p>The campus viewer is at <a href="{PROJECT_URL}">{PROJECT_URL}</a>.</p></body></html>',
        encoding="utf-8")
    (PAGES/".nojekyll").write_text("",encoding="utf-8")
    info={
        "project":"BNBU campus model","version":"v76",
        "viewer":"standalone zero-CDN model",
        "model_mesh_count":1379,"gis_features":522,
        "source_offline_html_sha256":hashlib.sha256(source).hexdigest(),
        "site_index_html_sha256":hashlib.sha256((PAGES/"index.html").read_bytes()).hexdigest(),
        "source_commit":os.environ.get("GITHUB_SHA","local"),
        "legacy_routes":["campus/viewer.html","campus/index.html","viewer.html"],
        "url":PROJECT_URL
    }
    assert info["source_offline_html_sha256"]==info["site_index_html_sha256"]
    (PAGES/"site-status.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return info

if __name__=="__main__":
    print(json.dumps(build(),ensure_ascii=False,indent=2))
