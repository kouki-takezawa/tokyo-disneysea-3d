"""DisneySea Plaza: the ground around the AquaSphere (plan in plain Python, build in Blender 5.2).

  python ds_plaza.py        # -> plateau_data/disneysea_plaza.json (plan) + summary

OSM relation 3297581 (highway=pedestrian, "ディズニーシー・プラザ") is the round plaza + west
arcade; the MiraCosta courtyards around it are paved too (everything open inside the park);
its inner rings are either buildings (MiraCosta blocks: left to the draft) or the
elliptical tree planters seen on the GSI aerial photo. Out to PLAZA_R from the
globe the whole relation is modelled:
  paving   blue-grey stone inside BLUE_R (the round plaza on the photo), terracotta
           brick outside it (the arcades). The AquaSphere build (ds_aquasphere)
           already paves out to its own plaza_r, so that disc is left out here.
  lines    the AquaSphere's 12 white radial lines continued out to BLUE_R
  planters every non-building inner ring + nearby garden/forest/flowerbed ways:
           a 0.45 m stone curb, soil/grass top, round-canopy trees spaced ~TREE_GAP m
Heights: flat at the AquaSphere ground (SPEC ground_rel, relative to the DEM datum).
"""
import json, math, pathlib, random, sys
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import ds_core as C
import ds_aquasphere as AQ

OUT = ROOT / "plateau_data" / "disneysea_plaza.json"
REL = 3297581
PLAZA_R = 85.0          # model the plaza out to this distance from the globe
BLUE_R = 42.0           # blue-grey round plaza (aerial photo), terracotta beyond
CURB_H, CURB_W = 0.45, 0.35
TREE_GAP = 5.0


def plan():
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    S = AQ.SPEC
    cx, cy = S["cx"], S["cy"]
    area = Point(cx, cy).buffer(PLAZA_R, 96)
    rel = next(r for r in C.DATA["relations"] if r["id"] == REL)
    outers = C.assemble_rings([m["way"] for m in rel["members"] if m["role"] == "outer"])
    inners = C.assemble_rings([m["way"] for m in rel["members"] if m["role"] == "inner"])
    def grounded(w):   # MiraCosta (layer 2) spans over the arcade courtyards: those stay paved
        try:
            return int(w["tags"].get("layer", "0")) <= 0
        except ValueError:
            return True
    bldg = unary_union([Polygon(w["pts"]).buffer(0) for w in C.ways_with("building")
                        if len(w["pts"]) >= 3 and grounded(w)
                        and Point(C.poly_centroid(w["pts"])).distance(Point(cx, cy)) < PLAZA_R + 60])
    holes, planters = [], []
    for ring in inners:
        p = Polygon(ring).buffer(0)
        if p.is_empty or not p.intersects(area):
            continue
        if p.intersection(bldg).area > 0.4 * p.area:
            holes.append(p)                      # building block: the draft has it
        elif p.distance(Point(cx, cy)) > S["pool_r"] + 1:
            planters.append(p)                   # tree planter
        else:
            holes.append(p)                      # the pool / pedestal (AquaSphere build)
    green = []
    for k, v in (("leisure", "garden"), ("landuse", "forest"), ("landuse", "flowerbed")):
        for w in C.ways_with(k, v):
            p = Polygon(w["pts"]).buffer(0)
            if p.is_valid and p.intersects(area) and not p.intersects(bldg.buffer(-0.5))                     and not any(p.intersection(q).area > 0.5 * p.area for q in planters):   # same bed mapped twice
                green.append((p, v))
    # the relation covers the round plaza and the west arcade; the MiraCosta courtyards (terracotta,
    # planters) lie outside it, so everything open within PLAZA_R inside the park is paved
    park = Polygon(C.PARK).buffer(0)
    paved = unary_union([Polygon(o).buffer(0) for o in outers] + [park.intersection(area)]).intersection(area)
    # elevated buildings (MiraCosta, layer 2) are drawn in OSM with their courtyards inside the
    # footprint: keep them out of the paving except around the courtyard planters
    upper = unary_union([Polygon(w["pts"]).buffer(0) for w in C.ways_with("building")
                         if len(w["pts"]) >= 3 and not grounded(w)
                         and Point(C.poly_centroid(w["pts"])).distance(Point(cx, cy)) < PLAZA_R + 60])
    courts = unary_union([g.buffer(8.0) for g, _ in green if g.intersects(upper)]).intersection(upper)
    paved = paved.difference(unary_union(holes + planters + [g for g, _ in green] + [bldg, upper.difference(courts)]))
    aq_disc = Point(cx, cy).buffer(S["plaza_r"], 128)
    paved = paved.difference(aq_disc)
    blue_disc = Point(cx, cy).buffer(BLUE_R, 128)
    blue, red = paved.intersection(blue_disc), paved.difference(blue_disc)

    def polys(g):
        return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area > 0.5]

    def ring(p):
        return [[round(x, 2), round(y, 2)] for x, y in list(p.exterior.coords)[:-1]]

    def rings(p):
        return {"r": ring(p), "h": [[[round(x, 2), round(y, 2)] for x, y in list(i.coords)[:-1]] for i in p.interiors]}

    rnd = random.Random(3)
    plant_out = []
    for p, kind in [(p, "planter") for p in planters] + green:
        p = p.intersection(area)
        for q in polys(p):
            inner = q.buffer(-CURB_W - 0.8)
            trees = []
            if kind != "flowerbed" and not inner.is_empty:
                minx, miny, maxx, maxy = inner.bounds
                cand = [(minx + (i + 0.5) * TREE_GAP, miny + (j + 0.5) * TREE_GAP)
                        for i in range(int((maxx - minx) / TREE_GAP) + 1) for j in range(int((maxy - miny) / TREE_GAP) + 1)]
                cand = [(x + rnd.uniform(-1, 1), y + rnd.uniform(-1, 1)) for x, y in cand]
                trees = [[round(x, 2), round(y, 2), round(rnd.uniform(5.5, 8.0), 2), round(rnd.uniform(2.0, 3.0), 2)]
                         for x, y in cand if inner.contains(Point(x, y))]
                if not trees:
                    c = inner.representative_point()
                    trees = [[round(c.x, 2), round(c.y, 2), 6.5, 2.4]]
            ins = q.buffer(-CURB_W)   # soil inside the curb (precomputed: Blender's Python has no shapely)
            plant_out.append({"kind": kind, **rings(q), "trees": trees, "in": [ring(i) for i in polys(ins)]})
    lines = []
    for k in range(S["plaza_lines"]):
        a = 2 * math.pi * k / S["plaza_lines"]
        seg = [(cx + S["plaza_r"] * math.cos(a), cy + S["plaza_r"] * math.sin(a)), (cx + BLUE_R * math.cos(a), cy + BLUE_R * math.sin(a))]
        from shapely.geometry import LineString
        ls = LineString(seg).intersection(blue)
        for part in getattr(ls, "geoms", [ls]):
            if part.length > 0.5:
                lines.append([[round(x, 2), round(y, 2)] for x, y in part.coords])
    data = {"center": [cx, cy], "ground": S["ground_rel"], "blue_r": BLUE_R, "plaza_r": PLAZA_R,
            "blue": [rings(p) for p in polys(blue)], "red": [rings(p) for p in polys(red)],
            "planters": plant_out, "lines": lines, "line_w": S["plaza_line_w"],
            "curb_h": CURB_H, "curb_w": CURB_W}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data


# ---------------------------------------------------------------- Blender
def build(col=None, ground_z=None):
    """Plaza ground as 3D geometry (paving slabs, curbs, soil, trees, white lines)."""
    import bpy, bmesh
    from mathutils import Vector
    D = json.loads(OUT.read_text(encoding="utf-8"))
    g = D["ground"] if ground_z is None else ground_z
    col = col or bpy.context.scene.collection
    pv = g + 0.045                       # same paving level as the AquaSphere plaza
    blue = AQ.mat_stone("mat_pz_blue", (0.42, 0.50, 0.60))
    red = AQ.mat_stone("mat_pz_brick", (0.55, 0.33, 0.25))
    curb = AQ.mat_stone("mat_pz_curb", (0.78, 0.72, 0.60))
    soil = AQ.mat_stone("mat_pz_soil", (0.30, 0.40, 0.18))   # low planting / grass on the soil
    bark = AQ.mat_stone("mat_pz_bark", (0.25, 0.19, 0.13))
    leaf = AQ.mat_stone("mat_pz_leaf", (0.16, 0.30, 0.12))
    white = AQ.mat_stone("mat_aq_line", (0.92, 0.92, 0.90))

    def slab(name, polys, z, th, mat):
        loops_all = [[p["r"]] + p["h"] for p in polys]
        objs = []
        for i, loops in enumerate(loops_all):
            o = C.extrude_loops(f"{name}_{i}", loops, z - th, th, mat, cap_bottom=False)
            if o:
                col.objects.link(o); objs.append(o)
        return objs

    out = {"blue": slab("PZ_Blue", D["blue"], pv, 0.15, blue), "red": slab("PZ_Brick", D["red"], pv, 0.15, red)}
    # planters: curb ring (outer ring minus an inset) + soil top + trees
    rnd = random.Random(5)
    for i, p in enumerate(D["planters"]):
        h = D["curb_h"] if p["kind"] != "flowerbed" else 0.3
        if p["in"]:
            o = C.extrude_loops(f"PZ_Curb_{i}", [p["r"]] + p["in"], g, h, curb)
            if o:
                col.objects.link(o)
            for j, q in enumerate(p["in"]):   # soil top as a filled sheet (tessellate_polygon drops faces on big concave beds)
                bm = bmesh.new()
                vs = [bm.verts.new((x, y, g + h - 0.08)) for x, y in q]
                es = [bm.edges.new((vs[k], vs[(k + 1) % len(vs)])) for k in range(len(vs))]
                bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=es)
                for f in bm.faces:
                    if f.normal.z < 0:
                        f.normal_flip()
                me = bpy.data.meshes.new(f"PZ_Soil_{i}_{j}"); bm.to_mesh(me); bm.free()
                so = bpy.data.objects.new(me.name, me); me.materials.append(soil); col.objects.link(so)
        for k, (x, y, th, cr) in enumerate(p["trees"]):
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.22, radius2=0.14, depth=th * 0.62)
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, th * 0.31))
            me = bpy.data.meshes.new(f"PZ_Trunk_{i}_{k}"); bm.to_mesh(me); bm.free()
            t = bpy.data.objects.new(me.name, me); t.location = (x, y, g + h - 0.08); me.materials.append(bark)
            col.objects.link(t)
            bm = bmesh.new()
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=cr)
            for v in bm.verts:   # lumpy, slightly flattened canopy
                v.co *= 1.0 + rnd.uniform(-0.12, 0.12)
                v.co.z *= 0.78
            me = bpy.data.meshes.new(f"PZ_Canopy_{i}_{k}"); bm.to_mesh(me); bm.free()
            c = bpy.data.objects.new(me.name, me); c.location = (x, y, g + h - 0.08 + th * 0.62 + cr * 0.45)
            me.materials.append(leaf); col.objects.link(c)
    # white radial lines continued from the AquaSphere plaza
    bm = bmesh.new()
    w = D["line_w"] / 2
    for (x0, y0), (x1, y1) in D["lines"]:
        L = math.hypot(x1 - x0, y1 - y0) or 1
        nx, ny = -(y1 - y0) / L * w, (x1 - x0) / L * w
        vs = [bm.verts.new((x0 + nx, y0 + ny, pv + 0.006)), bm.verts.new((x1 + nx, y1 + ny, pv + 0.006)),
              bm.verts.new((x1 - nx, y1 - ny, pv + 0.006)), bm.verts.new((x0 - nx, y0 - ny, pv + 0.006))]
        bm.faces.new(vs)
    me = bpy.data.meshes.new("PZ_Lines"); bm.to_mesh(me); bm.free()
    lo = bpy.data.objects.new("PZ_Lines", me); me.materials.append(white); col.objects.link(lo)
    return out


if __name__ == "__main__":
    d = plan()
    nt = sum(len(p["trees"]) for p in d["planters"])
    print(f"[plaza] {OUT.name}: blue {len(d['blue'])} / brick {len(d['red'])} paving pieces, "
          f"{len(d['planters'])} planters, {nt} trees, {len(d['lines'])} radial lines")
