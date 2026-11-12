"""Metamorphic tests for causal separation of perception and contact.

All fixtures are constructed geometric scenarios, NOT bird observations.
"""
import numpy as np
import pytest
from birdglass.contact import RectPane
from birdglass.control import perceived_surfaces, route, replay


def test_unseen_glass_cannot_change_geometric_aim():
    seen=RectPane("seen",0,-1,1,0,2)
    hidden=RectPane("hidden",0,1,3,0,2)
    p=np.array([-2.,0.,1.])
    h=np.array([1.,0.,0.])
    destination=np.array([3.,1.6,1.])
    only_seen=route(p,h,[seen],destination,.3,.05,recognized_glass={"seen"})
    with_hidden=route(p,h,[seen,hidden],destination,.3,.05,
                      recognized_glass={"seen"})
    np.testing.assert_array_equal(only_seen,with_hidden)
    with_recognized=route(p,h,[seen,hidden],destination,.3,.05,
                          recognized_glass={"seen","hidden"})
    assert not np.allclose(with_hidden,with_recognized)
    assert hidden.ymin < with_hidden[1] < hidden.ymax


def test_true_contact_remains_even_if_window_unperceived():
    hidden=RectPane("hidden",0,-1,1,0,2)
    aim=route([-1,0,1],[1,0,0],[hidden],[2,0,1],
              .3,.05,recognized_glass=())
    np.testing.assert_array_equal(aim,[2,0,1])
    observed=replay((-1,0,1),(5,0,0),(2,0,1),[hidden],
                    {"hidden":0.},{"hidden":.5})
    assert observed["outcome"]=="glass"
    assert observed["pane"]=="hidden"


def test_opaque_is_in_perceived_map_and_unrecognized_glass_is_not():
    wall=RectPane("wall",0,-1,1,0,2,"opaque")
    hidden=RectPane("hidden",0,2,3,0,2)
    assert [x.id for x in perceived_surfaces([wall,hidden],set())]==["wall"]
    aim=route([-2,0,1],[1,0,0],[wall,hidden],[2,0,1],
              .3,.05,recognized_glass=set())
    assert not np.allclose(aim,[2,0,1])


@pytest.mark.parametrize("strategy",["geometric","screened"])
def test_replay_never_passes_unrecognized_geometry_into_planner(strategy,monkeypatch):
    # Compare the identical known state with/without an unknown adjacent
    # glass patch. Instrument the planner boundary, not a claimed bird result.
    import birdglass.control as control
    import birdglass.reachability as reach
    seen=RectPane("seen",0,-1,1,0,2)
    hidden=RectPane("hidden",0,1,3,0,2)
    passed=[]
    if strategy=="geometric":
        original=control.route
        def spy(*args,**kwargs):
            passed.append(tuple(q.id for q in control.perceived_surfaces(
                args[2],kwargs["recognized_glass"])))
            return original(*args,**kwargs)
        monkeypatch.setattr(control,"route",spy)
    else:
        from birdglass.reachability import GapDecision
        def spy(start,velocity,goal,panes,**kwargs):
            passed.append(tuple(q.id for q in panes))
            return GapDecision(None,"no_crossing_found_in_tested_candidates",0,{})
        monkeypatch.setattr(reach,"choose_reachable_gap",spy)

    replay((-2,0,1),(5,0,0),(2,1.6,1),[seen,hidden],
           {"seen":1.,"hidden":0.},{"seen":0.,"hidden":.5},
           planner_strategy=strategy,dt=.025,max_time=.25)
    assert passed
    assert all(p==("seen",) for p in passed)


def test_zero_recognition_does_not_invoke_either_planner(monkeypatch):
    import birdglass.control as control
    import birdglass.reachability as reach
    hidden=RectPane("hidden",0,-1,1,0,2)
    def bad(*args,**kwargs):
        raise AssertionError("No perceived obstacle should trigger planning")
    monkeypatch.setattr(control,"route",bad)
    monkeypatch.setattr(reach,"choose_reachable_gap",bad)
    for strategy in ("geometric","screened"):
        val=replay((-1,0,1),(5,0,0),(2,0,1),[hidden],
                   {"hidden":0.},{"hidden":0.5},
                   planner_strategy=strategy)
        assert val["outcome"]=="glass"

def test_legacy_direct_route_is_oracle_comparator_only():
    window=RectPane("window",0,-1,1,0,2)
    start=[-2,0,1]
    goal=[2,0,1]
    oracle=route(start,[1,0,0],[window],goal,.3,.05)
    perceived=route(start,[1,0,0],[window],goal,.3,.05,
                    recognized_glass=set())
    assert not np.allclose(oracle,goal)
    np.testing.assert_array_equal(perceived,goal)
