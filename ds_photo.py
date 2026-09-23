"""GSI seamless aerial photo (国土地理院 シームレス空中写真) as a georeferenced
reference raster for the DisneySea draft (reference only: used to trace water
that OSM lacks and to check shorelines, never used as a texture).

Tiles are cached in plateau_data/gsi_photo/{z}_{x}_{y}.jpg. Coordinates are the
draft's local metres (origin 35.6267,139.8851, +X east, +Y north).
出典: 国土地理院 シームレス空中写真
"""
import math, io, pathlib, urllib.request
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "plateau_data" / "gsi_photo"
LAT0, LON0 = 35.6267, 139.8851
KX, KY = 111320.0 * math.cos(math.radians(LAT0)), 110574.0
URL = "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"


def _tile_f(lat, lon, z):
    n = 2 ** z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return fx, fy


def _fetch(z, x, y):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{z}_{x}_{y}.jpg"
    if not p.exists():
        req = urllib.request.Request(URL.format(z=z, x=x, y=y), headers={"User-Agent": "personal-research"})
        p.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    return Image.open(p).convert("RGB")


class Photo:
    """RGB array covering local box (x0,y0)-(x1,y1) with metre<->pixel helpers."""

    def __init__(self, x0, y0, x1, y1, z=18):
        lat0, lon0 = LAT0 + y1 / KY, LON0 + x0 / KX   # top-left
        lat1, lon1 = LAT0 + y0 / KY, LON0 + x1 / KX   # bottom-right
        fx0, fy0 = _tile_f(lat0, lon0, z)
        fx1, fy1 = _tile_f(lat1, lon1, z)
        tx, ty = range(int(fx0), int(fx1) + 1), range(int(fy0), int(fy1) + 1)
        im = Image.new("RGB", (256 * len(tx), 256 * len(ty)))
        for i, a in enumerate(tx):
            for j, b in enumerate(ty):
                im.paste(_fetch(z, a, b), (256 * i, 256 * j))
        box = (int((fx0 - tx[0]) * 256), int((fy0 - ty[0]) * 256),
               int((fx1 - tx[0]) * 256), int((fy1 - ty[0]) * 256))
        self.img = np.asarray(im.crop(box))
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        h, w = self.img.shape[:2]
        self.sx, self.sy = w / (x1 - x0), h / (y1 - y0)

    def to_px(self, x, y):
        return (x - self.x0) * self.sx, (self.y1 - y) * self.sy

    def to_m(self, u, v):
        return self.x0 + u / self.sx, self.y1 - v / self.sy
