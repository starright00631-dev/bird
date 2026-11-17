# BNBU Bird–Glass shared coordination log

Last checked: 2026-11-17  
Authoritative integration branch: main  
Repository: starright00631-dev/bird

## Working agreement

1. main is the shared source of truth; new work must use a feature branch and pull request targeting main. Do not push unreviewed research changes directly to main.
2. Read this log and README.md before adding a second implementation of an existing module.
3. Keep one canonical feature schema, source registry and test suite. Other BNBU Bird–Glass conversations must use the repository and this log as the handoff surface rather than maintaining separate incompatible copies.
4. Before starting duplicate work, record the current task, changed files, source pins, test state and open blockers here. Update the log when handing work to another conversation.
5. Do not merge a model result merely because another chat reports it. Require code, pinned inputs, executable tests, a reviewed PR diff and a reproducible result file.
6. Never treat synthetic records as external validation or local BNBU evidence.

## Confirmed main-line state

- birdglass/decision.py is version 0.2.0 and returns a pathway profile plus intervention_comparison. It compares mechanism fit and evidence needs; it does not estimate intervention efficacy or select a best option.
- The mechanics, optical geometry, solar geometry, observation-identifiability, approach-event and multi-scale vegetation modules are present.
- The main README had references to two absent documents and the data registry had a missing newline between BNBU and Oklahoma entries. This update adds the referenced audit/evidence documents and repairs the registry.
- PR #14 is an independent Draft branch and is not the main integration target.

## External-data work added

- De Groot et al. Dryad/Zenodo UBC dataset: all six source files are downloaded and checksum-verified in the CI artifact; only Search.Efficiency.csv is committed as a small source snapshot. The audit verifies 8,846 collision rows, 8,831 facade-date keys, 152 fatality events, 142 positive visits, 103 persistence trials, 29 search-efficiency trials, 155 scheduled dates and 303 point-count species rows.
- Zulian et al. 2023 Appendix 1: downloaded and pinned to SHA-256 0baba75389249af1dad546868183f956dd38facef64ae35b04ab761e293fd8a7; complete 8,835-row panel with 57 façades x 155 dates, 142 positive mortality visits and 152 events. It is the primary panel for the 2023 seasonal façade model.
- The UBC data are an external temperate-Pacific transfer benchmark, not BNBU calibration truth.
- Search-efficiency histories and carcass-persistence trials are observation-process data. They must not be used as collision labels.
- The UBC De Groot and Zulian datasets are separate products; do not join them without verified row keys and grain.

## Current handoff (2026-11-17)

- The UBC Search.Efficiency.csv snapshot on main matches the published 1,766-byte Zenodo checksum. The remaining five De Groot files are now fetched and checksum-verified in the 30-day CI artifact, not committed as raw files.
- This PR adds a pull-request workflow that fetches and checksum-verifies all six De Groot files in an ignored CI directory, plus downloader fail-closed tests.
- Independent BNBU Bird–Glass conversations should use this log for handoff. Separate ChatGPT conversations are not continuously visible to one another; GitHub is the durable shared coordination surface.

## Current handoff (2026-11-17)

- PR #17 is merged as 841af682. Post-merge CI passed: 157 tests passed, 1 skipped; UBC source audit verified all six De Groot files and the UVic source audit completed.
- The main branch has also added pinned UVic searcher-efficiency and carcass-persistence trial ingestion. This PR inspects the separate De Groot READ.ME.xlsx codebook before any field mapping is attempted.

## Immediate next tasks

1. Audit the reproducible Zulian seasonal GLMM outputs, DHARMa diagnostics, predictor collinearity and leave-one-building-out results; do not treat the UBC benchmark as Guangdong calibration.
2. Keep De Groot's 8,846-row source as a separate observation-process/version benchmark. A full GenEst/JAGS refit and source-version sensitivity analysis remain separate from the Zulian outcome panel.
3. Develop an independently validated subtropical transfer dataset with comparable façade survey effort, explicit zeros, glass area/type, multi-scale vegetation and observation-process metadata.
4. Add site/time-block validation only when additional independent sites or time windows support it; eight buildings at one campus do not establish external generalization.
5. Compare nonlinear challengers only after the interpretable GLMM baseline, uncertainty and group-aware validation are reproducible.
6. Localize BNBU only with measured pane/façade features and standardized monitoring; never manufacture negative examples from the 48 opportunistic reports.

## Status language

Use identified, downloaded, checksum_verified, schema_audited, model_fitted and externally_validated as separate states. Do not call a source integrated when only its landing page or metadata has been read.


## UBC source audit update (2026-11-17)

- All six De Groot files now pass pinned MD5/byte checks in CI; the five non-committed files are retained in the ubc-de-groot-verified-source-snapshot artifact for 30 days.
- The audit confirms 8,846 raw collision rows, 8,831 facade-date keys, 152 fatality events, 142 positive facade-date visits, 8,694 explicit zero rows, 15 repeated facade-date groups and four missing keys in the full cross-product.
- Search schedule: 155 dates, five periods, 225 monitoring days, all eight buildings scheduled on every date.
- Searcher efficiency: 29 trials; carcass persistence: 103 trials (85 finite intervals, 18 right-censored); point counts: 303 species rows in 86 checklists.
- The codebook is inspected; the 50-m VEGE_PERC is building-level and is not interchangeable with the 2023 façade-level TreeCov or StorReflVeg.
- Zulian Appendix 1 is now pinned and audited as the primary 8,835-row survey panel. Its feature mapping is FACADE_AREA, AREA_GLASS, PERC_VEG_AND_POROUS_SURFACE_FACADE, TREECOVER_FACADE_PERCENT and STORIES_REFLECT_CANOPY. Do not use building-level VEGE_PERC as the façade-level VegPer feature.


## Zulian façade covariate ingestion (2026-11-17)

- Added a separate downloader/schema inspector for the ACE-ECO Appendix 1 CSV from Zulian et al. (2023).
- Appendix 1 is a complete 8,835-row repeated survey panel (57 façades x 155 dates), not a 57-row covariate table. The exact SHA-256 is pinned; no duplicate or missing facade-date keys remain.
- Do not row-join it to De Groot: both sources have 152 mortality events, but their date-level keys differ and eight common-key outcomes mismatch. Use Appendix 1 as the primary model panel and De Groot as a separate observation-process/aggregate cross-check.
- Cross-source reconciliation: the 57 façade keys match, but only 139 of 155 survey dates overlap; 7,919 facade-date keys are common, 916 are Appendix-only and 912 De Groot-only. Eight common-key mortality counts and 171 METHOD values differ. No row join is allowed. Next: reproduce the four seasonal GLMM candidate sets, log-hours offset, nested building/façade random effects and AICc ranking on Appendix 1 alone.


## Zulian seasonal façade model (2026-11-17)

- Appendix 1 is downloaded and SHA-256 pinned (`0baba75389249af1dad546868183f956dd38facef64ae35b04ab761e293fd8a7`), with 8,835 unique façade-date rows, 57 façades, 8 buildings and 155 survey dates. `COLLISIONMORTALITY_X` is the binary-presence source outcome plus a separately preserved count; `COLLISIONS_X` remains separate.
- The De Groot raw collision file is explicitly not row-joined to Appendix 1: 139 common dates, 16 dates unique to each source, 7,919 common façade-date keys, 8 mortality mismatches and 171 METHOD mismatches.
- Seasonal GLMM uses binomial-logit, `log(survey_hours)` offset (24/48 hours), and one composite `facade_id` random intercept. Candidate sets and parameter counts reproduce the paper's df: full=8, building-only=6, vegetation-only=5, null=2. ORs are reported per 1-SD predictor, not hand-set raw increments.
- CI seasonal AICc pattern: fall building-only; winter building-only with full ΔAICc 1.25; spring full with building-only ΔAICc 1.92; summer null with building-only ΔAICc 0.05. These are within-study model-support comparisons, not predictive validation or causal effects.
- All seasonal candidate models converged with positive-definite Hessians. CI on the branch passed 182 tests (1 skipped) and the pinned UBC source/model audit; raw and derived files are retained in a 30-day CI artifact, not Git.
- Independent review added two input-integrity checks: reject fractional METHOD codes rather than truncating to 1/2, and reject fractional `STORIES_REFLECT_CANOPY` counts. Dedicated regression tests cover both.
- Remaining limitations: carcass detection/persistence are not corrected at façade level; only eight temperate Pacific buildings; glass area is not optical glass type/spectra; LOBO is internal UBC transfer only; no BNBU calibration or intervention efficacy.

## Finite-pane optics PR #23 merged (2026-11-17)

- PR #23 merged as `ff7377b2c954be32d215bc96c7582088e441e77e`.
- `scene_ray` now checks both bird-to-pane and real-scene-source-to-pane occlusion legs; reflection checks the real source coordinate rather than the virtual image. Source-side reflection and transmission regressions were added.
- The change is geometric-only and makes no behavioral-recognition or collision-probability claim. Post-merge CI is being checked.
