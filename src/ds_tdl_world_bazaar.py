"""東京ディズニーランド ワールドバザール -- Main Street and Center Street under the glass roof (Blender 5.2).

  blender -b --python src/ds_tdl_world_bazaar.py -- --cams wbz_street,wbz_castle,wbz_crossing,wbz_corner,wbz_back,wbz_aerial --samples 32
  blender -b --python src/ds_tdl_world_bazaar.py -- --cams none     # build + save the .blend only
  then open output/disneyland/world_bazaar/tdl_world_bazaar.blend (cameras CAM_*)

Builds on ds_tdl_entrance (the gates, the plaza, the World Bazaar front, the entrance building and the glass hall's
front gable) and adds the street behind it: the glass roof over Main Street and Center Street, the shops on both
sides, the paving and the street furniture.

Sources (looked at only; nothing copied into the repository):
  * OSM: the glass roof 72216847 (building=roof; it is the covered street itself: Main Street x = -12.3 .. 12.2 from
    the entrance building to y = -106.6, and Center Street across it at y = -41 .. -64, then turning away by about
    18 deg on both sides out to x = +-57), the shop blocks 365357846 / 72216851 / 72216845 / 196943265 (8.5 .. 8.85 m)
    whose fronts line it, the footways Main Street 629990046 and Center Street 217929579.
  * The user's photos (2026-09-27): Main Street towards the castle (the gabled glass roof on lattice trusses, the
    three round arches at the far end, blue-grey carriageway, terracotta sidewalks, green lamp posts, street clocks),
    the Confectionery corner (pink, teal trim, a porch with a balcony and the sign, a round window high on the corner),
    the lattice towers at the crossing (square iron shafts with X-bracing on tall octagonal pedestals), shops of 2 .. 3
    storeys in many colours (awnings, bay windows, balconies, mansards with dormers, a "1894" pediment).

Frame: the World Bazaar frame of ds_tdl_entrance (WB): +x along the entrance front (left to right from the plaza),
+y towards the plaza, so Main Street runs to -y.

ESTIMATES: the heights of the roof (eaves 12.1 m, ridge 16.2 m, from the front photo), the shops (ground floor 4.2 m,
upper floors 3.0 m), the arches at the end (springing 8.0 m), the tower and furniture sizes, the shops' widths and
styles (drawn at random from what the photos show, with the Confectionery and House of Greetings corners placed by
the photos, not surveyed).
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
import ds_tdl_entrance as EN
from ds_tdl_station import (B, box, prism, bm_box, bm_prism, bm_lathe, obj_bm, T, R, seg_arc, arch_opening, arch_band,
                            column_bm, globe_lamp_bm, text, _principled, _mottle)
from ds_tdl_entrance import frame, WB, WB_BACK

OUT = ROOT / "output" / "disneyland" / "world_bazaar"
HALL = dict(eave=12.1, ridge=16.2, base=11.5)            # main hall; the side glazing runs from base to the eaves
END_Y = -106.6
CROSS = dict(y0=-40.8, y1=-64.4, yc=-52.6, half=21.0)    # Center Street's straight part across Main Street
# the covered street (OSM 72216847) in the WB frame, cut at the back of the entrance building
WALK = [(55.7, -62.5), (54.7, -65.3), (53.7, -69.4), (24.0, -61.1), (23.0, -64.7), (13.2, -64.0), (10.9, -106.5),
        (8.9, -106.6), (0.6, -106.7), (-9.4, -106.5), (-11.6, -106.3), (-11.6, -64.4), (-19.8, -64.5), (-19.3, -60.7),
        (-55.4, -69.5), (-56.6, -65.3), (-58.7, -57.8), (-20.6, -44.9), (-20.7, -41.0), (-12.6, -40.8), (-12.3, WB_BACK),
        (12.2, WB_BACK), (12.2, -40.5), (21.1, -41.3), (21.4, -44.6), (57.6, -56.1), (57.3, -57.2), (56.5, -60.3)]
# Center Street's arms (angled part): start / end of the centre line, width
ARMS = [((-19.95, -52.8), (-57.05, -63.65), 15.0), ((22.7, -52.85), (55.65, -62.75), 15.0)]
# shop fronts: segments with the street on their left (p0 -> p1), in the WB frame
FRONTS = [
    ("MW1", (-12.3, WB_BACK), (-12.3, -40.8)), ("ME1", (12.2, -40.5), (12.2, WB_BACK)),        # Main Street, first half
    ("MW2", (-11.6, -64.4), (-11.6, -106.3)), ("ME2", (10.9, -106.5), (13.2, -64.0)),         # second half
    ("CNW", (-12.6, -40.8), (-20.7, -41.0)), ("CSW", (-19.8, -64.5), (-11.6, -64.4)),         # Center Street, straight
    ("CNE", (21.1, -41.3), (12.2, -40.5)), ("CSE", (13.2, -64.0), (23.0, -64.7)),
    ("ANW", (-20.6, -44.9), (-58.7, -57.8)), ("ASW", (-55.4, -69.5), (-19.3, -60.7)),         # Center Street, arms
    ("ANE", (57.6, -56.1), (21.4, -44.6)), ("ASE", (24.0, -61.1), (53.7, -69.4)),
]

PALETTE = {"pink": (0.86, 0.60, 0.57), "cream": (0.87, 0.79, 0.60), "yellow": (0.90, 0.75, 0.42), "blue": (0.44, 0.55, 0.64),
           "mint": (0.60, 0.77, 0.69), "peach": (0.91, 0.69, 0.53), "sand": (0.80, 0.68, 0.50), "sage": (0.52, 0.62, 0.50),
           "lilac": (0.68, 0.60, 0.71), "stone": (0.78, 0.74, 0.66)}
TRIMS = {"white": (0.93, 0.91, 0.85), "cream": (0.90, 0.84, 0.68), "teal": (0.30, 0.60, 0.58), "dkgreen": (0.12, 0.28, 0.22),
         "maroon": (0.42, 0.11, 0.13), "blue": (0.20, 0.30, 0.45)}


MERCH_COLORS = {"m_red": (0.75, 0.08, 0.10), "m_blue": (0.12, 0.30, 0.70), "m_yellow": (0.95, 0.75, 0.10),
                "m_pink": (0.95, 0.55, 0.70), "m_purple": (0.45, 0.20, 0.65), "m_white": (0.93, 0.92, 0.88),
                "m_black": (0.04, 0.04, 0.05), "m_green": (0.15, 0.55, 0.30), "m_orange": (0.95, 0.45, 0.10),
                "m_brown": (0.45, 0.28, 0.14)}
MERCH = ("m_red", "m_blue", "m_yellow", "m_pink", "m_purple", "m_white", "m_green", "m_orange")


def wbz_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    for k, c in PALETTE.items():
        mat, nt, b = _principled(f"st_wbz_{k}", c, 0.7); _mottle(nt, b, c, 6.0, 0.93, 0.03); M["w_" + k] = mat
    for k, c in TRIMS.items():
        M["t_" + k] = P(f"st_wbz_trim_{k}", c, 0.5)
    M["display"] = P("st_wbz_display", (0.80, 0.70, 0.52), 0.2, Emission_Color=(1.0, 0.82, 0.55, 1), Emission_Strength=0.5)
    M["door"] = P("st_wbz_door", (0.22, 0.11, 0.06), 0.5)
    M["road"] = P("st_wbz_road", (0.27, 0.31, 0.37), 0.75)
    M["walk"] = ST.mat_tiles("st_wbz_walk", (0.60, 0.25, 0.19), (0.56, 0.23, 0.18), 0.3, (0.50, 0.40, 0.36))
    M["edging"] = P("st_wbz_edging", (0.72, 0.70, 0.66), 0.8)
    M["aw_green"] = P("st_wbz_awning_green", (0.10, 0.36, 0.28), 0.8)
    M["aw_red"] = P("st_wbz_awning_red", (0.62, 0.10, 0.13), 0.8)
    M["aw_white"] = P("st_wbz_awning_white", (0.92, 0.90, 0.85), 0.8)
    M["aw_blue"] = P("st_wbz_awning_blue", (0.16, 0.30, 0.52), 0.8)
    M["shingle"] = P("st_wbz_shingle", (0.30, 0.34, 0.40), 0.7)
    M["clock"] = P("st_wbz_clock", (0.96, 0.95, 0.90), 0.3, Emission_Color=(1, 0.97, 0.9, 1), Emission_Strength=0.3)
    mat, nt, b = _principled("st_wbz_leaf", (0.18, 0.36, 0.12), 0.9); _mottle(nt, b, (0.18, 0.36, 0.12), 30.0, 0.6, 0.4); M["leaf"] = mat
    M["wood"] = P("st_wbz_wood", (0.45, 0.30, 0.18), 0.7)
    M["floor"] = ST.mat_tiles("st_wbz_floor", (0.46, 0.29, 0.16), (0.41, 0.25, 0.14), 0.25, (0.30, 0.20, 0.12))
    M["shopglass"] = ST.clear_glass("st_wbz_shopglass", (0.90, 0.95, 0.97), 0.12)
    M["brass"] = P("st_wbz_brass", (0.80, 0.62, 0.30), 0.3, Metallic=0.9)
    for k, c in MERCH_COLORS.items():                   # merchandise: plush, sweets, clothes, tins, cards
        M[k] = P(f"st_wbz_{k}", c, 0.55)
    return M


# ================================================================ 1. the glass roof: one gabled hall + trusses
def glass_hall(name, p0, p1, w, eave, ridge, base, step=6.0, gaps=(), end=None, start=None):
    """A gabled glass hall from p0 to p1 (WB frame), w wide. Local frame: y from 0 (p0) to -L, x across. Side glazing
    from base to the eaves (left out over gaps, (y0, y1) in local y) behind an eave girder with small round arches;
    trusses every step (the top chord on the roof, an arched bottom chord, lattice between), purlins, ridge.
    end / start: None (open), "gable" (a glazed gable) or n (n round arches on columns under a glazed gable)."""
    d = (p1[0] - p0[0], p1[1] - p0[1]); L = math.hypot(*d)
    ang = math.degrees(math.atan2(d[0], -d[1]))
    hw = w / 2; zg = lambda x: eave + (ridge - eave) * (1 - abs(x) / hw)
    with frame(f"HALL_{name}", p0[0], p0[1], ang):
        bmg, bmf = bmesh.new(), bmesh.new()
        for s in (-1, 1):                                  # roof glass
            v = [bmg.verts.new(p) for p in ((s * hw, 0, eave), (0, 0, ridge), (0, -L, ridge), (s * hw, -L, eave))]
            bmg.faces.new(v)
        # side glazing and the eave girder (chords, posts, the frieze of small arches)
        spans = [(0.0, -L)]
        for g0, g1 in sorted(gaps, key=lambda g: -max(g)):
            hi, lo = max(g0, g1), min(g0, g1)
            new = []
            for a, b_ in spans:
                if hi <= b_ or lo >= a:
                    new.append((a, b_)); continue
                if a > hi:
                    new.append((a, hi))
                if lo > b_:
                    new.append((lo, b_))
            spans = new
        for s in (-1, 1):
            x = s * hw
            bm_box(bmf, x - 0.12, x + 0.12, -L, 0, eave - 0.2, eave + 0.05)          # top chord over the whole length
            for a, b_ in spans:
                v = [bmg.verts.new(p) for p in ((x, a, base), (x, a, eave), (x, b_, eave), (x, b_, base))]
                bmg.faces.new(v)
                bm_box(bmf, x - 0.1, x + 0.1, b_, a, base - 0.25, base)
                n = max(1, int((a - b_) / 1.5))
                for k in range(n + 1):
                    y = a - (a - b_) * k / n
                    bm_box(bmf, x - 0.05, x + 0.05, y - 0.05, y + 0.05, base, eave - 0.2)
                    if k < n:
                        y2 = a - (a - b_) * (k + 1) / n
                        bm_prism(bmf, arch_band(y2 + 0.05, y - 0.05, eave - 0.2 - (y - y2) / 2 - 0.12, (y - y2) / 2 - 0.05, 0.05, 8), x - 0.03, x + 0.03, "yz")
        # trusses
        spring = eave - 1.3; rise = (ridge - 1.5) - spring
        _, (zc, Rr, half) = seg_arc(0.0, spring, w, rise, 9)
        zb = lambda x: zc + math.sqrt(max(Rr * Rr - x * x, 0.0))
        chevron = [(-hw, eave - 0.05), (0, ridge - 0.05), (hw, eave - 0.05), (hw, eave + 0.18), (0, ridge + 0.18), (-hw, eave + 0.18)]
        N = max(6, int(w / 1.6)) // 2 * 2
        y = -step / 2
        while y > -L:
            bm_prism(bmf, chevron, y - 0.09, y + 0.09, "xz")
            bm_prism(bmf, arch_band(-hw, hw, spring, rise, 0.16, 33), y - 0.07, y + 0.07, "xz")
            for k in range(N + 1):
                x = -hw + w * k / N
                if 0 < k < N:
                    bm_box(bmf, x - 0.03, x + 0.03, y - 0.04, y + 0.04, zb(x), zg(x))
                if k < N:
                    x2 = -hw + w * (k + 1) / N
                    a_, b2 = ((x, zb(x)), (x2, zg(x2))) if k < N / 2 else ((x, zg(x)), (x2, zb(x2)))
                    ux, uz = b2[0] - a_[0], b2[1] - a_[1]; l = math.hypot(ux, uz); nx, nz = -uz / l * 0.03, ux / l * 0.03
                    bm_prism(bmf, [(a_[0] + nx, a_[1] + nz), (b2[0] + nx, b2[1] + nz), (b2[0] - nx, b2[1] - nz), (a_[0] - nx, a_[1] - nz)], y - 0.03, y + 0.03, "xz")
            for s in (-1, 1):                              # knee brackets down to the eave girder
                bm_prism(bmf, [(s * hw, spring - 0.8), (s * (hw - 0.12), spring - 0.8), (s * (hw - 0.12), spring + 0.2), (s * hw, spring + 0.2)][::s], y - 0.06, y + 0.06, "xz")
            y -= step
        for f in (0.2, 0.4, 0.6, 0.8):                     # purlins, ridge
            for s in (-1, 1):
                x = s * hw * (1 - f); z = eave + (ridge - eave) * f
                bm_box(bmf, x - 0.05, x + 0.05, -L, 0, z + 0.02, z + 0.16)
        bm_box(bmf, -0.14, 0.14, -L, 0, ridge - 0.05, ridge + 0.3)
        for kind, y0, sg in ((start, 0.0, 1), (end, -L, -1)):  # ends
            if kind is None:
                continue
            bm_prism(bmg, [(-hw, eave), (hw, eave), (0, ridge)], y0 - 0.02, y0 + 0.02, "xz")
            for k in range(1, 12):
                x = -hw + w * k / 12
                bm_box(bmf, x - 0.05, x + 0.05, y0 - 0.06, y0 + 0.06, eave, zg(x))
            bm_prism(bmf, chevron, y0 - 0.12, y0 + 0.12, "xz")
            bm_box(bmf, -hw, hw, y0 - 0.15, y0 + 0.15, eave - 0.45, eave)
            if isinstance(kind, int):                      # round arches on slender iron columns (the castle end)
                n = kind; r = w / n / 2; zs = eave - 0.45 - r
                bmc = bmesh.new()
                for k in range(n + 1):
                    x = -hw + w * k / n
                    column_bm(bmc, x, y0, 0.0, zs, 0.22, 16)
                    bm_lathe(bmc, [(0, 0), (0.55, 0), (0.55, 0.5), (0.4, 0.7), (0.3, 1.2), (0, 1.2)], 12, T(x, y0, 0))
                obj_bm(f"ST_WBZ_{name}_end_columns", bmc, "hall_iron", smooth=True)
                for k in range(n):
                    cx = -hw + r * (2 * k + 1)
                    bm_prism(bmf, arch_band(cx - r + 0.2, cx + r - 0.2, zs, r - 0.2, 0.22, 25), y0 - 0.1, y0 + 0.1, "xz")
                    for sx in (-1, 1):                    # spandrel rings
                        bm_lathe(bmf, [(0.3, -0.04), (0.38, -0.04), (0.38, 0.04), (0.3, 0.04)], 16, T(cx + sx * (r - 0.55), y0, eave - 1.1) @ R(-math.pi / 2, "X"))
                bm_prism(bmg, [(-hw, zs), (hw, zs), (hw, eave), (-hw, eave)], y0 - 0.02, y0 + 0.02, "xz")
        obj_bm(f"ST_WBZ_{name}_glass", bmg, "hall_glass", recalc=False)
        obj_bm(f"ST_WBZ_{name}_iron", bmf, "hall_iron")


def lattice_tower(bm, x, y, z1):
    """Square lattice column on an octagonal pedestal (the crossing), up to z1."""
    bm_lathe(bm, [(0, 0), (1.05, 0), (1.05, 0.35), (0.9, 0.5), (0.85, 2.0), (1.0, 2.2), (1.0, 2.45), (0.7, 2.6), (0, 2.6)], 8,
             T(x, y, 0) @ R(math.pi / 8, "Z"))
    h = 0.45
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_box(bm, x + sx * h - 0.08, x + sx * h + 0.08, y + sy * h - 0.08, y + sy * h + 0.08, 2.6, z1)
    z = 2.9
    while z + 1.1 < z1:
        for s in (-1, 1):
            for a0, a1 in ((-h, h), (h, -h)):
                q = [(x + a0 - 0.03, z), (x + a1 - 0.03, z + 1.1), (x + a1 + 0.03, z + 1.1), (x + a0 + 0.03, z)]
                bm_prism(bm, q, y + s * h - 0.02, y + s * h + 0.02, "xz")
                q = [(y + a0 - 0.03, z), (y + a1 - 0.03, z + 1.1), (y + a1 + 0.03, z + 1.1), (y + a0 + 0.03, z)]
                bm_prism(bm, q, x + s * h - 0.02, x + s * h + 0.02, "yz")
            bm_box(bm, x - h, x + h, y + s * h - 0.04, y + s * h + 0.04, z - 0.05, z + 0.05)
            bm_box(bm, x + s * h - 0.04, x + s * h + 0.04, y - h, y + h, z - 0.05, z + 0.05)
        z += 1.1
    bm_box(bm, x - 0.7, x + 0.7, y - 0.7, y + 0.7, z1 - 0.35, z1)


def build_roof():
    H = HALL
    cy0, cy1 = CROSS["y0"] - WB_BACK, CROSS["y1"] - WB_BACK       # the crossing in the main hall's local y
    glass_hall("main", (0.0, WB_BACK), (0.0, END_Y), 24.5, H["eave"], H["ridge"], H["base"], 6.0, gaps=[(cy0, cy1)], end=3)
    w = CROSS["y0"] - CROSS["y1"]
    # Center Street across Main Street: one hall from arm to arm; no side glazing over Main Street
    glass_hall("cross", (-CROSS["half"], CROSS["yc"]), (CROSS["half"], CROSS["yc"]), w, H["eave"], H["eave"] + (H["ridge"] - H["eave"]) * w / 24.5,
               H["base"], 6.0, gaps=[(-(CROSS["half"] - 12.6), -(CROSS["half"] + 12.6))], start="gable", end="gable")
    for k, (p0, p1, aw) in enumerate(ARMS):
        glass_hall(f"arm{k}", p0, p1, aw, H["eave"], H["eave"] + (H["ridge"] - H["eave"]) * aw / 24.5, H["base"], 6.0, end=2)
    bm = bmesh.new()                                      # the four towers at the crossing and the girders they carry
    for sx in (-1, 1):
        for y in (CROSS["y0"] - 0.9, CROSS["y1"] + 0.9):
            lattice_tower(bm, sx * 11.0, y, H["eave"] - 0.2)
        bm_box(bm, sx * 11.0 - 0.2, sx * 11.0 + 0.2, CROSS["y1"] + 0.9, CROSS["y0"] - 0.9, H["eave"] - 1.2, H["eave"] - 0.2)
        for y in (CROSS["y0"] - 0.9, CROSS["y1"] + 0.9):
            bm_box(bm, sx * 11.0 - 0.2, sx * 12.4, y - 0.2, y + 0.2, H["eave"] - 1.2, H["eave"] - 0.2)
    obj_bm("ST_WBZ_towers", bm, "hall_iron")


# ================================================================ 2. the shops: one front per shop, styles from the photos
def shop(name, w, st, room=None):
    """One shop in the current frame: x 0..w along the street, the front on y = 0 facing +y (the street), z up.
    room = (x0, x1, depth): the part of the ground floor that is a real shop you can see into and walk into (clear
    windows, an open door, shop_interior); outside it the ground floor is solid behind a lit display backdrop."""
    wall = "brick" if st["wall"] == "brick" else "w_" + st["wall"]; trim = "t_" + st["trim"]
    fl = st["floors"]; gf, fh = 4.2, 3.0
    H = gf + fh * (fl - 1) + 0.3
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "display", "door", "iron", "roof", "sign", "flowers", "aw1", "aw2",
                                  "shopglass", "brass", "lamp", "lit")}
    rng = random.Random(name)
    if room and room[1] - room[0] < 2.8:
        room = None
    bm_box(P["wall"], 0, w, -9.0, 0.0, gf, H)                                        # upper floors
    for a, b_ in (((0, room[0]), (room[1], w)) if room else ((0, w),)):             # ground floor: solid outside the room
        if b_ - a > 0.01:
            bm_box(P["wall"], a, b_, -9.0, -0.5, 0.0, gf)
    for x0, x1 in ((0.0, 0.4), (w - 0.4, w)):
        bm_box(P["trim"], x0, x1, -0.3, 0.12, 0.0, H)                              # corner pilasters: base, shaft, capital
        bm_box(P["trim"], x0 - 0.04, x1 + 0.04, -0.3, 0.18, 0.0, 0.45)
        bm_box(P["trim"], x0 - 0.05, x1 + 0.05, -0.3, 0.2, gf - 0.55, gf - 0.3)
    # ground floor: bulkhead, display windows with mullions and a transom, a door, the fascia with the sign board
    dx = {"mid": w / 2, "left": 1.4, "right": w - 1.4}[st["door"]]
    if room and not (room[0] + 0.25 <= dx - 0.85 and dx + 0.85 <= room[1] - 0.25):
        dx = (room[0] + room[1]) / 2                     # the door opens into the room
    door_open = bool(room) and room[0] + 0.25 <= dx - 0.85 and dx + 0.85 <= room[1] - 0.25
    if door_open:                                        # two glazed leaves swung in against the reveals
        for sx in (-1, 1):
            hx = dx + sx * 0.7
            bm_box(P["door"], hx - 0.03, hx + 0.03, -1.0, -0.3, 0.0, 2.95)
            bm_box(P["shopglass"], hx - 0.035, hx + 0.035, -0.9, -0.4, 0.9, 2.7)
            bm_box(P["brass"], hx - sx * 0.05 - 0.015, hx - sx * 0.05 + 0.015, -0.95, -0.9, 1.0, 1.25)
        bm_box(P["trim"], dx - 0.7, dx + 0.7, -0.3, 0.0, 0.0, 0.03)                # threshold
    else:
        bm_box(P["door"], dx - 0.7, dx + 0.7, -0.3, -0.2, 0.0, 3.0)
        bm_box(P["brass"], dx - 0.1, dx - 0.04, -0.2, -0.15, 1.0, 1.3)
    bm_box(P["trim"], dx - 0.85, dx + 0.85, -0.3, 0.05, 3.0, 3.15)
    for sx in (-1, 1):
        bm_box(P["trim"], dx + sx * 0.78 - 0.08, dx + sx * 0.78 + 0.08, -0.3, 0.05, 0.0, 3.0)
        bm_box(P["iron"], dx + sx * 1.05 - 0.03, dx + sx * 1.05 + 0.03, 0.0, 0.25, 2.55, 2.6)   # carriage lamps by the door
        bm_lathe(P["iron"], [(0, 0), (0.05, 0), (0.1, 0.06), (0.1, 0.32), (0.13, 0.35), (0.03, 0.45), (0, 0.45)], 6, T(dx + sx * 1.05, 0.28, 2.3))
        globe_lamp_bm(P["lamp"], dx + sx * 1.05, 0.28, 2.48, 0.07)
    for a, b_ in ((0.4, dx - 0.86), (dx + 0.86, w - 0.4)):
        if b_ - a < 0.5:
            if b_ - a > 0.01:
                bm_box(P["wall"], a, b_, -0.3, -0.2, 0.0, 3.2)
            continue
        bm_box(P["trim"], a, b_, -0.3, 0.02, 0.0, 0.6)
        n = max(1, int((b_ - a) / 1.1))
        for k in range(n):                                # raised panels on the bulkhead
            pa = a + (b_ - a) * k / n + 0.08; pb = a + (b_ - a) * (k + 1) / n - 0.08
            bm_box(P["trim"], pa, pb, 0.02, 0.05, 0.12, 0.48)
        bm_box(P["shopglass"], a, b_, -0.24, -0.2, 0.6, 3.05)
        for x_a, x_b in (((a, b_),) if not room else ((a, min(b_, room[0])), (max(a, room[1]), b_))):
            if x_b - x_a > 0.01:                          # outside the room: a lit display backdrop behind the glass
                bm_box(P["display"], x_a, x_b, -0.48, -0.46, 0.6, 3.05)
        bm_box(P["trim"], a, b_, -0.3, 0.04, 3.05, 3.2)
        bm_box(P["trim"], a, b_, -0.3, -0.18, 2.42, 2.5)                                   # transom bar
        for k in range(1, n):
            x = a + (b_ - a) * k / n
            bm_box(P["trim"], x - 0.04, x + 0.04, -0.3, -0.16, 0.6, 3.05)
        for k in range(1, 2 * n):                        # transom lights
            x = a + (b_ - a) * k / (2 * n)
            bm_box(P["trim"], x - 0.02, x + 0.02, -0.3, -0.18, 2.5, 3.05)
    # a hanging blade sign on an iron bracket, beside the fascia
    bx = w - 0.75 if dx < w / 2 else 0.75
    bm_box(P["iron"], bx - 0.03, bx + 0.03, 0.12, 1.25, 3.62, 3.68)
    bm_box(P["iron"], bx - 0.02, bx + 0.02, 0.12, 0.16, 3.2, 3.68)
    bm_box(P["sign"], bx - 0.03, bx + 0.03, 0.35, 1.15, 2.95, 3.55)
    bm_box(P["brass"], bx - 0.04, bx + 0.04, 0.33, 1.17, 2.93, 2.97); bm_box(P["brass"], bx - 0.04, bx + 0.04, 0.33, 1.17, 3.53, 3.57)
    bm_box(P["trim"], 0.4, w - 0.4, -0.3, 0.14, 3.2, 3.95)                           # fascia
    sign_sz = min(0.3, (w - 1.5) / (0.62 * max(8, len(st.get("sign") or "")))) if st.get("sign") else 0.3
    sl = min(w - 1.4, max(2.0, len(st.get("sign") or "xxxxxxxx") * sign_sz * 0.66 + 0.5))
    bm_box(P["sign"], w / 2 - sl / 2, w / 2 + sl / 2, 0.14, 0.18, 3.32, 3.83)
    bm_box(P["trim"], -0.05, w + 0.05, -0.3, 0.32, 3.95, 4.2)
    if st.get("sign"):
        text(f"ST_WBZ_{name}_signtext", st["sign"], sign_sz, (w / 2, 0.2, 3.58), (math.pi / 2, 0, math.pi), "letters", 0.015)
    if st["awning"]:                                     # a sloping awning over the shopfront (striped or plain)
        k = 0; x = 0.5
        while x < w - 0.5:
            x1 = min(x + 0.5, w - 0.5)
            bm_prism(P["aw1" if (k % 2 == 0 or st["awning"][1] is None) else "aw2"], [(0.2, 3.2), (1.5, 2.6), (1.5, 2.45), (0.2, 3.05)], x, x1, "yz")
            x = x1; k += 1
    # upper floors: windows (rectangular with caps, arched, or paired), string courses; a bay window or a balcony
    nwin = max(1, int((w - 0.8) / 1.8))
    xs = [0.4 + (w - 0.8) * (i + 0.5) / nwin for i in range(nwin)]
    ww = min(1.05, (w - 0.8) / nwin - 0.65)
    oriel = st["oriel"] and w >= 5.0 and fl >= 2
    for f in range(1, fl):
        z0 = gf + fh * (f - 1) + 0.65; z1 = z0 + 1.95
        bm_box(P["trim"], 0, w, 0.0, 0.1, gf + fh * (f - 1) - 0.05, gf + fh * (f - 1) + 0.12)
        for x in xs:
            if oriel and abs(x - w / 2) < 1.3:
                continue
            gk = "lit" if rng.random() < 0.22 else "glass"   # a lamp on in some of the rooms upstairs
            if f == 1 and not st["balcony"] and rng.random() < 0.5:   # a flower box under the window
                bm_box(P["trim"], x - ww / 2 - 0.1, x + ww / 2 + 0.1, 0.0, 0.32, z0 - 0.42, z0 - 0.22)
                bm_box(P["flowers"], x - ww / 2 - 0.05, x + ww / 2 + 0.05, 0.03, 0.3, z0 - 0.22, z0 - 0.02)
            if st["win"] == "arch":
                bm_prism(P["trim"], arch_opening(x - ww / 2 - 0.13, x + ww / 2 + 0.13, z0 - 0.1, z1 - ww / 2, ww / 2 + 0.13, 12), 0.0, 0.08, "xz")
                bm_prism(P[gk], arch_opening(x - ww / 2, x + ww / 2, z0, z1 - ww / 2, ww / 2, 12), 0.08, 0.1, "xz")
                bm_box(P["trim"], x - 0.12, x + 0.12, 0.0, 0.14, z1 + 0.05, z1 + 0.3)
            else:
                bm_box(P["trim"], x - ww / 2 - 0.13, x + ww / 2 + 0.13, 0.0, 0.08, z0 - 0.1, z1 + 0.1)
                bm_box(P[gk], x - ww / 2, x + ww / 2, 0.08, 0.1, z0, z1)
                bm_box(P["trim"], x - ww / 2 - 0.25, x + ww / 2 + 0.25, 0.0, 0.26, z1 + 0.1, z1 + 0.3)
                if st["win"] == "pair":
                    bm_box(P["trim"], x - 0.05, x + 0.05, 0.08, 0.12, z0, z1)
            bm_box(P["trim"], x - 0.02, x + 0.02, 0.1, 0.12, z0, z1 - 0.1)
            bm_box(P["trim"], x - ww / 2, x + ww / 2, 0.1, 0.12, z0 + 1.15, z0 + 1.19)
            bm_box(P["trim"], x - ww / 2 - 0.2, x + ww / 2 + 0.2, 0.0, 0.2, z0 - 0.22, z0 - 0.1)
            if st["win_awn"] and st["awning"]:
                bm_prism(P["aw1"], [(0.05, z1 + 0.5), (0.75, z1 + 0.05), (0.75, z1 - 0.05), (0.05, z1 + 0.4)], x - ww / 2 - 0.1, x + ww / 2 + 0.1, "yz")
    if oriel:                                             # a bay window over the upper floors
        m = w / 2
        bay = [(m - 1.3, 0.0), (m + 1.3, 0.0), (m + 0.85, 0.75), (m - 0.85, 0.75)]
        bm_prism(P["wall"], bay, gf + 0.35, H - 0.5, "xy")
        bm_prism(P["trim"], [(m - 1.4, 0.0), (m + 1.4, 0.0), (m + 0.9, 0.85), (m - 0.9, 0.85)], gf + 0.15, gf + 0.35, "xy")
        bm_prism(P["trim"], [(m - 1.45, 0.0), (m + 1.45, 0.0), (m + 0.92, 0.9), (m - 0.92, 0.9)], H - 0.5, H - 0.3, "xy")
        for f in range(1, fl):
            z0 = gf + fh * (f - 1) + 0.65
            bm_box(P["glass"], m - 0.65, m + 0.65, 0.75, 0.77, z0, z0 + 1.9)
            bm_box(P["trim"], m - 0.03, m + 0.03, 0.77, 0.79, z0, z0 + 1.9)
    elif st["balcony"] and fl >= 2:                      # a balcony on the first floor: slab, iron railing, flowers
        bm_box(P["trim"], 0.4, w - 0.4, 0.0, 0.95, gf - 0.02, gf + 0.12)
        bm_box(P["iron"], 0.45, w - 0.45, 0.86, 0.92, gf + 0.98, gf + 1.04)
        bm_box(P["iron"], 0.45, w - 0.45, 0.86, 0.92, gf + 0.12, gf + 0.17)
        for sx in (0.45, w - 0.5):
            bm_box(P["iron"], sx, sx + 0.05, 0.0, 0.92, gf + 0.12, gf + 1.04)
        x = 0.6
        while x < w - 0.5:
            bm_box(P["iron"], x - 0.012, x + 0.012, 0.87, 0.91, gf + 0.17, gf + 0.98); x += 0.12
        x = 0.7
        while x < w - 0.7:
            bm_box(P["flowers"], x, x + 0.45, 0.7, 0.9, gf + 0.95, gf + 1.2); x += 0.7
    # cornice with brackets
    bm_box(P["trim"], 0, w, 0.0, 0.1, H - 0.75, H - 0.3)
    bm_box(P["trim"], -0.08, w + 0.08, 0.0, 0.45, H - 0.3, H)
    x = 0.45
    while x < w - 0.3:
        bm_box(P["trim"], x - 0.06, x + 0.06, 0.0, 0.38, H - 0.7, H - 0.3); x += 0.85
    # roof
    rf = st["roof"]
    if rf in ("parapet", "pediment"):
        bm_box(P["wall"], 0, w, -0.35, 0.0, H, H + 0.75)
        bm_box(P["trim"], -0.05, w + 0.05, -0.4, 0.06, H + 0.75, H + 0.87)
        if rf == "pediment":
            pw = min(w - 0.6, 4.2)
            pts, _ = seg_arc(w / 2, H + 0.87, pw, 0.5, 16)
            bm_prism(P["wall"], [(w / 2 - pw / 2, H + 0.87), (w / 2 + pw / 2, H + 0.87)] + pts, -0.35, 0.0, "xz")
            bm_prism(P["trim"], arch_band(w / 2 - pw / 2, w / 2 + pw / 2, H + 0.87, 0.5, 0.14, 16), -0.4, 0.06, "xz")
            if st.get("date"):
                text(f"ST_WBZ_{name}_date", st["date"], 0.42, (w / 2, 0.03, H + 1.12), (math.pi / 2, 0, math.pi), "t_maroon", 0.02)
    elif rf == "mansard":
        rm = st.get("roofmat", "shingle")
        bm2 = P["roof"]
        V = lambda x, y, z: bm2.verts.new((x, y, z))
        a, b_, c, d = V(0, 0.3, H), V(w, 0.3, H), V(w, -1.2, H + 2.0), V(0, -1.2, H + 2.0)
        e, f = V(w, -9.0, H + 2.0), V(0, -9.0, H + 2.0)
        bm2.faces.new((a, b_, c, d)); bm2.faces.new((d, c, e, f))
        for x in xs:                                      # dormers
            bm_box(P["wall"], x - 0.55, x + 0.55, -0.7, 0.45, H, H + 1.45)
            bm_prism(P["trim"], [(x - 0.72, H + 1.4), (x + 0.72, H + 1.4), (x, H + 2.0)], -0.7, 0.52, "xz")
            bm_box(P["glass"], x - 0.32, x + 0.32, 0.45, 0.47, H + 0.2, H + 1.2)
        P["_roofmat"] = rm
    elif rf == "gable":                                   # a front gable with a round window (kept under the glass)
        gh = min(w * 0.32, max(0.9, 11.9 - H))
        bm_prism(P["wall"], [(0, H), (w, H), (w / 2, H + gh)], -0.4, 0.0, "xz")
        for s in (-1, 1):
            xa = 0 if s < 0 else w
            q = [(xa - s * 0.25, H - 0.1), (w / 2, H + gh + 0.2), (w / 2, H + gh + 0.45), (xa - s * 0.25 - s * 0.05, H + 0.15)]
            bm_prism(P["trim"], q if s < 0 else q[::-1], -0.45, 0.1, "xz")
            v = [P["roof"].verts.new(p) for p in ((xa - s * 0.3, 0.1, H - 0.1), (w / 2, 0.1, H + gh + 0.3),
                                                   (w / 2, -9.0, H + gh + 0.3), (xa - s * 0.3, -9.0, H - 0.1))]
            P["roof"].faces.new(v)
        bm_lathe(P["trim"], [(0.32, 0), (0.45, 0), (0.45, 0.08), (0.32, 0.08)], 20, T(w / 2, 0.0, H + gh * 0.42) @ R(-math.pi / 2, "X"))
        bm_lathe(P["glass"], [(0, 0), (0.33, 0), (0.33, 0.02), (0, 0.02)], 20, T(w / 2, 0.0, H + gh * 0.42) @ R(-math.pi / 2, "X"))
    if st.get("turret") is not None:                     # a corner tower with a round window and a dome
        tx = st["turret"]; t0, t1 = (0.0, 2.8) if tx == 0 else (w - 2.8, w)
        tz = H + 0.6
        bm_box(P["wall"], t0, t1, -2.8, 0.2, H, tz)
        bm_box(P["trim"], t0 - 0.1, t1 + 0.1, -2.9, 0.4, tz - 0.3, tz)
        m = (t0 + t1) / 2
        bm_lathe(P["trim"], [(0.45, 0), (0.62, 0), (0.62, 0.1), (0.45, 0.1)], 24, T(m, 0.2, H - 1.3) @ R(-math.pi / 2, "X"))
        bm_lathe(P["glass"], [(0, 0), (0.46, 0), (0.46, 0.03), (0, 0.03)], 24, T(m, 0.2, H - 1.3) @ R(-math.pi / 2, "X"))
        prof = [(1.5 * math.cos(math.pi / 2 * i / 8), 0.55 * math.sin(math.pi / 2 * i / 8)) for i in range(9)]
        bm_lathe(P["roof"], [(0, 0)] + prof, 16, T(m, -1.3, tz))
    if st.get("porch"):                                  # a corner porch (the Confectionery): columns, balcony, sign
        d = 2.4
        bm_box(P["trim"], 0.2, w - 0.2, 0.0, d, gf - 0.1, gf + 0.25)
        for x in [0.4 + (w - 0.8) * k / 3 for k in range(4)]:
            bm_box(P["trim"], x - 0.25, x + 0.25, d - 0.5, d, 0.0, 0.9)
            column_bm(P["trim"], x, d - 0.25, 0.9, gf - 1.0, 0.14, 12)
        bm_box(P["trim"], 0.2, w - 0.2, d - 0.12, d, gf + 0.25, gf + 1.1)          # balcony parapet
        bm_box(P["sign"], w / 2 - 2.3, w / 2 + 2.3, d, d + 0.08, gf + 0.9, gf + 1.8)
        if st.get("porch_sign"):
            text(f"ST_WBZ_{name}_porchsign", st["porch_sign"], 0.48, (w / 2, d + 0.1, gf + 1.33), (math.pi / 2, 0, math.pi), "t_maroon", 0.02)
    if room:
        shop_interior(name, st, room, gf, rng)
    mats = {"wall": wall, "trim": trim, "glass": "win_dark", "display": "display", "door": "door", "iron": "iron",
            "shopglass": "shopglass", "brass": "brass", "lamp": "lamp", "lit": "display",
            "roof": P.pop("_roofmat", None) or st.get("roofmat", "shingle"), "sign": st.get("signmat", "t_maroon"),
            "flowers": "flowers_red", "aw1": st["awning"][0] if st["awning"] else "aw_green",
            "aw2": (st["awning"][1] or "aw_white") if st["awning"] else "aw_white"}
    for k, bm_ in P.items():
        if len(bm_.verts):
            obj_bm(f"ST_WBZ_{name}_{k}", bm_, mats[k])
        else:
            bm_.free()
    return H


def merch_item(theme, bmk, cx, cy, z, rng):
    """One piece of merchandise standing on a shelf / table top at z, centred on (cx, cy); returns the width it takes."""
    col = rng.choice(MERCH)
    if theme == "plush":                                  # Mickey plush heads (and a few in colour, bows on some)
        r = rng.uniform(0.1, 0.15); head = "m_black" if rng.random() < 0.6 else col
        bm_lathe(bmk(head), [(0, -r)] + [(r * math.sin(math.pi * i / 6), -r * math.cos(math.pi * i / 6)) for i in range(1, 6)] + [(0, r)], 8, T(cx, cy, z + r))
        for s in (-1, 1):
            e = r * 0.55
            bm_lathe(bmk(head), [(0, -e), (e * 0.87, -e * 0.5), (e * 0.87, e * 0.5), (0, e)], 8, T(cx + s * r * 0.85, cy, z + r * 1.75))
        if rng.random() < 0.35:
            bm_box(bmk("m_red"), cx - r * 0.5, cx + r * 0.5, cy - 0.03, cy + 0.03, z + r * 1.85, z + r * 2.2)
        return 2.1 * r
    if theme == "sweets":                                 # candy jars and gift tins
        if rng.random() < 0.5:
            bm_lathe(bmk("shopglass"), [(0, 0), (0.08, 0), (0.08, 0.24), (0.05, 0.27), (0, 0.27)], 8, T(cx, cy, z))
            bm_lathe(bmk(col), [(0, 0), (0.07, 0), (0.07, 0.17), (0, 0.17)], 8, T(cx, cy, z + 0.01))
            bm_lathe(bmk("brass"), [(0, 0), (0.06, 0), (0.06, 0.03), (0, 0.04)], 8, T(cx, cy, z + 0.27))
            return 0.17
        h = rng.uniform(0.1, 0.22)
        bm_box(bmk(col), cx - 0.1, cx + 0.1, cy - 0.08, cy + 0.08, z, z + h)
        bm_box(bmk("m_white"), cx - 0.101, cx + 0.101, cy - 0.081, cy + 0.081, z + h * 0.45, z + h * 0.55)
        return 0.21
    if theme == "apparel":                                # folded T-shirts, stacked
        n = rng.randint(2, 5)
        bm_box(bmk(col), cx - 0.15, cx + 0.15, cy - 0.12, cy + 0.12, z, z + 0.035 * n)
        return 0.32
    if theme == "home":                                   # mugs and upright plates
        if rng.random() < 0.5:
            bm_lathe(bmk(rng.choice(("m_white", col))), [(0, 0), (0.045, 0), (0.05, 0.1), (0, 0.1)], 8, T(cx, cy, z))
            return 0.11
        bm_lathe(bmk(col), [(0, 0), (0.12, 0), (0.12, 0.015), (0, 0.015)], 12, T(cx, cy, z + 0.12) @ R(math.pi / 2, "X"))
        return 0.05
    # cards: a row of greeting cards standing in a rack
    bm_box(bmk(col), cx - 0.06, cx + 0.06, cy - 0.01, cy + 0.01, z, z + 0.17)
    return 0.14


def fill_run(theme, bmk, xa, xb, ya, yb, z, rng):
    """Merchandise along the long side of a shelf / table top (xa..xb, ya..yb) standing at z."""
    along_x = (xb - xa) >= (yb - ya)
    L = (xb - xa) if along_x else (yb - ya)
    t = 0.05
    while t < L - 0.12:
        c = (xa + t, (ya + yb) / 2) if along_x else ((xa + xb) / 2, ya + t)
        t += merch_item(theme, bmk, c[0], c[1], z, rng) + 0.04


def shop_interior(name, st, room, gf, rng):
    """The shop inside the ground floor (x0..x1, from the front at y = -0.3 back to -depth): walls in the shop's own
    colour, a plank floor, shelving on the back wall (and a side wall when deep enough), display tables down the
    middle, a counter with the register, pendant lamps -- and the merchandise of the shop's theme on all of them."""
    x0, x1, D = room
    P = {}

    def bmk(k):
        if k not in P:
            P[k] = bmesh.new()
        return P[k]
    theme = st.get("theme", "plush")
    wallm = "w_" + (st["wall"] if st["wall"] != "brick" else "cream"); trim = "t_" + st["trim"]
    top = gf - 0.45
    bm_box(bmk("floor"), x0, x1, -D, -0.3, 0.0, 0.06)
    bm_box(bmk(wallm), x0, x0 + 0.15, -D, -0.3, 0.06, top)
    bm_box(bmk(wallm), x1 - 0.15, x1, -D, -0.3, 0.06, top)
    bm_box(bmk(wallm), x0, x1, -D - 0.15, -D, 0.0, top)
    bm_box(bmk("t_white"), x0, x1, -D - 0.15, -0.3, top, top + 0.15)                 # ceiling
    for a, b_, c0, c1 in ((x0 + 0.15, x1 - 0.15, -D, -D + 0.03), (x0 + 0.15, x0 + 0.18, -D, -0.3), (x1 - 0.18, x1 - 0.15, -D, -0.3)):
        bm_box(bmk(trim), a, b_, c0, c1, 0.06, 0.2)                                   # skirting
        bm_box(bmk(trim), a, b_, c0, c1, top - 0.2, top)                              # cornice
    iw = x1 - x0
    # shelving on the back wall: uprights, five boards, merchandise on four
    sy0, sy1 = -D + 0.03, -D + 0.5
    nu = max(2, int(iw / 1.2) + 1)
    for k in range(nu):
        ux = x0 + 0.3 + (iw - 0.6) * k / (nu - 1)
        bm_box(bmk("wood"), ux - 0.03, ux + 0.03, sy0, sy1, 0.06, 2.35)
    for zz in (0.3, 0.8, 1.3, 1.8, 2.3):
        bm_box(bmk("wood"), x0 + 0.3, x1 - 0.3, sy0, sy1, zz, zz + 0.04)
        if zz < 2.2:
            fill_run(theme, bmk, x0 + 0.35, x1 - 0.35, sy0 + 0.08, sy1 - 0.08, zz + 0.04, rng)
    # shelving along the left wall when the room is deep enough
    if D > 5.0:
        for zz in (0.5, 1.1, 1.7):
            bm_box(bmk("wood"), x0 + 0.15, x0 + 0.55, -D + 0.7, -1.2, zz, zz + 0.04)
            fill_run(theme, bmk, x0 + 0.2, x0 + 0.5, -D + 0.75, -1.25, zz + 0.04, rng)
        for yy in (-D + 0.7, -1.2):
            bm_box(bmk("wood"), x0 + 0.15, x0 + 0.55, yy - 0.03, yy + 0.03, 0.06, 2.0)
    # the counter along the right wall, the register on it
    cl = min(2.2, D - 2.4)
    if cl > 0.8:
        cy0 = -D + 0.9
        bm_box(bmk("wood"), x1 - 0.85, x1 - 0.25, cy0, cy0 + cl, 0.06, 0.95)
        bm_box(bmk(trim), x1 - 0.9, x1 - 0.2, cy0 - 0.05, cy0 + cl + 0.05, 0.95, 1.0)
        bm_box(bmk("m_black"), x1 - 0.7, x1 - 0.4, cy0 + 0.3, cy0 + 0.6, 1.0, 1.12)
        bm_box(bmk("m_black"), x1 - 0.62, x1 - 0.58, cy0 + 0.35, cy0 + 0.55, 1.12, 1.35)
        if theme == "sweets":                             # a glass-topped case of sweets on the counter
            bm_box(bmk("shopglass"), x1 - 0.85, x1 - 0.3, cy0 + 0.8, cy0 + cl - 0.1, 1.0, 1.35)
            fill_run("sweets", bmk, x1 - 0.8, x1 - 0.35, cy0 + 0.85, cy0 + cl - 0.15, 1.0, rng)
    # display tables down the middle, with merchandise; a big Mickey plush on the first table of a plush shop
    tx0, tx1 = x0 + 0.9, x1 - (1.2 if cl > 0.8 else 0.9)
    nt = max(1, int((tx1 - tx0) / 2.2))
    ty = -max(1.4, D * 0.45)
    for k in range(nt):
        cx = tx0 + (tx1 - tx0) * (k + 0.5) / nt
        bm_box(bmk("wood"), cx - 0.65, cx + 0.65, ty - 0.4, ty + 0.4, 0.8, 0.85)
        for sx in (-1, 1):
            for sy in (-1, 1):
                bm_box(bmk("wood"), cx + sx * 0.58 - 0.03, cx + sx * 0.58 + 0.03, ty + sy * 0.33 - 0.03, ty + sy * 0.33 + 0.03, 0.06, 0.8)
        if theme == "plush" and k == 0:
            r = 0.3
            bm_lathe(bmk("m_black"), [(0, -r)] + [(r * math.sin(math.pi * i / 8), -r * math.cos(math.pi * i / 8)) for i in range(1, 8)] + [(0, r)], 12, T(cx, ty, 0.85 + r))
            for s in (-1, 1):
                bm_lathe(bmk("m_black"), [(0, -0.17), (0.15, -0.085), (0.15, 0.085), (0, 0.17)], 10, T(cx + s * 0.27, ty, 0.85 + r * 1.75))
            bm_box(bmk("m_red"), cx - 0.25, cx + 0.25, ty - 0.2, ty + 0.2, 0.85, 0.9)
            continue
        fill_run(theme, bmk, cx - 0.6, cx + 0.6, ty - 0.35, ty - 0.02, 0.85, rng)
        fill_run(theme, bmk, cx - 0.6, cx + 0.6, ty + 0.02, ty + 0.35, 0.85, rng)
    if theme == "apparel" and D > 3.5:                    # a clothes rail by the window
        rx0, rx1, ry = x0 + 0.8, min(x0 + 2.4, x1 - 1.3), -1.0
        if rx1 - rx0 > 0.6:
            bm_box(bmk("iron"), rx0, rx1, ry - 0.015, ry + 0.015, 1.5, 1.53)
            for xx in (rx0, rx1):
                bm_box(bmk("iron"), xx - 0.015, xx + 0.015, ry - 0.015, ry + 0.015, 0.06, 1.53)
            xx = rx0 + 0.1
            while xx < rx1 - 0.08:
                bm_box(bmk(rng.choice(MERCH)), xx - 0.012, xx + 0.012, ry - 0.24, ry + 0.24, 0.85, 1.45); xx += 0.08
    # pendant lamps
    n_l = max(1, round(iw / 2.4))
    for k in range(n_l):
        lx = x0 + iw * (k + 0.5) / n_l
        bm_box(bmk("iron"), lx - 0.01, lx + 0.01, -D / 2 - 0.01, -D / 2 + 0.01, top - 0.7, top)
        bm_lathe(bmk("brass"), [(0, 0), (0.22, 0.0), (0.12, 0.14), (0.02, 0.2), (0, 0.2)], 12, T(lx, -D / 2, top - 0.85))
        globe_lamp_bm(bmk("lamp"), lx, -D / 2, top - 0.9, 0.1)
    for k, bm_ in P.items():
        obj_bm(f"ST_WBZ_{name}_in_{k}", bm_, k, smooth=(k in ("lamp", "m_black")))


THEMES = ("plush", "plush", "sweets", "apparel", "home", "cards")


def random_style(rng, prev):
    wall = rng.choice([c for c in list(PALETTE) + ["brick", "brick"] if c != prev])
    trim = rng.choice(["white", "white", "cream", "teal", "dkgreen", "maroon", "blue"])
    if wall in ("cream", "stone", "yellow", "sand") and trim in ("white", "cream"):
        trim = rng.choice(["teal", "dkgreen", "maroon", "blue"])
    aw = rng.random()
    awning = (("aw_green", None) if aw < 0.25 else ("aw_red", "aw_white") if aw < 0.4 else ("aw_blue", "aw_white") if aw < 0.5
              else ("aw_green", "aw_white") if aw < 0.6 else None)
    roof = rng.choice(["parapet", "parapet", "mansard", "gable", "pediment"])
    return dict(wall=wall, trim=trim, floors=2 if roof == "mansard" else rng.choice([2, 3, 3, 3]), roof=roof,
                win=rng.choice(["rect", "arch", "pair"]), balcony=rng.random() < 0.35, oriel=rng.random() < 0.25,
                awning=awning, win_awn=rng.random() < 0.3, door=rng.choice(["mid", "left", "right"]),
                signmat=rng.choice(["t_maroon", "t_dkgreen", "t_blue", "t_teal"]), roofmat=rng.choice(["shingle", "mauve", "t_dkgreen"]),
                theme=rng.choice(THEMES))


# the corner shops from the photos (by front and position: 0 = the first shop from p0, -1 = the last)
SPECIAL = {
    ("ME1", 0): dict(wall="pink", trim="teal", floors=3, roof="parapet", win="arch", balcony=False, oriel=False, awning=("aw_green", None),
                     win_awn=True, door="mid", signmat="w_mint", turret=0, porch=True, porch_sign="CONFECTIONERY", sign="WORLD BAZAAR CONFECTIONERY", theme="sweets", w=10.0),
    ("MW1", -1): dict(wall="cream", trim="dkgreen", floors=3, roof="pediment", win="arch", balcony=False, oriel=False, awning=None,
                      win_awn=False, door="mid", signmat="t_dkgreen", turret=1, sign="HOUSE OF GREETINGS", theme="cards", w=10.0),
    ("ME2", -1): dict(wall="cream", trim="maroon", floors=3, roof="pediment", win="pair", balcony=False, oriel=True, awning=("aw_green", None),
                      win_awn=False, door="left", signmat="t_maroon", date="1894", sign="GRAND EMPORIUM", theme="apparel", w=9.0),
    ("MW2", 0): dict(wall="peach", trim="white", floors=2, roof="mansard", win="rect", balcony=True, oriel=False, awning=("aw_red", "aw_white"),
                     win_awn=False, door="mid", signmat="t_blue", turret=0, sign="MAIN STREET", roofmat="t_dkgreen", theme="home", w=9.0),
}


CORNER = 4.2
# the shops and restaurants OSM places in World Bazaar (plateau_data/disneyland_osm.json points, in the WB frame):
# (x, y, the sign, the shop's theme). Each goes on the shop front nearest to it (within 14 m)
REAL_SHOPS = [(-14.9, -103.0, "PASTRY PALACE", "sweets"), (-20.1, -35.6, "GRAND EMPORIUM", "apparel"),
              (-17.0, -82.8, "PENNY ARCADE", "cards"), (15.9, -101.4, "DISNEY & CO.", "plush"),
              (25.8, -40.5, "WORLD BAZAAR CONFECTIONERY", "sweets"), (23.7, -70.7, "HOUSE OF GREETINGS", "cards"),
              (56.8, -51.0, "EASTSIDE CAFE", "home"), (-43.0, -47.8, "CENTER STREET COFFEEHOUSE", "home"),
              (16.3, -89.6, "DISNEY GALLERY", "cards"), (-17.1, -71.6, "TOWN CENTER FASHIONS", "apparel"),
              (-17.3, -76.6, "HARRINGTON'S JEWELRY & WATCHES", "apparel"), (19.2, -113.3, "REFRESHMENT CORNER", "sweets"),
              (46.5, -111.0, "HOME STORE", "home"), (48.7, -77.0, "MAGIC SHOP", "cards"),
              (13.3, -28.9, "MAIN STREET DAILY", "cards"), (17.0, -79.5, "SILHOUETTE STUDIO", "cards"),
              (-26.1, -8.7, "CAMERA CENTER", "cards"), (50.7, -81.8, "GREAT AMERICAN WAFFLE CO.", "sweets"),
              (-45.6, -77.5, "TOY STATION", "plush"), (-34.4, -111.5, "SWEETHEART CAFE", "sweets"),
              (-39.3, -68.8, "BIBBIDI BOBBIDI BOUTIQUE", "apparel")]


def build_shops(seed=7):
    rng = random.Random(seed)
    used = set()
    for fid, p0, p1 in FRONTS:
        d = (p1[0] - p0[0], p1[1] - p0[1]); L = math.hypot(*d); ang = math.degrees(math.atan2(d[1], d[0]))
        widths = []
        first = SPECIAL.get((fid, 0)); last = SPECIAL.get((fid, -1))
        rest = L - (first["w"] if first else 0) - (last["w"] if last else 0)
        while rest > 0.1:
            wd = rng.choice([5.5, 6.5, 7.0, 8.0, 9.5])
            if rest - wd < 4.5:
                wd = rest
            widths.append(wd); rest -= wd
        seq = ([("S", first)] if first else []) + [("R", w_) for w_ in widths] + ([("S", last)] if last else [])
        with frame(f"FRONT_{fid}", p0[0], p0[1], ang):
            x = 0.0; prev = None
            for i, (kind, v) in enumerate(seq):
                if kind == "S":
                    st = dict(v); wd = st.pop("w")
                else:
                    st = random_style(rng, prev); wd = v
                prev = st["wall"]
                a_ = math.radians(ang); mx, my = p0[0] + (x + wd / 2) * math.cos(a_), p0[1] + (x + wd / 2) * math.sin(a_)
                best = min(((math.hypot(sx - mx, sy - my), k) for k, (sx, sy, _, _) in enumerate(REAL_SHOPS) if k not in used), default=None)
                if best and best[0] < 14.0:                  # the real shop on this front
                    used.add(best[1]); _, _, nm, th = REAL_SHOPS[best[1]]
                    st["sign"] = nm; st["theme"] = th
                # the room: CORNER m clear of each end of the front (the next front's shops reach back 9 m from the
                # corner), only 4 m deep within 9.2 m of an end, 7.5 m elsewhere
                rx0 = max(0.0, CORNER - x); rx1 = min(wd, L - CORNER - x)
                near_end = x < 9.2 or x + wd > L - 9.2
                room = (rx0, rx1, 4.0 if near_end else 7.5) if rx1 - rx0 >= 2.8 else None
                with frame(f"SHOP_{fid}_{i}", x, 0.0, 0.0):
                    shop(f"{fid}_{i}", wd, st, room)
                x += wd


# ---------------------------------------------------------------- the blocks' outer walls (seen from the plaza and the park)
BLOCKS = (365357846, 72216851, 196943265, 72216845)   # OSM: the four shop blocks either side of Main Street


def to_wb(p):
    a = math.radians(WB["ang"]); dx, dy = p[0] + 521.3, p[1] - 891.2
    return (dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a))


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1e-9
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - dx * t, p[1] - ay - dy * t)


def outer_run(name, L, H, wall, trim, rng):
    """One outside wall of a block (x 0..L, +y out): a plinth, arched ground-floor windows (some lit displays), a string
    course, upper windows with caps, pilasters, a bracketed cornice and a parapet -- the same family as the shop fronts."""
    P = {k: bmesh.new() for k in ("wall", "trim", "glass", "display")}
    bm_box(P["wall"], 0, L, -0.3, 0, 0, H)
    bm_box(P["trim"], 0, L, 0, 0.12, 0, 0.5)
    nb = max(1, round(L / 4.0)) if L >= 2.5 else 0
    for k in range(nb):
        x0, x1 = L * k / nb, L * (k + 1) / nb; m = (x0 + x1) / 2
        bm_box(P["trim"], x0, x0 + 0.35, 0, 0.14, 0, H - 0.4)
        if x1 - x0 > 2.2:
            bm_prism(P["trim"], arch_opening(m - 0.95, m + 0.95, 0.5, 2.9, 0.55, 12), 0.0, 0.1, "xz")
            bm_prism(P["display" if rng.random() < 0.4 else "glass"], arch_opening(m - 0.8, m + 0.8, 0.6, 2.85, 0.45, 10), 0.1, 0.12, "xz")
            for z0 in (4.6,) + ((7.4,) if H > 10 else ()):
                bm_box(P["trim"], m - 0.62, m + 0.62, 0, 0.09, z0 - 0.12, z0 + 1.95)
                bm_box(P["glass"], m - 0.5, m + 0.5, 0.09, 0.11, z0, z0 + 1.8)
                bm_box(P["trim"], m - 0.75, m + 0.75, 0, 0.28, z0 + 1.85, z0 + 2.05)
    bm_box(P["trim"], 0, L, 0, 0.12, 3.7, 3.95)
    bm_box(P["trim"], -0.05, L + 0.05, 0, 0.4, H - 0.4, H - 0.1)
    x = 0.4
    while x < L - 0.3:
        bm_box(P["trim"], x - 0.06, x + 0.06, 0, 0.34, H - 0.75, H - 0.4); x += 0.85
    bm_box(P["wall"], 0, L, -0.3, 0, H - 0.1, H + 0.7)
    bm_box(P["trim"], -0.05, L + 0.05, -0.35, 0.06, H + 0.7, H + 0.82)
    for k, bm_ in P.items():
        if not len(bm_.verts):
            bm_.free(); continue
        obj_bm(f"ST_WBZ_{name}_{k}", bm_, {"wall": wall, "trim": trim, "glass": "win_dark", "display": "display"}[k])


def build_block_walls():
    """Every edge of the four blocks that is not a shop front on the covered street gets an outer wall, and the block a
    flat roof at the OSM height (8.5 / 8.85 m) behind the shops' own fronts."""
    ways = {w["id"]: w for w in json.loads((ROOT / "plateau_data" / "disneyland_osm.json").read_text(encoding="utf-8"))["ways"]}
    rng = random.Random(5)
    walk = WALK + [WALK[0]]
    for bid in BLOCKS:
        w = ways.get(bid)
        if not w:
            continue
        pts = [to_wb(p) for p in w["pts"][:-1]]
        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
        if area > 0:
            pts = pts[::-1]                               # clockwise: each wall's +y is outside
        H = float(str(w["tags"].get("height", "8.5")).replace("m", ""))
        prism(f"ST_WBZ_block{bid}_roof", [pts], H - 0.2, H, "shingle")
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if L < 0.8 or min(seg_dist(mid, walk[j], walk[j + 1]) for j in range(len(walk) - 1)) < 2.5:
                continue                                  # a shop front on the street (the shops build those)
            ny = (b[0] - a[0]) / L                         # the wall's outward normal's y (towards the plaza: +y)
            if ny > 0.5 and mid[1] > -30.0:
                if 11.5 < abs(mid[0]) < 36.0 and abs(mid[1]) < 1.5:
                    continue                              # the arcade shops beside the entrance (ds_tdl_entrance.wb_shops)
                with frame(f"BLOCK_{bid}_{i}", a[0], a[1], math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))):
                    EN.arcade_front(f"block{bid}_{i}", 0.0, L)   # facing the plaza: the same arcade building (user, 2026-09-28)
                continue
            wall = "w_" + rng.choice(list(PALETTE)); trim = "t_" + rng.choice(["white", "cream", "teal", "dkgreen", "maroon"])
            with frame(f"BLOCK_{bid}_{i}", a[0], a[1], math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))):
                outer_run(f"block{bid}_{i}", L, H, wall, trim, rng)


# ================================================================ 3. paving and street furniture
def build_street():
    prism("ST_WBZ_walk", [WALK], -0.02, 0.04, "walk")
    bm, bme = bmesh.new(), bmesh.new()
    rw, cw = 7.5, 3.6                                     # half the carriageway: Main Street, Center Street
    bm_box(bm, -rw, rw, END_Y, WB_BACK, 0.04, 0.05)       # Main Street
    bm_box(bm, -CROSS["half"], CROSS["half"], CROSS["yc"] - cw, CROSS["yc"] + cw, 0.042, 0.053)   # a little above Main Street's (no coincident faces)
    for s in (-1, 1):
        bm_box(bme, s * rw - 0.15, s * rw + 0.15, END_Y, WB_BACK, 0.04, 0.055)
    for p0, p1, _ in ARMS:                               # the arms' carriageways
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy); nx, ny = -dy / L * cw, dx / L * cw
        q0 = (p0[0] - dx / L * 1.5, p0[1] - dy / L * 1.5)
        bm_prism(bm, [(q0[0] + nx, q0[1] + ny), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny), (q0[0] - nx, q0[1] - ny)], 0.043, 0.054, "xy")
    obj_bm("ST_WBZ_road", bm, "road"); obj_bm("ST_WBZ_edging", bme, "edging")
    # lamp posts along the kerbs, street clocks at the crossing, trees in planters and benches near the castle end
    bmp, bml, bmc, bmf, bmt, bmw = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    posts = [(s * (rw + 1.1), y) for s in (-1, 1) for y in (-16.0, -29.0, -76.0, -90.0, -102.0)]
    for x, y in posts:
        bm_lathe(bmp, [(0, 0), (0.2, 0), (0.2, 0.3), (0.14, 0.5), (0.09, 0.9), (0.07, 3.5), (0.12, 3.6), (0.06, 3.7), (0, 3.7)], 10, T(x, y, 0.04))
        bm_lathe(bmp, [(0, 0), (0.1, 0), (0.22, 0.12), (0.22, 0.62), (0.26, 0.66), (0.08, 0.85), (0, 0.95)], 6, T(x, y, 3.74))
        globe_lamp_bm(bml, x, y, 4.1, 0.16)
    for x, y in ((9.6, CROSS["y0"] + 3.5), (-9.6, CROSS["y1"] - 3.5)):   # street clocks
        bm_lathe(bmp, [(0, 0), (0.3, 0), (0.3, 0.4), (0.18, 0.6), (0.12, 1.2), (0.1, 3.3), (0.2, 3.4), (0, 3.4)], 12, T(x, y, 0.04))
        bm_lathe(bmp, [(0, 0), (0.62, 0), (0.62, 0.34), (0, 0.34)], 24, T(x, y + 0.17, 4.05) @ R(math.pi / 2, "X"))
        for s in (-1, 1):
            bm_lathe(bmc, [(0, 0), (0.5, 0), (0.5, 0.02), (0, 0.02)], 24, T(x, y + s * 0.18, 4.05) @ R(-s * math.pi / 2, "X"))
            for k in range(12):
                a = 2 * math.pi * k / 12
                bm_box(bmp, x + 0.42 * math.cos(a) - 0.02, x + 0.42 * math.cos(a) + 0.02, y + s * 0.2 - 0.01, y + s * 0.2 + 0.01, 4.05 + 0.42 * math.sin(a) - 0.04, 4.05 + 0.42 * math.sin(a) + 0.04)
            bm_box(bmp, x - 0.015, x + 0.015, y + s * 0.21 - 0.01, y + s * 0.21 + 0.01, 4.05, 4.36)
            bm_box(bmp, x - 0.015, x + 0.2, y + s * 0.21 - 0.01, y + s * 0.21 + 0.01, 4.035, 4.065)
        bm_lathe(bmp, [(0, 0), (0.1, 0), (0.05, 0.3), (0, 0.4)], 8, T(x, y, 4.72))
    for x, y in ((-9.4, -84.0), (9.4, -84.0), (-9.4, -97.0), (9.4, -97.0)):   # trees in planters
        bm_box(bmw, x - 0.8, x + 0.8, y - 0.8, y + 0.8, 0.04, 0.7)
        bm_lathe(bmt, [(0, 0), (0.1, 0), (0.07, 2.4), (0, 2.4)], 8, T(x, y, 0.7))
        for dx, dy, dz, r in ((0, 0, 3.3, 1.1), (0.6, 0.3, 2.9, 0.8), (-0.5, -0.4, 3.0, 0.8), (0.1, -0.6, 3.8, 0.7)):
            globe_lamp_bm(bmf, x + dx, y + dy, dz, r)
    for x, y in ((-10.8, -22.0), (10.6, -35.0), (-10.2, -79.0), (10.2, -91.0)):     # benches
        s = 1 if x < 0 else -1
        bm_box(bmp, x - 0.3, x + 0.3, y - 0.9, y - 0.8, 0.04, 0.45); bm_box(bmp, x - 0.3, x + 0.3, y + 0.8, y + 0.9, 0.04, 0.45)
        bm_box(bmw, x - 0.28, x + 0.28, y - 0.95, y + 0.95, 0.42, 0.47)
        bm_box(bmw, x - s * 0.28 - 0.04, x - s * 0.28 + 0.04, y - 0.95, y + 0.95, 0.5, 0.9)
    obj_bm("ST_WBZ_furniture", bmp, "hall_iron", smooth=True); obj_bm("ST_WBZ_lamps", bml, "lamp", smooth=True)
    obj_bm("ST_WBZ_clock_faces", bmc, "clock"); obj_bm("ST_WBZ_tree_crowns", bmf, "leaf", smooth=True)
    obj_bm("ST_WBZ_trunks", bmt, "wood"); obj_bm("ST_WBZ_planters_benches", bmw, "wood")


# ================================================================ scene
def wbp(lx, ly):
    a = math.radians(WB["ang"])
    return (WB["x"] + lx * math.cos(a) - ly * math.sin(a), WB["y"] + lx * math.sin(a) + ly * math.cos(a))


def cams():
    return {
        "wbz_street": ((*wbp(1.5, -13.0), 1.65), (*wbp(0.0, -100.0), 5.5), 20),     # towards the castle end
        "wbz_castle": ((*wbp(-2.0, -70.0), 1.65), (*wbp(0.0, END_Y), 6.0), 22),    # the three arches
        "wbz_crossing": ((*wbp(5.0, -30.0), 1.7), (*wbp(-14.0, -54.0), 6.0), 18),   # the towers and Center Street
        "wbz_corner": ((*wbp(-3.0, -26.0), 1.7), (*wbp(12.0, -38.0), 5.5), 20),     # the Confectionery corner
        "wbz_back": ((*wbp(0.0, -40.0), 1.6), (*wbp(0.0, WB_BACK), 6.5), 22),        # back towards the entrance
        "wbz_shopfront": ((*wbp(4.0, -80.0), 1.7), (*wbp(12.0, -87.0), 2.4), 24),   # the shopfronts on the east side
        "wbz_inside": ((*wbp(13.0, -88.0), 1.6), (*wbp(19.0, -85.0), 1.3), 16),    # inside a shop
        "wbz_aerial": ((*wbp(70.0, -10.0), 75.0), (*wbp(0.0, -58.0), 0.0), 32),
    }


def build(context=True):
    en_cams = EN.build(context)
    wbz_materials(B.M)
    t0 = time.time()
    with frame("WBZ_frame", WB["x"], WB["y"], WB["ang"]):
        build_roof()
        build_shops()
        build_block_walls()
        build_street()
    out = dict(en_cams)
    for name, (loc, tgt, lens) in cams().items():
        cam = bpy.data.cameras.new("CAM_" + name); cam.lens = lens; cam.clip_start = 0.05; cam.clip_end = 3000
        co = bpy.data.objects.new("CAM_" + name, cam); B.col.objects.link(co); co.parent = B.root
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        out[name] = co
    print(f"[world_bazaar] built in {time.time() - t0:.1f}s, {len(B.col.objects)} objects")
    return out


def export_objects(merged):
    """For the mock (export_models.py --parts tdl_world_bazaar): the street only (the entrance is its own part), one mesh
    per material ("WZ_<material>") in the DisneySea frame, heights on the datum as the entrance."""
    EN.build(context=False)
    before = set(B.col.objects)
    wbz_materials(B.M)
    with frame("WBZ_frame", WB["x"], WB["y"], WB["ang"]):
        build_roof()
        build_shops()
        build_block_walls()
        build_street()
    B.root.location = (EN.P0[0], EN.P0[1], 0.0)
    bpy.context.view_layer.update()
    groups = {}
    for o in B.col.objects:
        if o in before or o.type not in ("MESH", "CURVE", "FONT") or o.hide_render:
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if mats:
            groups.setdefault("WZ_" + mats[0].name[3:], []).append((o, EN.GROUND_DATUM))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="wbz_street,wbz_castle,wbz_crossing,wbz_corner,wbz_back,wbz_aerial")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=60)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    cams_ = build()
    ST.world_sky()
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.camera = cams_["wbz_street"]
    for c in B.cutters.objects:
        c.hide_set(True)
    ST.frame_view()
    for scr in bpy.data.screens:                          # open standing in Main Street, looking at the castle end
        for area in scr.areas:
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.shading.type = "MATERIAL"
                    r3 = sp.region_3d; r3.view_perspective = "CAMERA"
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "tdl_world_bazaar.blend").resolve()))
    print("[world_bazaar] saved", OUT / "tdl_world_bazaar.blend")
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        old = ST.OUT
        ST.OUT = OUT
        try:
            ST.render(cams_, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES", "world_bazaar")
        finally:
            ST.OUT = old


if __name__ == "__main__" and bpy is not None:
    main()
