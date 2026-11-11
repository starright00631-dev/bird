"""Bird-facing optics and pre-impact mechanics kernels (NOT calibrated behavior).

External scene radiance, measured glass spectra, measured species cone
sensitivity and acuity must be supplied. No function turns contrast directly
into a species-agnostic collision probability.
"""
from math import atan, cos, degrees, isfinite, radians, sin, sqrt
import numpy as np

def fresnel_unpolarized(n_incident:float,n_transmitted:float,incidence_deg:float)->float:
    """Ideal uncoated lossless single dielectric interface, not double glazing."""
    if not all(map(isfinite,(n_incident,n_transmitted,incidence_deg))) or n_incident<=0 or n_transmitted<=0 or not 0<=incidence_deg<=90:
        raise ValueError("invalid refractive indices or angle")
    theta=radians(incidence_deg)
    sin_t=n_incident*sin(theta)/n_transmitted
    if sin_t>=1.:return 1.
    cos_i,cos_t=cos(theta),sqrt(max(0.,1.-sin_t**2))
    rs=((n_incident*cos_i-n_transmitted*cos_t)/(n_incident*cos_i+n_transmitted*cos_t))**2
    rp=((n_incident*cos_t-n_transmitted*cos_i)/(n_incident*cos_t+n_transmitted*cos_i))**2
    return .5*(rs+rp)

def perceived_spectrum(reflected_scene_radiance,transmitted_scene_radiance,
                       external_reflectance,external_transmittance):
    """Spectral R*L_reflected+T*L_transmitted; ray directions are external inputs.

    R and T must be measured for incidence angle and material conditions.
    Ignores fluorescence, multiple scattering and strongly polarized glare.
    """
    a,b,r,t=map(lambda x:np.asarray(x,float),
                (reflected_scene_radiance,transmitted_scene_radiance,
                 external_reflectance,external_transmittance))
    if any(v.ndim!=1 for v in (a,b,r,t)) or min(map(len,(a,b,r,t)))<2 or len(set(map(len,(a,b,r,t))))!=1:
        raise ValueError("matching 1D spectral arrays required")
    if any(not np.isfinite(v).all() or np.any(v<0) for v in (a,b,r,t)) or np.any(r>1) or np.any(t>1) or np.any(r+t>1+1e-10):
        raise ValueError("invalid passive material or radiance")
    return r*a+t*b

def relative_cone_catches(wavelengths_nm,observed_spectral_radiance,sensitivities):
    """Relative photon catches using measured bird-specific sensitivity arrays.

    Radiance must be energy per unit wavelength. Multiplication by wavelength
    converts to relative photon weighting; the common 1/(hc) factor is omitted.
    Sensitivities must include measured ocular media and cone oil droplet effects.
    """
    wl=np.asarray(wavelengths_nm,float)
    radiance=np.asarray(observed_spectral_radiance,float)
    cones=np.asarray(sensitivities,float)
    if wl.ndim!=1 or len(wl)<3 or radiance.shape!=wl.shape or cones.ndim!=2 or cones.shape[0]!=len(wl) or cones.shape[1]<2:
        raise ValueError("spectral or receptor shapes mismatch")
    if any(not np.isfinite(a).all() or np.any(a<0) for a in (wl,radiance,cones)) or np.any(wl<=0) or np.any(np.diff(wl)<=0):
        raise ValueError("positive sorted wavelengths and nonnegative spectra required")
    return np.trapezoid(radiance[:,None]*cones*wl[:,None],wl,axis=0)

def chromatic_noise_scaled_distance(catch_background,catch_marker,receptor_noise_sd):
    """Achromatic-invariant log-cone difference. NOT calibrated JND or avoidance."""
    bg,mark,noise=map(lambda x:np.asarray(x,float),
                      (catch_background,catch_marker,receptor_noise_sd))
    if bg.ndim!=1 or len(bg)<2 or mark.shape!=bg.shape or noise.shape!=bg.shape:
        raise ValueError("incompatible receptor inputs")
    if any(not np.isfinite(a).all() or np.any(a<=0) for a in (bg,mark,noise)):
        raise ValueError("positive measured catches/noise required")
    delta=np.log(mark/bg)
    precision=1/noise**2
    centered=delta-np.dot(delta,precision)/sum(precision)
    return float(np.sqrt(np.dot(centered**2,precision)))

def pattern_frequency_cycles_per_degree(spacing_m,distance_m):
    """Periodicity of a marker array from bird position; not a detection model."""
    if not all(map(isfinite,(spacing_m,distance_m))) or spacing_m<=0 or distance_m<=0:
        raise ValueError("positive finite pattern dimensions required")
    return 1/degrees(2*atan(spacing_m/(2*distance_m)))

def acuity_necessary_condition(spacing_m,distance_m,species_acuity_cpd):
    """Necessary periodic spatial-resolution check, not sufficient for detection."""
    if not isfinite(species_acuity_cpd) or species_acuity_cpd<=0:
        raise ValueError("measured acuity required")
    return pattern_frequency_cycles_per_degree(spacing_m,distance_m)<=species_acuity_cpd

def normal_kinetic_energy_j(mass_kg,velocity_mps,pane_normal=(1,0,0)):
    """Normal translational pre-impact energy; NOT injury or fatality probability."""
    v=np.asarray(velocity_mps,float);n=np.asarray(pane_normal,float)
    if not isfinite(mass_kg) or mass_kg<=0 or v.shape!=(3,) or n.shape!=(3,) or not np.isfinite(v).all() or not np.isfinite(n).all():
        raise ValueError("finite mass and vectors required")
    norm=float(np.linalg.norm(n))
    if norm<1e-12:raise ValueError("pane normal cannot be zero")
    normal_speed=float(v@(n/norm))
    return .5*mass_kg*normal_speed**2
