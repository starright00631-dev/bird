# BNBU campus modeling — v66 semantic hierarchy and evidence-linked GIS

**Current live development: v66.** Build the complete campus 3D scene, GIS
reference registry and viewer with standard-library Python:

```bash
python campus/build_v66.py
python -m unittest discover -s campus -p 'test_v66.py' -v
python -m http.server 8000
# open http://localhost:8000/campus/viewer.html
```

The source baseline remains **v64**; the v65 geometry-preserving Y-up rotation
is retained. v66 creates **real GLB scene-graph changes**, organizing the 1,377
existing mesh primitives into semantic layers (terrain, water, shore, vehicle
road, pedestrian paving, inferred at-grade connection, lake boardwalk, stairs,
glass candidates, opaque buildings). GLB meshes, accessors, material data,
vertex/triangle binary chunks, and source GIS **geometry coordinates are
unchanged**. This fixes navigation and physical classification, **not the
accuracy of site-survey geometry**.

**102 previously unresolved model-to-GIS links are now restored without
inventing a component.** This comprises 32 T4 + 32 T6 + 32 T8 stair
annotations, each linked to its existing v49 reconstructed stair mesh, and
six D1–D6 `V48_PHASEII_*GROUND_COURT*` annotations linked to the existing
`V49_PHASEII_*GRADE_MATCH_GROUND_LINK*` **ground-level** mesh. Their original
centres were checked against v64 inherited world XY: three stair centre
differences below 0.001 model units and D1–D6 centre differences around
0.14–0.30 units. These are **relative model cross-checks**, not external ground
measurements. The ten water/shore render alias repairs from v65 also persist.

Output files are generated into `campus/generated/`:
- `BNBU_v66_SEMANTIC_Y_UP.glb`: complete reparented, layerable scene
- `BNBU_v66_RESOLVED_REFERENCES.geojson`: 522 inherited features with valid
  legacy references, preserving every source polygon and metadata property
- `v66_provenance.json`: exact SHA-256, category counts, sources and limitations

The viewer now lets you locate and isolate **campus phases I and II, lake,
shore, hills, carriageway, elevated lakeside boardwalk, the verified existing CC
complex, stairs, glass candidates and opaque structures**, then click each
mesh to inspect matched source and confidence metadata. The CC/CTV focus is a
**visual search target, not proof of the nearby house or driveway**.

### Crucial evidence boundary

- The 2025 [official illustrated campus map](https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg)
  supports **relationships**, not metre-level positions or elevation.
- [Official campus/forest photography](https://bnbu.edu.cn/info/1075/115659.htm)
  establishes forested hills; [university lakeside photography](https://co.bnbu.edu.cn/en/info/1131/2702.htm)
  establishes lake-bank and built-deck typologies. Their cameras are **not
  georegistered** to this model.
- [Official interactive panorama](https://www.4dmodel.com/UICcode/code/#/list)
  is a reference for visually locating future control points, **not yet
  downloaded as calibrated photogrammetry**.
- The model has **four inherited relative-relief hill meshes** but no verified
  DEM. Their approximate vertical maxima (relative model units) range from
  ~2.6 to ~9.9 and must **not** be read as actual mountain elevations.
  There are five water mesh entities; **not automatically five real lakes**.
- The CTV programme is part of the cultural creativity area, but an adjacent
  separate structure, its roof and any driveway are **not independently
  georegistered**. Calling it `校长别墅` remains **unverified**; the quarantined
  v64 hypotheses remain excluded. Do not publish a fabricated building.
- Existing `GLASS` names do **not** establish optically measured glass extent.
  Six inferred grade-matched D1–D6 connections are **not bridges**.

### Required geometric reconstruction gate

For future actual terrain, shoreline, façade and route geometry edits, include
orthorectified aerial control and image source/permitted use; for vertical
modification include DEM/ground elevation points and their datum; for CTV
building obtain at least two locatable views/roof boundary plus a vehicle-way
source. Version each modified GLB/GIS asset, compare before/after geometry
and validate area/height/shore gaps. No artificial hill amplification,
unregistered curbs, random windows or new structures are permitted.

---

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

