# Independent-animal steering controller inference contract

New module: `birdglass/behavior_fit.py`.

## Causal/measurement requirements

Input records are not arbitrary position traces. Each row requires:
`individual_id`, `trial_id`, `frame`, `heading_yaw_rad`, and
`external_gap_yaw_rad`. The latter must be reconstructed from an
independently measured scene/obstacle field and bird viewpoint. Using the
**future held-out bird trajectory** to retrospectively choose its "intended
gap" would create label leakage and artificially inflate predictive fit.

The response is angular velocity
`wrap(heading[t+1] - heading[t]) / dt`. Candidate controller input
is delayed angular gap error
`wrap(gap[t-lag] - heading[t-lag])`. Candidate gains are constrained
nonnegative; the model is a parsimonious *yaw-only* behavioral baseline.

## Identifiability and validation

- Split by `individual_id` (all its trials held out together), rather than
  randomly splitting frames or holding out only trial IDs.
- Select lag and gain on training birds only, and report held-out losses
  against **both** fitted no-delay control and constant-heading.
- Use the same matched valid timestamps across candidate delays; otherwise
  a larger delay may appear better because difficult early flight frames
  disappeared from the comparison.
- Equalize bird, then trial weights so a bird with more/bigger recordings
  does not dominate model selection by accident.
- Reject duplicate frames; never bridge dropped frames.

## What is NOT claimed

The test generator makes a known artificial controller and verifies
algebraic parameter recovery. **No real annotated flight dataset is
present or fitted.** An estimated lag/gain from one species in an indoor
visible-obstacle tunnel is not a BNBU glass-recognition parameter.
Yaw-only control does not estimate roll, lift, 3D wing pose, luminance
adaptation, or injury severity. These require separate measured sources.

Reference: Lin, Ros & Biewener (2014), J. R. Soc. Interface,
DOI https://doi.org/10.1098/rsif.2014.0239.
Their pooled pigeon pole-flight lag/gain are published study parameters,
not ground truth for an unrelated animal or location.
