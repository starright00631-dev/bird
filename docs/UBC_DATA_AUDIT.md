# UBC bird-window collision data: ingestion and audit

**Status:** all six De Groot (2021) source files are downloaded and MD5-verified in the UBC CI workflow and retained as a 30-day workflow artifact; raw files are not committed to the repository. The codebook has been inspected. Zulian (2023) Appendix 1 is also downloaded, SHA-256-pinned and schema-audited in CI as a complete 8,835-row repeated façade-survey panel. Neither UBC dataset is a BNBU calibration model.

## Two distinct UBC data products

### A. De Groot et al. (2021), Dryad dataset (published 2022)

- Article: [Ornithological Applications, DOI 10.1093/ornithapp/duab027](https://doi.org/10.1093/ornithapp/duab027)
- Dataset: [Dryad DOI 10.5061/dryad.hqbzkh1g6](https://doi.org/10.5061/dryad.hqbzkh1g6)
- Archived mirror: [Zenodo record 6373683](https://zenodo.org/records/6373683)
- Study: 8 buildings, five 45-day sampling periods, 155 survey days across 225 monitoring days, 103 carcass-persistence trials, 29 searcher-efficiency trials and 72 winter 2017 point counts.
- Published bias-corrected mortality estimate: 360 fatalities (95% CI 281–486). This is a study-level estimate, not an observed count or a BNBU rate.

The six source files and pinned MD5 values are recorded in scripts/audit_ubc_sources.py. Dryad data are published under CC0; cite the dataset and paper.

**Repository snapshot:** Search.Efficiency.csv (29 rows; 1,766 bytes; MD5 f9e7a8816ef52eb9d3523f0f14b40d6b).

**CI-verified source snapshot:** all six Dryad files pass their published MD5 and byte-size checks. The five remaining files are downloaded into an ignored CI directory and uploaded as a 30-day workflow artifact; they are not copied into Git. The audit tests the raw grain and codebook before any model mapping.

The 29 search-efficiency trials contain repeated search histories. The descriptive sequential risk sets are:

| Search | At-risk trials with observed result | Found | Conditional fraction |
|---:|---:|---:|---:|
| 1 | 29 | 16 | 55.2% |
| 2 | 13 | 5 | 38.5% |
| 3 | 7 | 1 | 14.3% |
| 4 | 5 | 1 | 20.0% |
| 5 | 3 | 0 | 0.0% |
| 6 | 3 | 0 | 0.0% |

One missing result while at risk occurs at each of searches 3, 4 and 5. Once a carcass is detected, its subsequent NA cells are no longer at risk; they are not zero detections. Seasonal first-search samples are small and unbalanced: fall 0/2, spring 2/3, summer 3/3 and winter 11/21.

These are descriptive trial hazards only. They are not the final GenEst search-efficiency parameter, not a BNBU correction factor, and not enough to correct observed collisions without the persistence model and search schedule.

### Codebook findings from READ.ME.xlsx (bounded CI inspection)

The checksum-verified workbook contains five sheets: UBC.point.counts, Observed.Collision.Counts, Search.Schedule, Search.Efficiency and Carcass.Persistence. The CI preview is complete for these sheets (5 sheets; workbook SHA-256 554ab07b1a1975319b9d9201bd163ded86a574ca5ec22daa1f86daaa2faa653f).

| Source sheet | Codebook-defined fields | Modelling implication |
|---|---|---|
| Observed.Collision.Counts | COLLISIONMORTALITY_X: 0 means no mortality observed; 1 or more is the number of collision fatalities. METHOD: 1 is a 24-hour gap between collision surveys (or a clean-up survey); 2 is a 48-hour gap. | This is a count outcome, not a binary response. The 24/48-hour observation interval changes exposure and carcass availability; do not treat each row as equal-duration exposure without modelling the interval and detection process. |
| Observed.Collision.Counts | VEGE_CAT is a high/low vegetation stratum from the study's stratified design; VEGE_PERC is the actual vegetation percentage within 50 m of the building, measured in ArcGIS; STOREYS is the number of stories of the building façade. | VEGE_PERC is a building-level 50 m covariate, not pane-level or multi-scale vegetation. VEGE_CAT is a design stratum, not an independent continuous vegetation measure. |
| Search.Efficiency | s1-s6 are successive searches after carcass placement; 0 means not found, 1 found, NA not applicable. BuildingType is the ID of one of eight study buildings, not a high/low building-type category. Date is the carcass placement date for s1. | Detection ends the at-risk sequence. NA must not be converted to a failed search or zero detection. |
| Carcass.Persistence | LastPresent and FirstAbsent are elapsed days since placement at the last present and first absent checks. BuildingType is again a building ID among the eight study buildings. | Removal time is interval-censored, not an exact event time. |
| Search.Schedule | SearchDate plus one column for each of eight study buildings. | Reconstruct survey intervals by building; an absent date or unvisited building is not a zero-collision observation. |
| UBC.point.counts | Species, Count, Location, Date, JulianDay, Start, Interval, Duration_mins, Distance_m, Num_obs, Complete_Checklist and Num_spp_in_count. | Bird abundance/count models need to preserve point-count effort, checklist completeness, observer count and survey duration. |

**Important boundary:** this is a codebook-based schema description. No row-level join, field recoding, model fit or causal effect estimate has been produced from the five non-committed source files. The 50 m vegetation feature cannot be substituted for BNBU's requested multi-scale canopy/reflection features.


### Reproduced source audit (pinned Dryad/Zenodo snapshot)

The UBC CI run verifies all six archive files and checks the following source-grain facts:

| Source layer | Verified result | Safe interpretation |
|---|---:|---|
| Observed collision file | 8,846 rows | Raw source rows, not automatically 8,846 independent visits |
| Facade-date keys | 8,831 | 57 façades across 155 survey dates; 15 repeated facade-date groups |
| Collision events | 152 | Sum of the count-valued fatality field |
| Positive facade-date visits | 142 | Binary visit-level outcome after aggregation |
| Explicit zero rows | 8,694 | Explicit recorded zeros only |
| Missing facade-date keys | 4 | Retained as missing; never synthesized as zero |
| Search schedule | 155 dates, 5 periods | 225 inclusive monitoring days; all 8 buildings scheduled on every listed date |
| Searcher-efficiency trials | 29 | Six sequential search occasions; missing at-risk results remain missing |
| Carcass-persistence trials | 103 | 85 finite interval observations and 18 right-censored observations |
| Winter point counts | 303 species rows | 86 checklist groups: 72 at the eight study buildings and 14 ancillary |

The collision file contains 15 repeated facade-date groups. The audit preserves
the sum of 152 fatality events and the 142 positive facade-date visits as
different outcomes. It also records mixed zero/positive groups and repeated
positive events instead of silently deduplicating them. Four absent facade-date
keys in the full 57 x 155 cross-product remain missing observations, not
negative labels.

The METHOD field is checked against the scheduled 24/48-hour interval. All
8,846 source rows match the author schedule. The 2024 inventory is not used as
a proxy for façade or glass area.

### Why the De Groot source is not yet the final glass/vegetation model

The codebook confirms a count-valued fatality response, a 24/48-hour survey
interval, building-level VEGE_PERC within 50 m, a high/low VEGE_CAT
sampling stratum, and façade STOREYS. This source does not provide the full
façade-level predictor set required by the 2023 seasonal analysis:
FacArea, AreaGlass, VegPer, TreeCov, and StorReflVeg.

Zulian et al. (2023) reports those façade-level covariates in Appendix 1,
which is now pinned and audited as a complete 8,835-row façade-date panel.
Its variables are mapped to their actual source columns below. The De Groot
raw collision file is a different source version: its date grid and several
common-key outcomes/methods differ, so the two outcome panels must not be
row-joined. The 50-m building vegetation proportion is not a substitute for
façade-level porous cover, tree canopy or stories reflecting vegetation.

### B. Zulian et al. (2023), repeated façade-survey Appendix 1

- Article: [Avian Conservation and Ecology 18(2):15, DOI 10.5751/ACE-02482-180215](https://doi.org/10.5751/ACE-02482-180215)
- Appendix 1: [CSV](https://ace-eco.org/vol18/iss2/art15/appendix1.csv)
- Published design: 57 façades across 8 buildings, 155 survey days and 8,835 façade surveys.
- Published outcomes: 142 positive façade-surveys, 152 individual collision events and 23 species.

The appendix is downloaded by the UBC CI workflow, pinned to SHA-256 `0baba75389249af1dad546868183f956dd38facef64ae35b04ab761e293fd8a7`, and retained with the De Groot source files in a 30-day artifact. The raw 2.96 MB CSV is not committed to Git.

The article models detected carcass presence/absence by season using binomial mixed-effects models, with building and façade identity as random effects and log hours since the previous survey as an offset. The paper reports glass area as positively associated with collisions in every season; stories reflecting vegetation were influential in fall; façade area was influential in winter. These are UBC-specific associations, not coefficients to copy to BNBU.

Crucially, 142 positive façade-surveys and 152 individual collision events are different counts. If the appendix response is binary, summing its 0/1 values cannot reconstruct 152.

## Integration rules

1. Keep the De Groot Dryad files and the Zulian Appendix 1 as separate source products. The Appendix 1 panel has a verified 57 x 155 grid; the De Groot raw file differs in date-level keys and some common-key outcomes/methods, so do not row-join them.
2. Preserve completed survey zeroes. Missing visits, cancelled surveys and unvisited façades are not zero-collision observations.
3. Treat search efficiency and carcass persistence as observation-process data, not collision labels.
4. Read READ.ME.xlsx before mapping the remaining De Groot fields.
5. Use the UBC dataset as an external transfer benchmark from a temperate Pacific campus. It is not a Guangdong species prior or BNBU calibration truth.
6. Group validation by building/façade and time. Random row splits would leak repeated observations.

## Reproduction

~~~bash
python scripts/audit_ubc_sources.py --data-dir data/derived/ubc --out data/derived/ubc/ubc_audit.json
python scripts/audit_ubc_sources.py --fetch --data-dir data/derived/ubc --out data/derived/ubc/ubc_audit.json
python -m pytest -q tests
~~~

The first command audits files already present. The second fetches the six Dryad files and refuses any file whose checksum differs from the pinned record. The UBC pinned-source workflow also downloads the Zulian Appendix 1 CSV, checks its pinned SHA-256 and byte count, validates the complete 57-façade x 155-date panel, maps the paper's façade covariates and compares its keys with the separate De Groot file. Raw downloads and audit reports remain in the 30-day CI artifact, not Git.




## Zulian et al. (2023) Appendix 1: primary façade-survey panel

Source: https://ace-eco.org/vol18/iss2/art15/appendix1.csv  
Paper DOI: https://doi.org/10.5751/ACE-02482-180215  
Article license: CC BY 4.0; attribute the authors/source and identify changes.

The appendix is a **complete repeated façade-survey panel**, not a 57-row
covariate-only table. Its pinned source SHA-256 is
0baba75389249af1dad546868183f956dd38facef64ae35b04ab761e293fd8a7.

| Property | Verified result |
|---|---:|
| Rows / columns | 8,835 / 45 |
| Buildings / façades | 8 / 57 |
| Survey dates | 155 |
| Facade-date keys | 8,835, no duplicates |
| Visits per façade | 155 for every façade |
| Facades per date | 57 for every date |
| Primary carcass-mortality count | 152 |
| Positive carcass-mortality visits | 142 |
| Broader COLLISIONS_X count | 199 |
| Broader COLLISIONS_X positive visits | 186 |

The primary binomial response is derived from COLLISIONMORTALITY_X:
1 if the count is positive, otherwise 0. The separate COLLISIONS_X field is
retained as a secondary outcome and is not substituted into the paper-aligned
carcass model.

### Verified model feature mapping

| Model concept | Appendix field | Grain / unit |
|---|---|---|
| Façade area | FACADE_AREA | m², façade-level |
| Glass area | AREA_GLASS | m², façade-level |
| Porous/ground-shrub vegetation cover | PERC_VEG_AND_POROUS_SURFACE_FACADE | %, façade-level 50-m buffer |
| Tree canopy cover | TREECOVER_FACADE_PERCENT | %, façade-level 50-m buffer |
| Stories reflecting canopy | STORIES_REFLECT_CANOPY | continuous index, façade-level |
| Building vegetation stratum | VEGE_PERC | proportion 0-1, building-level |
| Survey exposure | METHOD | 1=24 h, 2=48 h |

The paper's VegPer maps to PERC_VEG_AND_POROUS_SURFACE_FACADE, not the
building-level VEGE_PERC. TreeCov maps to TREECOVER_FACADE_PERCENT, and
StorReflVeg maps to STORIES_REFLECT_CANOPY. All façade predictors are constant
within each façade across its 155 repeated survey rows.

The source field `STORIES_REFLECT_CANOPY` is treated as a continuous
reflected-canopy exposure index. Although the paper describes the concept as
the number of stories reflecting vegetation, the released Appendix 1 contains
fractional values (26 of 57 façades; range 0-8; mean 2.232). Preserve the
published values exactly and standardize them as a continuous predictor; do
not round or reject fractional values.

The paper's model uses a binomial logit mixed model with a log-hours offset,
season-specific fits, a BUILDING_X:FACADE random intercept, and four candidate
sets: full, building-only, vegetation-only and null. The full model includes
FACADE_AREA x AREA_GLASS. The current pipeline pins and audits the input panel;
the next model-fitting step will reproduce this baseline and add grouped
building holdouts and uncertainty-aware response curves.

### Why the De Groot raw CSV is not row-joined to this appendix

The De Groot raw collision file is a separate source version. It has 8,846
raw rows, 8,831 unique facade-date keys, 15 repeated keys and four missing
keys in the planned 57 x 155 grid. The Appendix 1 panel has 8,835 complete
facade-date rows. The pinned CI reconciliation confirms the same 57 façade
keys, but only 139 shared survey dates; each source has 16 dates absent from
the other. There are 7,919 common facade-date keys, 916 Appendix-only keys
and 912 De Groot-only keys. On the common keys, eight mortality counts and
171 METHOD values differ. Although both sources aggregate to 152 mortality
events, they are not the same row-level panel. Therefore Appendix 1 is the
primary modelling dataset for the 2023 façade analysis; De Groot remains an
independent observation-process and aggregate cross-check source. They must
not be row-joined or pooled.

### Important limitation for the final BNBU decision system

This UBC panel measures glass area and the vertical extent of reflected
canopy, but it does not provide categorical glass product/type labels
(transparent, reflective, tinted, fritted, patterned) or measured spectral
reflectance/transmittance. The final system will need a separate photo/spec
inspection layer for glass type. It will also need local BNBU vegetation and
glass observations before making campus-specific absolute-risk claims.


### Leave-one-building-out predictive diagnostic

The seasonal GLMM is also evaluated by holding out each of the eight buildings in turn. Predictions for held-out façades exclude their random intercepts. The comparator is an intercept-only binomial model with the same log survey-hours offset, so it preserves the 24/48-hour exposure difference.

The first reproducible 32-fold run gives the following test-visit-weighted out-of-building scores (lower is better):

| Season | Held-out visits | Positive visits | Full GLMM Brier | Offset-only Brier | Δ Brier | Full GLMM log loss | Offset-only log loss | Δ log loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fall | 1,881 | 57 | 0.03011 | 0.02979 | +0.00033 | 0.13388 | 0.14286 | -0.00898 |
| Winter | 3,192 | 51 | 0.02448 | 0.01579 | +0.00869 | 0.10987 | 0.08395 | +0.02592 |
| Spring | 1,881 | 26 | 0.02348 | 0.01372 | +0.00976 | 0.09772 | 0.07593 | +0.02179 |
| Summer | 1,881 | 8 | 0.00433 | 0.00424 | +0.00009 | 0.03163 | 0.02818 | +0.00345 |

Positive Δ means the full GLMM is worse than the exposure-only comparator. In this run, the full model has worse pooled Brier score in all four seasons and improves pooled log loss only in fall. It beats the baseline in 17 of 32 individual folds on Brier and 18 of 32 on log loss. Fold-mean AUC is approximately 0.633 in fall (8 defined folds), 0.497 in winter (8), 0.713 in spring (7) and 0.535 in summer (6); AUC is undefined for folds with a single outcome class, and summer has only eight positive visits overall.

**Decision:** retain this model as a paper-aligned, within-UBC association/reproduction benchmark, not as a reliable building-ranking or transferable prediction model. The leave-one-building-out results do not establish useful generalization even within this one campus. More independent sites, more positive outcomes and measured glass/vegetation features are required before a predictive challenger is justified. These results do not calibrate BNBU risk.


### Seasonal model-selection reproduction

All 16 seasonal candidate fits converged with positive-definite Hessians. The observed AICc differences are:

| Season | Best-supported model | Other model within ΔAICc ≤ 2 | ΔAICc |
|---|---|---|---:|
| Fall | Building-only | None | Full = 2.738 |
| Winter | Building-only | Full | Full = 1.253 |
| Spring | Full | Building-only | Building-only = 1.917 |
| Summer | Null | Building-only | Building-only = 0.049 |

This reproduces the paper's qualitative seasonal support pattern. The absolute log-likelihood/AICc values are not bit-identical to the publication, but the seasonal ΔAICc rankings and the odds-ratio-per-1-SD coefficient pattern align. The output does not establish causal effects or a predictive winner.

Examples of the paper-aligned OR-per-1-SD results in the best-supported candidate sets are: fall AreaGlass 2.56 (95% CI 1.70–3.86) and StorReflVeg 1.92 (1.15–3.19); winter FacArea 1.57 (1.07–2.31) and AreaGlass 1.47 (1.06–2.05); spring full-model AreaGlass 1.99 (1.32–3.02). In summer, the null and building-only models are essentially tied; do not infer a stable glass effect from that season's model choice. All coefficients are observational associations per one standard deviation, not causal effects or intervention efficacy.


## Held-out-building uncertainty (paired cluster bootstrap)

The pinned CI runs 5,000 paired building-cluster resamples across all four
seasonal folds. The resampling unit is the building; seasonal folds for the
same building move together. The comparator is a binomial exposure-only model
with the same log(24/48-hour) offset.

| Pooled metric | GLMM minus exposure-only | 95% building-cluster interval | Interpretation |
|---|---:|---:|---|
| Brier score | +0.00531 | -0.00027 to +0.00988 | No demonstrated improvement; positive values are worse |
| Log loss | +0.01283 | -0.00433 to +0.02735 | No demonstrated improvement; positive values are worse |

These intervals use only eight buildings and are a small-cluster uncertainty
screen, not cross-campus validation. The model remains a descriptive seasonal
association benchmark; do not use its coefficients as BNBU risk probabilities.
