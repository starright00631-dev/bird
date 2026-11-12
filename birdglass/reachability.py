"""Reachable gap search under delayed constant-airspeed turning constraints.

The existing geometric planner checks only a gap endpoint. This numerical
screen evaluates every candidate with a delayed yaw/3D heading controller
and continuous swept body/wing contact on ALL glass and opaque surfaces.

A returned candidate is only safe under the stated synthetic state and
controller assumptions, not biologically validated or field-safe.
Failure to find a candidate in a finite search is NOT a proof that
avoidance is impossible.
"""
from collections import deque
from dataclasses import dataclass
from math import acos
import numpy as np
from .contact import first_contact
from .control import turn, unit


@dataclass(frozen=True)
class Rollout:
    status: str
    time_s: float
    end_xyz: tuple
    contacted_pane: str | None


@dataclass(frozen=True)
class GapDecision:
    target_xyz: tuple | None
    status: str
    candidates_tested: int
    candidate_status_counts: dict


def rollout_target(start, velocity, target, panes, *, latency_s=.14,
                   gain_per_s=4.5, max_lateral_accel_mps2=12.,
                   body_radius_m=.05, wingspan_m=.3,
                   dt=.02, max_time_s=6.):
    """Simulate finite controller + all-surface collision against one target."""
    if not panes or len({p.x for p in panes})!=1:
        raise ValueError("This experimental planner requires one fixed facade plane")
    if (dt<=0 or max_time_s<=dt or latency_s<0 or gain_per_s<=0 or
        max_lateral_accel_mps2<=0 or body_radius_m<=0 or wingspan_m<=0):
        raise ValueError("Positive time/morphology/controller inputs required")
    p=np.asarray(start,dtype=float)
    v=np.asarray(velocity,dtype=float)
    destination=np.asarray(target,dtype=float)
    if p.shape!=(3,) or v.shape!=(3,) or destination.shape!=(3,) or not all(
        np.isfinite(x).all() for x in (p,v,destination)):
        raise ValueError("Finite 3D state required")
    speed=float(np.linalg.norm(v))
    heading=unit(v)
    x_plane=panes[0].x
    if p[0]>=x_plane or v[0]<=0:
        raise ValueError("Only forward-side arrivals currently supported")
    lag=int(round(latency_s/dt))
    commands=deque([heading.copy() for _ in range(lag)])
    lo_y=min(x.ymin for x in panes)-3
    hi_y=max(x.ymax for x in panes)+3
    hi_z=max(x.zmax for x in panes)+3
    for i in range(int(max_time_s/dt)):
        vec=destination-p
        desired=heading if np.linalg.norm(vec)<1e-10 or vec @ heading<=0 else unit(vec)
        commands.append(desired)
        heading=turn(heading,commands.popleft(),dt,gain_per_s,
                     max_lateral_accel_mps2,speed)
        q=p+speed*dt*heading
        hit=first_contact(p,q,heading*speed,panes,body_radius_m,wingspan_m)
        if hit is not None:
            endpoint=tuple(p+(q-p)*hit.t)
            return Rollout(hit.material,(i+hit.t)*dt,endpoint,hit.pane_id)
        p=q
        if p[0]>x_plane+.5*wingspan_m+.1:
            return Rollout("crossed",(i+1)*dt,tuple(p),None)
        if p[1]<lo_y or p[1]>hi_y or p[2]<-1 or p[2]>hi_z:
            return Rollout("diverted",(i+1)*dt,tuple(p),None)
    return Rollout("unresolved",max_time_s,tuple(p),None)


def choose_reachable_gap(start, velocity, goal, panes, *, latency_s=.14,
                         gain_per_s=4.5, max_lateral_accel_mps2=12.,
                         body_radius_m=.05, wingspan_m=.3, dt=.02,
                         max_candidates=16, grid_m=.4, max_time_s=6.):
    """Evaluate ranked feasible *geometric* gaps with a physical rollout.

    The first collision-free crossing within the tested set is returned.
    The search can abstain; it must never assert that every possible
    real bird maneuver has been exhausted.
    """
    if not panes or len({p.x for p in panes})!=1:
        raise ValueError("Coplanar fixed facade required")
    if max_candidates<1 or grid_m<=0:
        raise ValueError("Finite candidate budget required")
    p,heading,destination=np.asarray(start,float),unit(velocity),np.asarray(goal,float)
    x_plane=panes[0].x
    y_values=np.arange(min(x.ymin for x in panes)-1.8,
                       max(x.ymax for x in panes)+1.81,grid_m)
    z_values=np.arange(max(0.,min(x.zmin for x in panes)-1.2),
                       max(x.zmax for x in panes)+1.81,grid_m)
    candidates=[]
    for y in y_values:
        for z in z_values:
            if any(x.ymin-wingspan_m/2<=y<=x.ymax+wingspan_m/2 and
                   x.zmin-body_radius_m<=z<=x.zmax+body_radius_m
                   for x in panes):
                continue
            point=np.array([x_plane+.5,y,z])
            travel=point-p
            if np.linalg.norm(travel)<1e-10:
                continue
            angle=acos(float(np.clip(unit(travel)@heading,-1,1)))
            # Do not invite an immediate 180-degree turn in this planner.
            if angle>1.4:continue
            cost=angle+.04*np.linalg.norm(point[1:]-destination[1:])
            candidates.append((cost,float(y),float(z),tuple(point)))
    candidates.sort()
    statuses={}
    for _,_,_,candidate in candidates[:max_candidates]:
        rollout=rollout_target(start,velocity,candidate,panes,
             latency_s=latency_s,gain_per_s=gain_per_s,
             max_lateral_accel_mps2=max_lateral_accel_mps2,
             body_radius_m=body_radius_m,wingspan_m=wingspan_m,
             dt=dt,max_time_s=max_time_s)
        statuses[rollout.status]=statuses.get(rollout.status,0)+1
        if rollout.status=="crossed":
            return GapDecision(candidate,"screened_crossing_found",
                               sum(statuses.values()),statuses)
    return GapDecision(None,"no_crossing_found_in_tested_candidates",
                       sum(statuses.values()),statuses)
