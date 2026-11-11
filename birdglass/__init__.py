"""Mechanistic bird–facade collision research. Simulation only, not site-calibrated."""
from .contact import RectPane, SweptContact, first_contact, segment_rect_distance
from .risk import observed_mean, split_observation, paired_policy_delta
