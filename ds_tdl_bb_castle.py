"""美女と野獣の城 (Tokyo Disneyland, New Fantasyland, opened 2020-09-28) -- Blender 5.2.

  blender -b --python ds_tdl_bb_castle.py -- --samples 32          # renders + output/disneyland/bb_castle/bb_castle.blend
  blender -b --python ds_tdl_bb_castle.py -- --cams none

Sources (looked at only; nothing copied into the repository):
  * Reference video (README): WALT.「美女と野獣 - blender short film」(CIx4qyGuVLY, the only non-Shorts one): it
    films the enchanted rose under its glass dome, not the castle -> the rose is set on the pedestal in the courtyard.
  * Wikimedia Commons "Tokyo Disneyland Enchanted Tale of Beauty and the Beast" (2023-11, CC BY 2.0) and
    "Tokyo Disneyland (Oct 2020)" (CC BY-SA 4.0), "Disneyland Tokyo1234" (CC0), "Tokyo Disneyland under COVID-19"
    (CC BY-SA 2.0): the front seen from the bridge, the gatehouse, the courtyard, the grand stair, the keep at dusk.
  * Web: height about 28-30 m, second to Cinderella Castle (51 m) (ja.wikipedia, TDR blog, travel articles);
    French decoration with Renaissance elements; the angel statues turned into gargoyles by the curse.
  * OSM: the castle node 12883893925 (-622.4, 496.7), the queue bridge 1075436730 from (-609.5, 520.7) to the gate at
    (-622.0, 497.1), the gatehouse building 1042261257, the show building 754497701 behind, rocks (scree) around.

What the photos show, front to back (all built):
  bridge over a rocky chasm (stone parapets with cream coping, iron lamp posts on gargoyle plinths) ->
  gatehouse: pointed central arch with a studded wooden door, two side niches with lion statues, a lion-head relief,
  two corner towers under steep conical pink roofs, a cream dormer with an arched window, flanked by long low wings
  (lilac stone, two rows of arched windows, balustraded parapet with winged gargoyles), a copper-green dome with a
  gargoyle on top on the left ->
  courtyard: stone paving with a round medallion, an arcade of round arches on columns along the left, lamp posts ->
  the palace: a grand stair between lion statues up to a pointed door, two big round towers (darker base course,
  corbel ring, tall arched windows, conical pink roofs), a steep pink hip roof with cream dormers, balconies with
  balustrades, an upper stage with more dormers and pinnacles ->
  the keep: a tall square tower with a machicolated crenellated top (about 30 m) and a slim round turret with a spire,
  a second slender round tower with a spire, chimneys, gold finials.
Colours: lilac-grey stone, cream trim, rose-pink roof tiles, copper-green dome, gold finials, dark wood doors.

Frame: local metres, origin = the gate (OSM (-622.0, 497.1)); +Y into the castle (towards the south-west), +X to the
right of a guest facing the castle. Ground 0 (the DEM here: see GROUND_DATUM).
ESTIMATES: every size (scaled from the photos with the 4 m bridge and the 30 m height), the plan behind the gate
(the aerial photo predates the castle), the number of windows and statues, the rock shapes.
"""
import sys, math, argparse, pathlib, time, random

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix, noise
except ImportError:
    bpy = bmesh = Vector = Matrix = noise = None

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ds_tdl_station as ST
from ds_tdl_station import (B, box, prism, bm_box, bm_lathe, bm_prism, obj_bm, array_mod, radial_array, T, R, seg_arc,
                            _principled, _mottle, _bump, text)

OUT = ROOT / "output" / "disneyland" / "bb_castle"
GATE = (-622.0, 497.1)
ANG = 152.1                     # the local X axis in the plan (deg): the castle faces NE, towards the bridge
GROUND_DATUM = 0.0              # set from the DEM by export_objects()
rnd = random.Random(11)


# ================================================================ materials
def materials():
    M = ST.materials()
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]

    def stone(name, c1, c2, w=0.9, h=0.42):
        mat, nt, b = _principled(name, c1, 0.8)
        br = nt.nodes.new("ShaderNodeTexBrick")
        for k, v in (("Color1", (*c1, 1)), ("Color2", (*c2, 1)), ("Mortar", (*[x * 0.8 for x in c1], 1)), ("Scale", 1.0),
                     ("Mortar Size", 0.012), ("Brick Width", w), ("Row Height", h)):
            br.inputs[k].default_value = v
        br.offset = 0.5
        nt.links.new(ST._wall_uv(nt), br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
        _bump(nt, b, br.outputs["Fac"], -0.3, 0.01)
        return mat
    M["lilac"] = stone("bb_lilac", (0.50, 0.45, 0.58), (0.46, 0.42, 0.55))          # lilac-grey (photos, daylight)
    M["base"] = stone("bb_base", (0.33, 0.31, 0.43), (0.30, 0.28, 0.40), 1.2, 0.6)
    mat, nt, b = _principled("bb_cream", (0.78, 0.68, 0.52), 0.6); _mottle(nt, b, (0.78, 0.68, 0.52), 6, 0.9, 0.05); M["cream"] = mat
    M["roof"] = ST.mat_tiles("bb_roof", (0.62, 0.22, 0.30), (0.55, 0.19, 0.27), 0.32, (0.40, 0.15, 0.20))
    M["dome"] = P("bb_dome", (0.40, 0.55, 0.50), 0.5, Metallic=0.4)
    M["gold"] = P("bb_gold", (0.86, 0.66, 0.28), 0.25, Metallic=1.0)
    M["glass"] = P("bb_glass", (0.10, 0.12, 0.20), 0.08, Coat_Weight=1.0)
    M["stained"] = P("bb_stained", (0.30, 0.16, 0.36), 0.1, Emission_Color=(0.9, 0.5, 0.3, 1), Emission_Strength=0.15)
    M["wood"] = P("bb_wood", (0.30, 0.16, 0.09), 0.7)
    M["iron"] = P("bb_iron", (0.05, 0.05, 0.06), 0.4, Metallic=0.7)
    M["statue"] = P("bb_statue", (0.72, 0.69, 0.64), 0.7)
    M["paving"] = ST.mat_tiles("bb_paving", (0.46, 0.46, 0.49), (0.40, 0.41, 0.45), 0.6, (0.30, 0.30, 0.32))
    mat, nt, b = _principled("bb_rock", (0.30, 0.30, 0.28), 0.9); _mottle(nt, b, (0.30, 0.30, 0.28), 1.5, 0.65, 0.4); M["rock"] = mat
    M["water"] = P("bb_water", (0.85, 0.92, 0.95), 0.1, Transmission_Weight=0.5)
    M["lamp"] = P("bb_lamp", (1.0, 0.85, 0.55), 0.3, Emission_Color=(1.0, 0.8, 0.45, 1), Emission_Strength=3.0)
    M["rose"] = P("bb_rose", (0.75, 0.05, 0.2), 0.4, Emission_Color=(0.9, 0.1, 0.3, 1), Emission_Strength=1.0)
    M["bell"] = ST.clear_glass("bb_bell", (0.9, 0.95, 1.0), 0.25)
    M["ground_ctx"] = P("bb_ground_ctx", (0.36, 0.30, 0.28), 0.9)
    M["grass"] = P("bb_grass", (0.16, 0.30, 0.10), 0.9)
    return M


# ================================================================ building kit: one bmesh per material, faces as frames
class Parts(dict):
    def __missing__(self, k):
        self[k] = bmesh.new()
        return self[k]

    def flush(self, prefix):
        for k, bm in list(self.items()):
            if bm.verts:
                o = obj_bm(f"BB_{prefix}_{k}", bm, k, smooth=(k == "rock"))
        self.clear()


def xf(bm, verts, M):
    for v in verts:
        v.co = M @ v.co


def cube(P, mat, M, x0, x1, y0, y1, z0, z1):
    xf(P[mat], bm_box(P[mat], x0, x1, y0, y1, z0, z1), M)


def lathe(P, mat, prof, segs, M):
    bm_lathe(P[mat], prof, segs, M)


def poly_prism(P, mat, M, pts, w0, w1):
    """Polygon (u, z) in a face, extruded along the face normal w0..w1 (the face frame M: u, w (outward), z)."""
    bm = P[mat]
    v0 = [bm.verts.new(M @ Vector((u, w0, z))) for u, z in pts]; v1 = [bm.verts.new(M @ Vector((u, w1, z))) for u, z in pts]
    bm.faces.new(v0); bm.faces.new(v1[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((v0[i], v1[i], v1[j], v0[j]))


def face(ox, oy, a):
    """Face frame: u along the wall at angle a (rad), w outward (u rotated by -90 deg), z up, origin (ox, oy, 0)."""
    u = Vector((math.cos(a), math.sin(a), 0)); w = Vector((math.sin(a), -math.cos(a), 0))
    return Matrix(((u.x, w.x, 0, ox), (u.y, w.y, 0, oy), (0, 0, 1, 0), (0, 0, 0, 1)))


def pointed(u0, u1, spring, n=10):
    """Outline of a pointed (gothic) opening from the sill at z 0... springing at `spring`: two arcs of radius = width."""
    w = u1 - u0; r = w * 0.85; h = math.sqrt(r * r - (r - w / 2) ** 2)
    right = [(u0 + r * math.cos(t), spring + r * math.sin(t)) for t in [math.acos((w - r) / r) * k / n for k in range(n + 1)]]
    right = [(u0 + r - (r - (x - u0)) , z) for x, z in right]
    pts_r = [(u1 - (r - r * math.cos(t)), spring + r * math.sin(t)) for t in [math.acos((r - w / 2) / r) * k / n for k in range(n + 1)]]
    pts_l = [(u0 + (r - r * math.cos(t)), spring + r * math.sin(t)) for t in [math.acos((r - w / 2) / r) * k / n for k in range(n, -1, -1)]]
    return pts_r + pts_l


def round_top(u0, u1, spring, n=10):
    c, r = (u0 + u1) / 2, (u1 - u0) / 2
    return [(c + r * math.cos(math.pi * k / n), spring + r * math.sin(math.pi * k / n)) for k in range(n + 1)]


def window(P, M, u, z0, w, h, kind="pointed", frame=0.14, glass="glass", sill=True):
    """A window on a face: dark glass just proud of the wall, a cream frame round it, a sill."""
    u0, u1 = u - w / 2, u + w / 2
    spring = z0 + h - (w * 0.8 if kind == "pointed" else w / 2 if kind == "round" else 0)
    top = pointed(u0, u1, spring) if kind == "pointed" else round_top(u0, u1, spring) if kind == "round" else [(u1, z0 + h), (u0, z0 + h)]
    poly_prism(P, glass, M, [(u0, z0), (u1, z0)] + top[1:-1] if kind != "rect" else [(u0, z0), (u1, z0)] + top, 0.0, 0.03)
    tf = pointed(u0 - frame, u1 + frame, spring) if kind == "pointed" else round_top(u0 - frame, u1 + frame, spring) if kind == "round" else [(u1 + frame, z0 + h + frame), (u0 - frame, z0 + h + frame)]
    outer = [(u0 - frame, z0), (u1 + frame, z0)] + (tf[1:-1] if kind != "rect" else tf)
    # frame band = outer outline minus the opening: built as strips along the outline
    ring_o = outer; ring_i = [(u0, z0), (u1, z0)] + (top[1:-1] if kind != "rect" else top)
    n = min(len(ring_o), len(ring_i))
    for i in range(1, n - 1):
        a, b = ring_o[i], ring_o[i + 1] if i + 1 < n else ring_o[0]
        c, d = ring_i[i + 1] if i + 1 < n else ring_i[0], ring_i[i]
        try:
            poly_prism(P, "cream", M, [a, b, c, d], 0.0, 0.08)
        except ValueError:
            pass
    if sill:
        poly_prism(P, "cream", M, [(u0 - frame - 0.08, z0 - 0.14), (u1 + frame + 0.08, z0 - 0.14), (u1 + frame + 0.08, z0), (u0 - frame - 0.08, z0)], 0.0, 0.16)


def cone_roof(P, x, y, z, r, h, segs=24, finial=True, mat="roof", flare=0.12):
    """Steep conical roof with a small flared eave, a cream ring under it and a gold finial."""
    lathe(P, mat, [(0.0, z - 0.05), (r + flare, z), (r * 0.9, z + h * 0.08), (r * 0.08, z + h), (0.0, z + h)], segs, T(x, y, 0))
    lathe(P, "cream", [(0.0, z - 0.3), (r + 0.06, z - 0.3), (r + 0.1, z - 0.15), (r + 0.06, z), (0.0, z)], segs, T(x, y, 0))
    if finial:
        lathe(P, "gold", [(0, z + h), (0.08, z + h), (0.05, z + h + 0.3), (0.1, z + h + 0.45), (0.02, z + h + 1.0), (0, z + h + 1.05)], 8, T(x, y, 0))


def round_tower(P, x, y, r, z1, roof_h, base=2.5, win_rows=((4.5, 1.6), ), n_win=5, a0=0.0, a1=2 * math.pi, corbel=True):
    """Round tower: darker base course, lilac shaft, corbelled ring, conical roof; windows round the visible arc."""
    lathe(P, "base", [(0, 0), (r + 0.25, 0), (r + 0.25, base), (r + 0.05, base + 0.2), (0, base + 0.2)], 32, T(x, y, 0))
    lathe(P, "lilac", [(0, base), (r, base), (r, z1), (0, z1)], 32, T(x, y, 0))
    lathe(P, "cream", [(0, base - 0.05), (r + 0.3, base - 0.05), (r + 0.3, base + 0.15), (0, base + 0.15)], 32, T(x, y, 0))
    if corbel:
        lathe(P, "cream", [(0, z1 - 1.0), (r + 0.05, z1 - 1.0), (r + 0.4, z1 - 0.3), (r + 0.4, z1 + 0.05), (0, z1 + 0.05)], 32, T(x, y, 0))
        for k in range(16):                                # corbel brackets under the ring
            t = 2 * math.pi * k / 16
            M = face(x + (r + 0.02) * math.cos(t), y + (r + 0.02) * math.sin(t), t + math.pi / 2)
            cube(P, "cream", M, -0.12, 0.12, 0.0, 0.3, z1 - 1.45, z1 - 1.0)
    for zz, hh in win_rows:
        for k in range(n_win):
            t = a0 + (a1 - a0) * (k + 0.5) / n_win
            M = face(x + r * math.cos(t), y + r * math.sin(t), t + math.pi / 2)
            window(P, M, 0.0, zz, 0.7, hh, "pointed", 0.12)
    cone_roof(P, x, y, z1 + 0.05, r + 0.35, roof_h)


def hip_roof(P, x0, x1, y0, y1, ze, ridge_h, mat="roof"):
    """Hip roof with the ridge along the longer side (plain faces; tiles come from the material)."""
    bm = P[mat]; lx, ly = x1 - x0, y1 - y0
    if lx >= ly:
        d = ly / 2; ra, rb = (x0 + d, (y0 + y1) / 2), (x1 - d, (y0 + y1) / 2)
    else:
        d = lx / 2; ra, rb = ((x0 + x1) / 2, y0 + d), ((x0 + x1) / 2, y1 - d)
    V = lambda x, y, z: bm.verts.new((x, y, z))
    a, b_, c, e = V(x0, y0, ze), V(x1, y0, ze), V(x1, y1, ze), V(x0, y1, ze)
    r0, r1 = V(ra[0], ra[1], ze + ridge_h), V(rb[0], rb[1], ze + ridge_h)
    if lx >= ly:
        for q in ((a, b_, r1, r0), (c, e, r0, r1), (e, a, r0), (b_, c, r1)):
            bm.faces.new(q)
    else:
        for q in ((b_, c, r1, r0), (e, a, r0, r1), (a, b_, r0), (c, e, r1)):
            bm.faces.new(q)
    cube(P, "cream", Matrix.Identity(4), x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, ze - 0.35, ze)   # cornice


def dormer(P, M, u, z0, w=1.4, h=2.2, roof=True):
    """Cream dormer on a roof slope / wall top: frame, arched window, small pediment and finial."""
    cube(P, "cream", M, u - w / 2 - 0.2, u + w / 2 + 0.2, -0.6, 0.15, z0 - 0.2, z0 + h)
    window(P, M @ Matrix.Translation((0, 0.16, 0)), u, z0 + 0.25, w * 0.55, h * 0.72, "round", 0.1, sill=False)
    poly_prism(P, "cream", M, [(u - w / 2 - 0.35, z0 + h), (u + w / 2 + 0.35, z0 + h), (u, z0 + h + 0.9)], -0.6, 0.2)
    if roof:
        lathe(P, "gold", [(0, 0), (0.06, 0), (0.04, 0.35), (0, 0.5)], 6, M @ T(u, 0.0, z0 + h + 0.9))
    for s in (-1, 1):                                       # little pinnacles either side
        lathe(P, "cream", [(0, 0), (0.12, 0), (0.1, 0.5), (0, 1.0)], 8, M @ T(u + s * (w / 2 + 0.3), 0.0, z0 + h))


def balustrade(P, M, u0, u1, z, h=0.9, step=0.28):
    cube(P, "cream", M, u0, u1, -0.15, 0.15, z, z + 0.12)
    cube(P, "cream", M, u0, u1, -0.18, 0.18, z + h - 0.12, z + h)
    k = u0 + step / 2
    while k < u1:
        lathe(P, "cream", [(0, 0), (0.07, 0), (0.1, 0.25), (0.05, 0.45), (0.07, 0.62), (0, h - 0.24)], 6, M @ T(k, 0, z + 0.12))
        k += step


def gargoyle(P, M, u, z, s=1.0):
    """Winged gargoyle on a plinth (the cursed angel statues): body, head, two swept wings."""
    cube(P, "cream", M, u - 0.35 * s, u + 0.35 * s, -0.35 * s, 0.35 * s, z, z + 0.3 * s)
    lathe(P, "statue", [(0, 0), (0.22 * s, 0), (0.25 * s, 0.35 * s), (0.18 * s, 0.7 * s), (0, 0.8 * s)], 8, M @ T(u, 0, z + 0.3 * s))
    lathe(P, "statue", [(0, 0), (0.14 * s, 0), (0.15 * s, 0.14 * s), (0, 0.28 * s)], 8, M @ T(u, 0.12 * s, z + 1.05 * s))
    for sg in (-1, 1):
        poly_prism(P, "statue", M, [(u + sg * 0.15 * s, z + 0.6 * s), (u + sg * 0.75 * s, z + 1.35 * s), (u + sg * 0.55 * s, z + 0.95 * s),
                                    (u + sg * 0.62 * s, z + 0.7 * s)][:: sg], -0.05 * s, 0.05 * s)


def lion(P, M, u, z, s=1.0):
    """Seated lion statue on a pedestal (the guardians at the gate and the grand stair)."""
    cube(P, "cream", M, u - 0.55 * s, u + 0.55 * s, -0.6 * s, 0.6 * s, z, z + 0.9 * s)
    cube(P, "cream", M, u - 0.62 * s, u + 0.62 * s, -0.68 * s, 0.68 * s, z + 0.9 * s, z + 1.0 * s)
    zz = z + 1.0 * s
    lathe(P, "statue", [(0, 0), (0.4 * s, 0), (0.42 * s, 0.4 * s), (0.3 * s, 0.9 * s), (0, 1.0 * s)], 10, M @ T(u, 0.1 * s, zz))
    lathe(P, "statue", [(0, 0), (0.33 * s, 0), (0.36 * s, 0.25 * s), (0.25 * s, 0.55 * s), (0, 0.6 * s)], 10, M @ T(u, -0.2 * s, zz + 0.85 * s))
    for sg in (-1, 1):                                     # fore legs
        cube(P, "statue", M, u + sg * 0.15 * s - 0.08 * s, u + sg * 0.15 * s + 0.08 * s, -0.4 * s, -0.25 * s, zz, zz + 0.7 * s)


def lamp_post(P, x, y, h=4.2):
    lathe(P, "iron", [(0, 0), (0.25, 0), (0.25, 0.35), (0.1, 0.55), (0.07, h - 0.6), (0.12, h - 0.5), (0, h - 0.45)], 10, T(x, y, 0))
    lathe(P, "lamp", [(0, h - 0.45), (0.18, h - 0.4), (0.22, h - 0.05), (0.08, h + 0.1), (0, h + 0.12)], 8, T(x, y, 0))
    lathe(P, "iron", [(0, h + 0.1), (0.25, h + 0.1), (0.06, h + 0.4), (0, h + 0.5)], 8, T(x, y, 0))


# ================================================================ the castle, front to back
def build_bridge(P):
    M = Matrix.Identity(4)
    cube(P, "paving", M, -2.3, 2.3, -26.0, -0.5, -0.6, 0.0)                      # deck
    for s in (-1, 1):
        cube(P, "lilac", M, s * 2.3 - 0.35, s * 2.3 + 0.35, -26.0, -0.5, -0.6, 0.95)   # parapets
        cube(P, "cream", M, s * 2.3 - 0.45, s * 2.3 + 0.45, -26.0, -0.5, 0.95, 1.12)
        for yy in (-24.5, -16.0, -7.5):                                         # piers with lamps on gargoyle plinths
            cube(P, "lilac", M, s * 2.3 - 0.55, s * 2.3 + 0.55, yy - 0.55, yy + 0.55, -0.6, 1.4)
            cube(P, "cream", M, s * 2.3 - 0.62, s * 2.3 + 0.62, yy - 0.62, yy + 0.62, 1.4, 1.55)
            lamp_post(P, s * 2.3, yy, 3.4)
    for s in (-1, 1):                                                          # tall twin-lantern posts at the gate
        x, y, h = s * 3.4, -2.2, 6.0
        lathe(P, "iron", [(0, 0), (0.3, 0), (0.3, 0.5), (0.12, 0.8), (0.09, h), (0, h + 0.1)], 10, T(x, y, 0))
        for sg in (-1, 1):
            cube(P, "iron", T(x, y, 0), min(0, sg * 0.9), max(0, sg * 0.9), -0.04, 0.04, h - 0.6, h - 0.52)
            lathe(P, "lamp", [(0, 0), (0.16, 0.05), (0.2, 0.45), (0.08, 0.6), (0, 0.62)], 8, T(x + sg * 0.9, y, h - 1.25))
            lathe(P, "iron", [(0, 0.6), (0.24, 0.6), (0.05, 0.85), (0, 0.9)], 8, T(x + sg * 0.9, y, h - 1.25))
    for k in range(3):                                                         # arches under the deck, over the chasm
        y0, y1 = -24.0 + k * 8.0, -17.0 + k * 8.0
        pts, _ = seg_arc((y0 + y1) / 2, -4.0, y1 - y0, 1.8, 14)
        poly_prism(P, "lilac", face(-2.3, 0, math.pi / 2) @ Matrix.Rotation(0, 4, "Z"), [(-(y1), -0.6), (-(y0), -0.6), (-y0, -4.0)] + [(-u, z) for u, z in pts[::-1]] + [(-y1, -4.0)], 0.0, 4.6)


def build_gatehouse(P):
    M = face(0, 0, 0)                                      # the front face (y = 0), outward = -y
    # body: x -6.5..6.5, y 0..6, to 9.5 m, a lower base course
    cube(P, "lilac", Matrix.Identity(4), -6.5, 6.5, 0.0, 6.0, 0.0, 9.5)
    cube(P, "base", Matrix.Identity(4), -6.7, 6.7, -0.2, 6.2, 0.0, 1.2)
    cube(P, "cream", Matrix.Identity(4), -6.8, 6.8, -0.3, 6.3, 9.2, 9.6)
    # the central pointed arch: frame, deep reveal (dark), the wooden door set back, voussoirs, lion-head relief
    arch = [(-1.8, 0.0), (1.8, 0.0)] + pointed(-1.8, 1.8, 3.4)[1:-1]
    poly_prism(P, "glass", M, arch, -0.02, 0.01)
    outer = [(-2.3, 0.0), (2.3, 0.0)] + pointed(-2.3, 2.3, 3.4)[1:-1]
    poly_prism(P, "cream", M, outer, 0.01, 0.35)
    poly_prism(P, "wood", M, [(-1.5, 0.0), (1.5, 0.0)] + pointed(-1.5, 1.5, 3.3)[1:-1], 0.36, 0.42)
    for zz in (0.8, 1.6, 2.4, 3.2):                        # iron straps and studs on the door
        cube(P, "iron", M, -1.4, 1.4, 0.42, 0.45, zz, zz + 0.07)
    lathe(P, "statue", [(0, 0), (0.55, 0), (0.6, 0.2), (0.45, 0.45), (0, 0.5)], 12, M @ T(0, 0.35, 6.1) @ R(-math.pi / 2, "X"))
    for s in (-1, 1):                                      # side niches with the lions
        u = s * 4.3
        poly_prism(P, "cream", M, [(u - 1.2, 0.0), (u + 1.2, 0.0)] + pointed(u - 1.2, u + 1.2, 2.6)[1:-1], 0.0, 0.3)
        poly_prism(P, "glass", M, [(u - 0.9, 0.3), (u + 0.9, 0.3)] + pointed(u - 0.9, u + 0.9, 2.5)[1:-1], 0.3, 0.31)
        lion(P, M @ Matrix.Translation((0, 0.9, 0)), u, 0.0, 1.0)
        window(P, M, u, 5.6, 0.8, 1.6, "pointed")
    # dormer in the middle above the arch, a pink hip roof behind it
    hip_roof(P, -6.5, 6.5, 0.0, 6.0, 9.5, 3.4)
    dormer(P, M @ Matrix.Translation((0, 0.3, 0)), 0.0, 9.6, 2.2, 2.9)
    # the two corner towers (square below, round top, steep cones)
    for s in (-1, 1):
        x = s * 6.8
        cube(P, "lilac", Matrix.Identity(4), x - 1.7, x + 1.7, -0.6, 2.8, 0.0, 11.0)
        cube(P, "cream", Matrix.Identity(4), x - 1.9, x + 1.9, -0.8, 3.0, 10.7, 11.2)
        for k in range(8):                                 # corbels under the cornice
            cube(P, "cream", Matrix.Identity(4), x - 1.6 + k * 0.45, x - 1.4 + k * 0.45, -0.8, -0.6, 10.2, 10.7)
        window(P, face(x, -0.6, 0), 0.0, 7.2, 0.8, 1.8, "pointed")
        cone_roof(P, x, 1.1, 11.2, 2.15, 6.2)


def build_wings(P):
    """Long low wings left and right of the gatehouse, stepping back; balustrade with gargoyles; the dome on the left."""
    for s in (-1, 1):
        segs = [(6.5, 22.0, 1.0), (22.0, 38.0, 3.0)]        # (x from, x to, y of the front face)
        for xa, xb, yf in segs:
            x0, x1 = sorted((s * xa, s * xb))
            cube(P, "lilac", Matrix.Identity(4), x0, x1, yf, yf + 6.0, 0.0, 7.4)
            cube(P, "base", Matrix.Identity(4), x0, x1, yf - 0.15, yf + 6.0, 0.0, 1.0)
            cube(P, "cream", Matrix.Identity(4), x0 - 0.1, x1 + 0.1, yf - 0.3, yf + 6.0, 7.1, 7.5)
            M = face(0, yf, 0)
            k = min(x0, x1) + 1.6
            while k < max(x0, x1) - 1.0:
                window(P, M, k, 4.2, 0.75, 1.5, "round", 0.1)                     # upper arched windows
                poly_prism(P, "cream", M, [(k - 0.7, 0.9), (k + 0.7, 0.9)] + round_top(k - 0.7, k + 0.7, 2.4)[1:-1], 0.0, 0.12)   # blind arches
                k += 2.6
            balustrade(P, M, x0, x1, 7.5, 0.9)
            u = x0 + 1.3
            while u < x1 - 0.8:                            # winged gargoyles along the parapet
                gargoyle(P, M @ Matrix.Translation((0, -0.1, 0)), u, 8.4, 0.9)
                u += 5.0
            cube(P, "roof", Matrix.Identity(4), x0, x1, yf + 0.5, yf + 6.0, 7.4, 7.6)
    # the dome pavilion behind the left wing: drum with arched windows, copper dome, lantern and a gargoyle on top
    dx, dy = -15.0, 10.5
    lathe(P, "lilac", [(0, 0), (4.0, 0), (4.0, 9.0), (0, 9.0)], 36, T(dx, dy, 0))
    lathe(P, "cream", [(0, 8.7), (4.3, 8.7), (4.4, 9.2), (3.9, 9.4), (0, 9.4)], 36, T(dx, dy, 0))
    for k in range(10):
        t = math.pi * 1.1 + k * 0.28
        window(P, face(dx + 4.0 * math.cos(t), dy + 4.0 * math.sin(t), t + math.pi / 2), 0.0, 7.2, 0.6, 1.2, "round", 0.08)
    lathe(P, "dome", [(0, 9.4)] + [(3.9 * math.cos(math.pi / 2 * k / 12), 9.4 + 3.4 * math.sin(math.pi / 2 * k / 12)) for k in range(13)], 36, T(dx, dy, 0))
    for k in range(12):                                     # ribs on the dome
        t = 2 * math.pi * k / 12
        bm = P["cream"]
        pts = [(3.95 * math.cos(math.pi / 2 * j / 10), 9.4 + 3.45 * math.sin(math.pi / 2 * j / 10)) for j in range(11)]
        for j in range(10):
            (ra, za), (rb, zb) = pts[j], pts[j + 1]
            c = Vector(((ra + rb) / 2 * math.cos(t) + dx, (ra + rb) / 2 * math.sin(t) + dy, (za + zb) / 2))
            L = math.hypot(rb - ra, zb - za)
            Mr = Matrix.Translation(c) @ Matrix.Rotation(t, 4, "Z") @ Matrix.Rotation(-math.atan2(zb - za, rb - ra) + math.pi / 2, 4, "Y")
            cube(P, "cream", Mr, -0.08, 0.08, -0.08, 0.08, -L / 2, L / 2)
    lathe(P, "cream", [(0, 12.8), (0.9, 12.8), (0.9, 14.0), (1.0, 14.1), (0, 14.3)], 16, T(dx, dy, 0))
    for k in range(8):
        t = 2 * math.pi * k / 8
        cube(P, "cream", T(dx + 0.8 * math.cos(t), dy + 0.8 * math.sin(t), 0), -0.08, 0.08, -0.08, 0.08, 12.8, 14.0)
    gargoyle(P, T(dx, dy, 0), 0.0, 14.3, 1.1)


def build_courtyard(P):
    I = Matrix.Identity(4)
    cube(P, "paving", I, -14.0, 14.0, 6.0, 21.0, -0.02, 0.0)
    lathe(P, "base", [(0, 0), (3.0, 0), (3.0, 0.012), (0, 0.012)], 48, T(-2.0, 12.5, 0))
    lathe(P, "paving", [(0, 0.012), (2.6, 0.012), (2.6, 0.02), (0, 0.02)], 48, T(-2.0, 12.5, 0))
    # arcade of round arches on columns along the left (x = -12), with a roof behind
    cube(P, "lilac", I, -14.0, -11.6, 6.0, 21.0, 0.0, 5.2)
    M = face(-11.6, 6.0, math.pi / 2)                       # face towards +x (inside the courtyard)
    for k in range(5):
        u = 1.5 + k * 2.9
        poly_prism(P, "glass", M, [(u - 1.2, 0.0), (u + 1.2, 0.0)] + round_top(u - 1.2, u + 1.2, 2.6)[1:-1], -0.02, 0.01)
        poly_prism(P, "cream", M, [(u - 1.45, 0.0), (u - 1.2, 0.0)] + [(u - 1.2, 2.6), (u - 1.45, 2.6)], 0.0, 0.4)
        for sg in (-1, 1):
            lathe(P, "cream", [(0, 0), (0.25, 0), (0.22, 0.3), (0.16, 0.4), (0.15, 2.4), (0.25, 2.6), (0, 2.65)], 12, M @ T(u + sg * 1.35, 0.35, 0))
        ring = pointed(u - 1.45, u + 1.45, 2.6)
        poly_prism(P, "cream", M, [(u - 1.45, 2.6)] + round_top(u - 1.45, u + 1.45, 2.6)[1:-1] + [(u + 1.45, 2.6), (u + 1.2, 2.6)]
                   + round_top(u - 1.2, u + 1.2, 2.6)[-2:0:-1] + [(u - 1.2, 2.6)], 0.0, 0.35)
    balustrade(P, M, 0.0, 15.0, 5.2, 0.8)
    for x, y in ((-8.5, 9.0), (5.5, 9.0), (-8.5, 18.0), (7.5, 17.0)):
        lamp_post(P, x, y, 4.0)
    # the right side of the courtyard: a plain wall with blind arches
    cube(P, "lilac", I, 12.0, 14.0, 6.0, 21.0, 0.0, 6.5)
    Mr = face(12.0, 21.0, -math.pi / 2)
    for k in range(4):
        poly_prism(P, "cream", Mr, [(1.5 + k * 3.5 - 1.1, 0.8), (1.5 + k * 3.5 + 1.1, 0.8)] + pointed(1.5 + k * 3.5 - 1.1, 1.5 + k * 3.5 + 1.1, 3.0)[1:-1], 0.0, 0.1)
    # the enchanted rose (the reference film) on a pedestal by the stair, under a glass bell
    lathe(P, "cream", [(0, 0), (0.45, 0), (0.45, 0.2), (0.2, 0.35), (0.16, 0.95), (0.4, 1.05), (0.4, 1.15), (0, 1.15)], 16, T(-2.0, 12.5, 0))
    lathe(P, "gold", [(0, 1.15), (0.34, 1.15), (0.34, 1.22), (0, 1.22)], 20, T(-2.0, 12.5, 0))
    lathe(P, "bell", [(0.3, 1.22), (0.3, 1.75)] + [(0.3 * math.cos(math.pi / 2 * k / 6), 1.75 + 0.3 * math.sin(math.pi / 2 * k / 6)) for k in range(1, 7)], 20, T(-2.0, 12.5, 0))
    lathe(P, "grass", [(0, 1.22), (0.012, 1.22), (0.01, 1.6), (0, 1.6)], 6, T(-2.0, 12.5, 0))
    lathe(P, "rose", [(0, 1.55), (0.07, 1.6), (0.09, 1.68), (0.05, 1.74), (0, 1.73)], 12, T(-2.0, 12.5, 0))


def build_palace(P):
    I = Matrix.Identity(4)
    # the grand stair up to the palace door (platform at 1.8 m), lions on its cheeks
    for k in range(10):
        cube(P, "base", I, -4.5 + k * 0.08, 4.5 - k * 0.08, 16.0 + k * 0.4, 21.0, 0.0, 0.18 * (k + 1))
    for s in (-1, 1):
        cube(P, "cream", I, s * 4.7 - 0.45, s * 4.7 + 0.45, 16.0, 21.0, 0.0, 1.0)
        lion(P, face(0, 16.3, 0), s * 4.7, 1.0, 1.05)
    # main body: x -12..12, y 21..34, to 15.5 m; darker base
    cube(P, "lilac", I, -12.0, 12.0, 21.0, 34.0, 0.0, 15.5)
    cube(P, "base", I, -12.2, 12.2, 20.8, 34.2, 0.0, 2.2)
    cube(P, "cream", I, -12.3, 12.3, 20.7, 34.3, 2.2, 2.45)
    M = face(0, 21.0, 0)
    poly_prism(P, "cream", M, [(-1.9, 1.8), (1.9, 1.8)] + pointed(-1.9, 1.9, 5.0)[1:-1], 0.0, 0.35)
    poly_prism(P, "wood", M, [(-1.4, 1.8), (1.4, 1.8)] + pointed(-1.4, 1.4, 4.9)[1:-1], 0.35, 0.42)
    poly_prism(P, "cream", M, [(-2.4, 7.0), (2.4, 7.0), (0, 8.4)], 0.0, 0.4)           # pediment over the door, a shield
    lathe(P, "gold", [(0, 0), (0.45, 0), (0.45, 0.08), (0, 0.1)], 6, M @ T(0, 0.42, 7.5) @ R(-math.pi / 2, "X"))
    for u in (-7.0, -4.5, 4.5, 7.0):
        window(P, M, u, 3.4, 0.9, 2.6, "pointed")
        window(P, M, u, 8.8, 0.9, 2.4, "pointed", glass="stained")
    for u in (-2.2, 2.2):
        window(P, M, u, 9.0, 0.8, 2.2, "pointed", glass="stained")
    balustrade(P, M @ Matrix.Translation((0, 0.6, 0)), -9.0, 9.0, 12.2, 0.9)          # balcony
    cube(P, "cream", M, -9.2, 9.2, 0.0, 0.8, 11.9, 12.2)
    window(P, M, 0.0, 12.6, 1.2, 2.4, "round")
    hip_roof(P, -12.3, 12.3, 20.7, 34.3, 15.5, 6.5)
    for u in (-8.0, -4.0, 4.0, 8.0):
        dormer(P, M @ Matrix.Translation((0, 0.9, 0)), u, 15.8, 1.3, 2.1)
    # the two big round towers at the front corners
    for s in (-1, 1):
        round_tower(P, s * 11.0, 22.5, 3.4, 15.0, 7.2, base=2.4, win_rows=((4.0, 2.4), (9.5, 2.4)), n_win=6,
                    a0=math.pi * (0.9 if s < 0 else -0.35), a1=math.pi * (1.65 if s < 0 else 0.1) + (0 if s < 0 else math.pi * 0.0))
    # side towers further back (smaller)
    for s in (-1, 1):
        round_tower(P, s * 12.8, 32.0, 2.3, 18.0, 5.6, base=2.2, win_rows=((6.0, 1.8), (12.0, 1.8)), n_win=4)
    # the upper stage: x -6.5..6.5, y 25..33, from the roof to 23 m, balconies and dormers, a steep roof
    cube(P, "lilac", I, -6.5, 6.5, 25.0, 33.0, 15.0, 23.0)
    cube(P, "cream", I, -6.7, 6.7, 24.8, 33.2, 22.7, 23.1)
    Mu = face(0, 25.0, 0)
    for u in (-4.0, 0.0, 4.0):
        window(P, Mu, u, 17.0, 0.9, 2.2, "pointed")
    balustrade(P, Mu @ Matrix.Translation((0, 0.5, 0)), -6.0, 6.0, 19.8, 0.8)
    cube(P, "cream", Mu, -6.2, 6.2, 0.0, 0.6, 19.5, 19.8)
    hip_roof(P, -6.7, 6.7, 24.8, 33.2, 23.0, 5.2)
    dormer(P, Mu @ Matrix.Translation((0, 1.2, 0)), 0.0, 23.2, 1.5, 2.4)
    for s in (-1, 1):                                        # pinnacles on the corners of the upper stage
        for yy in (25.0, 33.0):
            lathe(P, "cream", [(0, 0), (0.35, 0), (0.35, 1.2), (0.2, 1.4), (0.25, 2.0), (0.05, 3.2), (0, 3.3)], 8, T(s * 6.5, yy, 23.0))
            lathe(P, "gold", [(0, 0), (0.06, 0), (0.03, 0.5), (0, 0.55)], 6, T(s * 6.5, yy, 26.3))
    for x, y in ((-9.0, 30.0), (9.5, 28.0), (-3.0, 33.5)):   # chimneys
        cube(P, "lilac", I, x - 0.5, x + 0.5, y - 0.5, y + 0.5, 15.5, 22.5)
        cube(P, "cream", I, x - 0.65, x + 0.65, y - 0.65, y + 0.65, 22.5, 22.9)
    # the keep: square tower to 30 m with a machicolated crenellated top, and its slim round turret with a spire
    kx, ky = 1.5, 31.0
    cube(P, "lilac", I, kx - 2.3, kx + 2.3, ky - 2.3, ky + 2.3, 15.0, 28.3)
    for k in range(10):                                      # machicolation corbels on the front and back
        for yy, sg in ((ky - 2.3, -1), (ky + 2.3, 1)):
            cube(P, "cream", I, kx - 2.2 + k * 0.47, kx - 2.0 + k * 0.47, yy + sg * 0.0, yy + sg * 0.35, 27.6, 28.3) if sg > 0 else \
                cube(P, "cream", I, kx - 2.2 + k * 0.47, kx - 2.0 + k * 0.47, yy - 0.35, yy, 27.6, 28.3)
    cube(P, "cream", I, kx - 2.7, kx + 2.7, ky - 2.7, ky + 2.7, 28.3, 28.7)
    cube(P, "lilac", I, kx - 2.6, kx + 2.6, ky - 2.6, ky + 2.6, 28.7, 29.6)
    for i in range(6):                                       # merlons
        for yy in (ky - 2.6, ky + 2.2):
            cube(P, "lilac", I, kx - 2.6 + i * 0.95, kx - 2.1 + i * 0.95, yy, yy + 0.4, 29.6, 30.4)
        for xx in (kx - 2.6, kx + 2.2):
            cube(P, "lilac", I, xx, xx + 0.4, ky - 2.6 + i * 0.95, ky - 2.1 + i * 0.95, 29.6, 30.4)
    Mk = face(kx, ky - 2.3, 0)
    for zz in (17.5, 21.5, 25.0):
        window(P, Mk, 0.0, zz, 0.7, 1.7, "pointed")
    tx, ty = kx + 2.6, ky - 2.4                              # the turret on the keep's front-right corner
    lathe(P, "cream", [(0, 22.0), (0.6, 22.0), (1.2, 23.5), (0, 23.5)], 20, T(tx, ty, 0))
    lathe(P, "lilac", [(0, 23.5), (1.15, 23.5), (1.15, 30.5), (0, 30.5)], 20, T(tx, ty, 0))
    window(P, face(tx, ty - 1.15, 0), 0.0, 27.5, 0.5, 1.2, "pointed")
    cone_roof(P, tx, ty, 30.5, 1.4, 4.2)
    # a second slender round tower with a spire (left-back), and small spires round the roofs
    round_tower(P, -4.8, 33.5, 1.4, 25.5, 5.0, base=15.0, win_rows=((21.0, 1.4),), n_win=3, corbel=True)
    for x, y, z, r, h in ((-9.5, 24.0, 15.5, 0.8, 4.5), (9.0, 33.5, 15.5, 0.8, 4.5), (-12.0, 33.8, 15.5, 0.6, 3.5)):
        lathe(P, "lilac", [(0, z - 2.0), (r, z - 2.0), (r, z + 1.0), (0, z + 1.0)], 16, T(x, y, 0))
        cone_roof(P, x, y, z + 1.0, r + 0.2, h)
    # gold statues on the front gable and gargoyles on the palace roof corners
    for s in (-1, 1):
        gargoyle(P, face(0, 20.7, 0), s * 12.0, 15.6, 1.0)


def build_rocks(P):
    """Rock masses round the chasm under the bridge and at the castle's foot (noise-displaced blobs)."""
    # (x, y, radius, height): low jagged rocks either side of the bridge (below the deck near it, taller further out),
    # the tall crag with the waterfall on the right, rocks at the feet of the wings
    blobs = [(-7.5, -20.0, 3.5, 2.5), (-8.0, -12.0, 3.0, 1.5), (-9.5, -4.5, 3.2, 3.0), (-15.0, -15.0, 4.5, 4.0), (-14.0, -6.0, 3.5, 5.5),
             (7.5, -21.0, 3.2, 3.0), (8.0, -13.5, 2.8, 1.8), (13.5, -18.0, 4.0, 6.5), (14.0, -9.0, 4.2, 8.0), (10.0, -3.5, 3.0, 4.0),
             (-4.0, -16.0, 2.6, -1.2), (4.0, -10.0, 2.6, -1.2), (-24.0, -1.0, 3.5, 2.5), (25.0, 0.0, 3.5, 3.0)]
    for i, (x, y, r, h) in enumerate(blobs):
        bm = P["rock"]
        res = bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
        seed = Vector((i * 3.1, i * 1.7, i * 0.9))
        for v in res["verts"]:
            n = v.co.copy()
            d = 1.0 + 0.3 * noise.noise(n * 1.3 + seed) + 0.12 * noise.noise(n * 3.5 + seed) + 0.05 * noise.noise(n * 9.0 + seed)
            spike = 1.0 + 0.6 * max(0.0, noise.noise(Vector((n.x * 2.2, n.y * 2.2, 0)) + seed))   # jagged crests
            z = max(n.z, -0.25)
            v.co = Vector((x + n.x * r * d, y + n.y * r * d * 0.85, z * abs(h) * d * spike + (h if h < 0 else 0)))
    # the chasm floor and a mist-white cascade on the right (the waterfall at the bridge)
    cube(P, "rock", Matrix.Identity(4), -6.0, 6.0, -26.0, -1.0, -4.5, -4.0)
    cube(P, "water", Matrix.Identity(4), 6.2, 7.2, -13.0, -11.0, -4.0, 4.5)


def build(context=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    B.col = bpy.data.collections.new("BB_Castle"); sc.collection.children.link(B.col)
    B.cutters = bpy.data.collections.new("Cutters"); sc.collection.children.link(B.cutters)
    B.root = bpy.data.objects.new("BB_Castle", None); B.col.objects.link(B.root); B.hide = []
    B.M = materials()
    t0 = time.time()
    P = Parts()
    for name, fn in (("bridge", build_bridge), ("gatehouse", build_gatehouse), ("wings", build_wings),
                     ("courtyard", build_courtyard), ("palace", build_palace), ("rocks", build_rocks)):
        fn(P); P.flush(name)
    if context:
        ctx = bpy.data.collections.new("Context"); sc.collection.children.link(ctx)
        old = B.col; B.col = ctx
        box("CTX_ground", (-80, 80, -60, 90, -0.3, -0.02), "ground_ctx")
        B.col = old
    print(f"[bb] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")


CAMS = {
    "bridge": ((0.0, -38.0, 1.7), (0.0, 10.0, 12.0), 24),         # the photos from the queue
    "front": ((-14.0, -48.0, 8.0), (0.0, 10.0, 12.0), 28),
    "courtyard": ((3.0, 7.0, 1.7), (-1.0, 22.0, 9.0), 16),
    "keep": ((22.0, 10.0, 3.0), (2.0, 30.0, 22.0), 24),
    "aerial": ((55.0, -50.0, 55.0), (0.0, 15.0, 8.0), 30),
    "rose": ((-0.8, 11.3, 1.7), (-2.0, 12.5, 1.5), 50),
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default=",".join(CAMS))
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=60)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    build()
    ST.world_sky()
    cams = {}
    for n, (loc, tgt, lens) in CAMS.items():
        cam = bpy.data.cameras.new("CAM_" + n); cam.lens = lens; cam.clip_start = 0.05; cam.clip_end = 3000
        co = bpy.data.objects.new("CAM_" + n, cam); B.col.objects.link(co)
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cams[n] = co
    bpy.context.scene.camera = cams["bridge"]
    ST.frame_view()
    for scr in bpy.data.screens:
        for area in scr.areas:
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.region_3d.view_location = (0.0, 12.0, 10.0); sp.region_3d.view_distance = 85.0
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "bb_castle.blend").resolve()))
    print("[bb] saved", OUT / "bb_castle.blend")
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        old = ST.OUT; ST.OUT = OUT
        try:
            ST.render(cams, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES", "bb")
        finally:
            ST.OUT = old


if __name__ == "__main__" and bpy is not None:
    main()
