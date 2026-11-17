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

- De Groot et al. Dryad/Zenodo UBC dataset: only Search.Efficiency.csv is currently imported. Its 29 rows, 1,766-byte file and MD5 are verified. The other five source files remain pending.
- Zulian et al. 2023 Appendix 1: identified as the 8,835-row façade-survey risk set, but the raw CSV has not yet been downloaded or verified.
- The UBC data are an external temperate-Pacific transfer benchmark, not BNBU calibration truth.
- Search-efficiency histories and carcass-persistence trials are observation-process data. They must not be used as collision labels.
- The UBC De Groot and Zulian datasets are separate products; do not join them without verified row keys and grain.

## Current handoff (2026-11-17)

- The UBC Search.Efficiency.csv snapshot on main now matches the published 1,766-byte Zenodo file checksum. The other five De Groot source files remain pending.
- This PR adds a pull-request workflow that fetches and checksum-verifies all six De Groot files in an ignored CI directory, plus downloader fail-closed tests.
- Independent BNBU Bird–Glass conversations should use this log for handoff. Separate ChatGPT conversations are not continuously visible to one another; GitHub is the durable shared coordination surface.

## Current handoff (2026-11-17)

- PR #17 is merged as 841af682. Post-merge CI passed: 157 tests passed, 1 skipped; UBC source audit verified all six De Groot files and the UVic source audit completed.
- This PR adds bounded inspection of the De Groot READ.ME.xlsx codebook. It deliberately does not infer mappings or fit a detection model until the field definitions have been reviewed.

## Immediate next tasks

1. Download and checksum-verify the remaining De Groot Dryad files; inspect the codebook before mapping columns.
2. Download and inspect Zulian Appendix 1; verify 8,835 rows, 57 façades, 8 buildings, 155 survey days, 142 positive survey intervals and 23 species before modeling.
3. Build the observation-process layer from repeated search efficiency, interval/right-censored carcass persistence and actual search schedule. Do not use a crude first-search fraction as the final detection correction.
4. Fit the interpretable façade-level baseline first: binomial mixed-effects model with building/façade grouping, season-specific structure and the documented survey-interval offset. Compare a count/rate formulation only if the raw response grain supports it.
5. Use grouped building/façade/time holdouts. Only then compare GAMM, Random Forest and HistGradientBoosting challengers from the other implementation stream.
6. Add local BNBU observations as aggregate-only localization/context, not synthetic negative examples.

## Status language

Use identified, downloaded, checksum_verified, schema_audited, model_fitted and externally_validated as separate states. Do not call a source integrated when only its landing page or metadata has been read.
