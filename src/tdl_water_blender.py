"""Tokyo Disneyland - water pass for Blender 5.2, made the same way as the DisneySea one (disneysea_water_blender.py).

  python src/ds_tdl_water.py                                          # 1) water model -> plateau_data/disneyland_water.json
  blender -b --python src/tdl_water_blender.py -- --cams rivers,moat --samples 48
  blender -b --python src/tdl_water_blender.py -- --render none      # build + save the .blend only

The water itself is built by disneysea_water_blender.build_water (the same materials, water volumes, beds, shores by
type, piers); only the data and the ground outline are the Land's:
  - ground slab = the park outline (tourism=theme_park way 1282875870) with every water body cut as a hole
  - water as a closed volume (refraction, absorption, ripple bump) at each body's freeboard below the ground, over a
    mud bed; shores by type (quay wall + coping, wet foundation, rockwork, beach, planted bank)
  - context from the Land draft (disneyland_blender.py): buildings by land colour, greenery, trees, the Western River
    Railroad; its flat ground and water slabs are left out
The scene ground is flat (0 m = the DisneySea promenade datum), so water sits at -freeboard; the DEM-based absolute
levels are in the JSON for the mock.
"""
import sys, math, json, time, argparse, pathlib, importlib, types

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import bpy

OUT = ROOT / "output" / "disneyland" / "water"
WATER_JSON = ROOT / "plateau_data" / "disneyland_water.json"

CAMERAS = {  # name -> (position, look-at, lens mm)
    "top":      ((-330, 690, 2000), (-330, 691, 0), 40),
    "aerial":   ((-150, 20, 620), (-360, 700, 0), 30),
    "rivers":   ((-60, 420, 18), (-90, 600, -1), 24),         # アメリカ河 from its south bank
    "tom":      ((80, 380, 140), (-90, 600, 0), 30),          # アメリカ河 and its islands from above
    "moat":     ((-560, 560, 70), (-430, 640, -1), 26),       # シンデレラ城の堀 (round the hub) from above the west side
    "moat_top": ((-420, 650, 520), (-420, 651, 0), 35),
    "jungle":   ((-120, 900, 25), (-170, 790, -1), 24),       # ジャングルクルーズの川
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="rivers,moat,jungle,tom,aerial")
    ap.add_argument("--render", default="yes", choices=["yes", "none"])
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1600x900")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--sky", type=float, default=0.035)
    ap.add_argument("--no-context", action="store_true", help="water only, no buildings")
    return ap.parse_args(argv)


def core_for_land(W):
    """ds_core with the Land's park outline as PARK (build_water cuts the ground slab from C.PARK)."""
    import ds_core
    C = types.SimpleNamespace(**{k: getattr(ds_core, k) for k in dir(ds_core) if not k.startswith("__")})
    C.PARK = [tuple(p) for p in W["park"]]
    return C


def build_context(C):
    """The Land draft (disneyland_blender.build) without its ground and water: buildings, greenery, trees, railway."""
    import disneyland_blender as DB
    d = DB.data()["disneyland"]
    mats = [C.flat_material(f"mat_land_{i}", c, roughness=0.8) for i, c in enumerate(DB.LAND_RGB)]
    m_green = C.flat_material("mat_tdl_green", (0.25, 0.42, 0.18), roughness=1.0)
    m_crown = C.flat_material("mat_tdl_tree", (0.14, 0.30, 0.12), roughness=1.0)
    m_rail = C.flat_material("mat_rail", (0.30, 0.30, 0.32), roughness=0.5, metallic=0.6)
    col = C.get_collection("Disneyland")
    for i, r in enumerate(d["green"]):
        o = C.flat_fill(f"TDL_Green_{i}", r, 0.03, m_green)
        if o: C.link(o, C.get_collection("Disneyland_Green", col))
    C.link(DB.trees_mesh("TDL_Trees", DB.tree_points(d["trees"]), m_crown, m_crown), C.get_collection("Disneyland_Green", col))
    bcol = C.get_collection("Disneyland_Buildings", col)
    for i, b in enumerate(d["buildings"]):
        h = b["h"]
        z0 = max(0.0, h - C.ROOF_T) if b.get("rf") else 0.0
        o = C.extrude_loops(f"TDL_Bldg_{i}", b["r"], z0, h - z0, mats[min(b["p"], len(mats) - 1)])
        if o: C.link(o, bcol)
    for i, l in enumerate(d["rail"]):
        C.link(DB.ribbon(f"TDL_Rail_{i}", l, 1.2, 0.05, 0.3, m_rail), C.get_collection("Disneyland_Rail", col))
    ctx = C.flat_material("mat_context", (0.22, 0.23, 0.22), roughness=1.0)
    sq = [(-1400, -300), (700, -300), (700, 1600), (-1400, 1600)]
    C.link(C.extrude_loops("Context_Ground", [sq, C.PARK], -3.3, 3.2, ctx), C.get_collection("Context"))


def main():
    args = parse_args()
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for m in ("ds_core", "disneysea_water_blender", "disneyland_blender"):
        if m in sys.modules:
            importlib.reload(sys.modules[m])
    import disneysea_water_blender as WB
    W = json.loads(WATER_JSON.read_text(encoding="utf-8"))
    C = core_for_land(W)
    M = WB.materials()
    WB.build_water(W, M, C)
    if not args.no_context:
        build_context(C)
    print(f"[tdl water] build {time.time() - t0:.1f}s objects={len(bpy.data.objects)}")
    WB.setup(args)
    cams = {n: WB.add_camera(n, *v) for n, v in CAMERAS.items()}
    bpy.context.scene.camera = cams["rivers"]
    for scr in bpy.data.screens:                      # the Land is far from the origin: open the .blend looking at it
        for area in scr.areas:
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.region_3d.view_location = (-330.0, 650.0, 0.0); sp.region_3d.view_distance = 750.0
                    sp.clip_end = 20000.0; sp.shading.color_type = "MATERIAL"
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "disneyland_water.blend"))
    print(f"[tdl water] saved {OUT / 'disneyland_water.blend'}")
    if args.render == "yes":
        for name in [c.strip() for c in args.cams.split(",") if c.strip()]:
            if name not in cams:
                print(f"[tdl water] unknown camera {name!r}; choices: {', '.join(cams)}")
                continue
            t1 = time.time()
            bpy.context.scene.camera = cams[name]
            bpy.context.scene.render.filepath = str(OUT / f"water_{name}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[tdl water] rendered {name} in {time.time() - t1:.1f}s", flush=True)
    print(f"[tdl water] total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
