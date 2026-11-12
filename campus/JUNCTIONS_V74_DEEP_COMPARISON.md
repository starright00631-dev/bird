# BNBU v74 — Junction-first source geometry and multi-view evidence comparison

## What is actually verified

The v74 pass prioritizes building–step–deck, deck–ramp–bank, road–footway, water-edge, and upper-level walkway transitions, **not** styling empty campus surfaces. The input is the unchanged v66 522-feature GIS and v71 1,379-mesh 3D source. Original v72 evidence includes 16 distinct photographs; another **seven** manually examined distinct official-school photographs bring the visual register to **23**, all linked to their publishers. No source photograph has surveyed camera coordinates or metrologically calibrated 3D control.

A first-party architect description, [Ronald Lu & Partners](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/), explicitly describes suspended and non-coincident bridges/staircases, and connected courtyards. Thus, an XY overlap is **not** a physical or accessible route unless the source 3D layers also meet appropriately.

## Complete computational scope

- 54 inherited `WALK_` polygons plus 2 inherited `ROAD_` polygons: **1,540 unordered pair comparisons** (plan gap, overlap area, source z).
- Source exact-polygon contact: only 4 pairs within a 1 m model XY gap, 9 within 3 m, 16 within 8 m and 30 within 15 m. These counts include overlapping or touching polygons and do not certify real network connectivity.
- Two major road/footway *overlaps* require semantic classification rather than filling: `ROAD_000` with `WALK_000` (74.441 m² model overlap) and `WALK_037` (78.843 m² model overlap). Overlap is not proof of pedestrian-vehicle at-grade crossing.
- Six inherited `V52_LEVEL2_PEDESTRIAN_CONNECTION_*` meshes, separately traced from their actual 3D triangle outlines, against all 56 ground road/footway polygons: **336 additional plan comparisons**, 6 within 10 m model XY. At near/overlapping ground links their local elevations differ by more than 3 model units. Do not mark them as ground-level traversable connections.
- Recomputed **11 prior v71 junctions** using the **actual triangulated local top surface** at the nearest or overlapping source point, instead of comparing the entire mesh's maximum Z.
- **47 3D review hotspots** retained for the model inspector, with source pair IDs, local source-anchored xyz, metrics, evidence class and "not surveyed" gates. No new physical meshes or GIS footprints were invented.

## Most consequential local-height corrections

| Junction (inheritance only) | Earlier whole-mesh top comparison | v74 local barycentric contact difference | Decision |
| --- | ---: | ---: | --- |
| V60 bridge deck → V54 eastern ramp | approximately 0 | **0.06849** | They approach the same level locally, but seam detail / walkability remain unverified |
| V54 eastern ramp → WALK_044 | **0.88** | **0.04946** | Previous whole-ramp-maximum method artificially inflated the landing mismatch; do **not** flatten or replace this ramp |
| V60 bridge deck → western V61 slab 03 | **0.64** | **0.640** | Genuine source-model level disagreement remains; do not invent a threshold ramp |
| V60 bridge deck → western V61 slab 02 | **0.64** | **0.640** | Same independent unresolved western landing level |
| V61 slab 02 → WALK_045 | **0.24** | **0.240** | Still requires close land-bank and threshold source evidence |

All numerical heights are inherited **model-relative units**, not geodetic surveying.

## New short-gap suspects — **not yet physical additions**

Four additional small same-layer source-footpath gaps emerged: `WALK_010`–`WALK_011` (1.348 m model), `WALK_013`–`WALK_014` (1.875 m), `WALK_011`–`WALK_031` (2.369 m), and `WALK_026`–`WALK_027` (2.726 m). They were compared against the exact GIS edge geometry, neighboring pavement and water footprints. Their apparent edge alignment **does not establish a current pedestrian link**. Unlike the two previously added v71 slab joints, these will remain markers until registered image or as-built alignment supports a physical edit.

The prior `WALK_038`–`WALK_039` gap of 0.642 m and `ROAD_000`–`WALK_040` gap of 1.143 m already have inherited V54 junction meshes. **Do not duplicate** them. `WALK_044`–`WALK_042` (6.017 m), `WALK_042`–`WALK_040` (11.513 m), and `WALK_045`–`WALK_046` (15.399 m, near water) remain particularly risky guesses; the last gap crosses/skirts the modeled water edge.

## Seven extra independently checked image viewpoints

See `evidence/connection_comparison_sources_v74.json`. Unique official page references: [pond bridge](https://www.uic.edu.cn/en/info/1055/8428.htm), [aerial showing lake and mountain](https://www.bnbu.edu.cn/info/1077/12404.htm), [official landscape gallery](https://www.bnbu.edu.cn/campus_life/Landscape_and_Facilities.htm), [library aerial](https://admission.uic.edu.cn/info/1717/1202.htm), [dusk research bridge](https://www.uic.edu.cn/en/research.htm), [bank approach](https://www.uic.edu.cn/en/) and [lake-side retaining structure](https://uic.edu.cn/en/index.htm). Their information is **typological and adjacency based**, not camera-registered. Avoid duplicate counting of the old v72 image views and don't reuse University of Illinois Chicago or Beijing Normal University's separate Beijing campus photos as BNBU Zhuhai evidence.

The 2025 official **illustrated** campus plan is only a neighborhood constraint, never orthophotography. A third-party POI directory lists named campus buildings including phase-I and phase-II LRC locations but does not establish as-built route outlines or photographic pose.

## Implementation and falsifiable QA

`src/audit_connections_v74.py` reads the inherited indexed glTF triangles directly, computes barycentric elevation on the source local XY plane, verifies parent GIS geometry, audits all 1,876 combination pairs, and exports:

- `generated/BNBU_v74_ALL_ROAD_WALK_PAIRWISE.json` (1,540 + 336 2D relations)
- `generated/BNBU_v74_LOCAL_3D_JUNCTION_HOTSPOTS.geojson` (47 source-anchored hotspot records)
- `generated/BNBU_v74_CONNECTION_RESEARCH_SUMMARY.json` (counts, hash control, limits)

`src/test_connections_v74.py` checks complete pairing, source file hashes, rerun-determinism, local contact heights, and **no new surveyed-connection assertions**. The standalone browser should allow selecting individual 3D hotspots without accidentally converting a diagnostic into a physical road, ramp, bridge, guardrail or glazing. The right target is geometrically faithful detail, not a screenshot-friendly but incorrect connection.

### Next geometry-permission gates

Obtain at least two matched photographic views or ortho control on each bridge landing, road/path transition and LRC stair; independent ground reference / point cloud for the 0.64/0.24 model-Z mismatches; measurements of bridge threshold, stair/landing end and support columns. Before any new physical join, match the source edge ID, local height at the actual endpoint, surface width, water exclusion, road class, source age and target topology. Avoid promoting the quarantined CTV small-house model or creating invented trees, roof service boxes and glass panels.