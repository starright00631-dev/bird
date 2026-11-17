#!/usr/bin/env python3
"""Rebuild the pinned UVic facade-period panel and its source audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from birdglass.uvic_panel import build_facade_period_panel, fetch_pinned_sources, write_json, write_panel_csv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-pinned", action="store_true", help="Download and verify the pinned upstream Git blobs")
    parser.add_argument("--fall-csv", type=Path)
    parser.add_argument("--winter-csv", type=Path)
    parser.add_argument("--buildings-csv", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("data/derived/uvic"))
    args = parser.parse_args()

    local_paths = (args.fall_csv, args.winter_csv, args.buildings_csv)
    if args.fetch_pinned:
        if any(path is not None for path in local_paths):
            parser.error("Use --fetch-pinned or all three local CSV paths, not both")
        texts, hashes = fetch_pinned_sources()
        strict = True
    else:
        if any(path is None for path in local_paths):
            parser.error("Pass --fetch-pinned or all of --fall-csv, --winter-csv and --buildings-csv")
        texts = {
            "fall": args.fall_csv.read_text(encoding="utf-8-sig"),
            "winter": args.winter_csv.read_text(encoding="utf-8-sig"),
            "buildings": args.buildings_csv.read_text(encoding="utf-8-sig"),
        }
        hashes = {}
        strict = False

    panel, audit = build_facade_period_panel(
        texts["fall"], texts["winter"], texts["buildings"],
        strict_source=strict,
        source_hashes=hashes or None,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = args.out_dir / "uvic_facade_period_panel.csv"
    audit_path = args.out_dir / "uvic_source_audit.json"
    write_panel_csv(panel, panel_path)
    write_json(audit, audit_path)
    print(f"Wrote {len(panel)} facade-period rows to {panel_path}")
    print(f"Wrote source audit to {audit_path}")
    print(
        f"Source rows={audit['totals']['raw_source_rows']}; "
        f"visits={audit['totals']['unique_facade_day_visits']}; "
        f"evidence={audit['totals']['collision_evidence_count']}"
    )


if __name__ == "__main__":
    main()
