"""Ground, water, greenery, rockwork massing, paths and the elevated railway
for the DisneySea draft. Everything is clipped to the park boundary
(OSM tourism=theme_park way 203538370); the bbox also contains parts of
Tokyo Disneyland and the surrounding roads, which the draft leaves out.

Water model: the ground is one slab (top z=0) with the big water bodies cut
out as holes, so the harbour sits WATER_Z below the promenade with vertical
quay walls. Islands (relation inner rings) get their own ground slabs. Small
ponds that cannot be cut cleanly (crossing the boundary, touching another
hole, or sitting on an island) are laid on top of the ground instead.
"""
try:
    import bpy, bmesh
except ImportError:
    bpy = bmesh = None
from ds_core import (DATA, WAYS, PARK, get_collection, flat_material, extrude_loops,
                      extrude_footprint, flat_fill, link, ways_with, multipolygons,
                      poly_area, poly_centroid, point_in_poly, ring_inside, in_park,
                      _clean_ring)

GROUND_Z = 0.0
GROUND_DEPTH = 3.0
WATER_Z = -1.0       # harbour surface ~1 m below the promenade
PATH_Z = 0.03
BRIDGE_Z = 0.5
RAIL_Z = 7.0         # DisneySea Electric Railway runs on a viaduct

STATE = {"holes": [], "surface_water": [], "islands": [], "tunnels": [], "levels": {}, "source": "osm"}  # mutate in place


def _relation_member_ids():
    ids = set()
    for r in DATA["relations"]:
        for m in r["members"]:
            ids.add(m["way"])
    return ids


def _plan_water():
    """Decide which water bodies become ground holes vs. surface slabs."""
    members = _relation_member_ids()
    cands = []
    for r, outers, inners in multipolygons("natural", "water"):
        for o in outers:
            cands.append((poly_area(o), _clean_ring(o), [_clean_ring(i) for i in inners if ring_inside(i, o)], f"R{r['id']}"))
    for key, val in (("natural", "water"), ("waterway", "river")):
        for w in ways_with(key, val):
            if w["id"] in members:
                continue
            ring = _clean_ring(w["pts"])
            if len(ring) >= 3:
                cands.append((poly_area(ring), ring, [], f"W{w['id']}"))
    cands.sort(key=lambda c: -c[0])

    used_verts = set()
    for area, ring, inners, tag in cands:
        if area < 20 or not in_park(ring):
            continue
        cx, cy = poly_centroid(ring)
        parent = next((h for h in STATE["holes"] if point_in_poly(cx, cy, h[0])), None)
        if parent:
            on_island = any(point_in_poly(cx, cy, isl) for isl in parent[1])
            if on_island:
                STATE["surface_water"].append((ring, tag))
            continue  # otherwise it duplicates water that is already cut
        keys = {(round(x, 1), round(y, 1)) for x, y in ring}
        if ring_inside(ring, PARK) and not (keys & used_verts):
            STATE["holes"].append((ring, inners, tag))
            STATE["islands"].extend(inners)
            used_verts |= keys
        else:
            STATE["surface_water"].append((ring, tag))


import json as _json, pathlib as _pl
WATER_JSON = _pl.Path(__file__).resolve().parent.parent / "plateau_data" / "disneysea_water.json"


def plan_water():
    """Final water plan used by the draft and the mock.

    Prefers the water tab's plateau_data/disneysea_water.json (ds_water.py): bodies
    flagged cut=True become ground holes, the rest surface ponds, and the harbour
    stretch that runs under Mysterious Island's rockwork is kept as "tunnels"
    (no ground hole), which removes the water strip across the island. Each body
    carries its own level/ground (relative to the DEM datum). Falls back to the
    plain OSM selection (_plan_water, which ds_water itself builds on)."""
    for k in ("holes", "surface_water", "islands", "tunnels"):
        STATE[k].clear()
    STATE["levels"].clear()
    if not WATER_JSON.exists():
        _plan_water(); STATE["source"] = "osm"; return
    d = _json.loads(WATER_JSON.read_text(encoding="utf-8"))
    for b in d["bodies"]:
        ring = _clean_ring(b["ring"]); inners = [_clean_ring(i) for i in b.get("inners", [])]
        STATE["levels"][b["id"]] = {"level": b["level"], "ground": b["ground"], "depth": b["depth"], "kind": b["kind"]}
        if b["cut"]:
            STATE["holes"].append((ring, inners, b["id"]))
            STATE["islands"].extend(inners)
        else:
            STATE["surface_water"].append((ring, b["id"]))
    STATE["tunnels"] = [_clean_ring(t["ring"]) for t in d.get("tunnels", [])]
    STATE["source"] = "water_json"


def build_ground():
    col = get_collection("Terrain")
    mat = flat_material("mat_ground", (0.55, 0.52, 0.45), roughness=0.95)
    loops = [PARK] + [h[0] for h in STATE["holes"]]
    obj = extrude_loops("Ground", loops, GROUND_Z - GROUND_DEPTH, GROUND_DEPTH, mat, cap_bottom=True)
    if obj is None:  # scanfill refused the holes -> fall back to a solid slab + surface water
        print("[terrain] WARNING: ground with holes failed, using solid slab")
        obj = extrude_footprint("Ground", PARK, GROUND_Z - GROUND_DEPTH, GROUND_DEPTH, mat, cap_bottom=True)
        STATE["surface_water"].extend((h[0], h[2]) for h in STATE["holes"])
        STATE["holes"].clear()
        STATE["islands"].clear()
    link(obj, col)
    for i, isl in enumerate(STATE["islands"]):
        o = extrude_footprint(f"Island_{i}", isl, GROUND_Z - GROUND_DEPTH, GROUND_DEPTH, mat, cap_bottom=False)
        if o:
            link(o, col)
    return obj


def build_water():
    col = get_collection("Water")
    mat = flat_material("mat_water", (0.04, 0.20, 0.30), roughness=0.05)
    mat_bed = flat_material("mat_waterbed", (0.10, 0.14, 0.14), roughness=1.0)
    n = 0
    for ring, inners, tag in STATE["holes"]:
        if tag == "W72388087":  # AquaSphere pool: water + floor come from ds_aquasphere
            continue
        lv = STATE["levels"].get(tag)
        wz = GROUND_Z + (lv["level"] - lv["ground"]) if lv else WATER_Z   # flat draft: keep the freeboard
        bz = max(-GROUND_DEPTH + 0.1, wz - (lv["depth"] if lv else 2.0))
        o = extrude_loops(f"Water_{tag}", [ring] + inners, wz - 0.05, 0.05, mat, cap_bottom=True)
        if o:
            link(o, col); n += 1
        bed = extrude_loops(f"WaterBed_{tag}", [ring] + inners, bz, 0.05, mat_bed)
        if bed:
            link(bed, col)
    for ring, tag in STATE["surface_water"]:
        o = flat_fill(f"Pond_{tag}", ring, GROUND_Z + 0.04, mat, thickness=0.05)
        if o:
            link(o, col); n += 1
    return n


GREEN = {  # tag -> (material name, color, z-top, thickness)
    ("leisure", "garden"):   ("mat_garden", (0.30, 0.45, 0.22), 0.06, 0.06),
    ("landuse", "grass"):    ("mat_grass", (0.33, 0.50, 0.24), 0.05, 0.05),
    ("natural", "grassland"): ("mat_grass", (0.33, 0.50, 0.24), 0.05, 0.05),
    ("landuse", "flowerbed"): ("mat_flowerbed", (0.52, 0.40, 0.28), 0.08, 0.08),
    ("natural", "scrub"):    ("mat_scrub", (0.25, 0.38, 0.18), 1.2, 1.2),
    ("natural", "sand"):     ("mat_sand", (0.80, 0.70, 0.50), 0.05, 0.05),
    ("natural", "beach"):    ("mat_sand", (0.80, 0.70, 0.50), 0.05, 0.05),
    # tree masses: a translucent-looking block standing in for canopy until real trees
    ("landuse", "forest"):   ("mat_tree_mass", (0.14, 0.30, 0.12), 7.0, 5.0),
    ("natural", "wood"):     ("mat_tree_mass", (0.14, 0.30, 0.12), 7.0, 5.0),
}


def build_greenery():
    col = get_collection("Greenery")
    n = 0
    for (k, v), (mname, color, ztop, thick) in GREEN.items():
        mat = flat_material(mname, color, roughness=0.95)
        for w in ways_with(k, v):
            if not in_park(w["pts"]):
                continue
            o = extrude_footprint(f"G_{v}_{w['id']}", w["pts"], GROUND_Z + ztop - thick, thick, mat, cap_bottom=False)
            if o:
                link(o, col); n += 1
        for r, outers, inners in multipolygons(k, v):
            for j, outer in enumerate(outers):
                if not in_park(outer):
                    continue
                holes = [i for i in inners if ring_inside(i, outer)]
                o = extrude_loops(f"G_{v}_R{r['id']}_{j}", [outer] + holes, GROUND_Z + ztop - thick, thick, mat)
                if o:
                    link(o, col); n += 1
    return n


def build_rockwork():
    """Placeholder raised masses for scree/bare_rock clusters (sculpting later)."""
    col = get_collection("Rockwork")
    mat = flat_material("mat_rock", (0.42, 0.34, 0.28), roughness=1.0)
    n = 0
    for key in ("scree", "bare_rock"):
        items = [(w["id"], [w["pts"]]) for w in ways_with("natural", key)]
        items += [(f"R{r['id']}_{j}", [o]) for r, outers, _ in multipolygons("natural", key)
                  for j, o in enumerate(outers)]
        for rid, loops in items:
            if not in_park(loops[0]):
                continue
            area = poly_area(loops[0])
            height = min(14.0, 1.5 + area ** 0.5 * 0.35)  # bigger cluster -> taller mound
            o = extrude_loops(f"Rock_{rid}", loops, GROUND_Z, height, mat)
            if o:
                link(o, col); n += 1
    return n


def _ribbon_faces(name, pts, width, z, mat):
    n = len(pts)
    if n < 2:
        return None
    bm = bmesh.new()
    lefts, rights = [], []
    for i in range(n):
        x, y = pts[i]
        px, py = pts[max(0, i - 1)]
        nx, ny = pts[min(n - 1, i + 1)]
        dx, dy = nx - px, ny - py
        L = (dx * dx + dy * dy) ** 0.5 or 1.0
        ox, oy = -dy / L * width / 2, dx / L * width / 2
        lefts.append(bm.verts.new((x + ox, y + oy, z)))
        rights.append(bm.verts.new((x - ox, y - oy, z)))
    for i in range(n - 1):
        try:
            bm.faces.new((lefts[i], lefts[i + 1], rights[i + 1], rights[i]))
        except ValueError:
            pass
    for f in bm.faces:  # ribbons are open sheets: make every face point up (downward ones render black)
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    return obj


def build_paths():
    col = get_collection("Paths")
    mat_main = flat_material("mat_path_main", (0.78, 0.72, 0.62), roughness=0.9)
    mat_side = flat_material("mat_path_side", (0.70, 0.66, 0.58), roughness=0.9)
    mat_bridge = flat_material("mat_bridge", (0.60, 0.52, 0.44), roughness=0.8)
    n = 0
    widths = {"pedestrian": 8.0, "footway": 3.5, "steps": 3.5, "service": 5.0, "corridor": 3.0}
    for key, width in widths.items():
        for w in ways_with("highway", key, closed_only=False):
            if not in_park(w["pts"]):
                continue
            bridge = w["tags"].get("bridge") in ("yes", "viaduct")
            if w["closed"] and (key == "pedestrian" or w["tags"].get("area") == "yes"):
                o = flat_fill(f"Plaza_{w['id']}", w["pts"], PATH_Z, mat_main, thickness=0.05)
            else:
                z = BRIDGE_Z if bridge else PATH_Z
                mat = mat_bridge if bridge else (mat_main if key == "pedestrian" else mat_side)
                o = _ribbon_faces(f"Path_{w['id']}", w["pts"], width, z, mat)
            if o:
                link(o, col); n += 1
    # entrance plaza (ディズニーシー・プラザ) is a multipolygon relation
    for r in DATA["relations"]:
        if r["id"] == 3297581:
            from ds_core import assemble_rings
            outers = assemble_rings([m["way"] for m in r["members"] if m["role"] == "outer"])
            inners = assemble_rings([m["way"] for m in r["members"] if m["role"] == "inner"])
            for j, o_ring in enumerate(outers):
                o = extrude_loops(f"Plaza_Entrance_{j}", [o_ring] + inners, PATH_Z - 0.05, 0.05, mat_main)
                if o:
                    link(o, col); n += 1
    return n


def build_railway():
    """DisneySea Electric Railway (elevated) as a deck ribbon + piers."""
    col = get_collection("Railway")
    mat_deck = flat_material("mat_rail_deck", (0.35, 0.40, 0.33), roughness=0.7)
    mat_pier = flat_material("mat_rail_pier", (0.45, 0.42, 0.38), roughness=0.8)
    n = 0
    for w in ways_with("railway", "narrow_gauge", closed_only=False):
        name = w["tags"].get("name", "")
        if "エレクトリックレールウェイ" not in name or not in_park(w["pts"]):
            continue
        pts = w["pts"]
        # deck = ribbon extruded 0.8 m thick
        left, right = [], []
        m = len(pts)
        for i in range(m):
            x, y = pts[i]
            px, py = pts[max(0, i - 1)]
            nx, ny = pts[min(m - 1, i + 1)]
            dx, dy = nx - px, ny - py
            L = (dx * dx + dy * dy) ** 0.5 or 1.0
            ox, oy = -dy / L * 2.0, dx / L * 2.0
            left.append((x + ox, y + oy))
            right.append((x - ox, y - oy))
        o = extrude_footprint(f"RailDeck_{w['id']}", left + right[::-1], RAIL_Z, 0.8, mat_deck, cap_bottom=True)
        if o:
            link(o, col); n += 1
        # piers every ~18 m
        acc = 0.0
        for i in range(1, m):
            (x0, y0), (x1, y1) = pts[i - 1], pts[i]
            seg = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            t = 18.0 - acc
            while t <= seg:
                px_, py_ = x0 + (x1 - x0) * t / seg, y0 + (y1 - y0) * t / seg
                sq = [(px_ - 0.6, py_ - 0.6), (px_ + 0.6, py_ - 0.6), (px_ + 0.6, py_ + 0.6), (px_ - 0.6, py_ + 0.6)]
                p = extrude_footprint(f"RailPier_{w['id']}_{i}_{int(t)}", sq, GROUND_Z, RAIL_Z, mat_pier)
                if p:
                    link(p, col)
                t += 18.0
            acc = seg - (t - 18.0)  # distance from the last pier to the segment end
    return n


def build_all():
    plan_water()
    build_ground()
    nw = build_water()
    ng = build_greenery()
    nr = build_rockwork()
    np_ = build_paths()
    nrl = build_railway()
    print(f"[terrain] water from {STATE['source']}: holes={len(STATE['holes'])} islands={len(STATE['islands'])} tunnels={len(STATE['tunnels'])} "
          f"water_objs={nw} green={ng} rock={nr} paths={np_} rail={nrl}")
