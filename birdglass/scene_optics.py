"""Finite-facade bird-view geometric optics, with no invented behavior rates.

Coordinates: metres in one world reference frame. A RectPatch is a planar
rectangle with full-edge vectors u and v. Specular reflection uses the virtual
image of a *scene source*, whereas transmission sees a source on the opposite
side of the pane. Geometry says whether a ray is possible, never whether a
particular bird chooses to follow it or recognises the glass.

Primary optical context: Hastad & Odeen, PeerJ 2:e621 (2014),
doi:10.7717/peerj.621. Their spectral observations are distinct from the
unmeasured radiance, coating, retinal physiology and behavioral response
at any particular study site.
"""
from dataclasses import dataclass
from math import acos, atan2, degrees, isfinite, sqrt
from typing import Iterable
import numpy as np
from .vision import perceived_spectrum, relative_cone_catches


def _v3(value):
    v = np.asarray(value, dtype=float)
    if v.shape != (3,) or not np.isfinite(v).all():
        raise ValueError("Expected a finite 3D metric vector")
    return v


def _unit(value):
    v = _v3(value)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError("Direction cannot be zero")
    return v / n


def _angle(a, b):
    return degrees(acos(float(np.clip(_unit(a) @ _unit(b), -1, 1))))


@dataclass(frozen=True)
class RectPatch:
    id: str
    center_m: tuple
    u_full_m: tuple
    v_full_m: tuple
    material: str = "glass"

    def __post_init__(self):
        u, v, c = _v3(self.u_full_m), _v3(self.v_full_m), _v3(self.center_m)
        if min(np.linalg.norm(u), np.linalg.norm(v)) <= 1e-8:
            raise ValueError("Patch edges must have nonzero length")
        if abs(float(u @ v)) / (np.linalg.norm(u)*np.linalg.norm(v)) > 1e-7:
            raise ValueError("Patch basis edges must be perpendicular")
        if self.material not in {"glass", "opaque"} or not self.id:
            raise ValueError("Unsupported surface material or empty id")

    @classmethod
    def from_axis_pane(cls, pane):
        return cls(
            pane.id,
            (pane.x, .5*(pane.ymin+pane.ymax), .5*(pane.zmin+pane.zmax)),
            (0., pane.ymax-pane.ymin, 0.),
            (0., 0., pane.zmax-pane.zmin),
            pane.material,
        )

    @property
    def normal(self):
        return _unit(np.cross(_v3(self.u_full_m), _v3(self.v_full_m)))

    @property
    def corners(self):
        c, u, v = _v3(self.center_m), _v3(self.u_full_m)/2, _v3(self.v_full_m)/2
        return (c-u-v, c+u-v, c+u+v, c-u+v)

    def contains(self, point, epsilon=1e-9):
        p = _v3(point)-_v3(self.center_m)
        u, v = _v3(self.u_full_m), _v3(self.v_full_m)
        return (abs(float(p @ self.normal)) <= epsilon
                and abs(float(p @ u)/float(u @ u)) <= .5+epsilon
                and abs(float(p @ v)/float(v @ v)) <= .5+epsilon)


@dataclass(frozen=True)
class SceneRay:
    kind: str
    pane_id: str
    surface_point_m: tuple
    apparent_target_m: tuple
    incidence_angle_deg: float
    gaze_to_heading_deg: float
    source_angular_diameter_deg: float


def _intersect_segment(viewer, target, patch):
    eye, aim = _v3(viewer), _v3(target)
    normal = patch.normal
    d = aim-eye
    divisor = float(d @ normal)
    if abs(divisor) <= 1e-12:
        return None
    t = float((_v3(patch.center_m)-eye) @ normal / divisor)
    if not (1e-12 < t < 1-1e-12):
        return None
    hit = eye + t*d
    return hit if patch.contains(hit) else None


def _is_opaque_occluded(viewer, hit, blocker_patches):
    """Unknown secondary glass optical effects are not treated as opaque."""
    for surface in blocker_patches:
        if surface.material != "opaque":
            continue
        # Extend just past hit so that a blocker at precisely the target
        # is excluded by the end-boundary convention.
        hit_before = _v3(viewer) + (hit-_v3(viewer))*(1-1e-7)
        if _intersect_segment(viewer, hit_before, surface) is not None:
            return True
    return False


def scene_ray(viewer_m, heading_mps, scene_center_m, patch: RectPatch,
              kind, scene_radius_m=0., blockers: Iterable[RectPatch]=()):
    """Physical existence of one reflection/transmission path to a pane.

    Reflecting scene and viewer must share a side. Transmitted scene and
    viewer must occupy opposite sides. Sources are represented by spheres
    for angular size, not by a complete geometry or measured BRDF.
    """
    if kind not in ("reflection", "transmission"):
        raise ValueError("kind must be reflection or transmission")
    if not isfinite(scene_radius_m) or scene_radius_m < 0:
        raise ValueError("Scene radius must be finite and nonnegative")
    eye, scene, heading = _v3(viewer_m), _v3(scene_center_m), _unit(heading_mps)
    if patch.material != "glass":
        return None
    c, n = _v3(patch.center_m), patch.normal
    eye_side, scene_side = float((eye-c) @ n), float((scene-c) @ n)
    if abs(eye_side)<1e-8 or abs(scene_side)<1e-8:
        return None
    if kind == "reflection":
        if eye_side*scene_side <= 0:
            return None
        apparent = scene - 2*scene_side*n
    else:
        if eye_side*scene_side >= 0:
            return None
        apparent = scene.copy()
    hit = _intersect_segment(eye, apparent, patch)
    if hit is None or _is_opaque_occluded(eye, hit, blockers):
        return None
    sight = _unit(apparent-eye)
    incidence = degrees(acos(float(np.clip(abs(sight @ n), 0., 1.))))
    diameter = degrees(2*atan2(scene_radius_m, np.linalg.norm(apparent-eye)))
    return SceneRay(kind, patch.id, tuple(hit), tuple(apparent),
                    incidence, _angle(sight, heading), diameter)


def minimum_heading_angle_deg(viewer_m, heading_mps, patch: RectPatch):
    """Minimum angular separation between heading and ANY point on a patch.

    Unlike a centre-point visibility test this respects very wide curtain
    walls. Evaluate the four edge interiors and endpoints analytically.
    """
    eye, head = _v3(viewer_m), _unit(heading_mps)
    n, center = patch.normal, _v3(patch.center_m)
    denom = float(head @ n)
    if abs(denom) > 1e-12:
        t = float((center-eye) @ n / denom)
        if t > 0 and patch.contains(eye+t*head):
            return 0.
    corners=patch.corners
    candidates=[]
    for i in range(4):
        a, b = corners[i]-eye, corners[(i+1)%4]-eye
        d=b-a
        # derivative d/ds[(head dot (a+s*d))/|a+s*d|] = 0
        p=float((head @ d)*(a @ a)-(head @ a)*(a @ d))
        q=float((head @ d)*(a @ d)-(head @ a)*(d @ d))
        values=[a,b]
        if abs(q)>1e-14:
            s=max(0.,min(1.,-p/q))
            values.append(a+s*d)
        for vector in values:
            if np.linalg.norm(vector)>1e-10:
                candidates.append(_angle(head,vector))
    if not candidates:
        raise ValueError("Viewer coincides with degenerate surface")
    return min(candidates)


def pane_solid_angle_sr(viewer_m, patch: RectPatch):
    """Exact unsigned solid angle subtended by a rectangle in steradians."""
    eye=_v3(viewer_m)
    n=patch.normal
    if abs(float((eye-_v3(patch.center_m)) @ n))<1e-9:
        raise ValueError("Viewer must not be in the pane plane")
    vecs=[corner-eye for corner in patch.corners]
    def triangle(a,b,c):
        la,lb,lc=np.linalg.norm(a),np.linalg.norm(b),np.linalg.norm(c)
        numerator=abs(float(a @ np.cross(b,c)))
        denominator=la*lb*lc + (a@b)*lc + (b@c)*la + (c@a)*lb
        return 2*atan2(numerator, denominator)
    return float(triangle(vecs[0],vecs[1],vecs[2])
                 + triangle(vecs[0],vecs[2],vecs[3]))


def measured_pixel_cone_catches(reflected:SceneRay, transmitted:SceneRay,
                                reflected_radiance, transmitted_radiance,
                                measured_reflectance, measured_transmittance,
                                wavelengths_nm, species_sensitivities,
                                point_tolerance_m=.01):
    """Combine geometrically co-located optical paths and measured spectra.

    The caller must supply *measured, direction-matched* radiances and
    whole-glazing reflectance/transmittance. This cannot estimate behavior.
    """
    if reflected.kind!="reflection" or transmitted.kind!="transmission":
        raise ValueError("Expected reflection and transmission rays")
    if reflected.pane_id!=transmitted.pane_id or np.linalg.norm(
            _v3(reflected.surface_point_m)-_v3(transmitted.surface_point_m)
            )>point_tolerance_m:
        raise ValueError("Rays must sample the same pane pixel")
    spectrum=perceived_spectrum(reflected_radiance,transmitted_radiance,
                                measured_reflectance,measured_transmittance)
    return relative_cone_catches(wavelengths_nm,spectrum,species_sensitivities)


def scene_path_table(viewpoints, scenes, patches, kinds=("reflection","transmission")):
    """Inspectable geometry-only rays; not collision probabilities.

    viewpoints: (id, position_xyz, heading_xyz)
    scenes: (id, scene_center_xyz, representative_radius_m)
    """
    result=[]
    for viewer_id,eye,heading in viewpoints:
        for source_id,where,radius in scenes:
            for pane in patches:
                for kind in kinds:
                    ray=scene_ray(eye,heading,where,pane,kind,radius,patches)
                    if ray is None:continue
                    result.append({"viewer_id":viewer_id,"scene_id":source_id,
                         "pane_id":pane.id,"kind":kind,
                         "surface_point_m":ray.surface_point_m,
                         "incidence_angle_deg":ray.incidence_angle_deg,
                         "gaze_to_heading_deg":ray.gaze_to_heading_deg,
                         "angular_diameter_deg":ray.source_angular_diameter_deg,
                         "calibrated_recognition":None})
    return result
