"""Continuous swept collision with *first contact time* across fixed facade surfaces.

Each bird body/wing sample is approximated as a sphere swept along a straight
segment during one simulation step. Piecewise convex distance to a finite pane
is evaluated exactly up to floating point tolerance. First-contact time is
found on the decreasing side of the distance curve, not from pane iteration
order. Wings are stationary relative to the heading during a step; articulation
is not modelled. This is a kinematic geometric kernel, not an injury model.
"""
from dataclasses import dataclass
from math import sqrt
from typing import Sequence
import numpy as np

@dataclass(frozen=True)
class RectPane:
    id: str
    x: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float
    material: str = "glass"

    def __post_init__(self):
        if self.ymin >= self.ymax or self.zmin >= self.zmax:
            raise ValueError("Pane bounds must be increasing")
        if self.material not in {"glass", "opaque"}:
            raise ValueError("material must be glass or opaque")

@dataclass(frozen=True)
class SweptContact:
    pane_id: str
    material: str
    body_part: str
    t: float
    distance_m: float


def _vec(x):
    v = np.asarray(x, dtype=float)
    if v.shape != (3,) or not np.isfinite(v).all():
        raise ValueError("finite position/velocity 3-vector required")
    return v


def _distance_sq(p, pane):
    return ((p[0]-pane.x)**2
            + max(pane.ymin-p[1], 0., p[1]-pane.ymax)**2
            + max(pane.zmin-p[2], 0., p[2]-pane.zmax)**2)


def _intervals(a, b, pane):
    d = b-a
    cuts = [0., 1.]
    for axis, bounds in ((1, (pane.ymin, pane.ymax)),
                         (2, (pane.zmin, pane.zmax))):
        if abs(d[axis]) > 1e-14:
            for edge in bounds:
                t = float((edge-a[axis])/d[axis])
                if 0 < t < 1:
                    cuts.append(t)
    return sorted(set(cuts))


def _minimizer(a, b, pane):
    d = b-a
    candidates = [(0., _distance_sq(a, pane)),
                  (1., _distance_sq(b, pane))]
    for low, high in zip(_intervals(a,b,pane)[:-1],
                         _intervals(a,b,pane)[1:]):
        mid=(low+high)/2
        p=a+d*mid
        components=[(float(a[0]-pane.x),float(d[0]))]
        if p[1]<pane.ymin: components.append((float(a[1]-pane.ymin),float(d[1])))
        elif p[1]>pane.ymax: components.append((float(a[1]-pane.ymax),float(d[1])))
        if p[2]<pane.zmin: components.append((float(a[2]-pane.zmin),float(d[2])))
        elif p[2]>pane.zmax: components.append((float(a[2]-pane.zmax),float(d[2])))
        denom=sum(v*v for _,v in components)
        t = mid if denom < 1e-24 else min(high,max(low,
            -sum(q*v for q,v in components)/denom))
        candidates.append((t,_distance_sq(a+d*t,pane)))
    return min(candidates,key=lambda x:(x[1],x[0]))


def segment_rect_distance(start, end, pane):
    a,b=_vec(start),_vec(end)
    return sqrt(max(0.,_minimizer(a,b,pane)[1]))


def first_sphere_contact(start, end, pane, radius_m):
    if radius_m < 0 or not np.isfinite(radius_m):
        raise ValueError("invalid radius")
    a,b=_vec(start),_vec(end)
    r2=radius_m**2
    if _distance_sq(a,pane)<=r2+1e-12:
        return 0.,sqrt(_distance_sq(a,pane))
    t_min,d2=_minimizer(a,b,pane)
    if d2>r2+1e-12:
        return None
    # Distance to a convex set along a segment is convex: on [0,t_min],
    # the first threshold crossing is the unique earliest root.
    low,high=0.,t_min
    for _ in range(55):
        mid=(low+high)/2
        if _distance_sq(a+(b-a)*mid,pane)<=r2:
            high=mid
        else:
            low=mid
    return high,sqrt(_distance_sq(a+(b-a)*high,pane))


def first_contact(start, end, velocity, panes:Sequence[RectPane],
                  body_radius_m, wingspan_m, wing_radius_m=.008):
    """Return earliest contact regardless of order of pane records.

    Approximates a bird by a body sphere and four spanwise wing spheres.
    Ties are deterministic, not claims about injury severity.
    """
    if min(body_radius_m,wingspan_m,wing_radius_m)<0:
        raise ValueError("negative dimensions")
    a,b,v=_vec(start),_vec(end),_vec(velocity)
    n=np.linalg.norm(v)
    if n<1e-12:
        raise ValueError("velocity must be nonzero")
    forward=v/n
    lateral=np.cross(forward,[0.,0.,1.])
    if np.linalg.norm(lateral)<1e-12:
        lateral=np.cross(forward,[0.,1.,0.])
    lateral/=np.linalg.norm(lateral)
    parts=[("body",np.zeros(3),body_radius_m)]
    for fraction in (-1.,-.5,.5,1.):
        parts.append((f"wing_{fraction:+.1f}",
                      lateral*(.5*wingspan_m*fraction),wing_radius_m))
    contacts=[]
    for pane in panes:
        for label,offset,radius in parts:
            ans=first_sphere_contact(a+offset,b+offset,pane,radius)
            if ans is not None:
                t,dist=ans
                contacts.append(SweptContact(pane.id,pane.material,label,t,dist))
    return min(contacts,key=lambda c:(c.t,c.pane_id,c.body_part)) if contacts else None
