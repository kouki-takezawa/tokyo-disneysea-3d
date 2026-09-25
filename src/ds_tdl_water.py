"""Water model for Tokyo Disneyland, made the same way as the DisneySea one (ds_water.py): every water body with its
level, depth and shoreline type, written to plateau_data/disneyland_water.json (plain Python; Blender reads only the
JSON, see tdl_water_blender.py). The JSON has the same layout as disneysea_water.json, so the DisneySea Blender
builder (disneysea_water_blender.build_water) makes the Land's water too.

  python src/ds_tdl_water.py            # builds the JSON and prints a summary

Sources
  shapes   OSM natural=water (multipolygon relations and closed ways) whose middle is inside the park
           (tourism=theme_park way 1282875870), from plateau_data/disneyland_osm.json. A way that is a member of a
           relation, or that lies inside a body already taken (and not on one of its islands), is a duplicate.
  levels   the ground at the shore from GSI DEM5A (ds_levels.dem, relative to the DisneySea promenade datum, as the
           rest of the Land) minus a freeboard per kind of water; DEM5A has no returns on water, so the water level is
           never read from the DEM itself.
  shores   each shore edge is probed 2.5 m on the land side: building -> the wall rises straight from the water,
           rock (scree / bare rock / cliff) -> rockwork bank, sand / beach -> beach, grass / garden / wood /
           forest / scrub / flowerbed -> planted bank, else a stone quay wall.
  kinds    the Rivers of America and the Jungle Cruise river -> "river"; the castle's moat -> "moat"; other open water
           over 150 m2 -> "channel"; smaller -> "pond"; amenity=fountain -> "fountain". Freeboards and depths are
           estimates (no survey), like the DisneySea ones.
"""
import json, math, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import ds_levels as LV
from ds_core import point_in_poly, poly_area, poly_centroid, _clean_ring, closed_rings, signed_area as _signed_area

OUT = ROOT / "plateau_data" / "disneyland_water.json"
from ds_disneyland import DATA, WAYS
PARK_WAY = 1282875870                   # 東京ディズニーランド (tourism=theme_park)
PARK = _clean_ring(WAYS[PARK_WAY]["pts"])
RIVERS_OF_AMERICA = "R1125423"
CASTLE = (-385.4, 594.0)                # Cinderella Castle's footprint centroid (way 217727348)
JUNGLE_POI = "ジャングルクルーズ"
PROBE = 2.5
SEG = 4.0

# (freeboard m = shore ground - water surface, depth m = surface - bed); estimates
PROFILE = {
    "river":    (1.0, 2.2),   # アメリカ河 (蒸気船・いかだ・カヌー) とジャングルクルーズの川
    "moat":     (1.3, 1.5),   # シンデレラ城の堀
    "channel":  (0.7, 1.2),   # ほかの水路・池
    "pond":     (0.35, 0.6),  # 小さな池・水盤
    "fountain": (0.25, 0.3),
}


def assemble(way_ids):
    """Chain member ways into closed rings."""
    return [_clean_ring(r) for r in closed_rings(WAYS, way_ids)]


def multipolygons(pred):
    for r in DATA["relations"]:
        if pred(r["tags"]):
            outers = assemble([m["way"] for m in r["members"] if m["role"] == "outer"])
            inners = assemble([m["way"] for m in r["members"] if m["role"] == "inner"])
            if outers:
                yield r, outers, inners


def in_park(ring):
    return point_in_poly(*poly_centroid(ring), PARK)


def is_water(t):
    return t.get("natural") == "water" or t.get("waterway") == "riverbank"


def candidates():
    members = {m["way"] for r in DATA["relations"] for m in r["members"]}
    cands = []
    for r, outers, inners in multipolygons(is_water):
        for o in outers:
            ins = [i for i in inners if point_in_poly(*poly_centroid(i), o)]
            cands.append((poly_area(o), o, ins, f"R{r['id']}", r["tags"]))
    for w in DATA["ways"]:
        if w["closed"] and is_water(w["tags"]) and w["id"] not in members:
            ring = _clean_ring(w["pts"])
            if len(ring) >= 3:
                cands.append((poly_area(ring), ring, [], f"W{w['id']}", w["tags"]))
    cands.sort(key=lambda c: -c[0])
    return cands


def plan():
    """Bodies in the park, largest first; drop duplicates (a smaller ring inside a taken body, not on its island)."""
    bodies = []
    for area, ring, inners, tag, tags in candidates():
        if area < 1.5 or not in_park(ring):
            continue
        cx, cy = poly_centroid(ring)
        parent = next((b for b in bodies if point_in_poly(cx, cy, b["ring"])), None)
        if parent and not any(point_in_poly(cx, cy, isl) for isl in parent["inners"]):
            continue
        bodies.append({"id": tag, "ring": ring, "inners": inners, "tags": tags, "cut": True})
    return clean(bodies)


def clean(bodies):
    """Clip each body to the park and take away what larger bodies already cover, so the Blender ground gets clean,
    separate holes (overlapping or self-touching cutters make the exact boolean return nothing)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    park = Polygon(PARK).buffer(-0.5)
    taken, out = None, []
    for b in bodies:
        g = Polygon(b["ring"], b["inners"]).buffer(0).intersection(park)
        if taken is not None:
            g = g.difference(taken.buffer(0.25))       # a thin strip of land: shared edges also break the boolean
        g = g.buffer(0)
        parts = sorted([p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area >= 1.5], key=lambda p: -p.area)
        if not parts:
            continue
        p = parts[0].simplify(0.05)
        taken = p if taken is None else unary_union([taken, p])
        out.append(dict(b, ring=[tuple(c) for c in p.exterior.coords][:-1],
                        inners=[[tuple(c) for c in r.coords][:-1] for r in p.interiors if Polygon(r).area >= 1.0]))
    return out


def land_polys():
    """Land cover for the shore probe: list of (type, ring, bbox)."""
    out = []

    def add(t, ring):
        if len(ring) >= 3:
            xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
            out.append((t, ring, (min(xs), min(ys), max(xs), max(ys))))

    def cover(tags):
        if "building" in tags:
            lay = tags.get("layer", "0")
            if lay.lstrip("-").isdigit() and int(lay) > 0:
                return None          # roofs over paths do not stand in the water
            return "building"
        n = tags.get("natural")
        if n in ("scree", "bare_rock", "cliff", "rock"):
            return "rock"
        if n in ("sand", "beach"):
            return "beach"
        if n in ("grassland", "scrub", "wood") or tags.get("landuse") in ("grass", "forest", "flowerbed") or tags.get("leisure") in ("garden", "park"):
            return "bank"
        return None

    for w in DATA["ways"]:
        if w["closed"]:
            t = cover(w["tags"])
            if t:
                add(t, w["pts"])
    for r, outers, _ in multipolygons(lambda t: cover(t) is not None):
        for o in outers:
            add(cover(r["tags"]), o)
    return out


ORDER = ["building", "rock", "beach", "bank"]


def classify(x, y, land):
    hits = {t for t, ring, (a, b, c, d) in land if a <= x <= c and b <= y <= d and point_in_poly(x, y, ring)}
    return next((t for t in ORDER if t in hits), "quay")


def shore_runs(ring, land, body_idx, ring_idx):
    """Runs of equal shore type along a ring (water on the left: CCW outer ring, CW island)."""
    n = len(ring)
    pieces = []
    for i in range(n):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1e-6:
            continue
        k = max(1, math.ceil(L / SEG))
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L        # right-hand normal = the land side
        for j in range(k):
            ax, ay = x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k
            bx, by = x0 + (x1 - x0) * (j + 1) / k, y0 + (y1 - y0) * (j + 1) / k
            mx, my = (ax + bx) / 2, (ay + by) / 2
            pieces.append((ax, ay, bx, by, classify(mx + nx * PROBE, my + ny * PROBE, land)))
    types = [p[4] for p in pieces]
    for i in range(len(types)):                       # one-piece flickers are noise
        a, b = types[i - 1], types[(i + 1) % len(types)]
        if a == b != types[i]:
            types[i] = a
    runs = []
    for p, t in zip(pieces, types):
        if runs and runs[-1]["t"] == t:
            runs[-1]["l"].append([round(p[2], 2), round(p[3], 2)])
        else:
            runs.append({"t": t, "b": body_idx, "r": ring_idx, "l": [[round(p[0], 2), round(p[1], 2)], [round(p[2], 2), round(p[3], 2)]]})
    if len(runs) > 1 and runs[0]["t"] == runs[-1]["t"]:
        runs[0]["l"] = runs[-1]["l"] + runs[0]["l"][1:]
        runs.pop()
    return runs


def shore_ground(ring):
    """Median ground height (relative to the datum) 4 m on the land side of the shore."""
    zs = []
    n = len(ring)
    for i in range(0, n, max(1, n // 60)):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L
        zs.append(LV.dem((x0 + x1) / 2 + nx * 4, (y0 + y1) / 2 + ny * 4))
    zs.sort()
    return zs[len(zs) // 2]


def nearest_poi(x, y, reach=80.0):
    best = (reach, "")
    for p in DATA["pois"]:
        n = p["tags"].get("name:ja") or p["tags"].get("name")
        if n:
            d = math.hypot(p["xy"][0] - x, p["xy"][1] - y)
            if d < best[0]:
                best = (d, n)
    return best[1]


def build():
    LV.levels()                                      # sets LV.DATUM (the DisneySea promenade datum, as the Land uses)
    raw = plan()
    jungle = [p["xy"] for p in DATA["pois"] if JUNGLE_POI in (p["tags"].get("name:ja") or p["tags"].get("name") or "")]
    land = land_polys()
    bodies, shores = [], []
    for bi, b in enumerate(raw):
        ring = b["ring"] if _signed_area(b["ring"]) > 0 else b["ring"][::-1]
        inners = [i[::-1] if _signed_area(i) > 0 else i for i in b["inners"]]
        t = b["tags"]
        area = poly_area(ring) - sum(poly_area(i) for i in inners)
        cx, cy = poly_centroid(ring)
        if b["id"] == RIVERS_OF_AMERICA or (jungle and area > 800 and min(math.hypot(cx - x, cy - y) for x, y in jungle) < 90):
            kind = "river"
        elif any(point_in_poly(*CASTLE, i) for i in inners) or (area > 300 and math.hypot(cx - CASTLE[0], cy - CASTLE[1]) < 70):
            kind = "moat"
        elif t.get("amenity") == "fountain":
            kind = "fountain"
        elif area > 150:
            kind = "channel"
        else:
            kind = "pond"
        free, depth = PROFILE[kind]
        ground = shore_ground(ring)
        name = t.get("name:ja") or t.get("name") or ""
        if kind == "moat":
            name = name or "シンデレラ城の堀"
        elif kind == "river" and not name:
            name = "ジャングルクルーズの川"
        if not name:
            near = nearest_poi(cx, cy)
            name = f"{near}の近くの水面" if near else ""
        bodies.append({"id": b["id"], "kind": kind, "cut": True, "port": "disneyland", "name": name,
                       "area": round(area), "ground": round(ground, 2), "freeboard": free, "depth": depth,
                       "level": round(ground - free, 2), "basis": "dem_shore", "src": "osm",
                       "ring": [[round(x, 2), round(y, 2)] for x, y in ring],
                       "inners": [[[round(x, 2), round(y, 2)] for x, y in i] for i in inners]})
        shores += shore_runs(ring, land, bi, 0)
        for k, isl in enumerate(inners):
            shores += shore_runs(isl, land, bi, k + 1)

    piers = [{"id": w["id"], "ring": [[round(x, 2), round(y, 2)] for x, y in _clean_ring(w["pts"])]}
             for w in DATA["ways"] if w["closed"] and w["tags"].get("man_made") == "pier" and in_park(w["pts"])]

    def body_at(x, y):
        for i, b in enumerate(bodies):
            if point_in_poly(x, y, b["ring"]) and not any(point_in_poly(x, y, h) for h in b["inners"]):
                return i
        return None
    falls = []
    for w in DATA["ways"]:
        if "waterway" in w["tags"] and not w["closed"] and point_in_poly(*w["pts"][0], PARK):
            a, z = body_at(*w["pts"][0]), body_at(*w["pts"][-1])
            if a is not None and z is not None and a != z:
                dz = bodies[a]["level"] - bodies[z]["level"]
                if abs(dz) > 0.15:
                    falls.append({"way": w["id"], "from": a, "to": z, "drop": round(dz, 2),
                                  "l": [[round(x, 2), round(y, 2)] for x, y in w["pts"]]})
    counts = {}
    for s in shores:
        counts[s["t"]] = counts.get(s["t"], 0) + sum(math.dist(s["l"][i], s["l"][i + 1]) for i in range(len(s["l"]) - 1))
    data = {"datum_m": round(LV.DATUM, 3), "note": "levels are relative to the DisneySea promenade datum (DEM5A median of paths)",
            "park": [[round(x, 2), round(y, 2)] for x, y in PARK],
            "profiles": {k: {"freeboard": v[0], "depth": v[1]} for k, v in PROFILE.items()},
            "bodies": bodies, "tunnels": [], "shores": shores, "piers": piers, "falls": falls,
            "shore_length": {k: round(v) for k, v in counts.items()}}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = build()
    print(f"[tdl water] {OUT}  bodies={len(d['bodies'])} shores={len(d['shores'])} piers={len(d['piers'])} falls={len(d['falls'])}")
    print("[tdl water] shore length m:", d["shore_length"])
    for b in sorted(d["bodies"], key=lambda b: -b["area"])[:14]:
        print(f"  {b['id']:>12} {b['kind']:8} {b['area']:7} m2 level {b['level']:+.2f} (ground {b['ground']:+.2f}) {b['name']}")
