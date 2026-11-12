# Experimental rollout-screened planner in the joint counterfactual

The `control.replay` simulation now has a declared
`planner_strategy` argument:

- `geometric` (legacy baseline): route to a geometrically unoccupied
  portal without first proving the maneuver is physically achievable.
- `screened`: enumerate openings, run the same delayed
  speed-conserving heading controller and body/wing swept first-contact
  test against *all glass and opaque surfaces*, and choose only a
  candidate simulated to cross without contact.

If the screened method does **not** find a valid crossing within its finite
candidate budget, it returns `no_crossing_found_in_tested_candidates`
and keeps the previous heading target. This does not imply no real
maneuver exists. Predicted contacts are still conditional on **unfit**
visibility, acceleration, body/wing samples, and recognition hypotheses.

`policy.assess` accepts the same planning strategy and returns the
fraction of paired flights in both policy arms whose screening yielded
no crossing. Shared initial flights and recognition draws remain paired.

This is only a **software/model consistency improvement**. A real
advantage must be demonstrated on independently annotated bird flight
paths, with measured species, control and scene parameters. Evaluation
must also show whether conservative routing increases contact with
unmodeled posts, rails, terrain, or vegetation. The digital campus model
is not a surveyed source of collision surfaces.

## Perceived scene versus physical screening (2026-11-12)

Both strategies invoked **within** `control.replay` are now recognition-gated:
the bird model proposes/simulates candidate movement around assumed-visible
opaque objects and previously recognized glass only. This corrects an
oracle-knowledge leak in the former full-facade planners. Direct callers of
`reachability.choose_reachable_gap` may still deliberately supply an
omniscient map as an **oracle baseline**; it must not be described as avian
sensory perception. True first contact remains tested on all glass and opaque
patches after the bird's action, so an apparently safe gap may strike
unrecognized neighboring glazing. See `docs/VISIBILITY_GATED_MAP.md`.
