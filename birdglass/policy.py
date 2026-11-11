"""Joint-facade, paired-noise counterfactual experiment.

Every policy is re-run across all surfaces and the same starts and random
draws. Benefits on individual glass panes cannot be added: redirected
approaches may hit other panes or opaque structures. This evaluates an
assumption-conditional mechanism, not causal treatment efficacy in the field.
"""
from dataclasses import dataclass
import numpy as np
from .control import replay

@dataclass(frozen=True)
class Scenario:
    name:str
    latency:float
    gain:float
    max_lateral_accel:float
    detection_range:float
    baseline_recognition:dict
    # These are assumptions, not fitted parameters.

def assess(panes,flights,scenarios,policy_delta,seed=17,dt=.025):
    """flights are (start, velocity, destination, body_radius, span, weight)."""
    if not flights or not scenarios:raise ValueError("need trials and scenarios")
    glass={x.id for x in panes if x.material=="glass"}
    if not set(policy_delta).issubset(glass):raise ValueError("only glass panes can be marked")
    if any(not np.isfinite(v) or not 0<=v<=1 for v in policy_delta.values()):
        raise ValueError("invalid hypothetical cue effect")
    rng=np.random.default_rng(seed)
    drawings=[{k:float(rng.random()) for k in glass} for _ in flights]
    result=[]
    for h in scenarios:
        per_policy=[]
        for delta in ({},policy_delta):
            probs={k:min(1.,h.baseline_recognition.get(k,0.)+delta.get(k,0.))
                   for k in glass}
            outcomes=[]
            for flight,draw in zip(flights,drawings):
                start,velocity,dest,body,span,weight=flight
                if weight<=0:raise ValueError("weights must be positive")
                val=replay(start,velocity,dest,panes,probs,draw,
                           body_radius=body,wingspan=span,latency=h.latency,
                           gain=h.gain,max_lateral_accel=h.max_lateral_accel,
                           detection_range=h.detection_range,dt=dt)
                outcomes.append((val["outcome"],val["pane"],float(weight)))
            per_policy.append(outcomes)
        base,changed=per_policy
        denom=sum(row[2] for row in base)
        def rate(rows,kind):
            return sum(w for outcome,_,w in rows if outcome==kind)/denom
        gb,ga=rate(base,"glass"),rate(changed,"glass")
        wb,wa=rate(base,"opaque"),rate(changed,"opaque")
        result.append({"scenario":h.name,"glass_before":gb,"glass_after":ga,
             "opaque_before":wb,"opaque_after":wa,
             "total_contact_reduction":(gb+wb)-(ga+wa),
             "pane_transfer":{pane:sum(w for o,p,w in changed if o=="glass" and p==pane)/denom
                               -sum(w for o,p,w in base if o=="glass" and p==pane)/denom
                               for pane in glass},
             "verified_field_effect":False})
    return result

def abstention_gate(rows):
    if not rows:raise ValueError("no result")
    gains=[x["total_contact_reduction"] for x in rows]
    return {"min_total_contact_reduction":min(gains),
            "max_total_contact_reduction":max(gains),
            "robust_under_tested_hypotheses":min(gains)>0,
            "authorized_for_deployment":False,
            "reason":"recognition, traffic and control are not independently field validated"}
