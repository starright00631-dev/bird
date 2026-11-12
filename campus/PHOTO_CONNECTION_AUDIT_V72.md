# BNBU v72 — Multi-image critical review of connection details

## Scope and falsifiability

**Why v71 was insufficient:** its waterfront analysis cited only a few representative perspectives and inserted two tiny grade-matched promenade pieces, leaving **building→stair, bridge→ramp, road→walkway and terraced waterfront access** visually generic or undefined. In a close browser screenshot, the bridge visually terminated over broad flat grey pavement without a credible dimensioned western transition. The v71 join finish also differed from the three original V61 paving slabs. Adding indiscriminate bridges or terrain polygons would conceal, not resolve, this discrepancy.

**This iteration reviewed 16 distinct images** individually in the searchable official and secondary photo sources. The stable per-photo metadata is in [connection_photos_v72.json](connection_photos_v72.json), including the *exact publisher URL*, what can actually be seen, potential source mesh, registration confidence, and whether a geometric operation is allowed. Three additional BNBU photographic collections contain many more frames requiring individual registration.

No copyrighted photograph is copied into the offline ZIP: the viewer displays thumbnails from the publisher site **only when the user opens the evidence tab while online**. Every image keeps its original source link and category filter. The 3D model itself works offline.

### Image-by-image evidence table

| ID | Category / source | Distinct observable detail | v71 deficiency and v72 choice |
|---|---|---|---|
| P01 | BNBU office LRC panorama | Glass-clad building above hard terrace; low waterfront roof, planted bank; wood pedestrian deck | Source V60 deck and V61 platforms *belong to different structural levels*; do not fill 0.64 model-unit missing grade blindly |
| P02 | 2025 Zhuhai reporting | Rail-supported over-water timber walk lands in planted area, not vehicle road | Existing V60 perimeter rail remains independent, and eastern V54 ramp gets source-height-following side-detail |
| P03 | BNBU admissions boardwalk | Timber finish meets planting and pond edge; overhead pergola visible | Distinct deck/ground materials; model is still missing verified pergola pose |
| P04 | BNBU FST lake panorama | Curved elevated bridge, supporting piers, lake islands, LRC stairs/terraces | Differentiate deck surface from eastern ramp, rather than an arbitrary flat bridge |
| P05 | BNBU LRC dusk | Elevated transparent LRC block and wide exterior staircase | V48 existing **19 upper tread elevations** (18 rises) support precise profile-following handrail placement |
| P06 | BNBU LRC daytime | Broad exterior flight and glass-building entrance | Not proven same as V48 flight. Do **not** copy step width/flight count from this photo |
| P07 | BNBU stair + retaining wall | Transparent balustrade and stone retaining wall at an academic staircase | Architectural type supports guardrails, not an exact glass pane area; do not add new collision glass to certified geometry |
| P08 | 2025 open-day curved crossing | Pedestrians above landscaped bank near glazed entrance | Raised rail/deck cannot be replaced with grade-level road/sidewalk |
| P09 | BNBU HR planted shore | Water edge, planted island, low shore parapet and level promenades | Retain planting/lake as separate features; photos do not resolve exact shore polygon |
| P10 | EducationOnline oblique aerial | Pond, LRC, pedestrian deck and academic blocks | Plan adjacency is observable but oblique perspective cannot supply surveyed distances |
| P11 | Pacific Alliance aerial | Campus road, plazas, buildings, plantings and pond relationship | ROAD_000 is not automatically identical to any pictured asphalt segment |
| P12 | BNBU LinkedIn campus courtyard | Stone approach and exterior stair flanked by vegetation, building entrance at higher level | No generic ramp should be inserted in a stair transition from appearance alone |
| P13 | BNBU student walk | Pedestrian pavement, landscaped verge, academic building edge | Distinguish road-like sources and walkway surfaces by illustration; exact curb alignment remains unknown |
| P14 | BNBU Excellence Road | Named vehicle road with separate verge and sidewalk leading to buildings | Existing ROAD_000 / WALK_040 seam remains; avoid inventing a new bridge or roadway from photograph |
| P15 | GlobalAdmissions waterfront deck | Timber deck, low concrete retaining edge, reflective pond, canopy | Does not establish whether photographed bank is exactly LAKE_00; no invented bank wall |
| P16 | BNBU roof/aerial | LRC roof + water + courtyards + multilevel land routes | Confirms levels and different surface types, not camera-registered 3D control points |

**Additional image sets**: [BNBU 2023 lakes/landmark multi-view gallery](https://www.bnbu.edu.cn/info/1075/14515.htm), [BNBU official paginated photo archive](https://bnbu.edu.cn/en/campus_life/photos.htm), [campus photo locations including LRC/exterior auditorium/admin entry](https://www.bnbu.edu.cn/info/1076/14661.htm). These are additional candidate frames, not counted as independently calibrated control.

**Explicit exclusion:** searches for “UIC” often return **University of Illinois Chicago** photos. No such photographs are included in the 16-photo BNBU register.

## Geometric tests and implementation

| Existing model feature | Verified source topology | v72 viewer change | What remains unknown |
|---|---|---|---|
| `V54_LAKE00_EAST_WATER_CROSSING_SHORE_RAMP_INFERRED_ENDPOINT_MATCH` | **122** XYZ vertices, upper bank profile approximately 0.91→0.03 model Z, lower extrusion to −0.14 | Two rails follow **actual projected source mesh perimeter** and upper surface pointwise, not interpolated across unrelated lawn polygons | Rail height 0.83 source units and post spacing are illustrative; endpoint location derived from old model, not registered photography |
| `V48_LRC_EXISTING_18_TREAD_EXTERIOR_STAIR_CONNECTED_NOT_SURVEYED` | **76** vertices; two x-side lines; **19** sequential upper step elevations 0.172→3.10; source width ~3.6 model units | Two side rails follow these 19 original stepped elevation samples; no second staircase invented | Glass vs steel finish, start/finish and entrance door alignment not established |
| Western V60 bridge → V61 slab | Plan intersection, top difference **0.64** | Three explicit **diagnostic** 3D height bars are available on demand (two 0.64, one 0.24) | Real grade transition may be ramp, stair or incorrectly modeled vertical position; photograph camera registration required |
| V71 V61 short joints (2) | Both source-bound 2.442 / 2.500 model-unit land gaps; previous geometry stays exact | New joins share V61 adjacent material rather than inconsistent source grey | No surveyed width, subgrade, coping or actual concrete specification |
| ROAD_000 / WALK_040 | Existing V54 at-grade seam, no elevation mismatch in source GLB | Different source road and sidewalk *display colors* make the connection recognizable; no new vehicle road | Photo is a different/unregistered street view; real kerb and accessible crossing slope unverified |
| LAKE_00 bank and exterior LRC | Photo types include planted islands, stair/terrace height changes and glass facades | Strictly keep the inherited terrain/lake boundary and preserve the unknown western landing | Need calibrated orthophoto/oblique cameras to recover true retaining-wall profile |

**Data integrity:** same 1,379 v71 GLB meshes (original 1,377 + two v71 land-only repairs), same original 522 geospatial features. v72 generates separate `BNBU_v72_SOURCE_ELEVATION_PROFILES.json`, containing four exact source-mesh XY/Z profiles, independently optional guardrail-display heights, three unresolved elevation-difference markers, original GLB/GIS checksums and 16-photo source IDs. The additional rails and warning cylinders are **display-only runtime objects**, excluded from analytical meshes and any bird-facing glass exposure denominator.

## Strict handling of photographic correspondence

1. **Publisher identity:** campus is BNBU, Zhuhai. Exclude UIC Chicago and off-campus public roads.
2. **Structure identity:** only LRC and central lake images with identifiable architecture are used as *tentative local structure anchors*. Generic academic / road images support types only.
3. **Topology before metric:** identify road, path, terrace, stair, elevated walkway, land, lake, planting as different classes; ask if XY plan intersection crosses a different Z.
4. **Coordinates:** 16 photos lack independently measured 3D control point correspondences; do not claim extrinsics, intrinsic calibration or photograph-derived placement.
5. **Height:** v71 GLB model units remain relative. v72 handrail top offsets are clearly *visual assumptions*, not measured physical dimensions or birdstrike glass.
6. **Reversal:** toggle v72 ramp/stair guardrails and 3 height-difference markers independently, compare back to unmodified v71 model.
7. **Acceptance:** four profile paths must agree pointwise with original model vertices; model hashes exact, 3 mismatch heights retained, and Chromium opens both offline HTML and local HTTP without missing 3D, GIS or new evidence data.

### Next true-geometry task

The decisive unsolved west bridge-to-land connection needs *at least* two appropriately overlapping camera views with identifiable LRC window/column corners and surveyed georeferenced control, to distinguish a missing actual stair/ramp from an incorrect historic deck height. Roads need exact high-resolution mapping before kerb and junction geometry is committed. v72 deliberately avoids ungrounded reconstruction while making existing real model structures and their uncertain transitions substantially more inspectable.
