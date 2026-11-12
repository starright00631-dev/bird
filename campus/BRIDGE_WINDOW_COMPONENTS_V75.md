# BNBU v75 — bridge components, transparent infill and twelve landing interfaces

## Why the inherited model is incomplete

The former display added rails/posts on the V60 lake crossing but omitted **transparent infill** visible in a BNBU open-day photograph. That infill can look like "windows" from a distance, but it is technically a **glass balustrade** rather than evidence that the bridge is an enclosed, windowed skybridge.

The same scene also contains **six other bridges**, \`V52_LEVEL2_PEDESTRIAN_CONNECTION_00–05\`, each currently represented by an inherited structural slab. The presence, placement, sill heights, mullion rhythm and roof form of windows on these *separate* academic links are not individually photographically verified. The user's first-hand statement that a bridge has windows is retained as a hypothesis requiring localization; glazing on neighboring LRC or T1–T8 buildings is NOT sufficient.

These are different evidence questions, requiring distinct objects and checks.

## Source-based bridge component census

| Component/system | Existing inherited source | v75 treatment | Missing proof |
| --- | --- | --- | --- |
| V60 lake crossing deck | V71 GLB \`V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE\` | Preserve source mesh, width and path | Surveyed edges/landfall |
| V60 support rhythm | 13 named V60 pier groups, 13 corresponding crossbeams | Verify existence and retain unchanged | Actual pile positions, head sizes and count |
| V60 rails/posts | V70 rail reference sampled at **340** positions on existing deck geometry | Retain original posts and horizontal rails | Measured railing height/post spacing |
| V60 glass-like railing infill | University open-day photo establishes transparent side-panel *type* | **New independent, toggleable translucent 3D strip**: 2 long runs, 339 mesh quads, from model boundary. No generated mullion grid | Real panel bounds, count, mounting and glazing optical specs |
| V60 east bridge → V54 sloping approach → WALK_044 | V71 source meshes; V74 local surface checks | Preserve sloping profile; previously measured local model deltas around 0.068 and 0.049 | Surveyed landing width, cross-slope, handrail termination |
| V60 west bridge → V61 platform → WALK_045 | V71 slabs and v74 local surface checks | **Unresolved** 0.64 and 0.24 inherited model-Z mismatches remain visible in v74 diagnoses | Camera-registered door/steps/ramp/elevation |
| V52 00–05 deck and soffit | Six inherited v71 source GLB meshes | Recompute each footprint, absolute local top Z and 2 endpoints; no triangulation changes | Door thresholds and end guards |
| V52 window/frames | User report: bridge has window, no individual V52 source matching | Inventory explicitly lists absent/missing window, sills/mullions, supports and canopy | Two camera-matched sides and measured window bounds |
| V52 separate stories versus ground routes | v74 336 overhead/ground comparisons | Maintain upper-level separation; never mark XY overlap as walkable | Stairs/vertical-access paths connecting actual floors |

**Critical distinction:** 339 *triangulated display quads* are not 339 real glass panes. Actual glass area remains unknown. The transparent infill GLB is neither registered real-world architecture nor a valid bird-collision exposure surface.

## Re-identified elevated bridge endpoints

The six V52 source slabs were inspected individually against the corresponding V40 inherited building envelopes and triangulated local top surfaces. Using building-pair order alone incorrectly reverses four end assignments.

| Bridge | Inherited building pair | Corrected model end A → end B | Local model top Z (A / B) | Immediate geometric risk |
| --- | --- | --- | --- | --- |
| V52_00 | T4–T5 | **T4 → T5** | 4.300 / 4.300 | Identify actual door thresholds, keep terrace roof layers apart |
| V52_01 | T5–T6 | **T6 → T5** | 4.300 / 4.300 | Reversed old label, separate adjacent terrace/gallery surfaces |
| V52_02 | T6–T7 | **T7 → T6** | 4.300 / 4.300 | Reversed old label, possible adjoining balcony not entrance |
| V52_03 | T7–T8 | **T8 → T7** | **3.709 / 4.291** | Nonflat bridge: flattening would corrupt the existing sloping deck |
| V52_04 | T1–T2 | **T1 → T2** | 3.800 / 3.800 | Gallery deck around 3.33–3.76 model Z, uncertain landing |
| V52_05 | T2–T3 | **T3 → T2** | 3.800 / 3.800 | Reversed label, missing independent T3/T2 threshold photo |

These are **model-internal Z units**, not measured metres above mean sea level. Building association is based on inherited V40 2D envelope intersection / proximity, not proof of a traversable opening. Every endpoint has \`threshold_passable_verified: false\`. The \`V52_03\` slope is real to the inherited triangulation; do not extrapolate height from one end.

## Image and architect evidence — role by role

1. [BNBU 2025 open day photograph](https://www.uic.edu.cn/info/1075/106799.htm): demonstrates transparent side infill supported by a rail frame on a low campus pedestrian crossing; **typology**, not actual position/number.
2. [BNBU FST panorama](https://fst.bnbu.edu.cn/mscbs_en/index.htm): shows a low curving lake crossing, columns and relationship to LRC and planted banks; distant perspective only.
3. [BNBU admissions boardwalk](https://admission.bnbu.edu.cn/info/1732/1481.htm): reveals an over-water timber walkway and overhead pergola, **not necessarily the same bridge**. Do not add its canopy to V60.
4. [Ronald Lu & Partners, designer](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/): identifies intentionally **offset suspended bridges and staircases** across an academic campus. This forbids treating plan overlap with ground paths as access.
5. [RLP design feature](https://www.sohu.com/a/246378126_803109): glazed, raised LRC volume and sloped shading fins are building details, not automatic evidence for V52 bridge windows.
6. [RLP extension photographs](https://architizer.com/projects/beijing-normal-university-hong-kong-baptist-university-united-international-college/): confirms glazed teaching facades/open-air circulation, but no exact V52 identification.
7. [BNBU T2 frontage](https://mpro.bnbu.edu.cn/info/1086/4347.htm): helps identify T2 massing, not a door or pane measurement.
8. [BNBU LRC description](https://www.bnbu.edu.cn/en/info/1077/2974.htm): explicitly identifies library glass windows, not window partitions on a bridge.
9. [720yun campus panorama scene directory](https://www.720yun.com/t/gapjawo88mt6wm27i9?pano_id=9hDEsEqYJ66W0pX3): potential multiview control for T1–T8/lake; **scene labels only**, not registered photographs.

**Source exclusions:** the University of Illinois Chicago and Hong Kong's Chu Hai College are unrelated institutions; their glass bridge photographs must not be reused. The campus's own rendered buildings are not automatically architectural as-built photography. Photo links are preserved; copyrighted photographs are not bundled.

## Real changes in this iteration

- \`build_bridges_v75.py\` imports the model-triangle surface sampler from \`audit_connections_v74.py\`, computes all V52 envelopes and 12 independently identified bridge ends, and records uncertainties in \`BNBU_v75_BRIDGE_COMPONENT_ATLAS.json\`.
- \`BNBU_v75_BOARDWALK_GLASS_INFILL_DISPLAY_ONLY.glb\` is an **entirely separate** optional rendering component attached in the viewer under the inherited source \`world\` coordinate root. Its source xy follows the existing V70 railing polyline; drawn bottom/top fractions are **illustrative** (0.10/0.80 model units above deck). Its two continuous strips have no fabricated pane seams.
- The viewer lists **seven distinct bridge systems** and displays their inherited components, 12 end-height samples and missing window/door evidence. V60 glass infill is independently toggleable.
- **No glass is added** to any of the six V52 slabs without a matching bridge photograph and true window envelope.
- The original \`BNBU_v71_CONNECTED_LAKEFRONT.glb\` and v74's 47 location-specific junction hotspots are retained without destructive edits. None of the visual meshes enters bird strike risk geometry.

## Stop / go conditions for a future *physical* bridge-window reconstruction

For each separate span: (1) locate the same bridge in at least two independent photographs and show recognizable fixed features; (2) identify the exact deck edge and the near/far building end; (3) estimate/measure glass lower/upper elevation, opening vs fixed pane, door threshold, support/roof type; (4) compare triangulated local deck Z at both ends, not overall mesh maximum; (5) preserve gaps crossing ponds and overhead paths until the grade and real crossing are independently verified; (6) run an isolated model diff and browser screenshot tests; (7) keep uncertainty flags and **never assert surveyed glass area** from rendering polygons. This also applies to the dozens of v74 non-bridge junctions, not just the lake crossing.

The defensible next outcome is not a screenshot made attractive with arbitrary 690+ fake windows. It is an auditable, progressively registered architectural reconstruction.
