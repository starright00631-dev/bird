#!/usr/bin/env python3
"""Run the versioned paired-policy synthetic stress benchmark."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from birdglass.contact import RectPane
from birdglass.policy import Scenario, abstention_gate, assess

SNAPSHOT_PATH = "data/reference/synthetic_policy_stress_v1.json"
MODEL_PATHS = (
    "birdglass/contact.py",
    "birdglass/control.py",
    "birdglass/policy.py",
    "birdglass/reachability.py",
    "birdglass/scene_optics.py",
    "birdglass/vision.py",
    "scripts/reproduce_policy_stress.py",
)
OUTPUT_NAME = "policy_stress.json"


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def reproduce(out_dir):
    snapshot_bytes = (PROJECT_ROOT / SNAPSHOT_PATH).read_bytes()
    snapshot = json.loads(snapshot_bytes)
    panes = [RectPane(**row) for row in snapshot["panes"]]
    flights = [
        (row["start"], row["velocity"], row["destination"],
         row["body_radius"], row["wingspan"], row["weight"])
        for row in snapshot["flights"]
    ]
    scenarios = [Scenario(**row) for row in snapshot["scenarios"]]
    runs = []
    for configuration in snapshot["runs"]:
        rows = assess(
            panes, flights, scenarios, snapshot["policy_delta"],
            seed=snapshot["seed"], **configuration,
        )
        runs.append({"configuration": configuration, "scenarios": rows, "gate": abstention_gate(rows)})

    result = json_bytes({
        "snapshot_id": snapshot["snapshot_id"],
        "evidence_kind": snapshot["evidence_kind"],
        "seed": snapshot["seed"],
        "runs": runs,
    })
    model_hashes = {
        path: sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
        for path in MODEL_PATHS
    }
    manifest = json_bytes({
        "schema_version": 1,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "model_version_sha256": sha256(json_bytes(model_hashes)).hexdigest(),
        "model_files_sha256": model_hashes,
        "snapshot": {
            "id": snapshot["snapshot_id"],
            "path": SNAPSHOT_PATH,
            "kind": snapshot["evidence_kind"],
            "sha256": sha256(snapshot_bytes).hexdigest(),
        },
        "outputs_sha256": {OUTPUT_NAME: sha256(result).hexdigest()},
    })
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_NAME).write_bytes(result)
    (out_dir / "manifest.json").write_bytes(manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    reproduce(args.out_dir)


if __name__ == "__main__":
    main()
