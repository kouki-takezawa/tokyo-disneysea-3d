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
import sys, math, argparse, pathlib, time

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
    M["screen"] = P("st_screen", (0.05, 0.12, 0.20), 0.15, Emission_Color=(0.3, 0.6, 0.9, 1), Emission_Strength=0.6)
    M["mauve"] = P("st_mauve", (0.30, 0.09, 0.13), 0.6)                    # the World Bazaar shops' mansards
    M["hall_iron"] = P("st_hall_iron", (0.15, 0.30, 0.28), 0.45, Metallic=0.5)
    M["hall_glass"] = ST.clear_glass("st_hall_glass", (0.70, 0.86, 0.82), 0.35)
    M["person"] = P("st_person", (0.22, 0.26, 0.36), 0.8)                  # 1.70 m scale figures (check renders only)
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
    rim = [(-hw - 0.07, zb - 0.07), (hw + 0.07, zb - 0.07)] + [(x * (hw + 0.07) / hw, z + 0.07) for x, z in top]
    prism("ST_WB_sign_rim", [rim], yf, yf + 0.11, "gold", "xz")
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
    prism("ST_WB_welcome_rim", [cart(1.53, 0.43)], yf + 0.14, yf + 0.22, "gold", "xz")
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
    bmp, bmc, bmr, bmk = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for x, kind in piers:
        px, py, pb = PW[kind]
        bm_box(bmp, x - px - 0.05, x + px + 0.05, yf - py - 0.05, yf + py + 0.05, 0, 0.2)      # pedestal: plinth, die, cap
        bm_box(bmp, x - px, x + px, yf - py, yf + py, 0.2, ped - 0.14)
        bm_box(bmp, x - px - 0.05, x + px + 0.05, yf - py - 0.05, yf + py + 0.05, ped - 0.14, ped)
        bm_box(bmk, x - px + 0.14, x + px - 0.14, yf + py, yf + py + 0.03, 0.36, ped - 0.3)     # raised panel
        for dx, dy in OFF[kind]:
            column_bm(bmc, x + dx, yf + dy, ped, cap - ped, 0.14, 12)
            for f in (0.36, 0.68):                                                              # collars on the shaft
                bm_lathe(bmr, [(0.12, 0), (0.18, 0.03), (0.18, 0.1), (0.12, 0.13)], 12, T(x + dx, yf + dy, ped + (cap - ped) * f))
        bm_box(bmp, x - pb - 0.06, x + pb + 0.06, yf - pb - 0.06, yf + pb + 0.06, cap, cap + 0.1)  # abacus, block
        bm_box(bmp, x - pb, x + pb, yf - pb, yf + pb, cap + 0.1, blk)
        bm_box(bmk, x - pb + 0.1, x + pb - 0.1, yf + pb, yf + pb + 0.03, cap + 0.3, blk - 0.2)
    obj_bm(f"ST_WB_{name}_piers", bmp, "trim"); obj_bm(f"ST_WB_{name}_panels", bmk, "trim")
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
    box(f"ST_WB_{name}_floor", (xl - 0.3, xr + 0.3, 0.0, yf + 0.8, 0.0, 0.04), "tile")
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
    box("ST_WB_passage", [(x - w / 2, x + w / 2, WB_BACK, 0.0, 0.0, 0.03) for x, w, sp, r, th in bays if th], "tile")
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


def wb_shops(s):
    """The shops either side (OSM 365357846 / 72216851, 8.85 m), x = 12.25 .. 35.5 on side s."""
    arcade_front(f"shop{s}", 12.25, 35.5, s)


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
        for s in (-1, 1):
            wb_shops(s)


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
           tilt=7.0, zc=1.5,                                         # local +Y: away from the gates (towards World Bazaar)
           fence=(12.0, 12.0), bank=(9.1, 9.1), brick=(8.8, 8.8), lawn=(8.1, 8.1))   # round (user, 2026-09-24); 24 m across
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
    prism("ST_Bed_lawn", [ellipse(lx, ly)], -0.3, 0.0, "grass")
    bm = bmesh.new()
    for q in band(ellipse(bx, by), ellipse(lx, ly)):
        bm_prism(bm, q, -0.3, 0.04, "xy")
    obj_bm("ST_Bed_brick_edging", bm, "brick")
    # the Mickey face, in flowers (units of the head radius R, x to the right, y up for a guest at the gates)
    R_ = 3.95; oy = -0.9                                   # head radius; the head sits a little low so the ears fit
    P_ = lambda x, y: (x * R_, y * R_ + oy)
    E_ = lambda rx, ry, cx, cy, n=48: ellipse(rx * R_, ry * R_, n, cx * R_, cy * R_ + oy)
    fz = 0.02
    bm = bmesh.new()                                   # purple head and ears (each a little higher: no coincident faces)
    for k, e in enumerate((E_(1.0, 1.0, 0.0, 0.0, 96), E_(0.62, 0.62, -0.95, 0.95, 64), E_(0.62, 0.62, 0.95, 0.95, 64))):
        bm_prism(bm, e, fz, fz + 0.14 + 0.01 * k, "xy")
    obj_bm("ST_Bed_mickey_head", bm, "flower_purple")
    bm = bmesh.new()                                   # the skin mask: a wide lower oval + two tall lobes (widow's peak between)
    for k, e in enumerate((E_(0.86, 0.6, 0.0, -0.3, 72), E_(0.3, 0.5, -0.27, 0.3, 48), E_(0.3, 0.5, 0.27, 0.3, 48))):
        bm_prism(bm, e, fz + 0.12, fz + 0.2 + 0.012 * k, "xy")
    obj_bm("ST_Bed_mickey_face", bm, "flower_white")
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
    prism("ST_Bed_mickey_features", feats, fz + 0.2, fz + 0.28, "flower_purple")
    prism("ST_Bed_tongue", [E_(0.16, 0.07, 0.0, -0.55, 28)], fz + 0.2, fz + 0.27, "flowers_red")
    prism("ST_Bed_red_flowers", [ellipse(0.85, 0.85, 32, 5.85, -5.1)], fz, fz + 0.3, "flowers_red")
    prism("ST_Bed_white_flowers", [ellipse(0.8, 0.8, 32, 4.45, -6.35)], fz, fz + 0.3, "flower_white")
    # the planting round the face (photo: purple and white flowers with red): a ring of alternating clumps on the lawn
    bmr, bmw_, bmp_ = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(40):
        a = 2 * math.pi * k / 40; rr = lx - 0.55
        cx_, cy_ = rr * math.cos(a), rr * math.sin(a)
        if abs(cx_ - 5.85) < 1.3 and abs(cy_ + 5.1) < 1.3 or abs(cx_ - 4.45) < 1.3 and abs(cy_ + 6.35) < 1.3:
            continue
        bm_prism((bmr, bmw_, bmp_)[k % 3], ellipse(0.32, 0.32, 10, cx_, cy_), fz, fz + 0.22, "xy")
    obj_bm("ST_Bed_ring_red", bmr, "flowers_red"); obj_bm("ST_Bed_ring_white", bmw_, "flower_white"); obj_bm("ST_Bed_ring_purple", bmp_, "flower_purple")
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
    posts = [(fx + 15.0 * math.cos(t) * ca - 15.0 * math.sin(t) * sa, fy + 15.0 * math.cos(t) * sa + 15.0 * math.sin(t) * ca)
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
