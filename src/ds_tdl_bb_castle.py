"""美女と野獣の城 (Tokyo Disneyland, New Fantasyland, opened 2020-09-28) -- Blender 5.2.

  blender -b --python src/ds_tdl_bb_castle.py -- --samples 32          # renders + output/disneyland/bb_castle/bb_castle.blend
  blender -b --python src/ds_tdl_bb_castle.py -- --cams none
  python -c "import ds_tdl_bb_castle as b; b.make_textures()"      # repaint the textures (plain Python: Blender has no PIL)

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
v2 (2026-09-25, the user asked for ~100 photos): 401 web photos gathered through Bing image search (looked at only,
not stored in the repository), about 150 of the exterior after removing near-duplicates. From them: the stacked
"wedding cake" palace (tiers with cornices, balustrades, steep rose mansards and baroque cream dormers), the slim keep
rising far above the tiers, the gatehouse's lion niches, the raised courtyard reached by a stair inside the gate, the
bronze grotesque lamp posts on the bridge, the boulder outcrops with waterfalls round the side and back.
Proportions were matched by rendering from the photos' viewpoints and comparing side by side (gate cornice : keep top
about 0.3 from the bridge).

SIZE (2026-09-25, the user's ruler): the gate door leaves are 3.0 m; everything is scaled uniformly from them (scale()).
Checked against the photos with the door as the unit: gate wall to the cornice about 1.8 doors (5.4 m), the lion
niches a little lower than the door (the first build had the door and niches ~1.6x too tall: fixed), the palace
door about 5 m, the gatehouse ridge 10.6 m, the wings' balustrade 13.5 m, the keep's crenellations about 37.5 m and
its spire tip 42.6 m above the gate. The public figure "about 30 m" is lower: the photos with the door as the unit
give the taller keep, so the door ruler was kept (the user's choice).
ESTIMATES: every size. The public figure is "about 30 m"; matching the photos needs the keep top about 43 m above the
bridge (the courtyard stands 2 m higher, the palace is scaled x1.15 in height), so the photo proportions were kept.
The plan behind the gate (the aerial photo predates the castle), window and statue counts, rock shapes are estimates.
"""
import sys, math, argparse, pathlib, time, random

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix, noise
except ImportError:
    bpy = bmesh = Vector = Matrix = noise = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_tdl_station as ST
from ds_tdl_station import (B, box, prism, bm_box, bm_lathe, bm_prism, obj_bm, array_mod, radial_array, T, R, seg_arc,
                            _principled, _mottle, _bump, text)

OUT = ROOT / "output" / "disneyland" / "bb_castle"
GATE = (-622.0, 497.1)
ANG = 152.1                     # the local X axis in the plan (deg): the castle faces NE, towards the bridge
COURT_Z = 2.0                  # the courtyard and palace stand on a platform: a stair climbs inside the gate (photos)
GATE_SZ = 0.70                 # the gatehouse is lower than first drawn (its cornice level with the wings' balustrade)
PALACE_SZ = 1.15               # the photos show the palace about twice the gatehouse: its heights x 1.15 (keep top ~37 m)
PALACE_DY = -6.0               # the palace stands 5 m closer than drawn (the courtyard is shallow in the photos)
DOOR_H = 3.0                   # the user's ruler (2026-09-25): the front (gate) door leaves are 3 m high
DOOR_LOCAL = 5.0               # their height as drawn (before GATE_SZ); SCALE shrinks the whole castle to match
WEB = False                    # export_objects(): no lead cames (hundreds of thousands of tiny boxes)
GROUND_DATUM = 0.0              # set from the DEM by export_objects()
rnd = random.Random(11)


# ================================================================ painted textures (so the blockwork shows in every view)
TEX_DIR = ROOT / "plateau_data" / "bb_castle"
TEX_M = 4.0                     # one texture tile covers 4 x 4 m (cube-projected UVs, see uv_project())


def scale():
    return DOOR_H / (DOOR_LOCAL * GATE_SZ)


def make_textures():
    """Paint the castle's surfaces as images (photos looked at, nothing copied): coursed ashlar in mixed lilac / grey /
    rose shades with thin light joints; the darker rusticated base; rose fish-scale / plain roof tiles."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    g = random.Random(5); N = 1024; px = N / TEX_M

    def ashlar(fn, course, lengths, palette, joint, rough, seed_noise):
        im = Image.new("RGB", (N, N), joint); d = ImageDraw.Draw(im)
        y = 0.0; row = 0
        while y < TEX_M - 1e-6:
            h = course
            x = -g.uniform(0, lengths[1])
            while x < TEX_M:
                L = g.uniform(*lengths)
                c = palette[g.randrange(len(palette))]
                k = g.uniform(0.9, 1.08)
                col = tuple(max(0, min(255, int(v * k))) for v in c)
                x0, x1 = x * px, (x + L) * px; y0, y1 = y * px, (y + h) * px
                d.rectangle([x0 + 1.5, y0 + 1.5, x1 - 1.5, y1 - 1.5], fill=col)
                if x1 > N:                                             # wrap horizontally (tileable)
                    d.rectangle([x0 - N + 1.5, y0 + 1.5, x1 - N - 1.5, y1 - 1.5], fill=col)
                x += L
            y += h; row += 1
        a = np.asarray(im).astype(np.float32)
        rng = np.random.default_rng(seed_noise)
        n = rng.normal(0, rough, (N // 8, N // 8, 1)).repeat(8, 0).repeat(8, 1)
        n = np.asarray(Image.fromarray(((n[:, :, 0] + 40) * 3).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)[:, :, None] / 3 - 40
        fine = rng.normal(0, rough * 0.6, (N, N, 1))
        a = (a + n + fine).clip(0, 255).astype(np.uint8)
        Image.fromarray(a).save(TEX_DIR / fn, quality=90)

    ashlar("stone.jpg", 0.42, (0.55, 1.25),
           [(172, 160, 192), (162, 152, 186), (184, 170, 198), (152, 146, 170), (190, 168, 186), (168, 158, 180), (146, 138, 166)],
           (196, 188, 200), 7.0, 1)
    ashlar("base.jpg", 0.62, (0.9, 1.6),
           [(104, 98, 132), (96, 90, 124), (112, 104, 138), (90, 86, 112), (118, 108, 136)], (70, 66, 86), 12.0, 2)
    # roof: staggered rounded tiles (fish-scale) in rose shades with dark gaps
    im = Image.new("RGB", (N, N), (70, 26, 34)); d = ImageDraw.Draw(im)
    tw, th = 0.28 * px, 0.22 * px
    for r in range(int(N / th) + 2):
        off = (r % 2) * tw / 2
        for c in range(int(N / tw) + 2):
            x0 = c * tw - off; y0 = r * th
            base = [(178, 78, 90), (166, 70, 82), (186, 88, 98), (158, 66, 78), (172, 84, 96)][g.randrange(5)]
            d.rounded_rectangle([x0 + 1, y0 + 1, x0 + tw - 1, y0 + th * 1.35], radius=tw * 0.45, fill=base)
            d.line([x0 + 3, y0 + th * 1.3, x0 + tw - 3, y0 + th * 1.3], fill=tuple(int(v * 0.72) for v in base), width=2)
    im.save(TEX_DIR / "roof.jpg", quality=90)


def image_material(name, fn, rough=0.8, bump=0.35):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree; b = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(TEX_DIR / fn), check_existing=True)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(tex.outputs["Color"], bw.inputs[0])
    _bump(nt, b, bw.outputs[0], bump, 0.01)
    px = tex.image.pixels[:4] if tex.image.size[0] else (0.6, 0.55, 0.65, 1)
    mat.diffuse_color = (0.55, 0.52, 0.64, 1)
    return mat


def uv_project(objs):
    """Cube-project UVs in world metres (1 UV unit = TEX_M m) on every textured object, in one multi-object edit."""
    objs = [o for o in objs if o.type == "MESH"]
    if not objs:
        return
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=TEX_M / scale(), correct_aspect=False, scale_to_bounds=False)   # true-size blocks after scaling
    bpy.ops.object.mode_set(mode="OBJECT")


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
    if not (TEX_DIR / "stone.jpg").exists():
        make_textures()
    M["lilac"] = image_material("bb_lilac", "stone.jpg")                 # coursed ashlar, mixed lilac / grey / rose (photos)
    M["base"] = image_material("bb_base", "base.jpg", 0.85, 0.6)       # rusticated base course
    mat, nt, b = _principled("bb_cream", (0.70, 0.57, 0.38), 0.55); _mottle(nt, b, (0.70, 0.57, 0.38), 6, 0.88, 0.05); M["cream"] = mat
    M["roof"] = image_material("bb_roof", "roof.jpg", 0.55, 0.5)
    M["dome"] = P("bb_dome", (0.40, 0.55, 0.50), 0.5, Metallic=0.4)
    M["gold"] = P("bb_gold", (0.86, 0.66, 0.28), 0.25, Metallic=1.0)
    M["glass"] = P("bb_glass", (0.10, 0.12, 0.20), 0.08, Coat_Weight=1.0)
    M["stained"] = P("bb_stained", (0.30, 0.16, 0.36), 0.1, Emission_Color=(0.9, 0.5, 0.3, 1), Emission_Strength=0.15)
    M["wood"] = P("bb_wood", (0.30, 0.16, 0.09), 0.7)
    M["iron"] = P("bb_iron", (0.05, 0.05, 0.06), 0.4, Metallic=0.7)
    M["statue"] = P("bb_statue", (0.72, 0.69, 0.64), 0.7)
    M["paving"] = ST.mat_tiles("bb_paving", (0.46, 0.46, 0.49), (0.40, 0.41, 0.45), 0.6, (0.30, 0.30, 0.32))
    mat, nt, b = _principled("bb_rock", (0.46, 0.40, 0.33), 0.9); _mottle(nt, b, (0.46, 0.40, 0.33), 1.4, 0.55, 0.6); M["rock"] = mat
    M["water"] = P("bb_water", (0.92, 0.95, 0.97), 0.3, Emission_Color=(0.9, 0.95, 1.0, 1), Emission_Strength=0.15)
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

    def flush(self, prefix, dy=0.0):
        for k, bm in list(self.items()):
            if bm.verts:
                o = obj_bm(f"BB_{prefix}_{k}", bm, k)
                o.location.y += dy
                if prefix == "palace":
                    o.scale.z = PALACE_SZ
                if prefix in ("palace", "courtyard"):
                    o.location.z += COURT_Z
                if prefix == "gatehouse":
                    o.scale.z = GATE_SZ
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
        for sg in (-1, 1):                                          # little brackets under the sill
            cube(P, "cream", M, u + sg * w * 0.35 - 0.05, u + sg * w * 0.35 + 0.05, 0.0, 0.12, z0 - 0.34, z0 - 0.14)
    if w >= 0.55 and h >= 1.0 and not WEB:
        top_z = spring if kind != "rect" else z0 + h
        cube(P, "cream", M, u - 0.025, u + 0.025, 0.0, 0.06, z0, top_z + (w * 0.4 if kind != "rect" else 0))   # mullion
        cube(P, "cream", M, u0, u1, 0.0, 0.06, z0 + (top_z - z0) * 0.62, z0 + (top_z - z0) * 0.62 + 0.05)      # transom
        step = 0.16                                                  # diamond leading (lead cames) over the glass
        for sgn in (1, -1):
            c = u0 - (top_z - z0)
            while c < u1 + (top_z - z0):
                pts = []
                for t in (0.0, 1.0):
                    zz = z0 + t * (top_z - z0); uu = c + sgn * t * (top_z - z0)
                    pts.append((uu, zz))
                (ua, za), (ub, zb) = pts
                if sgn < 0:
                    ua, ub = ua + (top_z - z0), ub + (top_z - z0)
                # clip to the rectangle u0..u1
                if max(ua, ub) > u0 and min(ua, ub) < u1:
                    t0 = 0.0 if u0 <= ua <= u1 else ((u0 if ua < u0 else u1) - ua) / (ub - ua)
                    t1 = 1.0 if u0 <= ub <= u1 else ((u0 if ub < u0 else u1) - ua) / (ub - ua)
                    t0, t1 = max(0.0, min(t0, t1)), min(1.0, max(t0, t1))
                    if t1 - t0 > 0.02:
                        a_ = (ua + (ub - ua) * t0, za + (zb - za) * t0); b_ = (ua + (ub - ua) * t1, za + (zb - za) * t1)
                        L_ = math.hypot(b_[0] - a_[0], b_[1] - a_[1]); ang = math.atan2(b_[1] - a_[1], b_[0] - a_[0])
                        Mm = M @ Matrix.Translation(((a_[0] + b_[0]) / 2, 0.035, (a_[1] + b_[1]) / 2)) @ Matrix.Rotation(-ang, 4, "Y")
                        cube(P, "iron", Mm, -L_ / 2, L_ / 2, -0.004, 0.004, -0.006, 0.006)
                c += step
    if kind in ("pointed", "round") and h >= 1.0:
        hood = (pointed if kind == "pointed" else round_top)(u0 - frame - 0.12, u1 + frame + 0.12, spring)
        inner = (pointed if kind == "pointed" else round_top)(u0 - frame, u1 + frame, spring)
        band = hood + inner[::-1]
        try:
            poly_prism(P, "cream", M, band, 0.0, 0.14)                      # hood moulding
        except ValueError:
            pass
        for sg in (-1, 1):                                                   # label stops
            cube(P, "cream", M, u + sg * (w / 2 + frame + 0.06) - 0.08, u + sg * (w / 2 + frame + 0.06) + 0.08, 0.0, 0.16, spring - 0.14, spring + 0.02)
        apex = max(zz for _, zz in hood)
        poly_prism(P, "cream", M, [(u - 0.1, apex - 0.28), (u + 0.1, apex - 0.28), (u + 0.14, apex + 0.08), (u - 0.14, apex + 0.08)], 0.0, 0.18)   # keystone


def arch_ring(u, w, spring, width):
    """A U-shaped arch surround (sides + arch) with the opening left open: outer outline then the inner one back."""
    uo0, uo1, ui0, ui1 = u - w / 2 - width, u + w / 2 + width, u - w / 2, u + w / 2
    return ([(uo1, 0.0)] + pointed(uo0, uo1, spring) + [(uo0, 0.0), (ui0, 0.0)] + pointed(ui0, ui1, spring)[::-1] + [(ui1, 0.0)])


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
    if abs(ra[0] - rb[0]) + abs(ra[1] - rb[1]) > 0.5:
        cresting(P, ra[0], ra[1], rb[0], rb[1], ze + ridge_h, 0.4, 0.5)


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
    cube(P, "lilac", I, -14.0, 14.0, 6.0, 44.0, -COURT_Z, 0.0)                              # the raised platform
    cube(P, "base", I, -14.2, 14.2, 5.8, 44.2, -COURT_Z, -COURT_Z + 1.2)
    for k in range(14):                                                                     # the stair inside the gate
        y0 = -0.2 + k * 0.45
        cube(P, "base", I, -1.9, 1.9, y0, 6.2, -COURT_Z, -COURT_Z + (k + 1) * COURT_Z / 14)
    cube(P, "paving", I, -14.0, 14.0, 6.0, 17.0, -0.02, 0.0)
    lathe(P, "base", [(0, 0), (2.4, 0), (2.4, 0.012), (0, 0.012)], 48, T(0.0, 8.0, 0))       # the monogram medallion
    lathe(P, "paving", [(0, 0.012), (2.0, 0.012), (2.0, 0.02), (0, 0.02)], 48, T(0.0, 8.0, 0))
    # arcade of round arches on columns along the left (x = -12), with a roof behind
    cube(P, "lilac", I, -14.0, -11.6, 6.0, 17.0, 0.0, 5.2)
    M = face(-11.6, 6.0, math.pi / 2)                       # face towards +x (inside the courtyard)
    for k in range(4):
        u = 1.5 + k * 2.9
        poly_prism(P, "glass", M, [(u - 1.2, 0.0), (u + 1.2, 0.0)] + round_top(u - 1.2, u + 1.2, 2.6)[1:-1], -0.02, 0.01)
        poly_prism(P, "cream", M, [(u - 1.45, 0.0), (u - 1.2, 0.0)] + [(u - 1.2, 2.6), (u - 1.45, 2.6)], 0.0, 0.4)
        for sg in (-1, 1):
            lathe(P, "cream", [(0, 0), (0.25, 0), (0.22, 0.3), (0.16, 0.4), (0.15, 2.4), (0.25, 2.6), (0, 2.65)], 12, M @ T(u + sg * 1.35, 0.35, 0))
        ring = pointed(u - 1.45, u + 1.45, 2.6)
        poly_prism(P, "cream", M, [(u - 1.45, 2.6)] + round_top(u - 1.45, u + 1.45, 2.6)[1:-1] + [(u + 1.45, 2.6), (u + 1.2, 2.6)]
                   + round_top(u - 1.2, u + 1.2, 2.6)[-2:0:-1] + [(u - 1.2, 2.6)], 0.0, 0.35)
    balustrade(P, M, 0.0, 11.0, 5.2, 0.8)
    for x, y in ((-8.5, 8.0), (5.5, 8.0), (-9.5, 13.5), (9.5, 12.5)):
        lamp_post(P, x, y, 4.0)
    # the right side of the courtyard: a plain wall with blind arches
    cube(P, "lilac", I, 12.0, 14.0, 6.0, 17.0, 0.0, 6.5)
    Mr = face(12.0, 17.0, -math.pi / 2)
    for k in range(3):
        poly_prism(P, "cream", Mr, [(1.5 + k * 3.5 - 1.1, 0.8), (1.5 + k * 3.5 + 1.1, 0.8)] + pointed(1.5 + k * 3.5 - 1.1, 1.5 + k * 3.5 + 1.1, 3.0)[1:-1], 0.0, 0.1)
    # the enchanted rose (the reference film) on a pedestal by the stair, under a glass bell
    lathe(P, "cream", [(0, 0), (0.45, 0), (0.45, 0.2), (0.2, 0.35), (0.16, 0.95), (0.4, 1.05), (0.4, 1.15), (0, 1.15)], 16, T(-9.0, 10.5, 0))
    lathe(P, "gold", [(0, 1.15), (0.34, 1.15), (0.34, 1.22), (0, 1.22)], 20, T(-9.0, 10.5, 0))
    lathe(P, "bell", [(0.3, 1.22), (0.3, 1.75)] + [(0.3 * math.cos(math.pi / 2 * k / 6), 1.75 + 0.3 * math.sin(math.pi / 2 * k / 6)) for k in range(1, 7)], 20, T(-9.0, 10.5, 0))
    lathe(P, "grass", [(0, 1.22), (0.012, 1.22), (0.01, 1.6), (0, 1.6)], 6, T(-9.0, 10.5, 0))
    lathe(P, "rose", [(0, 1.55), (0.07, 1.6), (0.09, 1.68), (0.05, 1.74), (0, 1.73)], 12, T(-9.0, 10.5, 0))


def boulder_cluster(P, x, y, r, h, seed):
    """A heap of angular boulders standing on the ground, filling a mound of radius r and height |h| (h < 0: sunk):
    each block is a low-poly sphere squashed into a stratified slab whose bottom sits on the ground."""
    g = random.Random(seed * 7 + 3)
    n = max(3, int(r * r * 0.8))
    for k in range(n):
        a_ = g.uniform(0, 2 * math.pi); d = r * math.sqrt(g.random()) * 0.9
        bx, by = x + d * math.cos(a_), y + d * math.sin(a_)
        top = max(0.8, abs(h) * (1 - (d / r) ** 2) ** 0.6 * g.uniform(0.75, 1.1))
        br = g.uniform(1.0, 2.0) * max(0.6, min(1.0, r / 3.0))
        base = (h if h < 0 else 0.0) - 0.3
        bm = P["rock"]
        res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        sd = Vector((seed * 3.1 + k, k * 1.7, seed * 0.9))
        rot = Matrix.Rotation(g.uniform(0, 3.14), 3, "Z")
        sx, sy = g.uniform(1.1, 1.7), g.uniform(0.9, 1.3)
        tilt = g.uniform(-0.12, 0.12)
        for v in res["verts"]:
            n_ = v.co.copy()
            f = 1.0 + 0.25 * noise.noise(n_ * 1.5 + sd)
            xy = Vector((n_.x * sx * f, n_.y * sy * f, 0.0))
            z = ((n_.z + 1.0) / 2.0) ** 0.7                          # 0 .. 1 from the ground up (rounded shoulders)
            z = round(z * 4.0) / 4.0 * 0.5 + z * 0.5                 # stratified ledges
            p_ = rot @ (xy * br)
            v.co = Vector((bx + p_.x, by + p_.y, base + z * (top - base) + tilt * p_.x))


def build_rocks(P):
    """Rock masses round the chasm under the bridge and at the castle's foot (noise-displaced blobs)."""
    # (x, y, radius, height): low jagged rocks either side of the bridge (below the deck near it, taller further out),
    # the tall crag with the waterfall on the right, rocks at the feet of the wings
    blobs = [(-7.5, -20.0, 3.5, 0.2), (-8.0, -12.0, 3.0, -0.4), (-9.5, -4.5, 3.2, 1.0), (-15.0, -15.0, 4.5, 1.5), (-14.0, -6.0, 3.5, 2.0),
             (7.5, -21.0, 3.2, 0.3), (8.0, -13.5, 2.8, -0.3), (13.5, -18.0, 4.0, 2.5), (14.0, -8.0, 4.2, 7.5), (10.0, -3.5, 3.0, 5.5),
             (-4.0, -16.0, 2.6, -1.2), (4.0, -10.0, 2.6, -1.2), (-24.0, -1.0, 3.5, 2.5), (25.0, 0.0, 3.5, 3.0)]
    for i, (x, y, r, h) in enumerate(blobs):
        boulder_cluster(P, x, y, r, h, i)
        continue
        bm = P["rock"]
        res = bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
        seed = Vector((i * 3.1, i * 1.7, i * 0.9))
        for v in res["verts"]:
            n = v.co.copy()
            d = 1.0 + 0.3 * noise.noise(n * 1.3 + seed) + 0.12 * noise.noise(n * 3.5 + seed) + 0.05 * noise.noise(n * 9.0 + seed)
            spike = 1.0 + 0.6 * max(0.0, noise.noise(Vector((n.x * 2.2, n.y * 2.2, 0)) + seed))   # jagged crests
            z = max(n.z, -0.25)
            v.co = Vector((x + n.x * r * d, y + n.y * r * d * 0.85, z * abs(h) * d * spike + (h if h < 0 else 0)))
    # the outcrop the palace stands on, seen from the village: big rocks round its right side and back
    for i, (x, y, r, h) in enumerate([(19.0, 12.0, 6.0, 9.0), (21.0, 24.0, 6.5, 12.0), (17.0, 36.0, 6.0, 10.0), (6.0, 41.0, 7.0, 8.0),
                                       (-8.0, 40.0, 6.5, 9.5), (-19.0, 32.0, 6.0, 7.0), (-21.0, 20.0, 5.0, 5.0), (26.0, 4.0, 5.0, 6.0)]):
        boulder_cluster(P, x, y, r, h, i)
        continue
        bm = P["rock"]
        res = bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
        seed = Vector((i * 5.3 + 40, i * 2.1, i * 1.3))
        for v in res["verts"]:
            n = v.co.copy()
            d = 1.0 + 0.32 * noise.noise(n * 1.2 + seed) + 0.14 * noise.noise(n * 3.2 + seed) + 0.05 * noise.noise(n * 8.0 + seed)
            spike = 1.0 + 0.5 * max(0.0, noise.noise(Vector((n.x * 2.0, n.y * 2.0, 0)) + seed))
            v.co = Vector((x + n.x * r * d, y + n.y * r * d, max(n.z, -0.25) * h * d * spike))
    for x, y, z0, z1 in ((26.0, 18.0, 0.0, 6.0), (26.5, 30.0, 0.0, 7.0), (-24.5, 26.0, 0.0, 4.0)):   # waterfalls down the rocks
        cube(P, "water", Matrix.Identity(4), x - 0.08, x + 0.08, y - 0.9, y + 0.9, z0, z1)
    # the chasm floor and a mist-white cascade on the right (the waterfall at the bridge)
    cube(P, "rock", Matrix.Identity(4), -6.0, 6.0, -26.0, -1.0, -4.5, -4.0)
    cube(P, "water", Matrix.Identity(4), 10.6, 10.9, -10.5, -6.5, -4.0, 6.0)                 # the cascade off the crag


# ================================================================ v2 parts (from ~100 photos): tiers, dormers, turrets
def side_frames(x0, x1, y0, y1):
    """Face frames of a rectangular block, each with its length: front (-y), right (+x), back (+y), left (-x)."""
    return [(face(x0, y0, 0.0), x1 - x0), (face(x1, y0, math.pi / 2), y1 - y0),
            (face(x1, y1, math.pi), x1 - x0), (face(x0, y1, -math.pi / 2), y1 - y0)]


def pyramid(P, x, y, z, half, h, mat="roof", finial=True):
    """Steep square roof (a 4-sided cone turned 45 deg) with a cream band under it and a finial."""
    lathe(P, mat, [(0.0, z), (half * 1.414 + 0.15, z), (half * 1.3, z + h * 0.07), (0.05, z + h), (0.0, z + h)], 4, T(x, y, 0) @ R(math.pi / 4, "Z"))
    cube(P, "cream", Matrix.Identity(4), x - half - 0.15, x + half + 0.15, y - half - 0.15, y + half + 0.15, z - 0.4, z)
    if finial:
        lathe(P, "gold", [(0, z + h), (0.07, z + h), (0.04, z + h + 0.4), (0.09, z + h + 0.5), (0.015, z + h + 1.2), (0, z + h + 1.25)], 8, T(x, y, 0))


def ornate_dormer(P, M, u, z0, w=1.6, h=2.6):
    """Baroque dormer (the castle's many cream dormers): pilasters, round-headed window, scrolled sides,
    a broken segmental pediment with a cartouche and a finial."""
    cube(P, "cream", M, u - w / 2, u + w / 2, -0.8, 0.05, z0, z0 + h)                         # body
    window(P, M @ Matrix.Translation((0, 0.06, 0)), u, z0 + 0.35, w * 0.5, h * 0.62, "round", 0.08, sill=False)
    for s in (-1, 1):
        cube(P, "cream", M, u + s * w / 2 - (0.18 if s > 0 else 0), u + s * w / 2 + (0.18 if s < 0 else 0) * 0 + (0.0 if s > 0 else 0.18), 0.05, 0.2, z0, z0 + h)
        sc = [(u + s * (w / 2 + 0.05), z0 + 0.1)] + [(u + s * (w / 2 + 0.05 + 0.45 * math.sin(math.pi * k / 8)), z0 + 0.1 + 0.9 * (1 - math.cos(math.pi * k / 8)) / 2 * 2) for k in range(1, 9)]
        pts = sc + [(u + s * (w / 2 + 0.05), z0 + 1.9)]
        poly_prism(P, "cream", M, pts if s > 0 else pts[::-1], -0.6, 0.0)                         # side scroll
    arc, _ = seg_arc(u, z0 + h, w + 0.5, 0.55, 14)
    band = [(x, z) for x, z in arc] + [(x, z - 0.22) for x, z in arc[::-1]]
    left, right = band[: len(band) // 2], band[len(band) // 2:]
    poly_prism(P, "cream", M, [p for i, p in enumerate(arc) if i < 6] + [(x, z - 0.22) for i, (x, z) in reversed(list(enumerate(arc))) if i < 6], -0.8, 0.15)
    poly_prism(P, "cream", M, [p for i, p in enumerate(arc) if i > 7] + [(x, z - 0.22) for i, (x, z) in reversed(list(enumerate(arc))) if i > 7], -0.8, 0.15)
    lathe(P, "cream", [(0, 0), (0.28, 0), (0.28, 0.1), (0, 0.12)], 10, M @ T(u, 0.16, z0 + h + 0.2) @ R(-math.pi / 2, "X"))   # cartouche
    lathe(P, "gold", [(0, 0), (0.1, 0), (0.07, 0.3), (0.12, 0.4), (0.02, 0.9), (0, 0.95)], 8, M @ T(u, -0.2, z0 + h + 0.45))
    cube(P, "roof", M, u - w / 2 - 0.1, u + w / 2 + 0.1, -2.2, -0.8, z0 + h - 0.2, z0 + h + 0.25)      # its little roof going back


def bartizan(P, x, y, z, r=0.9, h=3.2, roof=3.2):
    """Corbelled corner turret: a cone of corbels, a short round body with a slit window, a steep cone roof."""
    lathe(P, "cream", [(0.0, z - 1.6), (0.25, z - 1.6), (r + 0.1, z - 0.1), (r + 0.1, z), (0.0, z)], 20, T(x, y, 0))
    lathe(P, "lilac", [(0.0, z), (r, z), (r, z + h), (0.0, z + h)], 20, T(x, y, 0))
    lathe(P, "cream", [(0.0, z + h - 0.3), (r + 0.12, z + h - 0.3), (r + 0.12, z + h), (0.0, z + h)], 20, T(x, y, 0))
    cone_roof(P, x, y, z + h, r + 0.2, roof, 20)


def cresting(P, x0, y0, x1, y1, z, step=0.35, h=0.55):
    """Iron cresting along a ridge: spikes with a small ball, one every `step`."""
    L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / step))
    for k in range(n + 1):
        t = k / n; x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        lathe(P, "iron", [(0, 0), (0.025, 0), (0.015, h * 0.6), (0.05, h * 0.68), (0.012, h), (0, h)], 5, T(x, y, z))
    cube(P, "iron", Matrix.Identity(4), min(x0, x1) - 0.02, max(x0, x1) + 0.02, min(y0, y1) - 0.02, max(y0, y1) + 0.02, z, z + 0.06)


def stage(P, x0, x1, y0, y1, z0, z1, rows, sides=(0, 1, 2, 3), spacing=2.1, kind="round", balus=True, glass="glass"):
    """One tier of the palace: lilac block, windows in rows on its faces, a cream cornice and a balustrade."""
    cube(P, "lilac", Matrix.Identity(4), x0, x1, y0, y1, z0, z1)
    cube(P, "cream", Matrix.Identity(4), x0 - 0.25, x1 + 0.25, y0 - 0.25, y1 + 0.25, z1 - 0.45, z1)
    cube(P, "cream", Matrix.Identity(4), x0 - 0.12, x1 + 0.12, y0 - 0.12, y1 + 0.12, z1 - 0.75, z1 - 0.45)
    for (cx, cy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):          # quoins: alternating long / short blocks
        k = 0; zq = z0
        while zq < z1 - 0.9:
            L = 0.7 if k % 2 == 0 else 0.45
            sx = 1 if cx == x0 else -1; sy = 1 if cy == y0 else -1
            cube(P, "cream", Matrix.Identity(4), min(cx, cx + sx * L), max(cx, cx + sx * L), min(cy, cy - sy * 0.06), max(cy, cy - sy * 0.06), zq, zq + 0.4)
            cube(P, "cream", Matrix.Identity(4), min(cx, cx - sx * 0.06), max(cx, cx - sx * 0.06), min(cy, cy + sy * (1.15 - L)), max(cy, cy + sy * (1.15 - L)), zq, zq + 0.4)
            zq += 0.44; k += 1
    for M_, L_ in side_frames(x0, x1, y0, y1):                        # corbel table under the cornice
        k = 0.25
        while k < L_ - 0.2:
            cube(P, "cream", M_, k - 0.08, k + 0.08, 0.0, 0.2, z1 - 1.05, z1 - 0.75)
            k += 0.55
    for (cx, cy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):          # corner pinnacles
        lathe(P, "cream", [(0, 0), (0.22, 0), (0.22, 0.5), (0.12, 0.7), (0.14, 1.0), (0.04, 1.6), (0, 1.65)], 8, T(cx, cy, z1 + (0.85 if balus else 0.0)))
    for i, (M, L) in enumerate(side_frames(x0, x1, y0, y1)):
        if i not in sides:
            continue
        n = max(1, int((L - 0.6) / spacing))
        for zz, hh in rows:
            for k in range(n):
                window(P, M, (k + 0.5) * L / n, z0 + zz, 0.72, hh, kind, 0.11, glass=glass)
        if balus:
            balustrade(P, M @ Matrix.Translation((0, 0.05, 0)), 0.0, L, z1, 0.85)


def gargoyle_lamp(P, x, y, h=5.2):
    """Bridge lamp post: a crouching bronze grotesque on a cream pier, an iron post, a scrolled arm, a lantern."""
    cube(P, "cream", Matrix.Identity(4), x - 0.5, x + 0.5, y - 0.5, y + 0.5, 0.0, 1.1)
    lathe(P, "iron", [(0, 1.1), (0.34, 1.1), (0.4, 1.45), (0.3, 1.9), (0.36, 2.3), (0.22, 2.6), (0, 2.7)], 10, T(x, y, 0))   # the grotesque
    lathe(P, "iron", [(0, 2.35), (0.16, 2.4), (0.18, 2.6), (0, 2.75)], 8, T(x, y - 0.2, 0))
    lathe(P, "iron", [(0, 2.6), (0.09, 2.6), (0.07, h), (0.12, h + 0.1), (0, h + 0.25)], 8, T(x, y, 0))
    cube(P, "iron", Matrix.Identity(4), x - 0.03, x + 0.03, y - 1.0, y, h - 0.35, h - 0.28)
    lathe(P, "lamp", [(0, 0), (0.18, 0.05), (0.22, 0.5), (0.1, 0.65), (0, 0.66)], 8, T(x, y - 1.0, h - 1.05))
    lathe(P, "iron", [(0, 0.62), (0.28, 0.62), (0.06, 0.9), (0, 0.95)], 8, T(x, y - 1.0, h - 1.05))


# ================================================================ the gatehouse (v2)
def build_gatehouse(P):
    I = Matrix.Identity(4); M = face(0, 0, 0)
    # the curved bastion wall either side of the gate (battered base course, dressed top)
    for a, b in ((-7.0, -1.75), (1.75, 7.0)):                                                # the body, with the passage open
        cube(P, "lilac", I, a, b, 0.0, 6.0, 0.0, 9.0)
    cube(P, "lilac", I, -1.75, 1.75, 0.0, 6.0, 5.2, 9.0)
    cube(P, "trim", I, -1.75, 1.75, 0.3, 6.0, 5.05, 5.2)                                       # the passage ceiling
    cube(P, "base", I, -7.2, -1.75, -0.25, 6.2, 0.0, 1.4)
    cube(P, "base", I, 1.75, 7.2, -0.25, 6.2, 0.0, 1.4)
    cube(P, "cream", I, -7.3, 7.3, -0.35, 6.3, 8.6, 9.1)
    # the three pointed openings: the door in the middle, the lion niches either side (statue inside, lamp in front)
    for u, w, spring, deep in ((0.0, 3.4, 2.4, True), (-4.2, 2.2, 2.6, False), (4.2, 2.2, 2.6, False)):
        if deep:                                                # the gate: a moulded ring, the passage open behind it
            poly_prism(P, "cream", M, arch_ring(u, w, spring, 0.45), -0.05, 0.35)
            poly_prism(P, "trim", M, arch_ring(u, w + 0.9, spring + 0.1, 0.2), -0.15, -0.05)
            for k_ in range(9):                                 # voussoirs: joints across the ring
                t = math.pi * (k_ + 0.5) / 9
        else:
            poly_prism(P, "cream", M, [(u - w / 2 - 0.4, 0.0), (u + w / 2 + 0.4, 0.0)] + pointed(u - w / 2 - 0.4, u + w / 2 + 0.4, spring)[1:-1], -0.05, 0.35)
        if not deep:
            poly_prism(P, "glass", M, [(u - w / 2, 1.2), (u + w / 2, 1.2)] + pointed(u - w / 2, u + w / 2, spring)[1:-1], 0.35, 0.36)
        if deep:
            for sg in (-1, 1):                                  # the door leaves stand open against the reveals
                cube(P, "wood", M, sg * 1.7 - 0.12, sg * 1.7 + 0.12, 0.4, 1.9, 0.0, 5.0)
        else:
            lion(P, M @ Matrix.Translation((0, 0.95, 0)), u, 1.2, 0.95)
    # lion-head relief with a crest over the door; a string course; small windows above the niches
    lathe(P, "statue", [(0, 0), (0.6, 0), (0.66, 0.22), (0.5, 0.5), (0, 0.55)], 14, M @ T(0, 0.35, 6.4) @ R(-math.pi / 2, "X"))
    poly_prism(P, "cream", M, [(-1.2, 7.4), (1.2, 7.4), (1.0, 8.6), (0.0, 9.0), (-1.0, 8.6)], -0.2, 0.25)
    cube(P, "cream", M, -7.2, 7.2, -0.3, 0.05, 5.6, 5.85)
    for u in (-4.2, 4.2):
        window(P, M, u, 6.6, 0.75, 1.7, "pointed")
    # the steep rose hip roof with the ornate dormer, cresting on the ridge
    hip_roof(P, -7.3, 7.3, -0.35, 6.3, 9.1, 4.2)
    ornate_dormer(P, M @ Matrix.Translation((0, 1.2, 0)), 0.0, 9.2, 1.9, 2.9)
    cresting(P, -3.2, 3.0, 3.2, 3.0, 13.3)
    # square towers either side with tall rose pyramids; smaller cones at the ends of the gatehouse
    for s in (-1, 1):
        x = s * 7.6
        cube(P, "lilac", I, x - 1.8, x + 1.8, -0.8, 3.0, 0.0, 10.5)
        cube(P, "base", I, x - 1.95, x + 1.95, -0.95, 3.15, 0.0, 1.5)
        cube(P, "cream", I, x - 2.0, x + 2.0, -1.0, 3.2, 10.1, 10.6)
        for k in range(8):                                  # corbel table
            cube(P, "cream", I, x - 1.75 + k * 0.47, x - 1.5 + k * 0.47, -1.0, -0.8, 9.5, 10.1)
        window(P, face(x, -0.8, 0), 0.0, 7.0, 0.7, 1.8, "pointed")
        window(P, face(x, -0.8, 0), 0.0, 3.6, 0.5, 1.3, "pointed")
        pyramid(P, x, 1.1, 10.6, 2.0, 5.8)
        ornate_dormer(P, face(x, -0.1, 0), 0.0, 11.5, 0.9, 1.6)
        bartizan(P, s * 11.2, 1.5, 7.2, 1.0, 3.0, 3.6)
        gargoyle(P, face(s * 9.4, -0.3, 0), 0.0, 9.1, 0.8)


# ================================================================ the palace (v2): round towers + stacked tiers + the keep
def build_palace(P):
    I = Matrix.Identity(4)
    # the grand stair with lion guardians on its cheeks
    for k in range(9):
        cube(P, "base", I, -5.2 + k * 0.1, 5.2 - k * 0.1, 15.8 + k * 0.45, 22.0, 0.0, 0.2 * (k + 1))
    for s in (-1, 1):
        cube(P, "cream", I, s * 5.5 - 0.5, s * 5.5 + 0.5, 15.8, 22.0, 0.0, 1.1)
    # tier 0: the courtyard front between the two round towers (to 11.5 m)
    cube(P, "lilac", I, -8.0, 8.0, 21.5, 34.0, 0.0, 11.5)
    cube(P, "base", I, -8.2, 8.2, 21.3, 34.2, 0.0, 2.6)
    cube(P, "cream", I, -8.3, 8.3, 21.2, 34.3, 2.6, 2.85)
    M = face(0, 21.5, 0)
    # the door: pedimented surround, winged gargoyles on the entablature, lions on pedestals either side
    poly_prism(P, "cream", M, [(x, z + 1.8) for x, z in arch_ring(0.0, 3.0, 2.8, 0.8)], -0.05, 0.4)
    poly_prism(P, "wood", M, [(-1.5, 1.8), (1.5, 1.8)] + pointed(-1.5, 1.5, 4.4)[1:-1], 0.4, 0.46)
    for zz in (2.6, 3.6, 4.6):
        cube(P, "iron", M, -1.4, 1.4, 0.46, 0.49, zz, zz + 0.08)
    cube(P, "cream", M, -3.3, 3.3, -0.2, 0.9, 6.3, 7.0)                                    # entablature
    poly_prism(P, "cream", M, [(-2.6, 7.0), (2.6, 7.0), (0.0, 8.3)], -0.25, 0.2)            # pediment
    lathe(P, "gold", [(0, 0), (0.4, 0), (0.4, 0.08), (0, 0.1)], 6, M @ T(0, 0.22, 7.45) @ R(-math.pi / 2, "X"))
    for s in (-1, 1):
        cube(P, "cream", M, s * 2.9 - 0.45, s * 2.9 + 0.45, -0.3, 0.9, 1.8, 6.3)            # pilasters
        lion(P, M @ Matrix.Translation((0, 1.1, 0)), s * 2.9, 1.8, 1.0)
        gargoyle(P, M @ Matrix.Translation((0, 0.5, 0)), s * 2.9, 7.0, 1.2)
        for u in (s * 5.0, s * 6.6):
            window(P, M, u, 3.6, 0.8, 2.3, "pointed")
            window(P, M, u, 8.2, 0.75, 2.0, "pointed", glass="stained")
    cube(P, "cream", I, -8.4, 8.4, 20.9, 34.4, 11.1, 11.6)
    hip_roof(P, -8.4, 8.4, 20.9, 34.4, 11.6, 4.8)
    for u in (-4.6, 0.0, 4.6):
        ornate_dormer(P, M @ Matrix.Translation((0, 1.4, 0)), u, 11.8, 1.5, 2.6)
    # the two fat round towers at the front corners: rusticated base, corbelled rings, tall windows, cones with dormers
    for s in (-1, 1):
        x, y, r = s * 8.2, 23.0, 3.4
        lathe(P, "base", [(0, 0), (r + 0.3, 0), (r + 0.3, 3.0), (r + 0.1, 3.2), (0, 3.2)], 36, T(x, y, 0))
        lathe(P, "lilac", [(0, 3.0), (r, 3.0), (r, 13.0), (0, 13.0)], 36, T(x, y, 0))
        for zr in (3.1, 7.9):                                                                # moulded rings
            lathe(P, "cream", [(0, zr), (r + 0.35, zr), (r + 0.35, zr + 0.3), (r + 0.15, zr + 0.45), (0, zr + 0.45)], 36, T(x, y, 0))
        lathe(P, "cream", [(0, 11.8), (r + 0.05, 11.8), (r + 0.5, 12.8), (r + 0.5, 13.2), (0, 13.2)], 36, T(x, y, 0))
        for k in range(18):                                                                  # corbels
            t = 2 * math.pi * k / 18
            cube(P, "cream", face(x + r * math.cos(t), y + r * math.sin(t), t + math.pi / 2), -0.13, 0.13, 0.0, 0.35, 11.3, 11.8)
        a0, a1 = (math.pi * 0.95, math.pi * 1.75) if s < 0 else (-math.pi * 0.75, math.pi * 0.05)
        for zz, hh in ((4.2, 2.6), (9.0, 2.2)):
            for k in range(5):
                t = a0 + (a1 - a0) * (k + 0.5) / 5
                window(P, face(x + r * math.cos(t), y + r * math.sin(t), t + math.pi / 2), 0.0, zz, 0.72, hh, "pointed", 0.12)
        cone_roof(P, x, y, 13.2, r + 0.45, 8.0, 36)
        t = -math.pi / 2                                                                      # a dormer on the cone, facing the court
        ornate_dormer(P, face(x + (r - 0.9) * math.cos(t), y + (r - 0.9) * math.sin(t), 0.0), 0.0, 14.0, 1.0, 1.9)
    # tier 1: the main block behind (to 18.5 m): windows all round, balustrade, rose mansard with dormers
    stage(P, -7.0, 7.0, 25.0, 34.0, 11.5, 18.5, ((1.6, 2.2), (4.4, 1.8)))
    hip_roof(P, -7.2, 7.2, 24.8, 34.2, 18.5, 3.4)
    for u in (-3.5, 3.5):
        ornate_dormer(P, face(0, 25.6, 0), u, 18.7, 1.3, 2.3)
    for s in (-1, 1):                                                                        # side pavilions with pyramids
        x = s * 6.2
        stage(P, x - 2.2, x + 2.2, 24.0, 28.4, 11.5, 20.5, ((1.6, 2.2), (5.0, 1.8)), sides=(0, 1 if s > 0 else 3), spacing=2.0, balus=False)
        pyramid(P, x, 26.2, 20.5, 2.25, 7.5)
        ornate_dormer(P, face(x, 23.9, 0), 0.0, 21.4, 1.0, 1.9)
    # tier 2: the upper stage (to 23.5 m) with its balcony and the big dormer (the photos' cream centrepiece)
    stage(P, -4.2, 4.2, 26.0, 33.0, 18.5, 23.5, ((1.5, 2.0),), spacing=1.9)
    hip_roof(P, -4.4, 4.4, 25.8, 33.2, 23.5, 3.2)
    ornate_dormer(P, face(0, 26.3, 0), 0.0, 23.7, 1.8, 3.0)
    cube(P, "cream", I, -3.4, 3.4, 24.9, 26.0, 18.3, 18.6)                                  # balcony slab on corbels
    balustrade(P, face(0, 24.9, 0), -3.4, 3.4, 18.6, 0.9)
    # the keep: slim square tower to 30.5 m, machicolations, crenellations, a small spire; its thin round turret
    kx, ky, k = -1.2, 34.0, 1.65
    stage(P, kx - k, kx + k, ky - k, ky + k, 18.5, 34.4, ((6.4, 1.5), (8.6, 1.4), (10.4, 1.2)), spacing=1.4, balus=False)
    for zz in (24.3, 27.8, 31.2):                                                                   # string courses on the shaft
        cube(P, "cream", I, kx - k - 0.12, kx + k + 0.12, ky - k - 0.12, ky + k + 0.12, zz, zz + 0.22)
    for i in range(7):
        for (a, b), (c, d) in (((kx - k + i * 0.5, kx - k + i * 0.5 + 0.22), (ky - k - 0.35, ky - k)), ((kx - k + i * 0.5, kx - k + i * 0.5 + 0.22), (ky + k, ky + k + 0.35))):
            cube(P, "cream", I, a, b, c, d, 33.9, 34.4)
    cube(P, "cream", I, kx - k - 0.45, kx + k + 0.45, ky - k - 0.45, ky + k + 0.45, 34.4, 34.8)
    cube(P, "lilac", I, kx - k - 0.35, kx + k + 0.35, ky - k - 0.35, ky + k + 0.35, 34.8, 35.6)
    for i in range(4):
        for yy in (ky - k - 0.35, ky + k - 0.05):
            cube(P, "lilac", I, kx - k - 0.35 + i * 1.05, kx - k + 0.15 + i * 1.05, yy, yy + 0.4, 35.6, 36.3)
        for xx in (kx - k - 0.35, kx + k - 0.05):
            cube(P, "lilac", I, xx, xx + 0.4, ky - k - 0.35 + i * 1.05, ky - k + 0.15 + i * 1.05, 35.6, 36.3)
    lathe(P, "lilac", [(0, 34.8), (0.75, 34.8), (0.75, 37.2), (0, 37.2)], 16, T(kx + 0.8, ky - 0.8, 0))   # the little turret on its top
    cone_roof(P, kx + 0.8, ky - 0.8, 37.2, 0.95, 3.2, 16)
    tx, ty = kx - 3.0, ky - 1.2                                                               # the thin round turret
    lathe(P, "lilac", [(0, 18.5), (0.95, 18.5), (0.95, 29.0), (0, 29.0)], 20, T(tx, ty, 0))
    lathe(P, "cream", [(0, 28.6), (1.2, 28.6), (1.2, 29.0), (0, 29.0)], 20, T(tx, ty, 0))
    window(P, face(tx, ty - 0.95, 0), 0.0, 25.5, 0.45, 1.3, "pointed")
    cone_roof(P, tx, ty, 29.0, 1.2, 5.6, 20)
    # a second slender spire tower to the right of the keep, chimneys, bartizans and cresting round the tiers
    sx_, sy_ = 3.1, 29.0
    lathe(P, "lilac", [(0, 22.0), (0.85, 22.0), (0.85, 26.5), (0, 26.5)], 16, T(sx_, sy_, 0))
    cone_roof(P, sx_, sy_, 26.5, 1.05, 4.6, 16)
    for x, y in ((-5.8, 32.5), (5.8, 32.5), (1.8, 33.5)):
        cube(P, "lilac", I, x - 0.45, x + 0.45, y - 0.45, y + 0.45, 18.5, 24.5)
        cube(P, "cream", I, x - 0.6, x + 0.6, y - 0.6, y + 0.6, 24.5, 24.9)
    for x, y, z in ((-7.2, 34.2, 11.5), (7.2, 34.2, 11.5), (-4.4, 25.8, 18.5), (4.4, 25.8, 18.5)):
        bartizan(P, x, y, z, 0.75, 2.4, 2.6)
    cresting(P, -1.4, 29.5, 1.4, 29.5, 21.9)
    cresting(P, -3.0, 16.3 + 12.0, 3.0, 16.3 + 12.0, 16.4)


def build_bridge(P):
    M = Matrix.Identity(4)
    cube(P, "paving", M, -2.4, 2.4, -26.0, -0.5, -0.6, 0.0)
    for s in (-1, 1):
        cube(P, "lilac", M, s * 2.4 - 0.35, s * 2.4 + 0.35, -26.0, -0.5, -0.6, 1.0)
        cube(P, "cream", M, s * 2.4 - 0.45, s * 2.4 + 0.45, -26.0, -0.5, 1.0, 1.18)
        for yy in (-24.0, -18.0, -12.0, -6.0):                                              # square piers with pyramidal caps
            cube(P, "cream", M, s * 2.4 - 0.62, s * 2.4 + 0.62, yy - 0.62, yy + 0.62, -0.6, 1.5)
            lathe(P, "cream", [(0, 1.5), (0.95, 1.5), (0.1, 2.1), (0, 2.1)], 4, T(s * 2.4, yy, 0) @ R(math.pi / 4, "Z"))
        for yy in (-21.0, -9.0, -2.4):
            gargoyle_lamp(P, s * 3.3, yy, 5.4)
    for k in range(3):
        y0, y1 = -24.0 + k * 8.0, -17.0 + k * 8.0
        pts, _ = seg_arc((y0 + y1) / 2, -4.0, y1 - y0, 1.8, 14)
        poly_prism(P, "lilac", face(-2.4, 0, math.pi / 2), [(-(y1), -0.6), (-(y0), -0.6), (-y0, -4.0)] + [(-u, z) for u, z in pts[::-1]] + [(-y1, -4.0)], 0.0, 4.8)


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
        fn(P); P.flush(name, PALACE_DY if name == "palace" else 0.0)
    SCALE = scale()
    B.root.scale = (SCALE, SCALE, SCALE)                # uniform: the photos' proportions stay, the door sets the size
    bpy.context.view_layer.update()
    print(f"[bb] scale {SCALE:.3f} (door {DOOR_H} m)")
    uv_project([o for o in B.col.objects if o.type == "MESH" and o.data.materials and
                o.data.materials[0].name in ("bb_lilac", "bb_base", "bb_roof", "bb_paving", "bb_rock")])
    if context:
        ctx = bpy.data.collections.new("Context"); sc.collection.children.link(ctx)
        old = B.col; B.col = ctx
        box("CTX_ground", (-80, 80, -60, 90, -0.3, -0.02), "ground_ctx")
        B.col = old
    print(f"[bb] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")


CAMS = {
    "bridge": ((0.0, -21.0, 1.6), (0.0, 12.0, 17.5), 19),         # the photos from the queue (wide angle, on the deck)
    "front": ((-10.0, -40.0, 3.0), (0.0, 12.0, 16.0), 24),
    "courtyard": ((0.0, 7.2, 3.6), (0.0, 20.0, 15.0), 14),
    "keep": ((22.0, 10.0, 3.0), (2.0, 30.0, 22.0), 24),
    "village": ((40.0, 58.0, 2.0), (0.0, 22.0, 20.0), 26),         # from the Gaston side, over the rocks
    "aerial": ((55.0, -50.0, 55.0), (0.0, 15.0, 8.0), 30),
    "rose": ((-7.8, 9.3, 1.7), (-9.0, 10.5, 1.5), 50),
}


def export_objects(merged):
    """For the mock: the castle in the DisneySea frame (gate at the OSM point, turned by ANG), heights on the datum,
    one mesh per material ("BC_<material>") with plain colours / image textures glTF can carry."""
    global WEB
    WEB = True
    build(context=False)
    import ds_tracks
    h = ds_tracks.make_ground(ds_tracks.data())
    gz = h(*GATE)
    B.root.location = (GATE[0], GATE[1], gz); B.root.rotation_euler = (0, 0, math.radians(ANG))
    bpy.context.view_layer.update()
    for mat in bpy.data.materials:                       # keep image textures, flatten procedural colour chains
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
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith("CAM_"):
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if mats:
            groups.setdefault(mats[0].name, []).append((o, 0.0))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    res = []
    for k, parts in sorted(groups.items()):
        ob = merged("BC_" + k[3:], parts, out)
        ob.data.materials.clear(); ob.data.materials.append(bpy.data.materials[k])
        res.append(ob)
    print(f"[bb] export ground {gz:.2f} m")
    return res


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
        loc, tgt = Vector(loc) * scale(), Vector(tgt) * scale()
        co.location = loc; co.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
        cams[n] = co
    bpy.context.scene.camera = cams["bridge"]
    ST.frame_view()
    for scr in bpy.data.screens:
        for area in scr.areas:
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.region_3d.view_location = (0.0, 12.0, 10.0); sp.region_3d.view_distance = 85.0
                    sp.shading.color_type = "TEXTURE"                  # the blockwork and tiles show in Solid view too
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
