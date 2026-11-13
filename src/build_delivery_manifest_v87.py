#!/usr/bin/env python3
"""Generate v87 delivery manifest and SHA256 inventory."""
from pathlib import Path
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {"SHA256_v87.json", "v87_delivery_manifest.json"}

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

parent = json.loads((ROOT/'qa'/'v87_registration_audit.json').read_text('utf-8'))
browser = json.loads((ROOT/'qa'/'v87_browser_validation.json').read_text('utf-8'))
cpu = json.loads((ROOT/'qa'/'v84_cpu_browser_validation.json').read_text('utf-8'))
manifest = {
  "version":"v87",
  "package":"BNBU_campus_v87_2026-11-12.zip",
  "direct_parent":"v86 checkpoint; physical master v84",
  "parent_glb_sha256":parent['parent_glb_sha256'],
  "physical_master_modified":False,
  "physical_gpkg_modified":False,
  "active_geojson_modified":False,
  "active_kml_modified":False,
  "new_scientific_geometry_count":0,
  "candidate_is_display_only":True,
  "osm_source":{"retrieved_at_utc":parent['osm_retrieved_at_utc'],"raw_elements_sha256":parent['osm_raw_elements_sha256'],"ways":parent['osm_ways']},
  "registration":{"method":parent['registration_method'],"v86_shift_xy_m":parent['v86_bbox_centre_translation_xy_m'],"per_building_icp":{b:{"rotation_deg":parent['buildings'][b]['rotation_deg'],"mean_boundary_distance_m":parent['buildings'][b]['mean_boundary_distance_m'],"p95_boundary_distance_m":parent['buildings'][b]['p95_boundary_distance_m'],"baseline_iou":parent['buildings'][b]['baseline_iou'],"v86_bbox_candidate_iou":parent['buildings'][b]['v86_bbox_candidate_iou'],"icp_aligned_iou":parent['buildings'][b]['icp_aligned_iou']} for b in ('T1','T2','T3')}},
  "geometry":{"parent_meshes":1346,"parent_triangles":691593,"candidate_meshes":parent['per_building_icp_candidate_components'],"candidate_triangles":parent['per_building_icp_candidate_triangles'],"comparison_meshes":parent['v87_comparison_glb_meshes'],"comparison_triangles":parent['v87_comparison_glb_triangles'],"v52_04_05":"baseline-only; excluded from per-building ICP"},
  "gis":{"physical_gpkg_layers":146,"active_features":534,"qa_gpkg_layers":parent['qa_gpkg_layers'],"qa_gpkg_features":parent['qa_gpkg_features'],"birdstrike_area_eligible":False},
  "browser":{"v87_viewer_success":browser['success'],"v87_node_check":browser['node_check'],"v87_file_navigation":browser.get('file_navigation'),"v87_http_navigation":browser.get('http_navigation'),"v87_page_errors":len(browser.get('page_errors',[])),"v84_cpu_viewer_success":cpu['success'],"v84_cpu_meshes":cpu['initial_state']['sourceMeshCount'],"v84_cpu_triangles":cpu['initial_state']['sourceTriangles']},
  "rebuild_commands":["python src/analyze_osm_footprints_v87.py","python src/build_v87_viewer.py","python src/test_v87_browser.py --set-content-only","python src/test_v84_cpu_viewer.py","python -m unittest discover -s tests -v","python src/verify_v87.py"],
  "important_limitations":parent['important_limitations'],
}
(ROOT/'qa'/'v87_delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
entries=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(ROOT).as_posix()
    if p.name in EXCLUDE or '__pycache__' in p.parts or p.suffix=='.pyc' or rel.endswith('.zip'):
        continue
    entries.append({"path":rel,"size_bytes":p.stat().st_size,"sha256":sha(p)})
sha_doc={"version":"v87","algorithm":"SHA-256","files":entries,"file_count":len(entries)}
(ROOT/'qa'/'SHA256_v87.json').write_text(json.dumps(sha_doc,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({"file_count":len(entries),"manifest":str(ROOT/'qa'/'v87_delivery_manifest.json'),"sha256_inventory":str(ROOT/'qa'/'SHA256_v87.json')},ensure_ascii=False))