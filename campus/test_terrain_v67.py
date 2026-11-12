"""Independent source-traceable DSM reference tests with an artificial HGT fixture.

The synthetic tile tests the parser/coordinates, NOT empirical terrain accuracy.
The GitHub Actions build downloads and validates actual ArduPilot/JAXA-derived tile.
"""
import io
import json
import math
import struct
import unittest
import zipfile

from pyproj import Transformer
from build_terrain_v67 import (
    HGT_NAME, _pack_glb, build_dsm, extract_hgt, grid_range,
    inherited_bbox, sample_hgt,
)


class TerrainV67(unittest.TestCase):
    def make_tile(self,n=31):
        values=[100+(i*2)+(j%17) for i in range(n) for j in range(n)]
        data=struct.pack('>'+str(n*n)+'h',*values)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr(HGT_NAME,data)
        return data,stream.getvalue()

    def test_zip_hgt_north_south_pixel_order_and_void(self):
        hgt,z=self.make_tile()
        self.assertEqual(extract_hgt(z,n=31),hgt)
        region=sample_hgt(hgt,(5,8,9,12),n=31)
        self.assertEqual(region[0][0],100+5*2+9)
        self.assertEqual(region[3][3],100+8*2+12)
        modified=bytearray(hgt)
        struct.pack_into('>h',modified,(6*31+10)*2,-32768)
        self.assertIsNone(sample_hgt(bytes(modified),(5,8,9,12),n=31)[1][1])

    def test_derived_real_coordinate_crs_and_contour(self):
        n=31
        hgt,_=self.make_tile(n)
        transformer=Transformer.from_crs('EPSG:4326','EPSG:32649',always_xy=True)
        bounds=(113.30,22.30,113.72,22.70)
        glb,geo,report=build_dsm(hgt,bounds,transformer,n=n,padding=0)
        self.assertTrue(glb.startswith(b'glTF'))
        self.assertEqual(struct.unpack_from('<I',glb,8)[0],len(glb))
        self.assertGreater(report['observed_vertices'],0)
        self.assertGreater(report['triangle_count'],0)
        self.assertTrue(report['raw_raster_elevation_max_m']>report['raw_raster_elevation_min_m'])
        self.assertFalse(report['is_bare_earth_dem'])
        self.assertFalse(report['is_campus_registered'])
        jlen,jtyp=struct.unpack_from('<I4s',glb,12)
        self.assertEqual(jtyp,b'JSON')
        g=json.loads(glb[20:20+jlen])
        vcount=report['observed_vertices']
        self.assertEqual(g['accessors'][0]['count'],vcount)
        self.assertEqual(g['meshes'][0]['primitives'][0]['mode'],4)
        self.assertTrue(g['asset']['extras']['not_bare_earth'])
        rawmin=min((100+row*2+col%17 for row in range(31) for col in range(31)))
        self.assertGreaterEqual(report['raw_raster_elevation_min_m'],rawmin)
        self.assertEqual(geo['type'],'FeatureCollection')
        self.assertGreater(report['contour_segment_count'],0)
        for f in geo['features']:
            self.assertEqual(f['properties']['source'],'ALOS_DERIVED_HGT')
            self.assertFalse(f['properties']['is_observed_contour'])

    def test_grid_clip_and_parent_data_invariants(self):
        self.assertEqual(grid_range((113.25,22.25,113.75,22.75),n=31,padding=0),
                         (7,23,7,23))
        with self.assertRaises(AssertionError):
            grid_range((111.5,18.2,119.2,33.0),n=31,padding=0)
        sample={'type':'FeatureCollection','features':[{'geometry':{'type':'Point','coordinates':[113.513,22.357]}}]}
        with self.assertRaises(AssertionError): inherited_bbox(sample)


if __name__=='__main__':unittest.main()
