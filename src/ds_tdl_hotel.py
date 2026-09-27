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
GF, FH, NFLOORS = 5.0, 3.2, 5                          # ground floor, upper-floor height, upper floors on the crescent
CORNICE = GF + FH * NFLOORS                            # 21.0
EAVE, RIDGE = CORNICE + 1.5, CORNICE + 5.5             # 22.5, 27.0 (crescent's mansard)
MANSARD_D, DECK_D = 1.6, 0.5                           # the mansard's slope depth, then a short flat deck behind it
TURRET_TOP, DOME_TOP = 30.0, 34.0
BACK_H, NGW_H = 24.0, 58.0


def hotel_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    mat, nt, b = _principled("st_hotel_cream", (0.86, 0.76, 0.55), 0.55); _mottle(nt, b, (0.86, 0.76, 0.55), 7, 0.94, 0.03); M["h_cream"] = mat
    mat, nt, b = _principled("st_hotel_gold", (0.80, 0.62, 0.33), 0.4); _mottle(nt, b, (0.80, 0.62, 0.33), 7, 0.94, 0.02); M["h_gold_trim"] = mat
    M["h_slate"] = P("st_hotel_slate", (0.24, 0.29, 0.38), 0.45, Metallic=0.15)
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
    if balcony:
        bm_box(bm_rail, x - w / 2 + 0.1, x + w / 2 - 0.1, 0.14, 0.5, z0 - 0.06, z0 - 0.02)
        bm_box(bm_rail, x - w / 2 + 0.1, x + w / 2 - 0.1, 0.14, 0.5, z0 + 0.75, z0 + 0.82)
        for k in range(int((w - 0.2) / 0.16)):
            xx = x - w / 2 + 0.1 + k * 0.16
            bm_box(bm_rail, xx - 0.015, xx + 0.015, 0.16, 0.48, z0 - 0.02, z0 + 0.75)
        for dx in (-1, 1):
            bm_box(bm_rail, x + dx * (w / 2 - 0.1) - 0.02, x + dx * (w / 2 - 0.1) + 0.02, 0.14, 0.5, z0 - 0.06, z0 + 0.82)


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
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "iron", "slate", "gold", "lamp", "leaf")}
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
        paired_window(P["trim"], P["glass"], P["iron"], m, 2.0, z0, z0 + 1.85, balcony=(f == 0))
        bm_box(P["trim"], m - 1.15, m + 1.15, 0.0, 0.14, GF + FH * (f + 1) - 0.12, GF + FH * (f + 1) + 0.05)
    bm_box(P["trim"], -0.05, w + 0.05, -0.1, 0.28, CORNICE - 0.4, CORNICE - 0.25)   # a plain dentil cornice band
    for k in range(int(w / 0.5)):
        xx = k * 0.5 + 0.25
        bm_box(P["trim"], xx - 0.1, xx + 0.1, 0.0, 0.22, CORNICE - 0.25, CORNICE - 0.1)
    baluster_run(P["trim"], P["gold"], (0.0, 0.32), (w, 0.32), CORNICE, EAVE)   # a turned-baluster balustrade at the roofline
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
               "slate": "h_slate", "gold": "h_gold", "lamp": "h_lamp", "leaf": "h_leaf"}[k]
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


def crescent_turret(x, y, ang_deg):
    """A round domed corner turret, set against the crescent's wall at (x, y) facing outward along ang_deg."""
    with frame("HT_turret", x, y, ang_deg):
        bm_w, bm_t, bm_d, bm_g, bm_l = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        r, top, cy = 2.1, TURRET_TOP - 3.0, 0.6
        ring = [(r * math.cos(a), cy + r * math.sin(a)) for a in (2 * math.pi * i / 24 for i in range(24))]
        bm_prism(bm_w, ring, 0, top, "xy")
        for f in range(4):                                 # a round-headed window slit on each face
            z0 = GF + f * (top - GF - 1.0) / 4 + 0.5
            bm_prism(bm_t, arch_opening(-0.35, 0.35, z0, z0 + 1.1, 0.35, 8), cy + r - 0.15, cy + r + 0.02, "xz")
        bm_box(bm_t, -r - 0.15, r + 0.15, cy - r - 0.15, cy + r + 0.15, top - 0.5, top - 0.35)   # a cornice collar
        bm_lathe(bm_t, [(r - 0.1, 0), (r + 0.25, 0), (r + 0.25, 0.15), (r - 0.1, 0.15)], 24, T(0, cy, top - 0.35))
        bm_lathe(bm_d, [(0, 0), (r + 0.1, 0), (r + 0.1, 0.15), (r - 0.3, 0.9), (r * 0.5, 1.9), (0.15, 2.5), (0.15, 2.7), (0, 2.7)], 24, T(0, cy, top))
        bm_lathe(bm_g, [(0, 0), (0.09, 0), (0.06, 0.55), (0.1, 0.62), (0.03, 0.9), (0.03, 1.05), (0, 1.05)], 8, T(0, cy, top + 2.7))
        globe_lamp_bm(bm_l, 0, cy - r - 0.35, GF - 2.0, 0.11)
        obj_bm("HT_turret_wall", bm_w, "h_cream"); obj_bm("HT_turret_trim", bm_t, "h_gold_trim")
        obj_bm("HT_turret_dome", bm_d, "h_slate", smooth=True); obj_bm("HT_turret_finial", bm_g, "h_gold", smooth=True)
        obj_bm("HT_turret_lamp", bm_l, "h_lamp", smooth=True)


def entrance_pavilion(x, ang_deg):
    """The bespoke central pavilion (photographed head-on): a tall arched doorway, columns, a clock, a pediment and a
    small domed lantern above; projects 2.4 m out from the crescent's wall on to the court. Faces +y at x on the curve."""
    with frame("HT_pavilion", x, 0.0, ang_deg):
        hw, d = 7.0, 2.4
        bmw, bmt, bmg, bmc, bml = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        bm_box(bmw, -hw, hw, 0, d, 0, EAVE + 1.6)
        for k in range(1, int(GF)):                        # rusticated ground floor, as the crescent's own bays
            bm_box(bmt, -hw + 0.4, hw - 0.4, d - 0.02, d + 0.02, k * 1.0, k * 1.0 + 0.04)
        for s in (-1, 1):
            column_bm(bmc, s * (hw - 0.9), d - 0.35, 0.4, EAVE - 3.5, 0.32, 16)
            bm_box(bmt, s * (hw - 0.9) - 0.45, s * (hw - 0.9) + 0.45, d - 0.5, d - 0.15, 0.0, 0.4)
            sconce(bmt, bml, s * 3.6, d + 0.02, GF - 1.3)
        bm_prism(bmt, arch_opening(-3.1, 3.1, 0.0, 8.6, 3.0, 20), d, d + 0.12, "xz")     # the grand arched doorway
        bm_prism(bmg, arch_opening(-2.8, 2.8, 0.15, 8.5, 2.8, 18), d + 0.12, d + 0.16, "xz")
        for s in (-1, 1):                                  # panelled double doors (dark glass), recessed under the fanlight
            bm_box(bmg, s * 0.05, s * 1.35, d + 0.05, d + 0.09, 0.0, 4.6)
            for k in range(3):
                bm_box(bmg, s * 0.2, s * 1.2, d + 0.06, d + 0.08, 0.3 + k * 1.45, 0.3 + k * 1.45 + 1.1)
        bm_prism(bmt, arch_band(-3.1, 3.1, 8.6, 3.0, 0.35, 20, leg=0.3), d - 0.05, d + 0.2, "xz")
        bm_box(bmt, -hw + 0.6, hw - 0.6, d - 0.02, d + 0.02, EAVE - 3.5, EAVE - 3.1)      # entablature over the columns
        bm_lathe(bmc, [(0.9, 0), (1.05, 0), (1.05, 0.1), (0.9, 0.1)], 32, T(0, d + 0.03, GF + 8.9) @ R(-math.pi / 2, "X"))   # the clock
        bm_lathe(bmg, [(0, 0), (0.9, 0), (0.9, 0.08), (0, 0.08)], 32, T(0, d + 0.02, GF + 8.9) @ R(-math.pi / 2, "X"))
        cz = GF + 8.9                                       # clock hour marks round the rim + hour / minute hands (fixed at ten past ten)
        for i in range(12):
            a = math.pi / 2 - 2 * math.pi * i / 12
            bm_box(bmc, math.cos(a) * 0.72 - 0.025, math.cos(a) * 0.82 + 0.025, d + 0.03, d + 0.05,
                   cz + math.sin(a) * 0.72 - 0.025, cz + math.sin(a) * 0.82 + 0.025)
        for ang, ln in ((math.radians(60), 0.45), (math.radians(-30), 0.6)):
            bm_box(bmc, min(0, math.cos(ang) * ln) - 0.02, max(0, math.cos(ang) * ln) + 0.02, d + 0.03, d + 0.05,
                   cz + min(0, math.sin(ang) * ln) - 0.02, cz + max(0, math.sin(ang) * ln) + 0.02)
        pts, _ = seg_arc(0, EAVE + 0.1, 2 * hw - 1.0, 3.0, 20)
        bm_prism(bmw, [(-hw + 0.5, EAVE + 0.1), (hw - 0.5, EAVE + 0.1)] + pts[::-1], -0.3, d - 0.3, "xz")   # pediment
        bm_prism(bmt, arch_band(-hw + 0.5, hw - 0.5, EAVE + 0.1, 3.0, 0.3, 20, leg=0.4), -0.35, d - 0.25, "xz")
        bm_lathe(bmt, [(0.35, 0), (0.5, 0), (0.5, 0.1), (0.35, 0.1)], 24, T(0, d / 2, EAVE + 3.0) @ R(-math.pi / 2, "X"))   # cartouche
        bm_box(bmw, -hw, hw, 0, d - 0.1, EAVE + 1.6, EAVE + 2.0)
        bm_lathe(bmw, [(0, 0), (4.0, 0), (4.0, 0.3), (3.2, 1.6), (1.6, 2.6), (0.5, 3.0), (0.5, 3.3), (0, 3.3)], 28, T(0, d / 2, EAVE + 2.0))
        bm_lathe(bmc, [(0, 0), (0.1, 0), (0.06, 0.7), (0, 0.8)], 8, T(0, d / 2, DOME_TOP))
        for s in (-1, 1):                                  # flagpoles either side of the dome, on the pediment's shoulders
            fx, fz = s * (hw - 1.4), EAVE + 2.05
            bm_lathe(bmt, [(0, 0), (0.05, 0), (0.05, 5.2), (0.02, 5.4), (0, 5.4)], 8, T(fx, d / 2, fz))
            box(f"HT_pav_flag{s}", (min(fx, fx + s * 1.6), max(fx, fx + s * 1.6), d / 2 - 0.02, d / 2 + 0.02, fz + 4.6, fz + 5.05), "h_flower_purple")
        text("HT_pav_plaque", "TOKYO DISNEYLAND HOTEL", 0.22, (0, d - 0.19, GF - 1.9), (math.pi / 2, 0, 0), "h_bronze", 0.012)
        obj_bm("HT_pav_wall", bmw, "h_cream"); obj_bm("HT_pav_trim", bmt, "h_gold_trim")
        obj_bm("HT_pav_glass", bmg, "h_win_dark"); obj_bm("HT_pav_gold", bmc, "h_gold", smooth=True)
        obj_bm("HT_pav_lamps", bml, "h_lamp", smooth=True)
        box("HT_pav_floor", (-hw + 0.3, hw - 0.3, 0.0, d - 0.05, -0.05, 0.0), "h_paving1")


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
    x0, y0 = CRESCENT[0]; x1, y1 = CRESCENT[1]
    crescent_turret(x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0)))
    x0, y0 = CRESCENT[-1]; x1, y1 = CRESCENT[-2]
    crescent_turret(x0, y0, math.degrees(math.atan2(y0 - y1, x0 - x1)))
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
def rosette(cx, cy, r0, r1, n=16):
    """A rosette medallion in the paving: a small centre disc, alternating pink / grey wedges out to r1, a ring."""
    bm1, bm2 = bmesh.new(), bmesh.new()
    disc = [(cx + r0 * math.cos(2 * math.pi * i / (n * 2)), cy + r0 * math.sin(2 * math.pi * i / (n * 2))) for i in range(n * 2)]
    bm_prism(bm1, disc, 0.0, 0.02, "xy")
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        pts = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0)),
               (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))]
        bm_prism(bm1 if k % 2 == 0 else bm2, pts, 0.0, 0.02, "xy")
    bm_prism(bm2, ring_sector(r1 + 0.15, r1 + 0.4, 0, 2 * math.pi, n * 2 + 1, cx, cy), 0.0, 0.025, "xy")
    return bm1, bm2


def build_court():
    box("HT_court_ground", (-70, 70, 2, 45, -0.02, 0.0), "h_paving2")
    r1, r2 = rosette(0.0, 24.0, 2.0, 8.0)
    obj_bm("HT_court_rosette1", r1, "h_paving1"); obj_bm("HT_court_rosette2", r2, "h_paving2")
    # the gates: two brick piers with a bronze medallion either side of the drive, an iron gate between them, and a
    # low brick wall with iron bars running out to the court's edge on each side
    bmp, bmg, bmm = bmesh.new(), bmesh.new(), bmesh.new()
    gy, gw = 40.0, 3.4                                    # the gate's own half-width (the drive passing through it)
    for s in (-1, 1):
        px = s * 12.0
        bm_lathe(bmp, [(0, 0), (1.0, 0), (1.0, 0.15), (0.85, 0.2), (0.85, 3.0), (1.0, 3.05), (1.0, 3.3), (0.6, 3.5), (0, 3.5)], 16, T(px, gy, 0))
        bm_lathe(bmm, [(0, 0), (0.55, 0), (0.55, 0.08), (0, 0.08)], 24, T(px, gy - 1.02, 1.9) @ R(-math.pi / 2, "X"))
    for k in range(int(2 * gw / 0.14)):                   # the gate itself, between the two piers
        xx = -gw + 1.0 + k * 0.14
        if -gw + 1.0 < xx < gw - 1.0:
            bm_box(bmg, xx - 0.02, xx + 0.02, gy - 0.05, gy + 0.05, 0.3, 3.2)
    bm_box(bmg, -gw + 1.0, gw - 1.0, gy - 0.06, gy + 0.06, 3.1, 3.3)
    obj_bm("HT_gate_piers", bmp, "h_brick"); obj_bm("HT_gate_medallion", bmm, "h_gold", smooth=True)
    obj_bm("HT_gate_bars", bmg, "h_iron")
    bmw, bmb2 = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        x0, x1 = sorted((s * 12.0, s * 22.0))
        bm_box(bmw, x0, x1, gy - 0.15, gy + 0.15, 0.0, 1.0)
        for k in range(int((x1 - x0) / 0.16)):
            xx = x0 + 0.2 + k * 0.16
            if xx < x1 - 0.2:
                bm_box(bmb2, xx - 0.015, xx + 0.015, gy - 0.06, gy + 0.06, 1.0, 2.1)
    obj_bm("HT_gate_walls", bmw, "h_brick"); obj_bm("HT_gate_wall_bars", bmb2, "h_iron")
    # brick planters with Mickey topiary + a monogram, and plain hedge / spiral topiary, along the colonnade
    bmb, bmh, bmd = bmesh.new(), bmesh.new(), bmesh.new()
    positions = [(-24, 6.0), (24, 6.0), (-14, 4.5), (14, 4.5), (-30, 14.0), (30, 14.0)]
    for i, (x, y) in enumerate(positions):
        r = 1.5
        bm_lathe(bmb, [(0, 0), (r, 0), (r, 0.9), (r - 0.15, 1.0), (r - 0.15, 1.15), (r, 1.25), (r, 1.4), (0, 1.4)], 20, T(x, y, 0))
        bm_lathe(bmd, [(r - 0.55, 0), (r - 0.4, 0), (r - 0.4, 0.06), (r - 0.55, 0.06)], 24, T(x, y, 1.32) @ R(-math.pi / 2, "X"))
        mickey_topiary(bmh, x, y, 1.4) if i % 2 == 0 else spiral_topiary(bmh, x, y, 1.4)
    obj_bm("HT_planters", bmb, "h_brick"); obj_bm("HT_planter_medallions", bmd, "h_gold", smooth=True)
    obj_bm("HT_topiary", bmh, "h_leaf", smooth=True)
    # steps + balustrade up to the entrance pavilion
    bms = bmesh.new()
    for k in range(6):
        bm_box(bms, -6.0 + k * 0.05, 6.0 - k * 0.05, 2.0 + k * 0.35, 2.35 + k * 0.35, 0.0, 0.2 * (k + 1))
    obj_bm("HT_steps", bms, "h_paving1")
    # a low fountain basin in the court's own rosette, tall lamp posts flanking the drive, and a clipped hedge with
    # bedding plants along the foot of the crescent's wall (photos: the wings sit behind a narrow planting strip)
    bmf, bmw2 = bmesh.new(), bmesh.new()
    bm_lathe(bmf, [(0, 0), (3.2, 0), (3.2, 0.5), (2.7, 0.55), (2.7, 0.15), (0, 0.15)], 40, T(0.0, 24.0, 0.0))
    bm_lathe(bmw2, [(0, 0), (2.35, 0), (2.35, 0.4), (0, 0.4)], 40, T(0.0, 24.0, 0.05))
    bm_lathe(bmf, [(0.25, 0), (0.42, 0), (0.3, 0.35), (0.34, 0.42), (0.1, 0.7), (0, 0.75)], 16, T(0.0, 24.0, 0.55))
    obj_bm("HT_fountain_basin", bmf, "h_paving1"); obj_bm("HT_fountain_water", bmw2, "h_glass")
    bmp, bml = bmesh.new(), bmesh.new()
    for x, y in ((-18.0, 16.0), (18.0, 16.0), (-18.0, 32.0), (18.0, 32.0)):
        bm_lathe(bmp, [(0, 0), (0.28, 0), (0.28, 0.4), (0.16, 0.6), (0.1, 5.6), (0.16, 5.7), (0.08, 5.9), (0, 5.9)], 14, T(x, y, 0.0))
        for a in range(4):
            aa = a * math.pi / 2 + math.pi / 4
            globe_lamp_bm(bml, x + 0.35 * math.cos(aa), y + 0.35 * math.sin(aa), 6.0, 0.16)
        globe_lamp_bm(bml, x, y, 6.35, 0.2)
    obj_bm("HT_lampposts", bmp, "h_iron", smooth=True); obj_bm("HT_lamp_globes", bml, "h_lamp", smooth=True)


def mickey_topiary(bm, x, y, z0):
    bm_lathe(bm, [(0, 0), (0.35, 0.6), (0.42, 1.3), (0.33, 1.9), (0, 2.1)], 16, T(x, y, z0))
    for dx, dy, dz, r in ((0, 0, 2.5, 0.6), (0.42, 0.1, 2.85, 0.32), (-0.36, -0.15, 2.8, 0.32)):
        bm_lathe(bm, [(0, -r), (r, 0), (0, r)], 12, T(x + dx, y + dy, z0 + dz))
    for a, dz, dl in ((0.9, 1.7, 1), (-0.9, 1.7, -1)):
        bm_lathe(bm, [(0, -0.18), (0.5, -0.05), (0.55, 0.15), (0.15, 0.22)], 10, T(x + dl * 0.4, y, z0 + dz) @ R(a * dl, "Z"))


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
        near = d2 < 36.0
        return float(np.median(Z[near])) if near.any() else float(Z[np.argmin(d2)])
    return f


def export_objects(merged):
    """One mesh per material ("HO_<material>") in the mock's frame. The building stands on the court's level (BUILDING_Z);
    each court object (gates, planters, fountain, lamps) sits on the mock's ground where it stands; the court's own
    paving slab is left out (the hotel ground model has it)."""
    build()
    B.root.location = (FRAME["x"], FRAME["y"], 0.0); B.root.rotation_euler = (0, 0, math.radians(FRAME["ang"]))
    for o in B.col.objects:
        for m in o.modifiers:
            if m.type == "BEVEL":
                m.show_viewport = False
    bpy.context.view_layer.update()
    g = ground_sampler()
    court = ("HT_court_", "HT_gate", "HT_planter", "HT_topiary", "HT_steps", "HT_fountain", "HT_lamp")
    groups = {}
    for o in B.col.objects:
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith("CAM_") or o.name == "HT_court_ground":
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if not mats:
            continue
        if o.name.startswith(court) and o.type == "MESH" and len(o.data.vertices):
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
        "court": ((6.0, 30.0, 1.8), (0.0, 0.0, 11.0), 24),
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
