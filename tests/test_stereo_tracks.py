import numpy as np
import pytest
from birdglass.stereo_tracks import (
    normalize_wide_rows, read_stereo_csv, motion_summary,
    require_independent_bird_identity
)
from birdglass.pose_contact import analyze_pose_tracks
from birdglass.contact import RectPane

PARTS=("Box","Head","Tail","LeftWing","RightWing")

def row(frame,birds=("B1",),delta_mm=0):
    data={"Frame":frame}
    for b in birds:
        for part in PARTS:
            for axis in ("X","Y","Z"):
                data[f"{b}_{part}_{axis}"]=(
                    1000+delta_mm if axis=="X" else
                    700 if axis=="Y" else 500)
        data[f"{b}_Box_W"]=100  # pixels, never used as metres
        data[f"{b}_Box_H"]=85
    return data

def test_publication_schema_preserves_mm_and_pixel_separation():
    data=normalize_wide_rows([row(0),row(1,delta_mm=10)],"clip001")
    assert data.units=="mm" and data.frames_per_second==120
    assert len(data.observations)==2
    assert data.observations[0]["box_center_x"]==1000
    assert "box_w" not in data.observations[0]
    assert "box_center" in data.keypoint_columns
    summary=motion_summary(data)
    assert summary["B1"]["median_speed_mps"]==pytest.approx(1.2)
    assert summary["B1"]["contiguous_velocity_intervals"]==1
    assert not summary["B1"]["source_identity_certified"]

def test_multi_bird_tracking_never_conflates_B1_B2():
    data=normalize_wide_rows([row(0,("B1","B2")),
                              row(1,("B1","B2"),10)],"group_clip")
    assert len(data.observations)==4
    assert data.bird_labels==("B1","B2")
    assert len({x["individual_id"] for x in data.observations})==2

def test_unchanged_B1_in_different_recordings_is_not_new_verified_individual():
    a=normalize_wide_rows([row(0)],"first")
    b=normalize_wide_rows([row(0)],"second")
    assert a.observations[0]["individual_id"]!=b.observations[0]["individual_id"]
    with pytest.raises(ValueError,match="unverified"):
        require_independent_bird_identity(a)

def test_fps_and_units_link_into_pose_without_pane_inference():
    data=normalize_wide_rows([row(0),row(1,delta_mm=10)],"clip")
    pane=[RectPane("test_pane",1.5,-1,1,0,1)]
    r=analyze_pose_tracks(data.observations,data.keypoint_columns,
       frames_per_second=data.frames_per_second,units=data.units,
       pane_surfaces=pane,
       keypoint_radii_m={k:0. for k in data.keypoint_columns},
       coordinate_frame="calibrated_world")
    assert r[0].contiguous_frame_pairs==1
    assert r[0].first_sampled_keypoint_contact is None
    assert not r[0].collision_free_certified

def test_gap_frame_prohibits_false_velocity():
    data=normalize_wide_rows([row(0),row(2,delta_mm=10)],"gap")
    assert motion_summary(data)["B1"]["contiguous_velocity_intervals"]==0

def test_missing_wingpoint_does_not_become_zero_position():
    a,b=row(0),row(1,delta_mm=10)
    b["B1_RightWing_X"]=""
    data=normalize_wide_rows([a,b],"missing")
    assert np.isnan(data.observations[1]["right_wingtip_x"])

def test_duplicate_frame_rejected():
    with pytest.raises(ValueError,match="repeated"):
       normalize_wide_rows([row(0),row(0)],"clip")

def test_missing_required_3d_coordinate_rejected():
    r=row(0)
    del r["B1_Head_Z"]
    with pytest.raises(ValueError,match="Missing 3D"):
        normalize_wide_rows([r],"clip")

def test_image_only_fallback_cannot_be_called_3d():
    r=row(0)
    r.pop("B1_Box_Z")
    r["B1_Box_H"]=1000 # still only pixels
    with pytest.raises(ValueError):
        normalize_wide_rows([r],"clip")

def test_duplicate_csv_header_rejected():
    with pytest.raises(ValueError):
        read_stereo_csv("Frame,B1_Head_X,B1_Head_X\n0,1,2\n","clip")
