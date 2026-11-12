# External source fit: real metadata vs real flight frames

## 1. Genuine 3D-POP source audit (not synthetic data)

The included `data/external/3dpop_public_metadata.csv` is copied with
attribution from the published open repository
`alexhang212/Dataset-3DPOP/Dataset/Pop3DMetadata.csv`, Naik et al.,
*3D-POP*, CVPR 2023.

Its 59 metadata rows contain **57 source subject-session labels**, of which
**54 appear in more than one metadata row**. **18 rows reuse a previously
seen same-date, same-trial, same-video source identifier**. A source-safe
graph split yields component sizes **11, 11, 11, 11, 8, 5, 2**. These values
are computed from REAL metadata in `source_splits.py`, and verified with
a frozen regression test.

**Interpretation**: a random *row* split or even random *trial* split may
put the same source recording / documented pigeon within both sets,
inflating generalization scores. The graph split keeps such source groups
intact, but a bird may receive new names across recording dates: this
dataset does NOT certify all cross-date physical identities.
The registry itself has no 3D position rows: do not report this audit as
a flight-model fit or collisional validation.

## 2. Published stereo 2026 source schema

Tawhid et al. (2026), Data in Brief 67, 112956,
DOI https://doi.org/10.1016/j.dib.2026.112956,
report 360 synchronized stereo pair recordings at 120 frames/s.
Table 3 lists `Frame` (0-based), `B1_Box_X/Y/Z`,
`B1_Head_X/Y/Z`, `B1_Tail_X/Y/Z`,
`B1_LeftWing_X/Y/Z`, `B1_RightWing_X/Y/Z`.
Additional `B1_Box_W/H` fields are **pixels**, while all 3D
positions above are **millimetres**. The schema repeats for B2..B6.

`stereo_tracks.py` uses those **published** field names directly;
it preserves mm, missing keypoints and source trial labels, and exposes
finite difference speed diagnostics in m/s. B1..B6 refer to identity
consistent *within one stereo recording*, and cannot establish a real
bird's identity across multiple recordings. The adapter **rejects** an
unsupported independent-individual claim.

Paper data repository DOI in the publication is
https://doi.org/10.5281/zenodo.19712127; an NLM record also indexes
https://doi.org/10.5281/zenodo.21796326. Version correspondence must
be resolved from original repository metadata before pinning raw hashes.

**Actual flight CSVs remain unimported**. Two-frame regression fixtures
only validate field/units semantics. Estimated finite-difference
accelerations amplify stereo triangulation noise; filter/uncertainty
propagation is needed before physics fitting.

## 3. Next falsifiable experiments

- Acquire licensed raw stereoscopic CSV batches, verify coordinates
  and calibration, compare original source track groupings with
  independent bird IDs if published.
- Fit basic speed/acceleration/wing span distributions and evaluate
  held-out biological individuals, not merely held-out clips.
- Then connect bird-approach/avoidance videos with *real window geometry*
  and species-conditioned optics, estimating perception and behavior
  separately. Bird–bird avoidance can train kinematics, not glass
  recognizability.
