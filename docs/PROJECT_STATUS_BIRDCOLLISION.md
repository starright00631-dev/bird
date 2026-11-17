# Bird-collision decision-support project status

Last reviewed: 2026-11-16  
Working branch: research/full-interpretable-facade-model-20261116  
Base: research/solar-vegetation-exposure-20261113

## Completed in this branch

- Added provenance-aware measurements and evidence tiers.
- Added five vegetation buffers and separate attraction, routing, reflection
  and landscape pathways.
- Added glass-appearance classes and exterior marker compliance screening.
- Added a multi-pathway facade assessment and conditional intervention ranking.
- Added an approach-sample estimator that refuses selected-event denominators
  and returns bounds rather than a point estimate when approaches are censored.
- Added a reproducible, source-pinned audit of the 4,103-row Neotropical event
  dataset.
- Added initial unit tests for the new modules and sampling audit.

## Still open

1. Connect the local 48–50 BNBU observations as a provenance-aware local
   calibration table. Do not create synthetic negative rows.
2. Build the Zhuhai/Guangdong candidate-species list from GBIF and, if access
   is approved, eBird records with sampling effort.
3. Import pane-level glass measurements and a repeatable exterior-view
   reflection/transparent-scene audit.
4. Add remote-sensing canopy cover at all five buffers with consistent
   seasonal composites and resolution.
5. Add a time-varying nocturnal migration / artificial-light layer.
6. Acquire real, licensed approach videos and independent event annotations.
7. Validate the full report and CLI in CI before treating this as a usable
   BNBU decision product.

## Guardrails

- Campus 3D reconstruction is not a prerequisite.
- The 4,103 Neotropical rows are reported collision events, not a risk-set
  training dataset.
- The local BNBU observations are not a representative sample of all
  approaches and cannot identify collision incidence.
- The model must report what evidence supports each recommendation and what
  is not identified.
- No numeric treatment efficacy is assigned to BNBU before local validation.
