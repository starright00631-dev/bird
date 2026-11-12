"""Guard against loss of terrain/water/road layers or promoting unverified CTV geometry."""
import json
import lzma
import struct
from pathlib import Path

A = Path(__file__).resolve().parent / 'assets'
def raw(name):
    p = A / name
    return p.read_bytes() if p.exists() else lzma.decompress((A / (name + '.xz')).read_bytes())
def validate():
    doc = json.loads(raw('BNBU_v64_ACTIVE.geojson'))
    assert doc['type'] == 'FeatureCollection'
    f = doc['features']
    p = [x['properties'] for x in f]
    def count(key, val): return sum(x.get(key)==val for x in p)
    assert len(f)==522
    assert count('role','water_existing_v44_not_surveyed')==5
    assert count('role','shore_existing_v44_not_surveyed')==5
    assert count('feature_type','terrain_relief')==4
    assert count('role','vehicle_road')==2
    assert count('role','footpath')==54
    assert not any('CTV' in x.get('model_node','').upper() and any(v in x.get('model_node','').upper() for v in ('VILLA','HOUSE')) for x in p)
    assert all(x.get('is_surveyed')!=1 for x in p if x.get('feature_type')=='terrain_relief' or x.get('role') in ('vehicle_road','water_existing_v44_not_surveyed'))
    assert json.loads(raw('BNBU_v64_CTV_EXCLUDED.geojson'))['type']=='FeatureCollection'
    glb=raw('BNBU_v64_ACTIVE.glb')
    assert glb[:4]==b'glTF' and struct.unpack_from('<II',glb,4)==(2,len(glb))
    assert raw('BNBU_v64_EDITABLE_GIS.gpkg')[:16]==b'SQLite format 3\\0'.replace(b'\\0',b'\0')
    return {'geojson_features':len(f),'water_meshes':5,'shore_meshes':5,'relative_hills':4,'vehicle_roads':2,'footpaths':54,'active_glb_bytes':len(glb),'CTV_excluded':True,'surveyed':False}
if __name__=='__main__': print(json.dumps(validate(),indent=2))
