"""Reader for the exact *published* wide stereo trajectory CSV schema.

Tawhid et al., Data in Brief (2026), doi:10.1016/j.dib.2026.112956.
The published merged files contain Frame plus per-recording B1..B6 features:
Box_{X,Y,Z} and Head/Tail/LeftWing/RightWing_{X,Y,Z} in millimetres,
where Box_W/H are in **pixels** and never serve as morphological dimensions.

B1 in two files does not imply the same biological bird. The adapter
explicitly marks this identity ambiguity and cannot certify unseen-bird
validation or actual bird-glass contact on its own.
"""
from dataclasses import dataclass
import csv
import io
import math
import re
import numpy as np

_PARTS = {"box_center":"Box", "head":"Head", "tail":"Tail",
          "left_wingtip":"LeftWing", "right_wingtip":"RightWing"}
_KEYPOINT_COLS = {name:tuple(f"{name}_{axis}" for axis in ("x","y","z"))
                   for name in _PARTS}
_PREFIX_RE = re.compile(r"^(B[1-6])_Head_X$")


@dataclass(frozen=True)
class StereoIngest:
    recording_id: str
    observations: tuple
    bird_labels: tuple
    keypoint_columns: dict
    units: str = "mm"
    frames_per_second: int = 120
    identity_certified: bool = False
    source_domain: str = "controlled_aviary_multi_bird_flight"


def read_stereo_csv(text, recording_id):
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("CSV header missing or duplicated")
    return normalize_wide_rows(reader, recording_id, headers=reader.fieldnames)


def normalize_wide_rows(rows, recording_id, headers=None):
    """Convert exact wide merged stereo records into per-bird long pose rows.

    No coordinate imputation; NaN values remain missing. All 3D positions
    keep original mm units for the existing calibrated pose contact adapter.
    """
    if not isinstance(recording_id,str) or not recording_id.strip() or "/" in recording_id:
        raise ValueError("Give a stable recording identifier, not a path")
    rows = list(rows)
    if not rows:
        raise ValueError("Empty flight data")
    names = set(headers if headers is not None else rows[0].keys())
    if "Frame" not in names:
        raise ValueError("Source Frame index missing")
    birds = sorted({_PREFIX_RE.fullmatch(name).group(1)
                    for name in names if _PREFIX_RE.fullmatch(name)})
    if not birds:
        raise ValueError("No published B1..B6 head columns found")
    expected = {f"{b}_{part}_{axis}"
                for b in birds for part in _PARTS.values()
                for axis in ("X","Y","Z")}
    missing=expected-names
    if missing:
        raise ValueError(f"Missing 3D coordinate columns: {sorted(missing)[:6]}")
    frames=set()
    output=[]
    for row in rows:
        try:
            t=float(row["Frame"])
        except (TypeError,ValueError,KeyError):
            raise ValueError("Invalid Frame value") from None
        if not math.isfinite(t) or int(t)!=t or t<0 or int(t) in frames:
            raise ValueError("Noninteger, nonfinite or repeated source Frame")
        frames.add(int(t))
        for bird in birds:
            item={
                "individual_id":f"UNVERIFIED::{recording_id}::{bird}",
                "trial_id":recording_id,
                "frame":int(t),
                "source_bird_label":bird,
                "source_recording_id":recording_id,
                "individual_identity_certified":False,
            }
            for alias,prefix in _PARTS.items():
                for axis in ("X","Y","Z"):
                    raw=row.get(f"{bird}_{prefix}_{axis}")
                    if raw is None or str(raw).strip()=="":
                        value=float("nan")
                    else:
                        try:
                            value=float(raw)
                        except (ValueError,TypeError):
                            raise ValueError("Non-numeric published 3D coordinate") from None
                        if math.isinf(value):
                            raise ValueError("Infinite 3D position")
                    item[f"{alias}_{axis.lower()}"]=value
            output.append(item)
    return StereoIngest(recording_id,tuple(output),tuple(birds),
                        dict(_KEYPOINT_COLS))


def require_independent_bird_identity(imported):
    """Reject statistically invalid independent-individual holdout claims."""
    if not imported.identity_certified:
        raise ValueError("Only within-video B-labels are known; independent biological identities unverified")


def motion_summary(imported, part="box_center"):
    """Velocity/acceleration from contiguous 120-Hz metric 3D observations.

    Raw finite differences amplify stereo measurement noise: this is a
    diagnostic summary, NOT a calibrated bird flight or injury parameter.
    """
    if part not in _PARTS:
        raise ValueError("Unknown landmark")
    by_bird = {label:[] for label in imported.bird_labels}
    for row in imported.observations:
        xyz=np.array([row[f"{part}_{axis}"] for axis in ("x","y","z")],dtype=float)*.001
        by_bird[row["source_bird_label"]].append((row["frame"],xyz))
    result={}
    for bird,sequence in by_bird.items():
        sequence.sort(key=lambda p:p[0])
        speed=[]
        accel=[]
        frame_s=1/imported.frames_per_second
        for i in range(1,len(sequence)):
            f0,p0=sequence[i-1]
            f1,p1=sequence[i]
            if f1!=f0+1 or not np.isfinite([*p0,*p1]).all():
                continue
            speed.append(float(np.linalg.norm(p1-p0)/frame_s))
        for i in range(1,len(sequence)-1):
            f0,p0=sequence[i-1]
            f1,p1=sequence[i]
            f2,p2=sequence[i+1]
            if f1!=f0+1 or f2!=f1+1 or not np.isfinite([*p0,*p1,*p2]).all():
                continue
            accel.append(float(np.linalg.norm(p2-2*p1+p0)/frame_s**2))
        result[bird]={
            "contiguous_velocity_intervals":len(speed),
            "contiguous_acceleration_triplets":len(accel),
            "median_speed_mps":float(np.median(speed)) if speed else None,
            "median_finite_difference_accel_mps2":float(np.median(accel)) if accel else None,
            "source_identity_certified":False,
        }
    return result
