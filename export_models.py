"""Export Blender-built parts as GLB for the outline mock's 3D view (Blender 5.2).

  blender -b --python export_models.py -- --parts water,aquasphere
  python export_mock.py        # picks up output/disneysea/models/*.json (D.models)

Each GLB is in the mock's coordinates: local metres, heights relative to the
DEM datum (the Blender scenes use a flat promenade = 0, so every part is
lifted to its own ground level here). glTF is Y-up, which is exactly the
mock's V(x, y, z) = [x, z, -y].

  water       ds_water model (disneysea_water_blender.build_water) without the
              ground slabs: water surfaces, beds, shores, piers, each body
              raised by (level + freeboard). Merged per material into WS_*
              meshes; the mock assigns the materials by name (procedural
              Blender shaders do not survive glTF).
  aquasphere  ds_aquasphere.build(ground_z = SPEC ground_rel), modifiers
              applied, globe texture exported as JPEG.
  plaza       ds_plaza.build(): DisneySea Plaza paving, planters and trees around
              the AquaSphere, merged per kind into PZ_* meshes.
  volcano     ds_volcano_model.build(): the sculpted rock massif with vertex colours.
  --render    Cycles check renders instead of exporting (aquasphere: with the plaza;
              volcano: with the water model).
"""
import sys, math, json, argparse, pathlib, importlib

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bpy, bmesh
from mathutils import Matrix

OUT = ROOT / "output" / "disneysea" / "models"


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for m in ("ds_core", "ds_terrain", "ds_aquasphere", "disneysea_water_blender"):
        if m in sys.modules:
            importlib.reload(sys.modules[m])


def merged(name, parts, col):
    """One mesh from [(object, dz)] with modifiers and transforms applied."""
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o, dz in parts:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.transform(Matrix.Translation((0, 0, dz)) @ o.matrix_world)
        bm.from_mesh(me)
        ev.to_mesh_clear()
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out); bm.free()
    obj = bpy.data.objects.new(name, out)
    col.objects.link(obj)
    return obj


def top_faces_only(obj, z_top=None):
    """Keep the upward faces (water surface / bed top) of a closed slab."""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    kill = [f for f in bm.faces if f.normal.z < 0.9]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(obj.data); bm.free()


def export(objs, path, materials=False):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    kw = dict(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True,
              export_yup=True, export_normals=True, export_texcoords=materials)
    kw["export_materials"] = "EXPORT" if materials else "NONE"
    if materials:
        kw["export_image_format"] = "JPEG"
    if any(o.data.color_attributes for o in objs if o.type == "MESH"):
        kw["export_vertex_color"] = "ACTIVE"      # volcano: colours live in the vertex colours
    bpy.ops.export_scene.gltf(**kw)
    js = glb_to_json(path)
    print(f"[models] {path.name} {path.stat().st_size / 1e6:.2f} MB -> {js.name} {js.stat().st_size / 1e6:.2f} MB")


def glb_to_json(path):
    """GLB -> self-contained glTF JSON (buffer as a data: URI). The artifact host serves
    .json but not .glb; GLTFLoader reads either."""
    import struct, base64
    data = path.read_bytes()
    off, doc, blob = 12, None, b""
    while off < len(data):
        ln, typ = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + ln]
        if typ == 0x4E4F534A:
            doc = json.loads(chunk)
        elif typ == 0x004E4942:
            blob = chunk
        off += 8 + ln
    # images go out as sibling .jpg/.png files: GLTFLoader turns embedded images into blob: URLs,
    # which the artifact page's CSP blocks (the whole model then fails to load)
    for k, img in enumerate(doc.get("images", [])):
        if "bufferView" not in img:
            continue
        bv = doc["bufferViews"][img.pop("bufferView")]
        ext = ".png" if img.get("mimeType") == "image/png" else ".jpg"
        name = f"{path.stem}_img{k}{ext}"
        (path.parent / name).write_bytes(blob[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]])
        img.pop("mimeType", None)
        img["uri"] = name
    if doc.get("buffers"):
        doc["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(blob).decode()
    out = path.with_suffix(".json")
    out.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return out


def part_water():
    import ds_core as C
    import disneysea_water_blender as WB
    W = json.loads(WB.WATER_JSON.read_text(encoding="utf-8"))
    M = WB.materials()
    WB.build_water(W, M, C)
    bodies = {b["id"]: b for b in W["bodies"]}
    lift = lambda b: b["level"] + b["freeboard"]          # scene water sits at -freeboard
    groups = {}
    for o in list(bpy.data.objects):
        n = o.name
        if n.startswith(("Ground", "Island_")) or o.type != "MESH":
            continue
        if n.startswith("Water_"):
            b = bodies[n[6:]]; key = "WS_water"
        elif n.startswith("Bed_"):
            b = bodies[n[4:]]; key = "WS_bed"
        elif n.startswith("Shore_"):
            _, t, k = n.split("_")[:3]
            b = W["bodies"][W["shores"][int(k)]["b"]]
            mat = o.data.materials[0].name if o.data.materials else ""
            key = {"mat_quay_stone": "WS_quay", "mat_coping": "WS_coping", "mat_wet_foundation": "WS_wet",
                   "mat_rockwork": "WS_rock", "mat_sand_bank": "WS_sand", "mat_bank_grass": "WS_grass",
                   "mat_bank_mud": "WS_mud"}.get(mat, "WS_quay")
        elif n.startswith(("Pier_", "Pile_")):
            b = W["bodies"][0]; key = "WS_deck"
        else:
            continue
        groups.setdefault(key, []).append((o, lift(b)))
    col = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(col)
    outs = []
    for key, parts in groups.items():
        m = merged(key, parts, col)
        if key in ("WS_water", "WS_bed"):
            top_faces_only(m)
        outs.append(m)
    return outs


def part_aquasphere():
    import ds_aquasphere as AQ
    col = bpy.data.collections.new("Landmarks"); bpy.context.scene.collection.children.link(col)
    AQ.build(ground_z=AQ.SPEC["ground_rel"], col=col)
    # glTF keeps only plain base colours: unhook procedural colour/normal chains (image textures stay)
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        b = mat.node_tree.nodes.get("Principled BSDF")
        if not b:
            continue
        for inp in ("Base Color", "Normal", "Roughness", "Coat Weight"):
            for l in list(b.inputs[inp].links) if inp in b.inputs else []:
                if l.from_node.type != "TEX_IMAGE":
                    mat.node_tree.links.remove(l)
        if not b.inputs["Base Color"].links:
            b.inputs["Base Color"].default_value = mat.diffuse_color
    for img in bpy.data.images:   # web-sized globe texture
        if img.size[0] > 2048:
            img.scale(2048, 1024)
    return [o for o in col.objects if o.type == "MESH"]


def part_plaza():
    import ds_plaza as PZ
    col = bpy.data.collections.new("Plaza"); bpy.context.scene.collection.children.link(col)
    PZ.build(col=col)
    groups = {}
    for o in list(col.objects):   # merge per kind (hundreds of trees -> a few meshes)
        key = "_".join(o.name.split("_")[:2])
        groups.setdefault(key, []).append((o, 0.0))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in groups.items()]


def part_volcano():
    import ds_volcano_model as VM
    col = bpy.data.collections.new("Volcano"); bpy.context.scene.collection.children.link(col)
    return [VM.build(col=col)]


def render_checks(part, samples):
    """Cycles check renders of a part (before its materials are flattened for glTF)."""
    import ds_aquasphere as AQ
    sc = bpy.context.scene
    world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
    nt = world.node_tree; nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "MULTIPLE_SCATTERING"
    except TypeError:
        pass
    sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(200)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 0.035
    o = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs["Background"], o.inputs["Surface"])
    sc.render.engine = "CYCLES"; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.cycles.transmission_bounces = 12; sc.cycles.max_bounces = 12
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.view_settings.view_transform = "AgX"
    from mathutils import Vector
    S = AQ.SPEC
    if part == "volcano":   # (azimuth, distance, cam z, target z, lens) around the summit / lagoon
        cx, cy, g = -50.0, -80.0, 0.0
        shots = {"harbor": (0.35, 150.0, 14.0, 22.0, 30), "aerial": (-0.9, 230.0, 120.0, 10.0, 30),
                 "lagoon": (1.9, 40.0, 9.0, 8.0, 20), "cliff": (-0.3, 75.0, 3.0, 18.0, 24)}
    else:
        cx, cy, g = S["cx"], S["cy"], S["ground_rel"]
        mat = bpy.data.materials.new("check_ground"); mat.diffuse_color = (0.5, 0.5, 0.48, 1)
        me = bpy.data.meshes.new("check_ground")   # ground ring around the pool (the pool must stay open)
        AQ.disc(150, 0.0, 96, r_in=S["pool_r"] + 0.05).to_mesh(me)
        gobj = bpy.data.objects.new("check_ground", me); gobj.location = (cx, cy, g - 0.02); me.materials.append(mat)
        sc.collection.objects.link(gobj)
        ent = math.atan2(2.0 - cy, 390.0 - cx)
        shots = {"globe": (ent, 17.0, g + 3.2, g + 5.8, 32), "wide": (ent + 0.5, 34.0, g + 9.0, g + 3.0, 28),
                 "base": (ent - 0.3, 9.0, g + 1.0, g + 2.2, 24),
                 "plaza": (ent + 2.6, 30.0, g + 1.7, g + 2.0, 24)}
    for name, (a, dist, zc, zt, lens) in shots.items():
        cam = bpy.data.cameras.new(name); cam.lens = lens
        co = bpy.data.objects.new(name, cam); sc.collection.objects.link(co)
        co.location = (cx + math.cos(a) * dist, cy + math.sin(a) * dist, zc)
        co.rotation_euler = (Vector((cx, cy, zt)) - co.location).to_track_quat("-Z", "Y").to_euler()
        sc.camera = co
        sc.render.filepath = str(ROOT / "output" / "disneysea" / part / f"{part}_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[models] rendered {part}_{name}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(); ap.add_argument("--parts", default="water,aquasphere")
    ap.add_argument("--render", action="store_true", help="Cycles check renders (aquasphere) instead of exporting")
    ap.add_argument("--samples", type=int, default=64)
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    for part in args.parts.split(","):
        reset()
        if args.render:
            if part == "volcano":   # with the water model for context (harbour, lagoon)
                import ds_core as C, disneysea_water_blender as WB
                W = json.loads(WB.WATER_JSON.read_text(encoding="utf-8"))
                WB.build_water(W, WB.materials(), C)
                part_volcano()
            else:
                import ds_aquasphere as AQ
                col = bpy.data.collections.new("Landmarks"); bpy.context.scene.collection.children.link(col)
                AQ.build(ground_z=AQ.SPEC["ground_rel"], col=col)
                if (ROOT / "plateau_data" / "disneysea_plaza.json").exists():
                    import ds_plaza
                    ds_plaza.build(col=col)
            (ROOT / "output" / "disneysea" / part).mkdir(parents=True, exist_ok=True)
            render_checks(part, args.samples)
            continue
        objs = {"water": part_water, "aquasphere": part_aquasphere, "plaza": part_plaza, "volcano": part_volcano}[part]()
        export(objs, OUT / f"{part}.glb", materials=(part not in ("water",)))


if __name__ == "__main__":
    main()
