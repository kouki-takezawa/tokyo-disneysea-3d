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

    ashlar("stone.jpg", 0.5, (0.6, 1.3), [(178, 180, 186), (166, 168, 176), (190, 192, 198), (156, 158, 166), (200, 200, 206),
                                         (170, 172, 178), (148, 150, 158)], (214, 214, 218), 6.0, 3)
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
    M["stone"] = image_material("cc_stone", "stone.jpg", 0.85, 0.5, (0.62, 0.63, 0.66))    # light grey (reference)
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
    M["water"] = P("cc_water", (0.14, 0.30, 0.30), 0.05, Coat_Weight=1.0)
    M["banner_a"] = P("cc_banner_a", (0.30, 0.20, 0.60), 0.8); M["banner_b"] = P("cc_banner_b", (0.85, 0.65, 0.15), 0.8)
    M["paving"] = ST.mat_tiles("cc_paving", (0.66, 0.56, 0.50), (0.60, 0.50, 0.46), 0.6, (0.48, 0.42, 0.38))
    M["red"] = P("cc_red", (0.62, 0.08, 0.10), 0.6)
    M["statue"] = P("cc_statue", (0.85, 0.82, 0.76), 0.6)
    M["door_red"] = P("cc_door_red", (0.45, 0.06, 0.08), 0.6)
    M["door_dark"] = P("cc_door_dark", (0.16, 0.20, 0.22), 0.5, Metallic=0.4)
    M["banner_a"] = P("cc_banner_a", (0.05, 0.05, 0.40), 0.7)
    mat, nt, b = _principled("cc_rock", (0.46, 0.44, 0.40), 0.9); _mottle(nt, b, (0.46, 0.44, 0.40), 1.4, 0.6, 0.5); M["rock"] = mat
    M["grass"] = P("cc_grass", (0.18, 0.32, 0.12), 0.9)
    return M


# ================================================================ parts
def round_tower(P, x, y, r, top, cone_h, base_mat="stone", machi=True, windows=3, a0=-math.pi * 0.9, a1=-math.pi * 0.1, finial=True,
                z0=0.0, cone_r=None):
    """Stone drum from z0 to top: batter at the foot, arrow slits, a cream corbelled machicolation with small square
    openings, a crenellated parapet ring, then the blue cone with a cream skirt and a gold finial."""
    lathe(P, base_mat, [(0, z0), (r + 0.25, z0), (r, z0 + 1.2), (r, top - 1.6), (0, top - 1.6)], 28, T(x, y, 0))
    if machi:
        lathe(P, "cream", [(0, top - 1.8), (r + 0.02, top - 1.8), (r + 0.35, top - 1.1), (r + 0.35, top), (0, top)], 28, T(x, y, 0))
        for k in range(14):                                 # corbels
            t = 2 * math.pi * k / 14
            cube(P, "cream", face(x + r * math.cos(t), y + r * math.sin(t), t + math.pi / 2), -0.12, 0.12, 0.0, 0.3, top - 2.3, top - 1.8)
        for k in range(8):                                  # small square openings in the machicolation band
            t = 2 * math.pi * (k + 0.5) / 8
            if a0 <= t - 2 * math.pi <= a1 or a0 <= t <= a1 or True:
                cube(P, "glass", face(x + (r + 0.36) * math.cos(t), y + (r + 0.36) * math.sin(t), t + math.pi / 2), -0.18, 0.18, 0.0, 0.03, top - 0.9, top - 0.45)
    if machi and top - z0 > 10:                             # the lower machicolation ring (two rings in the photos)
        zm = z0 + (top - z0) * 0.66
        lathe(P, "cream", [(0, zm - 0.6), (r + 0.02, zm - 0.6), (r + 0.3, zm - 0.1), (r + 0.3, zm + 0.3), (0, zm + 0.3)], 28, T(x, y, 0))
        for k in range(8):
            t = 2 * math.pi * (k + 0.5) / 8
            cube(P, "glass", face(x + (r + 0.31) * math.cos(t), y + (r + 0.31) * math.sin(t), t + math.pi / 2), -0.15, 0.15, 0.0, 0.03, zm - 0.05, zm + 0.22)
    for k in range(windows):                                # arrow slits / small pointed windows on the visible side
        t = a0 + (a1 - a0) * (k + 0.5) / windows
        M = face(x + r * math.cos(t), y + r * math.sin(t), t + math.pi / 2)
        window(P, M, 0.0, z0 + (top - z0) * 0.45, 0.35, 1.0, "rect", 0.08, sill=False)
    cone_roof(P, x, y, top, cone_r or (r + 0.45), cone_h, 28, finial=finial)


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


# ================================================================ the castle, bottom to top
def build_base(P):
    """The stone lower castle: two masses either side of the through passage, the passage vault, the rear arch."""
    I = Matrix.Identity(4)
    Hb = 11.5
    for a, b in ((-13.0, -2.15), (2.15, 18.0)):
        cube(P, "stone", I, a, b, 1.0, 33.5, 0.0, Hb)
    cube(P, "stone", I, -2.15, 2.15, 1.0, 33.5, 9.6, Hb)                       # over the passage
    cube(P, "trim", I, -2.15, 2.15, 1.0, 33.5, 9.3, 9.6)                        # the passage ceiling
    cube(P, "paving", I, -2.2, 2.2, -1.0, 34.5, -0.02, 0.02)
    cube(P, "cream", I, -13.2, 18.2, 0.8, 33.7, Hb - 0.35, Hb)                  # string course on top of the base
    crenels(P, -13.1, 18.1, 0.9, 33.6, Hb, "cream", 0.9, 1.0)
    BC.hip_roof(P, -12.6, 17.6, 1.4, 33.1, Hb + 0.1, 2.6)                      # blue slate roofs behind the parapet
    # the front: the cream gothic frontispiece round the gate (13.2 m), the pointed gate arch (4.3 x 9.2), portcullis
    M = face(0, 1.0, 0)
    for a, b in ((-2.75, -2.15), (2.15, 2.75)):
        cube(P, "cream", I, a, b, -0.2, 2.0, 0.0, 13.2)
    cube(P, "cream", I, -2.75, 2.75, -0.2, 2.0, 9.4, 13.2)
    poly_prism(P, "trim", M, [(x, z) for x, z in arch_ring(0.0, 4.3, 6.3, 0.45)], -1.3, -1.1)
    for k in range(9):
        cube(P, "iron", M, -2.0 + k * 0.5, -1.94 + k * 0.5, -1.0, -0.95, 7.0, 9.0)             # portcullis bars (raised)
    cube(P, "iron", M, -2.1, 2.1, -1.0, -0.95, 7.2, 7.3); cube(P, "iron", M, -2.1, 2.1, -1.0, -0.95, 8.2, 8.3)
    window(P, M @ Matrix.Translation((0, -1.25, 0)), 0.0, 10.2, 1.6, 2.4, "pointed", 0.15, glass="stained")
    for sg in (-1, 1):                                                          # buttress pinnacles of the frontispiece
        cube(P, "trim", M, sg * 2.6 - 0.25, sg * 2.6 + 0.25, -1.5, -1.0, 0.0, 13.6)
        pinnacle(P, sg * 2.6, 1.0 - 1.25, 13.6, 2.6, 0.22)
    cube(P, "trim", M, -2.8, 2.8, -1.4, -1.0, 13.0, 13.3)
    balustrade(P, M @ Matrix.Translation((0, -1.2, 0)), -2.6, 2.6, 13.3, 0.7)
    lathe(P, "gold", [(0, 0), (0.45, 0), (0.45, 0.06), (0, 0.08)], 12, M @ T(0, -1.32, 9.9) @ R(math.pi / 2, "X"))   # crest over the gate
    # the rear (north): the big gothic arch of the passage, rose window, the Fairy Tale Hall stair on the east side
    Mr = face(0, 33.5, math.pi)
    poly_prism(P, "trim", Mr, [(x, z) for x, z in arch_ring(0.0, 5.5, 5.4, 0.6)], -0.35, 0.05)
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
    # the rear bridge over the moat (reference): deck on arches, pierced balustrades, gold lamps on pedestals
    cube(P, "stone", I, -3.6, 3.6, 33.5, 56.0, -1.6, -0.05)
    cube(P, "paving", I, -3.4, 3.4, 33.5, 56.0, -0.05, 0.02)
    for k in range(3):
        y0 = 36.0 + k * 6.5
        pts, _ = seg_arc(y0 + 2.5, -3.0, 5.0, 1.4, 12)
        poly_prism(P, "stone", face(-3.6, 0, math.pi / 2), [(-(y0 + 5.0), -1.6), (-y0, -1.6), (-y0, -3.0)] + [(-u_, z_) for u_, z_ in pts[::-1]] + [(-(y0 + 5.0), -3.0)], 0.0, 7.2)
    for sx in (-1, 1):
        Mb = face(sx * 3.5, 56.0 if sx < 0 else 33.5, math.pi / 2 if sx > 0 else -math.pi / 2)
        pierced_balustrade(P, Mb, 0.0, 22.5, 0.0, 1.0, 0.9)
        for v in (35.0, 41.5, 48.0, 54.5):
            gold_lamp(P, sx * 3.5, v, 0.0, 1.0)
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
    poly_prism(P, "cream", face(20.6, 0, math.pi / 2), [(-33.0, 0.3), (-20.3, 7.2), (-20.3, 8.3), (-33.0, 1.4)], -0.25, 0.0)
    Mh = face(18.0, 18.2, -math.pi / 2)                                          # the hall door on the landing
    poly_prism(P, "wood", Mh, [(-1.0, 7.2), (1.0, 7.2)] + pointed(-1.0, 1.0, 9.3)[1:-1], -0.02, 0.05)
    poly_prism(P, "trim", Mh, [(x, z + 7.2) for x, z in arch_ring(0.0, 2.0, 2.1, 0.3)], 0.0, 0.2)


FRONT_TOWERS = [   # (u, v, r, drum top, cone height): read off the elevation (cone tops 18.9 .. 24.4 m)
    (-10.6, 1.8, 2.1, 16.2, 7.6), (-5.6, 1.4, 1.95, 16.0, 6.6), (5.3, 1.4, 1.95, 16.3, 5.5), (11.1, 1.6, 1.4, 13.5, 5.4),
    (16.6, 1.9, 1.7, 15.8, 5.7),
]
REAR_TOWERS = [(-11.0, 32.0, 2.4, 17.0, 7.5), (15.8, 31.6, 3.1, 19.0, 9.5), (-12.5, 17.0, 1.8, 15.0, 6.0), (17.8, 12.0, 1.8, 15.5, 6.5)]


def build_towers(P):
    for u, v, r, top, ch in FRONT_TOWERS:
        round_tower(P, u, v, r, top, ch)
    for u, v, r, top, ch in REAR_TOWERS:
        round_tower(P, u, v, r, top, ch, a0=0.1, a1=math.pi - 0.1)
    # the set-back slim turret between the right front towers (cone 17.9 .. 24.4) and a square crenellated tower
    round_tower(P, 9.9, 5.0, 1.2, 17.9, 6.5, base_mat="cream", machi=False, z0=11.5)
    cube(P, "stone", Matrix.Identity(4), -14.0, -10.0, 22.0, 27.0, 0.0, 16.5)
    crenels(P, -14.2, -9.8, 21.8, 27.2, 16.5, "cream", 1.0, 0.9)


def build_palace(P):
    """The cream upper castle on the stone base: the clock gable, the palace with its tracery windows and gables,
    corner turrets, the keep with its gallery and upper stage, the slim spired turrets."""
    I = Matrix.Identity(4); zb = 11.5
    # the palace block (to 25.8 m): u -3.9 .. 8.4, v 4 .. 26, cream, a row of tracery windows on all faces
    cube(P, "cream", I, -3.9, 8.4, 4.0, 26.0, zb, 25.8)
    cube(P, "trim", I, -4.1, 8.6, 3.8, 26.2, 25.4, 25.8)
    for i, (M, L) in enumerate(BC.side_frames(-3.9, 8.4, 4.0, 26.0)):
        if i in (1, 3):                                                          # the long sides: the crown of gables
            crown(P, M, L, zb + 2.0, 2.6, 5.8, 3.2)
        else:
            n = max(1, int(L / 2.6))
            for k in range(n):
                gothic_window(P, M, (k + 0.5) * L / n, zb + 2.0, 1.1, 4.2)
        for k in range(max(1, int(L / 2.6))):
            BC.window(P, M, (k + 0.5) * L / max(1, int(L / 2.6)), zb + 10.4, 0.6, 1.6, "pointed", 0.1)
        pierced_balustrade(P, M @ Matrix.Translation((0, 0.3, 0)), 0.0, L, zb + 0.2, 0.9)
    BC.hip_roof(P, -4.1, 8.6, 3.8, 26.2, 25.8, 4.2)
    # the clock gable over the frontispiece: cream tracery front, the clock (15.2 m), steep blue gable roof (top 20.9)
    Mf = face(0, 2.0, 0)
    cube(P, "cream", I, -2.7, 2.7, 2.0, 7.0, 13.2, 15.6)
    gable_roof(P, -3.3, 3.3, 1.5, 8.0, 15.6, 20.9, along="y", ends=(False, True))   # the front stays open: slate either side of the clock panel
    poly_prism(P, "trim", Mf, [(-3.0, 15.4), (3.0, 15.4), (0.0, 20.9)], -0.7, -0.45)
    poly_prism(P, "cream", Mf, [(-2.4, 15.7), (2.4, 15.7), (0.0, 20.2)], -0.75, -0.7)
    bm_ = P["roof"]                                                             # the slate returns behind the clock panel
    v_ = [bm_.verts.new(p) for p in ((-3.3, 1.5, 15.6), (3.3, 1.5, 15.6), (0.0, 1.5, 20.9))]
    bm_.faces.new(v_)
    lathe(P, "trim", [(0.62, 0), (0.85, 0), (0.85, 0.16), (0.62, 0.16)], 32, Mf @ T(0, -0.85, 16.6) @ R(math.pi / 2, "X"))
    lathe(P, "clock", [(0, 0), (0.64, 0), (0.64, 0.05), (0, 0.06)], 32, Mf @ T(0, -0.8, 16.6) @ R(math.pi / 2, "X"))
    for ang_, ln in ((math.radians(60), 0.4), (math.radians(-80), 0.55)):
        cube(P, "gold", Mf @ Matrix.Translation((0, -0.9, 16.6)) @ Matrix.Rotation(ang_, 4, "Y"), -0.03, 0.03, -0.01, 0.01, 0.0, ln)
    for k in range(12):
        t = 2 * math.pi * k / 12
        cube(P, "gold", Mf @ Matrix.Translation((0.52 * math.cos(t), -0.88, 16.6 + 0.52 * math.sin(t))), -0.04, 0.04, -0.01, 0.01, -0.04, 0.04)
    pinnacle(P, 0.0, 1.5, 20.9, 2.4, 0.2)
    for sg in (-1, 1):                                                          # crockets up the gable edges
        for k in range(6):
            t = (k + 0.5) / 6
            pinnacle(P, sg * 3.0 * (1 - t), 1.45, 15.4 + 5.5 * t, 0.5, 0.08, "trim")
    # the upper palace gable (top 32.9) with the big tracery dormer (the red-framed windows of the drawing, 25.8 .. 28.4)
    gable_roof(P, -3.0, 2.2, 4.0, 24.0, 25.8, 32.9, along="y", ends=(False, True))
    bm_ = P["roof"]                                                             # the slate front of the upper gable
    v_ = [bm_.verts.new(p) for p in ((-3.0, 4.0, 25.8), (2.2, 4.0, 25.8), (-0.4, 4.0, 32.9))]
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
    crown(P, Mr, 22.0, zb + 1.0, 2.6, 6.0, 3.4)
    crown(P, face(-9.5, 33.3, -math.pi / 2), 7.3, zb + 1.0, 2.6, 6.0, 3.4)
    crown(P, face(12.5, 26.0, math.pi / 2), 7.3, zb + 1.0, 2.6, 6.0, 3.4)
    for k in range(12):                                                         # the rounded corbels under it
        u_ = -9.2 + k * 1.95
        lathe(P, "cream", [(0, 0), (0.25, 0), (0.55, 0.6), (0.6, 1.1), (0, 1.1)], 12, T(u_, 33.6, zb - 1.3))
    balustrade(P, face(-9.5, 33.9, 0), 0.0, 22.0, zb, 0.8)
    cube(P, "cream", I, -9.6, 12.6, 33.3, 34.0, zb - 0.2, zb)
    BC.hip_roof(P, -9.7, 12.7, 25.8, 33.5, 21.5, 4.0)
    for k in range(4):                                                          # small blue cones behind the gables
        cone_roof(P, -7.0 + k * 6.0, 29.5, 21.5, 1.3, 5.5, 16)
    # corner turrets of the palace (bartizans) and pinnacles along the eaves
    for (x_, y_) in ((-3.9, 4.0), (8.4, 4.0), (-3.9, 26.0), (8.4, 26.0)):
        bartizan(P, x_, y_, 23.2, 0.7, 2.4, 3.0)
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
    lathe(P, "gold", [(0, 39.8), (1.4, 39.8), (1.1, 41.0), (0.6, 44.5), (0.3, 47.5), (0.08, 50.2), (0, 51.0)], 8,
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


def build_forecourt(P):
    """The front stage and the island (reference): a raised stage before the gate, its stone retaining wall with cream
    pilasters and two dark double doors, pierced balustrades with gold lamps, a stair down in the middle, two gilded
    gothic arches over curving stairs either side, tall gold poles with blue and gold pennants, a red rosette on the
    paving; the whole castle stands on an island edged with rocks and grass in the moat."""
    I = Matrix.Identity(4)
    cube(P, "stone", I, -18.0, 22.0, -14.0, 1.0, -1.3, 1.0)
    cube(P, "paving", I, -17.8, 21.8, -13.8, 1.0, 1.0, 1.05)
    lathe(P, "red", [(0, 1.05), (3.4, 1.05), (3.4, 1.07), (0, 1.07)], 48, T(0.0, -6.5, 0))
    lathe(P, "paving", [(0, 1.07), (2.6, 1.07), (2.6, 1.08), (0, 1.08)], 48, T(0.0, -6.5, 0))
    for k in range(8):                                                          # the rosette's red points
        t = 2 * math.pi * k / 8
        poly_prism(P, "red", Matrix.Translation((0, -6.5, 0)) @ Matrix.Rotation(t, 4, "Z"),
                   [(-0.5, 3.4), (0.5, 3.4), (0.0, 4.6)], 1.05, 1.07) if False else None
    Mf = face(-18.0, -14.0, 0)                                                  # the retaining wall's front face
    for u in (0.5, 8.0, 14.0, 26.0, 32.0, 39.5):                                 # cream pilasters
        cube(P, "trim", Mf, u - 0.45, u + 0.45, -0.2, 0.05, -1.3, 1.1)
    for u in (11.0, 29.0):                                                      # the dark double doors
        cube(P, "door_dark", Mf, u - 1.3, u + 1.3, -0.08, 0.02, -1.3, 0.85)
        cube(P, "trim", Mf, u - 1.5, u + 1.5, -0.15, 0.05, 0.85, 1.0)
        cube(P, "iron", Mf, u - 0.03, u + 0.03, -0.1, -0.08, -1.3, 0.85)
    for (u0, u1) in ((0.0, 13.8), (22.2, 40.0)):
        pierced_balustrade(P, Mf @ Matrix.Translation((0, 0.3, 0)), u0, u1, 1.05, 1.0, 0.9)
    for sx, x0 in ((-1, -18.0), (1, 22.0)):
        pierced_balustrade(P, face(x0, 1.0 if sx < 0 else -14.0, -math.pi / 2 if sx < 0 else math.pi / 2), 0.0, 15.0, 1.05, 1.0, 0.9)
    for (x_, y_) in ((-18.0, -14.0), (-4.2, -14.0), (4.2, -14.0), (22.0, -14.0), (-18.0, -7.0), (22.0, -7.0), (-18.0, 0.5), (22.0, 0.5)):
        gold_lamp(P, x_, y_, 1.05, 1.0)
    for k in range(7):                                                          # the stair down in the middle
        cube(P, "trim", I, -4.0, 4.0, -14.0 - (k + 1) * 0.35, -14.0 - k * 0.35, -1.3, 1.0 - (k + 1) * 0.33)
    for sx in (-1, 1):                                                          # gilded gothic arches over curving stairs
        cx = sx * 8.5
        for (dx, h_) in ((-1.6, 6.5), (1.6, 6.5)):
            lathe(P, "trim", [(0, 1.05), (0.22, 1.05), (0.18, 1.3), (0.15, 1.05 + h_), (0, 1.05 + h_)], 10, T(cx + dx, -4.0, 0))
        pts = pointed(cx - 1.6, cx + 1.6, 1.05 + 6.5)
        P_ = [(x, -4.0, z) for x, z in pts]
        ST.curve_obj(f"CC_arch_{sx}", P_, "gold", 0.1)
        for k in range(10):                                                     # the curving stair up to a small landing
            a_ = math.radians(-90 + sx * k * 12)
            r_ = 3.0
            cube(P, "trim", T(cx + sx * r_ * 0.3 * math.cos(a_), -4.0 + r_ * math.sin(a_) * 0.5, 0), -0.8, 0.8, -0.35, 0.35, 1.05, 1.05 + 0.2 * (k + 1))
    for x_, fac in ((-15.5, 0.0), (-11.0, 0.0), (-6.0, 0.0), (6.0, 0.0), (11.0, 0.0), (15.5, 0.0), (20.0, 0.0)):
        pennant_pole(P, x_, -12.8, 1.05, 9.5, fac)
    cube(P, "water", I, -40.0, 44.0, -26.0, 62.0, -1.3, -1.25)                  # the moat
    # the island's edge: boulders and grass tufts round the stage and the castle base
    g = random.Random(21)
    edge = [(-19.0 + 41.0 * t, -15.2) for t in [i / 14 for i in range(15)]] + \
           [(-19.2, -14.0 + 48.0 * t) for t in [i / 16 for i in range(17)]] + [(23.2, -14.0 + 48.0 * t) for t in [i / 16 for i in range(17)]]
    for i, (x_, y_) in enumerate(edge):
        if g.random() < 0.65:
            BC.boulder_cluster(P, x_ + g.uniform(-0.6, 0.6), y_ + g.uniform(-0.6, 0.6), g.uniform(1.2, 2.2), g.uniform(0.6, 1.4) - 1.3, i + 200)
        if g.random() < 0.5:
            cube(P, "grass", I, x_ - 1.2, x_ + 1.2, y_ - 0.8, y_ + 0.8, -1.3, -1.05)
    cube(P, "grass", I, -19.5, 23.5, 1.0, 34.0, -1.3, -0.05)                    # the island ground round the base


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
    for name, fn in (("base", build_base), ("towers", build_towers), ("palace", build_palace), ("forecourt", build_forecourt)):
        fn(P)
        for k, bm in list(P.items()):
            if bm.verts:
                obj_bm(f"CC_{name}_{k}", bm, k)
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
    "stage": ((2.0, -48.0, 4.0), (2.0, -2.0, 9.0), 30),          # the reference's front view of the stage         # from across the plaza, long lens (the photos' view)
    "front_close": ((0.0, -40.0, 1.7), (0.0, 5.0, 15.0), 26),
    "rear": ((-18.0, 58.0, 1.7), (2.0, 20.0, 18.0), 22),
    "bridge": ((0.0, 92.0, 2.5), (0.0, 20.0, 16.0), 32),         # the reference's bridge view          # the Fantasyland side: the gothic arch, the stair
    "side": ((55.0, 5.0, 3.0), (2.0, 15.0, 20.0), 26),
    "aerial": ((60.0, -60.0, 70.0), (2.0, 12.0, 15.0), 30),
    "clock": ((0.0, -10.0, 13.0), (0.0, 1.0, 17.0), 35),
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default=",".join(CAMS)); ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=60); ap.add_argument("--quick", action="store_true")
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
