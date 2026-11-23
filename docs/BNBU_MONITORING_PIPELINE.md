# BNBU monitoring and held-out baselines

From the repository root, with `requirements.txt` installed:

```sh
python -m birdglass.bnbu_monitoring data/examples/synthetic_bnbu_monitoring.json monitoring-demo
```

The synthetic scene replays seven approaches through `approach_events`. It
contains a reflected cue, a through-glass cue, a first contact on an adjacent
frame, clearances, a truncated track and a dropped-frame track. Synthetic
identities and dates deliberately have no campus mapping. The command saves
`monitoring_report.json` and `manifest.json`, with input, source and output
SHA-256 values. The report preserves source references, per-trial outcomes,
held-out observations, baseline predictions, Brier scores and abstention
reasons. A second run on the same checked-out sources and dependencies produces
the same report bytes.

## Input and endpoint dictionary

| Record | Identity and scope | Required observation semantics |
| --- | --- | --- |
| Pane | `pane_id`, `building_id`, `facade_id`, `model_version`, `registration_source_id` | Site input joins the exact pane identity and geometry source to the field-verified `pane_registry` manifest. A known optical mechanism requires `optical_source_id`. Keep unlocated reports out of the pane panel. |
| Time block | `time_block_id`, `start`, `end` | Disjoint timezone-aware intervals defined before fitting. A visit or recording must fit within one block. |
| Video session | Exact pane identity, `video_id`, `source_id`, block and time interval, frame rate, `gate_id` | A continuous source and fixed risk-gate definition. Set `annotation_status` to `complete` only after annotating the full session. Only then does an empty session yield a confirmed zero. Preserve original source and use anonymized identifiers. Selected clips and opportunity reports are ineligible. |
| Approach | Exact pane identity, `approach_id`, `trial_id`, video, gate time, annotation source and reviewer, known `individual_id` where available | One independently annotated entry per source trial. Outcomes are glass first contact, opaque first contact, confirmed no contact, right censoring or a recording gap. The contacted surface has its own ID, including when it differs from the at-risk pane. |
| Patrol | Exact pane identity, `patrol_id`, `source_id`, block and interval | Surveyed visits have positive effective hours and an explicit count, including zero. Unsurveyed and unknown visits leave effort and count blank. The endpoint is detected-carcass presence per eligible visit. |

`data/templates/facade_approach_monitoring_template.csv` remains available for
the original façade-level aggregates. Converting those aggregates into this
event stream requires the underlying video and event-level records. The local
data audit documents why existing opportunity reports cannot supply those rows
or patrol zeros.

## Baselines and site release

Each test cell holds out one building in one time block. Training uses other
buildings in strictly earlier blocks and excludes shared source IDs and known
individual IDs. A fold reports the IDs available to fit and score, positive
counts, and why a fit or score is missing. The approach baseline uses an
intercept on fully observed outcomes and abstains on folds containing censoring
or incompatible gate definitions. It needs a prespecified competing-risk or
censoring model before those folds are eligible. The patrol baseline estimates
a constant detection rate from Bernoulli presence with an effort offset and
reports probability at each visit's effort. It measures detected carcasses.

Site release is disabled in this pipeline and the façade decision report. Local inputs still need a registered
study protocol, coverage and detection/persistence trials, an approved
validation artifact, an endpoint-matched candidate and baseline comparison,
calibration and uncertainty checks on real local holdouts, and linked pane
features and evidence snapshots. Record the meaningful effect, minimum sample
and event counts, candidate model/feature selection and stopping rules before
examining any held-out outcomes. Source ids in input identify supplied records
and do not certify a registered file or a local study on their own.

The historical BNBU records currently support candidate microzones. Fieldwork
must supply surveyable panes and neighboring structures, a standardized
camera/patrol schedule and anonymized source-backed rows. Keep contact, detected
carcass presence and injury on their own denominators. Treatment superiority
requires the separately designed local controlled comparison.

Run the same command with `data/examples/bnbu_monitoring_intake_pending.json`
to reproduce the empty field intake and its missing-evidence list.
