# UBC bird-window collision data: ingestion and audit

**Status:** all six De Groot et al. Dryad files passed their published MD5 checks in GitHub Actions run [44008534217](https://github.com/starright00631-dev/bird/actions/runs/44008534217). The full six-file artifact was subsequently downloaded and inspected. Only Search.Efficiency.csv is checked into Git; the other five files are retained in the 30-day Actions artifact, not committed as raw files. The current PR upgrades the audit so the row grain and censoring are checked automatically.

No UBC model has yet been fitted into the BNBU pipeline. These are temperate Pacific data and are a transfer/reproduction benchmark, not Guangdong/BNBU calibration truth.

## Source and study

- Article: De Groot et al. (2021), Ornithological Applications, DOI 10.1093/ornithapp/duab027
- Dataset: Dryad DOI 10.5061/dryad.hqbzkh1g6
- Archived mirror: Zenodo record 6373683
- Study design: 8 buildings, 57 façades, five 45-day sampling windows, 155 scheduled search dates across 225 monitoring days, 103 carcass-persistence trials, 29 searcher-efficiency trials and winter point counts.
- Published bias-corrected mortality estimate: 360 fatalities (95% CI 281–486). This is a GenEst model estimate from the paper, not an observed count and not a BNBU rate.

The dataset is published under CC0. The six source filenames and published MD5 values are pinned in scripts/audit_ubc_sources.py.

## Six-file acquisition status

| File | Zenodo MD5 | Audited contents |
|---|---|---|
| Carcass.Persistence.csv | 61dd1e109bb22925cd91b9b697ae4c9c | 103 carcass trials: 85 interval-censored and 18 right-censored |
| Observed.Collision.Counts.csv | 9e0c551f430e75e337a6b6da750a0d00 | 8,846 raw rows; 152 positive collision-event rows; 142 positive façade-date visits |
| READ.ME.xlsx | 299d4a431186ada9a47950b5824a2a93 | Source codebook; field definitions inspected |
| Search.Efficiency.csv | f9e7a8816ef52eb9d3523f0f14b40d6b | 29 repeated search-efficiency trials; checked in at data/raw/ubc and byte-level MD5-verified |
| Search.Schedule.csv | 729cde12568d04a8b102726b8112533b | 155 scheduled dates, eight building columns and five 45-day windows |
| UBC.point.counts.csv | 760e513ad29905159dbb886ccf532208 | 303 species rows forming 86 checklists; 72 at the eight study-building locations and 14 at two ancillary locations |

The UBC pinned-source workflow downloads all six files, checks every MD5 against the manifest, prints the CSV row counts and headers, and uploads the raw files plus the audit JSON as a 30-day artifact. The other five files are not represented as Git-committed data.

## Carcass persistence: corrected censoring audit

The raw file contains 103 trials. The audit now classifies:
- 85 finite LastPresent / FirstAbsent intervals;
- 18 right-censored trials where FirstAbsent is Inf;
- 0 invalid/incomplete trials.

The median finite interval width is 0.69 days (range 0.04–2.00 days). An earlier audit version incorrectly counted Inf as an ordinary finite interval; that logic has been corrected.

This follows the GenEst data convention: if a carcass persists beyond the final trial check, LastPresent is its last observed time and FirstAbsent is entered as Inf or NA. Such records are right-censored, not infinite removal times. See the [GenEst manual, Carcass Persistence data definition](https://pbil.univ-lyon1.fr/CRAN/web/packages/GenEst/GenEst.pdf).

Do not replace the intervals with exact removal times. The persistence likelihood must use interval-censored and right-censored observations.

## Searcher efficiency

The 29 trial rows contain repeated searches. The sequential risk sets are:

| Search | At-risk trials with observed result | Found | Conditional fraction |
|---:|---:|---:|---:|
| 1 | 29 | 16 | 55.2% |
| 2 | 13 | 5 | 38.5% |
| 3 | 7 | 1 | 14.3% |
| 4 | 5 | 1 | 20.0% |
| 5 | 3 | 0 | 0.0% |
| 6 | 3 | 0 | 0.0% |

One missing result while at risk occurs at each of searches 3, 4 and 5. Once a carcass is detected, subsequent NA cells are no longer at risk; they are not zero detections. Seasonal first-search samples are small and unbalanced: fall 0/2, spring 2/3, summer 3/3 and winter 11/21.

These are descriptive trial hazards only. They are not a fitted GenEst search-efficiency parameter and are not enough to correct collision counts without the persistence model and actual search schedule.

## Collision observations: event rows versus visit rows

The 8,846-row Observed.Collision.Counts.csv has:
- 152 positive event rows / total collision count;
- 142 unique façade-date visits with at least one collision;
- 8,694 explicit zero rows;
- 8,831 unique façade-date visits across 57 façades and 155 scheduled dates;
- 15 repeated façade-date groups, including 10 additional positive event rows;
- 4 façade-date combinations absent from the full 57 × 155 cross-product.

The four missing combinations are:
- International 1 — 2016-06-26
- Irving 10 — 2015-09-10
- Irving 4 — 2016-06-25
- Wesbrook 8 — 2015-02-13

These missing visits are not zeros. Repeated rows are not automatically duplicate errors: multiple positive rows can represent multiple collision events during one façade-date interval. For a visit-level presence target, aggregate to façade-date and use any positive event; for an event-count target, sum the positive event rows. Preserve both estimands. Never train on raw rows as if all 8,846 were independent façade visits.

The METHOD field agrees with the Search.Schedule.csv timing: within a sampling window it records 24-hour or 48-hour gaps, while the first survey of a window is coded as a clean-up survey. The audit finds zero schedule/method mismatches. The five seasonal windows sum to 225 inclusive monitoring days; gaps between windows are not exposure time.

## Vegetation and façade variables

VEGE_PERC is constant within each of the eight buildings, with one building-level value per building. VEGE_CAT is the corresponding high/low stratification. This is not a pane-level vegetation measurement. With only eight buildings, a model containing building fixed effects cannot separately estimate a building-constant VEGE_PERC coefficient. Do not pretend the 8,846 event/zero rows provide 8,846 independent vegetation replicates.

The codebook describes STOREYS as the number of stories, but 11 façade records contain non-integer values. These are preserved and flagged; do not round them or treat them as a verified ordinal floor count without resolving the source definition.

## Point counts: species rows versus checklists

UBC.point.counts.csv contains 303 species rows grouped into 86 checklists at 10 locations:
- 72 checklists at the eight study-building locations;
- 14 ancillary checklists at two other locations.

Each checklist is a Location × Date × Interval group with one row per species. The group-size field matches the species-row count; checklist metadata are internally consistent. The records describe 5-minute, 50-m-radius, one-observer complete checklists. They can inform winter site-level bird activity/species composition, but they are not pane-specific approaches and do not supply a year-round Guangdong abundance prior.

## Two distinct UBC data products

### A. De Groot et al. (2021), Dryad dataset

Keep the six De Groot files together as one observation-process and seasonal monitoring product. Search efficiency, carcass persistence, collision observations and the search schedule are distinct likelihood components. Reproduce the paper's GenEst workflow and propagate uncertainty rather than applying a single inverse detection fraction.

### B. Zulian et al. (2023), repeated façade-survey Appendix 1

- Article: Avian Conservation and Ecology 18(2):15, DOI 10.5751/ACE-02482-180215
- Appendix 1: https://ace-eco.org/vol18/iss2/art15/appendix1.csv
- Published design: 57 façades across 8 buildings, 155 survey days and 8,835 façade surveys.
- Published outcomes: 142 positive façade-surveys, 152 individual collision events and 23 species.

This is a separate dataset and is not downloaded or checksum-verified in this project version. Do not join it to the De Groot files without verified keys and compatible row grain.

## Integration rules

1. Keep the De Groot files and Zulian Appendix 1 as separate source products.
2. Preserve completed survey zeroes. Missing visits, cancelled surveys and unvisited façades are not zero-collision observations.
3. Treat search efficiency and carcass persistence as observation-process data, not collision labels.
4. Preserve the event-row, positive-visit and full scheduled-visit grains separately.
5. Use the 24/48-hour survey interval and clean-up schedule in the observation model; do not use raw row count as exposure.
6. Use UBC as an external temperate-Pacific benchmark, not a Guangdong species prior or BNBU calibration truth.
7. Group validation by building/façade and time. Random row splits would leak repeated observations.

## Reproduction

    python scripts/audit_ubc_sources.py --fetch --data-dir data/derived/ubc --out results/ubc_audit.json
    python -m pytest -q tests

The CI artifact contains the exact fetched bytes and audit JSON. The next modeling gate is a faithful observation-process reproduction; no corrected mortality model or BNBU risk estimate is claimed.
