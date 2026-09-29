"""東京ディズニーランドホテル -- the hotel's front court (the station side), its wings and towers, the rest of the building (Blender 5.2).

  python src/ds_tdl_hotel_plan.py                                  # the plan (plain Python): plateau_data/tdl_hotel_plan.json
  blender -b --python src/ds_tdl_hotel.py -- --cams court,gates_wide,aerial --samples 32
  blender -b --python src/ds_tdl_hotel.py -- --cams none           # build + save the .blend only
  then open output/disneyland/hotel/tdl_hotel.blend (cameras CAM_*)

Sources (looked at only; nothing copied into the repository):
  * OSM: the hotel's outline (way 218553057, building=retail + tourism=hotel, height 60, 701 rooms). One polygon for the
    whole complex; ds_tdl_hotel_plan.py cuts it into parts. The FRONT is the south side, towards the station: a U-shaped
    court about 45 m wide, the round garden in its middle (the round building 788770688 inside the ring path 1340488354).
  * The user's photos of that front (2026-09-28, five, from the station side): the main block at the head of the court
    (three tall arched windows, the middle one the tallest, paired pilasters, the gold dome on a drum with a lantern), the
    little blue-domed gazebo in front of its doors, the wings either side with a white balcony at every window, the two
    tall towers where the wings end (octagonal, a balustraded crown, a blue slate spire), the low blue and purple Victorian
    wings beyond them, the round three-step dais with the rose medallion and the TDH monogram, the two great round brick
    planters with gold medallions and Mickey topiary, square stone gate posts with urns, iron gates, balustrades.
  * Wikimedia Commons "Tokyo Disney Land Hotel" (2022): the same court, the planters and medallions close up.

Frame: local metres (FRAME below, in the mock's frame), +z up. The front court has its own frame (PLAN["court"]): origin on
the head wall opposite the round garden, +y out across the court towards the station, +x along the head wall (to the west:
on the left, seen from the station). Every facade run faces its own local +y (the outline is clockwise).

ESTIMATES (no photo has a person to scale against): ground floor 5.0 m, 7 floors of 3.2 m above (cornice 27.4 m), mansard to
33 m; the towers 11 floors and a spire to about 55 m; the dome's top about 44 m; the Victorian wings 4 floors. The tall
block to the north-east gets OSM's 60 m (58 m + a penthouse). Bay widths, the gazebo's and the dais' sizes, the gates.
The north side (the crescent on the porte-cochere loop) and the rest are the same facade as the court's wings, not
checked against any photo; a pediment over the middle of each long run, the porte-cochere where the loop road passes the
wall (an iron-and-glass canopy), the gatehouse in the loop, the tall block's 15 floors, the curtains and lit rooms: all
estimates.
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
from ds_tdl_station import (B, box, prism, bm_box, bm_prism, bm_lathe, obj_bm, array_mod, T, R, arch_opening, arch_band, ring_sector, curve_obj, column_bm,
                            globe_lamp_bm, text, _principled, _mottle)
from ds_tdl_entrance import frame, baluster_run

OUT = ROOT / "output" / "disneyland" / "hotel"

PLAN = json.loads((ROOT / "plateau_data" / "tdl_hotel_plan.json").read_text(encoding="utf-8"))   # ds_tdl_hotel_plan.py
COURT = PLAN["court"]                                  # the front court's frame, in this local frame
GF, FH, NFLOORS = 5.0, 3.2, 7                          # ground floor, upper-floor height, upper floors on the crescent
CORNICE = GF + FH * NFLOORS                            # 27.4
EAVE, RIDGE = CORNICE + 1.5, CORNICE + 5.5             # 28.9, 32.9 (crescent's mansard)
MANSARD_D, DECK_D = 1.6, 0.5                           # the mansard's slope depth, then a short flat deck behind it
TOWER_FLOORS, TOWER_R = 11, 6.2                        # the two corner towers: 11 floors, 12.4 m across the octagon
DOME_TOP = 46.0


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
    M["h_curtain"] = P("st_hotel_curtain", (0.93, 0.88, 0.76), 0.9)
    M["h_win_lit"] = P("st_hotel_winlit", (1.0, 0.86, 0.6), 0.4, Emission_Color=(1.0, 0.78, 0.48, 1), Emission_Strength=1.6)
    M["h_wood"] = P("st_hotel_wood", (0.40, 0.24, 0.12), 0.6)
    M["h_flower_pink"] = P("st_hotel_flpink", (0.85, 0.30, 0.45), 0.9)
    M["h_flower_white"] = P("st_hotel_flwhite", (0.95, 0.93, 0.88), 0.9)
    return M


# ================================================================ helpers
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


def dormer(bm_wall, bm_glass, bm_trim, x, w=1.4, dz=0.0):
    """A round-headed dormer standing on the mansard's slope (which runs back from the wall, local -y), with its own
    little gabled roof; its face is part way up the slope."""
    yf = -0.55                                            # the dormer's face
    z0 = EAVE + dz + (RIDGE - EAVE) * (-yf / MANSARD_D)   # the slope's height there: the dormer sits on it
    h = 1.8
    bm_box(bm_wall, x - w / 2, x + w / 2, yf - 1.1, yf, z0 - 0.5, z0 + h)
    bm_prism(bm_trim, arch_opening(x - w / 2 - 0.1, x + w / 2 + 0.1, z0 - 0.05, z0 + h - w / 2, w / 2 + 0.1, 12), yf, yf + 0.05, "xz")
    bm_prism(bm_glass, arch_opening(x - w / 2 + 0.15, x + w / 2 - 0.15, z0 + 0.15, z0 + h - w / 2, w / 2 - 0.15, 10), yf + 0.05, yf + 0.07, "xz")
    bm_prism(bm_wall, [(x - w / 2 - 0.28, z0 + h), (x + w / 2 + 0.28, z0 + h), (x, z0 + h + 0.9)], yf - 1.3, yf + 0.2, "xz")


def sconce(bm_iron, bm_lamp, x, y, z):
    """A small wrought-iron wall lamp bracket, out from the wall (y) to a globe."""
    bm_lathe(bm_iron, [(0, 0), (0.045, 0), (0.045, 0.05), (0, 0.05)], 8, T(x, y, z - 0.03))
    bm_box(bm_iron, x - 0.02, x + 0.02, y, y + 0.24, z - 0.02, z + 0.02)
    bm_box(bm_iron, x - 0.02, x + 0.02, y + 0.22, y + 0.26, z - 0.02, z + 0.2)
    globe_lamp_bm(bm_lamp, x, y + 0.24, z + 0.24, 0.1)


# ================================================================ 1. the crescent (Array + Curve, as the entrance's gates)
def crescent_bay(w, N, plain=False, nfl=NFLOORS, tag="crescent", kerb=True, balcony=lambda f: True, belt=0):
    """One bay of the main building's facade (local x 0..w along the wall, +y out from it, z up), Array N times.
    plain: a short run of wall (a kink in the outline) -- no windows, just the wall, cornice, balustrade and roof.
    nfl upper floors (the north-east block: 15); kerb: the kerb and hedge ball at the wall's foot (not under the
    porte-cochere); balcony(f): which floors have a balcony; belt: a heavier band every belt floors (the tall block)."""
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "iron", "slate", "gold", "lamp", "leaf", "rail")}
    m = w / 2
    cor = GF + FH * nfl; eave, ridge = cor + 1.5, cor + 5.5
    if not plain and kerb:
        bm_box(P["trim"], 0.15, w - 0.15, 0.9, 1.3, 0.0, 0.35)            # a low kerb along the foot of the wall
        bm_lathe(P["leaf"], [(0, -0.28), (0.32, 0), (0, 0.28)], 10, T(m, 1.35, 0.4) @ R(math.pi / 2, "X"))   # a clipped hedge ball
    bm_box(P["wall"], 0, w, -0.02, 0, 0, cor)                        # the wall face itself (bent along the curve)
    bm_box(P["trim"], 0.05, 0.35, 0.0, 0.18, 0, cor)                  # quoins at each bay edge
    bm_box(P["trim"], w - 0.35, w - 0.05, 0.0, 0.18, 0, cor)
    if not plain and w >= 3.0:
        # the rooms' relief (photos): a pier 0.55 m proud between the bays from the first floor to the cornice, so the
        # windows and balconies sit in a recess; a cap on each pier at every floor, a bracket block under the cornice
        pw = min(0.6, w * 0.14)
        for x0, x1 in ((0.0, pw), (w - pw, w)):
            bm_box(P["wall"], x0, x1, 0.0, 0.55, GF - 0.2, cor - 0.4)
            for f in range(nfl + 1):
                zc = GF + FH * f - 0.12
                bm_box(P["trim"], x0 - 0.03, x1 + 0.03, 0.0, 0.6, zc, zc + 0.14)
            bm_box(P["trim"], x0 - 0.06, x1 + 0.06, 0.0, 0.66, cor - 0.75, cor - 0.25)
    for k in range(1, int(cor / 1.0)):                                # rustication: horizontal joint lines, ground floor
        if k * 1.0 < GF - 0.6:
            bm_box(P["trim"], 0.35, w - 0.35, 0.0, 0.05, k * 1.0, k * 1.0 + 0.04)
    if not plain:
        bm_prism(P["trim"], arch_opening(m - 1.15, m + 1.15, GF - 4.35, GF - 0.55, 0.85, 14), 0.0, 0.15, "xz")   # ground floor
        bm_prism(P["glass"], arch_opening(m - 0.95, m + 0.95, GF - 4.15, GF - 0.7, 0.68, 12), 0.15, 0.18, "xz")
        bm_prism(P["trim"], arch_band(m - 1.15, m + 1.15, GF - 0.55, 0.85, 0.18, 14, leg=0.15), 0.14, 0.3, "xz")   # arch moulding + keystone
        bm_box(P["trim"], m - 0.12, m + 0.12, 0.14, 0.32, GF + 0.15, GF + 0.5)
        sconce(P["iron"], P["lamp"], m - 1.7, 0.16, GF - 2.4); sconce(P["iron"], P["lamp"], m + 1.7, 0.16, GF - 2.4)
        bm_box(P["trim"], m - 1.3, m + 1.3, 0.0, 0.2, GF - 0.55, GF - 0.2)    # string course under the upper floors
        for f in range(nfl):
            z0 = GF + FH * f + 0.55
            paired_window(P["trim"], P["glass"], P["rail"], m, 2.0, z0, z0 + 1.85, balcony=True)
            bm_box(P["trim"], m - 1.15, m + 1.15, 0.0, 0.14, GF + FH * (f + 1) - 0.12, GF + FH * (f + 1) + 0.05)
    bm_box(P["trim"], -0.05, w + 0.05, -0.1, 0.28, cor - 0.4, cor - 0.25)   # a plain dentil cornice band
    for k in range(int(w / 0.5)):
        xx = k * 0.5 + 0.25
        bm_box(P["trim"], xx - 0.1, xx + 0.1, 0.0, 0.22, cor - 0.25, cor - 0.1)
    baluster_run(P["trim"], P["rail"], (0.0, 0.32), (w, 0.32), cor, eave)   # a turned-baluster balustrade at the roofline
    # the mansard: an open face sloping back from the wall (no end caps, so Array copies never share a coincident face)
    # then a short flat deck; gold cresting along the ridge line where the slope meets the deck
    V = lambda x, y, z: P["slate"].verts.new((x, y, z))
    a0, b0 = V(0, 0.0, eave), V(w, 0.0, eave)
    a1, b1 = V(0, -MANSARD_D, ridge), V(w, -MANSARD_D, ridge)
    P["slate"].faces.new((a0, b0, b1, a1))
    a2, b2 = V(0, -MANSARD_D - DECK_D, ridge), V(w, -MANSARD_D - DECK_D, ridge)
    P["slate"].faces.new((a1, b1, b2, a2))
    bm_lathe(P["gold"], [(0, 0), (0.025, 0), (0.02, 0.16), (0.05, 0.2), (0, 0.28)], 6, T(m, -MANSARD_D, ridge))
    obj = {}
    for k, bm in P.items():
        if not len(bm.verts):
            bm.free(); continue
        mat = {"wall": "h_cream", "trim": "h_gold_trim", "glass": "h_win_dark", "iron": "h_iron",
               "slate": "h_slate", "gold": "h_gold", "lamp": "h_lamp", "leaf": "h_leaf", "rail": "h_white"}[k]
        o = obj_bm(f"HT_{tag}_{k}", bm, mat, smooth=(k in ("gold", "lamp", "leaf")), recalc=(k != "slate"))
        array_mod(o, N, (w, 0, 0))
        obj[k] = o
    return obj


def crescent_dormers(w, N, nfl=NFLOORS, tag="crescent"):
    """Round dormers on every other bay, sitting on the mansard's slope."""
    bm_wall, bm_glass, bm_trim = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(N):
        if k % 2 == 0:
            dormer(bm_wall, bm_glass, bm_trim, k * w + w / 2, dz=FH * (nfl - NFLOORS))
    o1 = obj_bm(f"HT_{tag}_dormer_wall", bm_wall, "h_cream")
    o2 = obj_bm(f"HT_{tag}_dormer_glass", bm_glass, "h_win_dark")
    o3 = obj_bm(f"HT_{tag}_dormer_trim", bm_trim, "h_gold_trim")
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


VIC_GF, VIC_FH, VIC_FLOORS = 4.4, 3.0, 4                 # the low Victorian wings


def victorian_run(name, L, wall, trim):
    """One run of a Victorian wing's facade (x 0..L, +y out): bays of about 4.2 m -- an arched ground-floor window and
    fretwork brackets; an oriel over the upper floors and a front gable with a round window on every other bay, paired
    windows on the rest; string courses, a cornice, the roof sloping back from the wall."""
    gf, fh = VIC_GF, VIC_FH; H = gf + fh * (VIC_FLOORS - 1)
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "slate", "gold", "lamp")}
    bm_box(P["wall"], 0, L, -0.02, 0, -0.5, H)
    nb = max(1, round(L / 4.2)) if L >= 2.8 else 0; bw = L / nb if nb else L
    for k in range(nb):
        x0, x1 = k * bw, (k + 1) * bw; m = (x0 + x1) / 2
        bm_box(P["trim"], x0, x0 + 0.3, 0, 0.15, 0, H)                            # pilasters
        bm_prism(P["trim"], arch_opening(m - 1.2, m + 1.2, 0.0, gf - 1.4, 0.9, 12), 0.0, 0.12, "xz")
        bm_prism(P["glass"], arch_opening(m - 1.0, m + 1.0, 0.15, gf - 1.5, 0.75, 10), 0.12, 0.15, "xz")
        for fx in (m - 1.25, m + 1.25):                    # fretwork brackets under the first floor
            bm_prism(P["trim"], [(fx - 0.1, gf - 0.6), (fx + 0.1, gf - 0.6), (fx + 0.1, gf), (fx - 0.1, gf)], 0.0, 0.5, "xz")
        globe_lamp_bm(P["lamp"], m - 1.55, 0.35, 2.6, 0.11)
        if k % 2 == 0:                                     # an oriel over the upper floors, a gable over it
            bm_prism(P["wall"], [(m - 1.4, 0.0), (m + 1.4, 0.0), (m + 0.9, 0.8), (m - 0.9, 0.8)], gf, H - 0.4, "xy")
            bm_prism(P["trim"], [(m - 1.5, 0.0), (m + 1.5, 0.0), (m + 0.95, 0.9), (m - 0.95, 0.9)], gf - 0.2, gf, "xy")
            for f in range(VIC_FLOORS - 1):
                z0 = gf + fh * f + 0.6
                bm_box(P["glass"], m - 0.7, m + 0.7, 0.8, 0.82, z0, z0 + 1.7)
                bm_box(P["trim"], m - 0.75, m + 0.75, 0.8, 0.86, z0 + 1.7, z0 + 1.85)
            bm_prism(P["wall"], [(m - 1.6, H), (m + 1.6, H), (m, H + 3.2)], -1.5, 0.2, "xz")
            bm_prism(P["trim"], [(m - 1.8, H - 0.1), (m, H + 3.45), (m, H + 3.65), (m - 1.95, H + 0.1)], -1.6, 0.3, "xz")
            bm_prism(P["trim"], [(m + 1.8, H - 0.1), (m + 1.95, H + 0.1), (m, H + 3.65), (m, H + 3.45)], -1.6, 0.3, "xz")
            bm_lathe(P["glass"], [(0, 0), (0.4, 0), (0.4, 0.04), (0, 0.04)], 16, T(m, 0.22, H + 1.2) @ R(-math.pi / 2, "X"))
            bm_lathe(P["gold"], [(0, 0), (0.08, 0), (0.05, 0.5), (0.1, 0.6), (0, 1.0)], 8, T(m, 0.0, H + 3.6))
        else:
            for f in range(VIC_FLOORS - 1):
                z0 = gf + fh * f + 0.6
                for dx in (-0.65, 0.65):
                    bm_box(P["trim"], m + dx - 0.45, m + dx + 0.45, 0.0, 0.1, z0 - 0.1, z0 + 1.9)
                    bm_box(P["glass"], m + dx - 0.35, m + dx + 0.35, 0.1, 0.12, z0, z0 + 1.8)
        for f in range(VIC_FLOORS - 1):                    # string courses (the half-timber bands on the purple wing)
            bm_box(P["trim"], x0, x1, 0.0, 0.12, gf + fh * f - 0.08, gf + fh * f + 0.06)
    bm_box(P["trim"], -0.1, L + 0.1, 0.0, 0.5, H - 0.4, H)                         # cornice
    V = lambda x, y, z: P["slate"].verts.new((x, y, z))                             # the roof, back from the wall
    a, b_, c, d = V(0, 0.5, H), V(L, 0.5, H), V(L, -3.2, H + 3.6), V(0, -3.2, H + 3.6)
    P["slate"].faces.new((a, b_, c, d))
    for k, bm_ in P.items():
        if not len(bm_.verts):
            bm_.free(); continue
        mat = {"wall": wall, "trim": trim, "glass": "h_win_dark", "slate": "h_slate", "gold": "h_gold", "lamp": "h_lamp"}[k]
        obj_bm(f"HT_{name}_{k}", bm_, mat, smooth=(k in ("gold", "lamp")), recalc=(k != "slate"))


def facade_runs(name, ring, run):
    """run(L, i) for each edge of a clockwise ring, in a frame at the edge's start turned along it (its +y: outside)."""
    for i in range(len(ring)):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % len(ring)]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 0.3:
            continue
        with frame(f"HT_{name}_run{i}", x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0))):
            run(L, i)


def build_victorian(name, wall, trim):
    part = PLAN["parts"][name]
    facade_runs(name, part["ring"], lambda L, i: victorian_run(f"{name}_{i}", L, wall, trim))
    H = VIC_GF + VIC_FH * (VIC_FLOORS - 1)
    prism(f"HT_{name}_roofdeck", part["roof"], H + 3.4, H + 3.6, "h_slate")


def entrance_pavilion(x, y, ang_deg):
    """The main block at the head of the court (photos): 26 m wide, projecting 3 m, three tall arched windows over the
    entrance (the middle one the tallest, with a fan of glazing bars), paired pilasters, balconied floors above, a
    balustraded attic, and the gold dome on an octagonal drum with a lantern. Faces +y at x on the curve."""
    with frame("HT_pavilion", x, y, ang_deg):
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
        text("HT_pav_plaque", "TOKYO DISNEYLAND HOTEL", 0.3, (0, d + 0.25, GF - 0.5), (math.pi / 2, 0, math.pi), "h_bronze", 0.015)
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
        gazebo(0.0, 7.0)


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


def build_main():
    """The main building: the same facade run round its whole outline (bays of about 5 m, a plain piece of wall on the
    short kinks), and the roof deck inside the mansards."""
    pe = porte_edge()
    def run(L, i):
        if L < 3.2:
            crescent_bay(L, 1, plain=True)
        else:
            n = max(1, round(L / 5.0)); w = L / n
            crescent_bay(w, n, kerb=(i != pe)); crescent_dormers(w, n)
            window_fill(f"main_{i}", n, w, NFLOORS, i)
            if i == pe:
                porte_cochere(L, w, n)
            elif L >= 30.0:
                pediment(f"main_{i}", L / 2 if n % 2 else L / 2 + w / 2, min(w * 0.9, 5.0) if n % 2 else min(w, 5.5))
    facade_runs("main", PLAN["parts"]["main"]["ring"], run)
    prism("HT_main_roofdeck", PLAN["parts"]["main"]["roof"], RIDGE - 0.25, RIDGE, "h_slate")


def build_front():
    """The front court (its own frame): the main block and the gazebo at its head, the two towers where the wings end,
    and the court itself (the dais, the planters, the gates)."""
    with frame("HT_court", COURT["x"], COURT["y"], COURT["ang"]):
        entrance_pavilion(0.0, 0.0, 0.0)
        corner_tower(26.5, 25.5, "west")
        corner_tower(-24.5, 17.5, "east")
        build_court()


# ================================================================ 2. the rooms' windows, the long back runs, the north-east block
def quad(bm, x0, x1, y, z0, z1):
    """A flat panel facing +y (a curtain, a pelmet): one face, the mock draws both sides."""
    v = [bm.verts.new(c) for c in ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))]
    bm.faces.new(v)


def window_fill(tag, n, w, nfl, seed):
    """Curtains and lights behind the paired windows of a run of n bays (crescent_bay's windows, not arrayed so every
    window differs): each light has its curtains open, half drawn or closed, and a pelmet; about one in ten rooms is lit,
    and about a third of the ground-floor arches (the lobby, the restaurants). ESTIMATE: the mix is made up."""
    rnd = random.Random(seed)
    cur, lit = bmesh.new(), bmesh.new()
    lw = 0.78                                              # paired_window(w=2.0): each light 0.78 wide at m +- 0.48
    for k in range(n):
        m = k * w + w / 2
        if rnd.random() < 0.35:
            bm_prism(lit, arch_opening(m - 0.93, m + 0.93, GF - 4.13, GF - 0.72, 0.66, 12), 0.15, 0.2, "xz")
        for f in range(nfl):
            z0 = GF + FH * f + 0.55; top = z0 + 1.85 - lw / 2
            for dx in (-0.48, 0.48):
                x0, x1 = m + dx - lw / 2 + 0.03, m + dx + lw / 2 - 0.03
                on = rnd.random() < 0.1
                if on:
                    bm_prism(lit, arch_opening(x0, x1, z0 + 0.02, top, lw / 2 - 0.03, 10), 0.12, 0.16, "xz")
                r = rnd.random()
                cw = 0.1 if (r < 0.5 or on) else (0.2 if r < 0.85 else (x1 - x0) / 2)
                quad(cur, x0, x0 + cw, 0.17, z0 + 0.04, top); quad(cur, x1 - cw, x1, 0.17, z0 + 0.04, top)
                quad(cur, x0, x1, 0.175, top - 0.16, top)
    obj_bm(f"HT_{tag}_curtains", cur, "h_curtain", recalc=False)
    if len(lit.verts):
        obj_bm(f"HT_{tag}_lit", lit, "h_win_lit")
    else:
        lit.free()


def pediment(tag, x, hw):
    """A pediment over the middle of a long run (the back wings: breaks up 40-60 m of the same bay): a tympanum with an
    oculus on the cornice, raking cornices, a gold finial and urns. ESTIMATE: not in any photo."""
    hh = hw * 0.42; z = CORNICE
    bw, bt, bg, bs = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    bm_prism(bw, [(x - hw, z), (x + hw, z), (x, z + hh)], -0.6, 0.4, "xz")
    for s_ in (-1, 1):
        bm_prism(bt, [(x + s_ * (hw + 0.25), z - 0.05), (x + s_ * (hw + 0.25), z + 0.2), (x, z + hh + 0.35), (x, z + hh + 0.1)], -0.7, 0.55, "xz")
        bm_lathe(bs, [(0, 0), (0.22, 0), (0.14, 0.15), (0.3, 0.45), (0.12, 0.8), (0, 0.9)], 10, T(x + s_ * hw, 0.1, z + 0.1))
    bm_box(bt, x - hw - 0.3, x + hw + 0.3, -0.7, 0.55, z - 0.25, z + 0.05)
    bm_lathe(bg, [(0, 0), (0.62, 0), (0.62, 0.05), (0, 0.05)], 20, T(x, 0.42, z + hh * 0.42) @ R(-math.pi / 2, "X"))
    bm_lathe(bt, [(0.62, 0), (0.8, 0), (0.8, 0.1), (0.62, 0.1)], 20, T(x, 0.4, z + hh * 0.42) @ R(-math.pi / 2, "X"))
    bm_lathe(bs, [(0, 0), (0.1, 0), (0.06, 0.6), (0.16, 0.75), (0, 1.3)], 8, T(x, 0.2, z + hh + 0.3))
    obj_bm(f"HT_pediment_{tag}_wall", bw, "h_cream"); obj_bm(f"HT_pediment_{tag}_trim", bt, "h_gold_trim")
    obj_bm(f"HT_pediment_{tag}_glass", bg, "h_win_dark"); obj_bm(f"HT_pediment_{tag}_gold", bs, "h_gold", smooth=True)


NGW_FLOORS = 15                                             # 5 + 15 x 3.2 = 53 m to the cornice, 58.5 m to the mansard's ridge


def build_ngw():
    """The tall block to the north-east (OSM's 60 m): the court wings' facade 15 floors high -- the same bays, piers and
    dormered mansard, balconies on every other floor, a heavier band every fourth floor, and a slate penthouse on the
    roof. ESTIMATE: no photo; built as "the same family, taller"."""
    part = PLAN["parts"]["ngw"]
    def run(L, i):
        if L < 3.2:
            crescent_bay(L, 1, plain=True, nfl=NGW_FLOORS, tag="ngw")
            return
        n = max(1, round(L / 5.0)); w = L / n
        crescent_bay(w, n, nfl=NGW_FLOORS, tag="ngw", balcony=lambda f: f % 2 == 1, belt=4)
        crescent_dormers(w, n, nfl=NGW_FLOORS, tag="ngw")
        window_fill(f"ngw_{i}", n, w, NGW_FLOORS, 1000 + i)
    facade_runs("ngw", part["ring"], run)
    ridge = RIDGE + FH * (NGW_FLOORS - NFLOORS)
    prism("HT_ngw_roofdeck", part["roof"], ridge - 0.25, ridge, "h_slate")
    pts = part["ring"]; cx, cy = sum(x for x, y in pts) / len(pts), sum(y for x, y in pts) / len(pts)
    prism("HT_ngw_penthouse", [[(cx + (x - cx) * 0.5, cy + (y - cy) * 0.5) for x, y in pts]], ridge - 0.25, ridge + 3.0, "h_slate")


# ================================================================ 3. the north side: the porte-cochere, the gatehouse in the loop
PORTE_MID = (16.06, 1.08)             # the middle of the wall the one-way loop road (OSM 659558364) passes nearest, 13-20 m out


def porte_edge():
    ring = PLAN["parts"]["main"]["ring"]
    for i in range(len(ring)):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % len(ring)]
        if math.hypot((x0 + x1) / 2 - PORTE_MID[0], (y0 + y1) / 2 - PORTE_MID[1]) < 3.0:
            return i
    return -1


def porte_cochere(L, w, n):
    """The north entrance (in the wall's frame, x 0..L along it, +y out over the drive): an iron-and-glass canopy
    14 m wide reaching 15 m over the loop road, on cast-iron columns; a lettered fascia with a lace valance, a gable with
    a clock, lanterns hanging under the glass, a paved floor with a rosette, glazed doors in the arches behind.
    ESTIMATE: sizes, the design (no photo of this side)."""
    xc, hw, y1 = L / 2, 7.0, 15.3
    zf0, zf1, zr = 5.5, 6.5, 8.9
    P = {k: bmesh.new() for k in ("iron", "white", "glass", "cream", "gold", "lamp", "floor", "door", "clock")}
    bm_box(P["floor"], xc - hw - 0.5, xc + hw + 0.5, 0.3, y1 + 0.3, -1.3, 0.06)       # deep: the ground slopes under it (mock)
    cols = [(xc + s_ * 6.6, y1 - 0.35) for s_ in (-1, 1)] + [(xc + s_ * 2.4, y1 - 0.35) for s_ in (-1, 1)] + \
           [(xc + s_ * 6.6, 7.6) for s_ in (-1, 1)]
    for x, y in cols:
        bm_lathe(P["iron"], [(0, -1.3), (0.34, -1.3), (0.34, 0.25), (0.22, 0.45), (0.2, 0.8), (0.15, 0.95), (0.13, zf0 - 0.6),
                             (0.2, zf0 - 0.45), (0.3, zf0 - 0.2), (0.34, zf0), (0, zf0)], 12, T(x, y, 0.0))
        for ca in (-1, 1):                                 # lace brackets from the column to the beam
            bm_prism(P["iron"], [(x + ca * 0.15, zf0 - 1.4), (x + ca * 0.18, zf0), (x + ca * 1.2, zf0)], y - 0.03, y + 0.03, "xz")
    bm_box(P["white"], xc - hw - 0.2, xc + hw + 0.2, y1 - 0.5, y1 + 0.1, zf0, zf1)            # the fascia, three sides
    for s_ in (-1, 1):
        bm_box(P["white"], xc + s_ * hw - 0.25, xc + s_ * hw + 0.25, 0.3, y1 + 0.1, zf0, zf1)
    bm_box(P["iron"], xc - hw, xc + hw, 7.45, 7.75, zf0 + 0.2, zf1 - 0.1)                     # a cross beam over the middle columns
    bm_box(P["gold"], xc - hw - 0.25, xc + hw + 0.25, y1 + 0.1, y1 + 0.14, zf1 - 0.12, zf1 - 0.06)
    for k in range(int(2 * (hw + 0.2) / 0.32)):             # the lace valance under the fascia
        x = xc - hw - 0.2 + 0.16 + k * 0.32
        bm_prism(P["white"], [(x - 0.14, zf0), (x + 0.14, zf0), (x, zf0 - 0.28)], y1 + 0.02, y1 + 0.06, "xz")
    for s_ in (-1, 1):
        for k in range(int(y1 / 0.32)):
            y = 0.5 + k * 0.32
            bm_prism(P["white"], [(y - 0.14, zf0), (y + 0.14, zf0), (y, zf0 - 0.28)], xc + s_ * (hw + 0.2) - 0.02, xc + s_ * (hw + 0.2) + 0.02, "yz")
    V = lambda bm, x, y, z: bm.verts.new((x, y, z))           # the glass roof: two slopes up to a ridge running out from the wall
    for s_ in (-1, 1):
        g = P["glass"]
        g.faces.new((V(g, xc + s_ * hw, 0.3, zf1), V(g, xc + s_ * hw, y1, zf1), V(g, xc, y1, zr), V(g, xc, 0.3, zr)))
        for k in range(int((y1 - 0.3) / 1.5) + 1):         # iron ribs over the glass
            y = 0.3 + k * 1.5
            bm_prism(P["iron"], [(xc + s_ * hw, zf1), (xc + s_ * hw, zf1 + 0.1), (xc, zr + 0.1), (xc, zr)], y - 0.04, y + 0.04, "xz")
    bm_box(P["iron"], xc - 0.08, xc + 0.08, 0.3, y1, zr - 0.05, zr + 0.2)
    bm_prism(P["cream"], [(xc - hw - 0.1, zf1), (xc + hw + 0.1, zf1), (xc, zr + 0.2)], y1 - 0.2, y1 + 0.05, "xz")   # the front gable
    bm_prism(P["white"], [(xc - hw - 0.4, zf1 - 0.05), (xc - hw - 0.4, zf1 + 0.2), (xc, zr + 0.5), (xc, zr + 0.25)], y1 - 0.25, y1 + 0.15, "xz")
    bm_prism(P["white"], [(xc + hw + 0.4, zf1 - 0.05), (xc, zr + 0.25), (xc, zr + 0.5), (xc + hw + 0.4, zf1 + 0.2)], y1 - 0.25, y1 + 0.15, "xz")
    bm_lathe(P["clock"], [(0, 0), (0.62, 0), (0.62, 0.04), (0, 0.04)], 24, T(xc, y1 + 0.05, 7.55) @ R(-math.pi / 2, "X"))
    bm_lathe(P["gold"], [(0.62, 0), (0.78, 0), (0.78, 0.08), (0.62, 0.08)], 24, T(xc, y1 + 0.05, 7.55) @ R(-math.pi / 2, "X"))
    bm_box(P["iron"], xc - 0.03, xc + 0.03, y1 + 0.1, y1 + 0.12, 7.55, 7.95)             # the hands (ten past ten)
    bm_prism(P["iron"], [(xc, 7.52), (xc + 0.4, 7.72), (xc + 0.4, 7.78), (xc, 7.58)], y1 + 0.1, y1 + 0.12, "xz")
    bm_lathe(P["gold"], [(0, 0), (0.1, 0), (0.06, 0.5), (0.18, 0.62), (0, 1.1)], 8, T(xc, y1 - 0.1, zr + 0.45))
    for x, y in ((xc - 3.5, 4.5), (xc + 3.5, 4.5), (xc - 3.5, 11.0), (xc + 3.5, 11.0)):   # lanterns on rods under the glass
        bm_box(P["iron"], x - 0.02, x + 0.02, y - 0.02, y + 0.02, 4.9, zf1 + (zr - zf1) * (1 - abs(x - xc) / hw))
        globe_lamp_bm(P["lamp"], x, y, 4.7, 0.22)
    for k in range(n):                                      # glazed doors in the arches under the canopy
        m = k * w + w / 2
        if abs(m - xc) > hw - 1.0:
            continue
        bm_box(P["white"], m - 1.0, m + 1.0, 0.16, 0.3, 0.0, 3.2)
        bm_box(P["door"], m - 0.85, m + 0.85, 0.3, 0.33, 0.06, 3.05)
        bm_box(P["white"], m - 0.04, m + 0.04, 0.3, 0.36, 0.06, 3.05)
        bm_box(P["gold"], m - 0.12, m - 0.08, 0.36, 0.42, 1.0, 1.6); bm_box(P["gold"], m + 0.08, m + 0.12, 0.36, 0.42, 1.0, 1.6)
    mats = {"iron": "h_iron", "white": "h_white", "glass": "h_glass", "cream": "h_cream", "gold": "h_gold", "lamp": "h_lamp",
            "floor": "h_paving2", "door": "h_win_dark", "clock": "h_clockface"}
    for k, bm_ in P.items():
        obj_bm(f"HT_porte_{k}", bm_, mats[k], smooth=(k in ("lamp", "gold")), recalc=(k != "glass"))
    r1, r2 = rosette(xc, 8.0, 0.8, 3.2, 12, z=0.06)
    obj_bm("HT_porte_rosette1", r1, "h_paving1"); obj_bm("HT_porte_rosette2", r2, "h_paving2")
    text("HT_porte_letters", "TOKYO DISNEYLAND HOTEL", 0.5, (xc, y1 + 0.12, (zf0 + zf1) / 2), (math.pi / 2, 0, math.pi), "h_letters", 0.03)


def gatehouse():
    """The little building in the middle of the loop road (OSM 788764389, 3.6 x 3.2 m): a gatehouse -- cream walls,
    windows all round, a slate pyramid roof with a finial, a clipped hedge round it. ESTIMATE: all but the footprint."""
    cx, cy, hx, hy, h = 26.75, 64.85, 1.8, 1.6, 2.9
    P = {k: bmesh.new() for k in ("cream", "white", "glass", "slate", "gold", "leaf")}
    bm_box(P["cream"], cx - hx, cx + hx, cy - hy, cy + hy, -1.0, h)
    bm_box(P["white"], cx - hx - 0.08, cx + hx + 0.08, cy - hy - 0.08, cy + hy + 0.08, h - 0.3, h)
    bm_box(P["white"], cx - hx - 0.05, cx + hx + 0.05, cy - hy - 0.05, cy + hy + 0.05, -1.0, 0.35)
    for s_ in (-1, 1):
        bm_box(P["glass"], cx - hx + 0.4, cx + hx - 0.4, cy + s_ * hy - 0.03, cy + s_ * hy + 0.03, 1.0, 2.3)
        bm_box(P["glass"], cx + s_ * hx - 0.03, cx + s_ * hx + 0.03, cy - hy + 0.4, cy + hy - 0.4, 1.0, 2.3)
    V = lambda x, y, z: P["slate"].verts.new((x, y, z))
    c = [V(cx - hx - 0.35, cy - hy - 0.35, h), V(cx + hx + 0.35, cy - hy - 0.35, h), V(cx + hx + 0.35, cy + hy + 0.35, h),
         V(cx - hx - 0.35, cy + hy + 0.35, h)]
    top = V(cx, cy, h + 2.0)
    for i in range(4):
        P["slate"].faces.new((c[i], c[(i + 1) % 4], top))
    P["slate"].faces.new(c[::-1])
    bm_lathe(P["gold"], [(0, 0), (0.08, 0), (0.05, 0.4), (0.12, 0.5), (0, 0.9)], 8, T(cx, cy, h + 1.95))
    ax, ay, bx, by = hx + 0.9, hy + 0.9, hx + 1.2, hy + 1.2   # the hedge: a square ring 0.9-1.2 m out from the walls
    for x0, x1, y0, y1 in ((-bx, bx, -by, -ay), (-bx, bx, ay, by), (-bx, -ax, -ay, ay), (ax, bx, -ay, ay)):
        bm_box(P["leaf"], cx + x0, cx + x1, cy + y0, cy + y1, -1.0, 0.7)
    mats = {"cream": "h_cream", "white": "h_white", "glass": "h_win_dark", "slate": "h_slate", "gold": "h_gold", "leaf": "h_leaf"}
    for k, bm_ in P.items():
        obj_bm(f"HT_booth_{k}", bm_, mats[k], smooth=(k == "gold"))


def build_plinth():
    """Stone plinth under the whole outline, 5 m deep: the ground round the building is not level."""
    prism("HT_plinth", [PLAN["footprint"]], -5.0, 0.02, "h_paving2")


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
    box("HT_court_ground", (-24, 24, 0.5, 34, -0.02, 0.0), "h_paving2")
    cx, cy = 0.0, COURT["garden"]
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
        px, py = cx + s_ * 12.8, cy
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
    gy, gw = cy + 11.0, 3.4                              # the gates across the court's mouth, between the towers
    posts = [(-gw - 0.5, gy), (gw + 0.5, gy), (-12.0, gy), (12.0, gy), (-19.0, gy), (20.0, gy)]
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
    for x0_, x1_ in ((-12.0, -gw - 0.5), (gw + 0.5, 12.0), (-19.0, -12.0), (12.0, 20.0)):
        baluster_run(bmt, bmbal, (x0_ + 0.55, gy), (x1_ - 0.55, gy), 0.0, 1.1)
    obj_bm("HT_gate_posts", bmp, "h_stone"); obj_bm("HT_gate_urns", bmu, "h_stone", smooth=True)
    obj_bm("HT_gate_bars", bmg, "h_iron"); obj_bm("HT_gate_balustrade", bmt, "h_stone"); obj_bm("HT_gate_balusters", bmbal, "h_white")
    # smaller brick planters with Mickey / spiral topiary along the foot of the crescent
    bmb, bmh, bmd = bmesh.new(), bmesh.new(), bmesh.new()
    for i_, (x, y) in enumerate([(-16.0, 5.0), (16.0, 5.0), (-17.0, 11.0), (17.5, 11.0)]):
        r = 1.5
        bm_lathe(bmb, [(0, 0), (r, 0), (r, 0.9), (r - 0.15, 1.0), (r - 0.15, 1.15), (r, 1.25), (r, 1.4), (0, 1.4)], 20, T(x, y, 0))
        mickey_topiary(bmh, x, y, 1.4) if i_ % 2 == 0 else spiral_topiary(bmh, x, y, 1.4)
    obj_bm("HT_planters_small", bmb, "h_brick"); obj_bm("HT_topiary_small", bmh, "h_leaf", smooth=True)
    # lamp posts flanking the drive
    bmp, bml = bmesh.new(), bmesh.new()
    for x, y in ((-8.0, cy + 13.5), (8.0, cy + 13.5), (-15.5, cy + 6.0), (16.0, cy + 6.0)):
        bm_lathe(bmp, [(0, 0), (0.28, 0), (0.28, 0.4), (0.16, 0.6), (0.1, 4.6), (0.16, 4.7), (0.08, 4.9), (0, 4.9)], 14, T(x, y, 0.0))
        for a in range(4):
            aa = a * math.pi / 2 + math.pi / 4
            globe_lamp_bm(bml, x + 0.35 * math.cos(aa), y + 0.35 * math.sin(aa), 5.0, 0.16)
        globe_lamp_bm(bml, x, y, 5.35, 0.2)
    obj_bm("HT_lampposts", bmp, "h_iron", smooth=True); obj_bm("HT_lamp_globes", bml, "h_lamp", smooth=True)
    court_beds(cx, cy)


def flower_bed(bms, bml, bmf, x0, x1, y0, y1, rnd):
    """A raised bed: a stone kerb, a clipped box hedge along its outer edge, flowers in clumps (purple / pink / white)."""
    bm_box(bms, x0, x1, y0, y1, 0.0, 0.32)
    bm_box(bml, x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.05, 0.32, 0.4)            # the soil's green cover
    hx = x1 - x0 > y1 - y0
    for s_ in (0, 1):                                      # the hedges at the bed's two long edges
        if hx:
            yy = y0 + 0.08 if s_ == 0 else y1 - 0.38
            bm_box(bml, x0 + 0.08, x1 - 0.08, yy, yy + 0.3, 0.32, 0.72)
        else:
            xx = x0 + 0.08 if s_ == 0 else x1 - 0.38
            bm_box(bml, xx, xx + 0.3, y0 + 0.08, y1 - 0.08, 0.32, 0.72)
    ax0, ax1 = (x0 + 0.5, x1 - 0.5) if not hx else (x0 + 0.3, x1 - 0.3)
    ay0, ay1 = (y0 + 0.5, y1 - 0.5) if hx else (y0 + 0.3, y1 - 0.3)
    nx, ny = max(1, int((ax1 - ax0) / 0.32)), max(1, int((ay1 - ay0) / 0.32))
    for i in range(nx):
        for j in range(ny):
            x = ax0 + (i + 0.5) * (ax1 - ax0) / nx + rnd.uniform(-0.05, 0.05)
            y = ay0 + (j + 0.5) * (ay1 - ay0) / ny + rnd.uniform(-0.05, 0.05)
            r = rnd.uniform(0.12, 0.17)
            bm_lathe(bmf[rnd.choice((0, 0, 1, 2))], [(0, -r * 0.6), (r, 0), (0, r * 0.6)], 6, T(x, y, 0.42))


def court_beds(cx, cy):
    """The court's smaller planting (ESTIMATE: the photos show beds and box hedging along the wings, not their plan):
    raised beds along the two wing walls, a ring of flowers round each great planter, iron benches inside the gates."""
    rnd = random.Random(7)
    bms, bml = bmesh.new(), bmesh.new()
    bmf = [bmesh.new() for _ in range(3)]
    flower_bed(bms, bml, bmf, -21.2, -19.6, 2.5, 10.5, rnd)       # along the east wing (the wall at x -21.4)
    flower_bed(bms, bml, bmf, 19.3, 20.9, 10.0, 18.0, rnd)        # along the west wing (the wall at x 21.0)
    for s_ in (-1, 1):                                             # round the great planters
        px, py = cx + s_ * 12.8, cy
        bm_lathe(bms, [(2.85, 0), (3.5, 0), (3.5, 0.25), (3.35, 0.25), (3.35, 0.12), (2.85, 0.12)], 40, T(px, py, 0))
        for k in range(36):
            a = 2 * math.pi * k / 36; rr = 3.1 + rnd.uniform(-0.08, 0.08); r = rnd.uniform(0.13, 0.18)
            bm_lathe(bmf[k % 3 if k % 3 else 0], [(0, -r * 0.6), (r, 0), (0, r * 0.6)], 6,
                     T(px + rr * math.cos(a), py + rr * math.sin(a), 0.2))
    obj_bm("HT_court_bed_kerbs", bms, "h_stone"); obj_bm("HT_court_bed_hedges", bml, "h_leaf")
    for bm_, mat in zip(bmf, ("h_flower_purple", "h_flower_pink", "h_flower_white")):
        obj_bm(f"HT_court_flowers_{mat[9:]}", bm_, mat, smooth=True)
    bmi, bmw = bmesh.new(), bmesh.new()                            # two iron benches inside the gates, facing the dais
    for s_ in (-1, 1):
        x, y0, y1 = s_ * 17.3, 27.4, 29.2
        for yy in (y0 + 0.1, y1 - 0.1):
            bm_box(bmi, x - 0.3, x + 0.3, yy - 0.04, yy + 0.04, 0.0, 0.45)
            bm_prism(bmi, [(x + s_ * 0.3, 0.45), (x + s_ * 0.38, 0.45), (x + s_ * 0.48, 0.95), (x + s_ * 0.4, 0.95)], yy - 0.04, yy + 0.04, "xz")
        for k in range(4):                                         # the seat's slats and the back's
            xx = x - 0.28 + k * 0.15
            bm_box(bmw, xx, xx + 0.11, y0, y1, 0.42, 0.46)
        for k in range(3):
            zz = 0.55 + k * 0.13
            xx = x + s_ * (0.35 + (zz - 0.45) * 0.2)
            bm_box(bmw, xx - 0.02, xx + 0.02, y0, y1, zz, zz + 0.09)
    obj_bm("HT_court_bench_iron", bmi, "h_iron"); obj_bm("HT_court_bench_wood", bmw, "h_wood")


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
    """One mesh per material ("HO_<material>") in the mock's frame. The building stands on the court's ground by its head wall;
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
        Mw = cg.matrix_world.copy()
        bm = bmesh.new(); step = 1.5
        nx, ny = int(48 / step) + 1, int(34 / step) + 1
        vs = []
        for j in range(ny):
            for i in range(nx):
                x, y = -24.0 + i * step, 0.5 + j * step
                wp = Mw @ Vector((x, y, 0.0))
                vs.append(bm.verts.new((x, y, g(wp.x, wp.y) + 0.02)))
        for j in range(ny - 1):
            for i in range(nx - 1):
                a = j * nx + i
                bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
        bm.normal_update()
        me = bpy.data.meshes.new("HT_court_ground"); bm.to_mesh(me); bm.free()
        me.materials.append(cg.data.materials[0]); cg.data = me
    hc = bpy.data.objects["HT_court"].matrix_world @ Vector((0.0, 4.0, 0.0))
    building_z = g(hc.x, hc.y)                           # the building stands on the court's ground by its head wall
    print(f"[hotel] building level {building_z:.2f} m")
    court = ("HT_court_", "HT_gate", "HT_planter", "HT_topiary", "HT_steps", "HT_fountain", "HT_lamp", "HT_rail", "HT_gazebo")
    def top_of(name):                                       # the highest ground under an object: it stands on that, the
        o = bpy.data.objects[name]                           # rest goes down into the slope (its base is deep)
        return max(g(p.x, p.y) for p in (o.matrix_world @ v.co for v in o.data.vertices))
    porte_z, booth_z = top_of("HT_porte_floor"), top_of("HT_booth_cream")   # the north side, on the slope up from the loop road
    print(f"[hotel] porte-cochere level {porte_z:.2f} m, gatehouse {booth_z:.2f} m")
    groups = {}
    for o in B.col.objects:
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith("CAM_"):
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if not mats:
            continue
        if o.name == "HT_court_ground":
            dz = 0.0                                      # already on the ground, vertex by vertex
        elif o.name.startswith("HT_porte"):
            dz = porte_z
        elif o.name.startswith("HT_booth"):
            dz = booth_z
        elif o.name.startswith(court) and o.type == "MESH" and len(o.data.vertices):
            c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
            dz = g(c.x, c.y)
        else:
            dz = building_z
        groups.setdefault("HO_" + mats[0].name[3:], []).append((o, dz))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


# ================================================================ scene
def court_to_local(x, y, z):
    a = math.radians(COURT["ang"])
    return (COURT["x"] + x * math.cos(a) - y * math.sin(a), COURT["y"] + x * math.sin(a) + y * math.cos(a), z)


def cams():
    C = court_to_local
    return {
        "court": (C(0.0, 30.0, 1.8), C(0.0, 0.0, 17.0), 14),          # as the photos: from the dais towards the main block
        "gates_wide": (C(0.0, 42.0, 1.7), C(0.0, 0.0, 16.0), 15),     # from outside the gates
        "pavilion": (C(0.0, 18.0, 2.0), C(0.0, 0.0, 16.0), 18),
        "tower": (C(-5.0, 45.0, 1.7), C(26.5, 25.5, 25.0), 20),
        "aerial": (C(40.0, 110.0, 90.0), C(0.0, -10.0, 0.0), 24),
        "north": ((0.0, 45.0, 6.0), (0.0, 0.0, 14.0), 22),            # the other side: the crescent on the loop road
        "porte": ((2.0, 34.0, 1.7), (15.0, 6.0, 5.0), 20),            # the porte-cochere from the loop road
        "ngw": ((110.0, -30.0, 2.0), (33.0, -58.0, 26.0), 18),        # the north-east block's long east face
        "windows": (C(10.0, 14.0, 6.0), C(21.0, 14.0, 12.0), 30),     # the west wing's windows close up (curtains, lights)
        "beds": (C(-6.0, 26.0, 1.6), C(-18.0, 20.0, 0.6), 22),        # the court's beds, a great planter's flower ring
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
    build_main()
    build_ngw()
    gatehouse()
    build_victorian("blue", "h_blue", "h_white")
    build_victorian("purple", "h_purple", "h_pink")
    build_plinth()
    build_front()
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
    ap.add_argument("--cams", default="court,gates_wide,pavilion,tower,aerial,north,porte,ngw,windows,beds")
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
