"""Tokyo Disneyland + the Maihama station area -- draft (blocking) scene for Blender 5.2, like disneysea_draft.py.

  blender -b --python src/disneyland_blender.py -- --cams aerial,castle,maihama --samples 16 --percent 50
  blender -b --python src/disneyland_blender.py -- --render none              # build + save .blend only
  python src/disneyland_blender.py --summary                                   # no Blender: what would be built

NOT YET RUN IN BLENDER (written on a machine without it; tools/blender_smoke.py imports it with a stub bpy and runs
summary()). Data: ds_disneyland.build() -- the same lists the mock draws (plateau_data/disneyland_osm.json, GSI DEM5A),
local metres on the DisneySea origin, +X east, +Y north, 0 m = the DisneySea promenade datum.

Like the DisneySea draft, the ground is flat (0 m): buildings stand on 0 and are boxes at their mock height (most are
estimates); roof-only structures are slabs. Elevated things keep their heights above the datum: the Keiyo Line viaduct
(10 m), the Resort Line beam (8 m + 0.9 m). Colours follow the lands (same as the mock).
Before modelling any part in detail, follow the reference videos listed in the README (Blender で作るときの参考動画).
"""
import sys, math, time, argparse, pathlib, json

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "output" / "disneyland"
LAND_RGB = [(0.69, 0.29, 0.35), (0.18, 0.55, 0.34), (0.63, 0.32, 0.18), (0.42, 0.56, 0.14), (0.48, 0.37, 0.65),
            (0.79, 0.51, 0.02), (0.18, 0.44, 0.69), (0.54, 0.58, 0.60)]   # --l0 .. --l7 in the mock
CAMERAS = {   # name -> (camera, target, lens mm); around the park (-330, 690) and Maihama Station (-123, 1053)
    "top": ((-330, 690, 2000), (-330, 691, 0), 40),
    "aerial": ((-150, 20, 620), (-360, 700, 0), 30),
    "castle": ((-300, 540, 40), (-390, 690, 30), 32),
    "maihama": ((80, 900, 90), (-123, 1053, 10), 28),
}


def datum():
    return json.loads((ROOT / "plateau_data" / "disneysea_levels.json").read_text(encoding="utf-8"))["datum_m"]


def data():
    import ds_disneyland as DLM
    return DLM.build(datum())


def summary():
    """What the scene would contain (runs without Blender)."""
    d = data()
    dl, mh = d["disneyland"], d["maihama"]
    return {"buildings": len(dl["buildings"]), "roofs": sum(1 for b in dl["buildings"] if b.get("rf")),
            "water": len(dl["water"]), "green": len(dl["green"]), "woods": len(dl["trees"]), "rail": len(dl["rail"]),
            "maihama_places": len(mh["places"]), "resort_line_ways": len(mh["loop"]), "jr_ways": len(mh["jr"]),
            "trees": len(tree_points(dl["trees"]))}


def tree_points(rings, step=9.0):
    """A tree every `step` m inside the woods (same pattern as the mock's tree symbols)."""
    from ds_core import point_in_poly
    pts = []
    for r in rings:
        xs, ys = [p[0] for p in r], [p[1] for p in r]
        x = math.ceil(min(xs) / step) * step
        while x <= max(xs):
            y = math.ceil(min(ys) / step) * step
            while y <= max(ys):
                jx, jy = x + ((y * 7) % 5) - 2, y + ((x * 3) % 5) - 2
                if point_in_poly(jx, jy, r):
                    pts.append((jx, jy))
                y += step
            x += step
    return pts


# ---------------------------------------------------------------- Blender side
def ribbon(name, line, width, z0, z1, mat):
    """A box swept along a polyline (viaduct deck, beam, rail)."""
    import bpy, bmesh
    bm = bmesh.new()
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        L = math.hypot(x1 - x0, y1 - y0) or 1e-6
        nx, ny = -(y1 - y0) / L * width / 2, (x1 - x0) / L * width / 2
        q = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
        lo = [bm.verts.new((x, y, z0)) for x, y in q]
        hi = [bm.verts.new((x, y, z1)) for x, y in q]
        bm.faces.new(hi)
        bm.faces.new(lo[::-1])
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    return ob


def trees_mesh(name, pts, mat_trunk, mat_crown):
    import bpy, bmesh
    from mathutils import Matrix
    bm = bmesh.new()
    for x, y in pts:
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.25, radius2=0.2, depth=3.2, matrix=Matrix.Translation((x, y, 1.6)))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=2.2, radius2=0.0, depth=3.6, matrix=Matrix.Translation((x, y, 4.9)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat_crown)
    return ob


def build():
    from ds_core import flat_material, get_collection, link, extrude_loops, flat_fill, ROOF_T
    d = data()
    dl, mh = d["disneyland"], d["maihama"]
    mats = [flat_material(f"mat_land_{i}", c, roughness=0.8) for i, c in enumerate(LAND_RGB)]
    m_ground = flat_material("mat_tdl_ground", (0.55, 0.53, 0.49), roughness=1.0)
    m_water = flat_material("mat_tdl_water", (0.10, 0.28, 0.35), roughness=0.08)
    m_green = flat_material("mat_tdl_green", (0.25, 0.42, 0.18), roughness=1.0)
    m_crown = flat_material("mat_tdl_tree", (0.14, 0.30, 0.12), roughness=1.0)
    m_conc = flat_material("mat_viaduct", (0.66, 0.65, 0.61), roughness=0.9)
    m_rail = flat_material("mat_rail", (0.30, 0.30, 0.32), roughness=0.5, metallic=0.6)
    m_place = flat_material("mat_maihama_place", (0.72, 0.71, 0.68), roughness=0.85)
    m_station = flat_material("mat_station", (0.85, 0.83, 0.78), roughness=0.7)

    col = get_collection("Disneyland")
    link(extrude_loops("TDL_Ground", [dl["park"]], -0.4, 0.4, m_ground), col)
    for i, r in enumerate(dl["water"]):
        o = flat_fill(f"TDL_Water_{i}", r, -0.3, m_water)
        if o: link(o, get_collection("Disneyland_Water", col))
    for i, r in enumerate(dl["green"]):
        o = flat_fill(f"TDL_Green_{i}", r, 0.03, m_green)
        if o: link(o, get_collection("Disneyland_Green", col))
    link(trees_mesh("TDL_Trees", tree_points(dl["trees"]), m_crown, m_crown), get_collection("Disneyland_Green", col))
    bcol = get_collection("Disneyland_Buildings", col)
    for i, b in enumerate(dl["buildings"]):
        h = b["h"]
        z0 = max(0.0, h - ROOF_T) if b.get("rf") else 0.0
        o = extrude_loops(f"TDL_Bldg_{i}", b["r"], z0, h - z0, mats[min(b["p"], len(mats) - 1)])
        if o: link(o, bcol)
    for i, l in enumerate(dl["rail"]):
        link(ribbon(f"TDL_Rail_{i}", l, 1.2, 0.05, 0.3, m_rail), get_collection("Disneyland_Rail", col))

    mcol = get_collection("Maihama")
    for i, p in enumerate(mh["places"]):
        o = extrude_loops(f"MH_Place_{i}", p["r"], 0.0, p["h"], m_station if p["k"] == "station" else m_place)
        if o: link(o, mcol)
    for i, l in enumerate(mh["jr"]):   # Keiyo Line viaduct: deck and rail level
        link(ribbon(f"MH_JR_Deck_{i}", l, 6.0, mh["jr_z"] - 1.2, mh["jr_z"] - 0.3, m_conc), mcol)
        link(ribbon(f"MH_JR_Rail_{i}", l, 1.2, mh["jr_z"] - 0.3, mh["jr_z"], m_rail), mcol)
    for i, l in enumerate(mh["loop"]):   # Resort Line beam
        link(ribbon(f"MH_RL_Beam_{i}", l, 0.85, mh["loop_z"], mh["loop_z"] + 0.9, m_conc), mcol)
    for i, r in enumerate(mh["platforms"]):
        c = sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)
        z = mh["jr_z"] if math.hypot(c[0] - mh["station"]["x"], c[1] - mh["station"]["y"]) < 60 else mh["loop_z"]
        o = extrude_loops(f"MH_Platform_{i}", [r], z - 0.4, 0.4 + 1.1, m_station)
        if o: link(o, mcol)
    return d


def main():
    if "--summary" in sys.argv:
        print(summary())
        return
    import bpy
    from mathutils import Vector
    sys.path.insert(0, str(ROOT / "src"))
    import disneysea_draft as DD                # same world / render / camera helpers as the DisneySea draft
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="aerial,maihama")
    ap.add_argument("--render", default="yes", choices=["yes", "none"])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--percent", type=int, default=50)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--sky", type=float, default=0.035)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    print(f"[disneyland] build done in {time.time() - t0:.1f}s, objects={len(bpy.data.objects)}")
    DD.setup_world(args.sky)
    DD.setup_render(args)
    cams = {n: DD.add_camera(n, *v) for n, v in CAMERAS.items()}
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "disneyland_draft.blend"))
    if args.render == "yes":
        for name in [c.strip() for c in args.cams.split(",") if c.strip() in cams]:
            bpy.context.scene.camera = cams[name]
            bpy.context.scene.render.filepath = str(out / f"disneyland_{name}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[disneyland] rendered {name}")


if __name__ == "__main__":
    main()
