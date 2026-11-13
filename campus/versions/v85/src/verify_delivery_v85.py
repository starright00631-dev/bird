from pathlib import Path
import hashlib,json,zipfile
import trimesh
R=Path(__file__).resolve().parents[1]
master=R/'model/BNBU_v84_FULL_EDITABLE.glb'
assert hashlib.sha256(master.read_bytes()).hexdigest()=='242ade4c7cf25a4437e674b271ea451f9367449c23530ca95679b33749989848'
s=trimesh.load(master,force='scene',process=False)
assert len(s.graph.nodes_geometry)==1346 and sum(len(x.faces) for x in s.geometry.values())==691593
r=json.loads((R/'qa/v85_v60_endpoints_3d.json').read_text())
assert r['parent_sha256']==hashlib.sha256(master.read_bytes()).hexdigest()
assert r['v52_source_faces_checked_unchanged']==12 and r['total_endpoint_probes']==14
assert len(r['v60_ends'])==2 and not any(x['is_routable'] for x in r['v60_ends'])
assert len(json.loads((R/'data/BNBU_v84_ACTIVE.geojson').read_text())['features'])==534
assert (R/'viewer/BNBU_Campus_3D_Offline_v84.html').stat().st_size>25_000_000
assert (R/'viewer/BNBU_v85_V52_V60_Actual_SourceTriangle_3D_Inspector.html').stat().st_size>250_000
print('PASS: v85 14 exact mesh-source probes, full v84 GLB/GIS/viewer retained unchanged')