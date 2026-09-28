"""東京ディズニーランドのエントランス周りの建物 -- the buildings round the entrance plaza and World Bazaar that had no model yet
(Blender 5.2): the promenade buildings either side of the plaza, the security-check canopies, the small service buildings,
a shop block west of World Bazaar, and the Monsters, Inc. building (outside only).

  blender -b --python src/ds_tdl_plaza_buildings.py -- --cams plaza_east,plaza_west,monsters,aerial --samples 32
  blender -b --python src/export_models.py -- --parts tdl_plaza_buildings

Sources (looked at only): OSM outlines (plateau_data/disneyland_osm.json, the ids in BUILDINGS). Commons photos
(2023-2024): the small buildings on the walkways have cream walls, dark-green slate roofs and cream awnings; the
Monsters, Inc. building is a tan stucco box with a stepped tower carrying the round blue logo, a faceted glass dome
skylight and a colonnade of square piers along its front.

Frame: the mock's local metres (origin 35.6267N 139.8851E, +x east, +y north), z up; each building stands on its own
ground in the export (the plaza, Land and hotel ground models).

ESTIMATES: every height and the style of each building (no photo shows most of them); the Monsters, Inc. tower's and
dome's size and places.
"""
import sys, math, json, argparse, pathlib, time, random

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix
except ImportError:
    bpy = bmesh = Vector = Matrix = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_tdl_station as ST
from ds_tdl_station import (B, box, prism, bm_box, bm_prism, bm_lathe, obj_bm, T, R, seg_arc, arch_opening, arch_band,
                            column_bm, globe_lamp_bm, text, _principled, _mottle)
from ds_tdl_entrance import frame

OUT = ROOT / "output" / "disneyland" / "plaza_buildings"
# id: (kind, height to the eaves, wall, trim, roof)
BUILDINGS = {
    203538205: ("promenade", 6.5, "pb_cream", "pb_white", "pb_green"),     # east of the plaza (Guest Relations / Promenade Gift East)
    119894892: ("promenade", 6.5, "pb_cream", "pb_white", "pb_green"),     # west of the plaza (Promenade Gift)
    217617126: ("promenade", 5.5, "pb_sand", "pb_white", "pb_green"),
    196942899: ("shop", 8.5, "pb_pink", "pb_white", "pb_slate"),           # west of World Bazaar
    1297667569: ("shop", 5.0, "pb_sand", "pb_white", "pb_green"),
    217842047: ("service", 4.2, "pb_cream", "pb_white", "pb_green"),       # toilets
    97767471: ("service", 3.6, "pb_cream", "pb_white", "pb_green"),
    1338996038: ("service", 3.6, "pb_cream", "pb_white", "pb_green"),
    1338996037: ("service", 3.6, "pb_cream", "pb_white", "pb_green"),
    1292415139: ("service", 3.6, "pb_cream", "pb_white", "pb_green"),
    218553048: ("canopy", 3.6, None, "pb_white", "pb_green"),               # security check
    203538203: ("canopy", 3.6, None, "pb_white", "pb_green"),               # security check
    1295097122: ("canopy", 3.2, None, "pb_white", "pb_green"),
    1338996034: ("canopy", 3.4, None, "pb_white", "pb_green"),
    1298497967: ("canopy", 3.2, None, "pb_white", "pb_green"),
    217930681: ("monsters", 12.0, "pb_tan", "pb_white", "pb_tan"),          # Monsters, Inc. Ride & Go Seek (outside only)
}


def materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    for k, c in (("pb_cream", (0.90, 0.84, 0.68)), ("pb_sand", (0.86, 0.74, 0.56)), ("pb_pink", (0.86, 0.66, 0.62)),
                 ("pb_tan", (0.80, 0.68, 0.52))):
        mat, nt, b = _principled("st_" + k, c, 0.7); _mottle(nt, b, c, 6.0, 0.93, 0.03); M[k] = mat
    M["pb_white"] = P("st_pb_white", (0.94, 0.93, 0.89), 0.5)
    M["pb_green"] = P("st_pb_green", (0.16, 0.30, 0.24), 0.55)
    M["pb_slate"] = P("st_pb_slate", (0.26, 0.31, 0.40), 0.5)
    M["pb_awning"] = P("st_pb_awning", (0.93, 0.90, 0.80), 0.8)
    M["pb_glass"] = P("st_pb_glass", (0.08, 0.10, 0.12), 0.15, Coat_Weight=1.0)
    M["pb_display"] = P("st_pb_display", (0.85, 0.75, 0.55), 0.3, Emission_Color=(1.0, 0.85, 0.6, 1), Emission_Strength=0.5)
    M["pb_blue"] = P("st_pb_blue", (0.10, 0.35, 0.75), 0.4)
    M["pb_dome"] = ST.clear_glass("st_pb_dome", (0.70, 0.85, 0.90), 0.45)
    M["pb_iron"] = P("st_pb_iron", (0.10, 0.12, 0.12), 0.4, Metallic=0.5)
    return M


def cw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts[::-1] if a > 0 else pts


def simplify(pts, tol=0.4):
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    if len(out) > 3 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < tol:
        out.pop()
    return out


def inset(pts, d):
    """The ring moved d inwards (miter at the corners; fine for the small, mostly convex outlines here)."""
    n = len(pts); out = []
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        n1 = (b[1] - a[1], -(b[0] - a[0])); l1 = math.hypot(*n1) or 1; n1 = (n1[0] / l1, n1[1] / l1)
        n2 = (c[1] - b[1], -(c[0] - b[0])); l2 = math.hypot(*n2) or 1; n2 = (n2[0] / l2, n2[1] / l2)
        m = (n1[0] + n2[0], n1[1] + n2[1]); lm = math.hypot(*m) or 1; m = (m[0] / lm, m[1] / lm)
        k = d / max(0.35, m[0] * n1[0] + m[1] * n1[1])
        out.append((b[0] - m[0] * k, b[1] - m[1] * k))   # clockwise ring: the edge normals point out, so inwards is minus
    return out


def facade(name, L, H, wall, trim, kind, rng):
    """One wall run (x 0..L, +y out, z up) of a promenade building / shop / service building."""
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "display", "awning", "iron")}
    bm_box(P["wall"], 0, L, -0.25, 0, 0, H)
    bm_box(P["trim"], 0, L, 0, 0.1, 0, 0.45)                                          # plinth
    bm_box(P["trim"], -0.05, L + 0.05, 0, 0.35, H - 0.35, H)                           # cornice
    nb = max(1, round(L / (4.0 if kind != "service" else 3.2))) if L >= 2.4 else 0
    for k in range(nb):
        x0, x1 = L * k / nb, L * (k + 1) / nb; m = (x0 + x1) / 2
        bm_box(P["trim"], x0, x0 + 0.3, 0, 0.12, 0, H - 0.35)                          # pilaster
        if x1 - x0 < 2.2:
            continue
        if kind == "service":                                                           # a door or a small window
            if k % 2 == 0:
                bm_box(P["trim"], m - 0.6, m + 0.6, 0, 0.08, 0, 2.4); bm_box(P["glass"], m - 0.5, m + 0.5, 0.08, 0.1, 0, 2.3)
            else:
                bm_box(P["trim"], m - 0.55, m + 0.55, 0, 0.08, 1.2, 2.5); bm_box(P["glass"], m - 0.45, m + 0.45, 0.08, 0.1, 1.3, 2.4)
            continue
        # shop window / arched window and an awning over it
        bm_prism(P["trim"], arch_opening(m - 1.2, m + 1.2, 0.45, 2.9, 0.55, 12), 0.0, 0.1, "xz")
        bm_prism(P["display" if rng.random() < 0.6 else "glass"], arch_opening(m - 1.05, m + 1.05, 0.5, 2.85, 0.45, 10), 0.1, 0.12, "xz")
        bm_prism(P["awning"], [(0.15, 3.55), (1.3, 3.05), (1.3, 2.95), (0.15, 3.42)], m - 1.3, m + 1.3, "yz")
        for j in range(5):                                                               # the awning's scalloped edge
            xx = m - 1.3 + 2.6 * (j + 0.5) / 5
            bm_lathe(P["awning"], [(0, -0.12), (0.26, 0), (0, 0.001)], 8, T(xx, 1.3, 2.95) @ R(math.pi / 2, "X"))
        if H > 6.0:                                                                      # upper windows
            z0 = 4.3
            bm_box(P["trim"], m - 0.65, m + 0.65, 0, 0.08, z0 - 0.1, z0 + 1.8)
            bm_box(P["glass"], m - 0.52, m + 0.52, 0.08, 0.1, z0, z0 + 1.65)
            bm_box(P["trim"], m - 0.78, m + 0.78, 0, 0.25, z0 + 1.7, z0 + 1.9)
            bm_box(P["trim"], m - 0.8, m + 0.8, 0, 0.3, z0 - 0.3, z0 - 0.15)
        if k % 2 == 1:
            globe_lamp_bm(P["display"], m - 1.55, 0.3, 2.6, 0.1)
    for k, bm_ in P.items():
        if not len(bm_.verts):
            bm_.free(); continue
        mat = {"wall": wall, "trim": trim, "glass": "pb_glass", "display": "pb_display", "awning": "pb_awning", "iron": "pb_iron"}[k]
        obj_bm(f"PB_{name}_{k}", bm_, mat)


def roof(name, pts, H, mat, pitch=2.2, d=1.8):
    """A mansard-like roof: a slope from the eaves in by d and up by pitch, then a flat top."""
    top = inset(pts, d)
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, H)) for x, y in pts]; hi = [bm.verts.new((x, y, H + pitch)) for x, y in top]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(hi)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    obj_bm(f"PB_{name}_roof", bm, mat, recalc=False)


def building(bid, pts, kind, H, wall, trim, rmat):
    rng = random.Random(bid)
    pts = cw(simplify(pts))
    if kind == "canopy":                                   # posts round the outline, a thin roof, a shallow hip
        bmp = bmesh.new()
        n = len(pts)
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            L = math.hypot(x1 - x0, y1 - y0); m = max(1, int(L / 4.0))
            for k in range(m):
                x, y = x0 + (x1 - x0) * k / m, y0 + (y1 - y0) * k / m
                bm_lathe(bmp, [(0, 0), (0.14, 0), (0.1, 0.3), (0.08, H - 0.3), (0.14, H - 0.15), (0, H)], 8, T(x, y, 0))
        obj_bm(f"PB_{bid}_posts", bmp, trim, smooth=True)
        prism(f"PB_{bid}_slab", [pts], H, H + 0.3, trim)
        roof(bid, pts, H + 0.3, rmat, pitch=1.0, d=min(1.5, 0.3 * min(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) for i in range(n))))
        return
    if kind == "monsters":
        monsters(bid, pts, H)
        return
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 0.3:
            continue
        with frame(f"PB_{bid}_run{i}", x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0))):
            facade(f"{bid}_{i}", L, H, wall, trim, kind, rng)
    prism(f"PB_{bid}_deck", [pts], H - 0.2, H, rmat)
    short = min(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) for i in range(len(pts)))
    roof(bid, pts, H, rmat, pitch=2.4 if kind != "service" else 1.4, d=min(2.0, max(0.6, short * 0.3)))


def monsters(bid, pts, H):
    """Monsters, Inc. (photos): a tan stucco box, a colonnade of square piers along its longest side, a stepped tower
    with the round blue logo, a faceted glass dome on the roof."""
    n = len(pts)
    prism(f"PB_{bid}_body", [pts], 0, H, "pb_tan")
    prism(f"PB_{bid}_cornice", [inset(pts, -0.3)], H - 0.5, H, "pb_white")
    i_long = max(range(n), key=lambda i: math.hypot(pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1]))
    (x0, y0), (x1, y1) = pts[i_long], pts[(i_long + 1) % n]
    L = math.hypot(x1 - x0, y1 - y0)
    with frame(f"PB_{bid}_front", x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0))):
        bmp, bmr, bmb = bmesh.new(), bmesh.new(), bmesh.new()
        k = max(2, int(L / 4.5))
        for j in range(k + 1):                                                          # the colonnade
            x = 1.0 + (L - 2.0) * j / k
            bm_box(bmp, x - 0.4, x + 0.4, 3.2, 4.0, 0, 4.6)
        bm_box(bmr, 0.4, L - 0.4, 0, 4.2, 4.6, 5.1)
        # the stepped tower with the logo, at the middle of the front
        m = L / 2
        for s, (w_, h_) in enumerate(((7.0, H + 3.0), (5.0, H + 6.0), (3.4, H + 8.0))):
            bm_box(bmr if s % 2 == 0 else bmp, m - w_ / 2, m + w_ / 2, -3.5 + s * 0.4, 0.4 - s * 0.2, 0, h_)
        bm_lathe(bmb, [(0, 0), (2.0, 0), (2.0, 0.2), (0, 0.2)], 32, T(m, 0.42, H + 3.5) @ R(-math.pi / 2, "X"))
        bm_lathe(bmr, [(1.9, 0), (2.25, 0), (2.25, 0.3), (1.9, 0.3)], 32, T(m, 0.4, H + 3.5) @ R(-math.pi / 2, "X"))
        obj_bm(f"PB_{bid}_piers", bmp, "pb_white"); obj_bm(f"PB_{bid}_tower", bmr, "pb_tan"); obj_bm(f"PB_{bid}_logo", bmb, "pb_blue")
        text(f"PB_{bid}_logotext", "MONSTERS, INC.", 0.42, (m, 0.65, H + 3.5), (math.pi / 2, 0, math.pi), "pb_white", 0.03)
    cx = sum(x for x, _ in pts) / n; cy = sum(y for _, y in pts) / n                   # the faceted glass dome
    r = max(4.0, min(9.0, math.sqrt(abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2)) * 0.25))
    bmd = bmesh.new()
    bm_lathe(bmd, [(r, 0)] + [(r * math.cos(math.pi / 2 * i / 4), r * 0.75 * math.sin(math.pi / 2 * i / 4)) for i in range(1, 5)], 10, T(cx, cy, H))
    obj_bm(f"PB_{bid}_dome", bmd, "pb_dome")
    bmf = bmesh.new()
    bm_lathe(bmf, [(r + 0.3, 0), (r + 0.3, 0.4), (r - 0.1, 0.4), (r - 0.1, 0)], 10, T(cx, cy, H))
    obj_bm(f"PB_{bid}_domering", bmf, "pb_white")


def build_all():
    ways = {w["id"]: w for w in json.loads((ROOT / "plateau_data" / "disneyland_osm.json").read_text(encoding="utf-8"))["ways"]}
    for bid, (kind, H, wall, trim, rmat) in BUILDINGS.items():
        w = ways.get(bid)
        if w:
            building(bid, [tuple(p) for p in w["pts"][:-1]], kind, H, wall, trim, rmat)


# ================================================================ for the mock (export_models.py --parts tdl_plaza_buildings)
def ground_sampler():
    """The mock's ground height at (x, y): the plaza, Land and hotel ground models (median of the vertices within 6 m)."""
    import base64, numpy as np
    P = []
    for fn in ("tdl_ground.json", "tdl_land_ground.json", "tdl_hotel_ground.json"):
        f = ROOT / "output" / "disneysea" / "models" / fn
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        buf = base64.b64decode(d["buffers"][0]["uri"].split(",")[1])
        for m in d["meshes"]:
            for p in m["primitives"]:
                a = d["accessors"][p["attributes"]["POSITION"]]; bv = d["bufferViews"][a["bufferView"]]
                off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
                P.append(np.frombuffer(buf, dtype=np.float32, count=a["count"] * 3, offset=off).reshape(-1, 3))
    P = np.vstack(P); X, Z, Y = P[:, 0], P[:, 1], -P[:, 2]
    def g(x, y):
        d2 = (X - x) ** 2 + (Y - y) ** 2
        near = d2 < 36.0
        return float(np.median(Z[near])) if near.any() else float(Z[np.argmin(d2)])
    return g


def export_objects(merged):
    """One mesh per material ("PB_<material>"); each building on the ground at its outline (the lowest of its corners)."""
    build()
    ways = {w["id"]: w for w in json.loads((ROOT / "plateau_data" / "disneyland_osm.json").read_text(encoding="utf-8"))["ways"]}
    g = ground_sampler()
    base = {bid: min(g(x, y) for x, y in ways[bid]["pts"][:-1]) for bid in BUILDINGS if bid in ways}
    bpy.context.view_layer.update()
    groups = {}
    for o in B.col.objects:
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith("CAM_"):
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if not mats:
            continue
        bid = int(o.name.split("_")[1]) if o.name.split("_")[1].isdigit() else None
        groups.setdefault("PB_" + mats[0].name[3:], []).append((o, base.get(bid, 0.0)))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


# ================================================================ scene
def cams():
    return {
        "plaza_east": ((-470.0, 950.0, 1.7), (-437.0, 925.0, 4.0), 24),
        "plaza_west": ((-560.0, 870.0, 1.7), (-593.0, 861.0, 4.0), 24),
        "monsters": ((-560.0, 760.0, 6.0), (-613.0, 798.0, 8.0), 24),
        "aerial": ((-450.0, 760.0, 160.0), (-540.0, 880.0, 0.0), 30),
    }


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    B.col = bpy.data.collections.new("TDL_PlazaBuildings"); sc.collection.children.link(B.col)
    B.cutters = bpy.data.collections.new("Cutters"); sc.collection.children.link(B.cutters)
    B.root = bpy.data.objects.new("TDL_PlazaBuildings", None); B.col.objects.link(B.root)
    B.hide = []
    B.M = materials(ST.materials())
    t0 = time.time()
    build_all()
    box("CTX_ground", (-700, -380, 700, 1080, -0.2, 0.0), "paving")
    out = {}
    for name, (loc, tgt, lens) in cams().items():
        cam = bpy.data.cameras.new("CAM_" + name); cam.lens = lens; cam.clip_start = 0.05; cam.clip_end = 3000
        co = bpy.data.objects.new("CAM_" + name, cam); B.col.objects.link(co); co.parent = B.root
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        out[name] = co
    print(f"[plaza buildings] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="plaza_east,plaza_west,monsters,aerial")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=60)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    cams_ = build()
    ST.world_sky()
    ST.frame_view()
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "tdl_plaza_buildings.blend").resolve()))
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        old = ST.OUT; ST.OUT = OUT
        try:
            ST.render(cams_, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES", "plaza")
        finally:
            ST.OUT = old


if __name__ == "__main__" and bpy is not None:
    main()
