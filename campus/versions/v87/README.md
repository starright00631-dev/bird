# BNBU v87 OSM full-way geometry capture

This repository path contains the reproducible OSM way-geometry acquisition and deterministic validation gate only.

- `src/fetch_osm_full_geometry_v87.py` retrieves complete OSM way geometry and validates node sequence, tags, closed rings and coordinate integrity.
- `tests/test_fetch_osm_full_geometry_v87.py` exercises the validation gate using local fixtures; it does not require Overpass access.
- Live acquisition is available only through manual workflow dispatch. The routine push workflow runs offline unit tests only.
- OSM is community-mapped reference geometry, not a survey control network. No OSM transform is promoted to the physical campus master.
- Full v87 registration experiments, viewer, candidate GLBs, GIS and QA assets are retained in the complete Library package `/BNBU_campus_v87_2026-11-12/`. They are research-only and do not replace mainline v76.1.

The independent registration integration test requires the full parent GLB and is explicitly skipped in repository-only CI.