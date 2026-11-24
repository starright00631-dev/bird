# BNBU workspace pane evidence

The 3D workspace can open a local JSON evidence package in **模型数据**. Choose a
registered pane in the selector or click its mesh. The details and conversation
use the same pane and evidence snapshot. The supplied v89 geometry does not
include independently verified physical pane bindings.

## Pane ontology demo

Download [the interactive pane graph](pane-ontology-demo.html) and open it in a
browser to follow a synthetic building, facade and pane to its optical records
and assessment status. The page runs offline and links each displayed fact to
the versioned fixture.

## Export a package

```sh
python -m birdglass.workspace_evidence \
  monitoring_report.json pane_registry.json object_mapping.json workspace_evidence.json \
  --vegetation-report pane_vegetation_report.json \
  --glass-observations pane_glass_observations.json
```

The first input is the canonical output of
[`birdglass.bnbu_monitoring`](BNBU_MONITORING_PIPELINE.md). The optional
vegetation input is a reviewed pane report from `birdglass.pane_vegetation`.
Repeat `--vegetation-report` for additional panes. The glass input is a
JSON array of public `PaneGlassObservation.as_dict()` records. The exporter
audits visual lineage and conflicts before selecting public facts. It
retains separate dated reflection views and withholds a single optical
classification when reviewed views disagree across different conditions.

The mapping file contains `dataset_kind` (`field` or `synthetic`),
`scene_version` (for this viewer, `v89`), `valid_until` and a
`bindings` array. Each binding holds `pane` with `pane_id`,
`building_id`, `facade_id` and `model_version`, plus exact GLB
`object_name`, `mapping_source_id` and `mapped_at`. Record the actual
mapping evidence in the source register and use explicit UTC offsets.
For field use, the mesh must also expose the same four identity fields as
GLB extras. A model file with only building or schematic glass nodes cannot
bind to a field package. The synthetic package can bind its clearly labeled
example to existing uniquely named nodes for QA.

The exported contract uses schema version 1. It carries the
monitoring snapshot ID and SHA-256 of the exact report bytes. It also carries
separate SHA-256 digests for the canonicalized registry, mapping, sorted glass
records and sorted vegetation reports. Retain all five inputs for
reproduction. Evidence facts include a controlled fact ID, value and unit,
evidence tier, capture date, enough metadata to identify each reflection view,
source IDs and a status. The viewer hides elapsed observations at their expiry
and retains the source identifiers. Sources link to an in-view index; consult
the archived report and source register to resolve original files. Public
packages should use already authorized source identifiers and avoid personal
names, credential material and private file URLs.

## Detail and conversation

For a bound pane, the compatible endpoint selects facts from the current scope
by returning the exact pane ID and fact IDs as JSON. The viewer uses the
same dated, sourced facts in the details and the answer. Wrong pane IDs,
unknown fact IDs and extra model output are rejected. Switching selection
clears the conversation and cancels pending requests. The request contains
the question, current pane scope and allowed facts; it omits photos,
trajectories, reviewer information and report files. Workspace v1 holds back
numeric site risk and treatment effect. Pane questions without evidence receive
the current evidence gap and the path to register or verify the pane.

Use an HTTPS compatible endpoint or a local loopback HTTP endpoint.
Credentials are stored in the current page session. A provider must allow
the launching page's origin, including the standalone file origin if used.
The offline viewer and evidence links work without the endpoint. If the
hosted Pages setup remains unavailable, open **双击查看_校园3D.html** from
the offline release or run the packaged local viewer server.

## Reproducible synthetic case

[The synthetic workspace package](../data/examples/synthetic_workspace_evidence.json)
comes from the actual synthetic monitoring and vegetation runners with a
shared, synthetic pane identity. Its v89 mesh associations are interface
fixtures. They make no assertions about the modeled buildings, lake or local
optical conditions.

| Canonical input | Model details | Conversation with simulated API |
| --- | --- | --- |
| `SYN-A-1`, two incompatible reflectance specifications | Reflectance conflict, both source IDs | Returns the same conflict and opens the source index |
| `SYN-A-1`, VLT 60% on 2026-01-09 at +08:00 | Same value, unit and date | Same value, unit and date |
| Adjacent `SYN-A-2`, no canopy observation | Missing vegetation | Rejects an answer for `SYN-A-1`; displays the missing state for `SYN-A-2` |
| Neither pane has field-validated risk or treatment effect | Conclusion withheld | Displays the same withheld status |

Run the contract and mock-browser checks with
`python -m pytest -q tests/test_workspace_evidence.py`,
`node --test campus/interface/test_pane_evidence.mjs` and
`python campus/interface/test_browser.py` after building the v89 package.
To regenerate the mock browser fixture from the reference inputs, run
`python -c "import runpy; runpy.run_path('tests/test_workspace_evidence.py')['write_browser_fixture']('data/examples/synthetic_workspace_evidence.json')"`.

An external endpoint connection and the comparative user study remain
pending. Use fixed, field-verified tasks in both display modes and record
correct pane identification, successful source checks, next-step selection,
elapsed time and errors. The synthetic regression cases cannot determine
whether the conversation improves field research.
