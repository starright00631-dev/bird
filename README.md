# BNBU Bird–Glass Collision Research

Evidence-led research to explain **where, why and under what conditions birds collide with glass**, and to compare interventions for existing façades. The goal is a transparent, testable decision system—not a single opaque risk score or an unsupported end-to-end claim.

> **Status (2026-11-16):** executable mechanistic components and an evidence-aware façade decision prototype exist. This is not yet a trained, site-calibrated BNBU collision model. DINOv2 glass recognition and automatic vegetation segmentation are not implemented.

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
| `birdglass/evidence.py`, `glazing.py`, `vegetation.py`, `decision.py` | Evidence tiers, glazing, five vegetation scales and conditional decisions |

The façade decision layer separates measured evidence from proxies, reflection from through-glass false passage, local canopy from landscape cover, selected clips from continuous approach video, and mechanism fit from measured intervention efficacy.

## Not yet implemented or calibrated

- DINOv2/ViT/CNN glass-image classification.
- Automatic tree-crown segmentation, NDVI and multi-buffer remote-sensing extraction.
- Harmonized external training table with comparable survey effort and non-event observations.
- Fitted hierarchical Poisson/negative-binomial GAMM/GLMM for façade collision rates.
- Trained CatBoost/Random Forest challenger model.
- BNBU-specific causal intervention effects or pane-level calibrated risk.
- BNBU pane geometry, measured full-assembly spectra and continuous approach denominator.

These are engineering gates, not features to infer from the current rule engine.

## Evidence and data

See [data registry](docs/data_registry.csv), [source register](docs/SOURCE_REGISTER.csv), [research gates](docs/RESEARCH_GATES.md), and [intervention evidence matrix](docs/INTERVENTION_EVIDENCE_MATRIX.md).

- UVic: 6,337 façade surveys and 756 building-days; useful for effort/detection modeling, not BNBU pane risk.
- Neotropical database: 4,103 event reports and 571 species; event-only, no non-event denominator.
- China 2025: 3,078 buildings; useful for multi-scale habitat hypotheses, not local causal effects.
- Ottawa 2026: 225 collisions and 51 species; treatment compliance evidence, site-specific.
- Oklahoma 2026 BACI: 6 treated and 134 untreated façades; field design benchmark, but low treated replication and a non-significant formal treatment-by-period interaction.
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
- `data/external/`: public metadata/QA artefacts only.
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

1. Complete façade decision tests and evidence contracts.
2. Acquire/harmonize external façade survey and treatment data with effort/detection metadata.
3. Build human-audited image/remote-sensing feature extraction and site-held-out validation.
4. Fit interpretable count/rate models with exposure offsets before predictive challengers.
5. Estimate treatment effects only from comparable field designs and produce an uncertainty-aware multi-objective frontier.
6. Use BNBU field verification to localize and calibrate, not to manufacture accuracy from 48 opportunistic submissions.
