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
NAME = "BNBU_Campus_Full_v72"
PACKAGE = OUT / NAME
ZIP_PATH = OUT / (NAME + ".zip")
ASSETS = {
    "generated/BNBU_v66_SEMANTIC_Y_UP.glb": "generated/BNBU_v66_SEMANTIC_Y_UP.glb",
    "generated/BNBU_v69_WATERFRONT_REFINED.glb": "generated/BNBU_v69_WATERFRONT_REFINED.glb",
    "generated/BNBU_v69_WATERFRONT_PROVENANCE.json": "generated/BNBU_v69_WATERFRONT_PROVENANCE.json",
    "generated/BNBU_v70_LAKEFRONT_DISPLAY_OVERLAY.json": "generated/BNBU_v70_LAKEFRONT_DISPLAY_OVERLAY.json",
    "generated/BNBU_v71_CONNECTED_LAKEFRONT.glb": "generated/BNBU_v71_CONNECTED_LAKEFRONT.glb",
    "generated/BNBU_v71_CONNECTION_PATCHES.geojson": "generated/BNBU_v71_CONNECTION_PATCHES.geojson",
    "generated/BNBU_v71_JUNCTION_AUDIT.geojson": "generated/BNBU_v71_JUNCTION_AUDIT.geojson",
    "generated/BNBU_v71_CONNECTION_PROVENANCE.json": "generated/BNBU_v71_CONNECTION_PROVENANCE.json",
    "generated/BNBU_v72_SOURCE_ELEVATION_PROFILES.json": "generated/BNBU_v72_SOURCE_ELEVATION_PROFILES.json",
    "evidence/connection_photos_v72.json": "connection_photos_v72.json",
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
    "src/build_lakefront_v70.py": "build_lakefront_v70.py",
    "src/build_connection_v71.py": "build_connection_v71.py",
    "src/test_connection_v71.py": "test_connection_v71.py",
    "src/build_connection_profiles_v72.py": "build_connection_profiles_v72.py",
    "src/test_connection_profiles_v72.py": "test_connection_profiles_v72.py",
    "src/connection_v71_control.json": "connection_v71_control.json",
    "src/build_terrain_v67.py": "build_terrain_v67.py",
    "src/test_v65.py": "test_v65.py",
    "src/test_v66.py": "test_v66.py",
    "src/test_waterfront_v69.py": "test_waterfront_v69.py",
    "src/test_lakefront_v70.py": "test_lakefront_v70.py",
    "src/test_terrain_v67.py": "test_terrain_v67.py",
    "src/validate_scene.py": "validate_scene.py",
    "docs/README_source.md": "README.md",
    "docs/WATERFRONT_V69_EVIDENCE.md": "WATERFRONT_V69_EVIDENCE.md",
    "docs/LAKEFRONT_V70_CRITICAL_COMPARISON.md": "LAKEFRONT_V70_CRITICAL_COMPARISON.md",
    "docs/JUNCTION_V71_AUDIT.md": "JUNCTION_V71_AUDIT.md",
    "docs/PHOTO_CONNECTION_AUDIT_V72.md": "PHOTO_CONNECTION_AUDIT_V72.md",
}

README = """# BNBU 校园完整三维模型与查看器 v72

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
- generated：v66 源GIS，v69 材质源，v70 独立桥栏杆，v71 两块源模型拼接（GLB+GIS+11项关系审核），v72 沿真实 122 顶点既有斜坡/19级既有楼梯的四组来源采样轨迹；v67 独立 ALOS 地形。
- src：源码及测试、来源记录；manifest.json：文件完整性 SHA-256。

数据准确性：v71 显示 1379 个三维网格，其中 v69 继承 v66 的 1377 个原有网格是继承模型，不等于 1377
个已测量真实构件。湖岸、车行路边线、玻璃面积和山体相对标高未实测。
CTV 附近小屋的身份和屋顶尺寸未得到独立核实。
ALOS 约 30 m DSM 含植被和建筑，不等于裸地 DEM，不能直接与
v69 建筑的相对 Z 标高合并。不得将模型作为定量鸟撞玻璃暴露分母。

新增 v70：使用校园湖岸照片对照，仅沿已有 V60 高架廊道多边形置入可关闭的栏杆视觉参考，现有 V13 草地改成草地表面材质、V61 实体临水平台改成石质铺装表面，均不调整范围和高度，渲染值不是实测。出于可追溯性，这些添加的栏杆从 1,377 个原始网格之外单独渲染，不用于鸟撞分析。\n\n原 v69：以原 SHORE 网格模型相对高程推导湿岸—植被岸材质渐变；将水面与历史湿地水面分开设定光学外观；并在查看器标出既有临水廊道轮廓与近岸视角。没有改变湖塘的平面轮廓、地形高程或新增建筑。学校官方于 2019 年记录东侧赤花山脚下湿地与两处淡水池塘，位置未经摄影测量配准；**不要把二期历史湿地模型当成那两处池塘**。

新增 v71：针对湖岸平台与步道相交的真实照片类型，对照原GLB与GIS检查11对构件间关系。仅在原V61铺装层两个2.44/2.50模型单位间隙，新增两块顶面与原板一致的细小几何；**不代表精确实地测量**。另外有三处高度矛盾、两处较远的路线缺口仍保持未更改；桥东坡道与ROAD_000→WALK_040铺装拼缝已存在，不再额外造桥。全部原有1377网格数据与522条GIS边界不变。查看 docs/JUNCTION_V71_AUDIT.md。

新增 v72：根据16张不同位置真实校园照片识别和核对水岸、道路、LRC外立面与桥的连接类型；这些图片是原网站的链接，未获得摄影配准，因此不能据此修改校园绝对XY坐标。可独立关闭的两侧坡道、楼梯扶手沿旧 GLB 顶点数据中的真实三维曲线逐点放置；扶手高度为典型示意，非现场测量。3处 3D 高差（0.24/0.64/0.64 模型单位）仍以检查标记呈现，并非新造坡道。详情见 docs/PHOTO_CONNECTION_AUDIT_V72.md 和 evidence/connection_photos_v72.json。浏览三维模型完全离线；“证据和数据”里的远程照片缩略图需要联网后才会加载。切勿将这些示意扶手算入可用于鸟撞风险的玻璃面积。

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
        ("v71","generated/BNBU_v71_CONNECTED_LAKEFRONT.glb"),
        ("dsm","generated/BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb"),
    ]:
        b64=base64.b64encode((PACKAGE/rel).read_bytes()).decode("ascii")
        tags.append('<script id="embedded-'+key+'" type="application/octet-stream">'+b64+'</script>')
    for key,rel in [
        ("gis","generated/BNBU_v66_RESOLVED_REFERENCES.geojson"),
        ("contours","generated/BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson"),
        ("dsm-meta","generated/BNBU_v67_TERRAIN_SOURCE_AND_LIMITS.json"),
        ("lakefront","generated/BNBU_v70_LAKEFRONT_DISPLAY_OVERLAY.json"),
        ("junctions","generated/BNBU_v71_JUNCTION_AUDIT.geojson"),
        ("junction-patches","generated/BNBU_v71_CONNECTION_PATCHES.geojson"),
        ("junction-meta","generated/BNBU_v71_CONNECTION_PROVENANCE.json"),
        ("profile-v72","generated/BNBU_v72_SOURCE_ELEVATION_PROFILES.json"),
        ("photos-v72","evidence/connection_photos_v72.json"),
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
    overlay=json.loads((PACKAGE/"generated/BNBU_v70_LAKEFRONT_DISPLAY_OVERLAY.json").read_text(encoding="utf-8"))
    assert overlay["role"]=="DISPLAY_ONLY_NO_METRIC_GEOMETRY"
    assert overlay["original_meshes"]==1377
    joints=json.loads((PACKAGE/"generated/BNBU_v71_JUNCTION_AUDIT.geojson").read_text())
    patches=json.loads((PACKAGE/"generated/BNBU_v71_CONNECTION_PATCHES.geojson").read_text())
    details=json.loads((PACKAGE/"generated/BNBU_v71_CONNECTION_PROVENANCE.json").read_text())
    assert len(joints["features"])==11 and len(patches["features"])==2
    assert details["original_meshes"]==1377 and details["output_meshes"]==1379
    grade=json.loads((PACKAGE/"generated/BNBU_v72_SOURCE_ELEVATION_PROFILES.json").read_text())
    photos=json.loads((PACKAGE/"evidence/connection_photos_v72.json").read_text())
    assert len(grade["rail_profiles"])==4 and len(grade["height_disagreement_markers"])==3
    assert len(photos["photos"])==16 and grade["photo_count_inspected"]==16
    for rel in ["generated/BNBU_v71_CONNECTED_LAKEFRONT.glb",
                "generated/BNBU_v69_WATERFRONT_REFINED.glb",
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
        "name":NAME,"source_model":"v64","geometry_scene":"v66","render_scene":"v72 viewer plus model v71 exact GLB + 4 source-sampled handrails; no source geometry edits","external_DSM":"v67",
        "mesh_count":1379,"original_mesh_count":1377,"GIS_feature_count":522,
        "v71_source_bounded_pavement_seams":2,"audited_junction_pairs":11,
        "v72_optional_source_height_rail_profiles":4,"v72_observed_distinct_photo_links":16,
        "v70_photo_typology_lakefront_overlay":True,
        "v69_material_and_shore_color_refinement":True,
        "original_geometry_edited":False,"new_geometry_approximate_and_unsurveyed":True,
        "standalone_file_embeds_assets":True,
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
