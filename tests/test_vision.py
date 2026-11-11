import numpy as np
import pytest
from birdglass.vision import (
  fresnel_unpolarized,perceived_spectrum,relative_cone_catches,
  chromatic_noise_scaled_distance,pattern_frequency_cycles_per_degree,
  acuity_necessary_condition,normal_kinetic_energy_j)

def test_fresnel_normal_4_percent():
    assert fresnel_unpolarized(1,1.5,0)==pytest.approx(.04,abs=1e-12)

def test_fresnel_grazing_and_tir():
    assert fresnel_unpolarized(1,1.5,90)==pytest.approx(1,abs=1e-12)
    assert fresnel_unpolarized(1.5,1,60)==pytest.approx(1,abs=1e-12)

def test_fresnel_reciprocal_normal():
    assert fresnel_unpolarized(1,1.5,0)==pytest.approx(fresnel_unpolarized(1.5,1,0))

def test_reflectance_transmittance_energy_balance():
    got=perceived_spectrum([1,2,3],[1,2,3],[.2,.4,.6],[.8,.6,.4])
    np.testing.assert_allclose(got,[1,2,3])

def test_reflection_and_black_interior():
    got=perceived_spectrum([10,20],[0,0],[.2,.2],[.3,.3])
    np.testing.assert_allclose(got,[2,4])

def test_invalid_passive_spectra_refused():
    with pytest.raises(ValueError):
        perceived_spectrum([1,1],[1,1],[.8,.8],[.3,.3])

def test_bird_specific_photon_catches():
    wl=[350,450,550,650]
    sensitivity=np.column_stack([np.ones(4),[1,0,0,0]])
    q=relative_cone_catches(wl,[1,1,1,1],sensitivity)
    assert q[0]>q[1]>0

def test_chromatic_proxy_ignores_global_brightness():
    bg=[1,3,2,4]
    assert chromatic_noise_scaled_distance(bg,[2,6,4,8],[.1]*4)<1e-12
    assert chromatic_noise_scaled_distance(bg,[2,3,2,4],[.1]*4)>0

def test_farther_spacing_harder_to_resolve():
    assert pattern_frequency_cycles_per_degree(.1,20)>pattern_frequency_cycles_per_degree(.1,2)
    assert acuity_necessary_condition(.1,2,2)
    assert not acuity_necessary_condition(.1,20,2)

def test_normal_kinetic_energy_quadratic_reduction():
    e1=normal_kinetic_energy_j(.04,[8,0,0])
    e2=normal_kinetic_energy_j(.04,[6,0,0])
    assert e2/e1==pytest.approx(.75**2)
    assert normal_kinetic_energy_j(.04,[0,8,0])==pytest.approx(0)

def test_bad_data_rejected():
    with pytest.raises(ValueError):normal_kinetic_energy_j(0,[1,0,0])
    with pytest.raises(ValueError):relative_cone_catches([400,350,500],[1,1,1],np.ones((3,3)))
