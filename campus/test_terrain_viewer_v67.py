"""Check independent observed-DSM HTML viewer has a parsable JavaScript module."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile

HTML = (Path(__file__).resolve().parent / 'terrain_reference.html').read_text(encoding='utf-8')


class JS(HTMLParser):
    def __init__(self):
        super().__init__();self.is_module=False;self.parts=[]
    def handle_starttag(self,tag,attrs):
        self.is_module=tag=='script' and ('type','module') in attrs
        if self.is_module:self.parts.append('')
    def handle_data(self,s):
        if self.is_module:self.parts[-1]+=s
    def handle_endtag(self,tag):
        if tag=='script':self.is_module=False


def verify():
    required=[
        'BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb',
        'BNBU_v67_TERRAIN_SOURCE_AND_LIMITS.json',
        'BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson',
        'JAXA', 'DSM', '不允许', './viewer.html',
    ]
    for key in required:assert key in HTML, key
    parsed=JS();parsed.feed(HTML)
    assert len(parsed.parts)==1
    if shutil.which('node'):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'terrain.mjs';p.write_text(parsed.parts[0]);
            subprocess.run(['node','--check',str(p)],check=True)
    print('v67 independent DSM viewer, static provenance, GLB/GIS paths, JS syntax OK')


if __name__=='__main__':verify()
