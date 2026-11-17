#!/usr/bin/env python3
"""Fit the descriptive, effort-offset UVic observed-evidence GEE baseline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from birdglass.uvic_panel import fit_observed_rate_gee, read_panel_csv, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/derived/uvic/uvic_facade_period_panel.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/uvic_observed_rate_baseline.json"))
    args = parser.parse_args()
    panel = read_panel_csv(args.input)
    result = fit_observed_rate_gee(panel)
    write_json(result, args.output)
    print(f"Wrote observed-evidence baseline to {args.output}")
    print(
        f"Rows={result['n_panel_rows']}; facades={result['n_facades']}; "
        f"evidence={result['collision_evidence_count']}; converged={result['converged']}"
    )


if __name__ == "__main__":
    main()
