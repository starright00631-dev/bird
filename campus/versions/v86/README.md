# BNBU Zhuhai Campus Editable GIS/3D — v86 Registration Candidate

**Date:** 2026-11-12  
**Direct parent:** v85 package, whose physical master is the v84 GLB  
**Master GLB SHA256:** `242ade4c7cf25a4437e674b271ea451f9367449c23530ca95679b33749989848`

## What changed in v86

This is a reversible **display-only registration candidate**, not a replacement master. It tests the recorded horizontal correction against the exact T1/T2/T3 source meshes and the two associated V52 bridge slabs. It does not change the physical master GLB, physical GPKG, ACTIVE GeoJSON/KML, or any mesh shape.

- Source selection: all 171 original mesh nodes with a standalone `T1`, `T2`, or `T3` name token, plus `V52_LEVEL2_PEDESTRIAN_CONNECTION_04_CLOSED_SLAB_EXISTING_TOPOGRAPHY` and `_05_...`.
- Exact scope: **173 mesh components / 10,700 source triangles**.
- Candidate translation in EPSG:32649 XY: **ΔX = −0.1823796654 m, ΔY = −4.0705763153 m, ΔZ = 0 m**.
- Candidate-only GLB contains the 173 translated meshes. A second comparison GLB contains both unchanged baseline and translated candidate collections (346 nodes / 21,400 triangles), so the two states can be toggled in Blender or another GLB editor.
- A standalone CPU 3D HTML viewer provides baseline, candidate and overlay modes, component filters, orbit and zoom.
- A separate QA-only GPKG and GeoJSON contain three centre points per building, baseline/candidate residual vectors, and translation vectors. They are not appended to the physical GIS master.

## How the candidate was estimated

The OSM source is the BNBU Map Overpass POI snapshot at `https://u-map.haotian22.top/poi.json`, with `timestamp_osm_base = 2026-11-10T19:09:14Z`. Its Overpass query is `https://github.com/HaoTian22/BNBU-Map/blob/main/Overpass.txt`, which ends in `out center;`. That output gives each way's **bounding-box centre**, not full polygon geometry or a surveyed control point.

| Building | OSM way | OSM bbox centre (lat, lon) | Model bbox centre (local XY) | OSM − model displacement (m) | Residual after candidate (m) |
|---|---:|---|---|---|---:|
| T1 | 664082910 | 22.3519150, 113.5152254 | 98.257969, −132.310966 | −0.464710, −4.625114 | 0.622272 |
| T2 | 664082908 | 22.3523537, 113.5148681 | 60.369709, −85.449732 | −0.202612, −3.507782 | 0.563158 |
| T3 | 664082909 | 22.3527163, 113.5145511 | 26.714051, −45.260068 | +0.120184, −4.078833 | 0.302676 |

The translation is the unweighted mean of the three OSM-minus-model centre deltas. The resulting centre residual RMS is **0.515100 m**, with a maximum of **0.622272 m**. The baseline mean centre mismatch is about **4.081 m**.

**Important statistical qualification:** the same three OSM centres were used both to estimate the translation and to report these residuals. These are in-sample fit statistics, not independent validation. The comparison is between OSM way bbox centres and the bounding-box centres of the `V40_MAIN_T1/T2/T3_FACADE_AND_SIDEWALLS` meshes; those are not guaranteed to be identical footprint definitions. The source snapshot does not contain the full OSM way polygon coordinates. No independent polygon-boundary fit, camera calibration, photo tie points, or surveyed control points were available. Therefore this is **not photogrammetric registration** and is not approved for the physical master. The three-building identity is supported by the OSM name tags; BNBU's official site independently lists teaching facilities across T1–T8 and the official Faculty of Business and Management contact page places its office at T1-602. These public references identify the building names, but they do not provide metric control points.

## V52 bridge-end sensitivity check

The original source-face IDs and normals for V52_04 and V52_05 are retained. Four endpoint source faces were re-probed in both coordinate scenarios. Their nearest surfaces within the shifted T1–T3 group keep the same relative gaps because the bridges and those building components move together. All four remain `is_routable = false` and `is_verified_connected = false`.

The closest unshifted external model surfaces change as follows (all model-space distances, not field measurements):

| Endpoint | Nearest external model surface | Baseline | Candidate |
|---|---|---:|---:|
| 04_A | WALK_022 | 4.494 m | 6.771 m |
| 04_B | WALK_022 | 3.982 m | 3.770 m |
| 05_A | WALK_023 | 12.629 m | 10.515 m |
| 05_B | WALK_023 | 7.344 m | 4.427 m |

Within the shifted building group, the nearest source-face gaps remain 0.090 m (04_A), 0.150 m (04_B), 0.150 m (05_A), and 0.040 m (05_B), because both bridge slabs and the adjacent T1/T2/T3 meshes move together. These are mesh-to-mesh distances to existing model surfaces; the surfaces are not independently surveyed or certified walkable landings. In particular, the candidate does not prove a continuous pedestrian route. It improves some external model proximities and worsens others, which is another reason to keep it as a separate scenario.

## Integrity and validation

- Parent physical GLB remains **1,346 meshes / 691,593 triangles**.
- The v86 candidate GLB round-tripped **173/173 meshes**; all face-index arrays and local vertex arrays were preserved. Independent reimport found zero baseline vertex error and zero candidate translation error at the tested float precision.
- The baseline/candidate comparison GLB round-tripped **346 nodes / 21,400 triangles**; source vertex colors and face indices are also preserved.
- The v84 physical GPKG, ACTIVE GeoJSON and ACTIVE KML are byte-identical to the parent v84 copies. The physical GPKG remains 146 layers; ACTIVE GIS remains 534 features.
- QA-only GPKG has 3 layers: `registration_centres` (9 points), `registration_residuals` (6 lines), and `candidate_shift_vectors` (3 lines). All are marked display-only, unsurveyed and non-routable.
- Chromium set-content test passed baseline, candidate and overlay modes; overlay rendered 21,400 source triangles. All five focus filters passed; zero page errors. Node JS syntax passed. This is CPU canvas rendering, not a WebGL test and not a GitHub Pages test.

## Files

- `model/BNBU_v84_FULL_EDITABLE.glb` — unchanged physical master.
- `model/BNBU_v84_ROAD000_RETAINED_ONLY.glb` — standalone exact 416-triangle retained source road mesh.
- `model/BNBU_v86_T1_T3_V52_04_05_TRANSLATED_DISPLAY_ONLY.glb` — candidate-only layer for import beside the master.
- `model/BNBU_v86_T1_T3_V52_04_05_BASELINE_AND_CANDIDATE.glb` — baseline and candidate collections together.
- `data/BNBU_v84_EDITABLE_GIS.gpkg`, `BNBU_v84_ACTIVE.geojson`, `BNBU_v84_ACTIVE.kml` — unchanged physical GIS.
- `data/BNBU_v86_REGISTRATION_QA_ONLY.gpkg` and `.geojson` — separate centre/residual evidence layers.
- `viewer/BNBU_v86_T1_T3_OSM_Registration_Comparison.html` — self-contained CPU 3D comparison viewer.
- `viewer/BNBU_Campus_3D_Offline_v84.html` — full campus viewer inherited from v84, including CPU fallback.
- `viewer/BNBU_v85_V52_V60_Actual_SourceTriangle_3D_Inspector.html` — 14-endpoint bridge/shore inspector inherited from v85.
- `qa/` — full registration audit, 173-component manifest, V52 endpoint recheck, browser test, hashes.
- `src/` — reproducible build, browser test and delivery verifier.
- `reference/README_v85.md` — previous v85 checkpoint description.

## Source references

- [BNBU official teaching-facilities article](https://mpro.bnbu.edu.cn/info/1086/4347.htm): confirms teaching locations are distributed across T1–T8 and other campus teaching buildings; images are useful for later identity-checked photo registration, not metric control.
- [BNBU Faculty of Business and Management contact page](https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm): gives the official T1-602 Business and Management Building address.
- [BNBU 2025 official hand-drawn campus map](https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg): topology only, not survey control.
- [RLP project description](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/): design/circulation context, not measured building control.

## Reproduce

Python 3.11+:

```sh
python -m pip install -r requirements.txt
python src/build_v86_registration_candidate.py
python src/test_v86_browser.py
python src/verify_v86.py
```

## Decision

**Do not merge the candidate into the scientific master yet.** The next evidence gate is full OSM way geometry (`out geom`) or surveyed building control points, plus identity-checked multi-view photos with camera poses. Only after independent polygon/photo residuals support the same transform should any of these 173 components be considered for a physical master update. The old v10 checkpoint is not used or reconstructed.