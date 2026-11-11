"""Metamorphic tests: no hidden-glass geometry is allowed into planning.

These exercise geometric/causal invariants only, not avian recognition rates.
"""
import numpy as np
from birdglass.contact import RectPane
from birdglass.control import route, replay


def test_hidden_glass_has_no_influence_on_perceived_gap_proposals():
    marked=RectPane("marked",0,-1,1,0,2)
    hidden=RectPane("hidden",0,1,3,0,2)
    start=np.array([-2.,0.,1.])
    heading=np.array([1.,0.,0.])
    target=np.array([3.,1.6,1.])
    known={"marked"}
    reference=route(start,heading,[marked],target,.3,.05,recognized_glass=known)
    with_hidden=route(start,heading,[marked,hidden],target,.3,.05,
                      recognized_glass=known)
    np.testing.assert_array_equal(with_hidden,reference)
    # Once a second pane is recognized, the *same physical* scene gives a
    # different perceived map; an unrecognized pane is a potential false gap.
    with_both=route(start,heading,[marked,hidden],target,.3,.05,
                    recognized_glass={"marked","hidden"})
    assert not np.allclose(with_hidden,with_both)
    assert hidden.ymin < with_hidden[1] < hidden.ymax


def test_no_recognized_glass_looks_open_but_still_physically_blocks():
    pane=RectPane("untreated",0,-1,1,0,2)
    start=np.array([-2.,0.,1.])
    target=np.array([2.,0.,1.])
    np.testing.assert_array_equal(
        route(start,[1,0,0],[pane],target,.3,.05,recognized_glass=set()),
        target)
    outcome=replay(start,[5,0,0],target,[pane],{"untreated":0.},
                   {"untreated":0.5})
    assert outcome["outcome"]=="glass"
    assert outcome["pane"]=="untreated"


def test_opaque_always_blocks_the_planners_perceived_gap():
    wall=RectPane("wall",0,-1,1,0,2,material="opaque")
    start=[-2,0,1]
    target=[2,0,1]
    waypoint=route(start,[1,0,0],[wall],target,.3,.05,
                   recognized_glass=set())
    assert not np.allclose(waypoint,target)


def test_replay_passes_only_previously_recognized_glass_to_planner(monkeypatch):
    from birdglass import control
    marked=RectPane("marked",0,-1,1,0,2)
    hidden=RectPane("hidden",0,1,3,0,2)
    recorded=[]
    original=control.route

    def observing_route(*args,**kwargs):
        recorded.append(set(kwargs["recognized_glass"]))
        return original(*args,**kwargs)

    monkeypatch.setattr(control,"route",observing_route)
    replay([-2,0,1],[5,0,0],[2,1.6,1],[marked,hidden],
           {"marked":1.,"hidden":0.},{"marked":0.,"hidden":0.5})
    assert recorded and recorded[0]=={"marked"}
    assert all("hidden" not in known for known in recorded)
