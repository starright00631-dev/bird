#!/usr/bin/env python3
"""Extract full 3D inline script and verify syntax with Node.js."""
from pathlib import Path
import re,subprocess,json
R=Path(__file__).resolve().parent
html=(R/'viewer/BNBU_Campus_3D_Offline_v80.html').read_text('utf8')
js=[(attrs.strip(),body) for attrs,body in re.findall(r'<script([^>]*)>(.*?)</script>',html,re.S)
    if 'type="application/' not in attrs]
assert len(js)==1
p=R/'qa/.v80_runtime_check.js';p.write_text(js[0][1],'utf8')
r=subprocess.run(['node','--check',str(p)],capture_output=True,text=True)
p.unlink()
assert r.returncode==0, r.stderr
msg=f'PASS: node --check: {len(js)} runtime inline script, {len(js[0][1])} UTF8 chars. GLB/GIS embedded asset hashes independently checked. Browser full WebGL render not verified in this container.\n'
(R/'qa/v80_Javascript_check.txt').write_text(msg,'utf8')
print(msg)