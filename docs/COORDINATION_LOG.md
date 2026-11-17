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
- Zulian et al. 2023 Appendix 1: identified as the 8,835-row façade-survey risk set, but the raw CSV has not yet been downloaded or verified.
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

1. Download and checksum-verify Zulian Appendix 1; verify its 57 façade rows, keys and covariate definitions before joining.
2. Build the façade-date panel from the 8,846 De Groot collision rows, preserving 152 events, 142 positive visits, explicit zeros and four missing facade-date keys.
3. Fit the paper-aligned seasonal binomial mixed-effects baseline with façade/building grouping and the survey-interval exposure term; separately retain a count model for event counts.
4. Test multicollinearity and the eight-building clustering limitation before interpreting VegPer, TreeCov, StorReflVeg, AreaGlass or FacArea effects.
5. Use grouped building/façade/time holdouts; compare GAMM, Random Forest and HistGradientBoosting only after the baseline is reproducible.
6. Use the external temperate campus as a transfer benchmark, then calibrate BNBU with local observations and measured façade features—not synthetic negative examples.

## Status language

Use identified, downloaded, checksum_verified, schema_audited, model_fitted and externally_validated as separate states. Do not call a source integrated when only its landing page or metadata has been read.


## UBC source audit update (2026-11-17)

- All six De Groot files now pass pinned MD5/byte checks in CI; the five non-committed files are retained in the ubc-de-groot-verified-source-snapshot artifact for 30 days.
- The audit confirms 8,846 raw collision rows, 8,831 facade-date keys, 152 fatality events, 142 positive facade-date visits, 8,694 explicit zero rows, 15 repeated facade-date groups and four missing keys in the full cross-product.
- Search schedule: 155 dates, five periods, 225 monitoring days, all eight buildings scheduled on every date.
- Searcher efficiency: 29 trials; carcass persistence: 103 trials (85 finite intervals, 18 right-censored); point counts: 303 species rows in 86 checklists.
- The codebook is inspected; the 50-m VEGE_PERC is building-level and is not interchangeable with the 2023 façade-level TreeCov or StorReflVeg.
- Next model input is the separately published Zulian et al. 2023 Appendix 1. Verify its exact keys and 57-façade grain before joining to the survey panel.


## Glass classification, vegetation exposure and retrofit decision layer (2026-11-17)

- Added structured glass observation schema separating visual class, surface treatment, mounting surface, measured reflectance/transmittance and pattern geometry.
- Added optional CLIP zero-shot photo triage. Similarity scores are not calibrated probabilities; all photo-only labels require human review.
- Added multi-scale vegetation exposure schema for 5 m, 25 m, 50 m, 100 m, 1 km and 10 km buffers. Building-level VEGE_PERC remains separate from façade-level porous-cover and tree-cover measures.
- Added evidence-tiered retrofit recommendations: exterior markers/pattern upgrade, external screen, external shading and supporting lighting management.
- No default efficacy percentages are generated. Ottawa 2026 estimates are recorded as context-specific model predictions, not transferable BNBU causal effects.
- Tree removal is not a default recommendation; glass-side mitigation is prioritized.
- Added glass and vegetation observation templates and unit tests.
