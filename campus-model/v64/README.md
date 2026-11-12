# BNBU editable campus GIS / 3D | v64 | 2026-11-11

Parent: v63 complete campus model; historical source-exclusion checkpoint: BNBU_hourly_campus_v10_2026-11-10.zip. All existing campus buildings, courtyards, bridges, roads, wetlands, and shoreline meshes are inherited. This release edits the **3D mesh** directly and is NOT merely a map audit.

## Geometry changes

- Reworked the actual triangle-mesh surface elevations for four v53 campus terrain relief objects: northern ridge, eastern arts hill, phase-II western hill and western woodland slope.
- Replaced 4 inherited closed terrain meshes by 4 independently editable, still closed meshes. Other 1,377 model scene nodes are unchanged at the vertex, face, transform and vertex-color level. Complete scene remains 1,381 nodes.
- 8,362 actual mesh vertices have updated model-relative Z, over 236,032 inherited triangle faces. XY and triangle connectivity remain identical; base level and original local maxima remain unchanged. Individual model-Z edits are limited to 0.35m. Surface-adjacency discontinuity indicator reduced by 20.8%-29.2% in three large hill regions and by 29.2% in western woodland (see qa/v64_build.json for all four exact values).
- Constrained top-face smoothing: 12 rounds of weighted topological Laplacian, original base/summit/outer profile fixed, original terrain volume approximately conserved. This is a mesh facet-quality improvement from the existing proxy, **not a reconstructed DEM**. There is NO claim that new Z fits actual topography.
- No new buildings, glazing, skylights, roofs, bridge supports, roads or trees generated in this iteration. Historical v10 deleted 690 fabricated glazing bands, 6 conjectural glass balustrades and 5 roof service structures; these do not return.

## Outputs

- `model/BNBU_v64_FULL_EDITABLE.glb`: complete campus 3D model, 1,381 individually editable nodes
- `model/BNBU_v64_RELIEF_CORRECTIONS_ONLY.glb`: four revised hill mesh objects
- `model/BNBU_v64_ARCHIVED_V53_RELIEF.glb`: original hill meshes for geometry provenance/diff
- `data/BNBU_v64_EDITABLE_GIS.gpkg`: 141 layers, 4 new terrain revision polygons with provenance
- `data/BNBU_v64_ACTIVE.geojson`: 531 features
- `data/BNBU_v64_ACTIVE.kml`: 531 placemarks
- `BNBU_Campus_3D_Viewer_v64.html`: self-contained, offline, v64/v63 comparison and independent hill visibility
- `figures/`: images generated from the original and reloaded GLB triangles, plus actual Chromium runtime screenshot
- `source/`: build, verify, render, viewer creation and browser-check scripts
- `qa/`: geometry validation results, browser test, SHA-256 manifest
- `reference/`: v10 GLB, GPKG, original correction code and validation evidence

## Data and confidence

Official map: https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg . This hand-drawn 2025 campus guide is **structural context, not orthorectified aerial data**. Campus aerial/mountain context: https://www.bnbu.edu.cn/about_us/overview/introducing.htm . Model geometry was derived exclusively from inherited v63 vertices; the referenced imagery did NOT yield per-vertex coordinates or height values.

GLB: EPSG:32649 easting and northing minus (758940,2474080), with local **model-relative Z**, not surveyed heights. GIS: EPSG:4326. `is_surveyed=0`, `is_dem=0`, `is_glass=0`, `metric_birdstrike_eligible=0` for all four new terrain revision GIS records. No actual OSM way vertices, photo camera calibration, true orthomosaic or external DEM available here.

## Rebuild

Python 3.11+, scipy, trimesh, numpy, shapely, Fiona, pyproj, matplotlib and optional playwright/Chromium.

    pip install -r requirements.txt
    python source/build_v64.py
    python source/verify_v64.py
    python source/render_v64.py
    python source/make_viewer_v64.py
    python source/test_viewer_v64.py

The parent v63 GLB and GPKG/GeoJSON/KML are bundled under `input/`; rebuild does not require reconstructing older versions. The reference v10 code and files allow auditing earlier glass exclusions.

## Unresolved accurate survey gaps

Actual hill DEM, bathymetry and shore elevation, OSM way vertex geometry, ortho-calibrated building/road outlines, precise phase-I/II roof forms, floor elevations, camera poses, and measured facade/glass areas remain unverified. No v64 terrain estimates should be used for engineering earthworks, routing or quantitative bird-strike exposure.