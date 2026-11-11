import numpy as np
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
