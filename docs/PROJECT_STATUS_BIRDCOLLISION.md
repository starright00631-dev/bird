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
| Observation bias | Detection/persistence framework and event identifiability exist | Comparable local search-effort, persistence and detection measurements |
| Vegetation | Five buffers and four distinct ecological pathways exist | Human-audited canopy/land-cover layers, species/resources and route features |
| Intervention | Evidence-gated candidate comparison exists | Matched/randomized BACI with pane-specific approach denominators and safety/cost measures |

## Main research constraints

- BNBU's 48 opportunistic submissions are a localization/hypothesis source, not a rate-model training set.
- The 38 candidate microzones are not verified panes; T29 and LRC references must not be collapsed into single glass surfaces.
- Event-only databases such as the Neotropical collection can inform species/event composition but cannot provide non-event exposure denominators.
- Vegetation can influence attraction, routing, optical reflection and obstruction in different directions and at different scales.
- A glass treatment's spacing screen is not an ABC Threat Factor certification or a local efficacy estimate.
- Collision/contact probability and injury/fatality probability are separate endpoints.

## Immediate engineering priorities

1. Complete and run the decision-edge regression tests.
2. Build a reproducible external data ingestion layer with source hashes, units, taxonomic crosswalks, sampling effort and data-grain metadata.
3. Acquire effort-aware bird occurrence/activity data for Guangdong/Zhuhai; do not treat regional presence as pane approach flow.
4. Build a human-audited glass/vegetation image feature pipeline and hold out sites during validation.
5. Fit an interpretable hierarchical count/rate baseline before trying boosted-tree challengers.
6. Implement field-ready pane-level intervention and monitoring records, then estimate effects only from comparable designs.

All new project work is committed directly to `main`. Campus 3D remains a separate supporting workstream; it is not the main research deliverable or a prerequisite for external-data model development.
