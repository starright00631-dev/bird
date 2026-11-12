# BNBU v76 — architectural feature recovery and connection evidence

## Scope and source discipline

This iteration recovers building identity from existing geometry instead of synthesizing a generic facade. The input source is the unchanged v71 GLB (1,379 mesh nodes) plus v66 GIS (522 features). Source building family identification is explicit: T1–T8 teaching (8), V15–V29 Phase I residences (15), D1–D6 Phase II residences (6), and the LRC (1). A prefix such as V34 is a historical mesh revision and **does not mean a V34 dormitory**.

The render-only architectural feature layer is produced by detecting the *actual inherited triangle boundary edges and sharp creases* above 34 degrees, with 0.0001 local source-coordinate quantization. Four independent glTF line systems distinguish T, V, D and LRC. It adds no source roof, building face, window, balcony, or door polygon. Source-specific color correction also separates these existing components in the viewer, and is individually reversible.

## Building family comparison

| Family | Existing historical details that were visually underrepresented | Evidence-backed type | Unverified and not added |
| --- | --- | --- | --- |
| T1–T8 | Roofs, parapets, facade sidewalls, story bands, recessed galleries and piers | [BNBU T1 photo](https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm) shows warm masonry and horizontal glazing ribbons | Building-specific window subdivision, exact entrances |
| V15–V29 | Individual main masses, roof decks, story-edge details, selected gallery slabs | [BNBU early Cultural Village](https://www.bnbu.edu.cn/info/1076/6575.htm) describes residential common rooms and semi-enclosed roof gardens; [2017 building code article](https://www.bnbu.edu.cn/info/1078/9214.htm) distinguishes V accommodation | Identical roof gardens and balcony grid on each V building |
| D1–D6 | Distinct six residence masses, dark roofs, roof ribs and central courtyard | [BNBU official dorm tour](https://bnbu.edu.cn/en/info/1255/10522.htm) documents balconies/open rails; [2022 construction article](https://www.bnbu.edu.cn/en/info/1255/10406.htm) confirms six-building living quarter | Exact dorm balcony/window dimensions, unit counts or D-by-D openings |
| LRC | Exposed diagonal braces, pillars, oval skylight, glass facades, cantilevered entrance canopies, atrium structure | [BNBU office photo](https://co.bnbu.edu.cn/) directly shows white diagonal bracing, blue glazing and raised soffit; [architect RLP](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/) describes campus levels | Glass panel count/area, surveyed door thresholds, invented geometry |

The existing model already includes detailed architectural components; the v75 rendering had largely flattened their visual distinction. This does not mean every real-world detail is already reconstructed.

## Environment and junction inspection

For each of the 30 buildings, project its inherited roof or mass to XY; compare with all **56 WALK/ROAD** route polygons and five lake polygons; record the closest four routes and two lakes, source bounding box and Z range. This yields candidate *spatial neighbors*, not doors, paths, and not a verified connection graph. Keep v74's 47 source-local junction cases, v75's 12 academic bridge ends, and V60 east/west shore approach as independent layers. The inherited model mismatch of approximately 0.64 source units between lake bridge and western platform remains unresolved, as does approximately 0.24 between platform and WALK_045. The V52_03 elevated connection remains sloping.

## Algorithms with actionable data requirements

**Stage A: implemented, no new photography required.** Semantic source-mesh classification + triangle sharp-edge extraction + original-surface material enhancement + topology-aware nearest-path audit. Source edges are exact inherited geometry; the colors are approximate visualization.

**Stage B: SfM/MVS with photographic registration.** Use [COLMAP](https://colmap.github.io/) or pycolmap on 3 or more mutually overlapping photographs per facade sector. Require matched fixed landmarks, baseline, common scene and a held-out view. If unrelated publicity photos do not overlap, SfM must report insufficient registration rather than hallucinating a result.

**Stage C: building structure refinement.** Use line segment detection, vanishing-point constraints, piecewise-planar regularization and projective reprojection error. Treat columns, glass, roofs, shadows and inset balconies as separate semantic planes. Line/plane-constrained photogrammetric mesh refinement is discussed in [Fang et al.](https://doi.org/10.1080/15481603.2025.2562734). Preserve cantilevers, actual slopes and exposed LRC braces; do not force all surfaces to be a rectangular grid.

**Stage D: evidence-calibrated windows and balconies.** A discrete facade-component approach such as [SemanticMesh](https://doi.org/10.1080/10095020.2024.2381592) is appropriate *after* camera calibration and opening segmentation. Count observed windows and size from actual fixed points; do not derive bird-collision exposure area from rendering polygons.

**Lower priority:** NeRF/3D Gaussian Splatting is useful for photographic visualization with overlapping images but does not, by itself, supply editable watertight geometry or verified door/railing connections. It should not replace the structural GLB.

## Tests and limitations

Source model and 522 GIS features immutable; every display edge is a source-triangle edge. Thirty buildings have type-safe identity and planar proximity records. No invented window/roof/balcony or traversable connection is claimed. All current links and architectural geometry are relative model coordinates, not field surveys. Next architectural additions require actual multi-view localization and quantifiable holdout reprojection error.
