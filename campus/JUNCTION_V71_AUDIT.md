# BNBU v71 — land / road / building / bridge connection audit

## Method: match observable structure types; measure only inherited model geometry

Photos are **perspective references**, not orthorectified camera-registered measurements. The source geometry is v69 GLB (1,377 original meshes; local EPSG:32649 offsets, model-relative Z), with v66 GeoJSON (522 original features). The code checks each polygon in the same projected CRS and reads its actual model height range. No image is used as a fictitious surveyed XY point.

### Photographic evidence and what it actually supports

| Source | Observable structure | Model verification and intervention |
| --- | --- | --- |
| [BNBU university office panoramic lakefront](https://co.bnbu.edu.cn/en/info/1131/2702.htm) | Raised waterfront gallery, hard-paved stepped apron, stairs/ramp, glass-faced buildings over a planted bank | Distinguish land ↔ paved promenade ↔ raised boardwalk, not one flat ground patch. Reconcile model V61 land-apron adjacency. Cannot derive exact stair grades. |
| [BNBU admissions lakeside promenade](https://admission.bnbu.edu.cn/info/1732/1481.htm) | Timber walkway reaches building-side pedestrian space, shrub beds and hard surface meet along well-defined edge | Existing V60 source over-water deck and V61 source hardscape retained; missing local V61 slab-to-slab joins can be repaired from original geometry. |
| [2025 campus bridge photograph](https://uic.edu.cn/info/1078/108739.htm) | Pedestrian bridge has railings and **lands in planting**, not vehicle carriageway | Retain v70 reversible model-bound rail proxy. Do not connect to ROAD_000 or treat any two-level crossing as a road. |
| [BNBU landscape image](https://www.bnbu.edu.cn/campus_life/Landscape_and_Facilities.htm) | Gallery over lake, glass facade, separate raised walk and terrestrial bank | An apparent plan intersection cannot establish same elevation; preserve stair and level-2 bridge distinction. |
| [Campus architect Ronald Lu & Partners](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/) | Masterplan uses pedestrian lanes, streets and semi-open courtyards | Pedestrian access and vehicle approach must be classified separately; a masterplan is not a surveyed lane geometry. |

## Source geometry cross-checks: original-model units, not field measurements

| Pair of inherited meshes | Source plan relation | Height comparison | v71 decision |
| --- | --- | --- | --- |
| V61 promenade slab 01 → slab 03 | **2.442** gap; nearest line entirely outside modeled water | Both z min ≈ 0.09 and z top ≈ 0.27 | **Added 4.156 m² model-plane source-bound slab join**; approx width 1.573, confidence *model topology only* |
| V61 slab 03 → slab 02 | **2.500** gap; land-only | Same V61 Z | **Added 4.247 m² model-plane join** with source-aligned corners |
| V60 over-water deck → western V61 slab 03 | ~4.54 m² plan overlap | Deck top **0.91** vs paved slab top **0.27**, difference **0.64** | **Unresolved grade transition.** Do not draw a made-up accessibility ramp |
| V60 deck → V61 slab 02 | ~14.84 m² plan overlap | Same ~0.64 height difference | **Unresolved**, even though footprints overlap |
| V60 deck → V54 east landfall ramp | ~11.83 m² plan overlap | Both maximum z ~0.91; ramp descends toward grade | **Existing modeled ramp**; no new bridge |
| V54 east ramp → WALK_044 | ~7.77 m² overlap | WALK_044 top ~0.03; V54 spans -0.14 to 0.91 | Existing ramp intersects original footpath; detailed slope/landing clearance *not verified* |
| V61 slab 02 → WALK_045 | ~0.32 m² plan overlap | V61 top ~0.27 vs WALK_045 ~0.03 | **Unresolved 0.24** height step; avoid false flush connection |
| ROAD_000 → WALK_040 | ~**1.143** source model gap | Both near Z=0 | Already spanned by `V54_PAVEMENT_SEAM_CLOSE_ROAD_000__WALK_040_MODEL_EDGE_MATCH` — **do not add another road**
| WALK_044 → WALK_042 | **6.017** gap | Both near Z=0 | Needs independently registered road/footway source; no fill |
| WALK_042 → WALK_040 | **11.513** gap | Both near Z=0 | Large unresolved missing circulation evidence; no fill |
| WALK_045 → WALK_046 | **15.399** gap | Both near Z=0 | Connection line encounters modeled water: **do not invent an over-water link** |

Separate existing `V48_LRC_EXISTING_18_TREAD_EXTERIOR_STAIR_CONNECTED_NOT_SURVEYED` ranges from model z ~-0.12 to 3.10, a pre-existing candidate **building-to-land vertical connector**. Its exact entrance head/foot geometry is *not* photo-registered. The six `V52_LEVEL2_PEDESTRIAN_CONNECTION_*` source bridges are explicitly **second-floor walkways** (approximately 3.42–4.30 relative Z), not vehicle roads. Six Phase-II D1–D6 at-grade links remain **land connections, not bridges**.

## Implementation: source-provenanced, revertible geometry

The new `BNBU_v71_CONNECTED_LAKEFRONT.glb` has **1,379 meshes**: exactly the original 1,377 meshes and **two** appended slab-joint meshes. Their footprints are computed from the nearest V61 source polygon edges, limited to 85% of the inherited narrow slab's model width and original-source slab top/bottom elevation. The `connection_v71_control.json` stores the exact source geometry hash and XY control corners for reproducibility. Build refuses altered source hashes, any polygon intersecting the inherited lake buffer, out-of-bounds joins, or mismatched adjacent top heights.

`BNBU_v71_CONNECTION_PATCHES.geojson` contains **only the two additional source-model features**. Original `BNBU_v66_RESOLVED_REFERENCES.geojson` remains **522 untouched original features**. `BNBU_v71_JUNCTION_AUDIT.geojson` contains **11 classified spatial relationships**. A separate viewer switch shows/hides two new slabs, while the GIS map can display model-checked green/orange/red status lines. None of this validates an accessible route or civil-engineering dimensions.

## Why not create more ramps and bridges now?

Photos establish that real physical transitions exist; they do **not** establish their projection into the current unsurveyed model. The western bridge/land interfaces have overlapping XY but a model **0.64** height offset. Treating those as flat pedestrian pavement would create a false slope and hide the actual alignment problem. The long footpath gaps also do not justify inventing new car roads.

For measurement-grade geometry, obtain georeferenced orthophotography, a bare-earth height reference or control points, identifiable camera poses for the near-bank facade and boardwalk landing, and road/footway as-built elevations. Before that, the new **two source-geometry repairs** and the **audit flags** are the honest extent of implementable corrections.

## Reproduction

```bash
python campus/build_v65.py
python campus/build_v66.py
python campus/refine_waterfront_v69.py
python -m pip install "pyproj>=3.6,<4" "shapely>=2,<3"
python campus/build_connection_v71.py
python -m unittest discover -s campus -p 'test_connection_v71.py' -v
```

v71 is a documented, model-derived **geometry correction**, but not a photogrammetric / surveyed reconstruction. Do not use the new patches or the photo-bound rail overlay as a quantitative bird-collision surface or a real-world navigation guarantee.
