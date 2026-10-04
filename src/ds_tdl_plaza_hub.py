"""東京ディズニーランドのプラザ(ハブ)周りの建物 -- the buildings round the plaza hub (plan 3, phase 5; plain Python, Blender is
not needed; no trees, no round clipped shrubs, no night version):

  python src/ds_tdl_plaza_ground.py      # (phase 3) the plaza ground: output/disneysea/models/tdl_plaza_ground.json
  python src/ds_tdl_plaza_hub.py         # -> output/disneysea/models/tdl_plaza_hub.json (glTF, buffer embedded) + a summary
  python src/export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_plaza_hub", layer ディズニーランド)

Relation to ds_tdl_plaza_buildings.py (Blender): that script is the ENTRANCE plaza / World Bazaar side (the promenade
buildings, security canopies, service buildings, the shop block west of World Bazaar, Monsters, Inc.). None of the
buildings here is in it (checked by OSM id and by its exported footprint), so this is a new model, not a rework.

What is modelled (outlines: the OSM building ways, ids below; every height is an ESTIMATE):
  crystal   クリスタルパレス・レストラン (way 72865093): rebuilt 2026-09-30 from the user's 8 photos
            (images/crystal_palace/1-8.png, not in the repo) and the GSI aerial photo. The OSM outline only wraps it; the
            real plan (aerial) is a Y: an octagon under the big dome, two front wings at +-76 deg from the entrance axis
            (towards the hub) ending in chamfered ends under small domes, a straight back wing, and low flat-roofed rooms
            filling the outline between them. White conservatory walls of tall round-headed windows with white glazing
            bars, a cornice and a balustrade; a raised nave with a grey glass pitched roof down each wing; ribbed grey
            glass domes with white ribs, lanterns, spires (a yellow pennant on the big one). The entrance: a cream block
            with a glazed arched door, a white iron canopy with an arched front and lace brackets, the teal oval sign
            with a gold rim and the small "meiji" oval, five steps with white handrails, stone planters with black
            three-lantern lamps and flower baskets, a pale stone patio with a black scrolled inlay (only ~3.5 m deep:
            the parade route passes in front), clipped hedges along the front wings. ESTIMATES: all heights (people in
            the photos: the floor ~1 m up, the aisle walls ~5 m, the dome's top ~25 m), the back wing and rooms (no
            photo), the interior (none: the door is a wall).
  pavilion  プラザパビリオン・レストラン (way 196942701, ~56 x 44 m): NO PHOTO. General knowledge only (ESTIMATE): a white
            Victorian building, arched windows, a green mansard and a small octagonal cupola, with a veranda (slim white
            columns, a green lean-to roof) along the sides facing the hub.
  bandstand the small bandstand (way 1293623988, node 12366581835) by the pavilion: a low platform, four white posts and
            a green hipped canopy (ESTIMATE; no photo).
  kiosks    the small mapped buildings on the hub itself (food booths 1293623986/87 and the others in KIOSKS): cream
            kiosks with a dark counter window band and a green hipped roof; building=roof ways as a canopy on posts
            (ESTIMATE: style only).
  gates     the entrances from the hub to the lands, as gate posts either side of the path with a sign board over it
            (the land names are not written: plain boards). Where the posts stand: the path's cross-section (OSM
            pedestrian areas + footways, minus buildings and water) at the point in GATES. Styles are ESTIMATES:
              Adventureland  (by Crystal Palace's south corner): stone-footed timber posts with thatched caps, a beam
              Westernland    (by the Plaza Pavilion's south-west corner): paired log posts and a log beam
              Tomorrowland   (the path west of the hub, between its two big buildings): two tapered white pylons with
                             blue rings and a sphere on top, no beam
            Fantasyland is entered through Cinderella Castle (ds_tdl_cinderella.py): nothing added there. No land has
            its own model at these points yet (checked the exported model footprints), so nothing is doubled.
Walk: every building is a closed solid down into the ground, so its walls stop the walker (the page's draft-box check
  also keeps it out of the OSM footprints); gate posts and kiosk walls are walls; the bandstand's platform (0.35 m) can
  be stepped onto. Beams and canopies are above head height.
Heights: each thing stands on the ground models that are already there (tdl_plaza_ground + tdl_land_ground triangles,
  sampled round its footprint): the floor line is the highest ground at the walls, the walls go 0.4 m below the lowest.
Overlaps: the Draft boxes of these OSM ways are hidden by the page (ds_disneyland.MODEL_KEYS -> "dlplazahub"). Things
  that other models already cover (checked with ds_ground.model_footprint(): cinderella, tdl_world_bazaar,
  tdl_plaza_buildings, tdl_plaza_center) are skipped.
Frame: the mock's local metres (+x east, +y north), z up; plan (x, y, z) -> glTF (x, z, -y) by ds_tdl_ground.write_gltf.
"""
import sys, json, math, base64, pathlib

import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
import ds_ground as GR
from ds_tdl_plaza_ground import HUB_C, CLIP
from ds_tdl_plaza_center import tri, frustum, sphere, box, lathe, Surface

MODELS = ROOT / "output" / "disneysea" / "models"
OUT = MODELS / "tdl_plaza_hub.json"
CRYSTAL, PAVILION, BANDSTAND = 72865093, 196942701, 1293623988
# the Westernland half of the pavilion's way (the Diamond Horseshoe on the south, Pecos Bill Cafe on the east: frames v2
# 0:16:40-0:16:46, Google labels) is built by ds_tdl_westernland.py; the pavilion keeps the hub side
DH_PART = Polygon([(-350, 640), (-350, 663), (-318, 663), (-318, 695), (-280, 695), (-280, 640)])
KIOSK_MIN, KIOSK_MAX = 3.5, 40.0                 # small mapped buildings inside CLIP (m^2) become kiosks / canopies
SKIP_MODELS = ("cinderella", "tdl_world_bazaar", "tdl_plaza_buildings", "tdl_plaza_center")
# land gates: (land, style, a point on the path, the path's direction there (plan bearing, deg from +x))
GATES = (("Adventureland", "adv", (-349.5, 732.5), 60.0),
         ("Westernland", "west", (-352.0, 655.0), -8.0),
         ("Tomorrowland", "tom", (-509.0, 663.5), 196.0))
NAMES = ("PH_white", "PH_cream", "PH_green", "PH_roof", "PH_iron", "PH_glass", "PH_win", "PH_gold", "PH_stone",
         "PH_wood", "PH_log", "PH_thatch", "PH_sign", "PH_tomw", "PH_tomb", "PH_dome", "PH_cproof", "PH_canopy", "PH_teal", "PH_sky",
         "PH_step", "PH_patio", "PH_swirl", "PH_hedge", "PH_black", "PH_globe", "PH_flower", "PH_flag")
UP = np.array([0.0, 0.0, 1.0])


# ---------------------------------------------------------------- the ground under things
def load_tris(path, keep, bounds):
    d = json.loads(path.read_text(encoding="utf-8"))
    buf = base64.b64decode(d["buffers"][0]["uri"].split(",", 1)[1])

    def acc(i):
        a = d["accessors"][i]; bv = d["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC3": 3}[a["type"]]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a["componentType"]]
        arr = np.frombuffer(buf, dtype=dt, count=a["count"] * n, offset=bv.get("byteOffset", 0) + a.get("byteOffset", 0))
        return arr.reshape(-1, n) if n > 1 else arr
    out = []
    x0, y0, x1, y1 = bounds
    for m in d["meshes"]:
        if not keep(m["name"]):
            continue
        p = m["primitives"][0]
        P = acc(p["attributes"]["POSITION"]).astype(float)[acc(p["indices"]).astype(int)].reshape(-1, 3, 3)
        P = np.stack([P[..., 0], -P[..., 2], P[..., 1]], -1)
        c = P[:, :, :2].mean(1)
        out.append(P[(c[:, 0] > x0) & (c[:, 0] < x1) & (c[:, 1] > y0) & (c[:, 1] < y1)])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


class Ground:
    def __init__(self, bounds):
        tris = [load_tris(MODELS / "tdl_plaza_ground.json", lambda n: n != "TP_edge", bounds),
                load_tris(MODELS / "tdl_land_ground.json", lambda n: n != "TL_edge", bounds)]
        self.s = Surface(np.concatenate(tris))

    def z(self, x, y):
        z = self.s.z(x, y)
        if z is None:                                  # in a hole (a building's footprint): the nearest ground round it
            for r in (1.5, 3.0, 5.0, 8.0):
                zs = [self.s.z(x + r * math.cos(a), y + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
                zs = [v for v in zs if v is not None]
                if zs:
                    return float(np.median(zs))
            return 0.0
        return float(z)

    def span(self, poly, out=1.0):
        """(lowest, highest) ground round a footprint (sampled on its outline pushed `out` m outwards)."""
        ring = poly.buffer(out, join_style=2).exterior
        zs = [self.z(*ring.interpolate(d).coords[0]) for d in np.arange(0, ring.length, 2.0)]
        return min(zs), max(zs)


# ---------------------------------------------------------------- building blocks
def quad(mesh, a, b, c, d, want=None):
    tri(mesh, a, b, c, want); tri(mesh, a, c, d, want)


def P3(p, z):
    return np.array([p[0], p[1], z], float)


def ring_ccw(poly):
    return [np.array(c) for c in list(orient(poly, 1.0).exterior.coords)[:-1]]


def out_normal(a, b):
    e = b - a; L = np.linalg.norm(e)
    return np.array([e[1], -e[0]]) / L                 # CCW ring: the outward side is to the right


def inset(ring, d):
    """Mitred inset of a CCW ring by d (inwards)."""
    n = len(ring); out = []
    for i in range(n):
        a, b, c = ring[i - 1], ring[i], ring[(i + 1) % n]
        n1, n2 = -out_normal(a, b), -out_normal(b, c)
        k = max(1.0 + float(np.dot(n1, n2)), 0.35)
        out.append(b + d * (n1 + n2) / k)
    return out


def slab(top_mesh, side_mesh, poly, z0, z1, bottom=False):
    for c in G.cdt(poly):
        tri(top_mesh, P3(c[0], z1), P3(c[1], z1), P3(c[2], z1), UP)
        if bottom:
            tri(side_mesh, P3(c[0], z0), P3(c[1], z0), P3(c[2], z0), -UP)
    for ring in [poly.exterior] + list(poly.interiors):
        cs = [np.array(c) for c in ring.coords]
        for a, b in zip(cs[:-1], cs[1:]):
            if np.linalg.norm(b - a) < 1e-6:
                continue
            m = (a + b) / 2; nrm = out_normal(a, b)
            if poly.contains(Point(*(m + 0.01 * nrm))):
                nrm = -nrm
            quad(side_mesh, P3(a, z0), P3(b, z0), P3(b, z1), P3(a, z1), np.array([*nrm, 0]))


def loft_rect(mesh, c, u, v, prof, cap=True):
    """A roof/solid over a rectangle: prof = [(half along u, half along v, dz)] from the bottom up; capped on top."""
    c = np.asarray(c, float); u = np.resize(np.r_[np.asarray(u, float)[:2], 0.0], 3); v = np.resize(np.r_[np.asarray(v, float)[:2], 0.0], 3)
    rings = [[c + UP * dz + su * hu * u + sv * hv * v for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))] for hu, hv, dz in prof]
    for A, B in zip(rings[:-1], rings[1:]):
        for k in range(4):
            k2 = (k + 1) % 4; mid = (A[k] + A[k2] + B[k] + B[k2]) / 4
            quad(mesh, A[k], A[k2], B[k2], B[k], mid - (c + UP * (mid - c)[2]))
    if cap:
        R = rings[-1]; quad(mesh, R[0], R[1], R[2], R[3], UP)


def arched_window(mesh, a, b, nrm, z0, z1, off=0.04, n=6):
    """A window: rectangle a-b (plan points on the wall) from z0 up to the spring z1, a half-round head over it."""
    o = np.array([*nrm, 0]) * off
    A, B = P3(a, 0) + o, P3(b, 0) + o
    quad(mesh, A + UP * z0, B + UP * z0, B + UP * z1, A + UP * z1, np.array([*nrm, 0]))
    w = np.linalg.norm(b - a) / 2; m = (A + B) / 2; e = (B - A) / (2 * w)
    pts = [m + e * w * math.cos(math.pi * k / n) + UP * (z1 + w * math.sin(math.pi * k / n)) for k in range(n + 1)]
    for p, q in zip(pts[:-1], pts[1:]):
        tri(mesh, m + UP * z1, p, q, np.array([*nrm, 0]))


def facade(M, ring, zb, zf, E, bay=3.2, wall="PH_white", pier="PH_white", win="PH_win", sill=0.9, head=1.0, dark_open=False):
    """The storey round a CCW ring: walls from zb (below ground) to zf + E, piers between the bays standing 0.18 m
    proud, an arched window in each bay (dark glass; `dark_open`: taller, down to the floor, like an open arcade)."""
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        L = np.linalg.norm(b - a)
        if L < 0.05:
            continue
        nrm = out_normal(a, b); e = (b - a) / L; N3 = np.array([*nrm, 0])
        quad(M[wall], P3(a, zb), P3(b, zb), P3(b, zf + E), P3(a, zf + E), N3)
        nb = max(1, int(round(L / bay))); bw = L / nb
        for k in range(nb + 1):                          # piers (a thin box half proud of the wall)
            if L < 1.2:
                break
            p = a + e * min(max(k * bw, 0.3), L - 0.3)
            box(M[pier], P3(p, (zb + zf + E) / 2) + N3 * 0.09, (0.28, 0.09, (zf + E - zb) / 2), (np.array([*e, 0]), N3, UP))
        for k in range(nb):
            ww = bw - 0.9
            if ww < 0.9:
                continue
            p0 = a + e * (k * bw + 0.45); p1 = a + e * ((k + 1) * bw - 0.45)
            z0 = zf + (0.05 if dark_open else sill); z1 = zf + E - head - ww / 2
            if z1 - z0 < 0.8:
                continue
            arched_window(M[win], p0, p1, nrm, z0, z1)


def cornice(M, poly, z0, h=0.5, out=0.35, mesh="PH_white"):
    slab(M[mesh], M[mesh], poly.buffer(out, join_style=2), z0, z0 + h, bottom=True)


def mansard(M, ring, z0, d, h, mesh="PH_green"):
    """A mansard slope from the ring at z0, inset d and h higher; returns the top ring."""
    inner = inset(ring, d); n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        nrm = out_normal(ring[i], ring[j])
        quad(M[mesh], P3(ring[i], z0), P3(ring[j], z0), P3(inner[j], z0 + h), P3(inner[i], z0 + h), np.array([*nrm, d / h]))
    return inner


def dormers(M, ring, inner, z0, h, step=7.0, size=1.3):
    """Small dormers half way up the mansard: a white front with a dark arched window, a green hipped cap."""
    n = len(ring); count = 0
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]; ai, bi = inner[i], inner[(i + 1) % n]
        L = np.linalg.norm(b - a)
        if L < step + 1.5:
            continue
        e = (b - a) / L; nrm = out_normal(a, b); N3 = np.array([*nrm, 0]); E3 = np.array([*e, 0])
        k = int(L // step)
        for t in (np.arange(k) + 0.5) / k:
            base = a + (b - a) * t; top = ai + (bi - ai) * t
            p = base + (top - base) * 0.45                      # the front face, a bit up the slope
            back = base + (top - base) * 1.0
            zf = z0 + h * 0.20
            c = P3((p + back) / 2, zf + size * 0.55)
            dep = np.linalg.norm(back - p) / 2
            box(M["PH_white"], c, (size / 2, dep, size * 0.55), (E3, N3, UP))
            arched_window(M["PH_win"], p - e * size * 0.28, p + e * size * 0.28, nrm, zf + 0.25, zf + size * 0.75, off=0.02, n=4)
            loft_rect(M["PH_green"], P3((p + back) / 2, zf + size * 1.1), E3[:2], N3[:2], [(size / 2 + 0.1, dep + 0.1, 0.0), (0.05, dep * 0.6, size * 0.55)])
            count += 1
    return count


def finial(M, x, y, z, h=1.2):
    lathe(M["PH_gold"], (x, y, z), [(0.14, 0.0), (0.10, 0.12), (0.05, 0.3), (0.04, h * 0.7), (0.0, h)], n=6)
    sphere(M["PH_gold"], (x, y, z + h * 0.45), 0.12, n=6, m=4)


# ---------------------------------------------------------------- クリスタルパレス・レストラン
# The plan is read off the GSI aerial photo (docs/plaza/aerial_wide.jpg), which the OSM outline only wraps: a glass
# dome on an octagon, three wings in a Y (the two front ones at +-76 deg from the entrance axis, each ending in a
# chamfered end under a small dome; the back one straight), a raised glass-roofed nave down each wing between flat
# side aisles, and low flat-roofed rooms filling the outline between the back wing and the front ones.
CP_C, CP_FRONT = (-375.0, 761.3), 236.0          # the dome's centre; the entrance axis (plan bearing, towards the hub)
CP_WINGS = ((-76.0, 25.0, 5.0, True), (76.0, 25.5, 5.0, True), (180.0, 33.0, 0.5, False))   # (deg off the axis, length, chamfer, end dome)
CP_HW, CP_NAVE, CP_RO = 8.0, 4.0, 8.0            # wing half width, nave half width, octagon radius
CP_AISLE, CP_STEP = 5.2, 0.19                    # aisle wall height over the floor; stair riser


def ngon(c, r, n, phase):
    return [np.asarray(c, float) + r * np.array([math.cos(phase + 2 * math.pi * k / n), math.sin(phase + 2 * math.pi * k / n)]) for k in range(n)]


def bar(mesh, p0, p1, w=0.035, d=0.035, nrm=None):
    """A thin square bar from p0 to p1 (3D), its faces square to `nrm` if given."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = p1 - p0; L = np.linalg.norm(ax)
    if L < 1e-4:
        return
    ax /= L
    N = np.asarray(nrm, float) if nrm is not None else (UP if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0]))
    N = N - ax * np.dot(N, ax); N /= np.linalg.norm(N)
    box(mesh, (p0 + p1) / 2, (L / 2, d, w), (ax, N, np.cross(ax, N)))


def cp_window(M, a, b, nrm, z0, z1, off=0.05, grid=3):
    """A tall conservatory window: dark glass with a round head, white glazing bars (mullions, transoms, a fan)."""
    arched_window(M["PH_win"], a, b, nrm, z0, z1, off=off, n=8)
    N3 = np.array([*nrm, 0]); o = N3 * (off + 0.03)
    A, B = P3(a, 0) + o, P3(b, 0) + o
    w = np.linalg.norm(B - A) / 2; m = (A + B) / 2; e = (B - A) / (2 * w)
    for t in np.linspace(-1, 1, grid + 1)[1:-1]:
        bar(M["PH_white"], m + e * w * t + UP * z0, m + e * w * t + UP * (z1 + w * math.sqrt(1 - t * t)), nrm=N3)
    for z in np.linspace(z0, z1, 4)[1:]:
        bar(M["PH_white"], A + UP * z, B + UP * z, nrm=N3)
    for k in (1, 2, 3):
        a_ = math.pi * k / 4
        bar(M["PH_white"], m + UP * z1, m + e * w * math.cos(a_) + UP * (z1 + w * math.sin(a_)), nrm=N3)
    for k in range(8):                                       # the head's rim
        a0, a1 = math.pi * k / 8, math.pi * (k + 1) / 8
        bar(M["PH_white"], m + e * w * math.cos(a0) + UP * (z1 + w * math.sin(a0)), m + e * w * math.cos(a1) + UP * (z1 + w * math.sin(a1)), 0.05, 0.05, N3)


def cp_walls(M, ring, zb, ztop, mesh="PH_white", win=None, skip=None):
    """Walls round a CCW ring (list of plan points) with white pilasters and, per bay, a cp_window.
    win = (bay, sill, spring, frame) heights absolute; skip(a, b) -> True: plain wall, no windows."""
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        L = np.linalg.norm(b - a)
        if L < 0.05:
            continue
        nrm = out_normal(a, b); e = (b - a) / L; N3 = np.array([*nrm, 0]); E3 = np.array([*e, 0])
        quad(M[mesh], P3(a, zb), P3(b, zb), P3(b, ztop), P3(a, ztop), N3)
        if win is None or (skip and skip(a, b)) or L < 1.6:
            continue
        bay, sill, spring, fr = win
        nb = max(1, int(round(L / bay))); bw = L / nb
        for k in range(nb + 1):
            p = a + e * min(max(k * bw, 0.18), L - 0.18)
            box(M["PH_white"], P3(p, (sill + ztop) / 2 - 0.1) + N3 * 0.07, (0.17, 0.07, (ztop - sill) / 2 + 0.1), (E3, N3, UP))
        for k in range(nb):
            ww = min(bw - 0.62, fr)
            p = a + e * (k + 0.5) * bw
            if ww > 0.6:
                cp_window(M, p - e * ww / 2, p + e * ww / 2, nrm, sill, spring - ww / 2 if spring - ww / 2 > sill + 0.6 else sill + 0.6)


def balustrade(M, ring, z0, h=0.8, closed=True, step=0.4, post=3.0, mesh="PH_white"):
    """A balustrade along a polyline of plan points: plinth rail, turned balusters (square here), top rail, posts."""
    pts = list(ring) + ([ring[0]] if closed else [])
    for a, b in zip(pts[:-1], pts[1:]):
        L = np.linalg.norm(b - a)
        if L < 0.1:
            continue
        e = (b - a) / L; E3 = np.array([*e, 0]); N3 = np.array([-e[1], e[0], 0.0])
        m = (a + b) / 2
        box(M[mesh], P3(m, z0 + 0.08), (L / 2, 0.14, 0.08), (E3, N3, UP))
        box(M[mesh], P3(m, z0 + h - 0.06), (L / 2 + 0.05, 0.17, 0.06), (E3, N3, UP))
        for t in np.arange(step / 2, L, step):
            box(M[mesh], P3(a + e * t, z0 + h / 2), (0.045, 0.045, h / 2 - 0.1), (E3, N3, UP))
        for t in np.linspace(0, L, max(2, int(L // post) + 2)):
            box(M[mesh], P3(a + e * t, z0 + h / 2 + 0.05), (0.13, 0.13, h / 2 + 0.05), (E3, N3, UP))


def dome(M, c, z0, r, h, ribs, lantern=True, flag=False):
    """A ribbed glass dome (grey) with white ribs and rings, a lantern, a spire; returns the top z."""
    prof = [(r * math.cos(t) ** 0.85, h * math.sin(t)) for t in np.linspace(0, math.pi / 2 * 0.93, 8)]
    lathe(M["PH_dome"], (c[0], c[1], z0), prof + [(0.0, prof[-1][1])], n=2 * ribs)
    for k in range(ribs):
        a = 2 * math.pi * (k + 0.5) / ribs
        pp = [np.array([c[0] + (rr + 0.04) * math.cos(a), c[1] + (rr + 0.04) * math.sin(a), z0 + zz]) for rr, zz in prof]
        for p, q in zip(pp[:-1], pp[1:]):
            frustum(M["PH_white"], p, q, 0.06 + 0.02 * r / 6, 0.06 + 0.02 * r / 6, n=4, caps=False)
    for t in (0.35, 0.7):
        rr, zz = r * math.cos(t) ** 0.85, h * math.sin(t)
        lathe(M["PH_white"], (c[0], c[1], z0 + zz - 0.06), [(rr + 0.05, 0.0), (rr + 0.05, 0.12), (rr - 0.1, 0.12)], n=2 * ribs)
    lathe(M["PH_white"], (c[0], c[1], z0 - 0.05), [(r + 0.2, 0.0), (r + 0.2, 0.35), (r - 0.2, 0.35)], n=2 * ribs)
    zt = z0 + prof[-1][1]; rt = prof[-1][0]
    if not lantern:
        finial(M, c[0], c[1], zt, h=1.2)
        return zt + 1.2
    rl = max(rt, 0.45)
    lathe(M["PH_white"], (c[0], c[1], zt), [(rl + 0.12, 0.0), (rl + 0.12, 0.2), (rl * 0.8, 0.2), (rl * 0.8, rl * 1.6), (rl + 0.1, rl * 1.6),
                                           (rl + 0.1, rl * 1.6 + 0.15), (0.0, rl * 1.6 + 0.15)], n=8)
    for k in range(8):                                           # lantern posts over dark openings
        a = 2 * math.pi * (k + 0.5) / 8
        box(M["PH_win"], (c[0] + rl * 0.81 * math.cos(a), c[1] + rl * 0.81 * math.sin(a), zt + 0.2 + rl * 0.7), (0.02, rl * 0.28, rl * 0.5),
            (np.array([math.cos(a), math.sin(a), 0]), np.array([-math.sin(a), math.cos(a), 0]), UP))
    zl = zt + rl * 1.6 + 0.15
    lathe(M["PH_dome"], (c[0], c[1], zl), [(rl * 0.95, 0.0), (rl * 0.8, rl * 0.45), (rl * 0.45, rl * 0.8), (0.0, rl * 0.9)], n=8)
    sp = rl * 3.2
    lathe(M["PH_white"], (c[0], c[1], zl + rl * 0.8), [(0.12 * rl, 0.0), (0.07 * rl, sp * 0.5), (0.02, sp), (0.0, sp)], n=6)
    sphere(M["PH_gold"], (c[0], c[1], zl + rl * 0.8 + sp * 0.35), 0.1 + 0.05 * rl, n=6, m=4)
    top = zl + rl * 0.8 + sp
    if flag:                                                      # the yellow pennant (photos 1, 4, 6-7)
        f0 = np.array([c[0], c[1], top - 0.15]); fw = np.array([1.0, 0.3, 0.0]); fw /= np.linalg.norm(fw)
        tri(M["PH_flag"], f0, f0 - UP * 0.7, f0 + fw * 1.0 - UP * 0.35, np.array([-0.3, 1.0, 0.0]))
        tri(M["PH_flag"], f0, f0 + fw * 1.0 - UP * 0.35, f0 - UP * 0.7, np.array([0.3, -1.0, 0.0]))
    return top


def swirl(cx, cy, e, n_, r0, turns, sgn, w=0.14):
    """A scroll (an inward spiral with a tail) as a polygon, for the patio's inlay."""
    pts = []
    for t in np.linspace(0, turns * 2 * math.pi, int(40 * turns)):
        r = r0 * (1 - t / (turns * 2 * math.pi * 1.15))
        pts.append((cx + (e[0] * math.cos(t) * sgn + n_[0] * math.sin(t)) * r, cy + (e[1] * math.cos(t) * sgn + n_[1] * math.sin(t)) * r))
    return LineString(pts).buffer(w, cap_style=1)


def crystal_palace(M, gr, poly, info):
    osm = orient(poly.buffer(0), 1.0)
    C = np.array(CP_C); fb = math.radians(CP_FRONT)
    F = np.array([math.cos(fb), math.sin(fb)]); Rt = np.array([F[1], -F[0]])
    at = lambda s, t: C + F * s + Rt * t
    dirs = []
    for off, L, ch, _ in CP_WINGS:
        a = fb + math.radians(off); dirs.append(np.array([math.cos(a), math.sin(a)]))

    def wing_poly(d, L, hw, ch, s0=0.0):
        n = np.array([-d[1], d[0]])
        return Polygon([C + d * s0 + n * hw, C + d * (L - ch) + n * hw, C + d * L + n * (hw - ch), C + d * L - n * (hw - ch),
                        C + d * (L - ch) - n * hw, C + d * s0 - n * hw])
    octa = Polygon(ngon(C, CP_RO, 8, fb + math.pi / 8))
    wings = [wing_poly(d, L, CP_HW, ch) for d, (_, L, ch, _) in zip(dirs, CP_WINGS)]
    VS0, VS1, VHW = 6.5, 10.6, 3.7                               # the entrance block (photos 2, 7: cream, one big arched door)
    vest = Polygon([at(VS0, -VHW), at(VS1, -VHW), at(VS1, VHW), at(VS0, VHW)])
    main = orient(unary_union([octa, vest] + wings).buffer(0.01, join_style=2).buffer(-0.01, join_style=2), 1.0)
    ring = ring_ccw(main.simplify(0.05))

    # levels: the floor is ~5 risers over the ground at the foot of the stairs (photos 5, 7)
    NST = 5; SS0 = VS1 + 3.0                                      # stairs start at the canopy's front edge
    zfoot = gr.z(*at(SS0 + NST * 0.33 + 0.3, 0))
    zlo, zhi = gr.span(main)
    zf = max(zfoot + NST * CP_STEP, zhi + 0.35); zb = zlo - 0.4
    ZA = zf + CP_AISLE                                          # the aisles' cornice
    slab(M["PH_stone"], M["PH_stone"], main.buffer(0.2, join_style=2), zb, zf - 0.35)     # the grey-white base
    slab(M["PH_white"], M["PH_white"], main.buffer(0.12, join_style=2), zf - 0.35, zf + 0.25)

    def on_vest_front(a, b):
        m = (a + b) / 2
        return vest.buffer(0.05).contains(Point(*m)) and np.dot(m - C, F) > VS0 + 0.3
    cp_walls(M, ring, zf + 0.25, ZA, win=(2.7, zf + 0.45, zf + 3.55 + 0.95, 1.9), skip=on_vest_front)
    band = main.buffer(0.3, join_style=2).difference(main.buffer(-0.35, join_style=2))
    slab(M["PH_white"], M["PH_white"], band, ZA, ZA + 0.45, bottom=True)                 # the cornice
    slab(M["PH_roof"], M["PH_roof"], main.buffer(-0.3, join_style=2), ZA, ZA + 0.3)    # the aisles' flat roofs
    par = ring_ccw(orient(main.buffer(-0.05, join_style=2).simplify(0.05), 1.0))
    balustrade(M, par, ZA + 0.45, h=0.75)

    # the low rooms filling the outline between the wings (the aerial's white flat roofs); small leftovers: paving
    rest = osm.difference(main)
    rooms = 0
    for g in getattr(rest, "geoms", [rest]):
        g = g.buffer(-0.02, join_style=2).buffer(0.02, join_style=2)
        if g.is_empty or g.geom_type != "Polygon":
            continue
        if g.area < 50:
            slab(M["PH_patio"], M["PH_patio"], g, zb, gr.z(*g.representative_point().coords[0]) + 0.04)
            continue
        g = orient(g.simplify(0.3), 1.0); rg = ring_ccw(g); rooms += 1
        zr = zf + 4.2
        cp_walls(M, rg, zb, zr, win=(2.7, zf + 0.45, zf + 3.1, 1.6), skip=lambda a, b: main.buffer(0.15).contains(Point(*((a + b) / 2))))
        slab(M["PH_white"], M["PH_white"], g.buffer(0.25, join_style=2).difference(g.buffer(-0.3, join_style=2)), zr, zr + 0.35, bottom=True)
        slab(M["PH_roof"], M["PH_roof"], g.buffer(-0.3, join_style=2), zr, zr + 0.25)

    # each wing's nave: clerestory walls with small arched windows and a grey glass pitched roof (the aerial's dark band)
    ZN, ZR = ZA + 2.5, ZA + 4.2
    domes = []
    for d, (_, L, ch, end_dome) in zip(dirs, CP_WINGS):
        s1 = L - 9.4 if end_dome else L - 1.8
        n = np.array([-d[1], d[0]]); D3, N3 = np.array([*d, 0]), np.array([*n, 0])
        nv = Polygon([C + d * CP_RO * 0.8 + n * CP_NAVE, C + d * s1 + n * CP_NAVE, C + d * s1 - n * CP_NAVE, C + d * CP_RO * 0.8 - n * CP_NAVE])
        rn = ring_ccw(orient(nv, 1.0))
        cp_walls(M, rn, ZA + 0.2, ZN, win=(2.4, ZA + 0.8, ZN - 0.55, 1.2), skip=lambda a, b: np.linalg.norm((a + b) / 2 - C) < CP_RO + 0.5)
        slab(M["PH_white"], M["PH_white"], nv.buffer(0.2, join_style=2).difference(nv.buffer(-0.2, join_style=2)), ZN, ZN + 0.3, bottom=True)
        e0, e1 = C + d * CP_RO * 0.8, C + d * (s1 + 0.25)
        for sg in (-1, 1):
            quad(M["PH_cproof"], P3(e0 + n * sg * (CP_NAVE + 0.3), ZN + 0.3), P3(e1 + n * sg * (CP_NAVE + 0.3), ZN + 0.3), P3(e1, ZR), P3(e0, ZR),
                 N3 * sg + UP * 2.0)
            for s in np.arange(CP_RO, s1, 1.6):                  # glazing bars
                bar(M["PH_white"], P3(C + d * s + n * sg * (CP_NAVE + 0.3), ZN + 0.33), P3(C + d * s, ZR + 0.03), 0.03, 0.03)
        tri(M["PH_white"], P3(e1 + n * (CP_NAVE + 0.3), ZN + 0.3), P3(e1 - n * (CP_NAVE + 0.3), ZN + 0.3), P3(e1, ZR), D3)   # the gable end
        frustum(M["PH_white"], P3(e0, ZR + 0.05), P3(e1, ZR + 0.05), 0.12, 0.12, n=4)                                     # the ridge crest
        for s in np.arange(CP_RO + 1.0, s1, 2.0):
            finial(M, *(C + d * s), ZR + 0.1, h=0.55)
        if end_dome:
            domes.append(C + d * (L - 5.6))

    # the end domes over the front wings' ends (photos 3, 6, 8): an octagonal drum with arched windows, a balustrade, a dome
    for q in domes:
        r8 = ngon(q, 3.3, 8, fb + math.pi / 8)
        cp_walls(M, r8, ZA + 0.2, ZA + 3.3, win=(2.5, ZA + 0.9, ZA + 2.3, 1.2))
        oq = Polygon(r8)
        slab(M["PH_white"], M["PH_white"], oq.buffer(0.3, join_style=2), ZA + 3.3, ZA + 3.75, bottom=True)
        balustrade(M, ngon(q, 3.45, 8, fb + math.pi / 8), ZA + 3.75, h=0.6, step=0.35)
        dome(M, q, ZA + 3.8, 2.9, 3.0, 8)

    # the octagon: tall arched windows over the aisle roofs, a balustrade, the drum, the big dome with its lantern and flag
    ZO = ZR + 1.3
    r8 = ngon(C, CP_RO, 8, fb + math.pi / 8)
    cp_walls(M, r8, ZA + 0.2, ZO, win=(6.2, ZA + 0.9, ZO - 1.9, 3.0))
    slab(M["PH_white"], M["PH_white"], octa.buffer(0.35, join_style=2), ZO, ZO + 0.5, bottom=True)
    balustrade(M, ngon(C, CP_RO + 0.1, 8, fb + math.pi / 8), ZO + 0.5, h=0.8)
    rd = CP_RO - 1.6
    cp_walls(M, ngon(C, rd, 8, fb + math.pi / 8), ZO + 0.4, ZO + 2.6, win=(3.0, ZO + 0.9, ZO + 1.6, 1.5))
    for p in ngon(C, rd + 0.25, 8, fb + math.pi / 8):              # scroll corbels at the drum's corners
        finial(M, p[0], p[1], ZO + 2.6, h=0.7)
    zd = ZO + 2.6
    slab(M["PH_white"], M["PH_white"], Polygon(ngon(C, rd, 8, fb + math.pi / 8)).buffer(0.3, join_style=2), zd, zd + 0.3, bottom=True)
    top = dome(M, C, zd + 0.3, rd - 0.15, 6.0, 16, flag=True)
    info["crystal"] = dict(floor_z=round(zf, 2), aisle=CP_AISLE, nave_ridge=round(ZR - zf, 1), octagon=round(ZO - zf, 1), top=round(top - zf, 1),
                           end_domes=len(domes), low_rooms=rooms)

    # the entrance: the cream block with its arched door, the white iron canopy, the sign, the stairs, planters and lamps
    FE, RE = np.array([*F, 0]), np.array([*Rt, 0])
    ZV = zf + 5.6
    quad(M["PH_cream"], P3(at(VS1 + 0.01, -VHW), zf), P3(at(VS1 + 0.01, VHW), zf), P3(at(VS1 + 0.01, VHW), ZV), P3(at(VS1 + 0.01, -VHW), ZV), FE)
    door_a, door_b = at(VS1 + 0.01, 1.35), at(VS1 + 0.01, -1.35)
    cp_window(M, door_a, door_b, F, zf + 0.02, zf + 2.75, off=0.03, grid=4)                 # the glazed double door and fanlight
    for t in (-1.55, 1.55):
        box(M["PH_white"], P3(at(VS1 + 0.12, t), zf + 2.0), (0.14, 0.12, 2.0), (RE, FE, UP))
    for t in (-2.9, 2.9):                                          # the small side windows (photo 7)
        cp_window(M, at(VS1 + 0.01, t + 0.45), at(VS1 + 0.01, t - 0.45), F, zf + 1.0, zf + 2.6, off=0.03, grid=2)
    for k in range(12):                                            # the white arched crest on top
        a0, a1 = math.pi * k / 12, math.pi * (k + 1) / 12
        p0, p1 = P3(at(VS1 - 0.1, VHW * math.cos(a0)), ZV + 1.6 * math.sin(a0)), P3(at(VS1 - 0.1, VHW * math.cos(a1)), ZV + 1.6 * math.sin(a1))
        quad(M["PH_white"], P3(p0, ZV), P3(p1, ZV), p1, p0, FE)
        quad(M["PH_white"], P3(p0, ZV), P3(p1, ZV), p1, p0, -FE)
    finial(M, *at(VS1 - 0.1, 0), ZV + 1.6, h=0.9)
    for t in (-VHW, VHW):
        finial(M, *at(VS1 - 0.1, t), ZV, h=0.8)

    CS0, CS1, CHW = VS1, SS0 + 0.3, 4.5                           # the canopy (photo 7): hipped, on slim white columns
    ce, cr = zf + 3.9, zf + 5.3
    cc = at((CS0 + CS1) / 2, 0); hs = (CS1 - CS0) / 2
    loft_rect(M["PH_canopy"], P3(cc, ce), F, Rt, [(hs, CHW, 0.0), (hs, CHW, 0.25), (hs * 0.55, CHW - 1.1, cr - ce)])
    box(M["PH_white"], P3(at(CS1, 0), ce - 0.15), (0.06, CHW, 0.18), (FE, RE, UP))             # the valance
    arc_ = [(CHW * u, ce + 0.05 + 0.75 * (1 - u * u)) for u in np.linspace(-1, 1, 17)]      # the arched front gable (photo 7)
    for (t0, z0_), (t1, z1_) in zip(arc_[:-1], arc_[1:]):
        for dn, w in ((0.02, FE), (-0.02, -FE)):
            quad(M["PH_white"], P3(at(CS1 + dn, t0), ce - 0.3), P3(at(CS1 + dn, t1), ce - 0.3), P3(at(CS1 + dn, t1), z1_), P3(at(CS1 + dn, t0), z0_), w)
        bar(M["PH_gold"], P3(at(CS1 + 0.05, t0), z0_), P3(at(CS1 + 0.05, t1), z1_), 0.03, 0.03)
    for sg in (-1, 1):
        box(M["PH_white"], P3(at((CS0 + CS1) / 2, sg * CHW), ce - 0.15), (hs, 0.06, 0.18), (FE, RE, UP))
    cols = [(CS1 - 0.35, t) for t in (-4.1, -3.4, 3.4, 4.1)] + [(CS0 + 0.9, t) for t in (-4.1, 4.1)]
    for s, t in cols:
        z0 = zf
        frustum(M["PH_white"], P3(at(s, t), z0), P3(at(s, t), ce - 0.3), 0.09, 0.07, n=8)
        box(M["PH_white"], P3(at(s, t), z0 + 0.3), (0.16, 0.16, 0.3), (FE, RE, UP))
        for dd in (F, -F, Rt * np.sign(t) * -1):
            p = at(s, t) + dd * 0.08
            q0, q1 = P3(p, ce - 1.3), P3(p + dd * 0.9, ce - 0.3)
            tri(M["PH_white"], q0, P3(p, ce - 0.3), q1, np.array([*np.array([-dd[1], dd[0]]), 0]))
            tri(M["PH_white"], q0, q1, P3(p, ce - 0.3), -np.array([*np.array([-dd[1], dd[0]]), 0]))
    crest2 = [P3(at((CS0 + CS1) / 2 + (hs * 0.55) * sg, 0), cr + 0.05) for sg in (-1, 1)]
    frustum(M["PH_white"], crest2[0], crest2[1], 0.08, 0.08, n=4)
    for s in np.linspace(CS0 + 0.6, CS1 - 0.6, 5):
        finial(M, *at(s, 0), cr, h=0.45)
    # the sign: a teal oval with a gold rim, the small light-blue "meiji" oval under it, over the canopy's front
    so = P3(at(CS1 + 0.05, 0), ce + 0.95)
    tilt = FE * 0.9 + UP * 0.25; tilt /= np.linalg.norm(tilt)
    upv = np.cross(tilt, RE); upv /= np.linalg.norm(upv)
    if upv[2] < 0:
        upv = -upv
    for (rx, rz, mat, dz, dn) in ((1.75, 0.72, "PH_gold", 0.0, 0.0), (1.62, 0.6, "PH_teal", 0.0, 0.03), (1.66, 0.64, "PH_sky", 0.0, 0.015),
                                  (0.55, 0.22, "PH_gold", -0.82, 0.02), (0.48, 0.17, "PH_sky", -0.82, 0.04)):
        c0 = so + upv * dz + tilt * dn
        pts = [c0 + RE * rx * math.cos(a_) + upv * rz * math.sin(a_) for a_ in np.linspace(0, 2 * math.pi, 25)]
        for p, q in zip(pts[:-1], pts[1:]):
            tri(M[mat], c0, p, q, tilt); tri(M[mat], c0, q, p, -tilt)
    lt = [so + tilt * 0.06 + RE * (t - 1.15) + upv * (0.17 * math.sin(t * 9.0) - 0.06 * t) for t in np.linspace(0, 2.3, 60)]
    for p, q in zip(lt[:-1], lt[1:]):                               # the script lettering, as one cream flourish
        bar(M["PH_cream"], p, q, 0.035, 0.012, tilt)

    # the landing under the canopy and the stairs down to the ground; planters with lamps either side; handrails
    slab(M["PH_step"], M["PH_step"], Polygon([at(VS1, -3.4), at(SS0, -3.4), at(SS0, 3.4), at(VS1, 3.4)]), zb, zf)
    rise = (zf - zfoot) / NST
    for k in range(NST):
        s0 = SS0 + k * 0.33
        slab(M["PH_step"], M["PH_step"], Polygon([at(s0, -3.3), at(s0 + 0.34, -3.3), at(s0 + 0.34, 3.3), at(s0, 3.3)]), zfoot - 0.5, zf - rise * (k + 1))
    SE = SS0 + NST * 0.33
    for sg in (-1, 1):
        pl = Polygon([at(SS0 - 0.6, sg * 3.4), at(SE + 0.3, sg * 3.4), at(SE + 0.3, sg * 5.2), at(SS0 - 0.6, sg * 5.2)])
        zp = zf + 0.2
        slab(M["PH_step"], M["PH_step"], pl, zfoot - 0.5, zp)
        slab(M["PH_step"], M["PH_step"], pl.buffer(0.08, join_style=2).difference(pl.buffer(-0.12, join_style=2)), zp, zp + 0.12)
        lp = at(SE - 0.6, sg * 4.3)                                 # the black lamp: a fluted post, three lanterns, a flower basket
        frustum(M["PH_black"], P3(lp, zp), P3(lp, zp + 3.0), 0.12, 0.07, n=8)
        for k in range(3):
            a_ = fb + math.pi / 2 + 2 * math.pi * k / 3
            arm = lp + 0.45 * np.array([math.cos(a_), math.sin(a_)])
            bar(M["PH_black"], P3(lp, zp + 2.7), P3(arm, zp + 2.75), 0.03, 0.03)
            loft_rect(M["PH_black"], P3(arm, zp + 2.75), F, Rt, [(0.12, 0.12, 0.0), (0.16, 0.16, 0.35), (0.05, 0.05, 0.55)])
            sphere(M["PH_globe"], P3(arm, zp + 2.95), 0.1, n=6, m=4)
        sphere(M["PH_hedge"], P3(lp, zp + 1.8), 0.38, n=8, m=5, sc=(1, 1, 0.8))
        for k in range(8):
            a_ = 2 * math.pi * k / 8
            sphere(M["PH_flower"], P3(lp + 0.32 * np.array([math.cos(a_), math.sin(a_)]), zp + 1.75), 0.14, n=6, m=4)
        post = at(SE + 1.0, sg * 5.8)                                # the menu stand (white post, a board)
        frustum(M["PH_white"], P3(post, zfoot), P3(post, zfoot + 1.7), 0.05, 0.05, n=6)
        box(M["PH_white"], P3(post, zfoot + 1.35), (0.28, 0.04, 0.36), (RE, FE, UP))
    for t in (-3.1, 0.0, 3.1):                                     # handrails down the stairs (photos 3, 5)
        pa, pb = P3(at(SS0 - 0.4, t), zf + 0.95), P3(at(SE + 0.1, t), zfoot + 0.95)
        frustum(M["PH_white"], pa, pb, 0.04, 0.04, n=6)
        frustum(M["PH_white"], pa - UP * 0.45, pb - UP * 0.45, 0.025, 0.025, n=4)
        for u in np.linspace(0, 1, 4):
            q = pa + (pb - pa) * u
            frustum(M["PH_white"], q - UP * (0.95 - 0.05), q, 0.03, 0.03, n=4)

    # the stone patio in front of the stairs (photos 3, 5): pale stone, a dark border, a black scrolled inlay. It is only
    # ~3.5 m deep: the parade route passes just in front (the paving strip of tdl_plaza_ground ends there)
    pc = at(SE + 0.1, 0); PD = 3.4
    pat = Polygon([at(SE - 0.4, -7.0), at(SE + PD, -7.0), at(SE + PD, 7.0), at(SE - 0.4, 7.0)]).difference(main.buffer(0.3))
    inlay = [LineString([at(SE + PD - 0.35, -6.6), at(SE + PD - 0.35, 6.6)]).buffer(0.12)]
    for sg in (-1, 1):
        inlay.append(swirl(*(pc + Rt * sg * 2.4 + F * 1.55), -Rt * 1.0, F, 1.25, 1.6, sg, 0.12))
        inlay.append(swirl(*(pc + Rt * sg * 4.9 + F * 1.3), Rt * 1.0, F, 0.75, 1.3, -sg, 0.1))
        inlay.append(LineString([pc + Rt * sg * 0.5 + F * 2.7, pc + Rt * sg * 2.4 + F * 2.95, pc + Rt * sg * 4.6 + F * 2.5, pc + Rt * sg * 6.0 + F * 1.6]).buffer(0.1))
    inlay.append(Polygon([pc + F * 0.3, pc + F * 1.5 + Rt * 0.55, pc + F * 2.8, pc + F * 1.5 - Rt * 0.55]))
    pt = load_tris(MODELS / "tdl_plaza_ground.json", lambda nm: nm.startswith(("TP_paving", "TP_ring")), pat.buffer(2).bounds)
    pav = Surface(pt)                                               # drape on the paving only (not over curbs and beds)
    pat = pat.intersection(unary_union([Polygon(t[:, :2]).buffer(0.01) for t in pt]).buffer(-0.15))
    inlay = unary_union(inlay).intersection(pat.buffer(-0.05))
    for g, mat, dz in ((pat, "PH_patio", 0.035), (inlay, "PH_swirl", 0.05)):
        x0, y0, x1, y1 = g.bounds
        for gx in np.arange(x0, x1, 1.0):
            for gy in np.arange(y0, y1, 1.0):
                cell = g.intersection(Polygon([(gx, gy), (gx + 1, gy), (gx + 1, gy + 1), (gx, gy + 1)]))
                if cell.area < 1e-4:
                    continue
                for c3 in G.cdt(cell):
                    tri(M[mat], *[P3(p, (pav.z(*p) if pav.z(*p) is not None else gr.z(*p)) + dz) for p in c3], UP)

    # clipped hedges along the front wings' walls (photos 2, 4, 6)
    for d in dirs[:2]:
        n = np.array([-d[1], d[0]])
        side = n if np.dot(n, F) > 0 else -n
        for s in np.arange(6.0, CP_WINGS[0][1] - CP_WINGS[0][2] - 1.0, 3.0):
            p = C + d * (s + 1.4) + side * (CP_HW + 1.1)
            if Polygon([at(VS1, -5.5), at(SE + 1, -5.5), at(SE + 1, 5.5), at(VS1, 5.5)]).buffer(1.0).contains(Point(*p)):
                continue
            zg = gr.z(*p)
            box(M["PH_hedge"], P3(p, zg + 0.45), (1.4, 0.45, 0.85), (np.array([*d, 0]), np.array([*side, 0]), UP))
    return osm


# ---------------------------------------------------------------- プラザパビリオン・レストラン (no photo: ESTIMATE)
def plaza_pavilion(M, gr, poly, info, avoid):
    P = orient(poly.buffer(0).simplify(0.9), 1.0)
    ring = ring_ccw(P)
    zlo, zhi = gr.span(P)
    zb, zf = zlo - 0.4, zhi + 0.05
    E = 5.0
    slab(M["PH_stone"], M["PH_stone"], P.buffer(0.2, join_style=2), zb, zf + 0.3)
    facade(M, ring, zb, zf + 0.3, E - 0.3, bay=3.0, wall="PH_cream", head=0.8)
    zc = zf + E
    cornice(M, P, zc, 0.45, 0.35)
    zm = zc + 0.45
    inner = mansard(M, ring, zm, 1.5, 2.0)
    top = Polygon(inner)
    if not top.is_valid:
        top = P.buffer(-1.5, join_style=2)
    zt = zm + 2.0
    slab(M["PH_roof"], M["PH_roof"], top, zt - 0.3, zt)
    nd = dormers(M, ring, inner, zm, 2.0, step=8.0, size=1.2)
    c = np.array(top.representative_point().coords[0]) if not top.contains(top.centroid) else np.array(top.centroid.coords[0])
    lathe(M["PH_white"], (c[0], c[1], zt - 0.1), [(3.0, 0.0), (3.0, 2.2), (3.3, 2.3), (3.3, 2.6), (0.0, 2.6)], n=8)   # the cupola drum
    for k in range(8):
        a0, a1 = 2 * math.pi * (k + 0.2) / 8, 2 * math.pi * (k + 0.8) / 8
        p0 = c + 3.02 * np.array([math.cos(a0), math.sin(a0)]); p1 = c + 3.02 * np.array([math.cos(a1), math.sin(a1)])
        mid = (a0 + a1) / 2
        arched_window(M["PH_win"], p0, p1, np.array([math.cos(mid), math.sin(mid)]), zt + 0.3, zt + 1.3, off=0.02, n=4)
    lathe(M["PH_green"], (c[0], c[1], zt + 2.5), [(3.2, 0.0), (3.0, 0.6), (2.3, 1.5), (1.2, 2.3), (0.4, 2.7), (0.0, 2.8)], n=8)
    finial(M, c[0], c[1], zt + 5.3, h=1.4)

    # the veranda on the sides facing the hub: slim white columns, a green lean-to roof, a stone floor (outside the
    # OSM outline, on the paving; clipped off other buildings and water)
    hub = np.array(HUB_C); nver = 0; floor_parts = []
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        L = np.linalg.norm(b - a); nrm = out_normal(a, b)
        if L < 4.0 or np.dot(nrm, (hub - (a + b) / 2) / np.linalg.norm(hub - (a + b) / 2)) < 0.55:
            continue
        D = 2.6
        strip = Polygon([a, b, b + nrm * D, a + nrm * D])
        if strip.intersects(avoid):
            continue
        e = (b - a) / L; E3, N3 = np.array([*e, 0]), np.array([*nrm, 0])
        zg = min(gr.z(*a + nrm * D), gr.z(*b + nrm * D), gr.z(*(a + b) / 2 + nrm * D))
        floor_parts.append((strip, zg))
        for t in np.linspace(0.4, L - 0.4, max(2, int(round(L / 3.0)) + 1)):
            p = a + e * t + nrm * (D - 0.3)
            frustum(M["PH_white"], P3(p, zg - 0.3), P3(p, zf + 3.6), 0.14, 0.12, n=8)
            box(M["PH_white"], P3(p, zf + 3.65), (0.22, 0.22, 0.08))
        z_in, z_out = zf + 4.2, zf + 3.7
        quad(M["PH_green"], P3(a, z_in), P3(b, z_in), P3(b + nrm * (D + 0.2), z_out), P3(a + nrm * (D + 0.2), z_out), np.array([*nrm, D / 0.5]))
        quad(M["PH_white"], P3(a + nrm * (D + 0.2), z_out), P3(b + nrm * (D + 0.2), z_out),
             P3(b + nrm * (D + 0.2), z_out - 0.35), P3(a + nrm * (D + 0.2), z_out - 0.35), N3)     # the fascia
        nver += 1
    for strip, zg in floor_parts:
        slab(M["PH_stone"], M["PH_stone"], strip, zg - 0.3, zg + 0.12)
    info["pavilion"] = dict(floor_z=round(zf, 2), eaves=E, top=round(zt + 5.3 - zf, 1), dormers=nd, veranda_sides=nver)
    return P


# ---------------------------------------------------------------- the bandstand, kiosks, canopies
def rect_of(poly):
    mr = poly.minimum_rotated_rectangle; cs = [np.array(c) for c in list(mr.exterior.coords)[:4]]
    e1, e2 = cs[1] - cs[0], cs[2] - cs[1]
    c = np.mean(cs, 0); l1, l2 = np.linalg.norm(e1), np.linalg.norm(e2)
    return c, e1 / l1, e2 / l2, l1 / 2, l2 / 2


def bandstand(M, gr, poly, info):
    c, u, v, hu, hv = rect_of(poly)
    zlo, zhi = gr.span(poly, 0.5)
    zf = zhi + 0.35
    loft_rect(M["PH_stone"], P3(c, zlo - 0.3), u, v, [(hu, hv, 0.0), (hu, hv, zf - zlo + 0.3)])
    for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = c + su * (hu - 0.2) * u + sv * (hv - 0.2) * v
        frustum(M["PH_white"], P3(p, zf), P3(p, zf + 2.9), 0.1, 0.08, n=8)
    loft_rect(M["PH_white"], P3(c, zf + 2.9), u, v, [(hu + 0.1, hv + 0.1, 0.0), (hu + 0.1, hv + 0.1, 0.25)])
    loft_rect(M["PH_green"], P3(c, zf + 3.15), u, v, [(hu + 0.45, hv + 0.45, 0.0), (hu * 0.5, max(hv * 0.3, 0.1), 1.2)])
    finial(M, *P3(c, zf + 4.35), h=0.8)
    info["bandstand"] = dict(size=(round(2 * hu, 1), round(2 * hv, 1)), floor_z=round(zf, 2))


def kiosk(M, gr, poly, roof_only):
    c, u, v, hu, hv = rect_of(poly)
    zlo, zhi = gr.span(poly, 0.5)
    zb = zlo - 0.4
    H = 2.7
    if roof_only:                                        # a canopy on four posts
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = c + su * max(hu - 0.15, 0.1) * u + sv * max(hv - 0.15, 0.1) * v
            frustum(M["PH_white"], P3(p, zb), P3(p, zhi + H), 0.07, 0.07, n=6)
    else:
        loft_rect(M["PH_cream"], P3(c, zb), u, v, [(hu, hv, 0.0), (hu, hv, zhi + H - zb)], cap=False)
        loft_rect(M["PH_win"], P3(c, zhi + 1.0), u, v, [(hu + 0.03, hv + 0.03, 0.0), (hu + 0.03, hv + 0.03, 1.0)], cap=False)
        loft_rect(M["PH_white"], P3(c, zhi + 0.9), u, v, [(hu + 0.18, hv + 0.18, 0.0), (hu + 0.18, hv + 0.18, 0.1)])   # the counter
    loft_rect(M["PH_white"], P3(c, zhi + H), u, v, [(hu + 0.15, hv + 0.15, 0.0), (hu + 0.15, hv + 0.15, 0.3)])
    rh = min(1.6, 0.45 * min(hu, hv) + 0.6)
    loft_rect(M["PH_green"], P3(c, zhi + H + 0.3), u, v, [(hu + 0.4, hv + 0.4, 0.0), (max(hu - min(hu, hv) + 0.1, 0.1), 0.1, rh)])
    finial(M, *P3(c, zhi + H + 0.3 + rh), h=0.6)


# ---------------------------------------------------------------- land gates
def path_span(paving, p, bearing, reach=14.0):
    """The paved cross-section through p across a path running at `bearing`: its two ends (plan points)."""
    t = np.array([math.cos(math.radians(bearing)), math.sin(math.radians(bearing))]); n = np.array([-t[1], t[0]])
    p = np.asarray(p, float)
    seg = LineString([p - n * reach, p + n * reach]).intersection(paving)
    parts = [g for g in getattr(seg, "geoms", [seg]) if g.geom_type == "LineString" and g.length > 1.0]
    if not parts:
        return None
    best = min(parts, key=lambda g: g.distance(Point(*p)))
    a, b = (np.array(c) for c in (best.coords[0], best.coords[-1]))
    return a, b, t, n


def gate(M, gr, name, style, a, b, t):
    """Posts just outside both ends of the paved span a-b, a beam over the path (not for Tomorrowland)."""
    w = np.linalg.norm(b - a); n = (b - a) / w
    pa, pb = a - n * 0.8, b + n * 0.8
    za, zb_ = gr.z(*pa), gr.z(*pb)
    T3, N3 = np.array([*t, 0]), np.array([*n, 0])
    if style == "adv":
        top = max(za, zb_) + 5.2
        for p, z in ((pa, za), (pb, zb_)):
            loft_rect(M["PH_stone"], P3(p, z - 0.3), t, n, [(0.75, 0.75, 0.0), (0.7, 0.7, 1.5), (0.55, 0.55, 1.6)])
            loft_rect(M["PH_wood"], P3(p, z + 1.6), t, n, [(0.32, 0.32, 0.0), (0.28, 0.28, top - z - 1.6 + 0.6)], cap=False)
            loft_rect(M["PH_thatch"], P3(p, top + 0.6), t, n, [(0.95, 0.95, 0.0), (0.75, 0.75, 0.3), (0.05, 0.05, 1.3)])
        box(M["PH_wood"], P3((pa + pb) / 2, top), (0.2, w / 2 + 1.0, 0.22), (T3, N3, UP))
        box(M["PH_sign"], P3((pa + pb) / 2, top - 0.75) + T3 * 0.25, (0.05, min(3.2, w * 0.3), 0.5), (T3, N3, UP))
        for s in (-1, 1):
            frustum(M["PH_wood"], P3((pa + pb) / 2 + n * s * min(2.6, w * 0.25), top - 0.2), P3((pa + pb) / 2 + n * s * min(2.6, w * 0.25), top - 0.3) + T3 * 0.25 - UP * 0.2, 0.03, 0.03, n=4)
    elif style == "west":
        top = max(za, zb_) + 5.0
        for p, z in ((pa, za), (pb, zb_)):
            for s in (-0.28, 0.28):
                q = p + t * s
                frustum(M["PH_log"], P3(q, z - 0.3), P3(q, top + 0.5), 0.22, 0.2, n=8)
                lathe(M["PH_log"], (q[0], q[1], top + 0.5), [(0.2, 0.0), (0.1, 0.2), (0.0, 0.25)], n=8)
        frustum(M["PH_log"], P3(pa - n * 0.8, top), P3(pb + n * 0.8, top), 0.2, 0.2, n=8)
        frustum(M["PH_log"], P3(pa - n * 0.4, top - 1.3), P3(pb + n * 0.4, top - 1.3), 0.16, 0.16, n=8)
        box(M["PH_sign"], P3((pa + pb) / 2, top - 0.65) + T3 * 0.1, (0.06, min(3.4, w * 0.32), 0.45), (T3, N3, UP))
    else:   # tomorrow
        for p, z in ((pa, za), (pb, zb_)):
            loft_rect(M["PH_tomb"], P3(p, z - 0.3), t, n, [(0.9, 0.9, 0.0), (0.9, 0.9, 0.7)])
            frustum(M["PH_tomw"], P3(p, z + 0.4), P3(p, z + 8.2), 0.55, 0.18, n=6)
            for h in (2.4, 4.4, 6.2):
                r = 0.55 + (0.18 - 0.55) * (h - 0.4) / 7.8
                frustum(M["PH_tomb"], P3(p, z + h), P3(p, z + h + 0.18), r + 0.18, r + 0.18, n=12)
            sphere(M["PH_tomb"], P3(p, z + 8.6), 0.45, n=10, m=6)
        top = max(za, zb_) + 8.6
    return dict(width=round(float(w), 1), posts=[tuple(round(float(x), 1) for x in pa), tuple(round(float(x), 1) for x in pb)], top=round(float(top), 1))


# ---------------------------------------------------------------- build
def build():
    ways = {w["id"]: w for w in DL.DATA["ways"]}
    area = Polygon([(-640, 540), (-270, 540), (-270, 830), (-640, 830)])
    gr = Ground(area.bounds)
    M = {n: G.Mesh(n) for n in NAMES}
    info = {}
    taken = unary_union([g for g in (GR.model_footprint(m) for m in SKIP_MODELS) if g is not None and not g.is_empty])
    bpolys = {i: Polygon(w["pts"]).buffer(0) for i, w in ways.items()
              if w["closed"] and len(w["pts"]) >= 4 and "building" in w["tags"] and w["tags"]["building"] != "no"}
    buildings = unary_union([p for p in bpolys.values() if p.intersects(area)])
    water = unary_union([Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"] if w["closed"] and len(w["pts"]) >= 4
                         and (w["tags"].get("natural") == "water" or w["tags"].get("water")) and Polygon(w["pts"]).intersects(area)])

    crystal_palace(M, gr, bpolys[CRYSTAL], info)
    avoid = unary_union([buildings.difference(bpolys[PAVILION].buffer(0.3)), water, taken])
    plaza_pavilion(M, gr, max(getattr(bpolys[PAVILION].difference(DH_PART), "geoms", [bpolys[PAVILION].difference(DH_PART)]), key=lambda g: g.area), info, avoid)
    bandstand(M, gr, bpolys[BANDSTAND], info)

    kiosks = []
    for i, p in bpolys.items():
        if i in (CRYSTAL, PAVILION, BANDSTAND) or not CLIP.contains(p.centroid) or not (KIOSK_MIN <= p.area <= KIOSK_MAX):
            continue
        if taken.intersection(p).area > 0.3 * p.area and ways[i]["tags"]["building"] == "roof":
            continue
        cin = GR.model_footprint("cinderella")
        if cin is not None and cin.intersection(p).area > 0.2 * p.area:
            continue
        kiosk(M, gr, p, ways[i]["tags"]["building"] == "roof")
        kiosks.append(i)
    info["kiosks"] = kiosks

    ped = unary_union([Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"] if w["closed"] and len(w["pts"]) >= 4
                       and w["tags"].get("highway") == "pedestrian" and Polygon(w["pts"]).intersects(area)])
    fw = unary_union([LineString(w["pts"]).buffer(1.5, cap_style=2) for w in DL.DATA["ways"] if len(w["pts"]) >= 2
                      and w["tags"].get("highway") == "footway" and LineString(w["pts"]).intersects(area)])
    paving = unary_union([ped, fw]).difference(buildings).difference(water)
    info["gates"] = {}
    for name, style, p, bearing in GATES:
        sp = path_span(paving, p, bearing)
        if sp is None:
            info["gates"][name] = "no path found"
            continue
        a, b, t, n = sp
        info["gates"][name] = gate(M, gr, name, style, a, b, t)
    return M, info


def main():
    M, info = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, {k: m for k, m in M.items() if m.tris})
    print(f"[plaza hub] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print("  triangles:", {k: len(m.tris) for k, m in M.items()})


if __name__ == "__main__":
    main()
