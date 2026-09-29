"""東京ディズニーランドのプラザ(ハブ)周りの建物 -- the buildings round the plaza hub (plan 3, phase 5; plain Python, Blender is
not needed; no trees, no round clipped shrubs, no night version):

  python src/ds_tdl_plaza_ground.py      # (phase 3) the plaza ground: output/disneysea/models/tdl_plaza_ground.json
  python src/ds_tdl_plaza_hub.py         # -> output/disneysea/models/tdl_plaza_hub.json (glTF, buffer embedded) + a summary
  python src/export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_plaza_hub", layer ディズニーランド)

Relation to ds_tdl_plaza_buildings.py (Blender): that script is the ENTRANCE plaza / World Bazaar side (the promenade
buildings, security canopies, service buildings, the shop block west of World Bazaar, Monsters, Inc.). None of the
buildings here is in it (checked by OSM id and by its exported footprint), so this is a new model, not a rework.

What is modelled (outlines: the OSM building ways, ids below; every height is an ESTIMATE):
  crystal   クリスタルパレス・レストラン (way 72865093, ~55 x 55 m): from the two Commons photos
            (docs/plaza/commons_crystal_palace_restaurant_1/2.jpg): a white one-storey arcade of arched windows all
            round, a white cornice, a bottle-green mansard with small dormers, square corner pavilions with bell-shaped
            green roofs and gold finials, and over the middle a big glass barrel vault on green iron ribs whose arched
            end faces the hub, with two small lanterns on its ridge. Where the photos do not reach (the far sides, the
            vault's length and radius, the pavilions' number and places: at the outline's four outermost corners) it is
            an ESTIMATE.
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
KIOSK_MIN, KIOSK_MAX = 3.5, 40.0                 # small mapped buildings inside CLIP (m^2) become kiosks / canopies
SKIP_MODELS = ("cinderella", "tdl_world_bazaar", "tdl_plaza_buildings", "tdl_plaza_center")
# land gates: (land, style, a point on the path, the path's direction there (plan bearing, deg from +x))
GATES = (("Adventureland", "adv", (-349.5, 732.5), 60.0),
         ("Westernland", "west", (-352.0, 655.0), -8.0),
         ("Tomorrowland", "tom", (-509.0, 663.5), 196.0))
NAMES = ("PH_white", "PH_cream", "PH_green", "PH_roof", "PH_iron", "PH_glass", "PH_win", "PH_gold", "PH_stone",
         "PH_wood", "PH_log", "PH_thatch", "PH_sign", "PH_tomw", "PH_tomb")
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
def crystal_palace(M, gr, poly, info):
    P = orient(poly.buffer(0).simplify(0.9), 1.0)
    ring = ring_ccw(P)
    zlo, zhi = gr.span(P)
    zb, zf = zlo - 0.4, zhi + 0.05
    E = 5.6                                               # the arcade storey (ESTIMATE; the photo shows one tall storey)
    slab(M["PH_stone"], M["PH_stone"], P.buffer(0.25, join_style=2), zb, zf + 0.35)          # the plinth
    facade(M, ring, zb, zf + 0.35, E - 0.35, bay=3.3, head=0.9)
    zc = zf + E
    cornice(M, P, zc, 0.55, 0.4)
    zm = zc + 0.55; MD, MH = 1.7, 2.5
    inner = mansard(M, ring, zm, MD, MH)
    top = Polygon(inner)
    if not top.is_valid:
        top = P.buffer(-MD, join_style=2)
    zt = zm + MH
    slab(M["PH_roof"], M["PH_roof"], top, zt - 0.3, zt)
    nd = dormers(M, ring, inner, zm, MH)

    # the glass barrel vault: its axis points at the hub, its arched end faces it (the photos, from the hub side)
    c = np.array(top.centroid.coords[0])
    ax = c - np.array(HUB_C); ax /= np.linalg.norm(ax); bx = np.array([-ax[1], ax[0]])
    Lh, R = 14.0, 7.5
    while Lh > 6 and not top.buffer(-0.5).contains(Polygon([c + ax * s * Lh + bx * t * (R + 0.4) for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))])):
        Lh -= 0.5; R = max(5.0, R - 0.15)
    A3, B3 = np.array([*ax, 0]), np.array([*bx, 0])
    zv = zt + 0.9
    loft_rect(M["PH_white"], P3(c, zt - 0.1), ax, bx, [(Lh + 0.3, R + 0.3, 0.0), (Lh + 0.3, R + 0.3, 1.0)], cap=False)
    NA = 14
    arc = lambda s, k, r=R: P3(c, zv) + A3 * s + B3 * r * math.cos(math.pi * k / NA) + UP * r * math.sin(math.pi * k / NA)
    for k in range(NA):
        quad(M["PH_glass"], arc(-Lh, k), arc(Lh, k), arc(Lh, k + 1), arc(-Lh, k + 1), None)
    for s in (-Lh, Lh):                                   # the arched ends: glass, radial glazing bars, a fanlight ring
        for k in range(NA):
            tri(M["PH_glass"], P3(c, zv) + A3 * s, arc(s, k), arc(s, k + 1), A3 * np.sign(s))
        for k in range(0, NA + 1, 2):
            frustum(M["PH_iron"], P3(c, zv) + A3 * s, arc(s, k), 0.09, 0.09, n=4)
        for k in range(NA):
            frustum(M["PH_iron"], P3(c, zv) + A3 * s + B3 * R * 0.35 * math.cos(math.pi * k / NA) + UP * R * 0.35 * math.sin(math.pi * k / NA),
                    P3(c, zv) + A3 * s + B3 * R * 0.35 * math.cos(math.pi * (k + 1) / NA) + UP * R * 0.35 * math.sin(math.pi * (k + 1) / NA), 0.08, 0.08, n=4)
    nrib = int(2 * Lh // 2.6) + 1
    for s in np.linspace(-Lh, Lh, nrib):                  # the iron ribs
        for k in range(NA):
            frustum(M["PH_iron"], arc(s, k, R + 0.08), arc(s, k + 1, R + 0.08), 0.11, 0.11, n=4, caps=False)
    for k in range(0, NA + 1, 2):                          # purlins
        frustum(M["PH_iron"], arc(-Lh, k, R + 0.1), arc(Lh, k, R + 0.1), 0.07, 0.07, n=4, caps=False)
    for s in (-Lh * 0.45, Lh * 0.45):                      # two lanterns on the ridge
        q = P3(c, zv + R - 0.2) + A3 * s
        loft_rect(M["PH_white"], q, ax, bx, [(1.0, 1.0, 0.0), (1.0, 1.0, 0.25)], cap=False)
        loft_rect(M["PH_glass"], q + UP * 0.25, ax, bx, [(0.9, 0.9, 0.0), (0.9, 0.9, 1.2)], cap=False)
        loft_rect(M["PH_green"], q + UP * 1.45, ax, bx, [(1.15, 1.15, 0.0), (1.15, 1.15, 0.15), (0.1, 0.1, 1.3)])
        finial(M, *(q + UP * 2.7), h=1.0)
    info["crystal"] = dict(floor_z=round(zf, 2), eaves=round(zc - zf, 1), mansard_top=round(zt - zf, 1),
                           vault=dict(half_len=round(Lh, 1), r=round(R, 1), apex=round(zv + R - zf, 1)), dormers=nd)

    # corner pavilions: at the outline's four outermost corners (relative to the vault's axes), inset into the footprint
    pv = []
    for sa, sb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        v = max(ring, key=lambda p: sa * np.dot(p - c, ax) + sb * np.dot(p - c, bx))
        d = v - c; d /= np.linalg.norm(d); hs = 3.3
        for back in np.arange(3.6, 14, 0.4):
            q = v - d * back
            sq = Polygon([q + ax * i * hs + bx * j * hs for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            if P.contains(sq) and not top.buffer(-0.3).contains(sq):
                break
        else:
            continue
        pv.append(q)
        zp = zf + E + 3.1
        loft_rect(M["PH_white"], P3(q, zb), ax, bx, [(hs, hs, 0.0), (hs, hs, zp - zb)], cap=False)
        sqr = ring_ccw(sq)
        for i in range(4):
            a, b = sqr[i], sqr[(i + 1) % 4]; nrm = out_normal(a, b); e = (b - a) / np.linalg.norm(b - a)
            arched_window(M["PH_win"], a + e * 1.3, b - e * 1.3, nrm, zf + E + 0.9, zp - 1.1 - (hs - 1.3), off=0.03)
            for t in (0.25, hs * 2 - 0.25):
                box(M["PH_white"], P3(a + e * t, (zb + zp) / 2) + np.array([*nrm, 0]) * 0.12, (0.3, 0.12, (zp - zb) / 2), (np.array([*e, 0]), np.array([*nrm, 0]), UP))
        loft_rect(M["PH_white"], P3(q, zp), ax, bx, [(hs + 0.35, hs + 0.35, 0.0), (hs + 0.35, hs + 0.35, 0.45)])
        loft_rect(M["PH_green"], P3(q, zp + 0.45), ax, bx, [(hs + 0.1, hs + 0.1, 0.0), (hs + 0.25, hs + 0.25, 0.5), (hs - 0.2, hs - 0.2, 1.4),
                                                           (hs - 1.3, hs - 1.3, 2.6), (0.9, 0.9, 3.3), (0.4, 0.4, 3.7), (0.1, 0.1, 3.8)])
        finial(M, *P3(q, zp + 4.2), h=1.5)
    info["crystal"]["pavilions"] = len(pv)
    return P


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
    plaza_pavilion(M, gr, bpolys[PAVILION], info, avoid)
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
