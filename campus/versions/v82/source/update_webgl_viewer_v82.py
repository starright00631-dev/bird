#!/usr/bin/env python3
"""Re-embed exact main v82 GLB in inherited Three.js offline viewer; add CPU access.
No CDN, no external asset needed for main GLB. Legacy sidecar assets remain explicitly display-only.
"""
from pathlib import Path
import base64,re,hashlib,json
R=Path(__file__).resolve().parents[1]
s=(R/'input'/'BNBU_Campus_3D_Offline_v81.html').read_text('utf8') if (R/'input'/'BNBU_Campus_3D_Offline_v81.html').exists() else (R/'reference'/'BNBU_Campus_3D_Offline_v81.html').read_text('utf8')
old=re.search(r'(<script id="embedded-v71" type="application/octet-stream">)(.*?)(</script>)',s,re.S)
assert old and base64.b64decode(old.group(2))==(R/'input'/'BNBU_v81_FULL_EDITABLE.glb').read_bytes()
newglb=(R/'model'/'BNBU_v82_FULL_EDITABLE.glb').read_bytes()
s=s[:old.start(2)]+base64.b64encode(newglb).decode()+s[old.end(2):]
s=s.replace('BNBU 校园 v81 ·','BNBU 校园 v82 ·')
s=s.replace('window.__BNBU_VERSION__="v81-evidence-gated"','window.__BNBU_VERSION__="v82-fixed-lrc-normals"')
s=s.replace('<input id="show-v75-glass" type="checkbox" checked>', '<input id="show-v75-glass" type="checkbox">')
s=s.replace('<input id="show-photo-proxies" type="checkbox" checked>', '<input id="show-photo-proxies" type="checkbox">')
s=s.replace('</header>', '</header>')
# Add strong no-WebGL fallback access without replacing full source asset.
s=s.replace('<div id="render-error" hidden role="alert"></div>',
'''<div id="render-error" hidden role="alert"></div><div style="position:absolute;right:15px;bottom:14px;z-index:10;background:#0d2237e6;padding:8px 12px;border-radius:7px;font:12px system-ui"><a href="BNBU_Campus_3D_CPU_v82.html" style="color:#95f5e9">WebGL 被禁用？切换可运行 CPU 三维查看器（完整 LRC 源三角面）</a></div>''')
s=s.replace('13 \u7ec4\u6865\u58a9/\u6a2a\u6881', '13 \u7ec4\u5386\u53f2\u63a8\u5b9a\u652f\u6491\u5df2\u9694\u79bb')
# Retain archived type-only overlays behind unchecked switches; do not activate by default.
assert hashlib.sha256(base64.b64decode(re.search(r'<script id="embedded-v71" type="application/octet-stream">(.*?)</script>',s,re.S).group(1))).digest()==hashlib.sha256(newglb).digest()
(R/'viewer'/'BNBU_Campus_3D_Offline_v82.html').write_text(s,'utf8')
print('FULL WEBGL HTML',len(s),'sha',hashlib.sha256(s.encode()).hexdigest())