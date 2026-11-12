# BNBU v69 waterfront evidence register

## Source geometry and boundaries

The v66 baseline contains 1,377 meshes. v69 keeps the same positions, triangles, scene transforms and registered GIS. Five inherited LAKE_00..LAKE_04 entities correspond to five existing SHORE_00..SHORE_04 banks and five existing v50 seams. Five **model entities** do not establish five real lakes. Shore color is interpolated only from the *unsurveyed original model-relative Z profile*. Appearance colors are not field-observed land cover or rock measurements. The browser adds a subtle procedural rippling normal map to original water surfaces and highlights existing promenade edges; these are visual effects, not measurements or new bridges.

## Official source constraints

- [BNBU 2015 campus development notice](https://www.bnbu.edu.cn/en/info/1077/3242.htm): the campus incorporates naturally present streams and ponds. No precise shore polygon is disclosed.
- [BNBU 2019 ecology survey](https://www.bnbu.edu.cn/info/1077/4589.htm): a seasonally changing natural wetland on the east side of the campus, at the foot of Chihua Hill, is connected to **two freshwater ponds on the hill**. It partly overlaps the campus. The article provides no surveyed pond polygon or height reference.
- [BNBU lakeside photograph](https://co.bnbu.edu.cn/en/info/1131/2702.htm): lakeside buildings, stone/concrete edges, shallow terraces, open-air decks. Photos establish types but have no camera poses calibrated to the inherited GLB.
- [Official UIC campus photograph](https://www.uic.edu.cn/en/info/1055/8428.htm): still water, planted banks and a boardwalk. No exact alignment to a model segment is available.

## Avoid incorrect wetland identity

The Phase-II archived model named V55_P2_ARCHIVED_WETLAND_RESTORED_WATER_NOT_SURVEYED is **not identified** with the two documented east-hill freshwater ponds. Its coordinates remain hypotheses. v69 does not create either pond, relocate the old wetland, or turn archive features into surveyed geography.

## QA

Run python campus/refine_waterfront_v69.py, then python -m unittest discover -s campus -p 'test_waterfront_v69.py' -v. The generated provenance JSON records exact source/output hashes and a digest of geometry buffers before and after. The v69 scene retains precisely 1,377 meshes, all 522 source GIS features, and unchanged shape/coordinate information.

**Unresolved:** licensed orthophoto or control-point registration for shorelines, higher resolution bare-earth observations for banks, verified natural ponds, and component-by-component facade photography. Appearance changes do **not** establish measured bird-spectrum reflectance or bird collision exposure.
