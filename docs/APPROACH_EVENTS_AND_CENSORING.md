# Camera-backed bird approaches: at-risk definition, censoring and optics

## Why this is necessary

Samuels, Fenton, Fernández-Juricic and MacDougall-Shackleton
(2022), *Opening the black box of bird-window collisions*, PeerJ 10:e14604,
https://doi.org/10.7717/peerj.14604, report **29 collisions and nine near
misses** from selected video events. At least nine additional flybys not
on a collision course were excluded. Their near miss definition required
an initially window-directed path, followed by observed redirection within
about 2 m. The full 38 events are therefore not a random sample of all
bird traffic, and 29/38 is not the unconditional probability of collision.
See peer-reviewed Methods and Supplemental Information 4 (coded event CSV):
https://pmc.ncbi.nlm.nih.gov/articles/PMC9784330/

## Executable measurement adapter

`birdglass/approach_events.py` accepts a full, calibrated metric
`frame,x_m,y_m,z_m` track, known frame rate, unique finite glass/opaque
surfaces (any 3D orientation), and **independently** verified video labels.

1. Detect a physically inbound crossing of a *stated* observation gate.
2. From the gate entrance, extrapolate **only the prior/current motion**:
   is there a first swept body-sphere contact with some glass patch
   within a stated future horizon? If not, the flight is a flyby, not
   a confirmed avoidance; if an opaque structure is first, it is not
   attributed to glass.
3. Scan the actual later track for geometry-estimated contacts against
   **all** provided surfaces. This is a proxy, not a video-confirmed strike.
4. A negative requires reviewed video, complete continuous recording
   past the counterfactual contact time plus explicitly stated follow-up,
   and no competing geometry contact. Missing frames or early camera exit
   are **right-censored**, never counted as successful avoidance.
5. Optionally join *only* geometry-compatible habitat reflection or
   transmission rays at the same entry state. Their existence does not
   imply species recognition, attraction or action efficacy.

Annotation can confirm glass, opaque contact or no contact. The
measurement system never turns geometry-only contact into an independently
verified outcome. Conflicts with scene calibration are returned for review.

## Hard limits and next validations

- A gate-based ballistic reference is a declared *operational estimand*,
  not what the animal consciously intended to do. Other gate radii must
  be evaluated (e.g., 1, 2, 3 metres) to check sensitivity.
- Positions/trajectory must share a surveyed coordinate frame with pane
  geometry; inherited unsurveyed campus meshes are **not eligible**.
- It uses a body-sphere proxy. Full dynamic wing-body contact requires
  measured articulated pose and surface visibility calibration.
- A negative requires documented camera coverage. Continuously recorded
  clips and motion/audio-triggered collision clips have different
  inclusion probabilities and must not be naively pooled.
- Even a perfect set of selected at-risk clips does not estimate the
  population collision incidence without a known approach sampling frame
  and calibrated event-detection/clip-selection probabilities.
- Coded outcome video evidence must be reviewed by independent observers.
  No real local video labels or supplementary raw rows have been inserted.
- Repeated birds and clips from one camera/building need hierarchical
  group splits; neither individual independence nor species transfer can
  be assumed.

## Model coupling

`birdglass.scene_optics.scene_path_table` provides the reflection/see-through
view of vegetation for each gate crossing, but optical geometry is not
a substitute for real bird visual adaptation and behavior.
The event adapter can later serve independent validation for
`behavior_fit`, `control`, `policy` and `pose_contact` without
retraining on the small set of BNBU anecdotal reports.

The example tracks in unit tests are artificial and test algorithm
semantics only; NO collision probability has been fitted here.
