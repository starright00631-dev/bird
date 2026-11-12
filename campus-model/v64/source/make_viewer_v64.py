#!/usr/bin/env python3
"""Build standalone embedded GLB v64, preserving v63 comparison mode and controls."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'viewer'))
from make_viewer import generate
s=(R/'viewer'/'viewer_template_v63.html').read_text('utf8')
s=s.replace('BNBU v63', 'BNBU v64')
s=s.replace('v63 \u535a\u96c5\u82d1', 'v63 \u535a\u96c5\u82d1')
s=s.replace('v63\uff1a\u5b8c\u6574\u7ee7\u627f v62', 'v64\uff1a\u5728 v63 \u5b8c\u6574\u6821\u56ed\u4e0a\u7ea6\u675f\u5e73\u6ed1\u56db\u7ec4\u539f\u6709\u5c71\u4f53\uff08\u4ec5 Z \u00b10.35 \u6a21\u578b\u7c73\uff0cXY \u4e0d\u53d8\uff09\u3002v63 \u7ee7\u627f v62')
s=s.replace('v53 \u00b7 \u56db\u5904\u5b9e\u4f53\u8d77\u4f0f\u5c71\u5730\uff08\u975e DEM\uff09','v64 \u00b7 \u56db\u7ec4\u539f\u6709\u5c71\u4f53\u5761\u9762\u7f51\u683c\u5e73\u6ed1\uff08\u975e DEM\uff09')
s=s.replace("if(n.startsWith('V53_TERRAIN_RELIEF_'))return 'landscape';","if(n.startsWith('V64_CONSTRAINED_RELIEF_')||n.startsWith('V53_TERRAIN_RELIEF_'))return 'landscape';")
s=s.replace("if(u.startsWith('V63_RETOPOLOGIZED_OPAQUE_STORYEDGE_'))return 'I';", "if(u.startsWith('V64_CONSTRAINED_RELIEF_PHASEII_'))return 'II';if(u.startsWith('V64_CONSTRAINED_RELIEF_'))return 'I';if(u.startsWith('V63_RETOPOLOGIZED_OPAQUE_STORYEDGE_'))return 'I';")
s=s.replace('if(!showV53Terrain&&m.name.startsWith("V53_TERRAIN_RELIEF_"))return false;', 'if(!showV53Terrain&&(m.name.startsWith("V64_CONSTRAINED_RELIEF_")||m.name.startsWith("V53_TERRAIN_RELIEF_")))return false;')
s=s.replace("const ms=current.items.filter(m=>m.name.startsWith('V53_TERRAIN_RELIEF_'));", "const ms=current.items.filter(m=>m.name.startsWith('V64_CONSTRAINED_RELIEF_')||m.name.startsWith('V53_TERRAIN_RELIEF_'));")
s=s.replace("'\u8fd4\u56de v63 \u4e3b\u6a21\u578b':'\u67e5\u770b v62 \u5bf9\u7167\u57fa\u7ebf'", "'\u8fd4\u56de v64 \u4e3b\u6a21\u578b':'\u67e5\u770b v63 \u5bf9\u7167\u57fa\u7ebf'")
s=s.replace('v62 \u5bf9\u7167\u57fa\u7ebf', 'v63 \u5bf9\u7167\u57fa\u7ebf')
s=s.replace("'\u8fd4\u56de v63 \u4e3b\u6a21\u578b'", "'\u8fd4\u56de v64 \u4e3b\u6a21\u578b'")
s=s.replace('v64 \u535a\u96c5\u82d1 46', 'v63 \u535a\u96c5\u82d1 46')
s=s.replace('v64 \u00b7 46 \u5904', 'v63 \u00b7 46 \u5904')
assert s.count('V64_CONSTRAINED_RELIEF_') >= 4
(R/'viewer'/'viewer_template_v64.html').write_text(s,'utf8')
generate(R/'model'/'BNBU_v64_FULL_EDITABLE.glb',R/'BNBU_Campus_3D_Viewer_v64.html','v64',R/'viewer'/'viewer_template_v64.html',strict=R/'input'/'BNBU_v63_FULL_EDITABLE.glb')