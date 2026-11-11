# Validation contract

The code models *first physical contact* against fixed glass and opaque
rectangles using a simplified swept body-and-wing envelope, not observed
collision or injury rates. Contact time is computed on each segment and the
earliest of all pane and wing/body candidates is reported. This corrects
order-dependent pane attribution in a simple first-hit simulator.

**The model is intentionally incomplete.** Without source measurements for
approach traffic, species-specific motion, optical recognizability, and
intervention response, a collision-risk estimate is not identified. Incident
reports alone identify only the product of encounter, collision and detection.

Reproduce: `python -m pip install -r requirements.txt && python -m pytest -q`.

## Uncertainty and falsification

- Fit time delay and heading gain on independent individuals, never random
  frames from the same flight on both train and test sets.
- Compare to unchanged-velocity, obstacle-agnostic, and nearest-gap controls.
- Evaluate all structure contacts and transferred risk, not glass alone.
- Stratify transfer by bird morphology, illumination, habitat and season.
- Calibrate treatment benefits using comparable independent studies or local
  field experiments before giving actionable installation advice.

No raw campus submissions, personal identifiers, or unlicensed raw recordings
are distributed in this repository.
