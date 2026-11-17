#!/usr/bin/env python3
"""Audit pinned UVic detection-trial and survey-schedule inputs."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from birdglass.uvic_detection import audit_detection_sources, fetch_pinned_detection_sources
from birdglass.uvic_panel import write_json

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-pinned", action="store_true")
    parser.add_argument("--search-efficiency-csv", type=Path)
    parser.add_argument("--search-schedule-csv", type=Path)
    parser.add_argument("--carcass-persistence-csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/derived/uvic/uvic_detection_audit.json"))
    args = parser.parse_args()
    local = (args.search_efficiency_csv, args.search_schedule_csv, args.carcass_persistence_csv)
    if args.fetch_pinned:
        if any(p is not None for p in local):
            parser.error("Use --fetch-pinned or all three local CSV paths, not both")
        texts, hashes = fetch_pinned_detection_sources()
        strict = True
    else:
        if any(p is None for p in local):
            parser.error("Pass --fetch-pinned or all three local CSV paths")
        texts = {
            "searcher_efficiency": args.search_efficiency_csv.read_text(encoding="utf-8-sig"),
            "search_schedule": args.search_schedule_csv.read_text(encoding="utf-8-sig"),
            "carcass_persistence": args.carcass_persistence_csv.read_text(encoding="utf-8-sig"),
        }
        hashes, strict = None, False
    audit = audit_detection_sources(texts["searcher_efficiency"], texts["search_schedule"],
                                    texts["carcass_persistence"], strict_source=strict,
                                    source_hashes=hashes)
    write_json(audit, args.output)
    print(f"Wrote detection-trial audit to {args.output}")
    print(f"Searcher={audit['source_rows']['searcher_efficiency_trials']}; persistence={audit['source_rows']['carcass_persistence_trials']}; schedule={audit['source_rows']['search_schedule_dates']}")

if __name__ == "__main__":
    main()
