## BNBU v69 — evidence-aware waterfront refinements (current)

The [v69 full offline release](https://github.com/starright00631-dev/bird/actions/runs/43143405025) now packages the complete model, a single double-click HTML viewer, and source/evidence/metadata for reproducibility. Download the CI artifact named **BNBU-v69-complete-offline-model-zip**, extract the nested `BNBU_Campus_Full_v69.zip`, then open `双击查看_校园3D.html` locally. Browser tests pass for both a standalone offline file and localhost viewer. The source changes are in [PR #6](https://github.com/starright00631-dev/bird/pull/6).

v69 makes **appearance-only edits** to inherited lake/shore/wetland geometry: independent PBR styles on five inherited lake water entities and the separate archived wetland, height-toned existing banks, display-only subtle ripple normals and existing walkway edge highlighting; a close-up lakefront initial camera view plus synchronized GIS focus. The original 1,377 mesh positions/indices, 522 GIS source features and separate v67 ALOS surface-reference data are retained. Official [2019 BNBU ecology report](https://www.bnbu.edu.cn/info/1077/4589.htm) records a natural seasonal wetland at Chihua Hill connected to **two freshwater ponds**, but their geolocated outlines are **not** verified. Do not equate them with the historical Phase II wetland mesh or interpret v69 as a surveyed shoreline/bare-earth terrain, glass area or bird-strike exposure map. See [waterfront evidence and limitations](campus/WATERFRONT_V69_EVIDENCE.md).

---

## Archived v68 interface release

**The archived v68 interface and complete model ZIP are built and published by [BNBU complete offline interface and ZIP](https://github.com/starright00631-dev/bird/actions/workflows/campus-package.yml).** Download the latest successful run's artifact named BNBU-v68-complete-offline-model-zip, then extract the nested BNBU_Campus_Full_v68.zip.

Open the extracted **双击查看_校园3D.html** directly in a modern browser (Chrome/Edge): it contains all necessary three.js code, v66 GLB, GIS and independent v67 DSM **offline, with no server or CDN**. Alternatively launch 启动查看器.bat to serve index.html locally with Python 3.

The reproducible viewer source lives in [campus/interface/](campus/interface/). A real Chromium browser CI tests both file:// and localhost startup, switching the campus/DSM scenes, all ten layers and the GIS data. Original v64 GLB/GPKG/GeoJSON/KML, v65 history, v66 model, v67 remotely sourced DSM, quarantined unverified CTV hypotheses, hashes and build code are included in the full ZIP. No new surveyed model geometry is asserted by the interface repair.

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
| `birdglass/reachability.py` | Optional forward-screened gap planning, with finite latency/acceleration and full structural collision checks |
| `birdglass/source_splits.py` | Real 3D-POP trial/video/subject overlap graph and leakage-safe source folds |
| `birdglass/stereo_tracks.py` | Published 2026 bird-flight wide-CSV schema to metric pose tracks, strictly separating mm positions and pixel sizes |

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

The 3D-POP source is mainly pigeon **ground/locomotor posture**, not flight or glass avoidance. Its real metadata are used **only to audit evaluation leakage**. The 2026 stereo bird-flight CSVs have a schema adapter but the raw files are not yet in this repository.

The archived larger v0.4 multi-module simulator is **not fully migrated**. See `docs/IMPORT_STATUS.md`. Current source code, not archived numerical output or documentation alone, defines the reproducible implementation.

No personal campus incident reports, identifying respondent details, access credentials or unlicensed raw footage are included. We do not infer bird injury or mortality from translational energy or sampled keypoint contacts. The model explicitly considers low-visual-impact additions and lighting/habitat adjustments, but does **not** authorize any installation without measured context, robust field validation and ecological/safety review.


## BNBU campus 3D scene (v66 evidence-linked semantic GIS / 3D)

The complete inherited v64 campus meshes and editable GIS source are stored in [`campus/`](campus/README.md). The v66 builder produces a physically categorized GLB with ten named scene layers, retaining the original 1,377 meshes and restoring 112 render associations (10 water/shore + 96 stair + 6 at-grade links). This is a scene-structure and source-link repair, **not a surveyed reconstruction**. The CTV “校长别墅” candidate remains excluded. Hill elevations are relative, water boundaries and driveways are not independently surveyed, and no glass area is calibrated.

Run `python campus/build_v66.py && python -m unittest discover -s campus -p 'test_v66.py' -v`, then `python -m http.server 8000`; open `http://localhost:8000/campus/viewer.html` to inspect the complete layered 3D model and GIS evidence. GitHub Actions produces downloadable generated GLB, GIS and provenance artifacts.


## Verified external bird–window video benchmark

The source-audited 2022 PeerJ study's **38 selected cases** (29 contacts,
9 near misses; only 36 rows with complete speed/angle/time predictors) are
reprocessed directly from the NIH PMC versioned public supplement and
cross-checked with the authors' published R-analysis file. The source has
the exact SHA-256 \`0e33f97b007bb5f479ebe45abd76680c2ff36ea92f0280f6ead48e708af6cf35\`.

**Falsification result:** when species are held out in entire groups, a
speed+angle+hour logistic model yields Brier 0.2386 versus 0.2170 for
the smoothed train-only intercept. Leave-calendar-year-out is 0.2568
versus 0.1939. This means that **this small selected case table does not
support a transferable predictive classifier**, let alone a panel-level
collision probability. Real 3D approach/avoidance tracks and independent
bird-visible optical conditions remain mandatory.

- Analysis, original paper discrepancy and full limits:
  [real video case benchmark](docs/REAL_CASE_VIDEO_BENCHMARK.md).
- Executable code: \`python -m birdglass.video_case_benchmark --input ORIGINAL.csv --output report.json\`.
- [Evidence workflow](https://github.com/starright00631-dev/bird/actions/workflows/inspect-samuels.yml)
  retrieves/checksums the original public CSV and published R code,
  validates source rows and publishes the inspectable output artifact.
- \`birdglass/approach_events.py\` operationalizes at-risk approach
  gates, finite-3D-facade ballistic intercepts, source-video verified
  outcomes and **right-censoring** for missing camera coverage.
  It does not infer behavior or site risk from a mirror ray alone.
