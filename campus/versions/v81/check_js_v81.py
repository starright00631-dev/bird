from pathlib import Path
import re,subprocess,json,hashlib
R=Path(__file__).resolve().parents[1]
s=(R/'viewer/BNBU_Campus_3D_Offline_v81.html').read_text('utf8')
tests=[]
for i,m in enumerate(re.finditer(r'<script\b([^>]*)>(.*?)</script>',s,re.S|re.I)):
 if re.search(r'type=["\'](?:application/(?:json|octet-stream)|text/json)["\']',m.group(1),re.I):continue
 if m.group(2).strip():
  path=R/'qa'/f'v81_script_{i}.js';path.write_text(m.group(2),'utf8')
  r=subprocess.run(['node','--check',str(path)],capture_output=True,text=True)
  tests.append({'script':i,'code_bytes':len(m.group(2)),'ok':r.returncode==0,'stderr':r.stderr[:300]})
  if r.returncode:print(r.stderr)
assert all(t['ok'] for t in tests) and tests
(R/'qa/v81_js_static.json').write_text(json.dumps(tests,ensure_ascii=False,indent=2),'utf8')
print(tests)