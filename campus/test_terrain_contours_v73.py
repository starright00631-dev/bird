"""v73: reproducibility and provenance tests for DSM-only 3D contours."""
import hashlib,json,unittest
import numpy as np
from build_terrain_contours_v73 import (
    INPUT,OUTPUT,CONTOURS,REPORT,NAME,Z_LIFT,TO_UTM,
    EAST,NORTH,COUNT,unpack,build,
)

class TerrainContour73(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=build()

    def test_source_geometry_byte_for_byte(self):
        before,bin0=unpack(INPUT.read_bytes())
        after,bin1=unpack(OUTPUT.read_bytes())
        self.assertEqual(bin0,bin1[:len(bin0)])
        self.assertEqual(before["meshes"],after["meshes"][:1])
        self.assertEqual(before["bufferViews"],after["bufferViews"][:3])
        self.assertEqual(before["accessors"],after["accessors"][:3])
        self.assertEqual(before["materials"],after["materials"][:1])
        self.assertEqual(before["nodes"][0],after["nodes"][0])
        self.assertEqual(len(after["meshes"]),2)
        self.assertEqual(after["meshes"][1]["primitives"][0]["mode"],1)
        self.assertEqual(after["nodes"][-1]["name"],NAME)
        self.assertFalse(after["nodes"][-1]["extras"]["vertical_registered_to_campus"])

    def test_all_contours_are_projected_and_height_labelled(self):
        features=json.loads(CONTOURS.read_text())["features"]
        out,binary=unpack(OUTPUT.read_bytes())
        v=out["bufferViews"][-2]
        xyz=np.frombuffer(binary,dtype="<f4",count=COUNT*2*3,offset=v["byteOffset"]).reshape(-1,3)
        self.assertEqual(xyz.shape,(7474,3))
        self.assertTrue(np.isfinite(xyz).all())
        for k in (0,11,100,898,1823,3736):
            f=features[k]
            h=f["properties"]["elevation_m_interpolated"]
            for j,(lon,lat) in enumerate(f["geometry"]["coordinates"]):
                e,n=TO_UTM.transform(lon,lat)
                np.testing.assert_allclose(xyz[2*k+j],[e-EAST,h+Z_LIFT,-(n-NORTH)],atol=.0002,rtol=0)
        self.assertEqual(self.report["contour_segment_count"],3737)
        self.assertEqual(self.report["contour_elevations_m"],list(range(10,111,10)))

    def test_reproduction_and_no_fabricated_features(self):
        old_glb=OUTPUT.read_bytes()
        old_report=REPORT.read_bytes()
        build()
        self.assertEqual(old_glb,OUTPUT.read_bytes())
        self.assertEqual(old_report,REPORT.read_bytes())
        for k in ("new_campus_buildings","new_campus_lakes","new_campus_roads"):
            self.assertEqual(self.report[k],0)
        self.assertTrue(self.report["binary_source_unchanged"])

if __name__=="__main__":
    unittest.main()
