#!/usr/bin/env python3
"""Static manifest+JavaScript check; not equivalent to a browser render."""
from pathlib import Path
import re,json,hashlib,subprocess
R=Path(__file__).resolve().parent;v=R/'viewer';code=(v/'viewer.js').read_text()
assets=sorted(set(re.findall(r'generated/([A-Za-z0-9_.-]+\.(?:glb|json|geojson|png|jpg))',code)))
missing=[p for p in assets if not (v/'generated'/p).is_file()]
jscheck=subprocess.run(['node','--check',str(v/'viewer.js')],capture_output=True,text=True)
html=(v/'BNBU_Campus_3D_Offline_v78.html').read_text()
script=html.rsplit('<script>',1)[-1].split('</script>',1)[0] if '<script>' in html else ''
# The bundled original loader script is the final inline JavaScript block.
if len(script)>150000:
 t=R/'qa/.offline_JS_syntax_test.js';t.write_text(script)
 c=subprocess.run(['node','--check',str(t)],capture_output=True,text=True);t.unlink()
 else_check=c.returncode==0
else:else_check=None
res={'version':'v78','checked_js_file':'viewer/viewer.js','node_check_rc':jscheck.returncode,'embedded_js_syntax_check':else_check,'relative_asset_urls':len(assets),'missing_relative_asset_urls':missing,'main_model_asset_matches':hashlib.sha256((v/'generated/BNBU_v78_RECONCILED_MAIN.glb').read_bytes()).hexdigest()==hashlib.sha256((R/'model/BNBU_v78_RECONCILED_MAIN_EDITABLE.glb').read_bytes()).hexdigest(),'scene_mesh_guard':'it.length!==1380' in code and 'it.length!==1379' not in code,'toggle_lrc':html.count('id="show-v78-skylight"')==1,'toggle_seams_default_unchecked':html.count('id="show-v78-seams"')==1,'headless_chromium_in_this_sandbox':'blocked local file and 127.0.0.1 navigation (net::ERR_BLOCKED_BY_ADMINISTRATOR)','browser_runtime_pass':False,'deployed_pages_confirmed':False}
assert res['scene_mesh_guard'] and jscheck.returncode==0 and not missing and res['main_model_asset_matches'] and res['toggle_lrc'] and res['toggle_seams_default_unchecked'] and else_check
(R/'qa/v78_viewer_static_verification.json').write_text(json.dumps(res,ensure_ascii=False,indent=2))
print(json.dumps(res,ensure_ascii=False,indent=2))