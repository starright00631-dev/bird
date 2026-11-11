# Spectral vision, bird morphology, and pre-impact mechanics

Implemented in `birdglass/vision.py`. Four verifiable layers are kept
distinct: external field radiance from mirror/transmission directions,
material reflectance/transmittance, receptor-specific photon catches, and
kinematic collision energy. **None** is a calibrated recognition probability.

## Equations and units

- Incident radiance at the eye: `L(λ) = R(λ,θ)L_reflected(λ) + T(λ,θ)L_transmitted(λ)`. The functions accept measured spectra, *not* images interpreted as if they were spectrometer output. For real double glazing, use measured whole-assembly properties, not the ideal single-boundary Fresnel approximation.
- Relative photon catches per receptor `Q_i ∝ ∫ L(λ) S_i(λ) λ dλ`. Wavelengths are nm. Relative units cancel in ratios when the same calibration applies; absolute photon quantum counts are not estimated.
- Chromatic proxy: log catch differences with the common brightness offset projected out using inverse-variance receptor noise. These are noise-scaled units, **not** a validated just-noticeable difference or collision prediction.
- Pattern periodicity: measured/assumed physical repeat spacing `s` seen from distance `d` corresponds to `1 / (2 atan(s / (2d)) [degrees])` cycles/degree. Passing an individually measured acuity threshold is only a **necessary** condition, not sufficient for awareness/avoidance.
- Normal translational pre-impact kinetic energy proxy: `E_n = 0.5 m (v · n)^2` in joules. Does not estimate force, impulse, neck motion, wing deformation, injury or survival.

## Published experimental anchor and domain cautions

- Håstad & Ödeen (2014), DOI `10.7717/peerj.621`: UVS and VS bird visual systems differ substantially. A nominal UV mark cannot be treated as equally visible to all species under all illumination/vegetation backgrounds.
- Swaddle et al. (2020), DOI `10.7717/peerj.9926`: in *protected-window* trials involving zebra finches, 'would collide' judgments were 17/20 for both control windows and 8/19 for both externally treated windows. Under the protected setup birds approaching treated windows also slowed around 25%; this is **not measured wild death or site-level efficacy**. The repeated bird design and unequal trial counts preclude naive independent-binomial inference from the totals. Forced-choice and uniform-treatment contrasts have different estimands and must NOT be pooled.
- Swaddle et al. (2023), DOI `10.7717/peerj.14676`: exterior versus interior placement of films led to very different avoidance in an aviary. Exterior optical behavior cannot be assumed for a film behind reflective glazing.
- Samuels et al. (2022), DOI `10.7717/peerj.14604`: 29 selected collisions and nine selected near misses were recorded; 29/38 is not a probability of a collision among all approaching birds.

## Architectural consequence: do not replace glass

For a bridge, evaluate through-vision and reflected-scene geometry separately.
For LRC curtain walls, consider angle-dependent reflection, receptor contrast,
adjacent-surface displacement and visual burden. For ground-floor dorms, measure
actual species-specific optical cues, incoming habitat routes and facade exposure,
not simply the presence of trees. Exterior screens/cords/shading and seasonal
light management remain possible candidate interventions, but their optical
and behavioral effects must be separately measured. No material is proposed
for installation without calibration and field evidence.

## Missing evidence and required adapter inputs

Per relevant species: independently sourced cone sensitivity curves,
photoreceptor noise/adaptation, and behavioral contrast–avoidance validation.
Per pane/time: bidirectional calibrated spectral radiances in relevant
reflected and transmitted directions, whole-assembly spectral R/T, angle,
season/light/weather condition. Per approach: morphology, mass, 3D
velocity, collision outcome and route denominator.

Do not backfill missing measurements with convenient global probabilities.
