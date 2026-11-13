# BNBU v89 — building feature audit

This branch now contains two distinct passes:
- **Inventory audit:** resolve every building component reference in the v88 scene and identify missing or asymmetric feature categories.
- **Reference-first visual gap audit:** compare identified official/credible building photos against the actual current source meshes, and record concrete appearance mismatches.

The audit remains **read-only**: no GLB, GIS, viewer, or physical geometry was changed.

## Scope checked

- 30 core building records: T1–T8, V15–V29, D1–D6, and Phase-I LRC.
- 8 additional mapped assets in the v88 registry.
- 1 official but unmapped Phase-II Learning Resource Centre and Laboratory Complex.
- 1 quarantined CTV-adjacent small-house hypothesis.

## Highest-priority findings

1. **T1:** the official T1 photograph shows horizontal ribbon glazing, projecting white frames, lower-level glazing and a canopy. The current T1 component set has no separately registered glazing surfaces or canopy.
2. **V29:** an identified V29 photograph shows six storeys, windows, recessed balconies and strong projecting frames; the current V29 model has only the opaque primary mass, roof and story-edge strips.
3. **V15–V29:** seven records have only three registered components each; none has separately identified glazing, balconies or railings. V25 is a major resolution outlier (62 vertices / 120 triangles in its primary mass).
4. **D1–D6:** each has roof cross-ribs, but no separately identified facade glazing, balconies/rails or stairs. Official Phase-II dormitory imagery shows a much richer facade grid; exact assignment needs building-specific views.
5. **Phase-II LRC/Laboratory Complex:** official building, still unmapped in the physical master, and distinct from the circular commons.

See [the reference-first visual gap audit](qa/REFERENCE_FIRST_VISUAL_GAP_AUDIT_V89.md) for exact GLB nodes, mesh evidence, image sources, confidence and reconstruction gates.

## Reproduce

Unpack the v88 whole-campus release, then run:

```bash
python source/audit_buildings_v89.py --package-root /path/to/BNBU_Campus_Full_v88 --out-dir qa
BNBU_PACKAGE_ROOT=/path/to/BNBU_Campus_Full_v88 python -m unittest discover -s tests -v
```

Dependencies: `numpy`, `trimesh` (both are included in the v88 release requirements). The script checks that the source GLB hash is unchanged after the read-only audit.

## Evidence references

- T1 official facade page: https://fbm.bnbu.edu.cn/en/about_us/contact_us.htm
- T2 official photo: https://mpro.bnbu.edu.cn/info/1086/4347.htm
- T3 official photo: https://fst.bnbu.edu.cn/en/info/1162/5820.htm
- Phase-I dormitory exterior: https://admission.bnbu.edu.cn/info/1734/1470.htm
- V29 identified photo: https://www.eol.cn/guangdong/gdgd/202406/t20240624_2619031.shtml
- Phase-II dormitory exterior: https://admission.bnbu.edu.cn/info/1734/1469.htm
- Phase-II LRC/Laboratory Complex: https://www.bnbu.edu.cn/en/info/1076/12578.htm
- Aedas No.2 Campus design page: https://www.aedas.com/en/project/bnu-hkbu-united-international-college-uic-no-2-campus/
- V15–V29 official hall identity mapping is recorded in the building registry.

All photos are typological evidence unless explicitly identified to a building; none is treated as a calibrated as-built survey.
