# BNBU v73: independent DSM three-dimensional contours

## What changed

The v67 ALOS-derived DSM remains a separate scene, because its absolute elevations are **not** registered to the relative coordinates used by the campus meshes. The v73 contour builder adds **3,737 three-dimensional line segments** (7,474 endpoints) to a new glTF binary. These lines have a **10-meter vertical contour interval**, interpolated from a DSM with nominal ~30-meter horizontal sampling. To prevent coincident-surface z-fighting in visualization, the lines are drawn 0.5m above their interpolated heights; this is a *display offset*, not an observation.

The exact source DSM binary data and first mesh remain unmodified. Source DSM: 4,140 elevation vertices and 8,024 triangles. Campus v71 geometry, v72 visual-only rail proxies, 522 GIS records, lake shoreline, roads, bridges, and existing buildings remain unchanged.

- Input: `generated/BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb`
- Contour evidence: `generated/BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson`
- Builder: `build_terrain_contours_v73.py`
- Test: `test_terrain_contours_v73.py`
- Output: `generated/BNBU_v73_ALOS_DSM_WITH_3D_CONTOURS.glb`
- Manifest: `generated/BNBU_v73_DSM_CONTOUR_PROVENANCE.json`
- Viewer: independent DSM scene with optional contour line visibility

## Limits

ALOS-derived DSM is **not bare-earth DEM**. Source HGT archive: <https://terrain.ardupilot.org/SRTM1/N22E113.hgt.zip>. This tile is historical: its exact metadata, accuracy, and comparability to current terrain should not be overstated. The 10m contour interval does **not** provide 10m horizontal measurement resolution.

The CTV-adjacent small house and potential “校长别墅” designation are not independently registered; no house/roof geometry has been created in v73. Photographs alone do not resolve precise shoreline, lake elevation, campus roadway, glazing, or building footprint positions. The off-grade campus bridge/platform junctions in v71/v72 remain unresolved, rather than repaired with fabricated ramps.

## Reproduction

The main repository pipeline regenerates v65–v72 geometries, builds the v73 DSM contours, then bundles a complete ZIP. It tests geometry integrity and both the offline standalone HTML and localhost HTTP viewer in Chromium. Local containers with security policies that block `file://` cannot substitute for that browser check.

For the distributed ZIP, open `双击查看_校园3D.html` or run `启动查看器.bat` on Windows. Select 遥感山体参考 and toggle the 3D contour control to inspect the derived geometry.
