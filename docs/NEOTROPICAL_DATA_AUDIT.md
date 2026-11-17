# Neotropical bird–window collision dataset: audit and permitted use

Source: Piratelli et al. (2025), *Ecology* 106(6), e70126.  
DOI: https://doi.org/10.1002/ecy.70126  
Data/software release: https://doi.org/10.5281/zenodo.15271127  
Repository: https://github.com/ajpiratelli/Data-Paper-BWC  
Pinned Git blob: 4f0205d8158e88f19f95a022bacaa06805ca31b7

The raw CSV was fetched from the public repository and parsed for this
project. The audit script now verifies the Git blob SHA before downloading
and records the dataset's actual unit: one curated, reported collision event.

## Observed contents

| Field | Count |
|---|---:|
| Reported collision records | 4,103 |
| Unique species | 571 |
| Countries | 11 |
| Date range | 1946–2020 |

Reported collection methods in the paper:
- local-specific systematic protocol: 1,419;
- observed by chance: 1,252;
- government agencies: 742;
- other approaches: 632;
- unknown procedure: 58.

Glass information in the audited CSV:
- translucent: 1,573;
- reflective: 1,137;
- unknown: 1,393.

Deterrent information:
- no deterrent recorded: 2,869;
- deterrent recorded: 389;
- unknown: 845.

Reported survivorship:
- dead: 2,537;
- alive: 1,515;
- unknown: 51.

These are counts among submitted reports. They are **not** population
frequencies, glass-specific risks, deterrent efficacy, or true mortality
rates. Missing pane/deterrent data and heterogeneous collection methods are
material.

## What the dataset can and cannot support

**Can support**
- descriptive composition of reported collision events;
- species/taxonomy and month hypotheses;
- audit of collection-method heterogeneity;
- exploratory analysis of how reporting sources describe glass and deterrents.

**Cannot identify**
- collision probability per bird approach;
- incidence per building, façade, pane-hour or survey effort;
- causal effects of glass type or deterrent;
- local Guangdong abundance, seasonal approach flow or species susceptibility;
- mortality probability for all collision events.

The 4,103 rows are not a complete risk set: there are no corresponding
systematically sampled non-collision approaches. A binary classifier that
treats each row as a positive and invents negatives would learn reporting and
selection patterns rather than collision risk.

## Split and dependence audit

The script provides:
- a stable 80/20 row-hash diagnostic for illustrating why row splits are
  inadequate;
- a country-held-out descriptive split to keep countries disjoint;
- a country-coordinate repetition diagnostic.

Country-held-out folds are not a validated collision model. Coordinates may
be rounded, reused or represent a reporting location; they are not a reliable
building identifier. Do not claim that repeated coordinate keys prove
same-building leakage. For any future building-level model, source, observer,
building, camera, bird and date identifiers are needed.

## Reproduction

```bash
python scripts/audit_neotropical_sampling.py --fetch-pinned --out results/neotropical_audit.json
python -m pytest -q tests
```

The script rejects a changed upstream Git blob so a future dataset update
cannot silently alter the analysis. Review the new version and its citation
before changing the pin.
