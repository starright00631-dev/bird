# BNBU v89 — building feature audit

This is the first building-by-building audit pass against the v88 whole-campus release. It is intentionally **audit-only**: no GLB, GIS, viewer, or physical geometry was changed.

## Scope checked

- 30 core building records: T1–T8, V15–V29, D1–D6, and Phase-I LRC.
- 8 additional mapped assets in the v88 registry.
- 1 official but unmapped Phase-II Learning Resource Centre and Laboratory Complex.
- 1 quarantined CTV-adjacent small-house hypothesis.

The audit resolves every component name in the v76 architecture atlas against the active v88 scene and records per-building mesh counts, triangle counts, transforms/bounds, Z levels, story-edge nodes, transparent glazing surfaces, opaque frames/returns, stairs and roof cross-ribs.

## Highest-priority findings

1. **Phase-II LRC/Laboratory Complex is not mapped to any active mesh.** It is a distinct official building and must not be substituted with the circular commons.
2. **V25 is a geometry-resolution outlier:** 62 vertices, 120 triangles, and only two primary-mesh Z levels. It needs building-specific imagery before repair.
3. **V15–V29 have no separately identified glazing, balcony or railing components**, despite official Phase-I dormitory exterior imagery showing window bays and recessed balcony/guardrail features. The photograph is not registered to an individual V block, so no sibling pattern is copied.
4. **T1 has zero explicit glazing-surface nodes**, while the official T1 facade photo clearly shows horizontal ribbon glazing and lower-level glazing. T2/T3/T4 contain only 7/3/4 transparent glazing surfaces respectively; opaque mullions, jambs and returns are classified separately.
5. **D1–D6 have no separately identified glazing, balcony/rail or stair components** in the building registry. Official Phase-II dormitory imagery shows a deep recessed facade grid, window/balcony bays and open guardrails, but the exact D-building assignment is unresolved.
6. Only 8 of 15 V buildings have separate V63 story-edge meshes. This is an inventory asymmetry, not yet proof that the other seven lack floor bands in their primary mesh.
7. The optional LRC skylight shell remains outside the default physical master as an unsurveyed candidate.

## Reproduce

Unpack the v88 whole-campus release, then run:

```bash
python source/audit_buildings_v89.py --package-root /path/to/BNBU_Campus_Full_v88 --out-dir qa
BNBU_PACKAGE_ROOT=/path/to/BNBU_Campus_Full_v88 python -m unittest discover -s tests -v
```

Dependencies: `numpy`, `trimesh` (both are included in the v88 release requirements). The script checks that the source GLB hash is unchanged after the read-only audit.

## Evidence references

- T1 official facade page: https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm
- Phase-I dormitory exterior: https://admission.bnbu.edu.cn/info/1734/1470.htm
- Phase-II dormitory exterior: https://admission.bnbu.edu.cn/info/1734/1469.htm
- Phase-II LRC/Laboratory Complex: https://www.bnbu.edu.cn/en/info/1076/12578.htm
- Aedas No.2 Campus design page: https://www.aedas.com/en/project/learning-resources-center-at-beijing-normal-hong-kong-baptist-university-bnbu-no-2-campus/
- V15–V29 official hall identity mapping is recorded in `qa/building_feature_audit_v89.json`.

All photos are typological evidence unless explicitly identified to a building; none is treated as a calibrated as-built survey.