# Measured 3D wing-pose contact adapter

This code is a data-to-model interface, not a trained wing biomechanical model.
`birdglass/pose_contact.py` accepts *measured* three-dimensional head, wingtip
and optionally body/tail keypoint tracks. It computes the first continuous
contact of each observed keypoint's swept-radius envelope against all
fixed glass or opaque rectangular surfaces. Contacts are sorted by time
rather than by pane iteration order.

### Why measured wing pose matters

The earlier surrogate held two wingtip locations at a constant fraction of
an assumed wingspan, irrespective of flap/fold maneuvers. This adapter does
not conflate wing chord, an assumed anatomical wingspan, and **observed
distance between wing keypoints**. A wing folded toward the body may
avoid a pane edge which the spread-wing surrogate would flag, or vice versa.

This is a *lower-coverage measurement model*, not a lower collision
probability: 3–5 tracked points cannot capture the whole membrane, wing
bones, deformation or body contact. Thus the output
`collision_free_certified` is always false.

### External data suited to component-specific tests

Ali et al. (2026), *A stereo dataset of annotated budgerigar flight trajectories
for multi-agent collision avoidance studies*, Data in Brief:
https://pmc.ncbi.nlm.nih.gov/articles/PMC13276749/
Dataset https://doi.org/10.5281/zenodo.21796326 (CC BY 4.0).
Reported 360 stereo recordings at 120 fps, with head, tail and both wing
keypoints, reconstructed metric 3D tracks and calibrated camera data.

Use this for **wing kinematics and temporal motion**, not for calibration
of visual glass recognition: its avoidance trials are bird–bird, not
bird–glass. Its interpolation uncertainty and rolling-shutter effects
limit contact precision even with stereo calibration.

Rahman et al., *Budges355* (2023), DOI
https://doi.org/10.17632/p5w3t7vw4f.3, another controlled 3D budgerigar
flight dataset with body/head/tail/wing trajectories, potentially useful
as a separate pose transfer test. Its data are archived in MATLAB rather
than the same 2026 CSV schema; no raw record is present here.

### Required external configuration

The real data's full column names are **not assumed**. Supply a mapping of
landmark names to actual x/y/z fields, real individual and trial IDs,
calibrated-world coordinate frame, m or mm units, frame rate and bounded
per-landmark radii. Fail on duplicate frames and split at missing frames;
do not bridge gaps or infer unseen wing shapes.

These tests use fabricated two-frame tracks to verify physical semantics;
no real dataset has been downloaded or fitted. Any site-level claim
requires independent camera and facade registration with uncertainty
propagation, plus actual birds' approaches and avoidance denominators.
