# BNBU Zhuhai Campus Editable GIS / 3D — v87

**Checkpoint:** 2026-11-12 local / 2026-11-13 UTC  
**Direct parent:** v86 package; physical parent remains `model/BNBU_v84_FULL_EDITABLE.glb`  
**Physical master SHA256:** `242ade4c7cf25a4437e674b271ea451f9367449c23530ca95679b33749989848`

## What changed in v87

v87 captures the **full OSM way geometry** for T1, T2 and T3 and compares those real community-mapped polygons with plan outlines derived from the inherited 3D facade/sidewall source triangles. It then builds a reversible, independently aligned per-building ICP candidate for inspection.

This is a real registration-data improvement over v86's three `out center` bounding-box centres. It does **not** establish a surveyed campus coordinate transform and does not alter the scientific master.

### Live OSM source capture

- Source: OpenStreetMap Overpass API, `out meta geom`.
- Endpoint used: `https://overpass-api.de/api/interpreter`.
- Query: `[out:json][timeout:90]; way(id:664082910,664082908,664082909); out meta geom;`
- Retrieved: `2026-11-13T00:59:04Z`.
- Raw response element SHA256: `11997f1ae0ede0d3cd6cadf570ef5038d41ab4d72e39b6e16c3a27c01e02bf87`.
- T1 way `664082910`, version 8, 19 nodes; T2 way `664082908`, version 9, 20 nodes; T3 way `664082909`, version 8, 17 nodes.
- All three closed-ring node-reference sequences exactly match the v86 snapshot; all three building names/tags match.
- OSM is licensed under ODbL. Attribute the data to OpenStreetMap contributors.

The complete raw Overpass response and capture status are committed on the development branch at `campus/versions/v87/qa/`. The ZIP also includes a joined, compact geometry snapshot and the original v86 node-reference snapshot so the analysis can be reproduced offline.

## Source-mesh footprint extraction

For each of `V40_MAIN_T1_FACADE_AND_SIDEWALLS`, `V40_MAIN_T2_FACADE_AND_SIDEWALLS` and `V40_MAIN_T3_FACADE_AND_SIDEWALLS`:

1. Re-import the original v84 GLB without processing and apply the exact scene-node transform.
2. Project each original source triangle to XY; extract its non-degenerate projected edge segment.
3. Node and polygonize the inherited triangle-derived linework.
4. Select the largest valid closed polygon as the **dominant projected facade-shell plan outline**.
5. Compare this source-derived outline with the full OSM polygon in EPSG:32649.

This is not a ground survey footprint: the V40 meshes are facade/sidewall geometry, and the OSM polygons are community-mapped. Both are explicitly marked unsurveyed.

## Registration findings

The v86 global translation was fitted from OSM bounding-box centres:

- v86: ΔX = −0.182380 m, ΔY = −4.070576 m.

The full polygons expose why that single translation is not a reliable building-shape registration:

- Mean OSM-polygon-centroid minus model-shell-centroid vector: **(−4.1527, −4.1346) m**.
- Pairwise relative-vector errors: T1–T2 **6.331 m**, T1–T3 **4.942 m**, T2–T3 **2.205 m**.
- The v86 bbox translation barely improves footprint IoU over the unshifted source shell.

A trimmed boundary ICP was therefore run **independently for each building**. It estimates a rigid 2D rotation and translation from the sampled source-shell boundary to the OSM polygon boundary. The three transforms are not a common campus transform.

| Building | ICP rotation | Baseline IoU | v86 global-shift IoU | v87 individual ICP IoU | Mean boundary residual | P95 residual |
|---|---:|---:|---:|---:|---:|---:|
| T1 | −73.735° | 0.293 | 0.296 | 0.499 | 5.096 m | 18.896 m |
| T2 | +110.143° | 0.306 | 0.303 | 0.705 | 3.124 m | 12.792 m |
| T3 | +110.280° | 0.236 | 0.238 | 0.710 | 2.940 m | 12.964 m |

The large, building-specific rotations and residuals are evidence **against** promoting a common transformation. T1 remains a poor shape fit; T2/T3 improve substantially but still have multi-metre tail residuals. The ICP candidate is for visual diagnosis only.

## Editable 3D outputs

- `model/BNBU_v87_T1_T3_PER_BUILDING_OSM_ICP_DISPLAY_ONLY.glb`: 171 T1/T2/T3 components, 10,196 original source triangles. Each building is transformed independently. V52_04 and V52_05 are excluded.
- `model/BNBU_v87_T1_T3_BASELINE_V86_V87_ICP_COMPARISON.glb`: 517 nodes / 31,596 triangles: baseline 173-component set, v86 global-translation set, and v87 171-component per-building ICP set.
- Mesh vertex arrays, face indices and source colors are preserved; only node transforms differ.
- `viewer/BNBU_v87_T1_T3_OSM_Footprint_ICP_Comparison.html`: self-contained CPU 3D viewer with baseline/v86/v87/overlay modes, T1/T2/T3/V52 filters, OSM and model outline toggles, plan view, orbit and zoom.

The V52 bridge slabs remain at baseline in v87 because their real landing assignments are not verified. A per-building alignment would otherwise silently break the campus bridge network.

## GIS QA-only outputs

`data/BNBU_v87_OSM_FOOTPRINT_QA_ONLY.gpkg` (5 layers / 15 features) and `data/BNBU_v87_OSM_FOOTPRINT_QA_ONLY.geojson` contain:

- OSM way footprints;
- baseline projected facade-shell outlines;
- v86 global-shift outlines;
- v87 independently ICP-aligned outlines;
- baseline centroid residual vectors.

These files are separate from the physical GIS master. No new measured glass, route, shoreline, building, or bird-strike exposure area is added.

## Viewer validation

- v84 full-campus **CPU fallback** was run in Chromium: 1,346 source meshes / 691,593 triangles; LRC, dormitory, road and terrain focus switching all worked; zoom/pitch/reset worked; zero page errors.
- v87 comparison viewer was run in Chromium: 173 components / 10,700 source triangles; baseline, v86, v87 and overlay modes worked; T1/T2/T3/V52_04/V52_05 focus switching worked; plan/3D controls worked; zero page errors.
- Local execution policy blocks direct `file://` and localhost navigation. A GitHub Actions workflow separately tests actual file and localhost HTTP navigation on an Ubuntu runner; its result is recorded in `qa/v87_browser_validation.json` when completed.
- The full v84 WebGL viewer has not been newly certified in this environment. Use `viewer/BNBU_Campus_3D_CPU_v84.html` as the tested full-scene offline viewer.

## Parent integrity

- Physical GLB remains 1,346 meshes / 691,593 triangles.
- Physical v84 GPKG remains 146 layers.
- Active GeoJSON/KML remain 534 features each.
- No active GIS or physical master file is edited.
- No speculative windows, roof plant rooms, rails, roads, bridge landings or shoreline geometry is added.
- No new scientific geometry and no bird-strike exposure area is eligible from v87.

## Rebuild / verify

Python 3.11+:

```sh
python -m pip install -r requirements.txt
python src/analyze_osm_footprints_v87.py
python src/build_v87_viewer.py
python src/test_v87_browser.py --set-content-only
python src/test_v84_cpu_viewer.py
python -m unittest discover -s tests -v
python src/verify_v87.py
```

The network capture workflow is `.github/workflows/bnbu-v87-osm-geometry.yml`. It commits the raw full-way response to the development branch. The real-browser workflow is `.github/workflows/bnbu-v87-browser.yml`. For a fully offline rebuild, use the included `qa/v87_osm_full_geometry_joined.json` and `qa/v87_osm_geometry_compact.json`; the network capture step is not required.

## Decision

v87 is a **registration diagnosis checkpoint**, not a new scientific master. It proves that the v86 bounding-box-centre translation does not adequately align the actual T1–T3 plan outlines. The next promotion gate is independent multi-view photo calibration / surveyed control points and verified bridge landing locations. Until then, keep v87 candidates display-only and keep all V52 endpoints non-routable.