"""Mechanistic bird–facade collision research. Simulation only, not site-calibrated."""
from .contact import RectPane, SweptContact, first_contact, segment_rect_distance
from .risk import observed_mean, split_observation, paired_policy_delta

from .decision import ApproachSample, FacadeContext, evaluate_facade
from .evidence import EvidenceTier, Measurement
from .glazing import (
    GlassAppearance,
    GlassPanel,
    MarkerContrast,
    MarkerSurface,
    PatternSpec,
    PatternStatus,
)
from .vegetation import VegetationProfile
from .solar import solar_position_enu, specular_reflection_alignment
