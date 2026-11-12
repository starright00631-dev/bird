"""Recompute real external 3D-POP source integrity audit without network."""
import json
from pathlib import Path
from birdglass.source_splits import (
    read_3dpop_metadata, audit_metadata, component_fold_assignment,
)

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data/external/3dpop_public_metadata.csv"

def build_report():
    rows=read_3dpop_metadata(SOURCE.read_text(encoding="utf-8"))
    report=audit_metadata(rows)
    assignment=component_fold_assignment(rows,n_folds=5)
    report["fold_trial_counts"]={
       str(i):sum(1 for v in assignment.values() if v==i)
       for i in sorted(set(assignment.values()))
    }
    report["interpretation"] = (
        "Real trial metadata only; source-safe split, not verified "
        "unseen biological individuals or fitted bird-flight motion"
    )
    return report

if __name__ == "__main__":
    print(json.dumps(build_report(),ensure_ascii=False,sort_keys=True,indent=2))
