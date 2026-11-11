"""Group-held-out estimation for a delay-controlled bird steering model.

OBSERVATIONAL INPUT REQUIREMENT:
- calibrated independent individual/trial/frame identifiers,
- bird heading angles and independently reconstructed candidate gap aims
  in the same world/camera coordinate frame and units.
- gap aims must NOT be inferred from the held-out future bird path.

Outputs assess predictive angular velocity on held-out INDIVIDUALS,
not randomly split frames. No real field data is bundled or fitted.
"""
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite, pi
import numpy as np

NEEDED = ("individual_id", "trial_id", "frame",
          "heading_yaw_rad", "external_gap_yaw_rad")

def wrap(angle):
    return (np.asarray(angle, dtype=float) + pi) % (2*pi) - pi

@dataclass(frozen=True)
class Track:
    individual_id: str
    trial_id: str
    frames: np.ndarray
    headings: np.ndarray
    gaps: np.ndarray


def parse_tracks(records):
    """Strict schema: no pixel velocities, inferred gap aims, or fake splits."""
    if hasattr(records, "to_dict"):
        records=records.to_dict("records")
    items=list(records)
    if not items:
        raise ValueError("No records supplied")
    if not all(all(k in r for k in NEEDED) for r in items):
        raise ValueError("Requires individual, trial, frame, heading AND independently annotated gap aim")
    groups=defaultdict(list)
    for r in items:
        individual,trial=str(r["individual_id"]),str(r["trial_id"])
        if not individual or not trial or individual=="None" or trial=="None":
            raise ValueError("Missing identifying group")
        value=[r["frame"],r["heading_yaw_rad"],r["external_gap_yaw_rad"]]
        try: numeric=np.asarray(value,float)
        except (ValueError,TypeError):raise ValueError("Non numeric frame/angle") from None
        if not np.isfinite(numeric).all() or numeric[0]<0 or numeric[0]!=int(numeric[0]):
            raise ValueError("Finite integer frame and angles required")
        groups[(individual,trial)].append(numeric)
    tracks=[]
    for (individual,trial),rows in groups.items():
        data=np.asarray(sorted(rows,key=lambda x:x[0]))
        f=data[:,0].astype(int)
        if len(np.unique(f))!=len(f):
            raise ValueError("Duplicate frames inside a trial")
        if len(data)<10:
            continue
        tracks.append(Track(individual,trial,f,
                            wrap(data[:,1]),wrap(data[:,2])))
    return tracks


def frame_rows(tracks, delay_frames, common_burn_in_frames):
    """Return rows with identical evaluation timestamp eligibility for lags.

    Every candidate lag is evaluated only on frames with a contiguous
    (max_lag+2)-frame window, even when the tested lag is zero.
    """
    if delay_frames<0 or common_burn_in_frames<delay_frames:
        raise ValueError("Invalid lag vs evaluation window")
    out=[]
    for tr in tracks:
        f=tr.frames
        for t in range(common_burn_in_frames,len(f)-1):
            frame_window=f[t-common_burn_in_frames:t+2]
            if not np.all(np.diff(frame_window)==1):
                continue
            error=float(wrap(tr.gaps[t-delay_frames]-tr.headings[t-delay_frames]))
            rate=float(wrap(tr.headings[t+1]-tr.headings[t]))
            out.append((tr.individual_id,tr.trial_id,error,rate))
    return out


def _balanced_weights(rows):
    """Equal individual weight, equal trial weight within individual."""
    trials=defaultdict(set)
    counts=defaultdict(int)
    for bird,trial,_,_ in rows:
        trials[bird].add(trial)
        counts[(bird,trial)]+=1
    n_individuals=len(trials)
    return np.array([
        1/(n_individuals*len(trials[bird])*counts[(bird,trial)])
        for bird,trial,_,_ in rows],dtype=float)


def _train_gain(rows,dt_s,ridge=1e-8):
    if len(rows)<15:
        raise ValueError("Insufficient independent frames")
    x=np.array([r[2] for r in rows],dtype=float)
    y=np.array([r[3]/dt_s for r in rows],dtype=float)
    w=_balanced_weights(rows)
    k=max(0.,float(np.dot(w*x,y)/(np.dot(w*x,x)+ridge)))
    loss=float(np.dot(w,(y-k*x)**2))
    return k,loss


def _test_loss(rows,k,dt_s):
    if not rows:
        raise ValueError("No matched held-out frames")
    x=np.array([r[2] for r in rows],dtype=float)
    y=np.array([r[3]/dt_s for r in rows],dtype=float)
    w=_balanced_weights(rows)
    return float(np.dot(w,(y-k*x)**2)),float(np.dot(w,y*y))


def leave_individual_out(records,dt_s=.02,max_lag_frames=8,min_individuals=3):
    """Select steering gain and lag using training birds only; test new birds.

    A zero-lag fitted control and constant-heading (turn rate zero) are
    evaluated on exactly the same held-out timestamps.
    """
    if not isfinite(dt_s) or dt_s<=0 or not isinstance(max_lag_frames,int) or max_lag_frames<0:
        raise ValueError("Invalid time sampling")
    tracks=parse_tracks(records)
    individuals=sorted({x.individual_id for x in tracks})
    if len(individuals)<min_individuals:
        raise ValueError("Need independent individuals for held-out validation")
    result=[]
    for test_id in individuals:
        train=[x for x in tracks if x.individual_id!=test_id]
        test=[x for x in tracks if x.individual_id==test_id]
        candidates=[]
        for lag in range(max_lag_frames+1):
            rows=frame_rows(train,lag,max_lag_frames)
            if len(rows)<15:continue
            gain,mse=_train_gain(rows,dt_s)
            candidates.append((mse,lag,gain))
        if not candidates:
            raise ValueError("Insufficient training rows after independent split")
        _,lag,gain=min(candidates,key=lambda x:(x[0],x[1]))
        matched=frame_rows(test,lag,max_lag_frames)
        if len(matched)<10:
            raise ValueError("Insufficient unseen-bird frames")
        loss,ballistic=_test_loss(matched,gain,dt_s)
        no_delay_train=frame_rows(train,0,max_lag_frames)
        k0,_=_train_gain(no_delay_train,dt_s)
        zero_delay_test=frame_rows(test,0,max_lag_frames)
        zero_lag_loss,_=_test_loss(zero_delay_test,k0,dt_s)
        # Same held-out timestamp support across all lag choices, by construction.
        result.append({
            "heldout_individual":test_id,
            "n_heldout_trials":len(test),
            "n_matched_frames":len(matched),
            "train_delay_s":lag*dt_s,
            "train_gain_per_s":gain,
            "heldout_mse_rad2_s2":loss,
            "zero_delay_mse_rad2_s2":zero_lag_loss,
            "straight_flight_mse_rad2_s2":ballistic,
            "split_rule":"independent_individual",
            "calibration_status":"UNVALIDATED_WITHOUT_REAL_TRACKS",
        })
    return result
