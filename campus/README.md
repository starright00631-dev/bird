# BNBU campus model — v64 evidence-aware import

This directory contains the **actual losslessly compressed v64 active campus GLB and editable GIS sources** recovered from the prior BNBU modeling project, **not** a newly invented campus. Unpack: `python campus/unpack_assets.py`; verify: `python campus/validate_scene.py`.

- `assets/BNBU_v64_ACTIVE.glb.xz` — complete active model, not surveyed.
- `assets/BNBU_v64_EDITABLE_GIS.gpkg.xz` — editable GIS database (EPSG:4326).
- `assets/BNBU_v64_ACTIVE.geojson.xz` and `assets/BNBU_v64_ACTIVE.kml.xz` — active geographic layers.
- `assets/BNBU_v64_CTV_EXCLUDED.geojson.xz` and `assets/BNBU_v64_CTV_UNVERIFIED_GEOMETRY_DO_NOT_USE_AS_SURVEY.glb.xz` — quarantined hypotheses; **not part of the active scene**.
- `viewer.html` — local interactive GLB viewer after unpacking; serve project root with `python -m http.server 8000` and browse `http://localhost:8000/campus/viewer.html`.

**v64 inspection:** 522 GeoJSON features; five legacy water meshes and five shore meshes (not proof of five distinct lakes); four relative hills (not DEM); two labeled vehicle-road entities and 54 footpaths. These are inherited model entities, **not** individually surveyed geometry. Full photo-to-camera registration, geodetic elevation, actual carriageway edges, verified CTV outbuilding identity/roof and measured glass surfaces remain outstanding. The supposed '校长别墅' name is not confirmed.

The inherited GLB local X/Y use EPSG:32649 with easting/northing offset (758940, 2474080). Z is model-relative. No new terrain vertex/shoreline/CTV structure was hallucinated in this import.

Independent official existence evidence:
- https://www.bnbu.edu.cn/info/1077/4186.htm (school account confirms a small campus lake and nearby mountain)
- https://bnbu.edu.cn/info/1075/14515.htm (lakefront and Phoenix-mountain campus photos)
- https://www.bnbu.edu.cn/info/1078/112309.htm (lake-region campus photograph)

## Geometry refinement gate
For **each** change, commit together: source evidence + its precise reference and camera/geospatial control points, changed 3D meshes and GIS layers, before/after render, residual or uncertainty checks, and updated tests. Separate road surface, elevated deck, pedestrian bridge, shoreline, and hill volumes by actual geometry. Only promote excluded CTV geometry after verification of its location, identity, roof, and adjacent carriageway. This import preserves inherited inaccuracies openly; it does not claim reconstruction has been validated.

## v65 coordinate/display integrity patch (not terrain reconstruction)

The inherited v64 meshes use **X=easting, Y=northing, Z=relative altitude**, while glTF/Three.js expects **Y-up**. The former viewer displayed this scene without the required coordinate conversion. Run:

```bash
python campus/build_v65.py
python -m unittest discover -s campus -p 'test_v65.py' -v
python -m http.server 8000
```

Then open `http://localhost:8000/campus/viewer.html`. The code generates
`campus/generated/BNBU_v65_DISPLAY_Y_UP.glb` (GLB Y-up root transform),
`BNBU_v65_RENDER_REFERENCES.geojson` (explicit render-node aliases),
and `v65_integrity_manifest.json`. The compressed **v64 source is immutable**.
A GitHub Actions artifact on each update includes the generated v65 scene.

Ten old lake/shore GIS display-node names are reconciled against inherited
`LAKE_00`–`LAKE_04` and `SHORE_00`–`SHORE_04` meshes. **102 unmatched
legacy node references remain unresolved**, rather than being fabricated.
No lake margins, mountain gradients, missing paths, CTV villa geometry, or
glass panels have been invented. Root-axis repair is necessary for correct
viewing but does **not** make the model topographically accurate.

### Remaining evidence-gated reconstruction
- Orthorectified aerial image + ground control to compare vehicle road and
  pedestrian paving surfaces; classify roads/decks/bridges by level and support.
- DEM or surveyed control points to revise ridge slope, vertical relief,
  shore profile and water surface in the **same** vertical reference frame.
- Registered CTV oblique imagery / overhead roof geometry to verify whether a
  small building exists and whether a vehicle carriageway borders it.
  The name “校长别墅” is **unverified**; keep its v64 source isolated.
- Building-specific façade photos and camera registration before assigning
  glazing, façade finish or collision-relevant transparent area.

