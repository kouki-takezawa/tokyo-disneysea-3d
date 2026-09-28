"""東京ディズニーランドホテルの平面 -- splits OSM's one hotel outline into the parts ds_tdl_hotel.py builds (plain Python:
shapely). Writes plateau_data/tdl_hotel_plan.json, in the hotel's local frame (ds_tdl_hotel.FRAME).

  python src/ds_tdl_hotel_plan.py

The front (the photographed side, the user's photos 2026-09-28) faces the station, south: the U-shaped court with the
round garden in the middle (OSM: the round building 788770688, the ring path 1340488354). Its head wall (OSM points 70..78)
carries the main block with the gold dome; the two wings end at the court's mouth, where the two tall towers stand.
Parts (all from way 218553057, simplified to 1 m):
  main     the main building, 8 floors (everything but the three below)
  ngw      the tall block to the north-east (points 20..40, closed across; OSM's height 60 m), the same facade as main, taller
  blue     the low Victorian wing west of the court's mouth (south of the mouth line, the OSM outline reaches 25 m further south)
  purple   the low Victorian wing at the east of the court's mouth
court frame: origin on the head wall opposite the round garden, +y out across the court towards the station.
"""
import json, math, pathlib
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

ROOT = pathlib.Path(__file__).resolve().parent.parent
OSM = ROOT / "plateau_data" / "disneyland_osm.json"
OUT = ROOT / "plateau_data" / "tdl_hotel_plan.json"
HOTEL_WAY = 218553057
FRAME = dict(x=-573.895, y=1171.313, ang=65.6534)       # = ds_tdl_hotel.FRAME
GARDEN = (-608.31, 1077.29)                             # the round building in the court (OSM 788770688)
HEAD = ((-609.61, 1097.91), (-616.53, 1094.93))         # the head wall's middle segment (OSM points 72 -> 73)
MANSARD_D, DECK_D = 1.6, 0.5


def to_local(p):
    a = math.radians(FRAME["ang"]); dx, dy = p[0] - FRAME["x"], p[1] - FRAME["y"]
    return (dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a))


def ring(poly):
    """Exterior ring, clockwise in the local frame (the outside on the left of each edge: facades face local +y)."""
    poly = orient(poly, sign=-1.0)
    return [[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]


def main():
    ways = {w["id"]: w for w in json.loads(OSM.read_text(encoding="utf-8"))["ways"]}
    pts = ways[HOTEL_WAY]["pts"][:-1]
    loc = [to_local(p) for p in pts]
    whole = Polygon(loc).buffer(0)
    ngw = Polygon(loc[20:41]).buffer(0)
    body = whole.difference(ngw.buffer(0.01))
    # the court frame: origin = the foot of the perpendicular from the garden to the head wall, +y towards the garden
    (hx0, hy0), (hx1, hy1) = [to_local(p) for p in HEAD]; g = to_local(GARDEN)
    ux, uy = hx1 - hx0, hy1 - hy0; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
    t = (g[0] - hx0) * ux + (g[1] - hy0) * uy
    ox, oy = hx0 + ux * t, hy0 + uy * t
    nx, ny = g[0] - ox, g[1] - oy; dist = math.hypot(nx, ny)
    ang_y = math.atan2(ny, nx)                               # the court's +y (towards the station)
    ang_x = ang_y - math.pi / 2                              # its +x (along the head wall)
    def to_c(p):
        dx, dy = p[0] - ox, p[1] - oy
        return (dx * math.cos(ang_x) + dy * math.sin(ang_x), -dx * math.sin(ang_x) + dy * math.cos(ang_x))
    def from_c(x, y):
        return (ox + x * math.cos(ang_x) - y * math.sin(ang_x), oy + x * math.sin(ang_x) + y * math.cos(ang_x))
    cb = [to_c(p) for p in body.exterior.coords]
    print("court: garden at", round(dist, 1), "m; body in court frame x", round(min(p[0] for p in cb), 1), round(max(p[0] for p in cb), 1),
          "y", round(min(p[1] for p in cb), 1), round(max(p[1] for p in cb), 1))
    # the two low wings: the parts of the body beyond the court's mouth, either side of it
    mouth_y = 28.0
    big = 400.0
    west = Polygon([from_c(12.0, mouth_y), from_c(big, mouth_y), from_c(big, big), from_c(12.0, big)])
    east = Polygon([from_c(-big, mouth_y - 10.0), from_c(-16.0, mouth_y - 10.0), from_c(-16.0, big), from_c(-big, big)])
    blue = body.intersection(west); purple = body.intersection(east)
    main_ = body.difference(blue.buffer(0.01)).difference(purple.buffer(0.01))
    parts = {}
    for name, poly in (("main", main_), ("ngw", ngw), ("blue", blue), ("purple", purple)):
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda q: q.area)
        poly = poly.simplify(1.0, preserve_topology=True)
        inset = poly.buffer(-(MANSARD_D + DECK_D - 0.05), join_style=2) if name in ("main", "ngw") else poly.buffer(-3.2, join_style=2)
        if inset.geom_type == "MultiPolygon":
            inset = [q for q in inset.geoms]
        else:
            inset = [inset]
        parts[name] = {"ring": ring(poly), "roof": [ring(q) for q in inset if q.area > 4.0], "area": round(poly.area)}
        print(name, len(parts[name]["ring"]), "points,", parts[name]["area"], "m2, roof pieces", len(parts[name]["roof"]))
    out = {"frame": FRAME, "court": {"x": round(ox, 3), "y": round(oy, 3), "ang": round(math.degrees(ang_x), 3), "garden": round(dist, 2)},
           "footprint": ring(whole), "parts": parts}
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
