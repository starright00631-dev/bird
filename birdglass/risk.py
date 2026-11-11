"""Observation identifiability and paired counterfactual estimands.

The product of traffic, conditional collision and observer discovery is
observable in incident records. Without independently measured components,
those records do not identify a pane's unconditional collision probability.
"""
from math import isfinite
from statistics import mean

def observed_mean(encounter_rate, collision_given_encounter, detection_probability):
    if not (isfinite(encounter_rate) and encounter_rate>=0):
        raise ValueError("encounter rate must be nonnegative")
    for p in (collision_given_encounter,detection_probability):
        if not isfinite(p) or not 0<=p<=1:
            raise ValueError("probabilities must lie in [0,1]")
    return encounter_rate*collision_given_encounter*detection_probability


def split_observation(observed_incidents, encounter_rate=None, discovery=None):
    """Either return an identified conditional collision rate or abstain."""
    if observed_incidents<0:
        raise ValueError("negative observation")
    if encounter_rate is None or discovery is None:
        return {"identified":False,"reason":"Need independent approaches and detection"}
    if encounter_rate<=0 or discovery<=0:
        return {"identified":False,"reason":"No positive denominator"}
    value=observed_incidents/(encounter_rate*discovery)
    if value>1:
        return {"identified":False,"reason":"Incompatible inputs or model"}
    return {"identified":True,"conditional_collision":value}


def paired_policy_delta(baseline_outcomes, treatment_outcomes, weights=None):
    """Paired total-structure contact reduction under identical approach draws.

    This is a simulation contrast unless trajectories and treatment are field
    validated. A glass-to-wall contact is still a contact.
    """
    a,b=list(baseline_outcomes),list(treatment_outcomes)
    if not a or len(a)!=len(b):
        raise ValueError("paired outcomes must be equal nonempty sequences")
    if weights is None: weights=[1.]*len(a)
    if len(weights)!=len(a) or any(x<0 or not isfinite(x) for x in weights):
        raise ValueError("invalid weights")
    valid={"glass","opaque","escaped","passed","diverted","unresolved"}
    if any(x not in valid for x in a+b):
        raise ValueError("unknown outcome")
    pairs=[(w,int(x in ("glass","opaque"))-int(y in ("glass","opaque")))
           for w,x,y in zip(weights,a,b)]
    total=sum(w for w,_ in pairs)
    if total<=0:raise ValueError("zero total weight")
    return sum(w*d for w,d in pairs)/total
