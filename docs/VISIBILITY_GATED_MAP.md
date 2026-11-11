# Visibility-gated perceived geometry — research invariant

## Falsifiable engineering hypothesis

When an approaching bird recognizes glazing patch A but not glazing patch B,
a model of its gap-selection decision **must not use the physical bounds of B
as a known obstacle**. The collision engine, in contrast, must retain B as a
solid surface. Otherwise knowledge of an invisible panel leaks from the
simulator's ground truth into the animal's navigation policy; policy
counterfactuals may falsely report successful avoidance and suppress risk
transfer from treated to untreated glazing.

Before this correction, `route(..., panes, ...)` scanned all windows as
obstacles, even though `replay` sampled a separate per-pane Bernoulli
recognition state. Thus the model implicitly let birds avoid glass they had
never detected. This is an **internal logical error**, irrespective of what
the true recognition process turns out to be.

After correction, the hypothetical perceived set is

`M_t = {opaque panes} union {glass panes recognized by time t}`.

The route search uses `M_t` for both its candidate grid and its collision
exclusion region. The actual continuous body/wing contact kernel still uses
all physical panes. Per-pane draws remain paired across policy conditions.

## Scientific connection and limits

- Lin, Ros & Biewener (2014), https://doi.org/10.1098/rsif.2014.0239,
  model pigeons steering toward perceived visual gaps through **visible poles**.
  Their experiments did not establish recognition probabilities for glass.
- Håstad & Ödeen (2014), https://doi.org/10.7717/peerj.621,
  show how wavelength-dependent marks can appear differently to UVS and VS
  bird visual systems. This does not identify patch-specific recognition at
  BNBU.
- Samuels et al. (2022), https://doi.org/10.7717/peerj.14604,
  captured collision/near-miss approach trajectories but the selected sample
  is not an unconditional arrival denominator.

The tests use synthetic panes and flight starts to verify *software
invariants*, not field treatment effectiveness: (1) adding an unseen glass
pane cannot alter perceived target selection; (2) making it recognized can
alter that selection; (3) unseen glass still causes physical contact; (4)
opaque obstacles remain in the route map; (5) the coupled replay forwards
only the previously recognized glass IDs to route planning.

Remaining acknowledged simplifications: all opaque structure is assumed
visible from every approach angle; each glass pane has an instantaneous
binary recognition draw within a generic forward cone; `route` uses a
heuristic rectangular grid, not measured retinal contours, and the facade
is coplanar with a +x traversal assumption. No species-specific visual
receptor data, delayed reaction trajectory, or empirical intervention
effect is inferred from these tests.

## Next empirical gate

Obtain calibrated trial-level video of both **collisions and successful
avoids**, with registered pane bounds, camera poses, bird/species/individual
IDs where possible, and measured spectral/reflection context. Evaluate
held-out onset of avoidance versus predicted glass recognizability and
trajectory, not only contact counts. Use matched approach denominators and
independent detection-effort data before BNBU facade risk or intervention
probabilities. Do not infer field effects from this engineering fix.
