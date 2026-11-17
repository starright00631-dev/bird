# BNBU bird–glass final model specification

**Purpose:** produce a pane-level, interpretable assessment of glass type, vegetation context and intervention options. The system is a multi-pathway decision model, not a single opaque risk score.

## 1. What the model must explain

For each verified façade/pane, the system keeps these pathways separate:

1. **Glass appearance and optics:** transparent/see-through, reflective/mirrored, tinted/low-E, fritted/patterned, frosted/translucent and opaque spandrel; exterior VLR/VLT; coating position; full-pane pattern geometry; reflected versus transmitted habitat.
2. **Vegetation structure:** five non-overlapping annular cover bands (0–5 m, 5–25 m, 25–100 m, 100 m–1 km, 1–10 km); façade-specific 50-m porous/ground-shrub and tree-cover percentages; building-level vegetation proportion; canopy height/distance and pane-height overlap.
3. **Vertical reflected-habitat context:** continuous STORIES_REFLECT_CANOPY. This is a potential vertical exposure variable, not proof that vegetation is visible in the pane.
4. **Measured optical scene:** reflected vegetation share and transmitted habitat share from bird-side views. Only measured/local-survey evidence triggers reflection-specific recommendations.
5. **Bird exposure and approach:** local activity by species/guild/season, all at-risk approaches through a defined pane-specific gate, glass/opaque contacts, no-contact and right-censored approaches.
6. **Observation process:** search effort, carcass persistence, searcher detection, censoring and reporting effort.
7. **Intervention:** exterior markers, screens/cords, shading, interior supplements, seasonal lighting and vegetation changes, with evidence, feasibility, cost, safety and ecological effects.

## 2. Canonical implementation

- birdglass/glazing.py owns GlassPanel, PatternSpec, assess_glazing and the conservative 2-D pattern screen.
- birdglass/vegetation.py owns the five non-overlapping bands and separate attraction, routing, reflection and obstruction pathways.
- birdglass/decision.py owns FacadeContext, evaluate_facade, approach-denominator identifiability and the intervention mechanism comparison.
- birdglass/glass_observation.py and birdglass/vegetation_observation.py are intake adapters into those canonical types. They do not duplicate the risk/decision rules.
- birdglass/facade_decision_report.py combines observations and attaches source IDs to canonical decision candidates. The machine-readable evidence mapping is data/reference/intervention_evidence.csv.
- birdglass/glass_image_classifier.py is optional CLIP photo triage pinned to an immutable model revision. Scores are relative logits, not probabilities; human review is mandatory.
- birdglass/vegetation_segmentation.py summarizes externally produced masks. It does not run segmentation inference. Every mask must retain source image, model/revision, CRS, pixel resolution and human-QA provenance.

## 3. Glass interpretation rules

| Observation | Interpretation | Decision rule |
|---|---|---|
| Clear transparent | Potential false-passage/see-through cue | Inspect from bird approach views; assess full-pane exterior markers |
| Reflective/mirrored | Potential external habitat reflection | Measure bird-side reflected scene across solar times/angles; markers are a candidate |
| Tinted/low-E | Optical behavior unresolved from label alone | Obtain full-assembly VLR/VLT/spectral R/T and coating position |
| Fritted/patterned | Treatment may reduce visibility risk, but geometry matters | Measure horizontal/vertical clear gaps, component dimension, surface and whole-pane coverage |
| Frosted/translucent | Not equivalent to clear glass; optical behavior still requires review | Do not infer safety from the label alone |
| Opaque spandrel | Transparency may be absent; reflectance still matters | Measure first-surface reflection and assess contact transfer to adjacent panes/frames |

The 5 cm by 5 cm, at-least-5 mm exterior pattern check is a general geometry screen, not ABC Threat Factor certification. Dot and line component dimensions are recorded separately; the component-only ABC geometry screen is not a full product rating. The 15% VLR boundary is an assembly/rating-specific review flag, not a universal biological hazard cutoff.

## 4. Vegetation interpretation rules

- Do not add or average cover percentages across spatial bands. Each band has its own denominator.
- Do not treat cumulative buffers as annular bands. The cumulative_cover_to_annular adapter converts them only when all five actual valid clipped areas are supplied, using area-weighted covered-area differences; missing/invalid areas fail closed.
- Keep façade-specific 50-m porous/tree cover separate from the five annular bands.
- Keep building-level VEGE_PERC separate from façade-level cover.
- Keep STORIES_REFLECT_CANOPY continuous; do not round it to an integer.
- Canopy presence plus a positive stories-reflecting-canopy value is only a potential context. Reflection-specific action requires measured reflected-scene evidence.
- High canopy cover alone never triggers tree removal. Attraction, routing, obstruction and optical reflection can act in different directions.

## 5. Model outputs and interpretation

The report returns:
- canonical glass assessment and pattern-screen status;
- five-band vegetation profile and separate façade/building/vertical variables;
- measured reflection/transmission pathways;
- approach/contact identifiability and its bounds;
- evidence-tagged intervention candidates and required checks;
- data gaps and validation scope.

The system does **not** return an absolute BNBU collision probability from glass type and vegetation proxies alone. A site prediction is accepted only as a ValidatedRiskPrediction with a pinned model artifact SHA-256, explicit endpoint and exposure definition, BNBU site calibration, held-out validation design and validation report ID. A bare probability is rejected.

## 6. External model evidence and current status

Zulian et al. (2023) Appendix 1 is the primary external façade association benchmark: 8,835 repeated façade-date rows, 57 façades, 8 buildings and 155 dates. The seasonal binomial GLMM uses the observed carcass-presence endpoint and a log survey-hours offset.

The paired building-cluster bootstrap resamples eight buildings 5,000 times. The pooled GLMM-minus-exposure-only Brier delta is +0.00531 (95% interval -0.00027 to +0.00988); log-loss delta is +0.01283 (-0.00433 to +0.02735). Positive deltas are worse. The external model therefore has not demonstrated predictive improvement over an exposure-only baseline on held-out buildings. It is retained for descriptive seasonal associations, not BNBU risk prediction.

The De Groot dataset is a separate source version and observation-process benchmark; it is not row-joined to Zulian. Its searcher-efficiency and carcass-persistence trials are not collision labels. GenEst pkm/cpm/estM reproduction remains a separate correction task.

## 7. Why BNBU calibration is not yet possible

The 48 opportunistic BNBU submissions can localize hypotheses but do not supply:
- systematic surveyed zeroes and comparable survey effort;
- a pane-by-time exposure denominator;
- continuous-video approach counts and glass/opaque/no-contact outcomes;
- local carcass-persistence and searcher-detection trials;
- a complete pane inventory with verified glass and vegetation measurements.

Therefore the current deliverable is an evidence-aware mechanism and intervention decision system. It must not be described as a trained BNBU collision probability model.

## 8. Minimum field protocol to finish BNBU calibration

1. Inventory each pane separately; record façade/pane ID, dimensions, glass appearance, coating position, VLR/VLT/spectral R/T, existing marker type and full 2-D geometry, source photo/spec and reviewer.
2. Measure vegetation in the five annular bands using one land-cover definition and resolution; separately record façade 50-m porous/tree cover, nearest crown, canopy height, sill height, STORIES_REFLECT_CANOPY and actual reflected-scene share.
3. Conduct repeated standardized façade patrols with date, time, effort, weather and explicit surveyed zeroes.
4. Use continuous video with a defined pane-specific risk gate to count all at-risk approaches, glass contacts, opaque contacts, no-contact and right-censored events.
5. Run local searcher-efficiency and carcass-persistence trials; correct collision observations only after validating the observation model.
6. Compare candidate retrofits with matched/randomized BACI; record installation compliance, cost, maintenance, daylight, safety, ecological effects and adjacent-pane risk transfer.
7. Train seasonal GLMM/GAMM baselines first, then compare ML challengers with grouped building/time holdouts. Calibrate only on BNBU data and retain uncertainty.

## 9. Intervention decision policy

- Exterior full-pane markers are the first candidate for confirmed untreated transparent/reflective glass, subject to pattern geometry, feasibility, safety and local bird guilds.
- Screens/cords are a conditional physical alternative; assess entanglement, stand-off, wind load, fire/egress, maintenance and contact transfer.
- Shading/solar screens are considered only after pane-specific reflected habitat is measured from plausible approach views.
- Lighting controls require measured nocturnal activity and artificial light; keep separate from daytime glass mechanisms.
- Interior blinds are supplementary for a measured transmitted false-passage pathway; they do not remove exterior reflection.
- UV-only film is deferred until local species and full-assembly spectral visibility are tested.
- Vegetation changes are never recommended from cover percentage alone; require route/resource/obstruction/reflection and ecological-impact evidence.
- No option receives a BNBU efficacy percentage or best-treatment ranking until comparable local intervention monitoring is available.
