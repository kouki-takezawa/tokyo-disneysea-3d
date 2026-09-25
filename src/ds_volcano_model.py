"""Mount Prometheus as a detailed rock massif (Blender 5.2), from the ds_volcano heightfield.

  python src/ds_volcano.py                                           # heightfield (plain Python)
  blender -b --python src/export_models.py -- --parts volcano         # mock model
  blender -b --python src/export_models.py -- --parts volcano --render

ds_volcano gives a 2 m grid: the Mysterious Island plateau (~5.3 m above the
promenade, from the DEM) and the rock ring around the caldera lagoon (summit
51 m). Here it becomes a sculpted mesh:
  resolution  resampled to STEP m (bilinear) over the plateau plus a thin margin
  crags       ridged multifractal noise, strongest on high steep rock
  strata      soft terraces every STRATA m (ledges and overhang-like bands)
  cliffs      plateau edges drop to the promenade, the lagoon edge drops into
              the water (the heightfield leaves the lagoon empty)
  crater      a bowl at the summit
  colour      per-vertex (so the mock shows the same): layered red-brown /
              dark basalt / ochre bands, darker on steep faces, dusty on ledges,
              scorched round the crater; the plateau floor (walkways) sandy
Heights are relative to the DEM datum, like the mock (no lifting needed).
"""
import json, math, pathlib, random
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "plateau_data" / "disneysea_volcano.json"

STEP = 0.6            # m
STRATA = 1.8          # m between rock layers
MARGIN = 3.0          # m of promenade kept around the plateau (the cliff foot)
LAGOON_FLOOR = -1.6   # where the rock meets the lagoon (water -1.24)


def _bilinear(grid, nx, ny, fx, fy):
    i0 = max(0, min(nx - 2, int(fx))); j0 = max(0, min(ny - 2, int(fy)))
    tx, ty = min(1, max(0, fx - i0)), min(1, max(0, fy - j0))
    a = grid[j0 * nx + i0]; b = grid[j0 * nx + i0 + 1]
    c = grid[(j0 + 1) * nx + i0]; d = grid[(j0 + 1) * nx + i0 + 1]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def build(col=None, step=STEP):
    import bpy, bmesh
    from mathutils import Vector, noise
    V = json.loads(SRC.read_text(encoding="utf-8"))
    nx, ny, st, x0, y0 = V["nx"], V["ny"], V["step"], V["x0"], V["y0"]
    raw = V["z"]
    lag = [1.0 if v is None else 0.0 for v in raw]
    zg = [LAGOON_FLOOR if v is None else v for v in raw]
    hg = V["h"]
    plat = [1.0 if (v is not None and v > 0.5) or v is None else 0.0 for v in raw]
    for _ in range(2):   # round the 2 m staircase of the plateau outline before resampling
        nxt = plat[:]
        for j in range(1, ny - 1):
            for i in range(1, nx - 1):
                nxt[j * nx + i] = sum(plat[(j + dj) * nx + i + di] for dj in (-1, 0, 1) for di in (-1, 0, 1)) / 9.0
        plat = nxt
    sx, sy = V["summit"]["x"], V["summit"]["y"]

    W = int((nx - 1) * st / step) + 1
    H = int((ny - 1) * st / step) + 1
    pos, col_rgb, keep = [], [], []
    for j in range(H):
        for i in range(W):
            fx, fy = i * step / st, j * step / st
            x, y = x0 + i * step, y0 + j * step
            p = _bilinear(plat, nx, ny, fx, fy)
            z = _bilinear(zg, nx, ny, fx, fy)
            h = _bilinear(hg, nx, ny, fx, fy)
            lg = _bilinear(lag, nx, ny, fx, fy)
            # sharpen the soft bilinear edges into cliffs: plateau edge and lagoon edge
            if p < 0.5:
                z = -0.3 if lg < 0.5 else LAGOON_FLOOR   # cliff foot tucked just under the promenade
            elif lg > 0.35:
                z = LAGOON_FLOOR
            rockw = min(1.0, h / 3.0)
            if rockw > 0:
                # break the smooth cone/rim: domain-warped large forms -> buttresses, gullies, sub-peaks
                wx = x + 12.0 * noise.noise(Vector((x * 0.012, y * 0.012, 3.1)))
                wy = y + 12.0 * noise.noise(Vector((x * 0.012, y * 0.012, 7.7)))
                big = noise.ridged_multi_fractal(Vector((wx * 0.022, wy * 0.022, 0.0)), 0.9, 2.0, 4, 1.0, 2.0)
                crag = noise.ridged_multi_fractal(Vector((wx * 0.06, wy * 0.06, 0.0)), 1.0, 2.1, 5, 1.0, 2.0)
                fine = noise.fractal(Vector((x * 0.25, y * 0.25, z * 0.25)), 0.6, 2.0, 4)
                z += rockw * (0.22 * min(h, 45.0) * (big - 0.9) + (0.7 + 0.05 * min(h, 30.0)) * (crag - 0.9) + 0.35 * fine)
                # strata: soft terraces whose spacing wanders with the rock
                th = STRATA * (1.0 + 0.45 * noise.noise(Vector((x * 0.02, y * 0.02, 1.3))))
                layer = z / th
                frac = layer - math.floor(layer)
                terr = (math.floor(layer) + frac ** 3) * th
                z = z + rockw * 0.45 * (terr - z)
            dsum = math.hypot(x - sx, y - sy)
            if dsum < 7.0 and h > 20:
                z -= 6.0 * (1 - dsum / 7.0) ** 1.5                                    # summit crater
            pos.append((x, y, z))
            keep.append(p > 0.02 or _bilinear(plat, nx, ny, fx, fy) > 0 or any(
                _bilinear(plat, nx, ny, fx + dx, fy + dy) > 0.5 for dx, dy in ((MARGIN / st, 0), (-MARGIN / st, 0), (0, MARGIN / st), (0, -MARGIN / st))))
            col_rgb.append((h, rockw, dsum, lg))

    # per-vertex colour from layers, slope and features
    def slope(i, j):
        a = pos[j * W + max(0, i - 1)][2]; b = pos[j * W + min(W - 1, i + 1)][2]
        c = pos[max(0, j - 1) * W + i][2]; d = pos[min(H - 1, j + 1) * W + i][2]
        gx, gy = (b - a) / (2 * step), (d - c) / (2 * step)
        return math.atan(math.hypot(gx, gy))
    RED, DARK, OCHRE = (0.31, 0.17, 0.11), (0.17, 0.14, 0.13), (0.50, 0.35, 0.22)
    SAND, DUST, SCORCH = (0.56, 0.49, 0.40), (0.46, 0.40, 0.31), (0.09, 0.07, 0.07)
    mix = lambda a, b, t: tuple(a[k] * (1 - t) + b[k] * t for k in range(3))
    colors = []
    rnd = random.Random(11)
    for j in range(H):
        for i in range(W):
            x, y, z = pos[j * W + i]
            h, rockw, dsum, lg = col_rgb[j * W + i]
            s = slope(i, j)
            band = 0.5 + 0.5 * math.sin(z * 1.3 + 6.0 * noise.noise(Vector((x * 0.025, y * 0.025, z * 0.04))))
            rock = mix(RED, OCHRE, 0.6 * band ** 2 + 0.2 * (0.5 + 0.5 * noise.noise(Vector((x * 0.1, y * 0.1, z * 0.1)))))
            rock = mix(rock, DARK, max(0.0, noise.noise(Vector((x * 0.08, y * 0.08, z * 0.3)))) * 1.2)
            if s > math.radians(55):
                rock = tuple(c * 0.72 for c in rock)                     # shadowed cliff faces
            elif s < math.radians(22) and h > 2:
                rock = mix(rock, DUST, 0.45)                             # dusty ledges
            if dsum < 12 and h > 18:
                rock = mix(rock, SCORCH, max(0.0, 1 - dsum / 12) ** 0.8)
            c = mix(SAND, rock, rockw) if lg < 0.5 else DARK
            j_ = rnd.uniform(0.94, 1.06)
            colors.append(tuple(min(1, v * j_) for v in c))

    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in pos]
    cl = bm.loops.layers.color.new("Col")
    for j in range(H - 1):
        for i in range(W - 1):
            ids = (j * W + i, j * W + i + 1, (j + 1) * W + i + 1, (j + 1) * W + i)
            if not all(keep[k] for k in ids):
                continue
            f = bm.faces.new([verts[k] for k in ids])
            for loop, k in zip(f.loops, ids):
                loop[cl] = (*colors[k], 1.0)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    me = bpy.data.meshes.new("VO_Rock"); bm.to_mesh(me); bm.free()
    ca = me.color_attributes["Col"]            # make it the active/render colour (glTF COLOR_0)
    me.color_attributes.active_color = ca
    me.color_attributes.render_color_index = me.color_attributes.find("Col")
    for p in me.polygons:
        p.use_smooth = True
    obj = bpy.data.objects.new("VO_Rock", me)
    obj.data.materials.append(_material())
    (col or bpy.context.scene.collection).objects.link(obj)
    print(f"[volcano] rock mesh {W}x{H} @ {step} m: {len(me.vertices)} verts, {len(me.polygons)} faces")
    return obj


def _material():
    import bpy
    mat = bpy.data.materials.get("mat_vo_rock") or bpy.data.materials.new("mat_vo_rock")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 0.92
    at = nt.nodes.new("ShaderNodeVertexColor"); at.layer_name = "Col"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6; nz.inputs["Detail"].default_value = 12
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 0.8
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
    mx.inputs["Factor"].default_value = 0.35
    nt.links.new(at.outputs["Color"], mx.inputs["A"])
    nt.links.new(nz.outputs["Color"], mx.inputs["B"])
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    nt.links.new(nz.outputs["Fac"], add.inputs[0]); nt.links.new(vo.outputs["Distance"], add.inputs[1])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.8; bp.inputs["Distance"].default_value = 0.15
    nt.links.new(add.outputs["Value"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    mat.diffuse_color = (0.35, 0.22, 0.15, 1)
    return mat
