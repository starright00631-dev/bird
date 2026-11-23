# Engineering and scientific completion gates

Repository status: **executable mechanistic research code plus an evidence-aware façade assessment prototype**. This is not yet a trained, site-calibrated BNBU collision model. The full archived historical simulator has only been partially migrated.

## Implemented components

### Mechanistic model

- Finite glass/opaque-structure first swept contact and deterministic first-hit attribution across adjacent faces.
- Arbitrarily oriented finite-pane reflection/transmission geometry, habitat virtual images, bird-facing angular footprint and solid angle.
- Measured-input spectral and species visual-response adapters; actual full-assembly spectral R/T remains an external measurement.
- Delayed heading/gap controller, reachability screening and full-structure collision checks.
- Paired full-façade counterfactuals with glass-to-opaque contact transfer and a non-deployment gate.
- Approach-event gates, right-censoring and observation identifiability.
- Source graph/leakage checks and a 2026 stereo-bird trajectory schema adapter.

#### Reproduce the paired-policy stress benchmark

From the checkout root, run `python scripts/reproduce_policy_stress.py --out-dir <directory>`.
The versioned synthetic fixture covers neighboring glass and opaque surfaces,
immediate and delayed recognition responses, and multiple integration step
sizes. `policy_stress.json` records both aggregate contact and per-pane
transfer, including opaque contact. `manifest.json` binds that result to the
exact synthetic input and simulation source bytes by SHA-256 and records the
Python and NumPy versions. The seed uses a fixed ordering of the glass pane
IDs. Keep the flight records in their original order to repeat the same draw
assignments.

The archived scenario, pane, reachability and intervention CSVs were imported
as outputs. Exact reproduction requires their original generators,
configuration, and evidence snapshots. The new stress fixture is independent
of those historical outputs and uses fictional geometry and assumed responses.

### Evidence-aware façade decision layer

- Typed `Measurement` and `EvidenceTier` values preserve units, provenance, uncertainty and missingness.
- Glass categories distinguish transparency, external reflection, low-E/tinted glass, fritted/patterned glass and opaque spandrel.
- Pattern screening checks coverage, surface, contrast, spacing and component width. The 2x2 status is an ECCC general-guidance screen; the 2x4 status is spacing geometry only. Neither computes an ABC Threat Factor.
- Vegetation retains five nested buffers (0–5 m, 5–25 m, 25–100 m, 100 m–1 km, 1–10 km) and separate attraction, routing, optical-reflection and obstruction pathways.
- Solar geometry computes approximate ENU solar position and geometric specular alignment, not radiance or bird perception.
- `evaluate_facade()` returns a multi-pathway profile, conditional recommendations, data gaps, identifiability and a mechanism-based intervention comparison.
- The intervention comparison does not rank efficacy or invent BNBU percentages. It distinguishes exterior markers, screens/cords, shading, interior blinds, lighting controls, vegetation management and UV-only options.
- Regression tests cover pattern screens, evidence tiers, censored approaches, glass/vegetation boundaries and intervention gates.

## Not yet implemented or calibrated

1. No DINOv2/ViT/CNN image pipeline for glass appearance classification.
2. No automatic crown segmentation, NDVI extraction or multi-buffer vegetation raster pipeline.
3. No harmonized external training table with comparable grain, survey effort, detection and zero/non-event observations.
4. No fitted hierarchical Poisson/negative-binomial GAMM/GLMM for façade collision rates.
5. No trained CatBoost, Random Forest or HistGradientBoosting challenger model.
6. No local causal/counterfactual treatment model or BNBU-specific intervention effect.
7. No pane-level BNBU geometry, measured full-assembly spectra or all-approach denominator.
8. No injury/fatality model; contact mechanics and collision counts are not injury outcomes.

## Open scientific blockers

- No independent 3D bird+obstacle+eye-direction tracks sufficient to calibrate recognition or visuomotor delay near glass.
- No independently observed denominator of all trajectories approaching each pane linked to verified contact/near-miss outcomes.
- No field-measured pane-by-pane spectral reflection/transmission registered against bird camera views for BNBU.
- Rigid keypoints do not reconstruct entire wing membranes, body compliance or fatality probability.
- BNBU's opportunistic reports lack standardized exposure and zero surveys; they are for localization and hypothesis generation, not training a rate model.

## Scientific order of operations

1. Acquire/harmonize external façade survey and treatment data with their effort/detection metadata.
2. Validate image and remote-sensing features against human-audited labels and held-out sites.
3. Fit interpretable count/rate models with exposure offsets and building/site/time structure.
4. Compare predictive challengers under bird-, façade-, site- and time-held-out validation.
5. Estimate intervention effects only from comparable field designs, then construct an uncertainty-aware multi-objective frontier.
6. Localize and calibrate the workflow to BNBU using verified pane geometry and field observations.

No replacement glass, universal UV efficacy or installation decision is authorized by simulation alone.
