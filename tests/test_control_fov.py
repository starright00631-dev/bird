import math
import numpy as np
import pytest
from birdglass.contact import RectPane
from birdglass.control import replay, visible_glass_ids

def test_large_pane_has_visible_edge_despite_offscreen_center():
    # The facade centre is 68 degrees away, but its near edge
    # crosses the bird's forward gaze, so a centre-only test fails.
    wide=RectPane("wide",0,-1,11,0,2)
    got=visible_glass_ids((-2,0,1),(1,0,0),[wide],7.,57.3)
    assert got==["wide"]
    center=np.array([2,5,0.])
    assert math.degrees(math.acos(center[0]/np.linalg.norm(center)))>57.3

def test_narrow_pane_outside_fov_not_in_candidates():
    side=RectPane("side",0,4,5,0,2)
    assert visible_glass_ids((-2,0,1),(1,0,0),[side],7.,57.3)==[]

def test_panes_behind_bird_or_beyond_range_not_visible():
    back=RectPane("behind",-5,-1,1,0,2)
    front=RectPane("front",0,-1,1,0,2)
    assert visible_glass_ids((-2,0,1),(1,0,0),[back,front],1.)==[]

def test_no_phantom_step_at_zero_latency():
    window=[RectPane("G",0,-.2,.2,0,2)]
    inputs=dict(start=(-2,0,1),velocity=(1,0,0),
         destination=(3,0,1),panes=window,
         recognition={"G":1.},draws={"G":.01},
         dt=.2,max_time=.21,detection_range=4.,gain=4.,
         max_lateral_accel=15.)
    instant=replay(latency=0,**inputs)
    delayed=replay(latency=.2,**inputs)
    assert instant["outcome"]==delayed["outcome"]=="unresolved"
    assert abs(instant["end_xyz"][1])>1e-5
    assert delayed["end_xyz"][1]==pytest.approx(0.,abs=1e-12)

def test_no_glass_recognition_even_when_geometrically_visible():
    window=[RectPane("G",0,-.2,.2,0,2)]
    inp=dict(start=(-2,0,1),velocity=(1,0,0),destination=(3,0,1),
             panes=window,draws={"G":.4},
             dt=.2,max_time=.21,detection_range=4.,latency=0)
    outcome=replay(recognition={"G":0.},**inp)
    assert outcome["end_xyz"][1]==pytest.approx(0,abs=1e-12)
