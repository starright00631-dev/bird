"""Bundle all verified BNBU research assets and a standalone, offline viewer."""
from __future__ import annotations

import base64
import hashlib
import json
import lzma
import shutil
import stat
import struct
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPUS = HERE.parent
OUT = CAMPUS.parent / "dist"
NAME = "BNBU_Campus_Full_v69"
PACKAGE = OUT / NAME
ZIP_PATH = OUT / (NAME + ".zip")
ASSETS = {
    "generated/BNBU_v66_SEMANTIC_Y_UP.glb": "generated/BNBU_v66_SEMANTIC_Y_UP.glb",
    "generated/BNBU_v69_WATERFRONT_REFINED.glb": "generated/BNBU_v69_WATERFRONT_REFINED.glb",
    "generated/BNBU_v69_WATERFRONT_PROVENANCE.json": "generated/BNBU_v69_WATERFRONT_PROVENANCE.json",
    "generated/BNBU_v66_RESOLVED_REFERENCES.geojson": "generated/BNBU_v66_RESOLVED_REFERENCES.geojson",
    "generated/v66_provenance.json": "generated/v66_provenance.json",
    "generated/BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb": "generated/BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb",
    "generated/BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson": "generated/BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson",
    "generated/BNBU_v67_TERRAIN_SOURCE_AND_LIMITS.json": "generated/BNBU_v67_TERRAIN_SOURCE_AND_LIMITS.json",
    "history/BNBU_v65_DISPLAY_Y_UP.glb": "generated/BNBU_v65_DISPLAY_Y_UP.glb",
    "history/BNBU_v65_RENDER_REFERENCES.geojson": "generated/BNBU_v65_RENDER_REFERENCES.geojson",
    "history/v65_integrity_manifest.json": "generated/v65_integrity_manifest.json",
    "source/v64/BNBU_v64_ACTIVE.glb": "assets/BNBU_v64_ACTIVE.glb",
    "source/v64/BNBU_v64_ACTIVE.geojson": "assets/BNBU_v64_ACTIVE.geojson",
    "source/v64/BNBU_v64_ACTIVE.kml": "assets/BNBU_v64_ACTIVE.kml",
    "source/v64/BNBU_v64_EDITABLE_GIS.gpkg": "assets/BNBU_v64_EDITABLE_GIS.gpkg",
    "source/archives/BNBU_v64_ACTIVE.glb.xz": "assets/BNBU_v64_ACTIVE.glb.xz",
    "source/archives/BNBU_v64_ACTIVE.geojson.xz": "assets/BNBU_v64_ACTIVE.geojson.xz",
    "source/archives/BNBU_v64_ACTIVE.kml.xz": "assets/BNBU_v64_ACTIVE.kml.xz",
    "source/archives/BNBU_v64_EDITABLE_GIS.gpkg.xz": "assets/BNBU_v64_EDITABLE_GIS.gpkg.xz",
    "source/CTV_UNVERIFIED_DO_NOT_MERGE.geojson.xz": "assets/BNBU_v64_CTV_EXCLUDED.geojson.xz",
    "source/CTV_UNVERIFIED_DO_NOT_MERGE.glb.xz": "assets/BNBU_v64_CTV_UNVERIFIED_GEOMETRY_DO_NOT_USE_AS_SURVEY.glb.xz",
    "src/build_v65.py": "build_v65.py",
    "src/build_v66.py": "build_v66.py",
    "src/refine_waterfront_v69.py": "refine_waterfront_v69.py",
    "src/build_terrain_v67.py": "build_terrain_v67.py",
    "src/test_v65.py": "test_v65.py",
    "src/test_v66.py": "test_v66.py",
    "src/test_waterfront_v69.py": "test_waterfront_v69.py",
    "src/test_terrain_v67.py": "test_terrain_v67.py",
    "src/validate_scene.py": "validate_scene.py",
    "docs/README_source.md": "README.md",
    "docs/WATERFRONT_V69_EVIDENCE.md": "WATERFRONT_V69_EVIDENCE.md",
}

README = """# BNBU 校园完整三维模型与查看器 v69

## 最简单的打开方式

解压整个 ZIP，**双击 双击查看_校园3D.html 即可直接打开**。
这是独立离线文件：无需 Python、Node.js、CDN 或网络。

也可以双击 启动查看器.bat（需要 Python 3）；它将自动启动本机 Web
服务并打开 index.html。macOS/Linux 可运行 start_viewer.sh。

## 功能

三维旋转、缩放、平移、点击查看构件，10 类要素切换，
一期 / 二期 / 主湖近岸 / 湿地历史模型 / 山体 / 临水廊道定位，
原有 522 条 GIS 矢量轮廓离线预览，独立的 ALOS DSM 场景。
建筑模型与遥感地形模型的标高未配准，绝不直接叠加。

## 包内文件

- source/v64：完整原始 GLB、GPKG、GeoJSON、KML。
- source/archives：v64 无损 XZ 源归档。
- source/CTV_UNVERIFIED_DO_NOT_MERGE.*：隔离的 CTV 小建筑推测记录，非活动场景。
- history：v65 坐标方向和节点关联版本。
- generated：v66 原几何与 GIS，v69 水岸反射材质 / 连续岸坡颜色版本；v67 ALOS 地形与插值等高线。
- src：源码及测试、来源记录；manifest.json：文件完整性 SHA-256。

数据准确性：v69 继承 v66 的 1377 个三维网格是继承模型，不等于 1377
个已测量真实构件。湖岸、车行路边线、玻璃面积和山体相对标高未实测。
CTV 附近小屋的身份和屋顶尺寸未得到独立核实。
ALOS 约 30 m DSM 含植被和建筑，不等于裸地 DEM，不能直接与
v69 建筑的相对 Z 标高合并。不得将模型作为定量鸟撞玻璃暴露分母。

新增 v69：以原 SHORE 网格模型相对高程推导湿岸—植被岸材质渐变；将水面与历史湿地水面分开设定光学外观；并在查看器标出既有临水廊道轮廓与近岸视角。没有改变湖塘的平面轮廓、地形高程或新增建筑。学校官方于 2019 年记录东侧赤花山脚下湿地与两处淡水池塘，位置未经摄影测量配准；**不要把二期历史湿地模型当成那两处池塘**。

源码：https://github.com/starright00631-dev/bird/tree/main/campus
"""

SERVER = '''"""Start a standard-library server on localhost only."""
from __future__ import annotations
import functools, http.server, threading, time, webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control","no-store")
        super().end_headers()
    def guess_type(self,path):
        if path.endswith(".glb"): return "model/gltf-binary"
        if path.endswith(".geojson"): return "application/geo+json"
        return super().guess_type(path)
if __name__=="__main__":
    handler=functools.partial(Handler,directory=str(ROOT))
    with http.server.ThreadingHTTPServer(("127.0.0.1",0),handler) as server:
        url="http://127.0.0.1:%d/index.html"%server.server_port
        print("Viewer URL:",url,flush=True)
        threading.Thread(target=lambda:(time.sleep(.5),webbrowser.open(url)),daemon=True).start()
        server.serve_forever()
'''

BAT = '''@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 serve.py
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  python serve.py
  goto :eof
)
echo 请直接双击 双击查看_校园3D.html 查看离线三维校园。
pause
'''

SH = '''#!/bin/sh
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then exec python3 serve.py; fi
if command -v python >/dev/null 2>&1; then exec python serve.py; fi
echo "Open the standalone HTML instead; Python was not found."
'''

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as inp:
        while (data:=inp.read(1048576)): h.update(data)
    return h.hexdigest()

def assemble_standalone(template,css,js):
    tags=[]
    for key,rel in [
        ("v69","generated/BNBU_v69_WATERFRONT_REFINED.glb"),
        ("dsm","generated/BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb"),
    ]:
        b64=base64.b64encode((PACKAGE/rel).read_bytes()).decode("ascii")
        tags.append('<script id="embedded-'+key+'" type="application/octet-stream">'+b64+'</script>')
    for key,rel in [
        ("gis","generated/BNBU_v66_RESOLVED_REFERENCES.geojson"),
        ("contours","generated/BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson"),
        ("dsm-meta","generated/BNBU_v67_TERRAIN_SOURCE_AND_LIMITS.json"),
    ]:
        content=(PACKAGE/rel).read_text(encoding="utf-8").replace("</script","<\\/script")
        tags.append('<script id="embedded-'+key+'" type="application/json">'+content+'</script>')
    standalone=template.replace('<link rel="stylesheet" href="./viewer.css">','<style>'+css+'</style>')
    standalone=standalone.replace('<!-- PACKAGER_EMBEDDED_DATA -->','\n'.join(tags))
    standalone=standalone.replace('<script src="./viewer.js"></script>','<script>'+js.replace("</script","<\\/script")+'</script>')
    assert "./viewer.js" not in standalone
    assert "cdn.jsdelivr" not in standalone
    assert "unpkg.com" not in standalone
    return standalone

def validate():
    gis=json.loads((PACKAGE/"generated/BNBU_v66_RESOLVED_REFERENCES.geojson").read_text(encoding="utf-8"))
    assert len(gis["features"])==522
    for rel in ["generated/BNBU_v69_WATERFRONT_REFINED.glb",
                "generated/BNBU_v66_SEMANTIC_Y_UP.glb",
                "generated/BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb",
                "source/v64/BNBU_v64_ACTIVE.glb"]:
        data=(PACKAGE/rel).read_bytes()
        assert data[:4]==b"glTF" and struct.unpack_from("<II",data,4)==(2,len(data))
    assert (PACKAGE/"source/v64/BNBU_v64_EDITABLE_GIS.gpkg").read_bytes()[:16]==b"SQLite format 3\x00"
    archived=(PACKAGE/"source/archives/BNBU_v64_ACTIVE.glb.xz").read_bytes()
    assert lzma.decompress(archived)==(PACKAGE/"source/v64/BNBU_v64_ACTIVE.glb").read_bytes()
    assert (PACKAGE/"双击查看_校园3D.html").stat().st_size>18_000_000

def build():
    bundled=HERE/"dist/viewer.bundle.js"
    if not bundled.is_file() or bundled.stat().st_size<250000:
        raise FileNotFoundError("Three.js is not bundled: run npm build first")
    missing=[src for src in ASSETS.values() if not (CAMPUS/src).is_file()]
    if missing: raise FileNotFoundError("Missing required assets: "+repr(missing))
    if PACKAGE.exists():shutil.rmtree(PACKAGE)
    PACKAGE.mkdir(parents=True)
    for dest,src in ASSETS.items():
        target=PACKAGE/dest
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(CAMPUS/src,target)
    template=(HERE/"index.template.html").read_text(encoding="utf-8")
    css=(HERE/"viewer.css").read_text(encoding="utf-8")
    js=bundled.read_text(encoding="utf-8")
    (PACKAGE/"index.html").write_text(template.replace('<!-- PACKAGER_EMBEDDED_DATA -->',''),encoding="utf-8")
    (PACKAGE/"viewer.css").write_text(css,encoding="utf-8")
    (PACKAGE/"viewer.js").write_text(js,encoding="utf-8")
    (PACKAGE/"双击查看_校园3D.html").write_text(assemble_standalone(template,css,js),encoding="utf-8")
    (PACKAGE/"README_打开方式.md").write_text(README,encoding="utf-8")
    (PACKAGE/"serve.py").write_text(SERVER,encoding="utf-8")
    (PACKAGE/"启动查看器.bat").write_text(BAT,encoding="utf-8")
    sh=PACKAGE/"start_viewer.sh"
    sh.write_text(SH,encoding="utf-8");sh.chmod(sh.stat().st_mode|stat.S_IXUSR)
    validate()
    manifest={
        "name":NAME,"source_model":"v64","geometry_scene":"v66","render_scene":"v69","external_DSM":"v67",
        "mesh_count":1377,"GIS_feature_count":522,
        "v69_material_and_shore_color_refinement":True,
        "physical_geometry_edited":False,"standalone_file_embeds_assets":True,
        "files":{str(p.relative_to(PACKAGE)):{"size":p.stat().st_size,"sha256":sha256(p)}
            for p in PACKAGE.rglob("*") if p.is_file()},
    }
    (PACKAGE/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    if ZIP_PATH.exists():ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH,"w",zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as out:
        for p in PACKAGE.rglob("*"):
            if p.is_file():out.write(p,arcname=str(Path(NAME)/p.relative_to(PACKAGE)))
    with zipfile.ZipFile(ZIP_PATH) as z:
        assert z.testzip() is None
    print(json.dumps({"zip":str(ZIP_PATH),"zip_bytes":ZIP_PATH.stat().st_size,
        "standalone_html_bytes":(PACKAGE/"双击查看_校园3D.html").stat().st_size,
        "file_count":len(manifest["files"])+1},ensure_ascii=False,indent=2))
    return ZIP_PATH

if __name__=="__main__":build()
