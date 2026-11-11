import math
import numpy as np
import pytest
from birdglass.behavior_fit import (
    parse_tracks,frame_rows,leave_individual_out,wrap
)

def synthetic_trials(individuals=4,trials_per_bird=2,frames=150,dt=.04,delay=3,k=3.6):
    """Fictitious known-controller generator for algebraic recovery only."""
    rng=np.random.default_rng(82)
    rows=[]
    for individual in range(individuals):
        for trial in range(trials_per_bird):
            phase=float(rng.uniform(-1,1))
            steps=np.arange(frames)
            gap=.5*np.sin(steps/19.+phase)+.3*np.sin(steps/6.+.3*individual)
            angle=np.zeros(frames)
            for t in range(frames-1):
                j=max(0,t-delay)
                angle[t+1]=float(wrap(angle[t]+dt*k*
                                      wrap(gap[j]-angle[j])))
            for t in range(frames):
                rows.append({
                    "individual_id":f"bird{individual}",
                    "trial_id":f"flight{trial}",
                    "frame":t,
                    "heading_yaw_rad":angle[t],
                    "external_gap_yaw_rad":gap[t]})
    return rows

def test_individual_heldout_recovers_known_synthetic_delay_and_gain():
    data=synthetic_trials()
    fit=leave_individual_out(data,dt_s=.04,max_lag_frames=6)
    assert len(fit)==4
    for row in fit:
        assert row["train_delay_s"]==pytest.approx(.12)
        assert row["train_gain_per_s"]==pytest.approx(3.6,rel=1e-4)
        assert row["heldout_mse_rad2_s2"]<1e-8
        assert row["heldout_mse_rad2_s2"]<row["zero_delay_mse_rad2_s2"]
        assert row["split_rule"]=="independent_individual"

def test_trial_of_same_bird_never_tested_with_its_training_trial():
    data=synthetic_trials(individuals=3,trials_per_bird=3)
    out=leave_individual_out(data,dt_s=.04,max_lag_frames=5)
    assert len(out)==3
    assert {x["n_heldout_trials"] for x in out}=={3}

def test_compared_lags_have_same_frame_support_after_data_gap():
    data=synthetic_trials(individuals=3,trials_per_bird=1,frames=50)
    data=[x for x in data if not (x["individual_id"]=="bird0"
                                  and x["frame"]==22)]
    tracks=parse_tracks(data)
    lengths=[len(frame_rows(tracks,lag,5)) for lag in range(6)]
    assert len(set(lengths))==1
    assert lengths[0]>0

def test_frame_duplicates_rejected():
    data=synthetic_trials(individuals=3,trials_per_bird=1,frames=20)
    with pytest.raises(ValueError,match="Duplicate"):
        parse_tracks(data+[data[0]])

def test_no_future_gap_aim_or_individual_id_is_silently_invented():
    data=synthetic_trials(individuals=3,trials_per_bird=1,frames=20)
    bad=[dict(x) for x in data]
    del bad[0]["external_gap_yaw_rad"]
    with pytest.raises(ValueError):
        leave_individual_out(bad)

def test_insufficient_independent_animals_rejected():
    data=synthetic_trials(individuals=2)
    with pytest.raises(ValueError,match="independent individuals"):
        leave_individual_out(data)
