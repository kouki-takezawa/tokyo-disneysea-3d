"""トゥモローランド・テラス -- Tomorrowland Terrace, the Land's biggest restaurant (plain Python, Blender is not needed; no
trees, no round clipped shrubs, no night version):

  python src/ds_tdl_tomorrowland_terrace.py   # -> output/disneysea/models/tdl_tomorrowland_terrace.json + a summary
  python src/export_mock.py                   # rebuilds the page ("tdl_tomorrowland_terrace", layer ディズニーランド)

Sources: the user's 8 photos (images/tomorrowland_terrace/1-8.png, not in the repo: the pond side, the entrance under the
faceted glass dome, the red-glass entrance, the covered terrace and its coffered ceiling, the park map), web photos
looked at for reference only (castel.jp, tdrfan.com: the dining hall -- the walls (white: the user, 2026-09-30), a stainless band round a raised
ceiling with a lit lattice, red patterned carpet, red chairs, white round tables, red booths; the stage with its pink
proscenium; the sign: two pale-blue hexagons, a dark-blue band with the name, a red diamond), the GSI aerial photo
(plan, the rotunda, the dome) and OSM:
  way 217930860 "トゥモローランド・テラス" (the south-east lobe: the dining hall, the domed entrance, the covered terrace
  along the parade route) + way 217930859 (unnamed, building=retail, toilets: the north-west lobe with the round rotunda).
The OSM outlines are the roof's edge (checked on the aerial photo): the walls stand WALL_IN m behind it under a deep
white fascia; on the parade side and on the two pond sides they stand further back (covered terraces).

What is modelled (every height is an ESTIMATE from people in the photos, 1.70 m):
  outside  stepped roof: a white fascia (soffit 4.3 m, top 5.6 m) round the outline, two pale-blue tiers set back over
           it (6.5 / 7.3 m); the rotunda's drum and low cone roof with a hexagonal cap (~10 m); the faceted glass dome on
           a white box over the south-east entrance (~11 m); walls of pale blue / lavender-grey panels, cream by the domed
           entrance, glazing with white mullions, a red glass wall by the south-west entrance; the covered terraces with
           white columns on blue bases, a coffered ceiling (blue pyramids, some lit), railings with planters on the pond
           sides; the hexagon sign under the parade-side fascia, a pylon sign with the name by the south-east entrance;
           blue-edged planters (hedge and yellow flowers) and white benches at the domed entrance.
  inside   red carpet, white walls (the user), a flat white ceiling (3.9 m) with a raised lit lattice over the middle of the hall
           edged by a stainless band; ordering counters (blue, stainless top, lit menu boards) along the kitchen on the
           south-west side; a low partition with a red booth; the rotunda (ceiling up to ~8 m, a ring light) with the stage
           and its pink proscenium and screen; white round tables with red chairs everywhere (the web photos), also on the
           covered terraces. The kitchen and the back-of-house on the west are closed blocks.
ESTIMATES: all heights, the positions of the doors, the counters, the stage and the kitchen, the table layout (the real
  restaurant seats ~1,500), the colours of the walls not in any photo (the north and west sides).
Walk: the floor is one slab at the 85th percentile of the ground round the outline (the ground models leave a hole
  under it; from -0.9 to -0.2 m round it, so every door is a step of 0.5 m or less); the doors are openings in the
  walls (the walls, glass and furniture stop the walker); the stage is too high to step onto.
Frame: the mock's local metres (+x east, +y north), z up; plan (x, y, z) -> glTF (x, z, -y) by ds_tdl_ground.write_gltf.
"""
import sys, json, math, pathlib

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.affinity import rotate
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
from ds_tdl_plaza_center import tri, frustum, box
from ds_tdl_plaza_hub import Ground, quad, P3, UP

MODELS = ROOT / "output" / "disneysea" / "models"
OUT = MODELS / "tdl_tomorrowland_terrace.json"
LOBE_A, LOBE_B = 217930860, 217930859        # the south-east lobe (named) and the north-west lobe with the rotunda
WALL_IN = 1.6                                  # walls behind the roof's edge (m)
Z_C, Z_E, Z_T1, Z_T2, Z_T3 = 3.9, 4.3, 5.6, 6.5, 7.3   # over the floor: ceiling, soffit, fascia top, the two tiers
ROT_C, ROT_R = (-537.0, 624.0), 14.0          # the rotunda (aerial photo)
ROT_OPEN = ((-78, -36), (-14, 14), (70, 100))  # its wall's openings (deg): to the hall, the pond deck, the north door
DOME_C, DOME_R = (-493.0, 548.0), 3.5          # the faceted glass dome over the south-east entrance (aerial photo)
HALL_C = (-510.0, 585.0)                       # the raised ceiling's centre
AXU = np.array([-math.sqrt(0.5), math.sqrt(0.5)])   # the hall's long axis (north-west), from the south-west walls
AXV = np.array([math.sqrt(0.5), math.sqrt(0.5)])    # across it (north-east)
KIT_P0, KIT_D = np.array([-488.7, 543.8]), np.array([-0.729, 0.684])   # the south-west wall line (kitchen side)
DOORS = {"se": (-491.8, 543.9), "sw": (-503.5, 550.0), "n": (-533.0, 652.8), "ne": (-517.0, 653.0)}
PARADE_SIGN = (-476.5, 585.0)                  # the hexagon sign hangs under the fascia nearest this point
PYLON = (-480.5, 551.0)
NAMES = ("TT_white", "TT_sky", "TT_blue", "TT_navy", "TT_cream", "TT_grey", "TT_roof", "TT_glass", "TT_redglass", "TT_dome",
         "TT_carpet", "TT_wallin", "TT_steel", "TT_ceil", "TT_light", "TT_lattice", "TT_chair", "TT_table", "TT_booth",
         "TT_stage", "TT_screen", "TT_hex", "TT_coffer", "TT_menu", "TT_sign", "TT_signb", "TT_signr", "TT_text",
         "TT_hedge", "TT_flower", "TT_planter", "TT_rail")


# ---------------------------------------------------------------- small helpers
def polys(g, min_area=0.05):
    return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty and p.area > min_area]


def cap(mesh, g, z, down=False):
    """Flat faces over a shapely geometry at height z (facing up, or down for a ceiling)."""
    for p in polys(g):
        for c in G.cdt(p):
            tri(mesh, P3(c[0], z), P3(c[1], z), P3(c[2], z), -UP if down else UP)


def sides(mesh, g, z0, z1, inward=False):
    """The vertical faces round a geometry's rings from z0 to z1 (facing out of it, or into it)."""
    for p in polys(g):
        for ring in [p.exterior] + list(p.interiors):
            cs = [np.array(c) for c in ring.coords]
            for a, b in zip(cs[:-1], cs[1:]):
                if np.linalg.norm(b - a) < 1e-6:
                    continue
                e = (b - a) / np.linalg.norm(b - a); n = np.array([e[1], -e[0]])
                if p.buffer(0).contains(Point(*((a + b) / 2 + 0.02 * n))):
                    n = -n
                if inward:
                    n = -n
                quad(mesh, P3(a, z0), P3(b, z0), P3(b, z1), P3(a, z1), np.array([*n, 0]))


def slab(top, side, g, z0, z1):
    cap(top, g, z1); sides(side, g, z0, z1)


def bar(mesh, p0, p1, w=0.06):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    if np.linalg.norm(p1 - p0) < 1e-4:
        return
    frustum(mesh, p0, p1, w, w, n=4, caps=False)


def plane_pts(c, u, w, n, off, pts2):
    return [np.asarray(c, float) + x * u + y * w + off * n for x, y in pts2]


def plate(mesh, poly2, c, u, w, n, off=0.0, back=None, t=0.0, edge=None):
    """A flat 2D shape (shapely, in (u, w) metres round c) on the plane through c; optional thickness t (a back face and
    an edge band)."""
    u, w, n = (np.asarray(v, float) for v in (u, w, n))
    for p in polys(poly2, 1e-6):
        for tr in G.cdt(p):
            A = plane_pts(c, u, w, n, off, tr)
            tri(mesh, *A, n)
            if t:
                B = plane_pts(c, u, w, n, off - t, tr)
                tri(back or mesh, *B, -n)
        if t:
            cs = list(p.exterior.coords)
            for a, b in zip(cs[:-1], cs[1:]):
                A0, B0 = plane_pts(c, u, w, n, off, (a, b)), plane_pts(c, u, w, n, off - t, (a, b))
                m = np.mean([*A0, *B0], 0)
                quad(edge or mesh, A0[0], A0[1], B0[1], B0[0], m - np.asarray(c, float) - np.dot(m - np.asarray(c, float), n) * n)


_TEXT = {}


def text_poly(s, height, font="arialbd.ttf"):
    """The outline of a line of text as a shapely geometry, `height` m tall (cap height), centred on (0, 0)."""
    key = (s, height, font)
    if key in _TEXT:
        return _TEXT[key]
    f = ImageFont.truetype(f"C:/Windows/Fonts/{font}", 96)
    l, t, r, b = f.getbbox(s)
    im = Image.new("L", (r - l + 12, b - t + 12), 0)
    ImageDraw.Draw(im).text((6 - l, 6 - t), s, font=f, fill=255)
    a = (np.array(im) > 127).astype(np.uint8)
    cnts, hier = cv2.findContours(a, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    sc = height / (b - t); H, Wd = a.shape
    out = []
    for i, c in enumerate(cnts):
        if hier[0][i][3] != -1 or len(c) < 3:
            continue
        holes = []
        k = hier[0][i][2]
        while k != -1:
            if len(cnts[k]) >= 3:
                holes.append([((x - Wd / 2) * sc, (H / 2 - y) * sc) for x, y in cnts[k][:, 0]])
            k = hier[0][k][0]
        p = Polygon([((x - Wd / 2) * sc, (H / 2 - y) * sc) for x, y in c[:, 0]], holes).buffer(0)
        if not p.is_empty:
            out.append(p.simplify(sc * 0.6))
    _TEXT[key] = unary_union(out)
    return _TEXT[key]


def chair(M, p, face, z):
    f = np.array([face[0], face[1], 0.0]); f /= np.linalg.norm(f); s = np.array([-f[1], f[0], 0.0])
    box(M["TT_chair"], P3(p, z + 0.46), (0.21, 0.21, 0.035), basis=(s, f, UP))
    box(M["TT_chair"], P3(p, z + 0.74) - f * 0.19, (0.2, 0.025, 0.25), basis=(s, f, UP))
    frustum(M["TT_steel"], P3(p, z), P3(p, z + 0.43), 0.03, 0.03, n=4, caps=False)


def table_set(M, p, z, n_chairs=4, rot=0.0):
    frustum(M["TT_table"], P3(p, z + 0.69), P3(p, z + 0.73), 0.46, 0.46, n=10)
    frustum(M["TT_steel"], P3(p, z), P3(p, z + 0.69), 0.04, 0.04, n=4, caps=False)
    frustum(M["TT_steel"], P3(p, z), P3(p, z + 0.03), 0.25, 0.25, n=4, caps=True)
    for k in range(n_chairs):
        a = rot + 2 * math.pi * k / n_chairs
        d = np.array([math.cos(a), math.sin(a)])
        chair(M, np.asarray(p) + 0.72 * d, -d, z)


def grid_points(region, c, u, v, step):
    """Points of a grid (axes u, v through c, spacing step) inside region."""
    x0, y0, x1, y1 = region.bounds
    R = math.hypot(x1 - x0, y1 - y0)
    out = []
    for i in range(-int(R / step) - 2, int(R / step) + 3):
        for j in range(-int(R / step) - 2, int(R / step) + 3):
            p = np.asarray(c) + i * step * u + j * step * v
            if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and region.contains(Point(*p)):
                out.append(p)
    return out


def rect(c, u, v, hu, hv):
    c = np.asarray(c, float)
    return Polygon([c + su * hu * u + sv * hv * v for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))])


# ---------------------------------------------------------------- plan
def plan():
    ways = {w["id"]: w for w in DL.DATA["ways"]}
    A, B = Polygon(ways[LOBE_A]["pts"]).buffer(0), Polygon(ways[LOBE_B]["pts"]).buffer(0)
    U = A.union(B).buffer(0.3, join_style=2).buffer(-0.3, join_style=2)
    pa = ways[LOBE_A]["pts"]
    east = LineString(pa[9:22]).buffer(6.5, join_style=2)          # the parade side
    north = LineString(pa[1:9]).buffer(5.0, join_style=2)          # the pond side of lobe A
    beast = LineString([(-509.1, 647.5), (-506.1, 644.8), (-506.4, 636.5), (-506.7, 632.1), (-511.0, 617.3)]).buffer(5.0, join_style=2)
    cov = unary_union([east, north, beast]).intersection(U)
    inner = U.buffer(-WALL_IN, join_style=2).difference(cov)
    inner = max(polys(inner), key=lambda p: p.area)
    # the kitchen: a band along the south-west walls (s along the wall line, t into the hall)
    k0 = KIT_P0; kn = np.array([KIT_D[1], -KIT_D[0]]) * -1
    kn = kn if np.dot(kn, AXV) > 0 else -kn
    kit = Polygon([k0 + s * KIT_D + t * kn for s, t in ((31, -5), (52, -5), (52, 8.5), (31, 8.5))]).intersection(inner)   # clear of the aisle from the domed entrance
    boh = inner.intersection(sbox(-600, 560, -560, 670))
    rot = Point(*ROT_C).buffer(ROT_R, 48)
    hall = rect(HALL_C, AXU, AXV, 13.0, 6.5).intersection(inner.buffer(-2.5))
    return dict(U=U, cov=cov, inner=inner, east=east.intersection(U), decks=unary_union([north, beast]).intersection(U).difference(east),
                kit=max(polys(kit), key=lambda p: p.area), boh=max(polys(boh), key=lambda p: p.area), rot=rot, hall=hall, kn=kn)


# ---------------------------------------------------------------- the walls
def walls(M, L, zf, zb):
    """The outer walls on the inner outline, bay by bay: glass, doors, red glass, solid panels (inside white)."""
    ring = L["inner"].exterior
    if not Polygon(ring).exterior.is_ccw:
        ring = LineString(list(ring.coords)[::-1])
    door_pts = {k: np.array(ring.interpolate(ring.project(Point(*p))).coords[0]) for k, p in DOORS.items()}
    cs = [np.array(c) for c in ring.coords]
    info = {"bays": 0, "glass": 0, "doors": 0}
    all_doors = []
    kit_zone, cov_zone = L["kit"].buffer(1.2), L["cov"].buffer(0.6)
    idx = 0
    for a, b in zip(cs[:-1], cs[1:]):
        Ln = np.linalg.norm(b - a)
        if Ln < 0.05:
            continue
        e = (b - a) / Ln; n = np.array([e[1], -e[0]])            # CCW ring: outward is to the right
        nb = max(1, round(Ln / 3.0))
        for k in range(nb):
            p, q = a + e * Ln * k / nb, a + e * Ln * (k + 1) / nb
            m = (p + q) / 2; idx += 1; info["bays"] += 1
            door = any(np.linalg.norm(m - d) < 1.8 for d in door_pts.values())
            by_cov = cov_zone.contains(Point(*m))
            if by_cov and not door and idx % 3 == 0 and Ln > 2.5:
                door = True
            red = np.linalg.norm(m - door_pts["sw"]) < 6.0 and not door
            se = np.linalg.norm(m - door_pts["se"]) < 7.5
            kind = ("door" if door else "red" if red else "glass" if by_cov or (se and idx % 2 == 0)
                    else "solid" if kit_zone.contains(Point(*m)) else "glass" if idx % 5 == 0 else "solid")
            if kind == "door":
                all_doors.append(m)
            ext = "TT_cream" if se else "TT_grey" if m[0] < -526 else "TT_sky"
            N3 = np.array([*n, 0.0])
            quad(M["TT_white"], P3(p, zb), P3(q, zb), P3(q, zf), P3(p, zf), N3)       # the base
            if kind == "solid":
                quad(M[ext], P3(p, zf), P3(q, zf), P3(q, zf + Z_E), P3(p, zf + Z_E), N3)
                pi, qi = p - n * 0.25, q - n * 0.25
                quad(M["TT_wallin"], P3(pi, zf), P3(qi, zf), P3(qi, zf + Z_C), P3(pi, zf + Z_C), -N3)
                quad(M["TT_white"], P3(p, zf + 0.0), P3(q, zf), P3(q, zf + 0.35), P3(p, zf + 0.35), N3 + 0.0)   # skirting line
            else:
                info["glass" if kind != "door" else "doors"] += 1
                g = "TT_redglass" if kind == "red" else "TT_glass"
                z0 = zf + (2.5 if kind == "door" else 0.0)
                quad(M[g], P3(p, z0), P3(q, z0), P3(q, zf + Z_E), P3(p, zf + Z_E), N3)
                for zz in ((zf + 2.5, zf + 0.05) if kind != "door" else (zf + 2.5,)):
                    bar(M["TT_white"], P3(p, zz) + N3 * 0.03, P3(q, zz) + N3 * 0.03, 0.04)
                if kind == "red":                                    # the white diagonal bars on the red glass
                    bar(M["TT_white"], P3(p, zf + 0.3) + N3 * 0.03, P3(q, zf + 2.2) + N3 * 0.03, 0.035)
                if kind != "door":   # the lintel inside over the glass (from the ceiling down to the head of the glass)
                    pass
            bar(M["TT_white"], P3(p, zf) + N3 * 0.03, P3(p, zf + Z_E) + N3 * 0.03, 0.05)   # a mullion / pier at each bay end
            if kind == "door" and np.linalg.norm(m - door_pts["sw"]) < 1.8:
                tp = text_poly("TOMORROWLAND TERRACE", 0.26)
                plate(M["TT_text"], tp, P3(m, zf + 3.45) + N3 * 0.05, np.array([*e, 0]), UP, N3)
    return info, door_pts, all_doors


# ---------------------------------------------------------------- roof, ceilings, floor
def roof(M, L, zf):
    U, inner = L["U"], L["inner"]
    rot = L["rot"]; dome_box = rect(DOME_C, np.array([1.0, 0]), np.array([0, 1.0]), 3.8, 3.8)
    t2 = unary_union([p for p in polys(U.buffer(-3.0, join_style=2)) if p.area > 30])
    t3 = unary_union([p for p in polys(U.buffer(-9.0, join_style=2)) if p.area > 60])
    hole = unary_union([rot, dome_box])
    # fascia and tiers
    sides(M["TT_white"], U, zf + Z_E, zf + Z_T1)
    cap(M["TT_roof"], U.difference(t2).difference(hole), zf + Z_T1)
    sides(M["TT_sky"], t2, zf + Z_T1, zf + Z_T2)
    cap(M["TT_roof"], t2.difference(t3).difference(hole), zf + Z_T2)
    sides(M["TT_sky"], t3, zf + Z_T2, zf + Z_T3)
    cap(M["TT_roof"], t3.difference(hole), zf + Z_T3)
    # a pale-blue line under the fascia's top edge (the photos: a thin blue stripe)
    sides(M["TT_sky"], U.buffer(0.02, join_style=2), zf + Z_T1 - 0.25, zf + Z_T1 - 0.1)
    # the soffit round the building (coffers on the parade side) and the ceilings inside
    east = L["east"]
    cells, lit = [], []
    for k, p in enumerate(grid_points(east.buffer(-1.3), (-480.0, 580.0), AXU, AXV, 2.4)):
        sq = rect(p, AXU, AXV, 1.2, 1.2)
        if not east.buffer(-0.2).contains(sq) or inner.buffer(0.3).intersects(sq):
            continue
        cells.append(sq)
        top = P3(p, zf + Z_E + 0.45)
        cs = [np.array(c) for c in sq.exterior.coords][:4]
        lit_cell = k % 5 == 2
        for i in range(4):
            a, b = cs[i], cs[(i + 1) % 4]
            tri(M["TT_light" if lit_cell else "TT_coffer"], P3(a, zf + Z_E), P3(b, zf + Z_E), top, -UP)
            bar(M["TT_white"], P3(a, zf + Z_E - 0.08), P3(b, zf + Z_E - 0.08), 0.08)
        lit.append(lit_cell)
    cap(M["TT_ceil"], U.difference(inner).difference(unary_union(cells) if cells else Polygon()), zf + Z_E, down=True)
    hall = L["hall"]
    cap(M["TT_ceil"], inner.difference(rot).difference(hall), zf + Z_C, down=True)
    # the raised hall ceiling: a stainless band, white sides, a lit lattice
    sides(M["TT_steel"], hall, zf + Z_C, zf + Z_C + 0.55, inward=True)
    sides(M["TT_wallin"], hall, zf + Z_C + 0.55, zf + 5.3, inward=True)
    cap(M["TT_light"], hall, zf + 5.3, down=True)
    x0, y0, x1, y1 = hall.bounds
    for s in np.arange(-14, 14.01, 1.6):
        for d0, d1 in ((AXU, AXV), (AXV, AXU)):
            ln = LineString([np.asarray(HALL_C) + s * d1 - 30 * d0, np.asarray(HALL_C) + s * d1 + 30 * d0]).intersection(hall)
            for g in getattr(ln, "geoms", [ln]):
                if g.is_empty or g.length < 0.2:
                    continue
                (ax, ay), (bx, by) = list(g.coords)[0], list(g.coords)[-1]
                bar(M["TT_lattice"], (ax, ay, zf + 5.2), (bx, by, zf + 5.2), 0.06)
    return dict(coffers=len(cells), lit=sum(lit))


def floor(M, L, zf, zb):
    cap(M["TT_carpet"], L["inner"], zf)
    cap(M["TT_hex"], L["U"].difference(L["inner"]), zf)
    sides(M["TT_white"], L["U"], zb, zf)


# ---------------------------------------------------------------- the rotunda and the dome
def rotunda(M, zf):
    cx, cy = ROT_C; n = 48
    def ang_open(a):
        d = math.degrees(a)
        return any(lo <= d <= hi for lo, hi in ROT_OPEN)
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n - math.pi, 2 * math.pi * (k + 1) / n - math.pi
        am = (a0 + a1) / 2
        p = np.array([cx + ROT_R * math.cos(a0), cy + ROT_R * math.sin(a0)]); q = np.array([cx + ROT_R * math.cos(a1), cy + ROT_R * math.sin(a1)])
        nrm = np.array([math.cos(am), math.sin(am), 0.0])
        z0 = zf + (3.0 if ang_open(am) else 0.0)
        for s in (1, -1):   # both faces of the wall, 0.2 m apart
            o = nrm[:2] * 0.1 * s
            quad(M["TT_wallin"], P3(p + o, z0), P3(q + o, z0), P3(q + o, zf + Z_C), P3(p + o, zf + Z_C), nrm * s)
        quad(M["TT_wallin"], P3(p, zf + Z_C), P3(q, zf + Z_C), P3(q, zf + 7.0), P3(p, zf + 7.0), -nrm)   # the drum inside
        po, qo = p + nrm[:2] * 0.3, q + nrm[:2] * 0.3   # outside, 0.3 m out (the same face would flicker with the inside)
        quad(M["TT_sky"], P3(po, zf + Z_T1), P3(qo, zf + Z_T1), P3(qo, zf + 8.3), P3(po, zf + 8.3), nrm)
        # the cone roof outside, the shallow cone ceiling inside
        r2 = 2.0
        P = lambda r, a, z: np.array([cx + r * math.cos(a), cy + r * math.sin(a), z])
        quad(M["TT_roof"], P(ROT_R + 0.4, a0, zf + 8.3), P(ROT_R + 0.4, a1, zf + 8.3), P(r2, a1, zf + 10.0), P(r2, a0, zf + 10.0), UP + nrm * 0.1)
        quad(M["TT_ceil"], P(ROT_R, a0, zf + 7.0), P(ROT_R, a1, zf + 7.0), P(r2, a1, zf + 8.0), P(r2, a0, zf + 8.0), -UP)
        quad(M["TT_light"], P(7.5, a0, zf + 7.35), P(7.5, a1, zf + 7.35), P(6.7, a1, zf + 7.45), P(6.7, a0, zf + 7.45), -UP)   # the ring light
        if k % 4 == 0:
            bar(M["TT_white"], P(ROT_R + 0.4, a0, zf + 8.35), P(r2, a0, zf + 10.05), 0.08)   # roof ribs
    hexa = Polygon([(cx + 2.4 * math.cos(math.pi * k / 3), cy + 2.4 * math.sin(math.pi * k / 3)) for k in range(6)])
    slab(M["TT_roof"], M["TT_sky"], hexa, zf + 9.6, zf + 10.5)
    cap(M["TT_ceil"], Point(cx, cy).buffer(2.0, 12), zf + 8.0, down=True)
    # the stage on the west side: platform, pink proscenium, a screen
    stage = Point(cx, cy).buffer(ROT_R - 0.15, 48).intersection(sbox(cx - 20, cy - 20, cx - 8.0, cy + 20))
    slab(M["TT_stage"], M["TT_stage"], stage, zf - 0.1, zf + 0.8)
    X = cx - 8.2
    for yy in (cy - 5.4, cy + 5.4):
        box(M["TT_stage"], (X, yy, zf + 0.8 + 1.9), (0.45, 0.6, 1.9))
    box(M["TT_stage"], (X, cy, zf + 4.35), (0.45, 6.0, 0.35))
    box(M["TT_screen"], (cx - ROT_R + 0.6, cy, zf + 2.7), (0.05, 4.4, 1.6))
    box(M["TT_white"], (X - 0.2, cy, zf + 0.8 + 3.5), (0.2, 4.8, 0.08))   # the light bar under the header
    return stage


def geodesic(M, c, z0, r):
    """A faceted glass dome (rings of 10 points, staggered), with white bars on its edges."""
    rings = [(0.0, 0.0), (28.0, 0.5), (56.0, 0.0), (78.0, 0.5)]
    pts = [[np.array([c[0] + r * math.cos(math.radians(el)) * math.cos(2 * math.pi * (k + sh) / 10),
                      c[1] + r * math.cos(math.radians(el)) * math.sin(2 * math.pi * (k + sh) / 10),
                      z0 + r * 0.85 * math.sin(math.radians(el))]) for k in range(10)] for el, sh in rings]
    top = np.array([c[0], c[1], z0 + r * 0.85])
    ctr = np.array([c[0], c[1], z0])
    for i in range(len(pts) - 1):
        A, B = pts[i], pts[i + 1]
        for k in range(10):
            k2 = (k + 1) % 10
            for t3 in ((A[k], A[k2], B[k]), (A[k2], B[k2], B[k])) if rings[i + 1][1] else ((A[k], A[k2], B[k2]), (A[k], B[k2], B[k])):
                tri(M["TT_dome"], *t3, np.mean(t3, 0) - ctr)
                for a, b in ((t3[0], t3[1]), (t3[1], t3[2]), (t3[2], t3[0])):
                    bar(M["TT_white"], a, b, 0.045)
    for k in range(10):
        a, b = pts[-1][k], pts[-1][(k + 1) % 10]
        tri(M["TT_dome"], a, b, top, UP)
        bar(M["TT_white"], a, top, 0.045)


def dome(M, zf):
    sq = rect(DOME_C, np.array([1.0, 0]), np.array([0, 1.0]), 3.8, 3.8)
    slab(M["TT_white"], M["TT_white"], sq, zf + Z_T1 - 0.2, zf + 7.4)
    sides(M["TT_sky"], sq.buffer(0.03, join_style=2), zf + 6.7, zf + 7.0)
    geodesic(M, DOME_C, zf + 7.4, DOME_R)


# ---------------------------------------------------------------- inside
def counters(M, L, zf):
    kit = L["kit"]; kn = L["kn"]
    slab(M["TT_wallin"], M["TT_wallin"], kit, zf, zf + Z_C)
    # the counter along the kitchen's hall side (the edge whose outward normal points along kn)
    cs = [np.array(c) for c in kit.exterior.coords]
    n_ct = 0
    for a, b in zip(cs[:-1], cs[1:]):
        L2 = np.linalg.norm(b - a)
        if L2 < 2.0:
            continue
        e = (b - a) / L2; n = np.array([e[1], -e[0]])
        if kit.contains(Point(*((a + b) / 2 + 0.05 * n))):
            n = -n
        if np.dot(n, kn) < 0.8:
            continue
        m = (a + b) / 2; hu = L2 / 2 - 0.6
        box(M["TT_navy"], P3(m + n * 0.4, zf + 0.5), (0.4, hu, 0.5), basis=(np.array([*n, 0]), np.array([*e, 0]), UP))
        box(M["TT_steel"], P3(m + n * 0.42, zf + 1.04), (0.46, hu + 0.05, 0.04), basis=(np.array([*n, 0]), np.array([*e, 0]), UP))
        for s in np.arange(-hu + 1.5, hu - 1.0, 3.2):   # lit menu boards over the counter
            box(M["TT_menu"], P3(m + e * s + n * 0.06, zf + 2.95), (0.04, 1.2, 0.42), basis=(np.array([*n, 0]), np.array([*e, 0]), UP))
            n_ct += 1
        for s in np.arange(-hu + 1.0, hu, 2.4):         # queue rails: posts and a rope bar
            for t in (1.8, 3.2):
                p0 = m + e * s + n * t
                frustum(M["TT_steel"], P3(p0, zf), P3(p0, zf + 0.95), 0.03, 0.03, n=4, caps=False)
                if s + 2.4 < hu:
                    bar(M["TT_steel"], P3(p0, zf + 0.92), P3(p0 + e * 2.4, zf + 0.92), 0.02)
        tp = text_poly("TOMORROWLAND TERRACE", 0.32)
        plate(M["TT_text"], tp, P3(m + n * 0.03, zf + 3.55), np.array([*e, 0]) * -1 if n[0] * e[1] - n[1] * e[0] < 0 else np.array([*e, 0]), UP, np.array([*n, 0]))
    slab(M["TT_wallin"], M["TT_wallin"], L["boh"], zf, zf + Z_C)
    return n_ct


def booth(M, L, zf):
    """A low partition with a red booth along the raised hall's south-west side."""
    c = np.asarray(HALL_C) - AXV * 7.6
    u3, v3 = np.array([*AXU, 0]), np.array([*AXV, 0])
    box(M["TT_wallin"], P3(c, zf + 0.55), (11.0, 0.15, 0.55), basis=(u3, v3, UP))
    box(M["TT_steel"], P3(c, zf + 1.12), (11.05, 0.2, 0.03), basis=(u3, v3, UP))
    box(M["TT_booth"], P3(c + AXV * 0.45, zf + 0.23), (11.0, 0.3, 0.23), basis=(u3, v3, UP))
    box(M["TT_booth"], P3(c + AXV * 0.2, zf + 0.75), (11.0, 0.08, 0.3), basis=(u3, v3, UP))
    for s in np.arange(-10.0, 10.1, 2.0):   # small square tables in front of the booth
        p = c + AXV * 1.25 + AXU * s
        box(M["TT_table"], P3(p, zf + 0.71), (0.35, 0.35, 0.02), basis=(u3, v3, UP))
        frustum(M["TT_steel"], P3(p, zf), P3(p, zf + 0.69), 0.04, 0.04, n=4, caps=False)
        chair(M, p + AXV * 0.65, -AXV, zf)
    return c


def furniture(M, L, zf, door_pts, all_doors, stage, booth_c):
    inner, cov = L["inner"], L["cov"]
    aisles = []
    hubs = [np.asarray(HALL_C), np.asarray(ROT_C)]
    aisles.append(LineString(hubs).buffer(2.0))
    for d in door_pts.values():   # a clear space inside each door and an aisle from it to the nearest middle
        aisles.append(Point(*d).buffer(3.5))
        aisles.append(LineString([d, min(hubs, key=lambda h: np.linalg.norm(h - d))]).buffer(2.0))
    aisles += [Point(*d).buffer(3.2) for d in all_doors]
    avoid = unary_union([L["kit"].buffer(3.6), L["boh"].buffer(1.3), stage.buffer(2.0),
                         Point(*ROT_C).buffer(ROT_R + 1.0).difference(Point(*ROT_C).buffer(ROT_R - 1.0)),
                         LineString([booth_c - AXU * 11.5, booth_c + AXU * 11.5]).buffer(2.4), *aisles])
    free = inner.buffer(-1.2).difference(avoid)
    n_in = 0
    for p in grid_points(free, HALL_C, AXU, AXV, 3.2):
        table_set(M, p, zf, 4, rot=math.atan2(AXU[1], AXU[0]))
        n_in += 1
    tfree = cov.buffer(-0.9).difference(inner.buffer(1.3)).difference(unary_union([Point(*d).buffer(2.6) for d in all_doors]))
    n_out = 0
    for p in grid_points(tfree, (-480.0, 580.0), AXU, AXV, 2.9):
        table_set(M, p, zf, 4, rot=math.atan2(AXU[1], AXU[0]) + math.pi / 4)
        n_out += 1
    return n_in, n_out


# ---------------------------------------------------------------- outside
def columns_rails(M, L, zf):
    U, cov, decks = L["U"], L["cov"], L["decks"]
    ring = U.buffer(-0.6, join_style=2).exterior
    n_col = 0
    for d in np.arange(0, ring.length, 6.0):
        p = np.array(ring.interpolate(d).coords[0])
        if not cov.buffer(-0.3).contains(Point(*p)) or L["inner"].buffer(1.2).contains(Point(*p)):
            continue
        box(M["TT_blue"], P3(p, zf + 0.35), (0.34, 0.34, 0.35))
        frustum(M["TT_white"], P3(p, zf + 0.7), P3(p, zf + Z_E), 0.24, 0.24, n=12, caps=False)
        n_col += 1
    # railings with planters along the pond sides
    edge = U.buffer(-0.3, join_style=2).exterior.intersection(decks.buffer(-0.05))
    n_rail = 0
    for g in getattr(edge, "geoms", [edge]):
        if g.geom_type != "LineString" or g.length < 1.0:
            continue
        for d in np.arange(0, g.length + 0.01, 1.5):
            p = np.array(g.interpolate(min(d, g.length)).coords[0])
            frustum(M["TT_rail"], P3(p, zf), P3(p, zf + 1.05), 0.025, 0.025, n=4, caps=False)
        cs = list(g.coords)
        for a, b in zip(cs[:-1], cs[1:]):
            bar(M["TT_rail"], (*a, zf + 1.05), (*b, zf + 1.05), 0.035)
            bar(M["TT_rail"], (*a, zf + 0.5), (*b, zf + 0.5), 0.015)
        for d in np.arange(2.0, g.length - 1.0, 5.0):   # white planter boxes on the rail, clipped hedge and flowers on top
            p = np.array(g.interpolate(d).coords[0]); q = np.array(g.interpolate(min(d + 0.1, g.length)).coords[0])
            e = (q - p) / (np.linalg.norm(q - p) or 1); e3 = np.array([*e, 0]); n3 = np.array([-e[1], e[0], 0])
            box(M["TT_white"], P3(p, zf + 1.3), (0.7, 0.25, 0.22), basis=(e3, n3, UP))
            box(M["TT_hedge"], P3(p, zf + 1.6), (0.62, 0.2, 0.09), basis=(e3, n3, UP))
            n_rail += 1
    return n_col, n_rail


def hex_sign(M, c, u, n, zc):
    """Two pale-blue hexagons with dark-blue rims, a dark-blue band with the name, a red diamond under it."""
    u3, n3 = np.array([*u, 0.0]), np.array([*n, 0.0])
    hexa = lambda cx, r: Polygon([(cx + r * math.cos(math.pi * k / 3), r * math.sin(math.pi * k / 3)) for k in range(6)])
    for cx in (-1.05, 1.05):
        plate(M["TT_signb"], hexa(cx, 1.12), P3(c, zc), u3, UP, n3, 0.0, t=0.1)
        plate(M["TT_sign"], hexa(cx, 0.98), P3(c, zc), u3, UP, n3, 0.02)
        plate(M["TT_sign"], hexa(cx, 0.98), P3(c, zc), u3, UP, -n3, 0.12)
    band = Polygon([(-2.75, 0), (-2.45, 0.38), (2.45, 0.38), (2.75, 0), (2.45, -0.38), (-2.45, -0.38)])
    plate(M["TT_signb"], band, P3(c, zc - 0.05), u3, UP, n3, 0.06, t=0.1)
    tp = text_poly("TOMORROWLAND TERRACE", 0.26)
    plate(M["TT_text"], tp, P3(c, zc - 0.05), u3, UP, n3, 0.075)
    plate(M["TT_text"], tp, P3(c, zc - 0.05), -u3, UP, -n3, 0.055)
    dia = Polygon([(0, -0.5), (0.55, 0), (0, 0.5), (-0.55, 0)])
    plate(M["TT_signr"], dia, P3(c, zc - 0.95), u3, UP, n3, 0.0, t=0.08)
    for s in (-1.6, 1.6):   # hangers up to the soffit
        bar(M["TT_steel"], P3(c + u * s, zc + 0.9), P3(c + u * s, zc + 3.0), 0.02)


def pylon(M, p, face, zg):
    """The pylon sign: a white post, a red 'Coca-Cola' box on top, the name on a long red box (orange-lit edges)."""
    f = np.array([face[0], face[1], 0.0]); f /= np.linalg.norm(f); s = np.array([-f[1], f[0], 0.0])
    box(M["TT_white"], P3(p, zg + 3.2), (0.14, 0.14, 3.2), basis=(s, f, UP))
    box(M["TT_signr"], P3(p, zg + 5.3) + s * 0.55, (0.5, 0.16, 0.42), basis=(s, f, UP))
    box(M["TT_signr"], P3(p, zg + 1.9) + s * 1.35, (1.3, 0.16, 0.32), basis=(s, f, UP))
    box(M["TT_light"], P3(p, zg + 3.6) + s * 0.08, (0.06, 0.08, 1.5), basis=(s, f, UP))
    for sg in (1, -1):
        plate(M["TT_text"], text_poly("TOMORROWLAND", 0.16), P3(p, zg + 2.0) + s * 1.35, s * sg, UP, f * sg, 0.17)
        plate(M["TT_text"], text_poly("TERRACE", 0.16), P3(p, zg + 1.74) + s * 1.35, s * sg, UP, f * sg, 0.17)
        plate(M["TT_text"], text_poly("Coca-Cola", 0.14, "georgiab.ttf"), P3(p, zg + 5.3) + s * 0.55, s * sg, UP, f * sg, 0.17)


def entrance_planters(M, L, gr, door_pts):
    """Blue-edged planters (hedge, yellow flowers) and white benches either side of the domed entrance."""
    d = door_pts["se"]
    U = L["U"]
    near = np.array(U.exterior.interpolate(U.exterior.project(Point(*d))).coords[0])
    n = near - d; n /= np.linalg.norm(n)
    e = np.array([-n[1], n[0]])
    out = 0
    for sg in (-1, 1):
        c = near + n * 2.2 + e * sg * 5.2
        z = gr.z(*c)
        pl = rect(c, e, n, 2.2, 0.8)
        slab(M["TT_planter"], M["TT_planter"], pl, z - 0.3, z + 0.45)
        cap(M["TT_hedge"], pl.buffer(-0.12, join_style=2).difference(rect(c + n * 0.35, e, n, 2.0, 0.25)), z + 0.72)
        sides(M["TT_hedge"], pl.buffer(-0.12, join_style=2), z + 0.45, z + 0.72)
        cap(M["TT_flower"], rect(c + n * 0.35, e, n, 2.0, 0.25), z + 0.6)
        b = c + n * 1.6
        box(M["TT_white"], P3(b, z + 0.42), (0.9, 0.22, 0.05), basis=(np.array([*e, 0]), np.array([*n, 0]), UP))
        for s2 in (-0.75, 0.75):
            box(M["TT_white"], P3(b + e * s2, z + 0.2), (0.05, 0.2, 0.2), basis=(np.array([*e, 0]), np.array([*n, 0]), UP))
        out += 1
    return out


# ---------------------------------------------------------------- build
def build():
    L = plan()
    gr = Ground(L["U"].buffer(15).bounds)
    ring = L["U"].buffer(1.5, join_style=2).exterior
    zs = np.array([gr.z(*ring.interpolate(d).coords[0]) for d in np.arange(0, ring.length, 1.5)])
    lo, hi = float(zs.min()), float(zs.max())
    zf, zb = float(np.percentile(zs, 85)), lo - 0.4      # a step of at most ~0.5 m up from the lowest ground (the page's STEP 0.55)
    M = {n: G.Mesh(n) for n in NAMES}
    info = {"floor": round(zf, 2), "ground": (round(lo, 2), round(hi, 2)), "outline m2": round(L["U"].area),
            "inside m2": round(L["inner"].area), "covered m2": round(L["cov"].area)}
    floor(M, L, zf, zb)
    wi, door_pts, all_doors = walls(M, L, zf, zb)
    info["walls"] = wi
    info["doors at"] = {k: tuple(np.round(v, 1)) for k, v in door_pts.items()}
    info["roof"] = roof(M, L, zf)
    stage = rotunda(M, zf)
    dome(M, zf)
    info["menu boards"] = counters(M, L, zf)
    bc = booth(M, L, zf)
    info["tables in/out"] = furniture(M, L, zf, door_pts, all_doors, stage, bc)
    info["columns, planters"] = columns_rails(M, L, zf)
    # the hexagon sign under the parade-side fascia, facing out
    U = L["U"]
    q = np.array(U.exterior.interpolate(U.exterior.project(Point(*PARADE_SIGN))).coords[0])
    q2 = np.array(U.exterior.interpolate(U.exterior.project(Point(*PARADE_SIGN)) + 0.5).coords[0])
    e = (q2 - q) / np.linalg.norm(q2 - q); n = np.array([e[1], -e[0]])
    if U.contains(Point(*(q + 0.3 * n))):
        n = -n
    u = np.array([-n[1], n[0]])                                     # left to right as seen from outside
    hex_sign(M, q - n * 1.0, u, n, zf + Z_E - 1.4)
    pylon(M, np.array(PYLON), (1.0, 0.0), gr.z(*PYLON))
    info["entrance planters"] = entrance_planters(M, L, gr, door_pts)
    return M, info


def main():
    M, info = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, {k: m for k, m in M.items() if m.tris})
    print(f"[tomorrowland terrace] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print("  triangles:", {k: len(m.tris) for k, m in M.items()})


if __name__ == "__main__":
    main()
