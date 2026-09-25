"""シンデレラ城 (Tokyo Disneyland, opened 1983) -- Blender 5.2.

  python -c "import ds_tdl_cinderella as c; c.make_textures()"   # paint the textures once (plain Python + PIL)
  blender -b --python ds_tdl_cinderella.py -- --samples 32         # renders + output/disneyland/cinderella/cinderella.blend
  blender -b --python export_models.py -- --parts cinderella        # the mock's model

Sources (looked at only; nothing copied into the repository):
  * The WED Enterprises "SOUTH ELEVATION" drawing for Oriental Land Co. (found through a web image search): the
    proportions of the whole front. Scaled with the published / OSM height 51 m (spire tip), 1 px = 2.9 cm.
  * About 250 web photos (Bing image search, deduplicated): front, rear courtyard side with the big gothic arch and
    the outside stair to Cinderella's Fairy Tale Hall, the moat, close-ups of the tracery windows, machicolations,
    the clock gable and the slate cones.
  * The Sketchfab model by blnae_ the user pointed to (not downloadable; its thumbnail and the user's screenshot only):
    the forecourt stage with its balustrade and banner poles in front of the gate, the moat round the base.
  * OSM way 217727348 (building, height 51): the footprint about 36 x 37 m with round tower lobes, the gate notch on
    the south side at (-388.6, 578.2).

  * THE REFERENCE (the user, 2026-09-25: "this image is correct"): the preview renders of the free3d model
    "Cinderella Castle" by 3d_molier International (https://free3d.com/ja/3d-model/cinderella-castle-6339.html,
    31 previews; paid model, not downloaded, previews looked at only). Taken from it: the colours (light grey
    stone base, pale pink upper castle, bright blue slate, gold spires and finials), the crown of tall gothic gables
    with pinnacles round the palace, the rounded corbel turrets along the top of the stone base, the red arched doors
    and quatrefoil window at the back, the rear bridge with its pierced balustrade and gold lamps, the front stage
    (retaining wall with pilasters and dark double doors, gold arches, tall gold banner poles with blue and gold
    pennants), the island edged with rocks and grass in the moat.

  * TURNTABLE (the user, 2026-09-25): TurboSquid 1439041 "Disneyland Cinderella Castle", the same 3d_molier model,
    two 72-frame 360-degree turntables and 39 stills (looked at only). They fixed the layout: the forecourt on its own
    island in front joined to the gate by a short arch bridge, its lower plaza D-shaped round the compass; the castle
    on a round grass island; a T-shaped rear terrace; the castle slimmer in plan than first built (PLAN_S) with
    stepped crenellated pink tiers instead of one long roof. Checked with cameras matching the turntable frames
    (turntable, ref_front, ref_rear, ref_side).

Frame: local metres, origin = the middle of the gate at the ground on the south front; +X east, +Y north (through
the castle). No rotation from the DisneySea frame. Ground 0 (DEM added on export).

Read off the drawing (metres): stone base 11.5; gate 4.3 wide, arch top 9.2; cream frontispiece 13.2; clock at 15.2
in the clock gable (top 20.9); upper palace walls 25.8, its gable 32.9; keep: shaft to 27.2 (gallery), upper stage
to 39.8, gold spire to 51; front round towers: cone tops 18.9 .. 24.4; slim turrets: 37.5 (left, gold spire),
42.7 (behind the gable), 41.3 (right).
ESTIMATES: everything the drawing does not show -- the depth of each part (from the footprint and the rear photos),
the rear towers and stair, the forecourt, the moat, window counts.
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
import ds_tdl_bb_castle as BC
from ds_tdl_station import B, bm_box, bm_lathe, bm_prism, obj_bm, T, R, seg_arc, _principled, _mottle, _bump
from ds_tdl_bb_castle import (Parts, cube, lathe, poly_prism, face, pointed, round_top, window, cone_roof, balustrade,
                              cresting, bartizan, arch_ring)

OUT = ROOT / "output" / "disneyland" / "cinderella"
ALL_S = 1.0        # plan scale of everything (checked against the turntable: 1.0)
STAGE_Z = 4.4      # gate floor = bridge = forecourt stage (turntable side frame: about 6.5 m above the water)
LOWER_Z = 0.8      # the forecourt's lower plaza (about 3.5 m above the water)
TEX_DIR = ROOT / "plateau_data" / "cc_castle"
TEX_M = 4.0
GATE = (-388.6, 578.2)
WEB = False


# ================================================================ textures and materials
def make_textures():
    """Rough grey-brown ashlar (the base and towers), smooth cream ashlar (the upper palace), blue slate scales."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    g = random.Random(9); N = 1024; px = N / TEX_M

    def ashlar(fn, course, lengths, palette, joint, rough, seed):
        im = Image.new("RGB", (N, N), joint); d = ImageDraw.Draw(im); y = 0.0
        while y < TEX_M - 1e-6:
            x = -g.uniform(0, lengths[1])
            while x < TEX_M:
                L = g.uniform(*lengths); c = palette[g.randrange(len(palette))]; k = g.uniform(0.9, 1.08)
                col = tuple(max(0, min(255, int(v * k))) for v in c)
                x0, x1, y0, y1 = x * px, (x + L) * px, y * px, (y + course) * px
                d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=col)
                if x1 > N:
                    d.rectangle([x0 - N + 2, y0 + 2, x1 - N - 2, y1 - 2], fill=col)
                x += L
            y += course
        a = np.asarray(im).astype(np.float32); rng = np.random.default_rng(seed)
        a = (a + rng.normal(0, rough, (N, N, 1))).clip(0, 255).astype(np.uint8)
        Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.6)).save(TEX_DIR / fn, quality=90)

    ashlar("stone.jpg", 0.5, (0.6, 1.3), [(206, 208, 212), (198, 200, 206), (214, 216, 220), (190, 192, 198), (220, 220, 224),
                                         (202, 204, 208), (186, 188, 194)], (226, 226, 230), 4.0, 3)
    ashlar("cream.jpg", 0.45, (0.9, 1.6), [(238, 204, 210), (232, 196, 204), (242, 212, 218), (228, 192, 200)], (222, 190, 198), 3.0, 4)
    im = Image.new("RGB", (N, N), (30, 44, 74)); d = ImageDraw.Draw(im)
    tw, th = 0.22 * px, 0.17 * px
    for r in range(int(N / th) + 2):
        off = (r % 2) * tw / 2
        for c in range(int(N / tw) + 2):
            x0 = c * tw - off; y0 = r * th
            base = [(46, 104, 170), (40, 94, 160), (54, 114, 180), (36, 86, 150), (62, 122, 186)][g.randrange(5)]
            d.rounded_rectangle([x0 + 1, y0 + 1, x0 + tw - 1, y0 + th * 1.35], radius=tw * 0.45, fill=base)
    im.save(TEX_DIR / "slate.jpg", quality=90)


def image_material(name, fn, rough=0.8, bump=0.3, tint=(0.6, 0.6, 0.6)):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree; b = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(str(TEX_DIR / fn), check_existing=True)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(tex.outputs["Color"], bw.inputs[0]); _bump(nt, b, bw.outputs[0], bump, 0.01)
    mat.diffuse_color = (*tint, 1)
    return mat


def materials():
    M = ST.materials()
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    if not (TEX_DIR / "stone.jpg").exists():
        make_textures()
    M["stone"] = image_material("cc_stone", "stone.jpg", 0.85, 0.5, (0.74, 0.75, 0.78))    # light grey (reference)
    M["cream"] = image_material("cc_cream", "cream.jpg", 0.55, 0.15, (0.88, 0.74, 0.77))    # pale pink upper castle
    M["lilac"] = M["cream"]                                 # (the shared helpers call the wall material "lilac")
    M["roof"] = image_material("cc_slate", "slate.jpg", 0.4, 0.4, (0.14, 0.36, 0.66))
    mat, nt, b = _principled("cc_trim", (0.93, 0.88, 0.78), 0.5); _mottle(nt, b, (0.93, 0.88, 0.78), 6, 0.93, 0.03); M["trim"] = mat
    M["gold"] = P("cc_gold", (1.0, 0.76, 0.28), 0.18, Metallic=1.0)
    M["glass"] = P("cc_glass", (0.10, 0.16, 0.30), 0.06, Coat_Weight=1.0)
    M["stained"] = P("cc_stained", (0.20, 0.30, 0.55), 0.08, Emission_Color=(0.4, 0.6, 1.0, 1), Emission_Strength=0.12)
    M["iron"] = P("cc_iron", (0.05, 0.05, 0.06), 0.4, Metallic=0.7)
    M["wood"] = P("cc_wood", (0.28, 0.15, 0.08), 0.7)
    M["clock"] = P("cc_clock", (0.62, 0.78, 0.86), 0.35)
    M["water"] = P("cc_water", (0.16, 0.42, 0.62), 0.05, Coat_Weight=1.0, Alpha=0.55)   # clear: the hanging rocks show through
    M["banner_a"] = P("cc_banner_a", (0.30, 0.20, 0.60), 0.8); M["banner_b"] = P("cc_banner_b", (0.85, 0.65, 0.15), 0.8)
    M["paving"] = ST.mat_tiles("cc_paving", (0.66, 0.56, 0.50), (0.60, 0.50, 0.46), 0.6, (0.48, 0.42, 0.38))
    M["red"] = P("cc_red", (0.62, 0.08, 0.10), 0.6)
    M["statue"] = P("cc_statue", (0.85, 0.82, 0.76), 0.6)
    M["door_red"] = P("cc_door_red", (0.45, 0.06, 0.08), 0.6)
    M["door_dark"] = P("cc_door_dark", (0.16, 0.20, 0.22), 0.5, Metallic=0.4)
    M["banner_a"] = P("cc_banner_a", (0.07, 0.12, 0.55), 0.7)                # royal blue (reference)
    mat, nt, b = _principled("cc_rock", (0.46, 0.44, 0.40), 0.9); _mottle(nt, b, (0.46, 0.44, 0.40), 1.4, 0.6, 0.5); M["rock"] = mat
    M["grass"] = P("cc_grass", (0.18, 0.32, 0.12), 0.9)
    return M


# ================================================================ parts
CONE_K = 1.4          # the reference's cones are about three times as tall as they are wide


def round_tower(P, x, y, r, top, cone_h, base_mat="stone", machi=True, windows=3, a0=-math.pi * 0.9, a1=-math.pi * 0.1, finial=True,
                z0=0.0, cone_r=None):
    """Stone drum from z0 to top: batter at the foot, arrow slits, a cream corbelled machicolation with small square
    openings, a crenellated parapet ring, then the blue cone with a cream skirt and a gold finial."""
    lathe(P, base_mat, [(0, z0), (r + 0.25, z0), (r, z0 + 1.2), (r, top - 1.6), (0, top - 1.6)], 28, T(x, y, 0))
    if machi:
        lathe(P, "trim", [(0, top - 1.8), (r + 0.02, top - 1.8), (r + 0.35, top - 1.1), (r + 0.35, top), (0, top)], 28, T(x, y, 0))
        for k in range(14):                                 # corbels
            t = 2 * math.pi * k / 14
            cube(P, "trim", face(x + r * math.cos(t), y + r * math.sin(t), t + math.pi / 2), -0.12, 0.12, 0.0, 0.3, top - 2.3, top - 1.8)
        for k in range(8):                                  # small square openings in the machicolation band
            t = 2 * math.pi * (k + 0.5) / 8
            if a0 <= t - 2 * math.pi <= a1 or a0 <= t <= a1 or True:
                cube(P, "glass", face(x + (r + 0.36) * math.cos(t), y + (r + 0.36) * math.sin(t), t + math.pi / 2), -0.18, 0.18, 0.0, 0.03, top - 0.9, top - 0.45)
    if machi and top - z0 > 10:                             # the lower machicolation ring (two rings in the photos)
        zm = z0 + (top - z0) * 0.66
        lathe(P, "trim", [(0, zm - 0.6), (r + 0.02, zm - 0.6), (r + 0.3, zm - 0.1), (r + 0.3, zm + 0.3), (0, zm + 0.3)], 28, T(x, y, 0))
        for k in range(8):
            t = 2 * math.pi * (k + 0.5) / 8
            cube(P, "glass", face(x + (r + 0.31) * math.cos(t), y + (r + 0.31) * math.sin(t), t + math.pi / 2), -0.15, 0.15, 0.0, 0.03, zm - 0.05, zm + 0.22)
    for k in range(windows):                                # arrow slits / small pointed windows on the visible side
        t = a0 + (a1 - a0) * (k + 0.5) / windows
        M = face(x + r * math.cos(t), y + r * math.sin(t), t + math.pi / 2)
        window(P, M, 0.0, z0 + (top - z0) * 0.45, 0.35, 1.0, "rect", 0.08, sill=False)
    cone_roof(P, x, y, top, cone_r or (r + 0.3), cone_h * CONE_K, 28, finial=finial)


def gothic_window(P, M, u, z0, w, h, glass="stained"):
    """Tall pointed tracery window (the palace's): frame, two lights with a mullion, a quatrefoil in the head,
    a crocketed gable (wimperg) over it with a finial, pinnacles either side."""
    window(P, M, u, z0, w, h, "pointed", 0.14, glass=glass)
    spring = z0 + h - w * 0.8
    lathe(P, "trim", [(0, 0), (w * 0.18, 0), (w * 0.18, 0.05), (0, 0.06)], 4, M @ T(u, 0.08, spring + w * 0.15) @ R(-math.pi / 2, "X"))
    top = z0 + h
    poly_prism(P, "trim", M, [(u - w / 2 - 0.25, top - 0.2), (u + w / 2 + 0.25, top - 0.2), (u, top + w * 1.1)], 0.02, 0.2)
    lathe(P, "gold", [(0, 0), (0.05, 0), (0.03, 0.3), (0.06, 0.36), (0, 0.6)], 6, M @ T(u, 0.1, top + w * 1.1))
    for sg in (-1, 1):
        x_ = u + sg * (w / 2 + 0.35)
        cube(P, "trim", M, x_ - 0.1, x_ + 0.1, 0.0, 0.25, z0 - 0.2, top + 0.2)
        lathe(P, "trim", [(0, 0), (0.12, 0), (0.08, 0.5), (0, 0.9)], 4, M @ T(x_, 0.12, top + 0.2) @ R(math.pi / 4, "Z"))


def crenels(P, x0, x1, y0, y1, z, mat="cream", h=0.8, step=0.9):
    """A crenellated parapet round a rectangle (walk-way wall + merlons)."""
    I = Matrix.Identity(4)
    for a, b, c, d in ((x0, x1, y0, y0 + 0.3), (x0, x1, y1 - 0.3, y1), (x0, x0 + 0.3, y0, y1), (x1 - 0.3, x1, y0, y1)):
        cube(P, mat, I, a, b, c, d, z, z + h * 0.45)
    for (a, b, c, d) in ((x0, x1, y0, y0 + 0.3), (x0, x1, y1 - 0.3, y1)):
        k = a
        while k < b - 0.3:
            cube(P, mat, I, k, min(b, k + step * 0.55), c, d, z + h * 0.45, z + h); k += step
    for (a, b, c, d) in ((x0, x0 + 0.3, y0, y1), (x1 - 0.3, x1, y0, y1)):
        k = c
        while k < d - 0.3:
            cube(P, mat, I, a, b, k, min(d, k + step * 0.55), z + h * 0.45, z + h); k += step


def pinnacle(P, x, y, z, h=2.0, r=0.18, mat="trim"):
    lathe(P, mat, [(0, 0), (r, 0), (r, h * 0.35), (r * 0.7, h * 0.42), (r * 0.8, h * 0.5), (0.02, h), (0, h)], 6, T(x, y, z))
    lathe(P, "gold", [(0, 0), (0.03, 0), (0.02, 0.3), (0, 0.35)], 5, T(x, y, z + h))


def gable_roof(P, x0, x1, y0, y1, ze, ridge, mat="roof", along="y", thick=0.2, ends=(True, True)):
    """Steep gable roof (ridge along y or x) with triangular cream end walls."""
    bm = P[mat]
    if along == "y":
        xm = (x0 + x1) / 2
        v = [bm.verts.new(p) for p in ((x0, y0, ze), (xm, y0, ridge), (xm, y1, ridge), (x0, y1, ze), (x1, y0, ze), (x1, y1, ze))]
        bm.faces.new((v[0], v[3], v[2], v[1])); bm.faces.new((v[4], v[1], v[2], v[5]))
        for (yy, s), e in zip(((y0, 1), (y1, -1)), ends):
            if not e:
                continue
            poly_prism(P, "cream", face(0, yy, 0), [(x0 + 0.15, ze), (x1 - 0.15, ze), (xm, ridge - 0.15)], min(0, s * 0.3), max(0, s * 0.3))
    else:
        ym = (y0 + y1) / 2
        v = [bm.verts.new(p) for p in ((x0, y0, ze), (x1, y0, ze), (x1, ym, ridge), (x0, ym, ridge), (x0, y1, ze), (x1, y1, ze))]
        bm.faces.new((v[0], v[1], v[2], v[3])); bm.faces.new((v[5], v[4], v[3], v[2]))


def crown(P, M, L, z0, bay=2.5, h=5.4, gable=3.2, glass="stained"):
    """The crown of tall gothic gables (reference): along a face of length L, one tall tracery window per bay under a
    steep crocketed gable, a slim pinnacle between the bays rising above the gables."""
    n = max(1, int(L / bay)); b = L / n
    for k in range(n):
        u = (k + 0.5) * b
        BC.window(P, M, u, z0 + 0.6, b * 0.5, h, "pointed", 0.12, glass=glass)
        cube(P, "trim", M, u - 0.03, u + 0.03, 0.0, 0.08, z0 + 0.6, z0 + h - b * 0.3)        # mullion
        top = z0 + h + 0.4
        poly_prism(P, "trim", M, [(u - b / 2 + 0.05, top - 0.3), (u + b / 2 - 0.05, top - 0.3), (u, top + gable)], -0.1, 0.25)
        poly_prism(P, "cream", M, [(u - b / 2 + 0.35, top - 0.1), (u + b / 2 - 0.35, top - 0.1), (u, top + gable - 0.5)], 0.25, 0.3)
        lathe(P, "trim", [(0.5, 0), (0.62, 0), (0.62, 0.08), (0.5, 0.08)], 12, M @ T(u, 0.3, top + gable * 0.35) @ R(-math.pi / 2, "X"))
        q0 = M @ Vector((u, -1.6, 0))                                            # the blue pyramid roof behind the gable
        lathe(P, "roof", [(0, top - 0.3), (b * 0.62, top - 0.3), (0.05, top + gable + 1.6), (0, top + gable + 1.6)], 4,
              T(q0.x, q0.y, 0) @ R(math.pi / 4, "Z"))
        lathe(P, "gold", [(0, top + gable + 1.6), (0.07, top + gable + 1.6), (0.04, top + gable + 2.3), (0, top + gable + 2.4)], 6, T(q0.x, q0.y, 0))
        pinnacle(P, *(M @ Vector((u, 0.1, top + gable))).xy, top + gable, 0.9, 0.08, "gold")
        for j in range(4):                                                      # crockets up both edges
            t = (j + 0.5) / 4
            for sg in (-1, 1):
                q = M @ Vector((u + sg * (b / 2 - 0.1) * (1 - t), 0.2, top - 0.3 + (gable + 0.3) * t))
                lathe(P, "trim", [(0, 0), (0.07, 0), (0, 0.18)], 4, T(q.x, q.y, q.z))
    for k in range(n + 1):
        q = M @ Vector((k * b, 0.15, 0.0))
        cube(P, "trim", Matrix.Translation((q.x, q.y, 0)), -0.14, 0.14, -0.14, 0.14, z0, z0 + h + 1.0)
        pinnacle(P, q.x, q.y, z0 + h + 1.0, gable + 1.4, 0.16)


def corbel_turret(P, x, y, z, r=0.85, h=1.6):
    """Rounded corbel turret on the wall top (reference): a ribbed cone of corbels, a short drum, a moulded cap."""
    prof = [(0.0, z - 1.9), (0.12, z - 1.9)]
    for k in range(1, 7):
        t = k / 6
        prof.append((0.12 + (r - 0.12) * math.sin(t * math.pi / 2), z - 1.9 + 1.9 * t))
    prof += [(r, z + h), (r + 0.12, z + h), (r + 0.12, z + h + 0.25), (0.0, z + h + 0.25)]
    lathe(P, "trim", prof, 20, T(x, y, 0))
    for k in range(10):                                                         # the ribs of the corbel cone
        t = 2 * math.pi * k / 10
        cube(P, "trim", T(x + (r * 0.6) * math.cos(t), y + (r * 0.6) * math.sin(t), 0), -0.05, 0.05, -0.05, 0.05, z - 1.2, z)


def pierced_balustrade(P, M, u0, u1, z, h=1.0, step=0.9):
    """The castle's balustrade (reference): a solid plinth, a row of round openings (rings), a moulded rail."""
    cube(P, "trim", M, u0, u1, -0.15, 0.15, z, z + 0.2)
    cube(P, "trim", M, u0, u1, -0.2, 0.2, z + h - 0.15, z + h)
    k = u0 + step / 2
    while k < u1 - 0.2:
        import train_blender as TBL
        TBL._torus(P["trim"], (h - 0.4) / 2, 0.05, M @ T(k, 0.0, z + 0.2 + (h - 0.35) / 2) @ R(math.pi / 2, "X"), 12, 4)
        k += step
    for k in range(int((u1 - u0) / step) + 1):
        cube(P, "trim", M, u0 + k * step - 0.06, u0 + k * step + 0.06, -0.12, 0.12, z + 0.2, z + h - 0.15)


def gold_lamp(P, x, y, z, s=1.0):
    """Gold urn lamp on a pedestal (reference): pedestal, scrolled stem, a lantern with a crown top."""
    lathe(P, "trim", [(0, z), (0.35 * s, z), (0.35 * s, z + 0.9 * s), (0.25 * s, z + 1.0 * s), (0, z + 1.0 * s)], 8, T(x, y, 0))
    zz = z + 1.0 * s
    lathe(P, "gold", [(0, zz), (0.2 * s, zz), (0.08 * s, zz + 0.4 * s), (0.25 * s, zz + 0.7 * s), (0.28 * s, zz + 1.1 * s),
                      (0.1 * s, zz + 1.3 * s), (0.18 * s, zz + 1.45 * s), (0, zz + 1.6 * s)], 8, T(x, y, 0))


def pennant_pole(P, x, y, z, h=9.0, facing=0.0, mat="banner_a"):
    """Tall gold pole with a ball finial, a cross arm and a blue pennant with a gold border (reference)."""
    lathe(P, "gold", [(0, z), (0.14, z), (0.1, z + 0.4), (0.07, z + h), (0.2, z + h + 0.1), (0.2, z + h + 0.35), (0, z + h + 0.45)], 10, T(x, y, 0))
    M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(facing, 4, "Z")
    cube(P, "gold", M, -1.1, 1.1, -0.04, 0.04, z + h - 0.7, z + h - 0.6)
    pts = [(-1.0, z + h - 0.7), (1.0, z + h - 0.7), (0.0, z + h - 4.6)]
    poly_prism(P, "gold", M, pts, -0.03, 0.03)
    poly_prism(P, mat, M, [(-0.82, z + h - 0.8), (0.82, z + h - 0.8), (0.0, z + h - 4.2)], -0.05, 0.05)


def gold_hip(P, x0, x1, y0, y1, ze, rh):
    """Gold ridge and hip beams on a hip roof, gold crosses at the ridge ends (reference: every blue roof)."""
    lx, ly = x1 - x0, y1 - y0
    if lx >= ly:
        d = ly / 2; ra, rb = Vector((x0 + d, (y0 + y1) / 2, ze + rh)), Vector((x1 - d, (y0 + y1) / 2, ze + rh))
    else:
        d = lx / 2; ra, rb = Vector(((x0 + x1) / 2, y0 + d, ze + rh)), Vector(((x0 + x1) / 2, y1 - d, ze + rh))
    corners = [Vector((x0, y0, ze)), Vector((x1, y0, ze)), Vector((x1, y1, ze)), Vector((x0, y1, ze))]
    segs = [(ra, rb)]
    for c in corners:
        r_ = ra if (c - ra).length < (c - rb).length else rb
        segs.append((c, r_))
    for a, b in segs:
        dv = b - a; L = dv.length
        if L < 1e-3:
            continue
        M = Matrix.Translation((a + b) / 2) @ dv.to_track_quat("Z", "Y").to_matrix().to_4x4()
        cube(P, "gold", M, -0.07, 0.07, -0.07, 0.07, -L / 2, L / 2)
    for r_ in (ra, rb):
        gold_cross(P, r_.x, r_.y, r_.z)


def gold_cross(P, x, y, z, s=1.0):
    """Gold finial cross with ball ends (the reference's roof crosses)."""
    cube(P, "gold", T(x, y, z), -0.06 * s, 0.06 * s, -0.06 * s, 0.06 * s, 0.0, 1.4 * s)
    cube(P, "gold", T(x, y, z), -0.45 * s, 0.45 * s, -0.05 * s, 0.05 * s, 0.9 * s, 1.0 * s)
    for (dx, dz) in ((-0.45, 0.95), (0.45, 0.95), (0.0, 1.45)):
        lathe(P, "gold", [(0, -0.1 * s), (0.1 * s, 0), (0, 0.1 * s)], 6, T(x + dx * s, y, z + dz * s))


def flag(P, x, y, z, mat="red", h=2.2, w=1.6):
    """A thin pole on a spire tip and a swallow-tailed pennant (reference)."""
    lathe(P, "gold", [(0, z), (0.03, z), (0.02, z + h), (0.06, z + h + 0.05), (0, z + h + 0.12)], 6, T(x, y, 0))
    poly_prism(P, mat, Matrix.Translation((x, y, 0)), [(0.02, z + h - 0.1), (w, z + h - 0.3), (w * 0.8, z + h - 0.5), (w, z + h - 0.7), (0.02, z + h - 0.6)], -0.01, 0.01)


def gothic_arch_frame(P, cx, cy, z, w, h, ang=0.0, n_crockets=8):
    """Free-standing white gothic arch (reference stage): two slim clustered columns, a pointed arch band with gold
    crockets along it, a gold finial on the apex and pinnacles on the column tops."""
    M = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(ang, 4, "Z")
    for sg in (-1, 1):
        u = sg * w / 2
        lathe(P, "trim", [(0, z), (0.3, z), (0.3, z + 0.5), (0.16, z + 0.7), (0.14, z + h), (0.24, z + h + 0.2), (0, z + h + 0.25)], 12, M @ T(u, 0, 0))
        pinnacle(P, *(M @ Vector((u, 0, 0))).xy, z + h + 0.25, 1.4, 0.14)
    band = pointed(-w / 2 - 0.15, w / 2 + 0.15, z + h) + pointed(-w / 2 + 0.12, w / 2 - 0.12, z + h)[::-1]
    poly_prism(P, "trim", M @ Matrix.Rotation(0, 4, "Z"), band, -0.15, 0.15)
    arc = pointed(-w / 2 - 0.15, w / 2 + 0.15, z + h)
    for k in range(1, n_crockets):
        u, zz = arc[int(k * (len(arc) - 1) / n_crockets)]
        q = M @ Vector((u, 0, zz))
        lathe(P, "gold", [(0, 0), (0.1, 0.05), (0.02, 0.3), (0, 0.32)], 5, T(q.x, q.y, q.z))
    apex = max(zz for _, zz in arc)
    q = M @ Vector((0, 0, apex))
    lathe(P, "gold", [(0, 0), (0.12, 0), (0.08, 0.4), (0.16, 0.55), (0.03, 1.4), (0, 1.45)], 8, T(q.x, q.y, q.z))


def gold_railing(P, pts, z_of, h=1.0):
    """Gold railing along a polyline (reference stairs): top rail, bottom rail, bars with a scroll every 0.25 m."""
    for (a, b), (za, zb) in zip(zip(pts[:-1], pts[1:]), zip(z_of[:-1], z_of[1:])):
        A, Bv = Vector((a[0], a[1], za)), Vector((b[0], b[1], zb))
        for dz in (0.1, h):
            dv = (Bv - A); L = dv.length
            M = Matrix.Translation((A + Bv) / 2 + Vector((0, 0, dz))) @ dv.to_track_quat("Z", "Y").to_matrix().to_4x4()
            cube(P, "gold", M, -0.03, 0.03, -0.03, 0.03, -L / 2, L / 2)
        n = max(1, int(dv.length / 0.25))
        for k in range(n):
            q = A + dv * (k / n)
            cube(P, "gold", T(q.x, q.y, q.z), -0.015, 0.015, -0.015, 0.015, 0.1, h)
            if k % 2 == 0:
                BC.cube(P, "gold", T(q.x, q.y, q.z + h * 0.55), -0.08, 0.08, -0.01, 0.01, -0.08, 0.08)


# ================================================================ the castle, bottom to top
def build_base(P):
    """The stone lower castle: two masses either side of the through passage, the passage vault, the rear arch."""
    I = Matrix.Identity(4)
    Hb = 11.5
    for a, b in ((-13.0, -2.15), (2.15, 18.0)):
        cube(P, "stone", I, a, b, 1.0, 33.5, 0.0, Hb)
    cube(P, "stone", I, -2.15, 2.15, 1.0, 33.5, STAGE_Z + 5.6, Hb)                      # over the passage
    cube(P, "trim", I, -2.15, 2.15, 1.0, 33.5, STAGE_Z + 5.3, STAGE_Z + 5.6)                      # the passage ceiling
    cube(P, "paving", I, -2.2, 2.2, -1.0, 33.6, -0.02, STAGE_Z)             # the passage at the stage level, through to the terrace
    cube(P, "cream", I, -13.2, 18.2, 0.8, 33.7, Hb - 0.35, Hb)                  # string course on top of the base
    crenels(P, -13.1, 18.1, 0.9, 33.6, Hb, "cream", 0.9, 1.0)
    BC.hip_roof(P, -12.6, 17.6, 1.4, 33.1, Hb + 0.1, 2.6)                      # blue slate roofs behind the parapet
    for (a0, a1, b0, b1) in ((-12.0, -5.0, 22.0, 32.0), (10.0, 17.0, 22.0, 32.0), (-12.0, -6.0, 3.0, 12.0), (11.0, 17.0, 5.0, 14.0)):
        BC.hip_roof(P, a0, a1, b0, b1, Hb + 0.6, 5.5)                           # the steep blue pyramids of the reference
        gold_hip(P, a0, a1, b0, b1, Hb + 0.6, 5.5)
    # the rear (north): the big gothic arch of the passage, rose window, the Fairy Tale Hall stair on the east side
    Mr = face(0, 33.5, math.pi)
    lathe(P, "trim", [(1.0, 0), (1.35, 0), (1.35, 0.25), (1.0, 0.25)], 28, Mr @ T(-5.2, -0.1, 6.6) @ R(math.pi / 2, "X"))
    for (du, dz) in ((0, 0.42), (0, -0.42), (0.42, 0), (-0.42, 0)):              # the quatrefoil window
        lathe(P, "glass", [(0, 0), (0.42, 0), (0.42, 0.05), (0, 0.05)], 16, Mr @ T(-5.2 + du, -0.05, 6.6 + dz) @ R(math.pi / 2, "X"))
    for u in (-9.8, -7.4, 6.0, 9.0):                                            # the red arched doors of the rear arcade
        poly_prism(P, "trim", Mr, [(x, z) for x, z in arch_ring(u, 1.5, 2.3, 0.3)], -0.3, 0.05)
        poly_prism(P, "door_red", Mr, [(u - 0.75, 0.0), (u + 0.75, 0.0)] + pointed(u - 0.75, u + 0.75, 2.3)[1:-1], 0.02, 0.06)
    for u in (-12.0, -7.0, -2.8, 2.8, 7.0, 12.0, 16.5):                          # rounded corbel turrets along the wall top
        corbel_turret(P, u, 33.7, Hb - 0.2, 0.85, 1.4)
    for x_ in (-13.3, 18.3):
        for v in (6.0, 12.0, 18.0, 24.0):
            corbel_turret(P, x_, v, Hb - 0.2, 0.75, 1.3)
    # the rear terrace (reference): a wide cross-shaped paved deck behind the castle over the moat, its sides a
    # stone wall with white pilasters standing in the water, pierced balustrades with gold finials on the posts
    cube(P, "trim", I, -14.0, 19.0, 33.4, 57.1, TZ - 0.6, TZ - 0.05) if False else None
    outline = [(-14.0, 33.5), (19.0, 33.5), (19.0, 42.0), (9.5, 42.0), (9.5, 58.0), (-4.5, 58.0), (-4.5, 42.0), (-14.0, 42.0)]
    TZ = STAGE_Z
    bm_prism(P["paving"], outline, TZ - 0.05, TZ + 0.02, "xy")
    bm_prism(P["stone"], outline, -1.6, TZ - 0.05, "xy")
    bm_prism(P["trim"], outline, TZ - 0.35, TZ - 0.05, "xy") if False else None
    edges = list(zip(outline[1:] + outline[:1], outline[2:] + outline[:2]))[:-1]
    for (x0_, y0_), (x1_, y1_) in edges:
        L_ = math.hypot(x1_ - x0_, y1_ - y0_)
        if L_ < 1:
            continue
        ang_ = math.atan2(y1_ - y0_, x1_ - x0_)
        Mb = face(x0_, y0_, ang_)
        pierced_balustrade(P, Mb @ Matrix.Translation((0, -0.2, 0)), 0.0, L_, TZ + 0.02, 1.0, 0.9)
        k_ = 0.0
        while k_ <= L_ + 1e-6:
            q = Mb @ Vector((k_, -0.2, 0))
            lathe(P, "trim", [(0, 0), (0.32, 0), (0.32, 1.25), (0.22, 1.35), (0, 1.35)], 10, T(q.x, q.y, TZ))
            gold_cross(P, q.x, q.y, TZ + 1.35, 0.5) if int(k_) % 8 == 0 else lathe(P, "gold", [(0, 1.35), (0.16, 1.35), (0.2, 1.6), (0.08, 1.85), (0, 1.95)], 8, T(q.x, q.y, TZ))
            cube(P, "trim", Mb, k_ - 0.3, k_ + 0.3, -0.05, 0.12, -1.6, TZ - 0.05)      # the white pilasters down to the water
            k_ += 4.0
    for k in range(6):                                                          # the stair down to the water at the end
        cube(P, "trim", I, -0.5, 5.5, 42.0 + k * 0.4, 42.4 + k * 0.4, -1.6, TZ - 0.05 - k * 0.26) if False else None
    # outside stair up the east side to the hall entrance (about 7 m), cream balustrade
    for k in range(24):
        z = 0.3 * (k + 1)
        cube(P, "trim", I, 18.0, 20.6, 33.0 - k * 0.55 - 0.55, 33.0 - k * 0.55, 0.0, z)
    cube(P, "trim", I, 18.0, 20.6, 16.2, 20.3, 0.0, 7.2)                         # landing
    for x_ in (18.1, 20.5):
        cube(P, "trim", I, x_ - 0.1, x_ + 0.1, 20.3, 33.0, 0.0, 0.1)
    Ms = face(20.6, 33.0, math.pi / 2 + math.atan2(7.2, 12.7) * 0)
    L = math.hypot(12.7, 7.2); ang = math.atan2(7.2, 12.7)
    Mrail = Matrix.Translation((20.6, 33.0 - 12.7 / 2, 7.2 / 2 + 0.9)) @ Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Rotation(ang, 4, "Y")
    for k in range(24):                                                         # the balustrade: one post per step
        cube(P, "trim", I, 20.35, 20.6, 33.0 - k * 0.55 - 0.3, 33.0 - k * 0.55 - 0.1, 0.3 * (k + 1), 0.3 * (k + 1) + 0.9)
    poly_prism(P, "trim", face(20.6, 0, math.pi / 2), [(33.0, 0.3), (20.3, 7.2), (20.3, 8.3), (33.0, 1.4)][::-1], -0.25, 0.0)
    Mh = face(18.0, 18.2, -math.pi / 2)                                          # the hall door on the landing
    poly_prism(P, "wood", Mh, [(-1.0, 7.2), (1.0, 7.2)] + pointed(-1.0, 1.0, 9.3)[1:-1], -0.02, 0.05)
    poly_prism(P, "trim", Mh, [(x, z + 7.2) for x, z in arch_ring(0.0, 2.0, 2.1, 0.3)], 0.0, 0.2)


FRONT_TOWERS = [   # (u, v, r, drum top, cone height): read off the elevation (cone tops 18.9 .. 24.4 m)
    (-10.6, 1.8, 2.1, 16.2, 7.6), (-5.6, 1.4, 1.95, 16.0, 6.6), (5.3, 1.4, 1.95, 16.3, 5.5), (11.1, 1.6, 1.4, 13.5, 5.4),
    (16.6, 1.9, 1.7, 15.8, 5.7),
]
REAR_TOWERS = [(-11.0, 32.0, 1.9, 17.0, 5.0), (15.8, 31.6, 2.1, 18.0, 5.5), (-12.5, 17.0, 1.8, 15.0, 6.0), (17.8, 12.0, 1.8, 15.5, 6.5)]


def build_towers(P):
    cols = ["red", "banner_b", "banner_a"]
    for i, (u, v, r, top, ch) in enumerate(FRONT_TOWERS):
        round_tower(P, u, v, r, top, ch)
        flag(P, u, v, top + ch * CONE_K + 0.9, cols[i % 3])
    for i, (u, v, r, top, ch) in enumerate(REAR_TOWERS):
        round_tower(P, u, v, r, top, ch, a0=0.1, a1=math.pi - 0.1)
        flag(P, u, v, top + ch * CONE_K + 0.9, cols[(i + 1) % 3])
    for (x_, y_) in ((-15.0, 20.0), (19.5, 25.0)):                             # grey crenellated drum towers (reference)
        lathe(P, "stone", [(0, 0), (2.3, 0), (2.1, 1.0), (2.1, 14.0), (2.5, 14.6), (2.5, 15.2), (0, 15.2)], 24, T(x_, y_, 0))
        for k in range(10):
            t = 2 * math.pi * k / 10
            cube(P, "stone", T(x_ + 2.3 * math.cos(t), y_ + 2.3 * math.sin(t), 0), -0.35, 0.35, -0.35, 0.35, 15.2, 16.0)
    # the set-back slim turret between the right front towers (cone 17.9 .. 24.4) and a square crenellated tower
    round_tower(P, 9.9, 5.0, 1.2, 17.9, 6.5, base_mat="cream", machi=False, z0=11.5)
    cube(P, "stone", Matrix.Identity(4), -14.0, -10.0, 22.0, 27.0, 0.0, 16.5)
    crenels(P, -14.2, -9.8, 21.8, 27.2, 16.5, "cream", 1.0, 0.9)


def build_palace(P):
    """The cream upper castle on the stone base: the clock gable, the palace with its tracery windows and gables,
    corner turrets, the keep with its gallery and upper stage, the slim spired turrets."""
    I = Matrix.Identity(4); zb = 11.5
    # the palace, in two parts (the turntable's side views): the front block (to 25.8 m) round the keep, and the
    # rear block stepping down to 20 m under blue roofs; tracery windows and crowns of gables on the faces
    YS = 16.5
    cube(P, "cream", I, -3.9, 8.4, 4.0, YS, zb, 25.8)
    cube(P, "trim", I, -4.1, 8.6, 3.8, YS + 0.2, 25.4, 25.8)
    cube(P, "cream", I, -3.4, 7.9, YS, 26.0, zb, 20.0)
    cube(P, "trim", I, -3.6, 8.1, YS, 26.2, 19.7, 20.0)
    BC.hip_roof(P, -3.5, 8.0, YS - 0.3, 26.1, 20.0, 4.2)
    gold_hip(P, -3.5, 8.0, YS - 0.3, 26.1, 20.0, 4.2)
    for i, (M, L) in enumerate(BC.side_frames(-3.4, 7.9, YS, 26.0)):
        if i == 0:
            continue
        crown(P, M, L, zb + 0.6, 2.4, 3.6, 2.2) if i in (1, 3) else [gothic_window(P, M, (k + 0.5) * L / 3, zb + 1.5, 1.0, 3.8) for k in range(3)]
        pierced_balustrade(P, M @ Matrix.Translation((0, 0.3, 0)), 0.0, L, zb + 0.2, 0.9)
    for i, (M, L) in enumerate(BC.side_frames(-3.9, 8.4, 4.0, YS)):
        if i in (1, 3):                                                          # the long sides: the crown of gables
            crown(P, M, L, zb + 2.0, 2.6, 5.8, 3.2)
        else:
            n = max(1, int(L / 2.6))
            for k in range(n):
                gothic_window(P, M, (k + 0.5) * L / n, zb + 2.0, 1.1, 4.2)
        for k in range(max(1, int(L / 2.6))):
            BC.window(P, M, (k + 0.5) * L / max(1, int(L / 2.6)), zb + 10.4, 0.6, 1.6, "pointed", 0.1)
        pierced_balustrade(P, M @ Matrix.Translation((0, 0.3, 0)), 0.0, L, zb + 0.2, 0.9)
    # stepped pink tiers with crenellated terraces (reference), not one long roof
    crenels(P, -4.1, 8.6, 3.8, YS + 0.2, 25.8, "cream", 0.9, 0.9)
    cube(P, "cream", I, -1.2, 7.0, 9.0, YS, 25.8, 28.4)                        # one low tier: only the keep rises above (turntable)
    for (M_, L_) in BC.side_frames(-1.2, 7.0, 9.0, YS):
        for k in range(max(1, int(L_ / 2.2))):
            BC.window(P, M_, (k + 0.5) * L_ / max(1, int(L_ / 2.2)), 26.3, 0.5, 1.5, "pointed", 0.08)
    crenels(P, -1.4, 7.2, 8.8, YS + 0.2, 28.4, "cream", 0.7, 0.85)
    for (x_, y_, z_) in ((-4.1, 3.8, 26.7), (8.6, 3.8, 26.7), (-4.1, YS + 0.2, 26.7), (8.6, YS + 0.2, 26.7), (-3.6, 26.2, 20.0), (8.1, 26.2, 20.0)):
        pinnacle(P, x_, y_, z_, 2.2, 0.18)
    # the upper palace gable (top 32.9) with the big tracery dormer (the red-framed windows of the drawing, 25.8 .. 28.4)
    gable_roof(P, -3.0, 2.2, 4.0, 11.0, 25.8, 31.0, along="y", ends=(False, True))
    bm_ = P["roof"]                                                             # the slate front of the upper gable
    v_ = [bm_.verts.new(p) for p in ((-3.0, 4.0, 25.8), (2.2, 4.0, 25.8), (-0.4, 4.0, 31.0))]
    bm_.faces.new(v_)
    Md = face(-0.4, 3.6, 0)
    cube(P, "cream", Md, -1.1, 1.1, -0.2, 1.6, 25.8, 29.6)
    gothic_window(P, Md, 0.0, 26.1, 1.1, 3.0, glass="stained")
    poly_prism(P, "trim", Md, [(-1.4, 29.4), (1.4, 29.4), (0.0, 31.4)], -0.3, 1.6)
    pinnacle(P, -0.4, 3.5, 31.8, 1.6, 0.14)
    # the rear cream wing over the stone arcade (Fantasyland side): corbels, a balustraded balcony, tall tracery
    # windows with gables, a slate roof with dormers
    cube(P, "cream", I, -9.5, 12.5, 26.0, 33.3, zb, 21.5)
    Mr = face(12.5, 33.3, math.pi)
    crown(P, Mr, 22.0, zb + 1.0, 2.75, 6.0, 4.6)
    crown(P, face(-9.5, 33.3, -math.pi / 2), 7.3, zb + 1.0, 2.4, 6.0, 4.6)
    crown(P, face(12.5, 26.0, math.pi / 2), 7.3, zb + 1.0, 2.4, 6.0, 4.6)
    for k in range(12):                                                         # the rounded corbels under it
        u_ = -9.2 + k * 1.95
        lathe(P, "cream", [(0, 0), (0.25, 0), (0.55, 0.6), (0.6, 1.1), (0, 1.1)], 12, T(u_, 33.6, zb - 1.3))
    balustrade(P, face(-9.5, 33.9, 0), 0.0, 22.0, zb, 0.8)
    cube(P, "cream", I, -9.6, 12.6, 33.3, 34.0, zb - 0.2, zb)
    BC.hip_roof(P, -9.7, 12.7, 25.8, 33.5, 21.5, 4.0)
    gold_hip(P, -9.7, 12.7, 25.8, 33.5, 21.5, 4.0)
    for k in range(4):                                                          # small blue cones behind the gables
        cone_roof(P, -7.0 + k * 6.0, 29.5, 21.5, 1.3, 5.5, 16)
    # corner turrets of the palace (bartizans) and pinnacles along the eaves
    for i, (x_, y_) in enumerate(((-3.9, 4.0), (8.4, 4.0), (-3.9, 26.0), (8.4, 26.0))):
        zt_ = 23.2 if y_ < 10 else 17.4                                          # the rear pair on the lower rear block
        bartizan(P, x_ + (0.5 if (y_ > 10 and x_ < 0) else -0.5 if y_ > 10 else 0.0), y_, zt_, 0.8, 2.6, 6.0)
        flag(P, x_, y_, zt_ + 9.6, ("red", "banner_b", "banner_a")[i % 3], 1.8, 1.3)
    for i, (x_, y_, z_, h_) in enumerate(((-6.8, 12.0, 16.0, 7.5), (11.2, 16.0, 16.0, 7.5), (-6.5, 22.0, 16.0, 6.5), (11.0, 8.0, 16.0, 6.0),
                                          (-1.5, 27.8, 21.5, 6.0), (6.5, 27.8, 21.5, 6.0))):
        lathe(P, "cream", [(0, zb), (0.95, zb), (0.95, z_), (1.15, z_ + 0.3), (1.15, z_ + 0.6), (0, z_ + 0.6)], 16, T(x_, y_, 0))
        crenels(P, x_ - 1.1, x_ + 1.1, y_ - 1.1, y_ + 1.1, z_ + 0.6, "trim", 0.6, 0.5) if i % 2 else None
        cone_roof(P, x_, y_, z_ + 0.6, 1.15, h_ * CONE_K, 16)
        flag(P, x_, y_, z_ + 0.6 + h_ * CONE_K + 0.9, ("banner_a", "red", "banner_b")[i % 3], 1.8, 1.3)
    for x_ in (-2.0, 0.5, 3.0, 5.5):
        pinnacle(P, x_, 3.8, 25.8, 1.8, 0.14)
    # the keep: square shaft to the gallery (27.2), the gallery ring, the tall upper stage (to 39.8) with pinnacles,
    # the gold spire to 51 m
    kx, ky = 3.9, 14.0
    cube(P, "cream", I, kx - 2.0, kx + 2.0, ky - 2.0, ky + 2.0, 25.8, 27.2)
    for (M, L) in BC.side_frames(kx - 2.0, kx + 2.0, ky - 2.0, ky + 2.0):
        BC.window(P, M, L / 2, 26.0, 0.5, 1.0, "pointed", 0.08)
    cube(P, "trim", I, kx - 2.6, kx + 2.6, ky - 2.6, ky + 2.6, 27.2, 27.6)
    balustrade(P, face(kx - 2.6, ky - 2.6, 0), 0.0, 5.2, 27.6, 0.8)
    lathe(P, "cream", [(0, 27.6), (2.0, 27.6), (2.0, 36.8), (2.25, 37.2), (2.25, 37.6), (1.5, 37.8), (1.5, 39.8), (0, 39.8)], 8,
          T(kx, ky, 0) @ R(math.pi / 8, "Z"))                                     # octagonal upper stage
    for k in range(8):
        t = 2 * math.pi * k / 8 + math.pi / 8
        M = face(kx + 1.86 * math.cos(t), ky + 1.86 * math.sin(t), t + math.pi / 2)
        BC.window(P, M, 0.0, 29.0, 0.45, 3.2, "pointed", 0.08, glass="stained")
        BC.window(P, M, 0.0, 33.5, 0.4, 2.2, "pointed", 0.08)
        pinnacle(P, kx + 2.2 * math.cos(t - math.pi / 8), ky + 2.2 * math.sin(t - math.pi / 8), 37.6, 2.2, 0.14)
        pinnacle(P, kx + 2.3 * math.cos(t - math.pi / 8), ky + 2.3 * math.sin(t - math.pi / 8), 27.6, 3.0, 0.16)
    lathe(P, "gold", [(0, 39.8), (1.4, 39.8), (1.2, 40.6), (0.75, 44.0), (0.4, 47.5), (0.12, 50.6), (0, 51.5)], 8,
          T(kx, ky, 0) @ R(math.pi / 8, "Z"))
    for k in range(8):                                                          # gold crockets up the spire
        t = 2 * math.pi * k / 8
        for j in range(5):
            zz = 40.6 + j * 1.9; rr = 1.0 - j * 0.18
            lathe(P, "gold", [(0, 0), (0.07, 0), (0, 0.3)], 4, T(kx + rr * math.cos(t), ky + rr * math.sin(t), zz))
    # slim spired turrets: left (gold spire to 37.5), behind the gable (blue cone to 42.7), right (to 41.3), right small
    for (x_, y_, r, top, ch, gold) in ((-3.0, 7.5, 0.9, 26.9, 10.6, True), (1.5, 16.5, 1.0, 34.4, 8.3, False),
                                       (7.3, 9.5, 1.3, 32.0, 9.3, False), (8.0, 5.0, 0.8, 24.4, 3.4, False)):
        lathe(P, "cream", [(0, zb), (r, zb), (r, top - 0.6), (r + 0.25, top - 0.3), (r + 0.25, top), (0, top)], 16, T(x_, y_, 0))
        BC.window(P, face(x_, y_ - r, 0), 0.0, top - 3.0, 0.35, 1.3, "pointed", 0.06)
        cone_roof(P, x_, y_, top, r + 0.2, ch * (0.55 if gold else 1.0), 16)
        if gold:
            lathe(P, "gold", [(0, top + ch * 0.55), (0.15, top + ch * 0.55), (0.03, top + ch), (0, top + ch + 0.1)], 8, T(x_, y_, 0))
            for j in range(6):                                                  # gold crockets up the spire
                zz = top + 0.8 + j * (ch * 0.9) / 6; rr = (r + 0.2) * (1 - j / 6.5)
                for k in range(6):
                    t = 2 * math.pi * k / 6
                    lathe(P, "gold", [(0, 0), (0.08, 0), (0, 0.35)], 4, T(x_ + rr * math.cos(t), y_ + rr * math.sin(t), zz))
        flag(P, x_, y_, top + ch + 0.2, "banner_a" if gold else "red", 2.4, 1.8)


def sq_pt(cx, cy, ax, ay, deg, n=4.0):
    """A point on a superellipse: the reference plaza is a rectangle with well-rounded front corners."""
    c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (cx + ax * math.copysign(abs(c) ** (2 / n), c), cy + ay * math.copysign(abs(s_) ** (2 / n), s_))


def build_forecourt(P):
    """The front of the reference, two levels:
      * the lower plaza: a chamfered paved deck over the moat with a red compass rose, gold-topped pedestals and
        pierced balustrades round its edge, ramps up either side;
      * the upper stage at the gate level (STAGE_Z): its front a stone retaining wall with white pilasters and two
        dark double doors; on the left a gold-railed platform under a gothic arch, on the right a grand curving stair
        rising to a round balcony under three gothic arches; tall gold poles with blue and gold pennants either side of
        the gate and along the stage; gold lamps on the posts.
    The castle stands on an island edged with rocks and grass."""
    I = Matrix.Identity(4); Z = STAGE_Z; LZ = LOWER_Z
    lower = [(-21.3, -14.0), (-21.3, -24.6), (-11.2, -32.2), (15.2, -32.2), (25.3, -24.6), (25.3, -14.0)]   # chamfered front (s06)
    bm_prism(P["paving"], lower, LZ - 0.25, LZ, "xy")
    bm_prism(P["stone"], lower, -1.6, LZ - 0.25, "xy")
    lathe(P, "red", [(0, LZ), (4.2, LZ), (4.2, LZ + 0.02), (0, LZ + 0.02)], 48, T(2.0, -19.5, 0))
    lathe(P, "paving", [(0, LZ + 0.02), (3.0, LZ + 0.02), (3.0, LZ + 0.03), (0, LZ + 0.03)], 48, T(2.0, -19.5, 0))
    for k in range(8):                                                          # the compass star
        t = math.pi / 4 * k; L_ = 4.0 if k % 2 == 0 else 2.6
        poly_prism(P, "red" if k % 2 else "trim", Matrix.Translation((2.0, -25.0, 0)) @ Matrix.Rotation(t, 4, "Z"),
                   [(-0.35, 0.0), (0.35, 0.0), (0.0, L_)], -0.92, -0.9) if False else None
        bm_prism(P["red" if k % 2 else "trim"], [(2.0 + 0.4 * math.cos(t + math.pi / 2), -19.5 + 0.4 * math.sin(t + math.pi / 2)),
                                                 (2.0 + L_ * math.cos(t), -19.5 + L_ * math.sin(t)),
                                                 (2.0 + 0.4 * math.cos(t - math.pi / 2), -19.5 + 0.4 * math.sin(t - math.pi / 2))], LZ + 0.03, LZ + 0.05, "xy")
    for (x0_, y0_), (x1_, y1_) in zip(lower[:-1], lower[1:]):                    # its balustrade and pedestals
        L_ = math.hypot(x1_ - x0_, y1_ - y0_); ang_ = math.atan2(y1_ - y0_, x1_ - x0_)
        Mb = face(x0_, y0_, ang_)
        if abs(x0_ - x1_) < 0.1 and abs(y0_ - y1_) < 0.1:
            continue
        cube(P, "trim", Mb, 0.0, L_, -0.1, 0.35, LZ - 0.25, LZ + 0.08)              # a white edge, no balustrade (s06)
    for rr in (6.5, 11.0):                                                # the concentric arcs on the paving
        pts_ = [(2.0 + rr * math.cos(math.radians(a_)), -19.5 + rr * math.sin(math.radians(a_))) for a_ in range(200, 341, 5)]
        for (xa, ya), (xb, yb) in zip(pts_[:-1], pts_[1:]):
            L_ = math.hypot(xb - xa, yb - ya)
            cube(P, "red" if rr < 7 else "stone", Matrix.Translation(((xa + xb) / 2, (ya + yb) / 2, 0)) @ Matrix.Rotation(math.atan2(yb - ya, xb - xa), 4, "Z"),
                 -L_ / 2, L_ / 2, -0.12, 0.12, LZ, LZ + 0.02)
    for a_ in (210, 240, 270, 300, 330):                                        # and the radial lines
        t = math.radians(a_)
        cube(P, "stone", Matrix.Translation((2.0 + 8.0 * math.cos(t), -19.5 + 8.0 * math.sin(t), 0)) @ Matrix.Rotation(t, 4, "Z"),
             -5.5, 5.5, -0.12, 0.12, LZ, LZ + 0.02)



# ================================================================ the centre of the front (reference still s06)
def tudor(u0, u1, spring, rise, n=10):
    """A low, slightly pointed arch from (u0, spring) over the apex to (u1, spring)."""
    w = u1 - u0; left = []
    for k in range(n + 1):
        t = k / n
        left.append((u0 + w / 2 * (1 - math.cos(t * math.pi / 2)), spring + rise * math.sin(t * math.pi / 2) + 0.25 * rise * t ** 6))
    right = [(u0 + u1 - u, z) for u, z in left[-2::-1]]
    return left + right


def slope_block(P, mat, x0, x1, y0, y1, za, zb, bottom=-1.6, axis="y"):
    """A block whose top slopes from za to zb along y (or x): the reference's ramps (slopes, not stairs)."""
    bm = P[mat]
    if axis == "y":
        top = ((x0, y0, za), (x1, y0, za), (x1, y1, zb), (x0, y1, zb))
    else:
        top = ((x0, y0, za), (x1, y0, zb), (x1, y1, zb), (x0, y1, za))
    v = [bm.verts.new((x, y, bottom)) for x, y, _ in top] + [bm.verts.new(p) for p in top]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])


def bal_line(P, A, B, h=1.0, step=0.42, mat="trim", newels=True):
    """White balustrade along a straight (possibly sloping) line A -> B: turned balusters, a plinth and a rail."""
    A, B = Vector(A), Vector(B); dv = B - A; L = dv.length
    if L < 0.05:
        return
    n = max(1, int(L / step))
    for k in range(n + 1):
        q = A + dv * (k / n)
        lathe(P, mat, [(0, 0), (0.07, 0), (0.1, 0.25), (0.05, 0.5), (0.07, 0.65), (0, h - 0.12)], 6, T(q.x, q.y, q.z))
    for zz, th in ((0.0, 0.12), (h - 0.14, 0.14)):
        M = Matrix.Translation((A + B) / 2 + Vector((0, 0, zz))) @ dv.to_track_quat("Z", "Y").to_matrix().to_4x4()
        cube(P, mat, M, -0.13, 0.13, 0.0, th, -L / 2, L / 2)
    if newels:
        for q in (A, B):
            cube(P, mat, T(q.x, q.y, q.z), -0.2, 0.2, -0.2, 0.2, 0.0, h + 0.1)


def banner(P, x, y, z, h=7.0, L=4.8, W=2.2):
    """Tall gold banner pole (reference): spike-and-ball finial, a crossbar with ball ends, a long blue shield-shaped
    pennant with a broad gold border and a gold emblem."""
    lathe(P, "gold", [(0, z), (0.16, z), (0.16, z + 0.25), (0.08, z + 0.4), (0.07, z + h), (0.18, z + h + 0.12), (0.18, z + h + 0.3),
                      (0.05, z + h + 0.4), (0.02, z + h + 1.0), (0, z + h + 1.05)], 10, T(x, y, 0))
    zb = z + h - 1.2
    M = Matrix.Translation((x, y, 0))
    cube(P, "gold", M, -W / 2 - 0.2, W / 2 + 0.2, -0.05, 0.05, zb, zb + 0.1)
    for sg in (-1, 1):
        lathe(P, "gold", [(0, -0.13), (0.13, 0), (0, 0.13)], 8, T(x + sg * (W / 2 + 0.3), y, zb + 0.05))
    poly_prism(P, "gold", M, [(-W / 2, zb), (W / 2, zb), (W / 2, zb - L * 0.2), (0.0, zb - L), (-W / 2, zb - L * 0.2)], -0.03, 0.03)
    poly_prism(P, "banner_a", M, [(-W / 2 + 0.22, zb - 0.2), (W / 2 - 0.22, zb - 0.2), (W / 2 - 0.22, zb - L * 0.22), (0.0, zb - L + 0.55),
                                  (-W / 2 + 0.22, zb - L * 0.22)], -0.05, 0.05)
    poly_prism(P, "gold", M, [(-0.32, zb - 1.1), (0.0, zb - 0.65), (0.32, zb - 1.1), (0.0, zb - 1.55)], -0.07, 0.07)      # the emblem


def build_front_centre(P):
    """The middle of the front as in the reference still: the stage with its white-pilastered stone wall and two dark
    doors, slopes up either side (no stairs), the gate frontispiece (low pointed arch, balcony, twin tracery arches,
    tracery band, the clock gable on a steep blue roof), the left pavilion (a platform with a white gothic arch, gold
    railing and urn), the right round balcony reached by a curving slope with a gold railing, three gothic arches on
    it, and eight tall banners. Built in world coordinates round the gate axis GX."""
    I = Matrix.Identity(4); Z = STAGE_Z; LZ = LOWER_Z; G = GX
    yf, yb = STAGE_F, STAGE_B
    # ---- the stage
    cube(P, "stone", I, G - 7.8, G + 7.8, yf, yb, -1.6, Z - 0.05)
    cube(P, "paving", I, G - 7.7, G + 7.7, yf + 0.25, yb, Z - 0.05, Z)
    Mf = face(G, yf, 0)
    cube(P, "trim", Mf, -7.9, 7.9, -0.05, 0.25, Z - 0.3, Z + 0.05)                # the coping
    cube(P, "trim", Mf, -7.9, 7.9, -0.05, 0.18, LZ, LZ + 0.3)                     # the plinth
    for u, wd, top in ((-7.25, 1.3, Z + 1.3), (-2.2, 1.0, Z + 0.05), (2.2, 1.0, Z + 0.05), (7.25, 1.3, Z + 1.3)):
        cube(P, "trim", Mf, u - wd / 2, u + wd / 2, -0.05, 0.32, LZ, top)
        cube(P, "trim", Mf, u - wd / 2 - 0.12, u + wd / 2 + 0.12, -0.05, 0.42, LZ, LZ + 0.5)
        cube(P, "trim", Mf, u - wd / 2 - 0.12, u + wd / 2 + 0.12, -0.05, 0.42, top - 0.35, top)
        if top > Z + 1:
            cube(P, "trim", Mf, u - wd / 2, u + wd / 2, -3.0, 0.0, Z - 0.3, top)    # the corner piers run back a little
    for u in (-4.75, 4.75):                                                     # the dark double doors, round-topped
        door = [(u - 1.0, LZ + 0.3), (u + 1.0, LZ + 0.3)] + [(u + math.cos(t) * 1.0, LZ + 2.3 + 0.35 * math.sin(t))
                                                              for t in [math.pi * k / 12 for k in range(13)]]
        poly_prism(P, "door_dark", Mf, door, 0.0, 0.05)
        ring = ([(u + 1.2, LZ + 0.3)] + [(u + math.cos(t) * 1.2, LZ + 2.3 + 0.5 * math.sin(t)) for t in [math.pi * k / 12 for k in range(13)]]
                + [(u - 1.2, LZ + 0.3), (u - 1.0, LZ + 0.3)] + [(u + math.cos(t) * 1.0, LZ + 2.3 + 0.35 * math.sin(t))
                                                                  for t in [math.pi * k / 12 for k in range(12, -1, -1)]] + [(u + 1.0, LZ + 0.3)])
        poly_prism(P, "trim", Mf, ring, 0.0, 0.12)
        cube(P, "iron", Mf, u - 0.03, u + 0.03, 0.05, 0.08, LZ + 0.3, LZ + 2.6)
        for zz in (LZ + 0.9, LZ + 2.0):
            cube(P, "iron", Mf, u - 0.95, u + 0.95, 0.05, 0.08, zz - 0.05, zz + 0.05)
        for sg in (-1, 1):
            lathe(P, "iron", [(0.08, 0), (0.13, 0), (0.13, 0.03), (0.08, 0.03)], 10, Mf @ T(u + sg * 0.3, 0.1, LZ + 1.35) @ R(-math.pi / 2, "X"))
    # ---- the slopes either side: curving (s06, s07, s11, s17), from the lower plaza beside the stage's corner out
    # along the island's edge and round back to the stage level at the castle end; beside the stage the ground stays
    # at the lower plaza's level
    for sg in (-1, 1):
        xa, xb = sorted((G + sg * 7.8, G + sg * 15.0))
        cube(P, "stone", I, xa, xb, yf, yb, -1.6, LZ - 0.05)
        cube(P, "paving", I, xa, xb, yf, yb, LZ - 0.05, LZ)
        P0 = Vector((G + sg * 9.9, yf - 1.2)); P1 = Vector((G + sg * 14.6, yf + 3.5)); P2 = Vector((G + sg * 11.6, yb - 2.6))
        N = 24; hw = 1.9
        cs, ins, outs, zs = [], [], [], []
        for k in range(N + 1):
            t = k / N
            c = (1 - t) ** 2 * P0 + 2 * (1 - t) * t * P1 + t * t * P2
            d = 2 * (1 - t) * (P1 - P0) + 2 * t * (P2 - P1); d.normalize()
            n = Vector((-d.y, d.x))
            e1, e2 = c + n * hw, c - n * hw
            if abs(e1.x - G) < abs(e2.x - G):
                ins.append(e1); outs.append(e2)
            else:
                ins.append(e2); outs.append(e1)
            cs.append(c); zs.append(LZ + (Z - LZ) * (3 * t * t - 2 * t ** 3))    # easing in at the foot and out at the top
        for mat, lo in (("stone", LZ - 0.05), ("paving", None)):
            bm = P[mat]
            for k in range(N):
                q = [ins[k], outs[k], outs[k + 1], ins[k + 1]]
                zz = [zs[k], zs[k], zs[k + 1], zs[k + 1]]
                if lo is None:
                    bm.faces.new([bm.verts.new((v.x, v.y, z + 0.02)) for v, z in zip(q, zz)])
                    continue
                vt = [bm.verts.new((v.x, v.y, z - 0.03)) for v, z in zip(q, zz)]
                vb = [bm.verts.new((v.x, v.y, lo)) for v in q]
                bm.faces.new(vt)
                bm.faces.new((vb[0], vb[3], vt[3], vt[0])); bm.faces.new((vb[1], vb[2], vt[2], vt[1]))
                if k == N - 1:
                    bm.faces.new((vb[3], vb[2], vt[2], vt[3]))
        # the landing at the top and the walk along the back to the stage
        la, lb = sorted((ins[N].x, outs[N].x))
        cube(P, "stone", I, la, lb, min(ins[N].y, outs[N].y), yb, LZ - 0.05, Z - 0.05)
        cube(P, "paving", I, la, lb, min(ins[N].y, outs[N].y), yb, Z - 0.05, Z)
        wa, wb = sorted((G + sg * 7.8, ins[N].x))
        cube(P, "stone", I, wa, wb, yb - 1.6, yb, LZ - 0.05, Z - 0.05)
        cube(P, "paving", I, wa, wb, yb - 1.6, yb, Z - 0.05, Z)
        # white balustrades along both curving edges, gold railings on the lower part, lamps on the newels
        for edge in (ins, outs):
            for k in range(0, N, 2):
                a, b = edge[k], edge[k + 2]
                bal_line(P, (a.x, a.y, zs[k]), (b.x, b.y, zs[k + 2]), 1.0, 0.42, newels=(k % 6 == 0))
            gr = [e + (c - e).normalized() * 0.35 for e, c in zip(edge[:8], cs[:8])]
            gold_railing(P, [(v.x, v.y) for v in gr], zs[:8], 0.8)
            gold_lamp(P, edge[0].x, edge[0].y, zs[0] + 1.1, 0.8)
        bal_line(P, (outs[N].x, outs[N].y, Z), (outs[N].x, yb, Z))
        gold_lamp(P, outs[N // 2].x, outs[N // 2].y, zs[N // 2] + 1.1, 0.8)
        gold_lamp(P, outs[N].x, outs[N].y, Z + 1.1, 0.8)
        # banners on the slopes: a pair along the inner edge, one at the outer foot (reference)
        for k, edge in ((2, ins), (5, ins), (6, outs)):
            v = edge[k] + (cs[k] - edge[k]).normalized() * 0.6
            banner(P, v.x, v.y, zs[k], 7.2, 4.6, 2.3)
    # ---- the gate frontispiece
    yg = GATE_F; Mg = face(G, yg, 0)
    ow, sp, rise = 1.25, Z + 2.2, 0.8                                            # the opening: 2.5 m wide, 3.0 m high
    H = Z + 7.3
    body = [(-2.9, 0.0), (-ow, 0.0)] + tudor(-ow, ow, sp, rise) + [(ow, 0.0), (2.9, 0.0), (2.9, H), (-2.9, H)]
    poly_prism(P, "stone", Mg, body, -1.3, 0.0)
    for (w0, w1) in ((0.75, 0.95), (0.0, 0.3)):                                  # the white mouldings round the arch
        ring = ([(-ow - w1, Z)] + tudor(-ow - w1, ow + w1, sp, rise + w1) + [(ow + w1, Z), (ow + w0, Z)]
                + tudor(-ow - w0, ow + w0, sp, rise + w0)[::-1] + [(-ow - w0, Z)])
        poly_prism(P, "trim", Mg, ring, 0.0, 0.14)
    for sg in (-1, 1):                                                          # the buttress piers with pinnacles
        cube(P, "trim", Mg, sg * 1.85 - 0.4, sg * 1.85 + 0.4, 0.0, 0.5, Z, Z + 5.6)
        cube(P, "trim", Mg, sg * 1.85 - 0.5, sg * 1.85 + 0.5, 0.0, 0.6, Z, Z + 0.6)
        cube(P, "trim", Mg, sg * 2.6 - 0.3, sg * 2.6 + 0.3, 0.0, 0.3, Z, H)
        q = Mg @ Vector((sg * 1.85, 0.25, 0)); pinnacle(P, q.x, q.y, Z + 5.6, 2.2, 0.28)
        q = Mg @ Vector((sg * 2.6, 0.15, 0)); pinnacle(P, q.x, q.y, H, 2.0, 0.2)
    cube(P, "trim", Mg, -1.45, 1.45, 0.0, 0.9, Z + 3.45, Z + 3.7)                   # the balcony over the gate
    for u in (-1.1, -0.35, 0.35, 1.1):
        lathe(P, "trim", [(0, 0), (0.12, 0), (0.2, 0.3), (0.2, 0.45), (0, 0.5)], 8, Mg @ T(u, 0.5, Z + 2.95))
    bal_line(P, Mg @ Vector((-1.4, 0.8, Z + 3.7)), Mg @ Vector((1.4, 0.8, Z + 3.7)), 0.8, 0.28)
    poly_prism(P, "glass", Mg, [(-1.1, Z + 3.7), (1.1, Z + 3.7), (1.1, Z + 4.1), (-1.1, Z + 4.1)], 0.0, 0.02)
    for u in (-0.8, 0.8):                                                       # the twin tracery arches
        BC.window(P, Mg, u, Z + 4.35, 1.3, 1.9, "pointed", 0.16)
        lathe(P, "trim", [(0.18, 0), (0.26, 0), (0.26, 0.06), (0.18, 0.06)], 12, Mg @ T(u, 0.06, Z + 5.55) @ R(-math.pi / 2, "X"))
    lathe(P, "gold", [(0, 0), (0.1, 0), (0.05, -0.5), (0, -0.6)], 8, Mg @ T(0, 0.2, Z + 6.2))
    cube(P, "trim", Mg, -2.7, 2.7, 0.0, 0.35, Z + 6.5, Z + 7.3)                  # the pierced tracery band
    for k in range(7):
        u = -2.1 + k * 0.7
        lathe(P, "stone", [(0, 0), (0.24, 0), (0.24, 0.04), (0, 0.04)], 12, Mg @ T(u, 0.36, Z + 6.9) @ R(-math.pi / 2, "X"))
        lathe(P, "trim", [(0.24, 0), (0.3, 0), (0.3, 0.06), (0.24, 0.06)], 12, Mg @ T(u, 0.36, Z + 6.9) @ R(-math.pi / 2, "X"))
    # the clock gable: white tracery gable, clock, crockets, pinnacles, the steep blue roof behind
    ga = Z + 12.6
    poly_prism(P, "trim", Mg, [(-2.5, H), (2.5, H), (0.0, ga)], 0.0, 0.3)
    Mg2 = Mg @ Matrix.Translation((0, 0.3, 0))
    for u in (-0.75, 0.75):
        BC.window(P, Mg2, u, H + 2.4, 0.55, 1.9, "pointed", 0.1)
    BC.window(P, Mg2, 0.0, H + 2.9, 0.6, 2.2, "pointed", 0.1)
    zc = H + 1.1
    lathe(P, "trim", [(0.72, 0), (0.95, 0), (0.95, 0.12), (0.72, 0.12)], 32, Mg @ T(0, 0.3, zc) @ R(-math.pi / 2, "X"))
    lathe(P, "clock", [(0, 0), (0.74, 0), (0.74, 0.05), (0, 0.06)], 32, Mg @ T(0, 0.3, zc) @ R(-math.pi / 2, "X"))
    for ang_, ln in ((math.radians(60), 0.45), (math.radians(-80), 0.6)):
        cube(P, "gold", Mg @ Matrix.Translation((0, 0.4, zc)) @ Matrix.Rotation(ang_, 4, "Y"), -0.035, 0.035, -0.01, 0.01, 0.0, ln)
    for k in range(12):
        t = 2 * math.pi * k / 12
        cube(P, "gold", Mg @ Matrix.Translation((0.6 * math.cos(t), 0.38, zc + 0.6 * math.sin(t))), -0.05, 0.05, -0.01, 0.01, -0.05, 0.05)
    for sg in (-1, 1):
        for k in range(7):
            t = (k + 0.5) / 7
            q = Mg @ Vector((sg * 2.5 * (1 - t), 0.2, 0))
            pinnacle(P, q.x, q.y, H + (ga - H) * t, 0.55, 0.08, "trim")
    q = Mg @ Vector((0, 0.15, 0)); pinnacle(P, q.x, q.y, ga, 2.6, 0.22)
    gable_roof(P, G - 3.0, G + 3.0, yg + 0.05, yg + 6.5, H - 0.1, Z + 13.2, along="y", ends=(False, False))
    bm_ = P["roof"]
    v_ = [bm_.verts.new(p) for p in ((G - 3.0, yg + 0.05, H - 0.1), (G + 3.0, yg + 0.05, H - 0.1), (G, yg + 0.05, Z + 13.2))]
    bm_.faces.new(v_)
    # the rear exit: the same opening and mouldings as the front entrance, in a stone screen closing the passage end
    Mr = face(G, PLAN_C[1] + (33.5 - PLAN_C[1]) * PLAN_S, math.pi)
    poly_prism(P, "stone", Mr, [(-2.9, 0.0), (-ow, 0.0)] + tudor(-ow, ow, sp, rise) + [(ow, 0.0), (2.9, 0.0), (2.9, Z + 5.6), (-2.9, Z + 5.6)], -0.6, 0.02)
    for (w0, w1) in ((0.75, 0.95), (0.0, 0.3)):
        ring = ([(-ow - w1, Z)] + tudor(-ow - w1, ow + w1, sp, rise + w1) + [(ow + w1, Z), (ow + w0, Z)]
                + tudor(-ow - w0, ow + w0, sp, rise + w0)[::-1] + [(-ow - w0, Z)])
        poly_prism(P, "trim", Mr, ring, 0.0, 0.14)
    # ---- banners either side of the gate
    for sg in (-1, 1):
        banner(P, G + sg * 2.2, yg - 1.3, Z, 6.6, 4.7, 2.1)
    # ---- the left pavilion: a white platform, its balustrade, a gold railing behind, a gold urn, a gothic arch
    px, py, pz = G - 5.0, -6.2, Z + 0.8
    cube(P, "trim", I, px - 2.3, px + 2.3, py - 2.0, py + 2.0, Z - 0.05, pz)
    cube(P, "paving", I, px - 2.2, px + 2.2, py - 1.9, py + 1.9, pz - 0.02, pz + 0.01)
    slope_block(P, "trim", px - 4.6, px - 2.3, py - 1.3, py + 1.3, Z, pz, Z - 0.05, axis="x")    # a slope up on its left
    bal_line(P, (px - 2.1, py - 1.95, pz), (px + 2.1, py - 1.95, pz), 0.9, 0.3)
    arc = [(px + 1.9 * math.cos(math.radians(a_)), py + 1.9 * math.sin(math.radians(a_))) for a_ in range(15, 200, 15)]
    gold_railing(P, arc, [pz] * len(arc), 1.1)
    gold_lamp(P, px + 2.0, py - 1.7, pz, 1.0)
    gothic_arch_frame(P, px, py + 0.4, pz, 3.0, 4.4, 0.0, 10)
    # ---- the right round balcony and the curving slope up to it
    cx, cy, Rb = G + 5.0, -4.4, 1.9
    zt = Z + 3.0
    lathe(P, "trim", [(0, Z - 0.05), (Rb, Z - 0.05), (Rb, zt - 0.3), (Rb + 0.25, zt - 0.1), (Rb + 0.25, zt), (0, zt)], 32, T(cx, cy, 0))
    for k in range(22):
        t = 2 * math.pi * k / 22
        lathe(P, "trim", [(0, 0), (0.09, 0), (0.12, 0.5), (0.06, 1.2), (0.1, 1.9), (0, 2.3)], 6, T(cx + (Rb + 0.1) * math.cos(t), cy + (Rb + 0.1) * math.sin(t), Z + 0.2))
    ring = [(cx + (Rb + 0.1) * math.cos(math.radians(a_)), cy + (Rb + 0.1) * math.sin(math.radians(a_))) for a_ in range(-10, 200, 15)]
    gold_railing(P, ring, [zt] * len(ring), 1.1)
    for a_ in (35.0, 95.0, 155.0):
        t = math.radians(a_)
        gothic_arch_frame(P, cx + (Rb - 0.35) * math.cos(t), cy + (Rb - 0.35) * math.sin(t), zt, 2.4, 4.4, t - math.pi / 2)
    r0, r1 = Rb + 0.3, Rb + 1.9                                                 # the curving slope: 1.6 m wide, round the front
    angs = [math.radians(200 + 150 * k / 24) for k in range(25)]
    zs = [Z + (zt - Z) * k / 24 for k in range(25)]
    for mat, dz, lo in (("trim", -0.04, LZ), ("paving", 0.0, None)):
        bm = P[mat]
        for k in range(24):
            a0, a1 = angs[k], angs[k + 1]
            q = [(cx + r * math.cos(a), cy + r * math.sin(a)) for r, a in ((r0, a0), (r1, a0), (r1, a1), (r0, a1))]
            zz = [zs[k] + dz, zs[k] + dz, zs[k + 1] + dz, zs[k + 1] + dz]
            if lo is None:
                vt = [bm.verts.new((x, y, z + 0.02)) for (x, y), z in zip(q, zz)]
                bm.faces.new(vt[::-1])
                continue
            vt = [bm.verts.new((x, y, z)) for (x, y), z in zip(q, zz)]
            vb = [bm.verts.new((x, y, lo)) for x, y in q]
            bm.faces.new(vt[::-1])
            bm.faces.new((vb[1], vb[2], vt[2], vt[1])); bm.faces.new((vb[3], vb[0], vt[0], vt[3]))
            if k == 0:
                bm.faces.new((vb[0], vb[1], vt[1], vt[0]))
    outer = [(cx + (r1 - 0.15) * math.cos(a), cy + (r1 - 0.15) * math.sin(a)) for a in angs]
    gold_railing(P, outer, zs, 1.1)
    for k in (0, 24):
        gold_lamp(P, outer[k][0], outer[k][1], zs[k], 0.8)


PLAN_SX = 0.80          # across (x): the front view is wider than 0.72 gave (the user's check)
PLAN_S = 0.72           # the reference model is slimmer: the castle's plan x 0.72 round its centre, heights kept
PLAN_C = (2.5, 17.0)
FORE_S = 0.72
FORE_SY = 0.85          # ... and a little longer front to back (the turntable's side view)           # the forecourt's plan x 0.70 (about as wide as the castle, as in the turntable views)
GATE_Y = PLAN_C[1] + (1.0 - PLAN_C[1]) * PLAN_S          # the gate after narrowing
BRIDGE = 6.0
FORE_DY = GATE_Y - BRIDGE - 1.0                            # the forecourt's back edge (local y 1.0) lands at the bridge
GX = PLAN_C[0] + (0.0 - PLAN_C[0]) * PLAN_SX              # the gate's axis after the plan scaling (world x)
STAGE_F = 1.0 + FORE_DY + (-14.0 - 1.0) * FORE_SY          # the stage's front wall (world y)
STAGE_B = GATE_Y - BRIDGE                                  # its back edge, where the bridge starts
GATE_F = GATE_Y - 1.0                                      # the face of the gate's frontispiece
FORE_DY_RAW = -8.0          # the forecourt island stands 8 m out from the castle, across the water (turntable views)


def floating_rock(P, x, y, rx, ry, depth, seed):
    """An upside-down craggy rock mass under an island (the reference model floats): a jagged cone from the water
    down to a blunt point, its rings randomly pushed in and out."""
    g = random.Random(seed)
    bm = P["rock"]; n = 16; rings = 7
    verts = []
    for j in range(rings):
        f = j / (rings - 1); z = -1.3 - depth * f
        sc = (1 - f) ** 0.7 * 0.95 + 0.05
        ring = []
        for i in range(n):
            t = 2 * math.pi * i / n
            k = sc * g.uniform(0.75, 1.15)
            ring.append(bm.verts.new((x + rx * k * math.cos(t) + g.uniform(-0.8, 0.8) * f, y + ry * k * math.sin(t) + g.uniform(-0.8, 0.8) * f,
                                      z + g.uniform(-0.8, 0.8) * (0 < j))))
        verts.append(ring)
    for j in range(rings - 1):
        for i in range(n):
            a, b = verts[j][i], verts[j][(i + 1) % n]; c, d = verts[j + 1][(i + 1) % n], verts[j + 1][i]
            bm.faces.new((a, b, c, d))
    bm.faces.new(verts[-1][::-1]); bm.faces.new(verts[0])


def build_islands(P):
    """The moat, the round grass island of the castle with rocks on its edge, the forecourt island's rocky edge,
    the stone arch bridge from the forecourt stage to the gate over the water gap."""
    I = Matrix.Identity(4)
    pool = [(2.5 + 30.0 * math.cos(t) * (1 + 0.04 * math.sin(3 * t)), 4.0 + 47.0 * math.sin(t) * (1 + 0.03 * math.cos(5 * t)))
            for t in [2 * math.pi * k / 72 for k in range(72)]]
    bm_prism(P["water"], pool, -1.32, -1.25, "xy")                            # the pool the model floats in
    floating_rock(P, 2.5, 17.0, 10.0, 7.5, 13.0, 7)                             # the rocks hanging under the islands
    floating_rock(P, 2.0, -16.0, 9.0, 7.0, 12.0, 11)
    R_ = 27.0 * PLAN_S
    lathe(P, "grass", [(0, -1.3), (R_, -1.3), (R_ - 1.0, -0.4), (R_ - 2.5, -0.05), (0, -0.05)], 48, T(2.5, 17.0, 0))   # the castle's island
    g = random.Random(21)
    for i in range(46):                                                         # its rocky edge
        t = 2 * math.pi * i / 46
        if 4.2 < t < 5.2 or 1.25 < t < 1.9:                                    # (the bridge in front and the terrace behind)
            continue
        x_, y_ = 2.5 + (R_ - 0.8) * math.cos(t), 17.0 + (R_ - 0.8) * math.sin(t)
        BC.boulder_cluster(P, x_, y_, g.uniform(1.3, 2.3), g.uniform(0.4, 1.2) - 1.3, i + 300)
    # the forecourt island's edge (its outline follows the stage and the D-shaped plaza, shifted by FORE_DY)
    edge = [(-19.0, -14.0 + 13.0 * t) for t in (0.0, 0.33, 0.66, 1.0)] + [(23.0, -14.0 + 13.0 * t) for t in (0.0, 0.33, 0.66, 1.0)] + \
           [(-22.5, -25.0), (-19.5, -28.0), (-16.0, -31.0), (20.0, -31.0), (23.5, -28.0), (26.5, -25.0)]   # rocks at the corners only (s06)
    for i, (x_, y_) in enumerate(edge):
        x_, y_ = GX + (x_ - 2.0) * FORE_S, 1.0 + FORE_DY + (y_ - 1.0) * FORE_SY
        BC.boulder_cluster(P, x_ + g.uniform(-0.4, 0.4), y_ + g.uniform(-0.4, 0.4), g.uniform(1.0, 1.7), g.uniform(0.4, 1.0) - 1.3, i + 200)
        if g.random() < 0.6:
            cube(P, "grass", I, x_ - 1.1, x_ + 1.1, y_ - 0.7, y_ + 0.7, -1.3, -1.02)
    # the bridge from the stage (at the gate level) over the gap to the gate: deck, balustrades, an arch below
    Z = STAGE_Z
    cube(P, "stone", I, GX - 2.6, GX + 2.6, GATE_Y - BRIDGE, GATE_Y + 0.5, -1.3, Z - 0.05)
    cube(P, "paving", I, GX - 2.4, GX + 2.4, GATE_Y - BRIDGE, GATE_Y + 0.5, Z - 0.05, Z)
    cutter_pts = [(-3.0, -1.3), (3.0, -1.3)] + pointed(-3.0, 3.0, -0.2)[1:-1]
    poly_prism(P, "water", face(0, FORE_DY + 4.0, 0), [(x, z) for x, z in cutter_pts], -0.05, 0.05) if False else None
    for sx in (-1, 1):
        pierced_balustrade(P, face(GX + sx * 2.5, GATE_Y - BRIDGE if sx < 0 else GATE_Y, math.pi / 2 if sx < 0 else -math.pi / 2), 0.0, BRIDGE, Z, 1.0, 0.9)
    for sx in (-1, 1):                                                          # the arch under the bridge, both faces
        poly_prism(P, "trim", face(GX + sx * 2.62, 0, math.pi / 2), [(x + GATE_Y - BRIDGE / 2, z) for x, z in arch_ring(0.0, 3.2, -0.3, 0.35)], -0.05, 0.05)


def build(context=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    B.col = bpy.data.collections.new("Cinderella"); sc.collection.children.link(B.col)
    B.cutters = bpy.data.collections.new("Cutters"); sc.collection.children.link(B.cutters)
    B.root = bpy.data.objects.new("Cinderella", None); B.col.objects.link(B.root); B.hide = []
    B.M = materials()
    BC.WEB = WEB
    t0 = time.time()
    P = Parts()
    for name, fn in (("base", build_base), ("towers", build_towers), ("palace", build_palace), ("forecourt", build_forecourt),
                     ("front", build_front_centre), ("islands", build_islands)):
        fn(P)
        if name in ("base", "towers", "palace"):
            Mp = Matrix.Translation((PLAN_C[0], PLAN_C[1], 0)) @ Matrix.Diagonal((PLAN_SX, PLAN_S, 1.0, 1.0)) @ Matrix.Translation((-PLAN_C[0], -PLAN_C[1], 0))
        elif name == "forecourt":
            Mp = Matrix.Translation((GX, 1.0 + FORE_DY, 0)) @ Matrix.Diagonal((FORE_S, FORE_SY, 1.0, 1.0)) @ Matrix.Translation((-2.0, -1.0, 0))
        else:
            Mp = None
        for k, bm in list(P.items()):
            if bm.verts:
                if Mp is not None:
                    bmesh.ops.transform(bm, matrix=Mp, verts=bm.verts)
                bmesh.ops.transform(bm, matrix=Matrix.Diagonal((ALL_S, ALL_S, 1.0, 1.0)), verts=bm.verts)
                o = obj_bm(f"CC_{name}_{k}", bm, k)
        P.clear()

    objs = [o for o in B.col.objects if o.type == "MESH" and o.data.materials and o.data.materials[0].name in ("cc_stone", "cc_cream", "cc_slate", "cc_paving")]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=TEX_M, correct_aspect=False, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    if context:
        ctx = bpy.data.collections.new("Context"); sc.collection.children.link(ctx)
        old = B.col; B.col = ctx
        ST.box("CTX_ground", (-70, 70, -60, 70, -1.4, -1.3), "grass")
        B.col = old
    print(f"[cc] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")


CAMS = {
    "front": ((2.5, -150.0, 2.0), (2.5, 10.0, 24.0), 60),
    "stage": ((2.0, -66.0, 6.0), (2.0, -12.0, 9.0), 30),
    "turntable": ((-120.0, -118.0, 62.0), (2.0, 6.0, 12.0), 50),   # the reference turntable's three-quarter view
    "ref_front": ((2.0, -150.0, 38.0), (2.0, 5.0, 14.0), 55),      # the turntable's front frame
    "ref_rear": ((2.0, 170.0, 40.0), (2.0, 20.0, 14.0), 55),       # the turntable's rear frame
    "ref_side": ((-170.0, 2.0, 30.0), (2.0, 8.0, 14.0), 50),       # the turntable's side frame          # the reference's front view of the stage         # from across the plaza, long lens (the photos' view)
    "ref_s06": ((GX, -128.0, 14.5), (GX, -13.3, 9.3), 84.0),      # the reference still of the front (s06)
    "rear_gate": ((GX, 80.0, 14.0), (GX, 29.0, 7.0), 45),        # the rear exit (same size as the front)
    "fore_top": ((GX - 30.0, -40.0, 45.0), (GX, -8.0, 2.0), 30),   # the forecourt from above-left (the curving slopes)
    "front_close": ((0.0, -40.0, 1.7), (0.0, 5.0, 15.0), 26),
    "rear": ((-18.0, 58.0, 1.7), (2.0, 20.0, 18.0), 22),
    "bridge": ((2.0, 64.0, 1.7), (2.0, 20.0, 14.0), 24),         # the reference's bridge view          # the Fantasyland side: the gothic arch, the stair
    "side": ((55.0, 5.0, 3.0), (2.0, 15.0, 20.0), 26),
    "aerial": ((60.0, -60.0, 70.0), (2.0, 12.0, 15.0), 30),
    "clock": ((0.0, -10.0, 13.0), (0.0, 1.0, 17.0), 35),
}


TT_EL, TT_D, TT_LENS = 14.0, 400.0, 96.7           # elevation (deg), distance (m), lens (mm): 12.9 px/m at 1920 px
TT_TARGET = (2.5, 2.5, 17.9)                          # image centre: the bridge, 17.5 m above the water


def tt_camera(k):
    az = math.radians(-5.0 * (k - 31))                # frame k of the reference turntable
    el = math.radians(TT_EL)
    tx, ty, tz = TT_TARGET
    loc = (tx + TT_D * math.cos(el) * math.cos(az), ty + TT_D * math.cos(el) * math.sin(az), tz + TT_D * math.sin(el))
    return loc, TT_TARGET, TT_LENS


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default=",".join(CAMS)); ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=60); ap.add_argument("--quick", action="store_true")
    ap.add_argument("--tt", default="", help="turntable frames to render like the reference, e.g. 1,13,25,37,49,61")
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
    for k in [int(v) for v in a.tt.split(",") if v]:
        loc, tgt, lens = tt_camera(k)
        cam = bpy.data.cameras.new(f"CAM_tt{k:03d}"); cam.lens = lens; cam.clip_start = 1.0; cam.clip_end = 3000
        co = bpy.data.objects.new(f"CAM_tt{k:03d}", cam); B.col.objects.link(co)
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cams[f"tt{k:03d}"] = co
    if a.tt:
        sc = bpy.context.scene
        sc.render.resolution_x, sc.render.resolution_y = 1920, 1038
        sc.render.film_transparent = True
        for o in list(bpy.data.objects):
            if o.name.startswith("CTX_"):
                o.hide_render = True
        a.cams = ",".join(f"tt{int(v):03d}" for v in a.tt.split(",") if v)
    bpy.context.scene.camera = cams["front"]
    ST.frame_view()
    for scr in bpy.data.screens:
        for area in scr.areas:
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.region_3d.view_location = (2.0, 12.0, 18.0); sp.region_3d.view_distance = 110.0
                    sp.shading.color_type = "TEXTURE"
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "cinderella.blend").resolve()))
    print("[cc] saved", OUT / "cinderella.blend")
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        old = ST.OUT; ST.OUT = OUT
        try:
            ST.render(cams, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES", "cc")
        finally:
            ST.OUT = old


def export_objects(merged):
    """For the mock: gate at the OSM point, heights on the DEM datum, one mesh per material ("CC_<material>")."""
    global WEB
    WEB = True
    build(context=False)
    import ds_tracks
    h = ds_tracks.make_ground(ds_tracks.data()); gz = h(*GATE)
    B.root.location = (GATE[0], GATE[1], gz)
    bpy.context.view_layer.update()
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        b = mat.node_tree.nodes.get("Principled BSDF")
        if not b:
            continue
        for inp in ("Base Color", "Normal", "Roughness"):
            for l in list(b.inputs[inp].links):
                if l.from_node.type != "TEX_IMAGE":
                    mat.node_tree.links.remove(l)
        if not b.inputs["Base Color"].links:
            b.inputs["Base Color"].default_value = mat.diffuse_color
    for img in bpy.data.images:
        if img.size[0] > 512:
            img.scale(512, 512)
    groups = {}
    for o in B.col.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        mats = [m for m in o.data.materials if m]
        if mats:
            groups.setdefault(mats[0].name, []).append((o, 0.0))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    res = []
    for k, parts in sorted(groups.items()):
        ob = merged("CC_" + k.split("_", 1)[1], parts, out)
        ob.data.materials.clear(); ob.data.materials.append(bpy.data.materials[k]); res.append(ob)
    print(f"[cc] export ground {gz:.2f} m")
    return res


if __name__ == "__main__" and bpy is not None:
    main()
