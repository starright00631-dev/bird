# BNBU physical pane registry

Use the [field template](../data/templates/bnbu_pane_registry_template.json) for
registrations and the [synthetic fixture](../data/examples/synthetic_pane_registry.json)
to exercise the format. The fixture has two neighboring panes and a candidate
comparison location. Its coordinates, measurement errors and photo IDs are
illustrative. T29 and LRC remain priorities for field verification. See the
[local data audit](BNBU_LOCAL_DATA_AUDIT.md) for the 38 candidate microzones.

## Register physical panes and locate reports

| Field | Collection rule |
| --- | --- |
| `identity` | Record `pane_id`, `building_id`, `facade_id`, and `model_version`. Keep the same pane ID when remeasuring the same physical window. Record a new model version when the geometry revision changes and retain the earlier registry snapshot with its evidence. |
| `floor`, `bay`, `microzone_id` | Use the floor and physical bay or grid designation that a second observer can find. Add a subdivision to the bay when a bay contains multiple panes. Add the historical microzone if the link has been checked. |
| `coordinate_system`, `corners_m`, `outward_azimuth_deg` | Record a metric frame ID that identifies its survey origin and axes. Enter 3D corners in perimeter order, without re-entering the closing point. Use degrees clockwise from true north for azimuth. Record the local east, north and up frame for solar and ray analysis. |
| `registration_error_m`, `geometry_source_id` | Record the geometric registration error in metres and cite the survey or registration artifact that defines its calculation. Keep maps and survey/photo alignment with that source. |
| `photos` | Give each pane annotation a unique `photo_id`. `source_id` locates the annotated photo or its manifest entry and `captured_at` includes the time zone. If one image annotates two panes, use separate annotation IDs that can resolve to the shared original. Index later optical photos under the same pane. |
| `field_verified_at` | Enter the time of onsite verification with a time-zone offset only after the physical locator, referenced geometry, error and at least one dated photo are available. |

Use `ImpactLocation` and `PaneRegistry.validate_impact` to retain the precision
of each collision report. Enter `verified_pane` only with one field-verified
pane and an independent impact evidence reference. Unresolved reports can
retain every plausible pane under `candidate_panes`, a broad location under
`microzone`, or `unknown`. A pane registration does not establish where an
old incident occurred. For privacy, publish anonymous report IDs and
authorized photo references with identifying details removed.

## Describe optical evidence by approach and time

Wrap existing `GlassObservation` values in `PaneGlassObservation` with the
same registry identity, an evidence ID, a dated source and its type. Use
`field_view` for annotated photos. Record stable viewpoint ID, approach
azimuth, lighting, visible vegetation reflected in the glass, and apparent
habitat or clear passage visible through the assembly. Collect multiple
light conditions where practical. Visual appearance (such as
`reflective_and_transparent`) and assembly/treatment (such as
`low_e_coating` or `ceramic_frit`) have separate fields. Use
`PatternObservation` for marker position, extent, gap, minimum size and
contrast. Keep the unit, evidence tier and source for each measurement.

For VLR/VLT and spectral fractions, record the incidence angle from the
surface normal and use `instrument` or `manufacturer_assembly_spec`.
Specify the complete installed assembly for manufacturer data, including its
specification reference. `SpectralObservation` records wavelength in
nanometres and reflectance and transmittance as fractions. Run
`audit_glass_evidence(registry, rows)` before selecting an observation for
reporting. Review conflicting assembly descriptions and non-overlapping VLR
or VLT measurements taken at the same angle against the original records.

Keep each automated photo screen as a `clip_screen` proxy. A correction is
a separate, human-reviewed row with a reviewer ID and the original ID in
`reviewed_from_evidence_id`. The audit checks that both records describe
the same pane, viewpoint and source photos.

`PaneGlassObservation.model_approach_view` runs the finite-pane ray and
solar-alignment modules on validated rectangular geometry. Sight lines
require viewpoints and targets in the pane's metric ENU frame. Retain the
model output alongside empirical photos and measurements as a geometric
hypothesis. Use `to_glass_panel` to create a decision-engine input from
a field-verified registry entry after the evidence audit.

## Pilot acceptance

The checked-in field template is empty. Independent verification still
requires authorized photos, measurement and registration sources for
adjacent panes, two observed optical appearances and a comparable control.
Record which settings and site conditions each source supports so that
other observers can relocate the pane and repeat the observation.
