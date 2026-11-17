"""Mechanistic bird–facade collision research. Simulation only, not site-calibrated."""
from .contact import RectPane, SweptContact, first_contact, segment_rect_distance
from .risk import observed_mean, split_observation, paired_policy_delta

# Evidence-aware facade decision support (research prototype)
from .evidence import EvidenceTier, Measurement
from .glazing import GlassAppearance, GlassPanel, MarkerSurface, PatternSpec
from .vegetation import VegetationProfile
from .decision import ApproachSample, FacadeContext, evaluate_facade
