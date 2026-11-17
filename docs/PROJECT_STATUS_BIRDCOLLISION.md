# BNBU Bird–Glass project status

**Primary project:** BNBU bird–glass collision research.  
**Primary development branch:** `main`.  
**Last project update:** 2026-11-17.

## Current deliverable

The repository now has a mechanistic research codebase and a multi-pathway façade assessment prototype. It is not yet a trained BNBU prediction model. The model must explain the pathway from bird activity and local route generation through glass optics, flight/contact and observation bias, then compare intervention mechanisms.

## Current model stages

| Stage | Current status | Next validation requirement |
|---|---|---|
| Regional bird availability | Schema and external evidence identified | Acquire Guangdong/Zhuhai species-by-week occurrence with sampling effort and taxonomy |
| Local approach flow | Identifiability and approach-event contracts exist | Continuous approach observations or a defensible effort-corrected movement proxy |
| Glass optics | Finite-pane reflection/transmission and solar geometry exist | Full-assembly VLR/VLT/spectral R/T and multi-time bird-facing imagery |
| Flight/contact | 3D movement/control/contact modules exist | Independent metric trajectories and held-out bird/trial validation |
| Observation bias | UVic and UBC searcher-efficiency/persistence sources are pinned and audited; UBC De Groot observation-process sensitivities are separate from collision outcomes | Obtain BNBU search effort, carcass persistence and searcher-detection trials before local correction |
| Vegetation | Five buffers and four distinct ecological pathways exist | Human-audited canopy/land-cover layers, species/resources and route features |
| External facade benchmark | Zulian 2023 Appendix 1 is pinned as an 8,835-row, 57-facade x 155-date panel; paper-aligned seasonal binomial GLMM, AICc comparison, DHARMa diagnostics and 32-fold leave-one-building-out validation run in CI | AICc support pattern matches the paper, but held-out-building Brier is worse than the offset-only baseline in all four seasons; retain as descriptive UBC benchmark, not transferable predictor or BNBU calibration | 
| Intervention | Evidence-gated candidate comparison exists | Matched/randomized BACI with pane-specific approach denominators and safety/cost measures |

## UBC benchmark interpretation

- Appendix 1 is the primary façade-feature panel. It has 8,835 complete façade-date rows, 57 façades, 8 buildings, 155 dates, 142 positive carcass-presence visits and 152 carcass-mortality events. `COLLISIONS_X` is a separate endpoint.
- The De Groot observed-collision file is a separate source version: only 139 dates overlap, 16 dates are unique to each source, 8 common-key mortality counts differ and 171 METHOD values differ. Do not row-join these files.
- The paper-aligned seasonal GLMM uses a binomial logit, log(24/48-hour survey exposure) offset and one composite building:façade random intercept. Candidate model df are 8/6/5/2.
- LOBO is not a predictive success: full-model Brier is worse than the exposure-only baseline in fall, winter, spring and summer; log-loss improves only in fall. No held-out-site or Guangdong validation exists.

## Main research constraints

- BNBU's 48 opportunistic submissions are a localization/hypothesis source, not a rate-model training set.
- The 38 candidate microzones are not verified panes; T29 and LRC references must not be collapsed into single glass surfaces.
- Event-only databases such as the Neotropical collection can inform species/event composition but cannot provide non-event exposure denominators.
- Vegetation can influence attraction, routing, optical reflection and obstruction in different directions and at different scales.
- A glass treatment's spacing screen is not an ABC Threat Factor certification or a local efficacy estimate.
- Collision/contact probability and injury/fatality probability are separate endpoints.

## Immediate engineering priorities

1. Reproduce the De Groot observation-process correction (GenEst pkm searcher efficiency, cpm carcass persistence and estM survey schedule) from the pinned trial inputs; reconcile the original model-list selections against complete AICc tables before using corrected mortality.
2. Acquire and harmonize an independent subtropical façade-survey dataset with explicit zeros, 24/48-hour effort, façade glass/vegetation features, searcher detection and carcass persistence; retain exact source versions and hashes.
3. Acquire effort-aware bird occurrence/activity data for Guangdong/Zhuhai; do not treat regional presence as pane approach flow or collision exposure.
4. Build pane-level measured glass appearance and whole-assembly spectral R/T records; link them to finite-pane reflection/transmission geometry and independent multi-view validation.
5. Collect continuous approach/avoidance trajectories and species morphology before fitting recognition, control or swept-contact parameters; keep synthetic kinematics as code tests only.
6. Implement field-ready BNBU pane-level survey and intervention monitoring records with costs, daylight, maintenance, safety, ecological effects and adjacent-pane risk transfer; estimate efficacy only from comparable controlled designs.

All new project work must use a feature branch and pull request, with review and passing CI before merge to `main`. Campus 3D remains a separate supporting workstream; it is not the main research deliverable or a prerequisite for external-data model development.
