# BNBU Zhuhai editable GIS/3D v84 (2026-11-12)

## Direct parent and effect

Built from **Library v83** (SHA256 main GLB `2b694603f2d592499196f40bf74b569de55ccf42d2c63217b82bf76dce717b36`), **not** v10. The original v10 checkpoint remains in `reference/` as historical provenance. The reconciled main v76.1 viewer, v76 LRC skylight and v83 V52 bridge-end diagnostic work remain inherited. GitHub PR #10 stays draft.

**Proven exact duplicate geometry removed from the active main GLB:** `V42_FACET_SIDE_ROAD_000` (314 triangles). The entire overlay lies on the existing 416-triangle original `ROAD_000` solid (maximum 3D separation 1.25e-8 model m measured at three interior samples on every overlay triangle). They have the same color and transform. Keeping both superimposes material on the same physical surface and can cause z-fighting. The original 314 triangles are independently preserved under `model/BNBU_v84_REDUNDANT_ROAD000_SIDE_DISPLAY_ONLY.glb`, not destroyed. Neither the physical original road nor its GIS footprint is changed. Other near-duplicates did **not** satisfy the exact 3D containment test and were conservatively retained.

Main GLB: **1,347 → 1,346 named meshes**, **691,907 → 691,593 triangles**. All **1,346 remaining meshes** retain exactly the parent vertex positions, faces, graph transforms, and color/texture attributes on full round-trip GLB reimport. Every model coordinate is unchanged. No new actual building, bridge, glass or road was created.

## A genuine WebGL viewer bug fixed

The inherited v83 full offline HTML embeds a **1,347-mesh** GLB but its runtime assertion still required **1,380** meshes (`it.length!==1380`), necessarily failing in any fully functioning WebGL browser. v84 replaces the assertion with **1,346** and embeds the actual v84 GLB hash `242ade4c7cf25a4437e674b271ea451f9367449c23530ca95679b33749989848`. The new **standalone** HTML also contains its *own CPU fallback HTML* inside the same file. It automatically enters an interactive 3D CPU preview when the browser really fails WebGL context creation, or can be opened manually using the fallback link. Unlike v83, the fallback does not require the sibling file to exist.

Independent Chromium test via `set_content` verified that automatic fallback renders 1,346 source mesh nodes and records all 691,593 source faces; the CPU viewport uses actual sampled source triangles (not generated geometry). The CPU standalone viewer and road focus switch also passed. **This environment did not provide a working WebGL context**, so native WebGL full-campus rendering is *not* claimed to have passed. A `WebGL context` page error occurred and was caught by the automatic fallback as designed. GitHub Pages availability remains unconfirmed, and may require the repository owner to activate Settings -> Pages -> GitHub Actions.

## Invariant GIS, bridge endpoints and science

`data/BNBU_v84_EDITABLE_GIS.gpkg` (146 layers), `data/BNBU_v84_ACTIVE.geojson` and `.kml` (534 features) are byte-exact parent v83 content. All 12 V52 bridge end source-face IDs and actual triangle vertices remain unchanged; their `is_routable=0` status continues to apply. LRC continuous skylight (34,816 inherited triangles) is preserved, and no earlier quarantined 690 speculative glazing belts, 6 railings, 5 roof plant rooms, V49 inferred pathways, V54 inferred landing or v60 support proxy was revived.

GLB XY coordinate origin: EPSG:32649 UTM offsets `(758940,2474080)`; Z model-relative, no surveyed datum. GIS is EPSG:4326. The 2025 [official campus hand-drawn map](https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg) remains a non-orthorectified topological/structural constraint. RLP's [project description](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/) supports campus circulation and elevated bridge *type*, not surveyed distances. An [official BNBU LRC photo](https://foundation.bnbu.edu.cn/jzxm/xyjs.htm) supports glazing/white diagonal external braces; it provides neither lens calibration nor projective registration.

No verified fresh OSM/Overpass way vertices, DEM, photogrammetric camera poses, bridge landings, real walkway access grades or glass exposure measurements were added. No quantitative birdstrike exposure calculation should be drawn from this scene.

## Files / reproduction

- `model/BNBU_v84_FULL_EDITABLE.glb` — editable master GLB.
- `model/BNBU_v84_REDUNDANT_ROAD000_SIDE_DISPLAY_ONLY.glb` — archived exact redundant overlay, optional.
- `model/BNBU_v84_ROAD000_RETAINED_ONLY.glb` — exact retained original road, inspectable.
- `data/BNBU_v84_EDITABLE_GIS.gpkg`, `BNBU_v84_ACTIVE.geojson`, `BNBU_v84_ACTIVE.kml` — unchanged GIS.
- `viewer/BNBU_Campus_3D_Offline_v84.html` — stand-alone full GLB + **automatic, embedded CPU 3D fallback**.
- `viewer/BNBU_Campus_3D_CPU_v84.html` — source triangle CPU 3D, orbit, category selection.
- `viewer/BNBU_v84_V52_Actual_Triangle_3D_Inspector.html` — v83 true source bridge-end inspector retained.
- `figures/` — actual Chromium screenshots, not photogrammetry.
- `input/` — full v83 GLB and GIS; `reference/` — v10, inherited viewers and V52 evidence.
- `qa/` — build, duplicate screening, 1,346-mesh independent validation, browser test and SHA256 inventory.

To reproduce in Python 3.11+: 

```sh
python -m pip install -r requirements.txt
python source/build_v84.py
python source/build_viewers_v84.py
python source/verify_v84.py
python source/test_viewers_v84.py
```

Static source and QA should be committed to the active draft PR branch; large binaries should remain in the full Library ZIP rather than blindly overwriting main.