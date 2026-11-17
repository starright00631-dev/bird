#!/usr/bin/env python3
"""Re-apply v88 whole-campus scene cleanup to the packaged v76.1 release."""
from pathlib import Path
import base64, json, struct, hashlib
import trimesh

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'history' / 'BNBU_v71_CONNECTED_LAKEFRONT_v76_parent.glb'
TARGET = ROOT / 'generated' / 'BNBU_v71_CONNECTED_LAKEFRONT.glb'
DUP = ROOT / 'generated' / 'BNBU_v88_V42_ROAD000_DUPLICATE_DISPLAY_ONLY.glb'
ATLAS = ROOT / 'generated' / 'BNBU_v76_ARCHITECTURE_COMPONENT_ATLAS.json'
VIEWER = ROOT / 'viewer.js'
STANDALONE = ROOT / '双击查看_校园3D.html'

def parse_glb(data: bytes):
    magic, version, total = struct.unpack_from('<4sII', data, 0)
    if magic != b'glTF' or version != 2 or total != len(data):
        raise ValueError('Invalid parent GLB')
    chunks=[]; off=12
    while off < len(data):
        length, kind = struct.unpack_from('<II', data, off); off += 8
        chunks.append((kind, data[off:off+length])); off += length
    doc=json.loads(chunks[0][1].decode('utf-8').rstrip(' \t\r\n\0'))
    return doc,chunks

def write_glb(path: Path, doc, chunks):
    raw=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    raw += b' ' * ((4-len(raw)%4)%4)
    out=bytearray(b'glTF'+struct.pack('<II',2,0))
    out += struct.pack('<II',len(raw),0x4E4F534A)+raw
    for kind, chunk in chunks[1:]: out += struct.pack('<II',len(chunk),kind)+chunk
    struct.pack_into('<I',out,8,len(out)); path.write_bytes(out)

def patch_viewer_js(s: str) -> str:
    s=s.replace('it.length!==1379','it.length!==1378')
    s=s.replace('Rn.building_records.find(d=>d.id===i)','Rn.building_records.concat(Rn.extended_records||[]).find(d=>d.id===i)')
    s=s.replace('for(let s of i.building_records){','for(let s of i.building_records.concat(i.extended_records||[])){')
    old_expr=r'r.textContent=s.id+" \xB7 "+{T:"\u6559\u5B66\u697C",V:"\u4E00\u671F\u5BBF\u820D",D:"\u4E8C\u671F\u5BBF\u820D",LRC:"\u5B66\u4E60\u8D44\u6E90\u4E2D\u5FC3"}[s.family]'
    new_expr=r'r.textContent=s.display_label||s.id+" \xB7 "+({T:"\u6559\u5B66\u697C",V:"\u4E00\u671F\u5BBF\u820D",D:"\u4E8C\u671F\u5BBF\u820D",LRC:"\u5B66\u4E60\u8D44\u6E90\u4E2D\u5FC3"}[s.family]||"\u5176\u4ED6\u5EFA\u7B51/\u7ED3\u6784")'
    s=s.replace(old_expr,new_expr)
    old_status=r'K("architecture-v76-status").textContent="\u5DF2\u6838\u5BF9 8 \u680B T\u300115 \u680B V\u30016 \u680B D \u4E0E LRC\uFF0C\u5171 30 \u680B\uFF1B\u4F9D\u539F\u4E09\u89D2\u9762\u6062\u590D\u7ED3\u6784\u7EBF\uFF0C\u65E0\u865A\u6784\u7A97\u683C\u3002"'
    new_status=r'K("architecture-v76-status").textContent="\u6838\u5FC330\u680B + 8\u4E2A\u6269\u5C55\u6620\u5C04\u8D44\u4EA7\u5DF2\u7EB3\u5165\u9009\u62E9\u5668\uFF1B\u4E8C\u671FLRC/\u5B9E\u9A8C\u7EFC\u5408\u697C\u4ECD\u672A\u5339\u914D\uFF0CC TV\u5C0F\u5EFA\u7B51\u5047\u8BBE\u4FDD\u6301\u9694\u79BB\u3002"'
    s=s.replace(old_status,new_status)
    s=s.replace('window.__BNBU_VERSION__="v76"','window.__BNBU_VERSION__="v88"')
    s=s.replace('v76BuildingCount:()=>Rn?.building_count||0,','v76BuildingCount:()=>Rn?.building_count||0,v88MappedAssetCount:()=>Rn?Rn.building_records.length+(Rn.extended_records||[]).length:0,')
    return s

def main():
    if not PARENT.exists(): raise FileNotFoundError(PARENT)
    if not ATLAS.exists(): raise FileNotFoundError(ATLAS)
    doc,chunks=parse_glb(PARENT.read_bytes())
    matches=[i for i,n in enumerate(doc.get('nodes',[])) if n.get('name')=='V42_FACET_SIDE_ROAD_000']
    if len(matches)!=1: raise ValueError(f'Expected one duplicate node, got {matches}')
    idx=matches[0]; parents=[]
    for i,node in enumerate(doc['nodes']):
        if idx in node.get('children',[]):
            node['children']=[x for x in node['children'] if x!=idx]
            parents.append(node.get('name',str(i)))
    for scene in doc.get('scenes',[]):
        if idx in scene.get('nodes',[]):
            scene['nodes']=[x for x in scene['nodes'] if x!=idx]
            parents.append('scene_root')
    if not parents: raise ValueError('Duplicate node is not attached to an active scene')
    doc.setdefault('asset',{}).setdefault('extras',{})['bnbu_v88_duplicate_cleanup']={
        'removed_active_node':'V42_FACET_SIDE_ROAD_000','retained_surface_node':'ROAD_000',
        'mesh_resource_retained_unreferenced':True,'parent_nodes':parents,
        'physical_surface_geometry_changed':False
    }
    write_glb(TARGET,doc,chunks)
    parent=trimesh.load(PARENT,force='scene',process=False)
    tf,g=parent.graph['V42_FACET_SIDE_ROAD_000']; mesh=parent.geometry[g].copy(); mesh.apply_transform(tf)
    scene=trimesh.Scene(); scene.add_geometry(mesh,geom_name='V42_FACET_SIDE_ROAD_000_DUPLICATE_DISPLAY_ONLY',node_name='V42_FACET_SIDE_ROAD_000_DUPLICATE_DISPLAY_ONLY')
    DUP.write_bytes(scene.export(file_type='glb'))
    # Keep the external viewer and the standalone embedded viewer in sync.
    VIEWER.write_text(patch_viewer_js(VIEWER.read_text('utf-8')),'utf-8')
    html=patch_viewer_js(STANDALONE.read_text('utf-8'))
    tag='<script id="embedded-v71" type="application/octet-stream">'
    start=html.index(tag)+len(tag); end=html.index('</script>',start)
    html=html[:start]+base64.b64encode(TARGET.read_bytes()).decode('ascii')+html[end:]
    atlas=json.loads(ATLAS.read_text('utf-8'))
    atag='<script id="embedded-v76-architecture" type="application/json">'
    start=html.index(atag)+len(atag); end=html.index('</script>',start)
    html=html[:start]+json.dumps(atlas,ensure_ascii=False,separators=(',',':'))+html[end:]
    STANDALONE.write_text(html,'utf-8')
    print(json.dumps({'success':True,'parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),'target_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),'removed_node':'V42_FACET_SIDE_ROAD_000','parent_nodes':parents},ensure_ascii=False))

if __name__=='__main__': main()