"""Independent observed DSM reference from ALOS-derived ArduPilot HGT N22E113.

This **does not** change the v64-v66 BNBU campus geometry or claim bare-earth DEM.
ArduPilot's directory named SRTM1 currently serves JAXA ALOS-derived, not
NASA SRTM, ~30 m digital *surface* model. The 2022-hosted tile is not
necessarily JAXA's latest (2024) v4.1 update. Source URL is recorded.

Coordinates:
    HGT: lon/lat grid WGS84, elevations from distributed source (nominal MSL);
    model horizontal: EPSG:32649 minus X=758940, northing=2474080;
    GLB reference Y-up: (easting - 758940, raw DSM height, -(northing-2474080)).
The DSM GLB is a **separate inspection scene**, never overlaid directly with
building model-relative elevations: vertical references are unregistered.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import struct
import urllib.request
import zipfile
from pathlib import Path
from statistics import median

SOURCE = "https://terrain.ardupilot.org/SRTM1/N22E113.hgt.zip"
HGT_NAME = "N22E113.hgt"
HGT_POINTS = 3601
LAT_SOUTH, LON_WEST = 22, 113
ROOT = Path(__file__).resolve().parent
SOURCE_GEOJSON = ROOT / "assets" / "BNBU_v64_ACTIVE.geojson.xz"
OUT = ROOT / "generated"
UTM_EAST_OFFSET = 758940
UTM_NORTH_OFFSET = 2474080
VOID = -32768
PADDING_DEG = 0.003
CONTOUR_INTERVAL_M = 10


def _coords(geometry):
    def recurse(v):
        if isinstance(v, list) and len(v) >= 2 and all(isinstance(x, (int, float)) for x in v[:2]):
            yield float(v[0]), float(v[1])
        elif isinstance(v, list):
            for child in v:
                yield from recurse(child)
    return recurse((geometry or {}).get("coordinates"))


def inherited_bbox(geojson: dict) -> tuple[float, float, float, float]:
    """Clipping bounds derive from the *unchanged* 522 GIS geometries."""
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 522, "Parent BNBU GIS source changed; re-audit scope"
    points = [p for f in geojson["features"] for p in _coords(f.get("geometry"))]
    assert len(points) > 1000
    minlon, maxlon = min(p[0] for p in points), max(p[0] for p in points)
    minlat, maxlat = min(p[1] for p in points), max(p[1] for p in points)
    assert 113.50 < minlon < maxlon < 113.53
    assert 22.34 < minlat < maxlat < 22.38
    return (minlon, minlat, maxlon, maxlat)


def grid_range(bbox: tuple[float, float, float, float], n: int = HGT_POINTS,
               padding: float = PADDING_DEG) -> tuple[int, int, int, int]:
    lonlo, latlo, lonhi, lathi = bbox
    # HGT rows start at the NORTH side of the whole degree; cols at WEST.
    west = math.floor((lonlo-padding-LON_WEST)*(n-1))
    east = math.ceil((lonhi+padding-LON_WEST)*(n-1))
    north = math.floor((LAT_SOUTH+1-lathi-padding)*(n-1))
    south = math.ceil((LAT_SOUTH+1-latlo+padding)*(n-1))
    assert 0 <= west < east < n and 0 <= north < south < n
    assert (east-west+1)*(south-north+1) < 100_000, "Unbounded raster extraction"
    return north, south, west, east


def extract_hgt(zip_bytes: bytes, n: int = HGT_POINTS) -> bytes:
    assert 100 < len(zip_bytes) < 35_000_000, "Unexpected ZIP size"
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        entries = [x for x in z.infolist() if not x.is_dir()]
        assert len(entries) == 1, "Expected a single HGT in tile archive"
        name = entries[0].filename.replace("\\", "/").split("/")[-1]
        assert name.lower() == HGT_NAME.lower(), name
        assert entries[0].file_size == 2*n*n, (entries[0].file_size, n)
        return z.read(entries[0])


def sample_hgt(hgt: bytes, bounds: tuple[int, int, int, int],
               n: int = HGT_POINTS):
    assert len(hgt) == 2*n*n
    r0, r1, c0, c1 = bounds
    assert 0 <= r0 < r1 < n and 0 <= c0 < c1 < n
    heights = []
    for row in range(r0, r1+1):
        line = []
        for col in range(c0, c1+1):
            value = struct.unpack_from(">h", hgt, (row*n+col)*2)[0]
            line.append(None if value <= VOID or value == -32767 else value)
        heights.append(line)
    return heights


def download_tile(url: str = SOURCE) -> bytes:
    if url != SOURCE:
        raise ValueError("Only the explicitly documented public source URL is allowed")
    req = urllib.request.Request(url, headers={"User-Agent": "BNBU-evidence-terrain/0.1"})
    with urllib.request.urlopen(req, timeout=45) as response:
        data = response.read(35_000_001)
    if len(data) > 35_000_000:
        raise ValueError("Unexpectedly large remote tile archive")
    return data


def _pack_glb(verts: list[tuple[float, float, float]], triangles: list[tuple[int,int,int]],
              colors: list[tuple[float, float, float]]) -> bytes:
    """Produces real binary glTF 2.0 triangle geometry with per-vertex color."""
    assert len(verts) == len(colors) and len(verts) > 12
    assert len(triangles) > 5
    pos = b"".join(struct.pack("<fff", *p) for p in verts)
    rgb = b"".join(struct.pack("<fff", *p) for p in colors)
    idx = b"".join(struct.pack("<III", *f) for f in triangles)
    # This mesh is flat-shaded by default; render material double-sided.
    buffer = pos + rgb + idx
    sizes = list(map(len, (pos, rgb, idx)))
    hvals = [p[1] for p in verts]
    xyz_min = [min(p[i] for p in verts) for i in range(3)]
    xyz_max = [max(p[i] for p in verts) for i in range(3)]
    doc = {
        "asset": {"version": "2.0", "generator": "BNBU v67 observed DSM reference",
                  "extras": {"source_url": SOURCE, "not_bare_earth": True,
                             "vertical_registered_to_campus": False,
                             "display_only": True}},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "AW3D30_DSM_REFERENCE_NOT_BARE_EARTH_UNREGISTERED", "mesh": 0,
                   "extras": {"surveyed_campus": False, "vertex_height": "raw HGT elevation",
                              "is_real_dsm_sample": True, "not_a_driveway_or_building": True}}],
        "meshes": [{"name": "ALOS_DSM_2022_ARdupilot_30M_GRID", "primitives": [
            {"attributes": {"POSITION": 0, "COLOR_0": 1}, "indices": 2, "material": 0, "mode": 4}]}],
        "materials": [{"name": "elevation_color_visualization_NOT_landcover",
                       "doubleSided": True, "pbrMetallicRoughness": {
                           "baseColorFactor": [1,1,1,1], "roughnessFactor": 1.0,
                           "metallicFactor": 0.0}}],
        "buffers": [{"byteLength": len(buffer)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": sizes[0], "target": 34962},
            {"buffer": 0, "byteOffset": sizes[0], "byteLength": sizes[1], "target": 34962},
            {"buffer": 0, "byteOffset": sizes[0]+sizes[1], "byteLength": sizes[2], "target": 34963}],
        "accessors": [
            {"bufferView": 0, "byteOffset": 0, "componentType": 5126, "count": len(verts),
             "type": "VEC3", "min": xyz_min, "max": xyz_max},
            {"bufferView": 1, "byteOffset": 0, "componentType": 5126, "count": len(colors),
             "type": "VEC3"},
            {"bufferView": 2, "byteOffset": 0, "componentType": 5125, "count": len(triangles)*3,
             "type": "SCALAR", "min": [0], "max": [len(verts)-1]}],
    }
    jsonblob = json.dumps(doc, separators=(",", ":")).encode()
    jsonblob += b" " * (-len(jsonblob)%4)
    buffer += b"\0" * (-len(buffer)%4)
    chunks = struct.pack("<I4s", len(jsonblob), b"JSON")+jsonblob
    chunks += struct.pack("<I4s", len(buffer), b"BIN\0")+buffer
    return b"glTF"+struct.pack("<II", 2, 12+len(chunks))+chunks


def build_dsm(hgt: bytes, bbox: tuple[float,float,float,float],
              transformer, n: int = HGT_POINTS, padding=PADDING_DEG) -> tuple[bytes, dict, dict]:
    """Each GLB vertex is at an actual integer HGT sample, no interpolation."""
    bounds = grid_range(bbox, n=n, padding=padding)
    r0,r1,c0,c1 = bounds
    sampled=sample_hgt(hgt,bounds,n)
    width, height = c1-c0+1, r1-r0+1
    verts=[]; ll=[]; elev=[]; valid=[]
    for ri in range(height):
        for ci in range(width):
            row,col=r0+ri,c0+ci
            lon=LON_WEST+col/(n-1)
            lat=LAT_SOUTH+1-row/(n-1)
            x,y=transformer.transform(lon,lat)
            raw=sampled[ri][ci]
            if raw is None:
                verts.append((float(x-UTM_EAST_OFFSET),0.,float(-(y-UTM_NORTH_OFFSET))))
                valid.append(False)
            else:
                verts.append((float(x-UTM_EAST_OFFSET),float(raw),float(-(y-UTM_NORTH_OFFSET))))
                valid.append(True);elev.append(raw)
            ll.append((lon,lat))
    assert len(elev)>=0.95*width*height, "DEM voids too extensive to use without gap repair"
    assert min(elev)>-1000 and max(elev)<4000, "Altitude out of plausible range; inspect datum/bytes"
    colors=[];lo,hi=min(elev),max(elev);span=max(hi-lo,1)
    for idx,(x,z,y) in enumerate(verts):
        if not valid[idx]:colors.append((.48,.48,.48));continue
        t=(z-lo)/span
        # elevation-themed continuous colors, NOT habitat class or canopy identification.
        colors.append((float(.19+.47*t),float(.47-.13*t),float(.30+.18*t)))
    triangles=[]
    for row in range(height-1):
        for col in range(width-1):
            a=row*width+col;b=a+1;c=a+width;d=c+1
            for f in ((a,c,b),(b,c,d)):
                if all(valid[i] for i in f):triangles.append(f)
    assert triangles
    geom=_pack_glb(verts,triangles,colors)
    # Derive visual contours by linear intersection on actual 30 m raster triangles.
    # This is interpolation between pixels, NOT additional surveyed contour points.
    levels=range(int(math.ceil(lo/CONTOUR_INTERVAL_M))*CONTOUR_INTERVAL_M,
                 int(math.floor(hi/CONTOUR_INTERVAL_M))*CONTOUR_INTERVAL_M+1,
                 CONTOUR_INTERVAL_M)
    features=[]
    for i,j,k in triangles:
        for level in levels:
            crossings=[]
            for a,b in ((i,j),(j,k),(k,i)):
                ha,hb=verts[a][1],verts[b][1]
                if (ha<level<=hb) or (hb<level<=ha):
                    factor=(level-ha)/(hb-ha)
                    p0,p1=ll[a],ll[b]
                    crossings.append([p0[0]+factor*(p1[0]-p0[0]),p0[1]+factor*(p1[1]-p0[1])])
            if len(crossings)==2:
                features.append({"type":"Feature","geometry":{"type":"LineString","coordinates":crossings},
                    "properties":{"elevation_m_interpolated":level,"source":"ALOS_DERIVED_HGT",
                    "is_observed_contour":False,"nominal_horizontal_sampling_m":30,
                    "vertical_alignment_to_bnbu":"unregistered"}})
    contour={"type":"FeatureCollection","name":"BNBU_v67_AW3D30_10m_interpolated_contours_NOT_survey",
             "features":features}
    manifest={"version":"v67-dsm-reference","source_title":"ArduPilot SRTM1 archive: ALOS-derived (~30 m) DSM, not NASA SRTM",
        "source_url":SOURCE,"source_archive_snapshot_utc":"2022-06-17 listed","latest_JAXA_v4_1":False,
        "bbox_derived_from":"522 original v64 GeoJSON features",
        "inherited_bbox_lon_lat":bbox,"clip_buffer_degrees":padding,
        "hgt_grid":"northwest-first, signed big-endian 16-bit, 1 arc-second",
        "hgt_window_rowcol":bounds,"grid_width":width,"grid_height":height,
        "observed_vertices":len(elev),"void_vertices":width*height-len(elev),
        "raw_raster_elevation_min_m":lo,"raw_raster_elevation_max_m":hi,
        "raster_elevation_median_m":median(elev),
        "triangle_count":len(triangles),"contour_segment_count":len(features),
        "sampled_hgt_window_sha256":hashlib.sha256(b"".join(struct.pack(">h",v if v is not None else VOID) for line in sampled for v in line)).hexdigest(),
        "terrain_glb_sha256":hashlib.sha256(geom).hexdigest(),
        "crs_horizontal":"WGS84 points transformed EPSG:32649 local offsets (758940,2474080)",
        "z_reference":"original HGT orthometric/nominal MSL; source geoid not independently verified",
        "is_bare_earth_dem":False,"is_campus_registered":False,
        "display_warning":"Absolute DSM heights do not match v66 model-relative vertical coordinates. Do not overlay, replace or align without vertical ground controls.",
        "contours":"10 m nominal isolines linearly interpolated across sampled 30 m triangular cells, not surveyed",
        "authorship":"Derived only from external DSM points and inherited GIS bounds; no invented buildings, lakeshores or driveways",
        "attribution":"ALOS World 3D - 30m (AW3D30), JAXA; terrain.ardupilot.org mirror; check both data-source terms before redistribution"}
    return geom,contour,manifest


def _read_base_geojson() -> tuple[dict,bytes]:
    import lzma
    uncompressed = ROOT / "assets" / "BNBU_v64_ACTIVE.geojson"
    if uncompressed.exists():
        data=uncompressed.read_bytes()
    else:
        data=lzma.decompress(SOURCE_GEOJSON.read_bytes())
    return json.loads(data),data


def build(out: Path = OUT, tile_zip: bytes | None = None) -> dict:
    try:
        from pyproj import Transformer
    except ImportError as e:
        raise RuntimeError("Install pyproj>=3.6; exact UTM conversion is required") from e
    source,basis=_read_base_geojson()
    bbox=inherited_bbox(source)
    payload=tile_zip if tile_zip is not None else download_tile()
    raw=extract_hgt(payload)
    transformer=Transformer.from_crs("EPSG:4326","EPSG:32649",always_xy=True)
    glb,contours,report=build_dsm(raw,bbox,transformer)
    report["remote_archive_sha256"]=hashlib.sha256(payload).hexdigest()
    report["raw_hgt_sha256"]=hashlib.sha256(raw).hexdigest()
    report["inherited_geojson_sha256"]=hashlib.sha256(basis).hexdigest()
    out.mkdir(parents=True,exist_ok=True)
    (out/"BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb").write_bytes(glb)
    (out/"BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson").write_text(
        json.dumps(contours,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (out/"BNBU_v67_TERRAIN_SOURCE_AND_LIMITS.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--tile",type=Path,help="Use an already downloaded N22E113.hgt.zip; never guess input tiles")
    parser.add_argument("--out",type=Path,default=OUT)
    args=parser.parse_args()
    report=build(args.out,args.tile.read_bytes() if args.tile else None)
    print(json.dumps({k:report[k] for k in ("grid_width","grid_height","raw_raster_elevation_min_m","raw_raster_elevation_max_m","triangle_count","contour_segment_count","remote_archive_sha256")},indent=2))
