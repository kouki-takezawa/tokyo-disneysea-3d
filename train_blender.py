"""Disney Resort Line train in Blender 5.2 -- same shape and numbers as the JS model (output/disneysea/train_model.js).

  blender -b --python train_blender.py -- --out output/disneysea/models/train_head.glb             # one head car
  blender -b --python train_blender.py -- --cars train --out output/disneysea/models/train.glb      # the 6-car set
  blender -b --python train_blender.py -- --cars head --scheme purple --render output/train_head.png

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
  inside   floor, ceiling, long benches, bogies, roof units (the JS model's detailed cabin is still TODO here)
"""
import sys, math, argparse, pathlib
import bpy, bmesh

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
    mod = ob.modifiers.new("thickness", "SOLIDIFY")   # a real skin for the booleans (JS draws a single sheet)
    mod.thickness = 0.06
    mod.offset = -1
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
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
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


# ---------------------------------------------------------------- one car / the set
def build_car(name, L, head, M):
    body = car_body(name, L, head)
    body.data.materials.append(M["paint"])
    cut(body, window_cutters(L, head))
    f, c = SPEC["floor"], SPEC["ceil"]
    Li = L - SPEC["rake"] - 0.05 if head else L
    box(f"{name}_floor", (Li - 0.1, 2.9, 0.06), (Li / 2, 0, f - 0.03), M["floor"], body)
    box(f"{name}_ceiling", (Li - 0.1, 2.7, 0.05), (Li / 2, 0, c + 0.02), M["ceil"], body)
    for side in (-1, 1):                       # long benches between the doors
        x0, x1 = 3.2, (8.4 if head else 10.5)
        box(f"{name}_bench{side}", (x1 - x0, 0.56, 0.55), ((x0 + x1) / 2, side * 1.13, f + 0.28), M["seat"], body)
        box(f"{name}_back{side}", (x1 - x0, 0.13, 0.42), ((x0 + x1) / 2, side * 1.38, f + 0.72), M["seat"], body)
    for bx in (2.7, L - 2.7):                  # bogies
        box(f"{name}_bogie{bx:.0f}", (2.6, 1.0, 0.14), (bx, 0, f - 0.12), M["dark"], body)
    for x in (2.5, L * 0.5 + 1.2, L - (4.2 if head else 2.5)):   # roof units
        box(f"{name}_roofunit{x:.0f}", (1.6, 1.0, 0.16), (x, 0, SPEC["y_top"] + 0.06), M["roof"], body)
    if head:                                   # windscreen glass + headlights
        box(f"{name}_windscreen", (SPEC["rake"] - 0.1, 2.0, 1.4), (L - SPEC["rake"] / 2 + 0.05, 0, 2.925), M["glass"], body)
        for side in (-1, 1):
            box(f"{name}_lamp{side}", (0.05, 0.4, 0.24), (L + 0.01, side * 0.74, 1.28), M["lamp"], body)
    return body


def build(cars="head", scheme="blue"):
    M = {"paint": paint_material(scheme), "floor": material("floor", (0.85, 0.71, 0.25), 0.7),
         "ceil": material("ceiling", (0.96, 0.94, 0.89), 0.7, emit=0.4), "seat": material("seat", (0.23, 0.23, 0.25), 0.8),
         "dark": material("dark", (0.14, 0.15, 0.17), 0.6, 0.3), "roof": material("roof_unit", (0.84, 0.85, 0.87), 0.6),
         "glass": material("glass", (0.06, 0.10, 0.14), 0.05, 0.1, alpha=0.5), "lamp": material("lamp", (1.0, 0.98, 0.9), 0.3, emit=6.0)}
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
