import math
import numpy as np
import pytest
from birdglass.contact import RectPane
from birdglass.scene_optics import (
    RectPatch,scene_ray,minimum_heading_angle_deg,pane_solid_angle_sr,
    scene_path_table,measured_pixel_cone_catches
)

def facade():
    return RectPatch.from_axis_pane(RectPane("G",0,-1,1,0,2))

def test_reflected_tree_is_virtual_and_hits_finite_glass():
    pane=facade()
    ray=scene_ray((-2,0,1),(1,0,0),(-2,0,1),pane,
                  "reflection",scene_radius_m=.3)
    assert ray is not None
    np.testing.assert_allclose(ray.surface_point_m,[0,0,1])
    np.testing.assert_allclose(ray.apparent_target_m,[2,0,1])
    assert ray.gaze_to_heading_deg==pytest.approx(0)
    assert ray.incidence_angle_deg==pytest.approx(0)
    assert ray.source_angular_diameter_deg>0

def test_transmitted_habitat_requires_behind_glass():
    pane=facade()
    trans=scene_ray((-2,0,1),(1,0,0),(2,0,1),pane,"transmission")
    assert trans is not None
    np.testing.assert_allclose(trans.surface_point_m,[0,0,1])
    assert scene_ray((-2,0,1),(1,0,0),(2,0,1),pane,"reflection") is None
    assert scene_ray((-2,0,1),(1,0,0),(-2,0,1),pane,"transmission") is None

def test_far_lateral_tree_mirrors_outside_finite_pane():
    pane=facade()
    assert scene_ray((-2,0,1),(1,0,0),(-2,8,1),pane,"reflection") is None

def test_nearer_opaque_screen_occludes_reflected_image():
    glass=facade()
    screen=RectPatch("screen",(-1,0,1),(0,3,0),(0,0,3),"opaque")
    assert scene_ray((-2,0,1),(1,0,0),(-2,0,1),
                     glass,"reflection",blockers=[screen]) is None

def test_minimum_angular_distance_uses_edge_not_center():
    wide=RectPatch("wide",(0,5,1),(0,12,0),(0,0,2))
    eye=(-2,0,1)
    # The projection of gaze along x intersects at y=0, inside this patch,
    # even though the pane's centre y=5 is outside a narrow central FOV.
    assert minimum_heading_angle_deg(eye,(1,0,0),wide)==pytest.approx(0)
    center=np.asarray(wide.center_m)-np.asarray(eye)
    assert math.degrees(math.acos(center[0]/np.linalg.norm(center)))>45

def test_off_axis_pane_not_falsely_visible():
    pane=facade()
    assert minimum_heading_angle_deg((-2,6,1),(1,0,0),pane)>0

def test_rectangular_solid_angle_agrees_with_closed_form():
    pane=facade()
    actual=pane_solid_angle_sr((-2,0,1),pane)
    expected=4*math.atan(1/(2*math.sqrt(6)))
    assert actual==pytest.approx(expected,abs=1e-12)

def test_rotation_invariance_of_incidence_and_size():
    original=facade()
    eye=np.array([-2,0,1.]); tree=np.array([-2,0,1.]);hd=np.array([1.,0,0])
    ref=scene_ray(eye,hd,tree,original,"reflection")
    rot=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    rotate=lambda v:tuple(rot@np.asarray(v))
    other=RectPatch("rot",rotate(original.center_m),
                    rotate(original.u_full_m),rotate(original.v_full_m))
    turned=scene_ray(rotate(eye),rotate(hd),rotate(tree),other,"reflection")
    assert turned is not None
    assert turned.incidence_angle_deg==pytest.approx(ref.incidence_angle_deg)
    assert pane_solid_angle_sr(rotate(eye),other)==pytest.approx(
        pane_solid_angle_sr(eye,original))

def test_spectral_cone_catches_require_matching_surface_pixel():
    pane=facade();eye=(-2,0,1);heading=(1,0,0)
    ref=scene_ray(eye,heading,(-2,0,1),pane,"reflection")
    trans=scene_ray(eye,heading,(2,0,1),pane,"transmission")
    sens=np.column_stack([np.ones(4),[1,0,0,0]])
    catches=measured_pixel_cone_catches(ref,trans,[2]*4,[1]*4,
                                        [.1]*4,[.7]*4,
                                        [350,450,550,650],sens)
    assert catches.shape==(2,) and np.all(catches>0)
    off=scene_ray(eye,heading,(2,1,1),pane,"transmission")
    with pytest.raises(ValueError):
        measured_pixel_cone_catches(ref,off,[2]*4,[1]*4,
                                    [.1]*4,[.7]*4,[350,450,550,650],sens)

def test_missing_observation_never_becomes_behavior_probability():
    results=scene_path_table(
        [("B",(-2,0,1),(1,0,0))],
        [("tree",(-2,0,1),.3),("behind",(2,0,1),.4)],
        [facade()])
    assert {r["kind"] for r in results}=={"reflection","transmission"}
    assert all(r["calibrated_recognition"] is None for r in results)

def test_invalid_geometry_rejected():
    with pytest.raises(ValueError):
        RectPatch("bad",(0,0,0),(0,2,0),(0,2,0))
