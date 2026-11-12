import pytest
from birdglass.contact import RectPane
from birdglass.control import replay
from birdglass.policy import Scenario,assess

PANES=[RectPane("G",0,-.8,.8,0,2)]

def test_screened_policy_is_connected_to_flight_loop():
    args=dict(start=(-.1,0,1),velocity=(5,0,0),
              destination=(2,0,1),panes=PANES,
              recognition={"G":1.},draws={"G":0.},
              body_radius=.05,wingspan=.3,latency=.12,
              detection_range=5.,dt=.02)
    screened=replay(planner_strategy="screened",**args)
    geometric=replay(planner_strategy="geometric",**args)
    assert screened["outcome"]=="glass"
    assert screened["planning_status"]=="no_crossing_found_in_tested_candidates"
    assert geometric["planning_status"]=="geometric_unchecked"

def test_planner_unknown_name_rejected():
    with pytest.raises(ValueError,match="planner_strategy"):
        replay((-1,0,1),(5,0,0),(2,0,1),PANES,{}, {},
               planner_strategy="safest_in_world")

def test_joint_counterfactual_reports_failure_not_fake_gain():
    flights=[((-.1,0,1),(5,0,0),(2,0,1),.05,.3,1.)]
    scenarios=[Scenario("test",.12,4.5,12.,5.,{"G":1.})]
    a=assess(PANES,flights,scenarios,{"G":0.},
             planner_strategy="screened",seed=1,dt=.02)
    assert a[0]["planning_strategy"]=="screened"
    assert a[0]["planning_no_crossing_baseline"]==pytest.approx(1.)
    assert a[0]["planning_no_crossing_policy"]==pytest.approx(1.)
    assert a[0]["total_contact_reduction"]==pytest.approx(0.)
    assert a[0]["verified_field_effect"] is False

def test_counterfactual_preserves_no_recognition_status():
    flights=[((-1,0,1),(4,0,0),(1,0,1),.05,.3,1.)]
    scenarios=[Scenario("unobserved",.12,4.5,12.,3.,{"G":0.})]
    a=assess(PANES,flights,scenarios,{"G":0.},
             planner_strategy="screened",seed=3,dt=.02)
    assert a[0]["planning_no_crossing_baseline"]==pytest.approx(0.)
    assert a[0]["planning_no_crossing_policy"]==pytest.approx(0.)
