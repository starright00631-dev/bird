# BNBU campus GIS / 3D geometry v77 — Phase-II circular pavilion

**Status:** editable **research proxy**, not a survey or a photogrammetrically registered BIM. Directly inherits the entire v76 model and retains the original v10 checkpoint. This is an actual GLB geometry edit (one existing mesh repositioned and two new independent opaque 3D meshes), not a desktop floorplan or audit replacing a model.

## Applied geometry changes

1. Existing Phase-II central circular roof cap (`V24_P2_CIRCULAR_COMMONS_09_LOW_CENTRAL_ROOF_CIRCLE`): shift only relative model Z **+0.0219999** units, removing most of its earlier **-0.028** intersection with the existing v58 square rooftop field. It now interpenetrates the paver plane by only **0.006** model units to prevent a tiny floating gap. Cap XY, radius, triangulation, vertex colors, and shape are retained. This small model-topology/physical-contact correction is **not** a measured elevation.
2. Add two independently editable watertight shallow 3D paving-seam meshes along inherited roof X/Y axes, clipped to the existing **16.36 × 16.36 model-unit** square roof field and cut out around the existing central roof cap. There are four nominal seam axes in each direction. The school photo confirms the **type of tiled roof field**, NOT the number, interval or true compass bearing of the joints. Therefore seam count, 0.084 model-unit line width and Z=7.364..7.374 are flagged **LOW / unregistered typology**. They are decorative opaque markings and do not represent a new glass area, windows, road or elevated bridge.

The official university photo (published 2025-06-26): <https://www.uic.edu.cn/en/info/1076/12578.htm>. 2025 official hand-drawn structural diagram: <https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg>. These images are **not** orthorectified for drawing metric X/Y. Original mesh locations were inherited from v76 GLB.

**DO NOT reintroduce** 690 removed fake glass stripes, six unsourced glass barriers, five roof service housings, guessed window modules, or random trees.

## Independent checks performed

- Complete GLB **1,382 nodes** after **1,380 v76 nodes**. **1,379 existing nodes** retained with equal vertices, faces, transforms and colors. One pre-existing roof cap's Z shifted, two new geometry objects were added, **320 triangles** in the two seam objects.
- Both new opaque 3D meshes are watertight, winding-consistent and positive-volume. Original cap retains exact XY/triangulation, and relative elevation shift is uniform. Cap lower surface overlaps parent square paving Z by **0.006 model units** after adjustment.
- Newly added GLB seam XY polygons match its GIS counterpart within worst-case **0.001998 model m²** (differences due to float32 GLB serialization), while GPKG layer and GeoJSON agree within 1e-5 model area.
- **143 GPKG layers**, **569 GeoJSON and KML features/placemarks**; an appended, clearly flagged `v77_p2_roof_disk_contact_and_paver_seams_unsurveyed` GPKG layer contains two new seam entities and one existing-cap correction. Historical GIS features are not silently overwritten; the new layer supersedes earlier conflicting cap Z for this named mesh.
- Headless Chromium parsed all 1,382 meshes in the fully offline standalone HTML viewer, tested the 2-mesh display toggle and produced an actual runtime screenshot. The renderer fell back to a software/decimated view with inherited rendering artifacts; **this does not constitute photo alignment**.

## Deliverables

`model/BNBU_v77_FULL_EDITABLE.glb` complete editable geometry; `model/BNBU_v77_PHASEII_ROOF_EDIT_ONLY.glb` the 3 edited/added pieces; `model/BNBU_v77_ARCHIVED_ORIGINAL_CENTRAL_ROOF_CAP.glb` original cap retained; `data/BNBU_v77_EDITABLE_GIS.gpkg`, `data/BNBU_v77_ACTIVE.geojson`, `data/BNBU_v77_ACTIVE.kml`; standalone HTML `BNBU_Campus_3D_Viewer_v77.html`; actual GLB before/after and viewer images in `figures/`; verified source, QA and SHA256 list in `source/` and `qa/`.

Rebuild (Python 3.11+, packages in `requirements.txt`):

```bash
python source/build_v77.py
python source/verify_v77.py
python source/render_v77.py
python source/make_viewer_v77.py
python source/test_viewer_v77.py
```

The `input/` folder supplies exact version-76 artifacts, while the `reference/` folder retains the full `BNBU_hourly_campus_v10_2026-11-10.zip` checkpoint and QA without rebuilding from v10.

## Coordinates / limits

The GLB uses **EPSG:32649 with model origin subtraction (758940,2474080)** from projected X/Y; GIS exports use **EPSG:4326**. Model Z is only relative, not a geodetic datum or DEM elevation. Presence of the round pavilion and paving typology is photo-supported; **XY position, tile count/spacing and elevations are not surveyed**. No newly verified OSM/Overpass way vertices, DEM or calibrated overlap photos were obtained. A newer Phase-II academic teaching cluster appears in official reporting but lacks reliable site footprints in the inherited model; no guessed building volumes were inserted. This model must not provide quantitatively measured glass area or birdstrike risk denominators.