"""Clipped shrubs and topiary as specs, grown in the page (docs/plants/plan.md, phase 4).

The models build their clipped shrubs as plain solids in one mesh per material: balls (the entrance's spiral and
three-ball topiaries, World Bazaar's potted balls, globe_lamp_bm / ball()) and boxes (the hedges of the plaza hub,
Monsters, Inc., Stitch Encounter, the entrance's middle planter and the balconies). When compress_models.py makes the
web copy of a model, extract() splits those meshes into connected pieces and reads each piece that is clearly a ball
(every vertex on one ellipsoid) or a box (four corners at the bottom, four at the top, a rectangle in plan):

  ball  [0, x, y, centre z, radius east, radius north, radius up, 0]
  box   [1, x, y, bottom z, half length, half width, height, yaw]       (yaw: the length's direction, radians from east)

(mock metres, y north, z up). The pieces inside the confirmed zones (plant_zones.py) leave the visible mesh and go to
models/clips.json; plants.js grows each one from its spec (its own lumps from a seed of its position, leaf cards over
it, near / mid / far). They stay in the web copy as an invisible mesh `PL_clipcol`, so the walker still bumps into the
hedges. The other pieces (lathed mounds, the Mickey bed's bank, flat strips) stay as they are; the page gives them the
leaf material and scatters leaf cards over them. The plain models are not changed and no Blender script is touched.

  python src/clip_specs.py            # what extract() would read from every model (a dry run)
"""
import json, math, pathlib, re, sys, base64
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "output" / "disneysea" / "models"
OUT = MODELS / "clips.json"
MESH = re.compile(r"^(EN_hedge|WZ_wbz_topiary|WZ_hedge|PB_pb_hedge|PH_hedge|SE_hedge|TT_hedge)$")
MODEL_IDS = {"tdl_entrance", "tdl_world_bazaar", "tdl_plaza_buildings", "tdl_plaza_hub", "tdl_stitch_encounter",
             "tdl_tomorrowland_terrace"}
COL = "PL_clipcol"


def _components(P, I):
    """label per triangle: the connected piece it belongs to (vertices welded by position, 1 mm)"""
    key = np.round(P * 1000).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    par = np.arange(inv.max() + 1)
    def f(a):
        r = a
        while par[r] != r:
            r = par[r]
        while par[a] != r:
            par[a], a = r, par[a]
        return r
    for t in I:
        a = f(inv[t[0]])
        for v in (inv[t[1]], inv[t[2]]):
            b = f(v)
            if b != a:
                par[b] = a
    return np.array([f(inv[t[0]]) for t in I])


def classify(V, nt):
    """a spec (list) for a piece with welded vertices V (glTF axes, y up) and nt triangles, or None"""
    lo, hi = V.min(0), V.max(0); d = hi - lo; c = (lo + hi) / 2
    if d.min() < 0.02:
        return None
    if nt >= 24 and d.max() / d.min() < 1.3:                              # a ball: every vertex on the ellipsoid
        q = np.linalg.norm((V - c) / (d / 2), axis=1)
        if q.std() < 0.06 and abs(q.mean() - 1) < 0.08:
            return [0, round(float(c[0]), 2), round(float(-c[2]), 2), round(float(c[1]), 2),
                    round(float(d[0] / 2), 3), round(float(d[2] / 2), 3), round(float(d[1] / 2), 3), 0]
    if nt in (10, 12) and len(V) == 8:                                     # a box (the bottom may be open)
        ys = np.round(V[:, 1], 3)
        lv = sorted(set(ys.tolist()))
        if len(lv) != 2:
            return None
        top = V[ys == lv[1]]
        if len(top) != 4:
            return None
        p = top[:, [0, 2]]
        o = p.mean(0)
        dd = np.linalg.norm(p - p[0], axis=1)
        j1, j2 = np.argsort(dd)[1:3]
        e1, e2 = p[j1] - p[0], p[j2] - p[0]
        l1, l2 = np.linalg.norm(e1), np.linalg.norm(e2)
        if l1 < 0.05 or l2 < 0.05 or abs(np.dot(e1, e2)) / (l1 * l2) > 0.05:
            return None
        if np.linalg.norm(p[0] + e1 + e2 - p[np.argsort(dd)[3]]) > 0.02:
            return None
        if l1 < l2:
            e1, e2, l1, l2 = e2, e1, l2, l1
        yaw = math.atan2(-e1[1], e1[0])                                   # glTF (x, z) -> mock (x, -z)
        yaw = (yaw + math.pi / 2) % math.pi - math.pi / 2                 # a box has no front: -90 .. 90 degrees
        return [1, round(float(o[0]), 2), round(float(-o[1]), 2), round(float(lv[0]), 2),
                round(float(l1 / 2), 3), round(float(l2 / 2), 3), round(float(lv[1] - lv[0]), 3), round(yaw, 4)]
    return None


def extract(doc, blob, inside=None):
    """Take the balls and boxes of the clipped-shrub meshes out of a glTF doc (buffer `blob`, embedded). Returns
    (doc, blob, specs, stats). inside(x, y) -> bool keeps only the pieces in the confirmed zones (the rest are left to
    the zone filter)."""
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
                                 "type": "SCALAR", "min": [int(idx.min())], "max": [int(idx.max())]})
        return len(doc["accessors"]) - 1
    child = {c for n in doc.get("nodes", []) for c in n.get("children", [])}
    specs, stats, col = [], {}, []
    for n in doc.get("nodes", []):
        if "mesh" not in n:
            continue
        mesh = doc["meshes"][n["mesh"]]
        name = mesh.get("name") or n.get("name", "")
        if not MESH.match(name):
            continue
        if any(k in n for k in ("translation", "rotation", "scale", "matrix")) or doc["nodes"].index(n) in child:
            print(f"[clips] {name}: a transformed or child node, left as it is"); continue
        prims = []
        took = kept = 0
        for p in mesh["primitives"]:
            P = view(p["attributes"]["POSITION"]).astype(np.float64)
            I = (view(p["indices"]).reshape(-1) if "indices" in p else np.arange(len(P))).reshape(-1, 3)
            lab = _components(P, I)
            gone = np.zeros(len(I), bool)
            for l in np.unique(lab):
                ts = np.nonzero(lab == l)[0]
                V = np.unique(np.round(P[np.unique(I[ts].reshape(-1))], 4), axis=0)
                s = classify(V, len(ts))
                if s is None or (inside and not inside(s[1], s[2])):
                    continue
                specs.append(s); gone[ts] = True
            took += int(gone.sum()); kept += int((~gone).sum())
            if gone.any():
                col.append({**p, "indices": add_indices(I[gone].reshape(-1))})
            if gone.all():
                continue
            prims.append(p if not gone.any() else {**p, "indices": add_indices(I[~gone].reshape(-1))})
        if took:
            stats[name] = [took, kept]
            if prims:
                doc["meshes"][n["mesh"]] = {**mesh, "primitives": prims}
            else:
                del n["mesh"]
    if col:
        doc["meshes"].append({"name": COL, "primitives": col})
        doc["nodes"].append({"name": COL, "mesh": len(doc["meshes"]) - 1})
        sc = doc["scenes"][doc.get("scene", 0)]
        sc["nodes"] = sc.get("nodes", []) + [len(doc["nodes"]) - 1]
    while len(out) % 4:
        out.append(0)
    doc["buffers"][0]["byteLength"] = len(out)
    return doc, bytes(out), specs, stats


def load():
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}


def save(model_id, specs):
    d = load()
    d[model_id] = specs
    OUT.write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    import plant_zones
    for mid in sorted(MODEL_IDS):
        f = MODELS / f"{mid}.json"
        if not f.exists():
            print(mid, "no plain file"); continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        blob = base64.b64decode(doc["buffers"][0]["uri"].split(",", 1)[1])
        _, _, sp, st = extract(doc, blob, plant_zones.inside)
        print(mid, "balls", sum(s[0] == 0 for s in sp), "boxes", sum(s[0] == 1 for s in sp), st)
