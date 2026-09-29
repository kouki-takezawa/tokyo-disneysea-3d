"""東京ディズニーランドのプラザ(ハブ)の中央物 -- the things standing on the plaza hub's ground (plan 3, phase 4; plain Python,
Blender is not needed; no trees, no round clipped shrubs, no night version):

  python src/ds_tdl_plaza_ground.py      # (phase 3) the ground this stands on: output/disneysea/models/tdl_plaza_ground.json
  python src/ds_tdl_plaza_center.py      # -> output/disneysea/models/tdl_plaza_center.json (glTF, buffer embedded) + a summary
  python src/export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_plaza_center", layer ディズニーランド)

What is modelled:
  statue   the Partners statue (Walt Disney holding Mickey's hand, his right hand raised and pointing ahead) in bronze,
           as low-poly figures (frustums and spheres, no likeness), on a multi-tier pale stone round pedestal with a
           bronze plaque, in the middle of the hub's small round bed (way 71900258). Placed at HUB_C (phase 3's centre,
           not the OSM "Partners" node 1345595271, which is ~70 m off; the bed's own centroid is 0.7 m from HUB_C).
           It faces World Bazaar (WB_EXIT), its back to the castle. No photo (Commons has none): general knowledge only.
  stage    "プラザガーデン" (OSM 12028823101, amenity=theatre, no way of its own): the curved band of barrier=wall
           lines with steps (ways 1298497935-42, steps 1298497922-27) at the south edge of the crescent lawn 72241312
           is read as a two-tier curved stage, tier 1 between the two wall arcs (+0.30 m), tier 2 from the inner arc
           to the lawn (+0.60 m, each tier no higher than the walker's step so it can be walked on), stair treads
           at the three passages the steps mark. The outline comes from the OSM lines; its use as a stage is an
           ESTIMATE. The other stage, "キャッスルフォアコート" (6293190962, (-411, 655)), is the castle's own forecourt
           stage, already built by ds_tdl_cinderella.py's build_forecourt() (the model ends 6.4 m south of the node,
           which marks the audience area in front of it): nothing is added for it here, so nothing is doubled.
  fences   a low iron fence (dark green, posts and two rails, 0.55 m over the curb) on the curb of every planter
           of tdl_plaza_ground inside FENCE_R of HUB_C (OSM tags many of these beds barrier=fence), except where the
           stage abuts the lawn.
  lamps    Victorian lamp posts (dark green fluted post, one white globe; style from the entrance colonnade's lamps,
           commons_entrance_canopy_lamps.jpg) along the beds' edges, about LAMP_STEP apart, on the paving.
  benches  park benches (dark green slats, cast-iron ends; commons_wb_arcade_bench_lamp.jpg) with their backs to the
           beds, facing the paths.
  Positions of lamps and benches are generated (ESTIMATES: no survey of the real ones), from the actual planters and
  paving of tdl_plaza_ground.json (read back from the file: what is built, cut by the other models' footprints), so
  nothing stands in a bed, on a building's footprint or off the paving.
Walk: nothing special is needed -- the mock's walker treats steep faces as walls (the pedestal, the fence rails and
  posts, the lamp posts, the bench ends and back) and flat faces as floors it can step onto up to 0.55 m (the stage
  tiers, the treads).
Heights: every object stands on tdl_plaza_ground's own surface (its triangles sampled at the object's footprint).
Frame: the mock's local metres (+x east, +y north), z up; plan (x, y, z) -> glTF (x, z, -y) by ds_tdl_ground.write_gltf.
"""
import sys, json, math, base64, pathlib

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
from ds_tdl_plaza_ground import HUB_C, CLIP

MODELS = ROOT / "output" / "disneysea" / "models"
GROUND = MODELS / "tdl_plaza_ground.json"
OUT = MODELS / "tdl_plaza_center.json"
WB_EXIT = (-477.0, 794.0)                        # the statue faces this way (World Bazaar), its back to the castle
FENCE_R = 80.0                                   # fence the beds within this distance of HUB_C
LAMP_R, BENCH_R = 75.0, 48.0                     # lamps / benches along the beds within these distances of HUB_C
LAMP_STEP, LAMP_GAP, LAMP_OFF = 15.0, 11.0, 0.9  # along a bed's edge; min gap between lamps; out from the curb (m)
BENCH_STEP, BENCH_GAP, BENCH_OFF = 7.0, 7.0, 0.75
CURB_W, CURB_H = G.CURB_W, G.CURB_H              # the planters' curb (ds_tdl_ground)
FENCE_H = 0.55                                   # fence top over the curb
STAGE_WALLS = {"N": (1298497937, 1298497939, 1298497940, 1298497935), "S": (1298497938, 1298497941, 1298497942, 1298497936)}
STAGE_STEPS = ((1298497927, 1298497926), (1298497924, 1298497925), (1298497922, 1298497923))   # (outer, inner) per passage
TIER1, TIER2, TIER2_DEPTH = 0.30, 0.60, 4.0      # stage tier heights over the paving; tier 2's depth to the lawn at most
NAMES = ("PC_bronze", "PC_stone", "PC_stone2", "PC_plaque", "PC_iron", "PC_globe", "PC_bench", "PC_stage", "PC_stage2")


# ---------------------------------------------------------------- reading the ground back
def load_ground():
    d = json.loads(GROUND.read_text(encoding="utf-8"))
    buf = base64.b64decode(d["buffers"][0]["uri"].split(",", 1)[1])

    def acc(i):
        a = d["accessors"][i]; bv = d["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC3": 3}[a["type"]]
        dt = {5126: np.float32, 5125: np.uint32}[a["componentType"]]
        arr = np.frombuffer(buf, dtype=dt, count=a["count"] * n, offset=bv.get("byteOffset", 0) + a.get("byteOffset", 0))
        return arr.reshape(-1, n) if n > 1 else arr
    out = {}
    for m in d["meshes"]:
        p = m["primitives"][0]
        P = acc(p["attributes"]["POSITION"]).astype(float)[acc(p["indices"]).astype(int)].reshape(-1, 3, 3)
        out[m["name"]] = np.stack([P[..., 0], -P[..., 2], P[..., 1]], -1)           # glTF (x, up, -y) -> plan (x, y, z)
    return out


class Surface:
    """Heights of a set of ground triangles (the highest one straight above/below a point), bucketed in 2 m cells."""
    def __init__(self, tris):
        e1, e2 = tris[:, 1, :2] - tris[:, 0, :2], tris[:, 2, :2] - tris[:, 0, :2]
        self.t = tris[np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) > 1e-8]
        self.cells = {}
        lo = np.floor(self.t[:, :, :2].min(1) / 2).astype(int); hi = np.floor(self.t[:, :, :2].max(1) / 2).astype(int)
        for k in range(len(self.t)):
            for i in range(lo[k, 0], hi[k, 0] + 1):
                for j in range(lo[k, 1], hi[k, 1] + 1):
                    self.cells.setdefault((i, j), []).append(k)

    def z(self, x, y):
        best = None
        for k in self.cells.get((math.floor(x / 2), math.floor(y / 2)), ()):
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = self.t[k]
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            u = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / d; v = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
            if u < -1e-6 or v < -1e-6 or u + v > 1 + 1e-6:
                continue
            h = u * az + v * bz + (1 - u - v) * cz
            best = h if best is None else max(best, h)
        return best


def union_of(tris):
    return unary_union([Polygon(t[:, :2]) for t in tris if abs(Polygon(t[:, :2]).area) > 1e-6]).buffer(0.01).buffer(-0.01)


# ---------------------------------------------------------------- low-poly primitives (flat normals)
def tri(mesh, a, b, c, want=None):
    """One triangle; `want`: a direction its normal should face (flipped to agree)."""
    a, b, c = (np.asarray(p, float) for p in (a, b, c))
    n = np.cross(b - a, c - a); L = np.linalg.norm(n)
    if L < 1e-10:
        return
    n /= L
    if want is not None and np.dot(n, want) < 0:
        b, c, n = c, b, -n
    mesh.add(np.array([a, b, c]), np.array([n, n, n]))


def solid_tri(mesh, a, b, c, ref):
    """A triangle of a closed solid round the point `ref`: its normal faces away from it."""
    tri(mesh, a, b, c, want=(np.asarray(a) + np.asarray(b) + np.asarray(c)) / 3 - np.asarray(ref))


def frame_of(p0, p1):
    ax = np.asarray(p1, float) - np.asarray(p0, float); ax /= np.linalg.norm(ax)
    up = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(ax, up); u /= np.linalg.norm(u); v = np.cross(ax, u)
    return ax, u, v


def frustum(mesh, p0, p1, r0, r1, n=8, caps=True, sq=(1.0, 1.0)):
    """A (possibly tapered, possibly flattened by `sq`) n-sided tube from p0 to p1, capped."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax, u, v = frame_of(p0, p1)
    ring = lambda p, r: [p + r * (sq[0] * math.cos(2 * math.pi * k / n) * u + sq[1] * math.sin(2 * math.pi * k / n) * v) for k in range(n)]
    A, B = ring(p0, r0), ring(p1, r1)
    for k in range(n):
        k2 = (k + 1) % n; mid = (p0 + p1) / 2
        for t3 in ((A[k], A[k2], B[k2]), (A[k], B[k2], B[k])):
            tri(mesh, *t3, want=np.mean(t3, 0) - (p0 + ax * np.dot(np.mean(t3, 0) - p0, ax)))
    if caps:
        for k in range(1, n - 1):
            tri(mesh, A[0], A[k], A[k + 1], want=-ax); tri(mesh, B[0], B[k], B[k + 1], want=ax)


def sphere(mesh, c, r, n=8, m=5, sc=(1.0, 1.0, 1.0), basis=None):
    c = np.asarray(c, float)
    X, Y, Z = basis if basis is not None else (np.eye(3)[0], np.eye(3)[1], np.eye(3)[2])
    P = lambda i, k: c + r * (sc[0] * math.sin(math.pi * i / m) * math.cos(2 * math.pi * k / n) * X
                              + sc[1] * math.sin(math.pi * i / m) * math.sin(2 * math.pi * k / n) * Y + sc[2] * math.cos(math.pi * i / m) * Z)
    for i in range(m):
        for k in range(n):
            a, b, cc, d = P(i, k), P(i, k + 1), P(i + 1, k + 1), P(i + 1, k)
            if i > 0:
                solid_tri(mesh, a, b, cc, c)
            if i < m - 1:
                solid_tri(mesh, a, cc, d, c)


def box(mesh, c, h, basis=None):
    """A box of half extents h = (hx, hy, hz) at c, axes `basis` (3 unit vectors; default the world axes)."""
    c = np.asarray(c, float)
    X, Y, Z = basis if basis is not None else (np.eye(3)[0], np.eye(3)[1], np.eye(3)[2])
    corner = lambda sx, sy, sz: c + sx * h[0] * np.asarray(X) + sy * h[1] * np.asarray(Y) + sz * h[2] * np.asarray(Z)
    for axis in range(3):
        for s in (-1, 1):
            q = []
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                sgn = [0, 0, 0]; sgn[axis] = s; o = [i for i in range(3) if i != axis]; sgn[o[0]] = a; sgn[o[1]] = b
                q.append(corner(*sgn))
            solid_tri(mesh, q[0], q[1], q[2], c); solid_tri(mesh, q[0], q[2], q[3], c)


def lathe(mesh, c, prof, n=24):
    """A solid of revolution round the vertical through c = (x, y, z0): prof = [(r, dz)] from the bottom outer corner
    up the outside and in over the top (the outward normal is to the right of the direction of travel)."""
    cx, cy, z0 = c
    for (r0, z0_), (r1, z1_) in zip(prof[:-1], prof[1:]):
        nr, nz = z1_ - z0_, -(r1 - r0)
        for k in range(n):
            t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            P = lambda r, t, z: (cx + r * math.cos(t), cy + r * math.sin(t), z0 + z)
            a, b, cc, d = P(r0, t0, z0_), P(r0, t1, z0_), P(r1, t1, z1_), P(r1, t0, z1_)
            tm = (t0 + t1) / 2; want = (nr * math.cos(tm), nr * math.sin(tm), nz)
            tri(mesh, a, b, cc, want); tri(mesh, a, cc, d, want)


def prism(mesh, poly, z_of, h, bottom_drop=0.15, wall_mesh=None):
    """A slab over the shapely polygon, its top h over the ground at every corner (it follows the plaza's gentle slope,
    so every edge stays h high -- a flat top would stand up to 0.7 m over the low side here), its sides down below it."""
    wall_mesh = wall_mesh or mesh
    for p in G._polys(poly.segmentize(1.5)):
        for c in G.cdt(p):
            top = np.column_stack([c[:, :2], [z_of(x, y) + h for x, y in c[:, :2]]])
            tri(mesh, *top, want=(0, 0, 1.0))
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            for (xa, ya), (xb, yb) in zip(cs[:-1], cs[1:]):
                mid = np.array([(xa + xb) / 2, (ya + yb) / 2]); e = np.array([xb - xa, yb - ya])
                nrm = np.array([e[1], -e[0], 0.0])
                if p.contains(Point(*(mid + 0.01 * nrm[:2] / (np.linalg.norm(nrm) or 1)))):
                    nrm = -nrm
                za, zb = z_of(xa, ya), z_of(xb, yb)
                tri(wall_mesh, (xa, ya, za - bottom_drop), (xb, yb, zb - bottom_drop), (xb, yb, zb + h), nrm)
                tri(wall_mesh, (xa, ya, za - bottom_drop), (xb, yb, zb + h), (xa, ya, za + h), nrm)


# ---------------------------------------------------------------- the statue and its pedestal
PEDESTAL = [(2.05, 0.0), (2.05, 0.75), (1.85, 0.85), (1.85, 1.05), (1.45, 1.15), (1.30, 1.25), (1.30, 2.55), (1.42, 2.65),
            (1.50, 2.80), (1.30, 2.88), (1.10, 2.95), (1.10, 3.10), (0.0, 3.10)]   # (r, z) of the multi-tier drum; ESTIMATE


def pedestal(M, cx, cy, z0, fwd):
    lathe(M["PC_stone"], (cx, cy, z0), PEDESTAL[:4] + [(0.0, 1.05)], n=32)             # the low plinth and step
    lathe(M["PC_stone2"], (cx, cy, z0), [(1.45, 1.05), (1.45, 1.15), (1.30, 1.25), (1.30, 2.55), (1.42, 2.65), (1.50, 2.80),
                                         (1.30, 2.88), (1.10, 2.95), (1.10, 3.10), (0.0, 3.10)], n=32)
    f = np.array([fwd[0], fwd[1], 0.0]); r = np.array([fwd[1], -fwd[0], 0.0]); up = np.array([0, 0, 1.0])
    # the bronze plaque on the drum's front (towards World Bazaar), a slightly larger stone frame behind it
    box(M["PC_stone"], np.array([cx, cy, z0 + 1.95]) + f * 1.30, (0.62, 0.05, 0.42), (r, f, up))
    box(M["PC_plaque"], np.array([cx, cy, z0 + 1.95]) + f * 1.36, (0.52, 0.03, 0.33), (r, f, up))
    return z0 + PEDESTAL[-1][1]


def statue(M, cx, cy, z0, fwd, S=1.08):
    """Walt (about 1.8 m x S) with his right hand raised and pointing ahead, his left holding Mickey's right hand;
    Mickey (about 1.0 m x S) on Walt's left, looking up. Local frame: u to the statue's right, v ahead, w up."""
    f = np.array([fwd[0], fwd[1], 0.0]); rgt = np.array([fwd[1], -fwd[0], 0.0]); up = np.array([0, 0, 1.0])
    base = np.array([cx, cy, z0]); B = M["PC_bronze"]
    L = lambda u, v, w: base + S * (u * rgt + v * f + w * up)
    wx = 0.22                                        # Walt stands a little right of the middle, Mickey left
    W = lambda u, v, w: L(u + wx, v, w)
    box(B, L(0, 0, 0.04), (0.95 * S, 0.60 * S, 0.04 * S), (rgt, f, up))                # the bronze base plate
    # Walt: shoes, legs, jacket, head, arms
    for s in (-1, 1):
        box(B, W(0.11 * s, 0.05, 0.12), (0.06 * S, 0.14 * S, 0.05 * S), (rgt, f, up))
        frustum(B, W(0.11 * s, 0.0, 0.14), W(0.10 * s, 0.01, 0.52), 0.065 * S, 0.075 * S, n=7)
        frustum(B, W(0.10 * s, 0.01, 0.52), W(0.10 * s, 0.0, 0.92), 0.075 * S, 0.095 * S, n=7)
    frustum(B, W(0, 0, 0.82), W(0, 0, 1.08), 0.20 * S, 0.19 * S, n=10, sq=(1.0, 0.72))   # hips / jacket skirt
    frustum(B, W(0, 0, 1.08), W(0, 0, 1.47), 0.19 * S, 0.22 * S, n=10, sq=(1.0, 0.68))   # chest
    frustum(B, W(0, 0, 1.47), W(0, 0, 1.53), 0.22 * S, 0.08 * S, n=10, sq=(1.0, 0.68))   # shoulders
    frustum(B, W(0, 0, 1.52), W(0, 0.01, 1.62), 0.055 * S, 0.055 * S, n=7)              # neck
    sphere(B, W(0, 0.01, 1.72), 0.115 * S, n=9, m=6, sc=(0.88, 1.0, 1.08), basis=(rgt, f, up))
    box(B, W(0, 0.075, 1.645), (0.018 * S, 0.012 * S, 0.018 * S), (rgt, f, up))         # the tie knot
    # right arm raised ahead (pointing down the plaza), finger and thumb
    frustum(B, W(0.21, 0, 1.44), W(0.30, 0.18, 1.52), 0.055 * S, 0.048 * S, n=7)
    frustum(B, W(0.30, 0.18, 1.52), W(0.38, 0.44, 1.64), 0.048 * S, 0.038 * S, n=7)
    sphere(B, W(0.39, 0.48, 1.65), 0.045 * S, n=7, m=4)
    frustum(B, W(0.39, 0.50, 1.66), W(0.41, 0.60, 1.70), 0.013 * S, 0.010 * S, n=5)
    # left arm down to Mickey's hand
    frustum(B, W(-0.21, 0, 1.44), W(-0.29, 0.02, 1.18), 0.055 * S, 0.048 * S, n=7)
    frustum(B, W(-0.29, 0.02, 1.18), W(-0.38, 0.06, 0.95), 0.048 * S, 0.04 * S, n=7)
    sphere(B, W(-0.40, 0.07, 0.91), 0.05 * S, n=7, m=4)
    # Mickey, on Walt's left: big shoes, short legs, pear body with shorts, head with round ears, arms
    mx = wx - 0.70
    K = lambda u, v, w: L(u + mx, v, w)
    for s in (-1, 1):
        sphere(B, K(0.08 * s, 0.07, 0.07), 0.09 * S, n=8, m=4, sc=(0.75, 1.35, 0.7), basis=(rgt, f, up))   # the shoes
        frustum(B, K(0.07 * s, 0.0, 0.10), K(0.06 * s, 0.0, 0.34), 0.035 * S, 0.035 * S, n=6)
    frustum(B, K(0, 0, 0.30), K(0, 0, 0.44), 0.14 * S, 0.15 * S, n=10)                   # the shorts
    frustum(B, K(0, 0, 0.44), K(0, 0, 0.62), 0.14 * S, 0.09 * S, n=10)                   # the body
    sphere(B, K(0.02, 0.02, 0.80), 0.16 * S, n=10, m=6)                                  # the head, turned a little up
    sphere(B, K(0.03, 0.15, 0.77), 0.07 * S, n=8, m=4, sc=(1.0, 1.1, 0.8))               # the snout
    for s in (-1, 1):                                                                     # the ears (flat discs)
        frustum(B, K(0.16 * s, -0.02, 0.97), K(0.16 * s, 0.02, 0.97), 0.095 * S, 0.095 * S, n=10)
    frustum(B, K(0.13, 0, 0.58), K(0.23, 0.04, 0.78), 0.03 * S, 0.028 * S, n=6)          # right arm up to Walt's hand
    frustum(B, K(0.23, 0.04, 0.78), K(0.30, 0.07, 0.88), 0.028 * S, 0.028 * S, n=6)
    sphere(B, K(0.31, 0.07, 0.90), 0.055 * S, n=7, m=4)                                  # the glove in Walt's hand
    frustum(B, K(-0.13, 0, 0.58), K(-0.20, 0.03, 0.42), 0.03 * S, 0.028 * S, n=6)        # left arm down
    sphere(B, K(-0.22, 0.04, 0.38), 0.055 * S, n=7, m=4)
    frustum(B, K(0, -0.13, 0.36), K(-0.05, -0.30, 0.22), 0.012 * S, 0.008 * S, n=4)      # the tail


# ---------------------------------------------------------------- street furniture
def lamp(M, x, y, z):
    lathe(M["PC_iron"], (x, y, z), [(0.20, 0.0), (0.20, 0.35), (0.14, 0.45), (0.10, 0.55), (0.075, 0.70), (0.065, 3.05),
                                    (0.11, 3.15), (0.11, 3.25), (0.07, 3.32), (0.0, 3.32)], n=8)
    sphere(M["PC_globe"], (x, y, z + 3.58), 0.27, n=10, m=6)
    lathe(M["PC_iron"], (x, y, z + 3.80), [(0.10, 0.0), (0.12, 0.04), (0.04, 0.16), (0.0, 0.22)], n=8)


def bench(M, x, y, z, face):
    """A 1.7 m park bench on the ground at (x, y, z), facing `face` (a unit plan vector)."""
    f = np.array([face[0], face[1], 0.0]); r = np.array([face[1], -face[0], 0.0]); up = np.array([0, 0, 1.0])
    P = lambda u, v, w: np.array([x, y, z]) + u * r + v * f + w * up
    for s in (-0.78, 0.78):                                                              # the cast-iron ends
        box(M["PC_iron"], P(s, 0.10, 0.22), (0.035, 0.03, 0.22), (r, f, up))
        box(M["PC_iron"], P(s, -0.18, 0.44), (0.035, 0.03, 0.44), (r, f, up))
        box(M["PC_iron"], P(s, -0.04, 0.44), (0.035, 0.18, 0.025), (r, f, up))
        box(M["PC_iron"], P(s, 0.02, 0.64), (0.03, 0.14, 0.02), (r, f, up))              # the armrest
    for k, v in enumerate((0.14, 0.02, -0.10)):                                          # seat slats
        box(M["PC_bench"], P(0, v, 0.45), (0.86, 0.05, 0.018), (r, f, up))
    tilt = math.radians(12); bu = up * math.cos(tilt) - f * math.sin(tilt); bf = f * math.cos(tilt) + up * math.sin(tilt)
    for w in (0.60, 0.74):                                                                # back slats, leaning back
        box(M["PC_bench"], P(0, -0.19 - (w - 0.5) * math.tan(tilt), w), (0.86, 0.015, 0.05), (r, bf, bu))


def fence(M, ring, z_of):
    """A low iron fence along `ring` (a LineString on the curb): posts about 1.5 m apart, a top and a middle rail --
    vertical strips (the page draws both sides), cheap and a wall to the walker."""
    ring = ring.simplify(0.12)
    pts = list(ring.coords)
    if len(pts) < 2:
        return 0
    L = ring.length; nposts = 0
    for d in np.arange(0.0, L, 1.5):
        p = ring.interpolate(d); z = z_of(p.x, p.y)
        if z is None:
            continue
        for ang in (0.0, math.pi / 2):
            ux, uy = 0.022 * math.cos(ang), 0.022 * math.sin(ang)
            a, b = (p.x - ux, p.y - uy), (p.x + ux, p.y + uy)
            tri(M["PC_iron"], (*a, z - 0.02), (*b, z - 0.02), (*b, z + FENCE_H + 0.05), None)
            tri(M["PC_iron"], (*a, z - 0.02), (*b, z + FENCE_H + 0.05), (*a, z + FENCE_H + 0.05), None)
        nposts += 1
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        za, zb = z_of(xa, ya), z_of(xb, yb)
        if za is None or zb is None:
            continue
        for h0, h1 in ((FENCE_H - 0.04, FENCE_H), (0.22, 0.25)):
            tri(M["PC_iron"], (xa, ya, za + h0), (xb, yb, zb + h0), (xb, yb, zb + h1), None)
            tri(M["PC_iron"], (xa, ya, za + h0), (xb, yb, zb + h1), (xa, ya, za + h1), None)
    return nposts


# ---------------------------------------------------------------- the Plaza Garden stage
def stage_plan(planters):
    ways = {w["id"]: w for w in DL.DATA["ways"] if w.get("id") is not None}

    def arc(ids):
        pts = []
        for i in ids:
            p = list(ways[i]["pts"])
            if p[0][0] > p[-1][0]:                    # every piece west -> east
                p = p[::-1]
            pts += p
        return pts
    N, S = arc(STAGE_WALLS["N"]), arc(STAGE_WALLS["S"])
    tier1 = Polygon(S + N[::-1]).buffer(0)
    # tier 2: from the inner arc towards the lawn, up to TIER2_DEPTH, not onto the lawn (a circle fitted to the arcs
    # gives the direction "towards the lawn": the arcs curve round the crescent lawn)
    P = np.array(N + S); A = np.c_[2 * P, np.ones(len(P))]; b = (P ** 2).sum(1)
    cx, cy, _ = np.linalg.lstsq(A, b, rcond=None)[0]
    inner = [(x + (cx - x) * TIER2_DEPTH / math.hypot(cx - x, cy - y), y + (cy - y) * TIER2_DEPTH / math.hypot(cx - x, cy - y)) for x, y in N]
    lawn = unary_union([q for q in planters if q.distance(tier1) < TIER2_DEPTH + 1])
    tier2 = Polygon(N + inner[::-1]).buffer(0).difference(lawn.buffer(0.05)).difference(tier1)
    tier2 = max(G._polys(tier2), key=lambda q: q.area) if not tier2.is_empty else tier2
    treads = []
    for outer, inner_ in STAGE_STEPS:
        for sid, depth in ((outer, 0.40), (inner_, 0.40)):
            p = ways[sid]["pts"]; (xa, ya), (xb, yb) = p[0], p[-1]
            # the step line crosses the wall; a tread 1.4 m wide, `depth` deep, at its lower end (the side away from the circle)
            da, db = math.hypot(xa - cx, ya - cy), math.hypot(xb - cx, yb - cy)
            lo = (xa, ya) if da > db else (xb, yb)
            d = np.array([cx - lo[0], cy - lo[1]]); d /= np.linalg.norm(d); t = np.array([d[1], -d[0]])
            c = np.array(lo) - d * 0.05
            treads.append((sid == outer, Polygon([c - t * 0.7, c + t * 0.7, c + t * 0.7 - d * depth, c - t * 0.7 - d * depth])))
    return tier1, tier2, treads, (cx, cy)


def build():
    Gd = load_ground()
    paving_tris = np.concatenate([v for k, v in Gd.items() if k.startswith(("TP_paving", "TP_line", "TP_ring"))])
    curb_tris = Gd["TP_curb"]
    ground = Surface(np.concatenate([paving_tris, curb_tris, Gd["TP_flower"], Gd["TP_soil"]]))
    paving_z = Surface(paving_tris); curb_z = Surface(curb_tris)
    paving = union_of(paving_tris)
    pl_all = union_of(np.concatenate([curb_tris, Gd["TP_flower"], Gd["TP_soil"]]))
    planters = [q for q in G._polys(pl_all) if q.area > 2.0]
    M = {n: G.Mesh(n) for n in NAMES}
    hub = Point(*HUB_C)
    info = {}

    # the statue on its pedestal, in the round bed at the centre
    fx, fy = WB_EXIT[0] - HUB_C[0], WB_EXIT[1] - HUB_C[1]; L_ = math.hypot(fx, fy); fwd = (fx / L_, fy / L_)
    zc = ground.z(*HUB_C) or paving_z.z(HUB_C[0], HUB_C[1] - 8.0)
    zs = [ground.z(HUB_C[0] + 2.05 * math.cos(a), HUB_C[1] + 2.05 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    z_ped = min([z for z in zs + [zc] if z is not None]) - 0.10
    top = pedestal(M, HUB_C[0], HUB_C[1], z_ped, fwd)
    statue(M, HUB_C[0], HUB_C[1], top, fwd)
    centre_bed = min(planters, key=lambda q: q.distance(hub) + (0 if q.contains(hub) else 1000))
    info["statue"] = dict(at=HUB_C, heading_deg=round(math.degrees(math.atan2(fwd[1], fwd[0])), 1), pedestal_z=round(float(z_ped), 2),
                          top_z=round(float(top), 2), bed_centroid=(round(centre_bed.centroid.x, 2), round(centre_bed.centroid.y, 2)),
                          bed_r=round(math.sqrt(centre_bed.area / math.pi), 2))

    # the Plaza Garden stage
    tier1, tier2, treads, sc = stage_plan(planters)
    zfun = lambda x, y: paving_z.z(x, y) if paving_z.z(x, y) is not None else (ground.z(x, y) if ground.z(x, y) is not None else z_ped)
    prism(M["PC_stage"], tier1, zfun, TIER1, wall_mesh=M["PC_stone2"])
    if not tier2.is_empty:
        prism(M["PC_stage2"], tier2, zfun, TIER2, wall_mesh=M["PC_stone2"])
    for is_outer, t in treads:
        prism(M["PC_stone"], t.difference(tier1).difference(tier2) if is_outer else t.intersection(tier1), zfun, 0.15 if is_outer else TIER1 + 0.15)
    stage_all = unary_union([tier1, tier2])
    info["stage"] = dict(tier1_m2=round(tier1.area, 1), tier2_m2=round(tier2.area, 1), bounds=[round(b, 1) for b in stage_all.bounds])

    # fences on the curbs of the beds round the hub (not where the stage abuts the lawn)
    keep_out = stage_all.buffer(0.6)
    nposts = 0; fence_len = 0.0
    for q in planters:
        if q.distance(hub) > FENCE_R:
            continue
        mid = q.buffer(-CURB_W / 2, join_style=2)
        for part in G._polys(mid):
            for ring in [part.exterior] + list(part.interiors):
                line = LineString(ring.coords).difference(keep_out)
                for seg in (line.geoms if hasattr(line, "geoms") else [line]):
                    if seg.is_empty or seg.length < 0.5:
                        continue
                    z_of = lambda x, y: curb_z.z(x, y) if curb_z.z(x, y) is not None else (
                        (paving_z.z(x, y) or ground.z(x, y) or z_ped) + CURB_H)
                    nposts += fence(M, seg, z_of); fence_len += seg.length
    info["fence"] = dict(posts=nposts, length_m=round(fence_len))

    # lamps along the beds' edges, benches with their backs to the beds
    blocked = unary_union([pl_all.buffer(0.35), stage_all.buffer(0.5), Point(*HUB_C).buffer(8.5)])
    lamps, benches = [], []
    order = sorted([q for q in planters if q.area > 30.0], key=lambda q: q.distance(hub))
    for q in order:
        if q.distance(hub) > LAMP_R:
            continue
        ring = q.buffer(LAMP_OFF, join_style=2).exterior
        for d in np.arange(LAMP_STEP / 2, ring.length, LAMP_STEP):
            p = ring.interpolate(d)
            if (not paving.contains(p.buffer(0.3)) or blocked.intersects(p.buffer(0.2))
                    or any(math.hypot(p.x - a, p.y - b) < LAMP_GAP for a, b in lamps)):
                continue
            lamps.append((p.x, p.y))
    for q in order:
        if q.distance(hub) > BENCH_R or q.area < 60.0 or q.contains(hub):   # none round the statue's own bed
            continue
        ring = q.buffer(BENCH_OFF, join_style=2).exterior
        for d in np.arange(BENCH_STEP / 2, ring.length, BENCH_STEP):
            p = ring.interpolate(d); pa, pb = ring.interpolate(d - 0.9), ring.interpolate(d + 0.9)
            t = np.array([pb.x - pa.x, pb.y - pa.y]); tl = np.linalg.norm(t)
            if tl < 1.6:                                  # on a corner: skip
                continue
            t /= tl; face = np.array([t[1], -t[0]])
            if q.contains(Point(p.x + face[0] * 1.0, p.y + face[1] * 1.0)) or q.distance(Point(p.x + face[0], p.y + face[1])) < 0.3:
                face = -face
            fp = Polygon([(p.x + t[0] * s + face[0] * v, p.y + t[1] * s + face[1] * v) for s, v in ((-0.9, -0.3), (0.9, -0.3), (0.9, 0.9), (-0.9, 0.9))])
            if (not paving.contains(fp) or fp.intersects(pl_all.buffer(0.1)) or fp.intersects(stage_all.buffer(0.5))
                    or fp.intersects(Point(*HUB_C).buffer(7.0))
                    or any(math.hypot(p.x - a, p.y - b) < 2.2 for a, b in lamps)
                    or any(math.hypot(p.x - a, p.y - b) < BENCH_GAP for a, b, _ in benches)):
                continue
            benches.append((p.x, p.y, tuple(face)))
    for x, y in lamps:
        lamp(M, x, y, paving_z.z(x, y) or ground.z(x, y) or z_ped)
    for x, y, face in benches:
        zs = [paving_z.z(x + face[1] * s, y - face[0] * s) for s in (-0.8, 0.0, 0.8)]
        bench(M, x, y, min([z for z in zs if z is not None] or [z_ped]), face)
    info["lamps"], info["benches"] = len(lamps), len(benches)
    return M, info, dict(lamps=lamps, benches=benches, stage=stage_all, planters=planters)


def main():
    M, info, _ = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, M)
    print(f"[plaza centre] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print("  triangles:", {k: len(m.tris) for k, m in M.items()})


if __name__ == "__main__":
    main()
