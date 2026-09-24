"""Water model for the DisneySea draft: every water body with its level, depth
and shoreline type, written to plateau_data/disneysea_water.json (plain
Python + OpenCV; Blender reads only the JSON, see disneysea_water_blender.py).

  python ds_water.py            # builds the JSON and prints a summary

Sources
  shapes   OSM natural=water (ways + multipolygons), same selection as
           ds_terrain._plan_water so the draft's ground holes match.
           The main harbour multipolygon also runs through Mysterious Island
           (the Transit Steamer route: Lost River Delta -> tunnel -> caldera
           lagoon -> tunnel -> harbour). Only the lagoon is open to the sky, so
           that stretch is split: the lagoon is traced from the GSI aerial photo
           (ds_photo, colour flood-fill) and everything else inside the caldera
           zone becomes "tunnel" water (under rockwork: no ground hole, dashed
           in the mock).
  levels   ground at the shore from GSI DEM5A (ds_levels.dem, relative to the
           promenade datum) minus a freeboard per kind of water. DEM5A has no
           returns on water (values there are interpolated), so the water level
           itself is never read from the DEM.
           CAUTION: the DEM and aerial photo predate Fantasy Springs (opened
           2024; the photo shows a construction site), so levels there are
           "estimated" from the freeboard only.
  shores   each shore edge is probed 2.5 m on the land side: building -> the
           facade rises straight from the water, rock -> rockwork bank,
           sand/beach -> beach, grass/garden/wood -> planted bank, else a
           stone quay wall.
"""
import json, math, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import ds_core as C
import ds_terrain as T
import ds_levels as LV

OUT = ROOT / "plateau_data" / "disneysea_water.json"
MAIN_HARBOR = "R3531413"
PROBE = 2.5            # m from the shoreline to the land-side probe
SEG = 4.0              # classify shores in pieces of at most this length

# (freeboard m = shore ground - water surface, depth m = surface - bed)
PROFILE = {
    "harbor":   (1.0, 2.5),   # メインの港と水路 (蒸気船・トランジット)
    "lagoon":   (1.3, 3.0),   # ミステリアスアイランドのカルデラ湖 (ノーチラス号)
    "channel":  (0.7, 1.2),   # 小さめの切り込み水路・池
    "pond":     (0.35, 0.6),  # 園路に置かれた池・噴水の水盤
    "fountain": (0.25, 0.3),
}

# Mysterious Island caldera: zone where the harbour water is covered except the lagoon
CALDERA_ZONE = ((-55.0, -40.0), 70.0)               # centre, radius (m)
CALDERA_BOX = (-140, -160, 60, 20)                 # photo crop, local metres
CALDERA_SEEDS = [(-65, -35), (-80, -25), (-60, -50)]  # open water pixels
CALDERA_TOL = 22                                    # Lab distance


def _names():
    tags = {f"W{w['id']}": w["tags"] for w in C.DATA["ways"]}
    tags.update({f"R{r['id']}": r["tags"] for r in C.DATA["relations"]})
    return tags


def trace_caldera():
    """Outline of the caldera lagoon from the aerial photo (OSM lacks it)."""
    import cv2, numpy as np
    from ds_photo import Photo
    ph = Photo(*CALDERA_BOX, z=18)
    img = cv2.GaussianBlur(ph.img, (5, 5), 0)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(float)
    px = [tuple(int(v) for v in ph.to_px(x, y)) for x, y in CALDERA_SEEDS]
    ref = np.median([lab[v, u] for u, v in px], axis=0)
    d = np.linalg.norm((lab - ref) * [1, 1.5, 1.5], axis=2)
    mask = cv2.morphologyEx((d < CALDERA_TOL).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    _, cc = cv2.connectedComponents(mask)
    u, v = px[0]
    m = (cc == cc[v, u]).astype(np.uint8) * 255
    # close over the moored Nautilus and the ripples so the lagoon is one clean body
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 1.2 * ph.sx, True)[:, 0, :]   # ~1.2 m tolerance
    ring = [ph.to_m(float(a), float(b)) for a, b in c]
    ring = [(round(x, 2), round(y, 2)) for x, y in ring]
    if _signed_area(ring) < 0:
        ring.reverse()
    return ring


def _signed_area(r):
    return sum(r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1] for i in range(len(r))) / 2


def _land_polys():
    """Land cover used to classify shores: list of (type, ring, bbox)."""
    out = []

    def add(t, ring):
        if len(ring) >= 3:
            xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
            out.append((t, ring, (min(xs), min(ys), max(xs), max(ys))))

    for w in C.ways_with("building"):
        if w["tags"].get("layer", "0").lstrip("-").isdigit() and int(w["tags"].get("layer", "0")) > 0:
            continue  # roofs / canopies over paths do not stand in the water
        add("building", w["pts"])
    for r, outers, _ in C.multipolygons("building"):
        for o in outers:
            add("building", o)
    cover = {"scree": "rock", "bare_rock": "rock", "cliff": "rock", "sand": "beach", "beach": "beach",
             "grassland": "bank", "scrub": "bank", "wood": "bank"}
    for v, t in cover.items():
        for w in C.ways_with("natural", v):
            add(t, w["pts"])
        for r, outers, _ in C.multipolygons("natural", v):
            for o in outers:
                add(t, o)
    for k, v in (("landuse", "grass"), ("leisure", "garden"), ("landuse", "forest"), ("landuse", "flowerbed")):
        for w in C.ways_with(k, v):
            add("bank", w["pts"])
        for r, outers, _ in C.multipolygons(k, v):
            for o in outers:
                add("bank", o)
    return out


ORDER = ["building", "rock", "beach", "bank"]
TUNNELS = []   # filled by build()


def _classify(x, y, land):
    for ring in TUNNELS:
        if C.point_in_poly(x, y, ring):
            return "portal"
    hits = set()
    for t, ring, (a, b, c, d) in land:
        if a <= x <= c and b <= y <= d and C.point_in_poly(x, y, ring):
            hits.add(t)
    for t in ORDER:
        if t in hits:
            return t
    return "quay"


def _shore_runs(ring, water_is_left, land, body_idx, ring_idx):
    """Split a ring into runs of equal shore type. water_is_left: walking the
    ring, water lies to the left (CCW outer ring / CW island)."""
    n = len(ring)
    pieces = []  # (x0,y0,x1,y1,type)
    for i in range(n):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1e-6:
            continue
        k = max(1, math.ceil(L / SEG))
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L   # right-hand normal
        if not water_is_left:
            nx, ny = -nx, -ny
        for j in range(k):
            ax, ay = x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k
            bx, by = x0 + (x1 - x0) * (j + 1) / k, y0 + (y1 - y0) * (j + 1) / k
            mx, my = (ax + bx) / 2, (ay + by) / 2
            t = _classify(mx + nx * PROBE, my + ny * PROBE, land)
            pieces.append((ax, ay, bx, by, t))
    # smooth single-piece flickers (a 4 m quay between two rock pieces is noise)
    types = [p[4] for p in pieces]
    for i in range(len(types)):
        a, b = types[i - 1], types[(i + 1) % len(types)]
        if a == b != types[i]:
            types[i] = a
    runs = []
    for p, t in zip(pieces, types):
        if runs and runs[-1]["t"] == t:
            runs[-1]["l"].append([round(p[2], 2), round(p[3], 2)])
        else:
            runs.append({"t": t, "b": body_idx, "r": ring_idx,
                         "l": [[round(p[0], 2), round(p[1], 2)], [round(p[2], 2), round(p[3], 2)]]})
    if len(runs) > 1 and runs[0]["t"] == runs[-1]["t"]:   # join across the ring start
        runs[0]["l"] = runs[-1]["l"] + runs[0]["l"][1:]
        runs.pop()
    return runs


def _shore_ground(ring, water_is_left):
    """Ground height (relative to datum) along the land side of a shore."""
    zs = []
    n = len(ring)
    step = max(1, n // 60)
    for i in range(0, n, step):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L
        if not water_is_left:
            nx, ny = -nx, -ny
        zs.append(LV.dem((x0 + x1) / 2 + nx * 4, (y0 + y1) / 2 + ny * 4))
    zs.sort()
    return zs[len(zs) // 2]


def _split_caldera(bodies):
    """Replace the main harbour by its open parts; the parts inside the caldera
    zone that are not the photo-traced lagoon become tunnels."""
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    h = next(b for b in bodies if b["id"] == MAIN_HARBOR)
    harbor = Polygon(h["ring"], h["inners"]).buffer(0)
    (cx, cy), rad = CALDERA_ZONE
    zone = Point(cx, cy).buffer(rad, 64)
    lagoon = Polygon(trace_caldera()).buffer(2.5)            # photo edge is a little inside the quay
    covered = harbor.intersection(zone).difference(lagoon)
    open_ = harbor.difference(covered)

    def polys(g):
        g = g.buffer(0)
        return [p for p in getattr(g, "geoms", [g]) if p.area > 5]

    out = [b for b in bodies if b["id"] != MAIN_HARBOR]
    parts = sorted(polys(open_), key=lambda p: -p.area)
    for i, p in enumerate(parts):
        sub = "" if i == 0 else ("_lagoon" if p.intersects(Point(-65, -35)) else f"_{i}")
        out.insert(i, {"id": MAIN_HARBOR + sub, "cut": True, "ring": list(p.exterior.coords)[:-1],
                       "inners": [list(r.coords)[:-1] for r in p.interiors],
                       "src": "osm+photo" if sub else "osm"})
    tunnels = [[(round(x, 2), round(y, 2)) for x, y in list(p.exterior.coords)[:-1]] for p in polys(covered)]
    return out, tunnels


def build():
    LV.compute()
    if not T.STATE["holes"]:
        T._plan_water()
    names = _names()
    bodies = []
    for ring, inners, tag in T.STATE["holes"]:
        bodies.append({"id": tag, "cut": True, "ring": ring, "inners": inners})
    for ring, tag in T.STATE["surface_water"]:
        bodies.append({"id": tag, "cut": False, "ring": ring, "inners": []})
    bodies, tunnels = _split_caldera(bodies)

    TUNNELS[:] = tunnels
    land = _land_polys()
    shores, out_bodies = [], []
    for bi, b in enumerate(bodies):
        ring = C._clean_ring(b["ring"])
        if _signed_area(ring) < 0:
            ring = ring[::-1]
        inners = [C._clean_ring(i) for i in b["inners"]]
        inners = [i[::-1] if _signed_area(i) > 0 else i for i in inners]   # islands clockwise
        t = names.get(b["id"], {})
        cx, cy = C.poly_centroid(ring)
        port = C.nearest_port(cx, cy, ring)
        area = C.poly_area(ring) - sum(C.poly_area(i) for i in inners)
        if b["id"] == MAIN_HARBOR + "_lagoon":
            kind = "lagoon"
        elif b["id"].startswith(MAIN_HARBOR):
            kind = "harbor"
        elif t.get("amenity") == "fountain":
            kind = "fountain"
        elif b["cut"]:
            kind = "channel"
        else:
            kind = "pond"
        free, depth = PROFILE[kind]
        ground = _shore_ground(ring, True)
        stale = port == "fantasy_springs"
        level = (0.0 if stale else ground) - free
        basis = "estimated" if stale else "dem_shore"
        if b["id"].startswith(MAIN_HARBOR) and b["id"] != MAIN_HARBOR:
            level, basis = out_bodies[0]["level"], "linked"   # same water as the harbour (via the tunnels)
            ground = level + free
        name = t.get("name:ja") or t.get("name") or ""
        if b["id"] == MAIN_HARBOR:
            name = "メインの港・水路(メディテレーニアンハーバー〜各港)"
        elif kind == "lagoon":
            name = "カルデラ湖(ミステリアスアイランド、港とトンネルでつながる)"
        ob = {"id": b["id"], "kind": kind, "cut": b["cut"], "port": port, "name": name,
              "area": round(area), "ground": round(ground, 2), "freeboard": free, "depth": depth,
              "level": round(level, 2), "basis": basis,
              "src": b.get("src", "osm"),
              "ring": [[round(x, 2), round(y, 2)] for x, y in ring],
              "inners": [[[round(x, 2), round(y, 2)] for x, y in i] for i in inners]}
        out_bodies.append(ob)
        shores += _shore_runs(ring, True, land, bi, 0)
        for k, isl in enumerate(inners):
            shores += _shore_runs(isl, True, land, bi, k + 1)

    piers = [{"id": w["id"], "ring": [[round(x, 2), round(y, 2)] for x, y in C._clean_ring(w["pts"])]}
             for w in C.ways_with("man_made", "pier") if C.in_park(w["pts"])]

    # waterfalls: a waterway segment joining two bodies whose levels differ
    def body_at(x, y):
        for i, b in enumerate(out_bodies):
            if C.point_in_poly(x, y, b["ring"]) and not any(C.point_in_poly(x, y, h) for h in b["inners"]):
                return i
        return None
    falls = []
    for w in C.ways_with("waterway", None, closed_only=False):
        if not C.in_park(w["pts"]):
            continue
        pts = w["pts"]
        a, z = body_at(*pts[0]), body_at(*pts[-1])
        if a is not None and z is not None and a != z:
            dz = out_bodies[a]["level"] - out_bodies[z]["level"]
            if abs(dz) > 0.15:
                falls.append({"way": w["id"], "from": a, "to": z, "l": [[round(x, 2), round(y, 2)] for x, y in pts],
                              "drop": round(dz, 2)})

    counts = {}
    for s in shores:
        L = sum(math.dist(s["l"][i], s["l"][i + 1]) for i in range(len(s["l"]) - 1))
        counts[s["t"]] = counts.get(s["t"], 0) + L
    data = {"datum_m": round(LV.DATUM, 3), "note": "levels are relative to the promenade datum (DEM5A median of paths)",
            "profiles": {k: {"freeboard": v[0], "depth": v[1]} for k, v in PROFILE.items()},
            "bodies": out_bodies, "tunnels": [{"ring": t, "body": 0} for t in tunnels], "shores": shores, "piers": piers, "falls": falls,
            "shore_length": {k: round(v) for k, v in counts.items()}}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = build()
    print(f"[water] {OUT}  bodies={len(d['bodies'])} tunnels={len(d['tunnels'])} shores={len(d['shores'])} piers={len(d['piers'])} falls={len(d['falls'])}")
    print("[water] shore length m:", d["shore_length"])
    for b in sorted(d["bodies"], key=lambda b: -b["area"])[:12]:
        print(f"  {b['id']:>12} {b['kind']:8} {b['port']:22} {b['area']:7} m2 level {b['level']:+.2f} "
              f"(ground {b['ground']:+.2f}) {b['basis']} {b['name']}")
