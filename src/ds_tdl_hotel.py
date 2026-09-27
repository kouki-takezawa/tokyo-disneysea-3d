"""東京ディズニーランドホテル -- the crescent hotel building, its motor court and the New Grand Wing / back wings (Blender 5.2).

  blender -b --python src/ds_tdl_hotel.py -- --cams court,court_close,crescent,gates,aerial --samples 32
  blender -b --python src/ds_tdl_hotel.py -- --cams none      # build + save the .blend only
  then open output/disneyland/hotel/tdl_hotel.blend (cameras CAM_*)

Sources (looked at only; nothing copied into the repository):
  * OSM: the building footprint (way 218553057, building=retail + tourism=hotel, height 60, 701 rooms, 5 stars). It is one
    polygon for the whole complex: a curved 21-bay crescent (about 101 m along the curve) facing a motor court, a large
    rectangular block off one end (the New Grand Wing, 2016), and a lower star-shaped spine of connecting wings behind
    and to the other side. The porte-cochere loop (way 659558365) sits in the court in front of the crescent.
  * Wikimedia Commons "Tokyo Disney Land Hotel" (2022, CC BY-SA 2.0, 20 photos) and "Tokyo DisneyLand Hotel.jpg": the
    motor court seen from the gates (the whole crescent, cream and gold, blue-grey mansard roofs, domed corner turrets,
    a taller central pavilion with a small dome, iron gates on round brick piers with a bronze monogram medallion), the
    court close up (round brick planters with the same medallion topped by Mickey-shaped topiary, spiral hedge topiary,
    a rose-pattern brick pavement, balustraded steps), the entrance pavilion head-on (a tall arched window/doorway,
    columns, a clock, a "TOKYO DISNEYLAND HOTEL" bronze plaque on the pier).
  * "Tokyo Disneyland 005.jpg": a wing's facade close up (paired arched windows, a cast-iron Juliet balcony each floor).

Frame: local metres, +x along the crescent (left to right facing it from the court), +y from the wall towards the court
(the porte-cochere side), z up. Origin: the arc-length midpoint of the crescent, so the OSM points below are already in
this frame (no P0 offset, unlike the entrance / World Bazaar scripts -- the hotel is a separate building, not on their frame).

ESTIMATES (no photo has a person to scale against; from typical grand-hotel proportions and window counts in the photos):
ground floor 5.0 m, 5 upper floors at 3.2 m (cornice 22.5 m), mansard to 27 m, corner turrets to 30 m, the entrance
pavilion's dome to 34 m; the New Grand Wing (OSM's 60 m belongs here: it reads much taller than the crescent in the
photos where the two appear together) is a plain 58 m block with a simpler version of the same cladding; the rest of the
footprint (the star-shaped spine and the wing to the west) is treated as a plain 24 m block, the same height as the
crescent, since neither is in any photo. Bay count (20), the motor court's paving pattern and the gates' size are
estimates too.
"""
import sys, math, argparse, pathlib, time

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix
except ImportError:
    bpy = bmesh = Vector = Matrix = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_tdl_station as ST
from ds_tdl_station import (B, box, prism, bm_box, bm_prism, bm_lathe, obj_bm, array_mod, bend, T, R, seg_arc,
                            arch_opening, arch_band, ring_sector, cutter, curve_obj, scroll_pts, column_bm,
                            globe_lamp_bm, text, bevel_mod, _principled, _mottle)
from ds_tdl_entrance import frame, text_mesh, baluster_run

OUT = ROOT / "output" / "disneyland" / "hotel"

# the crescent's OSM points 0..21, simplified (shapely, tolerance 1 m) to drop kinks under a metre: the wall is built as
# a straight facaded bay per segment (a frame per segment, no bend -- a few of these corners turn close to 90 deg over
# 2 m, which the Curve modifier cannot bend the mansard/balustrade through without tearing), already in the hotel's
# local frame (see the docstring)
CRESCENT = [(-32.55, 15.0), (-36.09, 9.7), (-27.27, 1.87), (-22.5, 2.34), (-19.26, -0.43), (-11.08, -0.24),
            (-11.21, 1.87), (5.74, -0.0), (5.93, 1.82), (26.19, 0.34), (27.41, 2.01), (31.8, 2.19),
            (34.49, -0.29), (35.24, -5.04), (30.47, -8.6)]
# the rest of the footprint (New Grand Wing + the star-shaped spine + the west wing), simplified from the same OSM way
BACK = [(30.5, -8.6), (35.2, -102.7), (-13.4, -103.7), (-21.5, -40.8), (-40.0, -25.3), (-74.3, -58.0),
        (-99.2, -38.5), (-71.7, -8.4), (-96.9, 19.8), (-120.1, 6.4), (-125.7, -11.2), (-153.3, 10.8),
        (-123.1, 37.4), (-158.4, 75.6), (-154.8, 112.7), (-133.1, 113.2), (-131.5, 83.1), (-108.4, 62.5),
        (-73.7, 64.3), (-85.4, 73.4), (-79.7, 79.4), (-33.9, 36.1), (-32.6, 15.0)]
NGW = BACK[0:4]                                       # the New Grand Wing's own corner, the tall block (58 m)
GF, FH, NFLOORS = 5.0, 3.2, 7                          # ground floor, upper-floor height, upper floors on the crescent
CORNICE = GF + FH * NFLOORS                            # 27.4
EAVE, RIDGE = CORNICE + 1.5, CORNICE + 5.5             # 28.9, 32.9 (crescent's mansard)
MANSARD_D, DECK_D = 1.6, 0.5                           # the mansard's slope depth, then a short flat deck behind it
TOWER_FLOORS, TOWER_R = 11, 6.2                        # the two corner towers: 11 floors, 12.4 m across the octagon
DOME_TOP = 46.0
BACK_H, NGW_H = 30.0, 58.0


def hotel_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    mat, nt, b = _principled("st_hotel_cream", (0.93, 0.80, 0.50), 0.55); _mottle(nt, b, (0.93, 0.80, 0.50), 7, 0.94, 0.03); M["h_cream"] = mat
    mat, nt, b = _principled("st_hotel_gold", (0.94, 0.89, 0.76), 0.45); _mottle(nt, b, (0.94, 0.89, 0.76), 7, 0.95, 0.02); M["h_gold_trim"] = mat
    M["h_slate"] = P("st_hotel_slate", (0.32, 0.44, 0.62), 0.45, Metallic=0.15)
    M["h_white"] = P("st_hotel_white", (0.95, 0.94, 0.90), 0.5)
    M["h_stone"] = P("st_hotel_stone", (0.86, 0.82, 0.74), 0.75)
    M["h_blue"] = P("st_hotel_blue", (0.28, 0.42, 0.68), 0.55)
    M["h_purple"] = P("st_hotel_purple", (0.42, 0.20, 0.45), 0.55)
    M["h_pink"] = P("st_hotel_pink", (0.90, 0.78, 0.82), 0.6)
    M["h_gold"] = P("st_hotel_gilt", (0.85, 0.66, 0.30), 0.3, Metallic=0.85)
    M["h_bronze"] = P("st_hotel_bronze", (0.42, 0.28, 0.14), 0.35, Metallic=0.8)
    M["h_iron"] = P("st_hotel_iron", (0.08, 0.10, 0.10), 0.4, Metallic=0.55)
    M["h_glass"] = ST.clear_glass("st_hotel_glass", (0.55, 0.62, 0.55), 0.3)
    M["h_win_dark"] = P("st_hotel_win", (0.06, 0.08, 0.10), 0.15, Coat_Weight=1.0)
    M["h_brick"] = ST.mat_brick("st_hotel_brick")
    M["h_paving1"] = ST.mat_tiles("st_hotel_paving1", (0.72, 0.42, 0.38), (0.68, 0.39, 0.35), 0.45, (0.55, 0.45, 0.40))
    M["h_paving2"] = ST.mat_tiles("st_hotel_paving2", (0.62, 0.60, 0.56), (0.58, 0.56, 0.52), 0.45, (0.48, 0.46, 0.42))
    mat, nt, b = _principled("st_hotel_leaf", (0.14, 0.32, 0.13), 0.9); _mottle(nt, b, (0.14, 0.32, 0.13), 35.0, 0.6, 0.4); M["h_leaf"] = mat
    M["h_flower_purple"] = P("st_hotel_flpurple", (0.30, 0.10, 0.45), 0.9)
    M["h_lamp"] = P("st_hotel_lamp", (1.0, 0.93, 0.78), 0.3, Emission_Color=(1.0, 0.85, 0.55, 1), Emission_Strength=3.5)
    M["h_letters"] = P("st_hotel_letters", (0.95, 0.72, 0.12), 0.3, Metallic=0.6)
    M["h_clockface"] = P("st_hotel_clock", (0.95, 0.93, 0.85), 0.35)
    return M


# ================================================================ helpers
def poly_curve(name, pts, loc=(0.0, 0.0, 0.0)):
    """A flat poly curve through 2D points (lying in world XY, height handled by the bent mesh's own Z)."""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.twist_mode = "Z_UP"
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    o = bpy.data.objects.new(name, cu); B.col.objects.link(o); o.parent = B.root
    o.location = loc; o.hide_render = True
    length = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
    return o, length


def paired_window(bm_frame, bm_glass, bm_rail, x, w, z0, z1, balcony=False):
    """Two round-arched lights sharing a surround (width w, sill z0, arch top z1); an iron Juliet balcony if balcony."""
    lw = w / 2 - 0.22
    bm_prism(bm_frame, arch_opening(x - w / 2, x + w / 2, z0 - 0.12, z1 - 0.1 - w * 0.15, w * 0.15, 14), -0.02, 0.1, "xz")
    for dx in (-1, 1):
        xl = x + dx * (w / 4 - 0.02)
        bm_prism(bm_glass, arch_opening(xl - lw / 2, xl + lw / 2, z0, z1 - lw / 2, lw / 2, 10), 0.1, 0.13, "xz")
    bm_box(bm_frame, x - 0.03, x + 0.03, -0.02, 0.14, z0, z1 - lw / 2)
    if balcony:                                            # a shallow balcony: slab on brackets, a white balustrade
        bm_box(bm_frame, x - w / 2 - 0.1, x + w / 2 + 0.1, 0.0, 0.75, z0 - 0.2, z0 - 0.06)
        for dx in (-1, 1):
            bm_box(bm_frame, x + dx * (w / 2 - 0.05) - 0.07, x + dx * (w / 2 - 0.05) + 0.07, 0.0, 0.6, z0 - 0.5, z0 - 0.2)
        bm_box(bm_rail, x - w / 2 - 0.05, x + w / 2 + 0.05, 0.62, 0.75, z0 + 0.8, z0 + 0.9)
        bm_box(bm_rail, x - w / 2 - 0.05, x + w / 2 + 0.05, 0.62, 0.75, z0 - 0.06, z0)
        for k in range(int((w + 0.1) / 0.17)):
            xx = x - w / 2 + 0.03 + k * 0.17
            bm_box(bm_rail, xx - 0.03, xx + 0.03, 0.65, 0.72, z0, z0 + 0.8)
        for dx in (-1, 1):
            bm_box(bm_rail, x + dx * (w / 2 + 0.05) - 0.05, x + dx * (w / 2 + 0.05) + 0.05, 0.0, 0.75, z0 - 0.06, z0 + 0.9)


def dormer(bm_wall, bm_glass, bm_trim, x, w=1.4):
    """A round-headed dormer standing on the mansard's slope (part way up it), with its own little gabled roof."""
    y0, y1 = 0.4, 0.85
    z0 = EAVE + (RIDGE - EAVE) * (y0 / MANSARD_D)         # the slope's own height at this depth: the dormer sits flush on it
    h = 1.9
    bm_box(bm_wall, x - w / 2, x + w / 2, y0, y1, z0, z0 + h)
    bm_prism(bm_trim, arch_opening(x - w / 2 - 0.1, x + w / 2 + 0.1, z0 - 0.05, z0 + h - w / 2, w / 2 + 0.1, 12), y0 - 0.02, y0 + 0.03, "xz")
    bm_prism(bm_glass, arch_opening(x - w / 2 + 0.15, x + w / 2 - 0.15, z0 + 0.15, z0 + h - w / 2, w / 2 - 0.15, 10), y1 - 0.03, y1, "xz")
    bm_prism(bm_wall, [(x - w / 2 - 0.28, z0 + h), (x + w / 2 + 0.28, z0 + h), (x, z0 + h + 0.9)], y0 - 0.18, y1 + 0.18, "xz")


def sconce(bm_iron, bm_lamp, x, y, z):
    """A small wrought-iron wall lamp bracket, out from the wall (y) to a globe."""
    bm_lathe(bm_iron, [(0, 0), (0.045, 0), (0.045, 0.05), (0, 0.05)], 8, T(x, y, z - 0.03))
    bm_box(bm_iron, x - 0.02, x + 0.02, y, y + 0.24, z - 0.02, z + 0.02)
    bm_box(bm_iron, x - 0.02, x + 0.02, y + 0.22, y + 0.26, z - 0.02, z + 0.2)
    globe_lamp_bm(bm_lamp, x, y + 0.24, z + 0.24, 0.1)


# ================================================================ 1. the crescent (Array + Curve, as the entrance's gates)
def crescent_bay(w, N):
    """One bay of the crescent (local x 0..w along the curve, y towards the court, z up), Array N times + bend."""
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "iron", "slate", "gold", "lamp", "leaf", "rail")}
    m = w / 2
    bm_box(P["trim"], 0.15, w - 0.15, 0.9, 1.3, 0.0, 0.35)                # a low kerb along the foot of the wall
    bm_lathe(P["leaf"], [(0, -0.28), (0.32, 0), (0, 0.28)], 10, T(m, 1.35, 0.4) @ R(math.pi / 2, "X"))   # a clipped hedge ball
    bm_box(P["wall"], 0, w, -0.02, 0, 0, CORNICE)                        # the wall face itself (bent along the curve)
    bm_box(P["trim"], 0.05, 0.35, 0.0, 0.18, 0, CORNICE)                  # quoins at each bay edge
    bm_box(P["trim"], w - 0.35, w - 0.05, 0.0, 0.18, 0, CORNICE)
    for k in range(1, int(CORNICE / 1.0)):                                # rustication: horizontal joint lines, ground floor
        if k * 1.0 < GF - 0.6:
            bm_box(P["trim"], 0.35, w - 0.35, 0.0, 0.05, k * 1.0, k * 1.0 + 0.04)
    bm_prism(P["trim"], arch_opening(m - 1.15, m + 1.15, GF - 4.35, GF - 0.55, 0.85, 14), 0.0, 0.15, "xz")   # ground floor
    bm_prism(P["glass"], arch_opening(m - 0.95, m + 0.95, GF - 4.15, GF - 0.7, 0.68, 12), 0.15, 0.18, "xz")
    bm_prism(P["trim"], arch_band(m - 1.15, m + 1.15, GF - 0.55, 0.85, 0.18, 14, leg=0.15), 0.14, 0.3, "xz")   # arch moulding + keystone
    bm_box(P["trim"], m - 0.12, m + 0.12, 0.14, 0.32, GF + 0.15, GF + 0.5)
    sconce(P["iron"], P["lamp"], m - 1.7, 0.16, GF - 2.4); sconce(P["iron"], P["lamp"], m + 1.7, 0.16, GF - 2.4)
    bm_box(P["trim"], m - 1.3, m + 1.3, 0.0, 0.2, GF - 0.55, GF - 0.2)    # string course under the upper floors
    for f in range(NFLOORS):
        z0 = GF + FH * f + 0.55
        paired_window(P["trim"], P["glass"], P["rail"], m, 2.0, z0, z0 + 1.85, balcony=True)
        bm_box(P["trim"], m - 1.15, m + 1.15, 0.0, 0.14, GF + FH * (f + 1) - 0.12, GF + FH * (f + 1) + 0.05)
    bm_box(P["trim"], -0.05, w + 0.05, -0.1, 0.28, CORNICE - 0.4, CORNICE - 0.25)   # a plain dentil cornice band
    for k in range(int(w / 0.5)):
        xx = k * 0.5 + 0.25
        bm_box(P["trim"], xx - 0.1, xx + 0.1, 0.0, 0.22, CORNICE - 0.25, CORNICE - 0.1)
    baluster_run(P["trim"], P["rail"], (0.0, 0.32), (w, 0.32), CORNICE, EAVE)   # a turned-baluster balustrade at the roofline
    # the mansard: an open sloped face (no end caps, so Array copies never share a coincident face) then a short flat
    # deck; gold cresting along the visible ridge line where the slope meets the deck
    V = lambda x, y, z: P["slate"].verts.new((x, y, z))
    a0, b0 = V(0, 0.0, EAVE), V(w, 0.0, EAVE)
    a1, b1 = V(0, MANSARD_D, RIDGE), V(w, MANSARD_D, RIDGE)
    P["slate"].faces.new((a0, b0, b1, a1))
    a2, b2 = V(0, MANSARD_D + DECK_D, RIDGE), V(w, MANSARD_D + DECK_D, RIDGE)
    P["slate"].faces.new((a1, b1, b2, a2))
    bm_lathe(P["gold"], [(0, 0), (0.025, 0), (0.02, 0.16), (0.05, 0.2), (0, 0.28)], 6, T(m, MANSARD_D, RIDGE))
    obj = {}
    for k, bm in P.items():
        mat = {"wall": "h_cream", "trim": "h_gold_trim", "glass": "h_win_dark", "iron": "h_iron",
               "slate": "h_slate", "gold": "h_gold", "lamp": "h_lamp", "leaf": "h_leaf", "rail": "h_white"}[k]
        o = obj_bm(f"HT_crescent_{k}", bm, mat, smooth=(k in ("gold", "lamp", "leaf")), recalc=(k != "slate"))
        array_mod(o, N, (w, 0, 0))
        obj[k] = o
    return obj


def crescent_dormers(w, N):
    """Round dormers on every other bay, sitting on the mansard's slope."""
    bm_wall, bm_glass, bm_trim = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(N):
        if k % 2 == 0:
            dormer(bm_wall, bm_glass, bm_trim, k * w + w / 2)
    o1 = obj_bm("HT_crescent_dormer_wall", bm_wall, "h_cream")
    o2 = obj_bm("HT_crescent_dormer_glass", bm_glass, "h_win_dark")
    o3 = obj_bm("HT_crescent_dormer_trim", bm_trim, "h_gold_trim")
    return [o1, o2, o3]


def obox(bm, cx, cy, ang, w, d, z0, z1):
    """A box of w (along ang) x d (across) x z0..z1, centred on (cx, cy) and turned by ang (radians)."""
    bmesh.ops.create_cube(bm, size=1.0, matrix=T(cx, cy, (z0 + z1) / 2) @ R(ang, "Z") @ Matrix.Diagonal((w, d, z1 - z0, 1.0)))


def corner_tower(cx, cy, name):
    """One of the two tall corner towers (photos): an octagon 12.4 m across, 11 floors of paired windows with a white
    balcony on every face, a bracketed cornice, an octagonal crown (a balustraded terrace and arched lights), and a
    steep blue slate spire with a gold finial."""
    r, H = TOWER_R, GF + FH * (TOWER_FLOORS - 1)
    bm_w, bm_t, bm_g, bm_r, bm_s, bm_gd, bm_l = (bmesh.new() for _ in range(7))
    ring = lambda rr, n=8, rot=math.pi / 8: [(cx + rr * math.cos(rot + 2 * math.pi * k / n), cy + rr * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]
    bm_prism(bm_w, ring(r), -0.5, H, "xy")
    bm_prism(bm_t, ring(r + 0.25), H - 0.1, H + 0.6, "xy")                       # cornice
    bm_prism(bm_t, ring(r + 0.35), H + 0.6, H + 0.8, "xy")
    ri = r * math.cos(math.pi / 8)                        # the face's distance from the centre
    fw = 2 * r * math.sin(math.pi / 8)                    # the face's width
    for k in range(8):
        a = 2 * math.pi * k / 8                            # face normal
        ux, uy = math.cos(a), math.sin(a)
        fx, fy = cx + ux * ri, cy + uy * ri
        for f in range(TOWER_FLOORS):
            z0 = (0.9 if f == 0 else GF + FH * (f - 1) + 0.55)
            h = 3.4 if f == 0 else 1.85
            obox(bm_t, fx, fy, a + math.pi / 2, 2.0, 0.24, z0 - 0.12, z0 + h + 0.12)     # window surround
            obox(bm_g, fx + ux * 0.1, fy + uy * 0.1, a + math.pi / 2, 1.7, 0.08, z0, z0 + h)
            obox(bm_t, fx + ux * 0.14, fy + uy * 0.14, a + math.pi / 2, 0.06, 0.06, z0, z0 + h)
            if f >= 1:                                     # a small balcony with a white balustrade
                obox(bm_t, fx + ux * 0.4, fy + uy * 0.4, a + math.pi / 2, 2.4, 0.8, z0 - 0.2, z0 - 0.06)
                obox(bm_r, fx + ux * 0.74, fy + uy * 0.74, a + math.pi / 2, 2.4, 0.12, z0 - 0.06, z0 + 0.9)
            if f >= 1:
                obox(bm_t, fx + ux * 0.05, fy + uy * 0.05, a + math.pi / 2, fw, 0.18, GF + FH * f - 0.1, GF + FH * f + 0.05)
        for q in (-1, 1):                                  # quoins on the corners of the octagon
            pa = a + q * math.pi / 8
            obox(bm_t, cx + r * math.cos(pa), cy + r * math.sin(pa), pa + math.pi / 2, 0.45, 0.45, 0, H)
    # the crown: a smaller octagonal drum with arched lights, a balustraded terrace round it
    rc, zc = r * 0.72, H + 0.8
    bm_prism(bm_w, ring(rc), zc, zc + 4.2, "xy")
    for k in range(8):
        a = 2 * math.pi * k / 8
        ux, uy = math.cos(a), math.sin(a)
        rci = rc * math.cos(math.pi / 8)
        obox(bm_g, cx + ux * (rci + 0.02), cy + uy * (rci + 0.02), a + math.pi / 2, 1.3, 0.06, zc + 0.7, zc + 3.2)
        obox(bm_t, cx + ux * (rci + 0.05), cy + uy * (rci + 0.05), a + math.pi / 2, 1.7, 0.12, zc + 3.2, zc + 3.5)
        # the terrace balustrade along the outer face
        pa0, pa1 = a - math.pi / 8, a + math.pi / 8
        rr = r - 0.1
        x0_, y0_ = cx + rr * math.cos(pa0), cy + rr * math.sin(pa0)
        x1_, y1_ = cx + rr * math.cos(pa1), cy + rr * math.sin(pa1)
        L = math.hypot(x1_ - x0_, y1_ - y0_); nb = int(L / 0.24)
        for b in range(nb):
            t = (b + 0.5) / nb
            bm_lathe(bm_r, [(0, 0), (0.07, 0), (0.04, 0.2), (0.08, 0.5), (0.04, 0.8), (0.06, 0.86), (0, 0.86)], 6, T(x0_ + (x1_ - x0_) * t, y0_ + (y1_ - y0_) * t, zc))
        obox(bm_r, (x0_ + x1_) / 2, (y0_ + y1_) / 2, a + math.pi / 2, L + 0.2, 0.22, zc + 0.86, zc + 1.0)
        bm_lathe(bm_r, [(0, 0), (0.18, 0), (0.18, 1.1), (0.24, 1.2), (0, 1.25)], 8, T(x0_, y0_, zc))   # posts
    bm_prism(bm_t, ring(rc + 0.3), zc + 4.2, zc + 4.6, "xy")
    # the spire: an octagonal pyramid, flared at the foot, lucarnes on alternate faces, the finial
    zs = zc + 4.6
    prof = [(rc + 0.3, 0), (rc * 0.8, 1.2), (rc * 0.55, 4.0), (rc * 0.3, 7.0), (0.25, 9.5), (0.0, 10.0)]
    bm_lathe(bm_s, prof, 8, T(cx, cy, zs) @ R(math.pi / 8, "Z"))
    for k in range(0, 8, 2):
        a = 2 * math.pi * k / 8
        ux, uy = math.cos(a), math.sin(a)
        obox(bm_w, cx + ux * rc * 0.72, cy + uy * rc * 0.72, a + math.pi / 2, 1.0, 1.2, zs + 0.6, zs + 2.2)
        obox(bm_g, cx + ux * (rc * 0.72 + 0.6), cy + uy * (rc * 0.72 + 0.6), a + math.pi / 2, 0.6, 0.05, zs + 0.9, zs + 1.9)
    bm_lathe(bm_gd, [(0, 0), (0.12, 0), (0.08, 0.6), (0.2, 0.75), (0.08, 0.9), (0.04, 2.2), (0, 2.3)], 8, T(cx, cy, zs + 9.8))
    for k in range(0, 8, 2):                                  # coach lamps by the tower's foot
        a = 2 * math.pi * k / 8 + math.pi / 8 * 0
        globe_lamp_bm(bm_l, cx + math.cos(a) * (ri + 0.35), cy + math.sin(a) * (ri + 0.35), 3.2, 0.13)
    for bm_, mat, sm in ((bm_w, "h_cream", False), (bm_t, "h_gold_trim", False), (bm_g, "h_win_dark", False), (bm_r, "h_white", False),
                         (bm_s, "h_slate", False), (bm_gd, "h_gold", True), (bm_l, "h_lamp", True)):
        obj_bm(f"HT_tower_{name}_{mat}", bm_, mat, smooth=sm)


def themed_wing(name, p0, p1, wall, trim, floors=4):
    """The lower Victorian wings in the court's front corners (photos: one blue with white trim, one purple with a
    pink ground): bays of oriel windows, arched ground-floor windows, fretwork brackets, a steep slate roof with a
    front gable over every other bay and finials. Built from p0 to p1 with its front on local +y."""
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    gf, fh = 4.4, 3.0; H = gf + fh * (floors - 1); D = 11.0
    with frame(f"HT_wing_{name}", p0[0], p0[1], ang):
        bm_w, bm_t, bm_g, bm_s, bm_gd, bm_l = (bmesh.new() for _ in range(6))
        bm_box(bm_w, 0, L, -D, 0, -0.5, H)
        nb = max(2, round(L / 4.2)); bw = L / nb
        for k in range(nb):
            x0, x1 = k * bw, (k + 1) * bw; m = (x0 + x1) / 2
            bm_box(bm_t, x0, x0 + 0.3, 0, 0.15, 0, H)                              # pilasters
            bm_prism(bm_t, arch_opening(m - 1.2, m + 1.2, 0.0, gf - 1.4, 0.9, 12), 0.0, 0.12, "xz")
            bm_prism(bm_g, arch_opening(m - 1.0, m + 1.0, 0.15, gf - 1.5, 0.75, 10), 0.12, 0.15, "xz")
            for fx in (m - 1.25, m + 1.25):                 # fretwork brackets under the first floor
                bm_prism(bm_t, [(fx - 0.1, gf - 0.6), (fx + 0.1, gf - 0.6), (fx + 0.1, gf), (fx - 0.1, gf)], 0.0, 0.5, "xz")
            if k % 2 == 0:                                  # an oriel (bay window) over the upper floors
                bay = [(m - 1.4, 0.0), (m + 1.4, 0.0), (m + 0.9, 0.8), (m - 0.9, 0.8)]
                bm_prism(bm_w, bay, gf, H - 0.4, "xy")
                bm_prism(bm_t, [(m - 1.5, 0.0), (m + 1.5, 0.0), (m + 0.95, 0.9), (m - 0.95, 0.9)], gf - 0.2, gf, "xy")
                for f in range(floors - 1):
                    z0 = gf + fh * f + 0.6
                    bm_box(bm_g, m - 0.7, m + 0.7, 0.8, 0.82, z0, z0 + 1.7)
                    bm_box(bm_t, m - 0.75, m + 0.75, 0.8, 0.86, z0 + 1.7, z0 + 1.85)
            else:
                for f in range(floors - 1):
                    z0 = gf + fh * f + 0.6
                    for dx in (-0.65, 0.65):
                        bm_box(bm_t, m + dx - 0.45, m + dx + 0.45, 0.0, 0.1, z0 - 0.1, z0 + 1.9)
                        bm_box(bm_g, m + dx - 0.35, m + dx + 0.35, 0.1, 0.12, z0, z0 + 1.8)
            for f in range(floors - 1):                     # string courses (the half-timber bands on the purple one)
                bm_box(bm_t, x0, x1, 0.0, 0.12, gf + fh * f - 0.08, gf + fh * f + 0.06)
        bm_box(bm_t, -0.1, L + 0.1, 0.0, 0.5, H - 0.4, H)                          # cornice
        # the roof: two slopes to a ridge along the wing; a front gable over every other bay, finials on them
        zr = H + 5.0
        V = lambda x, y, z: bm_s.verts.new((x, y, z))
        a, b_, c, d = V(-0.3, 0.6, H), V(L + 0.3, 0.6, H), V(L + 0.3, -D / 2, zr), V(-0.3, -D / 2, zr)
        bm_s.faces.new((a, b_, c, d))
        e, f_ = V(L + 0.3, -D - 0.6, H), V(-0.3, -D - 0.6, H)
        bm_s.faces.new((d, c, e, f_))
        for k in range(0, nb, 2):
            m = (k + 0.5) * bw
            bm_prism(bm_w, [(m - 1.6, H), (m + 1.6, H), (m, H + 3.2)], -1.5, 0.2, "xz")
            bm_prism(bm_t, [(m - 1.8, H - 0.1), (m, H + 3.45), (m, H + 3.65), (m - 1.95, H + 0.1)], -1.6, 0.3, "xz")
            bm_prism(bm_t, [(m + 1.8, H - 0.1), (m + 1.95, H + 0.1), (m, H + 3.65), (m, H + 3.45)], -1.6, 0.3, "xz")
            bm_lathe(bm_g, [(0, 0), (0.4, 0), (0.4, 0.04), (0, 0.04)], 16, T(m, 0.22, H + 1.2) @ R(-math.pi / 2, "X"))
            bm_lathe(bm_gd, [(0, 0), (0.08, 0), (0.05, 0.5), (0.1, 0.6), (0, 1.0)], 8, T(m, 0.0, H + 3.6))
        for k in range(nb):
            globe_lamp_bm(bm_l, (k + 0.5) * bw - 1.5, 0.35, 2.6, 0.11)
        for bm_, mat, sm in ((bm_w, wall, False), (bm_t, trim, False), (bm_g, "h_win_dark", False), (bm_s, "h_slate", False),
                             (bm_gd, "h_gold", True), (bm_l, "h_lamp", True)):
            obj_bm(f"HT_wing_{name}_{mat}", bm_, mat, smooth=sm)


def entrance_pavilion(x, ang_deg):
    """The main block at the head of the court (photos): 26 m wide, projecting 3 m, three tall arched windows over the
    entrance (the middle one the tallest, with a fan of glazing bars), paired pilasters, balconied floors above, a
    balustraded attic, and the gold dome on an octagonal drum with a lantern. Faces +y at x on the curve."""
    with frame("HT_pavilion", x, 0.0, ang_deg):
        hw, d = 13.0, 3.0
        top = CORNICE + 2.4
        bmw, bmt, bmg, bmr, bmgd, bml, bms = (bmesh.new() for _ in range(7))
        bm_box(bmw, -hw, hw, -2.0, d, -0.5, top)
        for k in range(1, int(GF)):                        # rusticated ground floor
            bm_box(bmt, -hw + 0.4, hw - 0.4, d - 0.02, d + 0.02, k * 1.0, k * 1.0 + 0.04)
        # the three great arches (floors 1-3), their glazing and fans
        for cxa, wa, za in ((0.0, 5.6, 16.0), (-7.0, 3.8, 13.2), (7.0, 3.8, 13.2)):
            ra = wa / 2
            bm_prism(bmt, arch_opening(cxa - ra - 0.35, cxa + ra + 0.35, GF - 0.2, za - ra, ra + 0.35, 24), d, d + 0.14, "xz")
            bm_prism(bmg, arch_opening(cxa - ra, cxa + ra, GF, za - ra, ra, 24), d + 0.14, d + 0.17, "xz")
            for k in range(1, 5):                            # vertical glazing bars
                xx = cxa - ra + wa * k / 5
                bm_box(bmr, xx - 0.03, xx + 0.03, d + 0.17, d + 0.2, GF, za - ra + math.sqrt(max(ra * ra - (xx - cxa) ** 2, 0)) - 0.05)
            for zz in (GF + 2.6, GF + 5.4, za - ra):         # transoms
                bm_box(bmr, cxa - ra, cxa + ra, d + 0.17, d + 0.2, zz - 0.03, zz + 0.03)
            for k in range(1, 6):                            # the fan in the arch head
                t = math.pi * k / 6
                ex, ez = cxa + ra * math.cos(t), za - ra + ra * math.sin(t)
                px_, pz_ = cxa, za - ra
                bm_prism(bmr, [(px_ - 0.03, pz_), (px_ + 0.03, pz_), (ex + 0.03, ez), (ex - 0.03, ez)], d + 0.17, d + 0.2, "xz")
            bm_box(bmt, cxa - 0.3, cxa + 0.3, d, d + 0.3, za - 0.1, za + 0.8)              # keystone
        for px_ in (-9.9, -8.9, -4.2, -3.2, 3.2, 4.2, 8.9, 9.9):   # paired pilasters with capitals
            bm_box(bmt, px_ - 0.25, px_ + 0.25, d, d + 0.25, GF, CORNICE)
            bm_box(bmt, px_ - 0.35, px_ + 0.35, d, d + 0.35, CORNICE - 0.8, CORNICE - 0.5)
        for f in range(4, NFLOORS):                          # string courses on the floors above the arches
            bm_box(bmt, -hw, hw, d, d + 0.14, GF + FH * f - 0.1, GF + FH * f + 0.05)
        with frame("HT_pavilion_face", 0.0, d, 0.0):        # (paired_window works on y = 0: build them on the face)
            fw_t, fw_g, fw_r = bmesh.new(), bmesh.new(), bmesh.new()
            for f in range(4, NFLOORS):
                z0 = GF + FH * f + 0.55
                for xw in (-10.8, -7.0, -2.2, 2.2, 7.0, 10.8):
                    paired_window(fw_t, fw_g, fw_r, xw, 2.0, z0, z0 + 1.85, balcony=True)
            obj_bm("HT_pav_face_trim", fw_t, "h_gold_trim"); obj_bm("HT_pav_face_glass", fw_g, "h_win_dark")
            obj_bm("HT_pav_face_rail", fw_r, "h_white")
        # the doors under the middle arch, a lamp either side
        for s_ in (-1, 1):
            bm_box(bmg, s_ * 0.05, s_ * 1.4, d + 0.17, d + 0.22, 0.0, 3.6)
            sconce(bmt, bml, s_ * 3.4, d + 0.25, 3.0)
        text("HT_pav_plaque", "TOKYO DISNEYLAND HOTEL", 0.3, (0, d + 0.25, GF - 0.5), (math.pi / 2, 0, 0), "h_bronze", 0.015)
        # cornice, attic with small arched lights, balustrade with urns
        bm_box(bmt, -hw - 0.2, hw + 0.2, -2.0, d + 0.5, CORNICE - 0.3, CORNICE + 0.1)
        for xw in (-10.5, -6.3, -2.1, 2.1, 6.3, 10.5):
            bm_prism(bmt, arch_opening(xw - 0.8, xw + 0.8, CORNICE + 0.4, CORNICE + 1.4, 0.8, 12), d - 0.02, d + 0.1, "xz")
            bm_prism(bmg, arch_opening(xw - 0.6, xw + 0.6, CORNICE + 0.5, CORNICE + 1.4, 0.6, 10), d + 0.1, d + 0.12, "xz")
        baluster_run(bmt, bmr, (-hw, d - 0.2), (hw, d - 0.2), top, top + 1.1)
        for xu in (-hw, -4.2, 4.2, hw):
            bm_box(bmt, xu - 0.3, xu + 0.3, d - 0.5, d + 0.1, top, top + 1.3)
            bm_lathe(bmgd, [(0, 0), (0.18, 0), (0.1, 0.15), (0.26, 0.45), (0.2, 0.7), (0.06, 0.8), (0.08, 1.0), (0, 1.05)], 10, T(xu, d - 0.2, top + 1.3))
        bm_box(bms, -hw + 0.3, hw - 0.3, -2.0, d - 0.6, top - 0.2, top)                 # roof deck
        # the gold dome: octagonal drum with round windows, the dome, a lantern, the finial
        dz0, R_ = top, 4.4
        ring = [(R_ * math.cos(math.pi / 8 + 2 * math.pi * k / 8), 0.5 + R_ * math.sin(math.pi / 8 + 2 * math.pi * k / 8)) for k in range(8)]
        bm_prism(bmw, ring, dz0, dz0 + 3.6, "xy")
        bm_prism(bmt, [(x_ * 1.08, 0.5 + (y_ - 0.5) * 1.08) for x_, y_ in ring], dz0 + 3.6, dz0 + 4.0, "xy")
        for k in range(8):
            a = 2 * math.pi * k / 8
            ri = R_ * math.cos(math.pi / 8)
            bm_lathe(bmt, [(0.45, 0), (0.62, 0), (0.62, 0.1), (0.45, 0.1)], 16, T(ri * math.cos(a), 0.5 + ri * math.sin(a), dz0 + 1.9) @ R(a, "Z") @ R(math.pi / 2, "Y"))
            bm_lathe(bmg, [(0, 0), (0.46, 0), (0.46, 0.03), (0, 0.03)], 16, T((ri + 0.01) * math.cos(a), 0.5 + (ri + 0.01) * math.sin(a), dz0 + 1.9) @ R(a, "Z") @ R(math.pi / 2, "Y"))
        prof = [(R_ * 1.02, 0)] + [(R_ * 1.02 * math.cos(math.pi / 2 * i_ / 10) ** 0.9, 4.6 * math.sin(math.pi / 2 * i_ / 10)) for i_ in range(1, 10)] + [(0.9, 4.6)]
        bm_lathe(bmgd, prof, 32, T(0, 0.5, dz0 + 4.0))
        lz = dz0 + 8.6
        for k in range(6):                                   # the lantern: columns, a cap
            a = 2 * math.pi * k / 6
            bm_box(bmr, 0.8 * math.cos(a) - 0.07, 0.8 * math.cos(a) + 0.07, 0.5 + 0.8 * math.sin(a) - 0.07, 0.5 + 0.8 * math.sin(a) + 0.07, lz, lz + 1.6)
        bm_lathe(bmgd, [(0, 0), (1.05, 0), (1.05, 0.2), (0.6, 0.7), (0.1, 1.1), (0.1, 1.6), (0.25, 1.75), (0.05, 2.1), (0, 2.4)], 16, T(0, 0.5, lz + 1.6))
        for bm_, nm, mat, sm in ((bmw, "wall", "h_cream", False), (bmt, "trim", "h_gold_trim", False), (bmg, "glass", "h_win_dark", False),
                                 (bmr, "rail", "h_white", False), (bmgd, "gold", "h_gold", True), (bml, "lamps", "h_lamp", True),
                                 (bms, "roof", "h_slate", False)):
            obj_bm(f"HT_pav_{nm}", bm_, mat, smooth=sm)
        box("HT_pav_floor", (-hw + 0.3, hw - 0.3, 0.0, d - 0.05, -0.05, 0.0), "h_paving1")
        gazebo(0.0, d + 6.5)


def gazebo(cx, cy):
    """The little porte-cochere in front of the doors (photos): an octagon of eight white columns on a stone base,
    an entablature, a scalloped blue dome and a gold finial; a lantern hangs in the middle."""
    bmb, bmc, bmt, bmd, bmg, bml = (bmesh.new() for _ in range(6))
    r = 3.3
    ring = lambda rr: [(cx + rr * math.cos(math.pi / 8 + 2 * math.pi * k / 8), cy + rr * math.sin(math.pi / 8 + 2 * math.pi * k / 8)) for k in range(8)]
    bm_prism(bmb, ring(r + 0.3), 0.0, 0.35, "xy")
    for k in range(8):
        a = math.pi / 8 + 2 * math.pi * k / 8
        column_bm(bmc, cx + r * math.cos(a), cy + r * math.sin(a), 0.35, 4.0, 0.2, 12)
    bm_prism(bmt, ring(r + 0.4), 4.35, 4.95, "xy")
    bm_prism(bmt, ring(r + 0.55), 4.95, 5.15, "xy")
    prof = [(r + 0.5, 0), (r + 0.5, 0.25), (r * 0.95, 0.9), (r * 0.8, 1.7), (r * 0.55, 2.4), (r * 0.3, 2.9), (0.3, 3.3), (0.3, 3.6), (0, 3.7)]
    bm_lathe(bmd, prof, 16, T(cx, cy, 5.15))
    for k in range(16):                                      # the scallops round the dome's foot
        a = 2 * math.pi * (k + 0.5) / 16
        bm_lathe(bmd, [(0, -0.3), (0.3, 0), (0, 0.3)], 8, T(cx + (r + 0.45) * math.cos(a), cy + (r + 0.45) * math.sin(a), 5.25))
    bm_lathe(bmg, [(0, 0), (0.12, 0), (0.09, 0.5), (0.2, 0.62), (0.07, 0.8), (0.04, 1.6), (0, 1.7)], 8, T(cx, cy, 8.8))
    bm_box(bmg, cx - 0.02, cx + 0.02, cy - 0.02, cy + 0.02, 3.0, 4.35)
    globe_lamp_bm(bml, cx, cy, 2.85, 0.25)
    for bm_, nm, mat, sm in ((bmb, "base", "h_stone", False), (bmc, "columns", "h_white", True), (bmt, "entab", "h_white", False),
                             (bmd, "dome", "h_slate", True), (bmg, "finial", "h_gold", True), (bml, "lamp", "h_lamp", True)):
        obj_bm(f"HT_gazebo_{nm}", bm_, mat, smooth=sm)


def build_crescent():
    # one straight facaded run per real wall segment (a frame per segment, no bend -- see the note by CRESCENT): as
    # many equal bays as fit at roughly 5 m each, so a long run gets more bays than a short one
    for i in range(len(CRESCENT) - 1):
        (x0, y0), (x1, y1) = CRESCENT[i], CRESCENT[i + 1]
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, round(L / 5.0)); w = L / n
        with frame(f"HT_crescent_seg{i}", x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0))):
            crescent_bay(w, n)
            crescent_dormers(w, n)
    # the two ends (round domed turrets, set against the wall on its own tangent there, bulging out towards the court)
    # and the bespoke centre pavilion (straddling local x = 0, this frame's own origin)
    for name, (ex, ey), (nx_, ny_), (dx_, dy_) in (("left", CRESCENT[0], CRESCENT[1], (CRESCENT[1][0] - CRESCENT[0][0], CRESCENT[1][1] - CRESCENT[0][1])),
                                                   ("right", CRESCENT[-1], CRESCENT[-2], (CRESCENT[-1][0] - CRESCENT[-2][0], CRESCENT[-1][1] - CRESCENT[-2][1]))):
        L_ = math.hypot(ex - nx_, ey - ny_); ux, uy = (ex - nx_) / L_, (ey - ny_) / L_      # onward, past the end
        Ld = math.hypot(dx_, dy_); cnx, cny = -dy_ / Ld, dx_ / Ld                          # the segment's own +y: the court side
        corner_tower(ex + ux * TOWER_R * 0.5 + cnx * 1.0, ey + uy * TOWER_R * 0.5 + cny * 1.0, name)
    # the two Victorian wings in the court's front corners, fronts facing across the court
    themed_wing("blue", (-41.0, 40.0), (-41.0, 20.0), "h_blue", "h_white")
    themed_wing("purple", (39.0, 2.0), (39.0, 22.0), "h_purple", "h_pink")
    mid_i = next(i for i in range(len(CRESCENT) - 1) if CRESCENT[i][0] <= 0.0 <= CRESCENT[i + 1][0])
    a, b = CRESCENT[mid_i], CRESCENT[mid_i + 1]
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    entrance_pavilion(0.0, ang)


# ================================================================ 2. the back massing (New Grand Wing + the spine)
def back_bay(name, w, nfloors, tall=False):
    """One bay of a back wing (local x 0..w, y towards outside, z up): a plainer relative of crescent_bay -- an
    arched ground floor, plain windows above with a string course each floor, and (tall) a shallow cap near the top."""
    P = {k: bmesh.new() for k in ("wall", "trim", "glass")}
    m, h = w / 2, GF + FH * nfloors
    bm_box(P["wall"], 0, w, -0.02, 0, 0, h)
    bm_box(P["trim"], 0.05, 0.25, 0.0, 0.14, 0, h); bm_box(P["trim"], w - 0.25, w - 0.05, 0.0, 0.14, 0, h)
    bm_prism(P["trim"], arch_opening(m - 1.0, m + 1.0, GF - 3.6, GF - 0.6, 0.75, 12), 0.0, 0.12, "xz")
    bm_prism(P["glass"], arch_opening(m - 0.82, m + 0.82, GF - 3.4, GF - 0.75, 0.6, 10), 0.12, 0.15, "xz")
    for f in range(nfloors):
        z0 = GF + FH * f
        cap = tall and f >= nfloors - 3                     # the top few floors, set back under a shallow mansard cap
        ww = 1.5 if not cap else 1.1
        bm_box(P["trim"], m - ww / 2 - 0.12, m + ww / 2 + 0.12, 0.0, 0.1, z0 + 0.55, z0 + 0.65)
        bm_box(P["glass"], m - ww / 2, m + ww / 2, 0.1, 0.13, z0 + 0.7, z0 + 2.35)
        bm_box(P["trim"], m - ww / 2 - 0.1, m + ww / 2 + 0.1, 0.0, 0.14, z0 + 2.35, z0 + 2.55)
        bm_box(P["trim"], 0, w, 0.0, 0.08, z0 - 0.08, z0 - 0.02)
    bm_box(P["trim"], -0.04, w + 0.04, -0.05, 0.22, h - 0.35, h - 0.15)
    obj = {}
    for k, bm in P.items():
        mat = {"wall": "h_cream", "trim": "h_gold_trim", "glass": "h_win_dark"}[k]
        obj[k] = obj_bm(f"HT_{name}_{k}", bm, mat)
    return obj, h


def back_wing(name, pts, total_h):
    """A closed footprint (local xy): a plain arcaded shell per straight run of at least 3 m (as many bays as fit,
    Array + Curve so kinks and corners still line up with the real OSM plan), a parapet, and (tall) a set-back mansard
    cap with its own cornice near the top -- reads as "the same family as the crescent, without the hero details"."""
    nfloors = int(total_h / FH)
    curve, L = poly_curve(f"HT_{name}_curve", pts + [pts[0]])
    n_est = max(4, round(L / 5.5)); w = L / n_est
    bays, h = back_bay(name, w, nfloors, tall=(total_h > 40))
    for o in bays.values():
        array_mod(o, n_est, (w, 0, 0)); bend(o, curve)
    prism(f"HT_{name}_roof", [pts], h - 0.2, h, "h_slate")                 # a flat roof on the footprint itself
    bm = bmesh.new()                                        # parapet: a low wall on every edge of the footprint
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        L_ = math.hypot(x1 - x0, y1 - y0)
        if L_ < 0.1:
            continue
        nx, ny = -(y1 - y0) / L_ * 0.35, (x1 - x0) / L_ * 0.35
        bm_prism(bm, [(x0, y0), (x1, y1), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)], h, h + 0.9, "xy")
    obj_bm(f"HT_{name}_parapet", bm, "h_gold_trim")
    if total_h > 40:                                        # New Grand Wing: a slate penthouse over the middle of the roof
        cx, cy = sum(x for x, y in pts) / len(pts), sum(y for x, y in pts) / len(pts)
        inner = [(cx + (x - cx) * 0.55, cy + (y - cy) * 0.55) for x, y in pts]
        prism(f"HT_{name}_cap", [inner], h, h + 3.2, "h_slate")


def build_plinth():
    """Stone plinth under the whole footprint, 5 m deep: the court is 2 .. 5 m above the ground behind the building."""
    prism("HT_plinth", [CRESCENT + BACK[1:-1]], -5.0, 0.02, "h_paving2")


def build_back():
    """Two disjoint footprints from the same OSM way, so neither shell doubles over the other: the low spine + west
    wing (BACK from the New Grand Wing's corner onward, closing straight back across) and the New Grand Wing itself
    (BACK's first 4 points, the OSM height belongs here -- it reads far taller than the crescent in the photos)."""
    back_wing("spine", BACK[3:], BACK_H)
    back_wing("ngw", BACK[0:4], NGW_H)


# ================================================================ 3. the motor court: paving, gates, planters, topiary
def rosette(cx, cy, r0, r1, n=16, z=0.0):
    """A rosette medallion in the paving: a small centre disc, alternating pink / grey wedges out to r1, a ring."""
    bm1, bm2 = bmesh.new(), bmesh.new()
    disc = [(cx + r0 * math.cos(2 * math.pi * i / (n * 2)), cy + r0 * math.sin(2 * math.pi * i / (n * 2))) for i in range(n * 2)]
    bm_prism(bm1, disc, z, z + 0.02, "xy")
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        pts = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0)),
               (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))]
        bm_prism(bm1 if k % 2 == 0 else bm2, pts, z, z + 0.02, "xy")
    bm_prism(bm2, ring_sector(r1 + 0.15, r1 + 0.4, 0, 2 * math.pi, n * 2 + 1, cx, cy), z, z + 0.025, "xy")
    return bm1, bm2


def build_court():
    box("HT_court_ground", (-70, 70, 2, 45, -0.02, 0.0), "h_paving2")
    cx, cy = 0.0, 26.0
    # the round dais: three steps (the photos), the rose medallion on top with the TDH monogram at its centre
    bms, bmn = bmesh.new(), bmesh.new()
    for k, (rr, zz) in enumerate(((8.6, 0.17), (7.8, 0.34), (7.0, 0.51))):
        bm_lathe(bms, [(0, 0), (rr, 0), (rr, zz), (0, zz)], 64, T(cx, cy, 0.0))
        bm_lathe(bmn, [(rr - 0.35, zz), (rr, zz), (rr, zz + 0.01), (rr - 0.35, zz + 0.01)], 64, T(cx, cy, 0.0))   # the step nosings
    obj_bm("HT_steps_dais", bms, "h_paving1"); obj_bm("HT_steps_nosing", bmn, "h_stone")
    r1, r2 = rosette(cx, cy, 1.6, 6.5, 20, z=0.52)
    obj_bm("HT_court_rosette1", r1, "h_paving1"); obj_bm("HT_court_rosette2", r2, "h_paving2")
    bmm = bmesh.new()
    bm_lathe(bmm, [(0, 0), (1.5, 0), (1.5, 0.02), (0, 0.02)], 40, T(cx, cy, 0.54))
    obj_bm("HT_court_monogram_disc", bmm, "h_stone")
    text("HT_court_monogram", "TDH", 0.9, (cx, cy, 0.57), (0, 0, 0), "h_gold_trim", 0.02)
    # the two great round brick planters either side of the dais, gold TDH medallions, topiary figures on top
    bmb, bmh, bmd, bmc = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for s_ in (-1, 1):
        px, py = cx + s_ * 11.2, cy - 1.0
        bm_lathe(bmb, [(0, 0), (2.8, 0), (2.8, 2.3), (0, 2.3)], 40, T(px, py, 0))
        bm_lathe(bmc, [(2.6, 2.3), (2.95, 2.3), (2.95, 2.5), (2.6, 2.5)], 40, T(px, py, 0))
        a = math.atan2(cy + 12 - py, cx - px)                 # the medallion faces the gates
        mx, my = px + 2.82 * math.cos(a), py + 2.82 * math.sin(a)
        bm_lathe(bmd, [(0, 0), (0.75, 0), (0.75, 0.08), (0, 0.08)], 32, T(mx, my, 1.3) @ R(a, "Z") @ R(math.pi / 2, "Y"))
        bm_lathe(bmh, [(0, 0), (2.4, 0), (2.4, 0.5), (1.6, 0.9), (0, 1.0)], 20, T(px, py, 2.3))   # the clipped shrubs
        mickey_topiary(bmh, px, py, 3.1, scale=1.6)
    obj_bm("HT_planters", bmb, "h_brick"); obj_bm("HT_planter_caps", bmc, "h_stone")
    obj_bm("HT_planter_medallions", bmd, "h_gold", smooth=True); obj_bm("HT_topiary", bmh, "h_leaf", smooth=True)
    # curved iron handrails down the steps, beside each planter
    for s_ in (-1, 1):
        pts = []
        for k in range(10):
            a = math.radians(90 + s_ * (22 + 38 * k / 9))    # from beside the planter round the gates' side of the steps
            rr = 8.9
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a), 0.95))
        curve_obj(f"HT_rail{s_}", pts, "h_iron", 0.035)
    # the gates: square stone posts with urns, iron gates, stone balustrades out to the court's sides
    bmp, bmg, bmt, bmbal, bmu = (bmesh.new() for _ in range(5))
    gy, gw = 40.0, 3.4
    posts = [(-gw - 0.5, gy), (gw + 0.5, gy), (-13.0, gy), (13.0, gy), (-22.0, gy), (22.0, gy)]
    for px, py in posts:
        bm_box(bmp, px - 0.55, px + 0.55, py - 0.55, py + 0.55, 0.0, 0.4)
        bm_box(bmp, px - 0.45, px + 0.45, py - 0.45, py + 0.45, 0.4, 2.6)
        bm_box(bmp, px - 0.3, px + 0.3, py + 0.44, py + 0.47, 0.9, 2.2)
        bm_box(bmp, px - 0.58, px + 0.58, py - 0.58, py + 0.58, 2.6, 2.85)
        bm_lathe(bmu, [(0, 0), (0.2, 0), (0.12, 0.15), (0.34, 0.45), (0.3, 0.72), (0.12, 0.85), (0.16, 1.0), (0, 1.1)], 12, T(px, py, 2.85))
    for k in range(int(2 * gw / 0.14)):                      # the gates between the middle posts
        xx = -gw + 0.1 + k * 0.14
        if -gw + 0.1 < xx < gw - 0.1:
            bm_box(bmg, xx - 0.02, xx + 0.02, gy - 0.05, gy + 0.05, 0.2, 2.4 + 0.5 * math.cos(xx / gw * math.pi / 2))
    bm_box(bmg, -gw + 0.05, gw - 0.05, gy - 0.06, gy + 0.06, 0.9, 1.0)
    for x0_, x1_ in ((-13.0, -gw - 0.5), (gw + 0.5, 13.0), (-22.0, -13.0), (13.0, 22.0)):
        baluster_run(bmt, bmbal, (x0_ + 0.55, gy), (x1_ - 0.55, gy), 0.0, 1.1)
    obj_bm("HT_gate_posts", bmp, "h_stone"); obj_bm("HT_gate_urns", bmu, "h_stone", smooth=True)
    obj_bm("HT_gate_bars", bmg, "h_iron"); obj_bm("HT_gate_balustrade", bmt, "h_stone"); obj_bm("HT_gate_balusters", bmbal, "h_white")
    # smaller brick planters with Mickey / spiral topiary along the foot of the crescent
    bmb, bmh, bmd = bmesh.new(), bmesh.new(), bmesh.new()
    for i_, (x, y) in enumerate([(-24, 7.0), (24, 5.0), (-16, 9.5), (16, 9.5)]):
        r = 1.5
        bm_lathe(bmb, [(0, 0), (r, 0), (r, 0.9), (r - 0.15, 1.0), (r - 0.15, 1.15), (r, 1.25), (r, 1.4), (0, 1.4)], 20, T(x, y, 0))
        mickey_topiary(bmh, x, y, 1.4) if i_ % 2 == 0 else spiral_topiary(bmh, x, y, 1.4)
    obj_bm("HT_planters_small", bmb, "h_brick"); obj_bm("HT_topiary_small", bmh, "h_leaf", smooth=True)
    # lamp posts flanking the drive
    bmp, bml = bmesh.new(), bmesh.new()
    for x, y in ((-6.5, 36.0), (6.5, 36.0), (-14.0, 16.0), (14.0, 16.0)):
        bm_lathe(bmp, [(0, 0), (0.28, 0), (0.28, 0.4), (0.16, 0.6), (0.1, 4.6), (0.16, 4.7), (0.08, 4.9), (0, 4.9)], 14, T(x, y, 0.0))
        for a in range(4):
            aa = a * math.pi / 2 + math.pi / 4
            globe_lamp_bm(bml, x + 0.35 * math.cos(aa), y + 0.35 * math.sin(aa), 5.0, 0.16)
        globe_lamp_bm(bml, x, y, 5.35, 0.2)
    obj_bm("HT_lampposts", bmp, "h_iron", smooth=True); obj_bm("HT_lamp_globes", bml, "h_lamp", smooth=True)


def mickey_topiary(bm, x, y, z0, scale=1.0):
    S = Matrix.Diagonal((scale, scale, scale, 1.0))
    bm_lathe(bm, [(0, 0), (0.35, 0.6), (0.42, 1.3), (0.33, 1.9), (0, 2.1)], 16, T(x, y, z0) @ S)
    for dx, dy, dz, r in ((0, 0, 2.5, 0.6), (0.42, 0.1, 2.85, 0.32), (-0.36, -0.15, 2.8, 0.32)):
        bm_lathe(bm, [(0, -r), (r, 0), (0, r)], 12, T(x + dx * scale, y + dy * scale, z0 + dz * scale) @ S)
    for a, dz, dl in ((0.9, 1.7, 1), (-0.9, 1.7, -1)):
        bm_lathe(bm, [(0, -0.18), (0.5, -0.05), (0.55, 0.15), (0.15, 0.22)], 10, T(x + dl * 0.4 * scale, y, z0 + dz * scale) @ R(a * dl, "Z") @ S)


def spiral_topiary(bm, x, y, z0):
    h = 2.6
    bm_lathe(bm, [(0.5, 0), (0.5, h * 0.15), (0.15, h * 0.55), (0.3, h * 0.8), (0, h)], 16, T(x, y, z0))


# ================================================================ for the mock (export_models.py --parts tdl_hotel)
FRAME = dict(x=-573.895, y=1171.313, ang=65.6534)      # the hotel's local frame in the DisneySea/mock frame (see docstring)
BUILDING_Z = 2.3                                       # the court's ground at the crescent's wall (tdl_hotel_ground.json)


def ground_sampler():
    """Height of the mock's hotel ground (tdl_hotel_ground.json) at an absolute (x, y): median of vertices within 6 m."""
    import json, base64, numpy as np
    d = json.loads((ROOT / "output" / "disneysea" / "models" / "tdl_hotel_ground.json").read_text(encoding="utf-8"))
    buf = base64.b64decode(d["buffers"][0]["uri"].split(",")[1])
    pts = []
    for m in d["meshes"]:
        for p in m["primitives"]:
            a = d["accessors"][p["attributes"]["POSITION"]]; bv = d["bufferViews"][a["bufferView"]]
            off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
            pts.append(np.frombuffer(buf, dtype=np.float32, count=a["count"] * 3, offset=off).reshape(-1, 3))
    P = np.vstack(pts); X, Z, Y = P[:, 0], P[:, 1], -P[:, 2]
    def f(x, y):
        d2 = (X - x) ** 2 + (Y - y) ** 2
        near = d2 < 81.0
        return float(np.median(Z[near])) if near.any() else float(Z[np.argmin(d2)])
    return f


def export_objects(merged):
    """One mesh per material ("HO_<material>") in the mock's frame. The building stands on the court's level (BUILDING_Z);
    each court object (the dais, planters, gates, gazebo, lamps) sits on the mock's ground where it stands; the court's
    paving becomes a 1.5 m grid on that ground (the hotel ground model has only the roads and paths there)."""
    build()
    B.root.location = (FRAME["x"], FRAME["y"], 0.0); B.root.rotation_euler = (0, 0, math.radians(FRAME["ang"]))
    for o in B.col.objects:
        for m in o.modifiers:
            if m.type == "BEVEL":
                m.show_viewport = False
    bpy.context.view_layer.update()
    g = ground_sampler()
    # the court's own paving follows the ground (the hotel ground model has only the roads and paths there): a 1.5 m grid
    cg = bpy.data.objects.get("HT_court_ground")
    if cg:
        ca, sa = math.cos(math.radians(FRAME["ang"])), math.sin(math.radians(FRAME["ang"]))
        bm = bmesh.new(); step = 1.5
        nx, ny = int(88 / step) + 1, int(44.8 / step) + 1
        vs = []
        for j in range(ny):
            for i in range(nx):
                x, y = -44.0 + i * step, 1.2 + j * step
                vs.append(bm.verts.new((x, y, g(FRAME["x"] + x * ca - y * sa, FRAME["y"] + x * sa + y * ca) + 0.02)))
        for j in range(ny - 1):
            for i in range(nx - 1):
                a = j * nx + i
                bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
        bm.normal_update()
        me = bpy.data.meshes.new("HT_court_ground"); bm.to_mesh(me); bm.free()
        me.materials.append(cg.data.materials[0]); cg.data = me
    court = ("HT_court_", "HT_gate", "HT_planter", "HT_topiary", "HT_steps", "HT_fountain", "HT_lamp", "HT_rail", "HT_gazebo")
    groups = {}
    for o in B.col.objects:
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith("CAM_"):
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if not mats:
            continue
        if o.name == "HT_court_ground":
            dz = 0.0                                      # already on the ground, vertex by vertex
        elif o.name.startswith(court) and o.type == "MESH" and len(o.data.vertices):
            from mathutils import Vector
            c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
            dz = g(c.x, c.y)
        else:
            dz = BUILDING_Z
        groups.setdefault("HO_" + mats[0].name[3:], []).append((o, dz))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


# ================================================================ scene
def cams():
    return {
        "court": ((0.0, 37.0, 1.8), (0.0, 0.0, 17.0), 15),          # as the photos: from the dais towards the main block
        "gates_wide": ((0.0, 47.0, 1.7), (0.0, 0.0, 16.0), 16),
        "court_close": ((-10.0, 20.0, 1.7), (0.0, 5.0, 9.0), 28),
        "crescent": ((0.0, 45.0, 6.0), (0.0, 0.0, 12.0), 22),
        "gates": ((16.0, 44.0, 1.7), (0.0, 20.0, 6.0), 22),
        "pavilion": ((0.0, 18.0, 3.0), (0.0, 0.0, 16.0), 24),
        "aerial": ((70.0, 70.0, 95.0), (-40.0, -20.0, 0.0), 26),
    }


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    B.col = bpy.data.collections.new("TDL_Hotel"); sc.collection.children.link(B.col)
    B.cutters = bpy.data.collections.new("Cutters"); sc.collection.children.link(B.cutters)
    B.root = bpy.data.objects.new("TDL_Hotel", None); B.col.objects.link(B.root)
    B.hide = []
    B.M = hotel_materials(ST.materials())
    t0 = time.time()
    build_crescent()
    build_back()
    build_plinth()
    build_court()
    out = {}
    for name, (loc, tgt, lens) in cams().items():
        cam = bpy.data.cameras.new("CAM_" + name); cam.lens = lens; cam.clip_start = 0.05; cam.clip_end = 3000
        co = bpy.data.objects.new("CAM_" + name, cam); B.col.objects.link(co); co.parent = B.root
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        out[name] = co
    print(f"[hotel] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="court,court_close,crescent,gates,pavilion,aerial")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=60)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    cams_ = build()
    ST.world_sky()
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.camera = cams_["court"]
    for c in B.cutters.objects:
        c.hide_set(True)
    ST.frame_view()
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "tdl_hotel.blend").resolve()))
    print("[hotel] saved", OUT / "tdl_hotel.blend")
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        old = ST.OUT
        ST.OUT = OUT
        try:
            ST.render(cams_, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES", "hotel")
        finally:
            ST.OUT = old


if __name__ == "__main__" and bpy is not None:
    main()
