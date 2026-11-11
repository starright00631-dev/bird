# Coupled-control research extension

The simulation now includes a constant-airspeed three-dimensional controller
with reaction-time buffering, curvature limits and an explicit physical gap
search, connected to continuous first-contact collision across glass and
opaque structures. Pane recognition is latent and must be independently
estimated; fixed random draws permit paired counterfactual comparisons.

This is a structural, *uncalibrated* controller. The nearest open-route cost,
recognition range, delay and lateral acceleration are not validated bird
parameters. A synthetic comparison is not a BNBU injury-risk estimate.

The next empirical gate requires calibrated 3D trial trajectories with known
obstacle geometry, individual-level holdouts and comparison to ballistic and
nearest-gap controls. No facade intervention is approved on this basis.

## Perceived geometry is not the true facade map

The planner now excludes **only opaque geometry and recognized glass**, whereas
contact checks all physical surfaces. This prevents hidden-glass geometry from
leaking into treatment counterfactuals. The invariant and falsification tests
are described in [VISIBILITY_GATED_MAP.md](VISIBILITY_GATED_MAP.md).
