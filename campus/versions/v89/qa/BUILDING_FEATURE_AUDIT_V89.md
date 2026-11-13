# BNBU v89 — building-by-building feature audit (audit-only)

Source GLB SHA256: `c7e043c96f6513782e3e9aececf62cfb5063f4e5ba23bcd5503cb7a8fb5dfe07`  
Source active mesh nodes: **1378**  
Inventory: **30 core + 8 mapped extensions = 38 mapped assets**, plus 1 unmapped official asset and 1 quarantined hypothesis.

## Critical findings

### V25_LOW_RESOLUTION_PRIMARY_MASS — HIGH

**Classification:** CONFIRMED_MODEL_RESOLUTION_OUTLIER; REAL-WORLD FEATURE ABSENCE REQUIRES PHOTO REGISTRATION

V25 is represented by a 62-vertex / 120-triangle primary mass with only base and roof Z levels; no intermediate story-edge components are present. Its height is 24.8 model units. This is a strong model-detail deficit relative to the other V-series primary meshes, not proof of the exact real facade design.

**Affected:** V25

**Next action:** Obtain V25-specific multi-view facade imagery and compare with the mesh before adding floor bands, balconies, openings or roof detail. Keep the current geometry unchanged until registered evidence exists.

### V_SERIES_FACADE_FEATURE_TYPE_GAP — HIGH

**Classification:** OFFICIAL_PHOTO_SUPPORTED_FEATURE_TYPE; INDIVIDUAL_BUILDING_ASSIGNMENT_UNRESOLVED

No V15-V29 record currently has a separately named transparent glazing, balcony or railing component. The official Phase-I dormitory exterior photograph shows repeated window bays, recessed balcony-like bays and guardrails across the residential blocks. The photo is not registered to an individual V building, so it establishes a family-level feature gap but not exact per-building geometry.

**Affected:** V15, V16, V17, V18, V19, V20, V21, V22, V23, V24, V25, V26, V27, V28, V29

**Next action:** Use the official V15-V29 hall pair mapping to identify each building, then gather facade-specific views. Segment the actual window/balcony bays per building; do not copy one facade pattern across all 15 buildings.

### T1_PHOTO_BACKED_GLAZING_OMISSION — HIGH

**Classification:** OFFICIAL_BUILDING_PHOTO_VS_CURRENT_COMPONENT_INVENTORY_MISMATCH

The official FBM page identifies its address as T1-602 and shows T1's facade with clear horizontal ribbon glazing and lower-level glazing. The current T1 component inventory has zero separately identified glazing-surface meshes. The photo is useful for facade type and feature presence, but is not a calibrated pane survey.

**Affected:** T1

**Next action:** Register the official T1 photo against the correct facade sector and existing V40 source mesh; recover continuous glazing bands and opaque frame/return geometry separately. Do not invent pane divisions or dimensions.

### V_SERIES_STORY_EDGE_COVERAGE_ASYMMETRY — HIGH_REVIEW

**Classification:** INVENTORY_ASYMMETRY; NOT YET A CONFIRMED PHYSICAL OMISSION

Only 8 of 15 V-series buildings have separately named V63 story-edge meshes. The other seven require a face-level check to determine whether floor-edge detail is embedded in the primary mesh or missing. V25 is the strongest outlier because its primary mesh has only two Z levels.

**Affected:** V15, V17, V19, V21, V23, V25, V27

**Next action:** Compare each building's source mesh at floor-height cross-sections and use building-specific photos to decide whether to reconstruct opaque story edges. Do not clone a sibling's bands blindly.

### T_SERIES_GLAZING_COVERAGE_ASYMMETRY — HIGH_REVIEW

**Classification:** EVIDENCE_GAP_AND_COMPONENT_COVERAGE_ASYMMETRY

Separate transparent glazing surfaces are uneven across T1-T8: T2 has 7, T3 has 3, T4 has 4, and T1/T5-T8 have none. The source naming also contains many GLASS-labelled opaque mullions, end jambs and head/sill returns; these are counted separately and must not be treated as transparent panes. Official T1 imagery is documented as showing long recessed glazing, but exact pane geometry is not registered. This is not a license to invent windows on other blocks.

**Affected:** T1, T5, T6, T7, T8

**Next action:** Build a per-building facade evidence matrix; register T1 imagery first, then source distinct T5-T8 views before making glass or window geometry. Keep opaque mullions/returns separate from glass surfaces.

### D_SERIES_FACADE_FEATURE_MAPPING_GAP — HIGH_REVIEW

**Classification:** EVIDENCE_SUPPORTED_FEATURE_TYPE; PER_BUILDING_MAPPING_UNRESOLVED

D1-D6 each contain a main mass, roof deck/roof field/frame, 12 roof cross-rib nodes and one inferred ground link. The current building component registry has no separately named glazing, balcony/rail or stair nodes for these six buildings. The official Phase-II dormitory exterior photo shows a deep recessed facade grid, repeated window/balcony bays, open guardrails and a prominent building-number panel, but the photo is not registered to a specific D1-D6 building.

**Affected:** D1, D2, D3, D4, D5, D6

**Next action:** Identify which official views correspond to each D building; map facade sectors and balconies only after image identity and pose are checked. Preserve the six distinct U/C-like plan masses rather than replacing them with a generic block.

### P2_LRC_LAB_COMPLEX_UNMAPPED — CRITICAL

**Classification:** CONFIRMED_OFFICIAL_BUILDING_WITHOUT_VERIFIED_MESH_MAPPING

The official Phase-II Learning Resource Centre and Laboratory Complex is absent from the mapped physical master. It must not be confused with the circular commons proxy. Official 2025 university material and Aedas project imagery describe a distinctive cubic composition with vertical fins, cantilevered/recessed volumes, a central glazed atrium, shared facilities and a sky garden.

**Affected:** P2_LRC_LAB_COMPLEX

**Next action:** Create a separate evidence package and locate the correct campus coordinates/scale and multiple views; do not insert a guessed mesh or re-label the circular commons.

### LRC_SKYLIGHT_CANDIDATE_SEPARATE — MEDIUM

**Classification:** OPTIONAL_UNSURVEYED_CANDIDATE_NOT_IN_DEFAULT_MASTER

The Phase-I LRC has 353 mapped components in the current atlas, including many facade/glazing and stair elements, but the optional 17,410-vertex / 34,816-triangle skylight shell remains in a separate unsurveyed candidate lineage rather than the default master.

**Affected:** LRC

**Next action:** Compare the optional candidate with the current LRC source, especially roof rim and arch ribs, then keep it separate until independent exterior views and alignment support promotion.

## Core-building inventory (all 30 checked at mesh/component level)

| ID | Official name | Family | Components | Triangles | Story-edge nodes | Glazing surfaces | Opaque frames/returns | Stairs | Cross-ribs |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| T1 | Business and Management Building | T | 24 | 1190 | 6 | 0 | 0 | 0 | 0 |
| T2 | Humanities Building | T | 89 | 5296 | 6 | 7 | 36 | 0 | 0 |
| T3 | Science Building | T | 58 | 3692 | 6 | 3 | 12 | 0 | 0 |
| T4 | Teaching Building T4 | T | 36 | 3156 | 5 | 4 | 8 | 2 | 0 |
| T5 | Teaching Building T5 | T | 22 | 2454 | 5 | 0 | 0 | 0 | 0 |
| T6 | Teaching Building T6 | T | 24 | 2718 | 5 | 0 | 0 | 2 | 0 |
| T7 | Teaching Building T7 | T | 22 | 2454 | 5 | 0 | 0 | 0 | 0 |
| T8 | CEFC Building | T | 26 | 2836 | 5 | 0 | 0 | 2 | 0 |
| V15 | Ming Xin House | V | 3 | 580 | 0 | 0 | 0 | 0 | 0 |
| V16 | Shang Xian House | V | 9 | 812 | 6 | 0 | 0 | 0 | 0 |
| V17 | Ren Ai House | V | 3 | 580 | 0 | 0 | 0 | 0 | 0 |
| V18 | Bao Pu House | V | 10 | 844 | 7 | 0 | 0 | 0 | 0 |
| V19 | Zhen Zhi House | V | 3 | 580 | 0 | 0 | 0 | 0 | 0 |
| V20 | Du Xing House | V | 8 | 780 | 5 | 0 | 0 | 0 | 0 |
| V21 | Bo Wen House | V | 3 | 556 | 0 | 0 | 0 | 0 | 0 |
| V22 | Ya Zhi House | V | 8 | 780 | 5 | 0 | 0 | 0 | 0 |
| V23 | Xue Qin House | V | 3 | 460 | 0 | 0 | 0 | 0 | 0 |
| V24 | Yang Ming House | V | 8 | 780 | 5 | 0 | 0 | 0 | 0 |
| V25 | Dong Po House | V | 3 | 188 | 0 | 0 | 0 | 0 | 0 |
| V26 | Goethe House | V | 9 | 812 | 6 | 0 | 0 | 0 | 0 |
| V27 | Hugo House | V | 3 | 676 | 0 | 0 | 0 | 0 | 0 |
| V28 | Shakespeare House | V | 9 | 812 | 6 | 0 | 0 | 0 | 0 |
| V29 | Yung Wing House | V | 9 | 812 | 6 | 0 | 0 | 0 | 0 |
| D1 | D1, Residence Cluster of Phase II Campus | D | 17 | 2328 | 0 | 0 | 0 | 0 | 12 |
| D2 | D2, Residence Cluster of Phase II Campus | D | 17 | 2128 | 0 | 0 | 0 | 0 | 12 |
| D3 | D3, Residence Cluster of Phase II Campus | D | 17 | 2128 | 0 | 0 | 0 | 0 | 12 |
| D4 | D4, Residence Cluster of Phase II Campus | D | 17 | 2136 | 0 | 0 | 0 | 0 | 12 |
| D5 | D5, Residence Cluster of Phase II Campus | D | 17 | 1744 | 0 | 0 | 0 | 0 | 12 |
| D6 | D6, Residence Cluster of Phase II Campus | D | 17 | 2128 | 0 | 0 | 0 | 0 | 12 |
| LRC | Phase I Learning Resource Centre | LRC | 353 | 22132 | 3 | 62 | 122 | 84 | 0 |

## Extended mapped assets

| ID | Display label | Components found | Triangles |
|---|---|---:|---:|
| T29 | T29 · Teaching Building Block 29 / T29教学楼 | 15 | 924 |
| ADMIN | Administration Building / 行政楼 | 8 | 216 |
| HALL | University Hall / 大学会堂 | 7 | 376 |
| SPORT | Sports Complex / 体育馆 | 7 | 376 |
| THEATRE | Performance Theatre / 表演剧场 | 6 | 226 |
| CC | Cultural Creativity Clusters / 文化创意群落 | 8 | 400 |
| YUZHAN | YUZHAN · model label, official identity unresolved | 6 | 152 |
| P2_CIRCULAR_COMMONS | Phase II circular commons · model label only | 11 | 30720 |

## Official Phase-I dormitory identity mapping

| Model IDs | Official building names | Official source |
|---|---|---|
| V15, V17 | Ming Xin House; Ren Ai House | [Scientific Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Scientific_Education_Hall/1.htm) |
| V16, V29 | Shang Xian House; Yung Wing House | [Moral Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Moral_Education_Hall.htm) |
| V18 | Bao Pu House | [Innovative Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Innovative_Education_Hall.htm) |
| V19, V20 | Zhen Zhi House; Du Xing House | [Global Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Global_Education_Hall.htm) |
| V21, V22 | Bo Wen House; Ya Zhi House | [Excellence Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Excellence_Education_Hall.htm) |
| V23, V24 | Xue Qin House; Yang Ming House | [Liberal Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Liberal_Education_Hall.htm) |
| V25, V28 | Dong Po House; Shakespeare House | [Literary Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Literary_Education_Hall.htm) |
| V26, V27 | Goethe House; Hugo House | [Wisdom Education Hall](https://sao.bnbu.edu.cn/campus/hostel_life/hostel_life/details_of_hall/Wisdom_Education_Hall.htm) |

## Photo-backed feature checks

| Source | What it establishes | What it does not establish |
|---|---|---|
| [Official T1 faculty page](https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm) | T1 identity and visible horizontal ribbon/lower-level glazing, projecting frames and warm cladding | Calibrated pane dimensions, exact mullion spacing or full facade registration |
| [Official Phase-I dormitory exterior](https://admission.bnbu.edu.cn/info/1734/1470.htm) | Repeated window bays, recessed balcony-like bays, guardrails and facade bands in the V dormitory family | Which exact facade belongs to each V15-V29 block |
| [Official Phase-II dormitory exterior](https://admission.bnbu.edu.cn/info/1734/1469.htm) | Deep recessed facade grid, repeated window/balcony bays, open guardrails and building-number panel | Exact D1-D6 assignment, dimensions or as-built elevations |
| [Official Phase-II LRC/Lab announcement](https://www.bnbu.edu.cn/en/info/1076/12578.htm) and [Aedas project page](https://www.aedas.com/en/project/learning-resources-center-at-beijing-normal-hong-kong-baptist-university-bnbu-no-2-campus/) | Distinct cubic massing, vertical fins, central glazed atrium, recessed/cantilevered volumes and sky garden | Surveyed coordinates, final as-built geometry or exact mesh transform |

## Interpretation and next iteration

This is a read-only inventory audit, not a claim that all buildings are complete. The highest-value next geometry work is: (1) reconstruct a source-backed model for the official Phase-II LRC/Lab Complex; (2) diagnose V25's low-resolution primary mass; (3) resolve the V-series story-edge coverage differences and missing facade feature types; (4) recover T1 glazing against its official photo, then build per-building T-series facade maps; and (5) map D1-D6 balconies, railings and entrance/circulation features from building-identified views.

**Classification rule:** transparent glazing surfaces are counted separately from opaque mullions, frames, jambs, transoms and head/sill returns. A component name containing GLASS is not sufficient to count it as a glass pane.

No physical geometry was changed in v89. All candidate repairs must be reversible and pass source-hash, topology, transform, and browser tests.