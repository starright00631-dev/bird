# BNBU Campus GIS / 3D v78 — main-first safe geometric reconciliation

Version date 2026-11-12. **This is an editable research scene, not surveyed BIM, orthophoto, a route map, or a measured bird-strike exposure model.** The 2025 BNBU hand-drawn map is a structural constraint, not a georeferenced image.

## What actually changed

The predecessor `main` v76.1 viewer was built on a **v71 1,379-mesh scene** with 30 source-identified building families (T/V/D/LRC), 47 inherited candidate junctions, 7 bridge systems, 12 V52 bridge endpoints and 12 Phase II radial/circular route gaps. The independent `bnbu-campus-v77-pavilion-20261112` branch built on the separate **v77 1,382-mesh GLB** (v75/v76 skylight lineage). Both have the same intended local X/Y/Z coordinate convention but **different root glTF transforms** and different mesh identifiers. `v78` does not blindly replace whole scenes or mix node labels.

- **37 existing opaque horizontal facade-storey edge meshes** retopologized from earlier v75 GLB, preserving identical parent upper planar footprints, minimum/maximum model Z, and building materials. Replaced the 37 original open main meshes. No new windows.
- **One LRC curved atrium skylight** carried from v76 3D geometry, inherited from existing rim/arch curves and not photogrammetrically measured. It is visibly labelled low-confidence and **not allowed** in bird-collision exposure-area calculations.
- **One original circular communal pavilion roof cap** inherits the v77 correction of +0.021999836 model-relative units with identical X/Y and faces. This is a local contact mismatch repair, not an actual measured floor elevation.
- **Two v77 model-inferred paving seam meshes** stay as an opt-in `DISPLAY_ONLY` sidecar, OFF by default, not counted in active GIS or main scene. Four unregistered v64 terrain-smoothing alternates are separately isolated; original v53 slope shapes retained in primary GLB. The two v71 lakefront joint face winding conventions are kept exactly from main.
- Retains the same **47 hotspot pair** identities, their floor classifications, and the 12 V52 endpoints and 12 PhaseII route gaps. New `qa/v78_junction_triangle_recheck.json` samples actual 3D triangles, local model Z, normals, and XY coverage. No road or bridge is automatically created just because XY seems near. True physical accessibility remains unverified.

The active scene contains **1,380 named mesh nodes** (1,341 original main nodes unchanged, 37 retopologized replacement nodes, one main cap corrected, one skylight added). **All 10 original BNBU_GROUP layer parents and 1,379 original mesh-to-layer relationships are explicitly reconstructed**, rather than exporting a flattened mesh-only scene. The v76.1 viewer mesh guard was updated from 1,379 to 1,380 and all legacy layer controls were retained. The active GeoJSON and KML each contain **567 features/placemarks**, excluding two unregistered roof paver seams. The GPKG retains **143 historic spatial layers** plus a nonspatial membership table recording active vs quarantined alternatives (the GeoPackage should not be mistaken as entirely accepted survey geometry).

## Coordinate and confidence

GLB model X/Y = EPSG:32649 Easting/Northing minus (758940, 2474080); Z = relative model-only units, not DEM elevation. GIS GeoJSON/KML/GPKG are EPSG:4326. The glTF `world` root rotation restored to match main's Y-up render (`[-0.70710678,0,0,0.70710678]`), so local raw geometry XY/Z and browser up direction are not silently mismatched.

Source constraints: BNBU 2025 official hand-drawn illustration <https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg>; building descriptions from Ronald Lu & Partners architecture context; main v76.1 source/photo component atlases; inherited v75/v76/v77 3D meshes; original v10 archived source in `reference/`. None of these substitutes for independent UAV orthophoto, camera pose, building-level photogrammetry, DEM, measured bathymetry, or OSM way IDs.

No 690 removed spurious glazing belts, 6 speculative glass railings, 5 guessed roof equipment rooms, random windows, trees, inferred routes, or new modelled water boundaries are reintroduced.

## Open locally

Fastest: open `viewer/BNBU_Campus_3D_Offline_v78.html` in a modern Chromium/Firefox browser. Contains the new model, original main photo/road/bridge overlays and sidecar GLB. No external URLs required.

Alternative: from the package root run `python viewer/serve.py` then open the local viewer URL documented by its output. In the source-backed interface the GLB and dataset paths are under `viewer/generated/`. Offline HTML can take longer to load because it embeds the entire binary model and legacy atlas.

Run reconstruction and QA (Python 3.11+):

```bash
python -m pip install -r requirements.txt
python build_v78.py
python make_v78_viewer.py
python verify_v78.py
python check_junction_triangles_v78.py
python check_viewer_static_v78.py
python render_v78.py
```

The full parent model assets and their SHA-256 provenance are included in `input/`. The archival v10 is in `reference/`, only for provenance. The strict main and branch GLB comparison is in `qa/v78_geometry_compatibility.json`.

## Testing / limitations

GLB read-back, 37 mesh watertight/positive volume, 1,341 unchanged parent meshes, preservation of 10 original layer group parents, corrected mesh-count guard, roof XY, preservation of 2 legacy joints, glTF root rotation, GeoPackage/GeoJSON/KML counts, 47 source triangle pairs, 12 bridge ends, 12 dorm-network gap classes, JavaScript `node --check`, embedded JS syntax, 16 web asset paths and model SHA consistency passed. 47/47 junction source pairs project onto corresponding triangles and 12/12 bridge endpoints do; those are **geometry sampling checks, NOT photograph-validated pedestrian entrances or bridges**.

**Full 3D browser runtime was not reverified in this environment**: Chromium blocks both localhost and file navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. Earlier main v76.1 browser tests passed in a different environment, but cannot be reinterpreted as an actual v78 render. GitHub Pages is **not confirmed live**, Settings -> Pages -> GitHub Actions activation remains a repository-owner task.

Remaining measurement gaps: image camera poses, OSM/Overpass verified node IDs and way vertices, actual entrance thresholds, real T1–T8/LRC/V15–V29/D1–D6 facade glass position and size, all 12 elevated bridge door transitions, lake-bank elevations, mountain DEM, CTV nearby house naming, roof skylight radius/curvature. No quantified bird-strike exposure claims can be made.