"""3D delayed heading controller for fixed facades (structural model only).

Transparent surfaces are always physically blocking, but only recognized
glass can trigger avoidance. The cue effect inputs are explicit uncalibrated
hypotheses, not expected field efficacy.
"""
from collections import deque
from math import acos, sin, cos
from .scene_optics import RectPatch, minimum_heading_angle_deg
import numpy as np
from .contact import first_contact

def unit(x):
    x=np.asarray(x,float)
    n=float(np.linalg.norm(x))
    if x.shape!=(3,) or not np.isfinite(x).all() or n<1e-12:
        raise ValueError("finite nonzero 3D vector required")
    return x/n

def turn(heading,target,dt,gain,amax,speed):
    a,b=unit(heading),unit(target)
    angle=acos(float(np.clip(a@b,-1.,1.)))
    if angle<1e-12:return a
    tangent=b-a*(a@b)
    if np.linalg.norm(tangent)<1e-10:
        tangent=np.cross(a,[0,0,1.])
        if np.linalg.norm(tangent)<1e-10:tangent=np.cross(a,[0,1.,0])
    tangent=unit(tangent)
    theta=min(angle,dt*gain*angle,dt*amax/speed)
    return unit(a*cos(theta)+tangent*sin(theta))

def perceived_surfaces(panes, recognized_glass):
    """Structural knowledge state: opaque facade plus recognized glazing.

    Opaque geometry is assumed visible (not an empirically calibrated vision
    model). Never pass this subset to the true physical contact calculation.
    """
    known=set(recognized_glass)
    return [pane for pane in panes if pane.material=="opaque"
            or (pane.material=="glass" and pane.id in known)]


def route(position,heading,panes,destination,span,body,step=.3,
          recognized_glass=()):
    """Hypothetical gap search in perceived, not omniscient, geometry."""
    perceived=perceived_surfaces(panes,recognized_glass)
    if not perceived:
        return np.asarray(destination,float).copy()
    x=perceived[0].x
    ys=np.arange(min(p.ymin for p in perceived)-2,
                 max(p.ymax for p in perceived)+2,step)
    zs=np.arange(max(0,min(p.zmin for p in perceived)-1.5),
                 max(p.zmax for p in perceived)+2,step)
    proposals=[]
    for y in ys:
        for z in zs:
            if any(p.ymin-span/2<=y<=p.ymax+span/2 and
                   p.zmin-body<=z<=p.zmax+body for p in perceived):continue
            point=np.array([x+.3,y,z])
            ang=acos(float(np.clip(unit(point-position)@heading,-1,1)))
            if ang>1.2:continue
            score=ang+0.05*np.linalg.norm(point[1:]-destination[1:])
            proposals.append((score,y,z,point))
    return min(proposals,key=lambda v:v[:3])[3] if proposals else destination

def visible_glass_ids(position,heading,panes,max_forward_distance_m,
                      max_view_angle_deg=57.2957795131):
    """Geometrically visible *portion* of each glass patch, not its centre.

    This is a field-of-view candidate set only. It does not infer whether
    birds can distinguish glass from a reflected/transmitted scene.
    """
    p=np.asarray(position,float)
    if p.shape!=(3,) or not np.isfinite(p).all() or max_forward_distance_m<=0:
        raise ValueError("invalid observer geometry")
    if not 0<max_view_angle_deg<180:
        raise ValueError("invalid angular attention threshold")
    return [
        pane.id for pane in panes
        if pane.material=="glass"
        and 0<=pane.x-p[0]<=max_forward_distance_m
        and minimum_heading_angle_deg(p,heading,RectPatch.from_axis_pane(pane))
            <=max_view_angle_deg
    ]


def replay(start,velocity,destination,panes,recognition,draws,
           body_radius=.05,wingspan=.3,latency=.14,gain=4.5,
           max_lateral_accel=12.,detection_range=7.,dt=.025,max_time=4.,
           planner_strategy="geometric"):
    """First contact across every pane, using a time-delayed heading command.

    Draws are fixed per pane per trajectory and can be shared across policies.
    All numerical and biological parameters require independent validation.
    """
    if not panes or dt<=0 or max_time<=dt or latency<0 or gain<=0 or max_lateral_accel<=0:
        raise ValueError("invalid simulator inputs")
    if len({p.x for p in panes})!=1:
        raise ValueError("coplanar facade only")
    if planner_strategy not in ("geometric","screened"):
        raise ValueError("planner_strategy must be geometric or screened")
    p=np.asarray(start,float)
    h=unit(velocity)
    speed=float(np.linalg.norm(velocity))
    goal=np.asarray(destination,float)
    target=goal.copy()
    # With zero latency the current steering target must take effect in
    # this step, not the following one. Round to the nearest time step;
    # caller must check time-step sensitivity for noninteger delays.
    lag=int(round(latency/dt))
    commands=deque([h.copy() for _ in range(lag)])
    known=set()
    planning_status="not_triggered"
    if len({pane.id for pane in panes})!=len(panes):
        raise ValueError("pane ids must be unique")
    for i in range(int(max_time/dt)):
        candidates=set(visible_glass_ids(p,h,panes,detection_range))
        for pane in panes:
            if pane.id not in candidates or pane.id in known:continue
            if draws.get(pane.id,1.)<recognition.get(pane.id,0.):
                known.add(pane.id)
                if planner_strategy=="geometric":
                    planning_status="geometric_unchecked"
                    target=route(p,h,panes,goal,wingspan,body_radius,
                                 recognized_glass=known)
                else:
                    # Import only at call time: reachability shares turn()
                    # and contact() kernels with this controller.
                    from .reachability import choose_reachable_gap
                    # Screen candidate actions against the *perceived* map,
                    # not hidden glass. True first_contact below still
                    # checks every physical facade patch and transfer.
                    decision=choose_reachable_gap(
                        p,h*speed,goal,perceived_surfaces(panes,known),
                        latency_s=latency,
                        gain_per_s=gain,
                        max_lateral_accel_mps2=max_lateral_accel,
                        body_radius_m=body_radius,wingspan_m=wingspan,
                        dt=dt,max_candidates=12,max_time_s=max_time+2.)
                    planning_status=decision.status
                    if decision.target_xyz is not None:
                        target=np.asarray(decision.target_xyz,float)
                    # If finite search finds no physically verified crossing,
                    # keep prior command, never claim a safe escape route.
        commands.append(unit(target-p))
        h=turn(h,commands.popleft(),dt,gain,max_lateral_accel,speed)
        nxt=p+h*speed*dt
        contact=first_contact(p,nxt,h*speed,panes,body_radius,wingspan)
        if contact:
            return {"outcome":contact.material,"pane":contact.pane_id,
                    "time_s":(i+contact.t)*dt,
                    "end_xyz":tuple(p+(nxt-p)*contact.t),
                    "planning_status":planning_status}
        p=nxt
        if p[0]>panes[0].x+wingspan/2+.1:
            return {"outcome":"passed","pane":None,"time_s":(i+1)*dt,
                    "end_xyz":tuple(p),"planning_status":planning_status}
        if abs(p[1])>100 or p[2]>100 or p[2]<-10:
            return {"outcome":"diverted","pane":None,"time_s":(i+1)*dt,
                    "end_xyz":tuple(p),"planning_status":planning_status}
    return {"outcome":"unresolved","pane":None,"time_s":max_time,
            "end_xyz":tuple(p),"planning_status":planning_status}
