"""Disney Resort Line train in Blender 5.2 -- same shape and numbers as the JS model (output/disneysea/train_model.js).

  blender -b --python src/train_blender.py -- --out output/disneysea/models/train_head.glb             # one head car
  blender -b --python src/train_blender.py -- --cars train --out output/disneysea/models/train.glb      # the 6-car set
  blender -b --python src/train_blender.py -- --cars head --scheme purple --render output/train_head.png

NOT YET RUN IN BLENDER (written on a machine without it; tools/blender_smoke.py imports it with a stub bpy and checks
that SPEC matches train_model.js). Local metres, +X = travel direction (nose at +X), Z up (the glTF exporter turns it
to Y up), beam top z = 0. Sources and estimates: docs/train/spec.md.

  body     loft of rounded-rectangle sections like skinGeometry(): full section, then the raked windscreen over the last
           `rake` m (the roof drops to `wind_bot` at the nose) and the last `nose_len` m rounded in plan and at the chin;
           the bottom stays open (the beam runs under it)
  windows  boolean cutters: tall Mickey heads (oval face + two ears), the long oval observation window on the head car,
           oval windows in the doors, and the windscreen (rounded rectangle in the raked part)
  paint    one material: white body, silver skirt below 0.55 m, the scheme colour band with a wavy top edge (object
           coordinates -> math nodes, the same formula as the JS shader), dark rubber round the windscreen is a separate
           frame object
  inside   v2 (2026-09-24, from the Type C photos): checkered floor, ceiling light strips, red end walls with glass
           gangway doors, black benches with red wavy backrests and yellow dots, round clear partitions with red balls,
           white poles, ceiling rails with Mickey-ring straps, LCDs over the doors; head car: glass cab partition,
           driver's desk with screens, magenta observation sofa
  outside  v2: glass in every window, door seams and sills, louvred skirt vents and panel lines, roof units with
           grilles, raked windscreen pane with a centre pillar, round headlights with rims, coupler; straddle bogies
           (dual running tyres on the beam top, guide and stabilising wheels, side frames, power collectors)
"""
import sys, math, argparse, pathlib
import bpy, bmesh
from mathutils import Vector, Matrix

# keep in sync with S in output/disneysea/train_model.js (tools/blender_smoke.py compares them)
SPEC = dict(head_len=15.05, mid_len=13.70, width=2.98, gap=0.55, cars=6,
            y_bot=-0.9, y_top=3.95, roof_r=1.1, nose_len=0.9, rake=2.1, wind_bot=2.05, floor=1.0, ceil=3.18)
SCHEMES = {"blue": ((0.184, 0.498, 0.839), (0.612, 0.788, 0.949)), "yellow": ((0.949, 0.710, 0.110), (0.984, 0.882, 0.541)),
           "purple": ((0.541, 0.310, 0.753), (0.788, 0.651, 0.902)), "green": ((0.247, 0.639, 0.302), (0.647, 0.851, 0.627)),
           "peach": ((0.941, 0.541, 0.478), (0.973, 0.784, 0.741))}


# ---------------------------------------------------------------- body
def section(w, z0, z1, rt, rb, n=10):
    hw = w / 2
    rt = min(rt, hw, (z1 - z0) / 2)
    rb = min(rb, hw, (z1 - z0) / 2)
    pts = []

    def arc(cy, cz, r, a0, a1):
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    arc(hw - rt, z1 - rt, rt, 0, math.pi / 2)
    arc(-hw + rt, z1 - rt, rt, math.pi / 2, math.pi)
    arc(-hw + rb, z0 + rb, rb, math.pi, 1.5 * math.pi)
    arc(hw - rb, z0 + rb, rb, 1.5 * math.pi, 2 * math.pi)
    return pts


def sections(L, head, N=12):
    """(x, width, top, bottom, roof radius) along the car, as skinGeometry() in train_model.js."""
    S = SPEC
    w0, Ln, R = S["width"], S["nose_len"], S["rake"]
    secs = [(0.0, w0, S["y_top"], S["y_bot"], S["roof_r"]), (L - R if head else L, w0, S["y_top"], S["y_bot"], S["roof_r"])]
    if head:
        xs = [L - R + (R - Ln) * i / (N // 2) for i in range(1, N // 2 + 1)]
        xs += [L - Ln + Ln * math.sin(i / N * math.pi / 2) for i in range(1, N + 1)]
        for x in xs:
            t = (x - (L - R)) / R
            e = 1 - math.cos(math.asin(min(1.0, (x - (L - Ln)) / Ln))) if x > L - Ln else 0.0
            secs.append((x, w0 - 0.9 * e, S["y_top"] - (S["y_top"] - S["wind_bot"]) * t, S["y_bot"] + 0.95 * e, S["roof_r"] - 0.7 * e))
    return secs


def car_body(name, L, head):
    n = 10
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for y, z in section(w, bot, top, rt, 0.18, n)] for x, w, top, bot, rt in sections(L, head)]
    P, skip = 4 * (n + 1), 3 * n + 2          # segment `skip` is the flat bottom: left open (the beam runs under the car)
    for a, b in zip(rings, rings[1:]):
        for i in range(P):
            if i == skip:
                continue
            j = (i + 1) % P
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if head:
        bm.faces.new(rings[-1])               # flat front face below the windscreen
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    mod = ob.modifiers.new("thickness", "SOLIDIFY")   # a real skin: the window holes get deep reveals
    mod.thickness = 0.10
    mod.offset = -1
    mod.material_offset = 1                            # inner face and the reveals: the cabin wall material
    mod.material_offset_rim = 1
    return ob


# ---------------------------------------------------------------- cutters (window openings)
def _ellipse_cutter(x, z, ry, rz, y_side, depth=0.5):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.0, depth=depth, location=(x, y_side, z), rotation=(math.pi / 2, 0, 0))
    c = bpy.context.object
    c.scale = (ry, rz, 1.0)                    # the cylinder's local x/y become the window's width / height
    return c


def window_cutters(L, head):
    """Mickey heads (face 0.34 x 0.44 + ears r 0.19), observation window, door windows: sideHole() in train_model.js."""
    hw, out = SPEC["width"] / 2, []
    doors = [1.95, L - 5.6 if head else L - 1.95]
    for side in (-1, 1):
        y = side * hw
        for i in range(3 if head else 4):
            cx, cz = 3.9 + 1.9 * i, 2.35
            out += [_ellipse_cutter(cx, cz, 0.34, 0.44, y), _ellipse_cutter(cx - 0.36, cz + 0.46, 0.19, 0.19, y),
                    _ellipse_cutter(cx + 0.36, cz + 0.46, 0.19, 0.19, y)]
        if head:
            out.append(_ellipse_cutter(12.35, 2.4, 0.9, 0.55, y))
        for d in doors:
            out += [_ellipse_cutter(d - 0.4, 2.3, 0.22, 0.6, y), _ellipse_cutter(d + 0.4, 2.3, 0.22, 0.6, y)]
    if head:   # windscreen: frontSd() = rounded rectangle z = 2.2..3.65, |y| < 1.0, in the raked part
        bpy.ops.mesh.primitive_cube_add(size=1, location=(L - SPEC["rake"] / 2 + 0.5, 0, 2.925))
        c = bpy.context.object
        c.scale = (SPEC["rake"] + 1.0, 2.0, 1.45)
        bev = c.modifiers.new("round", "BEVEL")
        bev.width, bev.segments = 0.25, 4
        out.append(c)
    for c in out:
        c.hide_render = True
        c.display_type = "WIRE"
    return out


def cut(body, cutters):
    for i, c in enumerate(cutters):
        m = body.modifiers.new(f"cut{i}", "BOOLEAN")
        m.operation, m.object, m.solver = "DIFFERENCE", c, "EXACT"
        c.parent = body                          # the cutters are in car coordinates: they move with the car


# ---------------------------------------------------------------- materials
def paint_material(scheme):
    """White body, silver skirt, colour band with the wavy top edge of the JS shader:
       wv = sin(1.7 u) * 0.10 + sin(0.83 u + 1) * 0.05, band from 0.55 to 1.45 + wv, light band up to + 0.2 + wv / 2."""
    a, b = SCHEMES[scheme]
    m = bpy.data.materials.new(f"paint_{scheme}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.34
    bsdf.inputs["Coat Weight"].default_value = 0.7
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def math_node(op, x, y=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for k, v in enumerate((x, y)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = v
            else:
                nt.links.new(v, n.inputs[k])
        return n.outputs[0]
    u, z = sep.outputs["X"], sep.outputs["Z"]
    wv = math_node("ADD", math_node("MULTIPLY", math_node("SINE", math_node("MULTIPLY", u, 1.7)), 0.10),
                   math_node("MULTIPLY", math_node("SINE", math_node("ADD", math_node("MULTIPLY", u, 0.83), 1.0)), 0.05))
    yA = math_node("ADD", wv, 1.45)
    yB = math_node("ADD", math_node("ADD", yA, 0.2), math_node("MULTIPLY", wv, 0.5))
    below = lambda lim: math_node("LESS_THAN", z, lim)

    def mix(fac, c_true, c_false):
        n = nt.nodes.new("ShaderNodeMix")
        n.data_type = "RGBA"
        nt.links.new(fac, n.inputs["Factor"])
        for sock, c in ((n.inputs[6], c_false), (n.inputs[7], c_true)):
            if isinstance(c, tuple):
                sock.default_value = (*c, 1.0)
            else:
                nt.links.new(c, sock)
        return n.outputs[2]
    col = mix(below(yB), b, (0.93, 0.94, 0.95))
    col = mix(below(yA), a, col)
    col = mix(below(0.55), (0.66, 0.69, 0.72), col)
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m


def material(name, color, rough=0.6, metal=0.0, alpha=1.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1:                               # see-through in Cycles and in EEVEE / Material Preview
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except (AttributeError, TypeError):
                pass
        m.diffuse_color = (*color, alpha)
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1.0)
        b.inputs["Emission Strength"].default_value = emit
    return m


def box(name, size, loc, mat, parent):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name, o.scale = name, size
    o.data.materials.append(mat)
    o.parent = parent
    return o


# ---------------------------------------------------------------- detail parts (one bmesh per material, v2)
# v2 (2026-09-24): photos of the Type C cars (Wikimedia Commons, see docs/train/spec.md) and how a straddle-type
# (Alweg / Hitachi) monorail is built: rubber running tyres on the beam top, guide wheels on the beam sides, a pair
# of stabilising wheels lower down, the power collector on the side of the beam, a skirt hiding all of it.
def _v(x, y, z):
    return Vector((x, y, z))


def _cube(bm, cx, cy, cz, sx, sy, sz, M=None):
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    for v in vs:
        p = _v(v.co.x * sx, v.co.y * sy, v.co.z * sz)
        v.co = (M @ p if M is not None else p) + _v(cx, cy, cz)


def _cyl(bm, r, h, M, segs=16, r2=None):
    """Cylinder (cone) along local Z, centred, placed by the 4x4 matrix M."""
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h, matrix=M)


def _sphere(bm, r, M, u=8, v=6):
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r, matrix=M)


def _torus(bm, R, r, M, seg=12, rseg=4):
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            ring.append(bm.verts.new(M @ _v((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        rings.append(ring)
    for i in range(seg):
        for j in range(rseg):
            a, b = rings[i], rings[(i + 1) % seg]
            bm.faces.new((a[j], b[j], b[(j + 1) % rseg], a[(j + 1) % rseg]))


def _prism_xz(bm, pts, y0, y1):
    """Polygon in (x, z) extruded along y."""
    v0 = [bm.verts.new((x, y0, z)) for x, z in pts]; v1 = [bm.verts.new((x, y1, z)) for x, z in pts]
    bm.faces.new(v0[::-1]); bm.faces.new(v1)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((v0[i], v0[j], v1[j], v1[i]))


def _T(x, y, z):
    return Matrix.Translation((x, y, z))


def _R(a, axis):
    return Matrix.Rotation(a, 4, axis)


def _S(x, y, z):
    return Matrix.Diagonal((x, y, z, 1.0))


def _flush(parts, name, parent):
    """One child object per material from the per-material bmeshes."""
    for k, (bm, mat) in parts.items():
        if not bm.verts:
            bm.free(); continue
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"{name}_{k}"); bm.to_mesh(me); bm.free()
        me.materials.append(mat)
        o = bpy.data.objects.new(f"{name}_{k}", me); bpy.context.collection.objects.link(o); o.parent = parent


# ---------------------------------------------------------------- one car / the set
def build_car(name, L, head, M):
    S = SPEC; hw = S["width"] / 2; f, c = S["floor"], S["ceil"]
    body = car_body(name, L, head)
    body.data.materials.append(M["paint"]); body.data.materials.append(M["cabin"])   # outside / inside + window reveals
    cut(body, window_cutters(L, head))
    P = {k: (bmesh.new(), M[k]) for k in M if k != "paint"}
    bm = lambda k: P[k][0]
    doors = [1.95, L - 5.6 if head else L - 1.95]
    x_in0 = 0.3                                   # cabin: from the rear end wall ...
    x_in1 = L - 3.6 if head else L - 0.3          # ... to the cab partition (head) / the front end wall
    # ---- glass in every window opening (the same ellipses as the cutters), set in the middle of the thick skin
    for side in (-1, 1):
        y = side * (hw - 0.05)
        wins = []
        for i in range(3 if head else 4):
            cx, cz = 3.9 + 1.9 * i, 2.35
            wins += [(cx, cz, 0.34, 0.44), (cx - 0.36, cz + 0.46, 0.19, 0.19), (cx + 0.36, cz + 0.46, 0.19, 0.19)]
        if head:
            wins.append((12.35, 2.4, 0.9, 0.55))
        for d in doors:
            wins += [(d - 0.4, 2.3, 0.22, 0.6), (d + 0.4, 2.3, 0.22, 0.6)]
        for k, (x, z, ry, rz) in enumerate(wins):
            _cyl(bm("glass"), 1.0, 0.012, _T(x, y + side * 0.002 * (k % 3), z) @ _R(math.pi / 2, "X") @ _S(ry + 0.03, rz + 0.03, 1.0), 24)
        # ---- doors: leaf seam, frame, sills (dark lines on the white skin, as in the photos)
        for d in doors:
            yo = side * (hw + 0.004)
            for dx, w in ((0.0, 0.03), (-0.78, 0.035), (0.78, 0.035)):
                _cube(bm("dark"), d + dx, yo, 1.9, w, 0.012, 1.9)
            _cube(bm("dark"), d, yo, 0.97, 1.6, 0.012, 0.03)
            _cube(bm("steel"), d, side * (hw + 0.02), 0.93, 1.6, 0.05, 0.04)     # door sill plate
        # ---- skirt: two round louvred vents, access-panel lines, lower edge trim
        for vx in (L * 0.28, L * 0.72):
            _cyl(bm("vent"), 0.27, 0.02, _T(vx, side * (hw + 0.006), 0.12) @ _R(math.pi / 2, "X"), 24)
            for k in range(7):
                zz = 0.12 - 0.18 + k * 0.06
                half = math.sqrt(max(0.0, 0.25 ** 2 - (zz - 0.12) ** 2))
                if half > 0.03:
                    _cube(bm("dark"), vx, side * (hw + 0.018), zz, 2 * half, 0.012, 0.018)
        for px in [x for x in (1.0, L / 2 - 0.2, L - 1.0)]:
            _cube(bm("dark"), px, side * (hw + 0.004), -0.2, 0.012, 0.012, 1.3)
        _cube(bm("vent"), L / 2, side * (hw + 0.01), -0.86, L - 0.6, 0.03, 0.06)
    # ---- roof: air-conditioning units (rounded), grilles; an antenna on the head car
    for x in (2.5, L * 0.5 + 1.2, L - (4.2 if head else 2.5)):
        _cube(bm("roof"), x, 0, S["y_top"] + 0.1, 1.7, 1.1, 0.2)
        for k in range(5):
            _cube(bm("dark"), x - 0.6 + 0.3 * k, 0, S["y_top"] + 0.205, 0.12, 0.9, 0.012)
    if head:
        _cyl(bm("dark"), 0.02, 0.35, _T(L - 4.0, 0.4, S["y_top"] + 0.17))
    # ---- head car front: windscreen pane along the rake, centre pillar, round headlights, coupler, dark recess
    if head:
        R_, wb, yt = S["rake"], S["wind_bot"], S["y_top"]
        zr = lambda x: yt - (yt - wb) * (x - (L - R_)) / R_          # the raked surface
        x0, x1 = L - R_ + 0.15, L - 0.15
        a = math.atan2(zr(x0) - zr(x1), x1 - x0)
        mid = _v((x0 + x1) / 2, 0, (zr(x0) + zr(x1)) / 2 - 0.06)
        span = math.hypot(x1 - x0, zr(x0) - zr(x1))
        Mw = _T(*mid) @ _R(a, "Y")
        _cube(bm("glass"), 0, 0, 0, span, 2.05, 0.012, Mw)
        _cube(bm("rubber"), 0, 0, 0, span, 0.06, 0.03, Mw @ _T(0, 0, 0.07))    # centre pillar (emergency door frame)
        for s in (-1, 1):
            _cyl(bm("lamp"), 0.15, 0.04, _T(L + 0.01, s * 0.74, 1.28) @ _R(math.pi / 2, "Y"), 20)
            _torus(bm("steel"), 0.165, 0.025, _T(L + 0.02, s * 0.74, 1.28) @ _R(math.pi / 2, "Y"), 20, 4)
        _cube(bm("dark"), L - 0.01, 0, 0.35, 0.04, 1.3, 0.55)                  # recess round the coupler
        _cyl(bm("steel"), 0.1, 0.5, _T(L + 0.15, 0, 0.25) @ _R(math.pi / 2, "Y"), 12)
        _cube(bm("dark"), L + 0.42, 0, 0.25, 0.08, 0.36, 0.26)                 # coupler head
        _cube(bm("dark"), L + 0.01, 0, 0.72, 0.03, 0.5, 0.05)                  # number plate strip
    # ---- bogies (straddle type): frame, dual running tyres on the beam top, guide + stabilising wheels, collectors
    bw = 0.85
    for bx in (2.7, L - 2.7):
        _cube(bm("dark"), bx, 0, f - 0.14, 2.6, 1.1, 0.14)
        for dx in (-0.85, 0.85):
            for ty in (-0.19, 0.19):
                _cyl(bm("rubber"), 0.44, 0.3, _T(bx + dx, ty, 0.44) @ _R(math.pi / 2, "X"), 20)
                _cyl(bm("steel"), 0.2, 0.32, _T(bx + dx, ty, 0.44) @ _R(math.pi / 2, "X"), 10)
        for s in (-1, 1):
            _cube(bm("dark"), bx, s * (bw / 2 + 0.42), -0.2, 2.5, 0.12, 1.0)   # side frame
            for dx in (-0.8, 0.8):
                _cyl(bm("rubber"), 0.2, 0.26, _T(bx + dx, s * (bw / 2 + 0.2), -0.2), 14)      # guide wheels (upper)
                _cyl(bm("rubber"), 0.16, 0.22, _T(bx + dx, s * (bw / 2 + 0.17), -0.7), 12)    # stabilising wheels (lower)
            _cube(bm("steel"), bx, s * (bw / 2 + 0.07), -0.85, 0.5, 0.06, 0.1)              # current collector shoe
    # ---- interior: checkered floor, ceiling with light strips, end walls
    tile = 0.5
    nx, ny = int((x_in1 - x_in0) / tile) + 1, 6
    for i in range(nx):
        for j in range(ny):
            xa, ya = x_in0 + i * tile, -1.4 + j * (2.8 / ny)
            xb = min(xa + tile, x_in1)
            if xb <= xa:
                continue
            _cube(bm("floor_a" if (i + j) % 2 == 0 else "floor_b"), (xa + xb) / 2, ya + 1.4 / ny, f - 0.01, xb - xa, 2.8 / ny, 0.02)
    _cube(bm("ceiling"), (x_in0 + x_in1) / 2, 0, c + 0.02, x_in1 - x_in0, 2.6, 0.04)
    for s in (-1, 1):
        _cube(bm("light"), (x_in0 + x_in1) / 2, s * 0.55, c - 0.005, x_in1 - x_in0 - 0.6, 0.12, 0.02)
    ends = [(x_in0, 1)] + ([] if head else [(x_in1, -1)])
    for xe, d in ends:                           # red end walls round the gangway door (glass)
        for ya, yb in ((-1.36, -0.5), (0.5, 1.36)):   # inside the skin: the roof curves in above 2.85 m
            _cube(bm("red_wall"), xe, (ya + yb) / 2, (f + 2.85) / 2, 0.08, yb - ya, 2.85 - f)
        _cube(bm("red_wall"), xe, 0, (f + 2.1 + c) / 2, 0.08, 1.0, c - f - 2.1)
        for ya, yb in ((-1.25, -0.5), (0.5, 1.25)):
            _cube(bm("red_wall"), xe, (ya + yb) / 2, (2.85 + c) / 2, 0.08, yb - ya, c - 2.85)
        _cube(bm("glass"), xe, 0, f + 1.05, 0.015, 1.0, 2.1)
        for yy in (-0.5, 0.5):
            _cube(bm("steel"), xe, yy, f + 1.05, 0.1, 0.05, 2.1)
    # ---- long benches between the doors: black cushion, red wavy backrest with yellow dots, glow under the seat,
    #      round clear partitions with red balls at both ends, white poles; the photos' Type C seats
    b0, b1 = doors[0] + 0.85, doors[1] - 0.85
    import random
    rnd = random.Random(7 if head else 3)
    for s in (-1, 1):
        _cube(bm("seat"), (b0 + b1) / 2, s * 1.1, f + 0.44, b1 - b0, 0.5, 0.12)
        _cube(bm("dark"), (b0 + b1) / 2, s * 1.22, f + 0.19, b1 - b0 - 0.1, 0.3, 0.38)
        _cube(bm("light"), (b0 + b1) / 2, s * 1.07, f + 0.37, b1 - b0 - 0.2, 0.02, 0.012)
        n = max(2, int((b1 - b0) / 0.46))
        top = [(b1, f + 0.5)] + [(b1 - (b1 - b0) * k / (n * 6), f + 0.95 + 0.07 * abs(math.sin(math.pi * k / 6))) for k in range(n * 6 + 1)] + [(b0, f + 0.5)]
        _prism_xz(bm("seat_back"), top, s * 1.33, s * 1.41) if s > 0 else _prism_xz(bm("seat_back"), top, s * 1.41, s * 1.33)
        for k in range(int((b1 - b0) * 3.2)):     # yellow polka dots on the backrest
            dx, dz, r = b0 + 0.1 + rnd.random() * (b1 - b0 - 0.2), f + 0.58 + rnd.random() * 0.3, 0.035 + rnd.random() * 0.05
            _cyl(bm("dots"), r, 0.01, _T(dx, s * 1.325, dz) @ _R(math.pi / 2, "X"), 12)
        for xe in (b0 - 0.08, b1 + 0.08):         # the round clear partitions
            M_ = _T(xe, s * 1.02, f + 0.72) @ _R(math.pi / 2, "Y")
            _torus(bm("pole"), 0.34, 0.025, M_, 20, 5)
            _cyl(bm("partition"), 0.33, 0.012, M_, 20)
            for zz, yy in ((f + 1.06, s * 1.02), (f + 0.38, s * 1.02), (f + 0.72, s * 0.68)):
                _sphere(bm("ball"), 0.045, _T(xe, yy, zz))
            _cyl(bm("pole"), 0.02, c - f - 1.06, _T(xe, s * 1.02, (f + 1.06 + c) / 2), 8)
    for d in doors:                               # grab poles beside the doors, red balls
        for dx in (-0.95, 0.95):
            for s in (-1, 1):
                _cyl(bm("pole"), 0.02, c - f, _T(d + dx, s * 1.3, (f + c) / 2), 8)
                for zz in (f + 0.9, f + 1.7):
                    _sphere(bm("ball"), 0.04, _T(d + dx, s * 1.3, zz))
        for s in (-1, 1):                         # LCD above each door, inside
            _cube(bm("lcd"), d, s * 1.3, c - 0.2, 1.0, 0.06, 0.22)
            _cube(bm("screen"), d, s * 1.265, c - 0.2, 0.9, 0.01, 0.17)
    # ---- ceiling rails and hand straps: yellow band, red ball, black Mickey ring
    for s in (-1, 1):
        _cyl(bm("pole"), 0.018, x_in1 - x_in0 - 0.4, _T((x_in0 + x_in1) / 2, s * 0.72, c - 0.12) @ _R(math.pi / 2, "Y"), 8)
        xs = b0 + 0.3
        while xs < b1 - 0.2:
            _cube(bm("strap"), xs, s * 0.72, c - 0.3, 0.03, 0.012, 0.32)
            _sphere(bm("ball"), 0.035, _T(xs, s * 0.72, c - 0.47), 6, 4)
            Mr = _T(xs, s * 0.72, c - 0.6) @ _R(math.pi / 2, "X")
            _torus(bm("ring"), 0.085, 0.012, Mr, 10, 3)
            for ex in (-0.075, 0.075):
                _torus(bm("ring"), 0.042, 0.01, _T(xs + ex, s * 0.72, c - 0.52) @ _R(math.pi / 2, "X"), 6, 3)
            xs += 0.62
    # ---- head car: glass cab partition, driver's desk with screens, observation sofa (magenta with yellow dots)
    if head:
        xp = x_in1
        _cube(bm("glass"), xp, 0, (f + c) / 2, 0.015, 2.6, c - f)
        for yy in (-1.3, -0.45, 0.45, 1.3):
            _cube(bm("rubber"), xp, yy, (f + c) / 2, 0.06, 0.06, c - f)
        _cube(bm("rubber"), xp, 0, f + 1.1, 0.06, 2.7, 0.05)
        for i in range(int((L - 0.4 - xp) / tile) + 1):
            for j in range(ny):
                xa, ya = xp + i * tile, -1.4 + j * (2.8 / ny)
                xb = min(xa + tile, L - 0.6)
                if xb > xa:
                    _cube(bm("floor_a" if (i + j) % 2 == 0 else "floor_b"), (xa + xb) / 2, ya + 1.4 / ny, f - 0.01, xb - xa, 2.8 / ny, 0.02)
        _cube(bm("rubber"), L - 1.55, 0.55, f + 0.45, 0.8, 1.0, 0.9)            # driver's desk
        Md = _T(L - 1.35, 0.55, f + 0.98) @ _R(-0.5, "Y")
        _cube(bm("lcd"), 0, 0, 0, 0.5, 0.9, 0.04, Md)
        for yy in (0.33, 0.77):
            _cube(bm("screen"), L - 1.42, yy, f + 1.02, 0.02, 0.3, 0.18)
        _cube(bm("rubber"), L - 2.35, 1.25, f + 0.9, 0.3, 0.3, 1.8)             # tall switch panel
        _cube(bm("magenta"), L - 2.5, -0.95, f + 0.25, 1.4, 0.8, 0.5)           # observation sofa
        _cube(bm("magenta"), L - 2.5, -1.3, f + 0.7, 1.4, 0.18, 0.5)
        for k in range(10):
            _cyl(bm("dots"), 0.05 + rnd.random() * 0.04, 0.01, _T(L - 3.1 + rnd.random() * 1.2, -1.205, f + 0.55 + rnd.random() * 0.3) @ _R(math.pi / 2, "X"), 12)
    _flush(P, name, body)
    return body


def gangway(name, M):
    """Bellows between two cars: a slightly smaller open tube with ribs."""
    g = car_body(name, SPEC["gap"] + 0.04, False)
    g.scale = (1.0, 0.94, 0.94)
    g.data.materials.append(M["bellows"]); g.data.materials.append(M["bellows"])
    return g


def materials(scheme="blue"):
    return {"paint": paint_material(scheme),
            "cabin": material("cabin", (0.93, 0.92, 0.88), 0.5),
            "floor_a": material("floor_a", (0.80, 0.74, 0.60), 0.6), "floor_b": material("floor_b", (0.55, 0.52, 0.45), 0.6),
            "ceiling": material("ceiling", (0.95, 0.95, 0.93), 0.6, emit=0.3), "light": material("light", (1.0, 0.98, 0.92), 0.3, emit=5.0),
            "seat": material("seat", (0.04, 0.04, 0.045), 0.8), "seat_back": material("seat_back", (0.72, 0.05, 0.04), 0.7),
            "dots": material("dots", (0.96, 0.78, 0.14), 0.6), "magenta": material("magenta", (0.80, 0.07, 0.32), 0.7),
            "pole": material("pole", (0.93, 0.93, 0.92), 0.3), "ball": material("ball", (0.85, 0.08, 0.04), 0.3),
            "strap": material("strap", (0.96, 0.74, 0.05), 0.6), "ring": material("ring", (0.02, 0.02, 0.02), 0.25),
            "red_wall": material("red_wall", (0.70, 0.07, 0.05), 0.6), "partition": material("partition", (0.93, 0.93, 0.95), 0.2, alpha=0.55),
            "lcd": material("lcd", (0.03, 0.03, 0.035), 0.4), "screen": material("screen", (0.25, 0.65, 0.95), 0.3, emit=2.0),
            "steel": material("steel", (0.78, 0.80, 0.82), 0.3, 0.9), "vent": material("vent", (0.45, 0.47, 0.50), 0.5, 0.4),
            "dark": material("dark", (0.14, 0.15, 0.17), 0.6, 0.3), "rubber": material("rubber", (0.03, 0.03, 0.03), 0.8),
            "roof": material("roof_unit", (0.84, 0.85, 0.87), 0.6),
            "glass": material("glass", (0.10, 0.14, 0.18), 0.03, 0.1, alpha=0.35), "lamp": material("lamp", (1.0, 0.98, 0.9), 0.3, emit=6.0),
            "bellows": material("bellows", (0.23, 0.24, 0.26), 0.85)}


def build(cars="head", scheme="blue"):
    M = materials(scheme)
    if cars == "head":
        return [build_car("Head", SPEC["head_len"], True, M)]
    out, x = [], 0.0
    lens = [SPEC["head_len"]] + [SPEC["mid_len"]] * (SPEC["cars"] - 2) + [SPEC["head_len"]]
    for i, L in enumerate(lens):
        head = i in (0, len(lens) - 1)
        o = build_car(f"Car{i}", L, head, M)
        if i == 0:                              # the rear head car faces -X, like train_model.js
            o.rotation_euler = (0, 0, math.pi)
            o.location.x = x + L
        else:
            o.location.x = x
        out.append(o)
        if i < len(lens) - 1:                   # bellows to the next car
            g = gangway(f"Gang{i}", M); g.location.x = x + L - 0.02; out.append(g)
        x += L + SPEC["gap"]
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="train_head.glb")
    ap.add_argument("--cars", default="head", choices=["head", "train"])
    ap.add_argument("--scheme", default="blue", choices=list(SCHEMES))
    ap.add_argument("--render", default="", help="also render a check image to this PNG")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = build(a.cars, a.scheme)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        for ch in o.children:
            ch.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(pathlib.Path(a.out)), export_format="GLB", use_selection=True, export_apply=True)
    print("[train] wrote", a.out)
    if a.render:
        cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        bpy.context.scene.collection.objects.link(cam)
        cam.location = (SPEC["head_len"] + 9, 7, 3.5)
        cam.rotation_euler = (math.radians(78), 0, math.radians(125))
        bpy.context.scene.camera = cam
        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
        bpy.context.scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(40), 0, math.radians(30))
        bpy.context.scene.render.filepath = str(pathlib.Path(a.render).resolve())
        bpy.ops.render.render(write_still=True)
        print("[train] rendered", a.render)


if __name__ == "__main__":
    main()
