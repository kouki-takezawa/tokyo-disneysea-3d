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
    217930681: ("monsters", 11.0, "pb_tan", "pb_white", "pb_tan"),          # Monsters, Inc. Ride & Go Seek (outside only)
}


def materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    for k, c in (("pb_cream", (0.90, 0.84, 0.68)), ("pb_sand", (0.86, 0.74, 0.56)), ("pb_pink", (0.86, 0.66, 0.62)),
                 ("pb_tan", (0.84, 0.71, 0.48))):
        mat, nt, b = _principled("st_" + k, c, 0.7); _mottle(nt, b, c, 6.0, 0.93, 0.03); M[k] = mat
    M["pb_white"] = P("st_pb_white", (0.94, 0.93, 0.89), 0.5)
    M["pb_green"] = P("st_pb_green", (0.16, 0.30, 0.24), 0.55)
    M["pb_slate"] = P("st_pb_slate", (0.26, 0.31, 0.40), 0.5)
    M["pb_awning"] = P("st_pb_awning", (0.93, 0.90, 0.80), 0.8)
    M["pb_stripe"] = P("st_pb_stripe", (0.20, 0.36, 0.30), 0.8)                    # the awnings' thin green stripes (photo)
    M["pb_navy"] = P("st_pb_navy", (0.05, 0.10, 0.28), 0.4)                        # Monsters, Inc.: the signs' panels
    M["pb_cyan"] = P("st_pb_cyan", (0.35, 0.75, 0.95), 0.35, Emission_Color=(0.35, 0.75, 0.95, 1), Emission_Strength=0.3)
    M["pb_tan2"] = P("st_pb_tan2", (0.58, 0.46, 0.31), 0.85)                       # the tower's recesses, the dome's joints
    M["pb_tan3"] = P("st_pb_tan3", (0.92, 0.82, 0.62), 0.75)                       # the lighter coping, panels, niches
    M["pb_bronze"] = P("st_pb_bronze", (0.36, 0.25, 0.14), 0.4, Metallic=0.6)     # the motto's letters, the plaques
    M["pb_tile"] = P("st_pb_tile", (0.20, 0.25, 0.31), 0.5)                       # the tower's tiled panel
    M["pb_trunk"] = P("st_pb_trunk", (0.42, 0.36, 0.28), 0.9)
    M["pb_leaf"] = P("st_pb_leaf", (0.16, 0.32, 0.10), 0.8)
    M["pb_hedge"] = P("st_pb_hedge", (0.13, 0.27, 0.09), 0.95)
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
        out.append((b[0] + m[0] * k, b[1] + m[1] * k))   # clockwise ring: (dy, -dx) points in
    return out


def facade(name, L, H, wall, trim, kind, rng):
    """One wall run (x 0..L, +y out, z up) of a promenade building / shop / service building."""
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "display", "awning", "stripe", "iron")}
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
        striped_awning(P["awning"], P["stripe"], m - 1.3, m + 1.3)
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
        mat = {"wall": wall, "trim": trim, "glass": "pb_glass", "display": "pb_display", "awning": "pb_awning", "stripe": "pb_stripe", "iron": "pb_iron"}[k]
        obj_bm(f"PB_{name}_{k}", bm_, mat)


def striped_awning(bmA, bmS, x0, x1, y=1.3, z_lo=2.95, z_hi=3.55):
    """A sloping awning over x0..x1, cream with thin green stripes (photo), and its scalloped valance."""
    x = x0; k = 0
    while x < x1 - 1e-3:
        w = 0.36 if k % 2 == 0 else 0.12
        xe = min(x1, x + w)
        bm_prism(bmA if k % 2 == 0 else bmS, [(0.15, z_hi), (y, z_lo + 0.1), (y, z_lo), (0.15, z_hi - 0.13)], x, xe, "yz")
        x = xe; k += 1
    n = max(3, round((x1 - x0) / 0.5))
    for j in range(n):
        xx = x0 + (x1 - x0) * (j + 0.5) / n
        bm_lathe(bmA, [(0, -0.12), ((x1 - x0) / n / 2, 0), (0, 0.001)], 8, T(xx, y, z_lo) @ R(math.pi / 2, "X"))


def area_perim(pts):
    n = len(pts)
    A = abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))) / 2
    return A, sum(math.hypot(pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1]) for i in range(n))


def simple_inset(pts, d):
    """True when the ring moved in by d keeps every edge's direction and does not cross itself."""
    q = inset(pts, d); n = len(q)
    for i in range(n):
        j = (i + 1) % n
        if (q[j][0] - q[i][0]) * (pts[j][0] - pts[i][0]) + (q[j][1] - q[i][1]) * (pts[j][1] - pts[i][1]) <= 0:
            return False
    def cross(a, b, c, d_):
        o = lambda p, q_, r: (q_[0] - p[0]) * (r[1] - p[1]) - (q_[1] - p[1]) * (r[0] - p[0])
        return o(a, b, c) * o(a, b, d_) < 0 and o(c, d_, a) * o(c, d_, b) < 0
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if cross(q[i], q[(i + 1) % n], q[j], q[(j + 1) % n]):
                return False
    return True


def roof(name, pts, H, mat, trim="pb_white", over=0.6, slope=0.75):
    """A hipped roof with eaves: a fascia board, then the slopes from the eaves (the outline out by `over`) up to a
    ridge. Rectangles get a true hip (a ridge along the long side); other outlines slope in to a small flat top."""
    base = inset(pts, -over)
    prism(f"PB_{name}_fascia", [base], H - 0.28, H, trim)
    bm = bmesh.new(); bmc = bmesh.new()
    if len(pts) == 4:
        (a, b, c, d) = [Vector((x, y, 0)) for x, y in base]
        if (b - a).length < (c - b).length:                        # make a-b the long side
            a, b, c, d = b, c, d, a
        L, W = (b - a).length, (c - b).length
        u = (b - a).normalized(); v = (d - a).normalized()
        h = W / 2 * slope; r0 = a + v * W / 2 + u * min(W / 2, L / 2); r1 = b + v * W / 2 - u * min(W / 2, L / 2)
        V = lambda p, z: bm.verts.new((p.x, p.y, z))
        va, vb, vc, vd = V(a, H), V(b, H), V(c, H), V(d, H); v0, v1 = V(r0, H + h), V(r1, H + h)
        if (r1 - r0).length > 1e-3:
            bm.faces.new((va, vb, v1, v0)); bm.faces.new((vc, vd, v0, v1))
        else:
            bm.faces.new((va, vb, v1)); bm.faces.new((vc, vd, v0))
        bm.faces.new((vb, vc, v1)); bm.faces.new((vd, va, v0))
        for p, q in ((r0, r1), (a, r0), (b, r1), (c, r1), (d, r0)):     # the ridge and hip caps
            p3, q3 = Vector((p.x, p.y, H if p in (a, b, c, d) else H + h)), Vector((q.x, q.y, H + h))
            dvec = q3 - p3
            if dvec.length < 0.05:
                continue
            m_ = Matrix.Translation((p3 + q3) / 2) @ dvec.to_track_quat("Z", "Y").to_matrix().to_4x4()
            bm_lathe(bmc, [(0, -dvec.length / 2), (0.09, -dvec.length / 2), (0.09, dvec.length / 2), (0, dvec.length / 2)], 6, m_)
        for p in ((r0, r1) if (r1 - r0).length > 1e-3 else (r0,)):         # finials at the ridge's ends
            bm_lathe(bmc, [(0, 0), (0.1, 0), (0.12, 0.15), (0.05, 0.3), (0.08, 0.45), (0, 0.8)], 8, T(p.x, p.y, H + h))
    else:
        A, Pm = area_perim(pts)
        d = min(2.5 if len(pts) > 6 else 3.5, max(0.6, 1.3 * A / Pm))
        while d > 0.3 and not simple_inset(pts, d):                 # narrow wings / concave corners: a shallower slope
            d *= 0.85
        top = inset(pts, d); d += over
        rise = max(d * slope, min(1.8, d * 1.6))                     # a short slope gets steeper (a mansard) to keep its height
        lo = [bm.verts.new((x, y, H)) for x, y in base]; hi = [bm.verts.new((x, y, H + rise)) for x, y in top]
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        bm.faces.new(hi)
        for i in range(n):                                          # the cap round the flat top
            j = (i + 1) % n
            p3, q3 = Vector((*top[i], H + rise)), Vector((*top[j], H + rise)); dvec = q3 - p3
            if dvec.length > 0.3:
                m_ = Matrix.Translation((p3 + q3) / 2) @ dvec.to_track_quat("Z", "Y").to_matrix().to_4x4()
                bm_lathe(bmc, [(0, -dvec.length / 2), (0.08, -dvec.length / 2), (0.08, dvec.length / 2), (0, dvec.length / 2)], 6, m_)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    obj_bm(f"PB_{name}_roof", bm, mat, recalc=False)
    if len(bmc.verts):
        obj_bm(f"PB_{name}_ridge", bmc, trim)
    else:
        bmc.free()


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
        roof(bid, pts, H + 0.3, rmat, trim, over=0.5, slope=0.45)
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
    roof(bid, pts, H, rmat, trim, over=0.7 if kind != "service" else 0.5, slope=0.8 if kind != "service" else 0.65)


# Monsters, Inc.: the outline without the queue's small jogs on its east side (OSM 217930681, points 0-10, 23)
MI_OUTLINE = [(-607.2, 764.2), (-634.1, 766.0), (-648.2, 782.8), (-642.8, 787.4), (-640.5, 817.7), (-621.7, 833.9),
              (-602.6, 833.0), (-590.4, 818.5), (-582.5, 810.0), (-582.5, 773.2), (-606.4, 774.7)]
MI_FRONT = {6: 3.2, 7: 3.2, 8: 3.6, 9: 3.2}    # the edges set back behind piers on the ground floor, and by how much
MI_H, MI_Z0 = 9.5, 4.3                         # the parapet's top; the lintel's underside (photos: people 1.7 m)
MI_DOME = (-606.0, 797.0, 12.0)                # centre x, y and radius (ESTIMATE from the photos)
MI_TOWER = (-624.0, 797.0, 14.0, 12.0, 13.0)   # east face: north end x, y; the logo unit's width; the finned block's width; depth


def offset_edges(pts, ds):
    """The ring with edge i moved inwards by ds[i] (a clockwise ring; the corners are the offset lines' crossings)."""
    n = len(pts); L = []
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        l = math.hypot(x1 - x0, y1 - y0); nx, ny = -(y1 - y0) / l, (x1 - x0) / l      # outward normal (clockwise: the left)
        L.append(((x0 - nx * ds[i], y0 - ny * ds[i]), ((x1 - x0) / l, (y1 - y0) / l)))
    out = []
    for i in range(n):
        (p, u), (q, v) = L[i - 1], L[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-6:
            out.append(q); continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def ring_wall(name, outer, inner, z0, z1, mat):
    """A wall between two rings with the same vertex count (a parapet round a flat roof)."""
    bm = bmesh.new(); n = len(outer)
    V = [[bm.verts.new((x, y, z)) for x, y in ring] for ring in (outer, inner) for z in (z0, z1)]   # outer lo/hi, inner lo/hi
    for i in range(n):
        j = (i + 1) % n
        for a_, b_ in ((0, 1), (1, 3), (3, 2), (2, 0)):
            bm.faces.new((V[a_][i], V[a_][j], V[b_][j], V[b_][i]))
    obj_bm(name, bm, mat)


def taper_box(bm, cx, cy, w0, d0, w1, d1, z0, z1):
    """A pier narrower at the foot (w0 x d0) than at the head (w1 x d1), in the current frame."""
    vs = [bm.verts.new((cx + sx * w / 2, cy + sy * d / 2, z)) for (w, d, z) in ((w0, d0, z0), (w1, d1, z1))
          for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([vs[i] for i in f])


def disc(bm, x, y, z, r, t=0.08, segs=24):
    """A disc facing +y in the current frame."""
    bm_lathe(bm, [(0, 0), (r, 0), (r, t), (0, t)], segs, T(x, y, z) @ R(-math.pi / 2, "X"))


def mi_logo(name, x, y, z, r):
    """The round Monsters, Inc. logo (photos): a white disc in a dark rim, the blue M with its one eye."""
    bmr, bmw, bmb = bmesh.new(), bmesh.new(), bmesh.new()
    disc(bmr, x, y, z, r * 1.15, 0.12); disc(bmw, x, y + 0.12, z, r, 0.06)
    disc(bmw, x, y + 0.25, z + r * 0.12, r * 0.2, 0.05, 12); disc(bmr, x, y + 0.3, z + r * 0.12, r * 0.09, 0.04, 10)
    obj_bm(f"{name}_rim", bmr, "pb_navy"); obj_bm(f"{name}_disc", bmw, "pb_white")
    text(f"{name}_M", "M", r * 1.25, (x, y + 0.2, z - r * 0.05), (math.pi / 2, 0, math.pi), "pb_blue", 0.05)


def mi_sign(name, x, y, deg, z):
    """The blue Monsters, Inc. wall sign (photos): a navy panel in a light-blue frame, the logo, the name under it."""
    with frame(f"PB_{name}", x, y, deg):
        bmn, bmc = bmesh.new(), bmesh.new()
        bm_box(bmn, -1.4, 1.4, 0, 0.45, z, z + 3.6)
        for bx in ((-1.55, 1.55, z - 0.15, z), (-1.55, 1.55, z + 3.6, z + 3.75), (-1.55, -1.4, z, z + 3.6), (1.4, 1.55, z, z + 3.6)):
            bm_box(bmc, bx[0], bx[1], 0.05, 0.5, bx[2], bx[3])
        obj_bm(f"PB_{name}_panel", bmn, "pb_navy"); obj_bm(f"PB_{name}_frame", bmc, "pb_cyan")
        mi_logo(f"PB_{name}_logo", 0, 0.45, z + 2.2, 0.95)
        text(f"PB_{name}_name", "MONSTERS, INC.", 0.3, (0, 0.5, z + 0.6), (math.pi / 2, 0, math.pi), "pb_white", 0.02)


def mi_pole_sign(name, x, y, deg):
    """The sign on a column by the queue (photo): a pedestal with round emblems, a tapered column, a blue board
    with the two monsters' faces in circles, "Ride & Go Seek!" and the sponsor's strip under it."""
    with frame(f"PB_{name}", x, y, deg):
        bmt, bmd, bmb, bmn, bmw = (bmesh.new() for _ in range(5))
        bm_box(bmt, -0.75, 0.75, -0.75, 0.75, 0, 1.0); bm_box(bmt, -0.85, 0.85, -0.85, 0.85, 1.0, 1.15)
        for sx in (-0.33, 0.33):
            disc(bmd, sx, 0.75, 0.55, 0.28, 0.05, 16)
        taper_box(bmt, 0, 0, 0.42, 0.42, 0.55, 0.55, 1.15, 3.9)
        bm_box(bmt, -0.4, 0.4, -0.4, 0.4, 3.9, 4.05)
        bm_box(bmw, -1.25, 1.25, -0.12, 0.12, 4.05, 4.45)                                 # the sponsor's strip
        bm_box(bmn, -1.75, 1.75, -0.2, 0.2, 4.45, 6.9)                                    # the board, its frame
        bm_box(bmb, -1.6, 1.6, 0.2, 0.24, 4.6, 6.75)
        bm_box(bmt, -1.85, 1.85, -0.28, 0.28, 6.9, 7.1)
        for sx in (-0.75, 0.75):                                                          # Mike's and Sulley's circles
            disc(bmw, sx, 0.24, 6.0, 0.62, 0.04, 20); disc(bmd if sx < 0 else bmb, sx, 0.28, 6.0, 0.52, 0.04, 20)
        obj_bm(f"PB_{name}_post", bmt, "pb_tan3"); obj_bm(f"PB_{name}_emblem", bmd, "pb_tan2")
        obj_bm(f"PB_{name}_board", bmb, "pb_blue"); obj_bm(f"PB_{name}_frame", bmn, "pb_navy")
        obj_bm(f"PB_{name}_white", bmw, "pb_white")
        text(f"PB_{name}_t1", "MONSTERS, INC.", 0.34, (0, 0.28, 5.2), (math.pi / 2, 0, math.pi), "pb_white", 0.02)
        text(f"PB_{name}_t2", "Ride & Go Seek!", 0.22, (0, 0.28, 4.82), (math.pi / 2, 0, math.pi), "pb_cyan", 0.02)
        text(f"PB_{name}_t3", "Panasonic", 0.22, (0, 0.14, 4.25), (math.pi / 2, 0, math.pi), "pb_blue", 0.02)


def palm(bm_t, bm_l, x, y, h, lean, rng):
    """A palm (photos: tall and slender in the beds before the front): a ringed, gently curving trunk, a crown of
    drooping fronds."""
    ax, ay = math.cos(lean), math.sin(lean); bend = rng.uniform(0.6, 1.4)
    P = lambda t: Vector((x + ax * bend * t * t, y + ay * bend * t * t, h * t))
    n = 10
    for k in range(n):
        a, b = P(k / n), P((k + 1) / n); d = b - a
        r0, r1 = 0.2 - 0.07 * k / n, 0.2 - 0.07 * (k + 1) / n
        M_ = Matrix.Translation(a) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bm_lathe(bm_t, [(0, 0), (r0 * 1.12, 0), (r0, 0.12), (r1, d.length), (0, d.length)], 7, M_)
    top = P(1.0)
    for f in range(11):                                                                   # the fronds
        az = 2 * math.pi * f / 11 + rng.uniform(-0.2, 0.2); L = rng.uniform(2.4, 3.2); up = rng.uniform(0.35, 0.8)
        u = Vector((math.cos(az), math.sin(az), 0)); side = Vector((-u.y, u.x, 0))
        pts = [top + u * (L * s) + Vector((0, 0, up * L * s - 1.6 * L * s * s * 0.5)) for s in (0, 0.25, 0.5, 0.75, 1.0)]
        wid = (0.05, 0.42, 0.5, 0.36, 0.03)
        vs = [(bm_l.verts.new(p - side * w), bm_l.verts.new(p - Vector((0, 0, 0.12 * w))), bm_l.verts.new(p + side * w))
              for p, w in zip(pts, wid)]
        for s in range(4):
            bm_l.faces.new((vs[s][0], vs[s + 1][0], vs[s + 1][1], vs[s][1]))
            bm_l.faces.new((vs[s][1], vs[s + 1][1], vs[s + 1][2], vs[s][2]))
    bm_lathe(bm_t, [(0, -0.3), (0.3, -0.2), (0.25, 0.1), (0, 0.2)], 8, T(top.x, top.y, top.z))


def mi_front(bid, i, L):
    """The ground floor of a set-back edge (its own frame, +y out): tapered piers under a projecting lintel, the
    back wall with panels echoing the piers, glass doors with their plaques; on the east face the store block and
    the motto."""
    d = MI_FRONT[i]; Z0 = MI_Z0
    bmp, bmg, bmd, bml, bmq = (bmesh.new() for _ in range(5))
    x_lo = 12.2 if i == 8 else 0.8                                                    # the store block takes 12 m of the east face
    k = max(1, round((L - 0.8 - x_lo) / 6.0))
    xs = [x_lo + (L - 0.8 - x_lo) * j / k for j in range(k + 1)]
    for x in xs:
        taper_box(bmp, x, -0.75, 0.75, 0.8, 1.5, 1.2, 0, Z0)
        taper_box(bmq, x, -d - 0.05, 0.9, 0.12, 1.9, 0.12, 0.6, Z0)                   # the panel behind the pier
    bm_box(bmp, 0, L, -0.3, 0.2, Z0, Z0 + 0.65)                                        # the lintel
    bm_box(bmq, 0, L, 0.2, 0.3, Z0 + 0.5, Z0 + 0.65)
    for j in range(k):
        m = (xs[j] + xs[j + 1]) / 2
        if (j + i) % 2 == 0:                                                               # a double glass door, its frame, a plaque
            bm_box(bmq, m - 1.5, m + 1.5, -d, -d + 0.1, 0, 2.9)
            bm_box(bmg, m - 1.3, m + 1.3, -d + 0.1, -d + 0.14, 0, 2.7)
            bm_box(bml, m - 1.0, m + 1.0, -d, -d + 0.12, 3.05, 3.45)
        else:                                                                              # a poster case
            bm_box(bmq, m - 0.95, m + 0.95, -d, -d + 0.1, 0.8, 3.3)
            bm_box(bmd, m - 0.8, m + 0.8, -d + 0.1, -d + 0.13, 0.95, 3.15)
    if i == 8:                                                                             # the company store (photo: its front stands forward)
        bmw = bmesh.new()
        bm_box(bmw, 0, 12.0, -3.6, 4.3, Z0, MI_H - 0.4)
        bm_box(bmw, 0, 12.0, -3.6, 3.0, 0, Z0)
        for x in (0.6, 11.4):
            taper_box(bmp, x, 3.7, 0.75, 0.8, 1.4, 1.1, 0, Z0)
        bm_box(bmp, 0, 12.0, 3.1, 4.5, Z0, Z0 + 0.65)
        for m in (3.4, 8.6):
            bm_box(bmq, m - 1.6, m + 1.6, 3.0, 3.1, 0, 3.0); bm_box(bmg, m - 1.4, m + 1.4, 3.1, 3.14, 0, 2.8)
        bm_box(bmq, 2.2, 9.8, 4.3, 4.45, Z0 + 1.2, Z0 + 2.4)                              # the store's name plaque
        bm_box(bmq, -0.1, 12.1, -3.6, 4.6, MI_H - 0.9, MI_H - 0.4)
        obj_bm(f"PB_{bid}_store", bmw, "pb_tan")
        text(f"PB_{bid}_storename", "MONSTERS, INC.", 0.52, (6.0, 4.47, Z0 + 1.95), (math.pi / 2, 0, math.pi), "pb_bronze", 0.04)
        text(f"PB_{bid}_storename2", "COMPANY STORE", 0.3, (6.0, 4.47, Z0 + 1.45), (math.pi / 2, 0, math.pi), "pb_bronze", 0.03)
        text(f"PB_{bid}_motto", "IT'S LAUGHTER WE'RE AFTER", 0.78, ((12.2 + L) / 2, 0.05, Z0 + 2.2), (math.pi / 2, 0, math.pi), "pb_bronze", 0.05)
    for nm, b_, mt in (("piers", bmp, "pb_tan"), ("panels", bmq, "pb_tan3"), ("doors", bmg, "pb_glass"),
                       ("posters", bmd, "pb_display"), ("plaques", bml, "pb_bronze")):
        if len(b_.verts):
            obj_bm(f"PB_{bid}_{nm}{i}", b_, mt)
        else:
            b_.free()


def monsters(bid, pts, H):
    """Monsters, Inc. Ride & Go Seek (photos 2023-2026): a warm tan stucco box; on the queue sides the ground floor is
    set back behind piers that widen upwards, under a lintel, with the motto over the entrance and the company store
    standing forward at the north end of the east face; grooves round the upper wall and a coping on the parapet; a
    low faceted dome of light and dark triangles (glazed on its south-west side) on a deep drum; behind it the tower
    whose frame dips to a V over the dark tiled panel with the round logo, rounded niches either side, grooved sides,
    and a finned block south of it; wall signs, a sign on a column, hedge beds, lamps (the photos' palms left out:
    no trees, the user's request)."""
    H, Z0 = MI_H, MI_Z0
    pts = cw(MI_OUTLINE); n = len(pts)
    prism(f"PB_{bid}_ground", [offset_edges(pts, [MI_FRONT.get(i, 0.0) for i in range(n)])], 0, Z0, "pb_tan")
    prism(f"PB_{bid}_body", [pts], Z0, H, "pb_tan")
    ring_wall(f"PB_{bid}_cornice", inset(pts, -0.22), inset(pts, 0.35), H - 0.45, H + 0.3, "pb_tan3")   # the coping
    prism(f"PB_{bid}_roofdeck", [inset(pts, 0.3)], H - 0.3, H + 0.05, "pb_tan")
    ring_wall(f"PB_{bid}_band", inset(pts, -0.12), inset(pts, 0.05), Z0 + 3.2, Z0 + 3.45, "pb_tan3")   # the band over the motto
    ring_wall(f"PB_{bid}_groove", inset(pts, -0.02), inset(pts, 0.05), H - 1.3, H - 1.18, "pb_tan2")
    for i, d in MI_FRONT.items():
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        with frame(f"PB_{bid}_q{i}", x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0))):
            mi_front(bid, i, math.hypot(x1 - x0, y1 - y0))
    mi_sign(f"{bid}_sign0", -586.5, 814.3, -47, 5.2)                                     # the north-east corner
    mi_sign(f"{bid}_sign2", -612.0, 833.44, -2.7, 5.2)                                     # the north face
    mi_pole_sign(f"{bid}_pole", -577.0, 776.5, -70)
    rng = random.Random(bid)                                                               # the beds before the front
    bmt, bml, bmh, bmc, bmlamp, bmpost = (bmesh.new() for _ in range(6))
    for (bx, by, bl) in ((-575.5, 790.0, 9.0), (-574.5, 813.5, 7.0)):
        bm_box(bmc, bx - 1.6, bx + 1.6, by - bl / 2, by + bl / 2, 0, 0.45)
        bm_box(bmh, bx - 1.4, bx + 1.4, by - bl / 2 + 0.2, by + bl / 2 - 0.2, 0.45, 1.05)
    for (lx, ly) in ((-576.0, 800.5), (-576.0, 782.0), (-576.0, 769.0)):                  # the lamps
        bm_lathe(bmpost, [(0, 0), (0.2, 0), (0.2, 0.5), (0.1, 0.7), (0.07, 3.8), (0.12, 3.9), (0.12, 4.0), (0, 4.0)], 10, T(lx, ly, 0))
        bm_lathe(bmlamp, [(0, 0), (0.22, 0.1), (0.25, 0.55), (0.12, 0.75), (0, 0.8)], 10, T(lx, ly, 4.0))
    bmt.free(); bml.free()                                                                # no trees (the user's request)
    obj_bm(f"PB_{bid}_hedge", bmh, "pb_hedge"); obj_bm(f"PB_{bid}_bedcurb", bmc, "pb_tan3")
    obj_bm(f"PB_{bid}_lamppost", bmpost, "pb_white"); obj_bm(f"PB_{bid}_lamp", bmlamp, "pb_display")
    mi_tower(bid, H)
    mi_dome(bid, H)


def mi_tower(bid, H):
    """The tower (photos; local +y = east, x southwards from its north end): the logo unit, then the finned block."""
    tx, ty, wl, wf, td = MI_TOWER
    with frame(f"PB_{bid}_tower", tx, ty, -90):
        bmt, bmf, bmr, bmk, bmn, bmg = (bmesh.new() for _ in range(6))
        top = H + 13.0
        bm_box(bmt, 0, wl, -td, 0, H - 0.5, top)                                          # the grooved block
        for z in [H + 0.6 + 0.85 * j for j in range(15)]:
            bm_box(bmr, -0.03, wl + 0.03, -td - 0.03, 0.03, z, z + 0.12)
        m = wl / 2
        bm_prism(bmt, [(m - 5.2, H - 0.5), (m + 5.2, H - 0.5), (m + 5.2, top + 2.6), (m + 1.8, top + 0.8),
                       (m - 1.8, top + 0.8), (m - 5.2, top + 2.6)], -2.0, 1.1, "xz")          # the frame dipping to a V
        bm_prism(bmn, [(m - 5.35, top + 2.6), (m - 5.2, top + 2.75), (m - 1.75, top + 0.95), (m + 1.75, top + 0.95),
                       (m + 5.2, top + 2.75), (m + 5.35, top + 2.6), (m + 1.8, top + 0.8), (m - 1.8, top + 0.8)], -2.0, 1.2, "xz")
        for sx in (-1, 1):                                                                 # the rounded niches
            c = m + sx * 3.55
            bm_prism(bmk, arch_opening(c - 0.8, c + 0.8, H + 1.2, top - 1.0, 0.8, 10), 1.1, 1.18, "xz")
            bm_prism(bmr, arch_opening(c - 0.95, c + 0.95, H + 1.05, top - 1.0, 0.95, 10), 1.08, 1.12, "xz")
        bm_box(bmt, m - 2.55, m + 2.55, 1.1, 1.35, H + 5.75, top + 0.6)                    # the tiled panel's surround
        bm_box(bmg, m - 2.3, m + 2.3, 1.35, 1.4, H + 6.0, top + 0.35)                    # the dark tiles and their joints
        for j in range(1, 6):
            x = m - 2.3 + 4.6 * j / 6; bm_box(bmr, x - 0.03, x + 0.03, 1.4, 1.43, H + 6.0, top + 0.35)
        for j in range(1, 7):
            z = H + 6.0 + (top - H - 5.65) * j / 7; bm_box(bmr, m - 2.3, m + 2.3, 1.4, 1.43, z - 0.03, z + 0.03)
        bm_box(bmt, m - 2.8, m + 2.8, 1.1, 1.6, H + 5.45, H + 5.75)                          # the sill
        wf0 = wl
        bm_box(bmt, wf0, wf0 + wf, -td + 1.0, -0.8, H - 0.5, H + 10.0)                     # the finned block
        bm_box(bmt, wf0 + 0.4, wf0 + wf - 0.4, -td + 1.6, -1.4, H + 10.0, H + 10.6)
        for j in range(int(wf / 1.1) + 1):
            x = wf0 + 0.3 + (wf - 0.6) * j / int(wf / 1.1)
            bm_box(bmf, x - 0.2, x + 0.2, -0.8, -0.2, H - 0.5, H + 9.6 + (0.4 if j % 2 else 0))
        obj_bm(f"PB_{bid}_towerbody", bmt, "pb_tan"); obj_bm(f"PB_{bid}_fins", bmf, "pb_tan")
        obj_bm(f"PB_{bid}_grooves", bmr, "pb_tan2"); obj_bm(f"PB_{bid}_niches", bmk, "pb_tan3")
        obj_bm(f"PB_{bid}_coping", bmn, "pb_tan3"); obj_bm(f"PB_{bid}_tiles", bmg, "pb_tile")
        mi_logo(f"PB_{bid}_logo", m, 1.43, (H + 6.0 + top + 0.35) / 2, 1.55)


def mi_dome(bid, H):
    """The dome (photos): a deep drum with a lip, then a low shell of 16 segments in three rows; each panel folded
    into two triangles, light and dark in turn, with dark joints; glazed over its south-west third; a ring at the top."""
    cx, cy, r = MI_DOME
    segs = 16; prof = [(r, 2.6), (r * 0.9, 5.1), (r * 0.7, 7.2), (r * 0.42, 8.6)]
    bmg, bmt, bml, bmw, bmi = (bmesh.new() for _ in range(5))
    bm_lathe(bmt, [(0, 0), (r + 0.5, 0), (r + 0.5, 2.3), (0, 2.3)], segs * 2, T(cx, cy, H))              # the drum
    bm_lathe(bml, [(r + 0.5, 2.2), (r + 0.75, 2.2), (r + 0.75, 2.6), (0, 2.6)], segs * 2, T(cx, cy, H))  # its lip
    Pt = lambda k, rr, z: Vector((cx + rr * math.cos(2 * math.pi * k / segs), cy + rr * math.sin(2 * math.pi * k / segs), H + z))

    def rib(bm, v0, v1, w=0.09):
        dvec = v1 - v0
        mm = Matrix.Translation((v0 + v1) / 2) @ dvec.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bm_lathe(bm, [(0, -dvec.length / 2), (w, -dvec.length / 2), (w, dvec.length / 2), (0, dvec.length / 2)], 4, mm)
    for k in range(segs):
        az = math.degrees(2 * math.pi * (k + 0.5) / segs)
        glazed = abs((az - 250 + 180) % 360 - 180) < 56                                   # facing south-west (the photos from the east and north-east show none)
        for j in range(len(prof) - 1):
            (r0, z0), (r1, z1) = prof[j], prof[j + 1]
            a, b, c, d = Pt(k, r0, z0), Pt(k + 1, r0, z0), Pt(k + 1, r1, z1), Pt(k, r1, z1)
            if glazed:
                bmg.faces.new([bmg.verts.new(v) for v in (a, b, c, d)])
                rib(bmi, (a + b) / 2, (c + d) / 2, 0.05); rib(bmi, (a + d) / 2, (b + c) / 2, 0.05)
            else:
                t1, t2 = ((a, b, c), (a, c, d)) if (k + j) % 2 == 0 else ((a, b, d), (b, c, d))
                for tri, bm_ in ((t1, bmt), (t2, bml)):
                    bm_.faces.new([bm_.verts.new(v) for v in tri])
                rib(bmw, *((a, c) if (k + j) % 2 == 0 else (b, d)), 0.07)
            rib(bmw, a, d); rib(bmw, a, b)
    rt, zt = prof[-1]
    bm_lathe(bml, [(0, zt), (rt + 0.45, zt), (rt + 0.45, zt + 0.9), (rt - 0.2, zt + 0.9), (rt - 0.2, zt + 0.6), (0, zt + 0.6)], segs * 2, T(cx, cy, H))
    obj_bm(f"PB_{bid}_domeglass", bmg, "pb_dome"); obj_bm(f"PB_{bid}_domepanels", bmt, "pb_tan")
    obj_bm(f"PB_{bid}_domelight", bml, "pb_tan3"); obj_bm(f"PB_{bid}_domerib", bmw, "pb_tan2")
    obj_bm(f"PB_{bid}_domemullion", bmi, "pb_iron")


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
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith(("CAM_", "CTX_")):   # CTX_: the preview ground
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
        "monsters": ((-555.0, 840.0, 16.0), (-608.0, 800.0, 8.0), 24),
        "monsters_q": ((-566.0, 790.0, 1.7), (-590.0, 805.0, 4.0), 24),
        "monsters_front": ((-540.0, 780.0, 1.7), (-600.0, 797.0, 9.0), 28),
        "monsters_store": ((-560.0, 822.0, 1.7), (-605.0, 792.0, 10.0), 30),
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
