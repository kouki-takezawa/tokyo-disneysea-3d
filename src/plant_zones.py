"""Plants only where the walk videos (or the user's photos) show them (user, 2026-10-06; docs/plants/confirmed_zones.md).

docs/plants/confirmed_zones.json holds
  routes   the walks of the two videos (v1 dusk, v2 day) as polylines in mock metres (x, y north), each with the time
           span it was read from and the distance "r" out to which the frames show the planting beside the path
  extra    polygons confirmed by a frame although the walk's view of them is hidden (the palms of Monsters, Inc.)
  remove   polygons taken out again (backstage, behind fences the frames do not see over)
  zones    the result: the confirmed area as polygons (rings), written by `python src/plant_zones.py build`

The area seen from a route is, per sample point every 6 m, the disc of radius r less the "shadows" of the buildings
(Land footprints over 40 m2: a building hides what stands behind it; a concave one, like the gate's arc, wall by
wall). The union of those, plus `extra`, less `remove`, simplified to 0.5 m, is `zones`. export_mock.py keeps only the trees, palms and shrubs inside it;
compress_models.py takes the plant triangles outside it out of the web copies of the models (the plain models stay
whole), and lays the lawns, wood floors and clipped-bed tops outside it as bare ground.

  python src/plant_zones.py build      # zones from the routes (shapely)
  python src/plant_zones.py check      # route segments that cross a building or a pond (WB's roof, the castle's tunnel,
                                       # the cave of Critter Country and the bridges are meant)
  python src/plant_zones.py stats      # how many of mock_data's trees lie inside
"""
import json, math, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILE = ROOT / "docs" / "plants" / "confirmed_zones.json"
STEP = 6.0

# plant meshes of the models (docs/plants/inventory.md): solid ones lose their triangles outside the zones ...
DROP = re.compile(r"^(PZ_Trunk|PZ_Canopy|AD_leaf|AD_leafr|AD_fern|PB_pb_hedge|WZ_wbz_topiary|WZ_wbz_leaf|WZ_hedge|"
                  r"WZ_flowers_|WZ_wbz_flowers_|HO_hotel_leaf|HO_hotel_fl|EN_hedge|EN_flower|WL_leaf|WL_fern|WL_grass|"
                  r"PH_hedge|PH_flower|SE_hedge|SE_flower|TT_hedge|TT_flower|TP_flower)")
# ... flat ones (lawns, wood floors, the tops the page clips into hedges) become ground there: new mesh name
def bare(name):
    m = re.match(r"^TL_(grass|wood)(_\w+)?$", name)
    if m:
        return "TL_ground" + (m.group(2) or "")
    if name.startswith("WS_grass"):
        return "WS_mud"
    if name.startswith("WG_grass"):
        return "WG_dirt"
    if re.match(r"^(TG_soil|TH_soil|TP_soil|AG_soil|WG_soil|PZ_Soil|EN_bed_lawn|EN_bed_lime|EN_bed_olive|BC_grass|CC_grass)", name):
        return "PL_bare"          # bare planting soil (mock_template MODEL_MAT)
    return None


def load():
    return json.loads(FILE.read_text(encoding="utf-8"))


_AREA = None
def area():
    """the confirmed area (shapely, prepared) or None if there is no zones file"""
    global _AREA
    if _AREA is None:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        from shapely.prepared import prep
        if not FILE.exists():
            return None
        z = load().get("zones") or []
        g = unary_union([Polygon(p["ring"], p.get("holes", [])).buffer(0) for p in z])
        _AREA = (g, prep(g))
    return _AREA


def inside(x, y):
    from shapely.geometry import Point
    a = area()
    return True if a is None else a[1].contains(Point(x, y))


def filter_flat(flat, stride):
    """keep the [x, y, ...] records of a flat list that lie inside the zones"""
    out = []
    for i in range(0, len(flat), stride):
        if inside(flat[i], flat[i + 1]):
            out += flat[i:i + stride]
    return out


def filter_doc(doc, blob):
    """Take the plant triangles outside the zones out of a glTF doc (buffer `blob`, embedded); flat plant meshes
    outside become bare ground (a second primitive set under a new mesh/node). Returns (doc, blob, stats)."""
    import numpy as np
    from shapely import contains_xy
    a = area()
    if a is None:
        return doc, blob, {}
    geom = a[0]
    stats = {}
    out = bytearray(blob)
    def view(i):
        ac = doc["accessors"][i]; bv = doc["bufferViews"][ac["bufferView"]]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[ac["componentType"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[ac["type"]]
        st = bv.get("byteStride")
        if st and st != np.dtype(dt).itemsize * n:
            raise ValueError("strided accessor")
        return np.frombuffer(blob, dt, ac["count"] * n, bv.get("byteOffset", 0) + ac.get("byteOffset", 0)).reshape(-1, n)
    def add_indices(idx):
        idx = np.ascontiguousarray(idx.astype(np.uint32))
        while len(out) % 4:
            out.append(0)
        off = len(out); out.extend(idx.tobytes())
        doc["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": idx.nbytes, "target": 34963})
        doc["accessors"].append({"bufferView": len(doc["bufferViews"]) - 1, "componentType": 5125, "count": int(idx.size),
                                 "type": "SCALAR", "min": [int(idx.min())] if idx.size else [0], "max": [int(idx.max())] if idx.size else [0]})
        return len(doc["accessors"]) - 1
    new_nodes = []
    for ni, n in enumerate(list(doc.get("nodes", []))):
        if "mesh" not in n:
            continue
        mesh = doc["meshes"][n["mesh"]]
        name = mesh.get("name") or n.get("name", "")
        to = None if DROP.match(name) else bare(name)
        if not DROP.match(name) and not to:
            continue
        prims_in, prims_out = [], []
        kept = gone = 0
        for p in mesh["primitives"]:
            P = view(p["attributes"]["POSITION"])
            I = view(p["indices"]).reshape(-1) if "indices" in p else np.arange(len(P), dtype=np.uint32)
            T = I.reshape(-1, 3)
            c = P[T].mean(axis=1)                       # triangle centroids; mock x = x, y = -z
            ok = contains_xy(geom, c[:, 0].astype(float), -c[:, 2].astype(float))
            kept += int(ok.sum()); gone += int((~ok).sum())
            if ok.all():
                prims_in.append(p); continue
            if ok.any():
                q = dict(p); q["indices"] = add_indices(T[ok].reshape(-1)); prims_in.append(q)
            if to and (~ok).any():
                q = dict(p); q["indices"] = add_indices(T[~ok].reshape(-1)); prims_out.append(q)
        if not gone:
            continue
        stats[name] = stats.get(name, [0, 0]); stats[name][0] += kept; stats[name][1] += gone
        if prims_in:
            doc["meshes"][n["mesh"]] = {**mesh, "primitives": prims_in}
        else:
            del n["mesh"]
        if prims_out:
            doc["meshes"].append({"name": to, "primitives": prims_out})
            new_nodes.append({"name": to, "mesh": len(doc["meshes"]) - 1})
    if new_nodes:
        base = len(doc["nodes"]); doc["nodes"] += new_nodes
        sc = doc["scenes"][doc.get("scene", 0)]
        sc["nodes"] = sc.get("nodes", []) + list(range(base, base + len(new_nodes)))
    while len(out) % 4:
        out.append(0)
    doc["buffers"][0]["byteLength"] = len(out)
    return doc, bytes(out), stats


def check(cfg, D):
    """route segments that cross a building or a pond (a waypoint to fix)"""
    from shapely.geometry import LineString, Polygon
    obst = [("bldg", Polygon(b["r"][0]).buffer(0)) for b in D["disneyland"]["buildings"]]
    obst += [("water", Polygon(w).buffer(0)) for w in D["disneyland"]["water"]]
    obst = [(k, g) for k, g in obst if g.area >= 40.0]
    bad = []
    for r in cfg["routes"]:
        for a, b in zip(r["pts"], r["pts"][1:]):
            L = LineString([a, b])
            for k, g in obst:
                if L.crosses(g) or L.within(g):
                    x = L.intersection(g)
                    if x.length > 3.0:
                        bad.append((r["id"], a, b, k, round(x.length, 1), [round(v) for v in g.centroid.coords[0]]))
    return bad


def build():
    from shapely.geometry import LineString, Point, Polygon, MultiPoint, mapping
    from shapely.ops import unary_union
    from shapely.strtree import STRtree
    cfg = load()
    D = json.loads((ROOT / "output" / "disneysea" / "mock_data.json").read_text(encoding="utf-8"))
    for b in check(cfg, D):
        print("[zones] crosses", *b)
    fps = []
    for b in D["disneyland"]["buildings"]:
        try:
            g = Polygon(b["r"][0]).buffer(0)
        except Exception:
            continue
        if g.area >= 40.0:
            fps.append(g)
    idx = STRtree(fps)
    seen = []
    for r in cfg["routes"]:
        R = float(r.get("r", cfg.get("radius", 30)))
        line = LineString(r["pts"])
        n = max(1, int(line.length / STEP))
        parts = []
        for k in range(n + 1):
            p = line.interpolate(k / n, normalized=True)
            disc = p.buffer(R, 24)
            sh = []
            for j in idx.query(disc):
                B = fps[j]
                if B.contains(p) or B.distance(p) < 0.5:   # under the glass roof / at a door: the roof does not hide
                    continue
                vs = list(B.exterior.coords)
                far = []
                for (x, y) in vs:
                    dx, dy = x - p.x, y - p.y; d = math.hypot(dx, dy) or 1e-6
                    far.append((x + dx / d * 2.5 * R, y + dy / d * 2.5 * R))
                if B.convex_hull.area < B.area * 1.05:            # convex: the hull of the corners and their projections
                    sh.append(MultiPoint(vs + far).convex_hull)
                else:                                            # concave (the gate's arc): each wall's own shadow
                    sh.append(unary_union([B] + [Polygon([vs[i], vs[i + 1], far[i + 1], far[i]]).buffer(0)
                                                 for i in range(len(vs) - 1)]))
            vis = disc.difference(unary_union(sh)) if sh else disc
            parts.append(vis)
        seen.append(unary_union(parts))
        print(f"[zones] {r['id']}: {line.length:.0f} m, r {R:.0f}")
    g = unary_union(seen + [Polygon(e["ring"]) for e in cfg.get("extra", [])])
    for e in cfg.get("remove", []):
        g = g.difference(Polygon(e["ring"]))
    g = g.simplify(0.5).buffer(0)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    cfg["zones"] = [{"ring": [[round(x, 1), round(y, 1)] for x, y in p.exterior.coords],
                     "holes": [[[round(x, 1), round(y, 1)] for x, y in h.coords] for h in p.interiors]}
                    for p in polys if p.area > 4.0]
    txt = json.dumps(cfg, ensure_ascii=False, indent=1)
    txt = re.sub(r"\[\s+(-?[\d.]+),\s+(-?[\d.]+)\s+\]", r"[\1, \2]", txt)     # one point per line, not three
    FILE.write_text(txt, encoding="utf-8")
    print(f"[zones] {len(cfg['zones'])} polygons, {g.area / 1e4:.1f} ha")


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build()
    elif sys.argv[1:2] == ["check"]:
        D = json.loads((ROOT / "output" / "disneysea" / "mock_data.json").read_text(encoding="utf-8"))
        for b in check(load(), D):
            print(*b)
    else:
        D = json.loads((ROOT / "output" / "disneysea" / "mock_data.json").read_text(encoding="utf-8"))
        t = D["trees3d"]; k = sum(inside(t[i], t[i + 1]) for i in range(0, len(t), 3))
        print("trees", k, "/", len(t) // 3)
