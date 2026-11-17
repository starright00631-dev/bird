# University of Victoria facade-survey adapter and observed-rate baseline

## Scope

The adapter rebuilds the authors' L0 collision-survey data into a panel with
one row per **facade x author-defined seasonal survey period**. The panel is
intended to validate survey-effort handling, repeated facade observations and
seasonal observation patterns. It is not a glass-type or vegetation model.

## Pinned sources

Repository: https://github.com/vivizulian/BirdCollisionsUniVictoria

Pinned publication branch commit: e859320c451a8fd4c6ef9e893e116e43c75a385c

| Source | Raw rows | Git blob SHA-1 |
|---|---:|---|
| collisionsData_Fall.csv | 2,123 | 87b323d7c3a57a764d3b90412840120e7160c69e |
| collisionsData_Winter.csv | 4,214 | 77357637df6fa0e90ea8ed5c3cd22ab97d8efb9a |
| 2024 Buildings for campus-wide estimate.csv | 51 | 9c095b2b5c290f2ef8f8670fb688f9d05b9a3849 |

The source files are fetched at the pinned commit and checked with Git's blob
SHA-1 algorithm before use. Raw or derived row-level data are not committed to
this repository; the source project has no explicit license file visible in
the pinned revision. The generated panel is written to the ignored local path
data/derived/uvic/ and is not checked into Git.

## Grain and aggregation

- A survey visit is keyed by BUILDING_CODE + FACADE + SURVEY_DATE.
- Multiple evidence rows on one facade-date remain multiple evidence records,
  but do not create additional survey visits.
- EVIDENCE_FOUND == Y contributes one recorded evidence item.
- carcass + feather pile is retained as a **fatal-evidence proxy**, not as a
  detection-corrected mortality count.
- The authors' date-to-period rule is retained: September/October = Fall;
  November/December = EarlyWinter; January/February = LateWinter; calendar
  year remains part of the period key.
- The original protocol uses 21 planned survey days per facade-period. Actual
  visits are counted; missing visits are not imputed as zero. The count model
  uses log(survey_visits) as its exposure offset.
- 2024 building floor count and gross floor area are carried as context only.
  They are not used as proxies for facade area, glass area or vegetation.

## Reproduction checks

The pinned source is expected to produce:

- 6,337 raw survey rows;
- 6,298 unique facade-day visits across 50 facades and 6 buildings;
- 39 additional source rows within already-counted facade-day visits;
- 315 collision-evidence rows;
- 137 carcass/feather-pile evidence rows;
- 300 facade-period rows across six periods.

| Period | Facade-day visits | Evidence rows | Fatal-evidence proxy |
|---|---:|---:|---:|
| Fall 2019 | 1,049 | 117 | 69 |
| Fall 2020 | 1,049 | 108 | 44 |
| Late winter 2020 | 1,050 | 6 | 5 |
| Early winter 2021 | 1,050 | 50 | 11 |
| Late winter 2021 | 1,050 | 27 | 3 |
| Late winter 2022 | 1,050 | 7 | 5 |

Two facade-day visits are absent from the two fall periods (one in each).
They are not inserted as zero observations. The script fails closed if pinned
source hashes, row counts, evidence-type counts or period totals change.

## Observed-evidence rate baseline

fit_uvic_observed_rate.py fits a Poisson GEE with:

- response: recorded collision-evidence count per facade-period;
- offset: log(survey_visits);
- fixed effects: building and survey-period categories;
- repeated-measure cluster: facade ID;
- working correlation: exchangeable;
- covariance: robust sandwich.

The output reports descriptive rate ratios, robust intervals and raw
period-specific evidence rates per 1,000 facade-day visits. This is an
observed-evidence baseline only. It does not estimate biological approach
rates, absolute pane collision probabilities, or causal effects of glass or
vegetation. No out-of-site predictive accuracy is claimed from six buildings.

## Important limits

The source does not contain facade-level glass area, glazing appearance,
reflectance/transmittance spectra, canopy cover, vegetation buffers or local
bird approach flow. The 2024 building inventory is temporally offset from the
2019-2022 surveys. Searcher-efficiency and carcass-persistence correction is
not applied by this baseline. A later detection-corrected reproduction must
rebuild the authors' GenEst/JAGS stages from their separate trial, banding and
point-count inputs; this adapter must not be represented as that full
reproduction.

The next data needed for the main decision system are comparable facade-level
surveys with glass type/area, multi-scale vegetation, lighting, survey effort,
zero visits and detection trials. The UVic data only test the observation and
rate-model layer.

## Run

    python -m pip install -r requirements.txt
    python scripts/build_uvic_facade_panel.py --fetch-pinned
    python scripts/fit_uvic_observed_rate.py
    python -m pytest -q tests

For offline use, pass the three source CSVs explicitly to the panel builder.
