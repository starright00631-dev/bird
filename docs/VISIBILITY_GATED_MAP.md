# Recognition-gated routing across adjacent fixed glazing

## Falsifiable engineering question (2026-11-12)

Does knowledge of **unrecognized** glazing enter the simulated bird's
route-choice policy? If pane A is recognized and pane B is not, adding B
must not change the animal's chosen target for the same sensory/control
state. Nevertheless, B must remain a physical collision surface.

**Found defect on the 2026-11-12 main baseline:** the two routes,
`geometric` and `screened`, enumerated gaps using **all real facade panes**
after *any* glazing became recognized. In `screened`, even a rollout
against unrecognized glass could reject a candidate, effectively granting
the controller privileged obstacle knowledge. Thus the old method was a
full-geometry *oracle*, not a perception-conditional bird model. The
distinction matters when one marked window shifts an approach toward
unmarked adjacent windows or walls.

## Implemented causal separation

At time t, the **hypothetical** perceived scene is
`{all opaque rectangles} U {glass rectangles previously recognized}`.
Both planners now search/screen candidate targets in that scene. At the
actual time step, `contact.first_contact` still checks the complete
glass-and-opaque facade using the swept body and wing model. Paired
policy comparisons keep identical arrivals, pane draws, and physical
scene; only recognition changes.

This is an internal consistency fix, not a real mechanism estimated from
data. In particular, treating all opaque facades as visible is a
simplification, and binary per-pane recognition is still an unfit state.

## Baseline and falsification protocol

- **Oracle baseline (prior code):** search and reject using every real
  pane, including unrecognized glass.
- **Recognition-gated model (this change):** route with only recognized
  glass and assumed-visible opaque geometry; measure actual physical
  contacts on all panes.
- **Synthetic regression conditions:** an unseen adjacent pane may not
  change the perceived gap aim; the same pane *when recognized* may change
  it; absent recognition still leads to a real glass collision; opaque
  structure is never erased; both `geometric` and `screened` replay
  planners receive no hidden glazing from the controller.
- These tests establish a structural invariant, **not** improved field
  accuracy or a numerical BNBU collision reduction. No actual birds were
  simulated from calibrated individual trajectories and no field action
  is authorized.

## Peer-reviewed evidence and its boundaries

1. Lin, Ros & Biewener (2014), DOI
   https://doi.org/10.1098/rsif.2014.0239:
   pigeon gap aiming in a corridor of clearly visible vertical poles;
   this does not identify glass recognition in urban species. Published
   equation correction: https://doi.org/10.1098/rsif.2016.0934.
2. Håstad & Ödeen (2014), DOI
   https://doi.org/10.7717/peerj.621:
   predicted UV marking visibility depends on the bird's visual-system
   class and viewing spectrum. It is not a BNBU calibrated detection
   probability or proof that all UV markings work.
3. Samuels et al. (2022), DOI
   https://doi.org/10.7717/peerj.14604:
   38 **selected** observed bird-window events, 29 contacts and nine
   near-misses; not a denominator for all approaches, and not raw 3D
   footage imported here.
4. The repository's 3D-POP public metadata audit includes pigeon
   subject/session identifiers but **walking** footage, not glass
   avoidance; no apparent flight-control validation can be inferred.

## Evidence needed before BNBU transport

Collect registered glazing and adjacent opaque geometry, synchronized
multi-view tracks including collisions *and* successful avoids, a
camera-verified approach denominator, time-resolved reflection/transmission
and spectral illumination, species/individual morphology and measured
latency. Fit and compare against straight-flight, visible-geometry
oracle, and perceived-gap steering on held-out birds/buildings/days.
Evaluate **all structural contacts**, not just treated-window counts.
Until those identifiability gates pass, no deployment probabilities,
casualty reductions or treatment approvals follow from this change.
