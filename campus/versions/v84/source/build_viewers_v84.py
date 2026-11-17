#!/usr/bin/env python3
"""Rebuild CPU viewer and correct full WebGL mesh guard and embedded full-GLB.
Make the WebGL -> CPU fallback fully self-contained, even when the HTML file is copied alone.
"""
from pathlib import Path
import re,base64,hashlib, json
R=Path(__file__).resolve().parents[1]
text=(R/'reference'/'_cpu_builder_generated_v83.py').read_text('utf8')
text=text.replace('BNBU_v83_FULL_EDITABLE.glb','BNBU_v84_FULL_EDITABLE.glb')
text=text.replace('v83','v84').replace('V83','V84')
text=text.replace('1347 个主模型网格','1346 个主模型网格')
text=text.replace('V52 十二处真实源三角面端点定位','道路重合副本移出主 GLB，保留原始实体道路')
(R/'source'/'_cpu_builder_generated_v84.py').write_text(text,'utf8')
exec(compile(text,str(R/'source'/'_cpu_builder_generated_v84.py'),'exec'),{'__file__':str(R/'source'/'_cpu_builder_generated_v84.py'),'__name__':'__main__'})
web=(R/'reference'/'BNBU_Campus_3D_Offline_v83.html').read_text('utf8')
newglb=(R/'model'/'BNBU_v84_FULL_EDITABLE.glb').read_bytes()
regex=r'(<script id="embedded-v71" type="application/octet-stream">)(.*?)(</script>)'
m=re.search(regex,web,re.S);assert m
assert hashlib.sha256(base64.b64decode(m.group(2))).hexdigest()=='2b694603f2d592499196f40bf74b569de55ccf42d2c63217b82bf76dce717b36'
web=web[:m.start(2)]+base64.b64encode(newglb).decode('ascii')+web[m.end(2):]
assert web.count('it.length!==1380')==1
web=web.replace('it.length!==1380','it.length!==1346')
web=web.replace('window.__BNBU_VERSION__="v82-fixed-lrc-normals"','window.__BNBU_VERSION__="v84-verified-road-overlay-dedup"')
web=web.replace('<title>BNBU 校园 v83 (v82 原始几何不变)','<title>BNBU 校园 v84 (1346 网格；1 处路面重合副本网格隔离)')
# Install an early error listener BEFORE the original full-GLB renderer starts.
# Some legacy renderers throw synchronously before a late fallback handler can run.
early='''''''''<script id="bnbu-early-webgl-detection">
window.__BNBU_WEBGL_FAILED__=false;
function __bnbuRecordWebGLError(msg){
 if(/(?:Error creating WebGL context|WebGL context could not be created|WebGL is not supported)/i.test(String(msg))){
  window.__BNBU_WEBGL_FAILED__=true;
  window.dispatchEvent(new Event('bnbu-webgl-failure'));
 }
}
window.addEventListener('error',e=>__bnbuRecordWebGLError(e.message),true);
window.addEventListener('unhandledrejection',e=>__bnbuRecordWebGLError(e.reason?.message||e.reason),true);
</script>'''''''''
web=web.replace('<head>','<head>'+early,1)

# Previously v83's full-scene runtime guard incorrectly demanded 1380 meshes of a 1347-mesh GLB.
# Update the visible button to use an embedded CPU document; no broken sibling-file href.
old='href="BNBU_Campus_3D_CPU_v83.html"'
assert web.count(old)==1
web=web.replace(old,'href="#cpu-fallback" id="bn-cpu-fallback"')
cpu=(R/'viewer'/'BNBU_Campus_3D_CPU_v84.html').read_bytes()
cpu64=base64.b64encode(cpu).decode('ascii')
js='''<script id="embedded-cpu-v84" type="application/octet-stream">'''+cpu64+'''</script>
<script>
(function(){
  const link=document.getElementById('bn-cpu-fallback');
  let switched=false;
  function switchToCpu(){
    if(switched)return;switched=true;
    const encoded=document.getElementById('embedded-cpu-v84').textContent.trim();
    // Convert bytes losslessly; UTF-8 Chinese labels are decoded using TextDecoder.
    const binary=atob(encoded),bytes=new Uint8Array(binary.length);
    for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
    const html=new TextDecoder('utf-8').decode(bytes);
    document.open(); document.write(html); document.close();
  }
  link.addEventListener('click',function(e){e.preventDefault();switchToCpu()});
  // Real WebGL is the preferred renderer. Switch automatically only after an actual
  // context-creation failure; do not hide unrelated asset or JavaScript bugs.
  function detectWebGLFailure(msg){
    if(/(?:Error creating WebGL context|WebGL context could not be created|WebGL is not supported)/i.test(String(msg)))
      setTimeout(switchToCpu,0);
  }
  window.addEventListener('error',e=>detectWebGLFailure(e.message),true);
  window.addEventListener('unhandledrejection',e=>detectWebGLFailure(e.reason?.message || e.reason),true);
  window.addEventListener('bnbu-webgl-failure',()=>setTimeout(switchToCpu,0));
  if(window.__BNBU_WEBGL_FAILED__)setTimeout(switchToCpu,0);
})();
</script>
'''
assert '</body>' in web
web=web.replace('</body>',js+'</body>')
webout=R/'viewer'/'BNBU_Campus_3D_Offline_v84.html'
webout.write_text(web,'utf8')
assert base64.b64decode(re.search(regex,web,re.S).group(2))==newglb
assert 'it.length!==1346' in web
assert 'embedded-cpu-v84' in web
# v83 source-triangle endpoint inspector is still exact as v84 has not moved V52 surfaces.
(R/'viewer'/'BNBU_v84_V52_Actual_Triangle_3D_Inspector.html').write_bytes((R/'reference'/'BNBU_v83_V52_Actual_Triangle_3D_Inspector.html').read_bytes())
(R/'qa'/'v84_viewer_build.json').write_text(json.dumps({'source_meshes':1346,'guard_mesh_count':1346,'embedded_main_sha256':hashlib.sha256(newglb).hexdigest(),'cpu_fallback_embedded':True,'v52_endpoint_source_triangles_unchanged':True,'no_external_cpu_viewer_dependency':True},indent=2),'utf8')
print('Viewer built',webout.stat().st_size,len(cpu),'mainsha',hashlib.sha256(newglb).hexdigest())