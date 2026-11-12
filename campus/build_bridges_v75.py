"""Evidence-limited v75 bridge register and SOURCE-ANCHORED glass-balustrade overlay.

The official open-day photo shows transparent railing infill on a low lake
crossing. This permits a visual material TYPE, not actual panel dimensions.
Six upper academic links have no photo-registered window count; do not invent
their curtain walls, roof shapes, openings or door thresholds.
"""
from __future__ import annotations
import json,hashlib,struct
from pathlib import Path
import numpy as np
from shapely.geometry import Point,box
from audit_connections_v74 import Surface,DATA,GLB,sha_file

BASE=Path(__file__).resolve().parent
RAILS=DATA/'BNBU_v70_LAKEFRONT_DISPLAY_OVERLAY.json'
GLASS=DATA/'BNBU_v75_BOARDWALK_GLASS_INFILL_DISPLAY_ONLY.glb'
ATLAS=DATA/'BNBU_v75_BRIDGE_COMPONENT_ATLAS.json'
DECK='V60_P1_EASTLAKE_EXISTING_BOARDWALK_CLOSED_OPAQUE_3D_DECK_PHOTO_TYPE'
PREFIX='V52_LEVEL2_PEDESTRIAN_CONNECTION_'
NODE='BNBU_V75_LAKEBRIDGE_TRANSPARENT_INFILL_UNSURVEYED_NOT_RISK_GLASS'
BUILDINGS={'00':['T4','T5'],'01':['T5','T6'],'02':['T6','T7'],
           '03':['T7','T8'],'04':['T1','T2'],'05':['T2','T3']}
PHOTOS=[
 {'id':'P08-GLASS','url':'https://www.uic.edu.cn/info/1075/106799.htm','publisher':'BNBU',
  'applies_to':'V60_lakefront_type','visible':'Glass-like transparent infill between metal railing posts on a low curving bridge; glazed academic building is separate',
  'limits':'No registered dimensions, glass pane count, or verified correspondence of every railing segment'},
 {'id':'P04-WIDE','url':'https://fst.bnbu.edu.cn/mscbs_en/index.htm','publisher':'BNBU FST',
  'applies_to':'V60_lakefront_type','visible':'Water crossing, support rhythm, planted islands, differing levels, LRC surroundings',
  'limits':'Oblique image cannot establish precise pier spacing or bridge landfall Z'},
 {'id':'P03-OTHER','url':'https://admission.bnbu.edu.cn/info/1732/1481.htm','publisher':'BNBU Admissions',
  'applies_to':'another_waterfront_walkway','visible':'Timber promenade, metal pergola and landscape',
  'limits':'Not established as the SAME lake bridge; no canopy may be transferred'},
 {'id':'RLP-LINKS','url':'https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/','publisher':'Ronald Lu & Partners',
  'applies_to':'V52_link_bridge_typology','visible':'Suspended, offset connecting bridges and stairs, with external balconies at differing levels',
  'limits':'Does not establish windows on any identified V52 mesh'},
 {'id':'RLP-LRC','url':'https://www.sohu.com/a/246378126_803109','publisher':'RLP architecture article',
  'applies_to':'LRC building only','visible':'Glazed LRC elevated volume, shading blades, lake-facing stepped spaces',
  'limits':'Glazing on a building is not automatically glazing on a bridge'},
 {'id':'RLP-PHOTO','url':'https://architizer.com/projects/beijing-normal-university-hong-kong-baptist-university-united-international-college/','publisher':'RLP/Architizer',
  'applies_to':'academic_architecture_not_bridge_ID','visible':'Academic glazed facades and balcony connections',
  'limits':'No individual bridge window measurement or facade camera registration'},
 {'id':'T2-VIEW','url':'https://mpro.bnbu.edu.cn/info/1086/4347.htm','publisher':'BNBU',
  'applies_to':'T2 building typology','visible':'Teaching complex frontage, gallery and ground connection',
  'limits':'No surveyed T2-to-T1/T3 door or bridge glass subdivision'},
 {'id':'LRC-NEWS','url':'https://www.bnbu.edu.cn/en/info/1077/2974.htm','publisher':'BNBU',
  'applies_to':'LRC building only','visible':'Library glazed walls and lake views',
  'limits':'Building glass differs from bridge glass'},
 {'id':'720YUN','url':'https://www.720yun.com/t/gapjawo88mt6wm27i9?pano_id=9hDEsEqYJ66W0pX3',
  'publisher':'720yun scene directory','applies_to':'candidate_registration_only',
  'visible':'Scene directory lists lake, T1–T8 and campus aerial viewpoints',
  'limits':'Only scene labels verified; not pixel registered; no physical geometry allowed'}
]

def glb_pack(doc,binary):
    doc['buffers']=[{'byteLength':len(binary)}]
    js=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    js+=b' '*(-len(js)%4)
    binary+=b'\0'*(-len(binary)%4)
    payload=struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    return b'glTF'+struct.pack('<II',2,len(payload)+12)+payload

def unpack_glb(data):
    assert data[:4]==b'glTF' and struct.unpack_from('<II',data,4)==(2,len(data))
    size,tag=struct.unpack_from('<I4s',data,12)
    assert tag==b'JSON'
    doc=json.loads(data[20:20+size]);p=20+size
    n,t=struct.unpack_from('<I4s',data,p);assert t==b'BIN\0'
    return doc,data[p+8:p+8+n]

def infill(rail):
    assert rail['role']=='DISPLAY_ONLY_NO_METRIC_GEOMETRY'
    assert rail['existing_deck_node']==DECK
    line=np.asarray(rail['railing_xy_polylines_local'][0],dtype=np.float64)
    assert line.shape==(340,3) and np.allclose(line[:,2],.91,atol=.001)
    split=int(np.argmax(line[:,0]));assert 165<=split<=175
    # Two long side polylines from the source boundary, not a closed glass box.
    sides=[line[:split+1],line[split:][::-1]]
    vertices=[];index=[]
    for side in sides:
        for a,b in zip(side[:-1],side[1:]):
            if np.linalg.norm(a[:2]-b[:2])<.05:continue
            k=len(vertices)
            vertices.extend(((a[0],a[1],a[2]+.10),(b[0],b[1],b[2]+.10),
                             (b[0],b[1],b[2]+.80),(a[0],a[1],a[2]+.80)))
            index.extend((k,k+1,k+2,k,k+2,k+3))
    v=np.asarray(vertices,dtype='<f4')
    ix=np.asarray(index,dtype='<u4')
    assert len(v)==1356 and len(ix)==2034
    vb=v.tobytes();ib=ix.tobytes()
    doc={
      'asset':{'version':'2.0','generator':'BNBU v75 photographic TYPOLOGY glass infill'},
      'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(vb),'target':34962},
        {'buffer':0,'byteOffset':len(vb),'byteLength':len(ib),'target':34963}],
      'accessors':[
        {'bufferView':0,'componentType':5126,'count':len(v),'type':'VEC3',
         'min':v.min(axis=0).astype(float).tolist(),'max':v.max(axis=0).astype(float).tolist()},
        {'bufferView':1,'componentType':5125,'count':len(ix),'type':'SCALAR','min':[0],'max':[int(ix.max())]}],
      'materials':[{'name':'illustrative_transparent_infill_not_surveyed',
       'pbrMetallicRoughness':{'baseColorFactor':[.48,.78,.86,.31],'roughnessFactor':.15,'metallicFactor':0},
       'alphaMode':'BLEND','doubleSided':True}],
      'meshes':[{'name':NODE,'primitives':[{'attributes':{'POSITION':0},'indices':1,'material':0}],
        'extras':{'source_boundary_points':340,'render_subdivisions_not_panes':339,
                  'bird_glass_exposure_eligible':False,'panes_measured':False,'surveyed':False}}],
      'nodes':[{'name':NODE,'mesh':0,'extras':{'type':'glass_balustrade_visual_only','source':DECK,
            'not_a_measured_window_or_bridge_facade':True}}],
      'scenes':[{'nodes':[0]}],'scene':0,
      'extras':{'source':'v70 derived lakefront railing contour, not observed panel geometry',
        'side_only':True,'glass_height_above_deck_illustration':[.10,.80],
        'scientific_glazing_area':None,'scientific_collision_denominator':False}}
    out=glb_pack(doc,vb+ib)
    check,_=unpack_glb(out);assert check['accessors'][0]['count']==1356
    GLASS.write_bytes(out)
    return {'glass_strip_sides':2,'railing_source_points':340,'tessellation_quads_not_real_panes':339,
        'triangles':678,'glazing_height_profile_model_units':[.10,.80],
        'glass_panel_count_verified':None,'real_glass_surface_area_verified':None,
        'excluded_from_bird_risk_geometry':True,
        'source_v70_sha256':sha_file(RAILS),'new_glb_sha256':hashlib.sha256(out).hexdigest()}

def bridge_inventory(surface):
    out=[]
    for num,buildings in BUILDINGS.items():
        name=next(x for x in surface.nodes if x.startswith(PREFIX+num+'_'))
        poly=surface.footprint(name)
        if poly.geom_type=='MultiPolygon':poly=max(poly.geoms,key=lambda p:p.area)
        assert poly.geom_type=='Polygon' and poly.is_valid
        v=surface.triangles(name).reshape(-1,3)
        rect=np.asarray(poly.minimum_rotated_rectangle.exterior.coords)[:4]
        a,b=rect[1]-rect[0],rect[2]-rect[1]
        axis=a if np.linalg.norm(a)>np.linalg.norm(b) else b
        axis/=np.linalg.norm(axis)
        boundary=np.asarray(poly.exterior.coords)
        along=boundary@axis
        envelopes={}
        for building in buildings:
            wall=surface.triangles('V40_MAIN_'+building+'_FACADE_AND_SIDEWALLS').reshape(-1,3)
            envelopes[building]=box(float(wall[:,0].min()+758940),float(wall[:,1].min()+2474080),
                                    float(wall[:,0].max()+758940),float(wall[:,1].max()+2474080))
        ends=[]
        for label,value in [('end_A',along.min()),('end_B',along.max())]:
            hits=boundary[abs(along-value)<.35]
            if not len(hits):hits=boundary[[int(np.argmin(abs(along-value)))]]
            xy=.985*hits.mean(axis=0)+.015*np.asarray(poly.centroid.coords[0])
            pt=Point(float(xy[0]),float(xy[1]))
            h=surface.local_top(name,pt)
            distances=sorted((round(pt.distance(geo),5),key) for key,geo in envelopes.items())
            assert distances[1][0]>distances[0][0]+1,(name,distances)
            ends.append({'end':label,'linked_building_candidate':distances[0][1],
                'building_candidate_method':'closest 2D inherited V40 building envelope (NOT door survey)',
                'other_building_bbox_plan_gap_model_units':distances[1][0],
                'model_utm_xy':[round(float(x),4) for x in xy],
                'glb_local_xyz':[round(float(xy[0]-758940),4),round(float(xy[1]-2474080),4),round(h['z'],4)],
                'model_top_height_m':round(h['z'],4),'surface_covered':bool(h['covered']),
                'photo_registered':False,'threshold_passable_verified':False,'door_or_transition_measured':False})
        out.append({
          'id':'V52_'+num,'node':name,'type':'elevated_academic_link_slab',
          'adjacent_academic_blocks_model_inference':buildings,
          'geometry_source':'v71 inherited GLB mesh','source_vertex_count':int(len(np.unique(v.round(4),axis=0))),
          'plan_area_model_sq_units':round(poly.area,3),
          'bbox_model_utm_xy':[round(float(x),3) for x in poly.bounds],
          'local_source_height_range_m':[round(float(v[:,2].min()),3),round(float(v[:,2].max()),3)],
          'local_surface_varies':bool(np.ptp(v[:,2])>.5),
          'endpoints':ends,
          'components':[
           {'name':'slab_and_soffit','status':'SOURCE_GEOMETRY_PRESENT'},
           {'name':'bridge_window_or_glazing','status':'USER_REPORT_UNLOCATED_NOT_MESHED'},
           {'name':'mullions_sills','status':'UNMEASURED_NOT_MODELED'},
           {'name':'roof_or_canopy','status':'PHOTO_NOT_REGISTERED'},
           {'name':'supports','status':'PHOTO_NOT_REGISTERED'},
           {'name':'both_door_thresholds','status':'UNVERIFIED_CONNECTIVITY'}],
          'surveyed':False,'eligible_bird_glass_denominator':False,
          'glazed_facade_mesh_created':False,
          'endpoint_assignment_revalidated_from_source_building_envelopes':True,
          'first_priority':'match two photogrammetrically controlled ends and glass type before solid edits'
        })
    return out

def build():
    before=sha_file(GLB)
    surface=Surface()
    rail=json.loads(RAILS.read_text(encoding='utf8'))
    glass=infill(rail)
    upper=bridge_inventory(surface)
    support=sorted(n for n in surface.nodes if n.startswith('V60_P1_EASTLAKE_BOARDWALK_PAIRED_PIER_'))
    cross=sorted(n for n in surface.nodes if n.startswith('V60_P1_EASTLAKE_BOARDWALK_OPAQUE_UNDERDECK_CROSSBEAM_'))
    assert len(upper)==6 and len(support)==len(cross)==13
    assert all(len(x['endpoints'])==2 for x in upper)
    atlas={
      'version':'v75','project':'BNBU Zhuhai inherited campus, NOT surveyed',
      'source_glb_sha256_before_and_after':before,'source_glb_modified':False,
      'glazing_claim_scope':'V60 transparent railing infill TYPE; V52 bridge-window IDs not photo registered',
      'system_count':7,'academic_elevated_bridge_count':6,
      'v52_elevated_academic_bridges':upper,
      'v60_lakefront_boardwalk':{
        'node':DECK,'type':'open_lakefront_footbridge_with_transparent_balustrade_type',
        'source_railing_xy_points':340,'source_pier_model_count':13,
        'source_opaque_crossbeam_model_count':13,'source_pier_names':support,
        'component_status':[
          {'name':'existing_deck_water_crossing','status':'SOURCE_GLTF_INHERITED_NOT_SURVEYED'},
          {'name':'pier_crossbeam_groups','status':'SOURCE_MODEL_NOT_ASBUILT'},
          {'name':'metal_railing_reference','status':'V70_MODEL_ANCHORED_APPROX'},
          {'name':'transparent_infill','status':'V75_PHOTO_TYPE_SUPPORTED_VISUAL_ONLY'},
          {'name':'real_pane_spacing_height','status':'NOT_MEASURED'},
          {'name':'eastern_bank_ramp_threshold','status':'V54_NEAR_MODEL_HEIGHT_UNVERIFIED'},
          {'name':'western_LRC_terrace_landing','status':'SOURCE_Z_GAP_0_64_UNRESOLVED'}],
        'actual_glazing_extent_measured':False,'new_glass_infill_rendered_separately':True,
        'glass_denominator_eligible':False
      },'v75_glass_infill':glass,'photo_and_design_source_register':PHOTOS,
      'source_photographs_copied_to_package':False,
      'geometric_priorities':[
        'V60 west-to-V61 terrace source local Z mismatch approx .64; do not fake ramp',
        'V61-to-WALK_045 source local Z mismatch approx .24; measure first',
        'V60 east-to-V54 ramp local Z delta approx .068; check exact seam',
        'V54 ramp-to-WALK_044 local delta approx .049; do not flatten ramp',
        'V52 six bridges yield 12 separate building/threshold interfaces requiring registration',
        'V52_03 slope: two local heights differ approx .58; do not flatten',
        'V52 window heights/frames/roof cannot be reconstructed from unrelated LRC glazing'],
      'gates':{'scientific_mesh_modified':False,'bird_collision_input_added':False,
        'infer_window_count':False,'assume_V52_glazing':False,'surveyor_certified':False,
        'photo_type_can_support_display':True},
      'v74_junction_hotspot_count_preserved':47
    }
    assert sha_file(GLB)==before
    ATLAS.write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return atlas

if __name__=='__main__':
    x=build()
    print(json.dumps({'seven_bridge_systems':x['system_count'],'glb_bytes':GLASS.stat().st_size,
      'source_piers':x['v60_lakefront_boardwalk']['source_pier_model_count'],
      'source_rail_points':x['v75_glass_infill']['railing_source_points']},indent=2))
