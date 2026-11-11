"""Contact geometry from externally measured time-varying 3D bird pose.

No single invented "wingspan" is used for all flight frames. Each measured
body/head/wing keypoint moves independently from frame t to t+1.
Keypoint-sphere contact is a conservative sampled-body proxy: absence of
contact does NOT demonstrate collision-free full wing membrane/body motion.

Metric calibration, source coordinate frame, frames per second, point
identity and point radii must be supplied. No imputation over gaps.
"""
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
import numpy as np
from .contact import first_sphere_contact

@dataclass(frozen=True)
class PoseContact:
    individual_id:str
    trial_id:str
    pane_id:str
    pane_material:str
    body_keypoint:str
    time_s_from_first_frame:float
    frame_index_before:int
    fraction_within_frame:float

@dataclass(frozen=True)
class PoseAudit:
    individual_id:str
    trial_id:str
    total_frames:int
    contiguous_frame_pairs:int
    gap_pairs_skipped:int
    invalid_keypoint_pairs_skipped:int
    observed_wingtip_distance_median_m:float | None
    first_sampled_keypoint_contact:PoseContact | None
    collision_free_certified:bool=False


def _point(row,columns,scale):
    try:
        arr=np.array([row[c] for c in columns],dtype=float)
    except (KeyError,ValueError,TypeError):
        return None
    return arr*scale if arr.shape==(3,) and np.isfinite(arr).all() else None


def analyze_pose_tracks(rows, keypoint_columns, *, frames_per_second, units,
                        pane_surfaces, keypoint_radii_m,
                        coordinate_frame):
    """Inspect pose tracks and earliest sampled-keypoint/pane contact.

    rows: iterable of mappings with individual_id, trial_id and frame.
    keypoint_columns: e.g. {"head":("head_x","head_y","head_z"),
      "left_wingtip":(...), "right_wingtip":(...)}.
    Whole-body shape remains unobserved when only a few points exist.
    """
    if (not isfinite(frames_per_second) or frames_per_second<=0 or
        units not in ("m","mm") or coordinate_frame!="calibrated_world"):
        raise ValueError("Explicit metric units, fps and world calibration required")
    if not keypoint_columns or not pane_surfaces:
        raise ValueError("Actual pose keypoint schema and panes are required")
    if any(len(c)!=3 or len(set(c))!=3 for c in keypoint_columns.values()):
        raise ValueError("Each keypoint needs three distinct coordinate columns")
    if set(keypoint_columns)!=set(keypoint_radii_m):
        raise ValueError("A measured or constrained radius is required for each point")
    if any(not isfinite(r) or r<0 for r in keypoint_radii_m.values()):
        raise ValueError("Invalid point radius")
    scale=1. if units=="m" else .001
    grouped=defaultdict(list)
    for row in rows:
        try:
            key=(str(row["individual_id"]),str(row["trial_id"]))
            frame=float(row["frame"])
        except (KeyError,TypeError,ValueError):
            raise ValueError("Missing individual, trial or frame") from None
        if any(not x or x=="None" for x in key) or not isfinite(frame) or frame<0 or int(frame)!=frame:
            raise ValueError("Non-finite, noninteger or unidentified frame")
        grouped[key].append((int(frame),row))
    if not grouped:
        raise ValueError("No real or synthetic pose rows provided")
    results=[]
    for (individual,trial),raw in sorted(grouped.items()):
        indexed=sorted(raw,key=lambda x:x[0])
        frames=[x[0] for x in indexed]
        if len(frames)!=len(set(frames)):
            raise ValueError("Repeated frame identifier within one trial")
        valid=0;gaps=0;missing=0;spans=[];all_hits=[]
        first=frames[0]
        for _,row in indexed:
            if "left_wingtip" in keypoint_columns and "right_wingtip" in keypoint_columns:
                l=_point(row,keypoint_columns["left_wingtip"],scale)
                r=_point(row,keypoint_columns["right_wingtip"],scale)
                if l is not None and r is not None:
                    spans.append(float(np.linalg.norm(l-r)))
        for (frame0,row0),(frame1,row1) in zip(indexed,indexed[1:]):
            if frame1-frame0!=1:
                gaps+=1
                continue
            valid+=1
            for name,cols in keypoint_columns.items():
                p=_point(row0,cols,scale)
                q=_point(row1,cols,scale)
                if p is None or q is None:
                    missing+=1
                    continue
                for pane in pane_surfaces:
                    hit=first_sphere_contact(p,q,pane,keypoint_radii_m[name])
                    if hit is None:
                        continue
                    t,_=hit
                    all_hits.append(PoseContact(individual,trial,pane.id,
                        pane.material,name,
                        (frame0-first+t)/frames_per_second,frame0,float(t)))
        first_contact=min(all_hits,key=lambda x:(
            x.time_s_from_first_frame,x.pane_id,x.body_keypoint)) if all_hits else None
        results.append(PoseAudit(individual,trial,len(frames),valid,gaps,
            missing,float(np.median(spans)) if spans else None,first_contact))
    return results
