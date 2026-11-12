# BNBU lake and near-land audit — v70

## What was compared, and how

**Baseline:** v69 offline Chromium screenshot, exact v69 GLB (1,377 source meshes), v66 GIS (522 model features), its V60 photographed-typology boardwalk polygon and V13/V61 existing lawn/promenade geometry. **Real-world reference:** campus and local-news published photographs; the photos are *perspective*, not surveyed orthophotos. Their precise camera intrinsics/extrinsics are unavailable; image pixels must not be interpreted as world coordinates.

| Reference | Visible real-world constraint | v69 discrepancy | v70 correction | Remaining uncertainty |
|---|---|---|---|---|
| [BNBU office lakeside](https://co.bnbu.edu.cn/en/info/1131/2702.htm) | Lakefront includes terraces, solid hardscape, a partially raised curved connection and vegetation; buildings include glass | Interstitial near-land looks flat and uniformly grey; promenade not visually distinguishable from illustrated basemap | Assign source V61 promenade slabs a stone-paving appearance; leave all edges and coordinates as-is | Exact widths/materials/height of every terrace require photo registration |
| [BNBU HR image](https://hro.bnbu.edu.cn/index.htm) | Water edge has landscaped planted soil/grass and a narrow railed crossing | V69's shore looks like a continuous pale uniform ribbon; near-land source lawn poorly legible | Existing V13 lakeside grass gets grass texture; boardwalk gets visual reference railings | Real planting species/counts, shore segment classification and stand locations not measured |
| [June 2025 Zhuhai campus photo](https://uic.edu.cn/info/1078/108739.htm) | Raised timber walkway with continuous side rails and visible stanchions, pond, greens | V60 deck is a visually thin brown surface without obvious upper handrails | Additional **reversible**, source-footprint-bound rail proxy, derived from the *water-facing boundary* of existing V60 deck | No photogrammetric verification of 0.9 m demo railing height, 2.8 m post pitch, or V60 alignment |
| [BNBU admission photo](https://admission.bnbu.edu.cn/info/1732/1481.htm) | Boardwalk timber/paver texture and planted frontage visibly differ | Material treatment is mostly grey and uniform | Give exact existing V60 deck warm timber-tone finish (not plank-by-plank reconstruction) | Not physical material spectroscopy, not board-by-board survey |
| [2019 BNBU ecology account](https://www.bnbu.edu.cn/info/1077/4589.htm) | Seasonal natural wetland at Chihua Hill with two freshwater ponds nearby | Five inherited water *mesh entities* might be mistaken for five true lakes or the documented two ponds | Preserve geography names and uncertainties; do **not** generate two arbitrary pond meshes | Requires orthorectified imagery and control points |

## Quantified source-internal findings (NOT measured campus dimensions)

The model-derived first lake polygon LAKE_00 has planar area ~9,557.4 m² and LAKE_01 ~7,507.2 m² (EPSG:32649, converted from existing model GeoJSON); the five LAKE_00..04 model entities **do not establish five real lake boundaries**.

V60 boardwalk has existing 2D model area ~488.10 m². Its intersection with the model LAKE_00 footprint is ~408.17 m² (83.6%), so its visible over-water structure should be presented as a *raised, detailed crossing* rather than an unqualified on-land path. To place display-only railing meshes without shifting waterlines, v70 clips the **existing V60 polygon boundary** to the interior of the inherited LAKE_00 polygon (~0.8 m inset) and samples that source-bound line in the original local model CRS. This produces approximately 230 m of two-sided path-bound railing boundary. No new alignment is drawn.

T4 existing 16-tread stair plan intersects the LAKE_00 polygon by ~48.28 m². **Plan overlap is not 3D collision.** A raised stair/deck may be legitimate; the model lacks registration and reliable clearance measurements. v70 preserves that stair and records a “needs verification” spatial flag, rather than deleting or moving it.

### What the v70 changes do not mean

The handrail dimensions and post spacing are *visual assumptions*, declared and switchable. The target corridor is a source-internal model, not a trace from a registered photograph. Existing source lawn/promenade surfaces are recolored but not re-polygonized. No camera registration, photogrammetry, 10–30 cm shoreline accuracy, real pond delineation, roof-size survey, vegetation inventory or measured bird-visible reflectance is claimed. These proxies **must be excluded** from any bird-strike glass-area denominator, bird collision predictor, and engineering survey exports.

## Reproduction and tests

Build v64/v65/v66/v69 as usual; install pyproj and shapely, then run `python campus/build_lakefront_v70.py`. Confirm `python -m unittest discover -s campus -p 'test_lakefront_v70.py' -v`. The overlay is stored separately in `campus/generated/BNBU_v70_LAKEFRONT_DISPLAY_OVERLAY.json`, with exact inherited source GLB/GIS SHA-256 and source coordinates. The v70 viewer uses the source GLB + this *display-only* addition. Toggle “实景类型参考” to inspect with the proxy hidden. Screenshot QA is performed on both offline file and local HTTP versions.
