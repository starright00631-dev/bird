# BNBU Zhuhai editable GIS/3D v83 · 2026-11-12

This release follows Library v82 (and prior v81/v80), **not** the old v10 reconstruction. The original v10 GLB/GPKG/source/QA remains archived under `reference/`. Parent v82 itself reconciles main v76.1 and the LRC v76 skylight branch; **the 34,816-face v76 LRC skylight remains intact**. GitHub PR #10 is not merged and `main` has not been overwritten.

## No qualified new campus geometry (intentional)

There is no independent orthorectified image, surveyed surface or identifiable genuine OSM way vertex set in this run. The **physical main GLB** remains **byte-for-byte identical to v82**: 1,347 meshes and 691,907 triangles, SHA256 `2b694603f2d592499196f40bf74b569de55ccf42d2c63217b82bf76dce717b36`. The main 146-layer GPKG and the active 534-feature GeoJSON/KML are also byte-identical (apart from v83 filenames). This is preferable to inventing routes, glazing or terrain. All 690 earlier speculative window belts, 6 unsupported balustrades, 5 guessed roof rooms, 6 V49 routes and 27 v60/V54 inferred pieces remain absent from the active scene.

## Measurable NEW deliverable: twelve V52 bridge-end source-face constraints

We derive **two terminal samples each from the six original V52 level-2 bridge-deck meshes** (00–05), using the long PCA axis of the upper surface; snap each sample onto an **actual original upward-facing source triangle**. At each end search real original triangles from other meshes, requiring positive Z normal and a constrained XYZ search; rank by closest-point 3D separation. Save original source mesh name, triangle index, local XYZ, normal, model Z, nearest candidate, 3D separation, and vertical difference. Validate independently against the reimported parent GLB.

| Source bridge | Model-suggested adjacent buildings/surfaces | Closest source-model 3D gap |
|---|---|---|
| 00 | T4 ↔ T5 (both `V40_MAIN_*_ROOF_FACING`) | 0.100 / 0.100 model m |
| 01 | T5 ↔ T6 (both `*_ROOF_FACING`) | 0.100 / 0.100 |
| 02 | T6 ↔ T7 (both `*_ROOF_FACING`) | 0.100 / 0.100 |
| 03 | T7 ↔ T8 (both `*_ROOF_FACING`) | 0.094 / 0.108 |
| 04 | T1 gallery ↔ T2 `ROOF_FACING` | 0.090 / 0.150 |
| 05 | T2 `PILOTIS_OPAQUE_SOFFIT` ↔ T3 gallery | 0.150 / 0.040 |

**Important:** these small distances are *internal to a proxy geometry created from inherited topology*. Some matching faces are roof-facing or soffits, not verified pedestrian landings. Their numerical proximity cannot demonstrate actual bridges, accessibility, clearance, glass area or route continuity. All 12 endpoints remain `verified=0, surveyed=0, routable=0` even if their original proxy faces meet in 3D.

Geographic context: [official hand-drawn 2025 campus map](https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg) confirms the T4–T8 academic sequence but is **not** orthorectified. [RLP architectural descriptions](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/) provide the structural type context, not independent bridge dimensions. A [crowdsourced 2026 POI directory](https://u-map.haotian22.top/poi-directory.html) gives named centroids but is not independent surveyed building footprint validation; existing proxies may already derive from POI anchors. An attempted live Overpass/OSM API request could not be retrieved in this runtime; no fabricated OSM ways were added.

## Actual new editable 3D and GIS QA assets

- `model/BNBU_v83_V52_SOURCE_FACE_CLIPS_ONLY.glb`: **24 distinct unmodified source face clips** (12 true bridge faces + 12 nearest candidate faces), preserving exact source XYZ and source triangle indices. Diagnostic-only, not a new bridge.
- `qa/BNBU_v83_V52_BRIDGE_ENDPOINT_DIAGNOSTIC.gpkg`: a **separate** EPSG:4326 GPKG layer with 12 diagnostic points, provenance and non-routability flags. **Never union into scientific active physical features.**
- `qa/v83_v52_probe.json`: full 12 per-triangle 3D normal/height/proximity records.
- `viewer/BNBU_v83_V52_Actual_Triangle_3D_Inspector.html`: no-network, no-WebGL interactive 3D inspector, two types of true source triangle, 12 endpoint selection, orbit and toggles, tested in Chromium via `set_content`.
- `viewer/BNBU_Campus_3D_CPU_v83.html`: 1,347 original nodes from unchanged main GLB in CPU 3D preview, with corrected semantic classification: tags such as `V26` (historical revision) are not automatically interpreted as `V26` dormitory; source triangle sampling is explicitly display-only. Tested with category and focus changes in Chromium.
- `viewer/BNBU_Campus_3D_Offline_v83.html`: exact embedded full-resolution v82 geometry (same SHA) and updated CPU fallback. JavaScript static-checked; **full WebGL navigation not verified** under this environment.
- `model/BNBU_v83_FULL_EDITABLE.glb`, `data/BNBU_v83_EDITABLE_GIS.gpkg`, `data/BNBU_v83_ACTIVE.geojson`, `data/BNBU_v83_ACTIVE.kml` and two display-only GIS archives are exact copies of v82's trusted assets.

## Coordinate and scientific limits

GLB local XY = EPSG:32649 easting/northing **minus** `(758940, 2474080)`; GIS = EPSG:4326; all Z are **relative, not surveyed vertical datums**. QA point longitude/latitude is only the mathematical transform of inherited local XY, not independent position validation. The bridge-landing uncertainty applies to V60 two banks, V52 all 12 ends and phase-II D1–D6 entry/ring roads. Source image/camera registration, DEM, true entrance surface, OSM way geometry and verifiable glazing dimensions are still missing. Do not use these proxies as quantitative birdstrike exposure denominators.

## Reproduce / verify

```sh
pip install -r requirements.txt
python source/build_v83.py
python source/build_cpu_viewer_v83.py
python source/build_bridge_inspector_v83.py
python source/update_full_viewer_v83.py
python source/verify_v83.py
python source/test_viewers_v83.py
```

`input/` includes all v82 physical source artifacts. `reference/` includes the v82 viewer-builder source, v82 offline WebGL HTML, plus v10 checkpoint ZIP. The final ZIP also carries the completed QA, screenshots, source code and SHA256 manifest. Local Chromium is optional for viewers; `playwright` installed for browser QA only. Tests do not assert native `file://` or external GitHub Pages availability.