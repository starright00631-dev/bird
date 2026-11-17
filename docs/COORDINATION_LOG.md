# BNBU Bird–Glass shared coordination log

Last checked: 2026-11-17
Authoritative integration branch: main
Repository: starright00631-dev/bird

## Working agreement

1. main is the shared source of truth. New integrated work must use a focused branch and PR; do not push unreviewed research changes directly to main.
2. Read this log and README.md before adding a second implementation of an existing module.
3. Keep one canonical feature schema, source registry and test suite. Other BNBU Bird–Glass conversations should use the repository and this log as the durable handoff surface.
4. Before starting overlapping work, inspect main, branches, PRs and CI. Record the current task, changed files, source pins, test state and blockers here.
5. Do not merge a model result merely because another chat reports it. Require code, pinned inputs, executable tests, a reviewed PR diff and reproducible outputs.
6. Synthetic records validate code semantics only; they are not external validation or BNBU evidence.

## Confirmed main-line state

- birdglass/decision.py is version 0.2.0 and returns a pathway profile plus intervention_comparison. It compares mechanism fit and evidence needs; it does not estimate intervention efficacy or select a best option.
- The mechanics, optical geometry, solar geometry, observation-identifiability, approach-event, multi-scale vegetation and UVic facade-panel modules are present.
- The UVic panel adapter produces 300 facade-period rows from 6,337 raw survey rows and fits an observed-evidence Poisson GEE. NB2 is a variance sensitivity check only; no glass/vegetation effects or out-of-site prediction are claimed.
- PR #16 fixed the checked-in UBC Search.Efficiency.csv row width and checksum; it was merged as f2d22c8. Its CI passed with 155 tests passed and 1 skipped.
- The UBC six-file De Groot source snapshot passed MD5 checks and was inspected from the CI artifact. Only Search.Efficiency.csv is checked into Git; the other five remain in the 30-day artifact, not the repository.
- The initial carcass-persistence audit incorrectly treated FirstAbsent=Inf as an ordinary interval. This PR fixes it using the GenEst convention: 85 finite intervals and 18 right-censored trials.
- The collision file has 8,846 raw rows but only 8,831 unique façade-date visits: 152 collision events occur across 142 positive visits; four expected facade-date combinations are absent. Missing visits are not zeros.
- The point-count file has 86 checklist groups: 72 at the eight study buildings and 14 at two ancillary locations. Its 303 rows are species records, not 303 independent counts.
- PR #14 remains an independent Draft research branch, not a mainline dependency.

## External-data state

### De Groot et al. UBC Dryad dataset

- All six published MD5 values are pinned in scripts/audit_ubc_sources.py.
- All six files were downloaded and checksum-verified in Actions; the exact source bytes and audit JSON are retained in a 30-day artifact.
- Carcass persistence: 85 interval-censored, 18 right-censored (FirstAbsent=Inf), 0 invalid/incomplete.
- Search efficiency: 29 repeated trials with sequential risk sets; missing-at-risk values are not zero detections.
- Collision data: 152 positive event rows, 142 positive façade-date visits, 8,694 explicit zero rows, 15 repeated façade-date groups and four missing full-cross-product visits.
- Search schedule: 155 dates, eight buildings, five 45-day windows and 225 inclusive monitoring days; METHOD agrees with within-window 24/48-hour gaps and clean-up starts.
- Point counts: 303 species rows in 86 checklists; 72 study-building and 14 ancillary checklists.
- The UBC files are not yet used to fit or validate a mortality model. Reproduce the observation process before using corrected counts.

### Zulian et al. 2023 Appendix 1

- Identified as 8,835 repeated façade surveys, 57 façades, 8 buildings, 155 survey days, 142 positive façade-surveys and 152 individual collision events.
- Raw appendix remains not downloaded or checksum-verified. Keep it separate from De Groot until row grain and keys are audited.

### BNBU local observations

The approximately 48 submissions remain aggregate-only localization and hypothesis context. They are not a complete risk set, a pane-level approach denominator or negative examples.

## Current PR task

Branch: feat/ubc-audit-censoring-grain-final-20261117
PR: #18

- Correct Inf/NA right-censoring in carcass persistence audit.
- Audit collision event rows versus positive façade-date visits and preserve missing visits.
- Audit 24/48-hour survey schedule and point-count checklist grain.
- Keep all six verified raw files and audit JSON in a 30-day artifact.
- Update docs, registry and tests so the other BNBU conversation can continue from one durable source of truth.

## Immediate next tasks

1. After PR #19 CI passes, download its updated artifact and verify the full JSON and codebook once more.
2. Reproduce the De Groot GenEst carcass-persistence and search-efficiency models, propagating uncertainty into estimated collision counts.
3. Obtain and audit Zulian Appendix 1 as a separate repeated-facade survey product.
4. Continue southern-China species-by-week/guild exposure data and measured glass/vegetation features; do not treat UBC coefficients as BNBU coefficients.
5. Keep the UVic Poisson GEE and NB2 sensitivity descriptive until group-held-out predictive validation is available.

## Status vocabulary

Use identified, downloaded, checksum_verified, schema_audited, model_fitted and externally_validated as separate states. Never call a source integrated when only its landing page or metadata has been read.
