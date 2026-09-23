"""Tokyo DisneySea - water pass for Blender 5.2.

  python ds_water.py                                            # 1) water model -> JSON
  blender -b --python disneysea_water_blender.py -- --cams harbor,caldera --samples 48

Builds the draft scene (buildings, landmarks, greenery, paths, railway from the
ds_* modules) but replaces the draft's flat ground + water slabs with the
water model in plateau_data/disneysea_water.json:
  - ground slab with every open water body (incl. ponds) cut as a hole;
    tunnel stretches under Mysterious Island stay covered
  - water as a closed volume (glass-like surface, absorption, ripple bump)
    at each body's freeboard below the promenade, over a mud bed
  - shores by type: quay (stone wall + coping), building (wet foundation),
    rock (irregular rockwork bank), beach (sand slope), bank (planted slope)
  - piers (deck + piles)
The scene ground is flat (promenade = 0), so water sits at -freeboard; the
DEM-based absolute levels are in the JSON for the mock.
"""
import sys, math, json, time, random, argparse, pathlib, importlib

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import bpy, bmesh
from mathutils import Vector

OUT = ROOT / "output" / "disneysea" / "water"
WATER_JSON = ROOT / "plateau_data" / "disneysea_water.json"
GROUND_DEPTH = 5.0

CAMERAS = {  # name -> (position, look-at, lens mm)
    "top":        ((-180, 60, 2100), (-180, 61, 0), 40),
    "aerial":     ((-60, -1150, 720), (-200, 40, 0), 32),
    "harbor":     ((175, -10, 16), (40, -70, -1), 24),
    "caldera":    ((-20, -8, 30), (-68, -42, -2), 22),
    "american":   ((100, -200, 18), (140, -345, -1), 24),
    "rock":       ((55, -335, 4), (75, -372, 0), 22),
    "lost_river": ((-320, -150, 12), (-335, -20, -1), 24),
    "fantasy":    ((-610, 130, 130), (-650, 255, 0), 30),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="harbor,caldera,american,rock,lost_river,fantasy,aerial,top")
    ap.add_argument("--render", default="yes", choices=["yes", "none"])
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1600x900")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--sky", type=float, default=0.035)
    ap.add_argument("--no-context", action="store_true", help="water only, no buildings")
    return ap.parse_args(argv)


# ---------------------------------------------------------------- materials
def _principled(mat):
    return mat.node_tree.nodes.get("Principled BSDF")


def mat_water(name, color, absorb, density, rough=0.03):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = _principled(mat)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = 1.333
    b.inputs["Transmission Weight"].default_value = 0.8   # a little diffuse: park water is murky green
    # ripples: large slow swell (wave) + fine chop (noise), in object space
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.9
    noise.inputs["Detail"].default_value = 8
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 0.12
    wave.inputs["Distortion"].default_value = 6
    wave.inputs["Detail"].default_value = 4
    mix = nt.nodes.new("ShaderNodeMath"); mix.operation = "ADD"
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.04
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], mix.inputs[0])
    nt.links.new(wave.outputs["Fac"], mix.inputs[1])
    nt.links.new(mix.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    vol = nt.nodes.new("ShaderNodeVolumeAbsorption")
    vol.inputs["Color"].default_value = (*absorb, 1)
    vol.inputs["Density"].default_value = density
    out = nt.nodes.get("Material Output")
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    mat.diffuse_color = (*color, 1)
    return mat


def mat_textured(name, c1, c2, scale, rough=0.9, bump=0.4, kind="noise"):
    """Two-tone procedural surface (stone, rock, sand, mud) with a matching bump."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = _principled(mat)
    b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "brick":
        tex = nt.nodes.new("ShaderNodeTexBrick")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Color1"].default_value = (*c1, 1)
        tex.inputs["Color2"].default_value = (*c2, 1)
        tex.inputs["Mortar"].default_value = (c2[0] * .6, c2[1] * .6, c2[2] * .6, 1)
        tex.inputs["Mortar Size"].default_value = 0.015
        tex.offset = 0.5
        nt.links.new(tc.outputs["Object"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        fac = tex.outputs["Fac"]
    else:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = 10
        tex.inputs["Roughness"].default_value = 0.65
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*c1, 1)
        ramp.color_ramp.elements[1].color = (*c2, 1)
        nt.links.new(tc.outputs["Object"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        fac = tex.outputs["Fac"]
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    nt.links.new(fac, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mat.diffuse_color = (*c1, 1)
    return mat


def materials():
    return {
        "water": mat_water("mat_harbor_water", (0.05, 0.17, 0.15), (0.35, 0.62, 0.55), 0.45),
        "pool": mat_water("mat_pool_water", (0.05, 0.15, 0.18), (0.45, 0.75, 0.80), 0.35),
        "bed": mat_textured("mat_water_bed", (0.07, 0.08, 0.06), (0.14, 0.13, 0.10), 0.6, 1.0, 0.2),
        "pool_bed": mat_textured("mat_pool_bed", (0.25, 0.42, 0.50), (0.35, 0.52, 0.58), 3.0, 0.6, 0.1),
        "quay": mat_textured("mat_quay_stone", (0.58, 0.52, 0.44), (0.46, 0.41, 0.35), 1.6, 0.85, 0.3, "brick"),
        "coping": mat_textured("mat_coping", (0.76, 0.72, 0.64), (0.66, 0.62, 0.55), 2.0, 0.7, 0.15),
        "wet": mat_textured("mat_wet_foundation", (0.22, 0.21, 0.18), (0.32, 0.30, 0.26), 2.5, 0.35, 0.2),
        "rock": mat_textured("mat_rockwork", (0.44, 0.33, 0.25), (0.62, 0.50, 0.40), 0.35, 0.95, 1.2),
        "sand": mat_textured("mat_sand_bank", (0.78, 0.68, 0.50), (0.66, 0.56, 0.40), 1.2, 0.95, 0.2),
        "grass": mat_textured("mat_bank_grass", (0.20, 0.32, 0.13), (0.30, 0.40, 0.18), 1.5, 0.95, 0.3),
        "mud": mat_textured("mat_bank_mud", (0.20, 0.17, 0.12), (0.28, 0.24, 0.17), 1.5, 0.8, 0.3),
        "ground": mat_textured("mat_promenade", (0.62, 0.57, 0.49), (0.70, 0.65, 0.57), 0.8, 0.9, 0.08),
        "deck": mat_textured("mat_pier_deck", (0.38, 0.27, 0.18), (0.30, 0.21, 0.14), 6.0, 0.8, 0.2),
    }


# ---------------------------------------------------------------- geometry helpers
def mesh_obj(name, verts, faces, mat, col):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    col.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = False
    return obj


def resample(line, step):
    """Polyline -> points every ~step m (keeps the corners)."""
    out = [tuple(line[0])]
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        k = max(1, int(L / step))
        for j in range(1, k + 1):
            out.append((x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k))
    return out


def normals_left(pts):
    """Unit normals pointing to the LEFT of travel (= towards the water)."""
    ns = []
    n = len(pts)
    for i in range(n):
        ax, ay = pts[max(0, i - 1)]
        bx, by = pts[min(n - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1.0
        ns.append((-dy / L, dx / L))
    return ns


def strip(name, pts, rows, mat, col, jitter=None):
    """Surface across a shoreline. rows = [(offset towards water m, z), ...]
    ordered from land to water; jitter(i, r) -> (d_offset, dz) for rockwork."""
    ns = normals_left(pts)
    verts, faces = [], []
    R = len(rows)
    for i, ((x, y), (nx, ny)) in enumerate(zip(pts, ns)):
        for r, (off, z) in enumerate(rows):
            do, dz = jitter(i, r) if jitter else (0.0, 0.0)
            verts.append((x + nx * (off + do), y + ny * (off + do), z + dz))
    for i in range(len(pts) - 1):
        for r in range(R - 1):
            a = i * R + r
            faces.append((a, a + 1, a + R + 1, a + R))
    return mesh_obj(name, verts, faces, mat, col)


def cut_slab(name, outer, holes, mat, col, C):
    """Ground slab with water holes via an exact boolean (tessellating one
    polygon with dozens of holes leaves sliver gaps)."""
    slab = C.extrude_loops(name, [outer], -GROUND_DEPTH, GROUND_DEPTH, mat, cap_bottom=True)
    col.objects.link(slab)
    if not holes:
        return slab
    bm = bmesh.new()
    for h in holes:
        o = C.extrude_loops("tmp_cut", [h], -GROUND_DEPTH - 1, GROUND_DEPTH + 2, mat, cap_bottom=True)
        if o:
            tmp = bmesh.new(); tmp.from_mesh(o.data)
            me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me); bpy.data.meshes.remove(o.data)
    cme = bpy.data.meshes.new(name + "_cutter")
    bm.to_mesh(cme); bm.free()
    cutter = bpy.data.objects.new(name + "_cutter", cme)
    col.objects.link(cutter)
    mod = slab.modifiers.new("water_holes", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    for solver in ("EXACT", "MANIFOLD", "FLOAT"):
        try:
            mod.solver = solver
            break
        except TypeError:
            continue
    dg = bpy.context.evaluated_depsgraph_get()
    new_me = bpy.data.meshes.new_from_object(slab.evaluated_get(dg))
    slab.modifiers.remove(mod)
    old = slab.data
    slab.data = new_me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter)
    bpy.data.meshes.remove(cme)
    return slab


# ---------------------------------------------------------------- build
def build_water(W, M, C):
    col_g = C.get_collection("Terrain")
    col_w = C.get_collection("Water")
    col_s = C.get_collection("Shores")
    bodies = W["bodies"]

    # which island (inner ring of a cut body) contains each other body?
    islands = []  # (ring, [hole rings])
    for b in bodies:
        if b["cut"]:
            for isl in b["inners"]:
                islands.append((isl, []))
    main_holes = []
    for b in bodies:
        cx, cy = C.poly_centroid(b["ring"])
        home = next((h for isl, h in islands if C.point_in_poly(cx, cy, isl)), None)
        (home if home is not None else main_holes).append(b["ring"])

    cut_slab("Ground", C.PARK, main_holes, M["ground"], col_g, C)
    for i, (isl, holes) in enumerate(islands):
        cut_slab(f"Island_{i}", isl, holes, M["ground"], col_g, C)

    stats = {"bodies": 0, "failed": []}
    for b in bodies:
        pool = b["kind"] in ("fountain",)
        zw = -b["freeboard"]
        zb = zw - b["depth"]
        loops = [b["ring"]] + b["inners"]
        o = C.extrude_loops(f"Water_{b['id']}", loops, zb, zw - zb - 0.002, M["pool" if pool else "water"], cap_bottom=True)
        bed = C.extrude_loops(f"Bed_{b['id']}", loops, zb - 0.3, 0.3, M["pool_bed" if pool else "bed"], cap_bottom=False)
        if o:
            col_w.objects.link(o); stats["bodies"] += 1
        else:
            stats["failed"].append(b["id"])
        if bed:
            col_w.objects.link(bed)

    rnd = random.Random(7)
    counts = {}
    for k, s in enumerate(W["shores"]):
        b = bodies[s["b"]]
        zw, t = -b["freeboard"], s["t"]
        zb = zw - b["depth"]
        pts = resample(s["l"], 1.5 if t == "rock" else 3.0)
        if len(pts) < 2:
            continue
        name = f"Shore_{t}_{k}"
        if t in ("quay", "portal"):
            # vertical dressed-stone wall face just in front of the ground edge + coping stones
            strip(name, pts, [(0.02, 0.0), (0.02, zb)], M["quay"], col_s)
            strip(name + "_coping", pts, [(-0.45, 0.14), (0.05, 0.14), (0.05, 0.0)], M["coping"], col_s)
            strip(name + "_wetline", pts, [(0.03, zw + 0.25), (0.03, zw - 0.05)], M["wet"], col_s)
        elif t == "building":
            strip(name, pts, [(0.03, 0.0), (0.03, zb)], M["wet"], col_s)
        elif t == "rock":
            H = [rnd.uniform(0.2, 1.6) for _ in pts]
            jit = lambda i, r: (rnd.uniform(-0.5, 0.5) if r else 0.0, rnd.uniform(-0.2, 0.3) if r in (1, 2) else 0.0)
            strip(name, pts, [(-1.2, 0.02), (-0.4, 0.02), (0.4, zw + 0.3), (1.5, zw - 0.3), (2.8, zb)],
                  M["rock"], col_s, jitter=lambda i, r: (jit(i, r)[0], jit(i, r)[1] + (H[i] if r == 1 else 0.0)))
        elif t == "beach":
            strip(name, pts, [(-3.0, 0.02), (0.0, zw + 0.02), (5.0, zw - 0.6), (8.0, zb)], M["sand"], col_s)
        elif t == "bank":
            strip(name, pts, [(-1.0, 0.02), (0.3, zw + 0.08)], M["grass"], col_s)
            strip(name + "_mud", pts, [(0.3, zw + 0.08), (2.0, zw - 0.5), (3.0, zb)], M["mud"], col_s)
        counts[t] = counts.get(t, 0) + 1

    col_p = C.get_collection("Piers")
    for p in W["piers"]:
        o = C.extrude_loops(f"Pier_{p['id']}", [p["ring"]], -0.25, 0.3, M["deck"], cap_bottom=True)
        if o:
            col_p.objects.link(o)
        for i, (x, y) in enumerate(resample(p["ring"] + [p["ring"][0]], 3.0)):
            sq = [(x - .15, y - .15), (x + .15, y - .15), (x + .15, y + .15), (x - .15, y + .15)]
            pile = C.extrude_loops(f"Pile_{p['id']}_{i}", [sq], -3.5, 3.3, M["wet"])
            if pile:
                col_p.objects.link(pile)
    print(f"[water] bodies={stats['bodies']} failed={stats['failed']} shores={counts} piers={len(W['piers'])}")


def build_context(C):
    """Everything else from the draft except its ground and water."""
    import ds_terrain as T, ds_buildings, ds_landmarks
    T._plan_water()
    T.build_greenery()
    T.build_rockwork()
    T.build_paths()
    # overlapping path ribbons lie in one plane and occlude each other's light
    # rays (renders as black blotches) -> paths do not cast shadow / bounce light
    for o in C.get_collection("Paths").objects:
        o.visible_shadow = False
        o.visible_diffuse = False
    T.build_railway()
    ds_buildings.build_buildings()
    ds_landmarks.build_all()
    mat = C.flat_material("mat_context", (0.22, 0.23, 0.22), roughness=1.0)
    sq = [(-2200, -2000), (1800, -2000), (1800, 2000), (-2200, 2000)]
    C.link(C.extrude_loops("Context_Ground", [sq, C.PARK], -3.3, 3.2, mat), C.get_collection("Context"))


def setup(args):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "MULTIPLE_SCATTERING"
    except TypeError:
        pass
    sky.sun_elevation = math.radians(38)
    sky.sun_rotation = math.radians(200)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = args.sky
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.transmission_bounces = 8
    scene.cycles.volume_bounces = 0
    scene.cycles.caustics_refractive = False
    scene.cycles.caustics_reflective = False
    w, h = (int(v) for v in args.res.split("x"))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = args.percent
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"


def add_camera(name, pos, target, lens):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.3
    cam.clip_end = 6000
    obj = bpy.data.objects.new(f"Cam_{name}", cam)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    return obj


def main():
    args = parse_args()
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for m in ("ds_core", "ds_terrain", "ds_buildings", "ds_landmarks"):
        if m in sys.modules:
            importlib.reload(sys.modules[m])
    import ds_core as C
    W = json.loads(WATER_JSON.read_text(encoding="utf-8"))
    M = materials()
    build_water(W, M, C)
    if not args.no_context:
        build_context(C)
    print(f"[water] build {time.time() - t0:.1f}s objects={len(bpy.data.objects)}")
    setup(args)
    cams = {n: add_camera(n, *v) for n, v in CAMERAS.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "disneysea_water.blend"))
    print(f"[water] saved {OUT / 'disneysea_water.blend'}")
    if args.render == "yes":
        for name in [c.strip() for c in args.cams.split(",") if c.strip()]:
            if name not in cams:
                print(f"[water] unknown camera {name!r}; choices: {', '.join(cams)}")
                continue
            t1 = time.time()
            bpy.context.scene.camera = cams[name]
            bpy.context.scene.render.filepath = str(OUT / f"water_{name}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[water] rendered {name} in {time.time() - t1:.1f}s", flush=True)
    print(f"[water] total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
