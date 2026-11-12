"""No browser screenshot implied: validate HTML module syntax and artifact references."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "viewer.html").read_text(encoding="utf-8")


class Modules(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_module = False
        self.modules = []
    def handle_starttag(self, tag, attrs):
        self.in_module = tag == "script" and ("type", "module") in attrs
        if self.in_module:
            self.modules.append("")
    def handle_data(self, data):
        if self.in_module:
            self.modules[-1] += data
    def handle_endtag(self, tag):
        if tag == "script":
            self.in_module = False


def verify():
    for name in ("BNBU_v66_SEMANTIC_Y_UP.glb", "BNBU_v66_RESOLVED_REFERENCES.geojson"):
        assert name in HTML, "viewer points to obsolete asset: " + name
    for keyword in ("terrain_unsurveyed", "water_unsurveyed", "shore_unsurveyed",
                    "vehicle_roads_unsurveyed", "pedestrian_paving_unsurveyed",
                    "elevated_boardwalk_unsurveyed", "ground_connectors_unsurveyed",
                    "architecture_opaque", "glass_proxies_unregistered", "stairs_unsurveyed"):
        assert 'data-part="' + keyword + '"' in HTML
    assert "点击" in HTML and "CTV" in HTML and "not_bridge" not in HTML
    p = Modules()
    p.feed(HTML)
    assert len(p.modules) == 1 and "GLTFLoader" in p.modules[0]
    if shutil.which("node"):
        with tempfile.TemporaryDirectory() as d:
            module = Path(d) / "viewer.mjs"
            module.write_text(p.modules[0], encoding="utf-8")
            subprocess.run(["node", "--check", str(module)], check=True)
    print("viewer v66 markup/assets/10 categories/module syntax: OK")


if __name__ == "__main__":
    verify()
