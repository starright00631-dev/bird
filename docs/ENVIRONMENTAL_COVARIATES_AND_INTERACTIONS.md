# Environmental and biological structure for bird–window collision risk

## Purpose

This document defines environmental covariates and interactions that belong in the model. It is not a BNBU vegetation inventory, species list, or façade survey. Campus-specific tree identities, bridge planting, glass area and flight corridors remain unknown until supported by attributable photographs, botanical records or field measurements.

The prediction unit is a **species (or explicitly pooled ecological guild) × approach event × pane × time window**. A building-level collision count is an aggregated outcome, not the primitive risk unit.

## 1. Causal decomposition: do not collapse unlike mechanisms

For species s, pane p and time t:

    expected true contacts[p,s,t]
      = bird_flux[s, local_airspace, t]
      × P(route enters pane approach volume | s, habitat, weather, t)
      × P(contact | approach, glass appearance, species vision, flight state)

Observed records add separate injury, persistence, search and reporting processes.

The same covariate may affect multiple stages through different paths. Vegetation can change bird abundance and local activity; redirect or obstruct flight paths; become a reflected scene in a pane; and change the background radiance against which glass markings are viewed. Those paths must be represented separately. Do not assign vegetation one positive or negative coefficient and call it a collision mechanism.

## 2. Species representation: hierarchical, not one model per rare species

Every species record should retain a scientific name, taxonomic authority/version, identification confidence and source. Common names alone are not stable join keys.

Species fields should include:
- residency and seasonal status: resident, partial migrant, passage migrant, winter visitor, breeding visitor;
- migration timing and nocturnal/diurnal tendency;
- habitat and foraging guild: canopy, shrub/understory, ground, open/aerial, water-associated, generalist;
- flocking/social tendency and territorial/reflection-directed behaviour, where observed;
- body mass, body length, wing chord, hand-wing index and independently sourced manoeuvrability proxies;
- visual system: UVS/VS class only where supported, cone sensitivities, ocular media and acuity source;
- juvenile/adult and age uncertainty.

Do not infer wingspan from AVONET wing chord. Do not infer visual sensitivity from taxonomic proximity alone. Do not label a species a BNBU collision species merely because it is regionally common.

Use partial pooling:

    species_effect[s] ~ Normal(guild_effect[guild(s)], sigma_species)

Guild effects can be estimated when there is sufficient independent sample size. Species-level deviations should shrink toward the guild mean when data are sparse. If a species has no glass-approach evidence, its behavioural glass-recognition parameter remains unestimated; morphology alone does not supply it.

For initial southern-China candidate coverage, query regional occurrence data before selecting focal taxa. Candidate guilds include resident urban/woodland passerines, shrub/edge foragers, canopy insectivores, open-ground foragers, water-associated birds and nocturnal migrants. These are sampling strata, not assertions about BNBU records.

A species becomes a focal taxon only when it has (a) reliable regional seasonal occurrence evidence and (b) a useful mechanism or adequate collision/approach sample. Otherwise retain it in a pooled guild or as a scenario.

## 3. Time structure: three nested clocks

### Annual / seasonal
Represent local phenology using species-specific occurrence and abundance curves, not a fixed four-season multiplier. In subtropical southern China, candidate periods to investigate include spring passage, breeding/juvenile dispersal, autumn passage and winter residency. Their dates must be inferred from regional weekly occurrence data; North American season coefficients must not be copied.

### Daily
At minimum distinguish pre-dawn/night, dawn, morning, solar noon, afternoon and dusk. The boundaries should be solar-time or data-driven bins, not fixed clock hours.

### Event-scale
For each approach, preserve timestamp, cloud/precipitation, visibility, wind speed/direction, solar altitude/azimuth, pane orientation and bird heading. The optical state can change within one day.

Do not use collision reports' date alone as evidence of the time-of-day mechanism. Opportunistic reports with no approach denominator cannot identify hourly risk.

## 4. Vegetation: four distinct pathways and multiple scales

### 4.1 Local feature representation

For each pane, use georeferenced vegetation observations or remote-sensing layers to calculate:
- distance to nearest tree/shrub crown and canopy edge;
- canopy height and vertical overlap with the pane;
- crown width, gap width and line-of-sight obstruction;
- leaf-on/leaf-off or evergreen/deciduous phenology;
- flowering/fruiting period only when species-level botanical evidence exists;
- patch area, perimeter/edge density and connectivity;
- visible vegetation solid angle from bird-approach viewpoints;
- whether vegetation is geometrically available as a reflected or transmitted scene.

Tree species is not a substitute for crown geometry or phenology. Plant labels should include taxonomic confidence and date.

### 4.2 Spatial scales

The 2025 China study (3,078 buildings, 2021–2023) tested local and landscape vegetation at different scales and found associations that differed by scale; it reported a negative association for trees within 5 m, while vegetation cover at larger 1 km and 10 km scales was positively associated. These are observational associations, not proof that planting trees within 5 m is protective or that removing distant green space reduces collisions.

Use pre-registered nested buffers such as 0–5 m, 5–25 m, 25–100 m, 100 m–1 km and 1–10 km as a sensitivity grid, not as biological thresholds. Fit continuous distance/area functions or penalized splines and test whether conclusions survive alternative buffer widths. Avoid entering highly collinear nested percentages as independent unconstrained predictors.

### 4.3 Separate causal pathways

1. **Attraction / abundance:** vegetation → food/shelter/resources → local bird flux.
2. **Flight routing:** vegetation edges/gaps → route distribution and approach frequency.
3. **Optical scene:** vegetation geometry → reflected/transmitted habitat radiance.
4. **Visibility / obstruction:** vegetation occludes or opens approach views and changes escape options.

The same vegetation patch may increase flux but decrease direct approaches to one pane. Estimate total risk as the product/sum of these pathways, not as a direct green-percentage score.

## 5. Solar and glass appearance: implemented refinement

The new birdglass/solar.py module adds:
- timezone-aware solar azimuth and altitude in local East-North-Up coordinates;
- pane-normal / sun-vector specular reflection geometry;
- angular mismatch between the predicted specular direction and a bird's direction from the pane.

This is a geometric eligibility calculation only. A specular alignment does not imply a bright reflection, habitat-like appearance, bird recognition failure or collision.

The physically relevant next layer is radiometry:

    L_eye(lambda, t, direction)
      = R(lambda, incidence, polarization, glazing) * L_scene_reflected
      + T(lambda, incidence, glazing) * L_scene_transmitted

Required measurements include whole-assembly spectral reflectance/transmittance, direction-matched HDR or calibrated radiance of reflected and transmitted scenes, cloud/diffuse irradiance, pane orientation, and bird-viewpoint geometry. Single-interface Fresnel reflectance is not a substitute for a coated/double-glazed assembly.

The 2020 zebra-finch experiment on lighting conditions (100 captive birds) found that the effect of stronger reflection differed between morning and midday and was not a simple monotonic “more reflection = more collisions” relationship. This is a reason to model interactions and test them, not to assume a universal morning effect.

The current solar kernel deliberately does not apply atmospheric refraction, terrain horizon, cloud attenuation, glass BRDF or spectral response. Those are subsequent modules requiring measurements.

## 6. Weather and light: avoid double-counting

Weather may affect migration intensity and bird flux; flight speed/route and visibility; optical scene and diffuse/specular balance; and detection/reporting conditions during surveys.

Create distinct variables for these pathways. A single weather score creates confounding and double-counting. At minimum record cloud fraction/sky condition, precipitation/fog, visibility, wind vector and solar irradiance at event time when available.

Artificial light at night is a separate exposure mechanism from daytime solar reflection. It should interact with nocturnal migrant activity and weather, not be used as a generic building brightness coefficient.

## 7. Candidate data sources and limits

| Source | Useful fields / model role | Limitation |
|---|---|---|
| China 2025, DOI 10.1016/j.biocon.2025.111375 | 3,078 buildings; species, season, glass, ALAN and vegetation at multiple scales; ecological hypotheses | Individual-level raw data are on request; observational associations only |
| Species/phylogeny collision work, DOI 10.1002/ece3.9974 | Species abundance, migration timing and foraging strategy; supports abundance-adjusted species comparisons | Verify exact publication metadata before ingest; geographic/monitoring differences |
| Finnish ringing dataset, Dryad DOI 10.5061/dryad.z8w9ghxwm | Species-season collisions with ringing denominators; species vulnerability priors | Boreal ecology; ringing is not a random population sample |
| eBird Status & Trends | Weekly species relative abundance and seasonal occurrence priors | Grid abundance is not façade approach flux; access/terms and local calibration required |
| AVONET, DOI 10.1111/ele.13898 | Body mass, wing chord, hand-wing index, habitat/lifestyle | Not wingspan, visual sensitivity or direct collision behaviour |
| Håstad & Ödeen 2014, DOI 10.7717/peerj.621 | Species-specific spectral sensitivity context | Does not supply measured collision-avoidance probability |
| Swaddle et al. 2020, DOI 10.5751/ACE-02167-170203 | Time-of-day × lighting experimental interaction | Captive zebra finches; not direct wild-site coefficient |
| Samuels et al. 2022, DOI 10.7717/peerj.14604 | Real glass approaches, speed, angle, near-miss and contact context | 38 selected events; not a random approach denominator |

## 8. Model and validation sequence

### Experiment ENV-1 — multiscale vegetation
Outcome: standardized collision counts or presence under known survey effort, not raw opportunistic submissions.
Baseline: glass area, building height, site and season.
Added blocks: local crown geometry; intermediate habitat; landscape green cover.
Test: held-out buildings and held-out sites; compare predictive log score, calibration and stability of scale effects. Include abundance/effort where measured. No causal tree-removal interpretation from observational coefficients.

### Experiment ENV-2 — solar-reflection eligibility
Outcome: whether a measured reflected scene aligns with a bird approach direction and whether the optical cue is present in calibrated radiance.
Baseline: pane geometry and static material class.
Added block: solar position, pane normal, reflected-scene geometry, cloud/irradiance and measured glazing spectra.
Test: independently timestamped HDR/photometric observations across pane orientations and times. The geometry kernel must first pass analytic mirror-law tests; behavioural prediction is a later gate.

### Experiment ENV-3 — species/guild transfer
Outcome: approach-to-contact or avoidance on complete, independently reviewed glass-approach videos.
Baseline: pooled behaviour model.
Added block: hierarchical guild and species traits, with uncertainty in taxonomy and trait measurements.
Test: leave-bird, leave-building, leave-season and leave-species where sample size permits. Selected camera-triggered videos must not be treated as population prevalence.

### Experiment ENV-4 — integrated exposure
Only after preceding components are supported:
    pane risk = species flux × route-to-pane probability × conditional contact probability
Then propagate injury and observation models separately.

## 9. BNBU-specific evidence gate

T8–T29, T4–T8 and V16 must not be treated as interchangeable locations or assumed to share a bridge, plantings or glass type. No tree species, planting bed, pane dimensions or bird corridor may be populated from generic imagery.

For any eventual site case, each vegetation object requires a source image/survey ID, date, position/uncertainty, taxonomic confidence and crown dimensions. Each glass object requires a source image/measurement, pane ID, orientation, dimensions, material evidence and confidence. If a feature is not visible or measured, retain it as unknown.

## 10. Decision rule

Add a covariate or algorithm only if:
1. its mechanism is specified;
2. an actual source can measure it;
3. it is not a proxy for a different causal stage;
4. a falsifiable ablation can test its incremental value;
5. validation is blocked by building/site/time/individual as appropriate.

The objective is not to include every imaginable factor. It is to represent factors that change the probability of a specific bird approaching and contacting a specific pane, while keeping unmeasured mechanisms explicitly uncertain.
