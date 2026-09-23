"""Tokyo DisneySea - draft (blocking) scene builder for Blender 5.2.

  blender -b --python disneysea_draft.py -- --cams aerial,top --samples 16 --percent 50
  blender -b --python disneysea_draft.py -- --render none          # build + save .blend only

Data: plateau_data/disneysea_osm.json (fetch_disneysea.py). Local metres,
origin (35.6267, 139.8851) near Mediterranean Harbor, +X east, +Y north.
Modules: ds_core (helpers/heights/port classes), ds_terrain (ground, water,
greenery, rock, paths, railway), ds_buildings (footprint boxes),
ds_landmarks (volcano, AquaSphere, Triton dome, S.S. Columbia).
"""
import sys, math, time, argparse, pathlib, importlib

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import bpy
from mathutils import Vector

OUT = ROOT / "output" / "disneysea"

# name -> (camera position, look-at target, lens mm)
CAMERAS = {
    "top":             ((-180, 60, 2100), (-180, 61, 0), 40),
    "aerial":          ((-60, -1150, 720), (-200, 40, 0), 32),
    "aerial_east":     ((900, -300, 520), (-150, 60, 0), 30),
    "mediterranean":   ((240, -30, 28), (-50, -111, 22), 26),
    "mysterious":      ((120, -260, 45), (-50, -111, 28), 30),
    "american":        ((380, -470, 55), (160, -290, 8), 28),
    "arabian_mermaid": ((-120, 330, 70), (-280, 110, 5), 28),
    "fantasy_springs": ((-420, 60, 75), (-690, 270, 12), 28),
    "aquasphere":      ((396, 30, 3.2), (352, 38, 7.5), 24),
    "aquasphere_close": ((374, 30, 2.0), (361, 36.4, 4.6), 30),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="aerial,top")
    ap.add_argument("--render", default="yes", choices=["yes", "none"])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--percent", type=int, default=50)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--sky", type=float, default=0.035, help="sky texture strength")
    ap.add_argument("--no-blend", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    return ap.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for m in ("ds_core", "ds_terrain", "ds_buildings", "ds_landmarks"):
        if m in sys.modules:  # re-running inside a GUI session
            importlib.reload(sys.modules[m])


def setup_world(strength):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "MULTIPLE_SCATTERING"   # NISHITA was removed in 5.x
    except TypeError:
        pass
    sky.sun_elevation = math.radians(42)
    sky.sun_rotation = math.radians(200)       # 0 = +Y (north), clockwise -> sun from SSW
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_context_plane():
    """Neutral 4 km ground around the park so it doesn't float in a void.
    Surroundings (Tokyo Bay, parking, Disneyland) are not modelled in the draft."""
    from ds_core import flat_material, get_collection, link, extrude_loops, PARK
    mat = flat_material("mat_context", (0.22, 0.23, 0.22), roughness=1.0)
    sq = [(-2200, -2000), (1800, -2000), (1800, 2000), (-2200, 2000)]
    # park outline cut out, so the context slab never pokes up through the water holes
    link(extrude_loops("Context_Ground", [sq, PARK], -3.3, 3.2, mat), get_collection("Context"))


def add_camera(name, pos, target, lens):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.5
    cam.clip_end = 6000
    obj = bpy.data.objects.new(f"Cam_{name}", cam)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = pos
    d = Vector(target) - Vector(pos)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return obj


def setup_render(args):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    w, h = (int(v) for v in args.res.split("x"))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = args.percent
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"


def main():
    args = parse_args()
    t0 = time.time()
    reset_scene()
    import ds_terrain, ds_buildings, ds_landmarks

    ds_terrain.build_all()
    ds_buildings.build_buildings()
    ds_landmarks.build_all()
    add_context_plane()
    print(f"[draft] build done in {time.time() - t0:.1f}s, objects={len(bpy.data.objects)}")

    setup_world(args.sky)
    setup_render(args)
    cams = {n: add_camera(n, *v) for n, v in CAMERAS.items()}

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not args.no_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(out / "disneysea_draft.blend"))
        print(f"[draft] saved {out / 'disneysea_draft.blend'}")

    if args.render == "yes":
        for name in [c.strip() for c in args.cams.split(",") if c.strip()]:
            if name not in cams:
                print(f"[draft] unknown camera {name!r}; choices: {', '.join(cams)}")
                continue
            t1 = time.time()
            bpy.context.scene.camera = cams[name]
            bpy.context.scene.render.filepath = str(out / f"draft_{name}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[draft] rendered {name} in {time.time() - t1:.1f}s")
    print(f"[draft] total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
