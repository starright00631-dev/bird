import numpy as np
import pytest
from birdglass.contact import RectPane
from birdglass.reachability import rollout_target,choose_reachable_gap
from birdglass.control import route

WINDOW=[RectPane("wide",0,-.8,.8,0,2)]

def test_open_gap_does_not_mean_dynamically_reachable():
    initial=(-.1,0,1)
    heading=(5,0,0)
    candidate=route(np.array(initial),np.array([1.,0,0]),
                     WINDOW,np.array([2,0,1]),.3,.05)
    assert abs(candidate[1])>.8 or candidate[2]>2
    result=rollout_target(initial,heading,candidate,WINDOW,
               latency_s=.12,dt=.01,max_time_s=1.)
    assert result.status=="glass" and result.time_s<.1
    screened=choose_reachable_gap(initial,heading,(2,0,1),
                                  WINDOW,latency_s=.12,dt=.01,
                                  max_candidates=8)
    assert screened.target_xyz is None
    assert screened.status=="no_crossing_found_in_tested_candidates"
    assert screened.candidates_tested>0

def test_forward_rollout_classifies_opaque_collision_as_collision():
    panes=[RectPane("wall",0,-1,1,0,2,"opaque")]
    out=rollout_target((-1,0,1),(4,0,0),(.5,0,1),panes,
            latency_s=.0,dt=.02)
    assert out.status=="opaque" and out.contacted_pane=="wall"

def test_no_obstacles_fabricated_through_transparent_surface():
    out=rollout_target((-2,0,1),(4,0,0),(.5,0,1),WINDOW,
            latency_s=0,dt=.02)
    assert out.status=="glass"

def test_screened_result_never_claims_field_approval():
    decision=choose_reachable_gap((-5,0,1),(3,0,0),(2,0,1),
          WINDOW,latency_s=.08,dt=.04,max_candidates=12)
    assert decision.status in {
        "screened_crossing_found","no_crossing_found_in_tested_candidates"}
    if decision.target_xyz is not None:
       rerun=rollout_target((-5,0,1),(3,0,0),decision.target_xyz,WINDOW,
                latency_s=.08,dt=.04)
       assert rerun.status=="crossed"

def test_latency_sensitivity_yields_fixed_physics_not_fake_probability():
    pane=WINDOW
    r1=rollout_target((-2,0,1),(4,0,0),(.5,1.8,1),pane,
                       latency_s=0,dt=.02)
    r2=rollout_target((-2,0,1),(4,0,0),(.5,1.8,1),pane,
                       latency_s=.5,dt=.02)
    assert r1.status in {"crossed","diverted","glass","unresolved"}
    assert r2.status in {"crossed","diverted","glass","unresolved"}
    assert r1.time_s>0 and r2.time_s>0

def test_nonpositive_physics_or_nonforward_arrival_refused():
    with pytest.raises(ValueError):
       rollout_target((1,0,1),(-2,0,0),(.5,2,1),WINDOW)
    with pytest.raises(ValueError):
       choose_reachable_gap((-2,0,1),(3,0,0),(.5,2,1),WINDOW,max_candidates=0)
