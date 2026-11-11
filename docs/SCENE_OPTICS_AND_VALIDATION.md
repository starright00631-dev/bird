# Finite-facade ray optics: geometric and physiological gates

**Implemented:** `birdglass/scene_optics.py` supports an arbitrary orthogonal
planar rectangular facade patch, not only facade-normal x-axis panes. The
calculation separates the **virtual image of reflected foreground habitat**
from **transmitted rear habitat**. A ray must actually hit the finite pane;
opaque nearer structures can block it. Per-patch view angle and solid angle
are computed, and the result can be joined to measured full-assembly
spectral R/T and species cone sensitivity using `birdglass/vision.py`.

These features repair a critical explanatory gap: a tree near a building is
**not automatically visible on each glass pane**. Visibility depends on the
bird's viewpoint, the pane orientation, finite extent and the source location.

## Optical quantities, not behavioral predictions

- `scene_ray`: reflection/transmission geometric existence, hit point,
  incidence angle, gaze angle and source angular size. Scene sources are
  represented by centers and approximate radii; no occlusion by foliage
  within an object, material BRDF, gloss roughness or image segmentation.
- `pane_solid_angle_sr`: exact solid angle for a planar finite rectangle.
- `minimum_heading_angle_deg`: smallest gaze-heading deviation to *any*
  point on a finite pane; centre-only tests are invalid for large curtain walls.
- `measured_pixel_cone_catches`: requires both ray types from **the same
  surface pixel**, measured spectral radiances, true whole-glazing spectral
  reflectance/transmittance, and measured species-specific receptor responses.

A ray's existence or receptor contrast is **not an observed attraction
probability, recognition probability, or intervention effectiveness**.
All of those must be identified from documented approaches/avoidances with
a valid sampling denominator and an independent species holdout.

## Research anchor, not parameter transfer

Håstad & Ödeen (2014), PeerJ 2:e621, DOI
https://doi.org/10.7717/peerj.621, measured spectra of real glazing,
sky, cloud and vegetation, and modelled VS versus UVS receptor responses.
They showed strong dependence of ultraviolet-pattern visibility on
species visual physiology and natural background structure. Their models
do not directly supply a universal avoidance probability, and their
sampling location is not a proxy for south-China habitat.

Swaddle et al. (2023), PeerJ 11:e14676, DOI
https://doi.org/10.7717/peerj.14676, used repeated measures on captive
zebra finches with external versus internal window treatments. Their
tunnel studies support explicitly representing **which side of the glass**
alters the optical signal. The extrapolated flight path and safety net are
not equivalent to observed wild-bird fatality rates. Avoid naïve pooling
of correlated repeated trials.

## Falsification / coupling roadmap

1. Register photogrammetry-derived pane coordinate frames to real campus
   images/photometric observations; compare predicted image locations to
   field-calibrated imagery across held-out viewpoints.
2. Compare predicted angular scene appearance, measured spectral responses
   and observed birds' routes, with eye direction unknown unless recorded.
3. Only after observed trajectories exist, fit behavioral recognition /
   avoidance parameters on independent birds, and route those estimates
   into `control.replay`. Do not transform geometric visibility to a
   fabricated probability.
4. Compare existing facade-adjacent shading/cord/lighting solutions as
   optical/behavioral *mechanisms*, with glass replacement excluded.

Source: structural simulation; 11 geometry/optics tests. Not BNBU risk
calibration or installation permission.
