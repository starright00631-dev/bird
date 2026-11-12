# Dynamic gap reachability: structural verification

## Problem repaired

An apparent opening in 3D geometry does not prove a bird can reach it
before first physical contact. Previously `control.route` chose
geometrically unoccupied endpoints without testing delayed steering,
speed-dependent curvature, finite wing/body extent or transferred risk
to neighbouring opaque elements.

This module (`birdglass/reachability.py`) simulates a specified
candidate path using exactly the same heading-update kernel
(`control.turn`) and first-contact collision kernel
(`contact.first_contact`). It screens each attempted opening against
ALL given glass/opaque panes, with finite time, assumed reaction latency,
gain and lateral acceleration.

The planner returns **no_crossing_found_in_tested_candidates** if no
tested candidate crosses safely. That is NOT equivalent to
"collision is inevitable": a bird might brake, fold wings, turn back,
escape vertically, use a longer path, or have different control parameters.

## Model mechanics

`||v||` remains constant and heading rotates by at most
`min(angle_to_goal, dt * gain * angle_to_goal, dt * amax / speed)`.
The initial heading command is queued for the specified latency.
Body and wing stations are sampled swept spheres. The first contact
on any pane is reported, including opaque structures; a successful
crossing needs no contact and must pass the facade boundary.

The comparison tests include a geometrically open gap within sight
which is not dynamically reachable when initial contact is imminent.

## Real-world calibration gates

Measured species/individual speed and 3D wing pose distributions
should replace assumed input ranges. To estimate recognition,
separately gather time-resolved pane approach/avoidance labels,
photometry and frame-registered scene geometry. This control model
has not been fitted to glass observations and does not produce
installation-ready risk rankings.

The finite candidate grid is a computational approximation.
Future implementation must test convergence in candidate density,
sample windows and time step; no universal safety or completeness
claim should be based on a selected grid resolution.
