"""Losslessly decompress archived v64 campus geometry. Python standard library only."""
from pathlib import Path
import lzma
import hashlib

ROOT = Path(__file__).resolve().parent / 'assets'
NAMES = ['BNBU_v64_ACTIVE.glb', 'BNBU_v64_EDITABLE_GIS.gpkg',
         'BNBU_v64_ACTIVE.geojson', 'BNBU_v64_ACTIVE.kml',
         'BNBU_v64_CTV_EXCLUDED.geojson',
         'BNBU_v64_CTV_UNVERIFIED_GEOMETRY_DO_NOT_USE_AS_SURVEY.glb']
for name in NAMES:
    src = ROOT / (name + '.xz')
    content = lzma.decompress(src.read_bytes())
    if name.endswith('.glb'): assert content.startswith(b'glTF')
    if name.endswith('.gpkg'): assert content.startswith(b'SQLite format 3')
    (ROOT / name).write_bytes(content)
    print(name, len(content), hashlib.sha256(content).hexdigest())
