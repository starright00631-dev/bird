# BNBU campus v79: layer-aware 3D junction proof, not speculative construction

Date: 2026-11-12. This is a geometry-extraction and false-connectivity-error correction based on **the actual v78 reconciled main GLB**. The official 2025 BNBU hand-drawn image constrains conceptual placement but is NOT an orthophoto or source of surveyed XY/Z. Full parent v78 (including v10 archive, code, assets and QA) is bundled in `input/BNBU_campus_geometry_v78_2026-11-12.zip` and is extracted by the build script.

## Substantive result

v78 sampled the **highest intersected triangle** at every XY coordinate. For all six Phase II dorms D1-D6, this selected the **model Z=32 rooftop**, while the given connection anchor was model Z=0 and the nearby radial pavement was Z=0.044. The resulting 32 m vertical component and ~37-38 m purported 3D discontinuity were **not a valid entrance measurement**. v79 enumerates all intersecting triangle heights and reselects the anchor-concordant layer. At these same points the model Z=0 dorm faces have normal (0,0,-1): they are **downward-facing base faces, not accessible ground doorways**. The road surfaces are upward-facing at model Z=0.044. Therefore neither the rooftop nor the floor underside qualifies as a verified walking connection.

Independent cross-check extracts bottom edges of source vertical facade triangles (56-64 source edges per dorm) and finds the nearest existing wall-base point to the radial-road endpoint. The source-model plan separations for D1-D6 are, respectively, 20.619, 19.744, 19.453, 20.329, 18.584 and 20.033 model meters. These are NOT surveyed distances, measured accessible thresholds or authorization to add connectors.

This same layer-aware barycentric procedure checks **47 historic hotspots + six V52 bridge systems (12 endpoints) + 12 Phase II dorm radial/ring gap pairs = 65 cases with 130 endpoint samples**. Each sample tracks source triangle index, all intersected height layers, exact model-relative height, original normal, confidence and no-route flag. Rather than inventing connecting roads, **130 individual 3D meshes** were extracted from the *actual original source triangles*, each with an ID and face list, into `model/BNBU_v79_REAL_SOURCE_FACE_CLIPS_ONLY.glb`. All 130 extracted mesh vertex arrays were independently imported and compared **bitwise** to their original parent triangle vertex arrays (max error 0). These are **display-only diagnostic geometry, NOT accepted new campus structures**.

The primary GLB is intentionally **unchanged**, SHA256 `6a89879e5b64e7d56581cee54cbc7e1b62b60eb1f48cb57b56bdbbb7dbbb23b4`, 1380 mesh nodes. All 143 GeoPackage spatial layers, 567 GeoJSON features and 567 KML placemarks are preserved; 130 non-spatial QA rows are added to the copied GPKG. No fake windows, glazing rails, roof equipment, trees, water boundaries, route links or measured glass exposure were added.

## Portable viewers and QA

- `viewer/BNBU_v79_Interactive_3D_Connector_Inspector.html`: small self-contained **interactive 3D Canvas viewer** (source triangle faces shown in 3D via orbit/zoom, not just a flat map). Works without network, libraries or WebGL. It was loaded in headless Chromium and nine case switches, orbit and zoom were tested. Screenshot: `qa/BNBU_v79_3D_Viewer_Chromium.png`. Its dashed gap segment is a diagnostic *annotation*, never a physical connector.
- `viewer/BNBU_Campus_3D_Full_v79_Inherited_v78.html`: unchanged full-campus v78 offline WebGL viewer. Full WebGL runtime is **not** newly verified here because the current Chromium environment returns null for WebGL1 and WebGL2. Do not confuse the validated diagnostic viewer with a passed full-campus browser test.
- `model/BNBU_v79_MAIN_INHERITED_UNMODIFIED.glb`: full 1380-mesh campus scene, exactly identical to v78.
- `data/BNBU_v79_EDITABLE_GIS.gpkg`: source 143 historic spatial layers, plus nonspatial `bnbu_v79_surface_layer_checks` table. Historical layers contain unverified alternatives, not survey truth.
- `data/BNBU_v79_ACTIVE.geojson` and `data/BNBU_v79_ACTIVE.kml`: unchanged accepted-as-active research features (567 each).
- `qa/v79_layer_aware_junctions.json`, `qa/v79_dorm_facade_ground_edges.json` and `qa/v79_face_clip_provenance.json`: detailed source-derived numeric evidence.

## Reproduce

Unzip this archive. Python 3.11+ with NumPy, Trimesh, Shapely, Fiona, and Playwright (Chromium only for browser test):

```
python source/build_v79.py
python source/make_v79_viewer.py
python source/verify_v79.py
python source/test_viewer_v79.py
```

`build_v79.py` unpacks exact v78 source once, retaining the nested v10 archive. No remote dataset or credentials are needed. This archival reproducibility is independent of GitHub Pages. GitHub Pages remains unconfirmed: repository owner must choose **Settings -> Pages -> GitHub Actions**.

## What remains unproven

No image-to-geometry calibrated camera poses, independent building registration, audited OSM way/node IDs, geodetic DEM, surveyed vertical datum, dorm threshold locations, confirmed bridge landings, lake-bank survey, CTV cottage identification, or real facade glass bounds. Future main-GLB edits require additional evidence and cross-view residual checks; no source-independent geometry added to this primary model in v79.