import pytest
from birdglass.contact import RectPane
from birdglass.pose_contact import analyze_pose_tracks

KEYS={"head":("hx","hy","hz"),
      "left_wingtip":("lx","ly","lz"),
      "right_wingtip":("rx","ry","rz")}
RADII={"head":.02,"left_wingtip":.01,"right_wingtip":.01}
PANE=[RectPane("edge_glass",0,.5,.9,0,2)]

def make_pose(wing_y=.7,units="m"):
    scale=1 if units=="m" else 1000
    return [
      {"individual_id":"bird-a","trial_id":"trial-1","frame":i,
       "hx":x*scale,"hy":0.,"hz":1*scale,
       "lx":x*scale,"ly":wing_y*scale,"lz":1*scale,
       "rx":x*scale,"ry":-wing_y*scale,"rz":1*scale}
      for i,x in enumerate((-1.,1.))
    ]

def run_pose(rows,units="m",fps=120,pane=PANE):
    return analyze_pose_tracks(rows,KEYS,frames_per_second=fps,units=units,
             pane_surfaces=pane,keypoint_radii_m=RADII,
             coordinate_frame="calibrated_world")

def test_measured_spread_wingtip_contacts_edge_pane():
    x=run_pose(make_pose(.7))[0]
    c=x.first_sampled_keypoint_contact
    assert c is not None and c.body_keypoint=="left_wingtip"
    assert c.pane_id=="edge_glass"
    assert c.time_s_from_first_frame==pytest.approx(.495/120,abs=1e-8)
    assert x.observed_wingtip_distance_median_m==pytest.approx(1.4)
    assert not x.collision_free_certified

def test_folded_wings_avoid_sampled_tip_contact():
    x=run_pose(make_pose(.12))[0]
    assert x.first_sampled_keypoint_contact is None
    assert not x.collision_free_certified

def test_metric_unit_conversion_invariant():
    a=run_pose(make_pose(.7,units="m"),"m")[0]
    b=run_pose(make_pose(.7,units="mm"),"mm")[0]
    assert a.first_sampled_keypoint_contact.time_s_from_first_frame==pytest.approx(
      b.first_sampled_keypoint_contact.time_s_from_first_frame)
    assert a.observed_wingtip_distance_median_m==pytest.approx(
      b.observed_wingtip_distance_median_m)

def test_frame_gaps_must_not_be_interpolated():
    rows=make_pose(.7)
    rows[1]["frame"]=3
    x=run_pose(rows)[0]
    assert x.contiguous_frame_pairs==0
    assert x.gap_pairs_skipped==1
    assert x.first_sampled_keypoint_contact is None

def test_missing_tip_frame_does_not_invent_3d_point():
    rows=make_pose(.7)
    rows[0]["lx"]=float("nan")
    x=run_pose(rows)[0]
    assert x.invalid_keypoint_pairs_skipped==1
    assert x.first_sampled_keypoint_contact is None

def test_duplicate_frame_rejected():
    rows=make_pose(.7)
    rows[1]["frame"]=rows[0]["frame"]
    with pytest.raises(ValueError,match="Repeated frame"):
        run_pose(rows)

def test_invalid_frame_or_unscaled_pixels_rejected():
    with pytest.raises(ValueError,match="metric"):
        run_pose(make_pose(.7),units="pixel")
    with pytest.raises(ValueError):
        analyze_pose_tracks(make_pose(.7),KEYS,
            frames_per_second=120,units="m",pane_surfaces=PANE,
            keypoint_radii_m=RADII,coordinate_frame="camera_pixels")

def test_individual_and_trial_are_never_joined():
    a=make_pose(.7)
    b=make_pose(.12)
    for r in b:r["trial_id"]="trial-2"
    out=run_pose(a+b)
    assert len(out)==2
    assert out[0].first_sampled_keypoint_contact is not None
    assert out[1].first_sampled_keypoint_contact is None

def test_opaque_first_contact_stays_opaque():
    walls=[RectPane("wall",-0.2,.5,.9,0,2,"opaque"),
           RectPane("glass",0,.5,.9,0,2)]
    x=run_pose(make_pose(.7),pane=walls)[0]
    assert x.first_sampled_keypoint_contact.pane_material=="opaque"

def test_no_unmeasured_body_shape_inference():
    x=run_pose(make_pose(.12))[0]
    assert x.first_sampled_keypoint_contact is None
    assert x.collision_free_certified is False
