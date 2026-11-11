# Bird–Glass Collision Research

Mechanistic, **fixed-facade** research on birds navigating glass and surrounding architecture. We model how habitat cues, specular reflections and transmission, individual flight control, morphology and nearby solid structures can interact, then test whether a *joint* intervention changes the complete route. Replacing glass is outside the research scope.

**Scientific status: computational components and data adapters, not a site-calibrated prediction or authorized installation plan.** An optical image being visible does not mean a bird recognizes the glass or avoids it.

## Executable component chain

| Module | Inspectable function |
| --- | --- |
| `birdglass/scene_optics.py` | 3D finite-pane reflection/transmission, habitat virtual images, bird-facing angular footprint, incidence and solid angle |
| `birdglass/vision.py` | Measured-input reflection/transmission spectrum, species cone catches, contrast proxies and normal pre-impact energy |
| `birdglass/control.py` | Delayed 3D heading control, curvature-constrained turning and open-gap baseline |
| `birdglass/contact.py` | Earliest swept body/wing point contact across glass **and opaque** surfaces |
| `birdglass/policy.py` | Paired full-facade counterfactuals with glass-to-wall risk transfer and non-deployment gate |
| `birdglass/behavior_fit.py` | Lag/gain estimation with **held-out individual birds**, equal time support across lags, and two baselines |
| `birdglass/pose_contact.py` | Column-mapped, metric 3D tracked head/wing/body landmarks and first contact of measured moving keypoint envelopes |
| `birdglass/risk.py` | Event observation identifiability: approach traffic × conditional contact × observer discovery |

Reproduce unit and regression checks:

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests
```

[CI status](https://github.com/starright00631-dev/bird/actions) and [research validation gates](https://github.com/starright00631-dev/bird/issues/1).

## Evidence and scientific boundaries

The following are **different** types of evidence and cannot be collapsed into a calibrated facade collision probability:

- Optical physics and measured material/species spectra, with source details in `docs/SCENE_OPTICS_AND_VALIDATION.md`.
- Published bird avoidance control concepts, with source details in `docs/PRIMARY_LITERATURE_AUDIT.md`.
- External metric 3D flight/keypoint data, with required field mapping in `docs/MEASURED_WING_POSE_ADAPTER.md`.
- Behavior parameter estimation protocol in `docs/BEHAVIOR_FIT_PROTOCOL.md`; unit tests recover known synthetic values, but **no real independent annotated gap-aim flight records have been fitted here**.
- Selected historical numerical sensitivity tests and provenance in `results/` and `docs/`. These are scenario evidence, not BNBU glass-specific forecasts.

The archived larger v0.4 multi-module simulator is **not fully migrated**. See `docs/IMPORT_STATUS.md`. Current source code, not archived numerical output or documentation alone, defines the reproducible implementation.

No personal campus incident reports, identifying respondent details, access credentials or unlicensed raw footage are included. We do not infer bird injury or mortality from translational energy or sampled keypoint contacts. The model explicitly considers low-visual-impact additions and lighting/habitat adjustments, but does **not** authorize any installation without measured context, robust field validation and ecological/safety review.
