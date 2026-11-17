# Intervention evidence matrix: glass, vegetation and mitigation

**Purpose:** compare interventions by the mechanism they address and the evidence needed to justify them. This is not a product endorsement, a BNBU efficacy estimate or an installation authorization.

## 1. Diagnose the glass before choosing a treatment

| Glass/scene condition | Mechanism to test | Measurements required | Candidate interventions |
|---|---|---|---|
| Clear transparent glass | Through-glass false passage; visible habitat behind the pane | Bird-facing exterior views, transmitted scene, VLT, pane extent and approach direction | Complete-pane exterior visual markers; interior blinds/plant repositioning only as supplementary measures |
| Highly reflective glass | Specular reflection of trees, sky or habitat | Exterior VLR, reflected scene, solar azimuth/altitude, view direction, cloud and time-of-day variation | Exterior visual markers; external shading/screen if measured reflection geometry supports it |
| Reflective and transparent | Both reflection and false passage may occur | Separate reflected and transmitted scene measurements | Exterior markers first; external shading for reflection and interior blinds for transmission are separate candidate mechanisms |
| Tinted or low-E | A product label alone does not identify the bird-visible hazard | Full insulating-glass-unit build, coating position, exterior VLR/VLT and actual reflected/transmitted scene | Defer until the optical pathway is measured; then compare surface-appropriate treatments |
| Fritted or patterned | Existing pattern may be incomplete, poorly spaced, low contrast or hidden on the wrong surface | Surface number, full-pane coverage, component shape/area, clear gaps, contrast, low-E position and viewing conditions | Verify the existing pattern; repair/complete it or upgrade only after checking the actual criteria |
| Opaque spandrel | No through-glass passage, but a reflective opaque surface may still create a mirror cue | Exterior reflectance, gloss, material/build and bird-facing scene | Assess reflection and material; do not automatically classify every opaque spandrel as safe |

A pane's appearance changes with illumination and approach angle. A single daytime photograph or a manufacturer's generic product label is insufficient.

## 2. Keep ECCC guidance separate from ABC Threat Factor rating

### Environment and Climate Change Canada (ECCC) general guidance

The ECCC guidance recommends that a visible pattern:

- cover the entire glass surface;
- be applied to the exterior surface;
- have no clear spaces greater than 5 cm horizontally or vertically;
- use components at least 5 mm wide;
- contrast clearly with the reflected vegetation and remain visible.

ECCC reports a 95% reduction in its tested configuration. That result belongs to the tested configuration and is not a universal efficacy coefficient for every glass type, species assemblage, illumination condition or BNBU building.

### American Bird Conservancy (ABC) 2025 Prescriptive Rating

ABC's Threat Factor is a rating of specified glass assemblies and pattern configurations, not a direct estimate of the percentage reduction at a particular site. The prescriptive criteria distinguish surface 1 from surface 2, account for low-E coating position, and impose material, marker geometry/area and spacing requirements. For relevant surface-2 assemblies, exterior visible-light reflectance must be no more than 15%; surface-1 criteria differ.

The 2025 option includes different 2x2 and 2x4 pattern criteria. For example, the 2x4 option distinguishes continuous-line spacing from shape spacing and specifies minimum shape area as well as horizontal, vertical and diagonal gaps. A simple “dot diameter” or “gap” check is not a complete ABC rating.

**Code boundary:** `birdglass/glazing.py` checks recorded pane coverage, exterior placement, contrast, spacing and component width. The 2x2 status is an ECCC-style general-guidance screen. The 2x4 status is spacing geometry only. Neither computes an ABC Threat Factor or certifies all material, geometry, gloss, coating and complete-assembly requirements.

## 3. What field evidence supports

| Study | Design and sample | Reported finding | Correct interpretation |
|---|---|---|---|
| China national study (2025), DOI 10.1016/j.biocon.2025.111375 | Citizen-science collision observations from 3,078 buildings, 2021–2023 | Migratory, non-predatory and lower-body-mass species were more likely to be recorded as casualties. Vegetation-cover associations were positive across scales and stronger at 1 km/10 km, while trees within 5 m were associated with lower collision occurrence, especially in fall. ALAN within 100 m was more strongly associated than larger buffers; the overall ALAN effect was marginal and season-dependent. | Supports explicit species, season, local-canopy and landscape-scale interactions. It does not justify one universal vegetation coefficient, tree removal or a BNBU causal effect. |
| Ottawa study (2026), DOI 10.1016/j.biocon.2026.112118 | Standardized spring/fall façade surveys in 2024–2025; 225 collisions, 51 species; 197 at untreated and 28 at treated façades | Treatments meeting guidelines had a significant negative association with collision risk (β = −2.18, SE = 0.74, p < 0.01); non-compliant treatments did not differ significantly from untreated façades (β = −0.38, SE = 0.31, p = 0.23). Model-derived no-treatment comparisons suggested 70.1% and 96.0% reductions for non-compliant and compliant treatments respectively, but significance was mixed depending on incidental records. | Strong support for complete, guideline-conforming treatments. The model-derived percentages are not randomized BNBU efficacy estimates. Raw data are available on request. |
| Oklahoma field study (2026), DOI 10.1093/ornithapp/duag047 | BACI design; 6 treated façades on 2 buildings and 134 untreated façades; exterior white dots at 5.1 × 5.1 cm spacing | Descriptive adjusted collision rates at treated façades declined by about 67%; untreated façades increased 15.7%. The formal treatment × period interaction was not statistically significant (p = 0.16; β = −1.47 ± 1.05), with only six treated façades. | Useful real-world intervention and BACI design benchmark, but not a definitive causal effect size. |

## 4. Conditional intervention comparison

- **Clear or reflective glass without a verified pattern:** complete-pane exterior markers are the best-supported first candidate for site review. Check bird-facing contrast and full coverage.
- **Existing pattern that passes only a 2x4 spacing screen:** consider a more conservative 2x2 arrangement where local small-bodied birds or high approach activity are supported. Do not claim an incremental effect size without field comparison.
- **Strong measured reflection:** compare exterior markers with external shading/screens using multi-time, multi-angle scene measurements. Preserve daylight, ventilation, human safety and structural constraints.
- **Measured through-glass false passage:** interior blinds or moving indoor plants may be supplementary, but do not remove exterior mirror reflection.
- **Measured nocturnal migrant activity plus measured artificial light:** consider seasonal lighting controls. This is a separate pathway from daytime glass transparency/reflection.
- **External screens or cords:** conditional alternatives when marker films are infeasible; assess entanglement, stand-off, wind load, fire/egress, maintenance and transfer of contact to frames or adjacent panes.
- **UV-only treatments:** defer until local species and spectral visibility are assessed in shade, overcast and low-light conditions. UV visibility is not universal.
- **Vegetation removal or pruning:** do not recommend from cover percentage or report density alone. Require route, reflection, resource-use and ecological-impact evidence.

## 5. Multi-scale vegetation is not one score

The model retains five nested buffers: 0–5 m, 5–25 m, 25–100 m, 100 m–1 km and 1–10 km.

| Scale | Features to retain | Potential pathway |
|---|---|---|
| 0–5 m | nearest crown, canopy height, pane-height overlap, reflected foliage, fruit/food resources | immediate reflection, attraction, route initiation or obstruction |
| 5–25 m | tree lines, shrub layers, façade adjacency, courtyard corridors | local route generation and approach direction |
| 25–100 m | connected canopy, water/green-space edge, open gaps | local movement network and alternative routes |
| 100 m–1 km | landscape green cover, water, urban density and night lighting | landscape availability and movement context |
| 1–10 km | broader green-space and habitat distribution | regional context, not direct pane-level exposure |

The China study is especially important because its near-building and landscape-scale vegetation associations differ. A single monotonic “more vegetation = more risk” or “more vegetation = less risk” rule is scientifically indefensible.

## 6. What is required before ranking effectiveness for BNBU

The model's intervention comparison reports mechanism match and evidence requirements; it deliberately does not output a best product or a local percentage reduction. A defensible ranking requires:

1. stable pane IDs and measured glass, scene and vegetation features;
2. all at-risk approaches through a defined pane-specific risk gate;
3. independent labels for glass contact, opaque contact, no contact and right-censoring;
4. equivalent survey effort and, for ground searches, carcass-persistence and searcher-efficiency correction;
5. matched panes or randomized/stepped-wedge before-after control-impact monitoring;
6. outcomes per comparable approach and per façade-time, including secondary contact or injury where measurable;
7. installation cost, maintenance, daylight/view, wind/structure, fire/egress, entanglement and ecological side effects.

Only after these are available should the project estimate treatment effects and a multi-objective Pareto frontier.

## Sources

- ECCC, [Frequently Asked Questions on Bird Collisions with Glass Windows](https://www.canada.ca/en/environment-climate-change/services/avoiding-harm-migratory-birds/faq-bird-collisions-glass-windows.html).
- American Bird Conservancy, [The Prescriptive Rating Option, updated 17 November 2025](https://abcbirds.org/wp-content/uploads/2025/12/the_prescriptive_rating_option_11_17_2025.pdf).
- China 2025, [Scale-dependent effects of urban vegetation and artificial lights at night on bird-building collisions in China](https://doi.org/10.1016/j.biocon.2025.111375).
- Lysyk et al. (2026), [Evaluating the efficacy of window treatments to prevent bird–window collisions](https://doi.org/10.1016/j.biocon.2026.112118).
- Riding et al. (2026), [Window markers reduce bird–window collisions in a real-world application](https://doi.org/10.1093/ornithapp/duag047); [Zenodo data and code](https://zenodo.org/records/20058828).
- Van Doren et al. (2021), [PNAS, DOI 10.1073/pnas.2101666118](https://doi.org/10.1073/pnas.2101666118).
