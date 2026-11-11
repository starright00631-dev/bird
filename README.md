# Bird–Glass Collision Research

This repository contains research code and inspectable evidence for **fixed-facade bird–glass collision mechanisms**. The scientific goal is to explain how bird movement, visual perception, glass and structural geometry, habitat and intervention choices interact to produce or avoid collisions. There is no proposal to replace glass.

## Executable code

- `birdglass/contact.py`: finite-pane swept body/wing geometry and **earliest contact time across all surfaces**, to prevent contact attribution based on iteration order.
- `birdglass/risk.py`: collision-observation identifiability checks and paired, all-structure counterfactual effects.
- `birdglass/control.py`, `birdglass/policy.py`: delayed 3D flight control and paired whole-facade replay; tests separate glass and opaque contact. Large panes use their full angular footprint instead of only their centre.\n- `birdglass/vision.py`, `birdglass/scene_optics.py`: supplied-measurement receptor calculations, finite-patch reflection/transmission geometry and geometric optical ray audits; behavior recognition is still uncalibrated.\n- `tests/`: physical invariants, geometry, controller-latency and optical visibility regression tests.

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests
```

## Research documentation and evidence

`docs/ARCHITECTURE.md`, `docs/CAUSAL_MODEL_AND_MEASUREMENT.md`, `docs/RESEARCH_GATES.md`, `docs/SOURCE_REGISTER.csv`, and the `results/` folders record the earlier, more extensive model study and its synthetic stress tests. **The complete previous simulator has not yet been imported into the present repository.** The code currently present comprises geometry, optics, sensory-input, motion and paired-replay kernels, but only partial historical import; it should not be mistaken for the full coupled perception-and-control simulator described in the research documents.

## Scientific status and limits

This is **not** a validated prediction model for BNBU facades. Simulated flights and treatment effects are hypotheses; the public observational study only supports its own detection/survey context. Without independent approach denominators and visually verified avoidance/collision trajectories, incident counts cannot identify facade-level conditional collision probabilities. No real installation is authorized by these tests.

Do not include raw personally identifying campus incident submissions or source data without permission and license checks. See `docs/VALIDATION.md`.
