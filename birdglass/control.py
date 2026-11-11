"""3D delayed heading controller for fixed facades (structural model only).

Transparent surfaces are always physically blocking, but only recognized
glass can trigger avoidance. The cue effect inputs are explicit uncalibrated
hypotheses, not expected field efficacy.
"""
from collections import deque
from math import acos, sin, cos
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

def route(position,heading,panes,destination,span,body,step=.3):
    """Finite-search baseline over physically open passages around facade."""
    x=panes[0].x
    ys=np.arange(min(p.ymin for p in panes)-2,max(p.ymax for p in panes)+2,step)
    zs=np.arange(max(0,min(p.zmin for p in panes)-1.5),max(p.zmax for p in panes)+2,step)
    proposals=[]
    for y in ys:
        for z in zs:
            if any(p.ymin-span/2<=y<=p.ymax+span/2 and
                   p.zmin-body<=z<=p.zmax+body for p in panes):continue
            point=np.array([x+.3,y,z])
            ang=acos(float(np.clip(unit(point-position)@heading,-1,1)))
            if ang>1.2:continue
            score=ang+0.05*np.linalg.norm(point[1:]-destination[1:])
            proposals.append((score,y,z,point))
    return min(proposals,key=lambda v:v[:3])[3] if proposals else destination

def replay(start,velocity,destination,panes,recognition,draws,
           body_radius=.05,wingspan=.3,latency=.14,gain=4.5,
           max_lateral_accel=12.,detection_range=7.,dt=.025,max_time=4.):
    """First contact across every pane, using a time-delayed heading command.

    Draws are fixed per pane per trajectory and can be shared across policies.
    All numerical and biological parameters require independent validation.
    """
    if not panes or dt<=0 or max_time<=dt or latency<0 or gain<=0 or max_lateral_accel<=0:
        raise ValueError("invalid simulator inputs")
    if len({p.x for p in panes})!=1:
        raise ValueError("coplanar facade only")
    p=np.asarray(start,float)
    h=unit(velocity)
    speed=float(np.linalg.norm(velocity))
    goal=np.asarray(destination,float)
    target=goal.copy()
    commands=deque([h.copy() for _ in range(int(round(latency/dt))+1)])
    known=set()
    for i in range(int(max_time/dt)):
        for pane in panes:
            if pane.material!="glass" or pane.id in known:continue
            dx=pane.x-p[0]
            if not 0<=dx<=detection_range:continue
            center=np.array([dx,(pane.ymin+pane.ymax)/2-p[1],
                                  (pane.zmin+pane.zmax)/2-p[2]])
            angle=acos(float(np.clip(unit(center)@h,-1,1)))
            if angle>1.0:continue
            if draws.get(pane.id,1.)<recognition.get(pane.id,0.):
                known.add(pane.id)
                target=route(p,h,panes,goal,wingspan,body_radius)
        commands.append(unit(target-p))
        h=turn(h,commands.popleft(),dt,gain,max_lateral_accel,speed)
        nxt=p+h*speed*dt
        contact=first_contact(p,nxt,h*speed,panes,body_radius,wingspan)
        if contact:
            return {"outcome":contact.material,"pane":contact.pane_id,
                    "time_s":(i+contact.t)*dt}
        p=nxt
        if p[0]>panes[0].x+wingspan/2+.1:
            return {"outcome":"passed","pane":None,"time_s":(i+1)*dt}
        if abs(p[1])>100 or p[2]>100 or p[2]<-10:
            return {"outcome":"diverted","pane":None,"time_s":(i+1)*dt}
    return {"outcome":"unresolved","pane":None,"time_s":max_time}
