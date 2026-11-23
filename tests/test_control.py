import numpy as np
import pytest
from birdglass.contact import RectPane
from birdglass.control import replay,turn

def test_lateral_acceleration_bound():
    a=turn([1,0,0],[0,1,0],.01,8,3,6)
    assert abs(np.linalg.norm(a)-1)<1e-12
    assert np.arccos(a[0])<=.01*3/6+1e-12

def test_straight_collision_and_paired_replay():
    surfaces=[RectPane("wall",0,-1,1,0,2,"opaque")]
    x=replay((-1,0,1),(5,0,0),(2,0,1),surfaces,{}, {})
    y=replay((-1,0,1),(5,0,0),(2,0,1),surfaces,{}, {})
    assert x==y
    assert x["outcome"]=="opaque"


@pytest.mark.parametrize("dt", [.1, .05, .025, .0125])
def test_contact_time_is_stable_across_integration_steps(dt):
    pane = RectPane("glass", 0, -.4, .4, .8, 1.2)
    contact = replay(
        (-4, 0, 1), (4, 0, 0), (2, 0, 1), [pane], {}, {},
        body_radius=.04, wingspan=.2, dt=dt,
    )
    assert contact["outcome"] == "glass"
    assert contact["time_s"] == pytest.approx(.99, abs=1e-12)
    assert contact["end_xyz"] == pytest.approx((-.04, 0, 1), abs=1e-12)


def test_recognition_threshold_is_strict():
    pane = RectPane("glass", 0, -.4, .4, .8, 1.2)
    inputs = dict(
        start=(-4, 0, 1), velocity=(4, 0, 0), destination=(2, 0, 1),
        panes=[pane], draws={"glass": .7}, body_radius=.04, wingspan=.2,
        latency=0., gain=5., max_lateral_accel=20.,
    )
    exactly = replay(recognition={"glass": .7}, **inputs)
    above = replay(recognition={"glass": np.nextafter(.7, 1.)}, **inputs)

    assert exactly["outcome"] == "glass"
    assert exactly["planning_status"] == "not_triggered"
    assert above["outcome"] == "passed"
    assert above["planning_status"] == "geometric_unchecked"
