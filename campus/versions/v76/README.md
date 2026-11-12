# BNBU editable GIS/3D campus · v76

**New actual geometry**: one contiguous curved LRC circular rooftop skylight glass infill, closed 36 mm model-thickness shell, not individual panes. This fills the roof opening that already existed in v75; its plan footprint is taken from the inner ring of `LRC_SKYLIGHT_RIM` (256 vertices), and the curvature is interpolated between two **existing model** arch ribs. Parent LRC roof mesh is not overwritten. The 2025 hand-drawn campus illustration is used for structural organization only, not for surveyed coordinates.

The skylight is present in the v10 archived school-official roof-photo source feature and described architecturally as a roof-lit atrium. Neither the perimeter, glass height, pane configuration nor true glass material has been measured. The original v10 skylight circle was a *proxy*. The new surface is only a shape hypothesis constrained to the inherited v75 geometry, not an orthorectified reconstruction. **Do not use the modeled 401 square meters of glass shell area as a real glass exposure or bird-strike risk denominator**. There are no new facade windows, patterned pane grids, balustrades, roof service rooms, or randomized trees. Those earlier 690/6/5 unsupported elements remain excluded.

## What changed

- v75 main GLB 1,379 independent nodes preserved byte-for-byte *at their vertex, triangle, transform and vertex color level*.
- Added `V76_LRC_EXISTING_SKYLIGHT_CONTINUOUS_GLASS_INFILL_RIB_DERIVED_UNSURVEYED` as a separate editable, watertight transparent-PBR material entity: 17,410 vertices, 34,816 triangles.
- Circular plan footprint: **315.382 model m²** inherited from the model opening. Curved glass proxy half-area approximately **401.012 model m²**, not measured.
- Output full GLB: 1,380 independent meshes. The delta-only GLB provides just the skylight.
- GIS: 142 GPKG layers, 566 GeoJSON features and 566 KML placemarks (one new one each); new layer explicitly says `nonmetric`.
- Complete off-line viewer has v75 comparison, dedicated skylight show/hide and LRC focus, tested in headless Chromium.
- Original v75 source geometry and v10 archived reference/validation are packaged as rebuild inputs and provenance.

## Coordinate system and trust

The GLB uses local XY = EPSG:32649 (UTM49N) **minus (758940, 2474080)**. Vertical Z is local model-relative, **not** an observed height datum. GIS outputs use EPSG:4326. The new skylight is `is_surveyed=0`, `metric_birdstrike_eligible=0`, `is_routable=0`, and `is_glass=1` only for *material type*, not a claim of surveyed glass extent.

Sources: [Official 2025 hand-drawn campus plan](https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg), [archived v10 official rooftop photo reference](https://admission.uic.edu.cn/info/1717/1202.htm) (original reference currently may be unavailable), [UIC LRC architectural skylight/atrium description](https://www.stefanogambacciani.com/copia-di-the-next-future-hotel-1), and existing v75 actual GLB roof/arch geometry. No Overpass real way coordinates, new orthophotos, original image camera poses, or DEM were acquired in this version.

## Files and rebuilding

`model/BNBU_v76_FULL_EDITABLE.glb` is the full scene. `model/BNBU_v76_SKYLIGHT_GLASS_ONLY.glb` isolates the new geometry. `data/BNBU_v76_EDITABLE_GIS.gpkg`, `data/BNBU_v76_ACTIVE.geojson`, `data/BNBU_v76_ACTIVE.kml` are editable GIS. `BNBU_Campus_3D_Viewer_v76.html` is a single-file offline viewer (the file embeds both v75 and v76 GLBs). `figures/` contains actual-mesh before/after and a browser screenshot. `qa/` includes numerical validation and a hash manifest.

```bash
pip install -r requirements.txt
python source/build_v76.py
python source/verify_v76.py
python source/render_v76.py
python source/make_viewer_v76.py
python source/test_viewer_v76.py
```

## Remaining work

Image registration and actual skylight material/size confirmation, road-network real OSM way nodes, verified phase-I/phase-II footprints, hill DEM with vertical controls, lake-edge heights, and per-glass-face camera alignment. The version does not claim to have solved these. The next geometrical improvements should use registered building photos, precise road way vertices and real terrain before adding more surface detail.