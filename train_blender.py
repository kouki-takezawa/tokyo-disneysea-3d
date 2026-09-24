"""Disney Resort Line (Type X) head car in Blender 5.2 -- DRAFT, not yet run in Blender.

  blender -b --python train_blender.py -- --out output/disneysea/models/train_head.glb

Same numbers as output/disneysea/train.html (see docs/train/spec.md; keep the two in sync).
Local metres, +X = travel direction, Z up (the glTF exporter converts to Y up). Beam top is z = 0.
Body = loft of rounded-rectangle sections (bmesh) with a tapered nose; the Mickey-head windows are cut with
booleans so that they are recessed.

NOTE: this draft still has the first prototype's shape (streamlined 3.4 m nose, round Mickey windows).
The JS model was rebuilt from reference photos on 2026-09-24 (boxy nose with three windscreen panes, tall
Mickey windows, white body + colour band + silver skirt, full interior): follow docs/train/spec.md and
output/disneysea/train.html (skinGeometry / sideHole / frontHole / interior) when finishing this in Blender.
"""
import sys, math, argparse, pathlib
import bpy, bmesh

SPEC = dict(head_len=15.05, mid_len=13.70, width=2.98, nose_len=3.4, bottom=0.62, top=3.95, roof_r=1.15,
            beam_w=0.85, color=(0.84, 0.86, 0.88, 1.0))   # white body; the colour band / skirt are TODO (see docs/train/spec.md)


def section(w, z0, z1, rt, rb, n=8):
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


def car_body(L, nose_front, nose_rear):
    S, Ln, N = SPEC, SPEC["nose_len"], 14

    def nose(t):
        return dict(w=S["width"] * (0.62 + 0.38 * math.sqrt(max(0, 1 - t * t))), top=S["top"] - 0.95 * t ** 2.1,
                    bot=S["bottom"] + 0.32 * t ** 2.6, rt=S["roof_r"] * (1 - 0.35 * t))
    full = dict(w=S["width"], top=S["top"], bot=S["bottom"], rt=S["roof_r"])
    secs = []
    if nose_rear:
        secs += [(Ln * (1 - (i / N) ** 0.9), nose((i / N) ** 0.9)) for i in range(N, 0, -1)]
    secs += [(Ln if nose_rear else 0, full), (L - Ln if nose_front else L, full)]
    if nose_front:
        secs += [(L - Ln + Ln * (i / N) ** 0.9, nose((i / N) ** 0.9)) for i in range(1, N + 1)]
    secs.sort(key=lambda s: s[0])
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for y, z in section(s["w"], s["bot"], s["top"], s["rt"], 0.18)] for x, s in secs]
    for a, b in zip(rings, rings[1:]):
        for i in range(len(a)):
            j = (i + 1) % len(a)
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for ring in (rings[0], rings[-1]):
        bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Body")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Body", me)
    bpy.context.collection.objects.link(ob)
    return ob


def mickey_cutters(x, side):
    """Cylinders (head + two ears) that punch the recessed window into the side wall."""
    out = []
    for dx, dz, r in ((0, 0, 0.58), (-0.52, 0.66, 0.31), (0.52, 0.66, 0.31)):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=0.3, location=(x + dx, side * SPEC["width"] / 2, 2.55 + dz),
                                            rotation=(math.pi / 2, 0, 0))
        out.append(bpy.context.object)
    return out


def material(name, color, rough=0.4, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    return m


def build():
    body = car_body(SPEC["head_len"], True, False)
    body.data.materials.append(material("paint", SPEC["color"], 0.35, 0.1, 0.8))
    for i in range(4):
        for side in (-1, 1):
            for c in mickey_cutters(5.2 + i * 2.6, side):
                m = body.modifiers.new(f"win{i}_{side}", "BOOLEAN")
                m.operation = "DIFFERENCE"
                m.object = c
                c.hide_render = True
    # TODO (on the Blender machine): doors as recessed panels, windscreen glass on the nose, skirts, bogies and the beam,
    # roof units, then bake dirt / AO into a texture and export with materials; compare with train.html.
    return body


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="train_head.glb")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body = build()
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(pathlib.Path(a.out)), export_format="GLB", use_selection=True, export_apply=True)
    print("[train] wrote", a.out)


if __name__ == "__main__":
    main()
