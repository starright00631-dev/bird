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
