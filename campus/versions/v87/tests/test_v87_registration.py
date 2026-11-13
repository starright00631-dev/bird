"""Historical v87 ICP integration checks are not repository-only unit tests.

They require the complete v84 physical-master GLB and generated registration
fixtures, which are shipped only in the full research ZIP.  The lightweight
repository CI deliberately tests the deterministic OSM geometry acquisition
and identity gates in test_fetch_osm_full_geometry_v87.py instead.
"""
import unittest


@unittest.skip("Requires full v84/v87 research assets; run from the complete research ZIP")
class TestV87RegistrationIntegration(unittest.TestCase):
    def test_requires_full_research_package(self):
        self.fail("This integration test must be run from the complete research ZIP")