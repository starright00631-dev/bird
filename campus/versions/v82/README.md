# BNBU Zhuhai editable GIS / 3D · v82 (2026-11-12)

This is **an actual mesh-winding repair and usable CPU 3D viewer**, not a reconstructed campus. Direct parent **v81**, which has already reconciled the earlier main v76.1 and branch v76 LRC skylight. Source v10 is archived as a reference only. The main GLB retains every active component from v81.

## Actual model delta

In the v81 active GLB, two inherited `V71_LRC_LAKESIDE_SOURCE_MATCHED_GRADE_JOINT_*_NOT_SURVEYED` LRC lakeside grade joints were closed yet winding-inconsistent and had negative signed mesh volume. Their top and bottom faces were already present; eight of the twelve side-face triangle index windings per mesh were backwards. They were repaired in v82 using mesh normal consistency. Exactly **16 triangle face index orders** were corrected across **two original meshes**. No vertex position, mesh boundary, material, height, surface or topological connection was added. The sum of triangles remains **691,907** across **1,347 nodes**. The corrected volumes are **+0.748137 and +0.764481 model m³** versus negative values beforehand. All 1,345 other meshes were independently re-imported and compared for byte-equivalent vertex arrays, face indices, transforms, visual UV/colors.

`model/BNBU_v82_LRC_WINDING_FIXED_ONLY.glb` contains the actual corrected triangles for isolated inspection. The parent GLB is saved in `input/`, not thrown away.

## Viewer functionality

`viewer/BNBU_Campus_3D_CPU_v82.html` is a standalone, no-network, no-WebGL 3D **CPU Canvas** renderer. It consumes source triangle triples extracted from **all 1,347 actual v82 mesh nodes** and contains selectable mesh categories, orbit, pan, zoom, focus and source face ID inspection. For full LRC preview, **all 51,880 original source triangles in its category** are retained in the CPU display; elsewhere the CPU LOD samples only existing source triangles without creating interpolated geometry. The display-only payload rounds coordinates to 0.001 model units to keep the HTML compact; never use CPU triangles for dimensional measurement or replace the GLB with the display LOD.

Chromium **executed** the standalone viewer code via `page.set_content` and successfully rendered, switched to LRC, toggled layer visibility and orbited; zero JS errors. The runtime **blocks navigation to file:, data: and localhost URLs**, so ordinary `file://`/HTTP page opening could not be proven here. WebGL full viewer still cannot be validated in this environment. This is why the CPU viewer is the **default** `viewer/双击查看_校园3D.html` entry point.

`viewer/BNBU_Campus_3D_Offline_v82.html` is a full-resolution Three.js option with a verified exact updated 13.9 MB v82 GLB embedded (SHA256 checked against standalone GLB), legacy optional display-only layers unchecked by default, and a prominent CPU fallback link. It has no main-GLB external URL. Its module JS passed `node --check` but real WebGL display was **not** confirmed. Main branch GitHub Pages still depends on the owner's Settings > Pages > GitHub Actions selection; a branch PR does not publish the public site.

## GIS & strict provenance

The underlying XY outlines did not change. The entire v81 GPKG (146 layers), active GeoJSON/KML (534 features/placemarks) and display-only archives are copied **SHA256-identically** into v82-named outputs. This prevents duplicate GIS features for an orientation-only change. Provenance remains `EPSG:32649` local offset `(758940, 2474080)` for GLB X/Y, `EPSG:4326` for GIS, with unsurveyed **model-relative Z**. The official hand-drawn campus illustration <https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg> is only a topology constraint; Ronald Lu & Partners <https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/> provides architecture *type* context, not exact camera-registered coordinates.

The previous six guessed V49 radial connectors, 26 V60 support meshes and one inferred V54 lakeside ramp remain out of main GLB (v80/v81 display-only archives). No old 690 fake glazing bands, six unsupported guardrails, five guessed rooftop machinery or randomized glass/trees/roads have been restored. Main scene contains the v76 LRC skylight but its glass area cannot be interpreted as surveyed bird-strike exposure.

## How to reproduce

1. Install `pip install -r requirements.txt` (Fiona/PROJ compatible binaries).
2. `python source/build_v82.py` to reproduce exact v82 GLB and byte-preserved GIS.
3. `python source/verify_v82.py` for independent GLB/GIS/KML QA.
4. `python source/build_cpu_viewer_v82.py` for usable source-based offline 3D preview.
5. `python source/update_webgl_viewer_v82.py` for full-resolution optional viewer.
6. `python source/test_viewers_v82.py` for CPU Chromium execution and WebGL JS syntax/source integrity.
7. `python source/render_geometry_v82.py` for genuine source-triangle before/after geometry preview.

## Unresolved evidence needs

OSM/Overpass real way vertices, bridge V52 endpoints (12), V60 east/west bank elevations, six Phase II dorm entrance levels, reliable DEM and orthophoto/camera-registered photographs remain missing. Do not infer a pedestrian connection from XY closeness or from the corrected face normals. The viewer does not certify any source mesh as walkable and must not be used for a scientific bird-strike area denominator.