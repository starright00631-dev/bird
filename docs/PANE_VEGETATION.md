# Vegetation evidence for individual panes

Run the same summarizer against a source bundle or the [synthetic example](../data/examples/synthetic_pane_vegetation.json).

```bash
python -m birdglass.pane_vegetation data/examples/synthetic_pane_vegetation.json
python -m birdglass.pane_vegetation pane-evidence.json --registry pane-registry.json --output pane-summary.json
```

The JSON summary retains the pane identity, reviewed values, denominators, and dated source references. The synthetic bundle tests the full command without providing observations of BNBU.

## Pane and source keys

A bundle carries `dataset_kind` (`field` or `synthetic`) and the registry identity `pane`, including `pane_id`, `building_id`, `facade_id`, and `model_version`. Repeat that identity on each `land_cover`, `site_context`, reflection, and monitoring record so an adjacent pane or a mismatched registration cannot be joined by façade alone. Field processing requires the exact, field-verified registration from the same dataset kind.

Each evidence record carries `status`. Reviewed records require `source_id`, `source_ref`, an ISO 8601 `recorded_at` with a UTC offset, a known `evidence_tier`, a pseudonymous `reviewer_id`, and an `annotation_version`. Use a stable source reference that leads back to the dated map, photo, survey sheet, or video. Use `source_ref` to identify the exact artifact and its reviewed crop or region when applicable. Use `reason` and, when available, `review_action` for pending, rejected or missing records. Numeric summaries are withheld until review and remain missing when there are no interpretable pixels.

## Coverage and site structure

- Register the window center to a projected metric CRS. Record its `center_xy_m`, `crs`, `position_reference` for the registration transform, imagery season, and square `pixel_resolution_m`. Inputs are cropped, north-up, human-reviewed raster labels. For each band provide the crop's `upper_left_pixel_center_xy_m` and its label `mask`.
- Pixel centers assign the five contiguous bands with an inclusive inner and exclusive outer radius. Each included cell is checked against its band. Raster labels use `tree_canopy`, `shrub`, `grass`, `bare_soil`, `bark_mulch`, `impervious`, `building`, `water`, and `other`. Mark pixels outside the crop footprint with `outside`; inside, use `occluded` or `unclassified` where appropriate. Class percentages use only the valid classified area. Compare footprints and valid areas before comparing percentages across panes and dates. A partially covered band describes only the reviewed pixels.
- Supply the annotation error estimate in percentage points per ring via `cover_uncertainty_pp`, or record `uncertainty_missing_reason`. Keep the raw image and independent reviewer or ground check alongside the coded mask.
- `site_context` stores the separate façade-wide 50 m tree-canopy and porous-ground percentages, pane sill and canopy height, nearest crown distance, corridor obstruction fraction, and potential food resources if observed. Façade-wide cover uses a documented façade buffer source rather than a sum of pane annuli. Distances and heights are metres, and percentages range from 0 to 100.

## Reflection and observed routes

- Annotate the exact projected glass area in each dated photo. Record `view_id`, approach bearing (clockwise from true north, 0° through <360°), and light conditions. Use `reflected_vegetation`, `reflected_other`, `transmitted_vegetation`, `transmitted_other`, or `other_visible` for interpretable pixels. Mark mixed reflection/transmission or ambiguous pixels as `unclassified`; use `occluded` and `outside` as above. The reflected vegetation share is the fraction of interpretable pane pixels with confirmed vegetation reflection. Keep the interpretable share and class counts to expose coverage. The measure describes the view and time of capture.
- Record `starts_at`, `ends_at`, `effort_s`, weather, phenology, and `coverage_mode` in each monitoring session. For continuous coverage, carve gaps out as separate sessions and record all routes explicitly, including an empty list for reviewed zero activity. Selected clips can document observed routes but do not establish a zero observation. Give each trajectory one stable `track_id`, a `track_ref` that locates the independent video or track within it, a timestamp within that session, approach bearing and species or guild. Use `unknown` when the taxon could not be identified.
- Keep the four hypotheses distinct. Canopy and resources inform potential habitat attraction, video and corridor structure inform route access, photo masks inform view-specific reflection, and occlusion or physical obstruction is recorded separately. A matching bearing alone cannot link a route to a particular photo or a causal mechanism. These route counts describe local activity and carry no estimate of in-risk approaches or collisions.

## Field acceptance

Connect the first usable set of ring masks and approach-angle photographs to a field-verified pane and retain the dated source index and review notes. Collect multiple capture times and independent route coverage to test whether the habitat is visible, reachable and used. The repository's candidate microzones and opportunistic reports still lack these linked observations. Automatic segmentation is outside this workflow. An automated method would first require held-out-building comparison against human masks, including shaded and obstructed cases, plus a documented quality threshold.
