# UBC bird-window collision data: ingestion and audit

**Status:** one raw observation-process file is checksum-verified; the remaining raw files and the 2023 façade-survey appendix are not yet imported. No UBC model has been fitted into the BNBU pipeline.

## Two distinct UBC data products

### A. De Groot et al. (2021), Dryad dataset (published 2022)

- Article: [Ornithological Applications, DOI 10.1093/ornithapp/duab027](https://doi.org/10.1093/ornithapp/duab027)
- Dataset: [Dryad DOI 10.5061/dryad.hqbzkh1g6](https://doi.org/10.5061/dryad.hqbzkh1g6)
- Archived mirror: [Zenodo record 6373683](https://zenodo.org/records/6373683)
- Study: 8 buildings, five 45-day sampling periods, 155 survey days across 225 monitoring days, 103 carcass-persistence trials, 29 searcher-efficiency trials and 72 winter 2017 point counts.
- Published bias-corrected mortality estimate: 360 fatalities (95% CI 281–486). This is a study-level estimate, not an observed count or a BNBU rate.

The six source files and pinned MD5 values are recorded in scripts/audit_ubc_sources.py. Dryad data are published under CC0; cite the dataset and paper.

**Imported and verified:** Search.Efficiency.csv (29 rows; 1,766 bytes; MD5 f9e7a8816ef52eb9d3523f0f14b40d6b).

**Not yet imported:** Carcass.Persistence.csv, Observed.Collision.Counts.csv, READ.ME.xlsx, Search.Schedule.csv and UBC.point.counts.csv. The downloader checks each published MD5 before writing any file.

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

### B. Zulian et al. (2023), repeated façade-survey Appendix 1

- Article: [Avian Conservation and Ecology 18(2):15, DOI 10.5751/ACE-02482-180215](https://doi.org/10.5751/ACE-02482-180215)
- Appendix 1: [CSV](https://ace-eco.org/vol18/iss2/art15/appendix1.csv)
- Published design: 57 façades across 8 buildings, 155 survey days and 8,835 façade surveys.
- Published outcomes: 142 positive façade-surveys, 152 individual collision events and 23 species.

The appendix is identified but not downloaded or checksum-verified in this project version. Do not claim that its raw rows are already in the repository.

The article models detected carcass presence/absence by season using binomial mixed-effects models, with building and façade identity as random effects and log hours since the previous survey as an offset. The paper reports glass area as positively associated with collisions in every season; stories reflecting vegetation were influential in fall; façade area was influential in winter. These are UBC-specific associations, not coefficients to copy to BNBU.

Crucially, 142 positive façade-surveys and 152 individual collision events are different counts. If the appendix response is binary, summing its 0/1 values cannot reconstruct 152.

## Integration rules

1. Keep the De Groot Dryad files and the Zulian Appendix 1 as separate source products until row grain and join keys are inspected.
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

The first command audits files already present. The second fetches the six Dryad files and refuses any file whose checksum differs from the pinned record. The 2023 appendix is supplied separately with --appendix1 after download and attribution checks. The UBC pinned-source workflow fetches all six archive files, verifies their MD5 values, and inspects the READ.ME.xlsx workbook. The codebook preview reports sheet names, dimensions and bounded non-empty rows; it is schema discovery only, not an automatic column mapping.
