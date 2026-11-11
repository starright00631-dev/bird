import numpy as np
import pytest
from birdglass.contact import RectPane,first_sphere_contact,first_contact,segment_rect_distance
from birdglass.risk import observed_mean,split_observation,paired_policy_delta

def test_first_contact_is_not_pane_order_dependent():
    front=RectPane("front",0,-1,1,-1,1,"opaque")
    back=RectPane("back",.1,-1,1,-1,1,"glass")
    a=(-1,0,0);b=(1,0,0);v=(2,0,0)
    x=first_contact(a,b,v,[front,back],.05,.2)
    y=first_contact(a,b,v,[back,front],.05,.2)
    assert x.pane_id==y.pane_id=="front"
    assert x.material=="opaque"

def test_first_contact_at_segment_entry():
    pane=RectPane("glass",0,-1,1,-1,1)
    ans=first_sphere_contact((-1,0,0),(1,0,0),pane,.2)
    assert ans is not None
    assert ans[0]==pytest.approx(.4,abs=1e-9)

def test_corner_grazing():
    pane=RectPane("corner",0,-1,1,-1,1)
    d=segment_rect_distance((-1,2,2),(1,2,2),pane)
    assert d==pytest.approx(np.sqrt(2),abs=1e-10)
    assert first_sphere_contact((-1,2,2),(1,2,2),pane,1.0) is None

def test_no_tunneling():
    pane=RectPane("p",0,-1,1,-1,1)
    assert first_sphere_contact((-100,0,0),(100,0,0),pane,.02) is not None

def test_outside_footprint_does_not_count():
    pane=RectPane("p",0,-1,1,-1,1)
    assert first_contact((-1,2,2),(1,2,2),(2,0,0),[pane],.05,.4) is None

def test_observation_not_identified_from_count():
    assert observed_mean(200,.02,.5)==pytest.approx(2.)
    assert observed_mean(50,.16,.25)==pytest.approx(2.)
    assert not split_observation(2)["identified"]

def test_paired_glass_to_wall_not_improvement():
    assert paired_policy_delta(["glass","glass"],["opaque","passed"])==pytest.approx(.5)

def test_invalid_geometry():
    with pytest.raises(ValueError):
        RectPane("bad",0,1,-1,0,1)
