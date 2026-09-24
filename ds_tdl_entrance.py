"""東京ディズニーランドのエントランス -- main entrance gates, the World Bazaar entrance and the plaza (Blender 5.2).

  blender -b --python ds_tdl_entrance.py -- --cams gate_in,gate_out,gates_arc,wb_porch,wb_sign,flowerbed,aerial --samples 32
  blender -b --python ds_tdl_entrance.py -- --cams none         # build + save the .blend only
  then open output/disneyland/entrance/tdl_entrance.blend (cameras CAM_*)

Reference videos (README; WALT., the same creator as the station video): 「Blenderでディズニーエントランスをモデリング」
(Shorts ARTD2DHt-x8, aNMlw8Z9Kjs). They model the World Bazaar entrance: the aerial photo as the plan guide, then the
sign ("Tokyo Disneyland" / "Welcome", light bulbs round it), the medallion, the pillars with a fleur-de-lis on the
pedestal, the beams, the arched frames, then the brick facade. This script keeps that order for the World Bazaar
entrance and builds the gates the same way: one bay first, then Array + Curve round the arc (as the station's fan).

Sources (looked at only; nothing copied into the repository):
  * OSM: the gate canopy (way 795427065, building=roof "東京ディズニーランド メインエントランス", an arc of radius
    54 .. 66 m round (-525, 897)), the World Bazaar buildings 365357846 / 72216851 (height 8.85 m) either side of Main
    Street, the Mickey flowerbed 1291649402, the Main Entrance footways (building_passage through the gates).
  * Wikimedia Commons "Tokyo Disneyland Main Entrance" (2023-11, 2025-06, CC BY 2.0 / CC BY-SA 4.0): the gates as
    rebuilt in 2023: a central pavilion (blue slate hip roof with a railed deck and two spires, a cream gable with lace
    bargeboards over a mint lattice, the red "Tokyo Disneyland" oval sign, a medallion), then long arcs of gate bays
    (cream square pillars with mint panels, fretwork, a small gable per bay with a numbered magenta medallion, slate
    roof with iron cresting and finials, green "ENTRANCE" boards, turnstile booths). "Tokyo Disneyland Entrance" (2013,
    CC BY 2.0): the World Bazaar porch (white columns on panelled pedestals, arches, balustrade, the red sign with the
    oval "Welcome" board, globe lamps) in front of the red brick facade (cream-framed arched windows, balconies with
    blue-green rails and flower boxes, the arch into Main Street). The Mickey flowerbed (purple and white).
  * GSI aerial photo (tools/aerial_overlay.py): the arc and the plaza.

Frame: local metres = the DisneySea frame minus P0 (-530, 915) (the plaza), no rotation; +X east, +Y north, ground 0
(the DEM here is -0.1 .. 0.07 m on the datum).

ESTIMATES (from photos, scaled with the OSM plan): gate pillars 3.7 m, beams 4.6 m, bay gables 6.1 m, main ridge 7.0 m;
central pavilion eaves 5.6 m, gable 9.0 m, deck 10.0 m, spires 12.5 m; World Bazaar porch columns 6.6 m, balustrade
8.4 m, facade cornice 8.4 m (OSM 8.85 m to the parapet), sign 4.4 .. 5.9 m. Bay counts, gate positions, the lattice,
the flowerbed's grass ring (radius 9 m) and the Mickey face pattern are drawn from the photos, not measured.
"""
import sys, math, argparse, pathlib, time

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix
except ImportError:
    bpy = bmesh = Vector = Matrix = None

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ds_tdl_station as ST
from ds_tdl_station import (B, box, prism, bm_box, bm_prism, bm_lathe, obj_bm, array_mod, arc_curve, bend, T, R,
                            seg_arc, arch_opening, arch_band, ring_sector, cutter, curve_obj, scroll_pts, column_bm,
                            globe_lamp_bm, text, hip, roof_obj, bevel_mod, _principled, _mottle)

OUT = ROOT / "output" / "disneyland" / "entrance"
P0 = (-530.0, 915.0)
GROUND_DATUM = 0.0
ARC = dict(cx=-525.0 - P0[0], cy=897.0 - P0[1], r=60.0, half=6.0, a_east=41.0, a_west=188.0, a_mid=110.0)
WB = dict(x=-521.3 - P0[0], y=891.2 - P0[1], ang=25.0)          # World Bazaar facade centre and its direction
FLOWERBED_OSM = [(-535.2, 925.8), (-536.1, 925.6), (-536.8, 926.0), (-537.0, 926.5), (-537.4, 926.2), (-537.9, 925.9),
                 (-538.8, 925.8), (-538.5, 925.4), (-538.4, 925.0), (-538.9, 924.3), (-539.8, 924.1), (-540.7, 924.4),
                 (-541.0, 924.9), (-541.1, 925.4), (-540.8, 926.0), (-540.2, 926.3), (-540.8, 926.9), (-541.0, 927.6),
                 (-541.1, 928.4), (-541.0, 929.1), (-540.6, 929.7), (-539.9, 930.2), (-539.2, 930.5), (-538.3, 930.4),
                 (-537.5, 930.1), (-537.0, 929.7), (-536.6, 929.2), (-536.4, 928.7), (-536.3, 928.2), (-535.9, 928.2),
                 (-535.4, 928.0), (-534.8, 927.3), (-534.8, 926.3)]


def extra_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    M["slate"] = P("st_slate_blue", (0.20, 0.27, 0.40), 0.45, Metallic=0.1)
    M["mint"] = P("st_mint", (0.50, 0.70, 0.63), 0.6)
    M["magenta"] = P("st_magenta", (0.50, 0.07, 0.26), 0.4)
    M["sign_red"] = P("st_sign_red", (0.40, 0.04, 0.06), 0.4, Coat_Weight=0.6)
    M["letters"] = P("st_letters", (0.95, 0.72, 0.12), 0.3, Metallic=0.6)
    M["booth"] = P("st_booth", (0.88, 0.83, 0.68), 0.5)
    M["green_sign"] = P("st_green_sign", (0.04, 0.36, 0.30), 0.4)
    M["bulb"] = P("st_bulb", (1.0, 0.92, 0.75), 0.3, Emission_Color=(1.0, 0.85, 0.55, 1), Emission_Strength=4.0)
    for key, name, col in (("flower_purple", "st_flower_purple", (0.26, 0.10, 0.50)), ("flower_white", "st_flower_white", (0.92, 0.92, 0.86)),
                           ("hedge", "st_hedge", (0.07, 0.20, 0.05))):   # flowers / clipped shrubs: speckled and bumpy
        mat, nt, b = _principled(name, col, 0.9); _mottle(nt, b, col, 40.0, 0.7, 0.5); M[key] = mat
    M["win_dark"] = P("st_win_dark", (0.05, 0.07, 0.09), 0.1, Coat_Weight=1.0)
    M["rail_blue"] = P("st_rail_blue", (0.08, 0.22, 0.24), 0.4, Metallic=0.6)
    M["flowers_red"] = P("st_flowers_red", (0.75, 0.10, 0.20), 0.8)
    M["blue_disc"] = P("st_blue_disc", (0.12, 0.25, 0.55), 0.4)
    return M


class frame:
    """Build into an Empty at (x, y) turned by ang (deg): the helpers parent to B.root, so swap it for a while."""
    def __init__(self, name, x, y, ang):
        self.e = bpy.data.objects.new(name, None); B.col.objects.link(self.e); self.e.parent = B.root
        self.e.location = (x, y, 0.0); self.e.rotation_euler = (0, 0, math.radians(ang))

    def __enter__(self):
        self.prev = B.root; B.root = self.e
        return self.e

    def __exit__(self, *a):
        B.root = self.prev


def arc_point(a_deg, r=None):
    r = ARC["r"] if r is None else r
    a = math.radians(a_deg)
    return ARC["cx"] + r * math.cos(a), ARC["cy"] + r * math.sin(a)


def lace(bm, x0, z0, x1, z1, depth, n, y0, y1):
    """Bargeboard with a scalloped lower edge from (x0, z0) to (x1, z1), in the xz plane, extruded y0..y1."""
    L = math.hypot(x1 - x0, z1 - z0); ux, uz = (x1 - x0) / L, (z1 - z0) / L; nx, nz = uz, -ux   # n points below
    top = [(x0, z0), (x1, z1)]
    bot = []
    for k in range(n, 0, -1):
        for j in range(7):
            t = (k - j / 6) / n
            s = math.sin(math.pi * j / 6)
            d = depth * (0.55 + 0.45 * s)
            bot.append((x0 + ux * L * t + nx * d, z0 + uz * L * t + nz * d))
    bm_prism(bm, top + bot, y0, y1, "xz")


def text_mesh(name, body, size, loc, rot, mat, extrude=0.01):
    """A text object turned into a mesh object (text objects cannot take Array / Curve modifiers)."""
    t = text(name + "_font", body, size, loc, rot, mat, extrude)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(t.evaluated_get(dg))
    o = bpy.data.objects.new(name, me); B.col.objects.link(o); o.parent = t.parent
    o.location, o.rotation_euler = t.location.copy(), t.rotation_euler.copy()
    bpy.data.objects.remove(t)
    return o


def clip_to_convex(p, d, poly):
    """The part of the line p + t d inside the convex polygon (counter-clockwise), as (t0, t1) or None."""
    t0, t1 = -1e9, 1e9
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]; bx, bz = poly[(i + 1) % n]
        ex, ez = bx - ax, bz - az
        nx, nz = -ez, ex                                   # inward normal of a counter-clockwise edge
        den = nx * d[0] + nz * d[1]; num = nx * (p[0] - ax) + nz * (p[1] - az)
        if abs(den) < 1e-12:
            if num < 0:
                return None
            continue
        t = -num / den
        if den > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    return (t0, t1) if t1 > t0 else None


def lattice(bm, tri, y0, y1, step=0.45, w=0.035):
    """Diamond lattice: bars at +-45 deg clipped to a triangle in the xz plane, extruded y0..y1."""
    xs = [p[0] for p in tri]; zs = [p[1] for p in tri]
    for sgn in (1, -1):
        d = (1 / math.sqrt(2), sgn / math.sqrt(2))
        c = min(xs) - (max(zs) - min(zs)) - 1
        while c < max(xs) + (max(zs) - min(zs)) + 1:
            p = (c, min(zs))
            seg = clip_to_convex(p, d, tri)
            if seg:
                (a, b) = seg
                ax, az = p[0] + d[0] * a, p[1] + d[1] * a; bx, bz = p[0] + d[0] * b, p[1] + d[1] * b
                nx, nz = -d[1] * w / 2, d[0] * w / 2
                bm_prism(bm, [(ax + nx, az + nz), (bx + nx, bz + nz), (bx - nx, bz - nz), (ax - nx, az - nz)], y0, y1, "xz")
            c += step


# ================================================================ 1. the World Bazaar entrance (the video's order)
def build_sign(yf):
    """Red sign with scrolled ends and a gold frame, "Tokyo Disneyland"; the oval "Welcome" board below; light bulbs
    round the top with Array + Curve (video); faces +y at yf."""
    zb, zt, hw, rise = 4.95, 5.55, 3.3, 0.35
    top, (zc, Rr, half) = seg_arc(0.0, zt, 2 * hw, rise, 32)
    board = [(-hw, zb), (hw, zb)] + top
    prism("ST_WB_sign_board", [board], yf, yf + 0.12, "sign_red", "xz")
    frame_pts = [(-hw - 0.12, zb - 0.1), (hw + 0.12, zb - 0.1)] + [(x * (hw + 0.12) / hw, z + 0.1) for x, z in top]
    prism("ST_WB_sign_frame", [frame_pts], yf - 0.04, yf + 0.06, "gold", "xz")
    for s in (-1, 1):                                    # scrolled ends (volutes)
        P = [(s * (hw + 0.1 + a * 0.9), yf + 0.06, zb + 0.28 + z * 0.9) for a, z in scroll_pts(0.4, 0.3, 0.16, 0.08, 10)]
        curve_obj(f"ST_WB_sign_scroll{s}", P, "gold", 0.045)
    text("ST_WB_sign_text", "Tokyo Disneyland", 0.42, (0, yf + 0.13, 5.33), (math.pi / 2, 0, math.pi), "letters", 0.03)
    bm = bmesh.new(); bm_lathe(bm, [(0, 0), (1.0, 0), (1.0, 0.1), (0, 0.1)], 40, T(0, yf + 0.02, 4.6) @ R(-math.pi / 2, "X") @ Matrix.Diagonal((1.9, 0.33, 1.0, 1.0)))
    obj_bm("ST_WB_welcome_board", bm, "sign_red")
    bm = bmesh.new(); bm_lathe(bm, [(0.93, 0), (1.05, 0), (1.05, 0.12), (0.93, 0.12)], 40, T(0, yf + 0.01, 4.6) @ R(-math.pi / 2, "X") @ Matrix.Diagonal((1.9, 0.33, 1.0, 1.0)))
    obj_bm("ST_WB_welcome_rim", bm, "gold")
    font_italic = "C:/Windows/Fonts/georgiaz.ttf"
    t = text("ST_WB_welcome_text", "Welcome", 0.3, (0, yf + 0.13, 4.6), (math.pi / 2, 0, math.pi), "letters", 0.02)
    if pathlib.Path(font_italic).exists():
        t.data.font = bpy.data.fonts.load(font_italic, check_existing=True)
    # bulbs: one bulb, Array fitted to the frame's arc, Curve modifier (arc in the xz plane: stood up by rot)
    arc = arc_curve("ST_WB_bulbarc", Rr + 0.18, math.pi / 2 + half, math.pi / 2 - half, 33, (0, yf + 0.14, zc), (math.pi / 2, 0, 0))
    bm = bmesh.new(); bm_lathe(bm, [(0, -0.05), (0.05, 0), (0, 0.05)], 8, T(0.05, 0, 0))
    bulbs = obj_bm("ST_WB_bulbs", bm, "bulb", smooth=True)
    a = bulbs.modifiers.new("Array", "ARRAY"); a.fit_type = "FIT_CURVE"; a.curve = arc
    a.use_relative_offset = True; a.relative_offset_displace = (3.0, 0, 0)
    bend(bulbs, arc)
    b2 = box("ST_WB_bulbs_low", (-hw + 0.1, -hw + 0.18, yf + 0.13, yf + 0.2, zb - 0.06, zb + 0.02), "bulb")
    array_mod(b2, 23, (0.29, 0, 0))
    # the medallion above the sign (gold ring, blue disc)
    bm = bmesh.new(); bm_lathe(bm, [(0.34, 0), (0.46, 0), (0.46, 0.08), (0.34, 0.08)], 32, T(0, yf + 0.02, 6.25) @ R(-math.pi / 2, "X"))
    obj_bm("ST_WB_medallion_ring", bm, "gold")
    bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.35, 0), (0.35, 0.05), (0, 0.05)], 32, T(0, yf + 0.01, 6.25) @ R(-math.pi / 2, "X"))
    obj_bm("ST_WB_medallion", bm, "blue_disc")


def fleur(bm, x, y, z, s=0.25):
    """Fleur-de-lis relief on a pedestal face (three petals + band), facing +y."""
    pts = []
    for k in range(25):
        t = k / 24 * 2 * math.pi
        r = 0.5 + 0.5 * abs(math.cos(1.5 * t))
        pts.append((x + s * r * math.sin(t) * 0.6, z + s * (0.2 + r * math.cos(t) * 0.8)))
    bm_prism(bm, pts, y, y + 0.04, "xz")
    bm_box(bm, x - s * 0.45, x + s * 0.45, y, y + 0.05, z - s * 0.05, z + s * 0.08)


def build_world_bazaar():
    with frame("WB_frame", WB["x"], WB["y"], WB["ang"]):
        build_sign(5.3)                                   # 1. the sign (+ bulbs, medallion) first, as in the video
        # 2. pillars: panelled pedestal with a fleur-de-lis, slender shaft, capital; globe lamps on the inner pair
        xs = [-20.0, -12.5, -3.4, 3.4, 12.5, 20.0]
        bm_p, bm_f, bm_c = bmesh.new(), bmesh.new(), bmesh.new()
        for x in xs:
            for y in (0.45, 5.2):
                bm_box(bm_p, x - 0.55, x + 0.55, y - 0.55, y + 0.55, 0, 1.5)
                bm_box(bm_p, x - 0.62, x + 0.62, y - 0.62, y + 0.62, 1.5, 1.62)
                column_bm(bm_c, x, y, 1.62, 6.6 - 1.62, 0.2, 16)
                if y > 1:
                    fleur(bm_f, x, y + 0.55, 0.85)
        obj_bm("ST_WB_pedestals", bm_p, "trim"); obj_bm("ST_WB_fleurs", bm_f, "gold"); obj_bm("ST_WB_columns", bm_c, "trim", smooth=True)
        bm = bmesh.new()
        for x in (-3.4, 3.4):
            globe_lamp_bm(bm, x, 5.2, 6.0, 0.22)
        obj_bm("ST_WB_lamps", bm, "lamp", smooth=True)
        # 3. beams: entablature, frieze panels (one + Array), cornice, balustrade (balusters: one + Array)
        box("ST_WB_entablature", [(-20.8, 20.8, -0.2, 5.8, 6.6, 7.4), (-21.0, 21.0, -0.2, 6.0, 7.4, 7.6)], "trim", 0.02)
        pnl = box("ST_WB_frieze", (-20.0, -18.6, 5.8, 5.84, 6.75, 7.25), "cream"); array_mod(pnl, 21, (1.9, 0, 0))
        box("ST_WB_balustrade", [(-21.0, 21.0, 5.55, 5.95, 8.3, 8.45), (-21.0, 21.0, 5.55, 5.95, 7.6, 7.72)] +
            [(x - 0.3, x + 0.3, 5.45, 6.05, 7.6, 8.6) for x in xs], "trim")
        bal = box("ST_WB_balusters", (-20.6, -20.5, 5.7, 5.8, 7.72, 8.3), "trim"); array_mod(bal, 140, (0.295, 0, 0))
        box("ST_WB_porch_ceiling", (-20.8, 20.8, -0.2, 5.8, 6.5, 6.6), "trim")
        # 4. arched frames between the columns: fretwork plates with segmental openings, rings in the spandrels
        bm = bmesh.new(); bmr = bmesh.new()
        for a, b in zip(xs[:-1], xs[1:]):
            pts, _ = seg_arc((a + b) / 2, 5.4, b - a - 0.4, min(1.0, (b - a) / 6), 20)
            bm_prism(bm, [(b - 0.2, 6.6), (a + 0.2, 6.6)] + pts[::-1], 5.15, 5.25, "xz")
            for cx in (a + 0.9, b - 0.9):
                bm_lathe(bmr, [(0.16, 0), (0.22, 0), (0.22, 0.06), (0.16, 0.06)], 16, T(cx, 5.27, 6.25) @ R(-math.pi / 2, "X"))
        obj_bm("ST_WB_arches", bm, "trim"); obj_bm("ST_WB_rings", bmr, "trim")
        # 5. the brick facade behind: arched ground floor, balconies, paired arched windows, pilasters, cornice
        fw = box("ST_WB_facade", (-22.0, 22.0, -14.0, 0.0, 0.0, 8.4), "brick")
        bays = [-16.0, -8.0, 0.0, 8.0, 16.0]
        ground = [arch_opening(x - (2.2 if x == 0 else 1.6), x + (2.2 if x == 0 else 1.6), -1, 2.9, 0.9, 16) for x in bays]
        upper = [arch_opening(x + dx - 0.45, x + dx + 0.45, 4.6, 6.2, 0.45, 12) for x in bays for dx in (-0.6, 0.6)]
        cutter("ST_WB_cut_ground", ground, fw, "xz", (-0.6, 0.6))
        cutter("ST_WB_cut_passage", [ground[2]], fw, "xz", (-14.5, 0.6))
        cutter("ST_WB_cut_upper", upper, fw, "xz", (-0.3, 0.6))
        box("ST_WB_shopfronts", [(x - 1.5, x + 1.5, -0.45, -0.4, 0, 3.6) for x in bays if x != 0], "win_dark")
        box("ST_WB_windows", [(x + dx - 0.45, x + dx + 0.45, -0.22, -0.18, 4.6, 6.7) for x in bays for dx in (-0.6, 0.6)], "win_dark")
        prism("ST_WB_arch_bands", [arch_band(x - (2.2 if x == 0 else 1.6), x + (2.2 if x == 0 else 1.6), 2.9, 0.9, 0.35, 16, leg=0.2) for x in bays]
              + [arch_band(x - 1.15, x + 1.15, 6.2, 0.7, 0.2, 14, leg=0.15) for x in bays], 0.0, 0.1, "trim", "xz")
        box("ST_WB_pilasters", [(x - 0.35, x + 0.35, 0.0, 0.18, 0.0, 8.4) for x in (-20, -12, -4, 4, 12, 20)], "trim", 0.02)
        box("ST_WB_courses", [(-22.2, 22.2, -0.1, 0.22, 3.9, 4.15), (-22.3, 22.3, -0.1, 0.35, 8.0, 8.45), (-22.4, 22.4, -0.1, 0.4, 8.45, 8.6)], "trim", 0.02)
        box("ST_WB_parapet", (-22.0, 22.0, -0.3, 0.0, 8.6, 9.3), "brick")
        # balconies under the upper windows: slab, corbels, blue-green rails, flower boxes
        box("ST_WB_balcony_slabs", [(x - 1.35, x + 1.35, 0.0, 0.75, 4.2, 4.35) for x in bays], "trim", 0.02)
        box("ST_WB_balcony_corbels", [(x + dx - 0.08, x + dx + 0.08, 0.0, 0.6, 3.95, 4.2) for x in bays for dx in (-1.1, 1.1)], "trim")
        box("ST_WB_balcony_rails", [(x - 1.35, x + 1.35, 0.68, 0.75, 4.35, 5.25) for x in bays] +
            [(x + s * 1.35 - 0.04, x + s * 1.35 + 0.03, 0.0, 0.75, 4.35, 5.25) for x in bays for s in (-1, 1)], "rail_blue")
        box("ST_WB_flower_boxes", [(x - 1.2, x + 1.2, 0.5, 0.68, 4.9, 5.2) for x in bays], "flowers_red")
        bm = bmesh.new()                                  # passage ceiling / Main Street glimpse
        bm_box(bm, -2.2, 2.2, -14.0, 0.0, 3.75, 3.85)
        obj_bm("ST_WB_passage_ceiling", bm, "trim")
        bm = bmesh.new()
        for x in bays:
            for s in (-1, 1):
                if x == 0:
                    continue
                globe_lamp_bm(bm, x + s * 2.1, 0.35, 3.3, 0.12)
        obj_bm("ST_WB_wall_lamps", bm, "lamp", smooth=True)
        box("ST_WB_porch_floor", (-21.0, 21.0, -0.2, 6.2, 0.0, 0.05), "tile")


# ================================================================ 2. the main entrance gates: one bay + Array + Curve
def bay_module(name, w, N, curve):
    """One gate bay in curve coordinates (x along the arc 0..w, y towards the plaza, z up), then Array N and bend."""
    h = ARC["half"]
    parts = {k: bmesh.new() for k in ("trim", "mint", "slate", "iron", "booth", "green_sign", "lamp", "magenta", "gold")}
    for s in (-1, 1):
        y = s * (h - 0.6)
        bm_box(parts["trim"], 0, w, y - 0.3, y + 0.3, 3.7, 4.55)                        # beam
        pts, _ = seg_arc(w / 2, 3.25, w - 0.7, 0.35, 16)                                   # fretwork plate
        bm_prism(parts["trim"], [(w - 0.35, 3.7), (0.35, 3.7)] + pts[::-1], y - 0.05, y + 0.05, "xz")
        ga, gz = w * 0.42, 6.1                                                              # the bay's gable
        yf = y + s * 0.32
        bm_prism(parts["trim"], [(w / 2 - ga, 4.55), (w / 2 + ga, 4.55), (w / 2, gz)], min(yf, yf - s * 0.12), max(yf, yf - s * 0.12), "xz")
        bm_prism(parts["mint"], [(w / 2 - ga + 0.35, 4.72), (w / 2 + ga - 0.35, 4.72), (w / 2, gz - 0.28)], min(yf, yf + s * 0.02), max(yf, yf + s * 0.02), "xz")
        bm_lathe(parts["magenta"], [(0, 0), (0.28, 0), (0.28, 0.05), (0, 0.05)], 20, T(w / 2, yf + s * 0.03, 5.05) @ R(-s * math.pi / 2, "X"))
        bm_lathe(parts["gold"], [(0.28, 0), (0.34, 0), (0.34, 0.06), (0.28, 0.06)], 20, T(w / 2, yf + s * 0.03, 5.05) @ R(-s * math.pi / 2, "X"))
        lace(parts["trim"], w / 2 - ga - 0.1, 4.55, w / 2, gz + 0.05, 0.22, 5, min(yf, yf + s * 0.1), max(yf, yf + s * 0.1))
        lace(parts["trim"], w / 2, gz + 0.05, w / 2 + ga + 0.1, 4.55, 0.22, 5, min(yf, yf + s * 0.1), max(yf, yf + s * 0.1))
        bm_lathe(parts["gold"], [(0, 0), (0.07, 0), (0.05, 0.3), (0.09, 0.35), (0, 0.7)], 8, T(w / 2, yf, gz))  # finial
        bm_box(parts["green_sign"], w / 2 - 0.85, w / 2 + 0.85, y + s * 0.06, y + s * 0.1, 2.85, 3.3)
        # roof: the main slope (eaves -> ridge) and the bay's small gable roof
        e_y, e_z, r_z = s * (h + 0.3), 4.55, 7.0
        v = [parts["slate"].verts.new(p) for p in ((0, e_y, e_z), (w, e_y, e_z), (w, 0, r_z), (0, 0, r_z))]
        parts["slate"].faces.new(v if s < 0 else v[::-1])
        yr = s * (h * (7.0 - 6.15) / (7.0 - 4.55))                                         # where the gable ridge meets the slope
        for x0, x1 in ((w / 2 - ga - 0.25, w / 2), (w / 2 + ga + 0.25, w / 2)):
            q = [parts["slate"].verts.new(p) for p in ((x0, yf + s * 0.25, 4.45), (x1, yf + s * 0.25, gz + 0.12), (x1, yr, gz + 0.12), (x0, yr, 4.45 + (7.0 - 4.45) * (1 - abs(yr) / h) * 0.0))]
            parts["slate"].faces.new(q)
    bm_box(parts["trim"], 0, w, -h + 0.2, h - 0.2, 3.95, 4.02)                               # ceiling
    for fx in (0.33, 0.67):                                                                 # turnstile booths
        bm_box(parts["booth"], w * fx - 0.2, w * fx + 0.2, -0.8, 0.8, 0, 1.05)
        bm_box(parts["mint"], w * fx - 0.22, w * fx + 0.22, -0.82, 0.82, 1.05, 1.1)
    globe_lamp_bm(parts["lamp"], w / 2, 0.0, 3.6, 0.2)
    cres = bmesh.new(); bm_lathe(cres, [(0, 0), (0.03, 0), (0.02, 0.3), (0.045, 0.34), (0, 0.46)], 6, T(0.2, 0, 7.0))
    out = []
    for k, bm in parts.items():
        o = obj_bm(f"ST_Gate_{name}_{k}", bm, k if k in B.M else "trim", recalc=(k != "slate"))
        if k == "slate":
            sd = o.modifiers.new("Solidify", "SOLIDIFY"); sd.thickness = 0.12; sd.offset = -1
        array_mod(o, N, (w, 0, 0)); bend(o, curve); out.append(o)
    c = obj_bm(f"ST_Gate_{name}_cresting", cres, "iron"); array_mod(c, max(1, int(w / 0.45)), (0.45, 0, 0), "Cres")
    array_mod(c, N, (w, 0, 0)); bend(c, curve)
    for s in (-1, 1):
        y = s * (h - 0.6) + s * 0.11
        rot = (math.pi / 2, 0, 0) if s < 0 else (math.pi / 2, 0, math.pi)
        tm = text_mesh(f"ST_Gate_{name}_entrance{s}", "ENTRANCE", 0.2, (w / 2, y, 3.02), rot, "white")
        tm.location = (0, 0, 0); tm.rotation_euler = (0, 0, 0)
        me = tm.data                                      # bake the placement into the vertices (bend() resets the transform)
        me.transform(Matrix.Translation((w / 2, y, 3.02)) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[0], 4, "X"))
        array_mod(tm, N, (w, 0, 0)); bend(tm, curve)
    # pillars: N + 1 of them (both faces), square with mint panels, pedestal and capital
    bmp, bmm = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        y = s * (h - 0.6)
        bm_box(bmp, -0.38, 0.38, y - 0.38, y + 0.38, 0, 0.6)
        bm_box(bmp, -0.28, 0.28, y - 0.28, y + 0.28, 0.6, 3.5)
        bm_box(bmp, -0.4, 0.4, y - 0.4, y + 0.4, 3.5, 3.72)
        for dy in (-1, 1):
            bm_box(bmm, -0.18, 0.18, y + dy * 0.28 - 0.01, y + dy * 0.28 + 0.01, 0.9, 3.2)
    for k, bm in (("pillars", bmp), ("panels", bmm)):
        o = obj_bm(f"ST_Gate_{name}_{k}", bm, "trim" if k == "pillars" else "mint")
        array_mod(o, N + 1, (w, 0, 0)); bend(o, curve)
    return out


def pavilion(name, a_deg, w, d, eave, apex, deck=None, sign=False, spires=False):
    """A pavilion on the arc at angle a_deg: x along the arc, y towards the plaza. Gables on both faces."""
    x0, y0 = arc_point(a_deg)
    with frame(f"PAV_{name}", x0, y0, a_deg + 90.0):
        hw, hd = w / 2, d / 2
        bm = bmesh.new(); bmm = bmesh.new()
        piers = [(sx * (hw - 0.55), sy * (hd - 0.55)) for sx in (-1, 1) for sy in (-1, 1)]
        piers += [(sx * hw * 0.38, sy * (hd - 0.45)) for sx in (-1, 1) for sy in (-1, 1)]
        for px, py in piers:
            bm_box(bm, px - 0.5, px + 0.5, py - 0.5, py + 0.5, 0, 0.7)
            bm_box(bm, px - 0.4, px + 0.4, py - 0.4, py + 0.4, 0.7, eave - 0.9)
            bm_box(bm, px - 0.55, px + 0.55, py - 0.55, py + 0.55, eave - 0.9, eave - 0.7)
            for dx in (-1, 1):
                bm_box(bmm, px + dx * 0.4 - 0.01, px + dx * 0.4 + 0.01, py - 0.22, py + 0.22, 1.1, eave - 1.3)
        obj_bm(f"ST_Pav_{name}_piers", bm, "trim"); obj_bm(f"ST_Pav_{name}_panels", bmm, "mint")
        box(f"ST_Pav_{name}_entablature", [(-hw, hw, -hd, -hd + 0.6, eave - 0.7, eave), (-hw, hw, hd - 0.6, hd, eave - 0.7, eave),
                                            (-hw, -hw + 0.6, -hd, hd, eave - 0.7, eave), (hw - 0.6, hw, -hd, hd, eave - 0.7, eave)], "trim", 0.02)
        box(f"ST_Pav_{name}_ceiling", (-hw, hw, -hd, hd, eave - 0.72, eave - 0.68), "trim")
        bm = bmesh.new()
        for s in (-1, 1):                                 # fretwork in the openings
            for a, b in ((-hw + 1.05, -hw * 0.38 - 0.4), (-hw * 0.38 + 0.4, hw * 0.38 - 0.4), (hw * 0.38 + 0.4, hw - 1.05)):
                pts, _ = seg_arc((a + b) / 2, eave - 1.3, b - a, min(0.6, (b - a) / 5), 18)
                bm_prism(bm, [(b, eave - 0.7), (a, eave - 0.7)] + pts[::-1], s * (hd - 0.35) - 0.05, s * (hd - 0.35) + 0.05, "xz")
        obj_bm(f"ST_Pav_{name}_fretwork", bm, "trim")
        # gables on both faces: frame, mint tympanum, arch round the sign, lace bargeboards, finial
        gw = hw * 0.72
        bmt, bmg, bml = bmesh.new(), bmesh.new(), bmesh.new()
        for s in (-1, 1):
            yf = s * (hd + 0.2)
            y_in = yf - s * 0.25
            bm_prism(bmt, [(-gw, eave), (gw, eave), (0, apex)], min(yf, y_in), max(yf, y_in), "xz")
            bm_prism(bmg, [(-gw + 0.5, eave + 0.15), (gw - 0.5, eave + 0.15), (0, apex - 0.4)], min(yf, yf + s * 0.03), max(yf, yf + s * 0.03), "xz")
            lattice(bml, [(-gw + 0.55, eave + 0.2), (gw - 0.55, eave + 0.2), (0, apex - 0.45)], min(yf + s * 0.03, yf + s * 0.06), max(yf + s * 0.03, yf + s * 0.06))
            bm_prism(bmt, arch_band(-gw * 0.55, gw * 0.55, eave + 0.15, gw * 0.5, 0.18, 18), min(yf, yf + s * 0.06), max(yf, yf + s * 0.06), "xz")
            for xa, za, xb, zb in ((-gw - 0.35, eave - 0.1, 0, apex + 0.15), (0, apex + 0.15, gw + 0.35, eave - 0.1)):
                lace(bml, xa, za, xb, zb, 0.32, 7, min(yf, yf + s * 0.12), max(yf, yf + s * 0.12))
            bm_lathe(bml, [(0, 0), (0.1, 0), (0.07, 0.5), (0.12, 0.55), (0, 1.1)], 8, T(0, yf, apex + 0.1))
        obj_bm(f"ST_Pav_{name}_gable", bmt, "trim"); obj_bm(f"ST_Pav_{name}_tympanum", bmg, "mint"); obj_bm(f"ST_Pav_{name}_lace", bml, "trim")
        # roof: hip with a flat deck (or a point), and a cross gable over each face
        def roof(bm):
            ew, ed, top = hw + 0.9, hd + 0.9, (deck if deck else apex + 1.2)
            tw, td = (hw * 0.45, hd * 0.28) if deck else (0.2, 0.2)
            V = lambda x, y, z: bm.verts.new((x, y, z))
            a, b_, c, e = V(-ew, -ed, eave), V(ew, -ed, eave), V(ew, ed, eave), V(-ew, ed, eave)
            ta, tb, tc, te = V(-tw, -td, top), V(tw, -td, top), V(tw, td, top), V(-tw, td, top)
            for q in ((a, b_, tb, ta), (b_, c, tc, tb), (c, e, te, tc), (e, a, ta, te), (ta, tb, tc, te)):
                bm.faces.new(q)
            for s in (-1, 1):
                yf, yr = s * (hd + 0.45), s * (td * 0.5)
                for xe in (-(gw + 0.45), gw + 0.45):
                    q = [V(xe, yf, eave - 0.05), V(0, yf, apex + 0.1), V(0, yr, apex + 0.1), V(xe, yr, eave - 0.05)]
                    bm.faces.new(q)
        roof_obj(f"ST_Pav_{name}_roof", roof, "slate", 0.18)
        if deck:                                          # railing on the deck, spires
            tw, td = hw * 0.45, hd * 0.28
            box(f"ST_Pav_{name}_deckrail", [(-tw, tw, -td, -td + 0.05, deck + 0.8, deck + 0.86), (-tw, tw, td - 0.05, td, deck + 0.8, deck + 0.86),
                                            (-tw, -tw + 0.05, -td, td, deck + 0.8, deck + 0.86), (tw - 0.05, tw, -td, td, deck + 0.8, deck + 0.86)], "iron")
            for yy in (-td + 0.02, td - 0.02):
                bar = box(f"ST_Pav_{name}_deckbars{yy:+.0f}", (-tw, -tw + 0.03, yy - 0.015, yy + 0.015, deck, deck + 0.8), "iron")
                array_mod(bar, int(2 * tw / 0.15) + 1, (0.15, 0, 0))
        if spires:
            bm = bmesh.new()
            for sx in (-1, 1):
                bm_lathe(bm, [(0, 0), (0.18, 0), (0.18, 0.3), (0.1, 0.5), (0.14, 0.9), (0.04, 1.6), (0.02, 2.4), (0, 2.5)], 10, T(sx * hw * 0.42, 0, (deck or apex)))
            obj_bm(f"ST_Pav_{name}_spires", bm, "trim", smooth=True)
        if sign:                                          # the red oval "Tokyo Disneyland" sign and the medallion, both faces
            for s in (-1, 1):
                yf = s * (hd + 0.25)
                rot = (math.pi / 2, 0, math.pi) if s > 0 else (math.pi / 2, 0, 0)   # text faces +y / -y
                M = T(0, yf, eave + 1.05) @ R(-s * math.pi / 2, "X") @ Matrix.Diagonal((2.3, 0.55, 1.0, 1.0))
                bm = bmesh.new(); bm_lathe(bm, [(0, 0), (1.0, 0), (1.0, 0.12), (0, 0.12)], 40, M); obj_bm(f"ST_Pav_{name}_sign{s}", bm, "sign_red")
                bm = bmesh.new(); bm_lathe(bm, [(0.9, -0.02), (1.08, -0.02), (1.08, 0.16), (0.9, 0.16)], 40, M); obj_bm(f"ST_Pav_{name}_signrim{s}", bm, "trim")
                text(f"ST_Pav_{name}_signtext{s}", "Tokyo Disneyland", 0.36, (0, yf + s * 0.14, eave + 1.02), rot, "letters", 0.03)
                Mm = T(0, yf, eave + 2.25) @ R(-s * math.pi / 2, "X")
                bm = bmesh.new(); bm_lathe(bm, [(0.3, 0), (0.42, 0), (0.42, 0.1), (0.3, 0.1)], 28, Mm); obj_bm(f"ST_Pav_{name}_medring{s}", bm, "gold")
                bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.31, 0), (0.31, 0.05), (0, 0.05)], 28, Mm); obj_bm(f"ST_Pav_{name}_med{s}", bm, "blue_disc")
            for s in (-1, 1):
                b = box(f"ST_Pav_{name}_entrance{s}", (-hw * 0.38 - 2.3, -hw * 0.38 - 0.7, s * (hd - 0.3) - 0.03, s * (hd - 0.3) + 0.03, eave - 1.75, eave - 1.3), "green_sign")
                array_mod(b, 2, (hw * 0.76 + 3.0, 0, 0))
                rot = (math.pi / 2, 0, math.pi) if s > 0 else (math.pi / 2, 0, 0)
                tm = text_mesh(f"ST_Pav_{name}_entrance_text{s}", "ENTRANCE", 0.2, (-hw * 0.38 - 1.5, s * (hd - 0.3 + 0.04), eave - 1.52), rot, "white")
                array_mod(tm, 2, ((hw * 0.76 + 3.0) * (1 if s < 0 else -1), 0, 0))
        bm = bmesh.new()                                  # turnstiles under the pavilion
        for k in range(int(w / 1.4)):
            x = -hw + 0.9 + k * 1.4
            bm_box(bm, x - 0.2, x + 0.2, -0.8, 0.8, 0, 1.05)
        obj_bm(f"ST_Pav_{name}_booths", bm, "booth")


def build_gates():
    A = ARC; r = A["r"]
    mid_half = math.degrees(9.0 / r); end_w = 7.0; end_half = math.degrees(end_w / 2 / r)
    pavilion("Centre", A["a_mid"], 18.0, 14.0, 5.6, 9.0, deck=10.0, sign=True, spires=True)
    pavilion("East", A["a_east"] + end_half, end_w, 13.0, 4.6, 7.0)
    pavilion("West", A["a_west"] - end_half, end_w, 13.0, 4.6, 7.0)
    for name, a0, a1 in (("East", A["a_east"] + 2 * end_half, A["a_mid"] - mid_half), ("West", A["a_mid"] + mid_half, A["a_west"] - 2 * end_half)):
        L = math.radians(a1 - a0) * r; N = max(1, round(L / 6.0)); w = L / N
        curve = arc_curve(f"ST_Gate_{name}_arc", r, math.radians(a0), math.radians(a1), 97, (A["cx"], A["cy"], 0.0), (0, 0, 0))
        bay_module(name, w, N, curve)


# ================================================================ 3. the Mickey flowerbed (checked against the photos)
# Photos (Commons "Tokyo Disneyland Main Entrance" 2023-11, night view towards World Bazaar): an oval bed between the
# gates and World Bazaar. From outside in: a low dark-green iron fence with arched panels, a sloping bank of clipped
# shrubs, a red brick edging band, then a lawn tilted towards the gates (high at the World Bazaar side) so that the
# whole Mickey face reads from the entrance: white flowers for the face, purple for the head, ears, eyes, nose and
# smile; red and white flowers beside it. The OSM polygon (1291649402, about 6 m) is only the face's position; the
# size is scaled from the photo against the World Bazaar facade (ESTIMATE): fence 41 x 27 m, lawn 29 x 15 m, lawn
# 0.6 m high at the front edge rising to 3.8 m at the back (12 deg), so the whole face shows from the gates.
BED = dict(x=-538.0 - P0[0], y=927.3 - P0[1] - 1.0, ang=205.0,     # local +X: left to right for a guest at the gates,
           tilt=12.0, zc=2.2,                                         # local +Y: away from the gates (towards World Bazaar)
           fence=(20.5, 13.5), bank=(16.2, 9.2), brick=(15.8, 8.8), lawn=(14.6, 7.6))


def bed_cam(dist, h, lens):
    a = math.radians(BED["ang"]); back = (-math.sin(a), math.cos(a))      # local +Y in the plan
    return ((BED["x"] - back[0] * dist, BED["y"] - back[1] * dist, h), (BED["x"], BED["y"], 0.9), lens)


def ellipse(rx, ry, n=96, cx=0.0, cy=0.0):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def ellipse_curve(name, rx, ry, n=129, loc=(0, 0, 0), rot=(0, 0, 0)):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.twist_mode = "Z_UP"
    sp = cu.splines.new("POLY"); sp.points.add(n - 1)
    for i, pt in enumerate(sp.points):
        t = 2 * math.pi * i / (n - 1)
        pt.co = (rx * math.cos(t), ry * math.sin(t), 0, 1)
    o = bpy.data.objects.new(name, cu); B.col.objects.link(o); o.parent = B.root
    o.location = loc; o.rotation_euler = rot; o.hide_render = True
    return o, sum(math.hypot(rx * (math.cos(2 * math.pi * (i + 1) / (n - 1)) - math.cos(2 * math.pi * i / (n - 1))),
                             ry * (math.sin(2 * math.pi * (i + 1) / (n - 1)) - math.sin(2 * math.pi * i / (n - 1)))) for i in range(n - 1))


def band(outer, inner):
    """Two closed rings (same count) -> a list of quads (a band), for bm_prism per quad."""
    n = len(outer)
    return [[outer[i], outer[(i + 1) % n], inner[(i + 1) % n], inner[i]] for i in range(n)]


def build_flowerbed():
    t = math.radians(BED["tilt"]); zc = BED["zc"]
    # (a) the parts on the tilted lawn plane: in a frame turned to face the gates and tilted about its X axis
    fr = bpy.data.objects.new("BED_tilted", None); B.col.objects.link(fr); fr.parent = B.root
    fr.location = (BED["x"], BED["y"], zc); fr.rotation_euler = (t, 0, math.radians(BED["ang"]))
    prev = B.root; B.root = fr
    lx, ly = BED["lawn"]; bx, by = BED["brick"]
    prism("ST_Bed_lawn", [ellipse(lx, ly)], -0.3, 0.0, "grass")
    bm = bmesh.new()
    for q in band(ellipse(bx, by), ellipse(lx, ly)):
        bm_prism(bm, q, -0.3, 0.04, "xy")
    obj_bm("ST_Bed_brick_edging", bm, "brick")
    # the Mickey face, in flowers: purple head and ears, white face mask (lower oval + two lobes round the eyes),
    # purple eyes, nose and smile; red and white clumps on the right as in the photo
    fz = 0.02
    bm = bmesh.new()                                   # purple head and ears (each a little higher: no coincident faces)
    for k, e in enumerate((ellipse(9.2, 5.9, 72, 0.0, -0.3), ellipse(3.3, 2.7, 48, -7.6, 4.3), ellipse(3.3, 2.7, 48, 7.6, 4.3))):
        bm_prism(bm, e, fz, fz + 0.14 + 0.01 * k, "xy")
    obj_bm("ST_Bed_mickey_head", bm, "flower_purple")
    bm = bmesh.new()                                   # white face mask: lower oval + two lobes round the eyes
    for k, e in enumerate((ellipse(7.9, 3.9, 72, 0.0, -1.3), ellipse(2.6, 3.0, 40, -2.25, 1.1), ellipse(2.6, 3.0, 40, 2.25, 1.1))):
        bm_prism(bm, e, fz + 0.12, fz + 0.2 + 0.012 * k, "xy")
    obj_bm("ST_Bed_mickey_face", bm, "flower_white")
    feats = [ellipse(1.0, 1.9, 28, -1.4, 1.5), ellipse(1.0, 1.9, 28, 1.4, 1.5), ellipse(2.3, 1.35, 32, 0.0, -0.6)]
    smile = []
    for k in range(25):                                # the smile: a thick arc under the nose
        a = math.radians(200 + 140 * k / 24)
        smile.append((5.2 * math.cos(a), -0.4 + 3.6 * math.sin(a)))
    for k in range(24, -1, -1):
        a = math.radians(200 + 140 * k / 24)
        smile.append((4.2 * math.cos(a), -0.4 + 2.7 * math.sin(a)))
    feats.append(smile)
    prism("ST_Bed_mickey_features", feats, fz + 0.2, fz + 0.28, "flower_purple")
    prism("ST_Bed_red_flowers", [ellipse(1.9, 1.2, 32, 10.9, 0.9)], fz, fz + 0.3, "flowers_red")
    prism("ST_Bed_white_flowers", [ellipse(2.1, 1.25, 32, 12.4, -0.6)], fz, fz + 0.3, "flower_white")
    B.root = prev
    # (b) the shrub bank: from the ground at the fence up to the brick edging on the tilted plane (a loft)
    ca, sa = math.cos(math.radians(BED["ang"])), math.sin(math.radians(BED["ang"]))
    to_plan = lambda X, Y, Zl: (BED["x"] + X * ca - (Y * math.cos(t) - Zl * math.sin(t)) * sa,
                                BED["y"] + X * sa + (Y * math.cos(t) - Zl * math.sin(t)) * ca,
                                zc + Y * math.sin(t) + Zl * math.cos(t))
    kx, ky = BED["bank"]; fx_, fy_ = BED["fence"]
    n = 96
    bm = bmesh.new()
    outer = [bm.verts.new((BED["x"] + X * ca - Y * sa, BED["y"] + X * sa + Y * ca, 0.02)) for X, Y in ellipse(fx_ - 0.6, fy_ - 0.6, n)]
    mid = [bm.verts.new(to_plan(X, Y, -0.35)) for X, Y in ellipse((kx + fx_) / 2, (ky + fy_) / 2, n)]
    inner = [bm.verts.new(to_plan(X, Y, 0.02)) for X, Y in ellipse(kx, ky, n)]
    for ra, rb in ((outer, mid), (mid, inner)):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
    for i in range(n):                                 # lift the middle ring into a rounded shrub mass (never below the paving)
        v = mid[i]; v.co.z = max(v.co.z + 0.45, 0.4)
        inner[i].co.z = max(inner[i].co.z, 0.3)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    o = obj_bm("ST_Bed_shrubs", bm, "hedge", smooth=True, recalc=False)
    # (c) the fence round the bed: one panel (post, rails, bars, an arched band) + Array + Curve round the oval
    ring, L = ellipse_curve("ST_Bed_fence_path", fx_, fy_, 129, (BED["x"], BED["y"], 0.0), (0, 0, math.radians(BED["ang"])))
    N = int(L / 2.4); pw = L / N
    bm = bmesh.new()
    bm_box(bm, -0.05, 0.05, -0.05, 0.05, 0.0, 1.0)                         # post
    bm_lathe(bm, [(0, 0), (0.07, 0.02), (0.05, 0.1), (0, 0.13)], 8, T(0, 0, 1.0))
    bm_box(bm, 0.0, pw, -0.02, 0.02, 0.86, 0.92)                            # top rail
    bm_box(bm, 0.0, pw, -0.02, 0.02, 0.1, 0.15)                             # bottom rail
    for k in range(1, int(pw / 0.12)):
        bm_box(bm, k * 0.12 - 0.01, k * 0.12 + 0.01, -0.01, 0.01, 0.15, 0.86)
    for c0 in (0.0, pw / 2):                                                # two arches per panel
        pts, _ = seg_arc(c0 + pw / 4, 0.55, pw / 2 - 0.05, pw / 4 - 0.02, 12)
        outer_arc = [(x, z) for x, z in pts]; inner_arc = [(x, z - 0.05) for x, z in pts[::-1]]
        bm_prism(bm, outer_arc + inner_arc, -0.015, 0.015, "xz")
    fence = obj_bm("ST_Bed_fence", bm, "rail_blue")
    array_mod(fence, N, (pw, 0, 0)); bend(fence, ring)


# ================================================================ 4. the plaza: paving lines, lamps
def build_plaza(context=True):
    A = ARC
    old = B.col
    if context:
        ctx = bpy.data.collections.new("Context"); bpy.context.scene.collection.children.link(ctx); B.col = ctx
        box("CTX_ground", (-150, 150, -120, 150, -0.2, 0.0), "paving")
        B.col = old
    bm = bmesh.new()                                      # white lines: arcs and radial lines round the gates' centre
    for rr in (22.0, 38.0, 70.0, 78.0):
        bm_prism(bm, ring_sector(rr - 0.15, rr + 0.15, math.radians(A["a_east"]), math.radians(A["a_west"]), 97, A["cx"], A["cy"]), 0.0, 0.012, "xy")
    for k in range(12):
        a = math.radians(A["a_east"] + (A["a_west"] - A["a_east"]) * (k + 0.5) / 12)
        ux, uy = math.cos(a), math.sin(a); px, py = -uy * 0.12, ux * 0.12
        p0 = (A["cx"] + ux * 22, A["cy"] + uy * 22); p1 = (A["cx"] + ux * 52, A["cy"] + uy * 52)
        bm_prism(bm, [(p0[0] + px, p0[1] + py), (p1[0] + px, p1[1] + py), (p1[0] - px, p1[1] - py), (p0[0] - px, p0[1] - py)], 0.0, 0.012, "xy")
    obj_bm("ST_Plaza_lines", bm, "white")
    build_flowerbed()
    fx, fy = BED["x"], BED["y"]
    # lamp posts with four globes: round the plaza and either side of the central pavilion
    ca, sa = math.cos(math.radians(BED["ang"])), math.sin(math.radians(BED["ang"]))
    posts = [(fx + 23.5 * math.cos(t) * ca - 16.0 * math.sin(t) * sa, fy + 23.5 * math.cos(t) * sa + 16.0 * math.sin(t) * ca)
             for t in (0.35, 2.79, 3.49, 5.93)]   # round the bed, outside its fence
    for d in (-12.0, 12.0):
        a = math.radians(ARC["a_mid"]); t = (-math.sin(a), math.cos(a))
        for rr in (49.0, 71.0):
            posts.append((A["cx"] + rr * math.cos(a) + t[0] * d, A["cy"] + rr * math.sin(a) + t[1] * d))
    bmp, bmg = bmesh.new(), bmesh.new()
    for x, y in posts:
        bm_lathe(bmp, [(0, 0), (0.3, 0), (0.3, 0.4), (0.12, 0.6), (0.09, 3.4), (0.14, 3.6), (0, 3.7)], 12, T(x, y, 0))
        for k in range(4):
            a = k * math.pi / 2
            bm_box(bmp, x + 0.02 * math.cos(a) - 0.03, x + 0.45 * math.cos(a) + 0.03, y + 0.02 * math.sin(a) - 0.03, y + 0.45 * math.sin(a) + 0.03, 3.45, 3.52)
            globe_lamp_bm(bmg, x + 0.5 * math.cos(a), y + 0.5 * math.sin(a), 3.75, 0.2)
        globe_lamp_bm(bmg, x, y, 4.05, 0.22)
    obj_bm("ST_Plaza_lampposts", bmp, "iron", smooth=True); obj_bm("ST_Plaza_globes", bmg, "lamp", smooth=True)


# ================================================================ scene
def cams():
    a = math.radians(ARC["a_mid"]); pav = arc_point(ARC["a_mid"]); ou = (math.cos(a), math.sin(a))
    wd = (-math.sin(math.radians(WB["ang"])), math.cos(math.radians(WB["ang"])))
    wb = (WB["x"], WB["y"])
    return {
        "gate_out": ((pav[0] + ou[0] * 32, pav[1] + ou[1] * 32, 1.7), (pav[0], pav[1], 6.0), 24),
        "gate_in": ((pav[0] - ou[0] * 17, pav[1] - ou[1] * 17, 1.7), (pav[0], pav[1], 6.0), 20),
        "gates_arc": ((ARC["cx"] + 5, ARC["cy"] + 10, 2.0), (arc_point(160)[0], arc_point(160)[1], 4.0), 20),
        "wb_porch": ((wb[0] + wd[0] * 24, wb[1] + wd[1] * 24, 1.7), (wb[0] + wd[0] * 4, wb[1] + wd[1] * 4, 5.0), 26),
        "wb_sign": ((wb[0] + wd[0] * 10.5, wb[1] + wd[1] * 10.5, 1.5), (wb[0] + wd[0] * 5.3, wb[1] + wd[1] * 5.3, 5.6), 18),
        "flowerbed": bed_cam(17.0, 1.7, 16),              # from the gates' side, as the photos (the face reads upright)
        "flowerbed_top": bed_cam(26.0, 14.0, 26),
        "aerial": ((70.0, -70.0, 85.0), (-10.0, 10.0, 0.0), 30),
    }


def build(context=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    B.col = bpy.data.collections.new("TDL_Entrance"); sc.collection.children.link(B.col)
    B.cutters = bpy.data.collections.new("Cutters"); sc.collection.children.link(B.cutters)
    B.root = bpy.data.objects.new("TDL_Entrance", None); B.col.objects.link(B.root)
    B.hide = []
    B.M = extra_materials(ST.materials())
    t0 = time.time()
    build_world_bazaar()                                  # the video's subject, in its order (sign, pillars, beams, arches, facade)
    build_gates()
    build_plaza(context)
    out = {}                                              # (the cutters keep their frame as parent: they are in its coordinates)
    for name, (loc, tgt, lens) in cams().items():
        cam = bpy.data.cameras.new("CAM_" + name); cam.lens = lens; cam.clip_start = 0.05; cam.clip_end = 3000
        co = bpy.data.objects.new("CAM_" + name, cam); B.col.objects.link(co); co.parent = B.root
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        out[name] = co
    print(f"[entrance] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")
    return out


def export_objects(merged):
    """For the mock: no context, one mesh per material ("EN_<material>") in the DisneySea frame (heights on the datum)."""
    build(context=False)
    B.root.location = (P0[0], P0[1], 0.0)
    for o in B.col.objects:
        for m in o.modifiers:
            if m.type == "BEVEL":
                m.show_viewport = False
        if o.type == "CURVE" and o.data.bevel_depth > 0:
            o.data.bevel_resolution = 0; o.data.resolution_u = 4
    bpy.context.view_layer.update()
    groups = {}
    for o in B.col.objects:
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith("CAM_"):
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if mats:
            groups.setdefault("EN_" + mats[0].name[3:], []).append((o, GROUND_DATUM))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="gate_in,gate_out,gates_arc,wb_porch,wb_sign,flowerbed,aerial")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=60)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    cams_ = build()
    ST.world_sky()
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.camera = cams_["gate_in"]
    for c in B.cutters.objects:
        c.hide_set(True)
    ST.frame_view()
    for scr in bpy.data.screens:                          # look at the plaza when the file opens
        for area in scr.areas:
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.region_3d.view_location = (-5.0, 5.0, 3.0); sp.region_3d.view_distance = 140.0
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "tdl_entrance.blend").resolve()))
    print("[entrance] saved", OUT / "tdl_entrance.blend")
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        old = ST.OUT
        ST.OUT = OUT
        try:
            ST.render(cams_, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES", "entrance")
        finally:
            ST.OUT = old


if __name__ == "__main__" and bpy is not None:
    main()
