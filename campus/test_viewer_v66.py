"""Validate that the obsolete v66 GitHub file no longer loads missing data.

The historical v66 model is still tested elsewhere. The public repository
entrypoint now redirects to the verified self-contained v76 Pages build.
"""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import shutil
import tempfile

ROOT=Path(__file__).resolve().parent
HTML=(ROOT/"viewer.html").read_text(encoding="utf-8")
TARGET="https://starright00631-dev.github.io/bird/"

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__();self.current=False;self.scripts=[]
    def handle_starttag(self,tag,attrs):
        self.current=tag=="script"
        if self.current:self.scripts.append("")
    def handle_data(self,data):
        if self.current:self.scripts[-1]+=data
    def handle_endtag(self,tag):
        if tag=="script":self.current=False

def verify():
    assert TARGET in HTML
    assert 'http-equiv="refresh"' in HTML
    assert 'rel="canonical"' in HTML
    assert "location.replace" in HTML
    assert 'actions/workflows/campus-package.yml' in HTML
    for obsolete in ("BNBU_v66_SEMANTIC_Y_UP.glb",
                     "BNBU_v66_RESOLVED_REFERENCES.geojson",
                     "cdn.jsdelivr.net","unpkg.com","fetch('./generated/"):
        assert obsolete not in HTML,"legacy viewer still fetches missing GitHub assets: "+obsolete
    parser=Scripts();parser.feed(HTML)
    assert len(parser.scripts)==1 and "location.replace" in parser.scripts[0]
    if shutil.which("node"):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"redirect.js";f.write_text(parser.scripts[0],encoding="utf-8")
            subprocess.run(["node","--check",str(f)],check=True)
    print("Legacy v66 file is a no-CDN redirect to verified v76 Pages viewer: OK")

if __name__=="__main__":verify()
