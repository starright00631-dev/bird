import pytest
from birdglass.contact import RectPane
from birdglass.policy import Scenario,assess,abstention_gate

def test_paired_joint_counterfactual_and_deployment_gate():
    panes=[RectPane("g",0,-1,1,0,2)]
    flights=[((-1,0,1),(5,0,0),(2,0,1),.04,.3,1.)]
    scenarios=[Scenario("unfit",.14,4.5,12.,7.,{"g":0.})]
    x=assess(panes,flights,scenarios,{"g":.8},seed=9)
    y=assess(panes,flights,scenarios,{"g":.8},seed=9)
    assert x==y
    assert not abstention_gate(x)["authorized_for_deployment"]

def test_policy_cannot_mark_opaque():
    panes=[RectPane("wall",0,-1,1,0,2,"opaque"),
           RectPane("g",0,1,2,0,2)]
    flights=[((-1,0,1),(5,0,0),(2,0,1),.04,.3,1.)]
    scenarios=[Scenario("unfit",.14,4.5,12.,7.,{})]
    with pytest.raises(ValueError):
        assess(panes,flights,scenarios,{"wall":.5})

def test_zero_effect_matches_paired_baseline():
    panes=[RectPane("g",0,-1,1,0,2)]
    flights=[((-1,0,1),(5,0,0),(2,0,1),.04,.3,1.)]
    rows=assess(panes,flights,[Scenario("same",.1,4.,10.,6.,{"g":.2})],{},seed=17)
    assert rows[0]["total_contact_reduction"]==pytest.approx(0.)
    assert rows[0]["glass_before"]==rows[0]["glass_after"]
