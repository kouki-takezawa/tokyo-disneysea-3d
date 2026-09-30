"""スティッチ・エンカウンター -- Stitch Encounter, the theatre show in Tomorrowland (plain Python, Blender is not needed;
no trees or palms, no round clipped shrubs, no night version):

  python src/ds_tdl_stitch_encounter.py   # -> output/disneysea/models/tdl_stitch_encounter.json + a summary
  python src/export_mock.py               # rebuilds the page ("tdl_stitch_encounter", layer ディズニーランド)

Sources: the user's 7 photos (images/stitch_encounter/1-7.png, not in the repo: the entrance from the north, the sign,
the pre-show corridor inside, the long facade with Space Mountain behind, the corner planter with the oval sign), the
web (tokyodisneyresort.jp / castel.jp: opened 17 July 2015 in the theatre that was Captain EO's, a show of ~12 minutes
for 160 guests who talk with Stitch on a big screen), the Google aerial photo (the drum with its hexagonal cap; the
labels スティッチ・エンカウンター, トレジャーコメット and a restroom on this building) and OSM:
  way 217930859 (unnamed, building=retail; its north-west lobe was modelled as part of the terrace before) with the
  node 12366545400 "スティッチエンカウンター" in the drum; the south-east edge is shared with トゥモローランド・テラス
  (way 217930860, ds_tdl_tomorrowland_terrace.py): a party wall.
The OSM outline is the roof's edge: the walls stand WALL_IN m behind it, and CANOPY m behind it along the north facade
(the photos: a deep white soffit over the glass on slanted white columns).

What is modelled (every height is an ESTIMATE from people in the photos, 1.70 m):
  outside  a white fascia (soffit Z_S, top Z_F) with a pale-blue line, the theatre's drum through the roof with a low
           cone and a hexagonal cap; the north facade (photos): a tall glass wall between dark-blue fins east of the
           entrance, the entrance (glass doors) and a purple wall with lilac arcs and the round bronze seal west of it,
           a lavender band along it all with blue downlights, dark-blue upper walls with rows of alien letters; the sign
           (grey console frame, dark screen with STITCH ENCOUNTER in lime green, two green screens, red robot pods, a
           satellite dish, lilac claws, the sponsor plate) on the band over the doors; slanted white columns under the
           soffit; light-blue planters with hedges and purple flowers; the oval sign on a post in the corner planter and
           the wait-time sign; queue posts and chains; blue-grey paving with pale-blue stripes. The other walls (no
           photos): purple under the band, dark blue over it.
  inside   the pre-show corridor behind the glass (photo 4): blue carpet with dark-red circles, blue walls with gold-
           framed monitors on the drum, queue posts, the Galactic Federation seal and screens over the green-lit theatre
           door; the theatre in the drum: rows of benches for ~160 facing the big screen (Stitch in his ship's window),
           a low stage, a dark ceiling with ring lights; the exit to トレジャーコメット (a shop with shelves, its own door
           on the north-west); the restrooms (west) and backstage (south, behind the screen) are closed blocks.
ESTIMATES: all heights, the plan inside (the doors, the corridor, the theatre's seats and screen, the shop), the walls
  on the south and west (no photos), the letters (made up glyphs, not a real alphabet).
Walk: the floor is one slab at the 85th percentile of the ground round the outline (from the ground models' hole under
  it); the doors are openings in the walls; benches, planters and walls stop the walker.
Frame: the mock's local metres (+x east, +y north), z up; plan (x, y, z) -> glTF (x, z, -y) by ds_tdl_ground.write_gltf.
"""
import sys, math, pathlib

import numpy as np
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
from ds_tdl_plaza_center import tri, frustum, box
from ds_tdl_plaza_hub import Ground, quad, P3, UP
from ds_tdl_tomorrowland_terrace import polys, cap, sides, slab, bar, plate, text_poly, rect

MODELS = ROOT / "output" / "disneysea" / "models"
OUT = MODELS / "tdl_stitch_encounter.json"
WAY, TERRACE = 217930859, 217930860
WALL_IN, CANOPY = 1.6, 5.0                    # walls behind the roof's edge (m); along the north facade
Z_B0, Z_B1, Z_S, Z_F = 3.45, 3.9, 7.0, 8.3    # over the floor: the lavender band, the soffit, the fascia's top
Z_C = Z_S - 0.05                               # the ceiling inside
ROT_C, ROT_R, Z_D = (-537.0, 624.0), 14.0, 9.0  # the theatre's drum (aerial photo) and its ceiling
DOOR_IN, DOOR_OUT = 40.0, 180.0                # the drum's doors (deg): from the corridor, out to the shop
ENT = np.array([-541.0, 650.0])                          # the entrance (the Google map's label; the photos: west of the glass)
SHOP_DOOR = np.array([-578.5, 632.5])                    # トレジャーコメット's door on the north-west face
PYLON = (-513.5, 657.5)                        # the oval sign in the corner planter (photo 7)
NAMES = ("SE_white", "SE_sky", "SE_roof", "SE_navy", "SE_purple", "SE_lilac", "SE_lav", "SE_glass", "SE_paving",
         "SE_stripe", "SE_planter", "SE_hedge", "SE_flower", "SE_frame", "SE_panel", "SE_green", "SE_red", "SE_redlit",
         "SE_bronze", "SE_text", "SE_dark", "SE_blue", "SE_carpet", "SE_dot", "SE_wallin", "SE_ceil", "SE_gold",
         "SE_screen", "SE_stitch", "SE_pink", "SE_bench", "SE_steel", "SE_light", "SE_shelf", "SE_goods", "SE_tfloor", "SE_shopceil", "SE_shopfloor")


def V3(p):
    return np.array([p[0], p[1], 0.0])


def ang_pt(a_deg, r=ROT_R):
    a = math.radians(a_deg)
    return np.array([ROT_C[0] + r * math.cos(a), ROT_C[1] + r * math.sin(a)])


def ellipse(cx, cy, rx, ry, n=28):
    return Polygon([(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)])


def rrect(w, h, r):
    """A rounded rectangle centred on (0, 0)."""
    return sbox(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, 8)


def glyphs(n, h, seed):
    """n made-up 'alien' letters in a row, h m tall, centred on (0, 0): rings, bars and hooks (not a real alphabet)."""
    rng = np.random.default_rng(seed)
    out, x = [], -n * h * 0.42
    for _ in range(n):
        parts, k = [], rng.integers(0, 5)
        c = (x + h * 0.32, 0.0); t = h * 0.12
        if k == 0:
            parts.append(Point(*c).buffer(h * 0.34, 12).difference(Point(*c).buffer(h * 0.34 - t, 12)))
            parts.append(sbox(c[0] - t / 2, -h / 2, c[0] + t / 2, 0))
        elif k == 1:
            parts += [sbox(x, -h / 2, x + t, h / 2), sbox(x, h / 2 - t, x + h * 0.6, h / 2), sbox(x, -t / 2, x + h * 0.45, t / 2)]
        elif k == 2:
            parts.append(Point(*c).buffer(h * 0.3, 12).difference(Point(*c).buffer(h * 0.3 - t, 12)).difference(sbox(c[0], -h, c[0] + h, 0)))
            parts.append(sbox(c[0] - t / 2, -h / 2, c[0] + t / 2, h / 2))
        elif k == 3:
            parts += [LineString([(x, -h / 2), (x + h * 0.32, h / 2), (x + h * 0.64, -h / 2)]).buffer(t / 2, cap_style=2), sbox(x + 0.1 * h, -t / 2, x + 0.54 * h, t / 2)]
        else:
            parts += [sbox(x, h / 2 - t, x + h * 0.6, h / 2), sbox(x + h * 0.24, -h / 2, x + h * 0.36, h / 2), Point(x + h * 0.3, -h * 0.3).buffer(t, 8)]
        out.append(unary_union(parts))
        x += h * 0.84
    return unary_union(out)


# ---------------------------------------------------------------- plan
def plan():
    ways = {w["id"]: w for w in DL.DATA["ways"]}
    pts = ways[WAY]["pts"]
    U = Polygon(pts).buffer(0)
    party = U.boundary.intersection(Polygon(ways[TERRACE]["pts"]).boundary.buffer(0.05))
    north = LineString(pts[37:44] + pts[0:5])
    can = north.buffer(CANOPY, cap_style=2, join_style=2).intersection(U)
    inner = unary_union([U.buffer(-WALL_IN, join_style=2), U.buffer(-0.15, join_style=2).intersection(party.buffer(WALL_IN + 0.2, cap_style=2))]).difference(can)
    inner = max(polys(inner), key=lambda p: p.area)
    drum = Point(*ROT_C).buffer(ROT_R, 64)
    wc = inner.intersection(sbox(-600, 560, -556.0, 622.0))
    boh = inner.intersection(sbox(-556.0, 560, -490, 607.5))
    return dict(U=U, party=party, north=north, can=can, inner=inner, drum=drum,
                wc=max(polys(wc), key=lambda p: p.area), boh=max(polys(boh), key=lambda p: p.area))


# ---------------------------------------------------------------- walls
def ring_ccw(g):
    r = g.exterior
    return r if Polygon(r).exterior.is_ccw else LineString(list(r.coords)[::-1])


def walls(M, L, zf, zb):
    """The outer walls on the inner outline, bay by bay: glass with fins, doors, purple, solid; the band on the north."""
    ring = ring_ccw(L["inner"])
    ent = np.array(ring.interpolate(ring.project(Point(*ENT))).coords[0])
    shop = np.array(ring.interpolate(ring.project(Point(*SHOP_DOOR))).coords[0])
    party, northz = L["party"].buffer(0.5), L["can"].buffer(0.4)
    cs = [np.array(c) for c in ring.coords]
    info = {"bays": 0, "glass": 0, "doors": 0}
    runs = []                                     # north-facade bays (for the band, planters, lights)
    for a, b in zip(cs[:-1], cs[1:]):
        Ln = np.linalg.norm(b - a)
        if Ln < 0.05:
            continue
        e = (b - a) / Ln; n = np.array([e[1], -e[0]]); N3 = V3(n)
        nb = max(1, round(Ln / 2.4))
        for k in range(nb):
            p, q = a + e * Ln * k / nb, a + e * Ln * (k + 1) / nb
            m = (p + q) / 2; info["bays"] += 1
            if party.contains(Point(*m)):
                quad(M["SE_wallin"], P3(p, zf), P3(q, zf), P3(q, zf + Z_C), P3(p, zf + Z_C), -N3)
                quad(M["SE_white"], P3(p, zb), P3(q, zb), P3(q, zf + Z_S), P3(p, zf + Z_S), N3)
                continue
            on_n = northz.contains(Point(*m))
            d_ent = np.dot(m - ent, e)
            kind = ("door" if on_n and abs(d_ent) < 3.3 else "door" if np.linalg.norm(m - shop) < 1.3
                    else "glass" if on_n and m[0] > ent[0] + 2.5 else "purple" if on_n and m[0] > ent[0] - 13.0 else "solid")
            quad(M["SE_white"], P3(p, zb), P3(q, zb), P3(q, zf), P3(p, zf), N3)       # the base
            if kind == "glass":
                info["glass"] += 1
                quad(M["SE_glass"], P3(p, zf), P3(q, zf), P3(q, zf + Z_S), P3(p, zf + Z_S), N3)
                for zz in (zf + 0.05, zf + 2.6, zf + 5.3):
                    bar(M["SE_white"], P3(p, zz) + N3 * 0.03, P3(q, zz) + N3 * 0.03, 0.035)
                box(M["SE_navy"], P3(p + n * 0.35, zf + Z_S / 2), (0.3, 0.2, Z_S / 2), basis=(N3, V3(e), UP))   # a fin
            elif kind == "door":
                info["doors"] += 1
                z0 = zf + 2.6
                quad(M["SE_glass" if on_n else "SE_navy"], P3(p, z0), P3(q, z0), P3(q, zf + (Z_B0 if on_n else Z_S)), P3(p, zf + (Z_B0 if on_n else Z_S)), N3)
                if on_n:
                    quad(M["SE_navy"], P3(p, zf + Z_B1), P3(q, zf + Z_B1), P3(q, zf + Z_S), P3(p, zf + Z_S), N3)
                quad(M["SE_wallin"], P3(p, z0) - N3 * 0.2, P3(q, z0) - N3 * 0.2, P3(q, zf + Z_C) - N3 * 0.2, P3(p, zf + Z_C) - N3 * 0.2, -N3)
                bar(M["SE_steel"], P3(p, zf) + N3 * 0.03, P3(p, z0) + N3 * 0.03, 0.05)
                bar(M["SE_steel"], P3(p, z0) + N3 * 0.03, P3(q, z0) + N3 * 0.03, 0.05)
            else:
                lo = "SE_purple"
                quad(M[lo], P3(p, zf), P3(q, zf), P3(q, zf + Z_B0), P3(p, zf + Z_B0), N3)
                quad(M["SE_lav"], P3(p, zf + Z_B0), P3(q, zf + Z_B0), P3(q, zf + Z_B1), P3(p, zf + Z_B1), N3)
                quad(M["SE_navy"], P3(p, zf + Z_B1), P3(q, zf + Z_B1), P3(q, zf + Z_S), P3(p, zf + Z_S), N3)
                pi, qi = p - n * 0.25, q - n * 0.25
                quad(M["SE_wallin"], P3(pi, zf), P3(qi, zf), P3(qi, zf + Z_C), P3(pi, zf + Z_C), -N3)
                if not on_n and info["bays"] % 4 == 0:   # a dark-blue pilaster now and then on the plain walls
                    box(M["SE_navy"], P3(p + n * 0.12, zf + Z_B0 / 2), (0.12, 0.3, Z_B0 / 2), basis=(N3, V3(e), UP))
            if on_n:
                runs.append((p, q, n, e, kind))
    return info, ent, shop, runs


def band(M, runs, zf):
    """The lavender band along the north facade (1.1 m deep), with blue downlights under it."""
    for p, q, n, e, kind in runs:
        d = 1.6 if kind == "door" else 1.1
        c = (p + q) / 2 + n * d / 2
        box(M["SE_lav"], P3(c, zf + (Z_B0 + Z_B1) / 2), (d / 2, np.linalg.norm(q - p) / 2 + 0.01, (Z_B1 - Z_B0) / 2), basis=(V3(n), V3(e), UP))
        frustum(M["SE_light"], P3(c, zf + Z_B0 - 0.03), P3(c, zf + Z_B0 + 0.01), 0.1, 0.1, n=8)


# ---------------------------------------------------------------- roof, soffit, floor
def roof(M, L, zf):
    U, inner = L["U"], L["inner"]
    hole = Point(*ROT_C).buffer(ROT_R + 0.3, 64)
    sides(M["SE_white"], U, zf + Z_S, zf + Z_F)
    sides(M["SE_sky"], U.buffer(0.03, join_style=2), zf + Z_S, zf + Z_S + 0.22)
    cap(M["SE_roof"], U.difference(hole), zf + Z_F)
    cap(M["SE_white"], U.difference(inner), zf + Z_S, down=True)
    cap(M["SE_ceil"], inner.difference(L["drum"]), zf + Z_C, down=True)
    # the drum over the roof, a low cone and the hexagonal cap
    cx, cy = ROT_C; n = 64; r2 = 2.4
    Pp = lambda r, a, z: np.array([cx + r * math.cos(a), cy + r * math.sin(a), z])
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        nr = np.array([math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0])
        quad(M["SE_white"], Pp(ROT_R + 0.3, a0, zf + Z_F), Pp(ROT_R + 0.3, a1, zf + Z_F), Pp(ROT_R + 0.3, a1, zf + 10.6), Pp(ROT_R + 0.3, a0, zf + 10.6), nr)
        quad(M["SE_sky"], Pp(ROT_R + 0.33, a0, zf + 10.1), Pp(ROT_R + 0.33, a1, zf + 10.1), Pp(ROT_R + 0.33, a1, zf + 10.3), Pp(ROT_R + 0.33, a0, zf + 10.3), nr)
        quad(M["SE_roof"], Pp(ROT_R + 0.6, a0, zf + 10.6), Pp(ROT_R + 0.6, a1, zf + 10.6), Pp(r2, a1, zf + 11.8), Pp(r2, a0, zf + 11.8), UP + nr * 0.1)
    hexa = Polygon([(cx + 3.0 * math.cos(math.pi * k / 3), cy + 3.0 * math.sin(math.pi * k / 3)) for k in range(6)])
    slab(M["SE_roof"], M["SE_white"], hexa, zf + 11.6, zf + 12.5)
    return dict(roof_m2=round(U.difference(hole).area))


def floor(M, L, zf, zb):
    inner, U = L["inner"], L["U"]
    rooms = inner.difference(L["drum"]).difference(L["wc"]).difference(L["boh"])
    cap(M["SE_carpet"], rooms, zf)
    cap(M["SE_tfloor"], L["drum"], zf)
    cap(M["SE_paving"], U.difference(inner), zf)
    sides(M["SE_white"], U, zb, zf)
    # dark-red circles on the corridor's carpet (photo 4)
    n = 0
    for x in np.arange(-534.0, -512.0, 5.5):
        for y in (642.5, 645.0):
            c = Point(x + (2.5 if y > 643 else 0), y).buffer(1.1 if n % 2 else 0.8, 20)
            if rooms.buffer(-0.3).contains(c) and not L["drum"].buffer(0.5).intersects(c):
                cap(M["SE_dot"], c, zf + 0.01); n += 1
    # pale-blue stripes in the paving under the canopy (the photos)
    can = L["can"].difference(inner)
    north = L["north"]
    for off in (1.4, 3.6):
        ln = north.parallel_offset(off, "right", join_style=2)
        st = ln.buffer(0.18, cap_style=2).intersection(can.buffer(-0.2))
        cap(M["SE_stripe"], st, zf + 0.01)
    return n


# ---------------------------------------------------------------- the drum: theatre
def drum(M, zf):
    cx, cy = ROT_C; n = 72
    opens = [(DOOR_IN, 2.0), (DOOR_OUT, 2.4)]
    def is_open(a_deg):
        return any(abs((a_deg - d + 180) % 360 - 180) < w / ROT_R * 180 / math.pi for d, w in opens)
    for k in range(n):
        a0, a1 = 360.0 * k / n, 360.0 * (k + 1) / n
        p, q = ang_pt(a0), ang_pt(a1)
        nr = V3(ang_pt((a0 + a1) / 2) - np.array(ROT_C)) / ROT_R
        z0 = zf + (2.7 if is_open((a0 + a1) / 2) else 0.0)
        po, qo = p + nr[:2] * 0.2, q + nr[:2] * 0.2
        quad(M["SE_wallin"], P3(po, z0), P3(qo, z0), P3(qo, zf + Z_C), P3(po, zf + Z_C), nr)        # the corridor side
        quad(M["SE_dark"], P3(p, z0), P3(q, z0), P3(q, zf + Z_D), P3(p, zf + Z_D), -nr)              # the theatre side
    cap(M["SE_ceil"], Point(*ROT_C).buffer(ROT_R, 64), zf + Z_D, down=True)
    for r in (5.0, 9.5):                                                                             # ring lights
        ring = Point(*ROT_C).buffer(r + 0.15, 48).difference(Point(*ROT_C).buffer(r - 0.15, 48))
        cap(M["SE_light"], ring, zf + Z_D - 0.05, down=True)
    # the green-lit frame of the door from the corridor, the seal and screens over it (photo 4)
    for d, w in opens:
        a = ang_pt(d, ROT_R + 0.22); t = np.array([-math.sin(math.radians(d)), math.cos(math.radians(d))])
        nr = V3(a - np.array(ROT_C)) / (ROT_R + 0.22)
        for s in (-1, 1):
            bar(M["SE_green"], P3(a + t * s * w, zf), P3(a + t * s * w, zf + 2.7), 0.06)
        bar(M["SE_green"], P3(a - t * w, zf + 2.7), P3(a + t * w, zf + 2.7), 0.06)
    a = ang_pt(DOOR_IN, ROT_R + 0.25); nr = V3(a - np.array(ROT_C)) / (ROT_R + 0.25); t3 = np.array([-nr[1], nr[0], 0])
    seal(M, P3(a, zf + 4.4), t3, nr, 1.1)
    for s in (-1, 1):
        plate(M["SE_screen"], rrect(1.6, 1.0, 0.25), P3(a, zf + 4.5) + t3 * s * 2.4, t3, UP, nr, 0.03, t=0.05, edge=M["SE_lav"])
    # gold-framed monitors on the corridor side (photo 4)
    mons = 0
    for d in np.arange(58.0, 131.0, 12.0):
        a = ang_pt(d, ROT_R + 0.22); nr = V3(a - np.array(ROT_C)) / (ROT_R + 0.22); t3 = np.array([-nr[1], nr[0], 0])
        plate(M["SE_gold"], rrect(0.95, 1.3, 0.12), P3(a, zf + 1.8), t3, UP, nr, 0.02, t=0.08)
        plate(M["SE_screen"], rrect(0.75, 1.05, 0.06), P3(a, zf + 1.8), t3, UP, nr, 0.03)
        mons += 1
    return mons


def seal(M, c, t3, n3, r):
    """The round Galactic Federation seal: a bronze disc, a raised ring, an inner boss and a star of small discs."""
    plate(M["SE_bronze"], Point(0, 0).buffer(r, 32), c, t3, UP, n3, 0.02, t=0.12)
    plate(M["SE_frame"], Point(0, 0).buffer(r * 0.93, 32).difference(Point(0, 0).buffer(r * 0.82, 32)), c, t3, UP, n3, 0.05)
    plate(M["SE_frame"], Point(0, 0).buffer(r * 0.32, 20), c, t3, UP, n3, 0.06)
    for k in range(8):
        a = 2 * math.pi * k / 8
        plate(M["SE_frame"], Point(r * 0.58 * math.cos(a), r * 0.58 * math.sin(a)).buffer(r * 0.08, 10), c, t3, UP, n3, 0.06)


def theatre(M, zf):
    """The big screen on the south (Stitch in his ship's window), a low stage, rows of benches facing it."""
    y_s = ROT_C[1] - 10.4                                     # the screen's plane (a chord of the drum)
    hw = math.sqrt(ROT_R ** 2 - 10.4 ** 2) - 0.3
    sc = np.array([ROT_C[0], y_s])
    X3, N3 = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
    box(M["SE_dark"], P3(sc, zf + 4.5), (hw, 0.1, 4.5))        # the wall behind it
    plate(M["SE_frame"], rrect(10.6, 5.4, 0.6), P3(sc, zf + 4.2), X3, UP, N3, 0.12, t=0.1)
    plate(M["SE_screen"], rrect(10.0, 4.9, 0.5), P3(sc, zf + 4.2), X3, UP, N3, 0.14)
    # Stitch in the window: a blue head, big ears (pink inside), dark eyes and nose -- flat shapes on the screen
    s = lambda g, mat, off: plate(M[mat], g, P3(sc, zf + 3.9), X3, UP, N3, off)
    s(ellipse(0, 0, 1.45, 1.1), "SE_stitch", 0.16)
    for sg in (-1, 1):
        ear = Polygon([(sg * 0.9, 0.55), (sg * 3.1, 1.5), (sg * 2.9, 0.95), (sg * 1.2, 0.05)])
        s(ear, "SE_stitch", 0.155)
        s(Polygon([(sg * 1.2, 0.5), (sg * 2.7, 1.2), (sg * 2.6, 0.95), (sg * 1.3, 0.2)]), "SE_pink", 0.165)
        s(ellipse(sg * 0.62, 0.25, 0.42, 0.34), "SE_dark", 0.17)
        s(ellipse(sg * 0.5, 0.35, 0.1, 0.09), "SE_text", 0.175)
    s(ellipse(0, -0.25, 0.32, 0.2), "SE_dark", 0.17)
    s(ellipse(0, -0.75, 0.75, 0.12), "SE_dark", 0.17)
    s(ellipse(0, -2.3, 1.7, 0.9), "SE_stitch", 0.155)                 # shoulders
    # a low stage in front
    stage = Point(*ROT_C).buffer(ROT_R - 0.1, 64).intersection(sbox(-600, y_s, -400, y_s + 1.6))
    slab(M["SE_purple"], M["SE_lav"], stage, zf - 0.1, zf + 0.5)
    # benches: arcs round a point behind the screen, a middle aisle, clear of the two doors
    F = np.array([ROT_C[0], y_s - 4.0])
    room = Point(*ROT_C).buffer(ROT_R - 1.4, 64).difference(Point(*ang_pt(DOOR_IN)).buffer(3.4)).difference(Point(*ang_pt(DOOR_OUT)).buffer(3.6))
    seats = 0
    for r in np.arange(8.6, 14.5, 1.2):
        L_arc = r * math.radians(120)
        for k in range(int(L_arc / 0.55)):
            a = math.radians(30) + k * 0.55 / r
            p = F + r * np.array([math.cos(a), math.sin(a)])
            if abs(p[0] - F[0]) < 0.8 or abs(p[0] - F[0]) > 11.0 or not room.contains(Point(*p).buffer(0.3)) or p[1] < y_s + 2.4:
                continue
            u = np.array([-math.sin(a), math.cos(a), 0]); f = -np.array([math.cos(a), math.sin(a), 0])
            box(M["SE_bench"], P3(p, zf + 0.42), (0.26, 0.24, 0.05), basis=(u, f, UP))
            box(M["SE_bench"], P3(p, zf + 0.7) - f * 0.22, (0.26, 0.03, 0.3), basis=(u, f, UP))
            box(M["SE_dark"], P3(p, zf + 0.19), (0.24, 0.2, 0.19), basis=(u, f, UP))
            seats += 1
    return seats


# ---------------------------------------------------------------- inside: blocks, partition, queue, shop
def rooms(M, L, zf, ent):
    for g in (L["wc"], L["boh"]):
        g2 = g.difference(L["drum"].buffer(0.25))
        for p in polys(g2, 1.0):
            sides(M["SE_wallin"], p, zf, zf + Z_C)
            cap(M["SE_ceil"], p, zf + Z_C - 0.01)
    # the partition between the corridor and the shop side (from the drum at 150 deg to the north wall)
    a = ang_pt(150, ROT_R + 0.2)
    ln = LineString([a, a + np.array([-0.6, 30.0])]).intersection(L["inner"])
    g = max(getattr(ln, "geoms", [ln]), key=lambda g: g.length)
    w = g.buffer(0.12, cap_style=2)
    slab(M["SE_wallin"], M["SE_wallin"], w, zf, zf + Z_C)
    # the queue: posts and chains in the corridor, the entrance to the theatre door
    ent_in = ent + np.array([0.0, -2.0])
    n = 0
    for y in (645.6, 643.4, 641.2):
        xs = np.arange(-533.5, -518.0, 1.9) if y != 643.4 else np.arange(-531.6, -514.5, 1.9)
        for x0, x1 in zip(xs[:-1], xs[1:]):
            for x in (x0,):
                frustum(M["SE_steel"], (x, y, zf), (x, y, zf + 0.95), 0.03, 0.03, n=6, caps=False); n += 1
            bar(M["SE_steel"], (x0, y, zf + 0.9), (x1, y, zf + 0.9), 0.015)
    # トレジャーコメット: shelves of goods along the shop's walls and two tables in the middle
    shop = L["inner"].intersection(sbox(-600, 622.3, a[0] - 0.4, 700)).difference(L["drum"].buffer(0.3))
    shop = max(polys(shop), key=lambda p: p.area)
    ring = shop.buffer(-0.6, join_style=2).exterior
    k = 0
    for d in np.arange(1.0, ring.length - 1.0, 1.6):
        p = np.array(ring.interpolate(d).coords[0]); q = np.array(ring.interpolate(d + 0.2).coords[0])
        e = (q - p) / (np.linalg.norm(q - p) or 1)
        if np.linalg.norm(p - SHOP_DOOR) < 3.0 or np.linalg.norm(p - ang_pt(DOOR_OUT)) < 3.5 or p[1] < 625.5:
            continue
        box(M["SE_shelf"], P3(p, zf + 0.9), (0.7, 0.25, 0.9), basis=(V3(e), np.array([-e[1], e[0], 0]), UP))
        for zz in (0.5, 1.0, 1.5):
            box(M["SE_goods"], P3(p, zf + zz + 0.12), (0.62, 0.2, 0.1), basis=(V3(e), np.array([-e[1], e[0], 0]), UP))
        k += 1
    # display tables in rows, clear of the way from the theatre's exit to the shop's door
    way = LineString([ang_pt(DOOR_OUT, ROT_R + 1.0), ang_pt(DOOR_OUT, ROT_R + 1.0) + np.array([-2.0, 6.0]), SHOP_DOOR]).buffer(2.2)
    free = shop.buffer(-2.4).difference(way)
    for x in np.arange(-582.0, -550.0, 3.6):
        for y in np.arange(624.0, 650.0, 3.2):
            if free.contains(Point(x, y).buffer(1.0)):
                box(M["SE_shelf"], (x, y, zf + 0.42), (0.9, 0.5, 0.42))
                box(M["SE_goods"], (x, y, zf + 0.92), (0.8, 0.4, 0.08))
                k += 1
    cap(M["SE_shopceil"], shop, zf + Z_C - 0.02, down=True)   # a white ceiling in the shop (under the dark one)
    cap(M["SE_shopfloor"], shop, zf + 0.005)
    return n, k


# ---------------------------------------------------------------- outside: the sign, the seal wall, columns, planters
def main_sign(M, c, u, n):
    """The sign on the band over the doors: a grey console frame with a dark screen and the name in lime green, green
    screens top and bottom, red robot pods either side, a dish on top, lilac claws, the sponsor plate under it."""
    u3, n3 = V3(u), V3(n)
    plate(M["SE_frame"], rrect(4.6, 1.75, 0.55), c, u3, UP, n3, 0.0, t=0.35)
    plate(M["SE_panel"], rrect(3.9, 1.2, 0.35), c, u3, UP, n3, 0.02)
    plate(M["SE_green"], text_poly("STITCH", 0.36, "comicbd.ttf"), c + UP * 0.25 - u3 * 0.3, u3, UP, n3, 0.035)
    plate(M["SE_green"], text_poly("ENCOUNTER", 0.36, "comicbd.ttf"), c - UP * 0.25 + u3 * 0.15, u3, UP, n3, 0.035)
    for dz in (1.05, -1.05):                                   # the small screens top and bottom, in grey housings
        plate(M["SE_frame"], rrect(1.2, 0.62, 0.2), c + UP * dz, u3, UP, n3, -0.05, t=0.3)
        plate(M["SE_green"], rrect(0.9, 0.4, 0.12), c + UP * dz, u3, UP, n3, -0.03)
    for s in (-1, 1):                                          # the red pods on short arms
        pc = c + u3 * s * 2.55 + UP * (0.55 if s < 0 else 0.35) + n3 * 0.1
        bar(M["SE_frame"], c + u3 * s * 2.2, pc, 0.07)
        frustum(M["SE_red"], pc - n3 * 0.25, pc + n3 * 0.25, 0.38, 0.38, n=12)
        frustum(M["SE_redlit"], pc + n3 * 0.25, pc + n3 * 0.3, 0.2, 0.2, n=10)
        frustum(M["SE_frame"], pc + UP * 0.35, pc + UP * 0.75, 0.03, 0.03, n=4)
        frustum(M["SE_redlit"], pc + UP * 0.75, pc + UP * 0.85, 0.07, 0.07, n=6)
        for k in (-1, 1):                                      # lilac claws at the bottom corners
            base = c + u3 * s * (1.6 + 0.25 * k) - UP * 0.85
            bar(M["SE_lav"], base, base - UP * 0.45 + n3 * 0.15, 0.09)
    dish = c + u3 * 0.9 + UP * 1.4
    bar(M["SE_frame"], dish - UP * 0.4, dish + UP * 0.4, 0.05)
    frustum(M["SE_frame"], dish + UP * 0.4, dish + UP * 0.6 + n3 * 0.15, 0.08, 0.55, n=14)
    plate(M["SE_text"], rrect(1.5, 0.28, 0.06), c - UP * 1.5, u3, UP, n3, 0.0, t=0.08)
    plate(M["SE_red"], text_poly("Daiwa House", 0.13), c - UP * 1.5, u3, UP, n3, 0.01)


def north_decor(M, L, gr, zf, ent, runs):
    """The purple wall west of the doors (arcs, the seal), alien letters on the dark-blue wall, columns, planters,
    the queue outside, the wait-time sign and the oval sign on its post."""
    # the facade's frame near the entrance: e along the wall (west->east is -e for a CCW ring on the north side)
    p, q, n, e, _ = min(runs, key=lambda r: np.linalg.norm((r[0] + r[1]) / 2 - ent))
    u = e                                                      # left to right as seen from outside (looking south)
    out = {}
    main_sign(M, P3(ent + n * 0.9, zf + Z_B1 + 1.2), u, n)
    purple = [r for r in runs if r[4] == "purple"]
    if purple:
        c = np.mean([(r[0] + r[1]) / 2 for r in purple], 0)
        # a wall face 2 cm out, the lilac arcs and the seal
        pw = c + n * 0.03
        for rr in (2.6, 3.4):
            arc = Point(0, 0).buffer(rr, 40).difference(Point(0, 0).buffer(rr - 0.35, 40)).intersection(sbox(-9, -3.5, 9, 9))
            plate(M["SE_lilac"], arc, P3(pw, zf + 1.6), V3(u), UP, V3(n), 0.0)
        seal(M, P3(c + n * 0.05, zf + 1.8), V3(u), V3(n), 1.1)
        out["seal at"] = tuple(np.round(c, 1))
    # alien letters in two rows on the dark-blue wall over the band, west of the doors
    for k, (dz, cnt) in enumerate(((5.6, 14), (4.9, 18))):
        c = ent - u * 8.5 + n * 0.03
        plate(M["SE_lilac"], glyphs(cnt, 0.45 if k == 0 else 0.3, 7 + k), P3(c, zf + dz), V3(u), UP, V3(n), 0.0)
    # slanted white columns under the soffit's edge (thin at the foot, wide at the top, leaning out)
    ring = L["U"].buffer(-0.7, join_style=2).exterior
    cols = 0
    for d in np.arange(0.0, ring.length, 10.5):
        tp = np.array(ring.interpolate(d).coords[0])
        if not L["can"].buffer(-0.5).contains(Point(*tp)) or np.linalg.norm(tp - ent) < 5.0:
            continue
        near = np.array(L["inner"].exterior.interpolate(L["inner"].exterior.project(Point(*tp))).coords[0])
        foot = tp + (near - tp) * 0.35
        z = gr.z(*foot)
        frustum(M["SE_white"], P3(foot, min(z, zf) - 0.2), P3(tp, zf + Z_S), 0.2, 0.42, n=10)
        cols += 1
    out["columns"] = cols
    # planters along the glass (light-blue edges, hedge, purple flowers)
    pl = 0
    for p, q, n2, e2, kind in runs:
        if kind != "glass":
            continue
        c = (p + q) / 2 + n2 * 1.6
        g = rect(c, e2, n2, np.linalg.norm(q - p) / 2 + 0.02, 0.55)
        slab(M["SE_planter"], M["SE_planter"], g, zf - 0.2, zf + 0.45)
        cap(M["SE_hedge"], g.buffer(-0.1, join_style=2), zf + 0.75)
        sides(M["SE_hedge"], g.buffer(-0.1, join_style=2), zf + 0.45, zf + 0.75)
        pl += 1
    # the corner planter with purple flowers and the oval sign on its post (photo 7)
    zc = gr.z(*PYLON)
    cp = Polygon([(PYLON[0] - 4.5, PYLON[1] - 1.2), (PYLON[0] + 1.5, PYLON[1] - 1.2), (PYLON[0] + 1.5, PYLON[1] + 1.2), (PYLON[0] - 4.5, PYLON[1] + 1.2)])
    slab(M["SE_planter"], M["SE_planter"], cp, zc - 0.3, zc + 0.5)
    cap(M["SE_flower"], cp.buffer(-0.15, join_style=2).intersection(sbox(-999, PYLON[1], 999, 999)), zc + 0.62)
    cap(M["SE_hedge"], cp.buffer(-0.15, join_style=2).intersection(sbox(-999, -999, 999, PYLON[1])), zc + 0.8)
    sides(M["SE_hedge"], cp.buffer(-0.15, join_style=2), zc + 0.5, zc + 0.62)
    oval_sign(M, np.array(PYLON), np.array([0.0, 1.0]), zc + 0.5, 2.4, "Stitch Encounter")
    # the wait-time sign and the queue posts in front of the doors (photo 2)
    ws = ent + n * 3.4 - u * 2.6
    oval_sign(M, ws, n, gr.z(*ws), 1.2, "Wait Time")
    for s in np.arange(-2.4, 2.41, 1.2):
        for t in (2.3, 3.4):
            pp = ent + n * t + u * s
            frustum(M["SE_steel"], P3(pp, zf), P3(pp, zf + 0.95), 0.03, 0.03, n=6, caps=False)
            if s < 2.3:
                bar(M["SE_steel"], P3(pp, zf + 0.85), P3(pp + u * 1.2, zf + 0.85), 0.012)
    out["planters"] = pl
    return out


def oval_sign(M, p, face, z, h, text):
    """An oval sign on a white post (lavender face in a white rim, dark letters), facing `face`."""
    f = V3(face) / np.linalg.norm(face); s = np.array([-f[1], f[0], 0.0])
    frustum(M["SE_white"], P3(p, z), P3(p, z + h), 0.07, 0.07, n=8)
    c = P3(p, z + h + 0.55)
    plate(M["SE_white"], ellipse(0, 0, 0.95, 0.6), c, s, UP, f, 0.05, t=0.12)
    for sg in (1, -1):
        plate(M["SE_lav"], ellipse(0, 0, 0.85, 0.5), c, s * sg, UP, f * sg, 0.075 if sg > 0 else 0.075)
        plate(M["SE_dark"], text_poly(text, 0.13, "comicbd.ttf"), c, s * sg, UP, f * sg, 0.085)


def shop_sign(M, shop, L, zf):
    ring = L["U"].exterior
    q = np.array(ring.interpolate(ring.project(Point(*shop))).coords[0])
    n = q - shop; n /= np.linalg.norm(n); u = np.array([-n[1], n[0]])
    if np.cross(np.append(n, 0), np.append(u, 0))[2] > 0:
        u = -u
    plate(M["SE_text"], text_poly("TREASURE COMET", 0.34), P3(shop + n * 0.04, zf + 4.6), V3(u), UP, V3(n))


# ---------------------------------------------------------------- build
def build():
    L = plan()
    gr = Ground(L["U"].buffer(15).bounds)
    ring = L["U"].buffer(1.5, join_style=2).exterior
    zs = np.array([gr.z(*ring.interpolate(d).coords[0]) for d in np.arange(0, ring.length, 1.5)])
    lo, hi = float(zs.min()), float(zs.max())
    door_z = min(gr.z(*p) for p in (ENT + np.array([0.0, 6.0]), SHOP_DOOR + np.array([-2.0, 2.5])))
    zf, zb = min(float(np.percentile(zs, 85)), door_z + 0.48), lo - 0.4   # a step of at most ~0.5 m at the doors (the page's STEP 0.55)
    M = {n: G.Mesh(n) for n in NAMES}
    info = {"floor": round(zf, 2), "ground": (round(lo, 2), round(hi, 2)), "outline m2": round(L["U"].area),
            "inside m2": round(L["inner"].area)}
    info["carpet circles"] = floor(M, L, zf, zb)
    wi, ent, shop, runs = walls(M, L, zf, zb)
    info["walls"] = wi
    info["entrance, shop door"] = (tuple(np.round(ent, 1)), tuple(np.round(shop, 1)))
    band(M, runs, zf)
    info.update(roof(M, L, zf))
    info["monitors"] = drum(M, zf)
    info["seats"] = theatre(M, zf)
    info["queue posts, shelves"] = rooms(M, L, zf, ent)
    info.update(north_decor(M, L, gr, zf, ent, runs))
    shop_sign(M, shop, L, zf)
    return M, info


def main():
    M, info = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, {k: m for k, m in M.items() if m.tris})
    print(f"[stitch encounter] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print("  triangles:", {k: len(m.tris) for k, m in M.items()})


if __name__ == "__main__":
    main()
