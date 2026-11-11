# BNBU Bird–Glass v0.4 — algorithm-to-reality architecture


## 1. Target estimand: the intervention acts on a route, not an isolated window

For an existing glazing patch `p`, species `s`, seasonal/time cell `t`, and fixed facade context `G`, define the expected **true glass contacts**:

\[
\Lambda_{pst}(a)=\int_{r\in\mathcal R} F_{st}(r\mid H_t,W_t,\mathrm{ALAN}_t,a_\mathrm{site})\;
\underbrace{P(C_p=1\mid r,s,G,O_t,a_\mathrm{pane},\theta)}_{\text{3-D flight + perception + action, conditional on route}}\,dr.
\]

Here `F` is an (unobserved) absolute **approach flow**, not the fraction of human reports or a BirdCLEF audio probability. `r` is a *time-indexed* route. `O` represents view-dependent, optically projected scene information. The collision event is evaluated against **all** glass and adjacent opaque construction, not just patch `p`. `a` is a joint assignment of measures to fixed building surfaces and optional site operations; glass replacement is absent from the action space.

To represent detection and mortality separately, survey evidence `Y` is downstream: `Y~Poisson(\Lambda x persistence x detection)` under a simple observation model, with further heterogeneity in real sampling. See `birdglass/identifiability.py`: there are infinitely many combinations with identical observed likelihood. This is why UVic 6,337 standardized facade searches cannot, alone, learn the movement/perception mechanism. BNBU 48 convenience reports do not supply negative search effort.

## 2. Proposed *modular* inference architecture and trainable losses

| Stage (state) | Practical algorithm | Required factual inputs | Trainable objective / validation | v0.4 completion |
|---|---|---|---|---|
| A. Who arrives and why? `F_{st}(r)` | Spatiotemporal marked point process / integrated step-selection model, with species × habitat × weather × season, movement graph and effort-corrected detections | Repeated camera crossings; acoustic segments with effort, field abundance/occupancy; exact habitat and wind; cross-source taxonomy | Poisson/negative-binomial held-out *arrival counts*, leave-site-time out, not sound-label AUC | Contract and causal separation only; no corridor arrival model fitted |
| B. Flying body state `x=[r,v,q,wing configuration]` | State-space trajectory reconstruction with camera pose/uncertainty; Savitzky–Golay derivative for basic checks, then constrained dynamics and species-specific motion prior | Stereo tracks, pose, frame rate, calibrated metric axes, individual IDs; AVONET mass matching; direct wingspan/pose (not AVONET wing length) | Next-frame likelihood; 3D RMSE and uncertainty coverages, leave individual/trial out | Existing 3D derivatives + swept finite body contact; no new real tracks acquired |
| C. Bird visual observation `z_t` | View-dependent virtual reflections / transparent ray traces; image spectral contrast and retinal motion transform; uncertain sensor likelihood | Registered glass planes; HDR / spectral imagery; illumination, camera/bird geometry; collision + near-miss filming | Detectability / avoidance-onset distance on independent videos; video-domain leave-building out | Ray geometry connected to optional controller ambiguity input; perception coefficients hypothetical |
| D. Decision/action `u_t` | **Perceived-gap aiming** with reaction latency, proportional steering and acceleration/curvature limit; future: fit delayed controller or inverse planner | Simultaneous true trajectory **and obstacle/gap aim** per frame; species and individual IDs | Predict steering angular rate on held-out flights; null-controller comparison; tune delay **within training tracks** | Runnable 3D delayed controller; `control_fit.py` with trial-group holdout; synthetic parameter-recovery test only |
| E. Collision & injury | Continuous body + effective wing sweep against **glass and opaque** surfaces; impact normal velocity and kinetic energy proxies; injury layer separate | Body/wing articulation, contact video, clinical/behavioral injury outcome | Sensitivity/false-negative contact tests, then held-out injury likelihood | Geometry and energy proxy implemented; injury not calibrated |
| F. Intervention search | **Joint** stochastic counterfactual replay, coupled re-aiming, opaque spillover and robust multiobjective search; abstain until transfer is identified | Local treatment efficacy under matching spectral/behavior conditions; installation aesthetics, fire/maintenance/safety; independent BACI | Paired on/off approach counts and *total-contact/injury endpoints*, leave-pane/day/period out; budget+visual frontier | Exact limited 4-pane search with shared random numbers; demonstration only |

We would not currently train one giant Transformer over the concatenation of sources: each source observes a different latent process, and the missing factors are not identified by that joint dataset. Deep-learning components can improve detection/pose and movement proposals, but are **measurement modules**, not a substitute for causal link identification.

## 3. Core algorithm implemented: perception-conditional gap-aiming + 3D controlled motion

Lin, Ros & Biewener (2014, DOI `10.1098/rsif.2014.0239`) found a pigeon gap-aiming control law with a reported pooled visuomotor latency about 134 ms and proportional gain about 4.74 s^-1 in indoor **visible-pole obstacle** experiments. This is implemented as the *model form/reference scenario* only; these values are not fitted for a songbird or an invisible pane.

At a given bird position `r(t)`, a pane's **physical boundary** is known to the simulator. However, its **perceived obstacle identity** is a latent Bernoulli recognition event, informed by scene photometry, reflection, transparency and any external markings. The distinction is key:

1. Build optical virtual-image rays from real/placeholder habitat points using `optical_geometry.py`. `optical_ambiguity_at_view` exposes an observation feature; converting that feature to recognizability remains **uncalibrated**, and its default normalization is only for sensitivity tests.
2. Construct the perceived union of opaque structure and **recognized** glazed patches; unrecognized glass can look like free space.
3. Search a 2D family of 3D passage directions at the glass plane, constraining perceived body and wing clearance. Choose a gap by a transparent *hypothetical* objective: heading change, goal-deviation, available perceived clearance. **The chosen gap can, in reality, be untreated glass.**
4. Feed the aim into a delayed, 3D proportional controller with a centripetal-acceleration constraint; integrate at 25 ms resolution. This retains an actual velocity vector and a mass/size-conditioned contact envelope. It currently **holds airspeed constant** and does not yet model bank, force limits or wingbeat-scale articulation.
5. On every candidate contact, sweep body and effective wing stations against **all** glass *and* adjacent opaque geometry. Keep two separate endpoints: glass contacts and all-structure contacts. A wall hit is not a successful avoidance.
6. For an intervention policy on one or multiple panes, replay **exactly the same** flight starts and per-pane random visual samples. Recompute every path; do not add isolated per-pane risk reductions.

The `fast_contact.py` acceleration uses exact piecewise quadratic segment-to-rectangle distance; tests compare it to the original independent numerical optimizer over random samples. This is an **engineering equivalence check**, not a flight validation.

## 4. Finding already implemented: joint policies are NOT an additive pane score

In the synthetic bridge archetype, same 24 constructed approaches and one high-awareness control hypothesis:

- no pattern: 18 synthetic glass contacts;
- B1 exterior dots only: 16;
- B2 only: 17 (on B2 itself 7 → 0, but other panes gain contacts);
- B1 + B2: 12.

The additive single-pane estimate predicts `18-(2+1)=15`, while the coupled controller produces **12** (joint reduction 6 vs additive 3). This is a deliberately engineered *identifiability and interaction stress test*, not a measured design effect.

In the fictional LRC with a continuous facade, some policies reduce glass contacts while increasing opaque-wall contact. Any optimizer that treats glass-only improvement as an unqualified success is invalid for our research goal. The exact numerical counts in the files are **assumption-conditioned**, not estimates for the real LRC.

When all current contradictory mechanistic hypotheses are included, the budget-constrained worst-case search selects **no action** for three fictional archetypes. This is the correct *abstention* under uncalibrated transfer assumptions, **not evidence interventions are ineffective**.




## 6. Experiments that must precede field risk maps

**Experiment A — controlled flight mechanics:** download and actually inspect the public Henningsson 2021 stereo budgerigar gap trials (Dryad `10.5061/dryad.rr4xgxd8j`) and 2026 annotated multi-budgerigar 120 fps stereo trajectories (Zenodo `10.5281/zenodo.19712127`). Fit per-individual/condition motion priors; group split by individual and experimental trial. Estimate uncertainty on speed/curvature/wing configuration; the bird-bird data do not identify glass perception. Compare delayed gap aiming to heading-only, nearest-gap and acceleration-only baselines on independent trajectories, with camera localization error propagated.

**Experiment B — glass-specific sensory/behavior:** a video corpus MUST include consecutive approaches, real collisions, near misses, different glass appearances, matched bird species and a camera-verified opportunity denominator, ideally with visible/head pose, glare/illumination, and response onset. Estimate `P(recognize | optical geometry, treatment, s, light)` and a movement controller jointly *only when those labels exist*. Mere 38 selected approaches from Samuels et al. (2022) cannot identify a regional collision base rate. Hold out building/camera, bird, day and seasonal contexts.

**Experiment C — contact vs injury:** finite contact diagnostics should be compared with 3D filmed contacts, including edge, partial wingfold and rebounds; glass and any screen/cord contact need independently measured severity. Momentum `m(v·n)` and normal kinetic energy `0.5*m*(v·n)^2` are explanatory *proxies*, not mortality probabilities.

**Experiment D — non-replacement intervention:** assess existing-building **external compliant patterns, properly installed cords/screens, local shading, nighttime lighting control where relevant**, and low-impact vegetation-route changes only with habitat safety evidence. The controlled endpoints are **all structural contacts and injury per camera-verified approach** plus view/daylight burden, maintenance and ecological safety. Matched randomized/stepped-wedge facade intervention includes adjacent untreated panes to capture displacement; require leave-period and leave-building validation. No glass replacement is ever considered.

## 7. Hard decision gates

`PARAMETER_REQUIREMENTS` documents each unidentified parameter and source. A field treatment can only be recommended once independent geometry, approach flow, vision, maneuverability and intervention-effects evidence have been validated **at a transportable setting**; current code returns `deployment_authorized=false`. Publication coefficients for Ottawa, Oklahoma, Klem etc. are never converted to arbitrary direct BNBU treatment gains.

Synthetic parameter ranges are epistemic stress tests — **not** Bayesian credible intervals. A single speed prior or a vegetation association is insufficient for a causal design decision. If sites, seasons, flight posture or optical conditions differ, transportability must be tested, not asserted.