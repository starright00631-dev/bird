import math
import numpy as np
import pytest
from birdglass.scene_optics import RectPatch
from birdglass.approach_events import (
    VideoAnnotation,analyze_approach,summarize_video_events)

GLASS=RectPatch("G",(0,0,1),(0,2,0),(0,0,2),"glass")
OPAQUE=RectPatch("wall",(-.5,0,1),(0,2,0),(0,0,2),"opaque")

def frames(points):
    return [{"frame":i,"x_m":p[0],"y_m":p[1],"z_m":p[2]}
            for i,p in enumerate(points)]

def run(points,*,annotation=VideoAnnotation(),patches=(GLASS,),
        fps=10,scene_sources=(),gate=1.,radius=.04):
    return analyze_approach(
        clip_id="clip-1",rows=frames(points),patches=patches,
        annotation=annotation,frames_per_second=fps,
        geometry_registered=True,gate_distance_m=gate,
        body_radius_m=radius,ballistic_horizon_s=2.,
        followup_s=.1,scene_sources=scene_sources)

def verified(outcome,surface=None,complete=True):
    return VideoAnnotation(outcome,surface,complete,True)

def test_direct_collision_requires_independent_contact_annotation():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1),(-.4,0,1),
          (-.02,0,1),(.2,0,1)]
    unreviewed=run(path)
    assert unreviewed.status=="unverified_contact_status"
    assert unreviewed.first_risk_pane=="G"
    assert unreviewed.ballistic_time_to_contact_s>0
    assert unreviewed.observed_geometry_first_contact=="G"
    confirmed=run(path,annotation=verified("glass_contact","G"))
    assert confirmed.status=="video_verified_glass_contact"
    assert not confirmed.unconditional_risk_identified

def test_turn_away_with_full_video_is_confirmed_clearance():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1),
          (-.7,.7,1),(-.5,1.8,1),(-.25,3.0,1),
          (-.2,4.0,1),(-.15,5.0,1),(-.1,6.0,1)]
    e=run(path,annotation=verified("no_contact"))
    assert e.status=="video_verified_geometric_clearance"
    assert e.observed_geometry_first_contact is None

def test_short_clip_is_right_censored_not_successful_avoidance():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1)]
    e=run(path,annotation=verified("no_contact"))
    assert e.status=="right_censored"

def test_unreviewed_complete_video_not_assumed_to_be_avoidance():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1),
          (-.7,1,1),(-.6,3,1),(-.5,5,1),(-.4,7,1)]
    e=run(path,annotation=VideoAnnotation(complete_video_coverage=True))
    assert e.status=="unverified_contact_status"

def test_non_collision_course_flyby_not_counted_as_near_miss():
    path=[(-2,4,1),(-1.2,4,1),(-.8,4,1),(-.4,4,1)]
    e=run(path)
    assert e.status=="not_on_ballistic_collision_course"
    assert e.first_risk_pane is None

def test_opaque_first_is_not_glass_risk_denominator():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1),(-.4,0,1)]
    e=run(path,patches=(GLASS,OPAQUE),gate=.8)
    assert e.status=="opaque_first_on_ballistic_path"
    assert e.first_risk_pane is None

def test_unknown_and_uncalibrated_input_refused():
    path=frames([(-2,0,1),(-1,0,1),(-.4,0,1)])
    with pytest.raises(ValueError,match="calibrated"):
        analyze_approach(clip_id="x",rows=path,patches=[GLASS])
    with pytest.raises(ValueError):
        VideoAnnotation("no_contact",reviewed_from_source_video=False)

def test_missing_frames_censor_verified_negative():
    path=frames([(-2,0,1),(-1.2,0,1),(-.8,0,1),
                 (-.6,.8,1),(-.5,2,1),(-.5,4,1),(-.5,5,1)])
    path[4]["frame"]=5
    path[5]["frame"]=6
    path[6]["frame"]=7
    e=analyze_approach(clip_id="gap",rows=path,patches=[GLASS],
        annotation=verified("no_contact"),frames_per_second=10,
        geometry_registered=True,gate_distance_m=1.,followup_s=.1)
    assert e.status=="right_censored"

def test_optical_reflection_is_inspectable_not_recognition():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1),
          (-.4,0,1),(.1,0,1)]
    e=run(path,scene_sources=[("tree",(-2,0,1),.3)])
    assert len(e.optical_rays)>=1
    assert any(r["kind"]=="reflection" for r in e.optical_rays)
    assert all(r["calibrated_recognition"] is None for r in e.optical_rays)

def test_tilted_pane_rotation_invariance_of_collision_course():
    # 90-degree rotation about the vertical world axis (z).
    rot=np.array([[0,-1,0],[1,0,0],[0,0,1]])
    transformed=RectPatch("G",tuple(rot@np.array(GLASS.center_m)),
        tuple(rot@np.array(GLASS.u_full_m)),
        tuple(rot@np.array(GLASS.v_full_m)))
    start=[(-2,0,1),(-1.2,0,1),(-.8,0,1),(-.4,0,1)]
    a=run(start)
    b=run([tuple(rot@np.array(p)) for p in start],patches=[transformed])
    assert a.status==b.status=="right_censored"
    assert a.first_risk_pane==b.first_risk_pane=="G"
    assert b.ballistic_time_to_contact_s==pytest.approx(a.ballistic_time_to_contact_s)

def test_observation_metric_never_claims_population_risk():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1),(-.4,0,1)]
    contact=run(path,annotation=verified("glass_contact","G"))
    summary=summarize_video_events([contact])
    assert summary["n_independently_verified_glass_contact"]==1
    assert summary["population_collision_probability_identified"] is False
    with pytest.raises(ValueError,match="double-counted"):
        summarize_video_events([contact,contact])

def test_geometry_video_conflict_marked_for_review():
    path=[(-2,0,1),(-1.2,0,1),(-.8,0,1),
          (-.4,0,1),(.1,0,1),(.4,0,1)]
    e=run(path,annotation=verified("no_contact"))
    assert e.status=="video_geometry_disagreement"
