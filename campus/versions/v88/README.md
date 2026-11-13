# BNBU Zhuhai Campus — v88 whole-campus release

## Start here

1. Extract the complete ZIP.
2. Open `BNBU_Campus_Full_v76/双击查看_校园3D.html` in Chrome or Edge. This is the full-campus offline viewer, with the v88 corrected master and extended asset selector embedded.
3. The normal full-campus model is the main editable asset at `BNBU_Campus_Full_v76/generated/BNBU_v71_CONNECTED_LAKEFRONT.glb`.
4. The main GIS remains the inherited v76 source set (522 active features). The QA-only extended building anchor GeoJSON/GPKG is under `registry/`; it is not the scientific GIS master.

## Whole-campus baseline

The physical master is based on the latest mainline v76.1 full-campus release, not the smaller alternate v84/v87 lineage. The main package preserves its buildings, roads, bridges, lakes, hills, terrain reference, LRC, 70 road/walk candidates, 47 junction hotspots, seven bridge systems and twelve academic bridge-end records.

### v88 geometry correction

The inherited `V42_FACET_SIDE_ROAD_000` mesh was a duplicate display overlay on the retained `ROAD_000` surface. It had 314 triangles. The node was detached from the active GLB scene graph; `ROAD_000` remains unchanged. Three interior samples on each of the 314 triangles (942 samples total) have maximum distance 5.82e-8 model units to the retained road surface. Vertex positions, vertex colours and node transforms match. The duplicate is retained separately as `generated/BNBU_v88_V42_ROAD000_DUPLICATE_DISPLAY_ONLY.glb`.

The active scene now has 1,378 mesh nodes and 659,479 triangles. One unused mesh resource remains in the GLB buffer for provenance; it is not referenced by the active scene and is not rendered. The 522-feature GIS and all other active mesh nodes are unchanged.

## Expanded building/facility inventory

The original v76 core inventory remains 30 (T1–T8, V15–V29, D1–D6 and Phase I LRC). v88 adds eight mapped selector entries already present in the source model: T29, Administration Building, University Hall, Sports Complex, Performance Theatre, Cultural Creativity Clusters, YUZHAN (model label only) and the Phase II circular commons (model label only). This gives 38 selectable mapped assets without inventing new building geometry.

Two important unmapped records are retained separately:

- **Phase II Learning Resource Centre and Laboratory Complex:** official 2025 material identifies a distinctive cubic building with library, laboratories, shared services and a sky garden. Its exact mesh mapping is unresolved. It is not the circular `V24_P2_CIRCULAR_COMMONS` proxy.
- **CTV-nearby small house:** a user-reported hypothesis, name and position unverified; remains quarantined and outside the physical master.

`registry/BNBU_v88_BUILDING_ASSET_REGISTRY.json`, CSV, GeoJSON and GPKG provide the expanded inventory. GeoJSON/GPKG points are model-anchor centres, not surveyed footprints, entrances, glass positions or bird-strike areas.

## Separate research candidates

- `research/alternate_v84_v87/` preserves the v84/v85/v86/v87 alternate research lineage and its full registration experiments. It is **not** merged into the main v76.1 physical master: it has 1,346 mesh nodes / 691,593 triangles / 534 GIS features and a different set of retained/removed model components.
- `research/lrc_skylight_v76_branch/` contains the separate one-mesh LRC skylight candidate. The source rim and two arch ribs match the main v76.1 model exactly; the candidate is 17,410 vertices / 34,816 triangles and watertight. It remains unsurveyed and is not in the default master or bird-strike exposure denominator.
- `research/lrc_skylight_v76_branch/BNBU_v88_FULL_CAMPUS_PLUS_LRC_SKYLIGHT_CANDIDATE.glb` combines the complete v88 master with that optional candidate for comparison only.

## Important geometry and evidence limits

- GLB XY uses EPSG:32649 with local offset (758940, 2474080). Z is model-relative, not a surveyed vertical datum.
- The official 2025 Phase II LRC/LC images are project imagery, not survey control or a calibrated as-built reconstruction.
- The existing source hills, lake surfaces, wetlands, V60 boardwalk supports, Phase II paths and bridges retain their source uncertainty flags.
- No new measured windows, doors, road connections, shorelines or bird-strike glass area are added in v88.

## Rebuild and verify

Python 3.11+ with the packages in `requirements.txt`:

```bash
python src/build_v88.py
python src/verify_v88.py
python src/test_v88_browser.py
```

The package includes SHA256 manifests. Verify the archive with `unzip -t` before use.