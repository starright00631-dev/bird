"""Source-pinned audit and conservative grouped-validation of selected window videos.

Samuels et al. (2022), PeerJ 10:e14604, Supplement 4:
https://doi.org/10.7717/peerj.14604
The 38 cases were deliberately selected collisions/near misses. Logistic
probabilities here are conditional to this selected collection, never
estimates of P(collision | arbitrary bird approaching a window).
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SOURCE_SHA256 = "0e33f97b007bb5f479ebe45abd76680c2ff36ea92f0280f6ead48e708af6cf35"
FEATURES = ("velocity", "horizangleP", "time_dec")
FEATURE_SETS = {
    "intercept": (),
    "speed_only": ("velocity",),
    "speed_angle": ("velocity", "horizangleP"),
    "speed_angle_time": FEATURES,
}


def read_original_csv(path):
    """Reject modified source bytes and inconsistent event annotations."""
    blob = Path(path).read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"Original PeerJ supplement hash mismatch: {digest}")
    rows = list(csv.DictReader(blob.decode("utf-8-sig").splitlines()))
    if len(rows) != 38 or len({r["event"] for r in rows}) != 38:
        raise ValueError("Unexpected case count or repeated source event")
    if Counter(r["type"] for r in rows) != {"Collision": 29, "Nearmiss": 9}:
        raise ValueError("The 29 collision and 9 near-miss sample definition changed")
    for r in rows:
        if r["collnear"] != ("1" if r["type"] == "Collision" else "0"):
            raise ValueError("Source binary label and type disagree")
        if r["type"] == "Nearmiss" and r["collafter"].strip():
            raise ValueError("Near miss cannot have post-impact severity label")
        datetime.strptime(r["date"], "%m/%d/%Y")
        if r["horizangleP"]:
            derived = abs(float(r["horizangle"]) - 90.)
            if abs(derived - float(r["horizangleP"])) > 1e-8:
                raise ValueError("Source incidence-angle conversion disagrees")
    return rows, digest


def summary_stat(values):
    data = [float(x) for x in values if str(x).strip()]
    return {
        "n": len(data),
        "mean": mean(data) if data else None,
        "sample_sd": stdev(data) if len(data) > 1 else None,
    }


def audit_selected_cases(rows, digest):
    collided = [r for r in rows if r["type"] == "Collision"]
    near = [r for r in rows if r["type"] == "Nearmiss"]
    complete = [r for r in rows if all(r[k].strip() for k in FEATURES)]
    return {
        "doi": "10.7717/peerj.14604",
        "original_csv_sha256": digest,
        "n_selected_video_events": len(rows),
        "n_collision_events": len(collided),
        "n_near_misses": len(near),
        "n_three_feature_complete": len(complete),
        "n_complete_collision": sum(r["type"] == "Collision" for r in complete),
        "n_complete_near_miss": sum(r["type"] == "Nearmiss" for r in complete),
        "missing_by_feature": {
            key: sum(not r[key].strip() for r in rows) for key in FEATURES
        },
        "pooled_speed_mps": summary_stat(r["velocity"] for r in rows),
        "collision_only_speed_mps": summary_stat(r["velocity"] for r in collided),
        "near_miss_only_speed_mps": summary_stat(r["velocity"] for r in near),
        "pooled_angle_offset_deg": summary_stat(r["horizangleP"] for r in rows),
        "immediate_died_or_stunned": sum(r["Outcome"] == "diedstunned"
                                         for r in collided),
        "observed_flying_away": sum(r["Outcome"] == "flew away"
                                    for r in collided),
        "independent_bird_identity_known": False,
        "long_term_survival_known": False,
        "complete_all_approaches_denominator_available": False,
        "published_descriptive_R_script_scope": "entire 38-row table",
        "paper_collisions_n26_wording_reproduced_by_pooled_n36": True,
        "note": "Mean 7.24 m/s and angle 16.53 deg match pooled valid n=36, not collision-only n=28. No inferred correction of original paper.",
    }


def leave_group_out(rows, group_by):
    """Leave one *species label* or calendar year out per fit, fixed L2 C=1.

    Feature scaling and intercept use TRAIN only; no search on held-out labels.
    Species grouping is NOT proof of independent individual identity.
    """
    if group_by not in ("species", "year"):
        raise ValueError("Only species/year group validity checks supported")
    complete = [r for r in rows if all(r[k].strip() for k in FEATURES)]
    y = np.array([int(r["collnear"]) for r in complete], dtype=int)
    X = np.array([[float(r[k]) for k in FEATURES] for r in complete], dtype=float)
    grouping = np.array(
        [r["species"] if group_by == "species"
         else datetime.strptime(r["date"], "%m/%d/%Y").year
         for r in complete]
    )
    if len(np.unique(grouping)) < 2:
        raise ValueError("At least two independent groups required")
    records = {
        "heldout_variable": group_by,
        "n_complete_cases": int(len(y)),
        "n_groups": int(len(np.unique(grouping))),
        "n_collisions": int(y.sum()),
        "n_near_misses": int(len(y) - y.sum()),
        "group_sizes": dict(Counter(str(g) for g in grouping)),
        "models": {},
    }
    for name, selected in FEATURE_SETS.items():
        predictions = np.zeros(len(y), dtype=float)
        for group in np.unique(grouping):
            test_mask = grouping == group
            train_mask = ~test_mask
            yy = y[train_mask]
            # Jeffreys half-count shrinks intercept-only estimates away
            # from exactly 0/1 for very small sampled cohorts.
            intercept = (yy.sum() + .5) / (len(yy) + 1.)
            if not selected or len(np.unique(yy)) < 2:
                predictions[test_mask] = intercept
                continue
            cols = [FEATURES.index(k) for k in selected]
            learner = make_pipeline(
                StandardScaler(),
                LogisticRegression(C=1., solver="lbfgs", max_iter=400),
            )
            learner.fit(X[train_mask][:, cols], yy)
            predictions[test_mask] = learner.predict_proba(
                X[test_mask][:, cols])[:, 1]
        scores = {
            "brier": float(brier_score_loss(y, predictions)),
            "log_loss": float(log_loss(y, predictions, labels=[0, 1])),
            "rank_auc": float(roc_auc_score(y, predictions)),
            "n_predictions": int(len(predictions)),
            "identified_population_probability": False,
        }
        records["models"][name] = scores
    records["full_minus_intercept_brier"] = (
        records["models"]["speed_angle_time"]["brier"]
        - records["models"]["intercept"]["brier"])
    return records


def benchmark(source_path):
    rows, digest = read_original_csv(source_path)
    return {
        "analysis": "predeclared_selected_video_case_falsification",
        "audit": audit_selected_cases(rows, digest),
        "leave_species_out": leave_group_out(rows, "species"),
        "leave_year_out": leave_group_out(rows, "year"),
        "interpretation": [
            "Selected case-series, NOT a calibrated approach-to-window risk model",
            "Only eight complete-feature near misses; grouped tests have high sampling uncertainty",
            "No individual bird identities: species-group validation is not individual-level validation",
            "No paired real glass optical scene, 3D trajectories or true all-bird opportunity denominator",
            "An animal recorded flying away has unknown longer-term survival",
            "Published descriptive values match pooled valid rows and the authors' published R code, not claimed n=26 collision subgroup",
        ],
    }


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--input", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    report = benchmark(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified source SHA256", report["audit"]["original_csv_sha256"])
    print("Real case count:", report["audit"]["n_selected_video_events"])
    for key in ("leave_species_out", "leave_year_out"):
        print(key, "intercept Brier", report[key]["models"]["intercept"]["brier"],
              "full Brier", report[key]["models"]["speed_angle_time"]["brier"])
    print("Research boundary: SELECTED source events only; no population collision risk.")


if __name__ == "__main__":
    main()
