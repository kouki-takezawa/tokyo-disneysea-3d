"""Special-shaped massing for the handful of landmarks that a flat footprint
box cannot represent (cone/dome/hull silhouettes). Scope is deliberately
limited to items on ds_core.DETAIL_PRIORITY where the real shape is not a
prism: everything else in that list (Sindbad's exit, the Indiana Jones relief,
New York Deli, etc.) is a building footprint and stays a box for now - full
facade detail is a later, per-item pass (see plan).

Each builder creates its bmesh centered on local (0,0,0) and only sets
obj.location to the real-world anchor at the end, so bmesh scale/translate
ops never need a custom pivot.
"""
import bpy, bmesh
from mathutils import Vector
from ds_core import DATA, get_collection, flat_material, link


def _finish(bm, name, location, mat):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    obj.location = location
    return obj


def build_prometheus():
    """Mount Prometheus as the rock-ring heightfield from ds_volcano (plateau_data/disneysea_volcano.json):
    summit 51 m on the south rim, ~20 m rim around the caldera lagoon, lagoon and caldera paths left open.
    The flat draft has no plateau, so the mesh uses h (rock above the plateau). Falls back to the old cone."""
    import json, pathlib
    f = pathlib.Path(__file__).resolve().parent / "plateau_data" / "disneysea_volcano.json"
    if f.exists():
        r = json.loads(f.read_text(encoding="utf-8"))
        nx, ny, st, x0, y0 = r["nx"], r["ny"], r["step"], r["x0"], r["y0"]
        H = r["h"]; rock = r["rock"]
        bm = bmesh.new()
        vid = {}
        for j in range(ny):
            for i in range(nx):
                if rock[j * nx + i] or any(0 <= j + dj < ny and 0 <= i + di < nx and rock[(j + dj) * nx + i + di]
                                           for dj in (-1, 0, 1) for di in (-1, 0, 1)):
                    vid[(i, j)] = bm.verts.new((x0 + i * st, y0 + j * st, H[j * nx + i]))
        for (i, j), v in list(vid.items()):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if all(k in vid for k in q) and any(rock[b * nx + a] for a, b in q):
                try:
                    bm.faces.new([vid[k] for k in q])
                except ValueError:
                    pass
        mat = flat_material("mat_prometheus", (0.30, 0.24, 0.20), roughness=1.0)
        obj = _finish(bm, "Mount_Prometheus", (0.0, 0.0, 0.0), mat)
        for p in obj.data.polygons:
            p.use_smooth = True
        return obj
    return _build_prometheus_cone()


def _build_prometheus_cone():
    """Mount Prometheus: 51m volcano cone with a crater dimple. Center from
    the OSM POI 'プロメテウス火山' (Mount Prometheus) at local (-50,-111)."""
    cx, cy = -50.0, -111.0
    base_r, rim_r, height = 70.0, 16.0, 51.0
    bm = bmesh.new()
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=28,
                                 radius1=base_r, radius2=rim_r, depth=height)
    verts = ret["verts"]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, height / 2))  # cone is centered on Z=0 by default
    top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
    ext = bmesh.ops.extrude_face_region(bm, geom=[top_face])
    ext_verts = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.scale(bm, vec=(0.45, 0.45, 1.0), verts=ext_verts)
    bmesh.ops.translate(bm, verts=ext_verts, vec=(0, 0, -7.0))  # sink crater floor
    mat = flat_material("mat_prometheus", (0.30, 0.24, 0.20), roughness=1.0)
    return _finish(bm, "Mount_Prometheus", (cx, cy, 0.0), mat)


def build_aquasphere():
    """DisneySea AquaSphere: rotating globe fountain at the harbor entrance.
    OSM natural=water way id 72388087, center ~(361,36), area 381 m^2 -> r~11m."""
    cx, cy = 361.0, 36.0
    basin_r, basin_h = 13.0, 2.2
    globe_r = 11.0
    mat_stone = flat_material("mat_aquasphere_basin", (0.72, 0.68, 0.62), roughness=0.6)
    mat_globe = flat_material("mat_aquasphere_globe", (0.55, 0.62, 0.60), roughness=0.25, metallic=0.3)

    bm = bmesh.new()
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32,
                                 radius1=basin_r, radius2=basin_r, depth=basin_h)
    bmesh.ops.translate(bm, verts=ret["verts"], vec=(0, 0, basin_h / 2))
    basin = _finish(bm, "Aquasphere_Basin", (cx, cy, 0.0), mat_stone)

    bm2 = bmesh.new()
    bmesh.ops.create_uvsphere(bm2, u_segments=32, v_segments=20, radius=globe_r)
    globe = _finish(bm2, "Aquasphere_Globe", (cx, cy, basin_h + globe_r * 0.75), mat_globe)
    return basin, globe


def build_triton_dome():
    """Octagonal tent roof over the Mermaid Lagoon indoor hall (ds_core.TRITON_ROOF, from the aerial photo),
    sitting on the hall's flat roof; the hall itself is boxed by ds_buildings."""
    from ds_core import TRITON_ROOF as TR
    cx, cy, r = TR["x"], TR["y"], TR["r"]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=r)
    below = [v for v in bm.verts if v.co.z < -0.01]
    bmesh.ops.delete(bm, geom=below, context="VERTS")
    open_edges = [e for e in bm.edges if e.is_boundary]
    if open_edges:
        bmesh.ops.holes_fill(bm, edges=open_edges, sides=0)
    bmesh.ops.scale(bm, vec=(1.0, 1.0, (TR["peak"] - TR["eaves"]) / r), verts=bm.verts)
    mat = flat_material("mat_triton_dome", (0.58, 0.44, 0.64), roughness=0.7)
    return _finish(bm, "Triton_Dome", (cx, cy, TR["eaves"]), mat)


def _footprint_by_name(*keys):
    for w in DATA["ways"]:
        name = w["tags"].get("name", "") + w["tags"].get("name:en", "")
        if any(k in name for k in keys):
            return w
    return None


def build_ss_columbia():
    """S.S. Columbia excursion steamship - stepped hull + two funnels instead
    of a single box, using its real OSM footprint as the hull outline."""
    w = _footprint_by_name("S.S.コロンビア", "SS Columbia")
    if not w:
        return None
    pts = w["pts"][:-1] if w["pts"][0] == w["pts"][-1] else w["pts"]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    local = [(x - cx, y - cy) for x, y in pts]
    inset = [(x * 0.55, y * 0.55) for x, y in local]

    from ds_core import extrude_footprint
    mat_hull = flat_material("mat_ship_hull", (0.15, 0.16, 0.18), roughness=0.7)
    mat_deck = flat_material("mat_ship_deck", (0.85, 0.83, 0.78), roughness=0.8)
    hull = extrude_footprint("SSColumbia_Hull", local, 0.0, 9.0, mat_hull, cap_bottom=True)
    deck = extrude_footprint("SSColumbia_Deck", inset, 9.0, 11.0, mat_deck, cap_bottom=True)

    # hull/deck verts are in footprint-local coords (centroid at 0,0)
    hull.location = (cx, cy, 0.0)
    deck.location = (cx, cy, 0.0)

    xs = [p[0] for p in local]
    span = max(xs) - min(xs)
    funnels = []
    for t in (0.35, 0.62):
        fx = min(xs) + span * t
        bm = bmesh.new()
        ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16,
                                     radius1=2.3, radius2=2.0, depth=9.0)
        bmesh.ops.translate(bm, verts=ret["verts"], vec=(0, 0, 4.5))
        funnels.append(_finish(bm, f"SSColumbia_Funnel_{int(t * 100)}", (cx + fx, cy, 20.0), mat_hull))

    col = get_collection("Buildings_PRIORITY_todo")
    for obj in [hull, deck, *funnels]:
        link(obj, col)
    return hull, deck, funnels


def build_all():
    col = get_collection("Landmarks")
    n = 0
    p = build_prometheus()
    if p:
        link(p, col); n += 1
    import ds_aquasphere  # detailed build (globe 8 m, pedestal 2 m, rim 0.40 m); flat draft ground = 0
    n += len(ds_aquasphere.build(ground_z=0.0, col=col))
    dome = build_triton_dome()
    if dome:
        link(dome, col); n += 1
    ship = build_ss_columbia()
    if ship:
        n += 1
    print(f"[landmarks] built {n} landmark objects")
