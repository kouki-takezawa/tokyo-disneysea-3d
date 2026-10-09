#!/usr/bin/env python
"""fetch_kusatsu.py -- Kusatsu onsen (Yubatake) diorama: OSM + GSI DEM -> plateau_data/.
Local frame: origin = Yubatake centre (OSM), +X east, +Y north, Z = elevation (m, GSI DEM5A/10B).
Outputs: plateau_data/kusatsu_osm.json (raw Overpass, radius R+margin), plateau_data/kusatsu_dem.json (grid).
(c) OpenStreetMap contributors (ODbL); elevation: GSI (Geospatial Information Authority of Japan) tiles.
Usage: python fetch_kusatsu.py [--osm] [--dem]
"""
import json, math, sys, time, urllib.request, urllib.parse, io
UA = "kusatsu-diorama/1.0 (personal 3D project)"
MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]
ORIGIN = (36.622927, 138.596740)   # OSM relation 12852884 "湯畑" centre
R = 260.0                         # fetch radius (spec radius 200 m + margin)

def overpass(q):
    last = None
    for m in MIRRORS:
        try:
            d = urllib.parse.urlencode({"data": q}).encode()
            req = urllib.request.Request(m, d, {"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=120))
        except Exception as e:
            last = e; print("mirror fail", m, e)
    raise last

def find_origin():
    q = '[out:json][timeout:60];nwr["name"~"湯畑"](36.615,138.585,36.630,138.605);out center tags;'
    return overpass(q)

def fetch_osm(lat, lon):
    q = f"""[out:json][timeout:120];
(way(around:{R},{lat},{lon})["building"];
 way(around:{R},{lat},{lon})["highway"];
 way(around:{R},{lat},{lon})["natural"="water"];
 way(around:{R},{lat},{lon})["waterway"];
 way(around:{R},{lat},{lon})["amenity"];
 way(around:{R},{lat},{lon})["tourism"];
 way(around:{R},{lat},{lon})["leisure"];
 way(around:{R},{lat},{lon})["man_made"];
 way(around:{R},{lat},{lon})["landuse"];
 way(around:{R},{lat},{lon})["barrier"];
 rel(around:{R},{lat},{lon})["building"];
 rel(around:{R},{lat},{lon})["natural"="water"];
 node(around:{R},{lat},{lon})["name"];
 node(around:{R},{lat},{lon})["amenity"];
 node(around:{R},{lat},{lon})["shop"];
 node(around:{R},{lat},{lon})["tourism"];
 node(around:{R},{lat},{lon})["highway"];
 node(around:{R},{lat},{lon})["man_made"];
 node(around:{R},{lat},{lon})["natural"];
);
out body geom;"""
    return overpass(q)

# --- GSI DEM (dem5a z15 / dem10b z14 PNG tiles: h = (R*65536+G*256+B)*0.01, 2^23 = nodata)
def tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def fetch_dem(lat0, lon0, half=300.0, step=4.0):
    import numpy as np
    from PIL import Image
    kn = 111132.92 - 559.82 * math.cos(2 * math.radians(lat0))
    ke = 111412.84 * math.cos(math.radians(lat0))
    cache = {}
    def tile(layer, z, x, y):
        k = (layer, z, x, y)
        if k not in cache:
            u = f"https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.png"
            try:
                b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60).read()
                a = np.asarray(Image.open(io.BytesIO(b)).convert("RGB")).astype(np.int64)
                h = (a[..., 0] * 65536 + a[..., 1] * 256 + a[..., 2]).astype(float)
                h = np.where(h == 2 ** 23, np.nan, np.where(h > 2 ** 23, (h - 2 ** 24) * 0.01, h * 0.01))
                cache[k] = h
            except Exception as e:
                print("tile fail", u, e); cache[k] = None
        return cache[k]
    def sample(layer, z, la, lo):
        tx, ty = tile_xy(la, lo, z); ix, iy = int(tx), int(ty)
        t = tile(layer, z, ix, iy)
        if t is None: return float("nan")
        px = min(255, int((tx - ix) * 256)); py = min(255, int((ty - iy) * 256))
        return float(t[py, px])
    xs = np.arange(-half, half + 1e-6, step); ys = np.arange(-half, half + 1e-6, step)
    grid = []; used = {"dem5a": 0, "dem10b": 0, "nan": 0}
    for y in ys:
        row = []
        for x in xs:
            la = lat0 + y / kn; lo = lon0 + x / ke
            h = sample("dem5a_png", 15, la, lo)
            if h == h: used["dem5a"] += 1
            else:
                h = sample("dem_png", 14, la, lo)
                if h == h: used["dem10b"] += 1
                else: used["nan"] += 1
            row.append(h)
        grid.append(row)
    return {"origin_latlon": [lat0, lon0], "step": step, "x0": -half, "y0": -half, "nx": len(xs), "ny": len(ys),
            "z_rows_south_to_north": [[None if v != v else round(v, 2) for v in r] for r in grid], "used": used,
            "note": "z = elevation above sea level (m); rows go south->north, columns west->east"}

if __name__ == "__main__":
    import os
    os.makedirs("plateau_data", exist_ok=True)
    lat, lon = ORIGIN
    if "--origin" in sys.argv:
        json.dump(find_origin(), open("plateau_data/_origin_probe.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--osm" in sys.argv:
        d = fetch_osm(lat, lon)
        d["_origin"] = [lat, lon]; d["_radius"] = R
        json.dump(d, open("plateau_data/kusatsu_osm.json", "w", encoding="utf-8"), ensure_ascii=False)
        print("osm elements", len(d["elements"]))
    if "--dem" in sys.argv:
        d = fetch_dem(lat, lon)
        json.dump(d, open("plateau_data/kusatsu_dem.json", "w"), separators=(",", ":"))
        print("dem", d["nx"], d["ny"], d["used"])
