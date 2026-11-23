# BNBU Bird–Glass Collision Research

Evidence-led research to explain **where, why and under what conditions birds collide with glass**, and to compare interventions for existing façades. The goal is a transparent, testable decision system—not a single opaque risk score or an unsupported end-to-end claim.

> **Status (2026-11-23).** The BNBU pane pilot has executable intake, synthetic monitoring and a source-linked assessment. BNBU field validation and treatment evaluation are pending. The pinned UBC model remains a descriptive benchmark after its held-out comparison with the exposure-only baseline.

## Model architecture

1. **Bird availability/activity:** species or guild, season, time, resources, weather and migration.
2. **Approach flow:** canopy, terrain, water, corridors, façade geometry and all at-risk approaches.
3. **Glass optics:** transparency, external reflection, reflected habitat, transmitted false passage, coatings and view/illumination.
4. **Flight/contact:** trajectories, morphology, perception/avoidance evidence, glass contact and opaque contact.
5. **Observation:** carcass persistence, searcher detection, reporting effort, censoring and missingness.
6. **Intervention:** exterior markers, screens/cords, shading, lighting and supplementary interior changes.

The output is a **pathway profile plus an evidence-gated intervention comparison**. Absolute collision rates require effort-corrected approach flow and independently observed outcomes. Injury probability is a separate endpoint.

## Implemented components

| Code | Responsibility |
|---|---|
| `birdglass/scene_optics.py` | Finite-pane reflection/transmission geometry |
| `birdglass/vision.py` | Measured-input spectra and species cone catches |
| `birdglass/control.py`, `contact.py`, `pose_contact.py` | Flight-control/contact mechanics |
| `birdglass/risk.py`, `approach_events.py` | Observation identifiability and approach censoring |
| `birdglass/source_splits.py`, `stereo_tracks.py` | Leakage audit and external trajectory schema |
| `birdglass/solar.py` | Approximate ENU sun position and specular geometry |
| `birdglass/evidence.py`, `glazing.py`, `vegetation.py`, `decision.py` | Canonical evidence tiers, glazing, five non-overlapping vegetation bands and conditional decisions |
| `birdglass/glass_observation.py`, `vegetation_observation.py`, `facade_decision_report.py` | Human/spec/instrument intake adapters into the canonical façade decision engine |
| `birdglass/glass_image_classifier.py`, `vegetation_segmentation.py` | Optional pinned CLIP photo triage and provenance-aware summaries of supplied annular masks (not segmentation inference) |
| `birdglass/uvic_panel.py` | Pinned UVic source verification, facade-period aggregation and observed-evidence Poisson GEE baseline |

The façade decision layer separates measured evidence from proxies, reflection from through-glass false passage, local canopy from landscape cover, selected clips from continuous approach video, and mechanism fit from measured intervention efficacy.

## Pane pilot and reproducibility

- [Pane registry and glass intake](docs/BNBU_PANE_REGISTRY.md) define the join across building, façade, physical pane and geometry version. The checked-in adjacent panes are synthetic. T29 and LRC are candidates for on-site verification.
- [Pane vegetation summaries](docs/PANE_VEGETATION.md) preserve five reviewed cover bands, dated reflection views and independent approach-monitoring sources. The same pane key keeps adjacent windows' evidence separate.
- [Monitoring pipeline](docs/BNBU_MONITORING_PIPELINE.md) runs an optical and first-contact replay, audits censoring and survey zeros, and evaluates exposure-only baselines with held-out buildings and later time blocks. The [scientific workflow](https://github.com/starright00631-dev/bird/actions/workflows/pytest.yml) exercises the synthetic replay and the empty local intake through the test suite.
- [Retrofit trial preregistration](docs/BNBU_RETROFIT_TRIAL.md) records matched controls, effort, adjacent-surface monitoring and safety or ecological vetoes. The output gives first-test candidates and the evidence needed to compare effects.
- [Policy stress replay](docs/IMPORT_STATUS.md) fixes the simulated pane draw order and records current source, input and output hashes. The archived historical simulation and independent local motion validation remain open.
- The [BNBU pilot roadmap](https://github.com/starright00631-dev/bird/issues/29) tracks the first independently locatable field walkthrough and the evidence needed for site-specific decisions.

## Not yet implemented or calibrated

- BNBU-calibrated glass/vegetation collision model with held-out-building/site validation.
- Automatic vegetation segmentation inference; the current mask utility only summarizes externally produced, human-QA masks.
- Harmonized external training table with comparable survey effort and non-event observations.
- Full detection-corrected GenEst/JAGS reproduction and a BNBU-calibrated GAMM/GLMM with measured glass and vegetation predictors.
- Trained CatBoost/Random Forest challenger model.
- BNBU-specific causal intervention effects or pane-level calibrated risk.
- BNBU pane geometry, measured full-assembly spectra and continuous approach denominator.

These are engineering gates, not features to infer from the current rule engine.

## Evidence and data

See the [final model specification](docs/FINAL_MODEL_SPECIFICATION.md), [glass observation template](data/templates/facade_glass_observations_template.csv), [vegetation exposure template](data/templates/facade_vegetation_exposure_template.csv), [approach-monitoring template](data/templates/facade_approach_monitoring_template.csv), [machine-readable intervention evidence](data/reference/intervention_evidence.csv), [data registry](docs/data_registry.csv), [source register](docs/SOURCE_REGISTER.csv), [experiment ledger](docs/EXPERIMENT_LEDGER.csv), [research gates](docs/RESEARCH_GATES.md), [intervention evidence matrix](docs/INTERVENTION_EVIDENCE_MATRIX.md), [UBC data audit](docs/UBC_DATA_AUDIT.md), [BNBU local-data audit](docs/BNBU_LOCAL_DATA_AUDIT.md), and [shared coordination log](docs/COORDINATION_LOG.md).

- UVic: 6,337 raw source rows collapse to 6,298 unique facade-day visits across 50 facades, 6 buildings and 6 survey windows. A pinned adapter builds 300 facade-period rows, a descriptive effort-offset Poisson GEE and an NB2 sensitivity check. A separate adapter audits 79 searcher-efficiency trials, 82 carcass-persistence trials and 126 scheduled survey dates. This validates the observation layer, not BNBU pane risk or glass/vegetation effects; full GenEst/JAGS refit remains pending. See [UVic reproduction and model notes](docs/UVIC_REPRODUCTION_AND_MODEL.md).
- Neotropical database: 4,103 event reports and 571 species; event-only, no non-event denominator.
- China 2025: 3,078 buildings; useful for multi-scale habitat hypotheses, not local causal effects.
- Ottawa 2026: 225 collisions and 51 species; treatment compliance evidence, site-specific.
- Oklahoma 2026 BACI: 6 treated and 134 untreated façades; field design benchmark, but low treated replication and a non-significant formal treatment-by-period interaction.
- UBC 2021 De Groot: all six Dryad files are checksum-verified in CI; 8,846 collision rows resolve to 8,831 facade-date keys, 152 fatality events and 142 positive visits. The 103 persistence trials, 29 search-efficiency trials, 155-date schedule and 303 point-count species rows are audited. Raw files remain in a 30-day CI artifact, not Git. This is the observation-process benchmark, not yet the final façade feature model.
- UBC 2023 Zulian: Appendix 1 is a complete 8,835-row panel (57 façades x 155 dates) with 152 carcass-mortality events and 142 positive visits. It includes FACADE_AREA, AREA_GLASS, façade-level porous-cover and tree-cover percentages, STORIES_REFLECT_CANOPY (continuous; fractional source values retained), METHOD and both collision outcomes. Its SHA-256 and full panel grain are pinned in CI. The seasonal GLMM reproduces the paper's AICc support pattern, but leave-one-building-out tests do not consistently beat an exposure-only baseline (pooled Brier is worse in all four seasons); retain it as a descriptive UBC benchmark, not a transferable predictor. The separate De Groot CSV is not row-joined.
- 2026 stereo bird-flight data: 360 retained trials at 120 fps; kinematics only, not glass recognition.

Sources are not pooled merely because they all concern bird collisions. Grain, effort, outcome definition, species mix and observation process must first be harmonized.

## BNBU local records: localization, not training

The supplied source contains 48 submissions, 47 collision reports after excluding one near-miss report, and 50 reported birds; at least two events are suspected. The 38-entry microzone catalogue is a field-audit queue: no candidate currently has verified pane geometry or an identified impact surface.

These opportunistic reports do not provide pane IDs, standardized zero surveys, approach denominators or consistent carcass/searcher-detection estimates. They cannot train a calibrated rate model. See [BNBU local-data audit](docs/BNBU_LOCAL_DATA_AUDIT.md). Raw records containing submitter identifiers are not committed.

## Quick start

Python 3.11 is used in CI.

~~~bash
python -m pip install -r requirements.txt
python -m pytest -q tests

# Replay the synthetic pane monitoring pipeline without a field dataset
python -m birdglass.bnbu_monitoring data/examples/synthetic_bnbu_monitoring.json monitoring-demo

# Rebuild the pinned UVic facade-period panel and fit the observed-evidence baseline
python scripts/build_uvic_facade_panel.py --fetch-pinned
python scripts/audit_uvic_detection_trials.py --fetch-pinned
python scripts/fit_uvic_observed_rate.py
~~~

Minimal façade assessment:

~~~python
from birdglass.decision import FacadeContext, evaluate_facade
from birdglass.evidence import EvidenceTier, Measurement
from birdglass.glazing import GlassAppearance, GlassPanel
from birdglass.vegetation import VegetationProfile

glass = GlassPanel(
    panel_id="example-pane-01",
    appearance=GlassAppearance.REFLECTIVE_AND_TRANSPARENT,
    exterior_vlr_pct=Measurement(
        18.0, "percent", EvidenceTier.MEASURED,
        source_id="replace-with-instrument-record",
    ),
)
vegetation = VegetationProfile(
    cover_pct={
        "0_5m": Measurement(32.0, "percent", EvidenceTier.REMOTE_SENSING),
        "1_10km": Measurement(61.0, "percent", EvidenceTier.REMOTE_SENSING),
    }
)
result = evaluate_facade(FacadeContext(glass=glass, vegetation=vegetation))
print(result["intervention_comparison"])
~~~

Example values are placeholders, not BNBU measurements. The comparison reports mechanism fit and evidence gaps; it intentionally returns no best option or local percentage reduction without comparable outcome data.

## Repository map

- `birdglass/`: executable mechanism, measurement and decision modules.
- `data/external/`: public metadata/QA artefacts; `data/raw/`: checksum-pinned public source snapshots with provenance.
- `docs/`: causal model, literature audit, registries, intervention evidence and validation gates.
- `results/`: scenario/sensitivity outputs; not observed field data.
- `scripts/`: source audits and reproducibility helpers.
- `tests/`: scientific invariants and regression tests.
- `campus/`: separate campus 3D visualization workstream. Its geometry is not a measured bird-collision exposure layer.

## Validation rules

- Missing values remain missing, never silently zero.
- A collision report is not a surveyed zero or approach denominator.
- Vegetation remains at 0–5 m, 5–25 m, 25–100 m, 100 m–1 km and 1–10 km; no universal signed score.
- The 2x2 pattern check is an ECCC general-guidance screen, not ABC Threat Factor certification. The 2x4 check is spacing geometry only.
- Intervention comparisons require matched/randomized before-after control-impact monitoring and explicit safety/ecological constraints.
- Validation holds out birds, façades/buildings, sites and time blocks as appropriate; random row splits are insufficient.

## Separate campus 3D project

The viewer and source evidence are documented in [campus/README.md](campus/README.md). The campus scene may later supply verified pane geometry and approach-view registration, but is not a prerequisite for the external-data model.

### 空间研究工作台与 AI 对话

右侧默认显示 AIP 对话，选择「模型数据」可打开原有 GIS、图层和证据面板。设置按钮支持配置 OpenAI 兼容 API 基础地址、模型 ID 和 API Key，默认使用 DeepSeek 的 `https://api.deepseek.com` 与 `deepseek-flash`。密钥只保存在当前页面内，刷新后需重新输入；对话直接从浏览器发送给所配置的服务，服务须支持浏览器跨域（离线 HTML 的 `file://` 来源尤其需要服务商允许）。3D 模型仍可离线使用，AI 对话需要网络和有效密钥。发送时包含当前场景、选中对象的显示信息和对话内容；请勿发送不愿提供给服务商的数据。模型无法自动读取整个场景或证据库，回答须结合研究资料核验。

## Next build sequence

1. Complete the BNBU pane inventory with human-reviewed glass appearance, coating position, full-assembly VLR/VLT or spectral R/T, marker geometry and source photos/specifications.
2. Populate the five non-overlapping vegetation bands plus façade-specific 50-m porous/tree cover, canopy height/distance, vertical reflection context and measured reflected-scene share.
3. Run standardized pane-level patrols and continuous-video sampling with explicit zeroes, comparable effort, all at-risk approaches, glass/opaque/no-contact outcomes and censoring.
4. Add local searcher-efficiency and carcass-persistence trials, then fit BNBU seasonal GLMM/GAMM baselines with measured glass × vegetation interactions.
5. Compare ML challengers using held-out buildings and time blocks; calibrate only on BNBU data.
6. Compare retrofit candidates with matched/randomized BACI and cost/safety/ecological constraints. Do not transport external efficacy percentages.
