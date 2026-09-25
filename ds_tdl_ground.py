"""東京ディズニーランドのエントランス広場の地面 -- the ground in front of and behind the main entrance gates
(plain Python: shapely + numpy, Blender is not needed; no trees).

  python ds_tdl_ground.py            # -> output/disneysea/models/tdl_ground.json (glTF, buffer embedded) + a summary
  python export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_ground", layer ディズニーランド)

What is modelled (OSM, plateau_data/disneyland_osm.json):
  paving   relation 17641752 (highway=pedestrian, "東京ディズニーランド メインエントランス"): the fan-shaped plaza between the gates
           and the Resort Line station, 23,700 m2  -> terracotta brick (the aerial photo shows pink paving with pale joint lines)
           relation 17641753: the plaza inside the gates, up to World Bazaar, 5,900 m2  -> dark slate (dark on the photo)
           the floor under the gate canopy (way 795427065) and the slivers between the areas  -> pale stone
  planters every inner ring of the two relations (36 + 11 tree beds and flowerbeds): a 0.30 m stone curb, 0.35 m wide, and a
           green top a little lower. Trees are left out (asked for: ground only). The rings inside the Mickey flowerbed's fence
           (ds_tdl_entrance.BED, radius 17 m) are the old flowerbed drawn in OSM: the model has its own bed there, so they are skipped.
Heights: the GSI DEM5A (ds_levels.dem, the mock's datum 5.29 m = 0), smoothed over ~5 m. Under the Blender entrance model (built on a flat 0
  plane: gates, flowerbed, white paving lines) the ground is flat at -0.03 m, blended into the DEM from FLAT_R0 to FLAT_R1 metres
  from the gates' centre. Farther out it follows the DEM: it falls 2.4 m to the west and 2 m to the station, as the DEM does.
Mesh: the paving is cut into CELL m cells (the height grid) and each piece is triangulated (constrained Delaunay), so the surface
  follows the terrain and the pieces meet exactly on the cell edges. A 0.15 m skirt hangs from the free edges.
ESTIMATES: the colours (aerial photo, washed out), the curb height and width, the skirt, the gate floor. The photo predates the
  2023 rebuild of the gates, so the paving pattern and the planters' contents are not checked against a photo of today.
"""
import sys, json, math, base64, pathlib

import numpy as np
import shapely
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ds_levels as LV
import ds_disneyland as DL

OUT = ROOT / "output" / "disneysea" / "models" / "tdl_ground.json"
REL_OUT, REL_IN, CANOPY_WAY = 17641752, 17641753, 795427065
BED_C, BED_R = (-538.0, 926.3), 19.0          # the Mickey flowerbed model (ds_tdl_entrance.BED: fence radius 17 m) + a margin
GATE_C = (-525.0, 897.0)                      # centre of the gates' arc (ds_tdl_entrance.ARC)
FLAT_Z, FLAT_R0, FLAT_R1 = -0.03, 75.0, 105.0   # flat under the entrance model, blended into the DEM out to FLAT_R1
CELL = 4.0                                    # height grid = cutting cells (m)
BLUR = 1.2                                    # DEM smoothing (cells)
CURB_H, CURB_W, SOIL_DROP, SKIRT = 0.30, 0.35, 0.06, 0.15
MIN_PLANTER = 2.0                             # m2


# ---------------------------------------------------------------- plan
def plan():
    rels = {r["id"]: r for r in DL.DATA["relations"]}

    def area(rid):
        r = rels[rid]
        outer = unary_union([Polygon(o).buffer(0) for o in DL.outer_rings(r)])
        holes = [Polygon(DL.WAYS[m["way"]]["pts"]).buffer(0) for m in r["members"]
                 if m["role"] == "inner" and m["way"] in DL.WAYS and len(DL.WAYS[m["way"]]["pts"]) >= 4]
        return Polygon(outer.exterior) if outer.geom_type == "Polygon" else outer, holes

    out_ext, out_holes = area(REL_OUT)
    in_ext, in_holes = area(REL_IN)
    canopy = Polygon(DL.WAYS[CANOPY_WAY]["pts"]).buffer(0)
    bed = Point(*BED_C).buffer(BED_R, 64)
    planters = []
    for p in out_holes + in_holes:
        if p.is_empty or p.area < MIN_PLANTER or p.centroid.distance(Point(*BED_C)) < BED_R:
            continue
        planters.append(p.intersection(out_ext.union(in_ext)))
    planters = [q for p in planters for q in _polys(p) if q.area >= MIN_PLANTER]
    pl_all = unary_union(planters)
    # paving zones: the outer plaza, the inner plaza, and the gate floor (the canopy + the slivers between the areas)
    closed = unary_union([out_ext, in_ext, canopy]).buffer(0.5, join_style=2).buffer(-0.5, join_style=2)
    z_out = out_ext.difference(pl_all)
    z_in = in_ext.difference(out_ext).difference(pl_all)
    z_gate = closed.difference(out_ext).difference(in_ext).difference(pl_all)
    z_gate = unary_union([g for g in _polys(z_gate) if g.area > 1.0])
    return dict(out=z_out, inn=z_in, gate=z_gate, planters=planters, closed=closed, bed=bed)


def _polys(g):
    return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty]


# ---------------------------------------------------------------- terrain
class Terrain:
    """The DEM on a CELL m grid, smoothed, flat under the entrance model; bilinear between the nodes."""
    def __init__(self, bounds):
        datum = json.loads((ROOT / "plateau_data" / "disneysea_levels.json").read_text(encoding="utf-8"))
        LV.DATUM = datum.get("datum_exact", datum["datum_m"])
        minx, miny, maxx, maxy = bounds
        self.i0, self.j0 = int(math.floor(minx / CELL)) - 2, int(math.floor(miny / CELL)) - 2
        ni, nj = int(math.ceil(maxx / CELL)) + 3 - self.i0, int(math.ceil(maxy / CELL)) + 3 - self.j0
        xs = (self.i0 + np.arange(ni)) * CELL
        ys = (self.j0 + np.arange(nj)) * CELL
        Z = np.array([[LV.dem(x, y) for x in xs] for y in ys], dtype=np.float32)      # [j, i]
        import cv2
        Z = cv2.GaussianBlur(Z, (0, 0), BLUR, borderType=cv2.BORDER_REPLICATE).astype(float)
        r = np.hypot(xs[None, :] - GATE_C[0], ys[:, None] - GATE_C[1])
        t = np.clip((FLAT_R1 - r) / (FLAT_R1 - FLAT_R0), 0, 1)
        w = t * t * (3 - 2 * t)
        self.Z = Z * (1 - w) + FLAT_Z * w
        self.ni, self.nj = ni, nj

    def _cell(self, x, y):
        gx, gy = x / CELL - self.i0, y / CELL - self.j0
        i = np.clip(np.floor(gx).astype(int), 0, self.ni - 2); j = np.clip(np.floor(gy).astype(int), 0, self.nj - 2)
        return i, j, np.clip(gx - i, 0, 1), np.clip(gy - j, 0, 1)

    def z(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        i, j, fx, fy = self._cell(x, y)
        Z = self.Z
        return Z[j, i] * (1 - fx) * (1 - fy) + Z[j, i + 1] * fx * (1 - fy) + Z[j + 1, i] * (1 - fx) * fy + Z[j + 1, i + 1] * fx * fy

    def grad(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        i, j, fx, fy = self._cell(x, y)
        Z = self.Z
        dx = ((1 - fy) * (Z[j, i + 1] - Z[j, i]) + fy * (Z[j + 1, i + 1] - Z[j + 1, i])) / CELL
        dy = ((1 - fx) * (Z[j + 1, i] - Z[j, i]) + fx * (Z[j + 1, i + 1] - Z[j, i + 1])) / CELL
        return dx, dy


# ---------------------------------------------------------------- mesh
class Mesh:
    """Triangles in plan coordinates (x east, y north, z up); one Mesh per material (glTF mesh name)."""
    def __init__(self, name):
        self.name = name
        self.tris = []        # (3, 3) arrays
        self.nrm = []         # (3, 3) arrays, per corner

    def add(self, tri, nrm):
        self.tris.append(np.asarray(tri, float)); self.nrm.append(np.asarray(nrm, float))


def cdt(poly):
    """Constrained Delaunay triangles of a polygon (with holes), counter-clockwise seen from above."""
    poly = shapely.geometry.polygon.orient(poly.buffer(0), 1.0) if poly.geom_type == "Polygon" else poly
    out = []
    for g in _polys(poly):
        for t in shapely.constrained_delaunay_triangles(g).geoms:
            c = np.array(t.exterior.coords[:3])
            if t.area < 1e-6:
                continue
            if (c[1, 0] - c[0, 0]) * (c[2, 1] - c[0, 1]) - (c[1, 1] - c[0, 1]) * (c[2, 0] - c[0, 0]) < 0:
                c = c[[0, 2, 1]]
            out.append(c)
    return out


def top_surface(mesh, T, poly, dz=0.0, cut=None):
    """The terrain (+ dz) over `poly` as triangles, cell by cell so the mesh follows the height grid. Returns the triangles."""
    tris = []
    minx, miny, maxx, maxy = poly.bounds
    for i in range(int(math.floor(minx / CELL)), int(math.ceil(maxx / CELL))):
        for j in range(int(math.floor(miny / CELL)), int(math.ceil(maxy / CELL))):
            piece = poly.intersection(box(i * CELL, j * CELL, (i + 1) * CELL, (j + 1) * CELL))
            if piece.is_empty or piece.area < 1e-4:
                continue
            tris += cdt(piece)
    for c in tris:
        z = T.z(c[:, 0], c[:, 1]) + dz
        dx, dy = T.grad(c[:, 0], c[:, 1])
        n = np.stack([-dx, -dy, np.ones(3)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
        mesh.add(np.column_stack([c[:, :2], z]), n)
    return tris


def wall(mesh, a, b, za, zb, zla, zlb):
    """A vertical quad under the directed edge a->b (plan points) from the top heights za, zb down to zla, zlb; it faces to the right of a->b."""
    (ax, ay), (bx, by) = a, b
    L = math.hypot(bx - ax, by - ay)
    if L < 1e-6:
        return
    n = np.array([(by - ay) / L, -(bx - ax) / L, 0.0])
    ab, bb = (ax, ay, zla), (bx, by, zlb)
    at, bt = (ax, ay, za), (bx, by, zb)
    mesh.add([ab, bb, bt], [n, n, n]); mesh.add([ab, bt, at], [n, n, n])


def free_edges(tris):
    """Directed edges used by exactly one triangle (the outline of the triangulated surface)."""
    count = {}
    key = lambda p: (round(p[0] * 1000), round(p[1] * 1000))
    for c in tris:
        for k in range(3):
            a, b = c[k], c[(k + 1) % 3]
            count.setdefault((key(a), key(b)), (a, b))
    return [(a, b) for (ka, kb), (a, b) in count.items() if (kb, ka) not in count]


def build():
    P = plan()
    zones = [("TG_paving", P["out"]), ("TG_slate", P["inn"]), ("TG_gate", P["gate"])]
    T = Terrain(unary_union([g for _, g in zones] + P["planters"]).bounds)
    meshes = {n: Mesh(n) for n in ("TG_paving", "TG_slate", "TG_gate", "TG_curb", "TG_soil", "TG_edge")}
    pl_lines = unary_union([q.exterior for q in P["planters"]])
    n_free = 0
    for name, g in zones:
        if g.is_empty:
            continue
        tris = []
        for poly in _polys(g):
            tris += top_surface(meshes[name], T, poly)
        for a, b in free_edges(tris):                                     # skirt on the free edges, except where a curb stands
            if pl_lines.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < 0.05:
                continue
            za, zb = float(T.z(a[0], a[1])), float(T.z(b[0], b[1]))
            wall(meshes["TG_edge"], a, b, za, zb, za - SKIRT, zb - SKIRT)
            n_free += 1
    for q in P["planters"]:
        q = shapely.geometry.polygon.orient(q, 1.0)
        q_in = q.buffer(-CURB_W, join_style=2)
        ring = q.difference(q_in) if not q_in.is_empty else q
        tris = []
        for poly in _polys(ring):
            for c in cdt(poly):
                z = T.z(c[:, 0], c[:, 1]) + CURB_H
                dx, dy = T.grad(c[:, 0], c[:, 1])
                n = np.stack([-dx, -dy, np.ones(3)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
                meshes["TG_curb"].add(np.column_stack([c[:, :2], z]), n); tris.append(c)
        qline = q.exterior
        for a, b in free_edges(tris):                                     # outer face down to the paving, inner face down to the soil
            za, zb = float(T.z(a[0], a[1])) + CURB_H, float(T.z(b[0], b[1])) + CURB_H
            if qline.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < 0.03:
                wall(meshes["TG_curb"], a, b, za, zb, za - CURB_H - 0.02, zb - CURB_H - 0.02)
            else:
                wall(meshes["TG_curb"], a, b, za, zb, za - SOIL_DROP, zb - SOIL_DROP)
        for poly in _polys(q_in):
            for c in cdt(poly):
                z = T.z(c[:, 0], c[:, 1]) + CURB_H - SOIL_DROP
                dx, dy = T.grad(c[:, 0], c[:, 1])
                n = np.stack([-dx, -dy, np.ones(3)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
                meshes["TG_soil"].add(np.column_stack([c[:, :2], z]), n)
    return P, T, meshes


# ---------------------------------------------------------------- glTF
def write_gltf(path, meshes):
    """Self-contained glTF 2.0 JSON (no materials: the mock colours the meshes by name). Plan (x, y, z) -> glTF (x, z, -y)."""
    buf = bytearray()
    views, accs, gmeshes, nodes = [], [], [], []

    def add_view(data, target):
        while len(buf) % 4:
            buf.append(0)
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(data), "target": target})
        buf.extend(data)
        return len(views) - 1

    for m in meshes.values():
        if not m.tris:
            continue
        P = np.concatenate(m.tris); N = np.concatenate(m.nrm)
        P = P[:, [0, 2, 1]] * np.array([1, 1, -1]); N = N[:, [0, 2, 1]] * np.array([1, 1, -1])
        key = np.concatenate([np.round(P * 1000), np.round(N * 1000)], 1).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        Pv = P[first].astype(np.float32); Nv = N[first].astype(np.float32); idx = inv.reshape(-1).astype(np.uint32)
        v_pos, v_nrm, v_idx = add_view(Pv.tobytes(), 34962), add_view(Nv.tobytes(), 34962), add_view(idx.tobytes(), 34963)
        a0 = len(accs)
        accs.append({"bufferView": v_pos, "componentType": 5126, "count": len(Pv), "type": "VEC3",
                     "min": Pv.min(0).tolist(), "max": Pv.max(0).tolist()})
        accs.append({"bufferView": v_nrm, "componentType": 5126, "count": len(Nv), "type": "VEC3"})
        accs.append({"bufferView": v_idx, "componentType": 5125, "count": len(idx), "type": "SCALAR"})
        gmeshes.append({"name": m.name, "primitives": [{"attributes": {"POSITION": a0, "NORMAL": a0 + 1}, "indices": a0 + 2, "mode": 4}]})
        nodes.append({"name": m.name, "mesh": len(gmeshes) - 1})
    doc = {"asset": {"version": "2.0", "generator": "ds_tdl_ground.py"}, "scene": 0,
           "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": gmeshes,
           "accessors": accs, "bufferViews": views,
           "buffers": [{"byteLength": len(buf), "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(buf)).decode()}]}
    path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return sum(len(m.tris) for m in meshes.values())


def main():
    P, T, meshes = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = write_gltf(OUT, meshes)
    zs = np.concatenate([np.array(m.tris)[:, :, 2].ravel() for m in meshes.values() if m.tris])
    print(f"[ground] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles, z {zs.min():.2f} .. {zs.max():.2f} m")
    print("  areas m2: outer paving %.0f, inner paving %.0f, gate floor %.0f, %d planters %.0f" % (
        P["out"].area, P["inn"].area, P["gate"].area, len(P["planters"]), sum(q.area for q in P["planters"])))
    print("  triangles:", {k: len(m.tris) for k, m in meshes.items()})


if __name__ == "__main__":
    main()
