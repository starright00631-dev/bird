#!/usr/bin/env python3
"""Retain the validated parent v82 full 3D WebGL scene and update only CPU fallback target.
Main source GLB is BIT-IDENTICAL, so no unsafe embedded Base64 surgery is needed.
"""
from pathlib import Path
import base64,re,hashlib
R=Path(__file__).resolve().parents[1]
s=(R/'reference'/'BNBU_Campus_3D_Offline_v82.html').read_text('utf8')
old=re.search(r'<script id="embedded-v71" type="application/octet-stream">(.*?)</script>',s,re.S)
assert old
raw=base64.b64decode(old.group(1));model=(R/'model'/'BNBU_v83_FULL_EDITABLE.glb').read_bytes()
assert raw==model
s=s.replace('<title>BNBU 校园 v82', '<title>BNBU 校园 v83 (v82 原始几何不变)')
s=s.replace('BNBU_Campus_3D_CPU_v82.html', 'BNBU_Campus_3D_CPU_v83.html')
# preserve truthful visual label: geometry remains v82, so legacy provenance in UI stays v82.
assert base64.b64decode(re.search(r'<script id="embedded-v71" type="application/octet-stream">(.*?)</script>',s,re.S).group(1))==model
(R/'viewer'/'BNBU_Campus_3D_Offline_v83.html').write_text(s,'utf8')
(R/'viewer'/'双击查看_校园3D.html').write_bytes((R/'viewer'/'BNBU_Campus_3D_CPU_v83.html').read_bytes())
print('embedded SHA256',hashlib.sha256(raw).hexdigest())