"""World Bazaar, video refinement R2 (docs/video_frames/refine_R2.md, 2026-10-04): the street furniture and planting the
v2 daytime walk shows along Center Street's arms, in the east arm's covered way (EXT_E) and outside its east end, and
the Parkside Wagon (the omnibus). Called from ds_tdl_world_bazaar.build_street (in the WB frame); nothing here imports
ds_tdl_world_bazaar (the arms and EXT_E come in as arguments).

Places (WEB): the arms' and EXT_E's centre lines (OSM 72216847 / 1338996034, as in ds_tdl_world_bazaar), the
"パークサイドワゴン" point WB (63.0, -120.2) (amenity=fast_food), the beds 218979567 / 203570864 for the palms; looks
from the video (v2 4:18 .. 7:30, v1 0:11:34 .. 0:11:50). ESTIMATES: all sizes, spacings and the bus's heading.
"""
import math, random

try:
    import bmesh
except ImportError:
    bmesh = None

from ds_tdl_station import bm_box, bm_lathe, obj_bm, T, R, globe_lamp_bm, text, _principled

PSW = (63.0, -120.2, 90.0)                    # the omnibus: OSM point, heading (deg; its nose to +y, v2 7:18)
PALMS = [(64.0, -113.0), (68.0, -117.0), (80.0, -100.0), (58.5, -116.5)]   # R2-29: round the beds 218979567 / 203570864
EXIT_BENCHES = [(62.0, -95.0), (60.0, -100.0), (57.5, -105.0), (63.5, -90.0)]  # R2-21: by the block's east face, facing it


def materials(M):
    M["cobble"] = _principled("st_wbz_cobble", (0.30, 0.21, 0.19), 0.85)[0]     # R2-27 the bus's round of setts
    return M


class Parts(dict):
    def __missing__(self, k):
        self[k] = bmesh.new()
        return self[k]

    def flush(self, name):
        for k, bm_ in self.items():
            if len(bm_.verts):
                obj_bm(f"ST_WBZ_R2_{name}_{k}", bm_, k, smooth=k in ("lamp", "flowers_red", "flowers_pink", "flowers_yellow", "topiary"))
            else:
                bm_.free()


def along(p0, p1, t, off):
    """The point t metres from p0 towards p1, off metres to the left; and the unit direction."""
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    return (p0[0] + ux * t - uy * off, p0[1] + uy * t + ux * off), (ux, uy), L


def lamp_post(P, x, y):
    """The street's green cast-iron lamp post with two arms and red hanging baskets (as build_street's, R1 S7)."""
    bm_lathe(P["hall_iron"], [(0, 0), (0.2, 0), (0.2, 0.3), (0.14, 0.5), (0.09, 0.9), (0.07, 3.5), (0.12, 3.6), (0.06, 3.7), (0, 3.7)], 10, T(x, y, 0.04))
    bm_lathe(P["hall_iron"], [(0, 0), (0.1, 0), (0.22, 0.12), (0.22, 0.62), (0.26, 0.66), (0.08, 0.85), (0, 0.95)], 6, T(x, y, 3.74))
    globe_lamp_bm(P["lamp"], x, y, 4.1, 0.16)
    for d in (-1, 1):
        bm_box(P["hall_iron"], x - 0.03, x + 0.03, y + d * 0.05, y + d * 0.5, 2.68, 2.74)
        bm_lathe(P["hall_iron"], [(0, 0), (0.08, 0.01), (0.17, 0.08), (0.21, 0.2), (0.21, 0.24), (0, 0.24)], 10, T(x, y + d * 0.47, 2.28))
        globe_lamp_bm(P["flowers_red"], x, y + d * 0.47, 2.56, 0.22)


def bench(P, x, y, a):
    """R2-21: a bench with a green slatted seat and back on cast-iron ends; a = the direction it faces (rad)."""
    M_ = T(x, y, 0.0) @ R(a - math.pi / 2, "Z")           # local: x along the bench, -y the side it faces
    for sx in (-0.85, 0.85):
        bm_box_m(P["hall_iron"], M_, sx - 0.04, sx + 0.04, -0.3, 0.3, 0.0, 0.8)
    bm_box_m(P["bench_green"], M_, -0.95, 0.95, -0.28, 0.25, 0.42, 0.47)
    bm_box_m(P["bench_green"], M_, -0.95, 0.95, 0.22, 0.28, 0.5, 0.9)


def bm_box_m(bm, M_, x0, x1, y0, y1, z0, z1):
    vs = bm_box(bm, x0, x1, y0, y1, z0, z1)
    bmesh.ops.transform(bm, matrix=M_, verts=vs)


def trash_can(P, x, y):
    """R2-21: a cream octagonal can with a gold band."""
    bm_lathe(P["t_cream"], [(0, 0), (0.3, 0), (0.3, 0.95), (0.25, 1.0), (0, 1.02)], 8, T(x, y, 0.0))
    bm_lathe(P["gaw_gold"], [(0, 0), (0.31, 0), (0.31, 0.06), (0, 0.06)], 8, T(x, y, 0.7))


def topiary_box(P, x, y):
    """R2-18: a red brick planter with a coping and a three-ball clipped topiary on a short trunk."""
    bm_box(P["brick"], x - 0.5, x + 0.5, y - 0.5, y + 0.5, 0.0, 0.85)
    bm_box(P["t_cream"], x - 0.56, x + 0.56, y - 0.56, y + 0.56, 0.85, 0.92)
    bm_lathe(P["wood"], [(0, 0), (0.05, 0), (0.04, 1.6), (0, 1.6)], 6, T(x, y, 0.9))
    for z, r in ((1.35, 0.45), (1.95, 0.35), (2.45, 0.25)):
        globe_lamp_bm(P["topiary"], x, y, z, r)


def palm(P, x, y, h, rng):
    import ds_tdl_plaza_buildings as PB
    PB.palm(P["palm_trunk"], P["palm_leaf"], x, y, h, rng.uniform(0, 2 * math.pi), rng, kind="canary")   # a spec marker: the page grows a canary palm (v2 6:36 .. 7:18)


def street_extras(ARMS, EXT_E):
    P = Parts(); rng = random.Random(2002)
    # R2-20: lamp posts with baskets along both arms (4.7 m either side of the centre line)
    for p0, p1, _ in ARMS:
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        for t in (7.0, 21.0, min(35.0, L - 2.0)):
            for s in (-1, 1):
                (x, y), _, _ = along(p0, p1, t, s * 4.7)
                lamp_post(P, x, y)
        # R2-21: benches by the shops (facing the street), a can every ~15 m
        for t in (10.0, 16.0, 22.0, 28.0):
            for s in (-1, 1):
                (x, y), (ux, uy), _ = along(p0, p1, t, s * 5.6)
                bench(P, x, y, math.atan2(-s * ux, s * uy))
        for t in (14.0, 30.0):
            (x, y), _, _ = along(p0, p1, t, 5.4)
            trash_can(P, x, y)
    # R2-17 R2-18: EXT_E (the east arm's covered way): hanging baskets in three rows, brick planters with topiaries
    p0, p1, w = EXT_E
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    k = 0; t = 2.5
    while t < L - 2.0:
        for off, zb in ((-1.5, 3.4), (0.0, 2.8), (1.5, 3.4)):
            (x, y), _, _ = along(p0, p1, t, off)
            bm_box(P["hall_iron"], x - 0.006, x + 0.006, y - 0.006, y + 0.006, zb + 0.45, 4.3)
            bm_lathe(P["hall_iron"], [(0, 0), (0.12, 0.02), (0.36, 0.14), (0.45, 0.32), (0.45, 0.4), (0, 0.4)], 10, T(x, y, zb - 0.1))
            globe_lamp_bm(P[("flowers_red", "flowers_pink", "flowers_yellow")[k % 3]], x, y, zb + 0.3, 0.42); k += 1
        t += 2.5
    t = 1.5
    while t < L - 1.0:
        for s in (-1, 1):
            (x, y), _, _ = along(p0, p1, t, s * 1.95)
            topiary_box(P, x, y)
        t += 3.0
    # R2-21 outside the east exit: benches facing the block's east face, cans
    for x, y in EXIT_BENCHES:
        bench(P, x, y, math.pi)
    for x, y in ((61.0, -88.0), (59.0, -108.0)):
        trash_can(P, x, y)
    # R2-29: palms round the beds (the OSM trees there are the mock's trees3d)
    for x, y in PALMS:
        palm(P, x, y, rng.uniform(5.5, 7.0), rng)
    P.flush("street")
    parkside_wagon()


def parkside_wagon():
    """R2-30 (v2 7:12 .. 7:30): the dark green omnibus on its round of setts -- red spoked wheels, the yellow grille,
    brass lamps, red-framed windows, a flat roof with a luggage rack and the "PARKSIDE WAGON" board. Local: x along
    the bus (nose at +x), y across, z up."""
    P = Parts()
    x0, y0, ang = PSW
    a = math.radians(ang)
    M0 = T(x0, y0, 0.0) @ R(a, "Z")

    def box(k, *b):
        bm_box_m(P[k], M0, *b)
    bm_lathe(P["cobble"], [(0, 0), (3.5, 0), (3.5, 0.03), (0, 0.03)], 32, T(x0, y0, 0.0))
    L0, L1 = -3.25, 3.25
    box("bus_green", L0, L1 - 1.2, -1.1, 1.1, 0.75, 2.4)            # the body
    box("bus_green", L1 - 1.2, L1, -0.75, 0.75, 0.75, 1.75)         # the bonnet
    box("bus_green", L0 - 0.05, L1 - 1.15, -1.15, 1.15, 0.7, 0.8)
    box("bus_red", L0 - 0.6 + 0.6, L1 - 1.0, -1.25, 1.25, 2.4, 2.55)   # the roof, over the front
    box("t_cream", L0, L1 - 1.0, -1.27, 1.27, 2.55, 2.6)
    box("m_yellow", L1, L1 + 0.05, -0.35, 0.35, 0.8, 1.7)           # the grille
    for s in (-1, 1):
        globe_lamp_bm(P["brass"], *trans(M0, L1 + 0.05, s * 0.6, 1.55), 0.15)
        for k in range(4):                                         # the windows, red framed
            xa = L0 + 0.3 + k * 1.15
            box("bus_red", xa, xa + 1.0, s * 1.1 - 0.03, s * 1.1 + 0.03, 1.25, 2.3)
            box("win_dark", xa + 0.06, xa + 0.94, s * 1.1 - 0.04, s * 1.1 + 0.04, 1.3, 2.25)
        box("gaw_gold", L0 + 0.2, L1 - 1.3, s * 1.1 - 0.035, s * 1.1 + 0.035, 1.05, 1.08)
        box("bus_green", L1 - 1.8, L1 - 0.4, s * 0.75, s * 1.15, 0.9, 1.0)    # the front mudguards
    for wx, r in ((L1 - 0.9, 0.5), (L0 + 0.9, 0.5)):              # the wheels: red discs with spokes, black tyres
        for s in (-1, 1):
            cx, cy, cz = trans(M0, wx, s * 1.12, r)
            Mw = T(cx, cy, cz) @ R(a, "Z") @ R(math.pi / 2, "X")
            bm_lathe(P["m_black"], [(r - 0.08, -0.06), (r, -0.06), (r, 0.06), (r - 0.08, 0.06)], 20, Mw)
            bm_lathe(P["bus_red"], [(0, -0.07), (0.12, -0.07), (0.12, 0.07), (0, 0.07)], 12, Mw)
            for q in range(12):
                aa = 2 * math.pi * q / 12
                vs = bm_box(P["bus_red"], 0.1, r - 0.06, -0.025, 0.025, -0.03, 0.03)
                bmesh.ops.transform(P["bus_red"], matrix=Mw @ R(aa, "Z"), verts=vs)
    for k in range(3):                                             # the luggage on the roof, the rail
        box("wood", L0 + 0.3 + k * 1.2, L0 + 1.2 + k * 1.2, -0.7, 0.7, 2.6, 2.95)
    box("brass", L0 + 0.1, L1 - 1.1, -1.2, -1.15, 2.6, 2.75); box("brass", L0 + 0.1, L1 - 1.1, 1.15, 1.2, 2.6, 2.75)
    box("wood", L1 - 1.1, L1 - 0.95, -0.8, 0.8, 2.6, 3.0)          # the board on the front of the roof
    cx, cy, cz = trans(M0, L1 - 0.92, 0.0, 2.8)
    text("ST_WBZ_R2_psw_sign", "PARKSIDE WAGON", 0.13, (cx, cy, cz), (math.pi / 2, 0, a + math.pi / 2), "gaw_gold", 0.01)
    box("bus_green", L0 - 0.4, L0, -0.5, 0.5, 0.3, 0.45)            # the step at the back
    P.flush("psw")


def trans(M_, x, y, z):
    from mathutils import Vector
    v = M_ @ Vector((x, y, z))
    return (v.x, v.y, v.z)
