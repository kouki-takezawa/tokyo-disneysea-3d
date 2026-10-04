"""東京ディズニーランドのエントランス -- main entrance gates, the World Bazaar entrance and the plaza (Blender 5.2).

  blender -b --python src/ds_tdl_entrance.py -- --cams gate_in,gate_out,gates_arc,wb_photo,wb_front,wb_porch,wb_sign,flowerbed,aerial --samples 32
  blender -b --python src/ds_tdl_entrance.py -- --cams none         # build + save the .blend only
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
    CC BY 2.0) and "Tokyo Disneyland World Bazaar" (2023, Flickr via Commons): the World Bazaar front. The Mickey
    flowerbed (purple and white).
  * The user's photo of the World Bazaar entrance (2026-09-27), measured with the people in it taken as 1.70 m:
    the rebuild of section 1 (sizes there).
  * GSI aerial photo (tools/aerial_overlay.py): the arc and the plaza.

Frame: local metres = the DisneySea frame minus P0 (-530, 915) (the plaza), no rotation; +X east, +Y north, ground 0
(the DEM here is -0.1 .. 0.07 m on the datum).

ESTIMATES (from photos, scaled with the OSM plan): gate pillars 3.7 m, beams 4.6 m, bay gables 6.1 m, main ridge 7.0 m;
central pavilion eaves 5.6 m, gable 9.0 m, deck 10.0 m, spires 12.5 m. World Bazaar (measured on the user's photo,
section 1): portico bays 3.9 / 4.0 / 3.9 m, capitals 6.6 m, balustrade 9.56 m, sign 6.0 m wide at 5.2 .. 6.3 m; the
depths (portico 4.6 m, the glass hall's gable 4.8 m behind the wall) are from perspective. Bay counts, gate positions, the lattice,
the flowerbed's grass ring (radius 9 m) and the Mickey face pattern are drawn from the photos, not measured.
"""
import sys, math, json, random, argparse, pathlib, time

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix
except ImportError:
    bpy = bmesh = Vector = Matrix = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
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
    M["sign_red"] = P("st_sign_red", (0.42, 0.03, 0.14), 0.4, Coat_Weight=0.6)   # (R1 #15: crimson towards magenta; was 0.40, 0.04, 0.06)
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
    M["screen"] = P("st_screen", (0.05, 0.12, 0.20), 0.15, Emission_Color=(0.3, 0.6, 0.9, 1), Emission_Strength=0.6)
    M["mauve"] = P("st_mauve", (0.34, 0.09, 0.12), 0.6)                    # the World Bazaar shops' mansards (R1 #10: a little lighter)
    M["hall_iron"] = P("st_hall_iron", (0.10, 0.24, 0.22), 0.45, Metallic=0.5)   # (R1 S6: darker blue-green; was 0.15, 0.30, 0.28)
    M["hall_glass"] = ST.clear_glass("st_hall_glass", (0.70, 0.86, 0.82), 0.35)
    M["person"] = P("st_person", (0.22, 0.26, 0.36), 0.8)                  # 1.70 m scale figures (check renders only)
    # the World Bazaar front and the greeting plazas (2026-09-30, the user's photos)
    M["lace"] = P("st_lace", (0.93, 0.92, 0.88), 0.9)
    M["door_brown"] = P("st_door_brown", (0.16, 0.10, 0.07), 0.5)
    for k, col in (("poster1", (0.30, 0.36, 0.62)), ("poster2", (0.35, 0.55, 0.45)), ("poster3", (0.62, 0.30, 0.45))):
        M[k] = P("st_" + k, col, 0.4)
    M["bench_green"] = P("st_bench_green", (0.12, 0.25, 0.16), 0.5)
    M["cons_glass"] = ST.clear_glass("st_cons_glass", (0.80, 0.90, 0.92), 0.7)
    M["rail_teal"] = P("st_rail_teal", (0.40, 0.74, 0.70), 0.5)
    M["brick_paving"] = P("st_brick_paving", (0.55, 0.24, 0.15), 0.85)
    M["brick_paving2"] = P("st_brick_paving2", (0.60, 0.29, 0.18), 0.85)
    M["sign_face"] = P("st_sign_face", (0.86, 0.90, 0.88), 0.5)
    M["sign_ink"] = P("st_sign_ink", (0.10, 0.25, 0.30), 0.5)
    mat, nt, b = _principled("st_flowers_pink", (0.85, 0.40, 0.60), 0.9); _mottle(nt, b, (0.85, 0.40, 0.60), 40.0, 0.7, 0.5); M["flowers_pink"] = mat
    # video refinement R1 (docs/video_frames/refine_R1.md, 2026-10-04; v2 = the July daytime walk)
    for key, name, col in (("bed_lime", "st_bed_lime", (0.36, 0.52, 0.13)),          # #1 the summer Mickey: lime face
                           ("bed_olive", "st_bed_olive", (0.09, 0.17, 0.04)),        #    dark olive head, ears, features
                           ("bed_lawn", "st_bed_lawn", (0.20, 0.36, 0.06)),          # #2 plain lawn round the face
                           ("hedge_bright", "st_hedge_bright", (0.10, 0.27, 0.05))): # #4 the bed's bright clipped bank
        mat, nt, b = _principled(name, col, 0.9); _mottle(nt, b, col, 40.0, 0.7, 0.5); M[key] = mat
    M["bed_brick"] = P("st_bed_brick", (0.55, 0.23, 0.17), 0.85)                 # #3 the pinkish terracotta edging
    M["wine_floor"] = P("st_wine_floor", (0.34, 0.05, 0.06), 0.35)               # #19 the portico and passage floor
    M["ped_stone"] = P("st_ped_stone", (0.60, 0.50, 0.24), 0.6)                  # #17 #20 the olive-yellow pedestals
    M["bronze"] = P("st_bronze", (0.14, 0.10, 0.06), 0.4, Metallic=0.7)          # #21 the Sharing the Magic statue
    M["cons_dome"] = ST.clear_glass("st_cons_dome", (0.88, 0.82, 0.62), 0.6)     # #11 the conservatories' cream glass
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


def lace(bm, x0, z0, x1, z1, depth, n, y0, y1, plane="xz"):
    """Bargeboard with a scalloped lower edge from (x0, z0) to (x1, z1), in the xz plane (or yz), extruded y0..y1."""
    L = math.hypot(x1 - x0, z1 - z0); ux, uz = (x1 - x0) / L, (z1 - z0) / L; nx, nz = uz, -ux   # n points below
    top = [(x0, z0), (x1, z1)]
    bot = []
    for k in range(n, 0, -1):
        for j in range(7):
            t = (k - j / 6) / n
            s = math.sin(math.pi * j / 6)
            d = depth * (0.55 + 0.45 * s)
            bot.append((x0 + ux * L * t + nx * d, z0 + uz * L * t + nz * d))
    bm_prism(bm, top + bot, y0, y1, plane)


def bracket(bm, xp, x_out, z_top, drop, y, t=0.05, plane="xz"):
    """A scroll-cut corbel under a beam (photos: at every pillar head): the corner between the pillar face xp and the
    beam underside z_top, cut by a quarter circle, with a small curl at the tip; in the xz plane (or yz) at y."""
    s = 1 if x_out > xp else -1; L = abs(x_out - xp)
    pts = [(xp, z_top)] + [(x_out - s * L * math.sin(math.radians(a)), z_top - drop + drop * math.cos(math.radians(a))) for a in range(0, 91, 10)]
    bm_prism(bm, pts, y - t, y + t, plane)
    bm_lathe(bm, [(0, 0), (0.06, 0), (0.06, 2 * t + 0.02), (0, 2 * t + 0.02)], 8,
             (T(xp + s * 0.07, y - t - 0.01, z_top - drop + 0.07) @ R(-math.pi / 2, "X")) if plane == "xz"
             else (T(y - t - 0.01, xp + s * 0.07, z_top - drop + 0.07) @ R(math.pi / 2, "Y")))


def hexa(bm, P):
    """A closed six-faced solid from 8 corners: P[0:4] the bottom loop, P[4:8] the top loop above them."""
    v = [bm.verts.new(p) for p in P]
    for q in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v[i] for i in q])


def on_slope(bm, x0, x1, f0, f1, s, h, lift, t, eave_z=4.55, ridge_z=7.0):
    """A thin panel lying on a bay's main roof slope: f = 0 at the ridge .. 1 at the eaves (y = s (h + 0.3) f)."""
    e = h + 0.3; n = (0, s * (ridge_z - eave_z), e); L = math.hypot(n[1], n[2]); n = (0, n[1] / L, n[2] / L)
    def P(x, f, o):
        return (x, s * e * f + n[1] * o, ridge_z - (ridge_z - eave_z) * f + n[2] * o)
    hexa(bm, [P(x0, f0, lift), P(x1, f0, lift), P(x1, f1, lift), P(x0, f1, lift),
              P(x0, f0, lift + t), P(x1, f0, lift + t), P(x1, f1, lift + t), P(x0, f1, lift + t)])


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


# ================================================================ 1. the World Bazaar entrance (rebuilt 2026-09-27)
# Measured on the user's photo (people at the centre pedestals taken as 1.70 m -> 25 px/m on the portico face) and
# checked with Commons photos (the whole front at sunset, the centre bay head-on). Plan from OSM: the shops either
# side (365357846 / 72216851, 8.85 m) have their fronts on local y = 0 and leave a 24.5 m gap (x = -12.25 .. 12.25)
# for the entrance building; the Main Street footway starts at y = 4 .. 5.6, the front of the portico.
# Local frame: +x along the front (left to right seen from the plaza), +y towards the plaza, z up.
WB_C = dict(front=4.6, ped=1.2, cap=6.6, block=7.95, ent=8.72, rail=9.56)       # centre portico (3 bays of 3.9 / 4.0 m)
WB_W = dict(front=3.6, ped=1.0, cap=6.1, block=7.35, ent=8.1, rail=8.9)         # wing porticos (lower, set back)
WB_HALL = dict(w=24.5, y=-4.8, base=8.6, eave=12.1, ridge=16.2, back=-8.5)       # the glass hall's front gable
WB_BACK = -8.5                                   # the entrance building's Main Street face (the gable stands on its roof)


def wb_sign(yf):
    """The centre bay sign (photo): 6.0 m over the end scrolls, arched top at 6.3 m, straight bottom at 5.2 m, the
    "Welcome" cartouche 3.05 x 0.85 m below it (4.45 .. 5.3 m), light bulbs round the board (one bulb + Array + Curve,
    as the video), a globe lamp on each centre column at 4.7 m. Faces +y; its back is at yf."""
    hw, zb, zs, rise = 2.55, 5.2, 5.62, 0.55
    top, (zc, Rr, half) = seg_arc(0.0, zs, 2 * hw, rise, 33)
    board = [(-hw, zb), (hw, zb)] + top
    prism("ST_WB_sign_board", [board], yf + 0.04, yf + 0.14, "sign_red", "xz")
    # (R1 #15, v2 0:50: a broad cream border with a thin gold line inside it, round the crimson board)
    rim = lambda d: [(-hw - d, zb - d), (hw + d, zb - d)] + [(x * (hw + d) / hw, z + d) for x, z in top]
    prism("ST_WB_sign_rim", [rim(0.15)], yf, yf + 0.11, "trim", "xz")
    prism("ST_WB_sign_rim_gold", [rim(0.04)], yf + 0.02, yf + 0.13, "gold", "xz")
    prism("ST_WB_sign_moulding", [arch_band(-hw - 0.08, hw + 0.08, zs, rise, 0.13, 33, leg=0.3)], yf, yf + 0.16, "trim", "xz")
    for s in (-1, 1):                                    # the ends curl out and down into scrolls, with a red roundel
        P = [(s * (hw + 0.55 - a), yf + 0.08, zs - 0.42 + z) for a, z in scroll_pts(0.45, 0.42, 0.14, 0.08, 10)]
        curve_obj(f"ST_WB_sign_scroll{s}", P, "trim", 0.05)
        bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.2, 0), (0.2, 0.1), (0, 0.1)], 24, T(s * (hw + 0.12), yf + 0.04, zb + 0.12) @ R(-math.pi / 2, "X"))
        obj_bm(f"ST_WB_sign_roundel{s}", bm, "sign_red")
        bm = bmesh.new(); bm_lathe(bm, [(0.17, 0), (0.25, 0), (0.25, 0.12), (0.17, 0.12)], 24, T(s * (hw + 0.12), yf + 0.03, zb + 0.12) @ R(-math.pi / 2, "X"))
        obj_bm(f"ST_WB_sign_roundel_rim{s}", bm, "gold")
    # the lettering follows the arch a little (text -> mesh, then each vertex dropped along a flatter arc)
    tm = text_mesh("ST_WB_sign_text", "Tokyo Disneyland", 0.56, (0, yf + 0.15, 5.66), (math.pi / 2, 0, math.pi), "letters", 0.03)
    for v in tm.data.vertices:
        v.co.y += 0.3 * (math.sqrt(max(Rr * Rr - v.co.x * v.co.x, 0.0)) - Rr)
    arc = arc_curve("ST_WB_bulbarc", Rr - 0.09, math.pi / 2 + half * 0.97, math.pi / 2 - half * 0.97, 33, (0, yf + 0.15, zc), (math.pi / 2, 0, 0))
    bm = bmesh.new(); bm_lathe(bm, [(0, -0.035), (0.035, 0), (0, 0.035)], 8, T(0.035, 0, 0))
    bulbs = obj_bm("ST_WB_bulbs", bm, "bulb", smooth=True)
    a = bulbs.modifiers.new("Array", "ARRAY"); a.fit_type = "FIT_CURVE"; a.curve = arc
    a.use_relative_offset = True; a.relative_offset_displace = (3.2, 0, 0)
    bend(bulbs, arc)
    b2 = box("ST_WB_bulbs_low", (-hw + 0.1, -hw + 0.16, yf + 0.14, yf + 0.19, zb + 0.06, zb + 0.12), "bulb")
    array_mod(b2, 22, (0.235, 0, 0))
    # the "Welcome" cartouche: a squared oval (superellipse), in front of the board's lower edge
    def cart(a_, b_, n=64, e=3.0):
        return [(math.copysign(abs(math.cos(t)) ** (2 / e), math.cos(t)) * a_,
                 4.87 + math.copysign(abs(math.sin(t)) ** (2 / e), math.sin(t)) * b_) for t in (2 * math.pi * k / n for k in range(n))]
    prism("ST_WB_welcome_rim", [cart(1.6, 0.5)], yf + 0.14, yf + 0.21, "trim", "xz")         # (R1 #15: cream, a gold line in it)
    prism("ST_WB_welcome_rim_gold", [cart(1.5, 0.41)], yf + 0.15, yf + 0.235, "gold", "xz")
    prism("ST_WB_welcome_board", [cart(1.45, 0.36)], yf + 0.16, yf + 0.25, "sign_red", "xz")
    t = text("ST_WB_welcome_text", "Welcome", 0.32, (0, yf + 0.26, 4.86), (math.pi / 2, 0, math.pi), "letters", 0.02)
    if pathlib.Path("C:/Windows/Fonts/georgiaz.ttf").exists():
        t.data.font = bpy.data.fonts.load("C:/Windows/Fonts/georgiaz.ttf", check_existing=True)
    bm, bmi = bmesh.new(), bmesh.new()                  # globe lamps on the centre columns, below the scrolls
    for s in (-1, 1):
        globe_lamp_bm(bm, s * 2.2, yf + 0.25, 4.72, 0.2)
        bm_box(bmi, s * 2.2 - 0.03, s * 2.2 + 0.03, yf - 0.2, yf + 0.25, 4.45, 4.51)
        bm_lathe(bmi, [(0, 0), (0.07, 0), (0.05, 0.1), (0, 0.1)], 8, T(s * 2.2, yf + 0.25, 4.45))
    obj_bm("ST_WB_sign_lamps", bm, "lamp", smooth=True); obj_bm("ST_WB_sign_lamp_brackets", bmi, "iron")


def baluster_run(bm_t, bm_b, p0, p1, z0, z1, step=0.24):
    """Plinth, top rail and turned balusters from p0 to p1 (a run along x or along y)."""
    (x0, y0), (x1, y1) = p0, p1
    along_x = abs(y1 - y0) < 1e-6
    L = abs(x1 - x0) if along_x else abs(y1 - y0)
    def bx(a0, a1, w, za, zb):
        if along_x:
            bm_box(bm_t, min(x0, x1), max(x0, x1), y0 - w, y0 + w, za, zb)
        else:
            bm_box(bm_t, x0 - w, x0 + w, min(y0, y1), max(y0, y1), za, zb)
    bx(0, L, 0.16, z0, z0 + 0.14)
    bx(0, L, 0.18, z1 - 0.1, z1)
    h = z1 - 0.1 - (z0 + 0.14)
    prof = [(0, 0), (0.06, 0), (0.06, 0.06 * h), (0.035, 0.15 * h), (0.075, 0.45 * h), (0.035, 0.85 * h), (0.055, 0.92 * h), (0.055, h), (0, h)]
    n = int(L / step)
    for k in range(n):
        f = (k + 0.5) / n
        bm_lathe(bm_b, prof, 6, T(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, z0 + 0.14))


def wb_portico(name, piers, H, ends=(True, True)):
    """One portico: piers [(x, kind)] on the front line H["front"] (kind "pair": two slender columns side by side,
    "cluster": three), panelled pedestals, collared shafts, square panelled blocks, thin arches with fretwork
    (rings, C-scrolls, pendant drops), entablature, flat roof with a balustrade; ends: returns back to the wall."""
    yf = H["front"]; ped, cap, blk, ent, rail = H["ped"], H["cap"], H["block"], H["ent"], H["rail"]
    OFF = {"pair": [(-0.21, 0.0), (0.21, 0.0)], "cluster": [(-0.42, 0.06), (0.0, -0.24), (0.42, 0.06)]}
    PW = {"pair": (0.6, 0.55, 0.42), "cluster": (0.8, 0.6, 0.55)}              # pedestal half x / half y, block half
    bmp, bmc, bmr, bmk, bmy = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for x, kind in piers:
        px, py, pb = PW[kind]
        bm_box(bmy, x - px - 0.05, x + px + 0.05, yf - py - 0.05, yf + py + 0.05, 0, 0.2)      # pedestal: plinth, die, cap
        bm_box(bmp, x - px, x + px, yf - py, yf + py, 0.2, ped - 0.14)
        bm_box(bmp, x - px - 0.05, x + px + 0.05, yf - py - 0.05, yf + py + 0.05, ped - 0.14, ped)
        bm_box(bmy, x - px + 0.14, x + px - 0.14, yf + py, yf + py + 0.03, 0.36, ped - 0.3)     # raised panel
        for dx, dy in OFF[kind]:
            column_bm(bmc, x + dx, yf + dy, ped, cap - ped, 0.14, 12)
            for f in (0.36, 0.68):                                                              # collars on the shaft
                bm_lathe(bmr, [(0.12, 0), (0.18, 0.03), (0.18, 0.1), (0.12, 0.13)], 12, T(x + dx, yf + dy, ped + (cap - ped) * f))
        bm_box(bmp, x - pb - 0.06, x + pb + 0.06, yf - pb - 0.06, yf + pb + 0.06, cap, cap + 0.1)  # abacus, block
        bm_box(bmp, x - pb, x + pb, yf - pb, yf + pb, cap + 0.1, blk)
        bm_box(bmk, x - pb + 0.1, x + pb - 0.1, yf + pb, yf + pb + 0.03, cap + 0.3, blk - 0.2)
    obj_bm(f"ST_WB_{name}_piers", bmp, "trim"); obj_bm(f"ST_WB_{name}_panels", bmk, "trim")
    obj_bm(f"ST_WB_{name}_pedestal_stone", bmy, "ped_stone")   # (R1 #17, v2 0:50: the plinths and panels olive-yellow)
    obj_bm(f"ST_WB_{name}_columns", bmc, "trim", smooth=True); obj_bm(f"ST_WB_{name}_collars", bmr, "trim", smooth=True)
    # arches between the blocks (and on the returns, in the yz plane): a thin rib, a ring and a C-scroll at each
    # springing, two pendant drops under the entablature, a lantern hanging in the middle of the bay
    spring = cap + 0.35; rise = blk - spring - 0.12
    bma, bmf, bmd, bml, bmg = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    spans = []
    for (xa, ka), (xb, kb) in zip(piers[:-1], piers[1:]):
        spans.append(("x", xa + PW[ka][2], xb - PW[kb][2], yf))
    for use, (x, kind) in zip(ends, (piers[0], piers[-1])):
        if use:
            spans.append(("y", 0.15, yf - PW[kind][2], x))
    for k, (ax, a0, a1, c) in enumerate(spans):
        plane = "xz" if ax == "x" else "yz"
        bm_prism(bma, arch_band(a0, a1, spring, rise, 0.1, 18), c - 0.06, c + 0.06, plane)
        def P(u, z, off=0.0):                            # (along the span, z) -> xyz
            return (u, c + off, z) if ax == "x" else (c + off, u, z)
        for u0, sg in ((a0, 1), (a1, -1)):
            M = T(*P(u0 + sg * 0.42, blk - 0.33)) @ (R(-math.pi / 2, "X") if ax == "x" else R(math.pi / 2, "Y"))
            bm_lathe(bmf, [(0.12, -0.02), (0.16, -0.02), (0.16, 0.02), (0.12, 0.02)], 16, M)
            curve = [P(u0 + sg * a, spring - 0.3 + z) for a, z in scroll_pts(0.5, 0.65, 0.12, 0.08, 10)]
            curve_obj(f"ST_WB_{name}_scroll{k}_{sg}", curve, "trim", 0.025)
            bm_lathe(bmd, [(0, 0), (0.05, 0), (0.07, -0.12), (0.03, -0.25), (0, -0.33)], 8, T(*P(u0 + sg * 0.95, blk - 0.02)))
        if ax == "x":                                    # the bay's lantern
            m = (a0 + a1) / 2
            bm_box(bmd, m - 0.015, m + 0.015, yf / 2 - 0.015, yf / 2 + 0.015, blk - 0.75, blk)
            bm_lathe(bml, [(0, 0), (0.1, 0), (0.17, 0.1), (0.17, 0.4), (0.2, 0.45), (0.05, 0.6), (0, 0.6)], 6, T(m, yf / 2, blk - 1.35))
            globe_lamp_bm(bmg, m, yf / 2, blk - 1.1, 0.11)
    obj_bm(f"ST_WB_{name}_arches", bma, "trim"); obj_bm(f"ST_WB_{name}_rings", bmf, "trim")
    obj_bm(f"ST_WB_{name}_drops", bmd, "trim", smooth=True); obj_bm(f"ST_WB_{name}_lanterns", bml, "iron")
    obj_bm(f"ST_WB_{name}_lantern_glow", bmg, "lamp", smooth=True)
    # entablature: architrave, frieze (panels over the piers and between), cornice; returns; roof, ceiling, beams
    xl = piers[0][0] - PW[piers[0][1]][2] - 0.1; xr = piers[-1][0] + PW[piers[-1][1]][2] + 0.1
    ent_boxes = [(xl, xr, yf - 0.45, yf + 0.45, blk, blk + 0.22), (xl, xr, yf - 0.4, yf + 0.4, blk + 0.22, ent - 0.22),
                 (xl - 0.1, xr + 0.1, yf - 0.4, yf + 0.55, ent - 0.22, ent - 0.1), (xl - 0.15, xr + 0.15, yf - 0.4, yf + 0.62, ent - 0.1, ent)]
    for use, x in zip(ends, (xl, xr)):
        if use:
            s = -1 if x == xl else 1
            ent_boxes += [(min(x, x - s * 0.9), max(x, x - s * 0.9), 0.0, yf, blk, ent - 0.22),
                          (min(x + s * 0.12, x - s * 0.9), max(x + s * 0.12, x - s * 0.9), 0.0, yf + 0.55, ent - 0.22, ent)]
    box(f"ST_WB_{name}_entablature", ent_boxes, "trim", 0.015)
    pnl = [(x - 0.3, x + 0.3, yf + 0.4, yf + 0.43, blk + 0.3, ent - 0.3) for x, _ in piers]
    for (xa, _), (xb, _) in zip(piers[:-1], piers[1:]):
        pnl.append((xa + 0.6, xb - 0.6, yf + 0.4, yf + 0.42, blk + 0.3, ent - 0.3))
    box(f"ST_WB_{name}_frieze", pnl, "cream")
    box(f"ST_WB_{name}_roof", (xl, xr, 0.0, yf, ent - 0.3, ent - 0.05), "trim")
    box(f"ST_WB_{name}_ceiling", [(xl, xr, 0.0, yf - 0.4, blk - 0.05, blk)] + [(x - 0.18, x + 0.18, 0.0, yf, blk - 0.32, blk) for x, _ in piers], "trim")
    box(f"ST_WB_{name}_floor", (xl - 0.3, xr + 0.3, 0.0, yf + 0.8, 0.0, 0.04), "wine_floor")   # (R1 #19: wine red, was tile)
    # balustrade on the roof: posts over the piers, runs between them and back along the returns
    bmt, bmb = bmesh.new(), bmesh.new()
    yb = yf + 0.2
    for x, kind in piers:
        pb = PW[kind][2]
        bm_box(bmt, x - pb, x + pb, yb - 0.4, yb + 0.4, ent, rail + 0.1)
        bm_box(bmt, x - pb - 0.07, x + pb + 0.07, yb - 0.47, yb + 0.47, rail + 0.1, rail + 0.2)
    for (xa, ka), (xb, kb) in zip(piers[:-1], piers[1:]):
        baluster_run(bmt, bmb, (xa + PW[ka][2], yb), (xb - PW[kb][2], yb), ent, rail)
    for use, (x, _) in zip(ends, (piers[0], piers[-1])):
        if use:
            baluster_run(bmt, bmb, (x, yb - 0.4), (x, 0.3), ent, rail)
            bm_box(bmt, x - 0.3, x + 0.3, 0.0, 0.6, ent, rail + 0.1)
    obj_bm(f"ST_WB_{name}_balustrade", bmt, "trim"); obj_bm(f"ST_WB_{name}_balusters", bmb, "trim")


def paired_window(bmf, bmp, bmh, x, y, z0, z1, sw):
    """Two arched lights in one cream surround (outer width sw, sill z0, top z1) and a segmental hood above."""
    bm_prism(bmf, arch_opening(x - sw / 2, x + sw / 2, z0, z1 - sw * 0.3, sw * 0.3, 16), y, y + 0.1, "xz")
    lw = sw / 2 - 0.26
    for dx in (-1, 1):
        xl = x + dx * (sw / 4 - 0.02)
        bm_prism(bmp, arch_opening(xl - lw / 2, xl + lw / 2, z0 + 0.14, z1 - 0.14 - lw / 2, lw / 2, 12), y + 0.1, y + 0.12, "xz")
    bm_prism(bmh, arch_band(x - sw / 2 - 0.12, x + sw / 2 + 0.12, z1 + 0.02, 0.28, 0.16, 16, leg=0.1), y, y + 0.2, "xz")
    bm_box(bmh, x - 0.1, x + 0.1, y, y + 0.22, z1 + 0.15, z1 + 0.5)                             # keystone
    bm_box(bmh, x - sw / 2 - 0.12, x + sw / 2 + 0.12, y, y + 0.2, z0 - 0.12, z0)                 # sill


PASSAGE = dict(x=9.3, y0=WB_BACK + 1.0, y1=-1.0, ceil=4.0, piers=(-5.9, -1.975, 1.975, 5.9), yp=-4.25, pw=0.9,
               alcove=(9.0, 12.0, -6.2, -3.8))
# (R1 #20, v2 1:00 .. 1:34, v1 1:19:00 .. 1:19:50: behind the front arches the passage is one hall, not five tunnels: a flat
#  cream ceiling with a cornice, a row of square brick piers on olive-yellow stone pedestals carrying brick arches both
#  ways, a brass lantern hanging in each bay, the floor wine red. The front and back faces keep their arches (the user's
#  photos); the piers stand on the line of the front's pilasters (x = +-1.975, +-5.9). #21: the Sharing the Magic statue
#  (OSM tourism=artwork, DS (-508.55, 891.64) = WB (11.7, -5.0)) in a brick alcove off the hall's east end.)
# ESTIMATES: the walls' thickness (1.0 m), the ceiling height (4.0 m), the pier size, the spring of the arches.


def span_wall(x0, x1, spring, rise, ztop, n=14):
    """The brick over an arch between two piers: the rectangle x0..x1 x spring..ztop less the arch (a plan polygon)."""
    return [(x0, ztop), (x1, ztop)] + seg_arc((x0 + x1) / 2, spring, x1 - x0, rise, n)[0]


def wb_passage_hall(wall):
    H = PASSAGE; hx, y0, y1, zc = H["x"], H["y0"], H["y1"], H["ceil"]
    ax0, ax1, ay0, ay1 = H["alcove"]
    cutter("ST_WB_cut_hall", [(-hx, hx, y0, y1, -0.5, zc), (ax0, ax1, ay0, ay1, -0.5, zc)], wall, "xz")
    box("ST_WB_passage", [(-hx, hx, WB_BACK, 0.0, 0.0, 0.03), (hx, ax1, ay0, ay1, 0.0, 0.03)], "wine_floor")
    box("ST_WB_passage_ceiling", [(-hx, hx, y0, y1, zc - 0.15, zc), (hx - 0.01, ax1, ay0, ay1, zc - 0.15, zc)], "trim")
    cor = 0.16                                            # the cornice round the hall
    box("ST_WB_passage_cornice", [(-hx, hx, y1 - cor, y1, zc - 0.4, zc - 0.15), (-hx, hx, y0, y0 + cor, zc - 0.4, zc - 0.15),
                                  (-hx, -hx + cor, y0, y1, zc - 0.4, zc - 0.15), (hx - cor, hx, y0, ay0, zc - 0.4, zc - 0.15),
                                  (hx - cor, hx, ay1, y1, zc - 0.4, zc - 0.15)], "trim")
    yp, h = H["yp"], H["pw"] / 2
    spring, rise = 2.65, 0.75
    bmb, bms, bmt = bmesh.new(), bmesh.new(), bmesh.new()
    for x in H["piers"]:
        bm_box(bmb, x - h, x + h, yp - h, yp + h, 0.9, zc - 0.15)                           # the brick pier
        bm_box(bms, x - h - 0.06, x + h + 0.06, yp - h - 0.06, yp + h + 0.06, 0.0, 0.9)     # its stone pedestal
        bm_box(bms, x - h - 0.1, x + h + 0.1, yp - h - 0.1, yp + h + 0.1, 0.0, 0.12)
        bm_box(bmt, x - h - 0.06, x + h + 0.06, yp - h - 0.06, yp + h + 0.06, spring - 0.15, spring)   # impost
        for ya, yb in ((y1, yp + h), (yp - h, y0)):       # the arches across, front and back of the pier
            bm_prism(bmb, span_wall(yb, ya, spring, rise, zc - 0.15) if yb < ya else span_wall(ya, yb, spring, rise, zc - 0.15),
                     x - h, x + h, "yz")
    xs = [-hx] + [v for x in H["piers"] for v in (x - h, x + h)] + [hx]
    for xa, xb in zip(xs[0::2], xs[1::2]):                # the arches along the row
        bm_prism(bmb, span_wall(xa, xb, spring, rise, zc - 0.15), yp - h, yp + h, "xz")
    obj_bm("ST_WB_passage_piers", bmb, "brick"); obj_bm("ST_WB_passage_pedestals", bms, "ped_stone")
    obj_bm("ST_WB_passage_imposts", bmt, "trim")
    bml, bmg = bmesh.new(), bmesh.new()                   # a brass lantern in the middle of each bay
    for xa, xb in zip(xs[0::2], xs[1::2]):
        for y in ((y1 + yp + h) / 2, (yp - h + y0) / 2):
            m = (xa + xb) / 2
            bm_box(bml, m - 0.015, m + 0.015, y - 0.015, y + 0.015, 3.3, zc - 0.15)
            bm_lathe(bml, [(0, 2.68), (0.06, 2.68), (0.1, 2.75), (0.17, 2.85), (0.17, 3.2), (0.2, 3.24), (0.06, 3.32), (0, 3.32)], 8, T(m, y, 0))
            globe_lamp_bm(bmg, m, y, 3.0, 0.12)
    obj_bm("ST_WB_passage_lanterns", bml, "gold"); obj_bm("ST_WB_passage_lantern_glow", bmg, "lamp", smooth=True)
    sharing_the_magic(ax1, (ay0 + ay1) / 2)


def sharing_the_magic(xw, yc):
    """Roy O. Disney and Minnie on a park bench (bronze, v2 1:12 .. 1:24) against the alcove's end wall at x = xw, facing
    -x (towards the hall); a plaque on the wall above. Simple forms: boxes and balls."""
    bm = bmesh.new()
    xb = xw - 0.12                                         # the bench: back, seat, arms, legs
    bm_box(bm, xb - 0.06, xb, yc - 0.8, yc + 0.8, 0.45, 1.0)
    bm_box(bm, xb - 0.5, xb, yc - 0.8, yc + 0.8, 0.42, 0.47)
    for s in (-1, 1):
        bm_box(bm, xb - 0.52, xb, yc + s * 0.8 - 0.03, yc + s * 0.8 + 0.03, 0.0, 0.7)
        bm_box(bm, xb - 0.5, xb - 0.44, yc + s * 0.75 - 0.03, yc + s * 0.75 + 0.03, 0.0, 0.42)
    yr, ym = yc + 0.32, yc - 0.42                         # Roy on the left, Minnie on the right, seen from the hall (v2 1:16)
    bm_box(bm, xb - 0.42, xb - 0.08, yr - 0.22, yr + 0.22, 0.47, 1.12)                   # torso
    bm_box(bm, xb - 0.38, xb - 0.12, yr - 0.15, yr + 0.15, 1.12, 1.2)                    # neck, shoulders
    globe_lamp_bm(bm, xb - 0.25, yr, 1.33, 0.13)                                          # head
    bm_box(bm, xb - 0.85, xb - 0.35, yr - 0.2, yr + 0.2, 0.47, 0.64)                     # thighs
    bm_box(bm, xb - 0.92, xb - 0.74, yr - 0.2, yr + 0.2, 0.0, 0.6)                       # shins
    for s in (-1, 1):
        bm_box(bm, xb - 0.62, xb - 0.15, yr + s * 0.25 - 0.05, yr + s * 0.25 + 0.05, 0.75, 0.88)   # forearms
    bm_lathe(bm, [(0, 0), (0.17, 0), (0.12, 0.3), (0.1, 0.42), (0, 0.45)], 10, T(xb - 0.25, ym, 0.47))   # Minnie: body (skirt)
    globe_lamp_bm(bm, xb - 0.25, ym, 1.04, 0.13)
    bm_lathe(bm, [(0, -0.015), (0.08, -0.015), (0.08, 0.015), (0, 0.015)], 12, T(xb - 0.25, ym - 0.11, 1.21) @ R(math.pi / 2, "Y"))
    bm_lathe(bm, [(0, -0.015), (0.08, -0.015), (0.08, 0.015), (0, 0.015)], 12, T(xb - 0.25, ym + 0.11, 1.21) @ R(math.pi / 2, "Y"))
    bm_lathe(bm, [(0, 0), (0.07, 0), (0.07, 0.03), (0, 0.03)], 8, T(xb - 0.25, ym, 1.16) @ R(math.pi / 2, "Y"))     # the bow
    bm_box(bm, xb - 0.62, xb - 0.42, ym - 0.12, ym + 0.12, 0.47, 0.6)                    # her legs over the seat edge
    bm_box(bm, xb - 0.68, xb - 0.58, ym - 0.1, ym + 0.1, 0.12, 0.5)
    obj_bm("ST_WB_statue", bm, "bronze", smooth=False)
    box("ST_WB_statue_plaque", [(xw - 0.03, xw, yc - 0.27, yc + 0.27, 1.72, 2.1)], "copper")


def wb_wall():
    """The entrance building (brick, x = -12.25 .. 12.25, y = -8.5 .. 0, 8.6 m) behind the porticos: arched ground
    floor (five arches go through to Main Street, as the photo from inside; the outermost are shop doors), a balcony over each
    arch (corbels, dark green railing, planting), paired arched windows with hoods, brick pilasters behind the piers
    with cream capitals, coach lamps. Sizes on the wall plane (photo, about 20 px/m there): the centre arch 3.3 m wide
    with its crown at 3.3 m, balconies 3.5 .. 4.4 m, windows 4.45 .. 6.4 m."""
    hw = WB_HALL["w"] / 2
    wall = box("ST_WB_wall", (-hw, hw, WB_BACK, 0.0, 0.0, WB_HALL["base"]), "brick")
    bays = [(0.0, 3.3, 2.5, 0.8, True)] + [(s * x, w, sp, r, th) for s in (-1, 1)
                                           for x, w, sp, r, th in ((3.95, 2.7, 2.4, 0.65, True), (8.0, 2.2, 2.3, 0.55, True), (10.85, 1.7, 2.2, 0.45, False))]
    cutter("ST_WB_cut_through", [arch_opening(x - w / 2, x + w / 2, -0.5, sp, r) for x, w, sp, r, th in bays if th], wall, "xz", (WB_BACK - 0.2, 0.3))
    cutter("ST_WB_cut_doors", [arch_opening(x - w / 2, x + w / 2, -0.5, sp, r) for x, w, sp, r, th in bays if not th], wall, "xz", (-0.35, 0.3))
    box("ST_WB_doors", [(x - w / 2, x + w / 2, -0.36, -0.3, 0.0, sp + r) for x, w, sp, r, th in bays if not th], "win_dark")
    wb_passage_hall(wall)
    prism("ST_WB_arch_bands", [arch_band(x - w / 2, x + w / 2, sp, r, 0.22, 16, leg=0.15) for x, w, sp, r, th in bays], 0.0, 0.08, "trim", "xz")
    box("ST_WB_keystones", [(x - 0.14, x + 0.14, 0.0, 0.12, sp + r - 0.05, sp + r + 0.38) for x, w, sp, r, th in bays], "trim")
    bms, bmr, bmg, bmfl = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    bmf, bmp, bmh = bmesh.new(), bmesh.new(), bmesh.new()
    for x, w, sp, r, th in bays:
        bw = min(2.3, w + 0.1)
        bm_box(bms, x - bw / 2, x + bw / 2, 0.0, 0.66, 3.5, 3.65)                               # slab, moulding, corbels
        bm_box(bms, x - bw / 2 + 0.08, x + bw / 2 - 0.08, 0.0, 0.58, 3.38, 3.5)
        for dx in (-1, 1):
            bm_box(bms, x + dx * (bw / 2 - 0.25) - 0.08, x + dx * (bw / 2 - 0.25) + 0.08, 0.0, 0.5, 3.0, 3.38)
            bm_box(bmr, x + dx * bw / 2 - 0.04, x + dx * bw / 2 + 0.04, 0.0, 0.66, 3.65, 4.42)
        bm_box(bmr, x - bw / 2, x + bw / 2, 0.58, 0.66, 4.34, 4.42)                             # railing
        bm_box(bmr, x - bw / 2, x + bw / 2, 0.58, 0.66, 3.65, 3.72)
        for k in range(1, int(bw / 0.11)):
            xx = x - bw / 2 + k * 0.11
            bm_box(bmr, xx - 0.012, xx + 0.012, 0.6, 0.64, 3.72, 4.34)
        bm_box(bmg, x - bw / 2 + 0.1, x + bw / 2 - 0.1, 0.12, 0.55, 3.65, 4.15)                 # planting behind it
        for k in range(int((bw - 0.3) / 0.32)):
            xx = x - bw / 2 + 0.3 + k * 0.32
            bm_box(bmfl, xx - 0.09, xx + 0.09, 0.4, 0.62, 4.1, 4.36)
        paired_window(bmf, bmp, bmh, x, 0.0, 4.45, 6.4, 1.6 if abs(x) < 5 else 1.35)
    obj_bm("ST_WB_balconies", bms, "trim"); obj_bm("ST_WB_balcony_rails", bmr, "rail_blue")
    obj_bm("ST_WB_balcony_planting", bmg, "hedge"); obj_bm("ST_WB_balcony_flowers", bmfl, "flowers_red")
    obj_bm("ST_WB_window_frames", bmf, "trim"); obj_bm("ST_WB_windows", bmp, "win_dark"); obj_bm("ST_WB_window_hoods", bmh, "trim")
    pil = [s * x for s in (-1, 1) for x in (1.975, 5.9, 9.55, 12.05)]
    box("ST_WB_pilasters", [(x - 0.32, x + 0.32, 0.0, 0.2, 0.0, 8.0) for x in pil], "brick")
    box("ST_WB_pilaster_caps", [(x - 0.38, x + 0.38, 0.0, 0.27, 6.3, 7.5) for x in pil] + [(x - 0.38, x + 0.38, 0.0, 0.27, 0.0, 0.5) for x in pil]
        + [(-hw, hw, 0.0, 0.1, 7.55, 8.0)], "trim", 0.02)
    bml, bmg2 = bmesh.new(), bmesh.new()                  # coach lamps beside the through arches
    for x, w, sp, r, th in bays:
        if not th:
            continue
        for dx in (-1, 1):
            lx = x + dx * (w / 2 + 0.45)
            bm_box(bml, lx - 0.03, lx + 0.03, 0.0, 0.3, 3.0, 3.06)
            bm_lathe(bml, [(0, 0), (0.06, 0), (0.12, 0.08), (0.12, 0.34), (0.15, 0.38), (0.03, 0.5), (0, 0.5)], 6, T(lx, 0.3, 2.7))
            globe_lamp_bm(bmg2, lx, 0.3, 2.92, 0.08)
    obj_bm("ST_WB_wall_lamps", bml, "iron"); obj_bm("ST_WB_wall_lamp_glow", bmg2, "lamp", smooth=True)


def wb_back():
    """The Main Street side of the entrance building (the user's photo from inside, 2026-09-27; people 1.70 m ->
    about 26 px/m on it): five arches through (crowns about 3 m), a cream string course at 3.6 m, tall windows upstairs
    (three in the centre, one then two either side) with cream frames and cornices, cream pilasters, the cornice at
    7.0 m, a dark mansard to 9.4 m with a gabled dormer in the middle and round-windowed dormers. Faces -y."""
    yb = WB_BACK; hw = WB_HALL["w"] / 2
    bays = [(0.0, 3.3, 2.5, 0.8)] + [(s * x, w, sp, r) for s in (-1, 1) for x, w, sp, r in ((3.95, 2.7, 2.4, 0.65), (8.0, 2.2, 2.3, 0.55))]
    prism("ST_WB_back_arch_bands", [arch_band(x - w / 2, x + w / 2, sp, r, 0.22, 16, leg=0.15) for x, w, sp, r in bays], yb - 0.08, yb, "trim", "xz")
    box("ST_WB_back_trim", [(x - 0.14, x + 0.14, yb - 0.12, yb, sp + r - 0.05, sp + r + 0.38) for x, w, sp, r in bays]
        + [(-hw, hw, yb - 0.15, yb, 3.5, 3.75), (-hw, hw, yb - 0.3, yb, 6.8, 7.05), (-hw - 0.1, hw + 0.1, yb - 0.45, yb, 7.05, 7.25)]
        + [(s * x - 0.3, s * x + 0.3, yb - 0.15, yb, 3.75, 6.8) for s in (-1, 1) for x in (1.9, 5.7, 9.9, 12.0)]
        + [(-1.9, 1.9, yb - 0.1, yb, 6.55, 6.8)], "trim", 0.02)
    bmf, bmp = bmesh.new(), bmesh.new()
    for x in (-1.05, 0.0, 1.05, -3.8, 3.8, -7.3, -8.4, 7.3, 8.4, -11.0, 11.0):
        bm_box(bmf, x - 0.5, x + 0.5, yb - 0.1, yb, 4.0, 6.1)                     # frame, cornice cap, sill
        bm_box(bmf, x - 0.6, x + 0.6, yb - 0.25, yb, 6.1, 6.3)
        bm_box(bmf, x - 0.56, x + 0.56, yb - 0.18, yb, 3.88, 4.0)
        bm_box(bmp, x - 0.37, x + 0.37, yb - 0.12, yb - 0.1, 4.14, 5.96)
        bm_box(bmf, x - 0.02, x + 0.02, yb - 0.14, yb - 0.1, 4.14, 5.96)          # glazing bars
        bm_box(bmf, x - 0.37, x + 0.37, yb - 0.14, yb - 0.1, 5.28, 5.32)
    # mansard (steep face, flat top up to the gable) and dormers
    bm = bmesh.new()
    V = lambda x, y, z: bm.verts.new((x, y, z))
    a, b_, c, d = V(-hw, yb - 0.3, 7.25), V(hw, yb - 0.3, 7.25), V(hw, yb + 1.3, 9.4), V(-hw, yb + 1.3, 9.4)
    e, f = V(hw, WB_HALL["y"], 9.4), V(-hw, WB_HALL["y"], 9.4)
    g, h = V(hw, WB_HALL["y"], 7.25), V(-hw, WB_HALL["y"], 7.25)
    for q in ((a, b_, c, d), (d, c, e, f), (b_, g, e, c), (a, d, f, h)):
        bm.faces.new(q)
    obj_bm("ST_WB_back_mansard", bm, "mauve")
    bmd = bmesh.new()
    bm_box(bmd, -1.1, 1.1, yb - 0.2, yb + 1.5, 7.2, 9.3)
    bm_prism(bmd, [(-1.35, 9.25), (1.35, 9.25), (0, 10.05)], yb - 0.3, yb + 1.5, "xz")
    bm_box(bmd, -1.35, 1.35, yb - 0.32, yb, 9.2, 9.3)
    bm_prism(bmp, arch_opening(-0.45, 0.45, 7.6, 8.55, 0.45, 12), yb - 0.23, yb - 0.21, "xz")
    for s in (-1, 1):
        for x in (4.4, 8.6):
            bm_box(bmd, s * x - 0.6, s * x + 0.6, yb, yb + 1.3, 7.2, 8.4)
            bm_prism(bmd, [(s * x - 0.78, 8.35), (s * x + 0.78, 8.35), (s * x, 9.0)], yb - 0.08, yb + 1.3, "xz")
            bm_lathe(bmd, [(0.27, 0), (0.38, 0), (0.38, 0.08), (0.27, 0.08)], 20, T(s * x, yb, 7.85) @ R(math.pi / 2, "X"))
            bm_lathe(bmp, [(0, 0), (0.28, 0), (0.28, 0.02), (0, 0.02)], 20, T(s * x, yb + 0.01, 7.85) @ R(math.pi / 2, "X"))
    obj_bm("ST_WB_back_window_frames", bmf, "trim"); obj_bm("ST_WB_back_windows", bmp, "win_dark"); obj_bm("ST_WB_back_dormers", bmd, "trim")


def wb_hall():
    """The glass hall over Main Street: its front gable stands on the back of the entrance building (y = -4.8), 24.5 m
    wide, eaves 12.1 m, ridge 16.2 m (photo: the gable's width equals the OSM gap, so it is ~1.5 times as far as the
    portico face). Green iron: mullions with round-arched heads, big arches in the lower band, rakes, rafters, purlins."""
    H = WB_HALL; hw = H["w"] / 2; y0, zb, ze, zr, yb = H["y"], H["base"], H["eave"], H["ridge"], H["back"]
    zg = lambda x: ze + (zr - ze) * (1 - abs(x) / hw)
    prism("ST_WB_hall_gable_glass", [[(-hw, zb), (hw, zb), (hw, ze), (0, zr), (-hw, ze)]], y0 - 0.03, y0, "hall_glass", "xz")
    bm = bmesh.new(); bma = bmesh.new()
    n = 20; step = 2 * hw / n
    for k in range(n + 1):
        x = -hw + k * step
        bm_box(bm, x - 0.06, x + 0.06, y0, y0 + 0.1, zb, zg(x))
    for z in (zb, 10.3, ze):
        bm_box(bm, -hw, hw, y0, y0 + 0.12, z - 0.08, z + 0.08)
    for k in range(n):
        xa, xb = -hw + k * step + 0.06, -hw + (k + 1) * step - 0.06
        bm_prism(bma, arch_band(xa, xb, ze - 0.62, (xb - xa) / 2, 0.06, 10), y0, y0 + 0.08, "xz")
        top = min(zg(xa), zg(xb))
        if top - ze > 1.1:                                # lancets under the rakes
            bm_prism(bma, arch_band(xa, xb, top - 0.75, (xb - xa) / 2, 0.06, 10), y0, y0 + 0.08, "xz")
            bm_box(bm, xa, xb, y0, y0 + 0.08, top - 0.8, top - 0.72)
    for cx, r0 in ((0.0, 3.3), (-7.35, 2.45), (7.35, 2.45)):  # the big arches (the centre one with a fan)
        bm_prism(bma, ring_sector(r0, r0 + 0.16, 0, math.pi, 33, cx, 9.2), y0, y0 + 0.14, "xz")
        for j in range(1, 6 if cx == 0 else 4):
            a = math.pi * j / (6 if cx == 0 else 4); ux, uz = math.cos(a), math.sin(a); nx, nz = -uz * 0.04, ux * 0.04
            bm_prism(bma, [(cx + ux * 0.4 + nx, 9.2 + uz * 0.4 + nz), (cx + ux * r0 + nx, 9.2 + uz * r0 + nz),
                           (cx + ux * r0 - nx, 9.2 + uz * r0 - nz), (cx + ux * 0.4 - nx, 9.2 + uz * 0.4 - nz)], y0, y0 + 0.1, "xz")
        bm_prism(bma, ring_sector(0.3, 0.42, 0, math.pi, 17, cx, 9.2), y0, y0 + 0.12, "xz")
    for s in (-1, 1):                                    # the rakes
        bm_prism(bm, [(s * (hw + 0.3), ze - 0.15), (0, zr - 0.1), (0, zr + 0.3), (s * (hw + 0.3), ze + 0.25)][::s], y0 - 0.1, y0 + 0.2, "xz")
    obj_bm("ST_WB_hall_frame", bm, "hall_iron"); obj_bm("ST_WB_hall_tracery", bma, "hall_iron")
    # roof and side walls
    bm = bmesh.new()
    for s in (-1, 1):
        v = [bm.verts.new(p) for p in ((s * hw, y0, ze), (0, y0, zr), (0, yb, zr), (s * hw, yb, ze))]
        bm.faces.new(v)
        v = [bm.verts.new(p) for p in ((s * hw, y0, zb), (s * hw, y0, ze), (s * hw, yb, ze), (s * hw, yb, zb))]
        bm.faces.new(v)
    obj_bm("ST_WB_hall_roof_glass", bm, "hall_glass", recalc=False)
    bm = bmesh.new()
    chevron = [(-hw - 0.3, ze - 0.05), (0, zr - 0.05), (hw + 0.3, ze - 0.05), (hw + 0.3, ze + 0.2), (0, zr + 0.2), (-hw - 0.3, ze + 0.2)]
    y = y0 - 3.0
    while y > yb:
        bm_prism(bm, chevron, y - 0.08, y + 0.08, "xz")
        for s in (-1, 1):
            bm_box(bm, s * hw - 0.08, s * hw + 0.08, y - 0.08, y + 0.08, zb, ze)
        y -= 3.0
    for f in (0.0, 0.25, 0.5, 0.75):
        for s in (-1, 1):
            x = s * hw * (1 - f); z = ze + (zr - ze) * f
            bm_box(bm, x - 0.07, x + 0.07, yb, y0, z - 0.02, z + 0.2)
    bm_box(bm, -0.15, 0.15, yb, y0, zr - 0.05, zr + 0.35)
    obj_bm("ST_WB_hall_rafters", bm, "hall_iron")
    bm = bmesh.new()                                      # arched trusses under the roof (the photo from inside)
    y = WB_BACK - 1.0                                     # (none here since the roof ends at the building: ds_tdl_world_bazaar)
    while y > yb:
        bm_prism(bm, arch_band(-hw, hw, zb, zr - 0.6 - zb, 0.3, 33), y - 0.1, y + 0.1, "xz")
        bm_prism(bm, arch_band(-hw + 0.9, hw - 0.9, zb, zr - 1.5 - zb, 0.12, 33), y - 0.06, y + 0.06, "xz")
        for s in (-1, 1):
            bm_box(bm, s * hw - 0.2, s * hw + 0.2, y - 0.2, y + 0.2, zb - 0.6, zb)
        y -= 6.0
    obj_bm("ST_WB_hall_trusses", bm, "hall_iron")


def arcade_front(name, x0, x1, s=1):
    """A World Bazaar arcade building from x0 to x1 (mirrored by s = -1), front on y = 0 facing +y: cream walls, an
    arcade in front (y 0 .. 2.8, columns, arches, a balustrade with ball finials on its roof), paired arched windows
    upstairs, a maroon mansard to 8.85 m with round dormers (photo and the sunset photo)."""
    X = lambda a, b: (min(s * a, s * b), max(s * a, s * b))
    box(f"ST_WB_{name}_wall", (*X(x0, x1), -8.0, 0.0, 0.0, 7.0), "cream")
    box(f"ST_WB_{name}_cornice", [(*X(x0, x1), 0.0, 0.1, 6.55, 6.95), (*X(x0, x1), 0.0, 0.3, 6.95, 7.15), (*X(x0, x1), 0.0, 0.4, 7.15, 7.3)], "trim", 0.02)
    bm = bmesh.new()                                      # mansard: steep front, flat top
    V = lambda x, y, z: bm.verts.new((s * x, y, z))
    a, b_, c, d = V(x0, 0.25, 7.3), V(x1, 0.25, 7.3), V(x1, -1.1, 8.85), V(x0, -1.1, 8.85)
    e, f = V(x1, -8.0, 8.85), V(x0, -8.0, 8.85)
    g, h = V(x1, -8.0, 7.3), V(x0, -8.0, 7.3)
    for q in ((a, b_, c, d), (d, c, e, f), (b_, g, e, c), (a, d, f, h)):
        bm.faces.new(q if s > 0 else q[::-1])
    obj_bm(f"ST_WB_{name}_mansard", bm, "mauve")
    nx = max(2, round((x1 - x0 - 1.35) / 3.3))
    xs = [x0 + 1.35 + k * (x1 - x0 - 1.35) / nx for k in range(nx + 1)]
    bmc, bmp, bma, bmd, bmo, bmr = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    bmf, bmw, bmh, bmt, bmb = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for x in xs:
        bm_box(bmp, s * x - 0.28, s * x + 0.28, 2.52, 3.08, 0.0, 0.55)
        column_bm(bmc, s * x, 2.8, 0.55, 2.65, 0.12, 12)
    for xa, xb in zip(xs[:-1], xs[1:]):
        a0, a1 = sorted((s * (xa + 0.25), s * (xb - 0.25)))
        bm_prism(bma, arch_band(a0, a1, 3.3, 0.45, 0.1, 14), 2.74, 2.86, "xz")
        m = s * (xa + xb) / 2
        bm_box(bmw, m - 1.0, m + 1.0, 0.0, 0.03, 0.3, 3.1)                     # shopfront: frame, glass
        bm_box(bmo, m - 0.9, m + 0.9, 0.03, 0.06, 0.4, 3.0)
    for k in range(1, nx, 2):                             # windows upstairs, a dormer over each
        m = s * (xs[k] + xs[k + 1]) / 2
        paired_window(bmf, bmo, bmh, m, 0.0, 5.0, 6.35, 1.35)
        bm_box(bmd, m - 0.7, m + 0.7, -0.6, 0.55, 7.2, 8.3)
        bm_prism(bmd, [(m - 0.85, 8.25), (m + 0.85, 8.25)] + seg_arc(m, 8.25, 1.7, 0.35, 12)[0], -0.6, 0.62, "xz")
        bm_lathe(bmd, [(0.3, 0), (0.42, 0), (0.42, 0.08), (0.3, 0.08)], 20, T(m, 0.55, 7.75) @ R(-math.pi / 2, "X"))
        bm_lathe(bmo, [(0, 0), (0.31, 0), (0.31, 0.02), (0, 0.02)], 20, T(m, 0.54, 7.75) @ R(-math.pi / 2, "X"))
    ax0, ax1 = sorted((s * (xs[0] - 0.3), s * (xs[-1] + 0.3)))
    box(f"ST_WB_{name}_arcade", [(ax0, ax1, 2.4, 3.2, 3.85, 4.1), (ax0 - 0.08, ax1 + 0.08, 2.35, 3.3, 4.1, 4.35),
                                  (ax0, ax1, 0.0, 2.8, 4.15, 4.3), (ax0, ax1, 0.0, 2.5, 3.8, 3.85)], "trim", 0.015)
    box(f"ST_WB_{name}_arcade_floor", (ax0, ax1, 0.0, 3.3, 0.0, 0.04), "tile")
    for x in xs:                                          # balustrade on the arcade roof, ball finials on alternate posts
        bm_box(bmt, s * x - 0.22, s * x + 0.22, 2.58, 3.02, 4.35, 5.2)
    for i, x in enumerate(xs):
        if i % 2 == 0:
            bm_lathe(bmr, [(0, 0), (0.12, 0), (0.06, 0.08)] + [(0.18 * math.sin(math.pi * j / 8), 0.26 - 0.18 * math.cos(math.pi * j / 8)) for j in range(1, 9)], 12, T(s * x, 2.8, 5.2))
    for xa, xb in zip(xs[:-1], xs[1:]):
        baluster_run(bmt, bmb, (s * (xa + 0.22), 2.8), (s * (xb - 0.22), 2.8), 4.35, 5.1)
    for nm, bm_, mt, sm in (("columns", bmc, "trim", True), ("pedestals", bmp, "trim", False), ("arches", bma, "trim", False),
                            ("dormers", bmd, "trim", False), ("glass", bmo, "win_dark", False), ("finials", bmr, "trim", True),
                            ("frames", bmw, "trim", False), ("window_frames", bmf, "trim", False), ("hoods", bmh, "trim", False),
                            ("balustrade", bmt, "trim", False), ("balusters", bmb, "trim", False)):
        obj_bm(f"ST_WB_{name}_{nm}", bm_, mt, smooth=sm)


def wb_people():
    """1.70 m figures for checking the scale (as in the user's photo); only in the check renders, not in the mock."""
    bm, bmh = bmesh.new(), bmesh.new()
    for x, y in ((-2.9, 5.3), (-0.4, 6.8), (1.1, 9.5), (3.0, 5.4), (-8.0, 4.4), (17.0, 3.6), (0.3, 1.2)):
        bm_lathe(bm, [(0, 0), (0.12, 0), (0.13, 0.8), (0.19, 0.9), (0.21, 1.3), (0.17, 1.45), (0.06, 1.5), (0, 1.5)], 12, T(x, y, 0))
        globe_lamp_bm(bmh, x, y, 1.595, 0.105)
    obj_bm("CTX_WB_people", bm, "person", smooth=True); obj_bm("CTX_WB_heads", bmh, "person", smooth=True)


def build_world_bazaar():
    with frame("WB_frame", WB["x"], WB["y"], WB["ang"]):
        wb_sign(WB_C["front"] + 0.2)                      # 1. the sign first, as in the video
        wb_portico("centre", [(-5.9, "cluster"), (-1.975, "pair"), (1.975, "pair"), (5.9, "cluster")], WB_C)   # 2. pillars, beams, arches
        for s in (-1, 1):                                 # piers listed left to right
            wb_portico(f"wing{s}", sorted((s * x, "pair") for x in (6.35, 9.65, 13.0)), WB_W, (s < 0, s > 0))
        wb_wall()                                         # 3. the brick building behind, and its Main Street side
        wb_back()
        wb_hall()
        wb_front()                                        # the rest of the front, round the corners (1b)


# ================================================================ 1b. the World Bazaar front round to the corners (2026-09-30)
# The user's photos (2026-09-30): Main Street House (three views of its portico), the whole front from the plaza, the
# greeting plazas either side (four views). Plan from OSM: beyond the entrance building the blocks 365357846 / 72216851
# keep the front on y = 0 out to x = +-35.5, turn 23 deg forward to a corner at x = +-44.5, y = 3.3, then run back 68 deg
# towards the gates' ends (Main Street House is on the west one). Seen from the plaza the whole front is one design:
# a white portico of paired columns on panelled pedestals, arches with ring fretwork and a balustrade on its roof (the
# centre's, lower), red brick behind it with arched doors (lace curtains, cream fanlights) and framed posters, a
# cream storey with windows, a maroon mansard with dormers; a glass conservatory on each corner (a round-ended glass
# house under a glass half-dome) and a hipped glass roof over the corner behind it.
# ESTIMATES: all heights (the portico is scaled from the photos' people, 1.70 m), the bay rhythm, the conservatory's
# radius, what is on each poster.
WB_S = dict(front=3.3, ped=0.9, cap=3.7, block=4.45, ent=5.1, rail=5.95)     # the side porticos
SIDE = dict(wall=7.6, mansard=9.4, depth=7.5)
FRONT_CHAINS = ([(-53.5, -17.0), (-52.5, -14.3), (-45.2, 3.7), (-35.8, -0.3), (-12.3, 0.1)],    # OSM 365357846, left to right
                [(12.2, -0.2), (35.1, 0.1), (44.2, 2.9), (51.8, -15.2), (54.0, -20.5)])       # OSM 72216851
CONS_CORNERS = ((-45.2, 3.7), (44.2, 2.9))
CONS = dict(r=4.6, cy=0.6, zb=0.75, zw=6.0, zs=6.6, back=-4.5)


def obox(bm, a, b, w, z0, z1):
    """A box along the plan segment a -> b, w wide, from z0 to z1."""
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    bm_prism(bm, [(a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny), (b[0] + nx, b[1] + ny), (a[0] + nx, a[1] + ny)], z0, z1, "xy")


def mansard_bm(bm, L, zw, zm, D, front=0.3, set_back=1.3):
    """Steep front face, flat top back to -D, closed ends (x = 0 .. L, +y out)."""
    V = lambda x, y, z: bm.verts.new((x, y, z))
    a, b_, c, d = V(0, front, zw), V(L, front, zw), V(L, -set_back, zm), V(0, -set_back, zm)
    e, f, g, h = V(L, -D, zm), V(0, -D, zm), V(L, -D, zw), V(0, -D, zw)
    for q in ((a, b_, c, d), (d, c, e, f), (b_, g, e, c), (h, a, d, f)):
        bm.faces.new(q)


def door_bay(P, m):
    """An arched door in the brick (photos: dark doors folded back, white lace curtains, a cream fanlight)."""
    bm_prism(P["frame"], arch_band(m - 0.95, m + 0.95, 2.55, 0.5, 0.16, 14, leg=2.55), 0.0, 0.08, "xz")
    bm_prism(P["dark"], arch_opening(m - 0.95, m + 0.95, 0.0, 2.55, 0.5, 14), 0.0, 0.03, "xz")
    bm_prism(P["frame"], arch_opening(m - 0.95, m + 0.95, 2.4, 2.55, 0.5, 14), 0.03, 0.05, "xz")           # fanlight
    bm_prism(P["glow"], arch_opening(m - 0.7, m + 0.7, 2.5, 2.58, 0.34, 12), 0.05, 0.06, "xz")
    for s in (-1, 1):
        bm_box(P["lace"], m + s * 0.62 - 0.26, m + s * 0.62 + 0.26, 0.04, 0.07, 0.3, 2.3)
        bm_box(P["door"], m + s * 0.95 - 0.04, m + s * 0.95 + 0.04, 0.0, 0.85, 0.0, 2.35)      # leaves folded back


def poster_bay(P, m, rng, bench):
    bm_box(P["frame"], m - 0.72, m + 0.72, 0.0, 0.1, 0.75, 2.95)
    bm_box(P[rng.choice(("poster1", "poster2", "poster3"))], m - 0.6, m + 0.6, 0.1, 0.12, 0.88, 2.82)
    if bench:                                            # a green park bench in front (photos)
        bm_box(P["bench"], m - 0.8, m + 0.8, 0.35, 0.8, 0.42, 0.47)
        bm_box(P["bench"], m - 0.8, m + 0.8, 0.3, 0.36, 0.5, 0.9)
        for s in (-1, 1):
            bm_box(P["iron"], m + s * 0.72 - 0.03, m + s * 0.72 + 0.03, 0.3, 0.8, 0.0, 0.9)


def pier_xs(x0p, x1p):
    n = max(1, round((x1p - x0p) / 3.9))
    return [x0p + k * (x1p - x0p) / n for k in range(n + 1)]


def front_run(name, L, x0p, x1p, rng, doors=()):
    """One straight piece of the front: x = 0 .. L on the OSM edge, +y out; portico piers from x0p to x1p."""
    D, zw, zm, ze = SIDE["depth"], SIDE["wall"], SIDE["mansard"], WB_S["ent"]
    box(f"ST_WB_{name}_brick", (0, L, -D, 0, 0, ze), "brick")
    box(f"ST_WB_{name}_upper", (0, L, -D, 0, ze, zw), "cream")
    box(f"ST_WB_{name}_trim", [(0, L, 0, 0.06, 0, 0.8), (0, L, 0, 0.3, zw - 0.35, zw), (-0.05, L + 0.05, 0, 0.45, zw, zw + 0.16)], "trim", 0.015)
    bm = bmesh.new(); mansard_bm(bm, L, zw + 0.16, zm, D); obj_bm(f"ST_WB_{name}_mansard", bm, "mauve")
    P = {k: bmesh.new() for k in ("frame", "dark", "glow", "lace", "door", "poster1", "poster2", "poster3", "bench", "iron",
                                  "wframe", "wglass", "whood", "dormer")}
    if x1p - x0p >= 3.0:
        xs = pier_xs(x0p, x1p)
        wb_portico(name, [(x, "pair") for x in xs], WB_S, (True, True))
        for k, (xa, xb) in enumerate(zip(xs[:-1], xs[1:])):
            m = (xa + xb) / 2
            if k in doors or (not doors and k % 2 == 0):
                door_bay(P, m)
            else:
                poster_bay(P, m, rng, rng.random() < 0.6)
            paired_window(P["wframe"], P["wglass"], P["whood"], m, 0.0, 5.55, 7.05, 1.2)
            if k % 2 == 1 or len(xs) == 2:              # a dormer over every second bay, a round window in it
                bm_box(P["dormer"], m - 0.7, m + 0.7, -0.7, 0.45, zw, zw + 1.05)
                bm_prism(P["dormer"], [(m - 0.85, zw + 1.0), (m + 0.85, zw + 1.0)] + seg_arc(m, zw + 1.0, 1.7, 0.35, 12)[0], -0.7, 0.52, "xz")
                bm_lathe(P["dormer"], [(0.28, 0), (0.4, 0), (0.4, 0.08), (0.28, 0.08)], 16, T(m, 0.45, zw + 0.55) @ R(-math.pi / 2, "X"))
                bm_lathe(P["wglass"], [(0, 0), (0.29, 0), (0.29, 0.02), (0, 0.02)], 16, T(m, 0.44, zw + 0.55) @ R(-math.pi / 2, "X"))
    else:
        paired_window(P["wframe"], P["wglass"], P["whood"], L / 2, 0.0, 5.55, 7.05, 1.2)
    mats = {"frame": "trim", "dark": "win_dark", "glow": "amber", "lace": "lace", "door": "door_brown", "poster1": "poster1",
            "poster2": "poster2", "poster3": "poster3", "bench": "bench_green", "iron": "iron", "wframe": "trim", "wglass": "win_dark",
            "whood": "trim", "dormer": "trim"}
    for k, bm_ in P.items():
        if len(bm_.verts):
            obj_bm(f"ST_WB_{name}_{k}", bm_, mats[k])
        else:
            bm_.free()


def main_street_house(m, yf):
    """The sign and what stands under the portico (the user's photos): a maroon oval board with a gold rim hung below
    the frieze ("MAIN STREET HOUSE"), two gooseneck lamps over it on the frieze, a guest information stand by the door."""
    zc, ze = 4.0, WB_S["ent"]
    def oval(a_, b_, n=40, e=2.6):
        return [(m + math.copysign(abs(math.cos(t)) ** (2 / e), math.cos(t)) * a_,
                 zc + math.copysign(abs(math.sin(t)) ** (2 / e), math.sin(t)) * b_) for t in (2 * math.pi * k / n for k in range(n))]
    prism("ST_WB_msh_sign_rim", [oval(1.12, 0.4)], yf + 0.62, yf + 0.7, "gold", "xz")
    prism("ST_WB_msh_sign_board", [oval(1.04, 0.33)], yf + 0.6, yf + 0.74, "sign_red", "xz")
    text("ST_WB_msh_sign_text", "MAIN STREET HOUSE", 0.17, (m, yf + 0.75, zc), (math.pi / 2, 0, math.pi), "letters", 0.01)
    box("ST_WB_msh_sign_hangers", [(m + s * 0.6 - 0.02, m + s * 0.6 + 0.02, yf + 0.64, yf + 0.68, zc + 0.35, WB_S["block"]) for s in (-1, 1)], "iron")
    bm, bmg = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        x = m + s * 0.75
        bm_box(bm, x - 0.03, x + 0.03, yf + 0.3, yf + 0.36, ze, ze + 0.55)                  # gooseneck: post, arm, shade
        bm_box(bm, x - 0.03, x + 0.03, yf + 0.3, yf + 0.95, ze + 0.5, ze + 0.56)
        bm_lathe(bm, [(0, 0.2), (0.07, 0.2), (0.2, 0.0), (0.2, -0.03), (0, -0.03)], 12, T(x, yf + 0.95, ze + 0.3))
        globe_lamp_bm(bmg, x, yf + 0.95, ze + 0.27, 0.06)
    x = m + 1.5                                           # the guest information stand
    bm_box(bm, x - 0.04, x + 0.04, 1.3, 1.38, 0.05, 1.5)
    bm_lathe(bm, [(0, 0), (0.25, 0), (0.25, 0.05), (0, 0.05)], 12, T(x, 1.34, 0))
    obj_bm("ST_WB_msh_lamps", bm, "iron"); obj_bm("ST_WB_msh_lamp_glow", bmg, "lamp", smooth=True)
    box("ST_WB_msh_stand", [(x - 0.28, x + 0.28, 1.38, 1.42, 0.85, 1.7)], "sign_red")
    box("ST_WB_msh_stand_rim", [(x - 0.32, x + 0.32, 1.35, 1.38, 0.8, 1.75)], "trim")


def conservatory(name):
    """The glass house on a corner (photos): a cream plinth, glass walls on white mullions round a semicircular front
    and straight sides, a white band, a glass half-dome and barrel on white ribs, a finial; the doorway at the front.
    Behind it, over the corner of the block, a glass clerestory under a hipped glass roof. Frame: +y out along the corner's
    bisector, the origin on the OSM corner."""
    r, cy, zb, zw, zs, back = CONS["r"], CONS["cy"], CONS["zb"], CONS["zw"], CONS["zs"], CONS["back"]
    n = 12
    apse = [(r * math.cos(math.pi * k / n), cy + r * math.sin(math.pi * k / n)) for k in range(n + 1)]
    path = [(r, back)] + apse + [(-r, back)]
    def grow(p, d):
        return (p[0] * (r + d) / r, cy + (p[1] - cy) * (r + d) / r) if p[1] >= cy - 1e-6 else (math.copysign(r + d, p[0]), p[1])
    bmw, bmg, bmr = bmesh.new(), bmesh.new(), bmesh.new()
    bm_prism(bmw, [grow(p, 0.2) for p in path], 0.0, zb, "xy")                                      # plinth
    for a, b in zip(path[:-1], path[1:]):
        v = [bmg.verts.new((a[0], a[1], zb)), bmg.verts.new((b[0], b[1], zb)), bmg.verts.new((b[0], b[1], zw)), bmg.verts.new((a[0], a[1], zw))]
        bmg.faces.new(v)
        obox(bmw, grow(a, 0.05), grow(b, 0.05), 0.3, zw, zs - 0.1)                                    # the band and its cornice
        obox(bmw, grow(a, 0.1), grow(b, 0.1), 0.4, zs - 0.12, zs)
        for z in (zb, 4.6):                                                                            # transoms
            obox(bmr, grow(a, 0.03), grow(b, 0.03), 0.08, z, z + 0.1)
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = max(1, round(L / 1.3))
        for j in range(k + 1):                                                                         # mullions
            f = j / k; p = grow((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), 0.04)
            bm_box(bmr, p[0] - 0.05, p[0] + 0.05, p[1] - 0.05, p[1] + 0.05, zb, zw)
    yf = cy + r + 0.06                                                                                 # the doorway at the front
    bm_prism(bmw, arch_band(-1.1, 1.1, 2.9, 0.7, 0.2, 14, leg=2.9), yf, yf + 0.12, "xz")
    bm = bmesh.new(); bm_prism(bm, arch_opening(-1.1, 1.1, 0.0, 2.9, 0.7, 14), yf - 0.02, yf + 0.03, "xz")
    obj_bm(f"ST_WB_{name}_doorway", bm, "win_dark")
    # roof: a quarter-sphere over the apse, a half-cylinder over the straight part
    bmd = bmesh.new(); m_el, m_az = 6, 16
    rows = [[bmd.verts.new((r * math.cos(el) * math.cos(az), cy + r * math.cos(el) * math.sin(az), zs + r * math.sin(el)))
             for az in (math.pi * j / m_az for j in range(m_az + 1))] for el in (math.pi / 2 * i / m_el for i in range(m_el))]
    top = bmd.verts.new((0, cy, zs + r))
    for i in range(m_el - 1):
        for j in range(m_az):
            bmd.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    for j in range(m_az):
        bmd.faces.new((rows[-1][j], rows[-1][j + 1], top))
    semi = [(r * math.cos(math.pi * j / m_az), r * math.sin(math.pi * j / m_az)) for j in range(m_az + 1)]
    v0 = [bmd.verts.new((x, cy, zs + z)) for x, z in semi]; v1 = [bmd.verts.new((x, back, zs + z)) for x, z in semi]
    for j in range(m_az):
        bmd.faces.new((v0[j], v1[j], v1[j + 1], v0[j + 1]))
    obj_bm(f"ST_WB_{name}_roof_glass", bmd, "cons_dome", recalc=False)   # (R1 #11, v2 0:02: the dome reads cream, was cons_glass)
    obj_bm(f"ST_WB_{name}_glass", bmg, "cons_glass", recalc=False)
    for k in range(9):                                    # ribs: meridians over the dome, arches over the barrel
        az = math.pi * k / 8
        curve_obj(f"ST_WB_{name}_rib{k}", [(r * 1.01 * math.cos(el) * math.cos(az), cy + r * 1.01 * math.cos(el) * math.sin(az), zs + r * 1.01 * math.sin(el))
                                           for el in (math.pi / 2 * i / 8 for i in range(9))], "white", 0.06)
    for j, y in enumerate((cy, (cy + back) / 2, back)):
        curve_obj(f"ST_WB_{name}_arch{j}", [(x * 1.01, y, zs + z * 1.01) for x, z in semi], "white", 0.07)
    bmfin = bmesh.new()                                   # the finial (R1 #11, v2 0:02: gilt)
    bm_lathe(bmfin, [(0, 0), (0.3, 0), (0.22, 0.25), (0.12, 0.3), (0.16, 0.6), (0.05, 0.9), (0.02, 1.4), (0, 1.4)], 12, T(0, cy, zs + r - 0.05))
    obj_bm(f"ST_WB_{name}_finial", bmfin, "gold", smooth=True)
    obj_bm(f"ST_WB_{name}_white", bmw, "white")
    obj_bm(f"ST_WB_{name}_frames", bmr, "white")
    # the hipped glass roof over the corner behind it (photos: higher than the mansard, green iron, a white balustrade)
    hx, y0, y1, zb2 = 4.8, back - 8.0, back + 0.5, SIDE["mansard"] - 0.2
    bmh, bmi, bmb = bmesh.new(), bmesh.new(), bmesh.new()
    corners = ((-hx, y0), (hx, y0), (hx, y1), (-hx, y1))
    for (xa, ya), (xb, yb) in zip(corners, corners[1:] + corners[:1]):
        v = [bmh.verts.new((xa, ya, zb2)), bmh.verts.new((xb, yb, zb2)), bmh.verts.new((xb, yb, zb2 + 1.6)), bmh.verts.new((xa, ya, zb2 + 1.6))]
        bmh.faces.new(v)
        obox(bmi, (xa, ya), (xb, yb), 0.14, zb2 + 1.55, zb2 + 1.75)
        obox(bmb, (xa, ya), (xb, yb), 0.3, zb2, zb2 + 0.12)                                            # balustrade
        obox(bmb, (xa, ya), (xb, yb), 0.3, zb2 + 0.72, zb2 + 0.84)
        L = math.hypot(xb - xa, yb - ya); nb, ni = int(L / 0.28), int(L / 1.2)
        for j in range(nb):
            f = (j + 0.5) / nb; p = (xa + (xb - xa) * f, ya + (yb - ya) * f)
            bm_box(bmb, p[0] - 0.05, p[0] + 0.05, p[1] - 0.05, p[1] + 0.05, zb2 + 0.12, zb2 + 0.72)
        for j in range(ni + 1):
            f = j / ni; p = (xa + (xb - xa) * f, ya + (yb - ya) * f)
            bm_box(bmi, p[0] - 0.05, p[0] + 0.05, p[1] - 0.05, p[1] + 0.05, zb2, zb2 + 1.6)
    bm = bmesh.new(); ST.hip_y(bm, -hx, hx, y0, y1, zb2 + 1.7, zb2 + 4.6)
    obj_bm(f"ST_WB_{name}_hip_glass", bm, "hall_glass", recalc=False)
    obj_bm(f"ST_WB_{name}_clerestory", bmh, "hall_glass", recalc=False)
    ym, half = (y0 + y1) / 2, max((y1 - y0) / 2 - hx, 0.0)
    for k, (cx_, cy_) in enumerate(corners):                                                           # the hips
        curve_obj(f"ST_WB_{name}_hip{k}", [(cx_, cy_, zb2 + 1.7), (0, ym + math.copysign(half, cy_ - ym), zb2 + 4.6)], "hall_iron", 0.06)
    obj_bm(f"ST_WB_{name}_clerestory_iron", bmi, "hall_iron"); obj_bm(f"ST_WB_{name}_balustrade", bmb, "white")


def wb_front():
    """The front beyond the entrance building, round the corners (1b)."""
    rng = random.Random(11)
    for side, chain in zip((-1, 1), FRONT_CHAINS):
        for i, (a, b) in enumerate(zip(chain[:-1], chain[1:])):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            x0p = 1.2 + (4.4 if a in CONS_CORNERS else 0.0) + (1.9 if a == chain[0] and side > 0 else 0.0)   # (clear of the wing portico)
            x1p = L - 1.2 - (4.4 if b in CONS_CORNERS else 0.0) - (1.9 if b == chain[-1] and side < 0 else 0.0)
            msh = side < 0 and i == 1                     # Main Street House: the west face towards the gates
            with frame(f"WBF_{side}_{i}", a[0], a[1], math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))):
                front_run(f"front{side}_{i}", L, x0p, x1p, rng, doors=(1, 2) if msh else ())
                if msh:
                    xs = pier_xs(x0p, x1p)
                    main_street_house((xs[1] + xs[2]) / 2, WB_S["front"])
    for k, c in enumerate(CONS_CORNERS):                  # the conservatories face out along the corner's bisector
        chain = FRONT_CHAINS[k]; i = chain.index(c)
        nx = ny = 0.0
        for a, b in ((chain[i - 1], c), (c, chain[i + 1])):
            L = math.hypot(b[0] - a[0], b[1] - a[1]); nx -= (b[1] - a[1]) / L; ny += (b[0] - a[0]) / L
        with frame(f"WB_cons{k}", c[0], c[1], math.degrees(math.atan2(-nx, ny))):
            conservatory(f"cons{k}")


# ================================================================ 2. the main entrance gates: one bay + Array + Curve
def turnstile_row(parts, x0, x1, y, k_booth="booth", k_trim="mint", k_scr="screen"):
    """The 2023 gates' lanes (photos): waist-high ticket pedestals about 1.5 m apart, each with a small screen on a
    slanted top, a low stainless rail between the lanes."""
    n = max(1, int((x1 - x0) / 1.5))
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        bm_box(parts[k_booth], x - 0.16, x + 0.16, y - 0.35, y + 0.35, 0, 0.95)
        bm_box(parts[k_trim], x - 0.18, x + 0.18, y - 0.37, y + 0.37, 0.95, 1.02)
        bm_prism(parts[k_scr], [(y - 0.12, 1.02), (y + 0.12, 1.02), (y + 0.12, 1.2), (y - 0.12, 1.12)], x - 0.1, x + 0.1, "yz")
        if k < n:
            bm_box(parts[k_trim], x + 0.16, x + (x1 - x0) / n - 0.16, y - 0.02, y + 0.02, 0.85, 0.9)


def valance(bm, x0, x1, y, z, depth=0.35, n_per_m=2.2):
    """A scalloped valance (photos: seafoam and cream, under the beam over the turnstiles), in the xz plane at y."""
    n = max(2, int((x1 - x0) * n_per_m))
    pts = [(x0, z), (x1, z)]
    for k in range(n, 0, -1):
        for j in range(5):
            t = (k - j / 4) / n
            pts.append((x0 + (x1 - x0) * t, z - depth * (0.45 + 0.55 * math.sin(math.pi * j / 4))))
    bm_prism(bm, pts, y - 0.03, y + 0.03, "xz")


def bay_module(name, w, N, curve):
    """One gate bay in curve coordinates (x along the arc 0..w, y towards the plaza, z up), then Array N and bend."""
    h = ARC["half"]
    parts = {k: bmesh.new() for k in ("trim", "mint", "slate", "iron", "booth", "green_sign", "lamp", "magenta", "gold", "screen", "hall_glass")}
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
        # the gable's spire (photos: a tall cream spike with a gold tip on every bay), the king post's pendant under
        # the apex, and an arched collar across the gable in front of the mint board
        bm_lathe(parts["trim"], [(0, 0), (0.1, 0), (0.1, 0.18), (0.06, 0.3), (0.09, 0.45), (0.035, 0.75), (0.015, 1.45), (0, 1.5)], 8, T(w / 2, yf, gz - 0.05))
        bm_lathe(parts["gold"], [(0, -0.05), (0.05, 0), (0, 0.05)], 8, T(w / 2, yf, gz + 1.0))
        bm_lathe(parts["trim"], [(0, 0), (0.05, 0), (0.08, 0.12), (0.05, 0.3), (0.06, 0.55), (0, 0.62)], 8, T(w / 2, yf + s * 0.08, gz - 0.62))
        bm_prism(parts["trim"], arch_band(w / 2 - ga * 0.62, w / 2 + ga * 0.62, 4.62, ga * 0.36, 0.08, 14), min(yf, yf + s * 0.07), max(yf, yf + s * 0.07), "xz")
        bm_box(parts["green_sign"], w / 2 - 0.85, w / 2 + 0.85, y + s * 0.06, y + s * 0.1, 2.85, 3.3)
        # roof: the main slope (eaves -> ridge) and the bay's small gable roof
        e_y, e_z, r_z = s * (h + 0.3), 4.55, 7.0
        v = [parts["slate"].verts.new(p) for p in ((0, e_y, e_z), (w, e_y, e_z), (w, 0, r_z), (0, 0, r_z))]
        parts["slate"].faces.new(v if s < 0 else v[::-1])
        yr = s * (h * (7.0 - 6.15) / (7.0 - 4.55))                                         # where the gable ridge meets the slope
        for x0, x1 in ((w / 2 - ga - 0.25, w / 2), (w / 2 + ga + 0.25, w / 2)):
            q = [parts["slate"].verts.new(p) for p in ((x0, yf + s * 0.25, 4.45), (x1, yf + s * 0.25, gz + 0.12), (x1, yr, gz + 0.12), (x0, yr, 4.45 + (7.0 - 4.45) * (1 - abs(yr) / h) * 0.0))]
            parts["slate"].faces.new(q)
        # a skylight on the upper slope, above the bay gable's roof (glass panes in a cream frame, iron glazing bars)
        on_slope(parts["trim"], 0.55, w - 0.55, 0.06, 0.3, s, h, 0.02, 0.08)
        on_slope(parts["hall_glass"], 0.65, w - 0.65, 0.08, 0.28, s, h, 0.1, 0.02)
        nb = max(2, int((w - 1.3) / 0.55))
        for k in range(nb + 1):
            xb = 0.65 + (w - 1.3) * k / nb
            on_slope(parts["iron"], xb - 0.025, xb + 0.025, 0.08, 0.28, s, h, 0.1, 0.05)
    bm_box(parts["trim"], 0, w, -h + 0.2, h - 0.2, 3.95, 4.02)                               # ceiling
    turnstile_row(parts, 0.55, w - 0.55, 0.0)                                              # the lanes
    for s in (-1, 1):                                                                       # scalloped valances under the beams
        valance(parts["mint"], 0.35, w - 0.35, s * (ARC["half"] - 0.6) - s * 0.35, 3.7)
    for fx in (0.3, 0.7):                                                                   # a screen over each pair of lanes
        bm_box(parts["screen"], w * fx - 0.32, w * fx + 0.32, -0.04, 0.04, 3.1, 3.45)
        bm_box(parts["iron"], w * fx - 0.02, w * fx + 0.02, -0.02, 0.02, 3.45, 3.95)
    for fx in (0.25, 0.75):                                                                 # ceiling lights
        globe_lamp_bm(parts["lamp"], w * fx, 0.0, 3.75, 0.13)
    globe_lamp_bm(parts["lamp"], w / 2, 0.0, 3.6, 0.2)
    cres = bmesh.new(); bm_lathe(cres, [(0, 0), (0.03, 0), (0.02, 0.3), (0.045, 0.34), (0, 0.46)], 6, T(0.2, 0, 7.0))
    out = []
    for k, bm in parts.items():
        if not len(bm.verts):
            bm.free(); continue
        o = obj_bm(f"ST_Gate_{name}_{k}", bm, k if k in B.M else "trim", recalc=(k != "slate"))
        if k == "slate":
            sd = o.modifiers.new("Solidify", "SOLIDIFY"); sd.thickness = 0.12; sd.offset = -1
        array_mod(o, N, (w, 0, 0)); bend(o, curve); out.append(o)
    c = obj_bm(f"ST_Gate_{name}_cresting", cres, "trim")         # photos: cream cresting on the ridge; array_mod(c, max(1, int(w / 0.45)), (0.45, 0, 0), "Cres")
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
        for dx in (-1, 1):                                # scroll brackets under the beam, both ways along the arc
            bracket(bmp, dx * 0.28, dx * 0.95, 3.7, 0.55, y)
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
                bracket(bm, px + dx * 0.4, px + dx * 1.25, eave - 0.9, 0.8, py, 0.06)   # the big scroll corbels (photos)
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
            bm_lathe(bml, [(0, 0), (0.07, 0), (0.12, 0.18), (0.07, 0.45), (0.09, 0.8), (0, 0.9)], 8, T(0, yf + s * 0.1, apex - 0.85))  # pendant
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
        ew, ed = hw + 0.9, hd + 0.9                       # a lace valance under the eaves all round (photos)
        bmv = bmesh.new()
        for s in (-1, 1):
            for xa, xb in ((-ew, -(gw + 0.45)), (gw + 0.45, ew)):
                lace(bmv, xa, eave, xb, eave, 0.28, max(2, int((xb - xa) / 0.6)), s * ed - 0.04, s * ed + 0.04)
            lace(bmv, -ed, eave, ed, eave, 0.28, max(2, int(2 * ed / 0.6)), s * ew - 0.04, s * ew + 0.04, "yz")
        obj_bm(f"ST_Pav_{name}_valance", bmv, "trim")
        if deck:                                          # railing on the deck, spires
            tw, td = hw * 0.45, hd * 0.28
            box(f"ST_Pav_{name}_deckrail", [(-tw, tw, -td, -td + 0.05, deck + 0.8, deck + 0.86), (-tw, tw, td - 0.05, td, deck + 0.8, deck + 0.86),
                                            (-tw, -tw + 0.05, -td, td, deck + 0.8, deck + 0.86), (tw - 0.05, tw, -td, td, deck + 0.8, deck + 0.86)], "trim")
            for yy in (-td + 0.02, td - 0.02):
                bar = box(f"ST_Pav_{name}_deckbars{yy:+.0f}", (-tw, -tw + 0.03, yy - 0.015, yy + 0.015, deck, deck + 0.8), "trim")
                array_mod(bar, int(2 * tw / 0.15) + 1, (0.15, 0, 0))
            bmu = bmesh.new()                             # posts with urn finials at the corners and the middles
            for px in (-tw, 0.0, tw):
                for py in (-td, td):
                    bm_box(bmu, px - 0.08, px + 0.08, py - 0.08, py + 0.08, deck, deck + 0.95)
                    bm_lathe(bmu, [(0, 0), (0.07, 0), (0.12, 0.1), (0.1, 0.22), (0.04, 0.26), (0.06, 0.32), (0, 0.4)], 10, T(px, py, deck + 0.95))
            obj_bm(f"ST_Pav_{name}_deckposts", bmu, "trim", smooth=True)
            lw, ld = tw * 0.55, td * 0.55                 # the skylight: a glazed lantern on the deck
            box(f"ST_Pav_{name}_lantern_frame", [(-lw - 0.05, lw + 0.05, -ld - 0.05, ld + 0.05, deck, deck + 0.12)], "trim")
            box(f"ST_Pav_{name}_lantern_glass", (-lw, lw, -ld, ld, deck + 0.12, deck + 0.5), "hall_glass")
            def lantern(bm):
                V = lambda x, y, z: bm.verts.new((x, y, z))
                a, b_, c, e = V(-lw - 0.08, -ld - 0.08, deck + 0.5), V(lw + 0.08, -ld - 0.08, deck + 0.5), V(lw + 0.08, ld + 0.08, deck + 0.5), V(-lw - 0.08, ld + 0.08, deck + 0.5)
                ta, tb = V(-lw * 0.5, 0, deck + 0.95), V(lw * 0.5, 0, deck + 0.95)
                for q in ((a, b_, tb, ta), (b_, c, tb), (c, e, ta, tb), (e, a, ta)):
                    bm.faces.new(q)
            roof_obj(f"ST_Pav_{name}_lantern_roof", lantern, "hall_glass", 0.03)
            bmb = bmesh.new()
            for k in range(9):
                x = -lw + 2 * lw * k / 8
                bm_box(bmb, x - 0.02, x + 0.02, -ld - 0.02, ld + 0.02, deck + 0.12, deck + 0.52)
            obj_bm(f"ST_Pav_{name}_lantern_bars", bmb, "hall_iron")
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
                bm = bmesh.new()                          # light bulbs round the oval's rim, as on the World Bazaar sign
                for k in range(36):
                    t_ = 2 * math.pi * k / 36
                    bm_lathe(bm, [(0, -0.045), (0.045, 0), (0, 0.045)], 6, T(2.28 * math.cos(t_), yf + s * 0.18, eave + 1.05 + 0.545 * math.sin(t_)))
                obj_bm(f"ST_Pav_{name}_signbulbs{s}", bm, "bulb", smooth=True)
                for sx in (-1, 1):                        # gold scrolls curling off the oval's ends and a crest on top
                    P = [(sx * (2.35 + a), yf + s * 0.08, eave + 1.05 - 0.3 + z) for a, z in scroll_pts(0.5, 0.45, 0.15, 0.08, 10)]
                    curve_obj(f"ST_Pav_{name}_signscroll{s}{sx}", P, "gold", 0.045)
                bm = bmesh.new()
                bm_prism(bm, [(-0.55, eave + 1.62), (0.55, eave + 1.62), (0.3, eave + 1.78), (0.12, eave + 1.95), (0, eave + 2.02), (-0.12, eave + 1.95), (-0.3, eave + 1.78)],
                         min(yf, yf + s * 0.08), max(yf, yf + s * 0.08), "xz")
                obj_bm(f"ST_Pav_{name}_signcrest{s}", bm, "gold")
                bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.31, 0), (0.31, 0.05), (0, 0.05)], 28, Mm); obj_bm(f"ST_Pav_{name}_med{s}", bm, "blue_disc")
            for s in (-1, 1):
                b = box(f"ST_Pav_{name}_entrance{s}", (-hw * 0.38 - 2.3, -hw * 0.38 - 0.7, s * (hd - 0.3) - 0.03, s * (hd - 0.3) + 0.03, eave - 1.75, eave - 1.3), "green_sign")
                array_mod(b, 2, (hw * 0.76 + 3.0, 0, 0))
                b = box(f"ST_Pav_{name}_entrance_frame{s}", (-hw * 0.38 - 2.36, -hw * 0.38 - 0.64, s * (hd - 0.3) - s * 0.05 - 0.02, s * (hd - 0.3) - s * 0.05 + 0.02, eave - 1.81, eave - 1.24), "gold")
                array_mod(b, 2, (hw * 0.76 + 3.0, 0, 0))
                rot = (math.pi / 2, 0, math.pi) if s > 0 else (math.pi / 2, 0, 0)
                tm = text_mesh(f"ST_Pav_{name}_entrance_text{s}", "ENTRANCE", 0.2, (-hw * 0.38 - 1.5, s * (hd - 0.3 + 0.04), eave - 1.52), rot, "white")
                array_mod(tm, 2, ((hw * 0.76 + 3.0) * (1 if s < 0 else -1), 0, 0))
        tp = {k: bmesh.new() for k in ("booth", "mint", "screen")}   # the lanes under the pavilion
        turnstile_row(tp, -hw + 0.9, hw - 0.9, 0.0)
        for s in (-1, 1):
            valance(tp["mint"], -hw + 0.6, hw - 0.6, s * (hd - 0.7), eave - 0.75)
        for k, bm_ in tp.items():
            obj_bm(f"ST_Pav_{name}_{k}", bm_, k)
        if deck:                                          # a weathervane on the deck (photo: a bird on an arrow)
            bmv = bmesh.new()
            bm_lathe(bmv, [(0, 0), (0.06, 0), (0.03, 2.2), (0, 2.25)], 8, T(0, 0, deck + 0.9))
            bm_box(bmv, -0.9, 0.9, -0.015, 0.015, deck + 2.6, deck + 2.66)
            bm_prism(bmv, [(0.9, deck + 2.5), (1.25, deck + 2.63), (0.9, deck + 2.76)], -0.015, 0.015, "xz")
            bm_prism(bmv, [(-0.9, deck + 2.45), (-0.55, deck + 2.63), (-0.9, deck + 2.81), (-1.2, deck + 2.81), (-0.95, deck + 2.63), (-1.2, deck + 2.45)], -0.015, 0.015, "xz")
            bm_prism(bmv, [(-0.2, deck + 2.66), (0.3, deck + 2.7), (0.45, deck + 2.95), (0.2, deck + 2.85), (-0.25, deck + 2.95), (-0.1, deck + 2.75)], -0.02, 0.02, "xz")
            obj_bm(f"ST_Pav_{name}_weathervane", bmv, "gold")


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
# The bed is round (the user's correction; the photos are wide-angle). Size (ESTIMATE): fence 34 m across, lawn 23 m;
# the lawn rises 7 deg towards World Bazaar (0.5 m at the front edge, 3.7 m at the back) so the whole face shows from the gates. The face reads as Mickey from
# straight above: round head, two round ears, the skin mask (lower oval + two tall lobes round the eyes with the
# widow's peak between), tall eyes, an oval nose, a smile turned up at the cheeks.
BED = dict(x=-538.0 - P0[0], y=927.3 - P0[1] - 1.0, ang=205.0,     # local +X: left to right for a guest at the gates,
           tilt=7.0, zc=1.0,                                         # local +Y: away from the gates (towards World Bazaar)
           fence=(7.2, 6.7), bank=(5.9, 5.5), brick=(5.8, 5.4), lawn=(5.1, 4.7))
# (R1 #3, 2026-10-04: the terracotta edging is about as broad as the lawn ring in the video, v2 0:00 .. 0:06: 0.7 m, was
#  0.4 m (brick 5.5 x 5.1, bank 5.7 x 5.3); the lawn and the face keep their size)
BED_SUMMER = True     # R1 #1 #2 #4: the summer planting of the daytime video (v2, July): a lime face with dark olive
                      # outlines on a plain lawn, a bright clipped bank. False: the winter one (purple and white, red ring)
# (2026-09-30, the user's photo of the whole front + OSM 1291649400: the planter is 14.4 x 13.3 m, the face in it about 6 m;
#  a stone curb with the plaza's teal railing, clipped green inside it, red flowers round the face. It was 24 m across before.)
# (2026-09-28: 34 m was too big -- only ~49 m between the World Bazaar portico and the gates' inner face, and the photos,
#  against people, put the bed at 15-20 m across the planting; 24 m to the fence leaves ~12 m of walkway either side)


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
    S = BED_SUMMER
    prism("ST_Bed_lawn", [ellipse(lx, ly)], -0.3, 0.0, "bed_lawn" if S else "flowers_red")   # summer: plain lawn (v2 0:00); winter: red flowers (photo)
    bm = bmesh.new()
    for q in band(ellipse(bx, by), ellipse(lx, ly)):
        bm_prism(bm, q, -0.3, 0.04, "xy")
    obj_bm("ST_Bed_brick_edging", bm, "bed_brick" if S else "brick")
    # the Mickey face, in flowers (units of the head radius R, x to the right, y up for a guest at the gates)
    k_ = lx / 8.1; R_ = 3.95 * k_; oy = -0.9 * k_                                   # head radius; the head sits a little low so the ears fit
    P_ = lambda x, y: (x * R_, y * R_ + oy)
    E_ = lambda rx, ry, cx, cy, n=48: ellipse(rx * R_, ry * R_, n, cx * R_, cy * R_ + oy)
    fz = 0.02
    bm = bmesh.new()                                   # purple head and ears (each a little higher: no coincident faces)
    for k, e in enumerate((E_(1.0, 1.0, 0.0, 0.0, 96), E_(0.62, 0.62, -0.95, 0.95, 64), E_(0.62, 0.62, 0.95, 0.95, 64))):
        bm_prism(bm, e, fz, fz + 0.14 + 0.01 * k, "xy")
    obj_bm("ST_Bed_mickey_head", bm, "bed_olive" if S else "flower_purple")
    bm = bmesh.new()                                   # the skin mask: a wide lower oval + two tall lobes (widow's peak between)
    for k, e in enumerate((E_(0.86, 0.6, 0.0, -0.3, 72), E_(0.3, 0.5, -0.27, 0.3, 48), E_(0.3, 0.5, 0.27, 0.3, 48))):
        bm_prism(bm, e, fz + 0.12, fz + 0.2 + 0.012 * k, "xy")
    obj_bm("ST_Bed_mickey_face", bm, "bed_lime" if S else "flower_white")
    feats = [E_(0.12, 0.25, -0.2, 0.36, 32), E_(0.12, 0.25, 0.2, 0.36, 32),          # eyes
             E_(0.22, 0.14, 0.0, -0.02, 36)]                                         # nose
    smile = []                                          # the smile: a crescent, turned up at the cheeks
    for k in range(33):
        u = -1 + 2 * k / 32
        smile.append(P_(0.62 * u, -0.26 - 0.32 * (1 - u * u) + 0.08 * u ** 4))
    for k in range(32, -1, -1):
        u = -1 + 2 * k / 32
        smile.append(P_(0.56 * u, -0.22 - 0.2 * (1 - u * u) + 0.1 * u ** 4))
    feats.append(smile)
    prism("ST_Bed_mickey_features", feats, fz + 0.2, fz + 0.28, "bed_olive" if S else "flower_purple")
    prism("ST_Bed_tongue", [E_(0.16, 0.07, 0.0, -0.55, 28)], fz + 0.2, fz + 0.27, "bed_olive" if S else "flowers_red")
    # the planting round the face (photo: purple and white flowers with red): a ring of alternating clumps on the lawn
    # (winter only: in summer the lawn round the face is plain, v2 0:00 .. 0:14)
    if not S:
        bmr, bmw_, bmp_ = bmesh.new(), bmesh.new(), bmesh.new()
        for k in range(36):
            a = 2 * math.pi * k / 36
            cx_, cy_ = (lx - 0.4) * math.cos(a), (ly - 0.4) * math.sin(a)
            bm_prism((bmr, bmw_, bmp_)[k % 3], ellipse(0.3, 0.3, 10, cx_, cy_), fz, fz + 0.22, "xy")
        obj_bm("ST_Bed_ring_red", bmr, "flowers_pink"); obj_bm("ST_Bed_ring_white", bmw_, "flower_white"); obj_bm("ST_Bed_ring_purple", bmp_, "flower_purple")
    B.root = prev
    # (b) the shrub bank: from the ground at the fence up to the brick edging on the tilted plane (a loft)
    ca, sa = math.cos(math.radians(BED["ang"])), math.sin(math.radians(BED["ang"]))
    to_plan = lambda X, Y, Zl: (BED["x"] + X * ca - (Y * math.cos(t) - Zl * math.sin(t)) * sa,
                                BED["y"] + X * sa + (Y * math.cos(t) - Zl * math.sin(t)) * ca,
                                zc + Y * math.sin(t) + Zl * math.cos(t))
    kx, ky = BED["bank"]; fx_, fy_ = BED["fence"]
    n = 96
    bm = bmesh.new()
    outer = [bm.verts.new((BED["x"] + X * ca - Y * sa, BED["y"] + X * sa + Y * ca, 0.4)) for X, Y in ellipse(fx_ - 0.3, fy_ - 0.3, n)]
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
    o = obj_bm("ST_Bed_shrubs", bm, "hedge_bright" if S else "hedge", smooth=True, recalc=False)
    # (c) the stone curb and the plaza's teal railing on it (photo 2026-09-30; it was a dark green fence on the paving)
    with frame("BED_flat", BED["x"], BED["y"], BED["ang"]):
        bm = bmesh.new()
        for q in band(ellipse(fx_ + 0.2, fy_ + 0.2), ellipse(fx_ - 0.3, fy_ - 0.3)):
            bm_prism(bm, q, 0.0, 0.45, "xy")
        obj_bm("ST_Bed_curb", bm, "stone")
        P = {"rail": bmesh.new()}
        railing(P, ellipse(fx_, fy_, 40), 0.45)
        obj_bm("ST_Bed_fence", P["rail"], "rail_teal")


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
    with frame("GREET_frame", WB["x"], WB["y"], WB["ang"]):
        build_greeting()
    fx, fy = BED["x"], BED["y"]
    # lamp posts with four globes: round the plaza and either side of the central pavilion
    ca, sa = math.cos(math.radians(BED["ang"])), math.sin(math.radians(BED["ang"]))
    posts = [(fx + 10.0 * math.cos(t) * ca - 10.0 * math.sin(t) * sa, fy + 10.0 * math.cos(t) * sa + 10.0 * math.sin(t) * ca)
             for t in (0.35, 2.79, 3.49, 5.93)]   # round the bed, outside its fence
    for d in (-12.0, 12.0):
        a = math.radians(ARC["a_mid"]); t = (-math.sin(a), math.cos(a))
        for rr in (49.0, 71.0):
            posts.append((A["cx"] + rr * math.cos(a) + t[0] * d, A["cy"] + rr * math.sin(a) + t[1] * d))
    bmp, bmg = bmesh.new(), bmesh.new()
    # (R1 #8, v2 0:08 .. 0:12, 0:38, v1 1:21:08 .. 1:21:20: the posts are about three people tall, ~5 m, on a pedestal,
    #  with big white globes: post 3.7 -> 4.8 m, arm globes 3.75 -> 4.8 m, the top one 4.05 -> 5.1 m, globes r 0.2 -> 0.28)
    for x, y in posts:
        bm_lathe(bmp, [(0, 0), (0.32, 0), (0.32, 0.12), (0.28, 0.16), (0.28, 0.82), (0.32, 0.86), (0.32, 0.92), (0.14, 1.1),
                       (0.1, 4.5), (0.15, 4.68), (0, 4.8)], 12, T(x, y, 0))
        for k in range(4):
            a = k * math.pi / 2
            bm_box(bmp, x + 0.02 * math.cos(a) - 0.035, x + 0.55 * math.cos(a) + 0.035, y + 0.02 * math.sin(a) - 0.035, y + 0.55 * math.sin(a) + 0.035, 4.5, 4.58)
            globe_lamp_bm(bmg, x + 0.6 * math.cos(a), y + 0.6 * math.sin(a), 4.82, 0.28)
        globe_lamp_bm(bmg, x, y, 5.1, 0.28)
    obj_bm("ST_Plaza_lampposts", bmp, "iron", smooth=True); obj_bm("ST_Plaza_globes", bmg, "lamp", smooth=True)
    # round flower beds at the feet of the lamp posts before and behind the central pavilion (ESTIMATE from the plan's
    # "花壇": a cream stone kerb 2.4 m across, a mound of clipped green edged with red and white flowers)
    bmk, bmh, bmr, bmw = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for x, y in posts[4:]:
        bm_lathe(bmk, [(0.95, 0), (1.2, 0), (1.2, 0.42), (1.1, 0.48), (0.95, 0.48)], 32, T(x, y, 0))
        bm_lathe(bmh, [(0.32, 0.3), (0.95, 0.3), (0.95, 0.5), (0.7, 0.72), (0.32, 0.8)], 24, T(x, y, 0))
        for k in range(20):                               # clumps round the kerb, red and white by turns
            a_ = 2 * math.pi * k / 20
            globe_lamp_bm(bmr if k % 2 else bmw, x + 0.8 * math.cos(a_), y + 0.8 * math.sin(a_), 0.56, 0.15)
    obj_bm("ST_Plaza_bed_kerbs", bmk, "stone"); obj_bm("ST_Plaza_bed_green", bmh, "hedge", smooth=True)
    obj_bm("ST_Plaza_bed_red", bmr, "flowers_red", smooth=True); obj_bm("ST_Plaza_bed_white", bmw, "flower_white", smooth=True)
    # (R1 #6, v2 0:36 .. 0:44: a mint cabinet, ~1.2 x 1.2 x 1.0 m with an oval panel, just outside the Mickey bed's fence on its
    #  World Bazaar side; one each side by symmetry. ESTIMATE: no web source places them)
    with frame("BED_boxes", BED["x"], BED["y"], BED["ang"]):
        bmb, bmo = bmesh.new(), bmesh.new()
        for s in (-1, 1):
            x, y = s * 5.2, 6.0
            bm_box(bmb, x - 0.6, x + 0.6, y - 0.6, y + 0.6, 0.0, 0.95)
            bm_box(bmb, x - 0.66, x + 0.66, y - 0.66, y + 0.66, 0.95, 1.03)
            bm_box(bmb, x - 0.63, x + 0.63, y - 0.63, y + 0.63, 0.0, 0.08)
            bm_lathe(bmo, [(0, 0), (0.3, 0), (0.3, 0.02), (0, 0.02)], 16, T(x, y + 0.6, 0.5) @ R(-math.pi / 2, "X") @ Matrix.Diagonal((1.0, 0.7, 1.0, 1.0)))
        obj_bm("ST_Plaza_cabinets", bmb, "mint"); obj_bm("ST_Plaza_cabinet_panels", bmo, "trim")


# ================================================================ 5. the planters in front of World Bazaar, the greeting plazas (2026-09-30)
# The user's photos (2026-09-30): every planter here has a stone curb with a pale teal iron railing on it (square posts
# with ball finials, top and bottom rails, pickets under an arched rail in each panel) and is planted with pink, purple
# and white flowers; the "Disney Character Greeting" spots either side are brick-paved (herringbone, terracotta) inside
# a C of planters, with a white sign post (a teal cap and a red roundel on top) at the opening; the planter in the middle
# in front of the entrance has a hedge ring and red flowers. OSM: the planters are the inner rings of the plaza
# (ds_tdl_ground builds their curbs and soil), the east greeting plaza is the pedestrian area 1291649416, the west one is
# its mirror image (its ring 1291649409 is the east one's mirror), the middle planter 795427954 (not a ring of the plaza:
# this builds it whole). Topiaries (spirals and tiered balls) stand in the greeting plazas' planters only (the user, 2026-09-30).
# ESTIMATES: the railing's size (0.9 m), the flower mix, the sign's size.
PLANTERS = (788435491, 1291649410, 1291649411, 1291649412, 1291649413, 1291649424, 1291649409, 1291649418, 1291649414, 1291649415)
GREET_WAY, MIDDLE_WAY = 1291649416, 795427954
CURB_TOP = -0.03 + 0.30                                   # ds_tdl_ground: the flat ground + CURB_H


def osm_wb(way_ids):
    """OSM ways -> their rings in the World Bazaar frame (counter-clockwise)."""
    ways = {w["id"]: w for w in json.loads((ROOT / "plateau_data" / "disneyland_osm.json").read_text(encoding="utf-8"))["ways"]}
    a = math.radians(WB["ang"]); out = {}
    for i in way_ids:
        pts = [((x + 521.3) * math.cos(a) + (y - 891.2) * math.sin(a), -(x + 521.3) * math.sin(a) + (y - 891.2) * math.cos(a))
               for x, y in ways[i]["pts"][:-1]]
        out[i] = pts if poly_area(pts) > 0 else pts[::-1]
    return out


def poly_area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def inset(p, d):
    """A counter-clockwise ring moved d inwards (mitred, clamped at sharp corners)."""
    out = []
    for i in range(len(p)):
        a, b, c = p[i - 1], p[i], p[(i + 1) % len(p)]
        n1 = (-(b[1] - a[1]), b[0] - a[0]); l1 = math.hypot(*n1) or 1; n1 = (n1[0] / l1, n1[1] / l1)
        n2 = (-(c[1] - b[1]), c[0] - b[0]); l2 = math.hypot(*n2) or 1; n2 = (n2[0] / l2, n2[1] / l2)
        m = (n1[0] + n2[0], n1[1] + n2[1]); lm = math.hypot(*m) or 1
        k = d / max(0.5, (m[0] * n1[0] + m[1] * n1[1]) / lm)
        out.append((b[0] + m[0] / lm * k, b[1] + m[1] / lm * k))
    return out


def inside(p, q):
    x, y = q; c = False
    for i in range(len(p)):
        (x1, y1), (x2, y2) = p[i - 1], p[i]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def edge_dist(p, q):
    best = 1e9
    for i in range(len(p)):
        (ax, ay), (bx, by) = p[i - 1], p[i]; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / L2))
        best = min(best, math.hypot(q[0] - ax - dx * t, q[1] - ay - dy * t))
    return best


def railing(P, ring, z0, h=0.9):
    """The teal railing round a ring (its path already inset onto the curb)."""
    for i in range(len(ring)):
        a, b = ring[i - 1], ring[i]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 0.05:
            continue
        obox(P["rail"], a, b, 0.05, z0 + 0.08, z0 + 0.13)
        obox(P["rail"], a, b, 0.06, z0 + h - 0.06, z0 + h)
        n = max(1, math.ceil(L / 1.7))
        for j in range(n):                                # panels: a post, an arched rail, pickets up to it
            f0, f1 = j / n, (j + 1) / n
            pa = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
            bm_box(P["rail"], pa[0] - 0.05, pa[0] + 0.05, pa[1] - 0.05, pa[1] + 0.05, z0, z0 + h + 0.06)
            bm_lathe(P["rail"], [(0, 0), (0.05, 0.02), (0.07, 0.07), (0.05, 0.12), (0, 0.14)], 6, T(pa[0], pa[1], z0 + h + 0.06))
            pl = L * (f1 - f0); arc = lambda t: z0 + 0.5 + 0.28 * math.sin(math.pi * t)
            steps = 6
            for s in range(steps):
                t0, t1 = s / steps, (s + 1) / steps
                q0 = (a[0] + (b[0] - a[0]) * (f0 + (f1 - f0) * t0), a[1] + (b[1] - a[1]) * (f0 + (f1 - f0) * t0))
                q1 = (a[0] + (b[0] - a[0]) * (f0 + (f1 - f0) * t1), a[1] + (b[1] - a[1]) * (f0 + (f1 - f0) * t1))
                zt = arc((t0 + t1) / 2)
                obox(P["rail"], q0, q1, 0.035, zt - 0.02, zt + 0.02)
            npk = max(1, int(pl / 0.15))
            for s in range(1, npk):
                t = s / npk; q = (a[0] + (b[0] - a[0]) * (f0 + (f1 - f0) * t), a[1] + (b[1] - a[1]) * (f0 + (f1 - f0) * t))
                bm_box(P["rail"], q[0] - 0.013, q[0] + 0.013, q[1] - 0.013, q[1] + 0.013, z0 + 0.13, arc(t))


def planting(P, ring, z0, rng, core="soil", band=(0.05, 2.4), step=0.5):
    """Flower clumps on a grid in the band `band` m in from the ring's edge; the deeper middle: `core`."""
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    y = min(ys) + step / 2
    while y < max(ys):
        x = min(xs) + step / 2 + (step / 2 if round(y / step) % 2 else 0)
        while x < max(xs):
            q = (x + rng.uniform(-0.1, 0.1), y + rng.uniform(-0.1, 0.1))
            if inside(ring, q):
                d = edge_dist(ring, q)
                if band[0] <= d < band[1]:
                    k = rng.choice(("fl_pink", "fl_pink", "fl_purple", "fl_white"))
                    s = rng.uniform(0.8, 1.15)
                    bm_lathe(P[k], [(0, 0), (0.33 * s, 0), (0.28 * s, 0.24 * s), (0, 0.42 * s)], 5, T(q[0], q[1], z0))
                elif d >= band[1] and core != "soil":
                    s = rng.uniform(0.9, 1.1)
                    bm_lathe(P[core], [(0, 0), (0.33 * s, 0), (0.28 * s, 0.2 * s), (0, 0.34 * s)], 5, T(q[0], q[1], z0))
            x += step
        y += step


def greeting_sign(x, y, ang):
    """The white sign post (photos): a square post on a base, a framed board with a teal cap, a red roundel on top."""
    with frame(f"GREET_sign{round(x)}", x, y, ang):
        box("ST_GR_sign_post", [(-0.09, 0.09, -0.09, 0.09, 0.0, 2.6), (-0.2, 0.2, -0.2, 0.2, 0.0, 0.25), (-0.13, 0.13, -0.13, 0.13, 1.12, 1.2)], "white")
        box("ST_GR_sign_board", [(-0.55, 0.55, 0.1, 0.16, 1.25, 2.35)], "white")
        box("ST_GR_sign_face", [(-0.45, 0.45, 0.16, 0.17, 1.35, 2.05)], "sign_face")
        box("ST_GR_sign_cap", [(-0.62, 0.62, 0.02, 0.22, 2.35, 2.45)], "rail_teal")
        bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.22, 0), (0.22, 0.05), (0, 0.05)], 16, T(0, 0.14, 2.72) @ R(-math.pi / 2, "X"))
        obj_bm("ST_GR_sign_roundel", bm, "flowers_red")
        bm = bmesh.new(); bm_lathe(bm, [(0.2, 0), (0.26, 0), (0.26, 0.06), (0.2, 0.06)], 16, T(0, 0.13, 2.72) @ R(-math.pi / 2, "X"))
        obj_bm("ST_GR_sign_roundel_rim", bm, "rail_teal")
        text("ST_GR_sign_text", "DISNEY CHARACTER\nGREETING", 0.09, (0, 0.18, 2.2), (math.pi / 2, 0, math.pi), "sign_ink", 0.005)


def ball(bm, x, y, z, r, segs=7):
    bm_lathe(bm, [(0, -r)] + [(r * math.sin(math.pi * i / 4), -r * math.cos(math.pi * i / 4)) for i in (1, 2, 3)] + [(0, r)], segs, T(x, y, z))


def topiary(P, x, y, z0, kind, rng):
    """The greeting plazas' topiaries (photos): a spiral on a stem, or three clipped balls one above the other."""
    bm_box(P["trunk"], x - 0.04, x + 0.04, y - 0.04, y + 0.04, z0, z0 + 2.2)
    if kind == 0:
        ph = rng.uniform(0, 6.28); n = 18
        for i in range(n):
            f = i / (n - 1); a = ph + f * 6 * math.pi; rr = 0.36 * (1 - f) + 0.04
            ball(P["hedge"], x + rr * math.cos(a), y + rr * math.sin(a), z0 + 0.35 + f * 2.0, 0.34 * (1 - f) + 0.12)
    elif kind == 1:
        for z, r in ((0.6, 0.5), (1.4, 0.4), (2.05, 0.3)):
            ball(P["hedge"], x, y, z0 + z, r, 9)
    else:                                                 # a clipped ball on a stem (R1 #12, v2 0:02, 0:38)
        bm_box(P["trunk"], x - 0.06, x + 0.06, y - 0.06, y + 0.06, z0, z0 + 1.4)
        ball(P["hedge"], x, y, z0 + 1.9, 0.8, 12)


def build_front_topiaries(P, rng):
    """R1 #12 (v2 0:02, 0:38): a tall clipped ball on a stem in a round stone tub beside each conservatory, on the
    outer side (the inner side is the greeting plaza's small planter, which has its topiary already). Placed 6 m along
    the angled front from the OSM corner, 5.2 m out (clear of the side portico). ESTIMATE: the tub, the sizes."""
    for k, c in enumerate(CONS_CORNERS):
        chain = FRONT_CHAINS[k]; i = chain.index(c)
        o = chain[i - 1] if k == 0 else chain[i + 1]       # the far end of the angled face
        a, b = (o, c) if k == 0 else (c, o)               # the face's own direction (its +y side is out)
        L = math.hypot(b[0] - a[0], b[1] - a[1]); n = (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)
        u = ((o[0] - c[0]) / L, (o[1] - c[1]) / L)
        x, y = c[0] + u[0] * 6.0 + n[0] * 5.2, c[1] + u[1] * 6.0 + n[1] * 5.2
        bm_lathe(P["tub"], [(0.0, 0), (0.85, 0), (0.85, 0.5), (0.75, 0.55), (0.0, 0.55)], 24, T(x, y, 0))
        bm_lathe(P["hedge"], [(0.0, 0.5), (0.72, 0.5), (0.7, 0.7), (0.4, 0.82), (0.0, 0.85)], 16, T(x, y, 0))
        topiary(P, x, y, 0.55, 2, rng)


def build_greeting():
    rng = random.Random(3)
    rings = osm_wb(PLANTERS + (GREET_WAY, MIDDLE_WAY))
    P = {k: bmesh.new() for k in ("rail", "fl_pink", "fl_purple", "fl_white", "hedge", "red", "trunk", "tub")}
    for i in PLANTERS:                                    # the plaza's planters: railing on the curb, flowers
        railing(P, inset(rings[i], 0.17), CURB_TOP)
        planting(P, inset(rings[i], 0.32), CURB_TOP - 0.06, rng)
    k = 0
    for i in (1291649409, 1291649418, 1291649414, 1291649415):      # topiaries in the greeting plazas' planters (the user, 2026-09-30)
        ring = rings[i]; xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        cand = []                                         # the planters are narrow: along their middle, 1.7 m apart
        y = min(ys)
        while y < max(ys):
            x = min(xs)
            while x < max(xs):
                if inside(ring, (x, y)):
                    d = edge_dist(ring, (x, y))
                    if d >= 0.3:
                        cand.append((d, x, y))
                x += 0.25
            y += 0.25
        placed = []
        for d, x, y in sorted(cand, reverse=True):
            if all(math.hypot(x - px, y - py) >= 1.7 for px, py in placed):
                placed.append((x, y)); topiary(P, x, y, CURB_TOP - 0.06, k % 2, rng); k += 1
    print("[entrance] topiaries", k)
    build_front_topiaries(P, rng)
    mid = rings[MIDDLE_WAY]                               # the middle planter: curb, hedge ring, red flowers
    prism("ST_GR_mid_curb", [mid], -0.03, 0.42, "stone")
    railing(P, inset(mid, 0.17), 0.42)
    planting(P, inset(mid, 1.1), 0.42, rng, core="red", band=(0.0, 0.0))
    ring = inset(mid, 0.55)
    for j in range(len(ring)):                            # the clipped hedge just inside the curb
        obox(P["hedge"], ring[j - 1], ring[j], 0.55, 0.42, 0.95)
    g = rings[GREET_WAY]                                  # the greeting plazas: brick floor, a pale stone edge
    for pts in (g, [(-x, y) for x, y in g][::-1]):
        prism(f"ST_GR_floor{round(pts[0][0])}", [pts], -0.03, 0.006, "brick_paving")
        prism(f"ST_GR_floor_inner{round(pts[0][0])}", [inset(pts, 0.45)], 0.006, 0.012, "brick_paving2")
    for s in (-1, 1):
        greeting_sign(s * 40.2, 12.9, 0.0)
    for k, bm_ in P.items():
        mat = {"rail": "rail_teal", "fl_pink": "flowers_pink", "fl_purple": "flower_purple", "fl_white": "flower_white",
               "hedge": "hedge", "red": "flowers_red", "trunk": "door_brown", "tub": "stone"}[k]
        obj_bm(f"ST_GR_{k}", bm_, mat)


# ================================================================ scene
def cams():
    a = math.radians(ARC["a_mid"]); pav = arc_point(ARC["a_mid"]); ou = (math.cos(a), math.sin(a))
    def wbp(lx, ly):                                      # World Bazaar local (x along the front, y to the plaza) -> plan
        a = math.radians(WB["ang"])
        return (WB["x"] + lx * math.cos(a) - ly * math.sin(a), WB["y"] + lx * math.sin(a) + ly * math.cos(a))
    return {
        "gate_out": ((pav[0] + ou[0] * 32, pav[1] + ou[1] * 32, 1.7), (pav[0], pav[1], 6.0), 24),
        "gate_in": ((pav[0] - ou[0] * 17, pav[1] - ou[1] * 17, 1.7), (pav[0], pav[1], 6.0), 20),
        "gate_detail": ((pav[0] + ou[0] * 12 + ou[1] * 17, pav[1] + ou[1] * 12 - ou[0] * 17, 1.7), (pav[0] + ou[1] * 13, pav[1] - ou[0] * 13, 5.0), 24),
        "gate_sign": ((pav[0] + ou[0] * 14, pav[1] + ou[1] * 14, 1.7), (pav[0], pav[1], 7.8), 35),
        "gates_arc": ((ARC["cx"] + 5, ARC["cy"] + 10, 2.0), (arc_point(160)[0], arc_point(160)[1], 4.0), 20),
        "wb_photo": ((*wbp(0.0, 20.3), 1.65), (*wbp(0.0, 4.6), 6.4), 19),      # as the user's photo: just outside the bed's fence
        "wb_front": ((*wbp(-30.0, 42.0), 1.7), (*wbp(0.0, 0.0), 7.5), 24),     # the whole front, beside the flowerbed
        "wb_porch": ((*wbp(9.0, 14.0), 1.7), (*wbp(-2.0, 2.0), 5.5), 20),
        "wb_sign": ((*wbp(0.0, 11.5), 1.6), (*wbp(0.0, 4.8), 5.4), 22),
        "wb_back": ((*wbp(0.0, -36.0), 1.6), (*wbp(0.0, WB_BACK), 6.5), 22),  # from Main Street, as the user's photo
        "wb_whole": ((*wbp(0.0, 47.0), 1.7), (*wbp(0.0, 0.0), 6.0), 16),         # the user's photo of the whole front
        "wb_msh": ((*wbp(-56.0, -1.8), 1.6), (*wbp(-48.8, -6.0), 3.3), 18),      # Main Street House, as the user's photos
        "wb_greet": ((*wbp(-27.0, 21.0), 1.6), (*wbp(-45.0, 1.0), 4.0), 16),    # the west greeting plaza and the conservatory
        "wb_greet_e": ((*wbp(29.0, 17.5), 2.2), (*wbp(37.0, 9.0), 0.0), 16),
        "flowerbed": bed_cam(20.5, 1.7, 16),              # from the gates' side, as the photos (the face reads upright)
        "flowerbed_top": bed_cam(26.0, 14.0, 26),
        "flowerbed_plan": ((BED["x"], BED["y"] - 0.01, 70.0), (BED["x"], BED["y"], 0.0), 35),   # straight down
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
    build_world_bazaar()                                  # the video's subject, in its order (sign, pillars, beams, arches, building)
    build_gates()
    build_plaza(context)
    if context:                                           # 1.70 m figures at the World Bazaar portico, for the scale
        old = B.col; B.col = bpy.data.collections["Context"]
        with frame("WB_people", WB["x"], WB["y"], WB["ang"]):
            wb_people()
        B.col = old
    out = {}                                              # (the cutters keep their frame as parent: they are in its coordinates)
    for name, (loc, tgt, lens) in cams().items():
        cam = bpy.data.cameras.new("CAM_" + name); cam.lens = lens; cam.clip_start = 0.05; cam.clip_end = 3000
        co = bpy.data.objects.new("CAM_" + name, cam); B.col.objects.link(co); co.parent = B.root
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        if name == "flowerbed_plan":                      # straight down, turned so that Mickey stands upright
            co.rotation_euler = (0, 0, math.radians(BED["ang"]))
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
        if o.name.startswith("ST_Gate_") and "_entrance" in o.name:
            continue                                      # web weight: the bays' small ENTRANCE lettering (the boards stay)
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if mats:
            groups.setdefault("EN_" + mats[0].name[3:], []).append((o, GROUND_DATUM))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="gate_in,gate_out,gates_arc,wb_photo,wb_front,wb_porch,wb_sign,wb_back,flowerbed,aerial")
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
