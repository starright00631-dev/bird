"""Approach-gated bird/facade events from calibrated 3D tracks.

This is a *measurement* layer connecting moving birds, finite 3D surfaces and
bird-view habitat rays. It never converts optical visibility to recognition,
or video selection to an unconditional collision probability.

Methods anchor: Samuels et al. (2022), PeerJ 10:e14604,
https://doi.org/10.7717/peerj.14604 (including supp-4).
Their video 'near miss' is an initially window-intersecting flight that
redirected near the facade; selected videos are not all bird approaches.
"""
from dataclasses import dataclass
from math import isfinite
import numpy as np

from .contact import RectPane, first_sphere_contact
from .scene_optics import RectPatch, scene_path_table


@dataclass(frozen=True)
class VideoAnnotation:
    """Independent evidence, not a state inferred from the same trajectory."""
    outcome: str = "unknown"  # glass_contact, opaque_contact, no_contact, unknown
    contacted_surface_id: str | None = None
    complete_video_coverage: bool = False
    reviewed_from_source_video: bool = False

    def __post_init__(self):
        if self.outcome not in {"glass_contact", "opaque_contact",
                                "no_contact", "unknown"}:
            raise ValueError("Unknown video outcome")
        if self.outcome in {"glass_contact", "opaque_contact"} and not self.contacted_surface_id:
            raise ValueError("Verified contacts require a surface ID")
        if self.outcome not in {"glass_contact", "opaque_contact"} and self.contacted_surface_id is not None:
            raise ValueError("Surface ID without verified contact")
        if self.outcome != "unknown" and not self.reviewed_from_source_video:
            raise ValueError("Cannot claim independent verification without source review")


@dataclass(frozen=True)
class ApproachEvent:
    clip_id: str
    status: str
    first_risk_pane: str | None
    gate_time_s: float | None
    ballistic_time_to_contact_s: float | None
    ballistic_contact_xyz_m: tuple | None
    gate_speed_mps: float | None
    observed_geometry_first_contact: str | None
    optical_rays: tuple
    note: str
    unconditional_risk_identified: bool = False


def _vec(value):
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.isfinite(result).all():
        raise ValueError("Finite 3D vector required")
    return result


def _basis(patch):
    c, u, v = (_vec(patch.center_m), _vec(patch.u_full_m),
               _vec(patch.v_full_m))
    return c, patch.normal, u/np.linalg.norm(u), v/np.linalg.norm(v)


def _local(value, patch):
    c,n,u,v = _basis(patch)
    d = _vec(value)-c
    return np.array([d@n,d@u,d@v], dtype=float)


def _local_rect(patch):
    return RectPane(patch.id, 0.,
                    -np.linalg.norm(patch.u_full_m)/2,
                    np.linalg.norm(patch.u_full_m)/2,
                    -np.linalg.norm(patch.v_full_m)/2,
                    np.linalg.norm(patch.v_full_m)/2,patch.material)


def _segment_contact(start, end, patch, radius):
    """Exact swept-sphere finite patch contact, any world-space orientation."""
    a,b = _local(start,patch),_local(end,patch)
    return first_sphere_contact(a,b,_local_rect(patch),radius)


def _trajectory(rows, fps):
    if not isfinite(fps) or fps<=0:
        raise ValueError("A measured frame rate is required")
    records = []
    for r in rows:
        try:
            f = float(r["frame"])
            point = (r["x_m"],r["y_m"],r["z_m"])
        except (KeyError,TypeError):
            raise ValueError("Requires frame,x_m,y_m,z_m metric columns") from None
        if not isfinite(f) or f<0 or int(f)!=f:
            raise ValueError("Frames must be nonnegative integers")
        records.append((int(f),_vec(point)))
    if len(records)<3:
        raise ValueError("At least three observed frames required")
    records.sort(key=lambda x:x[0])
    if len({x[0] for x in records})!=len(records):
        raise ValueError("Duplicate frame numbers cannot be averaged")
    return records


def _first_ballistic(point, velocity, patches, radius, horizon):
    possibilities=[]
    end=point+velocity*horizon
    for patch in patches:
        side=float(_local(point,patch)[0])
        direction=float(_local(point+velocity,patch)[0]-side)
        if abs(side)<1e-9 or side*direction>=0:
            continue
        ans=_segment_contact(point,end,patch,radius)
        if ans is not None:
            t,dist=ans
            possibilities.append((t*horizon,patch,point+(end-point)*t))
    if not possibilities:
        return None,False
    possibilities.sort(key=lambda x:(x[0],x[1].id))
    earliest=possibilities[0][0]
    # Overlapping surfaces cannot be attributed by alphabetical ID alone.
    ambiguous=any((x[1].id!=possibilities[0][1].id)
                  and (abs(x[0]-earliest)<=1e-7)
                  for x in possibilities[1:])
    return possibilities[0],ambiguous


def analyze_approach(*,clip_id,rows,patches,
                     annotation=VideoAnnotation(),frames_per_second=120.,
                     geometry_registered=False,
                     gate_distance_m=2.,body_radius_m=.04,
                     ballistic_horizon_s=2.,followup_s=.1,
                     scene_sources=()):
    """One bounded and video-auditable potential window approach.

    Gate crossing uses only the current and previous frame. Initial
    collision course is the *ballistic* extrapolation from that entrance.
    All subsequent positions are used for outcome evaluation, never to
    redefine whether the initial approach was collision-directed.

    No video-based labels are inferred from geometry alone. For a verified
    no-contact case, the recording must cover the predicted contact time
    plus follow-up and contain no unobserved frame interval.
    """
    if not clip_id or not isinstance(clip_id,str):
        raise ValueError("Stable source clip identity required")
    if not geometry_registered:
        raise ValueError("Facade and trajectory must share a calibrated metric frame")
    if not patches or len({p.id for p in patches})!=len(patches):
        raise ValueError("Nonempty, uniquely named surface geometry required")
    if (not all(isfinite(v) for v in
                (gate_distance_m,body_radius_m,ballistic_horizon_s,followup_s))
        or min(gate_distance_m,body_radius_m,ballistic_horizon_s)<=0
        or followup_s<0):
        raise ValueError("Invalid metric or time parameters")
    track=_trajectory(rows,frames_per_second)

    selected=None
    for (f0,p0),(f1,p1) in zip(track,track[1:]):
        if f1!=f0+1:
            # No interpolation across unobserved intervals, including
            # intervals before potential gate entry.
            continue
        velocity=(p1-p0)*frames_per_second
        if np.linalg.norm(velocity)<1e-9:
            continue
        for patch in patches:
            c,n,_,_=_basis(patch)
            d0=float((p0-c)@n)
            d1=float((p1-c)@n)
            face=1. if d0>=0 else -1.
            q0,q1=face*d0,face*d1
            if not (q0>gate_distance_m>=q1 and q0>q1):
                continue
            alpha=(q0-gate_distance_m)/(q0-q1)
            entrance=p0+alpha*(p1-p0)
            time_s=(f0+alpha-track[0][0])/frames_per_second
            candidate=(time_s,entrance,velocity,f1,patch.id)
            if selected is None or candidate[0]<selected[0]:
                selected=candidate
    if selected is None:
        return ApproachEvent(clip_id,"no_observed_inbound_gate",None,None,
                             None,None,None,None,(),
                             "No metric inbound gate crossing recorded; left truncation cannot be ruled out")
    t_gate,entry,velocity,frame_after_gate,trigger_pane=selected
    initial,ambiguous=_first_ballistic(entry,velocity,patches,body_radius_m,
                                       ballistic_horizon_s)
    if initial is None:
        return ApproachEvent(clip_id,"not_on_ballistic_collision_course",
                             None,t_gate,None,None,float(np.linalg.norm(velocity)),
                             None,(),"A near-facade flyby is not an observed near miss")
    t_contact,impacted,contact_pt=initial
    if ambiguous:
        return ApproachEvent(clip_id,"ambiguous_initial_surface",None,t_gate,
                             t_contact,tuple(contact_pt),float(np.linalg.norm(velocity)),
                             None,(),"The ballistic first contact ties across multiple surfaces")
    if impacted.material!="glass":
        return ApproachEvent(clip_id,"opaque_first_on_ballistic_path",
                             None,t_gate,t_contact,tuple(contact_pt),
                             float(np.linalg.norm(velocity)),None,(),
                             "Opaque structure precedes glass on the initial course")

    # Geometry-only visible habitat cues. Neither reflection nor
    # transmission implies recognition or behavioral attraction.
    rays=()
    if scene_sources:
        scene_table=scene_path_table(
            [(clip_id,tuple(entry),tuple(velocity))],
            list(scene_sources),list(patches))
        rays=tuple(r for r in scene_table if r["pane_id"]==impacted.id)

    # Inspect FULL sampled geometry, not only the anticipated glass patch.
    geom_hit=None
    for (f0,p0),(f1,p1) in zip(track,track[1:]):
        if f1!=f0+1 or (f1-track[0][0])/frames_per_second<t_gate:
            continue
        for patch in patches:
            ans=_segment_contact(p0,p1,patch,body_radius_m)
            if ans is not None:
                time=(f0+ans[0]-track[0][0])/frames_per_second
                if geom_hit is None or (time,patch.id)<(geom_hit[0],geom_hit[1]):
                    geom_hit=(time,patch.id,patch.material)
    geometry_pane=geom_hit[1] if geom_hit else None
    if annotation.outcome in {"glass_contact","opaque_contact"}:
        chosen={p.id:p.material for p in patches}
        if chosen.get(annotation.contacted_surface_id)!=annotation.outcome.split("_")[0]:
            raise ValueError("Video contact surface/material inconsistent with registry")
        mismatch=(geometry_pane is not None
                  and geometry_pane!=annotation.contacted_surface_id)
        return ApproachEvent(clip_id,"video_verified_"+annotation.outcome,
            impacted.id,t_gate,t_contact,tuple(contact_pt),
            float(np.linalg.norm(velocity)),geometry_pane,rays,
            "Independent impact label; geometric first-contact disagreement requires review"
             if mismatch else "Impact confirmed by independent video, not inferred from simulation")

    last_time=(track[-1][0]-track[0][0])/frames_per_second
    starts=[(f0,f1) for (f0,_),(f1,_) in zip(track,track[1:])
            if (f1-track[0][0])/frames_per_second>=t_gate and f1-f0!=1]
    adequately_observed=(annotation.complete_video_coverage
                         and last_time>=t_gate+t_contact+followup_s-1e-9
                         and not starts)
    if annotation.outcome=="no_contact":
        if not adequately_observed:
            status="right_censored"
            note="A negative observation requires continuous coverage past the counterfactual contact time"
        elif geom_hit is not None:
            status="video_geometry_disagreement"
            note="Video no-contact conflicts with body-sphere geometric contact"
        else:
            status="video_verified_geometric_clearance"
            note="Originally on ballistic collision course; independent video verifies no contact"
    else:
        status="unverified_contact_status" if adequately_observed else "right_censored"
        note="No independent contact/avoidance label; sampled geometry is insufficient"
    return ApproachEvent(clip_id,status,impacted.id,t_gate,t_contact,
                         tuple(contact_pt),float(np.linalg.norm(velocity)),
                         geometry_pane,rays,note)


def summarize_video_events(events):
    """Counts of selected, geometrically-at-risk clips; no incidence inference."""
    events=list(events)
    keys=[e.clip_id for e in events]
    if len(keys)!=len(set(keys)):
        raise ValueError("A recording cannot be double-counted as independent approaches")
    risk=[e for e in events if e.first_risk_pane is not None]
    return {
        "n_supplied_clips":len(events),
        "n_on_initial_ballistic_glass_course":len(risk),
        "n_independently_verified_glass_contact":sum(
            e.status=="video_verified_glass_contact" for e in risk),
        "n_independently_verified_opaque_contact":sum(
            e.status=="video_verified_opaque_contact" for e in risk),
        "n_independently_verified_clearance":sum(
            e.status=="video_verified_geometric_clearance" for e in risk),
        "n_right_censored":sum(e.status=="right_censored" for e in risk),
        "n_outcome_unresolved":sum(e.status not in {
            "video_verified_glass_contact","video_verified_opaque_contact",
            "video_verified_geometric_clearance","right_censored"}
            for e in risk),
        "population_collision_probability_identified":False,
        "reason":"Unknown complete bird-approach sampling frame and source-camera event selection",
    }
