"""Evidence-constrained campus junction comparisons from immutable source GLB/GIS.

Export all 1,540 road/footpath pairs plus detailed 3D local-surface
comparisons for nearby relationships and the 11 previously documented
lakefront pairs. Never merge or create inferred physical connections.
"""
from __future__ import annotations
import collections
import functools
import hashlib
import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, mapping, shape
from shapely.ops import nearest_points, transform, unary_union
from shapely.affinity import translate
from shapely.geometry import Polygon

from build_connection_v71 import unpack

HERE = Path(__file__).resolve().parent
ROOT = HERE if (HERE/'generated').exists() else HERE.parent
DATA = ROOT/'generated'
GLB = DATA/'BNBU_v71_CONNECTED_LAKEFRONT.glb'
GIS = DATA/'BNBU_v66_RESOLVED_REFERENCES.geojson'
OLD = DATA/'BNBU_v71_JUNCTION_AUDIT.geojson'
PAIR_OUTPUT = DATA/'BNBU_v74_ALL_ROAD_WALK_PAIRWISE.json'
HOTSPOT_OUTPUT = DATA/'BNBU_v74_LOCAL_3D_JUNCTION_HOTSPOTS.geojson'
REPORT_OUTPUT = DATA/'BNBU_v74_CONNECTION_RESEARCH_SUMMARY.json'
OFFSET = (758940., 2474080.)
UTM = Transformer.from_crs('EPSG:4326','EPSG:32649',always_xy=True).transform
WGS = Transformer.from_crs('EPSG:32649','EPSG:4326',always_xy=True).transform


def sha_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_features():
    features = json.loads(GIS.read_text(encoding='utf-8'))['features']
    assert len(features)==522
    geometry = {}
    for f in features:
        name = f['properties'].get('render_model_node') or f['properties'].get('model_node')
        if not name or f['geometry']['type'] not in ('Polygon','MultiPolygon'):
            continue
        polygon = transform(UTM,shape(f['geometry']))
        if not polygon.is_valid:polygon=polygon.buffer(0)
        if name not in geometry or polygon.area > geometry[name].area:
            geometry[name] = polygon
    return geometry


class Surface:
    def __init__(self):
        self.doc,self.binary = unpack(GLB.read_bytes())
        self.nodes = {n['name']:n for n in self.doc['nodes'] if 'mesh' in n and 'name' in n}
        assert len(self.doc['meshes'])==1379

    def accessor(self,number):
        acc=self.doc['accessors'][number]
        view=self.doc['bufferViews'][acc['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[acc['componentType']]
        width={'SCALAR':1,'VEC3':3}[acc['type']]
        start=view.get('byteOffset',0)+acc.get('byteOffset',0)
        # The model's vertex buffers are tightly packed; verify per-view stride.
        assert view.get('byteStride',width*np.dtype(dtype).itemsize)==width*np.dtype(dtype).itemsize
        ar=np.frombuffer(self.binary,dtype=np.dtype(dtype),count=acc['count']*width,offset=start)
        return ar.reshape(-1,width) if width>1 else ar

    @functools.lru_cache(maxsize=128)
    def triangles(self,node):
        prim=self.doc['meshes'][self.nodes[node]['mesh']]['primitives'][0]
        v=self.accessor(prim['attributes']['POSITION'])
        indices=self.accessor(prim['indices'])
        assert indices.size % 3==0
        return v[indices.reshape(-1,3)]

    def local_top(self,node,point,tolerance=.055):
        """Barycentric local visible surface z, not whole-mesh Z max.

        For a point outside source triangulation return a fallback that is
        explicitly labelled *uncovered*, never certified as a contact.
        """
        tris=self.triangles(node)
        x,y=point.x-OFFSET[0],point.y-OFFSET[1]
        a,b,c=tris[:,0,:2],tris[:,1,:2],tris[:,2,:2]
        v0=b-a;v1=c-a;v2=np.array([x,y])-a
        den=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0]
        valid=np.abs(den)>1e-7
        w1=np.divide(v2[:,0]*v1[:,1]-v2[:,1]*v1[:,0],den,out=np.zeros_like(den),where=valid)
        w2=np.divide(v0[:,0]*v2[:,1]-v0[:,1]*v2[:,0],den,out=np.zeros_like(den),where=valid)
        w0=1-w1-w2
        cover=valid&(w0>=-tolerance)&(w1>=-tolerance)&(w2>=-tolerance)
        if np.any(cover):
            zs=w0*tris[:,0,2]+w1*tris[:,1,2]+w2*tris[:,2,2]
            return dict(z=float(max(zs[cover])),method='barycentric_triangle_surface',covered=True)
        verts=tris.reshape(-1,3)
        i=int(np.argmin(np.linalg.norm(verts[:,:2]-np.array([x,y]),axis=1)))
        dist=float(np.linalg.norm(verts[i,:2]-np.array([x,y])))
        return dict(z=float(verts[i,2]),method='uncovered_nearest_vertex',covered=False,distance_to_vertex=round(dist,5))

    def global_max(self,node):
        return float(np.max(self.triangles(node)[:,:,2]))

    def footprint(self,node):
        """Union of model triangle projections, preserving the actual XY shape."""
        surfaces=[]
        for tri in self.triangles(node):
            poly=Polygon([(float(v[0]),float(v[1])) for v in tri])
            if poly.is_valid and poly.area>1e-7:surfaces.append(poly)
        assert surfaces,(node,'No projected face polygon')
        g=unary_union(surfaces)
        assert g.is_valid and g.area>0
        return translate(g,xoff=OFFSET[0],yoff=OFFSET[1])


def classify(gap,overlap,lake_intersection,a,b,source_class='walk_road'):
    if source_class=='v71':return 'previously_audited_local_surface_recheck'
    if source_class=='upper_bridge_vs_ground':return 'overhead_grade_separation_not_walkable_at_grade'
    if overlap>=10: return 'overlapping_carriageway_footpath_verify_actual_surface_split'
    if lake_intersection>0.01:return 'potential_water_barrier_no_connection_allowed'
    if gap<=0.0001:return 'touch_or_overlap_not_accessibility_proof'
    if gap<=3:return 'short_source_model_gap_requires_photo_registration'
    if gap<=8:return 'medium_source_model_gap_requires_photo_registration'
    if gap<=15:return 'long_source_model_gap_no_inferred_geometry'
    return 'remote_no_proximity_claim'


def build():
    geometries=load_features()
    surface=Surface()
    all_road_walk=sorted(n for n in geometries if n.startswith(('WALK_','ROAD_')) and len(n.split('_'))==2)
    assert len(all_road_walk)==56
    upper_bridges=sorted(n for n in surface.nodes if n.startswith('V52_LEVEL2_PEDESTRIAN_CONNECTION_'))
    assert len(upper_bridges)==6
    for name in upper_bridges:
        assert surface.global_max(name)>3.5
        geometries[name]=surface.footprint(name)
    water=geometries['LAKE_00']
    others=[geometries[n] for n in sorted(geometries) if n.startswith('LAKE_') and n!='LAKE_00']
    counters=collections.Counter()
    pairwise=[]
    hot=[]
    def measure(a,b,tag,existing=None):
        A,B=geometries[a],geometries[b]
        dist=A.distance(B);overlap=A.intersection(B)
        p,q=nearest_points(A,B)
        if overlap.area>1e-4:
            p=q=overlap.representative_point()
        line=LineString([(p.x,p.y),(q.x,q.y)])
        cross_buf=line.buffer(.4)
        water_area=float(cross_buf.intersection(water).area)+sum(cross_buf.intersection(w).area for w in others)
        surfA=surface.local_top(a,p);surfB=surface.local_top(b,q)
        max_z_a=surface.global_max(a);max_z_b=surface.global_max(b)
        gap3=float(np.linalg.norm([p.x-q.x,p.y-q.y,surfA['z']-surfB['z']]))
        style=classify(dist,overlap.area,water_area,a,b,tag)
        localp=[[round(p.x-OFFSET[0],5),round(p.y-OFFSET[1],5),round(surfA['z'],5)],
                [round(q.x-OFFSET[0],5),round(q.y-OFFSET[1],5),round(surfB['z'],5)]]
        props=dict(source_a=a,source_b=b,source_type=tag,status=style,
          source_geometry='inherited_v66_GIS_and_v71_GLB_no_new_physical_mesh',
          model_plan_gap_m=round(dist,5),model_plan_overlap_m2=round(overlap.area,4),
          model_water_buffer_overlap_m2=round(water_area,4),
          local_z_a=round(surfA['z'],5),local_z_b=round(surfB['z'],5),
          local_top_delta_m=round(abs(surfA['z']-surfB['z']),5),
          whole_mesh_top_delta_m=round(abs(max_z_a-max_z_b),5),
          local_surface_method_a=surfA['method'],local_surface_method_b=surfB['method'],
          both_projected_to_source_triangles=bool(surfA['covered'] and surfB['covered']),
          model_3d_point_distance=round(gap3,5),
          local_points_z_up=localp,
          original_footprints_preserved=True,is_surveyed=False,
          navigation_connection_proven=False,do_not_extrude_as_walkway=True,
          requires_photo_or_survey_registration=True)
        if existing:props['previous_v71_status']=existing
        return props,{'type':'Feature','geometry':mapping(transform(WGS,line)),'properties':props}
    for i,a in enumerate(all_road_walk):
        for b in all_road_walk[i+1:]:
            A,B=geometries[a],geometries[b]
            dist=A.distance(B);ov=A.intersection(B).area
            rec=dict(source_a=a,source_b=b,model_plan_gap_m=round(dist,5),model_plan_overlap_m2=round(ov,4),
                model_top_z_a=round(surface.global_max(a),4),model_top_z_b=round(surface.global_max(b),4))
            pairwise.append(rec)
            counters['all_pairs']+=1
            for t,label in [(1,'within_1'),(3,'within_3'),(8,'within_8'),(15,'within_15')]:
                if dist<=t:counters[label]+=1
            if ov>=10:counters['overlap_over_10m2']+=1
            if dist<=15:
                props,feature=measure(a,b,'walk_road')
                hot.append(feature)
    upper_pairs=[]
    upper_selected=0
    for a in upper_bridges:
        for b in all_road_walk:
            A,B=geometries[a],geometries[b]
            gap=A.distance(B);overlap=A.intersection(B).area
            upper_pairs.append(dict(source_a=a,source_b=b,model_plan_gap_m=round(gap,5),
                model_plan_overlap_m2=round(overlap,5),source_role='level_2_vs_at_grade'))
            counters['upper_vs_ground_pairwise']+=1
            if gap<=10:
                upper_selected+=1
                props,feature=measure(a,b,'upper_bridge_vs_ground')
                assert props['local_top_delta_m']>3.0,(a,b,props['local_top_delta_m'])
                hot.append(feature)
    assert len(upper_pairs)==336
    v71=json.loads(OLD.read_text())
    assert len(v71['features'])==11
    for f in v71['features']:
        p=f['properties'];a=p['source_node_a'];b=p['source_node_b']
        props,feature=measure(a,b,'v71',p['junction_status'])
        # Source GLB/GIS can be stale; never force a claim for unknown geometries.
        feature['properties']['historical_v71_gap_m']=p['model_plan_gap_m']
        hot.append(feature)
    # Named critical records must be present and correct in local-surface audit.
    def find(a,b):
        return next(x['properties'] for x in hot if x['properties']['source_a']==a and x['properties']['source_b']==b)
    from build_connection_v71 import DECK,RAMP,S
    west=find(DECK,S[2]);east=find(RAMP,'WALK_044');deckramp=find(DECK,RAMP)
    assert abs(west['local_top_delta_m']-.64)<.01
    assert east['local_top_delta_m']<.15 and deckramp['local_top_delta_m']<.15
    assert len(pairwise)==1540 and counters['within_15']==30
    assert all(x['properties']['is_surveyed'] is False and x['properties']['do_not_extrude_as_walkway'] for x in hot)
    summary=dict(version='v74',purpose='Junction-specific 2D topology + local barycentric GLB surface heights',
       all_road_walk_features=56,total_pairwise_comparisons=len(pairwise),selected_nearby_comparisons=counters['within_15'],
       upper_level_cross_checks=len(upper_pairs),upper_level_within_10_model_m=upper_selected,
       independently_preserved_v71_junctions=11,display_hotspot_count=len(hot),
       count_by_type=dict(counters),
       critical_local_results={'west_deck_to_prom_top_delta':west['local_top_delta_m'],
         'east_deck_to_ramp_top_delta':deckramp['local_top_delta_m'],
         'east_ramp_to_walk044_top_delta':east['local_top_delta_m']},
       inputs={'GIS_v66_sha256':sha_file(GIS),'GLB_v71_sha256':sha_file(GLB),'historic_v71_audit_sha256':sha_file(OLD)},
       photo_evidence_is_register_not_photogrammetry=True,
       campus_3d_meshes_edited=0,newsurveyed_links=0,
       limitations=['V44 inherited WALK_ polygons are not field surveys',
        'Model z is relative, not geodetic altitude',
        'Triangle-surface sample at overlap is not proof of walkable route',
        'Older GLB model may miss stairs/curbs/thresholds',
        'No revised physical bridge, roadway, shoreline, ramp or measured glass created'])
    PAIR_OUTPUT.write_text(json.dumps(dict(version='v74',comparison_count=len(pairwise),pairs=pairwise,
        upper_level_comparison_count=len(upper_pairs),upper_level_pairs=upper_pairs),ensure_ascii=False,separators=(',',':')))
    HOTSPOT_OUTPUT.write_text(json.dumps(dict(type='FeatureCollection',features=hot,meta=summary),ensure_ascii=False,separators=(',',':')))
    REPORT_OUTPUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':build()